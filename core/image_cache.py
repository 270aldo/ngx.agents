"""
Sistema de caché para imágenes procesadas.

Este módulo proporciona un sistema de caché para almacenar temporalmente
imágenes procesadas y sus resultados, reduciendo la necesidad de
reprocesamiento y llamadas a APIs externas.
"""

import asyncio
import base64
import hashlib
import time
from typing import Dict, Any, Optional, Union

from core.logging_config import get_logger
from core.telemetry import Telemetry

# Configurar logger
logger = get_logger(__name__)


class ImageCache:
    """
    Sistema de caché para almacenar temporalmente imágenes procesadas y sus resultados.

    Utiliza un diccionario en memoria con expiración de entradas para evitar
    el crecimiento descontrolado de la memoria.
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600,
        telemetry: Optional[Telemetry] = None,
    ):
        """
        Inicializa el sistema de caché de imágenes.

        Args:
            max_size: Tamaño máximo de la caché (número de imágenes)
            ttl_seconds: Tiempo de vida de las entradas en segundos
            telemetry: Instancia de Telemetry para métricas y trazas (opcional)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.telemetry = telemetry
        self.lock = asyncio.Lock()

        # Estadísticas
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0,
            "bytes_saved": 0,
        }

        logger.info(
            f"ImageCache inicializado con max_size={max_size}, ttl_seconds={ttl_seconds}"
        )

    async def get(
        self, key: str, operation_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene un resultado de la caché si existe y no ha expirado.

        Args:
            key: Clave de la caché (hash de la imagen + parámetros)
            operation_type: Tipo de operación (analyze_image, extract_text, etc.)

        Returns:
            Dict[str, Any] o None: Resultado almacenado en caché o None si no existe o ha expirado
        """
        span = None
        if self.telemetry:
            span = self.telemetry.start_span("image_cache.get")
            self.telemetry.add_span_attribute(span, "key", key)
            if operation_type:
                self.telemetry.add_span_attribute(
                    span, "operation_type", operation_type
                )

        try:
            async with self.lock:
                if key in self.cache:
                    entry = self.cache[key]

                    # Verificar si ha expirado
                    if time.time() - entry["timestamp"] > self.ttl_seconds:
                        # Expirado, eliminar de la caché
                        del self.cache[key]
                        self.stats["size"] -= 1
                        self.stats["evictions"] += 1

                        if self.telemetry:
                            self.telemetry.add_span_attribute(
                                span, "cache_result", "expired"
                            )
                            self.telemetry.record_metric(
                                "image_cache.expired",
                                1,
                                {"operation_type": operation_type or "unknown"},
                            )

                        logger.debug(f"Caché expirada para clave: {key}")
                        return None

                    # Incrementar contador de hits
                    self.stats["hits"] += 1

                    if self.telemetry:
                        self.telemetry.add_span_attribute(span, "cache_result", "hit")
                        self.telemetry.record_metric(
                            "image_cache.hits",
                            1,
                            {"operation_type": operation_type or "unknown"},
                        )

                    logger.debug(f"Caché hit para clave: {key}")
                    return entry["result"]

                # No encontrado en caché
                self.stats["misses"] += 1

                if self.telemetry:
                    self.telemetry.add_span_attribute(span, "cache_result", "miss")
                    self.telemetry.record_metric(
                        "image_cache.misses",
                        1,
                        {"operation_type": operation_type or "unknown"},
                    )

                logger.debug(f"Caché miss para clave: {key}")
                return None

        except Exception as e:
            logger.error(f"Error al obtener de caché: {e}", exc_info=True)

            if self.telemetry and span:
                self.telemetry.record_exception(span, e)

            return None
        finally:
            if self.telemetry and span:
                self.telemetry.end_span(span)

    async def set(
        self,
        key: str,
        result: Dict[str, Any],
        image_size: int = 0,
        operation_type: Optional[str] = None,
    ) -> None:
        """
        Almacena un resultado en la caché.

        Args:
            key: Clave de la caché (hash de la imagen + parámetros)
            result: Resultado a almacenar
            image_size: Tamaño aproximado de la imagen en bytes
            operation_type: Tipo de operación (analyze_image, extract_text, etc.)
        """
        span = None
        if self.telemetry:
            span = self.telemetry.start_span("image_cache.set")
            self.telemetry.add_span_attribute(span, "key", key)
            self.telemetry.add_span_attribute(span, "image_size", image_size)
            if operation_type:
                self.telemetry.add_span_attribute(
                    span, "operation_type", operation_type
                )

        try:
            async with self.lock:
                # Si la caché está llena, eliminar la entrada más antigua
                if len(self.cache) >= self.max_size and key not in self.cache:
                    oldest_key = None
                    oldest_time = float("inf")

                    for k, v in self.cache.items():
                        if v["timestamp"] < oldest_time:
                            oldest_time = v["timestamp"]
                            oldest_key = k

                    if oldest_key:
                        del self.cache[oldest_key]
                        self.stats["evictions"] += 1

                        if self.telemetry:
                            self.telemetry.record_metric(
                                "image_cache.evictions",
                                1,
                                {"operation_type": operation_type or "unknown"},
                            )

                        logger.debug(f"Caché evicción para clave: {oldest_key}")

                # Almacenar el resultado
                self.cache[key] = {
                    "result": result,
                    "timestamp": time.time(),
                    "image_size": image_size,
                }

                # Actualizar estadísticas
                if key not in self.cache:
                    self.stats["size"] += 1

                self.stats["bytes_saved"] += image_size

                if self.telemetry:
                    self.telemetry.record_metric(
                        "image_cache.sets",
                        1,
                        {"operation_type": operation_type or "unknown"},
                    )
                    self.telemetry.record_metric("image_cache.size", len(self.cache))

                logger.debug(f"Caché set para clave: {key}")

        except Exception as e:
            logger.error(f"Error al almacenar en caché: {e}", exc_info=True)

            if self.telemetry and span:
                self.telemetry.record_exception(span, e)
        finally:
            if self.telemetry and span:
                self.telemetry.end_span(span)

    async def generate_key(
        self, image_data: Union[str, bytes], params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Genera una clave única para la caché basada en la imagen y los parámetros.

        Args:
            image_data: Datos de la imagen (base64 o bytes)
            params: Parámetros adicionales que afectan al resultado

        Returns:
            str: Clave única para la caché
        """
        # Convertir imagen a bytes si es necesario
        if isinstance(image_data, str):
            if image_data.startswith("data:image"):
                # Es un data URI, extraer la parte base64
                image_bytes = base64.b64decode(image_data.split(",")[1])
            elif "," in image_data:
                # Posible data URI sin prefijo
                image_bytes = base64.b64decode(image_data.split(",")[1])
            else:
                # Asumir que es directamente base64
                try:
                    image_bytes = base64.b64decode(image_data)
                except Exception:
                    # Si falla, usar el string directamente
                    image_bytes = image_data.encode("utf-8")
        else:
            image_bytes = image_data

        # Calcular hash de la imagen
        image_hash = hashlib.md5(image_bytes).hexdigest()

        # Si hay parámetros, incluirlos en la clave
        if params:
            # Convertir parámetros a string y calcular hash
            params_str = str(sorted(params.items()))
            params_hash = hashlib.md5(params_str.encode("utf-8")).hexdigest()
            return f"{image_hash}_{params_hash}"

        return image_hash

    async def clear_expired(self) -> int:
        """
        Elimina todas las entradas expiradas de la caché.

        Returns:
            int: Número de entradas eliminadas
        """
        span = None
        if self.telemetry:
            span = self.telemetry.start_span("image_cache.clear_expired")

        try:
            async with self.lock:
                current_time = time.time()
                keys_to_remove = []

                for key, entry in self.cache.items():
                    if current_time - entry["timestamp"] > self.ttl_seconds:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self.cache[key]

                # Actualizar estadísticas
                self.stats["evictions"] += len(keys_to_remove)
                self.stats["size"] = len(self.cache)

                if self.telemetry:
                    self.telemetry.add_span_attribute(
                        span, "expired_entries_removed", len(keys_to_remove)
                    )
                    self.telemetry.record_metric(
                        "image_cache.expired_entries_removed", len(keys_to_remove)
                    )

                logger.debug(
                    f"Eliminadas {len(keys_to_remove)} entradas expiradas de la caché"
                )
                return len(keys_to_remove)

        except Exception as e:
            logger.error(f"Error al limpiar caché expirada: {e}", exc_info=True)

            if self.telemetry and span:
                self.telemetry.record_exception(span, e)

            return 0
        finally:
            if self.telemetry and span:
                self.telemetry.end_span(span)

    async def clear(self) -> None:
        """
        Limpia completamente la caché.
        """
        span = None
        if self.telemetry:
            span = self.telemetry.start_span("image_cache.clear")

        try:
            async with self.lock:
                previous_size = len(self.cache)
                self.cache.clear()

                # Actualizar estadísticas
                self.stats["evictions"] += previous_size
                self.stats["size"] = 0

                if self.telemetry:
                    self.telemetry.add_span_attribute(
                        span, "entries_removed", previous_size
                    )
                    self.telemetry.record_metric("image_cache.clear", 1)
                    self.telemetry.record_metric("image_cache.size", 0)

                logger.debug(
                    f"Caché limpiada completamente, eliminadas {previous_size} entradas"
                )

        except Exception as e:
            logger.error(f"Error al limpiar caché: {e}", exc_info=True)

            if self.telemetry and span:
                self.telemetry.record_exception(span, e)
        finally:
            if self.telemetry and span:
                self.telemetry.end_span(span)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la caché.

        Returns:
            Dict[str, Any]: Estadísticas de la caché
        """
        async with self.lock:
            # Calcular tasa de aciertos
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

            return {
                **self.stats,
                "hit_rate": hit_rate,
                "current_size": len(self.cache),
                "max_size": self.max_size,
            }


# Instancia global de la caché
image_cache = ImageCache()

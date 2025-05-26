"""
Sistema de caché específico por dominio.

Este módulo proporciona funcionalidades para implementar estrategias de caché
específicas por dominio, con el objetivo de reducir el uso de tokens en
llamadas a modelos de lenguaje.
"""

import logging
import time
import hashlib
import json
from typing import Dict, Any, Optional, List, Callable
import asyncio
from enum import Enum
from functools import wraps

# Configurar logger
logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    """Estrategias de caché disponibles."""

    EXACT_MATCH = "exact_match"  # Coincidencia exacta de prompts
    SEMANTIC_MATCH = "semantic_match"  # Coincidencia semántica (requiere embedding)
    PARAMETERIZED = "parameterized"  # Caché con parámetros (ej: fecha, usuario)
    DOMAIN_SPECIFIC = "domain_specific"  # Reglas específicas por dominio


class CacheEntry:
    """Entrada de caché con metadatos."""

    def __init__(
        self,
        key: str,
        value: Any,
        domain: str,
        ttl: Optional[int] = None,
        created_at: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Inicializa una entrada de caché.

        Args:
            key: Clave de la entrada
            value: Valor almacenado
            domain: Dominio al que pertenece la entrada
            ttl: Tiempo de vida en segundos (None = sin expiración)
            created_at: Timestamp de creación (None = ahora)
            metadata: Metadatos adicionales
        """
        self.key = key
        self.value = value
        self.domain = domain
        self.ttl = ttl
        self.created_at = created_at or time.time()
        self.metadata = metadata or {}
        self.access_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """
        Verifica si la entrada ha expirado.

        Returns:
            True si la entrada ha expirado, False en caso contrario
        """
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl

    def access(self) -> None:
        """Registra un acceso a la entrada."""
        self.access_count += 1
        self.last_accessed = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la entrada a un diccionario.

        Returns:
            Diccionario con los datos de la entrada
        """
        return {
            "key": self.key,
            "value": self.value,
            "domain": self.domain,
            "ttl": self.ttl,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }


class DomainCache:
    """
    Caché específico por dominio.

    Esta clase proporciona funcionalidades para implementar estrategias de caché
    específicas por dominio, con el objetivo de reducir el uso de tokens en
    llamadas a modelos de lenguaje.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "DomainCache":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(DomainCache, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_size: int = 10000, cleanup_interval: int = 3600):
        """
        Inicializa el caché.

        Args:
            max_size: Tamaño máximo del caché (número de entradas)
            cleanup_interval: Intervalo de limpieza en segundos
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self.cache: Dict[str, CacheEntry] = {}
        self.domain_rules: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task = None
        self._initialized = True

        # Iniciar tarea de limpieza
        self._start_cleanup_task()

        logger.info(
            f"DomainCache inicializado (max_size={max_size}, cleanup_interval={cleanup_interval}s)"
        )

    def _start_cleanup_task(self) -> None:
        """Inicia la tarea de limpieza periódica."""

        async def cleanup_task():
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup()

        loop = asyncio.get_event_loop()
        self._cleanup_task = loop.create_task(cleanup_task())

    def _generate_key(
        self,
        prompt: str,
        domain: str,
        strategy: CacheStrategy,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Genera una clave de caché.

        Args:
            prompt: Prompt a cachear
            domain: Dominio del prompt
            strategy: Estrategia de caché
            params: Parámetros adicionales

        Returns:
            Clave de caché
        """
        if strategy == CacheStrategy.EXACT_MATCH:
            # Usar hash del prompt como clave
            return f"{domain}:{hashlib.md5(prompt.encode()).hexdigest()}"
        elif strategy == CacheStrategy.PARAMETERIZED:
            # Incluir parámetros en la clave
            params_str = json.dumps(params or {}, sort_keys=True)
            return f"{domain}:{hashlib.md5((prompt + params_str).encode()).hexdigest()}"
        elif strategy == CacheStrategy.DOMAIN_SPECIFIC:
            # Usar reglas específicas del dominio
            domain_rule = self.domain_rules.get(domain, {})
            key_func = domain_rule.get("key_function")
            if key_func and callable(key_func):
                return f"{domain}:{key_func(prompt, params)}"
            # Fallback a exact match
            return f"{domain}:{hashlib.md5(prompt.encode()).hexdigest()}"
        else:
            # Fallback para semantic match y otros
            return f"{domain}:{hashlib.md5(prompt.encode()).hexdigest()}"

    async def get(
        self,
        prompt: str,
        domain: str,
        strategy: CacheStrategy = CacheStrategy.EXACT_MATCH,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Obtiene un valor del caché.

        Args:
            prompt: Prompt a buscar
            domain: Dominio del prompt
            strategy: Estrategia de caché
            params: Parámetros adicionales

        Returns:
            Valor cacheado o None si no existe
        """
        async with self._lock:
            if strategy == CacheStrategy.SEMANTIC_MATCH:
                # Buscar coincidencia semántica
                return await self._semantic_search(prompt, domain, params)

            # Generar clave según la estrategia
            key = self._generate_key(prompt, domain, strategy, params)

            # Buscar en caché
            entry = self.cache.get(key)
            if entry is None:
                return None

            # Verificar si ha expirado
            if entry.is_expired():
                del self.cache[key]
                return None

            # Registrar acceso
            entry.access()

            return entry.value

    async def _semantic_search(
        self, prompt: str, domain: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Realiza una búsqueda semántica en el caché.

        Args:
            prompt: Prompt a buscar
            domain: Dominio del prompt
            params: Parámetros adicionales

        Returns:
            Valor cacheado o None si no existe
        """
        # Obtener función de embedding para el dominio
        domain_rule = self.domain_rules.get(domain, {})
        embed_func = domain_rule.get("embed_function")
        similarity_threshold = domain_rule.get("similarity_threshold", 0.9)

        if not embed_func or not callable(embed_func):
            logger.warning(
                f"No se encontró función de embedding para el dominio {domain}"
            )
            return None

        try:
            # Obtener embedding del prompt
            prompt_embedding = await embed_func(prompt)

            # Buscar entradas del mismo dominio
            domain_entries = [
                entry
                for entry in self.cache.values()
                if entry.domain == domain and not entry.is_expired()
            ]

            best_match = None
            best_similarity = 0.0

            for entry in domain_entries:
                # Obtener embedding cacheado o calcularlo
                cached_embedding = entry.metadata.get("embedding")
                if cached_embedding is None:
                    # Si no hay embedding cacheado, obtener el prompt original y calcular
                    original_prompt = entry.metadata.get("original_prompt")
                    if original_prompt:
                        cached_embedding = await embed_func(original_prompt)
                        # Cachear el embedding para futuras búsquedas
                        entry.metadata["embedding"] = cached_embedding

                if cached_embedding:
                    # Calcular similitud
                    similarity = self._calculate_similarity(
                        prompt_embedding, cached_embedding
                    )
                    if (
                        similarity > best_similarity
                        and similarity >= similarity_threshold
                    ):
                        best_similarity = similarity
                        best_match = entry

            if best_match:
                # Registrar acceso
                best_match.access()
                logger.info(
                    f"Coincidencia semántica encontrada para dominio {domain} (similitud: {best_similarity:.2f})"
                )
                return best_match.value

            return None

        except Exception as e:
            logger.error(f"Error en búsqueda semántica para dominio {domain}: {e}")
            return None

    def _calculate_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """
        Calcula la similitud coseno entre dos embeddings.

        Args:
            embedding1: Primer embedding
            embedding2: Segundo embedding

        Returns:
            Similitud coseno (0-1)
        """
        import numpy as np

        # Convertir a arrays de numpy
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Calcular similitud coseno
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def set(
        self,
        prompt: str,
        value: Any,
        domain: str,
        ttl: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.EXACT_MATCH,
        params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Establece un valor en el caché.

        Args:
            prompt: Prompt a cachear
            value: Valor a almacenar
            domain: Dominio del prompt
            ttl: Tiempo de vida en segundos (None = sin expiración)
            strategy: Estrategia de caché
            params: Parámetros adicionales
            metadata: Metadatos adicionales
        """
        async with self._lock:
            # Verificar si se debe limpiar el caché
            if len(self.cache) >= self.max_size:
                await self._evict_entries()

            # Generar clave según la estrategia
            key = self._generate_key(prompt, domain, strategy, params)

            # Preparar metadatos
            entry_metadata = metadata or {}
            entry_metadata["strategy"] = strategy
            entry_metadata["original_prompt"] = prompt

            if params:
                entry_metadata["params"] = params

            # Si es búsqueda semántica, calcular embedding
            if strategy == CacheStrategy.SEMANTIC_MATCH:
                domain_rule = self.domain_rules.get(domain, {})
                embed_func = domain_rule.get("embed_function")

                if embed_func and callable(embed_func):
                    try:
                        embedding = await embed_func(prompt)
                        entry_metadata["embedding"] = embedding
                    except Exception as e:
                        logger.error(
                            f"Error al calcular embedding para dominio {domain}: {e}"
                        )

            # Crear entrada
            entry = CacheEntry(
                key=key, value=value, domain=domain, ttl=ttl, metadata=entry_metadata
            )

            # Almacenar en caché
            self.cache[key] = entry

    async def _evict_entries(self) -> None:
        """Elimina entradas del caché según política de evicción."""
        # Primero eliminar entradas expiradas
        expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self.cache[key]

        # Si aún se necesita espacio, eliminar las entradas menos usadas
        if len(self.cache) >= self.max_size:
            # Ordenar por número de accesos y tiempo del último acceso
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: (x[1].access_count, x[1].last_accessed),
            )

            # Eliminar el 10% de las entradas menos usadas
            entries_to_remove = max(1, int(len(self.cache) * 0.1))
            for key, _ in sorted_entries[:entries_to_remove]:
                del self.cache[key]

    async def cleanup(self) -> int:
        """
        Elimina entradas expiradas del caché.

        Returns:
            Número de entradas eliminadas
        """
        async with self._lock:
            before_count = len(self.cache)

            # Eliminar entradas expiradas
            expired_keys = [
                key for key, entry in self.cache.items() if entry.is_expired()
            ]
            for key in expired_keys:
                del self.cache[key]

            removed_count = before_count - len(self.cache)
            if removed_count > 0:
                logger.info(f"Limpieza de caché: {removed_count} entradas eliminadas")

            return removed_count

    def register_domain_rule(
        self,
        domain: str,
        key_function: Optional[Callable] = None,
        embed_function: Optional[Callable] = None,
        similarity_threshold: float = 0.9,
        default_ttl: Optional[int] = None,
    ) -> None:
        """
        Registra reglas específicas para un dominio.

        Args:
            domain: Nombre del dominio
            key_function: Función para generar claves de caché
            embed_function: Función para generar embeddings
            similarity_threshold: Umbral de similitud para búsquedas semánticas
            default_ttl: TTL por defecto para este dominio
        """
        self.domain_rules[domain] = {
            "key_function": key_function,
            "embed_function": embed_function,
            "similarity_threshold": similarity_threshold,
            "default_ttl": default_ttl,
        }

        logger.info(f"Reglas de dominio registradas para {domain}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché.

        Returns:
            Diccionario con estadísticas
        """
        stats = {
            "total_entries": len(self.cache),
            "max_size": self.max_size,
            "domains": {},
            "strategies": {
                "exact_match": 0,
                "semantic_match": 0,
                "parameterized": 0,
                "domain_specific": 0,
            },
        }

        # Agrupar por dominio y estrategia
        for entry in self.cache.values():
            # Contar por dominio
            if entry.domain not in stats["domains"]:
                stats["domains"][entry.domain] = 0
            stats["domains"][entry.domain] += 1

            # Contar por estrategia
            strategy = entry.metadata.get("strategy", CacheStrategy.EXACT_MATCH)
            if strategy in stats["strategies"]:
                stats["strategies"][strategy] += 1

        return stats

    def clear(self, domain: Optional[str] = None) -> int:
        """
        Limpia el caché.

        Args:
            domain: Dominio a limpiar (None = todos)

        Returns:
            Número de entradas eliminadas
        """
        before_count = len(self.cache)

        if domain:
            # Eliminar solo entradas del dominio especificado
            keys_to_remove = [
                key for key, entry in self.cache.items() if entry.domain == domain
            ]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            # Limpiar todo el caché
            self.cache.clear()

        removed_count = before_count - len(self.cache)
        logger.info(f"Caché limpiado: {removed_count} entradas eliminadas")

        return removed_count


# Función decoradora para cachear resultados de funciones
def cached(
    domain: str,
    ttl: Optional[int] = None,
    strategy: CacheStrategy = CacheStrategy.EXACT_MATCH,
    param_keys: Optional[List[str]] = None,
):
    """
    Decorador para cachear resultados de funciones.

    Args:
        domain: Dominio del caché
        ttl: Tiempo de vida en segundos
        strategy: Estrategia de caché
        param_keys: Lista de nombres de parámetros a incluir en la clave de caché

    Returns:
        Decorador configurado
    """

    def decorator(func):
        @wraps(func)
        async def wrapper_async(*args, **kwargs):
            # Obtener instancia del caché
            cache = DomainCache()

            # Extraer prompt del primer argumento
            prompt = args[0] if args else kwargs.get("prompt", "")

            # Extraer parámetros relevantes
            params = {}
            if param_keys:
                for key in param_keys:
                    if key in kwargs:
                        params[key] = kwargs[key]

            # Intentar obtener del caché
            cached_result = await cache.get(prompt, domain, strategy, params)
            if cached_result is not None:
                logger.debug(f"Resultado obtenido de caché para dominio {domain}")
                return cached_result

            # Ejecutar función original
            result = await func(*args, **kwargs)

            # Almacenar en caché
            await cache.set(prompt, result, domain, ttl, strategy, params)

            return result

        @wraps(func)
        def wrapper_sync(*args, **kwargs):
            # Para funciones síncronas, crear una versión asíncrona y ejecutarla
            async def async_wrapper():
                # Obtener instancia del caché
                cache = DomainCache()

                # Extraer prompt del primer argumento
                prompt = args[0] if args else kwargs.get("prompt", "")

                # Extraer parámetros relevantes
                params = {}
                if param_keys:
                    for key in param_keys:
                        if key in kwargs:
                            params[key] = kwargs[key]

                # Intentar obtener del caché
                cached_result = await cache.get(prompt, domain, strategy, params)
                if cached_result is not None:
                    logger.debug(f"Resultado obtenido de caché para dominio {domain}")
                    return cached_result

                # Ejecutar función original
                result = func(*args, **kwargs)

                # Almacenar en caché
                await cache.set(prompt, result, domain, ttl, strategy, params)

                return result

            # Ejecutar la versión asíncrona
            import asyncio

            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper())

        # Determinar si la función original es asíncrona
        if asyncio.iscoroutinefunction(func):
            return wrapper_async
        else:
            return wrapper_sync

    return decorator


# Instancia global para uso en toda la aplicación
domain_cache = DomainCache()

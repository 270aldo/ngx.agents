"""
Procesador de documentos estructurados.

Este módulo proporciona funcionalidades para analizar y extraer información
de documentos estructurados como tablas, formularios y otros tipos de documentos
con estructura definida.
"""

import asyncio
import base64
import io
import os
import time
from typing import Dict, Any, Optional, Union, List, Tuple

import pandas as pd
from PIL import Image

from core.logging_config import get_logger
from core.telemetry import Telemetry
from core.image_cache import image_cache
from core.vision_metrics import vision_metrics

# Configurar logger
logger = get_logger(__name__)


class DocumentProcessor:
    """
    Procesador de documentos estructurados.

    Proporciona métodos para extraer información estructurada de documentos,
    incluyendo tablas, formularios, y otros elementos con estructura definida.
    """

    def __init__(self, telemetry: Optional[Telemetry] = None):
        """
        Inicializa el procesador de documentos estructurados.

        Args:
            telemetry: Instancia de Telemetry para métricas y trazas (opcional)
        """
        self.telemetry = telemetry
        self.lock = asyncio.Lock()

        # Estadísticas
        self.stats = {
            "documents_processed": 0,
            "tables_extracted": 0,
            "forms_extracted": 0,
            "errors": 0,
            "processing_time_ms": 0,
        }

        logger.info("DocumentProcessor inicializado")

    async def extract_tables(
        self,
        image_data: Union[str, bytes, Dict[str, Any]],
        language_code: str = "es-ES",
        agent_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Extrae tablas de un documento o imagen.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            language_code: Código de idioma para el OCR
            agent_id: ID del agente que realiza la solicitud (para métricas)

        Returns:
            Dict[str, Any]: Tablas extraídas y metadatos
        """
        span = None
        start_time = time.time()

        if self.telemetry:
            span = self.telemetry.start_span("document_processor.extract_tables")
            self.telemetry.add_span_attribute(span, "language_code", language_code)
            self.telemetry.add_span_attribute(span, "agent_id", agent_id)

        try:
            # Procesar la entrada de imagen
            processed_image, image_format, image_size = await self._process_image_input(
                image_data
            )

            # Generar clave para caché
            cache_key = await image_cache.generate_key(
                processed_image,
                {"operation": "extract_tables", "language_code": language_code},
            )

            # Verificar caché
            cached_result = await image_cache.get(cache_key, "extract_tables")
            if cached_result:
                # Registrar métricas de caché hit
                await vision_metrics.record_cache_operation(hit=True)

                if self.telemetry:
                    self.telemetry.add_span_attribute(span, "cache_hit", True)
                    self.telemetry.record_metric("document_processor.cache_hits", 1)

                logger.debug(f"Caché hit para extract_tables con clave: {cache_key}")
                return cached_result

            # Registrar métricas de caché miss
            await vision_metrics.record_cache_operation(hit=False)

            if self.telemetry:
                self.telemetry.add_span_attribute(span, "cache_hit", False)
                self.telemetry.record_metric("document_processor.cache_misses", 1)

            # Implementar la extracción de tablas
            # Aquí se implementaría la lógica para detectar y extraer tablas
            # usando OCR y algoritmos de detección de estructuras

            # Simulación de extracción de tablas para este ejemplo
            tables = await self._detect_and_extract_tables(
                processed_image, language_code
            )

            # Preparar resultado
            result = {
                "tables": tables,
                "metadata": {
                    "language_code": language_code,
                    "table_count": len(tables),
                    "processing_time_ms": (time.time() - start_time) * 1000,
                },
            }

            # Guardar en caché
            await image_cache.set(cache_key, result, image_size, "extract_tables")

            # Actualizar estadísticas
            async with self.lock:
                self.stats["documents_processed"] += 1
                self.stats["tables_extracted"] += len(tables)
                self.stats["processing_time_ms"] += (time.time() - start_time) * 1000

            # Registrar métricas
            latency_ms = (time.time() - start_time) * 1000
            await vision_metrics.record_api_call(
                operation="extract_tables",
                agent_id=agent_id,
                success=True,
                latency_ms=latency_ms,
            )

            if self.telemetry:
                self.telemetry.add_span_attribute(span, "table_count", len(tables))
                self.telemetry.add_span_attribute(
                    span, "processing_time_ms", latency_ms
                )
                self.telemetry.record_metric(
                    "document_processor.tables_extracted", len(tables)
                )

            return result

        except Exception as e:
            # Actualizar estadísticas de error
            async with self.lock:
                self.stats["errors"] += 1

            # Registrar error
            logger.error(f"Error al extraer tablas: {e}", exc_info=True)

            # Registrar métricas de error
            latency_ms = (time.time() - start_time) * 1000
            await vision_metrics.record_api_call(
                operation="extract_tables",
                agent_id=agent_id,
                success=False,
                latency_ms=latency_ms,
                error_type=type(e).__name__,
            )

            if self.telemetry and span:
                self.telemetry.record_exception(span, e)

            return {
                "error": str(e),
                "tables": [],
                "metadata": {
                    "error_type": type(e).__name__,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                },
            }
        finally:
            if self.telemetry and span:
                self.telemetry.end_span(span)

    async def extract_forms(
        self,
        image_data: Union[str, bytes, Dict[str, Any]],
        language_code: str = "es-ES",
        agent_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Extrae datos de formularios de un documento o imagen.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            language_code: Código de idioma para el OCR
            agent_id: ID del agente que realiza la solicitud (para métricas)

        Returns:
            Dict[str, Any]: Datos de formularios extraídos y metadatos
        """
        span = None
        start_time = time.time()

        if self.telemetry:
            span = self.telemetry.start_span("document_processor.extract_forms")
            self.telemetry.add_span_attribute(span, "language_code", language_code)
            self.telemetry.add_span_attribute(span, "agent_id", agent_id)

        try:
            # Procesar la entrada de imagen
            processed_image, image_format, image_size = await self._process_image_input(
                image_data
            )

            # Generar clave para caché
            cache_key = await image_cache.generate_key(
                processed_image,
                {"operation": "extract_forms", "language_code": language_code},
            )

            # Verificar caché
            cached_result = await image_cache.get(cache_key, "extract_forms")
            if cached_result:
                # Registrar métricas de caché hit
                await vision_metrics.record_cache_operation(hit=True)

                if self.telemetry:
                    self.telemetry.add_span_attribute(span, "cache_hit", True)
                    self.telemetry.record_metric("document_processor.cache_hits", 1)

                logger.debug(f"Caché hit para extract_forms con clave: {cache_key}")
                return cached_result

            # Registrar métricas de caché miss
            await vision_metrics.record_cache_operation(hit=False)

            if self.telemetry:
                self.telemetry.add_span_attribute(span, "cache_hit", False)
                self.telemetry.record_metric("document_processor.cache_misses", 1)

            # Implementar la extracción de formularios
            # Aquí se implementaría la lógica para detectar y extraer datos de formularios

            # Simulación de extracción de formularios para este ejemplo
            form_fields = await self._detect_and_extract_form_fields(
                processed_image, language_code
            )

            # Preparar resultado
            result = {
                "form_fields": form_fields,
                "metadata": {
                    "language_code": language_code,
                    "field_count": len(form_fields),
                    "processing_time_ms": (time.time() - start_time) * 1000,
                },
            }

            # Guardar en caché
            await image_cache.set(cache_key, result, image_size, "extract_forms")

            # Actualizar estadísticas
            async with self.lock:
                self.stats["documents_processed"] += 1
                self.stats["forms_extracted"] += 1
                self.stats["processing_time_ms"] += (time.time() - start_time) * 1000

            # Registrar métricas
            latency_ms = (time.time() - start_time) * 1000
            await vision_metrics.record_api_call(
                operation="extract_forms",
                agent_id=agent_id,
                success=True,
                latency_ms=latency_ms,
            )

            if self.telemetry:
                self.telemetry.add_span_attribute(span, "field_count", len(form_fields))
                self.telemetry.add_span_attribute(
                    span, "processing_time_ms", latency_ms
                )
                self.telemetry.record_metric("document_processor.forms_extracted", 1)

            return result

        except Exception as e:
            # Actualizar estadísticas de error
            async with self.lock:
                self.stats["errors"] += 1

            # Registrar error
            logger.error(f"Error al extraer formularios: {e}", exc_info=True)

            # Registrar métricas de error
            latency_ms = (time.time() - start_time) * 1000
            await vision_metrics.record_api_call(
                operation="extract_forms",
                agent_id=agent_id,
                success=False,
                latency_ms=latency_ms,
                error_type=type(e).__name__,
            )

            if self.telemetry and span:
                self.telemetry.record_exception(span, e)

            return {
                "error": str(e),
                "form_fields": [],
                "metadata": {
                    "error_type": type(e).__name__,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                },
            }
        finally:
            if self.telemetry and span:
                self.telemetry.end_span(span)

    async def _process_image_input(
        self, image_data: Union[str, bytes, Dict[str, Any]]
    ) -> Tuple[bytes, str, int]:
        """
        Procesa la entrada de imagen en diferentes formatos.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)

        Returns:
            Tuple[bytes, str, int]: Bytes de la imagen, formato detectado y tamaño
        """
        # Si ya es bytes, devolver directamente
        if isinstance(image_data, bytes):
            return image_data, "unknown", len(image_data)

        # Si es una cadena base64, decodificar
        if isinstance(image_data, str) and image_data.startswith(
            ("data:image", "base64:")
        ):
            # Extraer la parte base64 si tiene prefijo
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
            elif image_data.startswith("base64:"):
                image_data = image_data[7:]

            # Decodificar
            image_bytes = base64.b64decode(image_data)
            return image_bytes, "unknown", len(image_bytes)

        # Si es un diccionario, procesar según las claves
        if isinstance(image_data, dict):
            # Si tiene URL, descargar la imagen
            if "url" in image_data:
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    async with session.get(image_data["url"]) as response:
                        if response.status == 200:
                            data = await response.read()
                            format_detected = (
                                os.path.splitext(image_data["url"])[1]
                                .lower()
                                .replace(".", "")
                            )
                            if not format_detected:
                                format_detected = "jpeg"  # Asumir JPEG
                            return data, format_detected, len(data)
                        else:
                            raise ValueError(
                                f"Error al descargar imagen de URL: {response.status}"
                            )

            # Si tiene path, leer el archivo
            elif "path" in image_data:
                path = image_data["path"]
                if not os.path.exists(path):
                    raise FileNotFoundError(
                        f"No se encontró el archivo de imagen: {path}"
                    )

                with open(path, "rb") as f:
                    data = f.read()
                format_detected = os.path.splitext(path)[1].lower().replace(".", "")
                if not format_detected:
                    format_detected = "jpeg"  # Asumir JPEG
                return data, format_detected, len(data)

            # Si tiene base64, extraer
            elif "base64" in image_data:
                base64_data = image_data["base64"]
                format_detected = image_data.get(
                    "format", "jpeg"
                )  # Usar formato proporcionado o asumir JPEG
                image_bytes = base64.b64decode(base64_data)
                return image_bytes, format_detected, len(image_bytes)

        # Si es una cadena que no es base64, asumir que es una ruta de archivo
        if isinstance(image_data, str):
            if not os.path.exists(image_data):
                raise FileNotFoundError(
                    f"No se encontró el archivo de imagen: {image_data}"
                )

            with open(image_data, "rb") as f:
                data = f.read()
            format_detected = os.path.splitext(image_data)[1].lower().replace(".", "")
            if not format_detected:
                format_detected = "jpeg"  # Asumir JPEG
            return data, format_detected, len(data)

        raise ValueError("Formato de imagen no soportado")

    async def _detect_and_extract_tables(
        self, image_bytes: bytes, language_code: str
    ) -> List[Dict[str, Any]]:
        """
        Detecta y extrae tablas de una imagen.

        Args:
            image_bytes: Bytes de la imagen
            language_code: Código de idioma para el OCR

        Returns:
            List[Dict[str, Any]]: Lista de tablas extraídas
        """
        # Implementación simulada para este ejemplo
        # En una implementación real, se utilizaría un modelo de ML para detectar tablas
        # y extraer su estructura y contenido

        # Abrir la imagen con PIL
        img = Image.open(io.BytesIO(image_bytes))

        # Simulación de detección de tablas
        # En una implementación real, aquí se utilizaría un modelo de visión por computadora

        # Simulamos la detección de 1-3 tablas
        import random

        num_tables = random.randint(1, 3)

        tables = []
        for i in range(num_tables):
            # Generar una tabla simulada
            num_rows = random.randint(3, 8)
            num_cols = random.randint(2, 5)

            # Crear datos simulados
            headers = [f"Columna {j+1}" for j in range(num_cols)]
            rows = []
            for r in range(num_rows):
                row = [f"Dato {r+1},{j+1}" for j in range(num_cols)]
                rows.append(row)

            # Crear DataFrame
            df = pd.DataFrame(rows, columns=headers)

            # Convertir a formato JSON
            table_data = {
                "table_id": f"table_{i+1}",
                "position": {
                    "x": random.randint(0, img.width - 200),
                    "y": random.randint(0, img.height - 200),
                    "width": random.randint(200, min(500, img.width)),
                    "height": random.randint(100, min(300, img.height)),
                },
                "headers": headers,
                "rows": rows,
                "confidence": round(random.uniform(0.7, 0.98), 2),
            }

            tables.append(table_data)

        return tables

    async def _detect_and_extract_form_fields(
        self, image_bytes: bytes, language_code: str
    ) -> List[Dict[str, Any]]:
        """
        Detecta y extrae campos de formularios de una imagen.

        Args:
            image_bytes: Bytes de la imagen
            language_code: Código de idioma para el OCR

        Returns:
            List[Dict[str, Any]]: Lista de campos de formulario extraídos
        """
        # Implementación simulada para este ejemplo
        # En una implementación real, se utilizaría un modelo de ML para detectar campos de formulario

        # Abrir la imagen con PIL
        img = Image.open(io.BytesIO(image_bytes))

        # Simulación de detección de campos de formulario
        # En una implementación real, aquí se utilizaría un modelo de visión por computadora

        # Simulamos la detección de 5-10 campos de formulario
        import random

        num_fields = random.randint(5, 10)

        # Posibles tipos de campos
        field_types = ["text", "checkbox", "radio", "signature", "date"]

        # Posibles etiquetas de campos
        field_labels = [
            "Nombre",
            "Apellido",
            "Dirección",
            "Ciudad",
            "Código Postal",
            "Teléfono",
            "Email",
            "Fecha de Nacimiento",
            "Género",
            "Estado Civil",
            "Ocupación",
            "Empresa",
            "Cargo",
            "Ingresos",
            "Acepto términos",
        ]

        form_fields = []
        used_labels = set()

        for i in range(num_fields):
            # Seleccionar etiqueta no utilizada
            available_labels = [l for l in field_labels if l not in used_labels]
            if not available_labels:
                break

            label = random.choice(available_labels)
            used_labels.add(label)

            # Seleccionar tipo de campo
            field_type = random.choice(field_types)

            # Generar valor según el tipo
            if field_type == "checkbox":
                value = random.choice([True, False])
            elif field_type == "radio":
                value = random.choice(["Opción 1", "Opción 2", "Opción 3"])
            elif field_type == "date":
                value = f"{random.randint(1, 28)}/{random.randint(1, 12)}/{random.randint(1980, 2023)}"
            elif field_type == "signature":
                value = "[Firma]"
            else:
                value = f"Valor de ejemplo para {label}"

            # Crear campo
            field = {
                "field_id": f"field_{i+1}",
                "label": label,
                "type": field_type,
                "value": value,
                "position": {
                    "x": random.randint(0, img.width - 100),
                    "y": random.randint(0, img.height - 50),
                    "width": random.randint(100, 300),
                    "height": random.randint(30, 80),
                },
                "confidence": round(random.uniform(0.75, 0.99), 2),
            }

            form_fields.append(field)

        return form_fields

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del procesador de documentos.

        Returns:
            Dict[str, Any]: Estadísticas del procesador
        """
        async with self.lock:
            avg_processing_time = (
                self.stats["processing_time_ms"] / self.stats["documents_processed"]
                if self.stats["documents_processed"] > 0
                else 0
            )

            return {**self.stats, "avg_processing_time_ms": avg_processing_time}


# Instancia global del procesador de documentos
document_processor = DocumentProcessor()

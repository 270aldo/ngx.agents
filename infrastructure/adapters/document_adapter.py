"""
Adaptador para integrar capacidades de procesamiento de documentos en los agentes.

Este módulo proporciona un adaptador que permite a los agentes utilizar
las capacidades de procesamiento de documentos estructurados y reconocimiento
de objetos específicos.
"""

import asyncio
from typing import Any, Dict, List, Union

from core.logging_config import get_logger
from infrastructure.adapters.telemetry_adapter import (
    get_telemetry_adapter,
    measure_execution_time,
)
from core.document_processor import document_processor
from core.object_recognition import object_recognition
from core.vision_metrics import vision_metrics

# Configurar logger
logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()


class DocumentAdapter:
    """
    Adaptador para integrar capacidades de procesamiento de documentos en los agentes.

    Proporciona métodos para extraer tablas, formularios y reconocer objetos específicos
    en imágenes y documentos.
    """

    def __init__(self):
        """Inicializa el adaptador de procesamiento de documentos."""
        self._initialized = False
        self.is_initialized = False

        # Lock para inicialización
        self._init_lock = asyncio.Lock()

        # Estadísticas
        self.stats = {
            "extract_tables_calls": 0,
            "extract_forms_calls": 0,
            "recognize_objects_calls": 0,
            "errors": {},
        }

    @measure_execution_time("document_adapter.initialize")
    async def initialize(self) -> bool:
        """
        Inicializa el adaptador de procesamiento de documentos.

        Returns:
            bool: True si la inicialización fue exitosa
        """
        async with self._init_lock:
            if self._initialized:
                return True

            span = telemetry_adapter.start_span("DocumentAdapter.initialize")
            try:
                telemetry_adapter.add_span_event(span, "initialization_start")

                # No hay inicialización específica necesaria ya que los
                # procesadores subyacentes se inicializan automáticamente

                self._initialized = True
                self.is_initialized = True

                telemetry_adapter.set_span_attribute(
                    span, "initialization_status", "success"
                )
                telemetry_adapter.record_metric(
                    "document_adapter.initializations", 1, {"status": "success"}
                )
                logger.info("DocumentAdapter inicializado.")
                return True
            except Exception as e:
                telemetry_adapter.record_exception(span, e)
                telemetry_adapter.set_span_attribute(
                    span, "initialization_status", "failure"
                )
                telemetry_adapter.record_metric(
                    "document_adapter.initializations", 1, {"status": "failure"}
                )
                logger.error(
                    f"Error durante la inicialización del adaptador de documentos: {e}"
                )
                return False
            finally:
                telemetry_adapter.end_span(span)

    async def _ensure_initialized(self) -> None:
        """Asegura que el adaptador esté inicializado."""
        if not self._initialized:
            await self.initialize()

    @measure_execution_time("document_adapter.extract_tables")
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
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "DocumentAdapter.extract_tables",
            {"agent_id": agent_id, "language_code": language_code},
        )

        start_time = asyncio.get_event_loop().time()

        try:
            # Incrementar contador
            self.stats["extract_tables_calls"] += 1

            # Llamar al procesador de documentos
            result = await document_processor.extract_tables(
                image_data=image_data, language_code=language_code, agent_id=agent_id
            )

            # Registrar métricas de éxito
            telemetry_adapter.set_span_attribute(
                span, "table_count", len(result.get("tables", []))
            )
            telemetry_adapter.set_span_attribute(span, "status", "success")
            telemetry_adapter.record_metric(
                "document_adapter.extract_tables.success", 1
            )

            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "document_adapter.errors",
                1,
                {"operation": "extract_tables", "error_type": error_type},
            )

            logger.error(f"Error en DocumentAdapter.extract_tables: {str(e)}")

            # Calcular latencia incluso en caso de error
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Registrar métricas de error
            await vision_metrics.record_api_call(
                operation="extract_tables",
                agent_id=agent_id,
                success=False,
                latency_ms=latency_ms,
                error_type=error_type,
            )

            return {"error": str(e), "tables": [], "status": "error"}

        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("document_adapter.extract_forms")
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
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "DocumentAdapter.extract_forms",
            {"agent_id": agent_id, "language_code": language_code},
        )

        start_time = asyncio.get_event_loop().time()

        try:
            # Incrementar contador
            self.stats["extract_forms_calls"] += 1

            # Llamar al procesador de documentos
            result = await document_processor.extract_forms(
                image_data=image_data, language_code=language_code, agent_id=agent_id
            )

            # Registrar métricas de éxito
            telemetry_adapter.set_span_attribute(
                span, "field_count", len(result.get("form_fields", []))
            )
            telemetry_adapter.set_span_attribute(span, "status", "success")
            telemetry_adapter.record_metric("document_adapter.extract_forms.success", 1)

            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "document_adapter.errors",
                1,
                {"operation": "extract_forms", "error_type": error_type},
            )

            logger.error(f"Error en DocumentAdapter.extract_forms: {str(e)}")

            # Calcular latencia incluso en caso de error
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Registrar métricas de error
            await vision_metrics.record_api_call(
                operation="extract_forms",
                agent_id=agent_id,
                success=False,
                latency_ms=latency_ms,
                error_type=error_type,
            )

            return {"error": str(e), "form_fields": [], "status": "error"}

        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("document_adapter.recognize_objects")
    async def recognize_objects(
        self,
        image_data: Union[str, bytes, Dict[str, Any]],
        domain: str = "general",
        confidence_threshold: float = 0.5,
        agent_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Reconoce objetos en una imagen para un dominio específico.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            domain: Dominio de objetos a reconocer (general, medical, industrial, retail, custom)
            confidence_threshold: Umbral de confianza para incluir detecciones (0.0-1.0)
            agent_id: ID del agente que realiza la solicitud (para métricas)

        Returns:
            Dict[str, Any]: Objetos reconocidos y metadatos
        """
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "DocumentAdapter.recognize_objects",
            {
                "agent_id": agent_id,
                "domain": domain,
                "confidence_threshold": confidence_threshold,
            },
        )

        start_time = asyncio.get_event_loop().time()

        try:
            # Incrementar contador
            self.stats["recognize_objects_calls"] += 1

            # Llamar al sistema de reconocimiento de objetos
            result = await object_recognition.recognize_objects(
                image_data=image_data,
                domain=domain,
                confidence_threshold=confidence_threshold,
                agent_id=agent_id,
            )

            # Registrar métricas de éxito
            telemetry_adapter.set_span_attribute(
                span, "object_count", len(result.get("detections", []))
            )
            telemetry_adapter.set_span_attribute(span, "status", "success")
            telemetry_adapter.record_metric(
                "document_adapter.recognize_objects.success", 1
            )

            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "document_adapter.errors",
                1,
                {"operation": "recognize_objects", "error_type": error_type},
            )

            logger.error(f"Error en DocumentAdapter.recognize_objects: {str(e)}")

            # Calcular latencia incluso en caso de error
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Registrar métricas de error
            await vision_metrics.record_api_call(
                operation="recognize_objects",
                agent_id=agent_id,
                success=False,
                latency_ms=latency_ms,
                error_type=error_type,
            )

            return {"error": str(e), "detections": [], "status": "error"}

        finally:
            telemetry_adapter.end_span(span)

    async def register_custom_domain(
        self,
        domain_name: str,
        objects: List[str],
        description: str = "",
        agent_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Registra un dominio personalizado con objetos específicos.

        Args:
            domain_name: Nombre del dominio personalizado
            objects: Lista de objetos a reconocer en este dominio
            description: Descripción del dominio
            agent_id: ID del agente que realiza la solicitud (para métricas)

        Returns:
            Dict[str, Any]: Información del dominio registrado
        """
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "DocumentAdapter.register_custom_domain",
            {
                "agent_id": agent_id,
                "domain_name": domain_name,
                "object_count": len(objects),
            },
        )

        try:
            # Llamar al sistema de reconocimiento de objetos
            result = await object_recognition.register_custom_domain(
                domain_name=domain_name,
                objects=objects,
                description=description,
                agent_id=agent_id,
            )

            # Registrar métricas de éxito
            telemetry_adapter.set_span_attribute(span, "status", "success")
            telemetry_adapter.record_metric(
                "document_adapter.register_custom_domain.success", 1
            )

            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "document_adapter.errors",
                1,
                {"operation": "register_custom_domain", "error_type": error_type},
            )

            logger.error(f"Error en DocumentAdapter.register_custom_domain: {str(e)}")

            return {"error": str(e), "status": "error"}

        finally:
            telemetry_adapter.end_span(span)

    async def get_available_domains(self) -> Dict[str, Any]:
        """
        Obtiene la lista de dominios disponibles para reconocimiento de objetos.

        Returns:
            Dict[str, Any]: Información de dominios disponibles
        """
        await self._ensure_initialized()

        try:
            return await object_recognition.get_available_domains()
        except Exception as e:
            logger.error(f"Error al obtener dominios disponibles: {e}")
            return {"error": str(e), "domains": {}, "count": 0}

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del adaptador de documentos.

        Returns:
            Dict[str, Any]: Estadísticas del adaptador
        """
        # Obtener estadísticas de los componentes subyacentes
        doc_processor_stats = await document_processor.get_stats()
        object_recognition_stats = await object_recognition.get_stats()

        return {
            **self.stats,
            "document_processor_stats": doc_processor_stats,
            "object_recognition_stats": object_recognition_stats,
            "initialized": self.is_initialized,
        }


# Instancia global del adaptador
document_adapter = DocumentAdapter()

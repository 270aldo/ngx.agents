"""
Adaptador para integrar capacidades de visión en los agentes.

Este módulo proporciona un adaptador que permite a los agentes utilizar
las capacidades de visión de Vertex AI para análisis de imágenes,
reconocimiento de objetos, personas y texto, y generación de descripciones.
"""

import asyncio
import os
from typing import Any, Dict, Optional, Union

from core.logging_config import get_logger
from infrastructure.adapters.telemetry_adapter import (
    get_telemetry_adapter,
    measure_execution_time,
)
from clients.vertex_ai.vision_client import vision_client

# Configurar logger
logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()


class VisionAdapter:
    """
    Adaptador para integrar capacidades de visión en los agentes.

    Proporciona métodos para análisis de imágenes, reconocimiento de objetos,
    personas y texto, y generación de descripciones detalladas.
    """

    def __init__(self):
        """Inicializa el adaptador de visión."""
        self._initialized = False
        self.is_initialized = False

        # Lock para inicialización
        self._init_lock = asyncio.Lock()

        # Estadísticas
        self.stats = {
            "analyze_image_calls": 0,
            "detect_objects_calls": 0,
            "detect_text_calls": 0,
            "detect_faces_calls": 0,
            "generate_description_calls": 0,
            "errors": {},
        }

    @measure_execution_time("vision_adapter.initialize")
    async def initialize(self) -> bool:
        """
        Inicializa el adaptador de visión.

        Returns:
            bool: True si la inicialización fue exitosa
        """
        async with self._init_lock:
            if self._initialized:
                return True

            span = telemetry_adapter.start_span("VisionAdapter.initialize")
            try:
                telemetry_adapter.add_span_event(span, "initialization_start")

                # Inicializar cliente de visión
                await vision_client.initialize()

                self._initialized = True
                self.is_initialized = True

                telemetry_adapter.set_span_attribute(
                    span, "initialization_status", "success"
                )
                telemetry_adapter.record_metric(
                    "vision_adapter.initializations", 1, {"status": "success"}
                )
                logger.info("VisionAdapter inicializado.")
                return True
            except Exception as e:
                telemetry_adapter.record_exception(span, e)
                telemetry_adapter.set_span_attribute(
                    span, "initialization_status", "failure"
                )
                telemetry_adapter.record_metric(
                    "vision_adapter.initializations", 1, {"status": "failure"}
                )
                logger.error(
                    f"Error durante la inicialización del adaptador de visión: {e}"
                )
                return False
            finally:
                telemetry_adapter.end_span(span)

    async def _ensure_initialized(self) -> None:
        """Asegura que el adaptador esté inicializado."""
        if not self._initialized:
            await self.initialize()

    @measure_execution_time("vision_adapter.analyze_image")
    async def analyze_image(
        self,
        image_data: Union[str, bytes, Dict[str, Any]],
        analysis_type: str = "full",
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Analiza una imagen y extrae información.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            analysis_type: Tipo de análisis ('full', 'labels', 'objects', 'text', 'faces', 'landmarks')
            max_results: Número máximo de resultados a devolver

        Returns:
            Dict[str, Any]: Resultados del análisis
        """
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "VisionAdapter.analyze_image",
            {
                "adapter.analysis_type": analysis_type,
                "adapter.max_results": max_results,
            },
        )

        try:
            telemetry_adapter.add_span_event(span, "analysis.start")
            self.stats["analyze_image_calls"] += 1

            # Procesar entrada de imagen
            processed_image = await self._process_image_input(image_data)

            # Llamar al cliente de visión
            result = await vision_client.analyze_image(
                image_data=processed_image,
                analysis_type=analysis_type,
                max_results=max_results,
            )

            telemetry_adapter.record_metric(
                "vision_adapter.calls", 1, {"operation": "analyze_image"}
            )
            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "vision_adapter.errors",
                1,
                {"operation": "analyze_image", "error_type": error_type},
            )

            logger.error(f"Error en VisionAdapter.analyze_image: {str(e)}")

            return {
                "error": str(e),
                "analysis_type": analysis_type,
                "labels": [],
                "objects": [],
                "text": "",
                "faces": [],
                "landmarks": [],
                "safe_search": {},
                "properties": {},
            }

        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("vision_adapter.detect_objects")
    async def detect_objects(
        self, image_data: Union[str, bytes, Dict[str, Any]], max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Detecta objetos en una imagen.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            max_results: Número máximo de resultados a devolver

        Returns:
            Dict[str, Any]: Objetos detectados
        """
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "VisionAdapter.detect_objects", {"adapter.max_results": max_results}
        )

        try:
            telemetry_adapter.add_span_event(span, "detection.start")
            self.stats["detect_objects_calls"] += 1

            # Procesar entrada de imagen
            processed_image = await self._process_image_input(image_data)

            # Llamar al cliente de visión
            result = await vision_client.detect_objects(
                image_data=processed_image, max_results=max_results
            )

            telemetry_adapter.record_metric(
                "vision_adapter.calls", 1, {"operation": "detect_objects"}
            )
            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "vision_adapter.errors",
                1,
                {"operation": "detect_objects", "error_type": error_type},
            )

            logger.error(f"Error en VisionAdapter.detect_objects: {str(e)}")

            return {"error": str(e), "analysis_type": "objects", "objects": []}

        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("vision_adapter.detect_text")
    async def detect_text(
        self, image_data: Union[str, bytes, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detecta texto en una imagen.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)

        Returns:
            Dict[str, Any]: Texto detectado
        """
        await self._ensure_initialized()

        span = telemetry_adapter.start_span("VisionAdapter.detect_text")

        try:
            telemetry_adapter.add_span_event(span, "detection.start")
            self.stats["detect_text_calls"] += 1

            # Procesar entrada de imagen
            processed_image = await self._process_image_input(image_data)

            # Llamar al cliente de visión
            result = await vision_client.detect_text(image_data=processed_image)

            telemetry_adapter.record_metric(
                "vision_adapter.calls", 1, {"operation": "detect_text"}
            )
            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "vision_adapter.errors",
                1,
                {"operation": "detect_text", "error_type": error_type},
            )

            logger.error(f"Error en VisionAdapter.detect_text: {str(e)}")

            return {"error": str(e), "analysis_type": "text", "text": ""}

        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("vision_adapter.detect_faces")
    async def detect_faces(
        self, image_data: Union[str, bytes, Dict[str, Any]], max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Detecta caras en una imagen.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            max_results: Número máximo de resultados a devolver

        Returns:
            Dict[str, Any]: Caras detectadas
        """
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "VisionAdapter.detect_faces", {"adapter.max_results": max_results}
        )

        try:
            telemetry_adapter.add_span_event(span, "detection.start")
            self.stats["detect_faces_calls"] += 1

            # Procesar entrada de imagen
            processed_image = await self._process_image_input(image_data)

            # Llamar al cliente de visión
            result = await vision_client.detect_faces(
                image_data=processed_image, max_results=max_results
            )

            telemetry_adapter.record_metric(
                "vision_adapter.calls", 1, {"operation": "detect_faces"}
            )
            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "vision_adapter.errors",
                1,
                {"operation": "detect_faces", "error_type": error_type},
            )

            logger.error(f"Error en VisionAdapter.detect_faces: {str(e)}")

            return {"error": str(e), "analysis_type": "faces", "faces": []}

        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("vision_adapter.generate_description")
    async def generate_description(
        self,
        image_data: Union[str, bytes, Dict[str, Any]],
        prompt: str = "Describe detalladamente esta imagen",
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = 1024,
    ) -> Dict[str, Any]:
        """
        Genera una descripción detallada de una imagen.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)
            prompt: Prompt para guiar la descripción
            temperature: Temperatura para la generación
            max_output_tokens: Máximo de tokens a generar

        Returns:
            Dict[str, Any]: Descripción generada
        """
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "VisionAdapter.generate_description",
            {"adapter.prompt_length": len(prompt), "adapter.temperature": temperature},
        )

        try:
            telemetry_adapter.add_span_event(span, "description.start")
            self.stats["generate_description_calls"] += 1

            # Procesar entrada de imagen
            processed_image = await self._process_image_input(image_data)

            # Llamar al cliente de visión
            result = await vision_client.generate_description(
                image_data=processed_image,
                prompt=prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )

            telemetry_adapter.record_metric(
                "vision_adapter.calls", 1, {"operation": "generate_description"}
            )
            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "vision_adapter.errors",
                1,
                {"operation": "generate_description", "error_type": error_type},
            )

            logger.error(f"Error en VisionAdapter.generate_description: {str(e)}")

            return {
                "error": str(e),
                "text": f"Error: {str(e)}",
                "finish_reason": "ERROR",
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            }

        finally:
            telemetry_adapter.end_span(span)

    async def _process_image_input(
        self, image_data: Union[str, bytes, Dict[str, Any]]
    ) -> Union[str, bytes]:
        """
        Procesa la entrada de imagen en diferentes formatos.

        Args:
            image_data: Datos de la imagen (base64, bytes o dict con url o path)

        Returns:
            Union[str, bytes]: Datos de imagen procesados
        """
        # Si ya es bytes o base64, devolver directamente
        if isinstance(image_data, bytes) or (
            isinstance(image_data, str) and "base64" in image_data
        ):
            return image_data

        # Si es un diccionario, procesar según las claves
        if isinstance(image_data, dict):
            # Si tiene URL, descargar la imagen
            if "url" in image_data:
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    async with session.get(image_data["url"]) as response:
                        if response.status == 200:
                            return await response.read()
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
                    return f.read()

            # Si tiene base64, extraer
            elif "base64" in image_data:
                return image_data["base64"]

            else:
                raise ValueError(
                    "Formato de imagen no válido. Debe contener 'url', 'path' o 'base64'."
                )

        # Si es una cadena que no es base64, asumir que es una ruta de archivo
        if isinstance(image_data, str):
            if not os.path.exists(image_data):
                raise FileNotFoundError(
                    f"No se encontró el archivo de imagen: {image_data}"
                )

            with open(image_data, "rb") as f:
                return f.read()

        raise ValueError("Formato de imagen no soportado.")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del adaptador.

        Returns:
            Dict[str, Any]: Estadísticas del adaptador
        """
        # Obtener estadísticas del cliente
        client_stats = await vision_client.get_stats()

        return {
            **self.stats,
            "client_stats": client_stats,
            "initialized": self.is_initialized,
        }


# Instancia global del adaptador
vision_adapter = VisionAdapter()

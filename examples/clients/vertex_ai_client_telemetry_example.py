from core.logging_config import get_logger

"""
Ejemplo de integración del adaptador de telemetría con el cliente Vertex AI optimizado.

Este módulo muestra cómo integrar el adaptador de telemetría en el cliente
Vertex AI optimizado para proporcionar observabilidad sin depender directamente
de OpenTelemetry.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List

# Importar el adaptador de telemetría
from core.telemetry_adapter import (
    start_span,
    end_span,
    set_span_attribute,
    add_span_event,
    record_exception,
    record_metric,
    measure_execution_time,
)

logger = get_logger(__name__)


class VertexAIClientWithTelemetry:
    """
    Cliente Vertex AI optimizado con telemetría integrada.

    Esta clase es un ejemplo de cómo integrar el adaptador de telemetría
    en el cliente Vertex AI optimizado.
    """

    def __init__(self):
        """Inicializa el cliente."""
        self._initialized = False
        self.is_initialized = False
        self.stats = {
            "content_requests": 0,
            "embedding_requests": 0,
            "multimodal_requests": 0,
            "latency_ms": {},
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
        }

    @measure_execution_time("vertex_ai.initialize")
    async def initialize(self) -> bool:
        """
        Inicializa el cliente.

        Returns:
            bool: True si la inicialización fue exitosa
        """
        if self._initialized:
            return True

        # Simular inicialización
        await asyncio.sleep(0.5)

        self._initialized = True
        self.is_initialized = True

        # Registrar evento de inicialización
        add_span_event(
            None, "vertex_ai.initialized", {"success": True, "timestamp": time.time()}
        )

        return True

    async def _ensure_initialized(self) -> None:
        """Asegura que el cliente esté inicializado."""
        if not self._initialized:
            await self.initialize()

    @measure_execution_time("vertex_ai.generate_content")
    async def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Genera contenido de texto.

        Args:
            prompt: Texto de entrada
            system_instruction: Instrucción del sistema
            temperature: Temperatura para la generación
            max_output_tokens: Máximo de tokens de salida
            top_p: Parámetro top_p
            top_k: Parámetro top_k

        Returns:
            Dict[str, Any]: Respuesta generada
        """
        # Asegurar inicialización
        await self._ensure_initialized()

        # Crear span para la operación
        span = start_span(
            "vertex_ai.content_generation",
            {
                "prompt_length": len(prompt),
                "temperature": temperature,
                "has_system_instruction": system_instruction is not None,
            },
        )

        try:
            # Registrar inicio de la operación
            add_span_event(span, "generation.start")

            # Simular generación
            start_time = time.time()
            await asyncio.sleep(0.5)  # Simular latencia
            end_time = time.time()

            # Simular respuesta
            response = {
                "text": "Respuesta generada para: " + prompt[:20] + "...",
                "finish_reason": "STOP",
                "usage": {
                    "prompt_tokens": len(prompt) // 4,
                    "completion_tokens": 50,
                    "total_tokens": (len(prompt) // 4) + 50,
                },
            }

            # Actualizar estadísticas
            self.stats["content_requests"] += 1
            self.stats["tokens"]["prompt"] += response["usage"]["prompt_tokens"]
            self.stats["tokens"]["completion"] += response["usage"]["completion_tokens"]
            self.stats["tokens"]["total"] += response["usage"]["total_tokens"]

            # Registrar latencia
            latency_ms = (end_time - start_time) * 1000
            if "content" not in self.stats["latency_ms"]:
                self.stats["latency_ms"]["content"] = []

            latencies = self.stats["latency_ms"]["content"]
            latencies.append(latency_ms)
            if len(latencies) > 100:
                latencies.pop(0)

            # Registrar métricas
            record_metric("vertex_ai.content_requests", 1)
            record_metric("vertex_ai.tokens.prompt", response["usage"]["prompt_tokens"])
            record_metric(
                "vertex_ai.tokens.completion", response["usage"]["completion_tokens"]
            )
            record_metric("vertex_ai.tokens.total", response["usage"]["total_tokens"])
            record_metric("vertex_ai.latency_ms.content", latency_ms)

            # Registrar atributos en el span
            set_span_attribute(span, "finish_reason", response["finish_reason"])
            set_span_attribute(
                span, "prompt_tokens", response["usage"]["prompt_tokens"]
            )
            set_span_attribute(
                span, "completion_tokens", response["usage"]["completion_tokens"]
            )
            set_span_attribute(span, "total_tokens", response["usage"]["total_tokens"])
            set_span_attribute(span, "latency_ms", latency_ms)

            # Registrar finalización
            add_span_event(
                span,
                "generation.complete",
                {
                    "finish_reason": response["finish_reason"],
                    "total_tokens": response["usage"]["total_tokens"],
                },
            )

            return response
        except Exception as e:
            # Registrar excepción
            record_exception(span, e)

            # Actualizar estadísticas
            if "errors" not in self.stats:
                self.stats["errors"] = {}
            if "content" not in self.stats["errors"]:
                self.stats["errors"]["content"] = 0
            self.stats["errors"]["content"] += 1

            # Registrar métrica de error
            record_metric("vertex_ai.errors.content", 1)

            raise
        finally:
            # Finalizar span
            end_span(span)

    @measure_execution_time("vertex_ai.generate_embedding")
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Genera un embedding para un texto.

        Args:
            text: Texto para generar embedding

        Returns:
            List[float]: Vector de embedding
        """
        # Asegurar inicialización
        await self._ensure_initialized()

        # Crear span para la operación
        span = start_span("vertex_ai.embedding_generation", {"text_length": len(text)})

        try:
            # Registrar inicio de la operación
            add_span_event(span, "embedding.start")

            # Simular generación
            start_time = time.time()
            await asyncio.sleep(0.2)  # Simular latencia
            end_time = time.time()

            # Simular embedding (vector de 3 dimensiones para simplificar)
            embedding = [0.1, 0.2, 0.3]

            # Actualizar estadísticas
            self.stats["embedding_requests"] += 1

            # Registrar latencia
            latency_ms = (end_time - start_time) * 1000
            if "embedding" not in self.stats["latency_ms"]:
                self.stats["latency_ms"]["embedding"] = []

            latencies = self.stats["latency_ms"]["embedding"]
            latencies.append(latency_ms)
            if len(latencies) > 100:
                latencies.pop(0)

            # Registrar métricas
            record_metric("vertex_ai.embedding_requests", 1)
            record_metric("vertex_ai.latency_ms.embedding", latency_ms)

            # Registrar atributos en el span
            set_span_attribute(span, "embedding_dimensions", len(embedding))
            set_span_attribute(span, "latency_ms", latency_ms)

            # Registrar finalización
            add_span_event(span, "embedding.complete", {"dimensions": len(embedding)})

            return embedding
        except Exception as e:
            # Registrar excepción
            record_exception(span, e)

            # Actualizar estadísticas
            if "errors" not in self.stats:
                self.stats["errors"] = {}
            if "embedding" not in self.stats["errors"]:
                self.stats["errors"]["embedding"] = 0
            self.stats["errors"]["embedding"] += 1

            # Registrar métrica de error
            record_metric("vertex_ai.errors.embedding", 1)

            raise
        finally:
            # Finalizar span
            end_span(span)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cliente.

        Returns:
            Dict[str, Any]: Estadísticas del cliente
        """
        # Calcular promedios de latencia
        for operation, latencies in self.stats["latency_ms"].items():
            if latencies:
                self.stats[f"latency_avg_ms_{operation}"] = sum(latencies) / len(
                    latencies
                )

        return self.stats


# Crear instancia del cliente
vertex_ai_client_with_telemetry = VertexAIClientWithTelemetry()


# Ejemplo de uso
async def example_usage():
    """Ejemplo de uso del cliente con telemetría."""
    # Inicializar cliente
    await vertex_ai_client_with_telemetry.initialize()

    # Generar contenido
    response = await vertex_ai_client_with_telemetry.generate_content(
        prompt="Explica la inteligencia artificial en términos simples", temperature=0.7
    )
    logger.info(f"Respuesta: {response['text']}")
    logger.info(f"Tokens: {response['usage']['total_tokens']}")

    # Generar embedding
    embedding = await vertex_ai_client_with_telemetry.generate_embedding(
        text="Ejemplo de texto para embedding"
    )
    logger.info(f"Embedding: {embedding}")

    # Obtener estadísticas
    stats = await vertex_ai_client_with_telemetry.get_stats()
    logger.info(f"Estadísticas: {stats}")


if __name__ == "__main__":
    asyncio.run(example_usage())

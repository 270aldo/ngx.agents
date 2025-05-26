"""
Adaptador para integrar capacidades de procesamiento de voz en los agentes.

Este módulo proporciona un adaptador que permite a los agentes utilizar
las capacidades de procesamiento de voz de Vertex AI para transcripción,
síntesis y análisis de audio.
"""

import asyncio
import os
from typing import Any, Dict, Union

from core.logging_config import get_logger
from infrastructure.adapters.telemetry_adapter import (
    get_telemetry_adapter,
    measure_execution_time,
)
from clients.vertex_ai.speech_client import speech_client
from core.vision_metrics import vision_metrics

# Configurar logger
logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()


class SpeechAdapter:
    """
    Adaptador para integrar capacidades de procesamiento de voz en los agentes.

    Proporciona métodos para transcripción de audio, síntesis de voz y análisis
    de características de audio como emociones e intenciones.
    """

    def __init__(self):
        """Inicializa el adaptador de procesamiento de voz."""
        self._initialized = False
        self.is_initialized = False

        # Lock para inicialización
        self._init_lock = asyncio.Lock()

        # Estadísticas
        self.stats = {
            "transcribe_calls": 0,
            "synthesize_calls": 0,
            "analyze_calls": 0,
            "errors": {},
        }

    @measure_execution_time("speech_adapter.initialize")
    async def initialize(self) -> bool:
        """
        Inicializa el adaptador de procesamiento de voz.

        Returns:
            bool: True si la inicialización fue exitosa
        """
        async with self._init_lock:
            if self._initialized:
                return True

            span = telemetry_adapter.start_span("SpeechAdapter.initialize")
            try:
                telemetry_adapter.add_span_event(span, "initialization_start")

                # Inicializar cliente de voz
                # Asumimos que el cliente ya tiene su propio método de inicialización
                # o se inicializa en el constructor

                self._initialized = True
                self.is_initialized = True

                telemetry_adapter.set_span_attribute(
                    span, "initialization_status", "success"
                )
                telemetry_adapter.record_metric(
                    "speech_adapter.initializations", 1, {"status": "success"}
                )
                logger.info("SpeechAdapter inicializado.")
                return True
            except Exception as e:
                telemetry_adapter.record_exception(span, e)
                telemetry_adapter.set_span_attribute(
                    span, "initialization_status", "failure"
                )
                telemetry_adapter.record_metric(
                    "speech_adapter.initializations", 1, {"status": "failure"}
                )
                logger.error(
                    f"Error durante la inicialización del adaptador de voz: {e}"
                )
                return False
            finally:
                telemetry_adapter.end_span(span)

    async def _ensure_initialized(self) -> None:
        """Asegura que el adaptador esté inicializado."""
        if not self._initialized:
            await self.initialize()

    @measure_execution_time("speech_adapter.transcribe_audio")
    async def transcribe_audio(
        self,
        audio_data: Union[str, bytes, Dict[str, Any]],
        language_code: str = "es-ES",
        agent_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Transcribe audio a texto.

        Args:
            audio_data: Datos del audio (base64, bytes o dict con url o path)
            language_code: Código de idioma para la transcripción
            agent_id: ID del agente que realiza la solicitud (para métricas)

        Returns:
            Dict[str, Any]: Resultados de la transcripción
        """
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "SpeechAdapter.transcribe_audio",
            {"adapter.language_code": language_code, "adapter.agent_id": agent_id},
        )

        start_time = asyncio.get_event_loop().time()

        try:
            # Procesar la entrada de audio
            processed_audio = await self._process_audio_input(audio_data)

            # Llamar al cliente de voz
            result = await speech_client.transcribe_audio(
                processed_audio, language_code
            )

            # Actualizar estadísticas
            self.stats["transcribe_calls"] += 1

            # Calcular latencia
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Registrar métricas
            await vision_metrics.record_api_call(
                operation="transcribe_audio",
                agent_id=agent_id,
                success=result.get("status") == "success",
                latency_ms=latency_ms,
                error_type=(
                    result.get("error") if result.get("status") == "error" else None
                ),
            )

            telemetry_adapter.record_metric(
                "speech_adapter.calls", 1, {"operation": "transcribe_audio"}
            )
            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "speech_adapter.errors",
                1,
                {"operation": "transcribe_audio", "error_type": error_type},
            )

            logger.error(f"Error en SpeechAdapter.transcribe_audio: {str(e)}")

            # Calcular latencia incluso en caso de error
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Registrar métricas de error
            await vision_metrics.record_api_call(
                operation="transcribe_audio",
                agent_id=agent_id,
                success=False,
                latency_ms=latency_ms,
                error_type=error_type,
            )

            return {"error": str(e), "text": f"Error: {str(e)}", "status": "error"}

        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("speech_adapter.synthesize_speech")
    async def synthesize_speech(
        self,
        text: str,
        voice_name: str = "es-ES-Standard-A",
        language_code: str = "es-ES",
        agent_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Sintetiza texto a voz.

        Args:
            text: Texto a sintetizar
            voice_name: Nombre de la voz a utilizar
            language_code: Código de idioma para la síntesis
            agent_id: ID del agente que realiza la solicitud (para métricas)

        Returns:
            Dict[str, Any]: Resultados de la síntesis, incluyendo audio en base64
        """
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "SpeechAdapter.synthesize_speech",
            {
                "adapter.voice_name": voice_name,
                "adapter.language_code": language_code,
                "adapter.text_length": len(text),
                "adapter.agent_id": agent_id,
            },
        )

        start_time = asyncio.get_event_loop().time()

        try:
            # Llamar al cliente de voz
            result = await speech_client.synthesize_speech(
                text, voice_name, language_code
            )

            # Actualizar estadísticas
            self.stats["synthesize_calls"] += 1

            # Calcular latencia
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Registrar métricas
            await vision_metrics.record_api_call(
                operation="synthesize_speech",
                agent_id=agent_id,
                success=result.get("status") == "success",
                latency_ms=latency_ms,
                error_type=(
                    result.get("error") if result.get("status") == "error" else None
                ),
            )

            telemetry_adapter.record_metric(
                "speech_adapter.calls", 1, {"operation": "synthesize_speech"}
            )
            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "speech_adapter.errors",
                1,
                {"operation": "synthesize_speech", "error_type": error_type},
            )

            logger.error(f"Error en SpeechAdapter.synthesize_speech: {str(e)}")

            # Calcular latencia incluso en caso de error
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Registrar métricas de error
            await vision_metrics.record_api_call(
                operation="synthesize_speech",
                agent_id=agent_id,
                success=False,
                latency_ms=latency_ms,
                error_type=error_type,
            )

            return {"error": str(e), "status": "error"}

        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("speech_adapter.analyze_audio")
    async def analyze_audio(
        self,
        audio_data: Union[str, bytes, Dict[str, Any]],
        analysis_type: str = "emotion",
        language_code: str = "es-ES",
        agent_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Analiza audio para detectar emociones, intenciones u otras características.

        Args:
            audio_data: Datos del audio (base64, bytes o dict con url o path)
            analysis_type: Tipo de análisis (emotion, intent, speaker_diarization)
            language_code: Código de idioma para el análisis
            agent_id: ID del agente que realiza la solicitud (para métricas)

        Returns:
            Dict[str, Any]: Resultados del análisis
        """
        await self._ensure_initialized()

        span = telemetry_adapter.start_span(
            "SpeechAdapter.analyze_audio",
            {
                "adapter.analysis_type": analysis_type,
                "adapter.language_code": language_code,
                "adapter.agent_id": agent_id,
            },
        )

        start_time = asyncio.get_event_loop().time()

        try:
            # Procesar la entrada de audio
            processed_audio = await self._process_audio_input(audio_data)

            # Llamar al cliente de voz
            result = await speech_client.analyze_audio(
                processed_audio, analysis_type, language_code
            )

            # Actualizar estadísticas
            self.stats["analyze_calls"] += 1

            # Calcular latencia
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Registrar métricas
            await vision_metrics.record_api_call(
                operation="analyze_audio",
                agent_id=agent_id,
                success=result.get("status") == "success",
                latency_ms=latency_ms,
                error_type=(
                    result.get("error") if result.get("status") == "error" else None
                ),
            )

            telemetry_adapter.record_metric(
                "speech_adapter.calls", 1, {"operation": "analyze_audio"}
            )
            return result

        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count

            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "adapter.error", str(e))
            telemetry_adapter.record_metric(
                "speech_adapter.errors",
                1,
                {"operation": "analyze_audio", "error_type": error_type},
            )

            logger.error(f"Error en SpeechAdapter.analyze_audio: {str(e)}")

            # Calcular latencia incluso en caso de error
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Registrar métricas de error
            await vision_metrics.record_api_call(
                operation="analyze_audio",
                agent_id=agent_id,
                success=False,
                latency_ms=latency_ms,
                error_type=error_type,
            )

            return {"error": str(e), "status": "error"}

        finally:
            telemetry_adapter.end_span(span)

    async def _process_audio_input(
        self, audio_data: Union[str, bytes, Dict[str, Any]]
    ) -> Union[str, bytes]:
        """
        Procesa la entrada de audio en diferentes formatos.

        Args:
            audio_data: Datos del audio (base64, bytes o dict con url o path)

        Returns:
            Union[str, bytes]: Datos de audio procesados
        """
        # Si ya es bytes o base64, devolver directamente
        if isinstance(audio_data, bytes) or (
            isinstance(audio_data, str) and "base64" in audio_data
        ):
            return audio_data

        # Si es un diccionario, procesar según las claves
        if isinstance(audio_data, dict):
            # Si tiene URL, descargar el audio
            if "url" in audio_data:
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    async with session.get(audio_data["url"]) as response:
                        if response.status == 200:
                            return await response.read()
                        else:
                            raise ValueError(
                                f"Error al descargar audio de URL: {response.status}"
                            )

            # Si tiene path, leer el archivo
            elif "path" in audio_data:
                path = audio_data["path"]
                if not os.path.exists(path):
                    raise FileNotFoundError(
                        f"No se encontró el archivo de audio: {path}"
                    )

                with open(path, "rb") as f:
                    return f.read()

            # Si tiene base64, extraer
            elif "base64" in audio_data:
                return audio_data["base64"]

            else:
                raise ValueError(
                    "Formato de audio no válido. Debe contener 'url', 'path' o 'base64'."
                )

        # Si es una cadena que no es base64, asumir que es una ruta de archivo
        if isinstance(audio_data, str):
            if not os.path.exists(audio_data):
                raise FileNotFoundError(
                    f"No se encontró el archivo de audio: {audio_data}"
                )

            with open(audio_data, "rb") as f:
                return f.read()

        raise ValueError("Formato de audio no soportado.")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del adaptador.

        Returns:
            Dict[str, Any]: Estadísticas del adaptador
        """
        # Obtener estadísticas del cliente
        client_stats = (
            await speech_client.get_stats()
            if hasattr(speech_client, "get_stats")
            else {}
        )

        return {
            **self.stats,
            "client_stats": client_stats,
            "initialized": self.is_initialized,
        }


# Instancia global del adaptador
speech_adapter = SpeechAdapter()

"""
Cliente para servicios de Speech-to-Text de Vertex AI.

Este módulo proporciona un cliente para interactuar con los servicios de
Speech-to-Text de Vertex AI, permitiendo la transcripción de audio a texto.
"""

import asyncio
import base64
import json
import logging
import os
import time
from typing import Dict, List, Optional, Union, Any

from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from core.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)
telemetry_adapter = get_telemetry_adapter()

class STTClient:
    """Cliente para servicios de Speech-to-Text de Vertex AI."""
    
    def __init__(self, config=None):
        """Inicializa el cliente STT."""
        self.config = config or self._load_default_config()
        self.client = self._initialize_client()
        
        # Estadísticas
        self.stats = {
            "transcribe_operations": 0,
            "errors": 0,
            "latency_ms": []
        }
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Carga la configuración por defecto."""
        import os
        
        # Función auxiliar para leer variables de entorno enteras
        def get_env_int(var_name: str, default_value: int) -> int:
            val_str = os.environ.get(var_name)
            if val_str is None:
                return default_value
            try:
                return int(val_str)
            except ValueError:
                logger.warning(f"Valor inválido para la variable de entorno {var_name}: '{val_str}'. Usando el valor por defecto: {default_value}")
                return default_value
        
        return {
            "project_id": os.environ.get("GOOGLE_CLOUD_PROJECT"),
            "location": os.environ.get("VERTEX_LOCATION", "us-central1"),
            "model": os.environ.get("VERTEX_STT_MODEL", "speech-standard"),
            "language_code": os.environ.get("VERTEX_STT_LANGUAGE", "es-ES"),
            "sample_rate": get_env_int("VERTEX_STT_SAMPLE_RATE", 16000),
            "enable_automatic_punctuation": os.environ.get("VERTEX_STT_PUNCTUATION", "true").lower() == "true",
            "enable_word_time_offsets": os.environ.get("VERTEX_STT_WORD_TIMING", "false").lower() == "true",
            "max_alternatives": get_env_int("VERTEX_STT_MAX_ALTERNATIVES", 1),
            "profanity_filter": os.environ.get("VERTEX_STT_PROFANITY_FILTER", "false").lower() == "true",
            "use_enhanced_model": os.environ.get("VERTEX_STT_ENHANCED", "true").lower() == "true",
            "timeout_seconds": get_env_int("VERTEX_STT_TIMEOUT", 60)
        }
        
    def _initialize_client(self) -> Any:
        """Inicializa el cliente de Vertex AI Speech-to-Text."""
        try:
            # Intentar importar bibliotecas necesarias
            try:
                from google.cloud import speech_v1p1beta1 as speech
                SPEECH_AVAILABLE = True
            except ImportError:
                logger.warning("No se pudo importar la biblioteca de Google Cloud Speech. Usando modo mock.")
                SPEECH_AVAILABLE = False
                
            if not SPEECH_AVAILABLE:
                return {"mock": True}
                
            # Inicializar cliente
            client = speech.SpeechClient()
            
            return {
                "speech_client": client,
                "speech": speech,
                "mock": False
            }
        except Exception as e:
            logger.error(f"Error al inicializar cliente de Speech-to-Text: {e}")
            return {"mock": True}
    
    @circuit_breaker(max_failures=3, reset_timeout=60)
    async def transcribe(self, audio_data: bytes, language_code: Optional[str] = None, 
                       config_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transcribe audio a texto.
        
        Args:
            audio_data: Datos de audio en bytes
            language_code: Código de idioma (opcional, sobreescribe la configuración)
            config_override: Configuración adicional para sobreescribir la predeterminada
            
        Returns:
            Dict: Resultado de la transcripción
        """
        span = telemetry_adapter.start_span("STTClient.transcribe", {
            "audio_size_bytes": len(audio_data),
            "language_code": language_code or self.config.get("language_code")
        })
        
        try:
            # Actualizar estadísticas
            self.stats["transcribe_operations"] += 1
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(0.5)  # Simular latencia
                
                # Generar resultado mock
                result = {
                    "results": [
                        {
                            "alternatives": [
                                {
                                    "transcript": "Esto es una transcripción de prueba en modo mock.",
                                    "confidence": 0.95
                                }
                            ]
                        }
                    ],
                    "mock": True
                }
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
            else:
                # Preparar configuración
                speech = self.client.get("speech")
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=self.config.get("sample_rate"),
                    language_code=language_code or self.config.get("language_code"),
                    max_alternatives=self.config.get("max_alternatives"),
                    enable_automatic_punctuation=self.config.get("enable_automatic_punctuation"),
                    enable_word_time_offsets=self.config.get("enable_word_time_offsets"),
                    profanity_filter=self.config.get("profanity_filter"),
                    use_enhanced=self.config.get("use_enhanced_model")
                )
                
                # Sobreescribir configuración si se proporciona
                if config_override:
                    for key, value in config_override.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
                
                # Preparar audio
                audio = speech.RecognitionAudio(content=audio_data)
                
                # Ejecutar operación de transcripción
                # Convertir a operación asíncrona
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.get("speech_client").recognize(
                        config=config,
                        audio=audio
                    )
                )
                
                # Convertir respuesta a diccionario
                result = {
                    "results": [
                        {
                            "alternatives": [
                                {
                                    "transcript": alt.transcript,
                                    "confidence": alt.confidence
                                } for alt in result.alternatives
                            ]
                        } for result in response.results
                    ]
                }
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            self.stats["latency_ms"].append(latency_ms)
            if len(self.stats["latency_ms"]) > 100:
                self.stats["latency_ms"].pop(0)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.record_metric("stt_client.latency", latency_ms, {"operation": "transcribe"})
            
            # Extraer y registrar información relevante
            if result.get("results") and result["results"][0].get("alternatives"):
                transcript = result["results"][0]["alternatives"][0].get("transcript", "")
                confidence = result["results"][0]["alternatives"][0].get("confidence", 0.0)
                
                telemetry_adapter.set_span_attribute(span, "transcript.length", len(transcript))
                telemetry_adapter.set_span_attribute(span, "transcript.confidence", confidence)
                
                # Añadir información procesada al resultado
                result["text"] = transcript
                result["confidence"] = confidence
            
            return result
            
        except Exception as e:
            logger.error(f"Error al transcribir audio: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver resultado vacío en caso de error
            return {
                "error": str(e),
                "results": [],
                "text": "",
                "confidence": 0.0
            }
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cliente.
        
        Returns:
            Dict[str, Any]: Estadísticas del cliente
        """
        # Calcular promedio de latencia
        avg_latency = sum(self.stats["latency_ms"]) / len(self.stats["latency_ms"]) if self.stats["latency_ms"] else 0
        
        return {
            "transcribe_operations": self.stats["transcribe_operations"],
            "errors": self.stats["errors"],
            "avg_latency_ms": avg_latency,
            "model": self.config.get("model"),
            "language_code": self.config.get("language_code"),
            "sample_rate": self.config.get("sample_rate"),
            "mock_mode": self.client.get("mock", False)
        }

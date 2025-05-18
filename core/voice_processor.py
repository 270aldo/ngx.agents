"""
Procesador de voz para NGX Agents.

Este módulo proporciona funcionalidades para procesar voz, incluyendo
conversión de voz a texto, texto a voz y análisis de emociones.
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Union, Any, Tuple

from clients.vertex_ai.voice.stt_client import STTClient
from clients.vertex_ai.voice.tts_client import TTSClient
from clients.vertex_ai.voice.emotion_analyzer import EmotionAnalyzer
from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter

logger = logging.getLogger(__name__)
telemetry_adapter = get_telemetry_adapter()

class VoiceProcessor:
    """Procesador de voz para NGX Agents."""
    
    def __init__(self, config=None):
        """Inicializa el procesador de voz."""
        self.config = config or self._load_default_config()
        self.stt_client = self._initialize_stt_client()
        self.tts_client = self._initialize_tts_client()
        self.emotion_analyzer = self._initialize_emotion_analyzer()
        
        # Estadísticas
        self.stats = {
            "speech_to_text_operations": 0,
            "text_to_speech_operations": 0,
            "emotion_analysis_operations": 0,
            "errors": 0,
            "stt_latency_ms": [],
            "tts_latency_ms": [],
            "emotion_latency_ms": []
        }
        
        logger.info("Procesador de voz inicializado")
        
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
        
        # Función auxiliar para leer variables de entorno flotantes
        def get_env_float(var_name: str, default_value: float) -> float:
            val_str = os.environ.get(var_name)
            if val_str is None:
                return default_value
            try:
                return float(val_str)
            except ValueError:
                logger.warning(f"Valor inválido para la variable de entorno {var_name}: '{val_str}'. Usando el valor por defecto: {default_value}")
                return default_value
        
        return {
            "default_language": os.environ.get("VOICE_DEFAULT_LANGUAGE", "es-ES"),
            "analyze_emotions": os.environ.get("VOICE_ANALYZE_EMOTIONS", "true").lower() == "true",
            "min_confidence_threshold": get_env_float("VOICE_MIN_CONFIDENCE", 0.6),
            "max_audio_duration_seconds": get_env_int("VOICE_MAX_DURATION", 60),
            "default_voice": os.environ.get("VOICE_DEFAULT_VOICE", "es-ES-Standard-A"),
            "cache_tts_results": os.environ.get("VOICE_CACHE_TTS", "true").lower() == "true"
        }
    
    def _initialize_stt_client(self) -> STTClient:
        """Inicializa el cliente STT."""
        return STTClient()
    
    def _initialize_tts_client(self) -> TTSClient:
        """Inicializa el cliente TTS."""
        return TTSClient()
    
    def _initialize_emotion_analyzer(self) -> EmotionAnalyzer:
        """Inicializa el analizador de emociones."""
        return EmotionAnalyzer()
    
    async def speech_to_text(self, audio_data: bytes, language_code: Optional[str] = None, 
                           analyze_emotion: Optional[bool] = None) -> Dict[str, Any]:
        """
        Convierte audio a texto y opcionalmente analiza emociones.
        
        Args:
            audio_data: Datos de audio en bytes
            language_code: Código de idioma (opcional)
            analyze_emotion: Si se debe analizar emociones (opcional)
            
        Returns:
            Dict: Resultado de la transcripción y análisis de emociones
        """
        span = telemetry_adapter.start_span("VoiceProcessor.speech_to_text", {
            "audio_size_bytes": len(audio_data),
            "language_code": language_code or self.config.get("default_language")
        })
        
        try:
            # Actualizar estadísticas
            self.stats["speech_to_text_operations"] += 1
            
            start_time = time.time()
            
            # Transcribir audio
            transcription_result = await self.stt_client.transcribe(
                audio_data, 
                language_code or self.config.get("default_language")
            )
            
            stt_end_time = time.time()
            stt_latency_ms = (stt_end_time - start_time) * 1000
            self.stats["stt_latency_ms"].append(stt_latency_ms)
            if len(self.stats["stt_latency_ms"]) > 100:
                self.stats["stt_latency_ms"].pop(0)
            
            # Extraer texto y confianza
            text = transcription_result.get("text", "")
            confidence = transcription_result.get("confidence", 0.0)
            
            # Preparar resultado
            result = {
                "text": text,
                "confidence": confidence,
                "language_code": language_code or self.config.get("default_language"),
                "transcription_details": transcription_result
            }
            
            # Analizar emociones si está habilitado
            should_analyze = analyze_emotion if analyze_emotion is not None else self.config.get("analyze_emotions")
            if should_analyze and confidence >= self.config.get("min_confidence_threshold"):
                emotion_start_time = time.time()
                
                emotion_result = await self.emotion_analyzer.analyze(audio_data, text)
                
                emotion_end_time = time.time()
                emotion_latency_ms = (emotion_end_time - emotion_start_time) * 1000
                self.stats["emotion_latency_ms"].append(emotion_latency_ms)
                if len(self.stats["emotion_latency_ms"]) > 100:
                    self.stats["emotion_latency_ms"].pop(0)
                
                # Actualizar estadísticas
                self.stats["emotion_analysis_operations"] += 1
                
                # Añadir resultado de emociones
                result["emotion"] = emotion_result
            
            end_time = time.time()
            total_latency_ms = (end_time - start_time) * 1000
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "text_length", len(text))
            telemetry_adapter.set_span_attribute(span, "confidence", confidence)
            telemetry_adapter.set_span_attribute(span, "total_latency_ms", total_latency_ms)
            telemetry_adapter.set_span_attribute(span, "stt_latency_ms", stt_latency_ms)
            
            if "emotion" in result:
                telemetry_adapter.set_span_attribute(span, "emotion_analyzed", True)
                telemetry_adapter.set_span_attribute(span, "emotion_latency_ms", emotion_latency_ms)
                telemetry_adapter.set_span_attribute(span, "dominant_emotion", result["emotion"].get("dominant_emotion"))
            else:
                telemetry_adapter.set_span_attribute(span, "emotion_analyzed", False)
            
            telemetry_adapter.record_metric("voice_processor.stt_latency", stt_latency_ms)
            telemetry_adapter.record_metric("voice_processor.total_latency", total_latency_ms)
            
            return result
            
        except Exception as e:
            logger.error(f"Error al convertir voz a texto: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver resultado vacío en caso de error
            return {
                "text": "",
                "confidence": 0.0,
                "language_code": language_code or self.config.get("default_language"),
                "error": str(e)
            }
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def text_to_speech(self, text: str, voice_config: Optional[Dict[str, Any]] = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        Convierte texto a audio.
        
        Args:
            text: Texto a sintetizar
            voice_config: Configuración de voz (opcional)
            
        Returns:
            Tuple[bytes, Dict[str, Any]]: Datos de audio y metadatos
        """
        span = telemetry_adapter.start_span("VoiceProcessor.text_to_speech", {
            "text_length": len(text),
            "voice_name": (voice_config or {}).get("voice_name", self.config.get("default_voice"))
        })
        
        try:
            # Actualizar estadísticas
            self.stats["text_to_speech_operations"] += 1
            
            start_time = time.time()
            
            # Preparar configuración de voz
            vc = voice_config or {}
            if "voice_name" not in vc and self.config.get("default_voice"):
                vc["voice_name"] = self.config.get("default_voice")
            
            if "language_code" not in vc and self.config.get("default_language"):
                vc["language_code"] = self.config.get("default_language")
            
            # Sintetizar texto
            audio_data, metadata = await self.tts_client.synthesize(text, vc)
            
            end_time = time.time()
            
            # Actualizar estadísticas
            tts_latency_ms = (end_time - start_time) * 1000
            self.stats["tts_latency_ms"].append(tts_latency_ms)
            if len(self.stats["tts_latency_ms"]) > 100:
                self.stats["tts_latency_ms"].pop(0)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "audio_size_bytes", len(audio_data))
            telemetry_adapter.set_span_attribute(span, "duration_seconds", metadata.get("duration_seconds", 0))
            telemetry_adapter.set_span_attribute(span, "tts_latency_ms", tts_latency_ms)
            telemetry_adapter.record_metric("voice_processor.tts_latency", tts_latency_ms)
            
            return audio_data, metadata
            
        except Exception as e:
            logger.error(f"Error al convertir texto a voz: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver audio vacío en caso de error
            return bytes(), {"error": str(e)}
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def analyze_voice_emotion(self, audio_data: bytes, transcript: Optional[str] = None) -> Dict[str, Any]:
        """
        Analiza emociones en la voz.
        
        Args:
            audio_data: Datos de audio en bytes
            transcript: Transcripción del audio (opcional)
            
        Returns:
            Dict: Resultado del análisis de emociones
        """
        span = telemetry_adapter.start_span("VoiceProcessor.analyze_voice_emotion", {
            "audio_size_bytes": len(audio_data),
            "has_transcript": transcript is not None
        })
        
        try:
            # Actualizar estadísticas
            self.stats["emotion_analysis_operations"] += 1
            
            start_time = time.time()
            
            # Si no hay transcripción, obtenerla primero
            if transcript is None:
                transcription_result = await self.stt_client.transcribe(
                    audio_data, 
                    self.config.get("default_language")
                )
                transcript = transcription_result.get("text", "")
            
            # Analizar emociones
            emotion_result = await self.emotion_analyzer.analyze(audio_data, transcript)
            
            end_time = time.time()
            
            # Actualizar estadísticas
            emotion_latency_ms = (end_time - start_time) * 1000
            self.stats["emotion_latency_ms"].append(emotion_latency_ms)
            if len(self.stats["emotion_latency_ms"]) > 100:
                self.stats["emotion_latency_ms"].pop(0)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "emotion_latency_ms", emotion_latency_ms)
            telemetry_adapter.set_span_attribute(span, "dominant_emotion", emotion_result.get("dominant_emotion"))
            telemetry_adapter.set_span_attribute(span, "confidence", emotion_result.get("confidence"))
            telemetry_adapter.record_metric("voice_processor.emotion_latency", emotion_latency_ms)
            
            return emotion_result
            
        except Exception as e:
            logger.error(f"Error al analizar emociones en la voz: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver resultado predeterminado en caso de error
            return {
                "emotions": {
                    "neutral": 1.0
                },
                "dominant_emotion": "neutral",
                "confidence": 0.0,
                "error": str(e)
            }
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_available_voices(self, language_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene las voces disponibles.
        
        Args:
            language_code: Código de idioma para filtrar (opcional)
            
        Returns:
            List[Dict[str, Any]]: Lista de voces disponibles
        """
        return await self.tts_client.get_available_voices(
            language_code or self.config.get("default_language")
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del procesador de voz.
        
        Returns:
            Dict[str, Any]: Estadísticas del procesador
        """
        # Calcular promedios de latencia
        avg_stt_latency = sum(self.stats["stt_latency_ms"]) / len(self.stats["stt_latency_ms"]) if self.stats["stt_latency_ms"] else 0
        avg_tts_latency = sum(self.stats["tts_latency_ms"]) / len(self.stats["tts_latency_ms"]) if self.stats["tts_latency_ms"] else 0
        avg_emotion_latency = sum(self.stats["emotion_latency_ms"]) / len(self.stats["emotion_latency_ms"]) if self.stats["emotion_latency_ms"] else 0
        
        # Obtener estadísticas de los clientes
        stt_stats = await self.stt_client.get_stats()
        tts_stats = await self.tts_client.get_stats()
        emotion_stats = await self.emotion_analyzer.get_stats()
        
        return {
            "speech_to_text_operations": self.stats["speech_to_text_operations"],
            "text_to_speech_operations": self.stats["text_to_speech_operations"],
            "emotion_analysis_operations": self.stats["emotion_analysis_operations"],
            "errors": self.stats["errors"],
            "avg_stt_latency_ms": avg_stt_latency,
            "avg_tts_latency_ms": avg_tts_latency,
            "avg_emotion_latency_ms": avg_emotion_latency,
            "default_language": self.config.get("default_language"),
            "default_voice": self.config.get("default_voice"),
            "analyze_emotions": self.config.get("analyze_emotions"),
            "min_confidence_threshold": self.config.get("min_confidence_threshold"),
            "stt_stats": stt_stats,
            "tts_stats": tts_stats,
            "emotion_stats": emotion_stats
        }

# Instancia global del procesador de voz
voice_processor = VoiceProcessor()

"""
Cliente para servicios de Text-to-Speech de Vertex AI.

Este módulo proporciona un cliente para interactuar con los servicios de
Text-to-Speech de Vertex AI, permitiendo la síntesis de texto a audio.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Dict, List, Optional, Union, Any, Tuple

from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from core.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)
telemetry_adapter = get_telemetry_adapter()

class TTSClient:
    """Cliente para servicios de Text-to-Speech de Vertex AI."""
    
    def __init__(self, config=None):
        """Inicializa el cliente TTS."""
        self.config = config or self._load_default_config()
        self.client = self._initialize_client()
        self.cache = {}
        
        # Estadísticas
        self.stats = {
            "synthesize_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
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
            "project_id": os.environ.get("GOOGLE_CLOUD_PROJECT"),
            "location": os.environ.get("VERTEX_LOCATION", "us-central1"),
            "model": os.environ.get("VERTEX_TTS_MODEL", "standard"),
            "language_code": os.environ.get("VERTEX_TTS_LANGUAGE", "es-ES"),
            "voice_name": os.environ.get("VERTEX_TTS_VOICE", "es-ES-Standard-A"),
            "audio_encoding": os.environ.get("VERTEX_TTS_ENCODING", "LINEAR16"),
            "speaking_rate": get_env_float("VERTEX_TTS_SPEAKING_RATE", 1.0),
            "pitch": get_env_float("VERTEX_TTS_PITCH", 0.0),
            "volume_gain_db": get_env_float("VERTEX_TTS_VOLUME", 0.0),
            "sample_rate": get_env_int("VERTEX_TTS_SAMPLE_RATE", 24000),
            "use_cache": os.environ.get("VERTEX_TTS_USE_CACHE", "true").lower() == "true",
            "max_cache_size": get_env_int("VERTEX_TTS_MAX_CACHE", 100),
            "timeout_seconds": get_env_int("VERTEX_TTS_TIMEOUT", 60)
        }
        
    def _initialize_client(self) -> Any:
        """Inicializa el cliente de Vertex AI Text-to-Speech."""
        try:
            # Intentar importar bibliotecas necesarias
            try:
                from google.cloud import texttospeech
                TTS_AVAILABLE = True
            except ImportError:
                logger.warning("No se pudo importar la biblioteca de Google Cloud Text-to-Speech. Usando modo mock.")
                TTS_AVAILABLE = False
                
            if not TTS_AVAILABLE:
                return {"mock": True}
                
            # Inicializar cliente
            client = texttospeech.TextToSpeechClient()
            
            return {
                "tts_client": client,
                "texttospeech": texttospeech,
                "mock": False
            }
        except Exception as e:
            logger.error(f"Error al inicializar cliente de Text-to-Speech: {e}")
            return {"mock": True}
    
    def _get_cache_key(self, text: str, voice_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Genera una clave de caché para el texto y la configuración de voz.
        
        Args:
            text: Texto a sintetizar
            voice_config: Configuración de voz
            
        Returns:
            str: Clave de caché
        """
        # Combinar texto y configuración
        config = voice_config or {}
        cache_data = {
            "text": text,
            "voice_name": config.get("voice_name", self.config.get("voice_name")),
            "language_code": config.get("language_code", self.config.get("language_code")),
            "speaking_rate": config.get("speaking_rate", self.config.get("speaking_rate")),
            "pitch": config.get("pitch", self.config.get("pitch")),
            "volume_gain_db": config.get("volume_gain_db", self.config.get("volume_gain_db")),
            "sample_rate": config.get("sample_rate", self.config.get("sample_rate")),
            "audio_encoding": config.get("audio_encoding", self.config.get("audio_encoding"))
        }
        
        # Generar hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    @circuit_breaker(max_failures=3, reset_timeout=60)
    async def synthesize(self, text: str, voice_config: Optional[Dict[str, Any]] = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        Sintetiza texto a audio.
        
        Args:
            text: Texto a sintetizar
            voice_config: Configuración de voz (opcional, sobreescribe la configuración)
            
        Returns:
            Tuple[bytes, Dict[str, Any]]: Datos de audio y metadatos
        """
        span = telemetry_adapter.start_span("TTSClient.synthesize", {
            "text_length": len(text),
            "voice_name": (voice_config or {}).get("voice_name", self.config.get("voice_name"))
        })
        
        try:
            # Actualizar estadísticas
            self.stats["synthesize_operations"] += 1
            
            # Verificar caché si está habilitada
            if self.config.get("use_cache"):
                cache_key = self._get_cache_key(text, voice_config)
                if cache_key in self.cache:
                    self.stats["cache_hits"] += 1
                    telemetry_adapter.set_span_attribute(span, "cache.hit", True)
                    telemetry_adapter.record_metric("tts_client.cache_hit", 1)
                    return self.cache[cache_key]
                else:
                    self.stats["cache_misses"] += 1
                    telemetry_adapter.set_span_attribute(span, "cache.hit", False)
                    telemetry_adapter.record_metric("tts_client.cache_miss", 1)
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(0.5)  # Simular latencia
                
                # Generar audio mock (silencio de 1 segundo)
                sample_rate = (voice_config or {}).get("sample_rate", self.config.get("sample_rate"))
                audio_data = bytes([0] * (sample_rate * 2))  # 1 segundo de silencio (16-bit)
                
                metadata = {
                    "duration_seconds": 1.0,
                    "sample_rate": sample_rate,
                    "channels": 1,
                    "mock": True
                }
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
            else:
                # Preparar configuración
                texttospeech = self.client.get("texttospeech")
                
                # Configuración de entrada
                input_text = texttospeech.SynthesisInput(text=text)
                
                # Configuración de voz
                vc = voice_config or {}
                voice = texttospeech.VoiceSelectionParams(
                    language_code=vc.get("language_code", self.config.get("language_code")),
                    name=vc.get("voice_name", self.config.get("voice_name"))
                )
                
                # Configuración de audio
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=getattr(
                        texttospeech.AudioEncoding, 
                        vc.get("audio_encoding", self.config.get("audio_encoding"))
                    ),
                    speaking_rate=vc.get("speaking_rate", self.config.get("speaking_rate")),
                    pitch=vc.get("pitch", self.config.get("pitch")),
                    volume_gain_db=vc.get("volume_gain_db", self.config.get("volume_gain_db")),
                    sample_rate_hertz=vc.get("sample_rate", self.config.get("sample_rate"))
                )
                
                # Ejecutar operación de síntesis
                # Convertir a operación asíncrona
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.get("tts_client").synthesize_speech(
                        input=input_text,
                        voice=voice,
                        audio_config=audio_config
                    )
                )
                
                # Extraer audio y metadatos
                audio_data = response.audio_content
                
                # Estimar duración basada en el tamaño del audio
                sample_rate = vc.get("sample_rate", self.config.get("sample_rate"))
                bytes_per_sample = 2  # 16-bit audio
                duration_seconds = len(audio_data) / (sample_rate * bytes_per_sample)
                
                metadata = {
                    "duration_seconds": duration_seconds,
                    "sample_rate": sample_rate,
                    "channels": 1,
                    "encoding": vc.get("audio_encoding", self.config.get("audio_encoding"))
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
            telemetry_adapter.set_span_attribute(span, "audio.size_bytes", len(audio_data))
            telemetry_adapter.set_span_attribute(span, "audio.duration_seconds", metadata.get("duration_seconds", 0))
            telemetry_adapter.record_metric("tts_client.latency", latency_ms, {"operation": "synthesize"})
            
            # Almacenar en caché si está habilitada
            result = (audio_data, metadata)
            if self.config.get("use_cache"):
                cache_key = self._get_cache_key(text, voice_config)
                self.cache[cache_key] = result
                
                # Limitar tamaño de caché
                if len(self.cache) > self.config.get("max_cache_size"):
                    # Eliminar entrada más antigua
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
            
            return result
            
        except Exception as e:
            logger.error(f"Error al sintetizar texto: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver audio vacío en caso de error
            return bytes(), {"error": str(e)}
            
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
        span = telemetry_adapter.start_span("TTSClient.get_available_voices", {
            "language_code": language_code
        })
        
        try:
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(0.2)  # Simular latencia
                
                # Generar voces mock
                voices = [
                    {"name": "es-ES-Standard-A", "gender": "FEMALE", "language_codes": ["es-ES"]},
                    {"name": "es-ES-Standard-B", "gender": "MALE", "language_codes": ["es-ES"]},
                    {"name": "es-ES-Wavenet-C", "gender": "FEMALE", "language_codes": ["es-ES"]},
                    {"name": "es-ES-Wavenet-D", "gender": "MALE", "language_codes": ["es-ES"]},
                    {"name": "en-US-Standard-A", "gender": "FEMALE", "language_codes": ["en-US"]},
                    {"name": "en-US-Standard-B", "gender": "MALE", "language_codes": ["en-US"]},
                    {"name": "en-US-Wavenet-C", "gender": "FEMALE", "language_codes": ["en-US"]},
                    {"name": "en-US-Wavenet-D", "gender": "MALE", "language_codes": ["en-US"]}
                ]
                
                # Filtrar por idioma si se proporciona
                if language_code:
                    voices = [v for v in voices if language_code in v["language_codes"]]
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
                telemetry_adapter.set_span_attribute(span, "voices.count", len(voices))
                
                return voices
            else:
                # Ejecutar operación para obtener voces
                # Convertir a operación asíncrona
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.get("tts_client").list_voices(language_code=language_code)
                )
                
                # Convertir respuesta a lista de diccionarios
                voices = []
                for voice in response.voices:
                    voices.append({
                        "name": voice.name,
                        "gender": str(voice.ssml_gender),
                        "language_codes": list(voice.language_codes),
                        "natural_sample_rate_hertz": voice.natural_sample_rate_hertz
                    })
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "real")
                telemetry_adapter.set_span_attribute(span, "voices.count", len(voices))
                
                return voices
                
        except Exception as e:
            logger.error(f"Error al obtener voces disponibles: {str(e)}", exc_info=True)
            telemetry_adapter.record_exception(span, e)
            
            # Devolver lista vacía en caso de error
            return []
            
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
            "synthesize_operations": self.stats["synthesize_operations"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "cache_hit_ratio": self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"]) if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0,
            "errors": self.stats["errors"],
            "avg_latency_ms": avg_latency,
            "model": self.config.get("model"),
            "voice_name": self.config.get("voice_name"),
            "language_code": self.config.get("language_code"),
            "sample_rate": self.config.get("sample_rate"),
            "cache_enabled": self.config.get("use_cache"),
            "cache_size": len(self.cache),
            "mock_mode": self.client.get("mock", False)
        }

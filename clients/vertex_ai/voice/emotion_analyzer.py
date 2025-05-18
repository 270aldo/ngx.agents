"""
Analizador de emociones en voz para NGX Agents.

Este módulo proporciona funcionalidades para analizar emociones en la voz
utilizando Vertex AI y modelos especializados.
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Union, Any

from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from core.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)
telemetry_adapter = get_telemetry_adapter()

class EmotionAnalyzer:
    """Analizador de emociones en la voz."""
    
    def __init__(self, config=None):
        """Inicializa el analizador de emociones."""
        self.config = config or self._load_default_config()
        self.client = self._initialize_client()
        
        # Estadísticas
        self.stats = {
            "analyze_operations": 0,
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
            "model": os.environ.get("VERTEX_EMOTION_MODEL", "gemini-1.5-pro"),
            "confidence_threshold": get_env_float("VERTEX_EMOTION_THRESHOLD", 0.6),
            "use_audio_features": os.environ.get("VERTEX_EMOTION_AUDIO_FEATURES", "true").lower() == "true",
            "use_text_content": os.environ.get("VERTEX_EMOTION_TEXT_CONTENT", "true").lower() == "true",
            "timeout_seconds": get_env_int("VERTEX_EMOTION_TIMEOUT", 30)
        }
        
    def _initialize_client(self) -> Any:
        """Inicializa el cliente para análisis de emociones."""
        try:
            # Intentar importar bibliotecas necesarias
            try:
                from google.cloud import aiplatform
                VERTEX_AVAILABLE = True
            except ImportError:
                logger.warning("No se pudo importar la biblioteca de Google Cloud AI Platform. Usando modo mock.")
                VERTEX_AVAILABLE = False
                
            if not VERTEX_AVAILABLE:
                return {"mock": True}
                
            # Inicializar cliente
            aiplatform.init(
                project=self.config.get("project_id"),
                location=self.config.get("location")
            )
            
            # Obtener modelo
            model_name = self.config.get("model")
            model = aiplatform.GenerativeModel(model_name)
            
            return {
                "aiplatform": aiplatform,
                "model": model,
                "mock": False
            }
        except Exception as e:
            logger.error(f"Error al inicializar cliente para análisis de emociones: {e}")
            return {"mock": True}
    
    @circuit_breaker(max_failures=3, reset_timeout=60)
    async def analyze(self, audio_data: bytes, transcript: Optional[str] = None) -> Dict[str, Any]:
        """
        Analiza emociones en el audio.
        
        Args:
            audio_data: Datos de audio en bytes
            transcript: Transcripción del audio (opcional)
            
        Returns:
            Dict: Resultado del análisis de emociones
        """
        span = telemetry_adapter.start_span("EmotionAnalyzer.analyze", {
            "audio_size_bytes": len(audio_data),
            "has_transcript": transcript is not None
        })
        
        try:
            # Actualizar estadísticas
            self.stats["analyze_operations"] += 1
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(0.3)  # Simular latencia
                
                # Generar resultado mock
                import random
                
                # Emociones básicas con valores aleatorios
                emotions = {
                    "happy": random.uniform(0.0, 1.0),
                    "sad": random.uniform(0.0, 1.0),
                    "angry": random.uniform(0.0, 1.0),
                    "surprised": random.uniform(0.0, 1.0),
                    "fearful": random.uniform(0.0, 1.0),
                    "neutral": random.uniform(0.0, 1.0)
                }
                
                # Normalizar para que sumen 1.0
                total = sum(emotions.values())
                emotions = {k: v / total for k, v in emotions.items()}
                
                # Determinar emoción dominante
                dominant_emotion = max(emotions.items(), key=lambda x: x[1])
                
                result = {
                    "emotions": emotions,
                    "dominant_emotion": dominant_emotion[0],
                    "confidence": dominant_emotion[1],
                    "mock": True
                }
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
            else:
                # Preparar prompt para el modelo
                prompt = "Analiza las emociones presentes en este audio. "
                
                if transcript and self.config.get("use_text_content"):
                    prompt += f"La transcripción del audio es: '{transcript}'. "
                
                prompt += """
                Proporciona un análisis detallado de las emociones detectadas en el audio.
                Clasifica las emociones en las siguientes categorías: happy (feliz), sad (triste), 
                angry (enojado), surprised (sorprendido), fearful (temeroso), neutral (neutral).
                
                Devuelve el resultado en formato JSON con la siguiente estructura:
                {
                    "emotions": {
                        "happy": 0.1,
                        "sad": 0.2,
                        "angry": 0.1,
                        "surprised": 0.1,
                        "fearful": 0.1,
                        "neutral": 0.4
                    },
                    "dominant_emotion": "neutral",
                    "confidence": 0.4,
                    "analysis": "El hablante muestra principalmente un tono neutral con ligeros indicios de tristeza."
                }
                
                Los valores de cada emoción deben sumar 1.0. La emoción dominante debe ser la que tenga el valor más alto.
                """
                
                # Preparar contenido multimodal
                aiplatform = self.client.get("aiplatform")
                model = self.client.get("model")
                
                # Convertir audio a formato adecuado para el modelo
                import base64
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                
                # Crear contenido multimodal
                content = [
                    {"text": prompt},
                    {"audio": audio_b64}
                ]
                
                # Ejecutar generación
                # Convertir a operación asíncrona
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: model.generate_content(content)
                )
                
                # Extraer resultado
                try:
                    # Intentar parsear JSON de la respuesta
                    import json
                    result_text = response.text
                    
                    # Extraer solo la parte JSON si hay texto adicional
                    import re
                    json_match = re.search(r'({[\s\S]*})', result_text)
                    if json_match:
                        result_text = json_match.group(1)
                    
                    result = json.loads(result_text)
                    
                    # Verificar estructura básica
                    if "emotions" not in result or "dominant_emotion" not in result:
                        raise ValueError("Respuesta del modelo no tiene la estructura esperada")
                    
                except Exception as e:
                    logger.warning(f"Error al parsear respuesta del modelo: {e}. Usando resultado predeterminado.")
                    result = {
                        "emotions": {
                            "happy": 0.1,
                            "sad": 0.1,
                            "angry": 0.1,
                            "surprised": 0.1,
                            "fearful": 0.1,
                            "neutral": 0.5
                        },
                        "dominant_emotion": "neutral",
                        "confidence": 0.5,
                        "analysis": "No se pudo analizar correctamente las emociones.",
                        "error": str(e)
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
            telemetry_adapter.set_span_attribute(span, "emotion.dominant", result.get("dominant_emotion"))
            telemetry_adapter.set_span_attribute(span, "emotion.confidence", result.get("confidence"))
            telemetry_adapter.record_metric("emotion_analyzer.latency", latency_ms, {"operation": "analyze"})
            
            return result
            
        except Exception as e:
            logger.error(f"Error al analizar emociones: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver resultado predeterminado en caso de error
            return {
                "emotions": {
                    "happy": 0.0,
                    "sad": 0.0,
                    "angry": 0.0,
                    "surprised": 0.0,
                    "fearful": 0.0,
                    "neutral": 1.0
                },
                "dominant_emotion": "neutral",
                "confidence": 0.0,
                "error": str(e)
            }
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del analizador.
        
        Returns:
            Dict[str, Any]: Estadísticas del analizador
        """
        # Calcular promedio de latencia
        avg_latency = sum(self.stats["latency_ms"]) / len(self.stats["latency_ms"]) if self.stats["latency_ms"] else 0
        
        return {
            "analyze_operations": self.stats["analyze_operations"],
            "errors": self.stats["errors"],
            "avg_latency_ms": avg_latency,
            "model": self.config.get("model"),
            "confidence_threshold": self.config.get("confidence_threshold"),
            "use_audio_features": self.config.get("use_audio_features"),
            "use_text_content": self.config.get("use_text_content"),
            "mock_mode": self.client.get("mock", False)
        }

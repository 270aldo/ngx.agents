"""
Adaptador para capacidades de voz.

Este adaptador proporciona una interfaz simplificada para utilizar
las capacidades de procesamiento de voz desde otros componentes del sistema.
"""

import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime

from core.voice_processor import voice_processor
from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.logging_config import get_logger

logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()

class VoiceAdapter(BaseAgentAdapter):
    """Adaptador para capacidades de voz."""
    
    _instance = None
    
    def __new__(cls):
        """Implementa patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(VoiceAdapter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el adaptador de voz."""
        super().__init__()
        if self._initialized:
            return
            
        self.voice_processor = voice_processor
        self._initialized = True
        
    async def process_voice_command(self, audio_data: bytes, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Procesa un comando de voz.
        
        Args:
            audio_data: Datos de audio en bytes
            context: Contexto adicional (opcional)
            
        Returns:
            Dict: Resultado del procesamiento con texto y análisis de emociones
        """
        span = telemetry_adapter.start_span("VoiceAdapter.process_voice_command", {
            "audio_size_bytes": len(audio_data),
            "has_context": context is not None
        })
        
        try:
            # Extraer configuración del contexto
            ctx = context or {}
            language_code = ctx.get("language_code")
            analyze_emotion = ctx.get("analyze_emotion")
            
            # Procesar audio
            result = await self.voice_processor.speech_to_text(
                audio_data, 
                language_code, 
                analyze_emotion
            )
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "text_length", len(result.get("text", "")))
            telemetry_adapter.set_span_attribute(span, "confidence", result.get("confidence", 0.0))
            
            if "emotion" in result:
                telemetry_adapter.set_span_attribute(span, "emotion_analyzed", True)
                telemetry_adapter.set_span_attribute(span, "dominant_emotion", result["emotion"].get("dominant_emotion"))
            else:
                telemetry_adapter.set_span_attribute(span, "emotion_analyzed", False)
            
            return result
            
        except Exception as e:
            logger.error(f"Error al procesar comando de voz: {str(e)}", exc_info=True)
            telemetry_adapter.record_exception(span, e)
            
            # Devolver resultado vacío en caso de error
            return {
                "text": "",
                "confidence": 0.0,
                "error": str(e)
            }
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def generate_voice_response(self, text: str, voice_config: Optional[Dict[str, Any]] = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        Genera una respuesta de voz.
        
        Args:
            text: Texto a sintetizar
            voice_config: Configuración de voz (opcional)
            
        Returns:
            Tuple[bytes, Dict[str, Any]]: Datos de audio y metadatos
        """
        span = telemetry_adapter.start_span("VoiceAdapter.generate_voice_response", {
            "text_length": len(text),
            "has_voice_config": voice_config is not None
        })
        
        try:
            # Generar audio
            audio_data, metadata = await self.voice_processor.text_to_speech(text, voice_config)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "audio_size_bytes", len(audio_data))
            telemetry_adapter.set_span_attribute(span, "duration_seconds", metadata.get("duration_seconds", 0))
            
            return audio_data, metadata
            
        except Exception as e:
            logger.error(f"Error al generar respuesta de voz: {str(e)}", exc_info=True)
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
        span = telemetry_adapter.start_span("VoiceAdapter.analyze_voice_emotion", {
            "audio_size_bytes": len(audio_data),
            "has_transcript": transcript is not None
        })
        
        try:
            # Analizar emociones
            result = await self.voice_processor.analyze_voice_emotion(audio_data, transcript)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "dominant_emotion", result.get("dominant_emotion"))
            telemetry_adapter.set_span_attribute(span, "confidence", result.get("confidence", 0.0))
            
            return result
            
        except Exception as e:
            logger.error(f"Error al analizar emociones en la voz: {str(e)}", exc_info=True)
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
        return await self.voice_processor.get_available_voices(language_code)
    
    async def process_conversation(self, audio_data: bytes, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Procesa una conversación completa (entrada de voz y generación de respuesta).
        
        Args:
            audio_data: Datos de audio en bytes
            context: Contexto adicional (opcional)
            
        Returns:
            Dict: Resultado del procesamiento con texto, respuesta y audio
        """
        span = telemetry_adapter.start_span("VoiceAdapter.process_conversation", {
            "audio_size_bytes": len(audio_data),
            "has_context": context is not None
        })
        
        try:
            # Procesar comando de voz
            command_result = await self.process_voice_command(audio_data, context)
            
            # Verificar si hay texto reconocido
            text = command_result.get("text", "")
            if not text:
                telemetry_adapter.set_span_attribute(span, "has_recognized_text", False)
                return {
                    "input": command_result,
                    "error": "No se pudo reconocer texto en el audio"
                }
            
            telemetry_adapter.set_span_attribute(span, "has_recognized_text", True)
            
            # Aquí normalmente se procesaría el texto para generar una respuesta
            # En este ejemplo, simplemente devolvemos un eco de la entrada
            response_text = f"Recibido: {text}"
            
            # Generar respuesta de voz
            ctx = context or {}
            voice_config = ctx.get("voice_config")
            audio_data, audio_metadata = await self.generate_voice_response(response_text, voice_config)
            
            # Preparar resultado
            result = {
                "input": command_result,
                "response": {
                    "text": response_text,
                    "audio": audio_data,
                    "audio_metadata": audio_metadata
                }
            }
            
            # Añadir información de emociones si está disponible
            if "emotion" in command_result:
                result["emotion"] = command_result["emotion"]
            
            telemetry_adapter.set_span_attribute(span, "response_length", len(response_text))
            telemetry_adapter.set_span_attribute(span, "audio_size_bytes", len(audio_data))
            
            return result
            
        except Exception as e:
            logger.error(f"Error al procesar conversación: {str(e)}", exc_info=True)
            telemetry_adapter.record_exception(span, e)
            
            # Devolver resultado de error
            return {
                "error": str(e)
            }
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del adaptador de voz.
        
        Returns:
            Dict[str, Any]: Estadísticas del adaptador
        """
        return await self.voice_processor.get_stats()

    async def _process_query(self, query: str, user_id: str = None, session_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario relacionada con voz.
        
        Args:
            query: La consulta del usuario
            user_id: ID del usuario
            session_id: ID de la sesión
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta del adaptador
        """
        try:
            # Clasificar el tipo de consulta
            query_type = await self._classify_query(query, user_id)
            
            # Verificar si hay datos de audio en los kwargs
            audio_data = kwargs.get('audio_data')
            context = kwargs.get('context', {})
            text = kwargs.get('text')
            
            # Determinar la operación a realizar según el tipo de consulta
            result = None
            
            if query_type == "voice_to_text" and audio_data:
                # Convertir voz a texto
                result = await self.process_voice_command(audio_data, context)
            elif query_type == "text_to_voice" and text:
                # Convertir texto a voz
                audio_data, metadata = await self.generate_voice_response(text, context)
                result = {
                    "audio_data": audio_data,
                    "metadata": metadata,
                    "text": text
                }
            elif query_type == "emotion_analysis" and audio_data:
                # Analizar emociones en la voz
                result = await self.analyze_voice_emotion(audio_data, text)
            elif query_type == "conversation" and audio_data:
                # Procesar una conversación completa
                result = await self.process_conversation(audio_data, context)
            elif query_type == "get_voices":
                # Obtener voces disponibles
                language_code = context.get("language_code") if context else None
                result = await self.get_available_voices(language_code)
            else:
                # Si no hay datos de audio ni texto, devolver error
                if not audio_data and not text:
                    return {
                        "success": False,
                        "error": "No se proporcionaron datos de audio ni texto para procesar",
                        "agent": self.__class__.__name__,
                        "timestamp": datetime.now().isoformat()
                    }
                # Procesamiento por defecto
                if audio_data:
                    result = await self.process_voice_command(audio_data, context)
                else:
                    audio_data, metadata = await self.generate_voice_response(text, context)
                    result = {
                        "audio_data": audio_data,
                        "metadata": metadata,
                        "text": text
                    }
            
            return {
                "success": True,
                "output": result.get("text", "Procesamiento de voz completado"),
                "query_type": query_type,
                "result": result,
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error al procesar consulta de voz: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para VoiceAdapter.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "transcribir": "voice_to_text",
            "reconocer": "voice_to_text",
            "convertir voz": "voice_to_text",
            "hablar": "text_to_voice",
            "sintetizar": "text_to_voice",
            "generar voz": "text_to_voice",
            "emociones": "emotion_analysis",
            "sentimiento": "emotion_analysis",
            "analizar voz": "emotion_analysis",
            "conversar": "conversation",
            "diálogo": "conversation",
            "voces": "get_voices",
            "listar voces": "get_voices"
        }

# Instancia global
voice_adapter = VoiceAdapter()

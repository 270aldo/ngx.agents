"""
Cliente específico para capacidades de procesamiento de voz de Vertex AI.

Este módulo proporciona un cliente especializado para interactuar con las APIs
de procesamiento de voz de Vertex AI, permitiendo realizar transcripción de audio,
síntesis de voz y análisis de audio.
"""
import logging
import base64
import os
import json
import asyncio
import time
from typing import Dict, Any, Optional, Union, List
import aiohttp
from google.cloud import aiplatform
from google.cloud.aiplatform import VertexAI
from core.logging_config import get_logger
from core.telemetry import Telemetry

# Configurar logger
logger = get_logger(__name__)

class VertexAISpeechClient:
    """
    Cliente para interactuar con las APIs de procesamiento de voz de Vertex AI.
    
    Proporciona métodos para realizar transcripción de audio, síntesis de voz
    y análisis de audio utilizando los modelos de Vertex AI.
    """
    
    def __init__(self, model: str = "chirp", telemetry: Optional[Telemetry] = None):
        """
        Inicializa el cliente de procesamiento de voz de Vertex AI.
        
        Args:
            model: Modelo de Vertex AI a utilizar para el procesamiento de voz
            telemetry: Instancia de Telemetry para métricas y trazas (opcional)
        """
        self.model = model
        self.telemetry = telemetry
        self.vertex_ai_initialized = False
        
        # Inicializar Vertex AI
        try:
            gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
            gcp_region = os.getenv("GCP_REGION", "us-central1")
            
            logger.info(f"Inicializando Vertex AI para VertexAISpeechClient con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            self.vertex_ai_initialized = True
            logger.info("Vertex AI inicializado correctamente para VertexAISpeechClient")
        except Exception as e:
            logger.error(f"Error al inicializar Vertex AI para VertexAISpeechClient: {e}", exc_info=True)
    
    async def transcribe_audio(self, audio_data: Union[str, Dict[str, Any]], 
                             language_code: str = "es-ES") -> Dict[str, Any]:
        """
        Transcribe audio a texto utilizando Vertex AI.
        
        Args:
            audio_data: Datos del audio (base64, URL o ruta de archivo)
            language_code: Código de idioma para la transcripción
            
        Returns:
            Dict[str, Any]: Resultados de la transcripción
        """
        # Iniciar telemetría si está disponible
        span = None
        start_time = time.time()
        
        if self.telemetry:
            span = self.telemetry.start_span("vertex_ai_speech_transcribe")
            self.telemetry.add_span_attribute(span, "model", self.model)
            self.telemetry.add_span_attribute(span, "language_code", language_code)
        
        try:
            # Procesar el audio según el formato proporcionado
            processed_audio = await self._process_audio_input(audio_data)
            
            # Llamar a Vertex AI para la transcripción
            if self.vertex_ai_initialized:
                # Usar el cliente de Vertex AI
                vertex_ai = VertexAI(project=os.getenv("GCP_PROJECT_ID", "your-gcp-project-id"))
                
                # Configurar el modelo
                config = {
                    "language_codes": [language_code],
                    "model": self.model
                }
                
                # Crear la solicitud
                request = {
                    "audio": {
                        "content": processed_audio
                    },
                    "config": config
                }
                
                # Enviar la solicitud
                response = await vertex_ai.speech.transcribe_async(**request)
                
                # Procesar la respuesta
                result = {
                    "text": response.results[0].alternatives[0].transcript if response.results else "",
                    "confidence": response.results[0].alternatives[0].confidence if response.results else 0.0,
                    "language_code": language_code,
                    "model": self.model,
                    "status": "success"
                }
                
                # Añadir alternativas si existen
                if response.results and len(response.results[0].alternatives) > 1:
                    result["alternatives"] = [
                        {
                            "text": alt.transcript,
                            "confidence": alt.confidence
                        }
                        for alt in response.results[0].alternatives[1:]
                    ]
            else:
                # Simulación para desarrollo/pruebas
                logger.warning("Vertex AI no inicializado. Usando transcripción simulada.")
                result = {
                    "text": "Texto simulado transcrito del audio. Vertex AI no está inicializado correctamente.",
                    "confidence": 0.8,
                    "language_code": language_code,
                    "model": "simulado",
                    "status": "simulated"
                }
            
            # Calcular duración
            duration = time.time() - start_time
            
            # Registrar en telemetría si está disponible
            if self.telemetry and span:
                self.telemetry.add_span_attribute(span, "duration", duration)
                self.telemetry.add_span_attribute(span, "status", "success")
                self.telemetry.end_span(span)
                
                # Registrar métricas
                self.telemetry.record_metric("vertex_ai_speech_transcribe_duration", duration)
                self.telemetry.record_metric("vertex_ai_speech_transcribe_count", 1)
            
            return result
        except Exception as e:
            logger.error(f"Error al transcribir audio: {e}", exc_info=True)
            
            # Registrar error en telemetría si está disponible
            if self.telemetry and span:
                self.telemetry.record_exception(span, e)
                self.telemetry.add_span_attribute(span, "status", "error")
                self.telemetry.end_span(span)
                
                # Registrar métricas de error
                self.telemetry.record_metric("vertex_ai_speech_transcribe_error_count", 1)
            
            return {
                "text": f"Error al transcribir audio: {str(e)}",
                "model": self.model,
                "status": "error",
                "error": str(e)
            }
    
    async def synthesize_speech(self, text: str, voice_name: str = "es-ES-Standard-A", 
                              language_code: str = "es-ES") -> Dict[str, Any]:
        """
        Sintetiza texto a voz utilizando Vertex AI.
        
        Args:
            text: Texto a sintetizar
            voice_name: Nombre de la voz a utilizar
            language_code: Código de idioma para la síntesis
            
        Returns:
            Dict[str, Any]: Resultados de la síntesis, incluyendo audio en base64
        """
        # Iniciar telemetría si está disponible
        span = None
        start_time = time.time()
        
        if self.telemetry:
            span = self.telemetry.start_span("vertex_ai_speech_synthesize")
            self.telemetry.add_span_attribute(span, "voice_name", voice_name)
            self.telemetry.add_span_attribute(span, "language_code", language_code)
            self.telemetry.add_span_attribute(span, "text_length", len(text))
        
        try:
            # Llamar a Vertex AI para la síntesis
            if self.vertex_ai_initialized:
                # Usar el cliente de Vertex AI
                vertex_ai = VertexAI(project=os.getenv("GCP_PROJECT_ID", "your-gcp-project-id"))
                
                # Configurar la solicitud
                request = {
                    "input": {
                        "text": text
                    },
                    "voice": {
                        "language_code": language_code,
                        "name": voice_name
                    },
                    "audio_config": {
                        "audio_encoding": "MP3"
                    }
                }
                
                # Enviar la solicitud
                response = await vertex_ai.text_to_speech.synthesize_async(**request)
                
                # Procesar la respuesta
                result = {
                    "audio_base64": base64.b64encode(response.audio_content).decode("utf-8"),
                    "audio_format": "mp3",
                    "voice_name": voice_name,
                    "language_code": language_code,
                    "text_length": len(text),
                    "status": "success"
                }
            else:
                # Simulación para desarrollo/pruebas
                logger.warning("Vertex AI no inicializado. Usando síntesis simulada.")
                result = {
                    "audio_base64": "",  # Audio vacío simulado
                    "audio_format": "mp3",
                    "voice_name": voice_name,
                    "language_code": language_code,
                    "text_length": len(text),
                    "status": "simulated"
                }
            
            # Calcular duración
            duration = time.time() - start_time
            
            # Registrar en telemetría si está disponible
            if self.telemetry and span:
                self.telemetry.add_span_attribute(span, "duration", duration)
                self.telemetry.add_span_attribute(span, "status", "success")
                self.telemetry.end_span(span)
                
                # Registrar métricas
                self.telemetry.record_metric("vertex_ai_speech_synthesize_duration", duration)
                self.telemetry.record_metric("vertex_ai_speech_synthesize_count", 1)
            
            return result
        except Exception as e:
            logger.error(f"Error al sintetizar voz: {e}", exc_info=True)
            
            # Registrar error en telemetría si está disponible
            if self.telemetry and span:
                self.telemetry.record_exception(span, e)
                self.telemetry.add_span_attribute(span, "status", "error")
                self.telemetry.end_span(span)
                
                # Registrar métricas de error
                self.telemetry.record_metric("vertex_ai_speech_synthesize_error_count", 1)
            
            return {
                "error": str(e),
                "status": "error"
            }
    
    async def analyze_audio(self, audio_data: Union[str, Dict[str, Any]], 
                          analysis_type: str = "emotion",
                          language_code: str = "es-ES") -> Dict[str, Any]:
        """
        Analiza audio para detectar emociones, intenciones u otras características.
        
        Args:
            audio_data: Datos del audio (base64, URL o ruta de archivo)
            analysis_type: Tipo de análisis (emotion, intent, speaker_diarization)
            language_code: Código de idioma para el análisis
            
        Returns:
            Dict[str, Any]: Resultados del análisis
        """
        # Iniciar telemetría si está disponible
        span = None
        start_time = time.time()
        
        if self.telemetry:
            span = self.telemetry.start_span("vertex_ai_speech_analyze")
            self.telemetry.add_span_attribute(span, "analysis_type", analysis_type)
            self.telemetry.add_span_attribute(span, "language_code", language_code)
        
        try:
            # Procesar el audio según el formato proporcionado
            processed_audio = await self._process_audio_input(audio_data)
            
            # Llamar a Vertex AI para el análisis
            if self.vertex_ai_initialized:
                # Usar el cliente de Vertex AI
                vertex_ai = VertexAI(project=os.getenv("GCP_PROJECT_ID", "your-gcp-project-id"))
                
                # Configurar el modelo según el tipo de análisis
                if analysis_type == "emotion":
                    # Análisis de emociones
                    prompt = """
                    Analiza el audio y determina la emoción predominante del hablante.
                    Clasifica la emoción en una de las siguientes categorías:
                    - Alegría
                    - Tristeza
                    - Enojo
                    - Miedo
                    - Sorpresa
                    - Neutral
                    
                    Proporciona también una puntuación de confianza para cada emoción.
                    """
                elif analysis_type == "intent":
                    # Análisis de intenciones
                    prompt = """
                    Analiza el audio y determina la intención del hablante.
                    Clasifica la intención en una de las siguientes categorías:
                    - Pregunta
                    - Solicitud
                    - Afirmación
                    - Negación
                    - Saludo
                    - Despedida
                    - Otro
                    
                    Proporciona también una puntuación de confianza para cada intención.
                    """
                elif analysis_type == "speaker_diarization":
                    # Diarización de hablantes
                    prompt = """
                    Analiza el audio e identifica los diferentes hablantes.
                    Para cada segmento de audio, indica:
                    - ID del hablante
                    - Tiempo de inicio
                    - Tiempo de fin
                    - Texto transcrito
                    """
                else:
                    # Análisis genérico
                    prompt = f"Analiza el audio y proporciona información detallada sobre {analysis_type}."
                
                # Primero transcribir el audio
                transcription_result = await self.transcribe_audio(audio_data, language_code)
                
                if transcription_result["status"] != "success":
                    return {
                        "error": f"Error en la transcripción previa al análisis: {transcription_result.get('error', 'Unknown error')}",
                        "status": "error"
                    }
                
                # Ahora analizar el texto transcrito con Gemini
                config = {
                    "max_output_tokens": 1024,
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "top_k": 40
                }
                
                # Crear la solicitud
                request = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": f"{prompt}\n\nTranscripción del audio: {transcription_result['text']}"}
                            ]
                        }
                    ],
                    "generation_config": config
                }
                
                # Enviar la solicitud
                response = await vertex_ai.generate_content_async(**request)
                
                # Procesar la respuesta
                analysis_text = response.text if hasattr(response, 'text') else str(response)
                
                # Intentar estructurar la respuesta
                structured_analysis = await self._structure_analysis_response(analysis_text, analysis_type)
                
                result = {
                    "transcription": transcription_result["text"],
                    "analysis_type": analysis_type,
                    "analysis": structured_analysis,
                    "raw_analysis": analysis_text,
                    "language_code": language_code,
                    "model": self.model,
                    "status": "success"
                }
            else:
                # Simulación para desarrollo/pruebas
                logger.warning("Vertex AI no inicializado. Usando análisis de audio simulado.")
                result = {
                    "transcription": "Texto simulado transcrito del audio.",
                    "analysis_type": analysis_type,
                    "analysis": {
                        "result": "Análisis simulado. Vertex AI no está inicializado correctamente."
                    },
                    "language_code": language_code,
                    "model": "simulado",
                    "status": "simulated"
                }
            
            # Calcular duración
            duration = time.time() - start_time
            
            # Registrar en telemetría si está disponible
            if self.telemetry and span:
                self.telemetry.add_span_attribute(span, "duration", duration)
                self.telemetry.add_span_attribute(span, "status", "success")
                self.telemetry.end_span(span)
                
                # Registrar métricas
                self.telemetry.record_metric("vertex_ai_speech_analyze_duration", duration)
                self.telemetry.record_metric("vertex_ai_speech_analyze_count", 1)
            
            return result
        except Exception as e:
            logger.error(f"Error al analizar audio: {e}", exc_info=True)
            
            # Registrar error en telemetría si está disponible
            if self.telemetry and span:
                self.telemetry.record_exception(span, e)
                self.telemetry.add_span_attribute(span, "status", "error")
                self.telemetry.end_span(span)
                
                # Registrar métricas de error
                self.telemetry.record_metric("vertex_ai_speech_analyze_error_count", 1)
            
            return {
                "error": str(e),
                "status": "error"
            }
    
    async def _process_audio_input(self, audio_data: Union[str, Dict[str, Any]]) -> str:
        """
        Procesa los datos de entrada del audio en el formato requerido por Vertex AI.
        
        Args:
            audio_data: Datos del audio (base64, URL o ruta de archivo)
            
        Returns:
            str: Datos del audio en formato base64
        """
        # Si ya es un diccionario con formato específico
        if isinstance(audio_data, dict):
            if "base64" in audio_data:
                return audio_data["base64"]
            elif "url" in audio_data:
                # Descargar audio desde URL
                return await self._download_audio(audio_data["url"])
            elif "path" in audio_data:
                # Leer audio desde archivo
                return await self._read_audio_file(audio_data["path"])
        
        # Si es un string, podría ser base64, URL o ruta
        elif isinstance(audio_data, str):
            # Verificar si es base64
            if audio_data.startswith("data:audio"):
                # Extraer la parte base64 del data URI
                return audio_data.split(",")[1]
            elif audio_data.startswith("http"):
                # Es una URL
                return await self._download_audio(audio_data)
            else:
                # Asumir que es una ruta de archivo
                return await self._read_audio_file(audio_data)
        
        # Si no se pudo procesar, devolver error
        raise ValueError("Formato de audio no soportado")
    
    async def _download_audio(self, url: str) -> str:
        """
        Descarga un audio desde una URL y lo convierte a base64.
        
        Args:
            url: URL del audio
            
        Returns:
            str: Audio en formato base64
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        return base64.b64encode(audio_data).decode("utf-8")
                    else:
                        raise Exception(f"Error al descargar audio: {response.status}")
        except Exception as e:
            logger.error(f"Error al descargar audio desde URL: {e}", exc_info=True)
            raise
    
    async def _read_audio_file(self, path: str) -> str:
        """
        Lee un audio desde un archivo y lo convierte a base64.
        
        Args:
            path: Ruta del archivo de audio
            
        Returns:
            str: Audio en formato base64
        """
        try:
            with open(path, "rb") as audio_file:
                audio_data = audio_file.read()
                return base64.b64encode(audio_data).decode("utf-8")
        except Exception as e:
            logger.error(f"Error al leer audio desde archivo: {e}", exc_info=True)
            raise
    
    async def _structure_analysis_response(self, analysis_text: str, analysis_type: str) -> Dict[str, Any]:
        """
        Intenta estructurar la respuesta de análisis en un formato más útil.
        
        Args:
            analysis_text: Texto del análisis
            analysis_type: Tipo de análisis
            
        Returns:
            Dict[str, Any]: Análisis estructurado
        """
        try:
            # Intentar extraer JSON si existe
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass
            
            # Estructurar según el tipo de análisis
            if analysis_type == "emotion":
                # Buscar emociones y puntuaciones
                emotions = {
                    "alegría": 0.0,
                    "tristeza": 0.0,
                    "enojo": 0.0,
                    "miedo": 0.0,
                    "sorpresa": 0.0,
                    "neutral": 0.0
                }
                
                # Buscar la emoción predominante
                emotion_match = re.search(r'predominante.*?es\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ]+)', analysis_text, re.IGNORECASE)
                predominant = emotion_match.group(1).lower() if emotion_match else "neutral"
                
                # Buscar puntuaciones
                for emotion in emotions.keys():
                    score_match = re.search(f'{emotion}[:\s]+([0-9.]+)', analysis_text, re.IGNORECASE)
                    if score_match:
                        try:
                            emotions[emotion] = float(score_match.group(1))
                        except:
                            pass
                
                return {
                    "predominant": predominant,
                    "scores": emotions
                }
                
            elif analysis_type == "intent":
                # Buscar intenciones y puntuaciones
                intents = {
                    "pregunta": 0.0,
                    "solicitud": 0.0,
                    "afirmación": 0.0,
                    "negación": 0.0,
                    "saludo": 0.0,
                    "despedida": 0.0,
                    "otro": 0.0
                }
                
                # Buscar la intención predominante
                intent_match = re.search(r'intención.*?es\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ]+)', analysis_text, re.IGNORECASE)
                predominant = intent_match.group(1).lower() if intent_match else "otro"
                
                # Buscar puntuaciones
                for intent in intents.keys():
                    score_match = re.search(f'{intent}[:\s]+([0-9.]+)', analysis_text, re.IGNORECASE)
                    if score_match:
                        try:
                            intents[intent] = float(score_match.group(1))
                        except:
                            pass
                
                return {
                    "predominant": predominant,
                    "scores": intents
                }
                
            elif analysis_type == "speaker_diarization":
                # Buscar segmentos de hablantes
                segments = []
                
                # Buscar patrones como "Hablante 1: [00:01:23 - 00:01:45] Texto transcrito"
                segment_matches = re.finditer(r'Hablante\s+(\d+):\s+\[([0-9:]+)\s*-\s*([0-9:]+)\]\s+(.*?)(?=Hablante\s+\d+:|$)', 
                                             analysis_text, re.DOTALL)
                
                for match in segment_matches:
                    segments.append({
                        "speaker_id": match.group(1),
                        "start_time": match.group(2),
                        "end_time": match.group(3),
                        "text": match.group(4).strip()
                    })
                
                return {
                    "segments": segments
                }
            
            # Si no se pudo estructurar, devolver el texto como está
            return {
                "text": analysis_text
            }
            
        except Exception as e:
            logger.error(f"Error al estructurar respuesta de análisis: {e}", exc_info=True)
            return {
                "text": analysis_text,
                "error": str(e)
            }


# Instancia global del cliente
speech_client = VertexAISpeechClient()

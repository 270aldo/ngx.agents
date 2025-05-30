\
"""
Cliente para interactuar con la API de Gemini de Google.

Este cliente implementa el patrón Singleton para asegurar una única instancia
y proporciona métodos para generar respuestas, analizar intenciones y más.
"""
import logging
import os
import base64
import mimetypes
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, BinaryIO, Tuple

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from clients.base_client import BaseClient, retry_with_backoff
from config.secrets import settings
from core.budget import budget_manager
from core.prompt_analyzer import prompt_analyzer
from core.domain_cache import domain_cache, CacheStrategy

logger = logging.getLogger(__name__)


class GeminiClient(BaseClient):
    """
    Cliente para la API de Gemini con patrón Singleton.
    
    Proporciona métodos para generar texto, analizar intenciones y otras
    tareas de procesamiento de lenguaje natural.
    """
    
    # Instancia única (patrón Singleton)
    _instance = None
    
    def __new__(cls, *args: Any, **kwargs: Any) -> "GeminiClient":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(GeminiClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self,
                model_name: str = "gemini-1.5-pro",
                optimize_prompts: bool = True,
                use_cache: bool = True,
                cache_ttl: Optional[int] = 3600 * 24):  # 24 horas por defecto
        """
        Inicializa el cliente de Gemini.
        
        Args:
            model_name: Nombre del modelo de Gemini a utilizar
            optimize_prompts: Si se deben optimizar los prompts para reducir tokens
            use_cache: Si se debe utilizar el sistema de caché
            cache_ttl: Tiempo de vida de las entradas en caché (en segundos)
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return
            
        super().__init__(service_name="gemini")
        self.model_name = model_name
        self.model = None
        self.optimize_prompts = optimize_prompts
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self._initialized = True
    
    async def initialize(self) -> None:
        """
        Inicializa la conexión con la API de Gemini.
        
        Configura la API key y prepara el modelo para su uso.
        """
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno")
        
        # Configurar la API key
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Inicializar el modelo
        self.model = genai.GenerativeModel(self.model_name)
        logger.info(f"Cliente Gemini inicializado con modelo {self.model_name}")
    
    @retry_with_backoff()
    async def generate_text(
        self, 
        prompt: str, 
        temperature: float = 0.7, 
        max_output_tokens: int = 1024,
        top_p: float = 0.95,
        top_k: int = 40,
        safety_settings: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Genera texto a partir de un prompt utilizando Gemini.
        
        Args:
            prompt: Texto de entrada para generar la respuesta
            temperature: Control de aleatoriedad (0.0-1.0)
            max_output_tokens: Longitud máxima de la respuesta
            top_p: Parámetro de nucleus sampling
            top_k: Parámetro de top-k sampling
            safety_settings: Configuración de filtros de seguridad
            
        Returns:
            Texto generado por el modelo
        """
        if not self.model:
            await self.initialize()
        
        self._record_call("generate_text")
        
        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            top_p=top_p,
            top_k=top_k
        )
        
        try:
            # Verificar caché primero si está habilitado
            agent_id = getattr(self, "current_agent_id", "default")
            cache_domain = f"gemini:{agent_id}"
            
            if self.use_cache:
                cached_result = await domain_cache.get(
                    prompt=prompt,
                    domain=cache_domain,
                    strategy=CacheStrategy.EXACT_MATCH
                )
                
                if cached_result is not None:
                    logger.info(f"Resultado obtenido de caché para agente {agent_id}")
                    return cached_result
            
            # Optimizar prompt si está habilitado
            original_prompt = prompt
            if self.optimize_prompts:
                analysis = prompt_analyzer.analyze_prompt(prompt)
                prompt = analysis["optimized_prompt"]
                if analysis["token_reduction"] > 0:
                    logger.info(f"Prompt optimizado: {analysis['token_reduction']} tokens reducidos ({analysis['percentage_reduction']:.1f}%)")
            
            # Estimar tokens de entrada (aproximado)
            prompt_tokens = self._estimate_tokens(prompt)
            
            # Verificar presupuesto antes de la llamada
            allowed, fallback_model = await budget_manager.record_usage(
                agent_id=agent_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=0,  # Se actualizará después
                model=self.model_name
            )
            
            if not allowed:
                logger.warning(f"Llamada bloqueada por límite de presupuesto para agente {agent_id}")
                return "Lo siento, no puedo procesar esta solicitud debido a restricciones de presupuesto."
            
            # Si se debe degradar a un modelo más económico
            if fallback_model:
                logger.info(f"Cambiando de {self.model_name} a {fallback_model} por restricciones de presupuesto")
                original_model = self.model
                self.model = genai.GenerativeModel(fallback_model)
                
                response = await self.model.generate_content_async(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # Restaurar modelo original para futuras llamadas
                self.model = original_model
            else:
                response = await self.model.generate_content_async(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            
            # Estimar tokens de salida y actualizar presupuesto
            completion_tokens = self._estimate_tokens(response.text)
            await budget_manager.record_usage(
                agent_id=agent_id,
                prompt_tokens=0,  # Ya contabilizados antes
                completion_tokens=completion_tokens,
                model=self.model_name
            )
            
            result_text = response.text
            
            # Guardar en caché si está habilitado
            if self.use_cache:
                await domain_cache.set(
                    prompt=original_prompt,  # Usar el prompt original como clave
                    value=result_text,
                    domain=cache_domain,
                    ttl=self.cache_ttl,
                    strategy=CacheStrategy.EXACT_MATCH,
                    metadata={
                        "model": self.model_name,
                        "agent_id": agent_id,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens
                    }
                )
            
            return result_text
        except Exception as e:
            logger.error(f"Error al generar texto con Gemini: {str(e)}")
            raise
    
    @retry_with_backoff()
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_output_tokens: int = 1024
    ) -> str:
        """
        Mantiene una conversación con el modelo.
        
        Args:
            messages: Lista de mensajes en formato [{"role": "user|model", "content": "texto"}]
            temperature: Control de aleatoriedad (0.0-1.0)
            max_output_tokens: Longitud máxima de la respuesta
            
        Returns:
            Respuesta del modelo a la conversación
        """
        if not self.model:
            await self.initialize()
        
        self._record_call("chat")
        
        # Verificar caché primero si está habilitado
        agent_id = getattr(self, "current_agent_id", "default")
        cache_domain = f"gemini_chat:{agent_id}"
        
        # Crear una clave de caché basada en los mensajes
        import json
        cache_key = json.dumps([{
            "role": msg.get("role", ""),
            "content": msg.get("content", "")
        } for msg in messages], sort_keys=True)
        
        if self.use_cache:
            cached_result = await domain_cache.get(
                prompt=cache_key,
                domain=cache_domain,
                strategy=CacheStrategy.EXACT_MATCH
            )
            
            if cached_result is not None:
                logger.info(f"Resultado de chat obtenido de caché para agente {agent_id}")
                return cached_result
        
        # Optimizar mensajes si está habilitado
        original_messages = messages.copy()
        if self.optimize_prompts:
            messages = prompt_analyzer.optimize_chat_messages(messages)
            # Calcular reducción de tokens
            original_tokens = sum(self._estimate_tokens(msg.get("content", "")) for msg in original_messages)
            optimized_tokens = sum(self._estimate_tokens(msg.get("content", "")) for msg in messages)
            token_reduction = original_tokens - optimized_tokens
            if token_reduction > 0:
                percentage_reduction = (token_reduction / original_tokens) * 100 if original_tokens > 0 else 0
                logger.info(f"Mensajes de chat optimizados: {token_reduction} tokens reducidos ({percentage_reduction:.1f}%)")
        
        # Estimar tokens de entrada (aproximado)
        prompt_tokens = sum(self._estimate_tokens(msg.get("content", "")) for msg in messages)
        
        # Verificar presupuesto antes de la llamada
        agent_id = getattr(self, "current_agent_id", "default")
        allowed, fallback_model = await budget_manager.record_usage(
            agent_id=agent_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=0,  # Se actualizará después
            model=self.model_name
        )
        
        if not allowed:
            logger.warning(f"Llamada de chat bloqueada por límite de presupuesto para agente {agent_id}")
            return "Lo siento, no puedo procesar esta solicitud debido a restricciones de presupuesto."
        
        # Si se debe degradar a un modelo más económico
        if fallback_model:
            logger.info(f"Cambiando de {self.model_name} a {fallback_model} por restricciones de presupuesto")
            original_model = self.model
            self.model = genai.GenerativeModel(fallback_model)
            
            chat = self.model.start_chat(history=[])
            
            # Agregar mensajes previos al historial
            for msg in messages[:-1]:
                if msg["role"] == "user":
                    chat.send_message(msg["content"])
                # Los mensajes del modelo se agregan automáticamente
            
            # Enviar el último mensaje y obtener respuesta
            response = await chat.send_message_async(messages[-1]["content"])
            
            # Restaurar modelo original para futuras llamadas
            self.model = original_model
        else:
            chat = self.model.start_chat(history=[])
            
            # Agregar mensajes previos al historial
            for msg in messages[:-1]:
                if msg["role"] == "user":
                    chat.send_message(msg["content"])
                # Los mensajes del modelo se agregan automáticamente
            
            # Enviar el último mensaje y obtener respuesta
            response = await chat.send_message_async(messages[-1]["content"])
        
        # Estimar tokens de salida y actualizar presupuesto
        completion_tokens = self._estimate_tokens(response.text)
        await budget_manager.record_usage(
            agent_id=agent_id,
            prompt_tokens=0,  # Ya contabilizados antes
            completion_tokens=completion_tokens,
            model=self.model_name
        )
        
        result_text = response.text
        
        # Guardar en caché si está habilitado
        if self.use_cache:
            await domain_cache.set(
                prompt=cache_key,
                value=result_text,
                domain=cache_domain,
                ttl=self.cache_ttl,
                strategy=CacheStrategy.EXACT_MATCH,
                metadata={
                    "model": self.model_name,
                    "agent_id": agent_id,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "message_count": len(messages)
                }
            )
        
        return result_text
    
    @retry_with_backoff()
    async def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Analiza la intención del usuario para determinar qué agentes deben responder.
        
        Args:
            user_input: Texto del usuario a analizar
            
        Returns:
            Diccionario con agentes recomendados y nivel de confianza
        """
        self._record_call("analyze_intent")
        
        prompt = f"""
        Analiza la siguiente entrada de usuario y determina qué agentes deberían responder.
        Devuelve un JSON con la siguiente estructura:
        {{
          "agents": [lista de IDs de agentes],
          "confidence": float entre 0 y 1,
          "intent": "categoría de la intención"
        }}
        
        Entrada del usuario: {user_input}
        """
        
        response = await self.generate_text(prompt, temperature=0.1)
        
        try:
            import json
            result = json.loads(response)
            return result
        except Exception as e:
            logger.error(f"Error al parsear la respuesta de análisis de intención: {str(e)}")
            return {"agents": [], "confidence": 0.0, "intent": "unknown"}
    
    @retry_with_backoff()
    async def summarize(self, text: str, max_words: int = 100) -> str:
        """
        Genera un resumen conciso de un texto.
        
        Args:
            text: Texto a resumir
            max_words: Longitud máxima aproximada del resumen en palabras
            
        Returns:
            Resumen del texto
        """
        self._record_call("summarize")
        
        prompt = f"""
        Resume el siguiente texto en aproximadamente {max_words} palabras,
        manteniendo los puntos clave y la información más relevante:
        
        {text}
        """
        
        return await self.generate_text(prompt, temperature=0.3, max_output_tokens=max_words * 5)

    @retry_with_backoff()
    async def analyze_image(self, image_data: Union[str, bytes, BinaryIO], prompt: str) -> str:
        """
        Analiza una imagen y genera una respuesta basada en el prompt.
        
        Args:
            image_data: Puede ser una ruta de archivo, bytes de imagen o un archivo abierto
            prompt: Instrucción sobre qué analizar en la imagen
            
        Returns:
            Texto generado con el análisis de la imagen
        """
        if not self.model:
            await self.initialize()
        
        self._record_call("analyze_image")
        
        # Preparar la imagen para la API
        if isinstance(image_data, str):
            # Es una ruta de archivo
            image_path = Path(image_data)
            if not image_path.exists():
                raise FileNotFoundError(f"No se encontró la imagen en {image_data}")
                
            with open(image_data, "rb") as img_file:
                image_bytes = img_file.read()
                
        elif isinstance(image_data, bytes):
            # Son bytes directamente
            image_bytes = image_data
        else:
            # Es un archivo abierto
            image_bytes = image_data.read()
        
        # Crear contenido multimodal para la API
        # En la versión 0.8.5, usamos directamente el método generate_content
        try:
            # Convertir imagen a base64
            image_parts = [
                {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()},
                {"text": prompt}
            ]
            
            response = await self.model.generate_content_async(image_parts)
            return response.text
        except Exception as e:
            logger.error(f"Error al analizar imagen con Gemini: {str(e)}")
            raise
    
    @retry_with_backoff()
    async def analyze_pdf(self, pdf_path: str, prompt: str, max_pages: int = 5) -> str:
        """
        Analiza un documento PDF y genera una respuesta.
        
        Args:
            pdf_path: Ruta al archivo PDF
            prompt: Instrucción sobre qué analizar en el PDF
            max_pages: Número máximo de páginas a procesar
            
        Returns:
            Texto generado con el análisis del PDF
        """
        self._record_call("analyze_pdf")
        
        try:
            # Importar PyPDF2
            import PyPDF2
            
            # Abrir el PDF
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Limitar número de páginas
                num_pages = min(len(reader.pages), max_pages)
                
                # Extraer texto
                text = ""
                for i in range(num_pages):
                    page = reader.pages[i]
                    text += page.extract_text() + "\n\n"
                
                # Analizar el contenido del PDF con Gemini
                full_prompt = f"{prompt}\n\nContenido del PDF (primeras {num_pages} páginas):\n{text}"
                return await self.generate_text(full_prompt)
                
        except ImportError:
            logger.error("PyPDF2 no está instalado. Por favor, instálalo con: pip install PyPDF2")
            raise
        except Exception as e:
            logger.error(f"Error al analizar PDF con Gemini: {str(e)}")
            raise
    
    @retry_with_backoff()
    async def analyze_csv(self, csv_path: str, prompt: str, sample_rows: int = 5) -> str:
        """
        Analiza un archivo CSV y genera una respuesta.
        
        Args:
            csv_path: Ruta al archivo CSV
            prompt: Instrucción sobre qué analizar en el CSV
            sample_rows: Número de filas a incluir como muestra
            
        Returns:
            Texto generado con el análisis del CSV
        """
        self._record_call("analyze_csv")
        
        try:
            # Importar pandas
            import pandas as pd
            
            # Leer el CSV
            df = pd.read_csv(csv_path)
            
            # Obtener información básica del dataframe
            info = {
                "columnas": list(df.columns),
                "tipos_de_datos": {col: str(df[col].dtype) for col in df.columns},
                "filas_totales": len(df),
                "muestra": df.head(sample_rows).to_string()
            }
            
            # Analizar el contenido del CSV con Gemini
            full_prompt = f"{prompt}\n\nInformación del CSV:\n"
            full_prompt += f"Columnas: {info['columnas']}\n"
            full_prompt += f"Tipos de datos: {info['tipos_de_datos']}\n"
            full_prompt += f"Total de filas: {info['filas_totales']}\n"
            full_prompt += f"Muestra de datos:\n{info['muestra']}"
            
            return await self.generate_text(full_prompt)
                
        except ImportError:
            logger.error("Pandas no está instalado. Por favor, instálalo con: pip install pandas")
            raise
        except Exception as e:
            logger.error(f"Error al analizar CSV con Gemini: {str(e)}")
            raise

    @retry_with_backoff()
    async def analyze_sentiment(self, text: str, detailed: bool = False) -> Dict[str, Any]:
        """
        Analiza el sentimiento de un texto.
        
        Args:
            text: Texto a analizar
            detailed: Si es True, devuelve un análisis detallado con emociones
            
        Returns:
            Diccionario con el análisis de sentimiento
        """
        self._record_call("analyze_sentiment")
        
        prompt = f"""
        Realiza un análisis de sentimiento del siguiente texto y devuelve los resultados en formato JSON:
        
        {text}
        
        El JSON debe tener el siguiente formato:
        {{"sentiment": "positivo|negativo|neutral",
        "score": float entre -1.0 y 1.0,
        "confidence": float entre 0 y 1,
        "dominant_emotion": "emoción principal"
        }}
        """
        
        if detailed:
            prompt += """
            Además, incluye un campo "emotions" con un objeto que contenga las siguientes emociones y su puntuación (0-1):
            alegría, tristeza, enojo, miedo, sorpresa, asco, confianza, anticipación, calma.
            """
        
        response = await self.generate_text(prompt, temperature=0.1)
        
        try:
            # Extraer el JSON de la respuesta usando regex para mayor robustez
            import json
            json_match = re.search(r'({.*})', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # Fallback si no se encuentra una estructura JSON
                result = {
                    "sentiment": "neutral",
                    "score": 0.0,
                    "confidence": 0.0,
                    "dominant_emotion": "none"
                }
                
            return result
        except Exception as e:
            logger.error(f"Error al parsear resultados de análisis de sentimiento: {str(e)}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "dominant_emotion": "none",
                "error": str(e)
            }


    def set_current_agent(self, agent_id: str) -> None:
        """
        Establece el agente actual para el seguimiento de presupuesto.
        
        Args:
            agent_id: ID del agente que está realizando la llamada
        """
        self.current_agent_id = agent_id
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estima el número de tokens en un texto.
        
        Esta es una estimación aproximada basada en palabras y caracteres.
        Para una estimación más precisa, se debería usar un tokenizador real.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Número estimado de tokens
        """
        if not text:
            return 0
            
        # Estimación simple: aproximadamente 4 caracteres por token en promedio
        # Esta es una aproximación muy básica y puede variar según el modelo y el idioma
        char_count = len(text)
        estimated_tokens = max(1, char_count // 4)
        
        return estimated_tokens


# Instancia global para uso en toda la aplicación
gemini_client = GeminiClient()

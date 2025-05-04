"""
Cliente para interactuar con Vertex AI de Google Cloud.

Proporciona acceso a modelos de IA avanzados de Google Cloud,
incluyendo modelos de texto, imagen y multimodales.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part

from prototipo.clients.base_client import BaseClient, retry_with_backoff
from prototipo.config.secrets import settings

logger = logging.getLogger(__name__)


class VertexClient(BaseClient):
    """
    Cliente para Vertex AI con patrón Singleton.
    
    Proporciona métodos para acceder a modelos de IA avanzados
    de Google Cloud Platform.
    """
    
    # Instancia única (patrón Singleton)
    _instance = None
    
    def __new__(cls, *args: Any, **kwargs: Any) -> "VertexClient":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(VertexClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_name: str = "gemini-1.5-pro", region: str = "us-central1"):
        """
        Inicializa el cliente de Vertex AI.
        
        Args:
            model_name: Nombre del modelo a utilizar
            region: Región de Google Cloud donde se ejecutará el modelo
        """
        # Evitar reinicialización en el patrón Singleton
        if self._initialized:
            return
            
        super().__init__(service_name="vertex")
        self.model_name = model_name
        self.region = region
        self.model = None
        self._initialized = True
    
    async def initialize(self) -> None:
        """
        Inicializa la conexión con Vertex AI.
        
        Configura las credenciales y prepara el modelo para su uso.
        """
        if not settings.GOOGLE_APPLICATION_CREDENTIALS:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS no está configurada en las variables de entorno")
        
        # Inicializar SDK de Vertex AI
        # Esto utilizará las credenciales configuradas en GOOGLE_APPLICATION_CREDENTIALS
        project_id = settings.GOOGLE_CLOUD_PROJECT
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT no está configurado en las variables de entorno")
            
        aiplatform.init(project=project_id, location=self.region)
        
        # Inicializar el modelo generativo
        self.model = GenerativeModel(self.model_name)
        logger.info(f"Cliente Vertex AI inicializado con modelo {self.model_name} en región {self.region}")
    
    @retry_with_backoff()
    async def generate_content(
        self, 
        prompt: Union[str, List[Dict[str, Any]]], 
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
        top_p: float = 0.95,
        top_k: int = 40
    ) -> Dict[str, Any]:
        """
        Genera contenido utilizando el modelo de Vertex AI.
        
        Args:
            prompt: Texto o lista de partes (para contenido multimodal)
            temperature: Control de aleatoriedad (0.0-1.0)
            max_output_tokens: Longitud máxima de la respuesta
            top_p: Parámetro de nucleus sampling
            top_k: Parámetro de top-k sampling
            
        Returns:
            Diccionario con el contenido generado y metadatos
        """
        if not self.model:
            await self.initialize()
        
        self._record_call("generate_content")
        
        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            top_p=top_p,
            top_k=top_k
        )
        
        # Convertir prompt a formato adecuado si es texto simple
        content = prompt
        if isinstance(prompt, str):
            content = [{"text": prompt}]
            
        # Convertir a formato de Part si es necesario
        parts = []
        for item in content if isinstance(content, list) else [content]:
            if isinstance(item, dict):
                if "text" in item:
                    parts.append(Part.from_text(item["text"]))
                elif "image" in item:
                    # Asumimos que item["image"] es bytes o una URL
                    parts.append(Part.from_image(item["image"]))
            else:
                parts.append(Part.from_text(str(item)))
        
        # Ejecutar de forma asíncrona
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content(
                parts,
                generation_config=generation_config
            )
        )
        
        # Procesar y devolver la respuesta
        result = {
            "text": response.text,
            "candidates": []
        }
        
        # Extraer candidatos si están disponibles
        for candidate in getattr(response, "candidates", []):
            candidate_info = {"content": []}
            for part in getattr(candidate, "content", {}).parts:
                if hasattr(part, "text") and part.text:
                    candidate_info["content"].append({"text": part.text})
                # Se pueden añadir más tipos de contenido según sea necesario
            result["candidates"].append(candidate_info)
        
        return result
    
    @retry_with_backoff()
    async def analyze_document(self, document_content: str) -> Dict[str, Any]:
        """
        Analiza un documento para extraer información estructurada.
        
        Args:
            document_content: Contenido del documento a analizar
            
        Returns:
            Diccionario con la información extraída
        """
        self._record_call("analyze_document")
        
        prompt = f"""
        Analiza el siguiente documento y extrae la información clave en formato JSON.
        Incluye campos como título, autor, fecha, temas principales y un resumen.
        
        Documento:
        {document_content}
        """
        
        response = await self.generate_content(prompt, temperature=0.2)
        
        try:
            # Intentar extraer JSON de la respuesta
            text = response["text"]
            # Buscar el primer { y el último }
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
            return {"error": "No se pudo extraer JSON", "text": text}
        except Exception as e:
            logger.error(f"Error al parsear la respuesta del análisis de documento: {str(e)}")
            return {"error": str(e), "text": response.get("text", "")}
    
    @retry_with_backoff()
    async def classify_content(
        self, 
        content: str, 
        categories: List[str]
    ) -> Dict[str, float]:
        """
        Clasifica contenido en categorías predefinidas.
        
        Args:
            content: Texto a clasificar
            categories: Lista de categorías posibles
            
        Returns:
            Diccionario con puntuaciones para cada categoría
        """
        self._record_call("classify_content")
        
        categories_str = ", ".join([f'"{cat}"' for cat in categories])
        prompt = f"""
        Clasifica el siguiente contenido en las categorías: {categories_str}.
        Devuelve un JSON con las puntuaciones para cada categoría (valores entre 0 y 1).
        
        Contenido:
        {content}
        
        Formato de respuesta:
        {{
          "category1": score1,
          "category2": score2,
          ...
        }}
        """
        
        response = await self.generate_content(prompt, temperature=0.1)
        
        try:
            # Extraer JSON de la respuesta
            text = response["text"]
            # Buscar el primer { y el último }
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                result = json.loads(json_str)
                # Asegurarse de que todas las categorías estén presentes
                for cat in categories:
                    if cat not in result:
                        result[cat] = 0.0
                return result
            
            # Si no se pudo extraer JSON, devolver un diccionario vacío
            return {cat: 0.0 for cat in categories}
        except Exception as e:
            logger.error(f"Error al parsear la respuesta de clasificación: {str(e)}")
            return {cat: 0.0 for cat in categories}


# Instancia global para uso en toda la aplicación
vertex_client = VertexClient()

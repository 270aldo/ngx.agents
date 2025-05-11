"""
Adaptador para el cliente Vertex AI optimizado.

Este módulo proporciona un adaptador que mantiene la API del cliente Vertex AI
actual pero utiliza internamente el cliente optimizado. Esto facilita la migración
gradual sin romper el código existente.
"""

import asyncio
import logging
import warnings
from typing import Any, Dict, List, Optional, Union

# Importar cliente refactorizado
from clients.vertex_ai import vertex_ai_client as optimized_client

# Configurar logger
logger = logging.getLogger(__name__)

# Advertencia de deprecación
warnings.warn(
    "Este adaptador está en uso para facilitar la migración al cliente refactorizado. "
    "Se recomienda migrar directamente al cliente refactorizado en clients.vertex_ai.",
    DeprecationWarning,
    stacklevel=2
)


class VertexAIClientAdapter:
    """
    Adaptador para el cliente Vertex AI refactorizado.
    
    Mantiene la API del cliente anterior pero utiliza internamente el cliente refactorizado.
    Esto facilita la migración gradual sin romper el código existente.
    """
    
    _instance = None
    
    def __new__(cls):
        """Implementa patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(VertexAIClientAdapter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el adaptador si no está inicializado."""
        if not self._initialized:
            self._initialized = True
            self.is_initialized = False
            
            # Estadísticas
            self.stats = {
                "content_requests": 0,
                "embedding_requests": 0,
                "multimodal_requests": 0
            }
    
    async def initialize(self) -> bool:
        """
        Inicializa el cliente.
        
        Returns:
            bool: True si la inicialización fue exitosa
        """
        result = await optimized_client.initialize()
        self.is_initialized = result
        return result
    
    async def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Genera contenido de texto usando el modelo de lenguaje.
        
        Args:
            prompt: Prompt para el modelo
            system_instruction: Instrucción de sistema (opcional)
            temperature: Temperatura para la generación (0.0-1.0)
            max_output_tokens: Máximo de tokens a generar
            top_p: Parámetro top_p para muestreo
            top_k: Parámetro top_k para muestreo
            
        Returns:
            Dict[str, Any]: Respuesta generada
        """
        self.stats["content_requests"] += 1
        
        return await optimized_client.generate_content(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            top_p=top_p,
            top_k=top_k
        )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Genera un embedding para un texto.
        
        Args:
            text: Texto para generar embedding
            
        Returns:
            List[float]: Vector de embedding
        """
        self.stats["embedding_requests"] += 1
        
        response = await optimized_client.generate_embedding(text)
        
        # El cliente optimizado devuelve un diccionario, pero el cliente
        # original devuelve directamente el vector
        return response.get("embedding", [])
    
    async def batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples textos en un solo batch.
        
        Args:
            texts: Lista de textos para generar embeddings
            
        Returns:
            List[List[float]]: Lista de vectores de embedding
        """
        response = await optimized_client.batch_embeddings(texts)
        
        # El cliente optimizado devuelve un diccionario, pero el cliente
        # original devuelve directamente la lista de vectores
        return response.get("embeddings", [])
    
    async def process_multimodal(
        self,
        prompt: str,
        image_data: Union[str, bytes],
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Procesa contenido multimodal (texto + imagen).
        
        Args:
            prompt: Texto de prompt
            image_data: Datos de imagen (base64 o bytes)
            temperature: Temperatura para generación
            max_output_tokens: Máximo de tokens a generar
            
        Returns:
            Dict[str, Any]: Respuesta generada
        """
        self.stats["multimodal_requests"] += 1
        
        return await optimized_client.process_multimodal(
            prompt=prompt,
            image_data=image_data,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
    
    async def process_document(
        self,
        document_content: bytes,
        mime_type: str,
        processor_id: str = "general-processor"
    ) -> Dict[str, Any]:
        """
        Procesa un documento usando Document AI.
        
        Args:
            document_content: Contenido del documento en bytes
            mime_type: Tipo MIME del documento
            processor_id: ID del procesador de Document AI
            
        Returns:
            Dict[str, Any]: Resultado del procesamiento
        """
        return await optimized_client.process_document(
            document_content=document_content,
            mime_type=mime_type,
            processor_id=processor_id
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cliente.
        
        Returns:
            Dict[str, Any]: Estadísticas del cliente
        """
        # Combinar estadísticas locales con las del cliente refactorizado
        refactorized_stats = await optimized_client.get_stats()
        
        return {
            **self.stats,
            "refactorized": refactorized_stats
        }
    
    async def flush_cache(self) -> bool:
        """
        Limpia la caché del cliente.
        
        Returns:
            bool: True si se limpió correctamente
        """
        return await optimized_client.flush_cache()
    
    async def close(self) -> None:
        """Cierra el cliente y libera recursos."""
        await optimized_client.close()
        self.is_initialized = False


# Instancia global del adaptador
vertex_ai_client = VertexAIClientAdapter()

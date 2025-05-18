"""
Adaptador para el Gestor de Embeddings.

Este adaptador proporciona una interfaz simplificada para utilizar
el Gestor de Embeddings desde otros componentes del sistema.
"""

import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from core.embeddings_manager import embeddings_manager
from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.logging_config import get_logger

logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()

class EmbeddingAdapter(BaseAgentAdapter):
    """Adaptador para capacidades de embeddings."""
    
    _instance = None
    
    def __new__(cls):
        """Implementa patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(EmbeddingAdapter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el adaptador de embeddings."""
        super().__init__()
        if self._initialized:
            return
            
        self.embeddings_manager = embeddings_manager
        self._initialized = True
        
    async def generate_embedding(self, text: str, namespace: Optional[str] = None) -> List[float]:
        """
        Genera un embedding para el texto proporcionado.
        
        Args:
            text: Texto para generar el embedding
            namespace: Namespace opcional
            
        Returns:
            Lista de valores float que representan el embedding
        """
        return await self.embeddings_manager.generate_embedding(text, namespace)
        
    async def find_similar(self, query: str, namespace: Optional[str] = None, 
                         top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Encuentra textos similares a la consulta.
        
        Args:
            query: Texto de consulta
            namespace: Namespace para la búsqueda
            top_k: Número de resultados a retornar
            
        Returns:
            Lista de documentos similares con scores
        """
        return await self.embeddings_manager.search_similar(query, namespace, top_k)
        
    async def store_text(self, text: str, metadata: Optional[Dict[str, Any]] = None, 
                       namespace: Optional[str] = None) -> str:
        """
        Almacena un texto y su embedding.
        
        Args:
            text: Texto a almacenar
            metadata: Metadatos asociados
            namespace: Namespace para organización
            
        Returns:
            ID del documento almacenado
        """
        return await self.embeddings_manager.store_embedding(text, None, metadata, namespace)
    
    async def batch_generate_embeddings(self, texts: List[str], namespace: Optional[str] = None) -> List[List[float]]:
        """
        Genera embeddings para múltiples textos en batch.
        
        Args:
            texts: Lista de textos para generar embeddings
            namespace: Namespace opcional
            
        Returns:
            Lista de embeddings
        """
        return await self.embeddings_manager.batch_generate_embeddings(texts, namespace)
    
    async def cluster_texts(self, texts: List[str], n_clusters: int = 5, 
                          namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Agrupa textos en clusters basados en sus embeddings.
        
        Args:
            texts: Lista de textos a agrupar
            n_clusters: Número de clusters a crear
            namespace: Namespace opcional
            
        Returns:
            Diccionario con los resultados del clustering
        """
        # Generar embeddings para los textos
        embeddings = await self.batch_generate_embeddings(texts, namespace)
        
        # Realizar clustering
        labels = await self.embeddings_manager.cluster_embeddings(embeddings, n_clusters)
        
        # Organizar resultados por cluster
        clusters = {}
        for i, (text, label) in enumerate(zip(texts, labels)):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append({"text": text, "index": i})
        
        return {
            "clusters": clusters,
            "labels": labels,
            "n_clusters": len(clusters)
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del adaptador y gestor de embeddings.
        
        Returns:
            Dict[str, Any]: Estadísticas
        """
        return await self.embeddings_manager.get_stats()

    async def _process_query(self, query: str, user_id: str = None, session_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario relacionada con embeddings.
        
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
            
            # Generar embedding para la consulta
            embedding = await self.generate_embedding(query)
            
            # Buscar documentos similares
            similar_docs = await self.find_similar(query)
            
            return {
                "success": True,
                "output": f"Procesamiento de embeddings completado para consulta de tipo {query_type}",
                "query_type": query_type,
                "embedding_length": len(embedding) if embedding else 0,
                "similar_docs_count": len(similar_docs) if similar_docs else 0,
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error al procesar consulta de embeddings: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para EmbeddingAdapter.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "embed": "embedding_generation",
            "similar": "similarity_search",
            "store": "text_storage",
            "cluster": "text_clustering",
            "batch": "batch_processing",
            "stats": "statistics_retrieval"
        }

# Instancia global
embedding_adapter = EmbeddingAdapter()

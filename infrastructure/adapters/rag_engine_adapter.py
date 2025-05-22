"""
Adaptador para Vertex AI RAG Engine.

Este módulo proporciona un adaptador para integrar Vertex AI RAG Engine
con el resto del sistema, permitiendo consultas basadas en documentos.
"""

import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from clients.vertex_ai.rag_engine_client import RAGEngineClient
from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.logging_config import get_logger

logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()

class RAGEngineAdapter(BaseAgentAdapter):
    """Adaptador para capacidades de RAG Engine."""
    
    _instance = None
    
    def __new__(cls):
        """Implementa patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(RAGEngineAdapter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el adaptador de RAG Engine."""
        super().__init__()
        if self._initialized:
            return
            
        self.rag_client = RAGEngineClient()
        self._initialized = True
        
    async def upload_document(self, file_path: str, destination_blob_name: Optional[str] = None) -> str:
        """
        Sube un documento al bucket de Cloud Storage para RAG Engine.
        
        Args:
            file_path: Ruta local del archivo a subir
            destination_blob_name: Nombre del blob en Cloud Storage (opcional)
            
        Returns:
            str: URI del documento en Cloud Storage
        """
        return await self.rag_client.upload_document(file_path, destination_blob_name)
        
    async def create_corpus(self, corpus_name: str, document_uris: List[str]) -> str:
        """
        Crea un corpus para RAG Engine.
        
        Args:
            corpus_name: Nombre del corpus
            document_uris: Lista de URIs de documentos en Cloud Storage
            
        Returns:
            str: ID del corpus creado
        """
        return await self.rag_client.create_corpus(corpus_name, document_uris)
        
    async def create_rag_application(self, corpus_id: str, application_name: Optional[str] = None) -> str:
        """
        Crea una aplicación RAG.
        
        Args:
            corpus_id: ID del corpus a utilizar
            application_name: Nombre de la aplicación (opcional)
            
        Returns:
            str: ID de la aplicación RAG creada
        """
        return await self.rag_client.create_rag_application(corpus_id, application_name)
        
    async def query_rag(self, query: str, application_id: Optional[str] = None, 
                      top_k: int = 5, temperature: float = 0.2, 
                      max_output_tokens: int = 1024) -> Dict[str, Any]:
        """
        Consulta una aplicación RAG.
        
        Args:
            query: Consulta a realizar
            application_id: ID de la aplicación RAG (opcional)
            top_k: Número de fragmentos a recuperar
            temperature: Temperatura para la generación
            max_output_tokens: Número máximo de tokens de salida
            
        Returns:
            Dict: Resultado de la consulta
        """
        return await self.rag_client.query_rag(
            query=query,
            application_id=application_id,
            top_k=top_k,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del adaptador y cliente de RAG Engine.
        
        Returns:
            Dict[str, Any]: Estadísticas
        """
        return await self.rag_client.get_stats()

    async def _process_query(self, query: str, user_id: str = None, session_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario relacionada con RAG Engine.
        
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
            
            # Extraer parámetros de los kwargs
            application_id = kwargs.get('application_id')
            top_k = kwargs.get('top_k', 5)
            temperature = kwargs.get('temperature', 0.2)
            max_output_tokens = kwargs.get('max_output_tokens', 1024)
            file_path = kwargs.get('file_path')
            destination_blob_name = kwargs.get('destination_blob_name')
            corpus_name = kwargs.get('corpus_name')
            document_uris = kwargs.get('document_uris', [])
            corpus_id = kwargs.get('corpus_id')
            
            # Determinar la operación a realizar según el tipo de consulta
            result = None
            
            if query_type == "query_rag":
                # Consultar RAG Engine
                result = await self.query_rag(
                    query=query,
                    application_id=application_id,
                    top_k=top_k,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens
                )
                
                return {
                    "success": True,
                    "output": result.get("answer", ""),
                    "query_type": query_type,
                    "citations": result.get("citations", []),
                    "latency_ms": result.get("latency_ms", 0),
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif query_type == "upload_document" and file_path:
                # Subir documento
                uri = await self.upload_document(file_path, destination_blob_name)
                
                return {
                    "success": bool(uri),
                    "output": f"Documento subido a: {uri}" if uri else "Error al subir documento",
                    "query_type": query_type,
                    "document_uri": uri,
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif query_type == "create_corpus" and corpus_name and document_uris:
                # Crear corpus
                corpus_id = await self.create_corpus(corpus_name, document_uris)
                
                return {
                    "success": bool(corpus_id),
                    "output": f"Corpus creado con ID: {corpus_id}" if corpus_id else "Error al crear corpus",
                    "query_type": query_type,
                    "corpus_id": corpus_id,
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif query_type == "create_application" and corpus_id:
                # Crear aplicación RAG
                app_id = await self.create_rag_application(corpus_id, kwargs.get('application_name'))
                
                return {
                    "success": bool(app_id),
                    "output": f"Aplicación RAG creada con ID: {app_id}" if app_id else "Error al crear aplicación RAG",
                    "query_type": query_type,
                    "application_id": app_id,
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif query_type == "stats":
                # Obtener estadísticas
                stats = await self.get_stats()
                
                return {
                    "success": True,
                    "output": "Estadísticas de RAG Engine recuperadas",
                    "query_type": query_type,
                    "stats": stats,
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            else:
                # No se pudo determinar la operación a realizar
                return {
                    "success": False,
                    "error": "No se proporcionaron los parámetros necesarios para la operación solicitada",
                    "query_type": query_type,
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error al procesar consulta de RAG Engine: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para RAGEngineAdapter.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "consultar": "query_rag",
            "preguntar": "query_rag",
            "responder": "query_rag",
            "subir": "upload_document",
            "cargar": "upload_document",
            "documento": "upload_document",
            "crear_corpus": "create_corpus",
            "corpus": "create_corpus",
            "crear_aplicacion": "create_application",
            "aplicacion": "create_application",
            "estadisticas": "stats",
            "stats": "stats"
        }

# Instancia global
rag_engine_adapter = RAGEngineAdapter()

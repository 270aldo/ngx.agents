"""
Gestor de embeddings para NGX Agents.

Este módulo proporciona funcionalidades para generar, almacenar y buscar
embeddings, facilitando la comprensión semántica y la búsqueda por similitud.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
import numpy as np
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from clients.vertex_ai.embedding_client import EmbeddingClient
from clients.pinecone.pinecone_client import PineconeClient
from core.logging_config import get_logger
from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from infrastructure.adapters.vector_store_adapter import MemoryVectorStore, PineconeVectorStore, VectorStoreAdapter

# Configurar logger
logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()

class EmbeddingsManager:
    """Gestor de embeddings para NGX Agents."""
    
    def __init__(self, config=None):
        """Inicializa el gestor de embeddings."""
        self.config = config or self._load_default_config()
        self.embedding_client = EmbeddingClient(self.config.get("embedding_client"))
        self.vector_store = self._initialize_vector_store()
        self.similarity_threshold = self.config.get("similarity_threshold", 0.7)
        self.vector_dimension = self.config.get("vector_dimension", 3072)
        
        # Estadísticas
        self.stats = {
            "embedding_generations": 0,
            "batch_generations": 0,
            "storage_operations": 0,
            "search_operations": 0,
            "delete_operations": 0,
            "errors": 0
        }
        
        logger.info("Gestor de embeddings inicializado")
        
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
        
        return {
            "similarity_threshold": float(os.environ.get("EMBEDDING_SIMILARITY_THRESHOLD", "0.7")),
            "vector_dimension": get_env_int("EMBEDDING_VECTOR_DIMENSION", 768),
            "vector_store_type": os.environ.get("VECTOR_STORE_TYPE", "memory"),
            "embedding_client": {
                "model_name": os.environ.get("VERTEX_EMBEDDING_MODEL", "textembedding-gecko"),
                "use_redis_cache": os.environ.get("USE_REDIS_CACHE", "false").lower() == "true",
                "redis_url": os.environ.get("REDIS_URL"),
                "cache_ttl": get_env_int("EMBEDDING_CACHE_TTL", 86400)  # 24 horas por defecto
            },
            "pinecone": {
                "api_key": os.environ.get("PINECONE_API_KEY"),
                "environment": os.environ.get("PINECONE_ENVIRONMENT", "us-west1-gcp"),
                "index_name": os.environ.get("PINECONE_INDEX_NAME", "ngx-embeddings"),
                "dimension": get_env_int("PINECONE_DIMENSION", 768),
                "metric": os.environ.get("PINECONE_METRIC", "cosine")
            }
        }
    
    def _initialize_vector_store(self) -> VectorStoreAdapter:
        """Inicializa el almacén vectorial según la configuración."""
        vector_store_type = self.config.get("vector_store_type", "memory")
        
        if vector_store_type == "pinecone":
            # Verificar si hay una API key de Pinecone
            if not self.config.get("pinecone", {}).get("api_key"):
                logger.warning("No se encontró API key de Pinecone. Usando almacenamiento en memoria.")
                return MemoryVectorStore()
            
            # Inicializar cliente de Pinecone
            pinecone_client = PineconeClient(self.config.get("pinecone"))
            return PineconeVectorStore(pinecone_client)
        else:
            # Usar almacenamiento en memoria por defecto
            return MemoryVectorStore()
    
    
    @telemetry_adapter.measure_execution_time("embedding_generation_manager")
    async def generate_embedding(self, text: str, namespace: Optional[str] = None) -> List[float]:
        """
        Genera un embedding para el texto proporcionado.
        
        Args:
            text: Texto para generar el embedding
            namespace: Namespace opcional para organización
            
        Returns:
            Lista de valores float que representan el embedding
        """
        span = telemetry_adapter.start_span("EmbeddingsManager.generate_embedding", {
            "text_length": len(text),
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["embedding_generations"] += 1
            
            # Generar embedding usando el cliente
            embedding = await self.embedding_client.generate_embedding(text, namespace)
            
            telemetry_adapter.set_span_attribute(span, "embedding_size", len(embedding))
            return embedding
            
        except Exception as e:
            logger.error(f"Error al generar embedding: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver un embedding vacío en caso de error
            return [0.0] * self.vector_dimension
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def store_embedding(self, text: str, embedding: Optional[List[float]] = None, 
                           metadata: Optional[Dict[str, Any]] = None, namespace: Optional[str] = None) -> str:
        """
        Almacena un embedding con metadatos.
        
        Args:
            text: Texto original
            embedding: Embedding pre-calculado (opcional)
            metadata: Metadatos asociados al embedding
            namespace: Namespace para organización
            
        Returns:
            ID del embedding almacenado
        """
        span = telemetry_adapter.start_span("EmbeddingsManager.store_embedding", {
            "text_length": len(text),
            "namespace": namespace or "default",
            "has_precalculated_embedding": embedding is not None
        })
        
        try:
            # Actualizar estadísticas
            self.stats["storage_operations"] += 1
            
            # Generar embedding si no se proporciona
            if embedding is None:
                embedding = await self.generate_embedding(text, namespace)
            
            # Almacenar en el vector store
            embedding_id = await self.vector_store.store(
                vector=embedding,
                text=text,
                metadata=metadata,
                namespace=namespace
            )
            
            telemetry_adapter.set_span_attribute(span, "embedding_id", embedding_id)
            logger.debug(f"Embedding almacenado con ID: {embedding_id}")
            return embedding_id
            
        except Exception as e:
            logger.error(f"Error al almacenar embedding: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            return ""
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def search_similar(self, query: Union[str, List[float]], namespace: Optional[str] = None, 
                          top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Busca textos similares basados en embeddings.
        
        Args:
            query: Texto o embedding para buscar similares
            namespace: Namespace para la búsqueda
            top_k: Número de resultados a retornar
            filter: Filtro opcional para metadatos
            
        Returns:
            Lista de documentos similares con scores
        """
        span = telemetry_adapter.start_span("EmbeddingsManager.search_similar", {
            "query_type": "embedding" if isinstance(query, list) else "text",
            "namespace": namespace or "default",
            "top_k": top_k,
            "has_filter": filter is not None
        })
        
        try:
            # Actualizar estadísticas
            self.stats["search_operations"] += 1
            
            # Obtener embedding de la consulta
            query_embedding = query if isinstance(query, list) else await self.generate_embedding(query, namespace)
            
            # Buscar en el vector store
            results = await self.vector_store.search(
                vector=query_embedding,
                namespace=namespace,
                top_k=top_k,
                filter=filter
            )
            
            # Convertir scores a similitud para mantener compatibilidad
            for result in results:
                if "score" in result:
                    result["similarity"] = result.pop("score")
            
            telemetry_adapter.set_span_attribute(span, "results_count", len(results))
            return results
            
        except Exception as e:
            logger.error(f"Error al buscar similares: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            return []
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def cluster_embeddings(self, embeddings: List[List[float]], n_clusters: int = 5) -> List[int]:
        """
        Agrupa embeddings en clusters.
        
        Args:
            embeddings: Lista de embeddings a agrupar
            n_clusters: Número de clusters a crear
            
        Returns:
            Lista de etiquetas de cluster para cada embedding
        """
        span = telemetry_adapter.start_span("EmbeddingsManager.cluster_embeddings", {
            "embeddings_count": len(embeddings),
            "n_clusters": n_clusters
        })
        
        try:
            # Importar scikit-learn para clustering
            try:
                from sklearn.cluster import KMeans
                SKLEARN_AVAILABLE = True
            except ImportError:
                logger.warning("scikit-learn no está disponible. No se puede realizar clustering.")
                SKLEARN_AVAILABLE = False
                
            if not SKLEARN_AVAILABLE:
                # Retornar etiquetas aleatorias si no está disponible scikit-learn
                import random
                return [random.randint(0, n_clusters-1) for _ in range(len(embeddings))]
            
            # Convertir a array de numpy
            X = np.array(embeddings)
            
            # Aplicar KMeans
            kmeans = KMeans(n_clusters=min(n_clusters, len(embeddings)), random_state=42)
            labels = kmeans.fit_predict(X)
            
            telemetry_adapter.set_span_attribute(span, "clusters_found", len(set(labels)))
            return labels.tolist()
            
        except Exception as e:
            logger.error(f"Error al agrupar embeddings: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Retornar etiquetas por defecto en caso de error
            return [0] * len(embeddings)
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def batch_store_embeddings(self, texts: List[str], embeddings: Optional[List[List[float]]] = None,
                                  metadatas: Optional[List[Dict[str, Any]]] = None, 
                                  namespace: Optional[str] = None) -> List[str]:
        """
        Almacena múltiples embeddings en batch.
        
        Args:
            texts: Lista de textos
            embeddings: Lista de embeddings pre-calculados (opcional)
            metadatas: Lista de metadatos asociados
            namespace: Namespace opcional
            
        Returns:
            Lista de IDs de los embeddings almacenados
        """
        span = telemetry_adapter.start_span("EmbeddingsManager.batch_store_embeddings", {
            "texts_count": len(texts),
            "namespace": namespace or "default",
            "has_precalculated_embeddings": embeddings is not None
        })
        
        try:
            # Actualizar estadísticas
            self.stats["batch_storage_operations"] += 1
            
            # Generar embeddings si no se proporcionan
            if embeddings is None:
                embeddings = await self.batch_generate_embeddings(texts, namespace)
            
            # Almacenar en el vector store
            ids = await self.vector_store.batch_store(
                vectors=embeddings,
                texts=texts,
                metadatas=metadatas,
                namespace=namespace
            )
            
            telemetry_adapter.set_span_attribute(span, "stored_count", len(ids))
            return ids
            
        except Exception as e:
            logger.error(f"Error al almacenar embeddings en batch: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            return []
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def delete_embedding(self, embedding_id: str, namespace: Optional[str] = None) -> bool:
        """
        Elimina un embedding del almacenamiento.
        
        Args:
            embedding_id: ID del embedding a eliminar
            namespace: Namespace del embedding
            
        Returns:
            True si se eliminó correctamente
        """
        span = telemetry_adapter.start_span("EmbeddingsManager.delete_embedding", {
            "embedding_id": embedding_id,
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["delete_operations"] += 1
            
            # Eliminar del vector store
            success = await self.vector_store.delete(embedding_id, namespace)
            
            telemetry_adapter.set_span_attribute(span, "success", success)
            return success
            
        except Exception as e:
            logger.error(f"Error al eliminar embedding: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            return False
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_embedding(self, embedding_id: str, namespace: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Recupera un embedding específico.
        
        Args:
            embedding_id: ID del embedding a recuperar
            namespace: Namespace del embedding
            
        Returns:
            Diccionario con el embedding y sus metadatos
        """
        span = telemetry_adapter.start_span("EmbeddingsManager.get_embedding", {
            "embedding_id": embedding_id,
            "namespace": namespace or "default"
        })
        
        try:
            # Obtener del vector store
            result = await self.vector_store.get(embedding_id, namespace)
            
            telemetry_adapter.set_span_attribute(span, "success", result is not None)
            return result
            
        except Exception as e:
            logger.error(f"Error al obtener embedding: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            return None
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del gestor de embeddings.
        
        Returns:
            Dict[str, Any]: Estadísticas de uso
        """
        # Obtener estadísticas del cliente
        client_stats = await self.embedding_client.get_stats()
        
        # Obtener estadísticas del vector store
        vector_store_stats = await self.vector_store.get_stats()
        
        return {
            "manager_stats": self.stats,
            "client_stats": client_stats,
            "vector_store_stats": vector_store_stats,
            "vector_dimension": self.vector_dimension,
            "similarity_threshold": self.similarity_threshold,
            "vector_store_type": self.config.get("vector_store_type", "memory"),
            "timestamp": datetime.now().isoformat()
        }

# Crear instancia única del gestor de embeddings
embeddings_manager = EmbeddingsManager()

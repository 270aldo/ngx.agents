"""
Adaptador para Vertex AI Vector Search.

Este módulo proporciona una implementación del adaptador de almacenamiento vectorial
utilizando Vertex AI Vector Search.
"""

import logging
import uuid
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from clients.vertex_ai.vector_search_client import VertexVectorSearchClient
from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from infrastructure.adapters.vector_store_adapter import VectorStoreAdapter
from core.logging_config import get_logger

logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()

class VertexVectorStore(VectorStoreAdapter):
    """Implementación de Vertex AI Vector Search para el almacén vectorial."""
    
    def __init__(self, client=None):
        """
        Inicializa el almacén vectorial de Vertex AI Vector Search.
        
        Args:
            client: Cliente de Vertex AI Vector Search (opcional)
        """
        super().__init__()
        self.client = client or VertexVectorSearchClient()
        self.stats = {
            "store_operations": 0,
            "batch_store_operations": 0,
            "search_operations": 0,
            "delete_operations": 0,
            "get_operations": 0
        }
    
    async def store(self, vector: List[float], text: str, metadata: Optional[Dict[str, Any]] = None, 
                  namespace: Optional[str] = None, id: Optional[str] = None) -> str:
        """
        Almacena un vector en Vertex AI Vector Search.
        
        Args:
            vector: Vector a almacenar
            text: Texto original
            metadata: Metadatos asociados
            namespace: Namespace opcional
            id: ID opcional (se genera uno si no se proporciona)
            
        Returns:
            str: ID del vector almacenado
        """
        span = telemetry_adapter.start_span("VertexVectorStore.store", {
            "vector_dimension": len(vector),
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["store_operations"] += 1
            
            # Generar ID si no se proporciona
            if id is None:
                id = str(uuid.uuid4())
            
            # Preparar metadatos
            if metadata is None:
                metadata = {}
            
            # Añadir texto a los metadatos
            metadata["text"] = text
            
            # Preparar vector para Vertex AI Vector Search
            vertex_vector = {
                "id": id,
                "values": vector,
                "metadata": metadata
            }
            
            # Almacenar en Vertex AI Vector Search
            await self.client.upsert([vertex_vector], namespace)
            
            telemetry_adapter.set_span_attribute(span, "vector_id", id)
            return id
            
        except Exception as e:
            logger.error(f"Error al almacenar vector en Vertex AI Vector Search: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return ""
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def search(self, vector: List[float], namespace: Optional[str] = None, 
                   top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Busca vectores similares en Vertex AI Vector Search.
        
        Args:
            vector: Vector de consulta
            namespace: Namespace opcional
            top_k: Número de resultados a retornar
            filter: Filtro opcional para metadatos
            
        Returns:
            List[Dict[str, Any]]: Lista de resultados
        """
        span = telemetry_adapter.start_span("VertexVectorStore.search", {
            "namespace": namespace or "default",
            "top_k": top_k,
            "has_filter": filter is not None
        })
        
        try:
            # Actualizar estadísticas
            self.stats["search_operations"] += 1
            
            # Consultar Vertex AI Vector Search
            result = await self.client.query(vector, top_k, namespace, filter)
            
            # Procesar resultados
            matches = result.get("matches", [])
            results = []
            
            for match in matches:
                # Extraer texto de los metadatos
                metadata = match.get("metadata", {})
                text = metadata.pop("text", "")
                
                results.append({
                    "id": match.get("id", ""),
                    "text": text,
                    "metadata": metadata,
                    "score": match.get("score", 0.0)
                })
            
            telemetry_adapter.set_span_attribute(span, "results_count", len(results))
            return results
            
        except Exception as e:
            logger.error(f"Error al buscar vectores en Vertex AI Vector Search: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return []
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def delete(self, id: str, namespace: Optional[str] = None) -> bool:
        """
        Elimina un vector de Vertex AI Vector Search.
        
        Args:
            id: ID del vector a eliminar
            namespace: Namespace opcional
            
        Returns:
            bool: True si se eliminó correctamente
        """
        span = telemetry_adapter.start_span("VertexVectorStore.delete", {
            "vector_id": id,
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["delete_operations"] += 1
            
            # Eliminar de Vertex AI Vector Search
            result = await self.client.delete([id], namespace)
            
            # Verificar resultado
            success = "error" not in result and result.get("deleted_count", 0) > 0
            
            telemetry_adapter.set_span_attribute(span, "success", success)
            return success
            
        except Exception as e:
            logger.error(f"Error al eliminar vector de Vertex AI Vector Search: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return False
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def batch_store(self, vectors: List[List[float]], texts: List[str], 
                        metadatas: Optional[List[Dict[str, Any]]] = None, 
                        namespace: Optional[str] = None, 
                        ids: Optional[List[str]] = None) -> List[str]:
        """
        Almacena múltiples vectores en batch en Vertex AI Vector Search.
        
        Args:
            vectors: Lista de vectores a almacenar
            texts: Lista de textos originales
            metadatas: Lista de metadatos asociados
            namespace: Namespace opcional
            ids: Lista de IDs opcionales
            
        Returns:
            List[str]: Lista de IDs de los vectores almacenados
        """
        span = telemetry_adapter.start_span("VertexVectorStore.batch_store", {
            "vectors_count": len(vectors),
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["batch_store_operations"] += 1
            
            # Verificar longitudes
            if len(vectors) != len(texts):
                raise ValueError("Las listas de vectores y textos deben tener la misma longitud")
            
            # Preparar metadatos
            if metadatas is None:
                metadatas = [{} for _ in range(len(vectors))]
            elif len(metadatas) != len(vectors):
                raise ValueError("La lista de metadatos debe tener la misma longitud que la lista de vectores")
            
            # Preparar IDs
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
            elif len(ids) != len(vectors):
                raise ValueError("La lista de IDs debe tener la misma longitud que la lista de vectores")
            
            # Preparar vectores para Vertex AI Vector Search
            vertex_vectors = []
            for i, (vector, text, metadata, id) in enumerate(zip(vectors, texts, metadatas, ids)):
                # Añadir texto a los metadatos
                if metadata is None:
                    metadata = {}
                metadata["text"] = text
                
                vertex_vectors.append({
                    "id": id,
                    "values": vector,
                    "metadata": metadata
                })
            
            # Almacenar en Vertex AI Vector Search
            await self.client.upsert(vertex_vectors, namespace)
            
            telemetry_adapter.set_span_attribute(span, "stored_count", len(ids))
            return ids
            
        except Exception as e:
            logger.error(f"Error al almacenar vectores en batch en Vertex AI Vector Search: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return []
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get(self, id: str, namespace: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Recupera un vector específico de Vertex AI Vector Search.
        
        Args:
            id: ID del vector a recuperar
            namespace: Namespace opcional
            
        Returns:
            Optional[Dict[str, Any]]: Vector y metadatos, o None si no existe
        """
        span = telemetry_adapter.start_span("VertexVectorStore.get", {
            "vector_id": id,
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["get_operations"] += 1
            
            # Vertex AI Vector Search no tiene una API directa para obtener un vector por ID
            # Implementamos una búsqueda por ID usando filtros
            filter = {"id": id}
            
            # Crear un vector aleatorio para la búsqueda
            # (Vertex AI Vector Search requiere un vector para la búsqueda)
            import random
            random_vector = [random.uniform(-1, 1) for _ in range(3072)]  # Usar dimensión por defecto
            
            results = await self.search(random_vector, namespace, 1, filter)
            
            if not results:
                telemetry_adapter.set_span_attribute(span, "vector_exists", False)
                return None
            
            # Recuperar el primer resultado
            result = results[0]
            
            telemetry_adapter.set_span_attribute(span, "success", True)
            return {
                "id": result["id"],
                "vector": result.get("vector", []),
                "text": result["text"],
                "metadata": result["metadata"]
            }
            
        except Exception as e:
            logger.error(f"Error al recuperar vector de Vertex AI Vector Search: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return None
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del almacén vectorial de Vertex AI Vector Search.
        
        Returns:
            Dict[str, Any]: Estadísticas
        """
        # Obtener estadísticas del cliente
        client_stats = await self.client.get_stats()
        
        return {
            "store_operations": self.stats["store_operations"],
            "batch_store_operations": self.stats["batch_store_operations"],
            "search_operations": self.stats["search_operations"],
            "delete_operations": self.stats["delete_operations"],
            "get_operations": self.stats["get_operations"],
            "client_stats": client_stats
        }

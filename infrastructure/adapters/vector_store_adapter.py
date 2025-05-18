"""
Adaptador para almacenamiento vectorial.

Este módulo proporciona una interfaz abstracta para diferentes
almacenes vectoriales, como Pinecone, y una implementación en memoria.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.logging_config import get_logger

logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()

class VectorStoreAdapter(ABC, BaseAgentAdapter):
    """Interfaz abstracta para almacenes vectoriales."""
    
    @abstractmethod
    async def store(self, vector: List[float], text: str, metadata: Optional[Dict[str, Any]] = None, 
                  namespace: Optional[str] = None, id: Optional[str] = None) -> str:
        """
        Almacena un vector en el almacén vectorial.
        
        Args:
            vector: Vector a almacenar
            text: Texto original
            metadata: Metadatos asociados
            namespace: Namespace opcional
            id: ID opcional (se genera uno si no se proporciona)
            
        Returns:
            str: ID del vector almacenado
        """
        pass
    
    @abstractmethod
    async def search(self, vector: List[float], namespace: Optional[str] = None, 
                   top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Busca vectores similares.
        
        Args:
            vector: Vector de consulta
            namespace: Namespace opcional
            top_k: Número de resultados a retornar
            filter: Filtro opcional para metadatos
            
        Returns:
            List[Dict[str, Any]]: Lista de resultados
        """
        pass
    
    @abstractmethod
    async def delete(self, id: str, namespace: Optional[str] = None) -> bool:
        """
        Elimina un vector del almacén.
        
        Args:
            id: ID del vector a eliminar
            namespace: Namespace opcional
            
        Returns:
            bool: True si se eliminó correctamente
        """
        pass
    
    @abstractmethod
    async def batch_store(self, vectors: List[List[float]], texts: List[str], 
                        metadatas: Optional[List[Dict[str, Any]]] = None, 
                        namespace: Optional[str] = None, 
                        ids: Optional[List[str]] = None) -> List[str]:
        """
        Almacena múltiples vectores en batch.
        
        Args:
            vectors: Lista de vectores a almacenar
            texts: Lista de textos originales
            metadatas: Lista de metadatos asociados
            namespace: Namespace opcional
            ids: Lista de IDs opcionales
            
        Returns:
            List[str]: Lista de IDs de los vectores almacenados
        """
        pass
    
    @abstractmethod
    async def get(self, id: str, namespace: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Recupera un vector específico.
        
        Args:
            id: ID del vector a recuperar
            namespace: Namespace opcional
            
        Returns:
            Optional[Dict[str, Any]]: Vector y metadatos, o None si no existe
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del almacén vectorial.
        
        Returns:
            Dict[str, Any]: Estadísticas
        """
        pass
        
    async def _process_query(self, query: str, user_id: str = None, session_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario relacionada con almacenamiento vectorial.
        
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
            vector = kwargs.get('vector')
            text = kwargs.get('text')
            metadata = kwargs.get('metadata')
            namespace = kwargs.get('namespace')
            id = kwargs.get('id')
            top_k = kwargs.get('top_k', 10)
            filter = kwargs.get('filter')
            vectors = kwargs.get('vectors')
            texts = kwargs.get('texts')
            metadatas = kwargs.get('metadatas')
            ids = kwargs.get('ids')
            
            # Determinar la operación a realizar según el tipo de consulta
            result = None
            
            if query_type == "store" and vector is not None and text is not None:
                # Almacenar vector
                result = await self.store(vector, text, metadata, namespace, id)
                return {
                    "success": True,
                    "output": f"Vector almacenado con ID: {result}",
                    "query_type": query_type,
                    "vector_id": result,
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif query_type == "search" and vector is not None:
                # Buscar vectores similares
                result = await self.search(vector, namespace, top_k, filter)
                return {
                    "success": True,
                    "output": f"Se encontraron {len(result)} resultados similares",
                    "query_type": query_type,
                    "results": result,
                    "result_count": len(result),
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif query_type == "delete" and id is not None:
                # Eliminar vector
                result = await self.delete(id, namespace)
                return {
                    "success": result,
                    "output": f"Vector {id} {'eliminado correctamente' if result else 'no pudo ser eliminado'}",
                    "query_type": query_type,
                    "vector_id": id,
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif query_type == "batch_store" and vectors is not None and texts is not None:
                # Almacenar vectores en batch
                result = await self.batch_store(vectors, texts, metadatas, namespace, ids)
                return {
                    "success": True,
                    "output": f"Se almacenaron {len(result)} vectores",
                    "query_type": query_type,
                    "vector_ids": result,
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif query_type == "get" and id is not None:
                # Obtener vector específico
                result = await self.get(id, namespace)
                if result:
                    return {
                        "success": True,
                        "output": f"Vector {id} recuperado correctamente",
                        "query_type": query_type,
                        "vector": result,
                        "agent": self.__class__.__name__,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"No se encontró el vector con ID {id}",
                        "query_type": query_type,
                        "agent": self.__class__.__name__,
                        "timestamp": datetime.now().isoformat()
                    }
            
            elif query_type == "stats":
                # Obtener estadísticas
                result = await self.get_stats()
                return {
                    "success": True,
                    "output": "Estadísticas del almacén vectorial recuperadas",
                    "query_type": query_type,
                    "stats": result,
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
            logger.error(f"Error al procesar consulta de almacenamiento vectorial: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para VectorStoreAdapter.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "almacenar": "store",
            "guardar": "store",
            "buscar": "search",
            "similar": "search",
            "eliminar": "delete",
            "borrar": "delete",
            "batch": "batch_store",
            "lote": "batch_store",
            "obtener": "get",
            "recuperar": "get",
            "estadísticas": "stats",
            "stats": "stats"
        }

class MemoryVectorStore(VectorStoreAdapter):
    """Implementación en memoria del almacén vectorial."""
    
    def __init__(self):
        """Inicializa el almacén vectorial en memoria."""
        super().__init__()
        self.store = {}
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
        Almacena un vector en memoria.
        
        Args:
            vector: Vector a almacenar
            text: Texto original
            metadata: Metadatos asociados
            namespace: Namespace opcional
            id: ID opcional (se genera uno si no se proporciona)
            
        Returns:
            str: ID del vector almacenado
        """
        span = telemetry_adapter.start_span("MemoryVectorStore.store", {
            "vector_dimension": len(vector),
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["store_operations"] += 1
            
            # Generar ID si no se proporciona
            if id is None:
                id = str(uuid.uuid4())
            
            # Preparar namespace
            ns = namespace or "default"
            if ns not in self.store:
                self.store[ns] = {}
            
            # Almacenar vector
            self.store[ns][id] = {
                "id": id,
                "vector": vector,
                "text": text,
                "metadata": metadata or {}
            }
            
            telemetry_adapter.set_span_attribute(span, "vector_id", id)
            return id
            
        except Exception as e:
            logger.error(f"Error al almacenar vector: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return ""
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def search(self, vector: List[float], namespace: Optional[str] = None, 
                   top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Busca vectores similares en memoria.
        
        Args:
            vector: Vector de consulta
            namespace: Namespace opcional
            top_k: Número de resultados a retornar
            filter: Filtro opcional para metadatos
            
        Returns:
            List[Dict[str, Any]]: Lista de resultados
        """
        span = telemetry_adapter.start_span("MemoryVectorStore.search", {
            "namespace": namespace or "default",
            "top_k": top_k,
            "has_filter": filter is not None
        })
        
        try:
            # Actualizar estadísticas
            self.stats["search_operations"] += 1
            
            # Preparar namespace
            ns = namespace or "default"
            if ns not in self.store:
                telemetry_adapter.set_span_attribute(span, "namespace_exists", False)
                return []
            
            # Calcular similitudes
            import numpy as np
            query_vec = np.array(vector)
            
            results = []
            for id, item in self.store[ns].items():
                # Aplicar filtro si se proporciona
                if filter and not self._match_filter(item["metadata"], filter):
                    continue
                
                # Calcular similitud coseno
                item_vec = np.array(item["vector"])
                similarity = self._calculate_similarity(query_vec, item_vec)
                
                results.append({
                    "id": id,
                    "text": item["text"],
                    "metadata": item["metadata"],
                    "score": similarity
                })
            
            # Ordenar por similitud (descendente) y limitar a top_k
            results.sort(key=lambda x: x["score"], reverse=True)
            results = results[:top_k]
            
            telemetry_adapter.set_span_attribute(span, "results_count", len(results))
            return results
            
        except Exception as e:
            logger.error(f"Error al buscar vectores: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return []
            
        finally:
            telemetry_adapter.end_span(span)
    
    def _calculate_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calcula la similitud coseno entre dos vectores.
        
        Args:
            vec1: Primer vector
            vec2: Segundo vector
            
        Returns:
            float: Similitud coseno (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    
    def _match_filter(self, metadata: Dict[str, Any], filter: Dict[str, Any]) -> bool:
        """
        Verifica si los metadatos coinciden con el filtro.
        
        Args:
            metadata: Metadatos a verificar
            filter: Filtro a aplicar
            
        Returns:
            bool: True si coincide, False en caso contrario
        """
        for key, value in filter.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
    
    async def delete(self, id: str, namespace: Optional[str] = None) -> bool:
        """
        Elimina un vector de la memoria.
        
        Args:
            id: ID del vector a eliminar
            namespace: Namespace opcional
            
        Returns:
            bool: True si se eliminó correctamente
        """
        span = telemetry_adapter.start_span("MemoryVectorStore.delete", {
            "vector_id": id,
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["delete_operations"] += 1
            
            # Preparar namespace
            ns = namespace or "default"
            if ns not in self.store:
                telemetry_adapter.set_span_attribute(span, "namespace_exists", False)
                return False
            
            # Verificar si existe el vector
            if id not in self.store[ns]:
                telemetry_adapter.set_span_attribute(span, "vector_exists", False)
                return False
            
            # Eliminar vector
            del self.store[ns][id]
            
            telemetry_adapter.set_span_attribute(span, "success", True)
            return True
            
        except Exception as e:
            logger.error(f"Error al eliminar vector: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return False
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def batch_store(self, vectors: List[List[float]], texts: List[str], 
                        metadatas: Optional[List[Dict[str, Any]]] = None, 
                        namespace: Optional[str] = None, 
                        ids: Optional[List[str]] = None) -> List[str]:
        """
        Almacena múltiples vectores en batch.
        
        Args:
            vectors: Lista de vectores a almacenar
            texts: Lista de textos originales
            metadatas: Lista de metadatos asociados
            namespace: Namespace opcional
            ids: Lista de IDs opcionales
            
        Returns:
            List[str]: Lista de IDs de los vectores almacenados
        """
        span = telemetry_adapter.start_span("MemoryVectorStore.batch_store", {
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
            
            # Almacenar vectores
            stored_ids = []
            for i, (vector, text, metadata, id) in enumerate(zip(vectors, texts, metadatas, ids)):
                stored_id = await self.store(vector, text, metadata, namespace, id)
                stored_ids.append(stored_id)
            
            telemetry_adapter.set_span_attribute(span, "stored_count", len(stored_ids))
            return stored_ids
            
        except Exception as e:
            logger.error(f"Error al almacenar vectores en batch: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return []
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get(self, id: str, namespace: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Recupera un vector específico.
        
        Args:
            id: ID del vector a recuperar
            namespace: Namespace opcional
            
        Returns:
            Optional[Dict[str, Any]]: Vector y metadatos, o None si no existe
        """
        span = telemetry_adapter.start_span("MemoryVectorStore.get", {
            "vector_id": id,
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["get_operations"] += 1
            
            # Preparar namespace
            ns = namespace or "default"
            if ns not in self.store:
                telemetry_adapter.set_span_attribute(span, "namespace_exists", False)
                return None
            
            # Verificar si existe el vector
            if id not in self.store[ns]:
                telemetry_adapter.set_span_attribute(span, "vector_exists", False)
                return None
            
            # Recuperar vector
            item = self.store[ns][id]
            
            telemetry_adapter.set_span_attribute(span, "success", True)
            return item
            
        except Exception as e:
            logger.error(f"Error al recuperar vector: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return None
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del almacén vectorial.
        
        Returns:
            Dict[str, Any]: Estadísticas
        """
        # Contar vectores por namespace
        namespace_counts = {}
        total_vectors = 0
        
        for ns, vectors in self.store.items():
            count = len(vectors)
            namespace_counts[ns] = count
            total_vectors += count
        
        return {
            "store_operations": self.stats["store_operations"],
            "batch_store_operations": self.stats["batch_store_operations"],
            "search_operations": self.stats["search_operations"],
            "delete_operations": self.stats["delete_operations"],
            "get_operations": self.stats["get_operations"],
            "total_vectors": total_vectors,
            "namespaces": len(self.store),
            "namespace_counts": namespace_counts
        }

class PineconeVectorStore(VectorStoreAdapter):
    """Implementación de Pinecone para el almacén vectorial."""
    
    def __init__(self, client):
        """
        Inicializa el almacén vectorial de Pinecone.
        
        Args:
            client: Cliente de Pinecone
        """
        self.client = client
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
        Almacena un vector en Pinecone.
        
        Args:
            vector: Vector a almacenar
            text: Texto original
            metadata: Metadatos asociados
            namespace: Namespace opcional
            id: ID opcional (se genera uno si no se proporciona)
            
        Returns:
            str: ID del vector almacenado
        """
        span = telemetry_adapter.start_span("PineconeVectorStore.store", {
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
            
            # Preparar vector para Pinecone
            pinecone_vector = {
                "id": id,
                "values": vector,
                "metadata": metadata
            }
            
            # Almacenar en Pinecone
            await self.client.upsert([pinecone_vector], namespace)
            
            telemetry_adapter.set_span_attribute(span, "vector_id", id)
            return id
            
        except Exception as e:
            logger.error(f"Error al almacenar vector en Pinecone: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return ""
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def search(self, vector: List[float], namespace: Optional[str] = None, 
                   top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Busca vectores similares en Pinecone.
        
        Args:
            vector: Vector de consulta
            namespace: Namespace opcional
            top_k: Número de resultados a retornar
            filter: Filtro opcional para metadatos
            
        Returns:
            List[Dict[str, Any]]: Lista de resultados
        """
        span = telemetry_adapter.start_span("PineconeVectorStore.search", {
            "namespace": namespace or "default",
            "top_k": top_k,
            "has_filter": filter is not None
        })
        
        try:
            # Actualizar estadísticas
            self.stats["search_operations"] += 1
            
            # Consultar Pinecone
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
            logger.error(f"Error al buscar vectores en Pinecone: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return []
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def delete(self, id: str, namespace: Optional[str] = None) -> bool:
        """
        Elimina un vector de Pinecone.
        
        Args:
            id: ID del vector a eliminar
            namespace: Namespace opcional
            
        Returns:
            bool: True si se eliminó correctamente
        """
        span = telemetry_adapter.start_span("PineconeVectorStore.delete", {
            "vector_id": id,
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["delete_operations"] += 1
            
            # Eliminar de Pinecone
            result = await self.client.delete([id], namespace)
            
            # Verificar resultado
            success = "error" not in result
            
            telemetry_adapter.set_span_attribute(span, "success", success)
            return success
            
        except Exception as e:
            logger.error(f"Error al eliminar vector de Pinecone: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return False
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def batch_store(self, vectors: List[List[float]], texts: List[str], 
                        metadatas: Optional[List[Dict[str, Any]]] = None, 
                        namespace: Optional[str] = None, 
                        ids: Optional[List[str]] = None) -> List[str]:
        """
        Almacena múltiples vectores en batch en Pinecone.
        
        Args:
            vectors: Lista de vectores a almacenar
            texts: Lista de textos originales
            metadatas: Lista de metadatos asociados
            namespace: Namespace opcional
            ids: Lista de IDs opcionales
            
        Returns:
            List[str]: Lista de IDs de los vectores almacenados
        """
        span = telemetry_adapter.start_span("PineconeVectorStore.batch_store", {
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
            
            # Preparar vectores para Pinecone
            pinecone_vectors = []
            for i, (vector, text, metadata, id) in enumerate(zip(vectors, texts, metadatas, ids)):
                # Añadir texto a los metadatos
                if metadata is None:
                    metadata = {}
                metadata["text"] = text
                
                pinecone_vectors.append({
                    "id": id,
                    "values": vector,
                    "metadata": metadata
                })
            
            # Almacenar en Pinecone
            await self.client.upsert(pinecone_vectors, namespace)
            
            telemetry_adapter.set_span_attribute(span, "stored_count", len(ids))
            return ids
            
        except Exception as e:
            logger.error(f"Error al almacenar vectores en batch en Pinecone: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return []
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get(self, id: str, namespace: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Recupera un vector específico de Pinecone.
        
        Args:
            id: ID del vector a recuperar
            namespace: Namespace opcional
            
        Returns:
            Optional[Dict[str, Any]]: Vector y metadatos, o None si no existe
        """
        span = telemetry_adapter.start_span("PineconeVectorStore.get", {
            "vector_id": id,
            "namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["get_operations"] += 1
            
            # Pinecone no tiene una API directa para obtener un vector por ID
            # Implementamos una búsqueda por ID usando filtros
            filter = {"id": id}
            results = await self.search([0.0] * 768, namespace, 1, filter)
            
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
            logger.error(f"Error al recuperar vector de Pinecone: {str(e)}")
            telemetry_adapter.record_exception(span, e)
            return None
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del almacén vectorial de Pinecone.
        
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

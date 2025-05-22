"""
Cliente para Vertex AI Vector Search.

Este módulo proporciona un cliente para interactuar con Vertex AI Vector Search,
permitiendo almacenar, consultar y eliminar vectores de embeddings.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Union, Any

from google.cloud import aiplatform
from google.oauth2 import service_account

from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from core.circuit_breaker import circuit_breaker
from core.logging_config import get_logger

logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()

class VertexVectorSearchClient:
    """Cliente para Vertex AI Vector Search."""
    
    def __init__(self, config=None):
        """Inicializa el cliente de Vertex AI Vector Search."""
        self.config = config or self._load_default_config()
        self.credentials = self._initialize_credentials()
        self.client = self._initialize_client()
        self.index_endpoint = None
        self.deployed_index = None
        
        # Estadísticas
        self.stats = {
            "upsert_operations": 0,
            "query_operations": 0,
            "delete_operations": 0,
            "errors": 0,
            "latency_ms": []
        }
        
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
            "project_id": os.environ.get("GOOGLE_CLOUD_PROJECT"),
            "location": os.environ.get("VERTEX_LOCATION", "us-central1"),
            "credentials_path": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            "index_name": os.environ.get("VERTEX_VECTOR_SEARCH_INDEX", "ngx-embeddings"),
            "index_endpoint_name": os.environ.get("VERTEX_VECTOR_SEARCH_ENDPOINT", "ngx-embeddings-endpoint"),
            "deployed_index_id": os.environ.get("VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID", "ngx-embeddings-deployed"),
            "dimension": get_env_int("VERTEX_VECTOR_DIMENSION", 3072),
            "distance_measure": os.environ.get("VERTEX_VECTOR_DISTANCE_MEASURE", "DOT_PRODUCT_DISTANCE"),
            "approximate_neighbors_count": get_env_int("VERTEX_VECTOR_NEIGHBORS_COUNT", 150),
            "leaf_node_embedding_count": get_env_int("VERTEX_VECTOR_LEAF_NODE_COUNT", 1000),
            "leaf_nodes_to_search_percent": get_env_int("VERTEX_VECTOR_LEAF_NODES_PERCENT", 10)
        }
        
    def _initialize_credentials(self) -> Optional[service_account.Credentials]:
        """Inicializa las credenciales de Google Cloud."""
        try:
            if self.config.get("credentials_path"):
                return service_account.Credentials.from_service_account_file(
                    self.config["credentials_path"]
                )
            return None  # Usar credenciales por defecto
        except Exception as e:
            logger.error(f"Error al inicializar credenciales: {e}")
            return None
        
    def _initialize_client(self) -> Any:
        """Inicializa el cliente de Vertex AI Vector Search."""
        try:
            # Intentar importar bibliotecas de Vertex AI
            try:
                from google.cloud import aiplatform
                VERTEX_AI_AVAILABLE = True
            except ImportError:
                logger.warning("No se pudieron importar las bibliotecas de Vertex AI. Usando modo mock.")
                VERTEX_AI_AVAILABLE = False
                
            if not VERTEX_AI_AVAILABLE:
                return {"mock": True}
                
            # Inicializar cliente
            if self.credentials:
                aiplatform.init(
                    project=self.config.get("project_id"),
                    location=self.config.get("location"),
                    credentials=self.credentials
                )
            else:
                aiplatform.init(
                    project=self.config.get("project_id"),
                    location=self.config.get("location")
                )
                
            # Obtener o crear el endpoint del índice
            self._get_or_create_index_endpoint()
            
            # Obtener o crear el índice
            self._get_or_create_index()
            
            # Obtener o crear el índice desplegado
            self._get_or_deploy_index()
            
            return {
                "aiplatform": aiplatform,
                "mock": False
            }
        except Exception as e:
            logger.error(f"Error al inicializar cliente de Vertex AI Vector Search: {e}")
            return {"mock": True}
    
    def _get_or_create_index_endpoint(self):
        """Obtiene o crea el endpoint del índice."""
        try:
            # Verificar si el endpoint existe
            endpoints = aiplatform.MatchingEngineIndexEndpoint.list(
                filter=f'display_name="{self.config.get("index_endpoint_name")}"'
            )
            
            if endpoints:
                self.index_endpoint = endpoints[0]
                logger.info(f"Endpoint de índice existente encontrado: {self.index_endpoint.name}")
            else:
                # Crear nuevo endpoint
                self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
                    display_name=self.config.get("index_endpoint_name"),
                    description="Endpoint para NGX Agents Vector Search"
                )
                logger.info(f"Nuevo endpoint de índice creado: {self.index_endpoint.name}")
        except Exception as e:
            logger.error(f"Error al obtener/crear endpoint de índice: {e}")
            raise
    
    def _get_or_create_index(self):
        """Obtiene o crea el índice."""
        try:
            # Verificar si el índice existe
            indexes = aiplatform.MatchingEngineIndex.list(
                filter=f'display_name="{self.config.get("index_name")}"'
            )
            
            if indexes:
                self.index = indexes[0]
                logger.info(f"Índice existente encontrado: {self.index.name}")
            else:
                # Crear nuevo índice
                self.index = aiplatform.MatchingEngineIndex.create(
                    display_name=self.config.get("index_name"),
                    description="Índice para NGX Agents Vector Search",
                    dimensions=self.config.get("dimension"),
                    approximate_neighbors_count=self.config.get("approximate_neighbors_count"),
                    distance_measure_type=self.config.get("distance_measure"),
                    leaf_node_embedding_count=self.config.get("leaf_node_embedding_count"),
                    leaf_nodes_to_search_percent=self.config.get("leaf_nodes_to_search_percent")
                )
                logger.info(f"Nuevo índice creado: {self.index.name}")
        except Exception as e:
            logger.error(f"Error al obtener/crear índice: {e}")
            raise
    
    def _get_or_deploy_index(self):
        """Obtiene o despliega el índice en el endpoint."""
        try:
            # Verificar si el índice ya está desplegado
            deployed_indexes = self.index_endpoint.deployed_indexes
            
            for deployed_index in deployed_indexes:
                if deployed_index.index == self.index.name:
                    self.deployed_index = deployed_index
                    logger.info(f"Índice ya desplegado: {deployed_index.id}")
                    return
            
            # Desplegar el índice
            self.deployed_index = self.index_endpoint.deploy_index(
                index=self.index,
                deployed_index_id=self.config.get("deployed_index_id"),
                display_name=f"Deployed {self.config.get('index_name')}"
            )
            logger.info(f"Índice desplegado: {self.deployed_index.id}")
        except Exception as e:
            logger.error(f"Error al desplegar índice: {e}")
            raise
    
    @circuit_breaker(max_failures=3, reset_timeout=60)
    async def upsert(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Inserta o actualiza vectores en Vertex AI Vector Search.
        
        Args:
            vectors: Lista de vectores a insertar/actualizar
                Cada vector debe tener el formato:
                {
                    "id": "id_único",
                    "values": [0.1, 0.2, ...],
                    "metadata": {"key": "value", ...}
                }
            namespace: Namespace opcional (se implementa como restricción en Vertex AI)
            
        Returns:
            Dict: Resultado de la operación
        """
        span = telemetry_adapter.start_span("VertexVectorSearchClient.upsert", {
            "client.vectors_count": len(vectors),
            "client.namespace": namespace or "default"
        })
        
        try:
            # Actualizar estadísticas
            self.stats["upsert_operations"] += 1
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(0.1)  # Simular latencia
                result = {"upserted_count": len(vectors)}
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
            else:
                # Preparar datos para Vertex AI Vector Search
                datapoints = []
                for vector in vectors:
                    # Añadir namespace a los metadatos si se proporciona
                    metadata = vector.get("metadata", {}).copy()
                    if namespace:
                        metadata["namespace"] = namespace
                    
                    datapoint = {
                        "id": vector["id"],
                        "embedding": vector["values"],
                        "restricts": [{"namespace": namespace or "default"}] if namespace else None,
                        "crowding_tag": metadata.get("crowding_tag"),
                    }
                    
                    # Añadir metadatos como restricciones adicionales
                    if metadata:
                        for key, value in metadata.items():
                            if isinstance(value, (str, int, float, bool)):
                                if "restricts" not in datapoint or datapoint["restricts"] is None:
                                    datapoint["restricts"] = []
                                datapoint["restricts"].append({key: value})
                    
                    datapoints.append(datapoint)
                
                # Ejecutar operación de upsert
                # Convertir a operación asíncrona
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.index.upsert_datapoints(datapoints=datapoints)
                )
                
                # Formatear resultado
                result = {"upserted_count": len(vectors)}
                telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            self.stats["latency_ms"].append(latency_ms)
            if len(self.stats["latency_ms"]) > 100:
                self.stats["latency_ms"].pop(0)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.upserted_count", len(vectors))
            telemetry_adapter.record_metric("vertex_vector_search_client.latency", latency_ms, {"operation": "upsert"})
            
            return result
            
        except Exception as e:
            logger.error(f"Error al realizar upsert en Vertex AI Vector Search: {str(e)}")
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver resultado vacío en caso de error
            return {"error": str(e)}
            
        finally:
            telemetry_adapter.end_span(span)
    
    @circuit_breaker(max_failures=3, reset_timeout=60)
    async def query(self, vector: List[float], top_k: int = 10, namespace: Optional[str] = None, 
                  filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta vectores similares en Vertex AI Vector Search.
        
        Args:
            vector: Vector de consulta
            top_k: Número de resultados a retornar
            namespace: Namespace opcional
            filter: Filtro opcional para metadatos
            
        Returns:
            Dict: Resultados de la consulta
        """
        span = telemetry_adapter.start_span("VertexVectorSearchClient.query", {
            "client.top_k": top_k,
            "client.namespace": namespace or "default",
            "client.has_filter": filter is not None
        })
        
        try:
            # Actualizar estadísticas
            self.stats["query_operations"] += 1
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(0.1)  # Simular latencia
                
                # Generar resultados mock
                import random
                matches = []
                for i in range(min(top_k, 5)):  # Limitar a 5 resultados en modo mock
                    matches.append({
                        "id": f"mock_id_{i}",
                        "score": random.uniform(0.5, 1.0),
                        "metadata": {"mock": True}
                    })
                
                result = {"matches": matches}
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
            else:
                # Preparar restricciones (filtros)
                restricts = []
                
                # Añadir namespace como restricción si se proporciona
                if namespace:
                    restricts.append({"namespace": namespace})
                
                # Añadir filtros adicionales como restricciones
                if filter:
                    for key, value in filter.items():
                        restricts.append({key: value})
                
                # Ejecutar operación de consulta
                # Convertir a operación asíncrona
                loop = asyncio.get_event_loop()
                query_result = await loop.run_in_executor(
                    None,
                    lambda: self.deployed_index.find_neighbors(
                        query_embedding=vector,
                        num_neighbors=top_k,
                        restricts=restricts if restricts else None
                    )
                )
                
                # Formatear resultados para mantener compatibilidad con Pinecone
                matches = []
                for neighbor in query_result[0]:
                    # Extraer metadatos de las restricciones
                    metadata = {}
                    if hasattr(neighbor, "restricts") and neighbor.restricts:
                        for restrict in neighbor.restricts:
                            metadata.update(restrict)
                    
                    matches.append({
                        "id": neighbor.id,
                        "score": neighbor.distance,
                        "metadata": metadata
                    })
                
                result = {"matches": matches}
                telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            self.stats["latency_ms"].append(latency_ms)
            if len(self.stats["latency_ms"]) > 100:
                self.stats["latency_ms"].pop(0)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.results_count", len(result.get("matches", [])))
            telemetry_adapter.record_metric("vertex_vector_search_client.latency", latency_ms, {"operation": "query"})
            
            return result
            
        except Exception as e:
            logger.error(f"Error al realizar consulta en Vertex AI Vector Search: {str(e)}")
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver resultado vacío en caso de error
            return {"matches": []}
            
        finally:
            telemetry_adapter.end_span(span)
    
    @circuit_breaker(max_failures=3, reset_timeout=60)
    async def delete(self, ids: Optional[List[str]] = None, namespace: Optional[str] = None, 
                   filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Elimina vectores de Vertex AI Vector Search.
        
        Args:
            ids: Lista de IDs a eliminar (opcional)
            namespace: Namespace opcional
            filter: Filtro opcional para metadatos
            
        Returns:
            Dict: Resultado de la operación
        """
        span = telemetry_adapter.start_span("VertexVectorSearchClient.delete", {
            "client.ids_count": len(ids) if ids else 0,
            "client.namespace": namespace or "default",
            "client.has_filter": filter is not None,
            "client.delete_all": ids is None and filter is None
        })
        
        try:
            # Actualizar estadísticas
            self.stats["delete_operations"] += 1
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(0.1)  # Simular latencia
                result = {"deleted_count": len(ids) if ids else 10}
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
            else:
                # Ejecutar operación de eliminación
                # Convertir a operación asíncrona
                loop = asyncio.get_event_loop()
                
                if ids:
                    # Eliminar por IDs
                    result = await loop.run_in_executor(
                        None,
                        lambda: self.index.remove_datapoints(datapoint_ids=ids)
                    )
                    deleted_count = len(ids)
                elif filter or namespace:
                    # Eliminar por filtro o namespace
                    # Primero necesitamos buscar los IDs que coinciden con el filtro
                    # Usamos un vector aleatorio para la búsqueda
                    import random
                    random_vector = [random.uniform(-1, 1) for _ in range(self.config.get("dimension"))]
                    
                    # Preparar restricciones (filtros)
                    restricts = []
                    
                    # Añadir namespace como restricción si se proporciona
                    if namespace:
                        restricts.append({"namespace": namespace})
                    
                    # Añadir filtros adicionales como restricciones
                    if filter:
                        for key, value in filter.items():
                            restricts.append({key: value})
                    
                    # Buscar IDs que coinciden con el filtro
                    query_result = await loop.run_in_executor(
                        None,
                        lambda: self.deployed_index.find_neighbors(
                            query_embedding=random_vector,
                            num_neighbors=1000,  # Límite alto para obtener muchos resultados
                            restricts=restricts
                        )
                    )
                    
                    # Extraer IDs
                    ids_to_delete = [neighbor.id for neighbor in query_result[0]]
                    
                    if ids_to_delete:
                        # Eliminar por IDs
                        result = await loop.run_in_executor(
                            None,
                            lambda: self.index.remove_datapoints(datapoint_ids=ids_to_delete)
                        )
                        deleted_count = len(ids_to_delete)
                    else:
                        result = {"deleted_count": 0}
                        deleted_count = 0
                else:
                    # No se proporcionaron IDs ni filtros
                    result = {"error": "Se requiere proporcionar IDs o filtros para eliminar"}
                    deleted_count = 0
                
                # Formatear resultado
                result = {"deleted_count": deleted_count}
                telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            self.stats["latency_ms"].append(latency_ms)
            if len(self.stats["latency_ms"]) > 100:
                self.stats["latency_ms"].pop(0)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.record_metric("vertex_vector_search_client.latency", latency_ms, {"operation": "delete"})
            
            return result
            
        except Exception as e:
            logger.error(f"Error al eliminar vectores en Vertex AI Vector Search: {str(e)}")
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver resultado vacío en caso de error
            return {"error": str(e)}
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cliente.
        
        Returns:
            Dict[str, Any]: Estadísticas del cliente
        """
        # Calcular promedio de latencia
        avg_latency = sum(self.stats["latency_ms"]) / len(self.stats["latency_ms"]) if self.stats["latency_ms"] else 0
        
        # Obtener información del índice
        index_stats = {}
        if not self.client.get("mock", False) and self.index:
            try:
                # Convertir a operación asíncrona
                loop = asyncio.get_event_loop()
                index_stats = await loop.run_in_executor(
                    None,
                    lambda: {
                        "index_name": self.index.display_name,
                        "index_id": self.index.name,
                        "dimension": self.config.get("dimension"),
                        "distance_measure": self.config.get("distance_measure")
                    }
                )
            except Exception as e:
                logger.error(f"Error al obtener estadísticas del índice: {e}")
                index_stats = {"error": str(e)}
        
        return {
            "upsert_operations": self.stats["upsert_operations"],
            "query_operations": self.stats["query_operations"],
            "delete_operations": self.stats["delete_operations"],
            "errors": self.stats["errors"],
            "avg_latency_ms": avg_latency,
            "index_name": self.config.get("index_name"),
            "location": self.config.get("location"),
            "dimension": self.config.get("dimension"),
            "distance_measure": self.config.get("distance_measure"),
            "index_stats": index_stats,
            "mock_mode": self.client.get("mock", False)
        }

"""
Cliente para Pinecone Vector Database.

Este módulo proporciona un cliente para interactuar con Pinecone,
permitiendo almacenar, consultar y eliminar vectores de embeddings.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Union, Any

from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from core.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)
telemetry_adapter = get_telemetry_adapter()

class PineconeClient:
    """Cliente para Pinecone Vector Database."""
    
    def __init__(self, config=None):
        """Inicializa el cliente de Pinecone."""
        self.config = config or self._load_default_config()
        self.client = self._initialize_client()
        self.index = None
        
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
            "api_key": os.environ.get("PINECONE_API_KEY"),
            "environment": os.environ.get("PINECONE_ENVIRONMENT", "us-west1-gcp"),
            "index_name": os.environ.get("PINECONE_INDEX_NAME", "ngx-embeddings"),
            "dimension": get_env_int("PINECONE_DIMENSION", 3072),
            "metric": os.environ.get("PINECONE_METRIC", "cosine")
        }
        
    def _initialize_client(self) -> Any:
        """Inicializa el cliente de Pinecone."""
        try:
            # Intentar importar biblioteca de Pinecone
            try:
                import pinecone
                PINECONE_AVAILABLE = True
            except ImportError:
                logger.warning("No se pudo importar la biblioteca de Pinecone. Usando modo mock.")
                PINECONE_AVAILABLE = False
                
            if not PINECONE_AVAILABLE:
                return {"mock": True}
                
            # Inicializar cliente
            pinecone.init(
                api_key=self.config.get("api_key"),
                environment=self.config.get("environment")
            )
            
            # Verificar si el índice existe
            index_name = self.config.get("index_name")
            if index_name not in pinecone.list_indexes():
                # Crear índice si no existe
                pinecone.create_index(
                    name=index_name,
                    dimension=self.config.get("dimension"),
                    metric=self.config.get("metric")
                )
                logger.info(f"Índice '{index_name}' creado en Pinecone")
            
            # Conectar al índice
            self.index = pinecone.Index(index_name)
            
            return {
                "pinecone": pinecone,
                "mock": False
            }
        except Exception as e:
            logger.error(f"Error al inicializar cliente de Pinecone: {e}")
            return {"mock": True}
    
    @circuit_breaker(max_failures=3, reset_timeout=60)
    async def upsert(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Inserta o actualiza vectores en Pinecone.
        
        Args:
            vectors: Lista de vectores a insertar/actualizar
                Cada vector debe tener el formato:
                {
                    "id": "id_único",
                    "values": [0.1, 0.2, ...],
                    "metadata": {"key": "value", ...}
                }
            namespace: Namespace opcional
            
        Returns:
            Dict: Resultado de la operación
        """
        span = telemetry_adapter.start_span("PineconeClient.upsert", {
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
                # Ejecutar operación de upsert
                # Convertir a operación asíncrona
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.index.upsert(
                        vectors=vectors,
                        namespace=namespace
                    )
                )
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
            telemetry_adapter.record_metric("pinecone_client.latency", latency_ms, {"operation": "upsert"})
            
            return result
            
        except Exception as e:
            logger.error(f"Error al realizar upsert en Pinecone: {str(e)}")
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
        Consulta vectores similares en Pinecone.
        
        Args:
            vector: Vector de consulta
            top_k: Número de resultados a retornar
            namespace: Namespace opcional
            filter: Filtro opcional para metadatos
            
        Returns:
            Dict: Resultados de la consulta
        """
        span = telemetry_adapter.start_span("PineconeClient.query", {
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
                # Ejecutar operación de consulta
                # Convertir a operación asíncrona
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.index.query(
                        vector=vector,
                        top_k=top_k,
                        namespace=namespace,
                        filter=filter,
                        include_metadata=True
                    )
                )
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
            telemetry_adapter.record_metric("pinecone_client.latency", latency_ms, {"operation": "query"})
            
            return result
            
        except Exception as e:
            logger.error(f"Error al realizar consulta en Pinecone: {str(e)}")
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
        Elimina vectores de Pinecone.
        
        Args:
            ids: Lista de IDs a eliminar (opcional)
            namespace: Namespace opcional
            filter: Filtro opcional para metadatos
            
        Returns:
            Dict: Resultado de la operación
        """
        span = telemetry_adapter.start_span("PineconeClient.delete", {
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
                result = await loop.run_in_executor(
                    None,
                    lambda: self.index.delete(
                        ids=ids,
                        namespace=namespace,
                        filter=filter
                    )
                )
                telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            self.stats["latency_ms"].append(latency_ms)
            if len(self.stats["latency_ms"]) > 100:
                self.stats["latency_ms"].pop(0)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.record_metric("pinecone_client.latency", latency_ms, {"operation": "delete"})
            
            return result
            
        except Exception as e:
            logger.error(f"Error al eliminar vectores en Pinecone: {str(e)}")
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
                    lambda: self.index.describe_index_stats()
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
            "environment": self.config.get("environment"),
            "dimension": self.config.get("dimension"),
            "metric": self.config.get("metric"),
            "index_stats": index_stats,
            "mock_mode": self.client.get("mock", False)
        }

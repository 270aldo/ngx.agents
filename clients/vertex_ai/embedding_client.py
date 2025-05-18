"""
Cliente para Vertex AI Embeddings.

Este módulo proporciona un cliente para generar embeddings utilizando
Vertex AI, con soporte para caché, batch processing y manejo de errores.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Union, Any

from google.cloud import aiplatform
from google.oauth2 import service_account

from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter
from core.circuit_breaker import circuit_breaker
from clients.vertex_ai.cache import CacheManager, CachePolicy

logger = logging.getLogger(__name__)
telemetry_adapter = get_telemetry_adapter()

class EmbeddingClient:
    """Cliente para Vertex AI Embeddings."""
    
    def __init__(self, config=None):
        """Inicializa el cliente de embeddings."""
        self.config = config or self._load_default_config()
        self.credentials = self._initialize_credentials()
        self.client = self._initialize_client()
        
        # Inicializar caché avanzado
        self.cache = CacheManager(
            use_redis=self.config.get("use_redis_cache", False),
            redis_url=self.config.get("redis_url"),
            ttl=self.config.get("cache_ttl", 3600),
            max_memory_size=self.config.get("max_cache_size", 1000),
            cache_policy=CachePolicy.LRU,
            partitions=self.config.get("cache_partitions", 4),
            l1_size_ratio=self.config.get("l1_size_ratio", 0.3),
            prefetch_threshold=self.config.get("prefetch_threshold", 0.7),
            compression_threshold=self.config.get("compression_threshold", 1024),
            compression_level=self.config.get("compression_level", 6),
            enable_telemetry=True
        )
        
        self.model_name = self.config.get("model_name", "text-embedding-large-exp-03-07")
        self.namespace = "embeddings"
        
        # Estadísticas
        self.stats = {
            "embedding_requests": 0,
            "batch_embedding_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
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
            "model_name": os.environ.get("VERTEX_EMBEDDING_MODEL", "textembedding-gecko"),
            "use_redis_cache": os.environ.get("USE_REDIS_CACHE", "false").lower() == "true",
            "redis_url": os.environ.get("REDIS_URL"),
            "cache_ttl": get_env_int("EMBEDDING_CACHE_TTL", 86400),  # 24 horas por defecto
            "max_cache_size": get_env_int("EMBEDDING_MAX_CACHE_SIZE", 1000),
            "cache_partitions": get_env_int("EMBEDDING_CACHE_PARTITIONS", 4),
            "l1_size_ratio": float(os.environ.get("EMBEDDING_L1_SIZE_RATIO", "0.3")),
            "prefetch_threshold": float(os.environ.get("EMBEDDING_PREFETCH_THRESHOLD", "0.7")),
            "compression_threshold": get_env_int("EMBEDDING_COMPRESSION_THRESHOLD", 1024),
            "compression_level": get_env_int("EMBEDDING_COMPRESSION_LEVEL", 6)
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
        """Inicializa el cliente de Vertex AI."""
        try:
            # Intentar importar bibliotecas de Vertex AI
            try:
                from vertexai.language_models import TextEmbeddingModel
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
                
            # Crear modelo de embeddings
            embedding_model = TextEmbeddingModel.from_pretrained(self.model_name)
            
            return {
                "embedding_model": embedding_model,
                "mock": False
            }
        except Exception as e:
            logger.error(f"Error al inicializar cliente de Vertex AI: {e}")
            return {"mock": True}
    
    def _get_cache_key(self, text: str, namespace: Optional[str] = None) -> str:
        """
        Genera una clave de caché para un texto.
        
        Args:
            text: Texto para generar la clave
            namespace: Namespace opcional
            
        Returns:
            str: Clave de caché
        """
        # Usar xxhash si está disponible (más rápido)
        try:
            import xxhash
            hash_func = lambda x: xxhash.xxh64(x).hexdigest()
        except ImportError:
            # Alternativa con hashlib
            hash_func = lambda x: hashlib.md5(x).hexdigest()
        
        # Generar hash del contenido
        content_hash = hash_func(text.encode('utf-8'))
        
        # Construir clave con formato para patrones de invalidación
        prefix = "embedding"
        if namespace:
            prefix = f"{prefix}:{namespace}"
            
        return f"{prefix}:{content_hash}"
        
    @circuit_breaker(max_failures=3, reset_timeout=60)
    async def generate_embedding(self, text: str, namespace: Optional[str] = None) -> List[float]:
        """
        Genera un embedding para el texto proporcionado.
        
        Args:
            text: Texto para generar el embedding
            namespace: Namespace opcional para caché
            
        Returns:
            Lista de valores float que representan el embedding
        """
        span = telemetry_adapter.start_span("EmbeddingClient.generate_embedding", {
            "client.text_length": len(text),
            "client.namespace": namespace or self.namespace
        })
        
        try:
            # Actualizar estadísticas
            self.stats["embedding_requests"] += 1
            
            # Verificar caché
            cache_key = self._get_cache_key(text, namespace or self.namespace)
            
            # Intentar obtener de caché
            cached = await self.cache.get(cache_key)
            if cached:
                self.stats["cache_hits"] += 1
                telemetry_adapter.set_span_attribute(span, "client.cache", "hit")
                return cached
                
            self.stats["cache_misses"] += 1
            telemetry_adapter.set_span_attribute(span, "client.cache", "miss")
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(0.1)  # Simular latencia
                
                # Generar embedding aleatorio de 768 dimensiones
                import random
                embedding = [random.uniform(-1, 1) for _ in range(768)]
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
            else:
                # Generar embedding con Vertex AI
                model = self.client["embedding_model"]
                result = model.get_embeddings([text])[0]
                embedding = result.values
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            self.stats["latency_ms"].append(latency_ms)
            if len(self.stats["latency_ms"]) > 100:
                self.stats["latency_ms"].pop(0)
            
            # Guardar en caché
            await self.cache.set(cache_key, embedding)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.dimensions", len(embedding))
            telemetry_adapter.record_metric("embedding_client.latency", latency_ms, {"operation": "embedding"})
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error al generar embedding: {str(e)}")
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver un embedding vacío en caso de error
            return [0.0] * 768
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def batch_generate_embeddings(self, texts: List[str], namespace: Optional[str] = None) -> List[List[float]]:
        """
        Genera embeddings para múltiples textos en batch.
        
        Args:
            texts: Lista de textos para generar embeddings
            namespace: Namespace opcional para caché
            
        Returns:
            Lista de embeddings (cada uno es una lista de floats)
        """
        span = telemetry_adapter.start_span("EmbeddingClient.batch_generate_embeddings", {
            "client.texts_count": len(texts),
            "client.total_length": sum(len(t) for t in texts),
            "client.namespace": namespace or self.namespace
        })
        
        try:
            # Actualizar estadísticas
            self.stats["batch_embedding_requests"] += 1
            
            # Verificar caché para cada texto
            embeddings = []
            texts_to_embed = []
            indices_to_embed = []
            
            # Verificar caché para cada texto
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text, namespace or self.namespace)
                
                # Intentar obtener de caché
                cached = await self.cache.get(cache_key)
                if cached:
                    self.stats["cache_hits"] += 1
                    embeddings.append(cached)
                    continue
                
                self.stats["cache_misses"] += 1
                texts_to_embed.append(text)
                indices_to_embed.append(i)
                embeddings.append(None)
            
            # Si todos los embeddings están en caché, retornar
            if all(e is not None for e in embeddings):
                telemetry_adapter.set_span_attribute(span, "client.cache", "all_hit")
                return embeddings
            
            telemetry_adapter.set_span_attribute(span, "client.cache", "partial_hit")
            telemetry_adapter.set_span_attribute(span, "client.texts_to_embed", len(texts_to_embed))
            
            start_time = time.time()
            
            # Verificar si estamos en modo mock
            if self.client.get("mock", False):
                await asyncio.sleep(0.2)  # Simular latencia
                
                # Generar embeddings aleatorios
                import random
                new_embeddings = [[random.uniform(-1, 1) for _ in range(768)] for _ in range(len(texts_to_embed))]
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
            else:
                # Generar embeddings con Vertex AI
                model = self.client["embedding_model"]
                results = model.get_embeddings(texts_to_embed)
                new_embeddings = [result.values for result in results]
                
                telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            self.stats["latency_ms"].append(latency_ms)
            if len(self.stats["latency_ms"]) > 100:
                self.stats["latency_ms"].pop(0)
            
            # Actualizar lista de embeddings y caché
            for i, embedding in zip(indices_to_embed, new_embeddings):
                embeddings[i] = embedding
                
                # Guardar en caché
                cache_key = self._get_cache_key(texts[i], namespace or self.namespace)
                await self.cache.set(cache_key, embedding)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.batch_size", len(texts_to_embed))
            telemetry_adapter.record_metric("embedding_client.latency", latency_ms, {"operation": "batch_embedding"})
            telemetry_adapter.record_metric("embedding_client.batch_size", len(texts_to_embed), {"operation": "embedding"})
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error al generar embeddings en batch: {str(e)}")
            self.stats["errors"] += 1
            telemetry_adapter.record_exception(span, e)
            
            # Devolver embeddings vacíos en caso de error
            return [[0.0] * 768 for _ in range(len(texts))]
            
        finally:
            telemetry_adapter.end_span(span)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cliente.
        
        Returns:
            Dict[str, Any]: Estadísticas del cliente
        """
        # Obtener estadísticas de caché
        cache_stats = await self.cache.get_stats()
        
        # Calcular promedio de latencia
        avg_latency = sum(self.stats["latency_ms"]) / len(self.stats["latency_ms"]) if self.stats["latency_ms"] else 0
        
        return {
            "embedding_requests": self.stats["embedding_requests"],
            "batch_embedding_requests": self.stats["batch_embedding_requests"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "errors": self.stats["errors"],
            "avg_latency_ms": avg_latency,
            "cache": cache_stats,
            "model_name": self.model_name,
            "namespace": self.namespace
        }
    
    async def flush_cache(self) -> bool:
        """
        Limpia la caché del cliente.
        
        Returns:
            bool: True si se limpió correctamente
        """
        try:
            await self.cache.flush()
            return True
        except Exception as e:
            logger.error(f"Error al limpiar caché: {e}")
            return False

"""
Cliente optimizado para Vertex AI.

Este módulo implementa un cliente centralizado para interactuar con Vertex AI,
proporcionando funcionalidades para generación de texto, embeddings y
procesamiento multimodal con caché avanzado, pooling de conexiones y telemetría detallada.
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Union

from core.logging_config import get_logger
from infrastructure.adapters.telemetry_adapter import get_telemetry_adapter, measure_execution_time

# Configurar logger
logger = get_logger(__name__)
telemetry_adapter = get_telemetry_adapter()

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

# Intentar importar bibliotecas de Vertex AI
try:
    import google.auth
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part
    from vertexai.language_models import TextEmbeddingModel
    from google.cloud import aiplatform
    from google.cloud import documentai_v1 as documentai
    from google.cloud import speech
    from google.cloud import texttospeech
    VERTEX_AI_AVAILABLE = True
except ImportError:
    logger.warning("No se pudieron importar las bibliotecas de Vertex AI. Usando modo mock.")
    VERTEX_AI_AVAILABLE = False
    # Mock objects para cuando las bibliotecas no están disponibles
    class GenerativeModel: pass
    class Part: pass
    class TextEmbeddingModel: pass
    class documentai:
        class DocumentProcessorServiceClient: pass
        class RawDocument: pass
        class ProcessRequest: pass

# Componentes locales refactorizados
from .cache import CacheManager
from .connection import ConnectionPool
from .decorators import with_retries

class VertexAIClient:
    """
    Cliente Vertex AI optimizado con telemetría integrada, pool de conexiones,
    caché avanzado y soporte multimodal.
    """
    
    def __init__(self, 
                 use_redis_cache=False,
                 redis_url=None,
                 cache_ttl=3600,
                 max_cache_size=1000,
                 max_connections=10,
                 cache_policy="hybrid",
                 cache_partitions=4,
                 l1_size_ratio=0.2,
                 prefetch_threshold=0.8,
                 compression_threshold=1024,
                 compression_level=6):
        """
        Inicializa el cliente con soporte para estrategias avanzadas de caché.
        
        Args:
            use_redis_cache: Si True, usa Redis para caché si está disponible
            redis_url: URL de conexión a Redis (opcional)
            cache_ttl: Tiempo de vida para entradas de caché (segundos)
            max_cache_size: Tamaño máximo del caché en memoria (MB)
            max_connections: Máximo de conexiones en el pool
            cache_policy: Política de caché ("lru", "lfu", "fifo", "hybrid")
            cache_partitions: Número de particiones para el caché
            l1_size_ratio: Proporción del tamaño para caché L1 (memoria)
            prefetch_threshold: Umbral de accesos para precarga
            compression_threshold: Tamaño mínimo para comprimir valores (bytes)
            compression_level: Nivel de compresión (1-9, 9 es máximo)
        """
        self._initialized = False
        self.is_initialized = False
        
        # Inicializar caché con estrategias avanzadas
        from .cache import CachePolicy
        
        # Convertir string de política a enum
        policy_map = {
            "lru": CachePolicy.LRU,
            "lfu": CachePolicy.LFU,
            "fifo": CachePolicy.FIFO,
            "hybrid": CachePolicy.HYBRID,
            "ttl": CachePolicy.TTL
        }
        cache_policy_enum = policy_map.get(cache_policy.lower(), CachePolicy.HYBRID)
        
        # Crear gestor de caché avanzado
        self.cache_manager = CacheManager(
            use_redis=use_redis_cache,
            redis_url=redis_url,
            ttl=cache_ttl,
            max_memory_size=max_cache_size,
            cache_policy=cache_policy_enum,
            partitions=cache_partitions,
            l1_size_ratio=l1_size_ratio,
            prefetch_threshold=prefetch_threshold,
            compression_threshold=compression_threshold,
            compression_level=compression_level,
            enable_telemetry=True
        )
        
        # Inicializar pool de conexiones
        self.connection_pool = ConnectionPool(
            max_size=max_connections,
            init_size=2,
            ttl=600  # 10 minutos
        )
        
        # Lock para inicialización
        self._init_lock = asyncio.Lock()
        
        # Estadísticas
        self.stats = {
            "content_requests": 0,
            "embedding_requests": 0,
            "multimodal_requests": 0,
            "batch_embedding_requests": 0,
            "document_requests": 0,
            "latency_ms": {},
            "tokens": {
                "prompt": 0,
                "completion": 0,
                "total": 0
            },
            "errors": {}
        }
    
    @measure_execution_time("vertex_ai.client.initialize")
    async def initialize(self) -> bool:
        """
        Inicializa el cliente.
        
        Returns:
            bool: True si la inicialización fue exitosa
        """
        async with self._init_lock:
            if self._initialized:
                return True
                
            span = telemetry_adapter.start_span("VertexAIClient.initialize")
            try:
                telemetry_adapter.add_span_event(span, "initialization_start")
                
                # Inicializar pool de conexiones
                await self.connection_pool.initialize()
                
                self._initialized = True
                self.is_initialized = True
                
                telemetry_adapter.set_span_attribute(span, "initialization_status", "success")
                telemetry_adapter.record_metric("vertex_ai.client.initializations", 1, {"status": "success"})
                logger.info("VertexAIClient inicializado.")
                return True
            except Exception as e:
                telemetry_adapter.record_exception(span, e)
                telemetry_adapter.set_span_attribute(span, "initialization_status", "failure")
                telemetry_adapter.record_metric("vertex_ai.client.initializations", 1, {"status": "failure"})
                logger.error(f"Error durante la inicialización del cliente VertexAI: {e}")
                return False
            finally:
                telemetry_adapter.end_span(span)
    
    async def _ensure_initialized(self) -> None:
        """Asegura que el cliente esté inicializado."""
        if not self._initialized:
            await self.initialize()
    
    def _get_cache_key(self, data: Any, operation: str = None, namespace: str = None) -> str:
        """
        Genera una clave de caché para los datos con soporte para patrones de invalidación.
        
        Args:
            data: Datos para generar la clave
            operation: Operación relacionada con los datos (ej: "generate_content", "embedding")
            namespace: Espacio de nombres para agrupar claves relacionadas
            
        Returns:
            str: Clave de caché con formato que soporta patrones de invalidación
        """
        # Usar xxhash si está disponible (más rápido)
        try:
            import xxhash
            hash_func = lambda x: xxhash.xxh64(x).hexdigest()
        except ImportError:
            # Alternativa con hashlib
            hash_func = lambda x: hashlib.md5(x).hexdigest()
        
        # Convertir a JSON y generar hash
        if isinstance(data, str):
            serialized = data
        else:
            serialized = json.dumps(data, sort_keys=True)
        
        # Generar hash del contenido
        content_hash = hash_func(serialized.encode('utf-8'))
        
        # Construir clave con formato para patrones de invalidación
        prefix = "vertex"
        if namespace:
            prefix = f"{prefix}:{namespace}"
        if operation:
            prefix = f"{prefix}:{operation}"
            
        return f"{prefix}:{content_hash}"

    @measure_execution_time("vertex_ai.client.generate_content")
    @with_retries(max_retries=3, base_delay=1.0, backoff_factor=2)
    async def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        cache_namespace: Optional[str] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Genera contenido de texto usando el modelo de lenguaje con soporte para caché avanzado.
        
        Args:
            prompt: Prompt para el modelo
            system_instruction: Instrucción de sistema (opcional)
            temperature: Temperatura para la generación (0.0-1.0)
            max_output_tokens: Límite de tokens de salida
            top_p: Parámetro top_p para muestreo
            top_k: Parámetro top_k para muestreo
            cache_namespace: Espacio de nombres para agrupar claves relacionadas (opcional)
            skip_cache: Si es True, omite la caché y siempre realiza la llamada a la API
            
        Returns:
            Dict[str, Any]: Respuesta generada y metadatos
        """
        await self._ensure_initialized()
        
        span_attributes = {
            "client.prompt_length": len(prompt),
            "client.temperature": temperature,
            "client.has_system_instruction": system_instruction is not None,
        }
        if max_output_tokens is not None: span_attributes["client.max_output_tokens"] = max_output_tokens
        if top_p is not None: span_attributes["client.top_p"] = top_p
        if top_k is not None: span_attributes["client.top_k"] = top_k
        
        span = telemetry_adapter.start_span("VertexAIClient.generate_content", attributes=span_attributes)
        
        try:
            telemetry_adapter.add_span_event(span, "generation.start")
            self.stats["content_requests"] += 1
            
            # Verificar caché
            await self._ensure_initialized()
        
            # Preparar datos para caché
            cache_data = {
                "prompt": prompt,
                "system_instruction": system_instruction,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "top_p": top_p,
                "top_k": top_k
            }
        
            # Generar clave de caché con soporte para patrones de invalidación
            cache_key = self._get_cache_key(
                data=cache_data,
                operation="generate_content",
                namespace=cache_namespace
            )
        
            # Intentar obtener de caché (a menos que se indique omitirla)
            if not skip_cache:
                cached_response = await self.cache_manager.get(cache_key)
                if cached_response:
                    self.stats["latency_ms"].setdefault("content_generation", []).append(0)  # 0ms desde caché
                    # Usar set_span_attribute en lugar de record_event para compatibilidad
                    telemetry_adapter.set_span_attribute(span, "cache.hit", True)
                    telemetry_adapter.set_span_attribute(span, "cache.operation", "generate_content")
                    telemetry_adapter.set_span_attribute(span, "cache.namespace", cache_namespace or "default")
                    telemetry_adapter.set_span_attribute(span, "client.cache", "hit")
                    telemetry_adapter.record_metric("vertex_ai.client.cache_hits", 1, {"operation": "content"})
                    return cached_response
                
            telemetry_adapter.add_span_event(span, "generation.cache_miss")
            telemetry_adapter.set_span_attribute(span, "client.cache", "miss")
            telemetry_adapter.record_metric("vertex_ai.client.cache_misses", 1, {"operation": "content"})
            
            start_time = time.time()
            
            # Adquirir cliente del pool
            client = await self.connection_pool.acquire()
            
            try:
                # Modo mock si no está disponible Vertex AI
                if client.get("mock", False):
                    await asyncio.sleep(0.2)  # Simular latencia
                    
                    mock_response = {
                        "text": f"[MOCK] Respuesta simulada para: {prompt[:50]}...",
                        "finish_reason": "STOP",
                        "usage": {
                            "prompt_tokens": len(prompt) // 4,
                            "completion_tokens": 20,
                            "total_tokens": (len(prompt) // 4) + 20
                        }
                    }
                    
                    telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
                    response = mock_response
                else:
                    # Configurar generación
                    generation_config = {}
                    if temperature is not None: generation_config["temperature"] = temperature
                    if max_output_tokens is not None: generation_config["max_output_tokens"] = max_output_tokens
                    if top_p is not None: generation_config["top_p"] = top_p
                    if top_k is not None: generation_config["top_k"] = top_k
                    
                    # Generar contenido
                    model = client["text_model"]
                    
                    if system_instruction:
                        result = model.generate_content(
                            prompt,
                            generation_config=generation_config,
                            system_instruction=system_instruction
                        )
                    else:
                        result = model.generate_content(
                            prompt,
                            generation_config=generation_config
                        )
                    
                    # Procesar respuesta
                    response = {
                        "text": result.text,
                        "finish_reason": result.candidates[0].finish_reason.name if result.candidates else "STOP",
                        "usage": {
                            "prompt_tokens": result.usage_metadata.prompt_token_count if hasattr(result, "usage_metadata") else 0,
                            "completion_tokens": result.usage_metadata.candidates_token_count if hasattr(result, "usage_metadata") else 0,
                            "total_tokens": result.usage_metadata.total_token_count if hasattr(result, "usage_metadata") else 0
                        }
                    }
                    
                    telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            finally:
                # Liberar cliente al pool
                await self.connection_pool.release(client)
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            
            op_latencies = self.stats["latency_ms"].setdefault("content_generation", [])
            op_latencies.append(latency_ms)
            if len(op_latencies) > 100:
                op_latencies.pop(0)

            self.stats["tokens"]["prompt"] += response["usage"]["prompt_tokens"]
            self.stats["tokens"]["completion"] += response["usage"]["completion_tokens"]
            self.stats["tokens"]["total"] += response["usage"]["total_tokens"]
            
            # Guardar en caché
            await self.cache_manager.set(cache_key, response)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.tokens.total", response["usage"]["total_tokens"])
            telemetry_adapter.record_metric("vertex_ai.client.latency", latency_ms, {"operation": "content_generation"})
            telemetry_adapter.record_metric("vertex_ai.client.tokens", response["usage"]["total_tokens"], {"type": "total"})
            
            return response
            
        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count
            
            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "client.error", str(e))
            telemetry_adapter.record_metric("vertex_ai.client.errors", 1, {"operation": "content_generation", "error_type": error_type})
            
            logger.error(f"Error al generar contenido: {str(e)}")
            
            return {
                "text": f"Error: {str(e)}",
                "finish_reason": "ERROR",
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                "error": str(e)
            }
            
        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("vertex_ai.client.generate_embedding")
    @with_retries(max_retries=2, base_delay=0.5, backoff_factor=2)
    async def generate_embedding(self, text: str) -> Dict[str, Any]:
        """
        Genera un embedding para un texto.
        
        Args:
            text: Texto para generar embedding
            
        Returns:
            Dict[str, Any]: Embedding generado y metadatos
        """
        await self._ensure_initialized()
        
        span = telemetry_adapter.start_span("VertexAIClient.generate_embedding", {
            "client.text_length": len(text)
        })
        
        try:
            telemetry_adapter.add_span_event(span, "embedding.start")
            self.stats["embedding_requests"] += 1
            
            # Verificar caché
            cache_key = self._get_cache_key({
                "type": "embedding",
                "text": text
            })
            
            # Intentar obtener de caché
            cached = await self.cache_manager.get(cache_key)
            if cached:
                telemetry_adapter.add_span_event(span, "embedding.cache_hit")
                telemetry_adapter.set_span_attribute(span, "client.cache", "hit")
                telemetry_adapter.record_metric("vertex_ai.client.cache_hits", 1, {"operation": "embedding"})
                return cached
                
            telemetry_adapter.add_span_event(span, "embedding.cache_miss")
            telemetry_adapter.set_span_attribute(span, "client.cache", "miss")
            telemetry_adapter.record_metric("vertex_ai.client.cache_misses", 1, {"operation": "embedding"})
            
            start_time = time.time()
            
            # Adquirir cliente del pool
            client = await self.connection_pool.acquire()
            
            try:
                # Modo mock si no está disponible Vertex AI
                if client.get("mock", False):
                    await asyncio.sleep(0.1)  # Simular latencia
                    
                    # Generar embedding aleatorio de 768 dimensiones
                    import random
                    vector = [random.uniform(-1, 1) for _ in range(768)]
                    
                    mock_response = {
                        "embedding": vector,
                        "dimensions": 768,
                        "model": "mock-embedding-model"
                    }
                    
                    telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
                    response = mock_response
                else:
                    # Generar embedding
                    model = client["embedding_model"]
                    result = model.get_embeddings([text])[0]
                    
                    response = {
                        "embedding": result.values,
                        "dimensions": len(result.values),
                        "model": model.model_name
                    }
                    
                    telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            finally:
                # Liberar cliente al pool
                await self.connection_pool.release(client)
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            
            op_latencies = self.stats["latency_ms"].setdefault("embedding", [])
            op_latencies.append(latency_ms)
            if len(op_latencies) > 100:
                op_latencies.pop(0)
            
            # Guardar en caché
            await self.cache_manager.set(cache_key, response)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.dimensions", response["dimensions"])
            telemetry_adapter.record_metric("vertex_ai.client.latency", latency_ms, {"operation": "embedding"})
            
            return response
            
        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count
            
            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "client.error", str(e))
            telemetry_adapter.record_metric("vertex_ai.client.errors", 1, {"operation": "embedding", "error_type": error_type})
            
            logger.error(f"Error al generar embedding: {str(e)}")
            
            return {
                "error": str(e),
                "embedding": [],
                "dimensions": 0
            }
            
        finally:
            telemetry_adapter.end_span(span)
    @measure_execution_time("vertex_ai.client.batch_embeddings")
    @with_retries(max_retries=2, base_delay=0.5, backoff_factor=2)
    async def batch_embeddings(self, texts: List[str]) -> Dict[str, Any]:
        """
        Genera embeddings para múltiples textos en un solo batch.
        
        Args:
            texts: Lista de textos para generar embeddings
            
        Returns:
            Dict[str, Any]: Embeddings generados y metadatos
        """
        await self._ensure_initialized()
        
        span = telemetry_adapter.start_span("VertexAIClient.batch_embeddings", {
            "client.texts_count": len(texts),
            "client.total_length": sum(len(t) for t in texts)
        })
        
        try:
            telemetry_adapter.add_span_event(span, "batch_embedding.start")
            self.stats["batch_embedding_requests"] += 1
            
            # No usar caché para batches por complejidad
            
            start_time = time.time()
            
            # Adquirir cliente del pool
            client = await self.connection_pool.acquire()
            
            try:
                # Modo mock si no está disponible Vertex AI
                if client.get("mock", False):
                    await asyncio.sleep(0.2)  # Simular latencia
                    
                    # Generar embeddings aleatorios
                    import random
                    vectors = [[random.uniform(-1, 1) for _ in range(768)] for _ in range(len(texts))]
                    
                    mock_response = {
                        "embeddings": vectors,
                        "dimensions": 768,
                        "count": len(texts),
                        "model": "mock-embedding-model"
                    }
                    
                    telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
                    response = mock_response
                else:
                    # Generar embeddings
                    model = client["embedding_model"]
                    results = model.get_embeddings(texts)
                    
                    vectors = [result.values for result in results]
                    
                    response = {
                        "embeddings": vectors,
                        "dimensions": len(vectors[0]) if vectors else 0,
                        "count": len(vectors),
                        "model": model.model_name
                    }
                    
                    telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            finally:
                # Liberar cliente al pool
                await self.connection_pool.release(client)
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            
            op_latencies = self.stats["latency_ms"].setdefault("batch_embedding", [])
            op_latencies.append(latency_ms)
            if len(op_latencies) > 100:
                op_latencies.pop(0)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.batch_size", len(texts))
            telemetry_adapter.record_metric("vertex_ai.client.latency", latency_ms, {"operation": "batch_embedding"})
            telemetry_adapter.record_metric("vertex_ai.client.batch_size", len(texts), {"operation": "embedding"})
            
            return response
            
        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count
            
            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "client.error", str(e))
            telemetry_adapter.record_metric("vertex_ai.client.errors", 1, {"operation": "batch_embedding", "error_type": error_type})
            
            logger.error(f"Error al generar embeddings en batch: {str(e)}")
            
            return {
                "error": str(e),
                "embeddings": [],
                "dimensions": 0,
                "count": 0
            }
            
        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("vertex_ai.client.process_multimodal")
    @with_retries(max_retries=2, base_delay=1.0, backoff_factor=2)
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
        await self._ensure_initialized()
        
        # Determinar el tipo de imagen
        is_base64 = isinstance(image_data, str)
        image_size = len(image_data)
        
        span = telemetry_adapter.start_span("VertexAIClient.process_multimodal", {
            "client.prompt_length": len(prompt),
            "client.image_size": image_size,
            "client.image_format": "base64" if is_base64 else "bytes",
            "client.temperature": temperature
        })
        
        try:
            telemetry_adapter.add_span_event(span, "multimodal.start")
            self.stats["multimodal_requests"] += 1
            
            # Verificar caché solo si la imagen es base64
            cache_key = None
            if is_base64:
                cache_key = self._get_cache_key({
                    "type": "multimodal",
                    "prompt": prompt,
                    "image_hash": hashlib.md5(image_data.encode() if isinstance(image_data, str) else image_data).hexdigest(),
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens
                })
                
                # Intentar obtener de caché
                cached = await self.cache_manager.get(cache_key)
                if cached:
                    telemetry_adapter.add_span_event(span, "multimodal.cache_hit")
                    telemetry_adapter.set_span_attribute(span, "client.cache", "hit")
                    telemetry_adapter.record_metric("vertex_ai.client.cache_hits", 1, {"operation": "multimodal"})
                    return cached
            
            if cache_key:
                telemetry_adapter.add_span_event(span, "multimodal.cache_miss")
                telemetry_adapter.set_span_attribute(span, "client.cache", "miss")
                telemetry_adapter.record_metric("vertex_ai.client.cache_misses", 1, {"operation": "multimodal"})
            
            start_time = time.time()
            
            # Adquirir cliente del pool
            client = await self.connection_pool.acquire()
            
            try:
                # Modo mock si no está disponible Vertex AI
                if client.get("mock", False):
                    await asyncio.sleep(0.5)  # Simular latencia
                    
                    mock_response = {
                        "text": f"[MOCK] Análisis de imagen con prompt: {prompt[:30]}...",
                        "finish_reason": "STOP",
                        "usage": {
                            "prompt_tokens": len(prompt) // 4 + 1000,  # Estimar tokens de imagen
                            "completion_tokens": 50,
                            "total_tokens": (len(prompt) // 4) + 1000 + 50
                        }
                    }
                    
                    telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
                    response = mock_response
                else:
                    # Preparar imagen
                    if is_base64:
                        # Convertir base64 a bytes
                        if "base64," in image_data:
                            image_data = image_data.split("base64,")[1]
                        image_bytes = base64.b64decode(image_data)
                    else:
                        image_bytes = image_data
                    
                    # Crear parte de imagen
                    image_part = Part.from_data(mime_type="image/jpeg", data=image_bytes)
                    
                    # Configurar generación
                    generation_config = {}
                    if temperature is not None: generation_config["temperature"] = temperature
                    if max_output_tokens is not None: generation_config["max_output_tokens"] = max_output_tokens
                    
                    # Generar contenido
                    model = client["multimodal_model"]
                    result = model.generate_content(
                        [prompt, image_part],
                        generation_config=generation_config
                    )
                    
                    # Procesar respuesta
                    response = {
                        "text": result.text,
                        "finish_reason": result.candidates[0].finish_reason.name if result.candidates else "STOP",
                        "usage": {
                            "prompt_tokens": result.usage_metadata.prompt_token_count if hasattr(result, "usage_metadata") else 0,
                            "completion_tokens": result.usage_metadata.candidates_token_count if hasattr(result, "usage_metadata") else 0,
                            "total_tokens": result.usage_metadata.total_token_count if hasattr(result, "usage_metadata") else 0
                        }
                    }
                    
                    telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            finally:
                # Liberar cliente al pool
                await self.connection_pool.release(client)
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            
            op_latencies = self.stats["latency_ms"].setdefault("multimodal", [])
            op_latencies.append(latency_ms)
            if len(op_latencies) > 100:
                op_latencies.pop(0)
                
            self.stats["tokens"]["prompt"] += response["usage"]["prompt_tokens"]
            self.stats["tokens"]["completion"] += response["usage"]["completion_tokens"]
            self.stats["tokens"]["total"] += response["usage"]["total_tokens"]
            
            # Guardar en caché si tenemos clave
            if cache_key:
                await self.cache_manager.set(cache_key, response)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.tokens.total", response["usage"]["total_tokens"])
            telemetry_adapter.record_metric("vertex_ai.client.latency", latency_ms, {"operation": "multimodal"})
            telemetry_adapter.record_metric("vertex_ai.client.tokens", response["usage"]["total_tokens"], {"type": "total", "operation": "multimodal"})
            
            return response
            
        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count
            
            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "client.error", str(e))
            telemetry_adapter.record_metric("vertex_ai.client.errors", 1, {"operation": "multimodal", "error_type": error_type})
            
            logger.error(f"Error al procesar contenido multimodal: {str(e)}")
            
            return {
                "text": f"Error: {str(e)}",
                "finish_reason": "ERROR",
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                "error": str(e)
            }
            
        finally:
            telemetry_adapter.end_span(span)

    @measure_execution_time("vertex_ai.client.process_document")
    @with_retries(max_retries=2, base_delay=1.0, backoff_factor=2)
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
        await self._ensure_initialized()
        
        span = telemetry_adapter.start_span("VertexAIClient.process_document", {
            "client.document_size": len(document_content),
            "client.mime_type": mime_type,
            "client.processor_id": processor_id
        })
        
        try:
            telemetry_adapter.add_span_event(span, "document.start")
            self.stats["document_requests"] = self.stats.get("document_requests", 0) + 1
            
            # Verificar caché
            doc_hash = hashlib.md5(document_content).hexdigest()
            cache_key = self._get_cache_key({
                "type": "document",
                "document_hash": doc_hash,
                "mime_type": mime_type,
                "processor_id": processor_id
            })
            
            # Intentar obtener de caché
            cached = await self.cache_manager.get(cache_key)
            if cached:
                telemetry_adapter.add_span_event(span, "document.cache_hit")
                telemetry_adapter.set_span_attribute(span, "client.cache", "hit")
                telemetry_adapter.record_metric("vertex_ai.client.cache_hits", 1, {"operation": "document"})
                return cached
                
            telemetry_adapter.add_span_event(span, "document.cache_miss")
            telemetry_adapter.set_span_attribute(span, "client.cache", "miss")
            telemetry_adapter.record_metric("vertex_ai.client.cache_misses", 1, {"operation": "document"})
            
            start_time = time.time()
            
            # Adquirir cliente del pool
            client = await self.connection_pool.acquire()
            
            try:
                # Modo mock si no está disponible Vertex AI
                if client.get("mock", False):
                    await asyncio.sleep(0.5)  # Simular latencia
                    
                    # Simular extracción de texto
                    mock_text = "Este es un texto extraído simulado del documento."
                    
                    mock_response = {
                        "text": mock_text,
                        "pages": 1,
                        "entities": [],
                        "mime_type": mime_type,
                        "processor_id": processor_id
                    }
                    
                    telemetry_adapter.set_span_attribute(span, "client.mode", "mock")
                    response = mock_response
                else:
                    # Procesar documento con Document AI
                    project_id = client["project_id"]
                    location = "us"  # Ubicación del procesador
                    
                    # Crear cliente de Document AI
                    docai_client = documentai.DocumentProcessorServiceClient()
                    
                    # Nombre del procesador
                    processor_name = docai_client.processor_path(
                        project_id, location, processor_id
                    )
                    
                    # Crear solicitud
                    raw_document = documentai.RawDocument(
                        content=document_content, mime_type=mime_type
                    )
                    request = documentai.ProcessRequest(
                        name=processor_name, raw_document=raw_document
                    )
                    
                    # Procesar documento
                    result = docai_client.process_document(request=request)
                    document = result.document
                    
                    # Extraer entidades
                    entities = []
                    for entity in document.entities:
                        entities.append({
                            "type": entity.type_,
                            "mention_text": entity.mention_text,
                            "confidence": entity.confidence
                        })
                    
                    # Crear respuesta
                    response = {
                        "text": document.text,
                        "pages": len(document.pages),
                        "entities": entities,
                        "mime_type": mime_type,
                        "processor_id": processor_id
                    }
                    
                    telemetry_adapter.set_span_attribute(span, "client.mode", "real")
            finally:
                # Liberar cliente al pool
                await self.connection_pool.release(client)
            
            end_time = time.time()
            
            # Actualizar estadísticas
            latency_ms = (end_time - start_time) * 1000
            
            op_latencies = self.stats["latency_ms"].setdefault("document", [])
            op_latencies.append(latency_ms)
            if len(op_latencies) > 100:
                op_latencies.pop(0)
            
            # Guardar en caché
            await self.cache_manager.set(cache_key, response)
            
            # Registrar métricas de telemetría
            telemetry_adapter.set_span_attribute(span, "client.latency_ms", latency_ms)
            telemetry_adapter.set_span_attribute(span, "client.document.pages", response["pages"])
            telemetry_adapter.set_span_attribute(span, "client.document.entities", len(response["entities"]))
            telemetry_adapter.record_metric("vertex_ai.client.latency", latency_ms, {"operation": "document"})
            
            return response
            
        except Exception as e:
            error_type = type(e).__name__
            error_count = self.stats["errors"].get(error_type, 0) + 1
            self.stats["errors"][error_type] = error_count
            
            telemetry_adapter.record_exception(span, e)
            telemetry_adapter.set_span_attribute(span, "client.error", str(e))
            telemetry_adapter.record_metric("vertex_ai.client.errors", 1, {"operation": "document", "error_type": error_type})
            
            logger.error(f"Error al procesar documento: {str(e)}")
            
            return {
                "text": "",
                "pages": 0,
                "entities": [],
                "error": str(e)
            }
            
        finally:
            telemetry_adapter.end_span(span)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cliente.
        
        Returns:
            Dict[str, Any]: Estadísticas del cliente
        """
        # Obtener estadísticas de caché
        cache_stats = await self.cache_manager.get_stats()
        
        # Calcular promedios de latencia
        latency_avg = {}
        for operation, latencies in self.stats["latency_ms"].items():
            if latencies:
                latency_avg[operation] = sum(latencies) / len(latencies)
        
        # Obtener estadísticas del pool de conexiones
        pool_stats = {
            "created": self.connection_pool.stats.get("created", 0),
            "reused": self.connection_pool.stats.get("reused", 0),
            "active": self.connection_pool.stats.get("active", 0),
            "max_size": self.connection_pool.max_size
        }
        
        return {
            **self.stats,
            "latency_avg_ms": latency_avg,
            "cache": cache_stats,
            "connection_pool": pool_stats,
            "initialized": self.is_initialized
        }
    
    async def flush_cache(self) -> bool:
        """
        Limpia la caché del cliente.
        
        Returns:
            bool: True si se limpió correctamente
        """
        try:
            await self.cache_manager.flush()
            return True
        except Exception as e:
            logger.error(f"Error al limpiar caché: {e}")
            return False
    
    async def close(self) -> None:
        """Cierra el cliente y libera recursos."""
        try:
            # Cerrar pool de conexiones
            await self.connection_pool.close()
            
            # Limpiar estado
            self._initialized = False
            self.is_initialized = False
            
            logger.info("Cliente VertexAI cerrado correctamente")
        except Exception as e:
            logger.error(f"Error al cerrar cliente VertexAI: {e}")


# Instancia global del cliente
vertex_ai_client = VertexAIClient(
    use_redis_cache=os.environ.get("USE_REDIS_CACHE", "false").lower() == "true",
    redis_url=os.environ.get("REDIS_URL"),
    cache_ttl=get_env_int("VERTEX_CACHE_TTL", 3600),
    max_cache_size=get_env_int("VERTEX_MAX_CACHE_SIZE", 1000),
    max_connections=get_env_int("VERTEX_MAX_CONNECTIONS", 10)
)


async def check_vertex_ai_connection() -> Dict[str, Any]:
    """
    Verifica la conexión con Vertex AI.
    
    Returns:
        Dict[str, Any]: Estado de la conexión
    """
    try:
        # Inicializar cliente
        await vertex_ai_client.initialize()
        
        # Hacer una solicitud simple
        response = await vertex_ai_client.generate_content(
            "Test connection to Vertex AI",
            temperature=0.0,
            max_output_tokens=10
        )
        
        # Verificar si hay error
        if "error" in response:
            return {
                "status": "error",
                "timestamp": time.time(),
                "details": {
                    "error": response["error"]
                }
            }
        
        # Obtener estadísticas
        stats = await vertex_ai_client.get_stats()
        
        return {
            "status": "ok",
            "timestamp": time.time(),
            "details": {
                "latency_ms": stats["latency_avg_ms"].get("content_generation", 0),
                "cache_hit_ratio": stats["cache"]["hit_ratio"],
                "initialized": stats["initialized"]
            }
        }
    except Exception as e:
        logger.error(f"Error al verificar conexión con Vertex AI: {e}")
        return {
            "status": "error",
            "timestamp": time.time(),
            "details": {
                "error": str(e),
                "error_type": type(e).__name__
            }
        }

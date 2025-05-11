import asyncio
import json
import logging # Mantendré logging estándar por ahora, se puede ajustar si es necesario.
import os
import time
import zlib
from typing import Any, Dict, Optional

from core.logging_config import get_logger # Asegurándonos que el logger sea el correcto

logger = get_logger(__name__)

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis no está disponible. Usando caché en memoria.")
    REDIS_AVAILABLE = False

class CacheManager:
    """
    Gestor de caché con soporte para Redis y caché en memoria.
    Proporciona características avanzadas como compresión, TTL configurable,
    y políticas de evicción LRU.
    """
    
    def __init__(self, 
                 use_redis=False, 
                 redis_url=None,
                 ttl=3600,  # 1 hora por defecto
                 max_memory_size=1000, # MB
                 compression_threshold=1024,  # Comprimir valores mayores a 1KB en bytes
                 compression_level=6):  # Nivel de compresión zlib (1-9)
        """
        Inicializa el gestor de caché.
        
        Args:
            use_redis: Si True, intenta usar Redis si está disponible
            redis_url: URL de conexión a Redis (opcional)
            ttl: Tiempo de vida predeterminado para entradas de caché (segundos)
            max_memory_size: Tamaño máximo del caché en memoria (en MB)
            compression_threshold: Tamaño mínimo para comprimir valores (en bytes)
            compression_level: Nivel de compresión (1-9, 9 es máximo)
        """
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.redis_client = None
        self.ttl = ttl
        self.max_memory_bytes = max_memory_size * 1024 * 1024 # Convertir MB a Bytes
        self.compression_threshold = compression_threshold
        self.compression_level = compression_level
        
        # Caché en memoria (diccionario de {clave: {value, timestamp, size}})
        self.memory_cache = {}
        self.memory_cache_current_bytes = 0 # Tamaño actual en bytes
        
        # Bloqueo para operaciones de caché en memoria
        self.lock = asyncio.Lock()
        
        # Métricas de caché
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "errors": 0,
            "compression_savings_bytes": 0, # Ahorro en bytes
            "current_items": 0,
            "current_memory_bytes": 0
        }
        
        # Inicializar Redis si es necesario
        if self.use_redis:
            try:
                self.redis_client = redis.Redis.from_url(
                    redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
                )
                # Ping para verificar conexión
                # asyncio.create_task(self._check_redis_connection()) # Mejor manejarlo síncrono en init o lazy
                logger.info("Cliente Redis configurado. La conexión se verificará en la primera operación.")
            except Exception as e:
                logger.error(f"Error al configurar Redis: {e}")
                self.use_redis = False # Desactivar si hay error
                self.stats["errors"] += 1
    
    async def _check_redis_connection(self):
        if self.redis_client:
            try:
                await self.redis_client.ping()
                logger.info("Conexión con Redis verificada.")
            except Exception as e:
                logger.error(f"No se pudo conectar a Redis: {e}. Desactivando uso de Redis para esta instancia.")
                self.use_redis = False
                self.stats["errors"] += 1


    async def get(self, key: str, default=None) -> Any:
        """
        Obtiene un valor de la caché.
        """
        try:
            # Intentar obtener de Redis
            if self.use_redis and self.redis_client:
                if not await self._ensure_redis_connected(): # Verificar conexión antes de operar
                    # Si falla la conexión, intentar desde memoria
                    return await self._get_from_memory(key, default)

                data = await self.redis_client.get(key)
                if data:
                    # Descompresión si es necesario
                    original_size = len(data)
                    if data.startswith(b'zlib:'):
                        data = zlib.decompress(data[5:])
                    
                    # Deserializar
                    value = json.loads(data.decode('utf-8'))
                    self.stats["hits"] += 1
                    # logger.debug(f"Cache HIT (Redis): {key}")
                    return value
            
            # Si no está en Redis o no usamos Redis, buscar en memoria
            return await self._get_from_memory(key, default)
        
        except Exception as e:
            logger.error(f"Error al obtener de caché ({key}): {e}")
            self.stats["errors"] += 1
            if isinstance(e, redis.exceptions.ConnectionError): # Si Redis cae, desactivar
                logger.warning("Desactivando Redis debido a error de conexión.")
                self.use_redis = False
            return default

    async def _get_from_memory(self, key: str, default=None) -> Any:
        async with self.lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                # Verificar TTL
                if time.time() - entry["timestamp"] < self.ttl:
                    self.stats["hits"] += 1
                    # Actualizar timestamp (LRU - se mueve al final al reinsertar en _cleanup_if_needed)
                    # No es estrictamente LRU aquí, pero _cleanup_if_needed lo maneja
                    # logger.debug(f"Cache HIT (Memory): {key}")
                    return entry["value"]
                else:
                    # Eliminar entrada expirada
                    # logger.debug(f"Cache EXPIRED (Memory): {key}")
                    self.memory_cache_current_bytes -= entry["size_bytes"]
                    del self.memory_cache[key]
                    self.stats["evictions"] +=1
        
        self.stats["misses"] += 1
        # logger.debug(f"Cache MISS: {key}")
        return default

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Almacena un valor en la caché.
        """
        current_ttl = ttl if ttl is not None else self.ttl
        try:
            # Serializar valor
            serialized_value = json.dumps(value).encode('utf-8')
            original_size_bytes = len(serialized_value)
            data_to_store = serialized_value
            is_compressed = False

            # Comprimir si supera el umbral
            if original_size_bytes > self.compression_threshold:
                compressed_data = zlib.compress(serialized_value, level=self.compression_level)
                # Solo usar si es más pequeño
                if len(compressed_data) < original_size_bytes:
                    data_to_store = b'zlib:' + compressed_data
                    is_compressed = True
                    self.stats["compression_savings_bytes"] += original_size_bytes - len(compressed_data)
            
            final_size_bytes = len(data_to_store)

            # Intentar almacenar en Redis
            if self.use_redis and self.redis_client:
                if not await self._ensure_redis_connected():
                    # Si falla, intentar en memoria
                    return await self._set_to_memory(key, value, original_size_bytes, final_size_bytes, is_compressed)

                await self.redis_client.set(key, data_to_store, ex=current_ttl)
                self.stats["sets"] += 1
                # logger.debug(f"Cache SET (Redis): {key}, TTL: {current_ttl}")
                return True # Asumimos éxito si no hay excepción
            
            # Si no usamos Redis, almacenar en memoria
            return await self._set_to_memory(key, value, original_size_bytes, final_size_bytes, is_compressed)

        except Exception as e:
            logger.error(f"Error al almacenar en caché ({key}): {e}")
            self.stats["errors"] += 1
            if isinstance(e, redis.exceptions.ConnectionError):
                logger.warning("Desactivando Redis debido a error de conexión.")
                self.use_redis = False
            return False

    async def _set_to_memory(self, key: str, value: Any, original_size_bytes: int, final_size_bytes: int, is_compressed: bool):
        async with self.lock:
            # Limpiar espacio si es necesario
            await self._cleanup_if_needed(needed_space_bytes=final_size_bytes)

            if self.memory_cache_current_bytes + final_size_bytes <= self.max_memory_bytes:
                # Eliminar si ya existe para actualizar tamaño y timestamp
                if key in self.memory_cache:
                    old_entry = self.memory_cache.pop(key)
                    self.memory_cache_current_bytes -= old_entry["size_bytes"]
                
                self.memory_cache[key] = {
                    "value": value, # Almacenar el valor original, no el serializado/comprimido
                    "timestamp": time.time(),
                    "size_bytes": final_size_bytes, # Tamaño del dato como se almacenaría (potencialmente comprimido)
                    "original_size_bytes": original_size_bytes,
                    "is_compressed": is_compressed
                }
                self.memory_cache_current_bytes += final_size_bytes
                self.stats["sets"] += 1
                # logger.debug(f"Cache SET (Memory): {key}")
                return True
            else:
                # logger.warning(f"No hay suficiente espacio en caché en memoria para {key} (necesita {final_size_bytes}, disponible después de limpieza: {self.max_memory_bytes - self.memory_cache_current_bytes})")
                return False


    async def _cleanup_if_needed(self, needed_space_bytes: int = 0):
        """
        Limpia la caché en memoria si es necesario (LRU y expirados).
        Debe ser llamado dentro de un lock.
        """
        # Primero, eliminar expirados
        now = time.time()
        expired_keys = [k for k, v in self.memory_cache.items() if now - v["timestamp"] >= self.ttl]
        for k in expired_keys:
            # logger.debug(f"Cache EVICT (Expired, Memory): {k}")
            entry = self.memory_cache.pop(k)
            self.memory_cache_current_bytes -= entry["size_bytes"]
            self.stats["evictions"] += 1
            
        # Si aún no hay suficiente espacio, aplicar LRU
        # Ordenar por timestamp (más antiguo primero)
        # Esto es O(N log N), podría optimizarse si el rendimiento es crítico con un OrderedDict o similar
        while self.memory_cache_current_bytes + needed_space_bytes > self.max_memory_bytes and self.memory_cache:
            lru_key = min(self.memory_cache, key=lambda k: self.memory_cache[k]["timestamp"])
            # logger.debug(f"Cache EVICT (LRU, Memory): {lru_key}")
            entry = self.memory_cache.pop(lru_key)
            self.memory_cache_current_bytes -= entry["size_bytes"]
            self.stats["evictions"] += 1
        
        self.stats["current_items"] = len(self.memory_cache)
        self.stats["current_memory_bytes"] = self.memory_cache_current_bytes

    async def flush(self):
        """Limpia todo el caché."""
        try:
            if self.use_redis and self.redis_client:
                if await self._ensure_redis_connected():
                    await self.redis_client.flushdb()
            
            async with self.lock:
                self.memory_cache.clear()
                self.memory_cache_current_bytes = 0
            
            logger.info("Caché limpiado (Redis y Memoria)")
            # Resetear algunas estadísticas relacionadas con el contenido
            self.stats["hits"] = 0
            self.stats["misses"] = 0
            self.stats["sets"] = 0
            self.stats["evictions"] = 0
            self.stats["compression_savings_bytes"] = 0
            self.stats["current_items"] = 0
            self.stats["current_memory_bytes"] = 0
        except Exception as e:
            logger.error(f"Error al limpiar caché: {e}")
            self.stats["errors"] += 1
            if isinstance(e, redis.exceptions.ConnectionError):
                self.use_redis = False


    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché.
        """
        async with self.lock: # Asegurar consistencia de stats de memoria
            self.stats["current_items"] = len(self.memory_cache)
            self.stats["current_memory_bytes"] = self.memory_cache_current_bytes

        cache_stats = self.stats.copy()
        if self.use_redis and self.redis_client and await self._ensure_redis_connected():
            try:
                redis_info = await self.redis_client.info()
                cache_stats["redis_used_memory"] = redis_info.get("used_memory_human")
                cache_stats["redis_keys"] = redis_info.get("db0", {}).get("keys") # Asume db0
            except Exception as e:
                logger.warning(f"No se pudieron obtener estadísticas de Redis: {e}")
                cache_stats["redis_stats_error"] = str(e)
        
        total_requests = cache_stats["hits"] + cache_stats["misses"]
        cache_stats["hit_ratio"] = cache_stats["hits"] / total_requests if total_requests > 0 else 0
        return cache_stats

    async def _ensure_redis_connected(self) -> bool:
        if not self.use_redis or not self.redis_client:
            return False
        try:
            await self.redis_client.ping()
            return True
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error: {e}. Disabling Redis for this session.")
            self.use_redis = False # Desactivar si hay error de conexión
            self.stats["errors"] += 1
            return False
        except Exception as e: # Capturar otros posibles errores de redis
            logger.error(f"Unexpected Redis error: {e}. Disabling Redis for this session.")
            self.use_redis = False
            self.stats["errors"] += 1
            return False
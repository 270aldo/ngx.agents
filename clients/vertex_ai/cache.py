import asyncio
import json
import logging # Mantendré logging estándar por ahora, se puede ajustar si es necesario.
import os
import time
import zlib
import hashlib
from enum import Enum
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple, Union, Set, Iterator

from core.logging_config import get_logger # Asegurándonos que el logger sea el correcto
from core.telemetry import telemetry

# Clase para contexto nulo cuando la telemetría está deshabilitada
class nullcontext:
    """Contexto nulo para usar cuando la telemetría está deshabilitada."""
    def __init__(self, enter_result=None):
        self.enter_result = enter_result
        
    def __enter__(self):
        return self.enter_result
        
    def __exit__(self, *excinfo):
        pass
        
    async def __aenter__(self):
        return self.enter_result
        
    async def __aexit__(self, *excinfo):
        pass

logger = get_logger(__name__)

# Intentar importar Redis para caché distribuido
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis no está disponible. Usando caché en memoria.")
    REDIS_AVAILABLE = False

# Intentar importar bibliotecas opcionales para funcionalidades avanzadas
try:
    import xxhash  # Para hashing más rápido
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False

# Definir políticas de caché
class CachePolicy(Enum):
    """Políticas de caché disponibles."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live
    HYBRID = "hybrid"  # Combinación de LRU y TTL

class CacheManager:
    """
    Gestor de caché avanzado con soporte para Redis y caché en memoria.
    
    Características:
    - Sistema de caché en múltiples niveles (L1: memoria, L2: Redis)
    - Compresión configurable con múltiples algoritmos
    - Múltiples políticas de evicción (LRU, LFU, FIFO, TTL, Híbrido)
    - Particionamiento de caché para distribución de carga
    - Invalidación inteligente basada en patrones
    - Precarga y calentamiento de caché
    - Estadísticas detalladas y telemetría
    - Soporte para fragmentación de valores grandes
    """
    
    def __init__(self, 
                 use_redis=False, 
                 redis_url=None,
                 ttl=3600,  # 1 hora por defecto
                 max_memory_size=1000, # MB
                 compression_threshold=1024,  # Comprimir valores mayores a 1KB en bytes
                 compression_level=6,  # Nivel de compresión zlib (1-9)
                 cache_policy=CachePolicy.HYBRID,  # Política de caché
                 partitions=4,  # Número de particiones para caché distribuido
                 l1_size_ratio=0.2,  # Porcentaje del tamaño máximo para caché L1 (memoria)
                 prefetch_threshold=0.8,  # Umbral de accesos para precarga
                 enable_telemetry=True):  # Habilitar telemetría
        """
        Inicializa el gestor de caché avanzado.
        
        Args:
            use_redis: Si True, intenta usar Redis si está disponible
            redis_url: URL de conexión a Redis (opcional)
            ttl: Tiempo de vida predeterminado para entradas de caché (segundos)
            max_memory_size: Tamaño máximo del caché en memoria (en MB)
            compression_threshold: Tamaño mínimo para comprimir valores (en bytes)
            compression_level: Nivel de compresión (1-9, 9 es máximo)
            cache_policy: Política de evicción de caché
            partitions: Número de particiones para distribución
            l1_size_ratio: Proporción del tamaño para caché L1 (memoria)
            prefetch_threshold: Umbral de accesos para precarga
            enable_telemetry: Habilitar telemetría detallada
        """
        # Configuración básica
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.redis_client = None
        self.ttl = ttl
        self.max_memory_bytes = max_memory_size * 1024 * 1024 # Convertir MB a Bytes
        self.compression_threshold = compression_threshold
        self.compression_level = compression_level
        self.cache_policy = cache_policy
        self.partitions = max(1, partitions)
        self.enable_telemetry = enable_telemetry
        
        # Configuración de caché en múltiples niveles
        self.l1_max_bytes = int(self.max_memory_bytes * l1_size_ratio)
        self.l2_enabled = self.use_redis
        self.prefetch_threshold = prefetch_threshold
        
        # Caché L1 (memoria) - Dividido en particiones para mejor rendimiento
        self.memory_cache = [{} for _ in range(self.partitions)]  # Lista de diccionarios por partición
        self.memory_cache_current_bytes = 0  # Tamaño actual en bytes
        self.access_counts = {}  # Contador de accesos para LFU
        self.access_order = []  # Orden de acceso para FIFO
        self.pattern_subscriptions = {}  # Patrones para invalidación inteligente
        
        # Bloqueos para operaciones de caché (uno por partición)
        self.locks = [asyncio.Lock() for _ in range(self.partitions)]
        
        # Métricas de caché avanzadas
        self.stats = {
            "hits": {"l1": 0, "l2": 0, "total": 0},
            "misses": {"l1": 0, "l2": 0, "total": 0},
            "sets": {"l1": 0, "l2": 0, "total": 0},
            "deletes": {"l1": 0, "l2": 0, "total": 0},
            "evictions": {"l1": 0, "l2": 0, "total": 0},
            "errors": {"l1": 0, "l2": 0, "connection": 0, "total": 0},
            "compression": {
                "savings_bytes": 0,
                "compressed_items": 0,
                "compression_ratio": 0
            },
            "prefetch": {"attempts": 0, "hits": 0},
            "prefetch_requests": 0,
            "pattern_invalidations": 0,
            "invalidated_keys": 0,
            "invalidations": {"pattern": 0, "direct": 0},
            "fragmentation": {"fragments": 0, "reassemblies": 0},
            "current_items": {"l1": 0, "l2": 0, "total": 0},
            "current_memory_bytes": {"l1": 0, "l2": 0, "total": 0},
            "partitions": {p: {"items": 0, "bytes": 0} for p in range(self.partitions)}
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
        """Verifica la conexión con Redis."""
        if self.redis_client:
            try:
                await self.redis_client.ping()
                logger.info("Conexión con Redis verificada.")
                return True
            except Exception as e:
                logger.error(f"No se pudo conectar a Redis: {e}. Desactivando uso de Redis para esta instancia.")
                self.use_redis = False
                self.l2_enabled = False
                self.stats["errors"]["connection"] += 1
                self.stats["errors"]["total"] += 1
                return False
        return False
        
    def _get_partition(self, key: str) -> int:
        """Determina la partición para una clave.
        
        Args:
            key: Clave para determinar la partición
            
        Returns:
            int: Índice de la partición (0 a partitions-1)
        """
        # Usar xxhash si está disponible (más rápido)
        if XXHASH_AVAILABLE:
            hash_value = xxhash.xxh32(key.encode()).intdigest()
        else:
            # Alternativa con hashlib
            hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
            
        return hash_value % self.partitions
        
    async def _get_lock_for_key(self, key: str) -> asyncio.Lock:
        """Obtiene el lock correspondiente a la partición de la clave.
        
        Args:
            key: Clave para obtener el lock
            
        Returns:
            asyncio.Lock: Lock para la partición
        """
        partition = self._get_partition(key)
        return self.locks[partition]


    async def get(self, key: str, default=None) -> Any:
        """Obtiene un valor de la caché utilizando el sistema de múltiples niveles.
        
        Primero busca en L1 (memoria) y luego en L2 (Redis) si está habilitado.
        Si se encuentra en L2 pero no en L1, se promueve a L1 (caché de escritura).
        
        Args:
            key: Clave a buscar
            default: Valor por defecto si no se encuentra
            
        Returns:
            Any: Valor encontrado o default si no existe
        """
        try:
            with telemetry.start_span("cache.get") if self.enable_telemetry else nullcontext() as span:
                if self.enable_telemetry and span:
                    span.set_attribute("cache.key", key)
                
                # 1. Intentar obtener de L1 (memoria)
                value = await self._get_from_memory(key, None)
                
                if value is not None:
                    # Incrementar contador de accesos para LFU
                    self.access_counts[key] = self.access_counts.get(key, 0) + 1
                    
                    # Actualizar orden de acceso para LRU
                    if key in self.access_order:
                        self.access_order.remove(key)
                    self.access_order.append(key)
                    
                    self.stats["hits"]["l1"] += 1
                    self.stats["hits"]["total"] += 1
                    
                    if self.enable_telemetry and span:
                        span.set_attribute("cache.hit", True)
                        span.set_attribute("cache.level", "L1")
                    
                    # Verificar si hay patrones suscritos a esta clave
                    await self._check_pattern_subscriptions(key)
                    
                    return value
                
                # 2. Si no está en L1 y L2 está habilitado, intentar obtener de Redis
                if self.l2_enabled and self.redis_client:
                    if not await self._ensure_redis_connected():
                        self.stats["misses"]["l1"] += 1
                        self.stats["misses"]["l2"] += 1
                        self.stats["misses"]["total"] += 1
                        if self.enable_telemetry and span:
                            span.set_attribute("cache.hit", False)
                        return default
                    
                    # Obtener de Redis
                    try:
                        redis_value = await self.redis_client.get(key)
                        if redis_value:
                            # Descomprimir y deserializar
                            value_data = await self._deserialize_value(redis_value)
                            
                            # Promover a L1 (caché de escritura)
                            await self._promote_to_l1(key, value_data)
                            
                            self.stats["hits"]["l2"] += 1
                            self.stats["hits"]["total"] += 1
                            self.stats["misses"]["l1"] += 1
                            
                            if self.enable_telemetry and span:
                                span.set_attribute("cache.hit", True)
                                span.set_attribute("cache.level", "L2")
                                span.set_attribute("cache.promoted", True)
                            
                            return value_data
                    except Exception as e:
                        logger.error(f"Error al obtener valor de Redis: {e}")
                        self.stats["errors"]["l2"] += 1
                        self.stats["errors"]["total"] += 1
                
                # 3. No se encontró en ningún nivel
                self.stats["misses"]["l1"] += 1
                if self.l2_enabled:
                    self.stats["misses"]["l2"] += 1
                self.stats["misses"]["total"] += 1
                
                if self.enable_telemetry and span:
                    span.set_attribute("cache.hit", False)
                
                return default
                
        except Exception as e:
            logger.error(f"Error al obtener de caché: {e}")
            self.stats["errors"]["total"] += 1
            return default
            
    async def _deserialize_value(self, serialized_value: bytes) -> Any:
        """Deserializa y descomprime un valor.
        
        Args:
            serialized_value: Valor serializado
            
        Returns:
            Any: Valor deserializado
        """
        try:
            value_data = json.loads(serialized_value)
            
            # Descomprimir si es necesario
            if value_data.get("compressed", False):
                import base64
                value = zlib.decompress(base64.b64decode(value_data["value"]))
                value = json.loads(value.decode())
            else:
                value = value_data["value"]
                
            return value
        except Exception as e:
            logger.error(f"Error al deserializar valor: {e}")
            raise
            
    async def _promote_to_l1(self, key: str, value: Any) -> None:
        """Promueve un valor de L2 a L1.
        
        Args:
            key: Clave del valor
            value: Valor a promover
        """
        # Obtener el tamaño aproximado
        value_size = len(json.dumps(value).encode())
        
        # Verificar si hay espacio en L1
        lock = await self._get_lock_for_key(key)
        async with lock:
            # Verificar si hay espacio o necesitamos hacer limpieza
            if self.memory_cache_current_bytes + value_size > self.l1_max_bytes:
                await self._cleanup_if_needed(value_size)
                
            # Almacenar en la partición correspondiente
            partition = self._get_partition(key)
            
            # Actualizar caché y métricas
            self.memory_cache[partition][key] = {
                "value": value,
                "timestamp": time.time(),
                "size_bytes": value_size,
                "access_count": 1
            }
            
            self.memory_cache_current_bytes += value_size
            self.stats["partitions"][partition]["items"] += 1
            self.stats["partitions"][partition]["bytes"] += value_size
            self.stats["current_items"]["l1"] += 1
            self.stats["current_memory_bytes"]["l1"] += value_size
            
            # Actualizar estructuras para políticas de caché
            self.access_counts[key] = 1
            self.access_order.append(key)
            
    async def _get_from_memory(self, key: str, default=None) -> Any:
        """Obtiene un valor del caché en memoria (L1).
        
        Args:
            key: Clave a buscar
            default: Valor por defecto si no se encuentra
            
        Returns:
            Any: Valor encontrado o default si no existe
        """
        try:
            # Determinar la partición
            partition = self._get_partition(key)
            lock = self.locks[partition]
            
            async with lock:
                # Buscar en la partición correspondiente
                if key in self.memory_cache[partition]:
                    entry = self.memory_cache[partition][key]
                    
                    # Verificar si ha expirado
                    if time.time() - entry["timestamp"] > self.ttl:
                        # Eliminar entrada expirada
                        self.memory_cache[partition].pop(key)
                        self.memory_cache_current_bytes -= entry["size_bytes"]
                        self.stats["partitions"][partition]["items"] -= 1
                        self.stats["partitions"][partition]["bytes"] -= entry["size_bytes"]
                        self.stats["current_items"]["l1"] -= 1
                        self.stats["current_memory_bytes"]["l1"] -= entry["size_bytes"]
                        self.stats["evictions"]["l1"] += 1
                        self.stats["evictions"]["total"] += 1
                        
                        # Limpiar de estructuras de políticas
                        if key in self.access_counts:
                            del self.access_counts[key]
                        if key in self.access_order:
                            self.access_order.remove(key)
                            
                        return default
                    
                    # Actualizar timestamp (renovar TTL)
                    entry["timestamp"] = time.time()
                    
                    # Incrementar contador de accesos
                    entry["access_count"] = entry.get("access_count", 0) + 1
                    
                    return entry["value"]
            
            return default
            
        except Exception as e:
            logger.error(f"Error al obtener de caché en memoria: {e}")
            self.stats["errors"]["l1"] += 1
            self.stats["errors"]["total"] += 1
            return default
            
    async def _check_pattern_subscriptions(self, key: str) -> None:
        """Verifica si hay patrones suscritos a esta clave y ejecuta acciones.
        
        Args:
            key: Clave que se ha accedido
        """
        # Verificar patrones de prefetch
        for pattern, action in self.pattern_subscriptions.items():
            if pattern in key or (hasattr(pattern, "match") and pattern.match(key)):
                # Ejecutar acción asociada al patrón
                if action.get("type") == "prefetch" and action.get("keys"):
                    self.stats["prefetch"]["attempts"] += 1
                    # Programar precarga de claves relacionadas
                    asyncio.create_task(self._prefetch_related_keys(action["keys"]))
                    
    async def _prefetch_related_keys(self, keys: List[str]) -> None:
        """Precarga claves relacionadas en L1 si están en L2.
        
        Args:
            keys: Lista de claves a precargar
        """
        if not self.l2_enabled or not self.redis_client:
            return
            
        for key in keys:
            # Verificar si ya está en L1
            partition = self._get_partition(key)
            if key in self.memory_cache[partition]:
                continue
                
            # Intentar obtener de L2
            try:
                redis_value = await self.redis_client.get(key)
                if redis_value:
                    # Deserializar y promover a L1
                    value_data = await self._deserialize_value(redis_value)
                    await self._promote_to_l1(key, value_data)
                    self.stats["prefetch"]["hits"] += 1
            except Exception as e:
                logger.debug(f"Error al precargar clave {key}: {e}")
                # No incrementamos errores ya que es una operación opcional
                
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, pattern: Optional[str] = None, 
               metadata: Optional[Dict[str, Any]] = None, prefetch_related: bool = False) -> bool:
        """
        Almacena un valor en la caché utilizando el sistema de múltiples niveles con soporte avanzado.
        
        Args:
            key: Clave para almacenar el valor
            value: Valor a almacenar
            ttl: Tiempo de vida en segundos (opcional, usa el predeterminado si no se especifica)
            pattern: Patrón al que pertenece esta clave (para invalidación inteligente)
            metadata: Metadatos asociados con la clave (para análisis y estadísticas)
            prefetch_related: Si True, intenta precargar claves relacionadas
            
        Returns:
            bool: True si se almacenó correctamente
        """
        current_ttl = ttl if ttl is not None else self.ttl
        try:
            with telemetry.start_span("cache.set") if self.enable_telemetry else nullcontext() as span:
                if self.enable_telemetry and span:
                    span.set_attribute("cache.key", key)
                    span.set_attribute("cache.ttl", ttl or self.ttl)
                    if pattern:
                        span.set_attribute("cache.pattern", pattern)
                    if prefetch_related:
                        span.set_attribute("cache.prefetch_enabled", True)
                
                # Preparar valor para almacenamiento
                value_data, original_size_bytes, final_size_bytes, is_compressed = await self._prepare_value_for_storage(value)
                
                # Preparar metadatos
                if metadata is None:
                    metadata = {}
                
                # Añadir metadatos del sistema
                metadata.update({
                    "timestamp": time.time(),
                    "size_bytes": final_size_bytes,
                    "original_size_bytes": original_size_bytes,
                    "compressed": is_compressed,
                    "ttl": current_ttl
                })
                
                # Registrar patrón si se especifica (para invalidación inteligente)
                if pattern:
                    await self._register_key_with_pattern(key, pattern)
                
                # 1. Almacenar en L1 (memoria) con metadatos
                await self._set_to_memory(key, value, original_size_bytes, final_size_bytes, is_compressed, metadata)
                
                # 2. Almacenar en L2 (Redis) si está habilitado
                if self.l2_enabled and self.redis_client:
                    if await self._ensure_redis_connected():
                        try:
                            # Crear estructura de datos para Redis con metadatos
                            redis_data = {
                                "value": value_data,
                                "timestamp": time.time(),
                                "compressed": is_compressed,
                                "original_size": original_size_bytes,
                                "metadata": metadata
                            }
                            
                            # Serializar para Redis
                            redis_value = json.dumps(redis_data)
                            
                            # Establecer en Redis con TTL
                            await self.redis_client.set(
                                key, 
                                redis_value,
                                ex=ttl or self.ttl
                            )
                            
                            self.stats["sets"]["l2"] += 1
                            
                            if self.enable_telemetry and span:
                                span.set_attribute("cache.l2_stored", True)
                                
                        except Exception as e:
                            logger.error(f"Error al almacenar en Redis: {e}")
                            self.stats["errors"]["l2"] += 1
                            self.stats["errors"]["total"] += 1
                            
                            if self.enable_telemetry and span:
                                span.set_attribute("cache.l2_error", str(e))
                                
                            if isinstance(e, redis.exceptions.ConnectionError):
                                logger.warning("Desactivando Redis debido a error de conexión.")
                                self.l2_enabled = False
                
                # 3. Realizar prefetching si está habilitado
                if prefetch_related and pattern and "*" in pattern:
                    # Intentar precargar claves relacionadas basadas en el patrón
                    try:
                        # Obtener base del patrón (sin comodines)
                        pattern_base = pattern.split("*")[0]
                        
                        # Buscar claves relacionadas en Redis
                        if self.l2_enabled and self.redis_client and await self._ensure_redis_connected():
                            related_keys = await self.redis_client.keys(f"{pattern_base}*")
                            if related_keys and len(related_keys) <= 10:  # Limitar a 10 claves para evitar sobrecarga
                                # Excluir la clave actual
                                related_keys = [k for k in related_keys if k != key]
                                if related_keys:
                                    asyncio.create_task(self._prefetch_related_keys(related_keys))
                                    self.stats["prefetch_requests"] += 1
                    except Exception as e:
                        logger.debug(f"Error en prefetching: {e}")  # Debug porque no es crítico
                
                self.stats["sets"]["total"] += 1
                return True
                
        except Exception as e:
            logger.error(f"Error al almacenar en caché ({key}): {e}")
            self.stats["errors"]["total"] += 1
            return False
            
    async def _prepare_value_for_storage(self, value: Any) -> Tuple[Any, int, int, bool]:
        """Prepara un valor para almacenamiento, aplicando compresión si es necesario.
        
        Args:
            value: Valor a preparar
            
        Returns:
            Tuple[Any, int, int, bool]: Valor preparado, tamaño original, tamaño final, si está comprimido
        """
        # Serializar valor
        serialized_value = json.dumps(value)
        original_size_bytes = len(serialized_value.encode('utf-8'))
        final_size_bytes = original_size_bytes
        is_compressed = False
        
        # Comprimir si supera el umbral
        if original_size_bytes > self.compression_threshold:
            try:
                import base64
                compressed_data = zlib.compress(serialized_value.encode('utf-8'), self.compression_level)
                compressed_size = len(compressed_data)
                
                # Solo usar compresión si realmente ahorra espacio
                if compressed_size < original_size_bytes:
                    # Codificar en base64 para JSON
                    value_data = base64.b64encode(compressed_data).decode('utf-8')
                    final_size_bytes = len(value_data)
                    is_compressed = True
                    
                    # Actualizar estadísticas de compresión
                    self.stats["compression"]["savings_bytes"] += (original_size_bytes - final_size_bytes)
                    self.stats["compression"]["compressed_items"] += 1
                    if self.stats["compression"]["compressed_items"] > 0:
                        self.stats["compression"]["compression_ratio"] = self.stats["compression"]["savings_bytes"] / \
                                                                     sum([self.stats["current_memory_bytes"]["l1"], 
                                                                          self.stats["compression"]["savings_bytes"]])
                    
                    return value_data, original_size_bytes, final_size_bytes, is_compressed
            except Exception as e:
                logger.error(f"Error al comprimir valor: {e}")
        
        # Si no se comprimió o hubo error
        return value, original_size_bytes, final_size_bytes, is_compressed
        
    async def _register_key_with_pattern(self, key: str, pattern: str) -> None:
        """Registra una clave con un patrón para invalidación inteligente.
        
        Args:
            key: Clave a registrar
            pattern: Patrón al que pertenece la clave
        """
        # Verificar si el patrón ya existe
        if pattern not in self.pattern_subscriptions:
            self.pattern_subscriptions[pattern] = {
                "type": "invalidation",
                "keys": set()
            }
        
        # Añadir clave al patrón
        if "keys" in self.pattern_subscriptions[pattern]:
            if isinstance(self.pattern_subscriptions[pattern]["keys"], set):
                self.pattern_subscriptions[pattern]["keys"].add(key)
            else:
                self.pattern_subscriptions[pattern]["keys"] = {key}
                
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalida todas las claves que coinciden con un patrón.
        
        Esta función es crucial para la invalidación inteligente de caché,
        permitiendo invalidar grupos de claves relacionadas con un solo comando.
        
        Args:
            pattern: Patrón para invalidar claves (ej: "vertex:generate_content:*")
            
        Returns:
            int: Número de claves invalidadas
        """
        with telemetry.start_span("cache.invalidate_pattern") if self.enable_telemetry else nullcontext() as span:
            if self.enable_telemetry and span:
                span.set_attribute("cache.pattern", pattern)
            
            invalidated_count = 0
            
            # 1. Invalidar claves registradas con este patrón exacto
            if pattern in self.pattern_subscriptions:
                keys_to_invalidate = self.pattern_subscriptions[pattern].get("keys", set())
                if keys_to_invalidate:
                    for key in list(keys_to_invalidate):  # Usar lista para evitar modificar durante iteración
                        await self.delete(key)
                        invalidated_count += 1
            
            # 2. Buscar patrones que coincidan con comodines
            if "*" in pattern:
                # Convertir patrón a expresión regular
                import re
                regex_pattern = pattern.replace(".", "\\.").replace("*", ".*")
                pattern_re = re.compile(regex_pattern)
                
                # Buscar en L1 (memoria)
                for partition_idx in range(self.partitions):
                    keys_to_delete = []
                    async with self.locks[partition_idx]:
                        for key in self.memory_cache[partition_idx].keys():
                            if pattern_re.match(key):
                                keys_to_delete.append(key)
                        
                        # Eliminar claves encontradas
                        for key in keys_to_delete:
                            if key in self.memory_cache[partition_idx]:
                                size_bytes = self.memory_cache[partition_idx][key].get("size_bytes", 0)
                                del self.memory_cache[partition_idx][key]
                                self.memory_cache_current_bytes -= size_bytes
                                self.stats["partitions"][partition_idx]["bytes"] -= size_bytes
                                self.stats["partitions"][partition_idx]["items"] -= 1
                                self.stats["current_memory_bytes"]["l1"] -= size_bytes
                                self.stats["current_items"]["l1"] -= 1
                                invalidated_count += 1
                
                # Buscar en L2 (Redis) si está habilitado
                if self.l2_enabled and self.redis_client:
                    try:
                        # Redis usa un formato diferente para patrones
                        redis_pattern = pattern.replace("*", "*")
                        redis_keys = await self.redis_client.keys(redis_pattern)
                        if redis_keys:
                            # Eliminar claves encontradas en Redis
                            await self.redis_client.delete(*redis_keys)
                            invalidated_count += len(redis_keys)
                            self.stats["deletes"]["l2"] += len(redis_keys)
                    except Exception as e:
                        logger.error(f"Error al invalidar patrón en Redis: {e}")
                        self.stats["errors"]["l2"] += 1
            
            # Actualizar estadísticas
            self.stats["pattern_invalidations"] += 1
            self.stats["invalidated_keys"] += invalidated_count
            
            if self.enable_telemetry and span:
                span.set_attribute("cache.invalidated_count", invalidated_count)
            
            logger.info(f"Invalidadas {invalidated_count} claves con patrón: {pattern}")
            return invalidated_count

    async def _set_to_memory(self, key: str, value: Any, original_size_bytes: int, final_size_bytes: int, is_compressed: bool, metadata: Optional[Dict[str, Any]] = None):
        """Almacena un valor en el caché en memoria (L1) con metadatos.
        
        Args:
            key: Clave para almacenar el valor
            value: Valor a almacenar
            original_size_bytes: Tamaño original en bytes
            final_size_bytes: Tamaño final en bytes (después de compresión si aplica)
            is_compressed: Si el valor está comprimido
            metadata: Metadatos asociados con la clave (opcional)
        """
        # Determinar la partición y obtener el lock
        partition = self._get_partition(key)
        lock = self.locks[partition]
        
        async with lock:
            # Verificar si la clave ya existe en esta partición
            existing_size = 0
            if key in self.memory_cache[partition]:
                existing_size = self.memory_cache[partition][key]["size_bytes"]
                self.memory_cache_current_bytes -= existing_size
                self.stats["partitions"][partition]["bytes"] -= existing_size
                self.stats["current_memory_bytes"]["l1"] -= existing_size
            else:
                # Si es nueva clave, verificar si necesitamos hacer limpieza
                if self.memory_cache_current_bytes + final_size_bytes > self.l1_max_bytes:
                    await self._cleanup_if_needed(final_size_bytes)
                self.stats["current_items"]["l1"] += 1
                self.stats["partitions"][partition]["items"] += 1
            
            # Almacenar en la partición correspondiente con metadatos
            cache_entry = {
                "value": value,
                "timestamp": time.time(),
                "size_bytes": final_size_bytes,
                "original_size": original_size_bytes,
                "compressed": is_compressed,
                "access_count": 1
            }
            
            # Añadir metadatos si existen
            if metadata:
                cache_entry["metadata"] = metadata
                
            self.memory_cache[partition][key] = cache_entry
            
            # Actualizar métricas
            self.memory_cache_current_bytes += final_size_bytes
            self.stats["partitions"][partition]["bytes"] += final_size_bytes
            self.stats["current_memory_bytes"]["l1"] += final_size_bytes
            self.stats["sets"]["l1"] += 1
            
            # Actualizar estructuras para políticas de caché
            self.access_counts[key] = 1
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            return True

    async def _cleanup_if_needed(self, needed_space_bytes: int = 0):
        """
        Limpia la caché en memoria si es necesario, aplicando la política configurada.
        
        Args:
            needed_space_bytes: Espacio adicional necesario en bytes
        """
        with telemetry.start_span("cache.cleanup") if self.enable_telemetry else nullcontext() as span:
            if self.enable_telemetry and span:
                span.set_attribute("cache.needed_space", needed_space_bytes)
                span.set_attribute("cache.policy", self.cache_policy.value)
            
            # 1. Primero eliminar entradas expiradas (común a todas las políticas)
            await self._evict_expired_entries()
            
            # 2. Si aún necesitamos espacio, aplicar la política configurada
            if self.memory_cache_current_bytes + needed_space_bytes > self.l1_max_bytes:
                if self.cache_policy == CachePolicy.LRU:
                    await self._apply_lru_policy(needed_space_bytes)
                elif self.cache_policy == CachePolicy.LFU:
                    await self._apply_lfu_policy(needed_space_bytes)
                elif self.cache_policy == CachePolicy.FIFO:
                    await self._apply_fifo_policy(needed_space_bytes)
                elif self.cache_policy == CachePolicy.HYBRID:
                    # Política híbrida: combina LRU con factor de frecuencia
                    await self._apply_hybrid_policy(needed_space_bytes)
                else:  # Default a LRU
                    await self._apply_lru_policy(needed_space_bytes)
                    
            # Actualizar estadísticas globales
            total_items = sum(len(cache) for cache in self.memory_cache)
            self.stats["current_items"]["l1"] = total_items
            self.stats["current_memory_bytes"]["l1"] = self.memory_cache_current_bytes
            self.stats["current_items"]["total"] = total_items  # Aproximación, no incluye L2
            
            if self.enable_telemetry and span:
                span.set_attribute("cache.items_after", total_items)
                span.set_attribute("cache.bytes_after", self.memory_cache_current_bytes)
    
    async def _evict_expired_entries(self):
        """Elimina todas las entradas expiradas del caché en memoria."""
        now = time.time()
        expired_count = 0
        expired_bytes = 0
        
        # Procesar cada partición
        for partition in range(self.partitions):
            # Usar lock por partición para minimizar contención
            async with self.locks[partition]:
                # Identificar claves expiradas
                expired_keys = []
                for k, v in self.memory_cache[partition].items():
                    if now - v["timestamp"] > self.ttl:
                        expired_keys.append(k)
                
                # Eliminar entradas expiradas
                for k in expired_keys:
                    entry = self.memory_cache[partition].pop(k)
                    size = entry["size_bytes"]
                    self.memory_cache_current_bytes -= size
                    self.stats["partitions"][partition]["bytes"] -= size
                    self.stats["partitions"][partition]["items"] -= 1
                    expired_bytes += size
                    expired_count += 1
                    
                    # Limpiar de estructuras de políticas
                    if k in self.access_counts:
                        del self.access_counts[k]
                    if k in self.access_order:
                        self.access_order.remove(k)
        
        # Actualizar estadísticas
        if expired_count > 0:
            self.stats["evictions"]["l1"] += expired_count
            self.stats["evictions"]["total"] += expired_count
            
            if self.enable_telemetry:
                telemetry.record_event("cache", "expired_eviction", {
                    "count": expired_count,
                    "bytes": expired_bytes
                })
    
    async def _apply_lru_policy(self, needed_space_bytes: int):
        """Aplica la política LRU (Least Recently Used) para liberar espacio.
        
        Args:
            needed_space_bytes: Espacio adicional necesario en bytes
        """
        # Usar el orden de acceso para determinar las claves menos recientemente usadas
        evicted_count = 0
        evicted_bytes = 0
        
        # Mientras necesitemos espacio y tengamos claves en el orden de acceso
        while (self.memory_cache_current_bytes + needed_space_bytes > self.l1_max_bytes and 
               self.access_order):
            # Obtener la clave menos recientemente usada
            lru_key = self.access_order[0] if self.access_order else None
            if not lru_key:
                break
                
            # Determinar la partición
            partition = self._get_partition(lru_key)
            
            # Verificar si la clave existe en la partición
            async with self.locks[partition]:
                if lru_key in self.memory_cache[partition]:
                    # Eliminar la entrada
                    entry = self.memory_cache[partition].pop(lru_key)
                    size = entry["size_bytes"]
                    self.memory_cache_current_bytes -= size
                    self.stats["partitions"][partition]["bytes"] -= size
                    self.stats["partitions"][partition]["items"] -= 1
                    evicted_bytes += size
                    evicted_count += 1
                
                # Eliminar de la lista de acceso
                if lru_key in self.access_order:
                    self.access_order.remove(lru_key)
                    
                # Eliminar del contador de accesos
                if lru_key in self.access_counts:
                    del self.access_counts[lru_key]
        
        # Actualizar estadísticas
        if evicted_count > 0:
            self.stats["evictions"]["l1"] += evicted_count
            self.stats["evictions"]["total"] += evicted_count
            
            if self.enable_telemetry:
                telemetry.record_event("cache", "lru_eviction", {
                    "count": evicted_count,
                    "bytes": evicted_bytes
                })
    
    async def _apply_lfu_policy(self, needed_space_bytes: int):
        """Aplica la política LFU (Least Frequently Used) para liberar espacio.
        
        Args:
            needed_space_bytes: Espacio adicional necesario en bytes
        """
        # Usar el contador de accesos para determinar las claves menos frecuentemente usadas
        evicted_count = 0
        evicted_bytes = 0
        
        # Ordenar claves por frecuencia de acceso (menor primero)
        sorted_keys = sorted(self.access_counts.items(), key=lambda x: x[1])
        
        # Mientras necesitemos espacio y tengamos claves
        for lfu_key, _ in sorted_keys:
            if self.memory_cache_current_bytes + needed_space_bytes <= self.l1_max_bytes:
                break
                
            # Determinar la partición
            partition = self._get_partition(lfu_key)
            
            # Verificar si la clave existe en la partición
            async with self.locks[partition]:
                if lfu_key in self.memory_cache[partition]:
                    # Eliminar la entrada
                    entry = self.memory_cache[partition].pop(lfu_key)
                    size = entry["size_bytes"]
                    self.memory_cache_current_bytes -= size
                    self.stats["partitions"][partition]["bytes"] -= size
                    self.stats["partitions"][partition]["items"] -= 1
                    evicted_bytes += size
                    evicted_count += 1
                
                # Eliminar de la lista de acceso
                if lfu_key in self.access_order:
                    self.access_order.remove(lfu_key)
                    
                # Eliminar del contador de accesos
                if lfu_key in self.access_counts:
                    del self.access_counts[lfu_key]
        
        # Actualizar estadísticas
        if evicted_count > 0:
            self.stats["evictions"]["l1"] += evicted_count
            self.stats["evictions"]["total"] += evicted_count
            
            if self.enable_telemetry:
                telemetry.record_event("cache", "lfu_eviction", {
                    "count": evicted_count,
                    "bytes": evicted_bytes
                })
    
    async def _apply_fifo_policy(self, needed_space_bytes: int):
        """Aplica la política FIFO (First In First Out) para liberar espacio.
        
        Args:
            needed_space_bytes: Espacio adicional necesario en bytes
        """
        # Usar el orden de inserción para determinar las claves más antiguas
        evicted_count = 0
        evicted_bytes = 0
        
        # Ordenar todas las entradas por timestamp de inserción
        all_entries = []
        for partition in range(self.partitions):
            for key, entry in self.memory_cache[partition].items():
                all_entries.append((key, entry["timestamp"]))
        
        # Ordenar por timestamp (más antiguo primero)
        sorted_entries = sorted(all_entries, key=lambda x: x[1])
        
        # Mientras necesitemos espacio y tengamos claves
        for fifo_key, _ in sorted_entries:
            if self.memory_cache_current_bytes + needed_space_bytes <= self.l1_max_bytes:
                break
                
            # Determinar la partición
            partition = self._get_partition(fifo_key)
            
            # Verificar si la clave existe en la partición
            async with self.locks[partition]:
                if fifo_key in self.memory_cache[partition]:
                    # Eliminar la entrada
                    entry = self.memory_cache[partition].pop(fifo_key)
                    size = entry["size_bytes"]
                    self.memory_cache_current_bytes -= size
                    self.stats["partitions"][partition]["bytes"] -= size
                    self.stats["partitions"][partition]["items"] -= 1
                    evicted_bytes += size
                    evicted_count += 1
                
                # Eliminar de la lista de acceso
                if fifo_key in self.access_order:
                    self.access_order.remove(fifo_key)
                    
                # Eliminar del contador de accesos
                if fifo_key in self.access_counts:
                    del self.access_counts[fifo_key]
        
        # Actualizar estadísticas
        if evicted_count > 0:
            self.stats["evictions"]["l1"] += evicted_count
            self.stats["evictions"]["total"] += evicted_count
            
            if self.enable_telemetry:
                telemetry.record_event("cache", "fifo_eviction", {
                    "count": evicted_count,
                    "bytes": evicted_bytes
                })
    
    async def _apply_hybrid_policy(self, needed_space_bytes: int):
        """Aplica una política híbrida que combina LRU con factor de frecuencia.
        
        Args:
            needed_space_bytes: Espacio adicional necesario en bytes
        """
        # Calcular puntuación para cada clave (combinación de recencia y frecuencia)
        now = time.time()
        scores = {}
        
        # Calcular puntuación para cada clave
        for partition in range(self.partitions):
            for key, entry in self.memory_cache[partition].items():
                # Recencia: tiempo desde el último acceso (normalizado)
                recency = (now - entry["timestamp"]) / self.ttl
                
                # Frecuencia: número de accesos (normalizado por el máximo)
                frequency = self.access_counts.get(key, 1)
                max_freq = max(self.access_counts.values()) if self.access_counts else 1
                frequency_norm = 1 - (frequency / max_freq) if max_freq > 0 else 0
                
                # Puntuación combinada (70% recencia, 30% frecuencia)
                scores[key] = 0.7 * recency + 0.3 * frequency_norm
        
        # Ordenar por puntuación (mayor primero)
        sorted_keys = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Aplicar evicción
        evicted_count = 0
        evicted_bytes = 0
        
        for hybrid_key, _ in sorted_keys:
            if self.memory_cache_current_bytes + needed_space_bytes <= self.l1_max_bytes:
                break
                
            # Determinar la partición
            partition = self._get_partition(hybrid_key)
            
            # Verificar si la clave existe en la partición
            async with self.locks[partition]:
                if hybrid_key in self.memory_cache[partition]:
                    # Eliminar la entrada
                    entry = self.memory_cache[partition].pop(hybrid_key)
                    size = entry["size_bytes"]
                    self.memory_cache_current_bytes -= size
                    self.stats["partitions"][partition]["bytes"] -= size
                    self.stats["partitions"][partition]["items"] -= 1
                    evicted_bytes += size
                    evicted_count += 1
                
                # Eliminar de la lista de acceso
                if hybrid_key in self.access_order:
                    self.access_order.remove(hybrid_key)
                    
                # Eliminar del contador de accesos
                if hybrid_key in self.access_counts:
                    del self.access_counts[hybrid_key]
        
        # Actualizar estadísticas
        if evicted_count > 0:
            self.stats["evictions"]["l1"] += evicted_count
            self.stats["evictions"]["total"] += evicted_count
            
            if self.enable_telemetry:
                telemetry.record_event("cache", "hybrid_eviction", {
                    "count": evicted_count,
                    "bytes": evicted_bytes
                })

    async def flush(self):
        """Limpia todo el caché (L1 y L2)."""
        try:
            with telemetry.start_span("cache.flush") if self.enable_telemetry else nullcontext():
                # 1. Limpiar L2 (Redis) si está habilitado
                if self.l2_enabled and self.redis_client:
                    if await self._ensure_redis_connected():
                        await self.redis_client.flushdb()
                        logger.info("Caché L2 (Redis) limpiado")
                
                # 2. Limpiar L1 (memoria)
                for partition in range(self.partitions):
                    async with self.locks[partition]:
                        self.memory_cache[partition].clear()
                
                # 3. Limpiar estructuras auxiliares
                self.memory_cache_current_bytes = 0
                self.access_counts.clear()
                self.access_order.clear()
                self.pattern_subscriptions.clear()
                
                # 4. Resetear estadísticas
                self.stats["hits"] = {"l1": 0, "l2": 0, "total": 0}
                self.stats["misses"] = {"l1": 0, "l2": 0, "total": 0}
                self.stats["sets"] = {"l1": 0, "l2": 0, "total": 0}
                self.stats["evictions"] = {"l1": 0, "l2": 0, "total": 0}
                self.stats["compression"] = {
                    "savings_bytes": 0,
                    "compressed_items": 0,
                    "compression_ratio": 0
                }
                self.stats["prefetch"] = {"attempts": 0, "hits": 0}
                self.stats["invalidations"] = {"pattern": 0, "direct": 0}
                self.stats["fragmentation"] = {"fragments": 0, "reassemblies": 0}
                self.stats["current_items"] = {"l1": 0, "l2": 0, "total": 0}
                self.stats["current_memory_bytes"] = {"l1": 0, "l2": 0, "total": 0}
                
                for p in range(self.partitions):
                    self.stats["partitions"][p] = {"items": 0, "bytes": 0}
                
                logger.info("Caché completamente limpiado (L1 y L2)")
                
                # Registrar evento de telemetría
                if self.enable_telemetry:
                    telemetry.record_event("cache", "flush", {"success": True})
                
                return True
                
        except Exception as e:
            logger.error(f"Error al limpiar caché: {e}")
            self.stats["errors"]["total"] += 1
            
            if isinstance(e, redis.exceptions.ConnectionError):
                logger.warning("Desactivando Redis debido a error de conexión.")
                self.l2_enabled = False
                self.use_redis = False
            
            if self.enable_telemetry:
                telemetry.record_event("cache", "flush_error", {"error": str(e)})
                
            return False


    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas detalladas del caché en múltiples niveles.
        
        Returns:
            Dict[str, Any]: Estadísticas completas del caché
        """
        try:
            with telemetry.start_span("cache.get_stats") if self.enable_telemetry else nullcontext():
                # Actualizar métricas de L1 (memoria)
                total_items_l1 = sum(len(cache) for cache in self.memory_cache)
                self.stats["current_items"]["l1"] = total_items_l1
                self.stats["current_memory_bytes"]["l1"] = self.memory_cache_current_bytes
                
                # Copiar estadísticas básicas
                cache_stats = {
                    "hits": self.stats["hits"].copy(),
                    "misses": self.stats["misses"].copy(),
                    "sets": self.stats["sets"].copy(),
                    "evictions": self.stats["evictions"].copy(),
                    "errors": self.stats["errors"].copy(),
                    "compression": self.stats["compression"].copy(),
                    "prefetch": self.stats["prefetch"].copy(),
                    "invalidations": self.stats["invalidations"].copy(),
                    "fragmentation": self.stats["fragmentation"].copy(),
                    "current_items": self.stats["current_items"].copy(),
                    "current_memory_bytes": self.stats["current_memory_bytes"].copy(),
                }
                
                # Añadir estadísticas de particiones
                cache_stats["partitions"] = {}
                for p in range(self.partitions):
                    cache_stats["partitions"][str(p)] = self.stats["partitions"][p].copy()
                
                # Calcular ratios de aciertos
                total_requests_l1 = cache_stats["hits"]["l1"] + cache_stats["misses"]["l1"]
                total_requests_l2 = cache_stats["hits"]["l2"] + cache_stats["misses"]["l2"]
                total_requests = cache_stats["hits"]["total"] + cache_stats["misses"]["total"]
                
                cache_stats["hit_ratio"] = {
                    "l1": cache_stats["hits"]["l1"] / total_requests_l1 if total_requests_l1 > 0 else 0,
                    "l2": cache_stats["hits"]["l2"] / total_requests_l2 if total_requests_l2 > 0 else 0,
                    "total": cache_stats["hits"]["total"] / total_requests if total_requests > 0 else 0
                }
                
                # Calcular eficiencia de compresión
                if cache_stats["compression"]["compressed_items"] > 0:
                    cache_stats["compression"]["avg_savings_per_item"] = (
                        cache_stats["compression"]["savings_bytes"] / 
                        cache_stats["compression"]["compressed_items"]
                    )
                else:
                    cache_stats["compression"]["avg_savings_per_item"] = 0
                
                # Obtener estadísticas de Redis (L2) si está habilitado
                if self.l2_enabled and self.redis_client and await self._ensure_redis_connected():
                    try:
                        # Obtener info de Redis
                        redis_info = await self.redis_client.info()
                        
                        # Extraer métricas relevantes
                        cache_stats["redis"] = {
                            "used_memory": redis_info.get("used_memory", 0),
                            "used_memory_human": redis_info.get("used_memory_human", "0B"),
                            "used_memory_peak": redis_info.get("used_memory_peak", 0),
                            "used_memory_peak_human": redis_info.get("used_memory_peak_human", "0B"),
                            "total_connections_received": redis_info.get("total_connections_received", 0),
                            "total_commands_processed": redis_info.get("total_commands_processed", 0),
                            "instantaneous_ops_per_sec": redis_info.get("instantaneous_ops_per_sec", 0),
                            "hit_rate": redis_info.get("keyspace_hits", 0) / 
                                       (redis_info.get("keyspace_hits", 0) + redis_info.get("keyspace_misses", 1))
                                       if (redis_info.get("keyspace_hits", 0) + redis_info.get("keyspace_misses", 0)) > 0 else 0,
                            "evicted_keys": redis_info.get("evicted_keys", 0),
                            "expired_keys": redis_info.get("expired_keys", 0),
                            "connected_clients": redis_info.get("connected_clients", 0),
                        }
                        
                        # Obtener número de claves
                        db_info = redis_info.get("db0", {})
                        if isinstance(db_info, dict):
                            cache_stats["redis"]["keys"] = db_info.get("keys", 0)
                        else:
                            # En algunos clientes Redis, db0 viene como string "keys=X,expires=Y"
                            try:
                                if isinstance(db_info, str) and "keys=" in db_info:
                                    keys_part = db_info.split("keys=")[1].split(",")[0]
                                    cache_stats["redis"]["keys"] = int(keys_part)
                                else:
                                    cache_stats["redis"]["keys"] = 0
                            except (ValueError, IndexError):
                                cache_stats["redis"]["keys"] = 0
                        
                        # Actualizar estadísticas de L2
                        self.stats["current_items"]["l2"] = cache_stats["redis"]["keys"]
                        cache_stats["current_items"]["l2"] = self.stats["current_items"]["l2"]
                        cache_stats["current_items"]["total"] = (
                            cache_stats["current_items"]["l1"] + cache_stats["current_items"]["l2"]
                        )
                        
                    except Exception as e:
                        logger.warning(f"No se pudieron obtener estadísticas de Redis: {e}")
                        cache_stats["redis_stats_error"] = str(e)
                
                # Añadir configuración actual
                cache_stats["config"] = {
                    "l1_max_bytes": self.l1_max_bytes,
                    "max_memory_bytes": self.max_memory_bytes,
                    "ttl": self.ttl,
                    "compression_threshold": self.compression_threshold,
                    "compression_level": self.compression_level,
                    "partitions": self.partitions,
                    "cache_policy": self.cache_policy.value,
                    "l2_enabled": self.l2_enabled,
                    "prefetch_threshold": self.prefetch_threshold
                }
                
                # Añadir tiempo de ejecución
                cache_stats["uptime"] = {
                    "started_at": getattr(self, "_start_time", time.time()),
                    "uptime_seconds": time.time() - getattr(self, "_start_time", time.time())
                }
                
                return cache_stats
                
        except Exception as e:
            logger.error(f"Error al obtener estadísticas del caché: {e}")
            return {
                "error": str(e),
                "timestamp": time.time()
            }

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
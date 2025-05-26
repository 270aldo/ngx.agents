"""
Gestor de estado optimizado para NGX Agents.

Este módulo implementa un sistema avanzado para gestionar el estado y contexto
de conversaciones, con soporte para persistencia, caché y embeddings.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from core.logging_config import get_logger

# Intentar importar telemetry_manager del módulo real, si falla usar el mock
try:
    from core.telemetry import telemetry_manager
except ImportError:
    from tests.mocks.core.telemetry import telemetry_manager

# Configurar logger
logger = get_logger(__name__)

# Intentar importar Redis y el pool manager
try:
    import redis.asyncio as redis
    from core.redis_pool import redis_pool_manager

    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis no está disponible. Usando caché en memoria.")
    REDIS_AVAILABLE = False
    redis_pool_manager = None


class LRUCache:
    """
    Implementación de caché LRU (Least Recently Used).

    Mantiene los elementos más recientemente utilizados y elimina
    los menos utilizados cuando se alcanza la capacidad máxima.
    """

    def __init__(self, capacity: int = 1000):
        """
        Inicializa la caché LRU.

        Args:
            capacity: Capacidad máxima de la caché
        """
        self.capacity = capacity
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.usage_order: List[str] = []

    def get(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor de la caché.

        Args:
            key: Clave a buscar

        Returns:
            Optional[Any]: Valor asociado o None si no existe
        """
        if key not in self.cache:
            return None

        # Verificar TTL
        entry = self.cache[key]
        if "ttl" in entry and "timestamp" in entry:
            if time.time() - entry["timestamp"] > entry["ttl"]:
                # Expirado
                del self.cache[key]
                self.usage_order.remove(key)
                return None

        # Actualizar orden de uso
        self.usage_order.remove(key)
        self.usage_order.append(key)

        return entry.get("value")

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Añade o actualiza un valor en la caché.

        Args:
            key: Clave para el valor
            value: Valor a almacenar
            ttl: Tiempo de vida en segundos (opcional)
        """
        # Si la clave ya existe, actualizar orden de uso
        if key in self.cache:
            self.usage_order.remove(key)

        # Si la caché está llena, eliminar el elemento menos usado
        elif len(self.cache) >= self.capacity:
            oldest_key = self.usage_order.pop(0)
            del self.cache[oldest_key]

        # Añadir nuevo valor
        entry = {"value": value, "timestamp": time.time()}
        if ttl is not None:
            entry["ttl"] = ttl

        self.cache[key] = entry
        self.usage_order.append(key)

    def delete(self, key: str) -> bool:
        """
        Elimina un valor de la caché.

        Args:
            key: Clave a eliminar

        Returns:
            bool: True si se eliminó correctamente
        """
        if key in self.cache:
            del self.cache[key]
            self.usage_order.remove(key)
            return True
        return False

    def clear(self) -> None:
        """Limpia toda la caché."""
        self.cache.clear()
        self.usage_order.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la caché.

        Returns:
            Dict[str, Any]: Estadísticas
        """
        return {
            "size": len(self.cache),
            "capacity": self.capacity,
            "usage_percentage": (
                len(self.cache) / self.capacity * 100 if self.capacity > 0 else 0
            ),
        }


class StateManager:
    """
    Gestor de estado avanzado para NGX Agents.

    Proporciona funcionalidades para almacenar y recuperar estado
    de conversaciones, con soporte para persistencia, caché y
    metadatos avanzados.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        redis_url: Optional[str] = None,
        cache_capacity: int = 1000,
        default_ttl: int = 3600,
        enable_persistence: bool = True,
    ):
        """
        Inicializa el gestor de estado.

        Args:
            redis_url: URL de conexión a Redis (opcional)
            cache_capacity: Capacidad de la caché en memoria
            default_ttl: TTL por defecto en segundos
            enable_persistence: Habilitar persistencia
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        # Configuración
        self.redis_url = redis_url
        self.cache_capacity = cache_capacity
        self.default_ttl = default_ttl
        self.enable_persistence = enable_persistence

        # Cliente Redis
        self.redis_client = None

        # Caché en memoria
        self.memory_cache = LRUCache(capacity=cache_capacity)

        # Caché temporal para contexto
        self.temp_context_cache = LRUCache(capacity=cache_capacity)

        # Lock para operaciones concurrentes
        self._lock = asyncio.Lock()

        # Estado de inicialización
        self.is_initialized = False

        # Estadísticas
        self.stats = {
            "get_operations": 0,
            "set_operations": 0,
            "delete_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "redis_operations": 0,
            "errors": 0,
        }

        self._initialized = True
        logger.info("Gestor de estado inicializado")

    async def initialize(self) -> bool:
        """
        Inicializa conexiones y recursos.

        Returns:
            bool: True si la inicialización fue exitosa
        """
        async with self._lock:
            if self.is_initialized:
                return True

            # Inicializar Redis si está disponible
            if REDIS_AVAILABLE and self.enable_persistence and redis_pool_manager:
                try:
                    # Usar el pool manager para obtener el cliente
                    self.redis_client = await redis_pool_manager.get_client()
                    if self.redis_client:
                        # Verificar conexión
                        await self.redis_client.ping()
                        logger.info("Conexión a Redis establecida desde el pool")
                    else:
                        logger.warning("No se pudo obtener cliente Redis del pool")
                except Exception as e:
                    logger.error(f"Error al conectar con Redis: {str(e)}")
                    self.redis_client = None
                    self.stats["errors"] += 1

            self.is_initialized = True
            return True

    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor de Redis.

        Args:
            key: Clave a buscar

        Returns:
            Optional[Any]: Valor asociado o None si no existe
        """
        if not self.redis_client:
            return None

        try:
            self.stats["redis_operations"] += 1
            value = await self.redis_client.get(key)

            if value:
                # Deserializar JSON
                return json.loads(value)

            return None

        except Exception as e:
            logger.error(f"Error al obtener valor de Redis: {str(e)}")
            self.stats["errors"] += 1
            return None

    async def _set_in_redis(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """
        Almacena un valor en Redis.

        Args:
            key: Clave para el valor
            value: Valor a almacenar
            ttl: Tiempo de vida en segundos (opcional)

        Returns:
            bool: True si se almacenó correctamente
        """
        if not self.redis_client:
            return False

        try:
            self.stats["redis_operations"] += 1

            # Serializar a JSON
            serialized = json.dumps(value)

            if ttl:
                await self.redis_client.setex(key, ttl, serialized)
            else:
                await self.redis_client.set(key, serialized)

            return True

        except Exception as e:
            logger.error(f"Error al almacenar valor en Redis: {str(e)}")
            self.stats["errors"] += 1
            return False

    async def _delete_from_redis(self, key: str) -> bool:
        """
        Elimina un valor de Redis.

        Args:
            key: Clave a eliminar

        Returns:
            bool: True si se eliminó correctamente
        """
        if not self.redis_client:
            return False

        try:
            self.stats["redis_operations"] += 1
            await self.redis_client.delete(key)
            return True

        except Exception as e:
            logger.error(f"Error al eliminar valor de Redis: {str(e)}")
            self.stats["errors"] += 1
            return False

    async def get_conversation_state(self, conversation_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de una conversación.

        Args:
            conversation_id: ID de la conversación

        Returns:
            Dict[str, Any]: Estado de la conversación
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="get_conversation_state",
            attributes={"conversation_id": conversation_id},
        )

        try:
            # Inicializar si es necesario
            if not self.is_initialized:
                await self.initialize()

            # Actualizar estadísticas
            self.stats["get_operations"] += 1

            # Clave para la caché
            cache_key = f"conv:{conversation_id}"

            # Verificar caché en memoria
            cached_value = self.memory_cache.get(cache_key)
            if cached_value is not None:
                self.stats["cache_hits"] += 1
                telemetry_manager.set_span_attribute(span_id, "cache", "hit")
                return cached_value

            self.stats["cache_misses"] += 1

            # Verificar Redis
            redis_value = await self._get_from_redis(cache_key)
            if redis_value is not None:
                # Actualizar caché en memoria
                self.memory_cache.put(cache_key, redis_value, ttl=self.default_ttl)
                telemetry_manager.set_span_attribute(span_id, "source", "redis")
                return redis_value

            # No se encontró, retornar estado vacío
            empty_state = {
                "conversation_id": conversation_id,
                "messages": [],
                "metadata": {},
                "created_at": time.time(),
                "updated_at": time.time(),
            }

            telemetry_manager.set_span_attribute(span_id, "source", "new")
            return empty_state

        except Exception as e:
            logger.error(f"Error al obtener estado de conversación: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1

            # Retornar estado vacío en caso de error
            return {
                "conversation_id": conversation_id,
                "messages": [],
                "metadata": {},
                "created_at": time.time(),
                "updated_at": time.time(),
                "error": str(e),
            }

        finally:
            telemetry_manager.end_span(span_id)

    async def set_conversation_state(
        self, conversation_id: str, state: Dict[str, Any]
    ) -> bool:
        """
        Actualiza el estado de una conversación.

        Args:
            conversation_id: ID de la conversación
            state: Nuevo estado

        Returns:
            bool: True si se actualizó correctamente
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="set_conversation_state",
            attributes={"conversation_id": conversation_id},
        )

        try:
            # Inicializar si es necesario
            if not self.is_initialized:
                await self.initialize()

            # Actualizar estadísticas
            self.stats["set_operations"] += 1

            # Clave para la caché
            cache_key = f"conv:{conversation_id}"

            # Actualizar timestamp
            state["updated_at"] = time.time()

            # Actualizar caché en memoria
            self.memory_cache.put(cache_key, state, ttl=self.default_ttl)

            # Actualizar Redis si está disponible
            if self.enable_persistence:
                await self._set_in_redis(cache_key, state, ttl=self.default_ttl * 2)

            telemetry_manager.set_span_attribute(span_id, "success", True)
            return True

        except Exception as e:
            logger.error(f"Error al actualizar estado de conversación: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return False

        finally:
            telemetry_manager.end_span(span_id)

    async def delete_conversation_state(self, conversation_id: str) -> bool:
        """
        Elimina el estado de una conversación.

        Args:
            conversation_id: ID de la conversación

        Returns:
            bool: True si se eliminó correctamente
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="delete_conversation_state",
            attributes={"conversation_id": conversation_id},
        )

        try:
            # Inicializar si es necesario
            if not self.is_initialized:
                await self.initialize()

            # Actualizar estadísticas
            self.stats["delete_operations"] += 1

            # Clave para la caché
            cache_key = f"conv:{conversation_id}"

            # Eliminar de caché en memoria
            self.memory_cache.delete(cache_key)

            # Eliminar de Redis si está disponible
            if self.enable_persistence:
                await self._delete_from_redis(cache_key)

            telemetry_manager.set_span_attribute(span_id, "success", True)
            return True

        except Exception as e:
            logger.error(f"Error al eliminar estado de conversación: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return False

        finally:
            telemetry_manager.end_span(span_id)

    async def add_message_to_conversation(
        self, conversation_id: str, message: Dict[str, Any]
    ) -> bool:
        """
        Añade un mensaje a una conversación.

        Args:
            conversation_id: ID de la conversación
            message: Mensaje a añadir

        Returns:
            bool: True si se añadió correctamente
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="add_message_to_conversation",
            attributes={"conversation_id": conversation_id},
        )

        try:
            # Obtener estado actual
            state = await self.get_conversation_state(conversation_id)

            # Añadir timestamp si no existe
            if "timestamp" not in message:
                message["timestamp"] = time.time()

            # Añadir ID si no existe
            if "message_id" not in message:
                message["message_id"] = str(uuid.uuid4())

            # Añadir mensaje
            if "messages" not in state:
                state["messages"] = []

            state["messages"].append(message)

            # Actualizar estado
            result = await self.set_conversation_state(conversation_id, state)

            telemetry_manager.set_span_attribute(span_id, "success", result)
            return result

        except Exception as e:
            logger.error(f"Error al añadir mensaje a conversación: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return False

        finally:
            telemetry_manager.end_span(span_id)

    async def get_conversation_messages(
        self, conversation_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los mensajes de una conversación.

        Args:
            conversation_id: ID de la conversación
            limit: Número máximo de mensajes a retornar (opcional)

        Returns:
            List[Dict[str, Any]]: Lista de mensajes
        """
        # Obtener estado
        state = await self.get_conversation_state(conversation_id)

        # Obtener mensajes
        messages = state.get("messages", [])

        # Aplicar límite si se especifica
        if limit is not None and limit > 0:
            messages = messages[-limit:]

        return messages

    async def set_conversation_metadata(
        self, conversation_id: str, metadata: Dict[str, Any]
    ) -> bool:
        """
        Actualiza los metadatos de una conversación.

        Args:
            conversation_id: ID de la conversación
            metadata: Nuevos metadatos

        Returns:
            bool: True si se actualizó correctamente
        """
        # Obtener estado actual
        state = await self.get_conversation_state(conversation_id)

        # Actualizar metadatos
        if "metadata" not in state:
            state["metadata"] = {}

        state["metadata"].update(metadata)

        # Actualizar estado
        return await self.set_conversation_state(conversation_id, state)

    async def get_conversation_metadata(
        self, conversation_id: str, key: Optional[str] = None
    ) -> Any:
        """
        Obtiene los metadatos de una conversación.

        Args:
            conversation_id: ID de la conversación
            key: Clave específica a obtener (opcional)

        Returns:
            Any: Metadatos completos o valor específico
        """
        # Obtener estado
        state = await self.get_conversation_state(conversation_id)

        # Obtener metadatos
        metadata = state.get("metadata", {})

        # Retornar valor específico si se solicita
        if key is not None:
            return metadata.get(key)

        return metadata

    async def set_temp_context(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """
        Almacena un valor en el contexto temporal.

        Args:
            key: Clave para el valor
            value: Valor a almacenar
            ttl: Tiempo de vida en segundos (opcional)

        Returns:
            bool: True si se almacenó correctamente
        """
        try:
            # Inicializar si es necesario
            if not self.is_initialized:
                await self.initialize()

            # Usar TTL por defecto si no se especifica
            if ttl is None:
                ttl = self.default_ttl

            # Almacenar en caché temporal
            self.temp_context_cache.put(key, value, ttl=ttl)

            return True

        except Exception as e:
            logger.error(f"Error al almacenar en contexto temporal: {str(e)}")
            self.stats["errors"] += 1
            return False

    async def get_temp_context(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor del contexto temporal.

        Args:
            key: Clave a buscar

        Returns:
            Optional[Any]: Valor asociado o None si no existe
        """
        try:
            # Inicializar si es necesario
            if not self.is_initialized:
                await self.initialize()

            # Obtener de caché temporal
            return self.temp_context_cache.get(key)

        except Exception as e:
            logger.error(f"Error al obtener de contexto temporal: {str(e)}")
            self.stats["errors"] += 1
            return None

    async def delete_temp_context(self, key: str) -> bool:
        """
        Elimina un valor del contexto temporal.

        Args:
            key: Clave a eliminar

        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            # Inicializar si es necesario
            if not self.is_initialized:
                await self.initialize()

            # Eliminar de caché temporal
            return self.temp_context_cache.delete(key)

        except Exception as e:
            logger.error(f"Error al eliminar de contexto temporal: {str(e)}")
            self.stats["errors"] += 1
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del gestor de estado.

        Returns:
            Dict[str, Any]: Estadísticas
        """
        # Estadísticas básicas
        result = {
            **self.stats,
            "initialized": self.is_initialized,
            "redis_available": self.redis_client is not None,
            "persistence_enabled": self.enable_persistence,
        }

        # Añadir estadísticas de caché
        result["memory_cache"] = self.memory_cache.get_stats()
        result["temp_context_cache"] = self.temp_context_cache.get_stats()

        return result

    async def close(self) -> None:
        """
        Cierra todas las conexiones y libera recursos.

        Este método debe ser llamado al apagar la aplicación
        para asegurar que todas las conexiones se cierran correctamente.
        """
        async with self._lock:
            try:
                # Cerrar cliente Redis (no el pool, ya que es compartido)
                if self.redis_client:
                    logger.info("Liberando cliente Redis...")
                    # Solo cerrar el cliente, no el pool compartido
                    await self.redis_client.close(close_connection_pool=False)
                    self.redis_client = None
                    logger.info("Cliente Redis liberado correctamente")

                # Limpiar cachés en memoria
                self.memory_cache.clear()
                self.temp_context_cache.clear()

                # Resetear estado
                self.is_initialized = False

                logger.info("StateManager cerrado correctamente")

            except Exception as e:
                logger.error(f"Error al cerrar StateManager: {str(e)}")
                self.stats["errors"] += 1


# Crear instancia global
state_manager = StateManager()

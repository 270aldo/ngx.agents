"""
Redis connection pool manager for NGX Agents.

This module provides a centralized Redis connection pool to improve performance
and resource utilization across the application.
"""

import asyncio
import os
from typing import Optional
from contextlib import asynccontextmanager

from core.logging_config import get_logger

logger = get_logger(__name__)

# Attempt to import Redis
try:
    import redis.asyncio as redis
    from redis.asyncio.connection import ConnectionPool

    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis not available. Connection pooling disabled.")
    REDIS_AVAILABLE = False
    redis = None
    ConnectionPool = None


class RedisPoolManager:
    """
    Manages Redis connection pools for the application.

    This class implements a singleton pattern to ensure only one pool
    is created and shared across the application.
    """

    _instance: Optional["RedisPoolManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the Redis pool manager."""
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._pool: Optional[ConnectionPool] = None
        self._redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Connection pool configuration
        self._max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
        self._min_idle_time = int(os.getenv("REDIS_MIN_IDLE_TIME", "300"))
        self._connection_timeout = int(os.getenv("REDIS_CONNECTION_TIMEOUT", "20"))
        self._socket_timeout = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
        self._socket_connect_timeout = int(
            os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5")
        )

        logger.info(
            f"Redis pool manager initialized with max_connections={self._max_connections}"
        )

    async def initialize(self) -> bool:
        """
        Initialize the Redis connection pool.

        Returns:
            bool: True if initialization was successful
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, skipping pool initialization")
            return False

        async with self._lock:
            if self._pool is not None:
                return True

            try:
                # Create connection pool with optimized settings
                self._pool = ConnectionPool.from_url(
                    self._redis_url,
                    max_connections=self._max_connections,
                    decode_responses=True,
                    socket_timeout=self._socket_timeout,
                    socket_connect_timeout=self._socket_connect_timeout,
                    connection_class=redis.Connection,
                    health_check_interval=30,  # Health check every 30 seconds
                )

                # Test the connection
                test_client = redis.Redis(connection_pool=self._pool)
                await test_client.ping()
                await test_client.close(close_connection_pool=False)

                logger.info("Redis connection pool initialized successfully")
                return True

            except Exception as e:
                logger.error(f"Failed to initialize Redis connection pool: {e}")
                self._pool = None
                return False

    async def get_client(self) -> Optional[redis.Redis]:
        """
        Get a Redis client from the connection pool.

        Returns:
            Optional[redis.Redis]: Redis client or None if not available
        """
        if not REDIS_AVAILABLE:
            return None

        if self._pool is None:
            if not await self.initialize():
                return None

        try:
            return redis.Redis(connection_pool=self._pool)
        except Exception as e:
            logger.error(f"Failed to get Redis client from pool: {e}")
            return None

    @asynccontextmanager
    async def get_client_context(self):
        """
        Context manager for getting a Redis client.

        Ensures the client is properly closed after use.

        Yields:
            Optional[redis.Redis]: Redis client or None if not available
        """
        client = await self.get_client()
        try:
            yield client
        finally:
            if client:
                await client.close(close_connection_pool=False)

    async def close(self) -> None:
        """Close the Redis connection pool."""
        async with self._lock:
            if self._pool:
                await self._pool.disconnect()
                self._pool = None
                logger.info("Redis connection pool closed")

    async def get_pool_stats(self) -> dict:
        """
        Get statistics about the connection pool.

        Returns:
            dict: Pool statistics
        """
        if not self._pool:
            return {"status": "not_initialized"}

        return {
            "status": "active",
            "max_connections": self._max_connections,
            "created_connections": self._pool.created_connections,
            "available_connections": len(self._pool._available_connections),
            "in_use_connections": len(self._pool._in_use_connections),
        }


# Global instance
redis_pool_manager = RedisPoolManager()


# Convenience functions
async def get_redis_client() -> Optional[redis.Redis]:
    """
    Get a Redis client from the global pool.

    Returns:
        Optional[redis.Redis]: Redis client or None if not available
    """
    return await redis_pool_manager.get_client()


async def close_redis_pool() -> None:
    """Close the global Redis connection pool."""
    await redis_pool_manager.close()

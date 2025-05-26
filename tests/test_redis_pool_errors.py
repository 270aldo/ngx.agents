"""
Tests para escenarios de error del Redis connection pool.

Este módulo contiene tests para verificar el comportamiento del pool de
conexiones Redis en situaciones de error.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from core.redis_pool import RedisPoolManager, redis_pool_manager


class TestRedisPoolErrors:
    """Tests para errores en el Redis pool manager."""

    @pytest.fixture
    async def pool_manager(self):
        """Fixture que crea un pool manager limpio para tests."""
        manager = RedisPoolManager()
        # Reset el estado
        manager._pool = None
        manager._initialized = True
        yield manager
        # Cleanup
        if manager._pool:
            await manager.close()

    @pytest.mark.asyncio
    async def test_initialization_failure(self, pool_manager):
        """Test que el pool maneja fallos de inicialización correctamente."""
        with patch("redis.asyncio.Redis") as mock_redis:
            # Simular que ping falla
            mock_client = AsyncMock()
            mock_client.ping.side_effect = Exception("Connection failed")
            mock_redis.return_value = mock_client

            with patch("redis.asyncio.ConnectionPool.from_url") as mock_pool:
                mock_pool.return_value = Mock()

                result = await pool_manager.initialize()
                assert result is False
                assert pool_manager._pool is None

    @pytest.mark.asyncio
    async def test_get_client_when_redis_unavailable(self):
        """Test obtener cliente cuando Redis no está disponible."""
        with patch("core.redis_pool.REDIS_AVAILABLE", False):
            manager = RedisPoolManager()
            client = await manager.get_client()
            assert client is None

    @pytest.mark.asyncio
    async def test_get_client_initialization_failure(self, pool_manager):
        """Test obtener cliente cuando la inicialización falla."""
        with patch.object(pool_manager, "initialize", return_value=False):
            client = await pool_manager.get_client()
            assert client is None

    @pytest.mark.asyncio
    async def test_get_client_context_manager_with_error(self, pool_manager):
        """Test el context manager cuando hay errores."""
        with patch.object(pool_manager, "get_client", return_value=None):
            async with pool_manager.get_client_context() as client:
                assert client is None

    @pytest.mark.asyncio
    async def test_get_client_context_manager_closes_on_exception(self, pool_manager):
        """Test que el context manager cierra el cliente incluso con excepciones."""
        mock_client = AsyncMock()

        with patch.object(pool_manager, "get_client", return_value=mock_client):
            with pytest.raises(Exception):
                async with pool_manager.get_client_context() as client:
                    raise Exception("Test exception")

            # Verificar que se llamó close
            mock_client.close.assert_called_once_with(close_connection_pool=False)

    @pytest.mark.asyncio
    async def test_pool_stats_when_not_initialized(self, pool_manager):
        """Test obtener estadísticas cuando el pool no está inicializado."""
        stats = await pool_manager.get_pool_stats()
        assert stats["status"] == "not_initialized"

    @pytest.mark.asyncio
    async def test_close_when_pool_is_none(self, pool_manager):
        """Test cerrar cuando no hay pool."""
        pool_manager._pool = None
        await pool_manager.close()  # No debería lanzar excepción

    @pytest.mark.asyncio
    async def test_concurrent_initialization(self, pool_manager):
        """Test que múltiples inicializaciones concurrentes se manejan correctamente."""

        # Simular inicialización lenta
        async def slow_init():
            await asyncio.sleep(0.1)
            return True

        with patch.object(pool_manager, "_pool", None):
            with patch("redis.asyncio.ConnectionPool.from_url") as mock_pool:
                mock_pool.return_value = Mock()

                # Crear múltiples tareas de inicialización
                tasks = [pool_manager.initialize() for _ in range(5)]
                results = await asyncio.gather(*tasks)

                # Todas deberían retornar True
                assert all(results)

                # Pero solo se debería crear un pool
                assert mock_pool.from_url.call_count == 1

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test que el patrón singleton funciona correctamente."""
        manager1 = RedisPoolManager()
        manager2 = RedisPoolManager()

        assert manager1 is manager2
        assert id(manager1) == id(manager2)


class TestRedisPoolIntegrationErrors:
    """Tests de integración para errores con el pool de Redis."""

    @pytest.mark.asyncio
    async def test_state_manager_with_pool_failure(self):
        """Test que el StateManager maneja fallos del pool correctamente."""
        from core.state_manager_optimized import StateManager

        # Crear StateManager con Redis habilitado
        state_manager = StateManager(
            enable_persistence=True, redis_url="redis://invalid:6379"
        )

        # Intentar inicializar (debería fallar pero no lanzar excepción)
        result = await state_manager.initialize()
        assert result is True  # StateManager continúa sin Redis

        # Verificar que funciona sin Redis
        await state_manager.set_conversation_state("test_conv", {"data": "test"})
        state = await state_manager.get_conversation_state("test_conv")
        assert state["data"] == "test"

        # Cleanup
        await state_manager.close()

    @pytest.mark.asyncio
    async def test_cache_manager_with_pool_failure(self):
        """Test que el CacheManager maneja fallos del pool correctamente."""
        from clients.vertex_ai.cache import CacheManager

        # Crear CacheManager con Redis habilitado
        cache = CacheManager(use_redis=True, redis_url="redis://invalid:6379")

        # Operaciones deberían funcionar solo con caché en memoria
        await cache.set("test_key", "test_value")
        value = await cache.get("test_key")
        assert value == "test_value"

        # Verificar que Redis está deshabilitado
        assert not cache.l2_enabled


class TestCircuitBreakerWithRedis:
    """Tests para circuit breaker con operaciones Redis."""

    @pytest.mark.asyncio
    async def test_redis_operations_with_circuit_breaker(self):
        """Test que las operaciones Redis funcionan con circuit breaker."""
        from core.state_manager_optimized import StateManager

        # Simular fallos intermitentes de Redis
        fail_count = 0

        async def flaky_redis_operation():
            nonlocal fail_count
            fail_count += 1
            if fail_count <= 3:
                raise Exception("Redis connection error")
            return {"success": True}

        # Crear un circuit breaker para la operación
        from core.circuit_breaker import circuit_breaker

        @circuit_breaker(name="test_redis_op", failure_threshold=2, recovery_timeout=1)
        async def protected_operation():
            return await flaky_redis_operation()

        # Las primeras llamadas deberían fallar
        with pytest.raises(Exception):
            await protected_operation()

        with pytest.raises(Exception):
            await protected_operation()

        # Ahora el circuit breaker debería estar abierto
        from core.circuit_breaker import CircuitBreakerOpenError

        with pytest.raises(CircuitBreakerOpenError):
            await protected_operation()

        # Esperar recuperación
        await asyncio.sleep(1.1)

        # Ahora debería funcionar
        result = await protected_operation()
        assert result["success"] is True

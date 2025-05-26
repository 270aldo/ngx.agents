"""
Tests para el circuit breaker implementation.

Este módulo contiene tests para verificar el comportamiento del circuit breaker
en diferentes escenarios de error.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    circuit_breaker,
)


class TestCircuitBreaker:
    """Tests para la clase CircuitBreaker."""

    @pytest.fixture
    def breaker(self):
        """Fixture que crea un circuit breaker para tests."""
        return CircuitBreaker(
            name="test_breaker",
            failure_threshold=3,
            recovery_timeout=2,
            success_threshold=2,
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_initial_state(self, breaker):
        """Test que el circuit breaker inicia en estado CLOSED."""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open

    @pytest.mark.asyncio
    async def test_successful_calls_pass_through(self, breaker):
        """Test que las llamadas exitosas pasan a través del circuit breaker."""

        async def successful_function():
            return "success"

        result = await breaker.call(successful_function)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker._stats["successful_calls"] == 1
        assert breaker._stats["failed_calls"] == 0

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, breaker):
        """Test que el circuito se abre después de alcanzar el umbral de fallos."""

        async def failing_function():
            raise Exception("Test failure")

        # Hacer fallar el circuit breaker hasta alcanzar el umbral
        for i in range(breaker.failure_threshold):
            with pytest.raises(Exception):
                await breaker.call(failing_function)

        # Verificar que el circuito está abierto
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open
        assert breaker._stats["failed_calls"] == breaker.failure_threshold

        # Verificar que las llamadas son rechazadas cuando está abierto
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(failing_function)

        assert breaker._stats["rejected_calls"] == 1

    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self, breaker):
        """Test que el circuito pasa a HALF_OPEN después del timeout."""

        async def failing_function():
            raise Exception("Test failure")

        # Abrir el circuito
        for i in range(breaker.failure_threshold):
            with pytest.raises(Exception):
                await breaker.call(failing_function)

        assert breaker.state == CircuitState.OPEN

        # Esperar el timeout de recuperación
        await asyncio.sleep(breaker.recovery_timeout + 0.1)

        # La próxima llamada debería cambiar el estado a HALF_OPEN
        async def successful_function():
            return "success"

        result = await breaker.call(successful_function)
        assert result == "success"

        # Después de una llamada exitosa en HALF_OPEN, necesitamos más éxitos
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_closes_after_success_in_half_open(self, breaker):
        """Test que el circuito se cierra después de éxitos en estado HALF_OPEN."""

        async def failing_function():
            raise Exception("Test failure")

        async def successful_function():
            return "success"

        # Abrir el circuito
        for i in range(breaker.failure_threshold):
            with pytest.raises(Exception):
                await breaker.call(failing_function)

        # Esperar timeout
        await asyncio.sleep(breaker.recovery_timeout + 0.1)

        # Hacer llamadas exitosas para cerrar el circuito
        for i in range(breaker.success_threshold):
            result = await breaker.call(successful_function)
            assert result == "success"

        # Verificar que el circuito está cerrado
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_circuit_reopens_on_failure_in_half_open(self, breaker):
        """Test que el circuito se reabre si falla en estado HALF_OPEN."""

        async def failing_function():
            raise Exception("Test failure")

        async def successful_function():
            return "success"

        # Abrir el circuito
        for i in range(breaker.failure_threshold):
            with pytest.raises(Exception):
                await breaker.call(failing_function)

        # Esperar timeout
        await asyncio.sleep(breaker.recovery_timeout + 0.1)

        # Hacer una llamada exitosa para pasar a HALF_OPEN
        await breaker.call(successful_function)
        assert breaker.state == CircuitState.HALF_OPEN

        # Hacer fallar una llamada en HALF_OPEN
        with pytest.raises(Exception):
            await breaker.call(failing_function)

        # Verificar que volvió a OPEN
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_manual_reset(self, breaker):
        """Test que el reset manual funciona correctamente."""

        async def failing_function():
            raise Exception("Test failure")

        # Abrir el circuito
        for i in range(breaker.failure_threshold):
            with pytest.raises(Exception):
                await breaker.call(failing_function)

        assert breaker.state == CircuitState.OPEN

        # Reset manual
        await breaker.reset()

        # Verificar que está cerrado
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._last_failure_time is None

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, breaker):
        """Test que las estadísticas se rastrean correctamente."""

        async def failing_function():
            raise Exception("Test failure")

        async def successful_function():
            return "success"

        # Hacer algunas llamadas exitosas
        for i in range(2):
            await breaker.call(successful_function)

        # Hacer algunas llamadas fallidas
        for i in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_function)

        stats = breaker.get_stats()
        assert stats["stats"]["total_calls"] == 4
        assert stats["stats"]["successful_calls"] == 2
        assert stats["stats"]["failed_calls"] == 2
        assert stats["stats"]["rejected_calls"] == 0


class TestCircuitBreakerDecorator:
    """Tests para el decorador circuit_breaker."""

    @pytest.mark.asyncio
    async def test_decorator_basic_functionality(self):
        """Test que el decorador funciona correctamente."""
        call_count = 0

        @circuit_breaker(name="test_decorated", failure_threshold=2, recovery_timeout=1)
        async def test_function(should_fail: bool = False):
            nonlocal call_count
            call_count += 1
            if should_fail:
                raise Exception("Test failure")
            return "success"

        # Llamada exitosa
        result = await test_function()
        assert result == "success"
        assert call_count == 1

        # Hacer fallar hasta abrir el circuito
        for i in range(2):
            with pytest.raises(Exception):
                await test_function(should_fail=True)

        # Verificar que el circuito está abierto
        with pytest.raises(CircuitBreakerOpenError):
            await test_function()

        # El contador no debería incrementarse cuando el circuito está abierto
        assert call_count == 3  # 1 exitosa + 2 fallidas

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_attributes(self):
        """Test que el decorador preserva los atributos de la función."""

        @circuit_breaker(name="test_attrs")
        async def documented_function():
            """Esta es una función documentada."""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "Esta es una función documentada."

        # Verificar que tiene el circuit breaker adjunto
        assert hasattr(documented_function, "circuit_breaker")
        assert isinstance(documented_function.circuit_breaker, CircuitBreaker)

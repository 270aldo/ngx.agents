"""
Circuit breaker implementation for NGX Agents.

This module provides a circuit breaker pattern implementation to prevent
cascading failures when calling external services.
"""

import asyncio
import time
from enum import Enum
from typing import Callable, Optional, Any, Dict
from functools import wraps

from core.logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """States of the circuit breaker."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external service calls.

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests are rejected immediately
    - HALF_OPEN: Testing if service has recovered

    State transitions:
    - CLOSED -> OPEN: When failure threshold is exceeded
    - OPEN -> HALF_OPEN: After timeout period
    - HALF_OPEN -> CLOSED: When test request succeeds
    - HALF_OPEN -> OPEN: When test request fails
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        success_threshold: int = 3,
        half_open_max_calls: int = 3,
    ):
        """
        Initialize the circuit breaker.

        Args:
            name: Name of the circuit breaker (for logging)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type to catch (default: Exception)
            success_threshold: Successes needed in half-open to close circuit
            half_open_max_calls: Max concurrent calls allowed in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._success_count = 0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rejected_calls": 0,
            "state_changes": [],
        }

        logger.info(
            f"Circuit breaker '{name}' initialized with failure_threshold={failure_threshold}, "
            f"recovery_timeout={recovery_timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get the current state of the circuit breaker."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self._state == CircuitState.OPEN

    async def _change_state(self, new_state: CircuitState) -> None:
        """Change the circuit breaker state."""
        old_state = self._state
        self._state = new_state

        # Log state change
        logger.info(
            f"Circuit breaker '{self.name}' state changed: {old_state.value} -> {new_state.value}"
        )

        # Record in statistics
        self._stats["state_changes"].append(
            {"from": old_state.value, "to": new_state.value, "timestamp": time.time()}
        )

        # Reset counters based on new state
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
            self._half_open_calls = 0

    async def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        return (
            self._state == CircuitState.OPEN
            and self._last_failure_time
            and time.time() - self._last_failure_time >= self.recovery_timeout
        )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: If function fails
        """
        async with self._lock:
            self._stats["total_calls"] += 1

            # Check if we should attempt reset
            if await self._should_attempt_reset():
                await self._change_state(CircuitState.HALF_OPEN)

            # Handle based on current state
            if self._state == CircuitState.OPEN:
                self._stats["rejected_calls"] += 1
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. Service calls are suspended."
                )

            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    self._stats["rejected_calls"] += 1
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN but max calls reached."
                    )
                self._half_open_calls += 1

        # Execute the function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            self._stats["successful_calls"] += 1

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    await self._change_state(CircuitState.CLOSED)

            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0  # Reset failure count on success

    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self._stats["failed_calls"] += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    await self._change_state(CircuitState.OPEN)

            elif self._state == CircuitState.HALF_OPEN:
                await self._change_state(CircuitState.OPEN)

    async def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        async with self._lock:
            await self._change_state(CircuitState.CLOSED)
            self._failure_count = 0
            self._last_failure_time = None

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "stats": self._stats.copy(),
            "failure_count": self._failure_count,
            "success_count": self._success_count,
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


def circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
    success_threshold: int = 3,
):
    """
    Decorator to apply circuit breaker pattern to async functions.

    Args:
        name: Circuit breaker name (defaults to function name)
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before attempting recovery
        expected_exception: Exception type to catch
        success_threshold: Successes needed to close circuit

    Example:
        @circuit_breaker(name="external_api", failure_threshold=3)
        async def call_external_api():
            # API call logic
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Create circuit breaker instance
        breaker_name = name or f"{func.__module__}.{func.__name__}"
        breaker = CircuitBreaker(
            name=breaker_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            success_threshold=success_threshold,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)

        # Attach breaker instance for inspection
        wrapper.circuit_breaker = breaker

        return wrapper

    return decorator


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """Get a circuit breaker by name from the registry."""
    return _circuit_breakers.get(name)


def register_circuit_breaker(breaker: CircuitBreaker) -> None:
    """Register a circuit breaker in the global registry."""
    _circuit_breakers[breaker.name] = breaker
    logger.info(f"Registered circuit breaker: {breaker.name}")


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all registered circuit breakers."""
    return _circuit_breakers.copy()


async def reset_all_circuit_breakers() -> None:
    """Reset all registered circuit breakers."""
    for breaker in _circuit_breakers.values():
        await breaker.reset()
    logger.info(f"Reset {len(_circuit_breakers)} circuit breakers")

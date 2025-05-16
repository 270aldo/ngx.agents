"""
Sistema de circuit breaker para servicios externos.

Este módulo proporciona funcionalidades para implementar el patrón circuit breaker,
que permite detectar fallos en servicios externos y evitar llamadas innecesarias
cuando un servicio está caído.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable, List, Tuple, Union
from datetime import datetime, timedelta
from functools import wraps
import random

# Configurar logger
logger = logging.getLogger(__name__)

class CircuitState(str, Enum):
    """Estados posibles del circuit breaker."""
    CLOSED = "closed"      # Funcionamiento normal, las llamadas pasan
    OPEN = "open"          # Circuito abierto, las llamadas fallan rápidamente
    HALF_OPEN = "half_open"  # Probando si el servicio se ha recuperado

class CircuitBreakerConfig:
    """Configuración del circuit breaker."""
    
    def __init__(
        self,
        failure_threshold: int = 5,           # Número de fallos para abrir el circuito
        success_threshold: int = 2,           # Número de éxitos para cerrar el circuito
        timeout: int = 60,                    # Tiempo en segundos que el circuito permanece abierto
        fallback_function: Optional[Callable] = None,  # Función a llamar cuando el circuito está abierto
        exclude_exceptions: Optional[List[type]] = None,  # Excepciones que no cuentan como fallos
        include_exceptions: Optional[List[type]] = None,  # Solo estas excepciones cuentan como fallos
        window_size: int = 10,                # Tamaño de la ventana para calcular la tasa de fallos
        error_threshold_percentage: float = 50.0  # Porcentaje de fallos para abrir el circuito
    ):
        """
        Inicializa la configuración del circuit breaker.
        
        Args:
            failure_threshold: Número de fallos para abrir el circuito
            success_threshold: Número de éxitos para cerrar el circuito
            timeout: Tiempo en segundos que el circuito permanece abierto
            fallback_function: Función a llamar cuando el circuito está abierto
            exclude_exceptions: Excepciones que no cuentan como fallos
            include_exceptions: Solo estas excepciones cuentan como fallos
            window_size: Tamaño de la ventana para calcular la tasa de fallos
            error_threshold_percentage: Porcentaje de fallos para abrir el circuito
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.fallback_function = fallback_function
        self.exclude_exceptions = exclude_exceptions or []
        self.include_exceptions = include_exceptions
        self.window_size = window_size
        self.error_threshold_percentage = error_threshold_percentage
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la configuración a un diccionario.
        
        Returns:
            Diccionario con los datos de la configuración
        """
        return {
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "timeout": self.timeout,
            "has_fallback": self.fallback_function is not None,
            "exclude_exceptions": [exc.__name__ for exc in self.exclude_exceptions],
            "include_exceptions": [exc.__name__ for exc in self.include_exceptions] if self.include_exceptions else None,
            "window_size": self.window_size,
            "error_threshold_percentage": self.error_threshold_percentage
        }

class CircuitBreaker:
    """
    Implementación del patrón circuit breaker.
    
    Esta clase proporciona funcionalidades para implementar el patrón circuit breaker,
    que permite detectar fallos en servicios externos y evitar llamadas innecesarias
    cuando un servicio está caído.
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Inicializa el circuit breaker.
        
        Args:
            name: Nombre del circuit breaker
            config: Configuración del circuit breaker
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change_time = datetime.now()
        
        # Historial de resultados para calcular la tasa de fallos
        self.results_window: List[bool] = []  # True = éxito, False = fallo
        
        # Lock para operaciones concurrentes
        self.lock = asyncio.Lock()
        
        # Estadísticas
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rejected_calls": 0,
            "fallback_calls": 0,
            "state_changes": 0,
            "avg_response_time": 0.0
        }
        
        logger.info(f"Circuit breaker '{name}' inicializado en estado {self.state}")
    
    async def execute(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Ejecuta una función protegida por el circuit breaker.
        
        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales para la función
            **kwargs: Argumentos con nombre para la función
            
        Returns:
            Resultado de la función
            
        Raises:
            CircuitBreakerOpenError: Si el circuito está abierto
            Exception: Cualquier excepción lanzada por la función
        """
        async with self.lock:
            # Verificar si el circuito está abierto
            if self.state == CircuitState.OPEN:
                # Verificar si ha pasado el tiempo de timeout
                if self._should_attempt_reset():
                    # Cambiar a estado half-open
                    await self._transition_to_half_open()
                else:
                    # Rechazar la llamada
                    self.stats["rejected_calls"] += 1
                    self.stats["total_calls"] += 1
                    
                    # Llamar a la función de fallback si existe
                    if self.config.fallback_function:
                        self.stats["fallback_calls"] += 1
                        return await self.config.fallback_function(*args, **kwargs)
                    
                    raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' está abierto")
        
        # Ejecutar la función
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            
            # Registrar éxito
            async with self.lock:
                self.stats["successful_calls"] += 1
                self.stats["total_calls"] += 1
                
                # Actualizar tiempo de respuesta promedio
                execution_time = time.time() - start_time
                self.stats["avg_response_time"] = (
                    (self.stats["avg_response_time"] * (self.stats["successful_calls"] - 1) + execution_time) / 
                    self.stats["successful_calls"]
                )
                
                # Actualizar historial de resultados
                self.results_window.append(True)
                if len(self.results_window) > self.config.window_size:
                    self.results_window.pop(0)
                
                # Actualizar contador de éxitos en estado half-open
                if self.state == CircuitState.HALF_OPEN:
                    self.success_count += 1
                    
                    # Verificar si se debe cerrar el circuito
                    if self.success_count >= self.config.success_threshold:
                        await self._transition_to_closed()
            
            return result
            
        except Exception as e:
            # Verificar si la excepción debe ser ignorada
            is_failure = True
            
            if self.config.exclude_exceptions and any(isinstance(e, exc) for exc in self.config.exclude_exceptions):
                is_failure = False
                
            if self.config.include_exceptions and not any(isinstance(e, exc) for exc in self.config.include_exceptions):
                is_failure = False
            
            # Registrar fallo
            async with self.lock:
                self.stats["total_calls"] += 1
                
                if is_failure:
                    self.stats["failed_calls"] += 1
                    self.last_failure_time = datetime.now()
                    
                    # Actualizar historial de resultados
                    self.results_window.append(False)
                    if len(self.results_window) > self.config.window_size:
                        self.results_window.pop(0)
                    
                    # Actualizar contador de fallos
                    if self.state == CircuitState.CLOSED:
                        self.failure_count += 1
                        
                        # Verificar si se debe abrir el circuito
                        if self._should_trip():
                            await self._transition_to_open()
                    
                    # En estado half-open, un solo fallo abre el circuito
                    elif self.state == CircuitState.HALF_OPEN:
                        await self._transition_to_open()
            
            # Llamar a la función de fallback si existe
            if is_failure and self.config.fallback_function:
                self.stats["fallback_calls"] += 1
                return await self.config.fallback_function(*args, **kwargs)
                
            # Relanzar la excepción
            raise
    
    def _should_trip(self) -> bool:
        """
        Determina si el circuito debe abrirse.
        
        Returns:
            True si el circuito debe abrirse, False en caso contrario
        """
        # Verificar si se ha alcanzado el umbral de fallos
        if self.failure_count >= self.config.failure_threshold:
            return True
            
        # Verificar la tasa de fallos en la ventana
        if len(self.results_window) >= self.config.window_size:
            failure_rate = (self.results_window.count(False) / len(self.results_window)) * 100
            return failure_rate >= self.config.error_threshold_percentage
            
        return False
    
    def _should_attempt_reset(self) -> bool:
        """
        Determina si se debe intentar resetear el circuito.
        
        Returns:
            True si se debe intentar resetear el circuito, False en caso contrario
        """
        if not self.last_state_change_time:
            return False
            
        # Verificar si ha pasado el tiempo de timeout
        elapsed = (datetime.now() - self.last_state_change_time).total_seconds()
        return elapsed >= self.config.timeout
    
    async def _transition_to_open(self) -> None:
        """Cambia el estado del circuito a abierto."""
        if self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change_time = datetime.now()
            self.stats["state_changes"] += 1
            logger.warning(f"Circuit breaker '{self.name}' cambiado a estado OPEN")
    
    async def _transition_to_half_open(self) -> None:
        """Cambia el estado del circuito a medio abierto."""
        if self.state != CircuitState.HALF_OPEN:
            self.state = CircuitState.HALF_OPEN
            self.last_state_change_time = datetime.now()
            self.success_count = 0
            self.stats["state_changes"] += 1
            logger.info(f"Circuit breaker '{self.name}' cambiado a estado HALF_OPEN")
    
    async def _transition_to_closed(self) -> None:
        """Cambia el estado del circuito a cerrado."""
        if self.state != CircuitState.CLOSED:
            self.state = CircuitState.CLOSED
            self.last_state_change_time = datetime.now()
            self.failure_count = 0
            self.stats["state_changes"] += 1
            logger.info(f"Circuit breaker '{self.name}' cambiado a estado CLOSED")
    
    async def reset(self) -> None:
        """Resetea el circuit breaker a su estado inicial."""
        async with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.last_state_change_time = datetime.now()
            self.results_window = []
            logger.info(f"Circuit breaker '{self.name}' reseteado")
    
    def get_state(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del circuit breaker.
        
        Returns:
            Diccionario con el estado actual
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change_time": self.last_state_change_time.isoformat(),
            "results_window": self.results_window,
            "failure_rate": (self.results_window.count(False) / len(self.results_window)) * 100 if self.results_window else 0,
            "config": self.config.to_dict(),
            "stats": self.stats
        }

class CircuitBreakerOpenError(Exception):
    """Excepción lanzada cuando el circuit breaker está abierto."""
    pass

class CircuitBreakerRegistry:
    """
    Registro de circuit breakers.
    
    Esta clase proporciona funcionalidades para gestionar múltiples circuit breakers.
    """
    
    # Instancia única (patrón Singleton)
    _instance = None
    
    def __new__(cls, *args: Any, **kwargs: Any) -> "CircuitBreakerRegistry":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(CircuitBreakerRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el registro de circuit breakers."""
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return
            
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
        self._initialized = True
        
        logger.info("CircuitBreakerRegistry inicializado")
    
    async def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Obtiene o crea un circuit breaker.
        
        Args:
            name: Nombre del circuit breaker
            config: Configuración del circuit breaker
            
        Returns:
            Circuit breaker
        """
        async with self._lock:
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = CircuitBreaker(name, config)
                
            return self.circuit_breakers[name]
    
    async def get(self, name: str) -> Optional[CircuitBreaker]:
        """
        Obtiene un circuit breaker por su nombre.
        
        Args:
            name: Nombre del circuit breaker
            
        Returns:
            Circuit breaker o None si no existe
        """
        return self.circuit_breakers.get(name)
    
    async def reset(self, name: str) -> bool:
        """
        Resetea un circuit breaker.
        
        Args:
            name: Nombre del circuit breaker
            
        Returns:
            True si se ha reseteado, False si no existe
        """
        circuit_breaker = await self.get(name)
        if circuit_breaker:
            await circuit_breaker.reset()
            return True
            
        return False
    
    async def reset_all(self) -> None:
        """Resetea todos los circuit breakers."""
        for circuit_breaker in self.circuit_breakers.values():
            await circuit_breaker.reset()
    
    async def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene el estado de todos los circuit breakers.
        
        Returns:
            Diccionario con el estado de todos los circuit breakers
        """
        return {name: circuit_breaker.get_state() for name, circuit_breaker in self.circuit_breakers.items()}

# Función decoradora para proteger funciones con circuit breaker
def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout: int = 60,
    fallback_function: Optional[Callable] = None,
    exclude_exceptions: Optional[List[type]] = None,
    include_exceptions: Optional[List[type]] = None,
    window_size: int = 10,
    error_threshold_percentage: float = 50.0
):
    """
    Decorador para proteger funciones con circuit breaker.
    
    Args:
        name: Nombre del circuit breaker
        failure_threshold: Número de fallos para abrir el circuito
        success_threshold: Número de éxitos para cerrar el circuito
        timeout: Tiempo en segundos que el circuito permanece abierto
        fallback_function: Función a llamar cuando el circuito está abierto
        exclude_exceptions: Excepciones que no cuentan como fallos
        include_exceptions: Solo estas excepciones cuentan como fallos
        window_size: Tamaño de la ventana para calcular la tasa de fallos
        error_threshold_percentage: Porcentaje de fallos para abrir el circuito
        
    Returns:
        Decorador configurado
    """
    def decorator(func):
        @wraps(func)
        async def wrapper_async(*args, **kwargs):
            # Obtener o crear circuit breaker
            registry = CircuitBreakerRegistry()
            config = CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                timeout=timeout,
                fallback_function=fallback_function,
                exclude_exceptions=exclude_exceptions,
                include_exceptions=include_exceptions,
                window_size=window_size,
                error_threshold_percentage=error_threshold_percentage
            )
            circuit_breaker = await registry.get_or_create(name, config)
            
            # Ejecutar función protegida
            return await circuit_breaker.execute(func, *args, **kwargs)
            
        @wraps(func)
        def wrapper_sync(*args, **kwargs):
            # Para funciones síncronas, crear una versión asíncrona y ejecutarla
            async def async_wrapper():
                # Obtener o crear circuit breaker
                registry = CircuitBreakerRegistry()
                config = CircuitBreakerConfig(
                    failure_threshold=failure_threshold,
                    success_threshold=success_threshold,
                    timeout=timeout,
                    fallback_function=fallback_function,
                    exclude_exceptions=exclude_exceptions,
                    include_exceptions=include_exceptions,
                    window_size=window_size,
                    error_threshold_percentage=error_threshold_percentage
                )
                circuit_breaker = await registry.get_or_create(name, config)
                
                # Ejecutar función protegida
                return await circuit_breaker.execute(
                    lambda *a, **kw: asyncio.to_thread(func, *a, **kw),
                    *args, **kwargs
                )
            
            # Ejecutar la versión asíncrona
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper())
        
        # Determinar si la función original es asíncrona
        if asyncio.iscoroutinefunction(func):
            return wrapper_async
        else:
            return wrapper_sync
            
    return decorator

# Instancia global para uso en toda la aplicación
circuit_breaker_registry = CircuitBreakerRegistry()
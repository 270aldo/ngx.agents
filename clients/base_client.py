"""
Cliente base con funcionalidad común para todos los clientes de servicios externos.

Implementa patrones como reintentos con backoff exponencial, manejo de errores,
y registro de métricas básicas.
"""

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from config.secrets import settings

logger = logging.getLogger(__name__)

# Tipo genérico para las funciones decoradas
T = TypeVar("T")


def retry_with_backoff(
    max_retries: Optional[int] = None, base_delay: Optional[float] = None
):
    """
    Decorador para reintentar funciones con backoff exponencial.

    Args:
        max_retries: Número máximo de reintentos (None usa el valor por defecto)
        base_delay: Tiempo base de espera entre reintentos (None usa el valor por defecto)

    Returns:
        Decorador configurado
    """
    # Usar valores de configuración si no se especifican
    _max_retries = max_retries if max_retries is not None else settings.MAX_RETRIES
    _base_delay = base_delay if base_delay is not None else settings.RETRY_BACKOFF

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper_async(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(
                1, _max_retries + 2
            ):  # +2 porque el primer intento no es reintento
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Si es el último intento, no esperar más
                    if attempt > _max_retries:
                        logger.error(
                            f"Agotados todos los intentos ({_max_retries+1}) para {func.__name__}"
                        )
                        raise last_exception

                    # Calcular tiempo de espera con jitter
                    wait_time = _base_delay * (2 ** (attempt - 1))
                    jitter = random.uniform(0.8, 1.2)  # ±20% de jitter
                    wait_time *= jitter

                    logger.warning(
                        f"Error en {func.__name__} (intento {attempt}/{_max_retries+1}): "
                        f"{str(e)}. Reintentando en {wait_time:.2f}s"
                    )
                    await asyncio.sleep(wait_time)

            # Nunca debería llegar aquí
            assert last_exception is not None
            raise last_exception

        @wraps(func)
        def wrapper_sync(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(1, _max_retries + 2):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt > _max_retries:
                        logger.error(
                            f"Agotados todos los intentos ({_max_retries+1}) para {func.__name__}"
                        )
                        raise last_exception

                    wait_time = _base_delay * (2 ** (attempt - 1))
                    jitter = random.uniform(0.8, 1.2)
                    wait_time *= jitter

                    logger.warning(
                        f"Error en {func.__name__} (intento {attempt}/{_max_retries+1}): "
                        f"{str(e)}. Reintentando en {wait_time:.2f}s"
                    )
                    time.sleep(wait_time)

            assert last_exception is not None
            raise last_exception

        # Determinar si la función original es asíncrona
        if asyncio.iscoroutinefunction(func):
            return wrapper_async
        else:
            return wrapper_sync

    return decorator


class BaseClient(ABC):
    """
    Clase base para todos los clientes de servicios externos.

    Proporciona funcionalidad común como métricas, manejo de errores,
    y métodos de utilidad.
    """

    def __init__(self, service_name: str):
        """
        Inicializa un nuevo cliente.

        Args:
            service_name: Nombre del servicio (para logs y métricas)
        """
        self.service_name = service_name
        self.call_count: Dict[str, int] = {}  # Contador simple de llamadas por método
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """
        Inicializa el cliente (autenticación, configuración, etc.)

        Esta función debe ser implementada por cada cliente concreto.
        """

    def _record_call(self, method_name: str) -> None:
        """
        Registra una llamada a un método para métricas.

        Args:
            method_name: Nombre del método llamado
        """
        if method_name not in self.call_count:
            self.call_count[method_name] = 0
        self.call_count[method_name] += 1

    def get_metrics(self) -> Dict[str, int]:
        """
        Obtiene métricas de uso del cliente.

        Returns:
            Diccionario con contadores de llamadas por método
        """
        return self.call_count.copy()

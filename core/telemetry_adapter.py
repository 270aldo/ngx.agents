"""
Adaptador de telemetría para NGX Agents.

Este módulo proporciona un adaptador que simplifica la integración con el sistema
de telemetría, ofreciendo funciones para medir rendimiento, registrar errores y
crear spans para seguimiento de operaciones.
"""

import functools
import time
from typing import Any, Dict, Optional, Union

# Intentar importar telemetry del módulo real, si falla usar el mock
try:
    from core.telemetry import telemetry_manager

    TELEMETRY_AVAILABLE = True
except ImportError:
    from tests.mocks.core.telemetry import telemetry_manager

    TELEMETRY_AVAILABLE = False

# Configurar logger
from core.logging_config import get_logger

logger = get_logger(__name__)

# Instancia global del adaptador
_telemetry_adapter_instance = None


def get_telemetry_adapter():
    """
    Obtiene la instancia única del adaptador de telemetría.

    Returns:
        TelemetryAdapter: Instancia del adaptador
    """
    global _telemetry_adapter_instance
    if _telemetry_adapter_instance is None:
        _telemetry_adapter_instance = TelemetryAdapter()
    return _telemetry_adapter_instance


def measure_execution_time(
    metric_name: str, attributes: Optional[Dict[str, Any]] = None
):
    """
    Decorador para medir el tiempo de ejecución de una función.

    Args:
        metric_name: Nombre de la métrica
        attributes: Atributos adicionales para la métrica

    Returns:
        Callable: Decorador
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000

                # Registrar métrica
                adapter = get_telemetry_adapter()
                adapter.record_metric(metric_name, execution_time_ms, attributes or {})

        return wrapper

    return decorator


class TelemetryAdapter:
    """
    Adaptador para simplificar la integración con telemetría.

    Proporciona una interfaz simplificada para registrar métricas, spans y eventos,
    con fallback a logging cuando la telemetría no está disponible.
    """

    def __init__(self):
        """Inicializa el adaptador de telemetría."""
        self.telemetry_manager = telemetry_manager

        if TELEMETRY_AVAILABLE:
            logger.info("Adaptador de telemetría inicializado con cliente real")
        else:
            logger.info("Telemetría no disponible, usando modo mock")

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Any:
        """
        Inicia un span para seguimiento de operaciones.

        Args:
            name: Nombre del span
            attributes: Atributos iniciales del span

        Returns:
            Any: Objeto span o ID del span
        """
        return self.telemetry_manager.start_span(name, attributes or {})

    def end_span(self, span: Any) -> None:
        """
        Finaliza un span.

        Args:
            span: Objeto span o ID del span a finalizar
        """
        self.telemetry_manager.end_span(span)

    def set_span_attribute(self, span: Any, key: str, value: Any) -> None:
        """
        Establece un atributo en un span.

        Args:
            span: Objeto span o ID del span
            key: Clave del atributo
            value: Valor del atributo
        """
        self.telemetry_manager.set_span_attribute(span, key, value)

    def add_span_event(
        self, span: Any, name: str, attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Añade un evento a un span.

        Args:
            span: Objeto span o ID del span
            name: Nombre del evento
            attributes: Atributos del evento
        """
        if hasattr(self.telemetry_manager, "add_span_event"):
            self.telemetry_manager.add_span_event(span, name, attributes or {})

    def record_exception(
        self,
        span: Any,
        exception: Exception,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra una excepción en un span.

        Args:
            span: Objeto span o ID del span
            exception: Excepción a registrar
            attributes: Atributos adicionales
        """
        if hasattr(self.telemetry_manager, "record_exception"):
            self.telemetry_manager.record_exception(span, exception, attributes or {})

    def record_metric(
        self,
        name: str,
        value: Union[int, float],
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra una métrica.

        Args:
            name: Nombre de la métrica
            value: Valor de la métrica
            attributes: Atributos de la métrica
        """
        # Registrar en log para debugging
        attr_str = ", ".join(f"{k}={v}" for k, v in (attributes or {}).items())
        logger.debug(f"METRIC: {name} = {value} {{{attr_str}}}")

    def record_counter(
        self, name: str, increment: int = 1, attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Incrementa un contador.

        Args:
            name: Nombre del contador
            increment: Valor a incrementar
            attributes: Atributos del contador
        """
        # Registrar en log para debugging
        attr_str = ", ".join(f"{k}={v}" for k, v in (attributes or {}).items())
        logger.debug(f"COUNTER: {name} += {increment} {{{attr_str}}}")

    def record_histogram(
        self,
        name: str,
        value: Union[int, float],
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra un valor en un histograma.

        Args:
            name: Nombre del histograma
            value: Valor a registrar
            attributes: Atributos del histograma
        """
        # Registrar en log para debugging
        attr_str = ", ".join(f"{k}={v}" for k, v in (attributes or {}).items())
        logger.debug(f"HISTOGRAM: {name} = {value} {{{attr_str}}}")


# Crear instancia global
telemetry_adapter = TelemetryAdapter()

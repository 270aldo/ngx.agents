"""
Adaptador de telemetría para NGX Agents.

Este módulo proporciona un adaptador que simplifica la integración con el sistema
de telemetría, ofreciendo funciones para medir rendimiento, registrar errores y
crear spans para seguimiento de operaciones.
"""

import functools
import logging
import time
from typing import Any, Dict, Optional, Union

# Importar telemetría
try:
    from core.telemetry import TelemetryClient

    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False

# Configurar logger
logger = logging.getLogger(__name__)

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
        self.client = None

        if TELEMETRY_AVAILABLE:
            try:
                self.client = TelemetryClient.get_instance()
                logger.info("Adaptador de telemetría inicializado con cliente real")
            except Exception as e:
                logger.warning(f"Error al inicializar cliente de telemetría: {e}")
        else:
            logger.info("Telemetría no disponible, usando modo mock")

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Any:
        """
        Inicia un span para seguimiento de operaciones.

        Args:
            name: Nombre del span
            attributes: Atributos iniciales del span

        Returns:
            Any: Objeto span o None si la telemetría no está disponible
        """
        if self.client:
            try:
                return self.client.start_span(name, attributes or {})
            except Exception as e:
                logger.warning(f"Error al iniciar span '{name}': {e}")

        # Modo mock: retornar un diccionario simple
        return {"name": name, "attributes": attributes or {}, "events": []}

    def end_span(self, span: Any) -> None:
        """
        Finaliza un span.

        Args:
            span: Objeto span a finalizar
        """
        if self.client and not isinstance(span, dict):
            try:
                self.client.end_span(span)
            except Exception as e:
                logger.warning(f"Error al finalizar span: {e}")

    def set_span_attribute(self, span: Any, key: str, value: Any) -> None:
        """
        Establece un atributo en un span.

        Args:
            span: Objeto span
            key: Clave del atributo
            value: Valor del atributo
        """
        if self.client and not isinstance(span, dict):
            try:
                self.client.set_span_attribute(span, key, value)
            except Exception as e:
                logger.warning(f"Error al establecer atributo '{key}' en span: {e}")
        elif isinstance(span, dict):
            # Modo mock: actualizar diccionario
            span["attributes"][key] = value

    def add_span_event(
        self, span: Any, name: str, attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Añade un evento a un span.

        Args:
            span: Objeto span
            name: Nombre del evento
            attributes: Atributos del evento
        """
        if self.client and not isinstance(span, dict):
            try:
                self.client.add_span_event(span, name, attributes or {})
            except Exception as e:
                logger.warning(f"Error al añadir evento '{name}' a span: {e}")
        elif isinstance(span, dict):
            # Modo mock: añadir a lista de eventos
            span["events"].append({"name": name, "attributes": attributes or {}})

    def record_exception(self, span: Any, exception: Exception) -> None:
        """
        Registra una excepción en un span.

        Args:
            span: Objeto span
            exception: Excepción a registrar
        """
        if self.client and not isinstance(span, dict):
            try:
                self.client.record_exception(span, exception)
            except Exception as e:
                logger.warning(f"Error al registrar excepción en span: {e}")
        elif isinstance(span, dict):
            # Modo mock: añadir como evento
            span["events"].append(
                {
                    "name": "exception",
                    "attributes": {
                        "exception.type": type(exception).__name__,
                        "exception.message": str(exception),
                    },
                }
            )

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
        if self.client:
            try:
                self.client.record_metric(name, value, attributes or {})
            except Exception as e:
                logger.warning(f"Error al registrar métrica '{name}': {e}")
        else:
            # Modo mock: registrar en log
            attr_str = ", ".join(f"{k}={v}" for k, v in (attributes or {}).items())
            logger.info(f"METRIC: {name} = {value} {{{attr_str}}}")

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
        if self.client:
            try:
                self.client.record_counter(name, increment, attributes or {})
            except Exception as e:
                logger.warning(f"Error al incrementar contador '{name}': {e}")
        else:
            # Modo mock: registrar en log
            attr_str = ", ".join(f"{k}={v}" for k, v in (attributes or {}).items())
            logger.info(f"COUNTER: {name} += {increment} {{{attr_str}}}")

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
        if self.client:
            try:
                self.client.record_histogram(name, value, attributes or {})
            except Exception as e:
                logger.warning(f"Error al registrar histograma '{name}': {e}")
        else:
            # Modo mock: registrar en log
            attr_str = ", ".join(f"{k}={v}" for k, v in (attributes or {}).items())
            logger.info(f"HISTOGRAM: {name} = {value} {{{attr_str}}}")

    def get_tracer(self, name: str) -> Any:
        """
        Obtiene un tracer para instrumentación manual.

        Args:
            name: Nombre del tracer

        Returns:
            Any: Objeto tracer o None si la telemetría no está disponible
        """
        if self.client:
            try:
                return self.client.get_tracer(name)
            except Exception as e:
                logger.warning(f"Error al obtener tracer '{name}': {e}")

        # Modo mock: retornar None
        return None

    def get_meter(self, name: str) -> Any:
        """
        Obtiene un meter para instrumentación manual.

        Args:
            name: Nombre del meter

        Returns:
            Any: Objeto meter o None si la telemetría no está disponible
        """
        if self.client:
            try:
                return self.client.get_meter(name)
            except Exception as e:
                logger.warning(f"Error al obtener meter '{name}': {e}")

        # Modo mock: retornar None
        return None

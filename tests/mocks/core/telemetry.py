"""
Mock del módulo de telemetría para pruebas.

Este módulo proporciona versiones simuladas de las funciones de telemetría
para usar en pruebas sin depender de OpenTelemetry.
"""

import logging
from typing import Dict, Any, Optional, Union

# Configurar logger
logger = logging.getLogger(__name__)


def initialize_telemetry() -> None:
    """
    Inicializa la telemetría simulada para pruebas.
    """
    logger.info("Mock: Telemetría inicializada (simulada)")


def shutdown_telemetry() -> None:
    """
    Cierra la telemetría simulada para pruebas.
    """
    logger.info("Mock: Telemetría cerrada (simulada)")


def get_tracer(name: str):
    """
    Obtiene un tracer simulado para pruebas.

    Args:
        name: Nombre del componente

    Returns:
        Tracer simulado
    """

    class MockTracer:
        def start_as_current_span(self, name, **kwargs):
            class MockSpan:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

                def set_attribute(self, key, value):
                    pass

                def record_exception(self, exception, attributes=None):
                    pass

                def set_status(self, status):
                    pass

                def add_event(self, name, attributes=None):
                    pass

            return MockSpan()

        def start_span(self, name, **kwargs):
            class MockSpan:
                def set_attribute(self, key, value):
                    pass

                def record_exception(self, exception, attributes=None):
                    pass

                def set_status(self, status):
                    pass

                def add_event(self, name, attributes=None):
                    pass

            return MockSpan()

    return MockTracer()


def get_meter(name: str):
    """
    Obtiene un meter simulado para pruebas.

    Args:
        name: Nombre del componente

    Returns:
        Meter simulado
    """

    class MockMeter:
        def create_counter(self, name, **kwargs):
            class MockCounter:
                def add(self, value, attributes=None):
                    pass

            return MockCounter()

        def create_histogram(self, name, **kwargs):
            class MockHistogram:
                def record(self, value, attributes=None):
                    pass

            return MockHistogram()

    return MockMeter()


def extract_trace_context(carrier: Dict[str, str]) -> Optional[Dict]:
    """
    Extrae el contexto de trace simulado para pruebas.

    Args:
        carrier: Headers HTTP

    Returns:
        Contexto de trace simulado
    """
    return {}


def inject_trace_context(carrier: Dict[str, str]) -> None:
    """
    Inyecta el contexto de trace simulado para pruebas.

    Args:
        carrier: Headers HTTP
    """
    carrier["X-Trace-ID"] = "mock-trace-id"
    carrier["X-Span-ID"] = "mock-span-id"


def record_exception(
    exception: Exception, attributes: Optional[Dict[str, str]] = None
) -> None:
    """
    Registra una excepción simulada para pruebas.

    Args:
        exception: Excepción a registrar
        attributes: Atributos adicionales
    """
    logger.error(f"Mock: Excepción registrada: {exception}")


def instrument_fastapi(app) -> None:
    """
    Instrumenta una aplicación FastAPI simulada para pruebas.

    Args:
        app: Aplicación FastAPI
    """
    logger.info("Mock: Aplicación FastAPI instrumentada (simulada)")


def create_span(
    name: str, attributes: Optional[Dict[str, str]] = None, kind: str = "INTERNAL"
) -> Any:
    """
    Crea un nuevo span simulado para pruebas.

    Args:
        name: Nombre del span
        attributes: Atributos del span
        kind: Tipo de span

    Returns:
        Span simulado
    """

    class MockSpan:
        def set_attribute(self, key, value):
            pass

        def record_exception(self, exception, attributes=None):
            pass

        def set_status(self, status):
            pass

        def add_event(self, name, attributes=None):
            pass

    return MockSpan()


def add_span_event(name: str, attributes: Optional[Dict[str, str]] = None) -> None:
    """
    Añade un evento al span simulado para pruebas.

    Args:
        name: Nombre del evento
        attributes: Atributos del evento
    """


def set_span_attribute(key: str, value: Union[str, int, float, bool]) -> None:
    """
    Establece un atributo en el span simulado para pruebas.

    Args:
        key: Clave del atributo
        value: Valor del atributo
    """


def get_current_trace_id() -> Optional[str]:
    """
    Obtiene el ID de trace simulado para pruebas.

    Returns:
        ID de trace simulado
    """
    return "mock-trace-id"


def get_current_span_id() -> Optional[str]:
    """
    Obtiene el ID de span simulado para pruebas.

    Returns:
        ID de span simulado
    """
    return "mock-span-id"


# Mock para telemetry_manager
class TelemetryManager:
    """
    Mock del gestor de telemetría para pruebas.
    """

    def start_span(self, name: str, attributes: Optional[Dict[str, str]] = None) -> str:
        """
        Inicia un span simulado para pruebas.

        Args:
            name: Nombre del span
            attributes: Atributos del span

        Returns:
            ID del span simulado
        """
        return "mock-span-id"

    def end_span(self, span_id: str) -> None:
        """
        Finaliza un span simulado para pruebas.

        Args:
            span_id: ID del span
        """

    def set_span_attribute(self, span_id: str, key: str, value: Any) -> None:
        """
        Establece un atributo en un span simulado para pruebas.

        Args:
            span_id: ID del span
            key: Clave del atributo
            value: Valor del atributo
        """


# Crear instancia global
telemetry_manager = TelemetryManager()


# Mock para health_tracker
class HealthTracker:
    """
    Mock del gestor de salud para pruebas.
    """

    def update_status(
        self,
        component: str,
        status: bool,
        details: str,
        alert_on_degraded: bool = False,
    ) -> None:
        """
        Actualiza el estado de un componente simulado para pruebas.

        Args:
            component: Nombre del componente
            status: Estado del componente
            details: Detalles del estado
            alert_on_degraded: Si se debe alertar en caso de degradación
        """


# Crear instancia global
health_tracker = HealthTracker()

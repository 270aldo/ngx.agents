#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Módulo de telemetría simplificado para pruebas.

Este módulo proporciona una implementación mock de telemetría para pruebas
que no depende de bibliotecas externas como OpenTelemetry.
"""

import time
import logging
import asyncio
import contextlib
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)


class MockSpan:
    """Implementación mock de un span de telemetría."""

    def __init__(self, name: str, parent=None):
        self.name = name
        self.parent = parent
        self.start_time = time.time()
        self.end_time = None
        self.attributes = {}
        self.events = []
        self.status = "OK"
        self.status_description = ""

    @property
    def duration_ms(self) -> float:
        """Duración del span en milisegundos."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000

    def set_attribute(self, key: str, value: Any) -> None:
        """Establece un atributo en el span."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Dict[str, Any] = None) -> None:
        """Añade un evento al span."""
        self.events.append(
            {"name": name, "timestamp": time.time(), "attributes": attributes or {}}
        )

    def set_status(self, status: str, description: str = "") -> None:
        """Establece el estado del span."""
        self.status = status
        self.status_description = description

    def end(self) -> None:
        """Finaliza el span."""
        self.end_time = time.time()


class MockTelemetry:
    """Implementación mock de telemetría para pruebas."""

    def __init__(self):
        self.spans = []
        self.current_span = None
        self.events = []
        self.metrics = {}

    @contextlib.contextmanager
    def start_span(self, name: str) -> MockSpan:
        """Inicia un nuevo span."""
        parent = self.current_span
        span = MockSpan(name, parent)
        self.spans.append(span)
        previous_span = self.current_span
        self.current_span = span
        try:
            yield span
        finally:
            self.current_span = previous_span
            span.end()

    def get_current_span(self) -> Optional[MockSpan]:
        """Obtiene el span actual."""
        return self.current_span

    def end_span(self, span: MockSpan) -> None:
        """Finaliza un span específico."""
        if span:
            span.end()

    def record_event(
        self, category: str, name: str, attributes: Dict[str, Any] = None
    ) -> None:
        """Registra un evento de telemetría."""
        event = {
            "category": category,
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        }
        self.events.append(event)
        logger.debug(f"Evento de telemetría: {category}.{name} - {attributes}")

    def record_error(
        self, category: str, name: str, attributes: Dict[str, Any] = None
    ) -> None:
        """Registra un error en telemetría."""
        error_event = {
            "category": category,
            "name": name,
            "type": "error",
            "timestamp": time.time(),
            "attributes": attributes or {},
        }
        self.events.append(error_event)
        logger.error(f"Error de telemetría: {category}.{name} - {attributes}")

    def record_metric(
        self, name: str, value: float, attributes: Dict[str, Any] = None
    ) -> None:
        """Registra una métrica."""
        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(
            {"value": value, "timestamp": time.time(), "attributes": attributes or {}}
        )

    def get_events(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene eventos filtrados por categoría opcional."""
        if category:
            return [e for e in self.events if e["category"] == category]
        return self.events

    def get_metrics(
        self, name: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Obtiene métricas filtradas por nombre opcional."""
        if name:
            return {name: self.metrics.get(name, [])}
        return self.metrics

    def clear(self) -> None:
        """Limpia todos los datos de telemetría."""
        self.spans = []
        self.current_span = None
        self.events = []
        self.metrics = {}


# Crear instancia global
telemetry = MockTelemetry()


def measure_execution_time(operation_name: str) -> Callable:
    """
    Decorador para medir el tiempo de ejecución de una función.

    Args:
        operation_name: Nombre de la operación para registrar

    Returns:
        Función decorada
    """

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with telemetry.start_span(operation_name) as span:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    span.set_status("OK")
                    return result
                except Exception as e:
                    span.set_status("ERROR", str(e))
                    raise
                finally:
                    duration = (time.time() - start_time) * 1000
                    telemetry.record_metric(f"{operation_name}.duration_ms", duration)

        def sync_wrapper(*args, **kwargs):
            with telemetry.start_span(operation_name) as span:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    span.set_status("OK")
                    return result
                except Exception as e:
                    span.set_status("ERROR", str(e))
                    raise
                finally:
                    duration = (time.time() - start_time) * 1000
                    telemetry.record_metric(f"{operation_name}.duration_ms", duration)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

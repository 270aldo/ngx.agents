"""
Módulo de telemetría mock para pruebas.

Este módulo proporciona una implementación completa de telemetría mock
para usar en pruebas sin depender de OpenTelemetry. Incluye un switch
de entorno para alternar entre telemetría real y mock.
"""

import logging
import time
import uuid
import os
from typing import Dict, Any, Optional
from contextlib import contextmanager

# Configurar logger
logger = logging.getLogger(__name__)

# Constantes para configuración
USE_MOCK = os.environ.get("USE_TELEMETRY_MOCK", "true").lower() == "true"
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

# Estadísticas globales para monitoreo
STATS = {
    "spans_created": 0,
    "spans_completed": 0,
    "events_recorded": 0,
    "errors_recorded": 0,
    "metrics_recorded": 0,
}


class TelemetryManager:
    """
    Gestor de telemetría completo para pruebas.

    Proporciona una implementación mock de las funciones de telemetría
    para usar en pruebas sin depender de OpenTelemetry, con funcionalidades
    similares a las de OpenTelemetry para facilitar la migración.
    """

    def __init__(self):
        """Inicializa el gestor de telemetría."""
        self.spans = {}
        self.metrics = {}
        self.counters = {}
        self.histograms = {}
        self.current_span_id = None

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> str:
        """
        Inicia un nuevo span.

        Args:
            name: Nombre del span
            attributes: Atributos del span

        Returns:
            str: ID del span
        """
        span_id = str(uuid.uuid4())
        self.spans[span_id] = {
            "name": name,
            "attributes": attributes or {},
            "events": [],
            "start_time": time.time(),
            "end_time": None,
            "status": "OK",
            "parent_id": self.current_span_id,
        }
        self.current_span_id = span_id
        STATS["spans_created"] += 1
        logger.debug(f"Started span {name} with ID {span_id}")
        return span_id

    def end_span(self, span_id: str) -> None:
        """
        Finaliza un span.

        Args:
            span_id: ID del span a finalizar
        """
        if span_id in self.spans:
            self.spans[span_id]["end_time"] = time.time()
            duration = (
                self.spans[span_id]["end_time"] - self.spans[span_id]["start_time"]
            )
            self.spans[span_id]["duration"] = duration
            STATS["spans_completed"] += 1
            logger.debug(
                f"Ended span {self.spans[span_id]['name']} with ID {span_id} (duration: {duration:.3f}s)"
            )

            # Restaurar el span padre como span actual
            self.current_span_id = self.spans[span_id].get("parent_id")
        else:
            logger.warning(f"Attempted to end non-existent span with ID {span_id}")

    def set_span_attribute(self, span_id: str, key: str, value: Any) -> None:
        """
        Establece un atributo en un span.

        Args:
            span_id: ID del span
            key: Clave del atributo
            value: Valor del atributo
        """
        if span_id in self.spans:
            self.spans[span_id]["attributes"][key] = value
            logger.debug(
                f"Set attribute {key}={value} on span {self.spans[span_id]['name']}"
            )
        else:
            logger.warning(
                f"Attempted to set attribute on non-existent span with ID {span_id}"
            )

    def add_span_event(
        self, span_id: str, name: str, attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Añade un evento a un span.

        Args:
            span_id: ID del span
            name: Nombre del evento
            attributes: Atributos del evento
        """
        if span_id in self.spans:
            event = {
                "name": name,
                "attributes": attributes or {},
                "timestamp": time.time(),
            }
            self.spans[span_id]["events"].append(event)
            STATS["events_recorded"] += 1
            logger.debug(f"Added event {name} to span {self.spans[span_id]['name']}")
        else:
            logger.warning(
                f"Attempted to add event to non-existent span with ID {span_id}"
            )

    def record_exception(
        self,
        span_id: str,
        exception: Exception,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra una excepción en un span.

        Args:
            span_id: ID del span
            exception: Excepción a registrar
            attributes: Atributos adicionales
        """
        if span_id in self.spans:
            event = {
                "name": "exception",
                "attributes": {
                    "exception.type": type(exception).__name__,
                    "exception.message": str(exception),
                    **(attributes or {}),
                },
                "timestamp": time.time(),
            }
            self.spans[span_id]["events"].append(event)
            self.spans[span_id]["status"] = "ERROR"
            STATS["errors_recorded"] += 1
            logger.debug(
                f"Recorded exception {type(exception).__name__} in span {self.spans[span_id]['name']}"
            )
        else:
            logger.warning(
                f"Attempted to record exception in non-existent span with ID {span_id}"
            )

    def create_counter(self, name: str, description: str = "", unit: str = "") -> str:
        """
        Crea un contador.

        Args:
            name: Nombre del contador
            description: Descripción del contador
            unit: Unidad de medida

        Returns:
            str: ID del contador
        """
        counter_id = str(uuid.uuid4())
        self.counters[counter_id] = {
            "name": name,
            "description": description,
            "unit": unit,
            "value": 0,
        }
        logger.debug(f"Created counter {name} with ID {counter_id}")
        return counter_id

    def increment_counter(
        self,
        counter_id: str,
        value: int = 1,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Incrementa un contador.

        Args:
            counter_id: ID del contador
            value: Valor a incrementar
            attributes: Atributos adicionales
        """
        if counter_id in self.counters:
            self.counters[counter_id]["value"] += value
            STATS["metrics_recorded"] += 1
            logger.debug(
                f"Incremented counter {self.counters[counter_id]['name']} by {value}"
            )
        else:
            logger.warning(
                f"Attempted to increment non-existent counter with ID {counter_id}"
            )

    def create_histogram(self, name: str, description: str = "", unit: str = "") -> str:
        """
        Crea un histograma.

        Args:
            name: Nombre del histograma
            description: Descripción del histograma
            unit: Unidad de medida

        Returns:
            str: ID del histograma
        """
        histogram_id = str(uuid.uuid4())
        self.histograms[histogram_id] = {
            "name": name,
            "description": description,
            "unit": unit,
            "values": [],
        }
        logger.debug(f"Created histogram {name} with ID {histogram_id}")
        return histogram_id

    def record_histogram(
        self,
        histogram_id: str,
        value: float,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Registra un valor en un histograma.

        Args:
            histogram_id: ID del histograma
            value: Valor a registrar
            attributes: Atributos adicionales
        """
        if histogram_id in self.histograms:
            self.histograms[histogram_id]["values"].append(
                {
                    "value": value,
                    "attributes": attributes or {},
                    "timestamp": time.time(),
                }
            )
            STATS["metrics_recorded"] += 1
            logger.debug(
                f"Recorded value {value} in histogram {self.histograms[histogram_id]['name']}"
            )
        else:
            logger.warning(
                f"Attempted to record value in non-existent histogram with ID {histogram_id}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del gestor de telemetría.

        Returns:
            Dict[str, Any]: Estadísticas
        """
        return {
            "spans": len(self.spans),
            "active_spans": sum(
                1 for span in self.spans.values() if span["end_time"] is None
            ),
            "completed_spans": sum(
                1 for span in self.spans.values() if span["end_time"] is not None
            ),
            "counters": len(self.counters),
            "histograms": len(self.histograms),
            "global_stats": STATS,
        }


# Crear instancia global
telemetry_manager = TelemetryManager()


# Funciones de utilidad para simular la API de OpenTelemetry
@contextmanager
def start_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Contexto para iniciar y finalizar un span automáticamente.

    Args:
        name: Nombre del span
        attributes: Atributos del span

    Yields:
        dict: Información del span
    """
    span_id = telemetry_manager.start_span(name, attributes)
    try:
        yield {"id": span_id, "name": name}
    finally:
        telemetry_manager.end_span(span_id)


def record_event(
    component: str, event_name: str, attributes: Optional[Dict[str, Any]] = None
) -> None:
    """
    Registra un evento.

    Args:
        component: Nombre del componente
        event_name: Nombre del evento
        attributes: Atributos del evento
    """
    if telemetry_manager.current_span_id:
        telemetry_manager.add_span_event(
            telemetry_manager.current_span_id, f"{component}.{event_name}", attributes
        )
    else:
        logger.debug(f"Recorded event {component}.{event_name} (no active span)")
        STATS["events_recorded"] += 1


def record_error(
    component: str, error_name: str, attributes: Optional[Dict[str, Any]] = None
) -> None:
    """
    Registra un error.

    Args:
        component: Nombre del componente
        error_name: Nombre del error
        attributes: Atributos del error
    """
    if telemetry_manager.current_span_id:
        event_attributes = {"error.name": error_name, **(attributes or {})}
        telemetry_manager.add_span_event(
            telemetry_manager.current_span_id, f"{component}.error", event_attributes
        )
        # Marcar el span como error
        if telemetry_manager.current_span_id in telemetry_manager.spans:
            telemetry_manager.spans[telemetry_manager.current_span_id][
                "status"
            ] = "ERROR"
    else:
        logger.debug(f"Recorded error {component}.{error_name} (no active span)")
        STATS["errors_recorded"] += 1


def get_current_span():
    """
    Obtiene el span actual.

    Returns:
        dict: Información del span actual o None si no hay span activo
    """
    if (
        telemetry_manager.current_span_id
        and telemetry_manager.current_span_id in telemetry_manager.spans
    ):
        span = telemetry_manager.spans[telemetry_manager.current_span_id]
        duration_ms = 0
        if span["end_time"] is not None:
            duration_ms = (span["end_time"] - span["start_time"]) * 1000
        else:
            duration_ms = (time.time() - span["start_time"]) * 1000

        return type(
            "Span",
            (),
            {
                "id": telemetry_manager.current_span_id,
                "name": span["name"],
                "duration_ms": duration_ms,
                "status": span["status"],
                "attributes": span["attributes"],
            },
        )
    return None


# Alias para compatibilidad con el módulo real
telemetry = type(
    "Telemetry",
    (),
    {
        "start_span": start_span,
        "record_event": record_event,
        "record_error": record_error,
        "get_current_span": get_current_span,
    },
)()

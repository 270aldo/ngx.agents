"""
Adaptadores para la infraestructura de NGX Agents.

Este paquete contiene adaptadores que facilitan la integración entre
diferentes componentes del sistema, proporcionando capas de abstracción
y compatibilidad.
"""

from infrastructure.adapters.telemetry_adapter import (
    get_telemetry_adapter,
    measure_execution_time,
    TelemetryAdapter,
)

__all__ = ["get_telemetry_adapter", "measure_execution_time", "TelemetryAdapter"]

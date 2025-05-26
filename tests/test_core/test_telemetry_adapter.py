"""
Pruebas para el adaptador de telemetría.

Este módulo contiene pruebas para verificar el funcionamiento
del adaptador de telemetría.
"""

import pytest

from core.telemetry_adapter import (
    telemetry_adapter,
    get_telemetry_adapter,
    measure_execution_time,
)


@pytest.mark.asyncio
async def test_get_telemetry_adapter():
    """Prueba la función get_telemetry_adapter."""
    # Obtener adaptador
    adapter = get_telemetry_adapter()

    # Verificar que es una instancia válida
    assert adapter is not None
    assert adapter is telemetry_adapter


@pytest.mark.asyncio
async def test_start_span():
    """Prueba la función start_span del adaptador."""
    # Iniciar span
    span = telemetry_adapter.start_span("test_span", {"test": True})

    # Verificar que se creó correctamente
    assert span is not None

    # Finalizar span
    telemetry_adapter.end_span(span)


@pytest.mark.asyncio
async def test_set_span_attribute():
    """Prueba la función set_span_attribute del adaptador."""
    # Iniciar span
    span = telemetry_adapter.start_span("test_span")

    # Establecer atributo
    telemetry_adapter.set_span_attribute(span, "test_key", "test_value")

    # Finalizar span
    telemetry_adapter.end_span(span)


@pytest.mark.asyncio
async def test_add_span_event():
    """Prueba la función add_span_event del adaptador."""
    # Iniciar span
    span = telemetry_adapter.start_span("test_span")

    # Añadir evento
    telemetry_adapter.add_span_event(span, "test_event", {"test": True})

    # Finalizar span
    telemetry_adapter.end_span(span)


@pytest.mark.asyncio
async def test_record_exception():
    """Prueba la función record_exception del adaptador."""
    # Iniciar span
    span = telemetry_adapter.start_span("test_span")

    # Registrar excepción
    try:
        raise ValueError("Test exception")
    except Exception as e:
        telemetry_adapter.record_exception(span, e)

    # Finalizar span
    telemetry_adapter.end_span(span)


@pytest.mark.asyncio
async def test_record_metric():
    """Prueba la función record_metric del adaptador."""
    # Registrar métrica
    telemetry_adapter.record_metric("test_metric", 123.45, {"test": True})


@pytest.mark.asyncio
async def test_record_counter():
    """Prueba la función record_counter del adaptador."""
    # Registrar contador
    telemetry_adapter.record_counter("test_counter", 5, {"test": True})


@pytest.mark.asyncio
async def test_record_histogram():
    """Prueba la función record_histogram del adaptador."""
    # Registrar histograma
    telemetry_adapter.record_histogram("test_histogram", 123.45, {"test": True})


@pytest.mark.asyncio
async def test_measure_execution_time_decorator():
    """Prueba el decorador measure_execution_time."""

    # Definir función decorada
    @measure_execution_time("test_execution_time", {"test": True})
    async def test_function():
        return "test"

    # Ejecutar función
    result = await test_function()

    # Verificar resultado
    assert result == "test"

"""
Tests para el adaptador de telemetría.

Este módulo contiene pruebas para verificar el correcto funcionamiento
del adaptador de telemetría, incluyendo su modo mock cuando la telemetría
real no está disponible.
"""

import asyncio
import logging
import pytest
from unittest.mock import patch, MagicMock

from infrastructure.adapters import (
    get_telemetry_adapter,
    measure_execution_time,
    TelemetryAdapter,
)


@pytest.fixture
def telemetry_adapter():
    """Fixture que proporciona una instancia del adaptador de telemetría."""
    return get_telemetry_adapter()


@pytest.fixture
def mock_telemetry_client():
    """Fixture que proporciona un mock del cliente de telemetría."""
    mock_client = MagicMock()
    return mock_client


class TestTelemetryAdapter:
    """Pruebas para el adaptador de telemetría."""

    def test_singleton_pattern(self):
        """Verifica que el adaptador implementa el patrón singleton."""
        adapter1 = get_telemetry_adapter()
        adapter2 = get_telemetry_adapter()

        assert adapter1 is adapter2, "El adaptador debería ser un singleton"

    def test_mock_mode_when_telemetry_not_available(self):
        """Verifica que el adaptador funciona en modo mock cuando la telemetría no está disponible."""
        with patch(
            "infrastructure.adapters.telemetry_adapter.TELEMETRY_AVAILABLE", False
        ):
            # Reiniciar la instancia global para forzar la creación de una nueva
            import infrastructure.adapters.telemetry_adapter

            infrastructure.adapters.telemetry_adapter._telemetry_adapter_instance = None

            adapter = get_telemetry_adapter()
            assert adapter.client is None, "El cliente debería ser None en modo mock"

            # Verificar que las operaciones no fallan en modo mock
            span = adapter.start_span("test_span")
            adapter.set_span_attribute(span, "test_key", "test_value")
            adapter.add_span_event(span, "test_event")
            adapter.record_exception(span, Exception("Test exception"))
            adapter.end_span(span)

            adapter.record_metric("test_metric", 42)
            adapter.record_counter("test_counter", 1)
            adapter.record_histogram("test_histogram", 100)

    @patch("infrastructure.adapters.telemetry_adapter.TelemetryClient")
    def test_integration_with_real_client(self, mock_telemetry_client_class):
        """Verifica la integración con el cliente de telemetría real."""
        mock_client = MagicMock()
        mock_telemetry_client_class.get_instance.return_value = mock_client

        with patch(
            "infrastructure.adapters.telemetry_adapter.TELEMETRY_AVAILABLE", True
        ):
            # Reiniciar la instancia global para forzar la creación de una nueva
            import infrastructure.adapters.telemetry_adapter

            infrastructure.adapters.telemetry_adapter._telemetry_adapter_instance = None

            adapter = get_telemetry_adapter()
            assert (
                adapter.client is mock_client
            ), "El cliente debería ser el mock en modo real"

            # Verificar que las operaciones llaman a los métodos correctos del cliente
            adapter.start_span("test_span", {"attr": "value"})
            mock_client.start_span.assert_called_once_with(
                "test_span", {"attr": "value"}
            )

            adapter.record_metric("test_metric", 42, {"dim": "value"})
            mock_client.record_metric.assert_called_once_with(
                "test_metric", 42, {"dim": "value"}
            )

    @pytest.mark.asyncio
    async def test_measure_execution_time_decorator(self):
        """Verifica que el decorador de medición de tiempo funciona correctamente."""
        with patch(
            "infrastructure.adapters.telemetry_adapter.get_telemetry_adapter"
        ) as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_get_adapter.return_value = mock_adapter

            # Definir una función decorada para la prueba
            @measure_execution_time("test_function", {"test_attr": "test_value"})
            async def test_function():
                await asyncio.sleep(0.1)
                return "result"

            # Llamar a la función decorada
            result = await test_function()

            # Verificar que la función devuelve el resultado correcto
            assert (
                result == "result"
            ), "La función decorada debería devolver el resultado original"

            # Verificar que se registró la métrica
            mock_adapter.record_metric.assert_called_once()
            args, kwargs = mock_adapter.record_metric.call_args

            # Verificar el nombre de la métrica
            assert (
                args[0] == "test_function"
            ), "El nombre de la métrica debería ser 'test_function'"

            # Verificar que el tiempo de ejecución es razonable (mayor que 0.1s)
            assert args[1] >= 100, "El tiempo de ejecución debería ser al menos 100ms"

            # Verificar los atributos
            assert args[2] == {
                "test_attr": "test_value"
            }, "Los atributos deberían ser correctos"

    def test_span_management_in_mock_mode(self):
        """Verifica la gestión de spans en modo mock."""
        adapter = TelemetryAdapter()
        adapter.client = None  # Forzar modo mock

        # Crear un span
        span = adapter.start_span("test_span", {"attr1": "value1"})

        # Verificar que el span es un diccionario con los valores correctos
        assert isinstance(span, dict), "El span debería ser un diccionario en modo mock"
        assert span["name"] == "test_span", "El nombre del span debería ser correcto"
        assert span["attributes"] == {
            "attr1": "value1"
        }, "Los atributos deberían ser correctos"
        assert (
            span["events"] == []
        ), "La lista de eventos debería estar vacía inicialmente"

        # Añadir atributos
        adapter.set_span_attribute(span, "attr2", "value2")
        assert (
            span["attributes"]["attr2"] == "value2"
        ), "El atributo debería haberse añadido"

        # Añadir eventos
        adapter.add_span_event(span, "test_event", {"event_attr": "event_value"})
        assert len(span["events"]) == 1, "Debería haber un evento"
        assert (
            span["events"][0]["name"] == "test_event"
        ), "El nombre del evento debería ser correcto"
        assert span["events"][0]["attributes"] == {
            "event_attr": "event_value"
        }, "Los atributos del evento deberían ser correctos"

        # Registrar excepción
        test_exception = ValueError("Test exception")
        adapter.record_exception(span, test_exception)
        assert len(span["events"]) == 2, "Debería haber dos eventos"
        assert (
            span["events"][1]["name"] == "exception"
        ), "El nombre del evento debería ser 'exception'"
        assert (
            span["events"][1]["attributes"]["exception.type"] == "ValueError"
        ), "El tipo de excepción debería ser correcto"
        assert (
            span["events"][1]["attributes"]["exception.message"] == "Test exception"
        ), "El mensaje de excepción debería ser correcto"

    @pytest.mark.asyncio
    async def test_exception_handling_in_decorated_function(self):
        """Verifica que el decorador maneja correctamente las excepciones."""
        with patch(
            "infrastructure.adapters.telemetry_adapter.get_telemetry_adapter"
        ) as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_get_adapter.return_value = mock_adapter

            # Definir una función decorada que lanza una excepción
            @measure_execution_time("test_function_with_exception")
            async def test_function_with_exception():
                await asyncio.sleep(0.1)
                raise ValueError("Test exception")

            # Llamar a la función decorada y verificar que la excepción se propaga
            with pytest.raises(ValueError, match="Test exception"):
                await test_function_with_exception()

            # Verificar que se registró la métrica a pesar de la excepción
            mock_adapter.record_metric.assert_called_once()
            args, kwargs = mock_adapter.record_metric.call_args

            # Verificar el nombre de la métrica
            assert (
                args[0] == "test_function_with_exception"
            ), "El nombre de la métrica debería ser correcto"

            # Verificar que el tiempo de ejecución es razonable (mayor que 0.1s)
            assert args[1] >= 100, "El tiempo de ejecución debería ser al menos 100ms"

    def test_logging_in_mock_mode(self, caplog):
        """Verifica que el adaptador registra en logs en modo mock."""
        caplog.set_level(logging.INFO)

        adapter = TelemetryAdapter()
        adapter.client = None  # Forzar modo mock

        # Registrar métrica
        adapter.record_metric("test_metric", 42, {"dim": "value"})

        # Verificar que se registró en el log
        assert (
            "METRIC: test_metric = 42 {dim=value}" in caplog.text
        ), "La métrica debería registrarse en el log"

        # Limpiar logs
        caplog.clear()

        # Registrar contador
        adapter.record_counter("test_counter", 1, {"dim": "value"})

        # Verificar que se registró en el log
        assert (
            "COUNTER: test_counter += 1 {dim=value}" in caplog.text
        ), "El contador debería registrarse en el log"

        # Limpiar logs
        caplog.clear()

        # Registrar histograma
        adapter.record_histogram("test_histogram", 100, {"dim": "value"})

        # Verificar que se registró en el log
        assert (
            "HISTOGRAM: test_histogram = 100 {dim=value}" in caplog.text
        ), "El histograma debería registrarse en el log"

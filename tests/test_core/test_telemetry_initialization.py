"""
Pruebas para la inicialización condicional de telemetría.

Este módulo contiene pruebas para verificar que la telemetría se inicializa
correctamente solo cuando está habilitada en la configuración.
"""

import pytest
from unittest.mock import patch, MagicMock
import os
from fastapi.testclient import TestClient

from core.settings import Settings
from core.telemetry import initialize_telemetry, shutdown_telemetry


@pytest.fixture
def mock_opentelemetry():
    """Mock para OpenTelemetry."""
    with patch("core.telemetry.Resource") as mock_resource, \
         patch("core.telemetry.TracerProvider") as mock_provider, \
         patch("core.telemetry.BatchSpanProcessor") as mock_processor, \
         patch("core.telemetry.OTLPSpanExporter") as mock_exporter, \
         patch("core.telemetry.set_tracer_provider") as mock_set_provider:
        
        yield {
            "resource": mock_resource,
            "provider": mock_provider,
            "processor": mock_processor,
            "exporter": mock_exporter,
            "set_provider": mock_set_provider
        }


@pytest.fixture
def settings_with_telemetry():
    """Configuración con telemetría habilitada."""
    return Settings(
        telemetry_enabled=True,
        gcp_project_id="test-project-id",
        environment="test"
    )


@pytest.fixture
def settings_without_telemetry():
    """Configuración con telemetría deshabilitada."""
    return Settings(
        telemetry_enabled=False,
        gcp_project_id="test-project-id",
        environment="test"
    )


def test_initialize_telemetry_when_enabled(mock_opentelemetry, settings_with_telemetry):
    """Prueba que la telemetría se inicializa cuando está habilitada."""
    with patch("core.telemetry.settings", settings_with_telemetry):
        initialize_telemetry()
        
        # Verificar que se crearon los componentes de telemetría
        mock_opentelemetry["resource"].create.assert_called_once()
        mock_opentelemetry["provider"].assert_called_once()
        mock_opentelemetry["exporter"].assert_called_once()
        mock_opentelemetry["processor"].assert_called_once()
        mock_opentelemetry["set_provider"].assert_called_once()


def test_initialize_telemetry_when_disabled(mock_opentelemetry, settings_without_telemetry):
    """Prueba que la telemetría no se inicializa cuando está deshabilitada."""
    with patch("core.telemetry.settings", settings_without_telemetry):
        initialize_telemetry()
        
        # Verificar que no se crearon los componentes de telemetría
        mock_opentelemetry["resource"].create.assert_not_called()
        mock_opentelemetry["provider"].assert_not_called()
        mock_opentelemetry["exporter"].assert_not_called()
        mock_opentelemetry["processor"].assert_not_called()
        mock_opentelemetry["set_provider"].assert_not_called()


def test_shutdown_telemetry_when_enabled(mock_opentelemetry, settings_with_telemetry):
    """Prueba que la telemetría se cierra correctamente cuando está habilitada."""
    # Configurar mock para el proveedor de trazas
    mock_provider_instance = MagicMock()
    mock_opentelemetry["provider"].return_value = mock_provider_instance
    
    with patch("core.telemetry.settings", settings_with_telemetry):
        # Inicializar telemetría
        initialize_telemetry()
        
        # Cerrar telemetría
        shutdown_telemetry()
        
        # Verificar que se llamó al método force_flush
        mock_provider_instance.force_flush.assert_called_once()


def test_shutdown_telemetry_when_disabled(mock_opentelemetry, settings_without_telemetry):
    """Prueba que la telemetría no se cierra cuando está deshabilitada."""
    # Configurar mock para el proveedor de trazas
    mock_provider_instance = MagicMock()
    mock_opentelemetry["provider"].return_value = mock_provider_instance
    
    with patch("core.telemetry.settings", settings_without_telemetry):
        # Inicializar telemetría (no debería hacer nada)
        initialize_telemetry()
        
        # Cerrar telemetría
        shutdown_telemetry()
        
        # Verificar que no se llamó al método force_flush
        mock_provider_instance.force_flush.assert_not_called()


@pytest.mark.parametrize("telemetry_enabled,expected_calls", [
    (True, 1),  # Telemetría habilitada, se debe llamar a instrument_fastapi
    (False, 0)  # Telemetría deshabilitada, no se debe llamar a instrument_fastapi
])
def test_app_initialization_with_telemetry(telemetry_enabled, expected_calls):
    """Prueba que la aplicación inicializa la telemetría correctamente según la configuración."""
    with patch("app.main.settings") as mock_settings, \
         patch("app.main.initialize_telemetry") as mock_initialize, \
         patch("app.main.instrument_fastapi") as mock_instrument:
        
        # Configurar mock de settings
        mock_settings.telemetry_enabled = telemetry_enabled
        
        # Importar la aplicación (esto ejecutará el código de inicialización)
        from app.main import app
        
        # Verificar que initialize_telemetry se llamó según la configuración
        assert mock_initialize.call_count == (1 if telemetry_enabled else 0)
        
        # Verificar que instrument_fastapi se llamó según la configuración
        assert mock_instrument.call_count == expected_calls


def test_exception_handler_with_telemetry_enabled():
    """Prueba que el manejador de excepciones registra errores en telemetría cuando está habilitada."""
    with patch("app.main.settings") as mock_settings, \
         patch("app.main.record_exception") as mock_record_exception, \
         patch("app.main._send_error_alert") as mock_send_alert:
        
        # Configurar mock de settings
        mock_settings.telemetry_enabled = True
        mock_settings.ENVIRONMENT = "production"
        
        # Importar la aplicación
        from app.main import app, global_exception_handler
        
        # Crear cliente de prueba
        client = TestClient(app)
        
        # Crear una solicitud de prueba
        request = MagicMock()
        request.headers = {"X-Request-ID": "test-request-id"}
        request.url.path = "/test-path"
        request.method = "GET"
        request.client.host = "127.0.0.1"
        
        # Crear una excepción de prueba
        exception = ValueError("Test error")
        
        # Llamar al manejador de excepciones
        global_exception_handler(request, exception)
        
        # Verificar que se registró la excepción en telemetría
        mock_record_exception.assert_called_once_with(exception, {
            "request_id": "test-request-id",
            "path": "/test-path",
            "method": "GET",
            "error_type": "ValueError"
        })


def test_exception_handler_with_telemetry_disabled():
    """Prueba que el manejador de excepciones no registra errores en telemetría cuando está deshabilitada."""
    with patch("app.main.settings") as mock_settings, \
         patch("app.main.record_exception") as mock_record_exception, \
         patch("app.main._send_error_alert") as mock_send_alert:
        
        # Configurar mock de settings
        mock_settings.telemetry_enabled = False
        mock_settings.ENVIRONMENT = "development"
        
        # Importar la aplicación
        from app.main import app, global_exception_handler
        
        # Crear cliente de prueba
        client = TestClient(app)
        
        # Crear una solicitud de prueba
        request = MagicMock()
        request.headers = {"X-Request-ID": "test-request-id"}
        request.url.path = "/test-path"
        request.method = "GET"
        request.client.host = "127.0.0.1"
        
        # Crear una excepción de prueba
        exception = ValueError("Test error")
        
        # Llamar al manejador de excepciones
        global_exception_handler(request, exception)
        
        # Verificar que no se registró la excepción en telemetría
        mock_record_exception.assert_not_called()

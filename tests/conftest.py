"""
Configuración para pytest.

Este módulo proporciona fixtures y configuraciones para las pruebas
de la API y los componentes de NGX Agents.
"""
import os
import sys
import json
import asyncio
import importlib.util
from datetime import datetime, timedelta
from typing import Dict, Any, Generator, AsyncGenerator
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from jose import jwt

# Añadir el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Cargar variables de entorno desde .env.test si existe
env_test_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.test'))
if os.path.exists(env_test_path):
    from dotenv import load_dotenv
    load_dotenv(env_test_path)

# Importar configuración de prueba
from core.test_settings import MockTestSettings

# Crear instancia de configuración de prueba con valores explícitos
test_settings_instance = MockTestSettings(
    supabase_url="http://localhost:54321",
    supabase_anon_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
    jwt_secret="test_secret_key",
    testing=True
)

# Importar módulos necesarios
from core.auth import create_access_token
from core.state_manager import StateManager

# Registrar los mocks
pytest_plugins = [
    "pytest_asyncio",
]

# Determinar si estamos ejecutando pruebas de agentes, unitarias o de integración
RUNNING_AGENT_TESTS = any('test_agent' in arg for arg in sys.argv) or any('agents/' in arg for arg in sys.argv)
RUNNING_UNIT_TESTS = any('test_unit' in arg for arg in sys.argv) or any('unit/' in arg for arg in sys.argv) or any('-m unit' in arg for arg in sys.argv)
RUNNING_INTEGRATION_TESTS = any('test_integration' in arg for arg in sys.argv) or any('integration/' in arg for arg in sys.argv) or any('-m integration' in arg for arg in sys.argv)

# Importar app solo si estamos ejecutando pruebas de integración
if RUNNING_INTEGRATION_TESTS and not RUNNING_UNIT_TESTS and not RUNNING_AGENT_TESTS:
    try:
        from app.main import app
    except ImportError as e:
        print(f"Advertencia: No se pudo importar app.main: {e}")
        # Proporcionar un mock básico para app
        class app:
            def __init__(self):
                pass
else:
    # Mock de FastAPI para pruebas de agentes y unitarias
    class app:
        def __init__(self):
            pass
        
        @staticmethod
        def get_test_client():
            """Retorna un cliente de prueba simulado."""
            return None



# Función para aplicar mocks a módulos
@pytest.fixture(autouse=True)
def mock_external_dependencies(monkeypatch):
    """Mockea dependencias externas para todas las pruebas."""
    # Solo aplicar mocks en pruebas unitarias y de agentes
    if not RUNNING_INTEGRATION_TESTS:
        # Mock adk.toolkit
        sys.modules["adk"] = importlib.import_module("tests.mocks.adk")
        sys.modules["adk.toolkit"] = importlib.import_module("tests.mocks.adk.toolkit")
        
        # Ya no es necesario parchear la clase Toolkit porque nuestro mock ya se llama Toolkit
        # y está siendo importado correctamente a través de sys.modules
        
        # Mock google.generativeai
        sys.modules["google"] = importlib.import_module("tests.mocks.google")
        sys.modules["google.generativeai"] = importlib.import_module("tests.mocks.google.generativeai")
        
        # Mock supabase
        sys.modules["supabase"] = importlib.import_module("tests.mocks.supabase")
        
        # Parchear el módulo sys.modules para que core.settings devuelva nuestra configuración de prueba
        class MockSettings:
            settings = test_settings_instance
        
        sys.modules["core.settings"] = MockSettings
    
    yield

# Marcar automáticamente las pruebas según su ubicación
def pytest_collection_modifyitems(items):
    """Marca automáticamente las pruebas según su ubicación en el árbol de directorios."""
    for item in items:
        # Marcar pruebas de agentes
        if "tests/agents/" in item.nodeid:
            item.add_marker(pytest.mark.agents)
        
        # Marcar pruebas de API y de integración
        if "tests/integration/" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Marcar pruebas de core como unitarias
        if "tests/unit/" in item.nodeid:
            item.add_marker(pytest.mark.unit)

# Configurar el alcance del event loop para pytest-asyncio
def pytest_configure(config):
    """Configura pytest-asyncio para usar function scope por defecto."""
    config.option.asyncio_default_fixture_loop_scope = "function"


# Configuración para las pruebas
@pytest.fixture(scope="session")
def test_settings() -> Dict[str, Any]:
    """Proporciona configuraciones para las pruebas."""
    return {
        "jwt_secret": "test_secret_key_for_testing_purposes_only",
        "jwt_algorithm": "HS256",
        "jwt_expiration_minutes": 60,
        "test_user_id": "00000000-0000-0000-0000-000000000000",
    }


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Proporciona un cliente de prueba para la API."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Proporciona un cliente asíncrono para la API."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_token(test_settings: Dict[str, Any]) -> str:
    """Genera un token JWT válido para las pruebas."""
    return create_access_token(
        user_id=test_settings["test_user_id"],
        expires_delta=timedelta(minutes=test_settings["jwt_expiration_minutes"])
    )


@pytest.fixture
def auth_headers(test_token: str) -> Dict[str, str]:
    """Proporciona headers de autenticación para las pruebas."""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def mock_supabase_client(monkeypatch) -> Any:
    """Proporciona un cliente de Supabase mockeado para las pruebas."""
    from tests.mocks.supabase import Client
    
    # Reemplazar la clase SupabaseClient con el mock
    from clients.supabase_client import SupabaseClient
    monkeypatch.setattr("core.state_manager.SupabaseClient", Client)
    
    return Client()


@pytest.fixture
def state_manager(mock_supabase_client) -> StateManager:
    """Proporciona un StateManager para las pruebas."""
    return StateManager(supabase_client=mock_supabase_client)

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
from datetime import datetime
from typing import Dict, Any, Generator, AsyncGenerator
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Añadir el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path: # Evitar duplicados
    sys.path.insert(0, project_root)

# Cargar variables de entorno desde .env.test si existe
env_test_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.test'))

if os.path.exists(env_test_path):
    from dotenv import load_dotenv
    print(f"DEBUG [conftest.py]: Loading .env.test from {env_test_path}")
    # override=True asegura que las variables de .env.test tienen precedencia
    load_dotenv(env_test_path, override=True)

    # Forzar la recarga de core.settings si ya fue importado.
    # Esto es crucial si otro módulo importó core.settings antes de que .env.test se cargara.
    if "core.settings" in sys.modules:
        print("DEBUG [conftest.py]: Reloading core.settings module to pick up .env.test variables.")
        import importlib
        # Es importante recargar el módulo que define 'settings'
        core_settings_module = sys.modules["core.settings"]
        importlib.reload(core_settings_module)
        # Después de recargar, cualquier importación de 'from core.settings import settings'
        # debería obtener la instancia 'settings' recién creada con los valores de .env.test.
else:
    print(f"DEBUG [conftest.py]: .env.test not found at {env_test_path}. Test-specific settings might be missing.")

# Importar la app real de FastAPI para usarla en los clientes de prueba
try:
    from app.main import app as actual_fastapi_app
except ImportError as e:
    # Esta es una condición crítica para las pruebas de API.
    # Si no podemos importar la app, las pruebas de API no pueden ejecutarse correctamente.
    print(f"ERROR CRÍTICO EN TEST SETUP: No se pudo importar app.main.app: {e}")
    raise ImportError(f"No se pudo importar app.main.app, necesario para pruebas de API: {e}")

# Importar configuración de prueba
from core.test_settings import MockTestSettings

# Crear instancia de configuración de prueba con valores explícitos
test_settings_instance = MockTestSettings(
    supabase_url="http://localhost:54321",
    supabase_anon_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
    testing=True
)

# Importar módulos necesarios
from core.state_manager import StateManager
from gotrue.errors import AuthApiError as AuthException
from gotrue.types import User, Session

# Registrar los mocks
pytest_plugins = [
    "pytest_asyncio",
]

# Determinar si estamos ejecutando pruebas de agentes, unitarias o de integración
RUNNING_AGENT_TESTS = any('test_agent' in arg for arg in sys.argv) or any('agents/' in arg for arg in sys.argv)
RUNNING_UNIT_TESTS = any('test_unit' in arg for arg in sys.argv) or any('unit/' in arg for arg in sys.argv) or any('-m unit' in arg for arg in sys.argv)
RUNNING_INTEGRATION_TESTS = any('test_integration' in arg for arg in sys.argv) or any('integration/' in arg for arg in sys.argv) or any('-m integration' in arg for arg in sys.argv)

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
        # sys.modules["supabase"] = importlib.import_module("tests.mocks.supabase")
        
        # Parchear el módulo sys.modules para que core.settings devuelva nuestra configuración de prueba
        # class MockSettings:
        #     settings = test_settings_instance
        # 
        # sys.modules["core.settings"] = MockSettings
    
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
        "test_user_id": "00000000-0000-0000-0000-000000000000",
        "test_user_email": "testuser@example.com",
        "valid_test_token": "valid_supabase_test_token_user_00000000-0000-0000-0000-000000000000"
    }


@pytest.fixture
def test_client(mock_supabase_client) -> Generator[TestClient, None, None]: 
    """Proporciona un cliente de prueba para la API."""
    from clients.supabase_client import SupabaseClient as RealSupabaseClient
    actual_fastapi_app.dependency_overrides[RealSupabaseClient] = lambda: mock_supabase_client
    with TestClient(actual_fastapi_app) as client:
        yield client
    actual_fastapi_app.dependency_overrides = {} # Limpiar overrides


@pytest.fixture
async def async_client(mock_supabase_client) -> AsyncGenerator[AsyncClient, None]: 
    """Proporciona un cliente asíncrono para la API."""
    from clients.supabase_client import SupabaseClient as RealSupabaseClient
    actual_fastapi_app.dependency_overrides[RealSupabaseClient] = lambda: mock_supabase_client
    async with AsyncClient(app=actual_fastapi_app, base_url="http://test") as client:
        yield client
    actual_fastapi_app.dependency_overrides = {} # Limpiar overrides


@pytest.fixture
def test_token(test_settings: Dict[str, Any]) -> str:
    """Genera un token JWT válido para las pruebas."""
    return test_settings["valid_test_token"]


@pytest.fixture
def auth_headers(test_token: str) -> Dict[str, str]:
    """Proporciona headers de autenticación para las pruebas."""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def mock_supabase_client(test_settings: Dict[str, Any]):
    """Proporciona un cliente de Supabase mockeado para las pruebas."""
    mock_client = MagicMock()
    mock_auth = MagicMock()

    # --- Mock para auth.get_user --- 
    async def mock_get_user(token: str):
        if token == test_settings["valid_test_token"]:
            mock_user = User(id=test_settings["test_user_id"], email=test_settings["test_user_email"], app_metadata={}, user_metadata={}, aud="authenticated", created_at=datetime.now())
            return mock_user
        raise AuthException("Invalid token for mock")
    mock_auth.get_user = AsyncMock(side_effect=mock_get_user)

    # --- Mock para auth.sign_in_with_password --- 
    async def mock_sign_in(credentials: dict): 
        email_val = credentials.get("email")
        password_val = credentials.get("password")
        if email_val == test_settings["test_user_email"] and password_val == "correct_password":
            mock_user_session_data = User(id=test_settings["test_user_id"], email=test_settings["test_user_email"], app_metadata={}, user_metadata={}, aud="authenticated", created_at=datetime.now())
            mock_session_obj = Session(access_token=test_settings["valid_test_token"], token_type="bearer", user=mock_user_session_data, refresh_token="dummy_refresh_token")
            return mock_session_obj
        raise AuthException("Invalid credentials for mock sign_in")
    mock_auth.sign_in_with_password = AsyncMock(side_effect=mock_sign_in)

    # --- Mock para auth.sign_up --- 
    async def mock_sign_up(credentials: dict):
        email = credentials.get("email")
        if email == "newuser@example.com":
            mock_user_signup = User(id="11111111-1111-1111-1111-111111111111", email=email, app_metadata={}, user_metadata={}, aud="authenticated", created_at=datetime.now())
            return mock_user_signup
        elif email == test_settings["test_user_email"]:
             raise AuthException("User already registered")
        raise AuthException("Mock sign_up error")
    mock_auth.sign_up = AsyncMock(side_effect=mock_sign_up)

    mock_client.auth = mock_auth
    
    return mock_client

@pytest.fixture
def state_manager(mock_supabase_client) -> StateManager:
    """Proporciona un StateManager para las pruebas."""
    sm = StateManager() 
    sm.client = mock_supabase_client 
    return sm

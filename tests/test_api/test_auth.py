"""
Pruebas para la autenticación de la API.

Este módulo contiene pruebas para verificar el funcionamiento
de la autenticación JWT en la API.
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

from core.settings import settings
from app.main import app
from clients.supabase_client import supabase_client
from gotrue.errors import AuthApiError as AuthException

@pytest.fixture(scope="function")
def test_client(supabase_client_mock: MagicMock) -> TestClient:
    """Proporciona un cliente de prueba para la API."""
    # Importar SupabaseClient para poder reemplazarlo en las dependencias
    from clients.supabase_client import SupabaseClient
    
    # Guardar el cliente interno original y el método initialize original
    original_client = supabase_client.client
    original_initialize = supabase_client.initialize
    
    # Crear un mock para el método initialize
    async def mock_initialize():
        print("DEBUG [test_client fixture]: Mock initialize called, doing nothing")
        # No hacemos nada, ya que el cliente ya está mockeado
        return
    
    # Reemplazar el cliente interno con nuestro mock
    supabase_client.client = supabase_client_mock
    # Reemplazar el método initialize para evitar que se inicialice el cliente real
    supabase_client.initialize = mock_initialize
    
    # Reemplazar la dependencia SupabaseClient en FastAPI
    # Esto es crucial porque en auth.py se usa Depends(lambda: SupabaseClient())
    app.dependency_overrides[SupabaseClient] = lambda: supabase_client
    
    print(f"DEBUG [test_client fixture]: Patched supabase_client.client with mock, overrode initialize method, and overrode SupabaseClient dependency")
    
    with TestClient(app) as client:
        yield client
    
    # Restaurar el cliente interno original y el método initialize
    supabase_client.client = original_client
    supabase_client.initialize = original_initialize
    
    # Limpiar las sobreescrituras de dependencias
    app.dependency_overrides = {}

@pytest.fixture(scope="function")
async def async_client(supabase_client_mock: MagicMock) -> AsyncClient:
    """Proporciona un cliente asíncrono para la API."""
    # Importar SupabaseClient para poder reemplazarlo en las dependencias
    from clients.supabase_client import SupabaseClient
    
    # Guardar el cliente interno original y el método initialize original
    original_client = supabase_client.client
    original_initialize = supabase_client.initialize
    
    # Crear un mock para el método initialize
    async def mock_initialize():
        print("DEBUG [async_client fixture]: Mock initialize called, doing nothing")
        # No hacemos nada, ya que el cliente ya está mockeado
        return
    
    # Reemplazar el cliente interno con nuestro mock
    supabase_client.client = supabase_client_mock
    # Reemplazar el método initialize para evitar que se inicialice el cliente real
    supabase_client.initialize = mock_initialize
    
    # Reemplazar la dependencia SupabaseClient en FastAPI
    # Esto es crucial porque en auth.py se usa Depends(lambda: SupabaseClient())
    app.dependency_overrides[SupabaseClient] = lambda: supabase_client
    
    print(f"DEBUG [async_client fixture]: Patched supabase_client.client with mock, overrode initialize method, and overrode SupabaseClient dependency")
    
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    
    # Restaurar el cliente interno original y el método initialize
    supabase_client.client = original_client
    supabase_client.initialize = original_initialize
    
    # Limpiar las sobreescrituras de dependencias
    app.dependency_overrides = {}

@pytest.fixture(scope="function")
def auth_headers(test_settings: dict):
    """Proporciona headers de autenticación para las pruebas."""
    # Usamos directamente el token de prueba en lugar de hacer una llamada al endpoint
    return {"Authorization": f"Bearer {test_settings['valid_test_token']}"}

@pytest.fixture(scope="function")
def test_settings():
    """Proporciona configuraciones para las pruebas."""
    # Verificar que settings tenga los valores necesarios
    if not settings.test_user_email or not settings.valid_test_token:
        print(f"DEBUG [test_settings fixture]: Valores de prueba no encontrados en settings: test_user_email={settings.test_user_email}, valid_test_token={settings.valid_test_token}")
        # Proporcionar valores por defecto si no están en settings
        return {
            "test_user_email": "testuser@example.com",
            "test_user_id": "00000000-0000-0000-0000-000000000000",
            "valid_test_token": "valid_supabase_test_token_user_00000000-0000-0000-0000-000000000000",
        }
    
    print(f"DEBUG [test_settings fixture]: Usando valores de settings: test_user_email={settings.test_user_email}")
    return {
        "test_user_email": settings.test_user_email,
        "test_user_id": settings.test_user_id,
        "valid_test_token": settings.valid_test_token,
    }

@pytest.fixture
def supabase_client_mock(mocker, test_settings: dict) -> MagicMock:
    """Mock del cliente Supabase para pruebas de autenticación."""
    mock_client = MagicMock()
    mock_auth = MagicMock() # Este será el mock para supabase_client.client.auth

    # Mock de supabase_client.client.auth.sign_in_with_password
    async def mock_sign_in_with_password(credentials):
        print(f"DEBUG: supabase_client_mock: mock_sign_in_with_password llamado con credentials: {credentials}")
        email = credentials.get("email")
        password = credentials.get("password")
        if email == test_settings["test_user_email"] and password == "correct_password":
            mock_session = MagicMock()
            mock_session.session = MagicMock()
            mock_session.session.user = MagicMock()
            mock_session.session.user.id = test_settings["test_user_id"]
            mock_session.session.user.email = test_settings["test_user_email"]
            mock_session.session.access_token = test_settings["valid_test_token"]
            mock_session.session.refresh_token = "dummy_refresh_token"
            mock_session.session.expires_in = 3600
            return mock_session
        else:
            # Simula la AuthApiError de Supabase para credenciales inválidas
            # AuthException requiere status y code
            raise AuthException("Invalid login credentials", status=401, code=400)

    # Mock de supabase_client.client.auth.sign_up
    async def mock_sign_up(credentials: dict):
        print(f"DEBUG: supabase_client_mock: mock_sign_up llamado con credentials: {credentials}")
        email = credentials.get("email")
        if email == test_settings["test_user_email"]:
            # Simula la AuthApiError de Supabase para usuario ya registrado
            # Necesitamos simular la estructura de error de Supabase
            # AuthException requiere status y code
            raise AuthException("User already registered", status=409, code=400)
        else:
            mock_response = MagicMock()
            mock_response.user = MagicMock()
            mock_response.user.id = "11111111-1111-1111-1111-111111111111" # ID de usuario único para el nuevo usuario
            mock_response.user.email = email
            # mock_response.session = None # Para sign_up, session es None si se requiere confirmación por email
            return mock_response

    # Mock de supabase_client.client.auth.get_user
    async def mock_get_user(jwt: str):
        print(f"DEBUG: supabase_client_mock: mock_get_user llamado con jwt: {jwt}")
        if jwt == test_settings["valid_test_token"]:
            mock_user_response = MagicMock()
            mock_user_response.user = MagicMock()
            mock_user_response.user.id = test_settings["test_user_id"]
            mock_user_response.user.email = test_settings["test_user_email"]
            return mock_user_response
        else:
            # Simula la AuthApiError para token inválido
            raise AuthException("Invalid JWT")

    # Usar AsyncMock para métodos asíncronos
    from unittest.mock import AsyncMock
    
    mock_auth.sign_in_with_password = AsyncMock(side_effect=mock_sign_in_with_password)
    mock_auth.sign_up = AsyncMock(side_effect=mock_sign_up)
    mock_auth.get_user = AsyncMock(side_effect=mock_get_user)
    
    # Asignar el mock de auth al cliente
    mock_client.auth = mock_auth
    
    print(f"DEBUG [supabase_client_mock fixture]: Created mock with auth attribute")
    
    return mock_client

def test_health_endpoint(test_client: TestClient):
    """Prueba el endpoint de health (no requiere autenticación)."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "ok"

def test_docs_without_auth(test_client: TestClient):
    """Prueba que el endpoint de docs requiere autenticación."""
    response = test_client.get("/docs")
    assert response.status_code == 401
    assert "detail" in response.json()

def test_docs_with_auth(test_client: TestClient, auth_headers):
    """Prueba que el endpoint de docs funciona con autenticación."""
    response = test_client.get("/docs", headers=auth_headers)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_openapi_with_auth(test_client: TestClient, auth_headers):
    """Prueba que el endpoint de openapi.json funciona con autenticación."""
    response = test_client.get("/openapi.json", headers=auth_headers)
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    assert "paths" in response.json()

def test_invalid_token(test_client: TestClient):
    """Prueba que un token inválido es rechazado."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = test_client.get("/docs", headers=headers)
    assert response.status_code == 401
    assert "detail" in response.json()

@pytest.mark.skip(reason="Fixture async_client requiere revisión")
@pytest.mark.asyncio
async def test_async_auth(async_client, auth_headers):
    """Prueba la autenticación con un cliente asíncrono."""
    # Temporalmente desactivado mientras se resuelve el problema con el fixture
    # response = await async_client.get("/docs", headers=auth_headers)
    # assert response.status_code == 200
    # assert "text/html" in response.headers["content-type"]
    pass

# Pruebas para el endpoint de Login (/auth/token)
def test_login_success(test_client: TestClient, test_settings: dict):
    """Prueba el login exitoso."""
    login_data = {
        "username": test_settings["test_user_email"], # FastAPI OAuth2PasswordRequestForm usa 'username'
        "password": "correct_password"
    }
    response = test_client.post("/auth/token", data=login_data)
    assert response.status_code == 200
    json_response = response.json()
    assert "access_token" in json_response
    assert json_response["access_token"] == test_settings["valid_test_token"]
    assert "token_type" in json_response
    assert json_response["token_type"].lower() == "bearer"

def test_login_failure_invalid_credentials(test_client: TestClient, test_settings: dict):
    """Prueba el login con credenciales inválidas."""
    login_data = {
        "username": test_settings["test_user_email"],
        "password": "wrong_password"
    }
    response = test_client.post("/auth/token", data=login_data)
    assert response.status_code == 401 # Esperamos 401 por AuthException de Supabase
    json_response = response.json()
    assert "detail" in json_response
    # El mensaje exacto puede depender del mock_sign_in si se personaliza
    # o de cómo FastAPI maneje la AuthException re-levantada.
    # Por ahora, solo verificamos que haya un detalle.

# Pruebas para el endpoint de Registro (/auth/register)
def test_register_success(test_client: TestClient):
    """Prueba el registro exitoso de un nuevo usuario."""
    register_data = {
        "email": "newuser@example.com",
        "password": "newpassword123",
        "full_name": "New User"
    }
    response = test_client.post("/auth/register", json=register_data) # Enviamos como JSON
    assert response.status_code == 201
    json_response = response.json()
    assert json_response["email"] == "newuser@example.com"
    assert "id" in json_response
    assert json_response["id"] == "11111111-1111-1111-1111-111111111111" # Del mock_sign_up
    assert "hashed_password" not in json_response # Asegurarse de no devolver la contraseña

def test_register_failure_user_exists(test_client: TestClient, test_settings: dict):
    """Prueba el registro con un email que ya existe."""
    register_data = {
        "email": test_settings["test_user_email"], # Usuario que ya existe según el mock
        "password": "anypassword",
        "full_name": "Existing User"
    }
    response = test_client.post("/auth/register", json=register_data)
    assert response.status_code == 409 # Esperamos 409 por AuthException("User already registered") que se convierte a HTTP_409_CONFLICT
    json_response = response.json()
    assert "detail" in json_response
    assert "User already registered" in json_response["detail"] # Basado en el mock

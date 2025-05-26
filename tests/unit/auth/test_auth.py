"""
Pruebas unitarias para el middleware de autenticación.
"""

import pytest
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# Importar desde el proyecto
from app.middleware.auth import get_api_key, APIKeyMiddleware

# Constantes para pruebas
TEST_API_KEY = "test_api_key"
TEST_USER_ID = "test_user_id"


# Mock para el cliente Supabase
class MockSupabaseClient:
    def get_or_create_user_by_api_key(self, api_key):
        if api_key == TEST_API_KEY:
            return {"id": TEST_USER_ID, "api_key": api_key}
        return {}


# Patch para SupabaseClient
@pytest.fixture(autouse=True)
def mock_supabase_client():
    with patch("app.middleware.auth.SupabaseClient", return_value=MockSupabaseClient()):
        yield


# Crear una aplicación FastAPI de prueba
app = FastAPI()

# Añadir el middleware de autenticación
app.add_middleware(APIKeyMiddleware, excluded_paths=["/excluded", "/health"])

# Configurar el cliente de prueba sin pasar app directamente
client = TestClient(app=app)


# Definir rutas de prueba
@app.get("/protected")
async def protected_route(api_key: str = Depends(get_api_key)):
    return {"message": "Acceso permitido", "api_key": api_key, "user_id": TEST_USER_ID}


@app.get("/excluded")
async def excluded_route():
    return {"message": "Ruta excluida"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Configurar el patch para api_key_header
@pytest.fixture
def mock_api_key_header():
    async def mock_header(request):
        return request.headers.get("X-API-Key")

    with patch(
        "app.middleware.auth.api_key_header", new=AsyncMock(side_effect=mock_header)
    ):
        yield


def test_protected_route_with_valid_api_key():
    """Prueba acceder a una ruta protegida con una API key válida."""
    response = client.get("/protected", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert response.json()["message"] == "Acceso permitido"
    assert response.json()["api_key"] == TEST_API_KEY
    assert response.json()["user_id"] == TEST_USER_ID


def test_protected_route_with_invalid_api_key():
    """Prueba acceder a una ruta protegida con una API key inválida."""
    response = client.get("/protected", headers={"X-API-Key": "invalid_key"})
    assert response.status_code == 401
    assert "inválida" in response.json()["detail"]


def test_protected_route_without_api_key():
    """Prueba acceder a una ruta protegida sin API key."""
    response = client.get("/protected")
    assert response.status_code == 401
    assert "no proporcionada" in response.json()["detail"]


def test_excluded_route():
    """Prueba acceder a una ruta excluida sin API key."""
    response = client.get("/excluded")
    assert response.status_code == 200
    assert response.json()["message"] == "Ruta excluida"


def test_health_check():
    """Prueba acceder a la ruta de health check sin API key."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_get_api_key_with_valid_key(mock_api_key_header):
    """Prueba la función get_api_key con una API key válida."""
    # Crear una solicitud simulada
    request = MagicMock()
    request.headers = {"X-API-Key": TEST_API_KEY}

    # Llamar a la función
    result = await get_api_key(request)

    # Verificar que se devolvió la API key correcta
    assert result == TEST_API_KEY

    # Verificar que se almacenó el user_id en request.state
    assert request.state.user_id == TEST_USER_ID


@pytest.mark.asyncio
async def test_get_api_key_with_invalid_key(mock_api_key_header):
    """Prueba la función get_api_key con una API key inválida."""
    # Crear una solicitud simulada
    request = MagicMock()
    request.url.path = "/test"
    request.headers = {"X-API-Key": "invalid_key"}

    # Verificar que se lanza una excepción
    with pytest.raises(HTTPException) as excinfo:
        await get_api_key(request)

    # Verificar el mensaje de error
    assert excinfo.value.status_code == 401
    assert "inválida" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_api_key_without_key(mock_api_key_header):
    """Prueba la función get_api_key sin API key."""
    # Crear una solicitud simulada sin API key
    request = MagicMock()
    request.url.path = "/test"
    request.headers = {}

    # Verificar que se lanza una excepción
    with pytest.raises(HTTPException) as excinfo:
        await get_api_key(request)

    # Verificar el mensaje de error
    assert excinfo.value.status_code == 401
    assert "no proporcionada" in excinfo.value.detail

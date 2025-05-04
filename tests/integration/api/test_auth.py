"""
Pruebas para la autenticación de la API.

Este módulo contiene pruebas para verificar el funcionamiento
de la autenticación JWT en la API.
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from jose import jwt

from core.settings import settings


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


def test_expired_token(test_client: TestClient, test_settings):
    """Prueba que un token expirado es rechazado."""
    # Crear un token expirado
    payload = {
        "sub": test_settings["test_user_id"],
        "exp": 1  # Timestamp muy antiguo (1970-01-01 00:00:01 UTC)
    }
    expired_token = jwt.encode(
        payload,
        test_settings["jwt_secret"],
        algorithm=test_settings["jwt_algorithm"]
    )
    
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = test_client.get("/docs", headers=headers)
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "expirado" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_async_auth(async_client: AsyncClient, auth_headers):
    """Prueba la autenticación con un cliente asíncrono."""
    response = await async_client.get("/docs", headers=auth_headers)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

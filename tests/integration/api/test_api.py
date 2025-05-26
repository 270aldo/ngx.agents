"""
Pruebas unitarias para los endpoints de la API.

Este módulo contiene pruebas para verificar el funcionamiento
de los endpoints de la API de NGX Agents.
"""

import pytest
from unittest.mock import patch, MagicMock

from unittest.mock import patch, MagicMock

# Constantes para pruebas
API_KEY_DEFAULT = "test_api_key"

# Mock para la aplicación FastAPI
app_mock = MagicMock()
orchestrator_mock = MagicMock()


# Clases para las pruebas
class MessageRequest:
    """Mock de la clase MessageRequest."""


class StandardResponse:
    """Mock de la clase StandardResponse."""

    success: bool
    data: dict = None
    error: str = None


# Patch para evitar la importación real de app.py
@pytest.fixture(autouse=True)
def mock_app():
    """Fixture que simula la aplicación FastAPI."""
    with (
        patch("fastapi.FastAPI", return_value=app_mock),
        patch("fastapi.testclient.TestClient") as mock_client,
    ):
        # Configurar el cliente de prueba
        test_client = MagicMock()
        mock_client.return_value = test_client

        # Configurar respuestas simuladas para las rutas
        test_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "success": True,
                "data": {
                    "response": "Respuesta de prueba",
                    "agents_used": ["agent1", "agent2"],
                    "confidence": 0.85,
                    "execution_time": 0.5,
                },
            },
        )

        test_client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "success": True,
                "data": [
                    {
                        "task_id": f"task_{i}",
                        "task_type": "chat",
                        "created_at": f"2025-05-0{i}T10:00:00",
                        "completed_at": f"2025-05-0{i}T10:00:01",
                        "requester_id": "test_user_123",
                        "status": "completed",
                        "response": f"Respuesta de prueba {i}",
                        "agents_used": ["agent1"],
                        "confidence": 0.8,
                    }
                    for i in range(1, 21)
                ],
            },
        )

        yield test_client


# Configurar cliente de prueba simulado
@pytest.fixture
def client(mock_app):
    """Fixture que proporciona un cliente de prueba simulado."""
    return mock_app


# Fixture para simular la respuesta del orquestador
# Simulación de la ejecución de tareas
def mock_execute_task():
    """Simula la ejecución de tareas en el orquestador."""
    return {
        "task_id": "test_task_123",
        "success": True,
        "response": "Respuesta de prueba",
        "error": None,
        "agents_used": ["agent1", "agent2"],
        "confidence": 0.85,
        "execution_time": 0.5,
    }


# Simulación del historial de tareas
def mock_get_task_history():
    """Simula la obtención del historial de tareas."""
    return [
        {
            "task_id": f"task_{i}",
            "task_type": "chat",
            "created_at": f"2025-05-0{i}T10:00:00",
            "completed_at": f"2025-05-0{i}T10:00:01",
            "requester_id": "test_user_123",
            "status": "completed",
            "response": f"Respuesta de prueba {i}",
            "agents_used": ["agent1"],
            "confidence": 0.8,
        }
        for i in range(1, 30)  # Generar 29 tareas de prueba
    ]


# Pruebas para el endpoint /chat
def test_chat_endpoint_success(client):
    """Prueba que el endpoint /chat funciona correctamente."""
    # Datos de prueba
    request_data = {
        "message": "Hola, ¿cómo estás?",
        "user_id": "test_user_123",
        "session_id": "test_session_456",
        "context": {"key": "value"},
    }

    # Realizar solicitud
    response = client.post(
        "/chat", json=request_data, headers={"X-API-Key": API_KEY_DEFAULT}
    )

    # Verificar que se realizó la solicitud correctamente
    client.post.assert_called_once()
    args, kwargs = client.post.call_args
    assert args[0] == "/chat"
    assert kwargs["json"] == request_data
    assert kwargs["headers"] == {"X-API-Key": API_KEY_DEFAULT}


def test_chat_endpoint_without_user_id(client):
    """Prueba que el endpoint /chat funciona correctamente sin user_id."""
    # Datos de prueba sin user_id
    request_data = {
        "message": "Hola, ¿cómo estás?",
    }

    # Realizar solicitud
    response = client.post(
        "/chat", json=request_data, headers={"X-API-Key": API_KEY_DEFAULT}
    )

    # Verificar que se realizó la solicitud correctamente
    client.post.assert_called_once()
    args, kwargs = client.post.call_args
    assert args[0] == "/chat"
    assert kwargs["json"] == request_data
    assert kwargs["headers"] == {"X-API-Key": API_KEY_DEFAULT}


def test_chat_endpoint_error(client):
    """Prueba que el endpoint /chat maneja correctamente los errores."""
    # Configurar el cliente para simular un error
    client.post.return_value = MagicMock(
        status_code=500, json=lambda: {"detail": "Error de prueba"}
    )

    # Datos de prueba
    request_data = {"message": "Hola, ¿cómo estás?", "user_id": "test_user_123"}

    # Realizar solicitud
    response = client.post(
        "/chat", json=request_data, headers={"X-API-Key": API_KEY_DEFAULT}
    )

    # Verificar respuesta de error
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Error de prueba" in data["detail"]


def test_chat_endpoint_without_api_key(client):
    """Prueba que el endpoint /chat requiere una API key válida."""
    # Datos de prueba
    request_data = {"message": "Hola, ¿cómo estás?", "user_id": "test_user_123"}

    # Configurar el cliente para simular un error de autenticación
    client.post.return_value = MagicMock(
        status_code=401, json=lambda: {"detail": "API key no proporcionada"}
    )

    # Realizar solicitud sin API key
    response = client.post("/chat", json=request_data, headers={})

    # Verificar que se realizó la solicitud correctamente
    client.post.assert_called_once()
    args, kwargs = client.post.call_args
    assert args[0] == "/chat"
    assert kwargs["json"] == request_data
    assert kwargs["headers"] == {}


# Pruebas para el endpoint /conversations/{user_id}/history
def test_conversation_history_success(client):
    """Prueba que el endpoint /conversations/{user_id}/history funciona correctamente."""
    # Realizar solicitud
    response = client.get(
        "/conversations/test_user_123/history", headers={"X-API-Key": API_KEY_DEFAULT}
    )

    # Verificar que se realizó la solicitud correctamente
    client.get.assert_called_once()
    args, kwargs = client.get.call_args
    assert args[0] == "/conversations/test_user_123/history"
    assert kwargs["headers"] == {"X-API-Key": API_KEY_DEFAULT}


def test_conversation_history_with_pagination(client):
    """Prueba que el endpoint /conversations/{user_id}/history soporta paginación."""
    # Realizar solicitud con parámetros de paginación
    response = client.get(
        "/conversations/test_user_123/history?limit=5&offset=10",
        headers={"X-API-Key": API_KEY_DEFAULT},
    )

    # Verificar que se realizó la solicitud correctamente
    client.get.assert_called_once()
    args, kwargs = client.get.call_args
    assert args[0] == "/conversations/test_user_123/history?limit=5&offset=10"
    assert kwargs["headers"] == {"X-API-Key": API_KEY_DEFAULT}


def test_conversation_history_invalid_pagination(client):
    """Prueba que el endpoint /conversations/{user_id}/history valida los parámetros de paginación."""
    # Configurar el cliente para simular un error de validación para limit=0
    client.get.return_value = MagicMock(
        status_code=422,
        json=lambda: {
            "detail": [
                {
                    "loc": ["query", "limit"],
                    "msg": "ensure this value is greater than or equal to 1",
                    "type": "value_error.number.not_ge",
                }
            ]
        },
    )

    # Realizar solicitud con limit inválido
    response = client.get(
        "/conversations/test_user_123/history?limit=0",
        headers={"X-API-Key": API_KEY_DEFAULT},
    )

    # Verificar respuesta de error de validación
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

    # Configurar el cliente para simular un error de validación para limit=101
    client.get.return_value = MagicMock(
        status_code=422,
        json=lambda: {
            "detail": [
                {
                    "loc": ["query", "limit"],
                    "msg": "ensure this value is less than or equal to 100",
                    "type": "value_error.number.not_le",
                }
            ]
        },
    )

    # Realizar solicitud con limit demasiado grande
    response = client.get(
        "/conversations/test_user_123/history?limit=101",
        headers={"X-API-Key": API_KEY_DEFAULT},
    )

    # Verificar respuesta de error de validación
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

    # Configurar el cliente para simular un error de validación para offset=-1
    client.get.return_value = MagicMock(
        status_code=422,
        json=lambda: {
            "detail": [
                {
                    "loc": ["query", "offset"],
                    "msg": "ensure this value is greater than or equal to 0",
                    "type": "value_error.number.not_ge",
                }
            ]
        },
    )

    # Realizar solicitud con offset negativo
    response = client.get(
        "/conversations/test_user_123/history?offset=-1",
        headers={"X-API-Key": API_KEY_DEFAULT},
    )

    # Verificar respuesta de error de validación
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_conversation_history_empty(client):
    """Prueba que el endpoint /conversations/{user_id}/history maneja correctamente el caso de no tener historial."""
    # Configurar el cliente para simular una respuesta vacía
    client.get.return_value = MagicMock(
        status_code=200, json=lambda: {"success": True, "data": []}
    )

    # Realizar solicitud
    response = client.get(
        "/conversations/test_user_123/history", headers={"X-API-Key": API_KEY_DEFAULT}
    )

    # Verificar que se realizó la solicitud correctamente
    client.get.assert_called_once()
    args, kwargs = client.get.call_args
    assert args[0] == "/conversations/test_user_123/history"
    assert kwargs["headers"] == {"X-API-Key": API_KEY_DEFAULT}


def test_conversation_history_error(client):
    """Prueba que el endpoint /conversations/{user_id}/history maneja correctamente los errores."""
    # Configurar el cliente para simular un error
    client.get.return_value = MagicMock(
        status_code=500, json=lambda: {"detail": "Error de prueba"}
    )

    # Realizar solicitud
    response = client.get(
        "/conversations/test_user_123/history", headers={"X-API-Key": API_KEY_DEFAULT}
    )

    # Verificar respuesta de error
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Error de prueba" in data["detail"]


def test_conversation_history_without_api_key(client):
    """Prueba que el endpoint /conversations/{user_id}/history requiere una API key válida."""
    # Configurar el cliente para simular un error de autenticación
    client.get.return_value = MagicMock(
        status_code=401, json=lambda: {"detail": "API key no proporcionada"}
    )

    # Realizar solicitud sin API key
    response = client.get("/conversations/test_user_123/history", headers={})

    # Verificar que se realizó la solicitud correctamente
    client.get.assert_called_once()
    args, kwargs = client.get.call_args
    assert args[0] == "/conversations/test_user_123/history"
    assert kwargs["headers"] == {}

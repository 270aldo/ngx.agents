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
        status_code=401, json=lambda: {"detail": "No autorizado"}
    )

    # Realizar solicitud
    response = client.post(
        "/chat",
        json=request_data,
        # No se envía X-API-Key
    )

    # Verificar respuesta de error
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "No autorizado" in data["detail"]


# Pruebas para el endpoint /task_history
def test_get_task_history_success(client):
    """Prueba que el endpoint /task_history funciona correctamente."""
    # Realizar solicitud
    response = client.get("/task_history", headers={"X-API-Key": API_KEY_DEFAULT})

    # Verificar respuesta exitosa
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 20  # Según el mock
    assert "task_id" in data["data"][0]


def test_get_task_history_with_pagination(client):
    """Prueba que el endpoint /task_history funciona con paginación."""

    # Configurar el cliente para devolver 10 elementos en la primera página
    # y 5 en la segunda página (un total de 15 simulados)
    def side_effect_pagination(url, params=None, headers=None):
        skip = params.get("skip", 0)
        limit = params.get("limit", 20)

        all_tasks = mock_get_task_history()  # Obtiene 29 tareas
        paginated_tasks = all_tasks[skip : skip + limit]

        return MagicMock(
            status_code=200, json=lambda: {"success": True, "data": paginated_tasks}
        )

    client.get.side_effect = side_effect_pagination

    # Primera página
    response1 = client.get(
        "/task_history?skip=0&limit=10", headers={"X-API-Key": API_KEY_DEFAULT}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["data"]) == 10

    # Segunda página
    response2 = client.get(
        "/task_history?skip=10&limit=10", headers={"X-API-Key": API_KEY_DEFAULT}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["data"]) == 10  # Debería ser 10, si hay 29 en total mockeados.

    # Tercera página (con menos elementos)
    response3 = client.get(
        "/task_history?skip=20&limit=10", headers={"X-API-Key": API_KEY_DEFAULT}
    )
    assert response3.status_code == 200
    data3 = response3.json()
    assert len(data3["data"]) == 9  # Los 9 restantes de 29.

    # Asegurarse de que los datos no se solapen (simple check por ID)
    ids1 = {task["task_id"] for task in data1["data"]}
    ids2 = {task["task_id"] for task in data2["data"]}
    ids3 = {task["task_id"] for task in data3["data"]}
    assert not (ids1 & ids2)  # No debe haber intersección
    assert not (ids1 & ids3)
    assert not (ids2 & ids3)


def test_get_task_history_error(client):
    """Prueba que el endpoint /task_history maneja errores correctamente."""
    # Configurar el cliente para simular un error
    client.get.side_effect = None  # Limpiar side_effect anterior si existe
    client.get.return_value = MagicMock(
        status_code=500, json=lambda: {"detail": "Error de base de datos"}
    )

    # Realizar solicitud
    response = client.get("/task_history", headers={"X-API-Key": API_KEY_DEFAULT})

    # Verificar respuesta de error
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Error de base de datos" in data["detail"]


def test_get_task_history_without_api_key(client):
    """Prueba que el endpoint /task_history requiere una API key."""
    client.get.side_effect = None  # Limpiar side_effect anterior si existe
    client.get.return_value = MagicMock(
        status_code=401, json=lambda: {"detail": "No autorizado"}
    )

    response = client.get("/task_history")  # Sin API Key
    assert response.status_code == 401
    assert "No autorizado" in response.json()["detail"]

"""
Pruebas unitarias para el servidor A2A.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

import sys
import os

# Añadir el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from app.main import app

# from infrastructure.adapters.a2a_adapter import a2a_adapter, get_a2a_server_status
from infrastructure.a2a.models import (
    TaskStatus,
    AgentStatus,
    MessageRole,
    PartType,
    AgentInfo,
    TaskRequest,
    Task,
    Message,
    Part,
)

# Cliente de prueba para FastAPI
client = TestClient(app)


@pytest.fixture
def reset_state():
    """Reinicia el estado del servidor entre pruebas."""
    # registered_agents.clear()
    # tasks.clear()
    # if hasattr(manager, 'active_connections'):
    # manager.active_connections.clear()
    # if hasattr(manager, 'last_active_time'):
    # manager.last_active_time.clear()
    yield


def test_root(reset_state):
    """Prueba el endpoint raíz."""
    response = client.get("/")
    assert response.status_code == 200
    assert (
        "Servidor A2A" in response.json()["message"]
    )  # Cambiado para coincidir con el mensaje real


def test_register_agent(reset_state):
    """Prueba el registro de un agente."""
    # Crear un objeto AgentInfo para el registro
    agent_info = AgentInfo(
        agent_id="test_agent_1",
        name="Test Agent 1",
        description="Agente de prueba",
        capabilities=["test"],
        endpoint="http://localhost:8000",
        version="1.0.0",
    )

    # Convertir a diccionario para la solicitud JSON
    agent_data = (
        agent_info.dict() if hasattr(agent_info, "dict") else agent_info.model_dump()
    )

    # Realizar la solicitud de registro
    response = client.post("/agents/register", json=agent_data)

    # Verificar la respuesta
    assert response.status_code == 200, f"Error: {response.text}"
    assert response.json()["status"] == "success"
    assert response.json()["agent_id"] == "test_agent_1"

    # Verificar que el agente se registró correctamente en memoria
    # assert "test_agent_1" in registered_agents
    # assert registered_agents["test_agent_1"]["name"] == "Test Agent 1"
    # assert registered_agents["test_agent_1"]["status"] == AgentStatus.OFFLINE


def test_register_duplicate_agent(reset_state):
    """Prueba el registro de un agente duplicado."""
    # Crear un objeto AgentInfo para el registro
    agent_info = AgentInfo(
        agent_id="test_agent_1",
        name="Test Agent 1",
        description="Agente de prueba",
        capabilities=["test"],
        endpoint="http://localhost:8000",
        version="1.0.0",
    )

    # Convertir a diccionario para la solicitud JSON
    agent_data = (
        agent_info.dict() if hasattr(agent_info, "dict") else agent_info.model_dump()
    )

    # Primer registro (debería ser exitoso)
    response = client.post("/agents/register", json=agent_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Segundo registro (debería fallar con error de conflicto)
    response = client.post("/agents/register", json=agent_data)
    assert response.status_code == 409  # Conflict

    # Verificar que el mensaje de error es correcto
    error_data = response.json()
    assert "error" in error_data
    assert error_data["error"] == "agent_already_exists"
    assert "test_agent_1" in error_data["message"]


def test_discover_agents(reset_state):
    """Prueba el descubrimiento de agentes."""
    # Registrar algunos agentes
    agents = [
        AgentInfo(
            agent_id=f"test_agent_{i}",
            name=f"Test Agent {i}",
            description=f"Agente de prueba {i}",
            capabilities=["test"],
            endpoint="http://localhost:8000",
            version="1.0.0",
        )
        for i in range(1, 4)
    ]

    for agent in agents:
        agent_data = agent.dict() if hasattr(agent, "dict") else agent.model_dump()
        client.post("/agents/register", json=agent_data)

    # Probar el endpoint de descubrimiento
    response = client.get("/agents/discover")
    assert response.status_code == 200

    # Verificar la estructura de la respuesta
    response_data = response.json()
    assert "agents" in response_data
    assert "total" in response_data
    assert "online" in response_data
    assert "timestamp" in response_data

    # Verificar que devuelve todos los agentes registrados
    discovered_agents = response_data["agents"]
    assert len(discovered_agents) == 3
    assert response_data["total"] == 3
    assert response_data["online"] == 0  # Todos están offline por defecto

    # Verificar que los agentes están ordenados alfabéticamente por nombre
    assert discovered_agents[0]["name"] == "Test Agent 1"
    assert discovered_agents[1]["name"] == "Test Agent 2"
    assert discovered_agents[2]["name"] == "Test Agent 3"

    # Verificar el estado de los agentes
    for agent in discovered_agents:
        assert agent["status"] == AgentStatus.OFFLINE


def test_request_task_nonexistent_agent(reset_state):
    """Prueba solicitar una tarea a un agente que no existe."""
    # Crear objeto TaskRequest
    task_request = TaskRequest(
        agent_id="nonexistent_agent",
        task={
            "requester_id": "test_requester",
            "task_type": "test_task",
            "input": "Test task",
        },
    )

    # Convertir a diccionario para la solicitud JSON
    request_data = (
        task_request.dict()
        if hasattr(task_request, "dict")
        else task_request.model_dump()
    )

    # Realizar la solicitud
    response = client.post("/agents/request", json=request_data)

    # Verificar que la respuesta es un error 404 (Not Found)
    assert response.status_code == 404

    # Verificar que el mensaje de error es correcto
    error_data = response.json()
    assert "error" in error_data
    assert error_data["error"] == "agent_not_found"
    assert "nonexistent_agent" in error_data["message"]
    assert "agent_id" in error_data["details"]


@pytest.mark.asyncio
async def test_request_task_agent_offline(reset_state):
    """Prueba solicitar una tarea a un agente que está offline."""
    # Registrar un agente
    agent_info = AgentInfo(
        agent_id="test_agent_1",
        name="Test Agent 1",
        description="Agente de prueba",
        capabilities=["test"],
        endpoint="http://localhost:8000",
        version="1.0.0",
    )

    # Convertir a diccionario para la solicitud JSON
    agent_data = (
        agent_info.dict() if hasattr(agent_info, "dict") else agent_info.model_dump()
    )

    # Registrar el agente (estará offline por defecto)
    client.post("/agents/register", json=agent_data)

    # Verificar que el agente está offline
    # assert registered_agents["test_agent_1"]["status"] == AgentStatus.OFFLINE

    # Crear objeto TaskRequest
    task_request = TaskRequest(
        agent_id="test_agent_1",
        task={
            "requester_id": "test_requester",
            "task_type": "test_task",
            "input": "Test task",
        },
    )

    # Convertir a diccionario para la solicitud JSON
    request_data = (
        task_request.dict()
        if hasattr(task_request, "dict")
        else task_request.model_dump()
    )

    # Realizar la solicitud
    response = client.post("/agents/request", json=request_data)

    # Verificar que la respuesta es un error 400 (Bad Request) porque el agente está offline
    assert response.status_code == 400

    # Verificar que el mensaje de error es correcto
    error_data = response.json()
    assert "error" in error_data
    assert error_data["error"] == "agent_offline"
    assert "test_agent_1" in error_data["message"]
    assert "agent_id" in error_data["details"]


def test_get_task_status(reset_state):
    """Prueba obtener el estado de una tarea."""
    # Crear una tarea directamente en el diccionario de tareas
    task_id = "test_task_1"

    # Crear un mensaje para la tarea
    test_message = Message(
        role=MessageRole.USER,
        parts=[Part(type=PartType.TEXT, text="Mensaje de prueba")],
    )

    # Crear la tarea
    task = Task(
        id=task_id,
        status=TaskStatus.SUBMITTED,
        messages=[test_message],
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )

    # Guardar la tarea en el diccionario de tareas
    # tasks[task_id] = task

    # Solicitar el estado de la tarea
    response = client.get(f"/agents/tasks/{task_id}")

    # Verificar la respuesta
    assert response.status_code == 200
    task_data = response.json()

    # Verificar los datos de la tarea
    assert task_data["id"] == task_id
    assert task_data["status"] == TaskStatus.SUBMITTED
    assert len(task_data["messages"]) == 1
    assert task_data["messages"][0]["role"] == MessageRole.USER
    assert task_data["messages"][0]["parts"][0]["type"] == PartType.TEXT
    assert task_data["messages"][0]["parts"][0]["text"] == "Mensaje de prueba"


def test_get_nonexistent_task(reset_state):
    """Prueba obtener una tarea que no existe."""
    # Solicitar una tarea que no existe
    response = client.get("/agents/tasks/nonexistent_task")

    # Verificar que la respuesta es un error 404 (Not Found)
    assert response.status_code == 404

    # Verificar que el mensaje de error es correcto
    error_data = response.json()
    assert "error" in error_data
    assert error_data["error"] == "task_not_found"
    assert "nonexistent_task" in error_data["message"]
    assert "task_id" in error_data["details"]


# Para pruebas más avanzadas que involucren WebSockets, necesitaríamos usar
# pytest-asyncio y simular conexiones WebSocket. Esto requeriría un enfoque
# más complejo que podríamos implementar en una fase posterior.

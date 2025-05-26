"""
Pruebas para los endpoints de agentes de la API.

Este módulo contiene pruebas para verificar el funcionamiento
de los endpoints relacionados con los agentes.
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient


def test_list_agents(test_client: TestClient, auth_headers):
    """Prueba el endpoint para listar agentes."""
    with patch("app.routers.agents.get_agents") as mock_get_agents:
        # Configurar el mock para devolver agentes de prueba
        mock_agents = {
            "test_agent_1": MagicMock(
                agent_id="test_agent_1",
                name="Test Agent 1",
                description="Test agent for testing",
                capabilities=["test", "mock"],
            ),
            "test_agent_2": MagicMock(
                agent_id="test_agent_2",
                name="Test Agent 2",
                description="Another test agent",
                capabilities=["test", "mock"],
            ),
        }
        mock_get_agents.return_value = mock_agents

        # Realizar la solicitud
        response = test_client.get("/agents/", headers=auth_headers)

        # Verificar la respuesta
        assert response.status_code == 200
        assert "agents" in response.json()
        agents = response.json()["agents"]
        assert len(agents) == 2
        assert any(a["agent_id"] == "test_agent_1" for a in agents)
        assert any(a["agent_id"] == "test_agent_2" for a in agents)


def test_run_agent(test_client: TestClient, auth_headers):
    """Prueba el endpoint para ejecutar un agente."""
    with patch("app.routers.agents.get_agent") as mock_get_agent:
        # Configurar el mock del agente
        mock_agent = MagicMock()
        mock_agent.agent_id = "test_agent"
        mock_agent.run_async.return_value = {
            "response": "Respuesta de prueba",
            "session_id": str(uuid.uuid4()),
            "metadata": {"key": "value"},
        }
        mock_get_agent.return_value = mock_agent

        # Datos de la solicitud
        request_data = {"input_text": "Texto de prueba", "context": {"test": True}}

        # Realizar la solicitud
        response = test_client.post(
            "/agents/test_agent/run", json=request_data, headers=auth_headers
        )

        # Verificar la respuesta
        assert response.status_code == 200
        assert "response" in response.json()
        assert "session_id" in response.json()
        assert "metadata" in response.json()
        assert response.json()["agent_id"] == "test_agent"

        # Verificar que se llamó al método run_async del agente
        mock_agent.run_async.assert_called_once()
        args, kwargs = mock_agent.run_async.call_args
        assert kwargs["input_text"] == "Texto de prueba"
        assert "user_id" in kwargs
        assert kwargs["context"] == {"test": True}


def test_run_agent_with_session(test_client: TestClient, auth_headers):
    """Prueba el endpoint para ejecutar un agente con un session_id existente."""
    with patch("app.routers.agents.get_agent") as mock_get_agent:
        # Configurar el mock del agente
        mock_agent = MagicMock()
        mock_agent.agent_id = "test_agent"

        session_id = str(uuid.uuid4())
        mock_agent.run_async.return_value = {
            "response": "Respuesta de prueba con sesión",
            "session_id": session_id,
            "metadata": {"session": True},
        }
        mock_get_agent.return_value = mock_agent

        # Datos de la solicitud
        request_data = {
            "input_text": "Texto de prueba con sesión",
            "session_id": session_id,
        }

        # Realizar la solicitud
        response = test_client.post(
            "/agents/test_agent/run", json=request_data, headers=auth_headers
        )

        # Verificar la respuesta
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

        # Verificar que se llamó al método run_async del agente con el session_id
        mock_agent.run_async.assert_called_once()
        args, kwargs = mock_agent.run_async.call_args
        assert kwargs["session_id"] == session_id


def test_agent_not_found(test_client: TestClient, auth_headers):
    """Prueba el comportamiento cuando se solicita un agente que no existe."""
    with patch("app.routers.agents.get_agent") as mock_get_agent:
        # Configurar el mock para lanzar una excepción
        mock_get_agent.side_effect = HTTPException(
            status_code=404, detail="Agente no encontrado"
        )

        # Datos de la solicitud
        request_data = {"input_text": "Texto de prueba"}

        # Realizar la solicitud
        response = test_client.post(
            "/agents/non_existent_agent/run", json=request_data, headers=auth_headers
        )

        # Verificar la respuesta
        assert response.status_code == 404
        assert "detail" in response.json()
        assert "no encontrado" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_async_run_agent(async_client: AsyncClient, auth_headers):
    """Prueba el endpoint para ejecutar un agente de forma asíncrona."""
    with patch("app.routers.agents.get_agent") as mock_get_agent:
        # Configurar el mock del agente
        mock_agent = MagicMock()
        mock_agent.agent_id = "test_agent"
        mock_agent.run_async.return_value = {
            "response": "Respuesta asíncrona de prueba",
            "session_id": str(uuid.uuid4()),
            "metadata": {"async": True},
        }
        mock_get_agent.return_value = mock_agent

        # Datos de la solicitud
        request_data = {"input_text": "Texto de prueba asíncrono"}

        # Realizar la solicitud
        response = await async_client.post(
            "/agents/test_agent/run", json=request_data, headers=auth_headers
        )

        # Verificar la respuesta
        assert response.status_code == 200
        assert "response" in response.json()
        assert response.json()["agent_id"] == "test_agent"

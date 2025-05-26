"""
Pruebas unitarias para el conector A2A.

Este módulo contiene pruebas para verificar el funcionamiento
del conector A2A que permite la comunicación con el servidor A2A.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response, HTTPStatusError, RequestError, Request

from agents.orchestrator.a2a_connector import A2AConnector
from a2a import (
    AgentNotFoundError,
    AgentOfflineError,
    TaskNotFoundError,
    ConnectionError,
    AgentStatus,
)


# Función auxiliar para crear objetos Response correctamente configurados
def create_mock_response(status_code=200, json_data=None, text=""):
    """Crea un objeto Response correctamente configurado para pruebas."""
    mock_request = Request("GET", "http://test-server:8000")
    response = Response(status_code=status_code, text=text)
    response.request = mock_request
    if json_data is not None:
        response.json = lambda: json_data
    return response


# Fixture para el conector A2A
@pytest_asyncio.fixture
async def a2a_connector():
    """Fixture que proporciona un conector A2A con cliente mock."""
    connector = A2AConnector(a2a_url="http://test-server:8000")
    connector.client = AsyncMock()
    yield connector
    await connector.close()


# Pruebas para el método discover_agents
@pytest.mark.asyncio
async def test_discover_agents_success(a2a_connector):
    """Prueba que discover_agents devuelve la lista de agentes cuando la solicitud es exitosa."""
    # Configurar el mock
    mock_response = create_mock_response(
        status_code=200,
        json_data={"agents": [{"agent_id": "agent1", "name": "Agent 1"}]},
    )
    a2a_connector.client.get.return_value = mock_response

    # Ejecutar la función
    result = await a2a_connector.discover_agents()

    # Verificar el resultado
    assert result == [{"agent_id": "agent1", "name": "Agent 1"}]
    a2a_connector.client.get.assert_called_once_with("/agents/discover")


@pytest.mark.asyncio
async def test_discover_agents_http_error(a2a_connector):
    """Prueba que discover_agents maneja correctamente errores HTTP."""
    # Configurar el mock para lanzar un error HTTP
    mock_response = Response(500, text="Error interno del servidor")
    mock_error = HTTPStatusError(
        "Error HTTP", request=MagicMock(), response=mock_response
    )
    a2a_connector.client.get.side_effect = mock_error

    # Ejecutar la función y verificar que lanza la excepción esperada
    with pytest.raises(Exception) as excinfo:
        await a2a_connector.discover_agents()

    assert "Error al descubrir agentes" in str(excinfo.value)


@pytest.mark.asyncio
async def test_discover_agents_connection_error(a2a_connector):
    """Prueba que discover_agents maneja correctamente errores de conexión."""
    # Configurar el mock para lanzar un error de conexión
    a2a_connector.client.get.side_effect = RequestError(
        "Error de conexión", request=MagicMock()
    )

    # Ejecutar la función y verificar que lanza la excepción esperada
    with pytest.raises(ConnectionError) as excinfo:
        await a2a_connector.discover_agents()

    assert "Error de conexión al servidor A2A" in str(excinfo.value)


# Pruebas para el método get_agent_info
@pytest.mark.asyncio
async def test_get_agent_info_success(a2a_connector):
    """Prueba que get_agent_info devuelve la información del agente cuando la solicitud es exitosa."""
    # Configurar el mock
    mock_response = create_mock_response(
        status_code=200,
        json_data={"agent_id": "agent1", "name": "Agent 1", "status": "online"},
    )
    a2a_connector.client.get.return_value = mock_response

    # Ejecutar la función
    result = await a2a_connector.get_agent_info("agent1")

    # Verificar el resultado
    assert result == {"agent_id": "agent1", "name": "Agent 1", "status": "online"}
    a2a_connector.client.get.assert_called_once_with("/agents/agent1")


@pytest.mark.asyncio
async def test_get_agent_info_not_found(a2a_connector):
    """Prueba que get_agent_info lanza AgentNotFoundError cuando el agente no existe."""
    # Configurar el mock para lanzar un error 404
    mock_response = Response(404, text="Agente no encontrado")
    mock_error = HTTPStatusError(
        "Error HTTP", request=MagicMock(), response=mock_response
    )
    a2a_connector.client.get.side_effect = mock_error

    # Ejecutar la función y verificar que lanza la excepción esperada
    with pytest.raises(AgentNotFoundError) as excinfo:
        await a2a_connector.get_agent_info("agent1")

    assert "agent1" in str(excinfo.value)


# Pruebas para el método request_task
@pytest.mark.asyncio
async def test_request_task_success(a2a_connector):
    """Prueba que request_task envía correctamente una solicitud de tarea."""
    # Configurar el mock
    mock_response = create_mock_response(
        status_code=200, json_data={"task_id": "task123", "status": "pending"}
    )
    a2a_connector.client.post.return_value = mock_response

    # Ejecutar la función
    result = await a2a_connector.request_task("agent1", {"input": "test"})

    # Verificar el resultado
    assert result == {"task_id": "task123", "status": "pending"}
    a2a_connector.client.post.assert_called_once()

    # Verificar que se pasó el JSON correcto
    call_args = a2a_connector.client.post.call_args
    assert call_args[0][0] == "/agents/request"
    assert "agent_id" in call_args[1]["json"]
    assert call_args[1]["json"]["agent_id"] == "agent1"
    assert "task" in call_args[1]["json"]


@pytest.mark.asyncio
async def test_request_task_agent_not_found(a2a_connector):
    """Prueba que request_task lanza AgentNotFoundError cuando el agente no existe."""
    # Configurar el mock para lanzar un error 404
    mock_response = Response(404, text="Agente no encontrado")
    mock_error = HTTPStatusError(
        "Error HTTP", request=MagicMock(), response=mock_response
    )
    a2a_connector.client.post.side_effect = mock_error

    # Ejecutar la función y verificar que lanza la excepción esperada
    with pytest.raises(AgentNotFoundError) as excinfo:
        await a2a_connector.request_task("agent1", {"input": "test"})

    assert "agent1" in str(excinfo.value)


@pytest.mark.asyncio
async def test_request_task_agent_offline(a2a_connector):
    """Prueba que request_task lanza AgentOfflineError cuando el agente está offline."""
    # Configurar el mock para lanzar un error 400
    mock_response = Response(400, text="Agente offline")
    mock_error = HTTPStatusError(
        "Error HTTP", request=MagicMock(), response=mock_response
    )
    a2a_connector.client.post.side_effect = mock_error

    # Ejecutar la función y verificar que lanza la excepción esperada
    with pytest.raises(AgentOfflineError) as excinfo:
        await a2a_connector.request_task("agent1", {"input": "test"})

    assert "agent1" in str(excinfo.value)


# Pruebas para el método get_task_status
@pytest.mark.asyncio
async def test_get_task_status_success(a2a_connector):
    """Prueba que get_task_status devuelve el estado de la tarea cuando la solicitud es exitosa."""
    # Configurar el mock
    mock_response = create_mock_response(
        status_code=200,
        json_data={
            "task_id": "task123",
            "status": "completed",
            "result": "test result",
        },
    )
    a2a_connector.client.get.return_value = mock_response

    # Ejecutar la función
    result = await a2a_connector.get_task_status("task123")

    # Verificar el resultado
    assert result == {
        "task_id": "task123",
        "status": "completed",
        "result": "test result",
    }
    a2a_connector.client.get.assert_called_once_with("/agents/tasks/task123")


@pytest.mark.asyncio
async def test_get_task_status_not_found(a2a_connector):
    """Prueba que get_task_status lanza TaskNotFoundError cuando la tarea no existe."""
    # Configurar el mock para lanzar un error 404
    mock_response = Response(404, text="Tarea no encontrada")
    mock_error = HTTPStatusError(
        "Error HTTP", request=MagicMock(), response=mock_response
    )
    a2a_connector.client.get.side_effect = mock_error

    # Ejecutar la función y verificar que lanza la excepción esperada
    with pytest.raises(TaskNotFoundError) as excinfo:
        await a2a_connector.get_task_status("task123")

    assert "task123" in str(excinfo.value)


# Pruebas para el método wait_for_task_completion
@pytest.mark.asyncio
async def test_wait_for_task_completion_success(a2a_connector):
    """Prueba que wait_for_task_completion espera correctamente a que una tarea se complete."""
    # Configurar el mock para devolver primero "pending" y luego "completed"
    pending_response = create_mock_response(
        status_code=200, json_data={"task_id": "task123", "status": "submitted"}
    )
    completed_response = create_mock_response(
        status_code=200,
        json_data={
            "task_id": "task123",
            "status": "completed",
            "result": "test result",
        },
    )

    a2a_connector.client.get.side_effect = [pending_response, completed_response]

    # Ejecutar la función con un timeout corto
    result = await a2a_connector.wait_for_task_completion(
        "task123", timeout=1.0, poll_interval=0.1
    )

    # Verificar el resultado
    assert result == {
        "task_id": "task123",
        "status": "completed",
        "result": "test result",
    }
    assert a2a_connector.client.get.call_count == 2


@pytest.mark.asyncio
async def test_wait_for_task_completion_timeout(a2a_connector):
    """Prueba que wait_for_task_completion lanza TimeoutError cuando se agota el tiempo."""
    # Configurar el mock para devolver siempre "pending"
    pending_response = create_mock_response(
        status_code=200, json_data={"task_id": "task123", "status": "submitted"}
    )

    a2a_connector.client.get.return_value = pending_response

    # Ejecutar la función con un timeout muy corto
    with pytest.raises(TimeoutError) as excinfo:
        await a2a_connector.wait_for_task_completion(
            "task123", timeout=0.2, poll_interval=0.1
        )

    assert "Tiempo de espera agotado" in str(excinfo.value)
    assert a2a_connector.client.get.call_count >= 1


# Pruebas para el método execute_task
@pytest.mark.asyncio
async def test_execute_task_success(a2a_connector):
    """Prueba que execute_task ejecuta correctamente una tarea y devuelve el resultado."""
    # Configurar mocks para request_task y wait_for_task_completion
    request_response = {"task_id": "task123", "status": "submitted"}
    completion_response = {
        "task_id": "task123",
        "status": "completed",
        "result": "test result",
    }

    # Usar patch para reemplazar los métodos del conector
    with patch.object(
        a2a_connector, "request_task", return_value=request_response
    ) as mock_request:
        with patch.object(
            a2a_connector, "wait_for_task_completion", return_value=completion_response
        ) as mock_wait:
            # Ejecutar la función
            result = await a2a_connector.execute_task(
                "agent1", {"input": "test"}, wait_for_completion=True
            )

            # Verificar el resultado
            assert result == completion_response
            mock_request.assert_called_once_with("agent1", {"input": "test"})
            mock_wait.assert_called_once_with("task123", 30.0)


@pytest.mark.asyncio
async def test_execute_task_no_wait(a2a_connector):
    """Prueba que execute_task devuelve la respuesta inmediata cuando wait_for_completion es False."""
    # Configurar mock para request_task
    request_response = {"task_id": "task123", "status": "submitted"}

    # Usar patch para reemplazar el método request_task
    with patch.object(
        a2a_connector, "request_task", return_value=request_response
    ) as mock_request:
        with patch.object(a2a_connector, "wait_for_task_completion") as mock_wait:
            # Ejecutar la función sin esperar completitud
            result = await a2a_connector.execute_task(
                "agent1", {"input": "test"}, wait_for_completion=False
            )

            # Verificar el resultado
            assert result == request_response
            mock_request.assert_called_once_with("agent1", {"input": "test"})
            mock_wait.assert_not_called()


# Pruebas para el método register_agent
@pytest.mark.asyncio
async def test_register_agent_success(a2a_connector):
    """Prueba que register_agent registra correctamente un agente."""
    # Configurar el mock
    mock_response = create_mock_response(
        status_code=200, json_data={"success": True, "agent_id": "agent1"}
    )
    a2a_connector.client.post.return_value = mock_response

    # Crear un objeto AgentInfo mock
    agent_data = {
        "agent_id": "agent1",
        "name": "Agent 1",
        "capabilities": ["capability1"],
    }
    agent_info = MagicMock()
    agent_info.model_dump.return_value = agent_data
    agent_info.dict = MagicMock(
        return_value=agent_data
    )  # Para compatibilidad con versiones anteriores

    # Ejecutar la función
    result = await a2a_connector.register_agent(agent_info)

    # Verificar el resultado
    assert result == {"success": True, "agent_id": "agent1"}
    # Verificar que se llamó al método post con los argumentos correctos
    a2a_connector.client.post.assert_called_once()
    args, kwargs = a2a_connector.client.post.call_args
    assert args[0] == "/agents/register"
    assert "json" in kwargs


# Pruebas para el método update_agent_status
@pytest.mark.asyncio
async def test_update_agent_status_success(a2a_connector):
    """Prueba que update_agent_status actualiza correctamente el estado de un agente."""
    # Configurar el mock
    mock_response = create_mock_response(
        status_code=200,
        json_data={"success": True, "agent_id": "agent1", "status": "online"},
    )
    a2a_connector.client.put.return_value = mock_response

    # Ejecutar la función
    result = await a2a_connector.update_agent_status("agent1", AgentStatus.ONLINE)

    # Verificar el resultado
    assert result == {
        "success": True,
        "agent_id": "agent1",
        "status": AgentStatus.ONLINE,
    }
    a2a_connector.client.put.assert_called_once_with(
        "/agents/status", json={"agent_id": "agent1", "status": AgentStatus.ONLINE}
    )


@pytest.mark.asyncio
async def test_update_agent_status_not_found(a2a_connector):
    """Prueba que update_agent_status lanza AgentNotFoundError cuando el agente no existe."""
    # Configurar el mock para lanzar un error 404
    mock_response = Response(404, text="Agente no encontrado")
    mock_error = HTTPStatusError(
        "Error HTTP", request=MagicMock(), response=mock_response
    )
    a2a_connector.client.put.side_effect = mock_error

    # Ejecutar la función y verificar que lanza la excepción esperada
    with pytest.raises(AgentNotFoundError) as excinfo:
        await a2a_connector.update_agent_status("agent1", AgentStatus.ONLINE)

    assert "agent1" in str(excinfo.value)

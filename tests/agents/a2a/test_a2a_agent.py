"""
Pruebas unitarias para el agente A2A.
"""

import pytest
from unittest.mock import patch, AsyncMock

import sys
import os

# Añadir el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from agents.base.a2a_agent import A2AAgent


@pytest.fixture
def agent():
    """Crea una instancia de A2AAgent para pruebas."""
    return A2AAgent(
        agent_id="test_agent_1",
        name="Test Agent 1",
        description="Agente de prueba para tests unitarios",
        capabilities=["test_capability"],
        skills=[{"name": "test_skill", "description": "Habilidad de prueba"}],
        a2a_server_url="ws://localhost:9001",
    )


@pytest.mark.asyncio
async def test_agent_initialization(agent):
    """Prueba la inicialización correcta del agente."""
    assert agent.agent_id == "test_agent_1"
    assert agent.name == "Test Agent 1"
    assert agent.description == "Agente de prueba para tests unitarios"
    assert len(agent.skills) == 1
    assert agent.skills[0]["name"] == "test_skill"
    assert not agent.is_connected
    assert not agent.is_registered


# TODO: Refactorizar esta prueba para usar mocks adecuados para el método register de A2AAgent (p.ej., mock httpx.AsyncClient)
# @pytest.mark.asyncio
# async def test_register_success():
#     """Prueba el registro exitoso del agente."""
#     agent = A2AAgent(
#         agent_id="test_agent_1",
#         name="Test Agent 1",
#         description="Agente de prueba",
#         capabilities=["test_capability"],
#         skills=[{"name": "test_skill", "description": "Habilidad de prueba"}]
#     )
#
#     # Enfoque más simple: parchear directamente el método register
#     async def mock_register():
#         agent.is_registered = True
#         return True
#
#     # Aplicar el parche
#     with patch.object(agent, 'register', mock_register):
#         # Ejecutar el método que queremos probar
#         result = await agent.register()
#
#         # Verificar que el registro fue exitoso
#         assert result is True
#         assert agent.is_registered is True

# TODO: Refactorizar esta prueba para usar mocks adecuados para el método register de A2AAgent (p.ej., mock httpx.AsyncClient)
# @pytest.mark.asyncio
# async def test_register_failure():
#     """Prueba el registro fallido del agente."""
#     agent = A2AAgent(
#         agent_id="test_agent_1",
#         name="Test Agent 1",
#         description="Agente de prueba",
#         capabilities=["test_capability"],
#         skills=[{"name": "test_skill", "description": "Habilidad de prueba"}]
#     )
#
#     # Enfoque más simple: parchear directamente el método register
#     async def mock_register_failure():
#         # No modificamos is_registered, debe permanecer False
#         return False
#
#     # Aplicar el parche
#     with patch.object(agent, 'register', mock_register_failure):
#         # Ejecutar el método que queremos probar
#         result = await agent.register()
#
#         # Verificar que el registro falló
#         assert result is False
#         assert agent.is_registered is False


@pytest.mark.asyncio
async def test_connect_success():
    """Prueba la conexión exitosa del agente."""
    agent = A2AAgent(
        agent_id="test_agent_1",
        name="Test Agent 1",
        description="Agente de prueba",
        capabilities=["test_capability"],
        skills=[{"name": "test_skill", "description": "Habilidad de prueba"}],
    )

    # Simular una conexión WebSocket exitosa
    mock_websocket = AsyncMock()

    # Parchear websockets.connect y _message_loop para evitar conexiones reales
    with (
        patch("websockets.connect", AsyncMock(return_value=mock_websocket)),
        patch.object(agent, "_message_loop", AsyncMock()),
        patch.object(agent, "_send_pings", AsyncMock()),
    ):

        # Simular una tarea para _send_pings
        mock_task = AsyncMock()
        with patch("asyncio.create_task", return_value=mock_task):
            result = await agent.connect()

            # Verificar que la conexión fue exitosa
            assert result is True
            assert agent.is_connected is True
            assert agent.websocket is mock_websocket


@pytest.mark.asyncio
async def test_disconnect():
    """Prueba la desconexión del agente."""
    agent = A2AAgent(
        agent_id="test_agent_1",
        name="Test Agent 1",
        description="Agente de prueba",
        capabilities=["test_capability"],
        skills=[{"name": "test_skill", "description": "Habilidad de prueba"}],
    )

    # Simular una conexión WebSocket
    mock_websocket = AsyncMock()
    agent.websocket = mock_websocket
    agent.is_connected = True

    # Simular una tarea de pings con cancel() que devuelve None
    mock_task = AsyncMock()
    mock_task.cancel.return_value = None
    agent._send_pings_task = mock_task

    # Parchear asyncio.CancelledError para evitar problemas con await mock_task
    with patch("asyncio.CancelledError", Exception):
        result = await agent.disconnect()

    # Verificar que la desconexión fue exitosa
    assert result is True
    assert agent.is_connected is False
    assert agent.websocket is None

    # Verificar que se canceló la tarea de pings
    mock_task.cancel.assert_called_once()

    # Verificar que se cerró el WebSocket
    mock_websocket.close.assert_called_once()


# TODO: Refactorizar esta prueba para usar A2AAgent.execute_task o _process_message y mocks adecuados.
# El método _handle_task era específico de TestA2AAgent.
# @pytest.mark.asyncio
# async def test_handle_task():
#     """Prueba el manejo de tareas."""
#     agent = A2AAgent(
#         agent_id="test_agent_1",
#         name="Test Agent 1",
#         description="Agente de prueba",
#         capabilities=["test_capability"],
#         skills=[{"name": "test_skill", "description": "Habilidad de prueba"}]
#     )
#
#     # Parchear random.random para asegurar un resultado exitoso
#     with patch('random.random', return_value=0.9):
#         result, status = await agent._handle_task("task_123", {"input": "Test task"})
#
#         # Verificar que la tarea se completó exitosamente
#         assert status == "completed"
#         assert "response" in result
#         assert "Test Agent 1" in result["response"]
#
#     # Parchear random.random para asegurar un resultado fallido
#     with patch('random.random', return_value=0.1):
#         result, status = await agent._handle_task("task_123", {"input": "Test task"})
#
#         # Verificar que la tarea falló
#         assert status == "failed"
#         assert "error" in result

# TODO: Refactorizar esta prueba para usar A2AAgent._process_message y mocks adecuados.
# La interacción con _handle_task era específica de TestA2AAgent.
# @pytest.mark.asyncio
# async def test_process_message_task():
#     """Prueba el procesamiento de mensajes de tipo 'task'."""
#     agent = A2AAgent(
#         agent_id="test_agent_1",
#         name="Test Agent 1",
#         description="Agente de prueba",
#         capabilities=["test_capability"],
#         skills=[{"name": "test_skill", "description": "Habilidad de prueba"}]
#     )
#
#     # Simular un mensaje de tarea
#     task_message = {
#         "type": "task",
#         "task_id": "task_123",
#         "content": {"input": "Test task"}
#     }
#
#     # Parchear _handle_task y send_message para evitar ejecución real
#     with patch.object(agent, '_handle_task', AsyncMock(return_value=({"response": "Test response"}, "completed"))), \
#          patch.object(agent, 'send_message', AsyncMock()):
#
#         await agent._process_message(task_message)
#
#         # Verificar que se llamó a _handle_task con los parámetros correctos
#         agent._handle_task.assert_called_once_with("task_123", {"input": "Test task"})
#
#         # Verificar que se envió un mensaje de actualización
#         agent.send_message.assert_called_once()
#         args, kwargs = agent.send_message.call_args
#         update_message = args[0]
#         assert update_message["type"] == "task_update"
#         assert update_message["task_id"] == "task_123"
#         assert update_message["status"] == "completed"
#         assert update_message["result"] == {"response": "Test response"}

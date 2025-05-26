"""
Pruebas unitarias para el adaptador A2A.

Este módulo contiene pruebas para verificar el funcionamiento
del adaptador A2A, incluyendo la comunicación entre agentes.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import time
import sys

# Mockear las dependencias de configuración antes de importar el adaptador
sys.modules["core.settings"] = MagicMock()
sys.modules["core.telemetry"] = MagicMock()
sys.modules["infrastructure.adapters.telemetry_adapter"] = MagicMock()

from infrastructure.adapters.a2a_adapter import (
    A2AAdapter,
    a2a_adapter,
    get_a2a_server,
    get_a2a_server_status,
)
from infrastructure.a2a_optimized import MessagePriority


# Fixture para el adaptador A2A
@pytest.fixture
def adapter():
    """Fixture que proporciona un adaptador A2A con configuración predeterminada."""
    return A2AAdapter()


# Pruebas para el método register_agent
@pytest.mark.asyncio
async def test_register_agent(adapter):
    """Prueba que register_agent registra correctamente un agente."""
    # Mock para a2a_server.register_agent
    with patch(
        "infrastructure.a2a_optimized.a2a_server.register_agent", new_callable=AsyncMock
    ) as mock_register:
        # Datos de prueba
        agent_id = "test_agent"
        agent_info = {
            "name": "Test Agent",
            "description": "Agente de prueba",
            "message_callback": AsyncMock(),
        }

        # Registrar agente
        adapter.register_agent(agent_id, agent_info)

        # Verificar que se registró en el adaptador
        assert agent_id in adapter.registered_agents
        assert adapter.registered_agents[agent_id] == agent_info

        # Verificar que se llamó a register_agent del servidor optimizado
        # Nota: Como se usa create_task, necesitamos esperar un poco
        await asyncio.sleep(0.1)
        mock_register.assert_called_once()
        assert mock_register.call_args[1]["agent_id"] == agent_id


# Pruebas para el método unregister_agent
@pytest.mark.asyncio
async def test_unregister_agent(adapter):
    """Prueba que unregister_agent elimina correctamente un agente."""
    # Mock para a2a_server.unregister_agent
    with patch(
        "infrastructure.a2a_optimized.a2a_server.unregister_agent",
        new_callable=AsyncMock,
    ) as mock_unregister:
        # Registrar agente primero
        agent_id = "test_agent"
        agent_info = {
            "name": "Test Agent",
            "description": "Agente de prueba",
            "message_callback": AsyncMock(),
        }
        adapter.registered_agents[agent_id] = agent_info

        # Eliminar registro
        adapter.unregister_agent(agent_id)

        # Verificar que se eliminó del adaptador
        assert agent_id not in adapter.registered_agents

        # Verificar que se llamó a unregister_agent del servidor optimizado
        await asyncio.sleep(0.1)
        mock_unregister.assert_called_once_with(agent_id)


# Pruebas para el método send_message
@pytest.mark.asyncio
async def test_send_message(adapter):
    """Prueba que send_message envía correctamente un mensaje."""
    # Mock para a2a_server.send_message
    with patch(
        "infrastructure.a2a_optimized.a2a_server.send_message", new_callable=AsyncMock
    ) as mock_send:
        # Configurar mock
        mock_send.return_value = True

        # Datos de prueba
        from_agent_id = "agent1"
        to_agent_id = "agent2"
        message = {"content": "Mensaje de prueba"}

        # Enviar mensaje
        result = await adapter.send_message(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            message=message,
            priority="HIGH",
        )

        # Verificar resultado
        assert result is True

        # Verificar que se llamó a send_message del servidor optimizado
        mock_send.assert_called_once_with(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            message=message,
            priority=MessagePriority.HIGH,
        )


# Pruebas para el método call_agent
@pytest.mark.asyncio
async def test_call_agent_success(adapter):
    """Prueba que call_agent llama correctamente a un agente y obtiene su respuesta."""
    # Mocks
    with (
        patch.object(adapter, "register_agent") as mock_register,
        patch.object(adapter, "unregister_agent") as mock_unregister,
        patch.object(adapter, "send_message", new_callable=AsyncMock) as mock_send,
    ):

        # Configurar mocks
        mock_send.return_value = True

        # Registrar un agente de prueba
        agent_id = "test_agent"
        adapter.registered_agents[agent_id] = {
            "name": "Test Agent",
            "description": "Agente de prueba",
        }

        # Simular respuesta del agente
        expected_response = {
            "status": "success",
            "output": "Respuesta de prueba",
            "agent_id": agent_id,
            "agent_name": "Test Agent",
        }

        # Configurar el comportamiento de register_agent para capturar el callback
        def register_side_effect(temp_id, info):
            # Simular que el agente responde inmediatamente
            asyncio.create_task(info["message_callback"](expected_response))

        mock_register.side_effect = register_side_effect

        # Llamar al agente
        response = await adapter.call_agent(
            agent_id=agent_id, user_input="Consulta de prueba", context={"key": "value"}
        )

        # Verificar respuesta
        assert response == expected_response

        # Verificar que se registró un agente temporal
        assert mock_register.called
        assert "temp_" in mock_register.call_args[0][0]

        # Verificar que se envió un mensaje
        assert mock_send.called
        assert mock_send.call_args[1]["to_agent_id"] == agent_id
        assert "user_input" in mock_send.call_args[1]["message"]
        assert mock_send.call_args[1]["message"]["user_input"] == "Consulta de prueba"

        # Verificar que se eliminó el agente temporal
        assert mock_unregister.called


@pytest.mark.asyncio
async def test_call_agent_not_registered(adapter):
    """Prueba que call_agent maneja correctamente el caso de un agente no registrado."""
    # Llamar a un agente no registrado
    response = await adapter.call_agent(
        agent_id="nonexistent_agent", user_input="Consulta de prueba"
    )

    # Verificar respuesta de error
    assert response["status"] == "error"
    assert "no está registrado" in response["error"]


@pytest.mark.asyncio
async def test_call_agent_send_failure(adapter):
    """Prueba que call_agent maneja correctamente el fallo al enviar un mensaje."""
    # Mocks
    with (
        patch.object(adapter, "register_agent"),
        patch.object(adapter, "unregister_agent") as mock_unregister,
        patch.object(adapter, "send_message", new_callable=AsyncMock) as mock_send,
    ):

        # Configurar mocks para simular fallo al enviar
        mock_send.return_value = False

        # Registrar un agente de prueba
        agent_id = "test_agent"
        adapter.registered_agents[agent_id] = {
            "name": "Test Agent",
            "description": "Agente de prueba",
        }

        # Llamar al agente
        response = await adapter.call_agent(
            agent_id=agent_id, user_input="Consulta de prueba"
        )

        # Verificar respuesta de error
        assert response["status"] == "error"
        assert "No se pudo enviar el mensaje" in response["error"]

        # Verificar que se eliminó el agente temporal
        assert mock_unregister.called


@pytest.mark.asyncio
async def test_call_agent_timeout(adapter):
    """Prueba que call_agent maneja correctamente el timeout al esperar respuesta."""
    # Mocks
    with (
        patch.object(adapter, "register_agent"),
        patch.object(adapter, "unregister_agent") as mock_unregister,
        patch.object(adapter, "send_message", new_callable=AsyncMock) as mock_send,
        patch("asyncio.wait_for", side_effect=asyncio.TimeoutError),
    ):

        # Configurar mocks
        mock_send.return_value = True

        # Registrar un agente de prueba
        agent_id = "test_agent"
        adapter.registered_agents[agent_id] = {
            "name": "Test Agent",
            "description": "Agente de prueba",
        }

        # Llamar al agente
        response = await adapter.call_agent(
            agent_id=agent_id, user_input="Consulta de prueba"
        )

        # Verificar respuesta de error por timeout
        assert response["status"] == "error"
        assert "Timeout" in response["error"]

        # Verificar que se eliminó el agente temporal
        assert mock_unregister.called


# Pruebas para el método call_multiple_agents
@pytest.mark.asyncio
async def test_call_multiple_agents_success(adapter):
    """Prueba que call_multiple_agents llama correctamente a múltiples agentes en paralelo."""
    # Mock para call_agent
    original_call_agent = adapter.call_agent

    async def mock_call_agent(agent_id, user_input, context=None):
        # Simular respuestas diferentes según el agente
        if agent_id == "agent1":
            return {
                "status": "success",
                "output": "Respuesta del agente 1",
                "agent_id": "agent1",
                "agent_name": "Agent 1",
            }
        elif agent_id == "agent2":
            return {
                "status": "success",
                "output": "Respuesta del agente 2",
                "agent_id": "agent2",
                "agent_name": "Agent 2",
            }
        else:
            return {
                "status": "error",
                "error": f"Agente desconocido: {agent_id}",
                "output": f"Error: Agente desconocido {agent_id}",
                "agent_id": agent_id,
                "agent_name": agent_id,
            }

    # Aplicar el mock
    adapter.call_agent = mock_call_agent

    try:
        # Llamar a múltiples agentes
        responses = await adapter.call_multiple_agents(
            user_input="Consulta de prueba",
            agent_ids=["agent1", "agent2"],
            context={"key": "value"},
        )

        # Verificar respuestas
        assert len(responses) == 2
        assert "agent1" in responses
        assert "agent2" in responses
        assert responses["agent1"]["status"] == "success"
        assert responses["agent2"]["status"] == "success"
        assert responses["agent1"]["output"] == "Respuesta del agente 1"
        assert responses["agent2"]["output"] == "Respuesta del agente 2"

    finally:
        # Restaurar el método original
        adapter.call_agent = original_call_agent


@pytest.mark.asyncio
async def test_call_multiple_agents_with_error(adapter):
    """Prueba que call_multiple_agents maneja correctamente errores en algunos agentes."""
    # Mock para call_agent
    original_call_agent = adapter.call_agent

    async def mock_call_agent(agent_id, user_input, context=None):
        # Simular éxito para agent1 y error para agent2
        if agent_id == "agent1":
            return {
                "status": "success",
                "output": "Respuesta del agente 1",
                "agent_id": "agent1",
                "agent_name": "Agent 1",
            }
        elif agent_id == "agent2":
            # Simular una excepción
            raise Exception("Error simulado")
        else:
            return {
                "status": "error",
                "error": f"Agente desconocido: {agent_id}",
                "output": f"Error: Agente desconocido {agent_id}",
                "agent_id": agent_id,
                "agent_name": agent_id,
            }

    # Aplicar el mock
    adapter.call_agent = mock_call_agent

    try:
        # Llamar a múltiples agentes
        responses = await adapter.call_multiple_agents(
            user_input="Consulta de prueba",
            agent_ids=["agent1", "agent2", "agent3"],
            context={"key": "value"},
        )

        # Verificar respuestas
        assert len(responses) == 3
        assert "agent1" in responses
        assert "agent2" in responses
        assert "agent3" in responses

        # Verificar respuesta exitosa
        assert responses["agent1"]["status"] == "success"
        assert responses["agent1"]["output"] == "Respuesta del agente 1"

        # Verificar manejo de excepción
        assert responses["agent2"]["status"] == "error"
        assert "Error simulado" in responses["agent2"]["error"]

        # Verificar respuesta de error normal
        assert responses["agent3"]["status"] == "error"
        assert "Agente desconocido" in responses["agent3"]["error"]

    finally:
        # Restaurar el método original
        adapter.call_agent = original_call_agent


@pytest.mark.asyncio
async def test_call_multiple_agents_empty_list(adapter):
    """Prueba que call_multiple_agents maneja correctamente una lista vacía de agentes."""
    # Llamar con lista vacía
    responses = await adapter.call_multiple_agents(
        user_input="Consulta de prueba", agent_ids=[], context={"key": "value"}
    )

    # Verificar que se devuelve un diccionario vacío
    assert isinstance(responses, dict)
    assert len(responses) == 0


# Pruebas para las funciones de compatibilidad
def test_get_a2a_server():
    """Prueba que get_a2a_server devuelve la instancia global del adaptador."""
    server = get_a2a_server()
    assert server is a2a_adapter
    assert isinstance(server, A2AAdapter)


@pytest.mark.asyncio
async def test_get_a2a_server_status():
    """Prueba que get_a2a_server_status devuelve el estado del servidor."""
    # Mock para a2a_server.get_stats
    with patch(
        "infrastructure.a2a_optimized.a2a_server.get_stats", new_callable=AsyncMock
    ) as mock_get_stats:
        # Configurar mock
        mock_get_stats.return_value = {
            "running": True,
            "registered_agents": ["agent1", "agent2"],
            "total_messages_sent": 10,
            "failed_deliveries": 1,
            "timestamp": time.time(),
        }

        # Obtener estado
        status = get_a2a_server_status()

        # Verificar resultado
        assert status["status"] == "ok"
        assert "timestamp" in status
        assert status["details"]["registered_agents"] == 2
        assert status["details"]["is_active"] is True

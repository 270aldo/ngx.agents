"""
Pruebas unitarias para el adaptador del Orchestrator.

Este módulo contiene pruebas para verificar el correcto funcionamiento
del adaptador del Orchestrator con el sistema A2A optimizado.
"""

import pytest
from unittest.mock import patch, AsyncMock

from infrastructure.adapters.orchestrator_adapter import (
    orchestrator_adapter,
    initialize_orchestrator_adapter,
)
from app.schemas.a2a import A2ATaskContext


@pytest.fixture
def mock_a2a_adapter():
    """Fixture para simular el adaptador A2A."""
    with patch("infrastructure.adapters.orchestrator_adapter.a2a_adapter") as mock:
        mock.call_agent = AsyncMock()
        mock.call_multiple_agents = AsyncMock()
        mock.register_agent = AsyncMock()
        yield mock


@pytest.fixture
def mock_intent_analyzer_adapter():
    """Fixture para simular el adaptador del Intent Analyzer."""
    with patch(
        "infrastructure.adapters.orchestrator_adapter.intent_analyzer_adapter"
    ) as mock:
        mock.analyze_intent = AsyncMock()
        yield mock


@pytest.fixture
def mock_state_manager_adapter():
    """Fixture para simular el adaptador del State Manager."""
    with patch(
        "infrastructure.adapters.orchestrator_adapter.state_manager_adapter"
    ) as mock:
        mock.load_state = AsyncMock()
        mock.save_state = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_initialize_orchestrator_adapter(mock_a2a_adapter):
    """Prueba la inicialización del adaptador del Orchestrator."""
    # Configurar el mock
    mock_a2a_adapter.register_agent.return_value = None

    # Llamar a la función de inicialización
    await initialize_orchestrator_adapter()

    # Verificar que se llamó a register_agent con los parámetros correctos
    mock_a2a_adapter.register_agent.assert_called_once()
    call_args = mock_a2a_adapter.register_agent.call_args[1]
    assert call_args["agent_id"] == orchestrator_adapter.agent_id
    assert call_args["agent_name"] == orchestrator_adapter.name
    assert call_args["agent_description"] == orchestrator_adapter.description
    assert call_args["agent_version"] == orchestrator_adapter.version
    assert call_args["agent_capabilities"] == orchestrator_adapter.capabilities
    assert callable(call_args["handler"])


@pytest.mark.asyncio
async def test_consult_other_agent(mock_a2a_adapter):
    """Prueba la consulta a otro agente a través del adaptador."""
    # Configurar el mock
    mock_response = {
        "status": "success",
        "output": "Respuesta de prueba",
        "agent_id": "test_agent",
        "agent_name": "Test Agent",
    }
    mock_a2a_adapter.call_agent.return_value = mock_response

    # Llamar al método
    result = await orchestrator_adapter._consult_other_agent(
        agent_id="test_agent",
        query="Consulta de prueba",
        user_id="test_user",
        session_id="test_session",
    )

    # Verificar que se llamó a call_agent con los parámetros correctos
    mock_a2a_adapter.call_agent.assert_called_once()
    call_args = mock_a2a_adapter.call_agent.call_args[1]
    assert call_args["agent_id"] == "test_agent"
    assert call_args["user_input"] == "Consulta de prueba"
    assert isinstance(call_args["context"], A2ATaskContext)
    assert call_args["context"].user_id == "test_user"
    assert call_args["context"].session_id == "test_session"

    # Verificar el resultado
    assert result == mock_response


@pytest.mark.asyncio
async def test_consult_other_agent_error(mock_a2a_adapter):
    """Prueba el manejo de errores al consultar a otro agente."""
    # Configurar el mock para lanzar una excepción
    mock_a2a_adapter.call_agent.side_effect = Exception("Error de prueba")

    # Llamar al método
    result = await orchestrator_adapter._consult_other_agent(
        agent_id="test_agent", query="Consulta de prueba"
    )

    # Verificar el resultado
    assert result["status"] == "error"
    assert "Error de prueba" in result["error"]
    assert result["agent_id"] == "test_agent"


@pytest.mark.asyncio
async def test_run_async_impl():
    """Prueba la implementación asíncrona del método run."""
    # Parchear el método run de la clase base
    with patch.object(orchestrator_adapter, "run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"status": "success", "response": "Respuesta de prueba"}

        # Llamar al método
        result = await orchestrator_adapter._run_async_impl(
            user_input="Entrada de prueba",
            user_id="test_user",
            session_id="test_session",
        )

        # Verificar que se llamó al método run de la clase base
        mock_run.assert_called_once_with(
            "Entrada de prueba", user_id="test_user", session_id="test_session"
        )

        # Verificar el resultado
        assert result["status"] == "success"
        assert result["response"] == "Respuesta de prueba"


@pytest.mark.asyncio
async def test_register_with_a2a_server_error(mock_a2a_adapter):
    """Prueba el manejo de errores al registrar el adaptador con el servidor A2A."""
    # Configurar el mock para lanzar una excepción
    mock_a2a_adapter.register_agent.side_effect = Exception("Error de registro")

    # Llamar al método
    await orchestrator_adapter._register_with_a2a_server()

    # Verificar que se llamó a register_agent
    mock_a2a_adapter.register_agent.assert_called_once()

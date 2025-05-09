"""
Pruebas unitarias para el adaptador A2A.

Este módulo contiene pruebas para verificar el funcionamiento
del adaptador A2A que conecta el orquestador con el servidor A2A.
"""

import pytest
import pytest_asyncio
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from agents.orchestrator.a2a_adapter import A2AAdapter
from agents.orchestrator.orchestrator import Orchestrator, TaskResult
from agents.orchestrator.a2a_connector import A2AConnector
from a2a import (
    AgentNotFoundError, AgentOfflineError, 
    TaskNotFoundError, ConnectionError,
    TaskStatus, AgentStatus, MessageRole, PartType
)

# Fixture para el orquestador mock
@pytest.fixture
def mock_orchestrator():
    """Fixture que proporciona un orquestador mock."""
    orchestrator = MagicMock(spec=Orchestrator)
    orchestrator.register_agent = AsyncMock(return_value=True)
    orchestrator.route_task = AsyncMock(return_value=["agent1", "agent2"])
    orchestrator._select_best_result = AsyncMock()
    return orchestrator

# Fixture para el conector A2A mock
@pytest.fixture
def mock_connector():
    """Fixture que proporciona un conector A2A mock."""
    connector = MagicMock(spec=A2AConnector)
    connector.discover_agents = AsyncMock()
    connector.get_agent_info = AsyncMock()
    connector.request_task = AsyncMock()
    connector.get_task_status = AsyncMock()
    connector.wait_for_task_completion = AsyncMock()
    connector.execute_task = AsyncMock()
    connector.register_agent = AsyncMock()
    connector.update_agent_status = AsyncMock()
    connector.close = AsyncMock()
    return connector

# Fixture para el adaptador A2A
@pytest_asyncio.fixture
async def a2a_adapter(mock_orchestrator, mock_connector):
    """Fixture que proporciona un adaptador A2A con orquestador y conector mock."""
    adapter = A2AAdapter(orchestrator=mock_orchestrator, connector=mock_connector)
    yield adapter
    await adapter.close()

# Pruebas para el método discover_agents
@pytest.mark.asyncio
async def test_discover_agents_with_cache(a2a_adapter, mock_connector):
    """Prueba que discover_agents usa la caché cuando está disponible y no ha expirado."""
    # Configurar datos de prueba
    test_agents = [
        {"agent_id": "agent1", "name": "Agent 1"},
        {"agent_id": "agent2", "name": "Agent 2"}
    ]
    
    # Llenar la caché
    a2a_adapter.agent_cache = {
        "agent1": {"agent_id": "agent1", "name": "Agent 1"},
        "agent2": {"agent_id": "agent2", "name": "Agent 2"}
    }
    a2a_adapter.cache_timestamp = datetime.now()
    
    # Ejecutar la función
    result = await a2a_adapter.discover_agents()
    
    # Verificar que se usó la caché (no se llamó al conector)
    mock_connector.discover_agents.assert_not_called()
    assert len(result) == 2
    assert result[0]["agent_id"] in ["agent1", "agent2"]
    assert result[1]["agent_id"] in ["agent1", "agent2"]

@pytest.mark.asyncio
async def test_discover_agents_expired_cache(a2a_adapter, mock_connector):
    """Prueba que discover_agents actualiza la caché cuando ha expirado."""
    # Configurar datos de prueba
    test_agents = [
        {"agent_id": "agent1", "name": "Agent 1"},
        {"agent_id": "agent2", "name": "Agent 2"}
    ]
    mock_connector.discover_agents.return_value = test_agents
    
    # Configurar caché expirada
    a2a_adapter.agent_cache = {
        "agent0": {"agent_id": "agent0", "name": "Old Agent"}
    }
    a2a_adapter.cache_timestamp = datetime.now() - timedelta(seconds=a2a_adapter.cache_ttl + 10)
    
    # Ejecutar la función
    result = await a2a_adapter.discover_agents()
    
    # Verificar que se actualizó la caché
    mock_connector.discover_agents.assert_called_once()
    assert len(result) == 2
    assert result[0]["agent_id"] in ["agent1", "agent2"]
    assert result[1]["agent_id"] in ["agent1", "agent2"]
    assert len(a2a_adapter.agent_cache) == 2
    assert "agent1" in a2a_adapter.agent_cache
    assert "agent2" in a2a_adapter.agent_cache

@pytest.mark.asyncio
async def test_discover_agents_force_refresh(a2a_adapter, mock_connector):
    """Prueba que discover_agents actualiza la caché cuando se fuerza el refresco."""
    # Configurar datos de prueba
    test_agents = [
        {"agent_id": "agent1", "name": "Agent 1"},
        {"agent_id": "agent2", "name": "Agent 2"}
    ]
    mock_connector.discover_agents.return_value = test_agents
    
    # Configurar caché válida pero que será ignorada
    a2a_adapter.agent_cache = {
        "agent0": {"agent_id": "agent0", "name": "Old Agent"}
    }
    a2a_adapter.cache_timestamp = datetime.now()
    
    # Ejecutar la función con force_refresh=True
    result = await a2a_adapter.discover_agents(force_refresh=True)
    
    # Verificar que se actualizó la caché a pesar de no estar expirada
    mock_connector.discover_agents.assert_called_once()
    assert len(result) == 2
    assert "agent1" in a2a_adapter.agent_cache
    assert "agent2" in a2a_adapter.agent_cache

# Pruebas para el método register_agents_with_orchestrator
@pytest.mark.asyncio
async def test_register_agents_with_orchestrator(a2a_adapter, mock_orchestrator, mock_connector):
    """Prueba que register_agents_with_orchestrator registra correctamente los agentes con el orquestador."""
    # Configurar datos de prueba
    test_agents = [
        {"agent_id": "agent1", "name": "Agent 1"},
        {"agent_id": "agent2", "name": "Agent 2"}
    ]
    mock_connector.discover_agents.return_value = test_agents
    
    # Ejecutar la función
    count = await a2a_adapter.register_agents_with_orchestrator()
    
    # Verificar que se registraron los agentes
    assert count == 2
    mock_connector.discover_agents.assert_called_once()
    assert mock_orchestrator.register_agent.call_count == 2
    
    # Verificar que se llamó a register_agent con los argumentos correctos
    mock_orchestrator.register_agent.assert_any_call("agent1", test_agents[0])
    mock_orchestrator.register_agent.assert_any_call("agent2", test_agents[1])

@pytest.mark.asyncio
async def test_register_agents_with_orchestrator_partial_success(a2a_adapter, mock_orchestrator, mock_connector):
    """Prueba que register_agents_with_orchestrator maneja correctamente fallos parciales."""
    # Configurar datos de prueba
    test_agents = [
        {"agent_id": "agent1", "name": "Agent 1"},
        {"agent_id": "agent2", "name": "Agent 2"}
    ]
    mock_connector.discover_agents.return_value = test_agents
    
    # Configurar que solo el primer agente se registre correctamente
    mock_orchestrator.register_agent.side_effect = [True, False]
    
    # Ejecutar la función
    count = await a2a_adapter.register_agents_with_orchestrator()
    
    # Verificar que solo se registró un agente
    assert count == 1
    mock_connector.discover_agents.assert_called_once()
    assert mock_orchestrator.register_agent.call_count == 2

# Pruebas para el método execute_task_with_agent
@pytest.mark.asyncio
async def test_execute_task_with_agent_success(a2a_adapter, mock_connector):
    """Prueba que execute_task_with_agent ejecuta correctamente una tarea en un agente."""
    # Configurar datos de prueba
    task = {
        "requester_id": "user123",
        "task_type": "test",
        "input": "test input",
        "context": {"key": "value"}
    }
    
    # Configurar la respuesta del conector
    mock_connector.execute_task.return_value = {
        "task_id": "task123",
        "status": TaskStatus.COMPLETED,
        "messages": [
            {
                "role": MessageRole.USER,
                "parts": [{"type": PartType.TEXT, "text": "test input"}]
            },
            {
                "role": MessageRole.AGENT,
                "parts": [{"type": PartType.TEXT, "text": "test response"}]
            }
        ]
    }
    
    # Ejecutar la función
    result = await a2a_adapter.execute_task_with_agent("agent1", task)
    
    # Verificar que se llamó al conector correctamente
    mock_connector.execute_task.assert_called_once()
    call_args = mock_connector.execute_task.call_args[1]
    assert call_args["agent_id"] == "agent1"
    assert "task_data" in call_args
    assert call_args["wait_for_completion"] is True
    
    # Verificar el resultado
    assert isinstance(result, TaskResult)
    assert result.agent_id == "agent1"
    assert result.success is True
    assert result.response == "test response"
    assert result.error is None
    assert result.confidence > 0

@pytest.mark.asyncio
async def test_execute_task_with_agent_not_found(a2a_adapter, mock_connector):
    """Prueba que execute_task_with_agent maneja correctamente el error de agente no encontrado."""
    # Configurar el conector para lanzar AgentNotFoundError
    mock_connector.execute_task.side_effect = AgentNotFoundError(agent_id="agent1")
    
    # Ejecutar la función
    result = await a2a_adapter.execute_task_with_agent("agent1", {"input": "test"})
    
    # Verificar el resultado
    assert isinstance(result, TaskResult)
    assert result.agent_id == "agent1"
    assert result.success is False
    assert result.response == ""
    assert "no encontrado" in result.error
    assert result.confidence == 0.0

@pytest.mark.asyncio
async def test_execute_task_with_agent_offline(a2a_adapter, mock_connector):
    """Prueba que execute_task_with_agent maneja correctamente el error de agente offline."""
    # Configurar el conector para lanzar AgentOfflineError
    mock_connector.execute_task.side_effect = AgentOfflineError(agent_id="agent1")
    
    # Ejecutar la función
    result = await a2a_adapter.execute_task_with_agent("agent1", {"input": "test"})
    
    # Verificar el resultado
    assert isinstance(result, TaskResult)
    assert result.agent_id == "agent1"
    assert result.success is False
    assert result.response == ""
    assert "offline" in result.error
    assert result.confidence == 0.0

@pytest.mark.asyncio
async def test_execute_task_with_agent_timeout(a2a_adapter, mock_connector):
    """Prueba que execute_task_with_agent maneja correctamente el error de timeout."""
    # Configurar el conector para lanzar TimeoutError
    mock_connector.execute_task.side_effect = TimeoutError("Tiempo de espera agotado")
    
    # Ejecutar la función
    result = await a2a_adapter.execute_task_with_agent("agent1", {"input": "test"})
    
    # Verificar el resultado
    assert isinstance(result, TaskResult)
    assert result.agent_id == "agent1"
    assert result.success is False
    assert result.response == ""
    assert "Tiempo de espera agotado" in result.error
    assert result.confidence == 0.0

# Pruebas para el método execute_task
@pytest.mark.asyncio
async def test_execute_task_with_specific_agents(a2a_adapter, mock_orchestrator, mock_connector):
    """Prueba que execute_task ejecuta correctamente una tarea con agentes específicos."""
    # Configurar datos de prueba
    task = {"input": "test input"}
    target_agents = ["agent1", "agent2"]
    
    # Configurar las respuestas para execute_task_with_agent
    agent1_result = TaskResult(
        agent_id="agent1",
        success=True,
        response="response from agent1",
        error=None,
        execution_time=0.5,
        confidence=0.8
    )
    agent2_result = TaskResult(
        agent_id="agent2",
        success=True,
        response="response from agent2",
        error=None,
        execution_time=0.3,
        confidence=0.9
    )
    
    # Configurar el comportamiento del adaptador
    with patch.object(a2a_adapter, 'execute_task_with_agent') as mock_execute:
        mock_execute.side_effect = [agent1_result, agent2_result]
        
        # Configurar el orquestador para seleccionar el mejor resultado
        mock_orchestrator._select_best_result.return_value = agent2_result
        
        # Ejecutar la función
        result = await a2a_adapter.execute_task(task, target_agents=target_agents)
        
        # Verificar que se llamó a execute_task_with_agent para cada agente
        assert mock_execute.call_count == 2
        mock_execute.assert_any_call(agent_id="agent1", task=task, timeout=30.0)
        mock_execute.assert_any_call(agent_id="agent2", task=task, timeout=30.0)
        
        # Verificar que se seleccionó el mejor resultado
        mock_orchestrator._select_best_result.assert_called_once()
        
        # Verificar el resultado
        assert result["success"] is True
        assert result["response"] == "response from agent2"
        assert result["error"] is None
        assert result["agents_used"] == ["agent2"]
        assert result["confidence"] == 0.9
        assert result["execution_time"] == 0.3

@pytest.mark.asyncio
async def test_execute_task_with_routing(a2a_adapter, mock_orchestrator, mock_connector):
    """Prueba que execute_task enruta correctamente una tarea cuando no se especifican agentes."""
    # Configurar datos de prueba
    task = {"input": "test input"}
    
    # Configurar el orquestador para enrutar a agent1 y agent2
    mock_orchestrator.route_task.return_value = ["agent1", "agent2"]
    
    # Configurar las respuestas para execute_task_with_agent
    agent1_result = TaskResult(
        agent_id="agent1",
        success=True,
        response="response from agent1",
        error=None,
        execution_time=0.5,
        confidence=0.8
    )
    agent2_result = TaskResult(
        agent_id="agent2",
        success=True,
        response="response from agent2",
        error=None,
        execution_time=0.3,
        confidence=0.9
    )
    
    # Configurar el comportamiento del adaptador
    with patch.object(a2a_adapter, 'register_agents_with_orchestrator') as mock_register:
        with patch.object(a2a_adapter, 'execute_task_with_agent') as mock_execute:
            mock_register.return_value = 2
            mock_execute.side_effect = [agent1_result, agent2_result]
            
            # Configurar el orquestador para seleccionar el mejor resultado
            mock_orchestrator._select_best_result.return_value = agent2_result
            
            # Ejecutar la función
            result = await a2a_adapter.execute_task(task)
            
            # Verificar que se registraron los agentes
            mock_register.assert_called_once()
            
            # Verificar que se enrutó la tarea
            mock_orchestrator.route_task.assert_called_once_with(task)
            
            # Verificar que se llamó a execute_task_with_agent para cada agente
            assert mock_execute.call_count == 2
            
            # Verificar el resultado
            assert result["success"] is True
            assert result["response"] == "response from agent2"
            assert result["agents_used"] == ["agent2"]

@pytest.mark.asyncio
async def test_execute_task_no_agents_found(a2a_adapter, mock_orchestrator):
    """Prueba que execute_task maneja correctamente el caso de no encontrar agentes."""
    # Configurar datos de prueba
    task = {"input": "test input"}
    
    # Configurar el orquestador para no encontrar agentes
    mock_orchestrator.route_task.return_value = []
    
    # Configurar el comportamiento del adaptador
    with patch.object(a2a_adapter, 'register_agents_with_orchestrator') as mock_register:
        mock_register.return_value = 0
        
        # Ejecutar la función
        result = await a2a_adapter.execute_task(task)
        
        # Verificar que se registraron los agentes
        mock_register.assert_called_once()
        
        # Verificar que se enrutó la tarea
        mock_orchestrator.route_task.assert_called_once_with(task)
        
        # Verificar el resultado
        assert result["success"] is False
        assert "No se encontraron agentes disponibles" in result["error"]
        assert result["agents_used"] == []
        assert result["confidence"] == 0.0

@pytest.mark.asyncio
async def test_execute_task_no_valid_results(a2a_adapter, mock_orchestrator):
    """Prueba que execute_task maneja correctamente el caso de no obtener resultados válidos."""
    # Configurar datos de prueba
    task = {"input": "test input"}
    
    # Configurar el orquestador para enrutar a agent1
    mock_orchestrator.route_task.return_value = ["agent1"]
    
    # Configurar las respuestas para execute_task_with_agent
    agent1_result = TaskResult(
        agent_id="agent1",
        success=False,
        response="",
        error="Error en el agente",
        execution_time=0.5,
        confidence=0.0
    )
    
    # Configurar el comportamiento del adaptador
    with patch.object(a2a_adapter, 'register_agents_with_orchestrator') as mock_register:
        with patch.object(a2a_adapter, 'execute_task_with_agent') as mock_execute:
            mock_register.return_value = 1
            mock_execute.return_value = agent1_result
            
            # Configurar el orquestador para no seleccionar ningún resultado
            mock_orchestrator._select_best_result.return_value = None
            
            # Ejecutar la función
            result = await a2a_adapter.execute_task(task)
            
            # Verificar el resultado
            assert result["success"] is False
            assert "No se pudo obtener un resultado válido" in result["error"]
            assert result["agents_used"] == []
            assert result["confidence"] == 0.0

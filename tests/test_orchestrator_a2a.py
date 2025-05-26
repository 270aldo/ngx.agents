"""
Pruebas unitarias para la integración del orquestador con A2A.

Este módulo contiene pruebas para verificar la integración
del orquestador con el adaptador A2A.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from agents.orchestrator.agent import NGXNexusOrchestrator
from agents.orchestrator.a2a_adapter import A2AAdapter
from a2a import AgentStatus


# Fixture para el orquestador
@pytest.fixture
def orchestrator():
    """Fixture que proporciona un orquestador con configuración predeterminada."""
    mock_mcp_toolkit = MagicMock()
    return NGXNexusOrchestrator(mcp_toolkit=mock_mcp_toolkit)


# Fixture para el adaptador A2A mock
@pytest.fixture
def mock_a2a_adapter():
    """Fixture que proporciona un adaptador A2A mock."""
    adapter = MagicMock(spec=A2AAdapter)
    adapter.register_agents_with_orchestrator = AsyncMock(return_value=2)
    adapter.execute_task = AsyncMock()
    return adapter


# Pruebas para el método get_a2a_adapter
@pytest.mark.asyncio
async def test_get_a2a_adapter(orchestrator):
    """Prueba que get_a2a_adapter inicializa y devuelve el adaptador A2A."""
    # Usar patch para evitar la creación real del adaptador
    with patch("agents.orchestrator.a2a_adapter.A2AAdapter") as mock_adapter_class:
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        # Ejecutar la función
        adapter = await orchestrator.get_a2a_adapter()

        # Verificar que se creó el adaptador
        mock_adapter_class.assert_called_once_with(orchestrator=orchestrator)
        assert adapter == mock_adapter

        # Verificar que se almacenó la instancia
        assert orchestrator._a2a_adapter == mock_adapter

        # Llamar de nuevo para verificar que se reutiliza la instancia
        adapter2 = await orchestrator.get_a2a_adapter()
        assert adapter2 == adapter
        assert mock_adapter_class.call_count == 1  # No se debe crear otra instancia


@pytest.mark.asyncio
async def test_get_a2a_adapter_disabled(orchestrator):
    """Prueba que get_a2a_adapter no inicializa el adaptador cuando A2A está deshabilitado."""
    # Deshabilitar A2A
    orchestrator.config.use_a2a = False

    # Usar patch para verificar que no se crea el adaptador
    with patch("agents.orchestrator.a2a_adapter.A2AAdapter") as mock_adapter_class:
        # Ejecutar la función
        adapter = await orchestrator.get_a2a_adapter()

        # Verificar que no se creó el adaptador
        mock_adapter_class.assert_not_called()
        assert adapter is None
        assert orchestrator._a2a_adapter is None


# Pruebas para el método refresh_agents
@pytest.mark.asyncio
async def test_refresh_agents(orchestrator, mock_a2a_adapter):
    """Prueba que refresh_agents actualiza correctamente la lista de agentes desde A2A."""
    # Configurar el orquestador para usar el adaptador mock
    with patch.object(orchestrator, "get_a2a_adapter", return_value=mock_a2a_adapter):
        # Ejecutar la función
        count = await orchestrator.refresh_agents()

        # Verificar que se llamó al adaptador
        mock_a2a_adapter.register_agents_with_orchestrator.assert_called_once()
        assert count == 2


@pytest.mark.asyncio
async def test_refresh_agents_disabled(orchestrator):
    """Prueba que refresh_agents no hace nada cuando A2A está deshabilitado."""
    # Deshabilitar A2A
    orchestrator.config.use_a2a = False

    # Ejecutar la función
    count = await orchestrator.refresh_agents()

    # Verificar que no se actualizaron agentes
    assert count == 0


@pytest.mark.asyncio
async def test_refresh_agents_error(orchestrator):
    """Prueba que refresh_agents maneja correctamente los errores."""
    # Configurar el adaptador para lanzar una excepción
    mock_adapter = AsyncMock()
    mock_adapter.register_agents_with_orchestrator.side_effect = Exception(
        "Error de prueba"
    )

    # Configurar el orquestador para usar el adaptador mock
    with patch.object(orchestrator, "get_a2a_adapter", return_value=mock_adapter):
        # Ejecutar la función
        count = await orchestrator.refresh_agents()

        # Verificar que se manejó el error
        assert count == 0


# Pruebas para el método execute_task
@pytest.mark.asyncio
async def test_execute_task(orchestrator, mock_a2a_adapter):
    """Prueba que execute_task ejecuta correctamente una tarea a través del adaptador A2A."""
    # Configurar la respuesta del adaptador para _execute_with_agents
    agent_result = MagicMock()
    agent_result.success = True
    agent_result.response = "Respuesta de prueba"
    agent_result.error = None
    agent_result.agent_id = "agent1"
    agent_result.confidence = 0.9
    agent_result.execution_time = 0.5
    agent_result.dict = MagicMock(
        return_value={
            "success": True,
            "response": "Respuesta de prueba",
            "error": None,
            "agent_id": "agent1",
            "confidence": 0.9,
            "execution_time": 0.5,
        }
    )

    # Configurar el orquestador para usar el adaptador mock y devolver agentes
    with (
        patch.object(orchestrator, "route_task", return_value=["agent1"]),
        patch.object(
            orchestrator, "_execute_with_agents", return_value={"agent1": agent_result}
        ),
        patch.object(orchestrator, "_select_best_result", return_value=agent_result),
    ):

        # Ejecutar la función
        task = {"task_type": "test", "input": "prueba"}
        result = await orchestrator.execute_task(task)

        # Verificar el resultado
        assert result["success"] is True
        assert result["response"] == "Respuesta de prueba"
        assert result["error"] is None
        assert result["agents_used"] == ["agent1"]
        assert result["confidence"] == 0.9
        assert result["execution_time"] == 0.5


@pytest.mark.asyncio
async def test_execute_task_with_target_agents(orchestrator, mock_a2a_adapter):
    """Prueba que execute_task ejecuta correctamente una tarea con agentes específicos."""
    # Configurar la respuesta del adaptador para _execute_with_agents
    agent_result = MagicMock()
    agent_result.success = True
    agent_result.response = "Respuesta de prueba"
    agent_result.error = None
    agent_result.agent_id = "agent1"
    agent_result.confidence = 0.9
    agent_result.execution_time = 0.5
    agent_result.dict = MagicMock(
        return_value={
            "success": True,
            "response": "Respuesta de prueba",
            "error": None,
            "agent_id": "agent1",
            "confidence": 0.9,
            "execution_time": 0.5,
        }
    )

    # Configurar el orquestador para usar el adaptador mock y devolver agentes
    with (
        patch.object(
            orchestrator, "_execute_with_agents", return_value={"agent1": agent_result}
        ),
        patch.object(orchestrator, "_select_best_result", return_value=agent_result),
    ):

        # Ejecutar la función con agentes específicos
        task = {"task_type": "test", "input": "prueba"}
        target_agents = ["agent1"]
        result = await orchestrator.execute_task(task, target_agents=target_agents)

        # Verificar el resultado
        assert result["success"] is True
        assert result["response"] == "Respuesta de prueba"
        assert result["error"] is None
        assert result["agents_used"] == ["agent1"]
        assert result["confidence"] == 0.9
        assert result["execution_time"] == 0.5

        # Verificar que se registró en el historial de tareas
        task_id = next(iter(orchestrator.task_history))
        assert orchestrator.task_history[task_id]["target_agents"] == target_agents


# Nota: Se eliminó la prueba test_execute_task_with_custom_timeout ya que el método execute_task no acepta un parámetro timeout


@pytest.mark.asyncio
async def test_execute_task_a2a_disabled(orchestrator):
    """Prueba que execute_task devuelve un error cuando A2A está deshabilitado."""
    # Deshabilitar A2A
    orchestrator.config.use_a2a = False

    # Configurar el orquestrador para simular que no hay agentes disponibles
    with patch.object(orchestrator, "route_task", return_value=[]):
        # Ejecutar la función
        task = {"task_type": "test", "input": "prueba"}
        result = await orchestrator.execute_task(task)

        # Verificar el resultado
        assert result["success"] is False
        assert "No se encontraron agentes disponibles" in result["error"]
    assert result["agents_used"] == []
    assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_execute_task_error(orchestrator, mock_a2a_adapter):
    """Prueba que execute_task maneja correctamente los errores."""
    # Configurar el método _execute_with_agents para que devuelva un diccionario vacío
    # Esto simulará que no se obtuvieron resultados válidos
    with (
        patch.object(orchestrator, "route_task", return_value=["agent1"]),
        patch.object(orchestrator, "_execute_with_agents", return_value={}),
        patch.object(orchestrator, "_select_best_result", return_value=None),
    ):

        # Ejecutar la función
        task = {"task_type": "test", "input": "prueba"}
        result = await orchestrator.execute_task(task)

        # Verificar que se manejó el error
        assert result["success"] is False
        assert (
            "No se pudo obtener un resultado válido de ningún agente" in result["error"]
        )
        assert result["agents_used"] == []
        assert result["confidence"] == 0.0


# Pruebas para el método route_task
@pytest.mark.asyncio
async def test_route_task_by_skills(orchestrator):
    """Prueba que route_task enruta correctamente una tarea por habilidades."""
    # Registrar agentes de prueba
    agent1 = {
        "agent_id": "agent1",
        "name": "Agent 1",
        "status": AgentStatus.ONLINE,
        "capabilities": ["test"],
        "skills": ["skill1", "skill2"],
    }
    agent2 = {
        "agent_id": "agent2",
        "name": "Agent 2",
        "status": AgentStatus.ONLINE,
        "capabilities": ["other"],
        "skills": ["skill3"],
    }
    agent3 = {
        "agent_id": "agent3",
        "name": "Agent 3",
        "status": AgentStatus.OFFLINE,
        "capabilities": ["test"],
        "skills": ["skill1", "skill2"],
    }

    await orchestrator.register_agent("agent1", agent1)
    await orchestrator.register_agent("agent2", agent2)
    await orchestrator.register_agent("agent3", agent3)

    # Ejecutar la función con una tarea que requiere skill1
    task = {"task_type": "test", "required_skills": ["skill1"], "data": {}}
    result = await orchestrator.route_task(task)

    # Verificar que se seleccionó el agente correcto
    assert "agent1" in result
    assert "agent2" not in result
    assert "agent3" not in result  # Offline


@pytest.mark.asyncio
async def test_route_task_no_agents(orchestrator):
    """Prueba que route_task maneja correctamente el caso de no encontrar agentes."""
    # Ejecutar la función sin agentes registrados
    task = {"task_type": "test", "required_skills": ["skill1"], "data": {}}
    result = await orchestrator.route_task(task)

    # Verificar que no se encontraron agentes
    assert result == []


@pytest.mark.asyncio
async def test_route_task_with_fallback(orchestrator):
    """Prueba que route_task utiliza el agente de respaldo cuando es necesario."""
    # Configurar agente de respaldo
    orchestrator.config.enable_fallback = True
    orchestrator.config.fallback_agent_id = "fallback_agent"

    # Registrar agente de respaldo
    fallback_agent = {
        "agent_id": "fallback_agent",
        "name": "Fallback Agent",
        "status": AgentStatus.ONLINE,
        "capabilities": ["fallback"],
        "skills": [],
    }
    await orchestrator.register_agent("fallback_agent", fallback_agent)

    # Ejecutar la función con una tarea que no coincide con ningún agente
    task = {"task_type": "unknown", "required_skills": ["unknown_skill"], "data": {}}
    result = await orchestrator.route_task(task)

    # Verificar que se seleccionó el agente de respaldo
    assert result == ["fallback_agent"]


# Pruebas para el método _select_best_result
@pytest.mark.asyncio
async def test_select_best_result(orchestrator):
    """Prueba que _select_best_result selecciona correctamente el mejor resultado."""
    # Crear resultados de prueba
    results = {
        "agent1": TaskResult(
            agent_id="agent1",
            success=True,
            response="Respuesta de agent1",
            error=None,
            execution_time=0.5,
            confidence=0.7,
        ),
        "agent2": TaskResult(
            agent_id="agent2",
            success=True,
            response="Respuesta de agent2",
            error=None,
            execution_time=0.3,
            confidence=0.9,
        ),
        "agent3": TaskResult(
            agent_id="agent3",
            success=False,
            response="",
            error="Error en agent3",
            execution_time=0.4,
            confidence=0.1,
        ),
    }

    # Ejecutar la función
    best_result = await orchestrator._select_best_result(results)

    # Verificar que se seleccionó el resultado con mayor confianza
    assert best_result.agent_id == "agent2"
    assert best_result.confidence == 0.9


@pytest.mark.asyncio
async def test_select_best_result_no_valid_results(orchestrator):
    """Prueba que _select_best_result maneja correctamente el caso de no tener resultados válidos."""
    # Crear resultados de prueba con confianza por debajo del umbral
    results = {
        "agent1": TaskResult(
            agent_id="agent1",
            success=True,
            response="Respuesta de agent1",
            error=None,
            execution_time=0.5,
            confidence=0.7,
        ),
        "agent2": TaskResult(
            agent_id="agent2",
            success=False,
            response="",
            error="Error en agent2",
            execution_time=0.3,
            confidence=0.1,
        ),
    }

    # Ejecutar la función
    best_result = await orchestrator._select_best_result(results)

    # Verificar que se seleccionó el resultado con mayor confianza aunque esté por debajo del umbral
    assert best_result.agent_id == "agent1"
    assert best_result.confidence == 0.7


@pytest.mark.asyncio
async def test_select_best_result_empty(orchestrator):
    """Prueba que _select_best_result devuelve None cuando no hay resultados."""
    # Ejecutar la función con un diccionario vacío
    best_result = await orchestrator._select_best_result({})

    # Verificar que se devolvió None
    assert best_result is None


@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    """Testea que el Orchestrator se inicializa correctamente."""
    assert orchestrator is not None
    assert isinstance(orchestrator, NGXNexusOrchestrator)

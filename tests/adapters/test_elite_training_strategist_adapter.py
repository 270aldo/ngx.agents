"""
Pruebas para el adaptador del agente EliteTrainingStrategist.

Este módulo contiene pruebas unitarias para verificar el correcto funcionamiento
del adaptador del agente EliteTrainingStrategist con los componentes optimizados.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from infrastructure.adapters.elite_training_strategist_adapter import (
    EliteTrainingStrategistAdapter,
)
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter


# Fixtures
@pytest.fixture
def elite_training_strategist_adapter():
    """Fixture que proporciona una instancia del adaptador EliteTrainingStrategist."""
    # Crear mocks para las dependencias
    gemini_client_mock = AsyncMock()
    gemini_client_mock.generate_response = AsyncMock(return_value="Respuesta simulada")
    gemini_client_mock.generate_structured_output = AsyncMock(
        return_value={
            "plan_name": "Plan de Entrenamiento de Fuerza",
            "program_type": "STRENGTH",
            "duration_weeks": 8,
            "description": "Plan de entrenamiento enfocado en fuerza",
            "phases": [
                {
                    "phase_name": "Fase de Adaptación",
                    "duration_weeks": 2,
                    "description": "Fase inicial para adaptación",
                }
            ],
        }
    )

    supabase_client_mock = MagicMock()
    supabase_client_mock.get_user_profile = MagicMock(
        return_value={
            "age": 30,
            "gender": "masculino",
            "experience_level": "intermedio",
            "goals": ["fuerza", "hipertrofia"],
        }
    )

    mcp_toolkit_mock = MagicMock()

    # Crear instancia del adaptador con mocks
    adapter = EliteTrainingStrategistAdapter(
        agent_id="test_elite_training_strategist",
        gemini_client=gemini_client_mock,
        supabase_client=supabase_client_mock,
        mcp_toolkit=mcp_toolkit_mock,
    )

    return adapter


# Pruebas
@pytest.mark.asyncio
async def test_get_context(elite_training_strategist_adapter):
    """Prueba el método _get_context del adaptador."""
    # Mock para state_manager_adapter.load_state
    with patch.object(
        state_manager_adapter, "load_state", new_callable=AsyncMock
    ) as mock_load_state:
        # Configurar el mock para devolver un contexto de prueba
        mock_load_state.return_value = {
            "conversation_history": [
                {
                    "role": "user",
                    "content": "Necesito un plan de entrenamiento para aumentar mi fuerza",
                }
            ],
            "user_profile": {"age": 30, "gender": "masculino"},
            "training_plans": [],
            "performance_data": {},
            "last_updated": datetime.now().isoformat(),
        }

        # Llamar al método a probar
        context = await elite_training_strategist_adapter._get_context(
            "test_user", "test_session"
        )

        # Verificar que se llamó al método load_state del adaptador
        mock_load_state.assert_called_once_with("test_user", "test_session")

        # Verificar que el contexto devuelto es el esperado
        assert "conversation_history" in context
        assert "user_profile" in context
        assert "training_plans" in context
        assert context["user_profile"]["age"] == 30


@pytest.mark.asyncio
async def test_update_context(elite_training_strategist_adapter):
    """Prueba el método _update_context del adaptador."""
    # Mock para state_manager_adapter.save_state
    with patch.object(
        state_manager_adapter, "save_state", new_callable=AsyncMock
    ) as mock_save_state:
        # Crear un contexto de prueba
        test_context = {
            "conversation_history": [
                {
                    "role": "user",
                    "content": "Necesito un plan de entrenamiento para aumentar mi fuerza",
                },
                {
                    "role": "assistant",
                    "content": "Aquí tienes un plan de entrenamiento...",
                },
            ],
            "user_profile": {"age": 30, "gender": "masculino"},
            "training_plans": [
                {
                    "plan_name": "Plan de Fuerza",
                    "program_type": "STRENGTH",
                    "duration_weeks": 8,
                }
            ],
            "performance_data": {},
            "last_updated": datetime.now().isoformat(),
        }

        # Llamar al método a probar
        await elite_training_strategist_adapter._update_context(
            test_context, "test_user", "test_session"
        )

        # Verificar que se llamó al método save_state del adaptador
        mock_save_state.assert_called_once()

        # Verificar que se pasaron los argumentos correctos
        args, kwargs = mock_save_state.call_args
        assert args[0] == "test_user"
        assert args[1] == "test_session"
        assert "conversation_history" in args[2]
        assert "training_plans" in args[2]
        assert "last_updated" in args[2]


@pytest.mark.asyncio
async def test_classify_query(elite_training_strategist_adapter):
    """Prueba el método _classify_query del adaptador."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(
        intent_analyzer_adapter, "analyze_intent", new_callable=AsyncMock
    ) as mock_analyze_intent:
        # Configurar el mock para devolver un análisis de intención
        mock_analyze_intent.return_value = {
            "primary_intent": "training_plan",
            "confidence": 0.85,
            "entities": [
                {"type": "goal", "value": "fuerza"},
                {"type": "duration", "value": "8 semanas"},
            ],
        }

        # Llamar al método a probar
        query_type = await elite_training_strategist_adapter._classify_query(
            "Necesito un plan de entrenamiento para aumentar mi fuerza en 8 semanas"
        )

        # Verificar que se llamó al método analyze_intent del adaptador
        mock_analyze_intent.assert_called_once()

        # Verificar que el tipo de consulta devuelto es el esperado
        assert query_type == "generate_training_plan"


@pytest.mark.asyncio
async def test_consult_other_agent(elite_training_strategist_adapter):
    """Prueba el método _consult_other_agent del adaptador."""
    # Mock para a2a_adapter.call_agent
    with patch.object(
        a2a_adapter, "call_agent", new_callable=AsyncMock
    ) as mock_call_agent:
        # Configurar el mock para devolver una respuesta simulada
        mock_call_agent.return_value = {
            "status": "success",
            "output": "Respuesta del agente consultado",
            "agent_id": "test_agent",
            "agent_name": "Test Agent",
        }

        # Llamar al método a probar
        response = await elite_training_strategist_adapter._consult_other_agent(
            agent_id="test_agent",
            query="¿Qué suplementos recomiendas para mejorar la recuperación muscular?",
            user_id="test_user",
            session_id="test_session",
        )

        # Verificar que se llamó al método call_agent del adaptador
        mock_call_agent.assert_called_once()

        # Verificar que la respuesta devuelta es la esperada
        assert response["status"] == "success"
        assert "Respuesta del agente consultado" in response["output"]
        assert response["agent_id"] == "test_agent"


@pytest.mark.asyncio
async def test_skill_generate_training_plan(elite_training_strategist_adapter):
    """Prueba el método _skill_generate_training_plan del adaptador."""
    # Importar la clase de entrada para la skill
    from agents.elite_training_strategist.schemas import GenerateTrainingPlanInput

    # Crear datos de entrada para la skill
    input_data = GenerateTrainingPlanInput(
        user_query="Necesito un plan de entrenamiento para aumentar mi fuerza",
        user_profile={
            "age": 30,
            "gender": "masculino",
            "experience_level": "intermedio",
            "goals": ["fuerza", "hipertrofia"],
        },
        duration_weeks=8,
        focus_areas=["piernas", "espalda", "pecho"],
    )

    # Llamar al método a probar
    result = await elite_training_strategist_adapter._skill_generate_training_plan(
        input_data
    )

    # Verificar que el resultado tiene la estructura esperada
    assert hasattr(result, "plan_name")
    assert hasattr(result, "program_type")
    assert hasattr(result, "duration_weeks")
    assert hasattr(result, "description")

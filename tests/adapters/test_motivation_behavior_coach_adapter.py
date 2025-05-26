"""
Pruebas para el adaptador del agente MotivationBehaviorCoach.

Este módulo contiene pruebas unitarias para verificar el correcto funcionamiento
del adaptador del agente MotivationBehaviorCoach con los componentes optimizados.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from infrastructure.adapters.motivation_behavior_coach_adapter import (
    MotivationBehaviorCoachAdapter,
)
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter


# Fixtures
@pytest.fixture
def motivation_behavior_coach_adapter():
    """Fixture que proporciona una instancia del adaptador MotivationBehaviorCoach."""
    # Crear mocks para las dependencias
    gemini_client_mock = AsyncMock()
    gemini_client_mock.generate_response = AsyncMock(return_value="Respuesta simulada")
    gemini_client_mock.generate_structured_output = AsyncMock(
        return_value={
            "habit": "Ejercicio diario",
            "cue": "Después de despertarse",
            "routine": "15 minutos de ejercicio",
            "reward": "Desayuno saludable",
            "implementation_intention": "Cuando me despierte, haré 15 minutos de ejercicio",
            "steps": [
                {
                    "description": "Comenzar con 5 minutos",
                    "timeframe": "Semana 1",
                    "difficulty": "Baja",
                },
                {
                    "description": "Aumentar a 10 minutos",
                    "timeframe": "Semana 2",
                    "difficulty": "Media",
                },
                {
                    "description": "Llegar a 15 minutos",
                    "timeframe": "Semana 3",
                    "difficulty": "Media",
                },
            ],
            "tips": ["Comenzar pequeño", "Ser consistente", "Celebrar logros"],
        }
    )

    supabase_client_mock = MagicMock()

    mcp_toolkit_mock = MagicMock()

    # Crear instancia del adaptador con mocks
    adapter = MotivationBehaviorCoachAdapter(
        agent_id="test_motivation_coach",
        gemini_client=gemini_client_mock,
        supabase_client=supabase_client_mock,
        mcp_toolkit=mcp_toolkit_mock,
    )

    return adapter


# Pruebas
@pytest.mark.asyncio
async def test_get_context(motivation_behavior_coach_adapter):
    """Prueba el método _get_context del adaptador."""
    # Mock para state_manager_adapter.load_state
    with patch.object(
        state_manager_adapter, "load_state", new_callable=AsyncMock
    ) as mock_load_state:
        # Configurar el mock para devolver un contexto de prueba
        mock_load_state.return_value = {
            "conversation_history": [
                {"role": "user", "content": "Quiero establecer un hábito de ejercicio"}
            ],
            "user_profile": {"goals": ["Mejorar salud", "Aumentar energía"]},
            "habit_plans": [{"habit": "Meditación", "cue": "Antes de dormir"}],
            "goal_plans": [{"goal": "Correr 5km", "timeline": "3 meses"}],
            "last_updated": datetime.now().isoformat(),
        }

        # Llamar al método a probar
        context = await motivation_behavior_coach_adapter._get_context(
            "test_user", "test_session"
        )

        # Verificar que se llamó al método load_state del adaptador
        mock_load_state.assert_called_once_with("test_user", "test_session")

        # Verificar que el contexto devuelto es el esperado
        assert "conversation_history" in context
        assert "user_profile" in context
        assert "habit_plans" in context
        assert "goal_plans" in context
        assert len(context["habit_plans"]) == 1
        assert context["habit_plans"][0]["habit"] == "Meditación"


@pytest.mark.asyncio
async def test_update_context(motivation_behavior_coach_adapter):
    """Prueba el método _update_context del adaptador."""
    # Mock para state_manager_adapter.save_state
    with patch.object(
        state_manager_adapter, "save_state", new_callable=AsyncMock
    ) as mock_save_state:
        # Crear un contexto de prueba
        test_context = {
            "conversation_history": [
                {"role": "user", "content": "Quiero establecer un hábito de ejercicio"},
                {
                    "role": "assistant",
                    "content": "Aquí tienes un plan para establecer ese hábito...",
                },
            ],
            "user_profile": {"goals": ["Mejorar salud", "Aumentar energía"]},
            "habit_plans": [
                {
                    "habit": "Ejercicio diario",
                    "cue": "Después de despertarse",
                    "routine": "15 minutos de ejercicio",
                }
            ],
            "goal_plans": [],
            "last_updated": datetime.now().isoformat(),
        }

        # Llamar al método a probar
        await motivation_behavior_coach_adapter._update_context(
            test_context, "test_user", "test_session"
        )

        # Verificar que se llamó al método save_state del adaptador
        mock_save_state.assert_called_once()

        # Verificar que se pasaron los argumentos correctos
        args, kwargs = mock_save_state.call_args
        assert args[0] == "test_user"
        assert args[1] == "test_session"
        assert "conversation_history" in args[2]
        assert "user_profile" in args[2]
        assert "habit_plans" in args[2]
        assert "last_updated" in args[2]


@pytest.mark.asyncio
async def test_classify_query(motivation_behavior_coach_adapter):
    """Prueba el método _classify_query del adaptador."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(
        intent_analyzer_adapter, "analyze_intent", new_callable=AsyncMock
    ) as mock_analyze_intent:
        # Configurar el mock para devolver un análisis de intención
        mock_analyze_intent.return_value = {
            "primary_intent": "habit",
            "confidence": 0.85,
            "entities": [
                {"type": "habit_type", "value": "ejercicio"},
                {"type": "frequency", "value": "diario"},
            ],
        }

        # Llamar al método a probar
        query_type = await motivation_behavior_coach_adapter._classify_query(
            "Quiero establecer un hábito de ejercicio diario"
        )

        # Verificar que se llamó al método analyze_intent del adaptador
        mock_analyze_intent.assert_called_once()

        # Verificar que el tipo de consulta devuelto es el esperado
        assert query_type == "habit_formation"


@pytest.mark.asyncio
async def test_classify_query_by_keywords(motivation_behavior_coach_adapter):
    """Prueba el método _classify_query_by_keywords del adaptador."""
    # Probar diferentes tipos de consultas
    assert (
        motivation_behavior_coach_adapter._classify_query_by_keywords(
            "Quiero establecer un hábito de meditación"
        )
        == "habit_formation"
    )
    assert (
        motivation_behavior_coach_adapter._classify_query_by_keywords(
            "Necesito motivación para seguir con mi dieta"
        )
        == "motivation_strategies"
    )
    assert (
        motivation_behavior_coach_adapter._classify_query_by_keywords(
            "Cómo puedo cambiar mi comportamiento de procrastinación"
        )
        == "behavior_change"
    )
    assert (
        motivation_behavior_coach_adapter._classify_query_by_keywords(
            "Quiero establecer una meta de correr un maratón"
        )
        == "goal_setting"
    )
    assert (
        motivation_behavior_coach_adapter._classify_query_by_keywords(
            "Cómo superar el obstáculo de la falta de tiempo"
        )
        == "obstacle_management"
    )

    # Probar consulta sin palabras clave específicas
    assert (
        motivation_behavior_coach_adapter._classify_query_by_keywords(
            "Ayúdame con mi entrenamiento"
        )
        == "motivation_strategies"
    )


@pytest.mark.asyncio
async def test_consult_other_agent(motivation_behavior_coach_adapter):
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
        response = await motivation_behavior_coach_adapter._consult_other_agent(
            agent_id="test_agent",
            query="¿Qué ejercicios recomiendas para principiantes?",
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
async def test_skill_habit_formation(motivation_behavior_coach_adapter):
    """Prueba el método _skill_habit_formation del adaptador."""
    # Importar la clase de entrada para la skill
    from agents.motivation_behavior_coach.schemas import HabitFormationInput

    # Mock para _generate_habit_plan
    with patch.object(
        motivation_behavior_coach_adapter,
        "_generate_habit_plan",
        new_callable=AsyncMock,
    ) as mock_generate_habit_plan:
        # Configurar el mock para devolver datos simulados
        mock_generate_habit_plan.return_value = {
            "habit": "Ejercicio diario",
            "cue": "Después de despertarse",
            "routine": "15 minutos de ejercicio",
            "reward": "Desayuno saludable",
            "implementation_intention": "Cuando me despierte, haré 15 minutos de ejercicio",
            "steps": [
                {
                    "description": "Comenzar con 5 minutos",
                    "timeframe": "Semana 1",
                    "difficulty": "Baja",
                },
                {
                    "description": "Aumentar a 10 minutos",
                    "timeframe": "Semana 2",
                    "difficulty": "Media",
                },
                {
                    "description": "Llegar a 15 minutos",
                    "timeframe": "Semana 3",
                    "difficulty": "Media",
                },
            ],
            "tips": ["Comenzar pequeño", "Ser consistente", "Celebrar logros"],
            "obstacles": [
                {
                    "obstacle": "Falta de tiempo",
                    "strategy": "Levantarse 15 minutos antes",
                }
            ],
            "consistency_strategies": [
                "Usar recordatorios",
                "Preparar ropa de ejercicio la noche anterior",
            ],
        }

        # Crear datos de entrada para la skill
        input_data = HabitFormationInput(
            user_input="Quiero establecer un hábito de ejercicio diario por la mañana",
            user_profile={"goals": ["Mejorar salud", "Aumentar energía"]},
        )

        # Llamar al método a probar
        result = await motivation_behavior_coach_adapter._skill_habit_formation(
            input_data
        )

        # Verificar que se llamó al método _generate_habit_plan
        mock_generate_habit_plan.assert_called_once()

        # Verificar que el resultado tiene la estructura esperada
        assert hasattr(result, "habit_plan")
        assert hasattr(result, "tips")
        assert hasattr(result, "obstacles")
        assert hasattr(result, "consistency_strategies")
        assert result.habit_plan.habit_name == "Ejercicio diario"
        assert len(result.tips) == 3
        assert len(result.obstacles) == 1

"""
Pruebas para el adaptador del agente PrecisionNutritionArchitect.

Este módulo contiene pruebas unitarias para verificar el correcto funcionamiento
del adaptador del agente PrecisionNutritionArchitect con los componentes optimizados.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime

from infrastructure.adapters.precision_nutrition_architect_adapter import (
    PrecisionNutritionArchitectAdapter,
)
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter


# Fixtures
@pytest.fixture
def precision_nutrition_architect_adapter():
    """Fixture que proporciona una instancia del adaptador PrecisionNutritionArchitect."""
    # Crear mocks para las dependencias
    gemini_client_mock = AsyncMock()
    gemini_client_mock.generate_response = AsyncMock(return_value="Respuesta simulada")
    gemini_client_mock.generate_text = AsyncMock(
        return_value=json.dumps(
            {
                "objective": "Plan nutricional personalizado",
                "macronutrients": {
                    "protein": "25-30%",
                    "carbs": "40-50%",
                    "fats": "20-30%",
                },
                "calories": "2000-2200 kcal",
                "meals": [
                    {"name": "Desayuno", "examples": ["Avena con frutas y nueces"]},
                    {"name": "Almuerzo", "examples": ["Ensalada con proteína magra"]},
                ],
                "recommended_foods": ["Vegetales de hoja verde", "Proteínas magras"],
                "foods_to_avoid": ["Alimentos ultraprocesados", "Azúcares refinados"],
            }
        )
    )

    supabase_client_mock = MagicMock()
    supabase_client_mock.get_user_profile = MagicMock(
        return_value={
            "age": 30,
            "gender": "masculino",
            "dietary_restrictions": "sin gluten",
            "goals": ["pérdida de peso", "salud general"],
        }
    )

    mcp_toolkit_mock = MagicMock()

    # Crear instancia del adaptador con mocks
    adapter = PrecisionNutritionArchitectAdapter(
        agent_id="test_precision_nutrition_architect",
        gemini_client=gemini_client_mock,
        supabase_client=supabase_client_mock,
        mcp_toolkit=mcp_toolkit_mock,
    )

    return adapter


# Pruebas
@pytest.mark.asyncio
async def test_get_context(precision_nutrition_architect_adapter):
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
                    "content": "Necesito un plan de alimentación para bajar de peso",
                }
            ],
            "user_profile": {
                "age": 30,
                "gender": "masculino",
                "dietary_restrictions": "sin gluten",
            },
            "meal_plans": [],
            "supplement_recommendations": [],
            "biomarker_analyses": [],
            "last_updated": datetime.now().isoformat(),
        }

        # Llamar al método a probar
        context = await precision_nutrition_architect_adapter._get_context(
            "test_user", "test_session"
        )

        # Verificar que se llamó al método load_state del adaptador
        mock_load_state.assert_called_once_with("test_user", "test_session")

        # Verificar que el contexto devuelto es el esperado
        assert "conversation_history" in context
        assert "user_profile" in context
        assert "meal_plans" in context
        assert "supplement_recommendations" in context
        assert "biomarker_analyses" in context
        assert context["user_profile"]["age"] == 30


@pytest.mark.asyncio
async def test_update_context(precision_nutrition_architect_adapter):
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
                    "content": "Necesito un plan de alimentación para bajar de peso",
                },
                {
                    "role": "assistant",
                    "content": "Aquí tienes un plan de alimentación...",
                },
            ],
            "user_profile": {
                "age": 30,
                "gender": "masculino",
                "dietary_restrictions": "sin gluten",
            },
            "meal_plans": [
                {
                    "daily_plan": [
                        {
                            "name": "Desayuno",
                            "time": "8:00 AM",
                            "items": [{"name": "Avena con frutas y nueces"}],
                        }
                    ],
                    "total_calories": "2000-2200 kcal",
                    "macronutrient_distribution": {
                        "protein": "25-30%",
                        "carbs": "40-50%",
                        "fats": "20-30%",
                    },
                }
            ],
            "supplement_recommendations": [],
            "biomarker_analyses": [],
            "last_updated": datetime.now().isoformat(),
        }

        # Llamar al método a probar
        await precision_nutrition_architect_adapter._update_context(
            test_context, "test_user", "test_session"
        )

        # Verificar que se llamó al método save_state del adaptador
        mock_save_state.assert_called_once()

        # Verificar que se pasaron los argumentos correctos
        args, kwargs = mock_save_state.call_args
        assert args[0] == "test_user"
        assert args[1] == "test_session"
        assert "conversation_history" in args[2]
        assert "meal_plans" in args[2]
        assert "last_updated" in args[2]


@pytest.mark.asyncio
async def test_classify_query(precision_nutrition_architect_adapter):
    """Prueba el método _classify_query del adaptador."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(
        intent_analyzer_adapter, "analyze_intent", new_callable=AsyncMock
    ) as mock_analyze_intent:
        # Configurar el mock para devolver un análisis de intención
        mock_analyze_intent.return_value = {
            "primary_intent": "meal_plan",
            "confidence": 0.85,
            "entities": [
                {"type": "goal", "value": "pérdida de peso"},
                {"type": "restriction", "value": "sin gluten"},
            ],
        }

        # Llamar al método a probar
        query_type = await precision_nutrition_architect_adapter._classify_query(
            "Necesito un plan de alimentación para bajar de peso que sea sin gluten"
        )

        # Verificar que se llamó al método analyze_intent del adaptador
        mock_analyze_intent.assert_called_once()

        # Verificar que el tipo de consulta devuelto es el esperado
        assert query_type == "create_meal_plan"


@pytest.mark.asyncio
async def test_consult_other_agent(precision_nutrition_architect_adapter):
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
        response = await precision_nutrition_architect_adapter._consult_other_agent(
            agent_id="test_agent",
            query="¿Qué ejercicios recomiendas para complementar esta dieta?",
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
async def test_skill_create_meal_plan(precision_nutrition_architect_adapter):
    """Prueba el método _skill_create_meal_plan del adaptador."""
    # Importar la clase de entrada para la skill
    from agents.precision_nutrition_architect.schemas import CreateMealPlanInput

    # Crear datos de entrada para la skill
    input_data = CreateMealPlanInput(
        user_input="Necesito un plan de alimentación para bajar de peso que sea sin gluten",
        user_profile={
            "age": 30,
            "gender": "masculino",
            "dietary_restrictions": "sin gluten",
            "goals": ["pérdida de peso", "salud general"],
        },
    )

    # Llamar al método a probar
    result = await precision_nutrition_architect_adapter._skill_create_meal_plan(
        input_data
    )

    # Verificar que el resultado tiene la estructura esperada
    assert hasattr(result, "daily_plan")
    assert hasattr(result, "total_calories")
    assert hasattr(result, "macronutrient_distribution")
    assert hasattr(result, "recommendations")

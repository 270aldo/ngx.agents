import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agents.precision_nutrition_architect.agent import PrecisionNutritionArchitect
from agents.precision_nutrition_architect.schemas import (
    CreateMealPlanInput,
    CreateMealPlanOutput,
    RecommendSupplementsInput,
    RecommendSupplementsOutput,
    AnalyzeBiomarkersInput,
    AnalyzeBiomarkersOutput,
    PlanChrononutritionInput,
    PlanChrononutritionOutput,
)


@pytest.fixture
def mocked_agent():
    """Fixture para crear un agente PrecisionNutritionArchitect con dependencias mockeadas."""
    # Mock de GeminiClient
    gemini_client = MagicMock()

    # Mock de StateManager
    state_manager = MagicMock()
    state_manager.load_state = AsyncMock(return_value={})
    state_manager.save_state = AsyncMock()

    # Crear el agente con los mocks
    agent = PrecisionNutritionArchitect(
        gemini_client=gemini_client, state_manager=state_manager
    )

    return agent


@pytest.mark.asyncio
async def test_skill_create_meal_plan(mocked_agent):
    """Test para verificar que la skill create_meal_plan funciona correctamente."""
    # Mock para _generate_meal_plan
    mock_meal_plan = {
        "meals": [
            {
                "name": "Desayuno",
                "description": "Tostadas de aguacate con huevos",
                "macros": {"proteinas": "20g", "carbohidratos": "30g", "grasas": "15g"},
            }
        ],
        "daily_macros": {"protein": "120g", "carbs": "200g", "fat": "60g"},
        "total_calories": 2000,
        "notes": "Plan personalizado",
    }

    # Patch del método _generate_meal_plan
    with patch.object(
        mocked_agent, "_generate_meal_plan", new_callable=AsyncMock
    ) as mock_generate:
        mock_generate.return_value = mock_meal_plan

        # Crear los parámetros de entrada
        input_params = CreateMealPlanInput(
            input_text="Necesito un plan de comidas para ganar masa muscular",
            user_profile={
                "age": 30,
                "weight": 75,
                "height": 180,
                "activity_level": "high",
            },
            goals=["muscle_gain"],
            dietary_restrictions=["no_dairy"],
        )

        # Ejecutar la skill
        result = await mocked_agent._skill_create_meal_plan(input_params)

        # Verificar que el resultado es del tipo correcto
        assert isinstance(result, CreateMealPlanOutput)

        # Verificar que los datos están presentes en el resultado
        assert result.daily_plan is not None
        assert len(result.daily_plan) > 0


@pytest.mark.asyncio
async def test_skill_recommend_supplements(mocked_agent):
    """Test para verificar que la skill recommend_supplements funciona correctamente."""
    # Mock para _generate_supplement_recommendation
    mock_supplements = {
        "recommended_supplements": [
            {
                "name": "Vitamina D",
                "dosage": "2000 UI",
                "timing": "Con el desayuno",
                "purpose": "Mejorar niveles de vitamina D",
            }
        ],
        "general_recommendations": "Mantener una dieta equilibrada",
        "notes": "Suplementos recomendados basados en necesidades específicas",
    }

    # Patch del método _generate_supplement_recommendation
    with patch.object(
        mocked_agent, "_generate_supplement_recommendation", new_callable=AsyncMock
    ) as mock_generate:
        mock_generate.return_value = mock_supplements

        # Crear los parámetros de entrada
        input_params = RecommendSupplementsInput(
            input_text="Necesito recomendaciones de suplementos para mejorar mi rendimiento",
            user_profile={
                "age": 40,
                "sex": "male",
                "health_conditions": ["hipertensión"],
            },
            biomarkers={"vitamin_d": 20, "iron": 80},
            goals=["mejorar rendimiento"],
        )

        # Ejecutar la skill
        result = await mocked_agent._skill_recommend_supplements(input_params)

        # Verificar que el resultado es del tipo correcto
        assert isinstance(result, RecommendSupplementsOutput)

        # Verificar que los datos están presentes en el resultado
        assert result.supplements is not None


@pytest.mark.asyncio
async def test_skill_analyze_biomarkers(mocked_agent):
    """Test para verificar que la skill analyze_biomarkers funciona correctamente."""
    # Mock para _generate_biomarker_analysis
    mock_analysis = {
        "analysis_summary": "Análisis de biomarcadores",
        "key_findings": [
            {
                "parameter": "Glucosa",
                "value": "110 mg/dL",
                "interpretation": "Elevado",
                "recommendation": "Reducir azúcares",
            }
        ],
        "overall_recommendations": ["Aumentar actividad física"],
        "lifestyle_suggestions": ["Ejercicio regular"],
    }

    # Patch del método _generate_biomarker_analysis
    with patch.object(
        mocked_agent, "_generate_biomarker_analysis", new_callable=AsyncMock
    ) as mock_generate:
        mock_generate.return_value = mock_analysis

        # Crear los parámetros de entrada
        input_params = AnalyzeBiomarkersInput(
            input_text="Necesito un análisis de mis biomarcadores",
            biomarkers={
                "glucose": 110,
                "cholesterol": {"total": 190, "hdl": 45, "ldl": 120},
                "vitamin_d": 25,
            },
            user_profile={"age": 35, "sex": "male"},
        )

        # Ejecutar la skill
        result = await mocked_agent._skill_analyze_biomarkers(input_params)

        # Verificar que el resultado es del tipo correcto
        assert isinstance(result, AnalyzeBiomarkersOutput)

        # Verificar que los datos están presentes en el resultado
        assert result.analyses is not None
        assert len(result.analyses) > 0
        assert result.overall_assessment is not None
        assert result.nutritional_priorities is not None


@pytest.mark.asyncio
async def test_skill_plan_chrononutrition(mocked_agent):
    """Test para verificar que la skill plan_chrononutrition funciona correctamente."""
    # Mock para _generate_chrononutrition_plan
    mock_plan = {
        "time_windows": [
            {
                "name": "Alimentación",
                "start_time": "07:00",
                "end_time": "08:00",
                "description": "Desayuno rico en proteínas",
                "nutritional_focus": [
                    "Proteínas de alta calidad",
                    "Carbohidratos complejos",
                ],
            }
        ],
        "fasting_period": "16:00-08:00",
        "eating_period": "08:00-16:00",
        "general_recommendations": "Consumir carbohidratos antes del ejercicio",
    }

    # Patch del método _generate_chrononutrition_plan
    with patch.object(
        mocked_agent, "_generate_chrononutrition_plan", new_callable=AsyncMock
    ) as mock_generate:
        mock_generate.return_value = mock_plan

        # Crear los parámetros de entrada
        input_params = PlanChrononutritionInput(
            input_text="Necesito un plan de crononutrición para optimizar mi rendimiento",
            user_profile={
                "age": 35,
                "weight": 70,
                "height": 175,
                "activity_level": "moderate",
            },
            sleep_pattern={"wake_time": "06:00", "sleep_time": "22:00"},
            training_schedule={"monday": {"time": "18:00", "type": "Fuerza"}},
        )

        # Ejecutar la skill
        result = await mocked_agent._skill_plan_chrononutrition(input_params)

        # Verificar que el resultado es del tipo correcto
        assert isinstance(result, PlanChrononutritionOutput)

        # Verificar que los datos están presentes en el resultado
        assert result.time_windows is not None
        assert len(result.time_windows) > 0
        assert result.fasting_period is not None
        assert result.eating_period is not None

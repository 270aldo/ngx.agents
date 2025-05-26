import pytest
from unittest.mock import MagicMock, AsyncMock

from agents.elite_training_strategist.agent import EliteTrainingStrategist
from agents.elite_training_strategist.schemas import (
    GenerateTrainingPlanInput,
    GenerateTrainingPlanOutput,
)
from core.logging_config import get_logger


# Fixture para crear una instancia del agente con mocks
logger = get_logger(__name__)


@pytest.fixture
def mocked_agent():
    # Mockear dependencias externas
    mock_gemini_client = MagicMock()
    # Mockear generate_structured_output como AsyncMock y que devuelva una estructura esperada
    # por GenerateTrainingPlanOutputSchema
    mock_gemini_client.generate_structured_output = AsyncMock(
        return_value={
            "plan_name": "Mocked Plan Name",
            "program_type": "PRIME",  # Coincidir con program_type_request para las aserciones del artifact
            "duration_weeks": 12,  # Coincidir con duration_weeks_input
            "description": "Mocked plan description from Gemini.",
            "phases": [
                {
                    "phase_name": "Fase Preparatoria",
                    "duration_weeks": 2,
                    "description": "Acondicionamiento general.",
                    "sessions_per_week": 3,
                    "focus": "Resistencia base",
                }
            ],
            "response": "Generated Plan Mock Text from Gemini Structured Output",  # Este es el texto principal
            "artifacts": [],  # Lógica interna crea el artifact, el LLM no lo devuelve así.
        }
    )
    # Mantener el mock de generate_content por si se usa en otro lado, aunque la skill usa generate_structured_output
    mock_gemini_client.generate_content = AsyncMock(
        return_value="Unused mock text for generate_content"
    )

    mock_mcp_toolkit = MagicMock()
    # Simular respuesta de Supabase (perfil de cliente)
    # NOTA: En la skill generate_training_plan, no se usa mcp_toolkit directamente,
    # sino que la información del perfil se obtiene a través de _get_context.
    # Así que este mock de invoke no es estrictamente necesario para esta skill,
    # pero lo dejamos como ejemplo para otras skills.
    mock_mcp_toolkit.invoke = AsyncMock(
        return_value=[
            {
                "program_type": "PRIME",
                "goals": "Perder peso, ganar fuerza",
                "experience_level": "Intermedio",
                # ... otros campos del perfil
            }
        ]
    )

    # Crear instancia del agente
    # Necesitamos proporcionar los argumentos mínimos para __init__
    # Es posible que ADKAgent o BaseAgent requieran más argumentos.
    # Si la inicialización falla, necesitaremos ajustar esto.
    try:
        agent = EliteTrainingStrategist(
            # , mcp_toolkit=mock_mcp_toolkit # Si __init__ lo acepta
        )
    except TypeError as e:
        # Si faltan argumentos posicionales, capturarlo aquí
        pytest.fail(
            f"Error al inicializar EliteTrainingStrategist: {e}. Revisa los argumentos requeridos por BaseAgent/ADKAgent."
        )
        return None  # Para satisfacer al linter

    # Sobrescribir los clientes con mocks después de la inicialización
    agent.gemini_client = mock_gemini_client
    # agent.mcp_toolkit = mock_mcp_toolkit # Eliminar esta línea, mcp_toolkit no es un campo válido

    # Mockear métodos de contexto para aislar la skill
    agent._get_context = AsyncMock(
        return_value={
            "client_profile": {
                "program_type": "PRIME",
                "goals": "Perder peso, ganar fuerza",
                "experience_level": "Intermedio",
                "current_metrics": "Peso: 85kg, % Grasa: 20%",
                "preferences": "Entrenar 3 veces por semana",
                "injury_history": "Ninguna",
            },
            "history": [
                # Ejemplo de entrada histórica
                # {"input": {"text": "..."}, "output": {"response": "..."}, "skill_used": "..."}
            ],
        }
    )
    agent._update_context = AsyncMock()

    return agent


@pytest.mark.asyncio
async def test_skill_generate_training_plan(mocked_agent):
    """Prueba la skill _skill_generate_training_plan."""
    agent = mocked_agent

    # Datos de entrada para la skill
    user_id = "test_user_123"  # Se usa para _get_context y _update_context
    user_goals = "Quiero correr un maratón en 6 meses y mejorar mi fuerza general."
    constraints = "Solo puedo entrenar Lunes, Miércoles y Viernes por la mañana."
    program_type_request = (
        "PRIME"  # Se usa para aserciones, no es input directo a la skill ahora
    )
    session_id = "test_session_abc"  # Se usa para _get_context y _update_context
    duration_weeks_input = 12

    # Preparar el input Pydantic para la skill
    plan_input = GenerateTrainingPlanInput(
        goals=[user_goals],
        preferences={"constraints": constraints},  # Incluir constraints en preferences
        duration_weeks=duration_weeks_input,
        # training_history podría añadirse si es necesario para la prueba
    )

    # Ejecutar la skill
    result = await agent._skill_generate_training_plan(params=plan_input)

    # Aserciones
    assert isinstance(result, GenerateTrainingPlanOutput)
    assert result.response == "Generated Plan Mock Text from Gemini Structured Output"

    # Verificar artefactos
    assert result.artifacts is not None
    assert len(result.artifacts) == 1

    # Verificar llamadas a mocks
    # La skill _skill_generate_training_plan llama a _generate_training_plan_logic,
    # y _generate_training_plan_logic llama a gemini_client.generate_content.
    # El mock de _get_context se usa indirectamente por _generate_training_plan_logic.

    # Si gemini_client.generate_content fue llamado, significa que la lógica interna de la skill se ejecutó.
    agent.gemini_client.generate_structured_output.assert_called_once()
    call_args, call_kwargs = agent.gemini_client.generate_structured_output.call_args
    prompt = call_args[0]
    assert isinstance(prompt, str)
    assert user_goals in prompt
    # assert constraints in prompt # Constraints ahora está en preferences, el prompt puede variar
    assert (
        program_type_request in prompt
    )  # program_type_request se obtiene del contexto y se usa en el prompt

    # Verificar que el artefacto tiene la estructura correcta
    # result.artifacts[0] es un diccionario, no un objeto TrainingPlanArtifact
    assert "data" in result.artifacts[0]
    assert "content" in result.artifacts[0]["data"]
    assert (
        result.artifacts[0]["data"]["content"]
        == "Generated Plan Mock Text from Gemini Structured Output"
    )
    assert result.artifacts[0]["content_type"] == "text/markdown"
    assert "Plan de Entrenamiento (PRIME)" in result.artifacts[0]["label"]

    logger.info(
        f"\nResultado de la prueba test_skill_generate_training_plan: {result.model_dump_json(indent=2)}"
    )

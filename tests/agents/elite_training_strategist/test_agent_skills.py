import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from agents.elite_training_strategist.agent import EliteTrainingStrategist

# Fixture para crear una instancia del agente con mocks
@pytest.fixture
def mocked_agent():
    # Mockear dependencias externas
    mock_gemini_client = MagicMock()
    mock_gemini_client.generate_content = AsyncMock(return_value="Generated Plan Mock Text")
    
    mock_mcp_toolkit = MagicMock()
    # Simular respuesta de Supabase (perfil de cliente)
    # NOTA: En la skill generate_training_plan, no se usa mcp_toolkit directamente,
    # sino que la información del perfil se obtiene a través de _get_context.
    # Así que este mock de invoke no es estrictamente necesario para esta skill,
    # pero lo dejamos como ejemplo para otras skills.
    mock_mcp_toolkit.invoke = AsyncMock(return_value=[
        {
            "program_type": "PRIME",
            "goals": "Perder peso, ganar fuerza",
            "experience_level": "Intermedio",
            # ... otros campos del perfil
        }
    ])
    
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
        pytest.fail(f"Error al inicializar EliteTrainingStrategist: {e}. Revisa los argumentos requeridos por BaseAgent/ADKAgent.")
        return None # Para satisfacer al linter

    # Sobrescribir los clientes con mocks después de la inicialización
    agent.gemini_client = mock_gemini_client
    # agent.mcp_toolkit = mock_mcp_toolkit # Eliminar esta línea, mcp_toolkit no es un campo válido
    
    # Mockear métodos de contexto para aislar la skill
    agent._get_context = AsyncMock(return_value={
        "client_profile": {
            "program_type": "PRIME", 
            "goals": "Perder peso, ganar fuerza", 
            "experience_level": "Intermedio",
            "current_metrics": "Peso: 85kg, % Grasa: 20%",
            "preferences": "Entrenar 3 veces por semana",
            "injury_history": "Ninguna"
        },
        "history": [
             # Ejemplo de entrada histórica
            # {"input": {"text": "..."}, "output": {"response": "..."}, "skill_used": "..."}
        ]
    })
    agent._update_context = AsyncMock()
    
    return agent

@pytest.mark.asyncio
async def test_skill_generate_training_plan(mocked_agent):
    """Prueba la skill _skill_generate_training_plan."""
    agent = mocked_agent
    
    # Datos de entrada para la skill
    user_id = "test_user_123"
    user_goals = "Quiero correr un maratón en 6 meses y mejorar mi fuerza general."
    constraints = "Solo puedo entrenar Lunes, Miércoles y Viernes por la mañana."
    program_type_request = "PRIME" 
    session_id = "test_session_abc"

    # Ejecutar la skill
    result = await agent._skill_generate_training_plan(
        user_id=user_id,
        goals=[user_goals], 
        weeks=12, 
        constraints=constraints,
        session_id=session_id
    )

    # Aserciones
    assert isinstance(result, dict)
    assert "response" in result
    assert "artifacts" in result
    assert isinstance(result["response"], str)
    assert result["response"] == "Generated Plan Mock Text"
    assert isinstance(result["artifacts"], list)
    # Verificar si se creó el artefacto esperado
    assert len(result["artifacts"]) == 1
    assert result["artifacts"][0]["type"] == "markdown"
    assert result["artifacts"][0]["label"] == f"Plan de Entrenamiento ({program_type_request.upper()}) - 12 Semanas"
    assert result["artifacts"][0]["content"] == "Generated Plan Mock Text"

    # Verificar llamadas a mocks
    agent.gemini_client.generate_content.assert_called_once()
    call_args, call_kwargs = agent.gemini_client.generate_content.call_args
    prompt = call_args[0]
    assert isinstance(prompt, str)
    assert user_goals in prompt
    assert constraints in prompt
    assert program_type_request in prompt

    # Verificar que el contexto fue actualizado
    agent._get_context.assert_called_once_with(user_id, session_id)
    agent._update_context.assert_called_once()
    update_args, update_kwargs = agent._update_context.call_args
    assert update_args[0] == user_id
    assert update_args[1] == session_id
    assert update_args[2]["skill_used"] == "generate_training_plan"
    assert update_args[2]["input"]["goals"] == [user_goals]
    assert update_args[2]["output"]["response"] == "Generated Plan Mock Text"

    print(f"\nResultado de la prueba test_skill_generate_training_plan: {result}")

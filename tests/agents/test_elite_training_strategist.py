"""
Pruebas unitarias para el agente EliteTrainingStrategist.

Este módulo contiene pruebas para verificar el funcionamiento
del agente EliteTrainingStrategist.
"""

import pytest
from unittest.mock import patch

from agents.elite_training_strategist import EliteTrainingStrategist


# Mock para GeminiClient
class MockGeminiClient:
    async def generate_response(self, user_input, context=None, temperature=0.7):
        return f"Respuesta simulada para: {user_input}"

    async def generate_structured_output(self, prompt):
        return {
            "objective": "Plan de entrenamiento personalizado",
            "duration": "4-6 semanas",
            "frequency": "3-4 días por semana",
            "sessions": [
                {
                    "name": "Sesión de ejemplo",
                    "exercises": [
                        {
                            "name": "Ejemplo de ejercicio",
                            "sets": 3,
                            "reps": "8-12",
                            "rest": "60-90 segundos",
                        }
                    ],
                }
            ],
        }


# Mock para SupabaseClient
class MockSupabaseClient:
    def get_user_profile(self, user_id):
        return {
            "name": "Usuario de prueba",
            "age": 30,
            "experience_level": "intermedio",
            "goals": "Ganar masa muscular",
            "limitations": "Ninguna",
        }

    def log_conversation_message(self, user_id, role, message):
        return True


# Mock para MCPToolkit y MCPClient
class MockMCPToolkit:
    pass


class MockMCPClient:
    pass


@pytest.fixture
def mock_dependencies():
    """Fixture para simular las dependencias del agente."""
    with (
        patch(
            "agents.elite_training_strategist.GeminiClient",
            return_value=MockGeminiClient(),
        ),
        patch(
            "agents.elite_training_strategist.SupabaseClient",
            return_value=MockSupabaseClient(),
        ),
        patch(
            "agents.elite_training_strategist.MCPToolkit", return_value=MockMCPToolkit()
        ),
        patch(
            "agents.elite_training_strategist.MCPClient", return_value=MockMCPClient()
        ),
    ):
        yield


@pytest.mark.asyncio
async def test_elite_training_strategist_initialization():
    """Prueba la inicialización del agente EliteTrainingStrategist."""
    agent = EliteTrainingStrategist()

    # Verificar atributos básicos
    assert agent.agent_id == "elite_training_strategist"
    assert agent.name == "Elite Training Strategist"
    assert "elite_training" in agent.capabilities
    assert "training_plan_design" in agent.capabilities
    assert len(agent.skills) > 0


@pytest.mark.asyncio
async def test_run_method_success(mock_dependencies):
    """Prueba que el método run() funciona correctamente."""
    agent = EliteTrainingStrategist()

    # Inicializar manualmente las dependencias
    agent.gemini_client = MockGeminiClient()
    agent.supabase_client = MockSupabaseClient()
    agent.mcp_toolkit = MockMCPToolkit()
    agent.mcp_client = MockMCPClient()

    # Ejecutar el método run
    result = await agent.run(
        "Necesito un plan de entrenamiento para ganar masa muscular", "test_user_123"
    )

    # Verificar el resultado
    assert result["status"] == "success"
    assert "Respuesta simulada para:" in result["response"]
    assert result["error"] is None
    assert result["confidence"] > 0
    assert result["agent_id"] == "elite_training_strategist"
    assert "elite_training" in result["metadata"]["capabilities_used"]


@pytest.mark.asyncio
async def test_run_method_with_error(mock_dependencies):
    """Prueba que el método run() maneja correctamente los errores."""
    agent = EliteTrainingStrategist()

    # Inicializar manualmente las dependencias
    agent.gemini_client = MockGeminiClient()
    agent.supabase_client = MockSupabaseClient()
    agent.mcp_toolkit = MockMCPToolkit()
    agent.mcp_client = MockMCPClient()

    # Simular un error en generate_response
    with patch.object(
        MockGeminiClient, "generate_response", side_effect=Exception("Error simulado")
    ):
        # Ejecutar el método run
        result = await agent.run("Necesito un plan de entrenamiento", "test_user_123")

        # Verificar el resultado
        assert result["status"] == "error"
        assert "Error simulado" in result["error"]
        assert result["confidence"] == 0.0
        assert result["agent_id"] == "elite_training_strategist"


@pytest.mark.asyncio
async def test_generate_training_plan(mock_dependencies):
    """Prueba la generación de un plan de entrenamiento."""
    agent = EliteTrainingStrategist()

    # Inicializar manualmente las dependencias
    agent.gemini_client = MockGeminiClient()
    agent.supabase_client = MockSupabaseClient()
    agent.mcp_toolkit = MockMCPToolkit()
    agent.mcp_client = MockMCPClient()

    # Ejecutar el método _generate_training_plan
    result = await agent._generate_training_plan(
        "Necesito un plan de entrenamiento", None
    )

    # Verificar el resultado
    assert "objective" in result
    assert "duration" in result
    assert "frequency" in result
    assert "sessions" in result
    assert len(result["sessions"]) > 0


@pytest.mark.asyncio
async def test_prepare_context(mock_dependencies):
    """Prueba la preparación del contexto para la generación de respuesta."""
    agent = EliteTrainingStrategist()

    # Inicializar manualmente las dependencias
    agent.gemini_client = MockGeminiClient()
    agent.supabase_client = MockSupabaseClient()
    agent.mcp_toolkit = MockMCPToolkit()
    agent.mcp_client = MockMCPClient()

    # Ejecutar el método _prepare_context
    context = agent._prepare_context(
        "Necesito un plan de entrenamiento",
        {"name": "Usuario de prueba", "age": 30},
        {"additional_info": "Información adicional"},
    )

    # Verificar el contexto
    assert "Usuario de prueba" in context
    assert "30" in context
    assert "Información adicional" in context

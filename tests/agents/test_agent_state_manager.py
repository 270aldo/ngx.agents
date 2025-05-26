"""
Pruebas para la integración del StateManager en los agentes.

Este módulo contiene pruebas para verificar que los agentes
utilizan correctamente el StateManager para persistir y recuperar
el estado de las conversaciones.
"""

import uuid
import pytest
from typing import Dict, Any

from agents.orchestrator.agent import NGXNexusOrchestrator
from agents.progress_tracker.agent import ProgressTracker
from agents.elite_training_strategist.agent import EliteTrainingStrategist
from agents.precision_nutrition_architect.agent import PrecisionNutritionArchitect
from agents.biohacking_innovator.agent import BiohackingInnovator
from agents.biometrics_insight_engine.agent import BiometricsInsightEngine
from agents.client_success_liaison.agent import ClientSuccessLiaison
from agents.recovery_corrective.agent import RecoveryCorrective
from agents.security_compliance_guardian.agent import SecurityComplianceGuardian
from agents.systems_integration_ops.agent import SystemsIntegrationOps
from agents.gemini_training_assistant.agent import GeminiTrainingAssistant
from agents.motivation_behavior_coach.agent import MotivationBehaviorCoach


@pytest.fixture
def orchestrator():
    """Fixture para crear una instancia del agente Orchestrator."""
    return NGXNexusOrchestrator()


@pytest.fixture
def progress_tracker():
    """Fixture para crear una instancia del agente ProgressTracker."""
    return ProgressTracker()


@pytest.fixture
def elite_training_strategist():
    """Fixture para crear una instancia del agente EliteTrainingStrategist."""
    return EliteTrainingStrategist()


@pytest.fixture
def precision_nutrition_architect():
    """Fixture para crear una instancia del agente PrecisionNutritionArchitect."""
    return PrecisionNutritionArchitect()


@pytest.fixture
def biohacking_innovator():
    """Fixture para crear una instancia del agente BiohackingInnovator."""
    return BiohackingInnovator()


@pytest.fixture
def biometrics_insight_engine():
    """Fixture para crear una instancia del agente BiometricsInsightEngine."""
    return BiometricsInsightEngine()


@pytest.fixture
def client_success_liaison():
    """Fixture para crear una instancia del agente ClientSuccessLiaison."""
    return ClientSuccessLiaison()


@pytest.fixture
def recovery_corrective():
    """Fixture para crear una instancia del agente RecoveryCorrective."""
    return RecoveryCorrective()


@pytest.fixture
def security_compliance_guardian():
    """Fixture para crear una instancia del agente SecurityComplianceGuardian."""
    return SecurityComplianceGuardian()


@pytest.fixture
def systems_integration_ops():
    """Fixture para crear una instancia del agente SystemsIntegrationOps."""
    return SystemsIntegrationOps()


@pytest.fixture
def gemini_training_assistant():
    """Fixture para crear una instancia del agente GeminiTrainingAssistant."""
    return GeminiTrainingAssistant()


@pytest.fixture
def motivation_behavior_coach():
    """Fixture para crear una instancia del agente MotivationBehaviorCoach."""
    return MotivationBehaviorCoach()


@pytest.mark.asyncio
async def test_orchestrator_state_manager(orchestrator, test_settings: Dict[str, Any]):
    """Prueba la integración del StateManager en el agente Orchestrator."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "Hola, ¿cómo puedes ayudarme con mi entrenamiento?"

    # Ejecutar el agente
    await orchestrator._run_async_impl(input_text, user_id, session_id)

    # Verificar que se guardó el contexto
    context = await orchestrator._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_progress_tracker_state_manager(
    progress_tracker, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente ProgressTracker."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "Quiero ver mi progreso en el último mes"

    # Ejecutar el agente
    await progress_tracker._run_async_impl(input_text, user_id, session_id)

    # Verificar que se guardó el contexto
    context = await progress_tracker._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_elite_training_strategist_state_manager(
    elite_training_strategist, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente EliteTrainingStrategist."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "Necesito un plan de entrenamiento para maratón"

    # Ejecutar el agente
    await elite_training_strategist._run_async_impl(input_text, user_id, session_id)

    # Verificar que se guardó el contexto
    context = await elite_training_strategist._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_precision_nutrition_architect_state_manager(
    precision_nutrition_architect, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente PrecisionNutritionArchitect."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "Quiero un plan de nutrición para ganar masa muscular"

    # Ejecutar el agente
    await precision_nutrition_architect._run_async_impl(input_text, user_id, session_id)

    # Verificar que se guardó el contexto
    context = await precision_nutrition_architect._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_biohacking_innovator_state_manager(
    biohacking_innovator, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente BiohackingInnovator."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "¿Qué técnicas de biohacking recomiendas para mejorar el sueño?"

    # Ejecutar el agente
    await biohacking_innovator.run(input_text, user_id, session_id=session_id)

    # Verificar que se guardó el contexto
    context = await biohacking_innovator._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_biometrics_insight_engine_state_manager(
    biometrics_insight_engine, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente BiometricsInsightEngine."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "¿Qué significan mis niveles de cortisol?"

    # Ejecutar el agente
    await biometrics_insight_engine.run(input_text, user_id, session_id=session_id)

    # Verificar que se guardó el contexto
    context = await biometrics_insight_engine._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_client_success_liaison_state_manager(
    client_success_liaison, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente ClientSuccessLiaison."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "¿Cómo puedo mejorar la retención de clientes?"

    # Ejecutar el agente
    await client_success_liaison._run_async_impl(
        input_text, user_id, session_id=session_id
    )

    # Verificar que se guardó el contexto
    context = await client_success_liaison._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_recovery_corrective_state_manager(
    recovery_corrective, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente RecoveryCorrective."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "Tengo dolor en la rodilla después de correr"

    # Ejecutar el agente
    await recovery_corrective._run_async_impl(
        input_text, user_id, session_id=session_id
    )

    # Verificar que se guardó el contexto
    context = await recovery_corrective._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_security_compliance_guardian_state_manager(
    security_compliance_guardian, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente SecurityComplianceGuardian."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = (
        "¿Qué medidas de seguridad debo implementar para proteger datos de salud?"
    )

    # Ejecutar el agente
    await security_compliance_guardian._run_async_impl(
        input_text, user_id, session_id=session_id
    )

    # Verificar que se guardó el contexto
    context = await security_compliance_guardian._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_systems_integration_ops_state_manager(
    systems_integration_ops, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente SystemsIntegrationOps."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "¿Cómo puedo integrar mi sistema con una API externa?"

    # Ejecutar el agente
    await systems_integration_ops.run(input_text, user_id, session_id=session_id)

    # Verificar que se guardó el contexto
    context = await systems_integration_ops._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_gemini_training_assistant_state_manager(
    gemini_training_assistant, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente GeminiTrainingAssistant."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "Necesito un plan de entrenamiento para principiantes"

    # Ejecutar el agente
    await gemini_training_assistant._run_async_impl(
        input_text, user_id, session_id=session_id
    )

    # Verificar que se guardó el contexto
    context = await gemini_training_assistant._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_motivation_behavior_coach_state_manager(
    motivation_behavior_coach, test_settings: Dict[str, Any]
):
    """Prueba la integración del StateManager en el agente MotivationBehaviorCoach."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    input_text = "¿Cómo puedo mantenerme motivado para hacer ejercicio?"

    # Ejecutar el agente
    await motivation_behavior_coach._run_async_impl(
        input_text, user_id, session_id=session_id
    )

    # Verificar que se guardó el contexto
    context = await motivation_behavior_coach._get_context(user_id, session_id)

    # Verificar que el contexto contiene los campos esperados
    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0
    assert context["conversation_history"][-1]["user"] == input_text


@pytest.mark.asyncio
async def test_context_persistence_across_sessions(
    orchestrator, test_settings: Dict[str, Any]
):
    """Prueba que el contexto se mantiene entre sesiones."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())

    # Primera interacción
    input_text1 = "Hola, me llamo Juan"
    await orchestrator._run_async_impl(input_text1, user_id, session_id)

    # Segunda interacción
    input_text2 = "¿Recuerdas mi nombre?"
    await orchestrator._run_async_impl(input_text2, user_id, session_id)

    # Verificar que el contexto contiene ambas interacciones
    context = await orchestrator._get_context(user_id, session_id)

    assert len(context["conversation_history"]) >= 2
    assert context["conversation_history"][0]["user"] == input_text1
    assert context["conversation_history"][1]["user"] == input_text2


@pytest.mark.asyncio
async def test_context_sharing_between_agents(
    orchestrator, elite_training_strategist, test_settings: Dict[str, Any]
):
    """Prueba que el contexto se comparte entre agentes."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())

    # Interacción con el primer agente
    input_text1 = "Quiero un plan de entrenamiento para maratón"
    await orchestrator._run_async_impl(input_text1, user_id, session_id)

    # Interacción con el segundo agente usando el mismo session_id
    input_text2 = "¿Qué ejercicios específicos recomiendas?"
    await elite_training_strategist._run_async_impl(input_text2, user_id, session_id)

    # Verificar que el contexto del segundo agente contiene información
    context = await elite_training_strategist._get_context(user_id, session_id)

    assert "conversation_history" in context
    assert len(context["conversation_history"]) > 0

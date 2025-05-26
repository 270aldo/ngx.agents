"""
Pruebas de integración del sistema completo.

Este módulo contiene pruebas end-to-end que verifican la integración de todos los componentes
del sistema NGX Agents optimizado, incluyendo la comunicación entre agentes.
"""

import pytest
import uuid
import time
from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.a2a_optimized import a2a_server

from infrastructure.adapters.motivation_behavior_coach_adapter import (
    MotivationBehaviorCoachAdapter,
)
from infrastructure.adapters.recovery_corrective_adapter import (
    RecoveryCorrectiveAdapter,
)
from infrastructure.adapters.client_success_liaison_adapter import (
    ClientSuccessLiaisonAdapter,
)
from infrastructure.adapters.security_compliance_guardian_adapter import (
    SecurityComplianceGuardianAdapter,
)
from infrastructure.adapters.systems_integration_ops_adapter import (
    SystemsIntegrationOpsAdapter,
)

from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)


@pytest.fixture
async def setup_a2a_server():
    """Fixture para inicializar y configurar el servidor A2A."""
    # Iniciar servidor A2A
    await a2a_server.start()

    # Limpiar registros de agentes existentes
    a2a_server.agents = {}
    a2a_server.message_queues = {}

    yield a2a_server

    # Detener servidor después de las pruebas
    await a2a_server.stop()


@pytest.fixture
def mock_vertex_ai_client():
    """Fixture para simular el cliente de Vertex AI."""
    with patch("clients.vertex_ai_client.vertex_ai_client") as mock:
        # Configurar respuestas simuladas
        mock.generate_content = AsyncMock(
            return_value={
                "text": "Respuesta simulada de Vertex AI",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            }
        )

        mock.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])

        mock.generate_multimodal_content = AsyncMock(
            return_value={
                "text": "Respuesta multimodal simulada",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 150,
                    "completion_tokens": 75,
                    "total_tokens": 225,
                },
            }
        )

        yield mock


@pytest.fixture
def mock_state_manager_adapter():
    """Fixture para simular el adaptador del StateManager."""
    with patch("core.state_manager_adapter.state_manager_adapter") as mock:
        # Configurar respuestas simuladas
        mock.load_state = AsyncMock(
            return_value={
                "conversation_history": [],
                "user_profile": {
                    "name": "Usuario de prueba",
                    "preferences": ["Fitness", "Nutrición"],
                },
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        mock.save_state = AsyncMock(return_value=None)

        yield mock


@pytest.fixture
def mock_intent_analyzer_adapter():
    """Fixture para simular el adaptador del IntentAnalyzer."""
    with patch("core.intent_analyzer_adapter.intent_analyzer_adapter") as mock:
        # Configurar respuestas simuladas
        mock.classify_intent = AsyncMock(
            return_value={
                "primary_intent": "fitness_goal",
                "confidence": 0.85,
                "entities": [
                    {"type": "exercise", "value": "correr", "confidence": 0.9}
                ],
                "sentiment": "positive",
            }
        )

        mock.analyze_intent = AsyncMock(
            return_value={
                "intent": "fitness_goal",
                "confidence": 0.85,
                "entities": [
                    {"type": "exercise", "value": "correr", "confidence": 0.9}
                ],
            }
        )

        yield mock


@pytest.fixture
def mock_gemini_client():
    """Fixture para simular el cliente Gemini."""
    mock = MagicMock()
    mock.generate_response = AsyncMock(
        return_value="Respuesta simulada del modelo Gemini"
    )
    mock.generate_structured_output = AsyncMock(
        return_value={"result": "Resultado estructurado simulado", "confidence": 0.9}
    )

    return mock


@pytest.fixture
def mock_supabase_client():
    """Fixture para simular el cliente Supabase."""
    mock = MagicMock()
    mock.get_user_data = MagicMock(return_value=None)
    return mock


@pytest.fixture
async def setup_agents(mock_gemini_client, mock_supabase_client, setup_a2a_server):
    """Fixture para configurar los agentes con adaptadores."""
    # Crear instancias de los agentes con adaptadores
    motivation_coach = MotivationBehaviorCoachAdapter(
        gemini_client=mock_gemini_client, supabase_client=mock_supabase_client
    )

    recovery_corrective = RecoveryCorrectiveAdapter(
        gemini_client=mock_gemini_client, supabase_client=mock_supabase_client
    )

    client_success = ClientSuccessLiaisonAdapter(
        gemini_client=mock_gemini_client, supabase_client=mock_supabase_client
    )

    security_guardian = SecurityComplianceGuardianAdapter(
        agent_id="security_guardian",
        gemini_client=mock_gemini_client,
        supabase_client=mock_supabase_client,
    )

    systems_integration = SystemsIntegrationOpsAdapter(
        gemini_client=mock_gemini_client, supabase_client=mock_supabase_client
    )

    # Registrar agentes en el servidor A2A
    await setup_a2a_server.register_agent(
        "motivation_coach", motivation_coach._run_async_impl
    )
    await setup_a2a_server.register_agent(
        "recovery_corrective", recovery_corrective._run_async_impl
    )
    await setup_a2a_server.register_agent(
        "client_success", client_success._run_async_impl
    )
    await setup_a2a_server.register_agent(
        "security_guardian", security_guardian._run_async_impl
    )
    await setup_a2a_server.register_agent(
        "systems_integration", systems_integration._run_async_impl
    )

    # Devolver diccionario con los agentes
    agents = {
        "motivation_coach": motivation_coach,
        "recovery_corrective": recovery_corrective,
        "client_success": client_success,
        "security_guardian": security_guardian,
        "systems_integration": systems_integration,
    }

    return agents


class TestSystemIntegration:
    """Pruebas de integración del sistema completo."""

    @pytest.mark.asyncio
    async def test_agent_communication(
        self, setup_agents, setup_a2a_server, mock_state_manager_adapter
    ):
        """Prueba la comunicación entre agentes utilizando el sistema A2A optimizado."""
        # Obtener agentes
        agents = setup_agents

        # Datos de prueba
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"

        # Consulta de prueba para el agente de motivación
        query = "Necesito ayuda para mantenerme motivado en mi rutina de ejercicios"

        # Ejecutar consulta en el agente de motivación
        response = await agents["motivation_coach"]._run_async_impl(
            input_text=query, user_id=user_id, session_id=session_id
        )

        # Verificar que se obtuvo una respuesta
        assert response is not None
        assert "response" in response
        assert isinstance(response["response"], str)

        # Verificar que se consultó al StateManager
        mock_state_manager_adapter.load_state.assert_called_once()
        mock_state_manager_adapter.save_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_cross_agent_consultation(
        self, setup_agents, setup_a2a_server, mock_state_manager_adapter
    ):
        """Prueba la consulta cruzada entre agentes."""
        # Configurar respuesta simulada para el servidor A2A
        setup_a2a_server.send_message = AsyncMock(
            return_value={
                "status": "success",
                "agent_id": "recovery_corrective",
                "output": "Respuesta simulada del agente de recuperación",
                "metadata": {
                    "query_type": "recovery_protocol",
                    "timestamp": time.time(),
                },
            }
        )

        # Obtener agentes
        agents = setup_agents

        # Datos de prueba
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"

        # Consultar desde el agente de motivación al agente de recuperación
        result = await agents["motivation_coach"]._consult_other_agent(
            agent_id="recovery_corrective",
            query="¿Qué ejercicios de recuperación recomiendas después de una carrera intensa?",
            user_id=user_id,
            session_id=session_id,
        )

        # Verificar que se obtuvo una respuesta
        assert result is not None
        assert "output" in result
        assert "agent_id" in result
        assert result["agent_id"] == "recovery_corrective"

    @pytest.mark.asyncio
    async def test_multi_agent_workflow(
        self, setup_agents, setup_a2a_server, mock_state_manager_adapter
    ):
        """Prueba un flujo de trabajo que involucra múltiples agentes."""
        # Obtener agentes
        agents = setup_agents

        # Datos de prueba
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"

        # Configurar respuestas simuladas para el servidor A2A
        async def mock_send_message(from_agent_id, to_agent_id, message, **kwargs):
            if to_agent_id == "recovery_corrective":
                return {
                    "status": "success",
                    "agent_id": "recovery_corrective",
                    "output": "Plan de recuperación generado",
                    "metadata": {"query_type": "recovery_protocol"},
                }
            elif to_agent_id == "security_guardian":
                return {
                    "status": "success",
                    "agent_id": "security_guardian",
                    "output": "Verificación de seguridad completada",
                    "metadata": {"query_type": "data_protection"},
                }
            else:
                return {
                    "status": "success",
                    "agent_id": to_agent_id,
                    "output": f"Respuesta del agente {to_agent_id}",
                    "metadata": {"query_type": "general_request"},
                }

        setup_a2a_server.send_message = mock_send_message

        # Simular un flujo de trabajo completo
        # 1. El usuario consulta al agente de motivación
        motivation_response = await agents["motivation_coach"]._run_async_impl(
            input_text="Quiero un plan de entrenamiento para maratón",
            user_id=user_id,
            session_id=session_id,
        )

        # 2. El agente de motivación consulta al agente de recuperación
        recovery_consultation = await agents["motivation_coach"]._consult_other_agent(
            agent_id="recovery_corrective",
            query="Plan de recuperación para entrenamiento de maratón",
            user_id=user_id,
            session_id=session_id,
        )

        # 3. El agente de motivación consulta al agente de seguridad
        security_consultation = await agents["motivation_coach"]._consult_other_agent(
            agent_id="security_guardian",
            query="Verificar protección de datos para plan de entrenamiento",
            user_id=user_id,
            session_id=session_id,
        )

        # Verificar que todas las consultas fueron exitosas
        assert motivation_response is not None
        assert "response" in motivation_response

        assert recovery_consultation is not None
        assert recovery_consultation["status"] == "success"
        assert recovery_consultation["output"] == "Plan de recuperación generado"

        assert security_consultation is not None
        assert security_consultation["status"] == "success"
        assert security_consultation["output"] == "Verificación de seguridad completada"

        # Verificar que se consultó al StateManager
        assert mock_state_manager_adapter.load_state.call_count >= 1
        assert mock_state_manager_adapter.save_state.call_count >= 1

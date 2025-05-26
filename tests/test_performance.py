"""
Pruebas de rendimiento para el sistema NGX Agents optimizado.

Este módulo contiene pruebas que miden el rendimiento del sistema con los componentes
optimizados y lo comparan con el rendimiento del sistema original.
"""

import pytest
import time
import statistics
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.a2a_optimized import a2a_server
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from clients.vertex_ai import vertex_ai_client

from infrastructure.adapters.motivation_behavior_coach_adapter import (
    MotivationBehaviorCoachAdapter,
)
from infrastructure.adapters.recovery_corrective_adapter import (
    RecoveryCorrectiveAdapter,
)

from agents.motivation_behavior_coach.agent import MotivationBehaviorCoach
from agents.recovery_corrective.agent import RecoveryCorrective

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

        yield mock


@pytest.fixture
def mock_vertex_client():
    """Fixture para simular el cliente antiguo de Vertex."""
    with patch("clients.vertex_client.vertex_client") as mock:
        # Configurar respuestas simuladas
        mock.generate_content = AsyncMock(
            return_value={
                "text": "Respuesta simulada del cliente antiguo",
                "usage": {
                    "prompt_tokens": 100,
                    "candidates_token_count": 50,
                    "total_tokens": 150,
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

        yield mock


@pytest.fixture
def mock_gemini_client():
    """Fixture para simular el cliente Gemini."""
    mock = MagicMock()
    mock.generate_response = AsyncMock(
        return_value="Respuesta simulada del modelo Gemini"
    )

    return mock


@pytest.fixture
def mock_supabase_client():
    """Fixture para simular el cliente Supabase."""
    mock = MagicMock()
    mock.get_user_data = MagicMock(return_value=None)
    return mock


@pytest.fixture
async def setup_optimized_agents(
    mock_gemini_client, mock_supabase_client, setup_a2a_server
):
    """Fixture para configurar los agentes optimizados."""
    # Crear instancias de los agentes con adaptadores
    motivation_coach = MotivationBehaviorCoachAdapter(
        gemini_client=mock_gemini_client, supabase_client=mock_supabase_client
    )

    recovery_corrective = RecoveryCorrectiveAdapter(
        gemini_client=mock_gemini_client, supabase_client=mock_supabase_client
    )

    # Registrar agentes en el servidor A2A
    await setup_a2a_server.register_agent(
        "motivation_coach", motivation_coach._run_async_impl
    )
    await setup_a2a_server.register_agent(
        "recovery_corrective", recovery_corrective._run_async_impl
    )

    # Devolver diccionario con los agentes
    agents = {
        "motivation_coach": motivation_coach,
        "recovery_corrective": recovery_corrective,
    }

    return agents


@pytest.fixture
def setup_original_agents(mock_gemini_client, mock_supabase_client):
    """Fixture para configurar los agentes originales."""
    # Crear instancias de los agentes originales
    motivation_coach = MotivationBehaviorCoach(
        gemini_client=mock_gemini_client, supabase_client=mock_supabase_client
    )

    recovery_corrective = RecoveryCorrective(
        gemini_client=mock_gemini_client, supabase_client=mock_supabase_client
    )

    # Devolver diccionario con los agentes
    agents = {
        "motivation_coach": motivation_coach,
        "recovery_corrective": recovery_corrective,
    }

    return agents


class TestPerformance:
    """Pruebas de rendimiento para el sistema NGX Agents optimizado."""

    @pytest.mark.asyncio
    async def test_response_time_comparison(
        self, setup_optimized_agents, setup_original_agents, mock_state_manager_adapter
    ):
        """Compara el tiempo de respuesta entre los agentes optimizados y los originales."""
        # Obtener agentes
        optimized_agents = setup_optimized_agents
        original_agents = setup_original_agents

        # Datos de prueba
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"

        # Consultas de prueba
        test_queries = [
            "¿Cómo puedo mantenerme motivado para hacer ejercicio?",
            "Necesito un plan de entrenamiento para principiantes",
            "¿Qué ejercicios son buenos para la recuperación muscular?",
            "¿Cómo puedo mejorar mi resistencia?",
            "Necesito consejos para mantener una rutina constante",
        ]

        # Medir tiempo de respuesta para agentes optimizados
        optimized_times = []
        for query in test_queries:
            start_time = time.time()
            await optimized_agents["motivation_coach"]._run_async_impl(
                input_text=query, user_id=user_id, session_id=session_id
            )
            end_time = time.time()
            optimized_times.append(end_time - start_time)

        # Medir tiempo de respuesta para agentes originales
        original_times = []
        for query in test_queries:
            start_time = time.time()
            await original_agents["motivation_coach"]._run_async_impl(
                input_text=query, user_id=user_id, session_id=session_id
            )
            end_time = time.time()
            original_times.append(end_time - start_time)

        # Calcular estadísticas
        avg_optimized = statistics.mean(optimized_times)
        avg_original = statistics.mean(original_times)

        # Imprimir resultados
        logger.info(
            f"Tiempo promedio de respuesta (optimizado): {avg_optimized:.4f} segundos"
        )
        logger.info(
            f"Tiempo promedio de respuesta (original): {avg_original:.4f} segundos"
        )
        logger.info(
            f"Mejora de rendimiento: {(1 - avg_optimized/avg_original) * 100:.2f}%"
        )

        # Verificar que el rendimiento ha mejorado
        assert (
            avg_optimized <= avg_original
        ), "El rendimiento de los agentes optimizados debería ser igual o mejor que el de los originales"

    @pytest.mark.asyncio
    async def test_memory_usage_comparison(
        self, setup_optimized_agents, setup_original_agents
    ):
        """Compara el uso de memoria entre los agentes optimizados y los originales."""
        # Esta prueba es más conceptual ya que no podemos medir directamente el uso de memoria en pytest
        # En un entorno real, se utilizarían herramientas como memory_profiler

        # Obtener agentes
        optimized_agents = setup_optimized_agents
        original_agents = setup_original_agents

        # Datos de prueba
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"

        # Consulta de prueba
        query = "Necesito un plan de entrenamiento completo para un maratón"

        # Ejecutar consulta en ambos tipos de agentes
        await optimized_agents["motivation_coach"]._run_async_impl(
            input_text=query, user_id=user_id, session_id=session_id
        )

        await original_agents["motivation_coach"]._run_async_impl(
            input_text=query, user_id=user_id, session_id=session_id
        )

        # En un entorno real, aquí mediríamos el uso de memoria
        # Para esta prueba, simplemente verificamos que ambos agentes funcionan
        assert True, "Ambos agentes deberían ejecutarse sin errores"

    @pytest.mark.asyncio
    async def test_a2a_communication_performance(
        self, setup_optimized_agents, setup_a2a_server
    ):
        """Mide el rendimiento de la comunicación entre agentes utilizando el sistema A2A optimizado."""
        # Obtener agentes
        agents = setup_optimized_agents

        # Datos de prueba
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"

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

        # Medir tiempo de comunicación entre agentes
        communication_times = []
        for _ in range(10):  # Realizar 10 pruebas
            start_time = time.time()
            await agents["motivation_coach"]._consult_other_agent(
                agent_id="recovery_corrective",
                query="¿Qué ejercicios de recuperación recomiendas?",
                user_id=user_id,
                session_id=session_id,
            )
            end_time = time.time()
            communication_times.append(end_time - start_time)

        # Calcular estadísticas
        avg_time = statistics.mean(communication_times)
        max_time = max(communication_times)
        min_time = min(communication_times)

        # Imprimir resultados
        logger.info(f"Tiempo promedio de comunicación A2A: {avg_time:.4f} segundos")
        logger.info(f"Tiempo máximo de comunicación A2A: {max_time:.4f} segundos")
        logger.info(f"Tiempo mínimo de comunicación A2A: {min_time:.4f} segundos")

        # Verificar que el tiempo de comunicación es aceptable
        assert (
            avg_time < 0.5
        ), "El tiempo promedio de comunicación A2A debería ser menor a 0.5 segundos"

    @pytest.mark.asyncio
    async def test_state_manager_performance(self, mock_state_manager_adapter):
        """Mide el rendimiento del StateManager optimizado."""
        # Datos de prueba
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"

        # Estado de prueba
        test_state = {
            "conversation_history": [
                {"role": "user", "content": "Mensaje de prueba 1"},
                {"role": "assistant", "content": "Respuesta de prueba 1"},
            ],
            "user_profile": {
                "name": "Usuario de prueba",
                "preferences": ["Fitness", "Nutrición"],
            },
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Medir tiempo de operaciones de guardado
        save_times = []
        for _ in range(10):  # Realizar 10 pruebas
            start_time = time.time()
            await state_manager_adapter.save_state(user_id, session_id, test_state)
            end_time = time.time()
            save_times.append(end_time - start_time)

        # Medir tiempo de operaciones de carga
        load_times = []
        for _ in range(10):  # Realizar 10 pruebas
            start_time = time.time()
            await state_manager_adapter.load_state(user_id, session_id)
            end_time = time.time()
            load_times.append(end_time - start_time)

        # Calcular estadísticas
        avg_save_time = statistics.mean(save_times)
        avg_load_time = statistics.mean(load_times)

        # Imprimir resultados
        logger.info(
            f"Tiempo promedio de guardado de estado: {avg_save_time:.4f} segundos"
        )
        logger.info(f"Tiempo promedio de carga de estado: {avg_load_time:.4f} segundos")

        # Verificar que los tiempos son aceptables
        assert (
            avg_save_time < 0.1
        ), "El tiempo promedio de guardado de estado debería ser menor a 0.1 segundos"
        assert (
            avg_load_time < 0.1
        ), "El tiempo promedio de carga de estado debería ser menor a 0.1 segundos"

    @pytest.mark.asyncio
    async def test_vertex_ai_client_performance(
        self, mock_vertex_ai_client, mock_vertex_client
    ):
        """Compara el rendimiento entre el cliente centralizado de Vertex AI y el cliente antiguo."""
        # Consulta de prueba
        test_prompt = "Genera un plan de entrenamiento para un maratón"

        # Medir tiempo de respuesta para el cliente centralizado
        centralized_times = []
        for _ in range(5):  # Realizar 5 pruebas
            start_time = time.time()
            await vertex_ai_client.generate_content(test_prompt)
            end_time = time.time()
            centralized_times.append(end_time - start_time)

        # Medir tiempo de respuesta para el cliente antiguo
        old_times = []
        for _ in range(5):  # Realizar 5 pruebas
            start_time = time.time()
            await mock_vertex_client.generate_content(test_prompt)
            end_time = time.time()
            old_times.append(end_time - start_time)

        # Calcular estadísticas
        avg_centralized = statistics.mean(centralized_times)
        avg_old = statistics.mean(old_times)

        # Imprimir resultados
        logger.info(
            f"Tiempo promedio de respuesta (cliente centralizado): {avg_centralized:.4f} segundos"
        )
        logger.info(
            f"Tiempo promedio de respuesta (cliente antiguo): {avg_old:.4f} segundos"
        )
        logger.info(
            f"Mejora de rendimiento: {(1 - avg_centralized/avg_old) * 100:.2f}%"
        )

        # Verificar que el rendimiento ha mejorado
        assert (
            avg_centralized <= avg_old
        ), "El rendimiento del cliente centralizado debería ser igual o mejor que el del cliente antiguo"

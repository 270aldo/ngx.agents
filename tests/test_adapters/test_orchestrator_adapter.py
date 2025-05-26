"""
Pruebas para el adaptador del agente Orchestrator.

Este módulo contiene pruebas para verificar el funcionamiento
del adaptador del agente Orchestrator con el sistema A2A optimizado.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from infrastructure.adapters.orchestrator_adapter import orchestrator_adapter
from infrastructure.a2a_optimized import MessagePriority


@pytest.mark.asyncio
async def test_initialize():
    """Prueba la inicialización del adaptador."""
    # Mockear las dependencias
    with patch(
        "infrastructure.adapters.orchestrator_adapter.a2a_adapter"
    ) as mock_a2a_adapter:
        # Configurar mocks
        mock_a2a_adapter.register_agent.return_value = None

        # Inicializar adaptador
        await orchestrator_adapter._register_with_a2a_server()

        # Verificar que se llamaron los métodos esperados
        mock_a2a_adapter.register_agent.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_intent():
    """Prueba el análisis de intención."""
    # Mockear las dependencias
    with (
        patch(
            "infrastructure.adapters.orchestrator_adapter.intent_analyzer_adapter"
        ) as mock_intent_analyzer,
        patch(
            "infrastructure.adapters.orchestrator_adapter.telemetry"
        ) as mock_telemetry,
    ):

        # Configurar mocks
        mock_intent_analyzer.analyze.return_value = asyncio.Future()
        mock_intent_analyzer.analyze.return_value.set_result(
            {
                "type": "route_message",
                "confidence": 0.9,
                "target_agents": [
                    "elite_training_strategist",
                    "precision_nutrition_architect",
                ],
                "priority": "high",
            }
        )

        mock_telemetry.start_span.return_value = MagicMock()
        mock_telemetry.record_event.return_value = None

        # Datos de prueba
        user_input = "Necesito un plan de entrenamiento y nutrición"
        context = {}

        # Analizar intención
        result = await orchestrator_adapter._analyze_intent(user_input, context)

        # Verificar resultado
        assert result is not None
        assert result["type"] == "route_message"
        assert result["confidence"] == 0.9
        assert "elite_training_strategist" in result["target_agents"]
        assert "precision_nutrition_architect" in result["target_agents"]
        assert result["priority"] == "high"

        # Verificar que se llamaron los métodos esperados
        mock_intent_analyzer.analyze.assert_called_once_with(user_input, context)
        mock_telemetry.record_event.assert_called_once()


@pytest.mark.asyncio
async def test_determine_target_agents():
    """Prueba la determinación de agentes objetivo."""
    # Mockear las dependencias
    with patch(
        "infrastructure.adapters.orchestrator_adapter.telemetry"
    ) as mock_telemetry:

        # Configurar mocks
        mock_telemetry.start_span.return_value = MagicMock()
        mock_telemetry.record_event.return_value = None

        # Datos de prueba
        intent = {
            "type": "route_message",
            "confidence": 0.9,
            "target_agents": [
                "elite_training_strategist",
                "precision_nutrition_architect",
            ],
            "priority": "high",
        }
        user_input = "Necesito un plan de entrenamiento y nutrición"
        context = {}

        # Determinar agentes objetivo
        target_agents, priority = await orchestrator_adapter._determine_target_agents(
            intent, user_input, context
        )

        # Verificar resultado
        assert target_agents == [
            "elite_training_strategist",
            "precision_nutrition_architect",
        ]
        assert priority == MessagePriority.HIGH

        # Verificar que se llamaron los métodos esperados
        mock_telemetry.record_event.assert_called_once()


@pytest.mark.asyncio
async def test_determine_target_agents_with_emergency():
    """Prueba la determinación de agentes objetivo con palabras clave de emergencia."""
    # Mockear las dependencias
    with patch(
        "infrastructure.adapters.orchestrator_adapter.telemetry"
    ) as mock_telemetry:

        # Configurar mocks
        mock_telemetry.start_span.return_value = MagicMock()
        mock_telemetry.record_event.return_value = None

        # Datos de prueba
        intent = {
            "type": "route_message",
            "confidence": 0.9,
            "target_agents": ["recovery_corrective"],
            "priority": "normal",
        }
        user_input = "Tengo una emergencia, me duele mucho la rodilla"
        context = {}

        # Determinar agentes objetivo
        target_agents, priority = await orchestrator_adapter._determine_target_agents(
            intent, user_input, context
        )

        # Verificar resultado
        assert target_agents == ["recovery_corrective"]
        assert priority == MessagePriority.CRITICAL

        # Verificar que se llamaron los métodos esperados
        mock_telemetry.record_event.assert_called_once()


@pytest.mark.asyncio
async def test_route_message_single_agent():
    """Prueba el enrutamiento de mensajes a un solo agente."""
    # Mockear las dependencias
    with (
        patch(
            "infrastructure.adapters.orchestrator_adapter.telemetry"
        ) as mock_telemetry,
        patch.object(
            orchestrator_adapter, "_consult_other_agent"
        ) as mock_consult_agent,
    ):

        # Configurar mocks
        mock_telemetry.start_span.return_value = MagicMock()

        mock_consult_agent.return_value = asyncio.Future()
        mock_consult_agent.return_value.set_result(
            {
                "status": "success",
                "output": "Respuesta del agente",
                "agent_id": "elite_training_strategist",
            }
        )

        # Datos de prueba
        user_input = "Necesito un plan de entrenamiento"
        target_agents = ["elite_training_strategist"]
        priority = MessagePriority.NORMAL
        user_id = "test_user"
        session_id = "test_session"
        context = {}

        # Enrutar mensaje
        result = await orchestrator_adapter._route_message(
            user_input, target_agents, priority, user_id, session_id, context
        )

        # Verificar resultado
        assert result is not None
        assert result["status"] == "success"
        assert result["output"] == "Respuesta del agente"
        assert result["agent_id"] == "elite_training_strategist"

        # Verificar que se llamaron los métodos esperados
        mock_consult_agent.assert_called_once()


@pytest.mark.asyncio
async def test_route_message_multiple_agents():
    """Prueba el enrutamiento de mensajes a múltiples agentes."""
    # Mockear las dependencias
    with (
        patch(
            "infrastructure.adapters.orchestrator_adapter.telemetry"
        ) as mock_telemetry,
        patch.object(
            orchestrator_adapter, "_call_multiple_agents_parallel"
        ) as mock_call_multiple,
        patch.object(orchestrator_adapter, "_combine_responses") as mock_combine,
    ):

        # Configurar mocks
        mock_telemetry.start_span.return_value = MagicMock()

        mock_call_multiple.return_value = asyncio.Future()
        mock_call_multiple.return_value.set_result(
            {
                "elite_training_strategist": {
                    "status": "success",
                    "output": "Respuesta del agente de entrenamiento",
                    "agent_id": "elite_training_strategist",
                },
                "precision_nutrition_architect": {
                    "status": "success",
                    "output": "Respuesta del agente de nutrición",
                    "agent_id": "precision_nutrition_architect",
                },
            }
        )

        mock_combine.return_value = {
            "status": "success",
            "output": "Respuesta combinada de los agentes",
            "agent_responses": {
                "elite_training_strategist": {
                    "status": "success",
                    "output": "Respuesta del agente de entrenamiento",
                    "agent_id": "elite_training_strategist",
                },
                "precision_nutrition_architect": {
                    "status": "success",
                    "output": "Respuesta del agente de nutrición",
                    "agent_id": "precision_nutrition_architect",
                },
            },
        }

        # Datos de prueba
        user_input = "Necesito un plan de entrenamiento y nutrición"
        target_agents = ["elite_training_strategist", "precision_nutrition_architect"]
        priority = MessagePriority.HIGH
        user_id = "test_user"
        session_id = "test_session"
        context = {}

        # Enrutar mensaje
        result = await orchestrator_adapter._route_message(
            user_input, target_agents, priority, user_id, session_id, context
        )

        # Verificar resultado
        assert result is not None
        assert result["status"] == "success"
        assert result["output"] == "Respuesta combinada de los agentes"
        assert "agent_responses" in result

        # Verificar que se llamaron los métodos esperados
        mock_call_multiple.assert_called_once()
        mock_combine.assert_called_once()


@pytest.mark.asyncio
async def test_call_multiple_agents_parallel():
    """Prueba la llamada a múltiples agentes en paralelo."""
    # Mockear las dependencias
    with (
        patch(
            "infrastructure.adapters.orchestrator_adapter.telemetry"
        ) as mock_telemetry,
        patch.object(orchestrator_adapter, "_safe_call_agent") as mock_safe_call,
    ):

        # Configurar mocks
        mock_telemetry.start_span.return_value = MagicMock()
        mock_telemetry.record_event.return_value = None

        # Configurar respuestas para cada agente
        async def mock_safe_call_side_effect(agent_id, query, context, timeout):
            if agent_id == "elite_training_strategist":
                return {
                    "status": "success",
                    "output": "Respuesta del agente de entrenamiento",
                    "agent_id": "elite_training_strategist",
                }
            elif agent_id == "precision_nutrition_architect":
                return {
                    "status": "success",
                    "output": "Respuesta del agente de nutrición",
                    "agent_id": "precision_nutrition_architect",
                }
            else:
                return {
                    "status": "error",
                    "error": "Agente desconocido",
                    "output": f"Error al llamar al agente {agent_id}",
                    "agent_id": agent_id,
                }

        mock_safe_call.side_effect = mock_safe_call_side_effect

        # Datos de prueba
        user_input = "Necesito un plan de entrenamiento y nutrición"
        agent_ids = ["elite_training_strategist", "precision_nutrition_architect"]
        priority = MessagePriority.HIGH
        context = {}

        # Llamar a múltiples agentes
        result = await orchestrator_adapter._call_multiple_agents_parallel(
            user_input, agent_ids, priority, context
        )

        # Verificar resultado
        assert result is not None
        assert len(result) == 2
        assert "elite_training_strategist" in result
        assert "precision_nutrition_architect" in result
        assert result["elite_training_strategist"]["status"] == "success"
        assert result["precision_nutrition_architect"]["status"] == "success"

        # Verificar que se llamaron los métodos esperados
        assert mock_safe_call.call_count == 2
        mock_telemetry.record_event.assert_called_once()


@pytest.mark.asyncio
async def test_safe_call_agent():
    """Prueba la llamada segura a un agente."""
    # Mockear las dependencias
    with patch(
        "infrastructure.adapters.orchestrator_adapter.a2a_adapter"
    ) as mock_a2a_adapter:

        # Configurar mocks
        mock_a2a_adapter.call_agent.return_value = asyncio.Future()
        mock_a2a_adapter.call_agent.return_value.set_result(
            {
                "status": "success",
                "output": "Respuesta del agente",
                "agent_id": "elite_training_strategist",
            }
        )

        # Datos de prueba
        agent_id = "elite_training_strategist"
        query = "Necesito un plan de entrenamiento"
        context = {}
        timeout = 60

        # Llamar al agente
        result = await orchestrator_adapter._safe_call_agent(
            agent_id, query, context, timeout
        )

        # Verificar resultado
        assert result is not None
        assert result["status"] == "success"
        assert result["output"] == "Respuesta del agente"
        assert result["agent_id"] == "elite_training_strategist"

        # Verificar que se llamaron los métodos esperados
        mock_a2a_adapter.call_agent.assert_called_once_with(
            agent_id=agent_id, user_input=query, context=context
        )


@pytest.mark.asyncio
async def test_safe_call_agent_timeout():
    """Prueba la llamada segura a un agente con timeout."""
    # Mockear las dependencias
    with (
        patch(
            "infrastructure.adapters.orchestrator_adapter.a2a_adapter"
        ) as mock_a2a_adapter,
        patch(
            "infrastructure.adapters.orchestrator_adapter.telemetry"
        ) as mock_telemetry,
    ):

        # Configurar mocks para simular un timeout
        async def mock_call_agent(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simular una operación que toma tiempo
            return {
                "status": "success",
                "output": "Respuesta del agente",
                "agent_id": "elite_training_strategist",
            }

        mock_a2a_adapter.call_agent.side_effect = mock_call_agent
        mock_telemetry.record_error.return_value = None

        # Datos de prueba
        agent_id = "elite_training_strategist"
        query = "Necesito un plan de entrenamiento"
        context = {}
        timeout = 0.05  # Timeout muy corto para forzar el error

        # Llamar al agente
        result = await orchestrator_adapter._safe_call_agent(
            agent_id, query, context, timeout
        )

        # Verificar resultado
        assert result is not None
        assert result["status"] == "error"
        assert "timeout" in result["error"].lower()
        assert result["agent_id"] == "elite_training_strategist"

        # Verificar que se llamaron los métodos esperados
        mock_a2a_adapter.call_agent.assert_called_once()
        mock_telemetry.record_error.assert_called_once()


@pytest.mark.asyncio
async def test_combine_responses():
    """Prueba la combinación de respuestas de múltiples agentes."""
    # Mockear las dependencias
    with patch(
        "infrastructure.adapters.orchestrator_adapter.telemetry"
    ) as mock_telemetry:

        # Configurar mocks
        mock_telemetry.start_span.return_value = MagicMock()
        mock_telemetry.record_event.return_value = None

        # Datos de prueba
        responses = {
            "elite_training_strategist": {
                "status": "success",
                "output": "Respuesta del agente de entrenamiento",
                "agent_id": "elite_training_strategist",
            },
            "precision_nutrition_architect": {
                "status": "success",
                "output": "Respuesta del agente de nutrición",
                "agent_id": "precision_nutrition_architect",
            },
        }
        agent_ids = ["elite_training_strategist", "precision_nutrition_architect"]

        # Combinar respuestas
        result = orchestrator_adapter._combine_responses(responses, agent_ids)

        # Verificar resultado
        assert result is not None
        assert result["status"] == "success"
        assert "Respuesta del agente de entrenamiento" in result["output"]
        assert "Respuesta del agente de nutrición" in result["output"]
        assert "agent_responses" in result

        # Verificar que se llamaron los métodos esperados
        mock_telemetry.record_event.assert_called_once()


@pytest.mark.asyncio
async def test_combine_responses_all_errors():
    """Prueba la combinación de respuestas cuando todos los agentes fallan."""
    # Mockear las dependencias
    with patch(
        "infrastructure.adapters.orchestrator_adapter.telemetry"
    ) as mock_telemetry:

        # Configurar mocks
        mock_telemetry.start_span.return_value = MagicMock()
        mock_telemetry.record_event.return_value = None

        # Datos de prueba
        responses = {
            "elite_training_strategist": {
                "status": "error",
                "error": "Error en el agente de entrenamiento",
                "output": "Error al procesar la solicitud",
                "agent_id": "elite_training_strategist",
            },
            "precision_nutrition_architect": {
                "status": "error",
                "error": "Error en el agente de nutrición",
                "output": "Error al procesar la solicitud",
                "agent_id": "precision_nutrition_architect",
            },
        }
        agent_ids = ["elite_training_strategist", "precision_nutrition_architect"]

        # Combinar respuestas
        result = orchestrator_adapter._combine_responses(responses, agent_ids)

        # Verificar resultado
        assert result is not None
        assert result["status"] == "error"
        assert "Todos los agentes fallaron" in result["error"]
        assert "agent_responses" in result

        # Verificar que se llamaron los métodos esperados
        mock_telemetry.record_event.assert_called_once()


@pytest.mark.asyncio
async def test_process_query():
    """Prueba el procesamiento completo de una consulta."""
    # Mockear las dependencias
    with (
        patch(
            "infrastructure.adapters.orchestrator_adapter.telemetry"
        ) as mock_telemetry,
        patch.object(orchestrator_adapter, "_analyze_intent") as mock_analyze_intent,
        patch.object(
            orchestrator_adapter, "_determine_target_agents"
        ) as mock_determine_agents,
        patch.object(orchestrator_adapter, "_route_message") as mock_route_message,
        patch.object(orchestrator_adapter, "_update_metrics") as mock_update_metrics,
    ):

        # Configurar mocks
        mock_telemetry.start_span.return_value = MagicMock()
        mock_telemetry.record_event.return_value = None

        mock_analyze_intent.return_value = asyncio.Future()
        mock_analyze_intent.return_value.set_result(
            {
                "type": "route_message",
                "confidence": 0.9,
                "target_agents": [
                    "elite_training_strategist",
                    "precision_nutrition_architect",
                ],
                "priority": "high",
            }
        )

        mock_determine_agents.return_value = asyncio.Future()
        mock_determine_agents.return_value.set_result(
            (
                ["elite_training_strategist", "precision_nutrition_architect"],
                MessagePriority.HIGH,
            )
        )

        mock_route_message.return_value = asyncio.Future()
        mock_route_message.return_value.set_result(
            {
                "status": "success",
                "output": "Respuesta combinada de los agentes",
                "agent_responses": {
                    "elite_training_strategist": {
                        "status": "success",
                        "output": "Respuesta del agente de entrenamiento",
                        "agent_id": "elite_training_strategist",
                    },
                    "precision_nutrition_architect": {
                        "status": "success",
                        "output": "Respuesta del agente de nutrición",
                        "agent_id": "precision_nutrition_architect",
                    },
                },
            }
        )

        # Datos de prueba
        query = "Necesito un plan de entrenamiento y nutrición"
        user_id = "test_user"
        session_id = "test_session"
        program_type = "general"
        state = {}
        profile = {}

        # Procesar consulta
        result = await orchestrator_adapter._process_query(
            query, user_id, session_id, program_type, state, profile
        )

        # Verificar resultado
        assert result is not None
        assert result["status"] == "success"
        assert result["output"] == "Respuesta combinada de los agentes"
        assert "agent_responses" in result

        # Verificar que se llamaron los métodos esperados
        mock_analyze_intent.assert_called_once_with(query, state)
        mock_determine_agents.assert_called_once()
        mock_route_message.assert_called_once()
        mock_update_metrics.assert_called_once()

        # Verificar que se actualizó el estado
        assert "routing_decisions" in state
        assert len(state["routing_decisions"]) == 1
        assert state["routing_decisions"][0]["query"] == query


@pytest.mark.asyncio
async def test_adjust_score_based_on_context():
    """Prueba el ajuste de puntuación basado en el contexto."""
    # Datos de prueba
    score = 0.7
    context = {
        "requires_coordination": True,
        "agent_interactions": ["agent1", "agent2", "agent3"],
    }

    # Ajustar puntuación
    result = orchestrator_adapter._adjust_score_based_on_context(score, context)

    # Verificar resultado
    assert result > score  # La puntuación debe aumentar
    assert result <= 1.0  # La puntuación no debe superar 1.0


@pytest.mark.asyncio
async def test_get_priority_name():
    """Prueba la obtención del nombre de la prioridad."""
    # Datos de prueba
    priorities = [
        (MessagePriority.CRITICAL, "critical"),
        (MessagePriority.HIGH, "high"),
        (MessagePriority.NORMAL, "normal"),
        (MessagePriority.LOW, "low"),
    ]

    # Verificar cada prioridad
    for priority, expected_name in priorities:
        result = orchestrator_adapter._get_priority_name(priority)
        assert result == expected_name

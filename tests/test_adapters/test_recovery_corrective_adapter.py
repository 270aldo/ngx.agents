"""
Pruebas para el adaptador del agente RecoveryCorrective.

Este módulo contiene pruebas para verificar el funcionamiento
del adaptador del agente RecoveryCorrective con el sistema A2A optimizado.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from infrastructure.adapters.recovery_corrective_adapter import (
    recovery_corrective_adapter,
)
from infrastructure.adapters.a2a_adapter import a2a_adapter


@pytest.mark.asyncio
async def test_initialize():
    """Prueba la inicialización del adaptador."""
    # Mockear las dependencias
    with (
        patch(
            "infrastructure.adapters.recovery_corrective_adapter.intent_analyzer_adapter"
        ) as mock_intent_analyzer,
        patch(
            "infrastructure.adapters.recovery_corrective_adapter.state_manager_adapter"
        ) as mock_state_manager,
        patch(
            "infrastructure.adapters.recovery_corrective_adapter.a2a_adapter"
        ) as mock_a2a_adapter,
    ):

        # Configurar mocks
        mock_intent_analyzer.initialize.return_value = asyncio.Future()
        mock_intent_analyzer.initialize.return_value.set_result(True)

        mock_state_manager.initialize.return_value = asyncio.Future()
        mock_state_manager.initialize.return_value.set_result(True)

        mock_a2a_adapter.register_agent.return_value = None

        # Inicializar adaptador
        result = await recovery_corrective_adapter.initialize()

        # Verificar resultado
        assert result is True

        # Verificar que se llamaron los métodos esperados
        mock_intent_analyzer.initialize.assert_called_once()
        mock_state_manager.initialize.assert_called_once()
        mock_a2a_adapter.register_agent.assert_called_once()


@pytest.mark.asyncio
async def test_process_query():
    """Prueba el procesamiento de consultas del adaptador."""
    # Mockear las dependencias
    with (
        patch(
            "infrastructure.adapters.recovery_corrective_adapter.intent_analyzer_adapter"
        ) as mock_intent_analyzer,
        patch(
            "infrastructure.adapters.recovery_corrective_adapter.telemetry_adapter"
        ) as mock_telemetry,
        patch(
            "infrastructure.adapters.recovery_corrective_adapter.vertex_ai_client"
        ) as mock_vertex_ai,
    ):

        # Configurar mocks
        mock_intent_analyzer.analyze_intent.return_value = asyncio.Future()
        mock_intent_analyzer.analyze_intent.return_value.set_result(
            [MagicMock(intent_type="injury", confidence=0.9)]
        )

        mock_telemetry.start_span.return_value = "test_span"
        mock_telemetry.set_span_attribute.return_value = None
        mock_telemetry.end_span.return_value = None

        mock_vertex_ai.generate_text.return_value = (
            "Análisis de lesión generado por el modelo"
        )

        # Datos de prueba
        query = "Tengo dolor en la rodilla al correr"
        user_id = "test_user"
        session_id = "test_session"
        program_type = "general"
        state = {}
        profile = {"age": 30, "gender": "male", "fitness_level": "intermediate"}

        # Procesar consulta
        response = await recovery_corrective_adapter._process_query(
            query=query,
            user_id=user_id,
            session_id=session_id,
            program_type=program_type,
            state=state,
            profile=profile,
        )

        # Verificar resultado
        assert response is not None
        assert response["status"] == "success"
        assert "output" in response
        assert response["agent_id"] == recovery_corrective_adapter.agent_id
        assert "query_type" in response
        assert "processing_time" in response

        # Verificar que se llamaron los métodos esperados
        mock_intent_analyzer.analyze_intent.assert_called_once_with(query)
        mock_telemetry.start_span.assert_called_once()
        mock_vertex_ai.generate_text.assert_called_once()


@pytest.mark.asyncio
async def test_determine_query_type():
    """Prueba la determinación del tipo de consulta."""
    # Casos de prueba
    test_cases = [
        # (intent_result, query, expected_type)
        ([MagicMock(intent_type="injury_assessment")], "", "assess_injury"),
        ([MagicMock(intent_type="pain_evaluation")], "", "assess_pain"),
        ([MagicMock(intent_type="mobility_improvement")], "", "improve_mobility"),
        ([MagicMock(intent_type="recovery_plan")], "", "create_recovery_plan"),
        ([MagicMock(intent_type="exercise_recommendation")], "", "recommend_exercises"),
        (
            [MagicMock(intent_type="rehabilitation_protocol")],
            "",
            "rehabilitation_protocol",
        ),
        ([], "tengo una lesión en el tobillo", "assess_injury"),
        ([], "siento dolor en la espalda", "assess_pain"),
        ([], "quiero mejorar mi movilidad", "improve_mobility"),
        ([], "necesito un plan de recuperación", "create_recovery_plan"),
        ([], "recomiéndame ejercicios para el hombro", "recommend_exercises"),
        ([], "protocolo de rehabilitación para rodilla", "rehabilitation_protocol"),
        ([], "consulta genérica", "generic_query"),
    ]

    # Probar cada caso
    for intent_result, query, expected_type in test_cases:
        result = recovery_corrective_adapter._determine_query_type(intent_result, query)
        assert (
            result == expected_type
        ), f"Para intent={intent_result}, query='{query}', se esperaba '{expected_type}' pero se obtuvo '{result}'"


@pytest.mark.asyncio
async def test_build_prompt_with_context():
    """Prueba la construcción de prompts con contexto."""
    # Datos de prueba
    prompt = "responde a esta consulta"
    context = {
        "user_profile": {
            "age": 35,
            "gender": "female",
            "fitness_level": "advanced",
            "medical_conditions": ["tendinitis"],
        },
        "injury_assessments": [
            {
                "date": "2025-05-14T10:00:00",
                "query": "lesión previa",
                "assessment": "Evaluación de la lesión previa",
            }
        ],
        "recovery_plans": [
            {
                "date": "2025-05-14T11:00:00",
                "query": "plan previo",
                "plan": "Plan de recuperación previo",
            }
        ],
    }

    # Construir prompt
    result = recovery_corrective_adapter._build_prompt_with_context(prompt, context)

    # Verificar resultado
    assert "Como especialista en recuperación y corrección de lesiones" in result
    assert "responde a esta consulta" in result
    assert "Información del usuario" in result
    assert "Edad: 35" in result
    assert "Género: female" in result
    assert "Nivel de condición física: advanced" in result
    assert "Condiciones médicas: tendinitis" in result
    assert "Evaluación de lesión previa" in result
    assert "Plan de recuperación previo" in result


@pytest.mark.asyncio
async def test_a2a_integration():
    """Prueba la integración con el sistema A2A."""
    # Mockear las dependencias
    with (
        patch("infrastructure.adapters.a2a_adapter.a2a_server") as mock_a2a_server,
        patch.object(recovery_corrective_adapter, "run_async_impl") as mock_run_async,
    ):

        # Configurar mocks
        mock_a2a_server.send_message.return_value = asyncio.Future()
        mock_a2a_server.send_message.return_value.set_result(True)

        mock_run_async.return_value = asyncio.Future()
        mock_run_async.return_value.set_result(
            {
                "status": "success",
                "output": "Respuesta de prueba",
                "agent_id": recovery_corrective_adapter.agent_id,
            }
        )

        # Registrar el adaptador con el sistema A2A
        a2a_adapter.register_agent(
            agent_id=recovery_corrective_adapter.agent_id,
            agent_info={
                "name": recovery_corrective_adapter.name,
                "description": recovery_corrective_adapter.description,
                "message_callback": lambda x: asyncio.Future(),
            },
        )

        # Verificar que el agente está registrado
        assert recovery_corrective_adapter.agent_id in a2a_adapter.registered_agents

        # Simular una llamada al agente a través del sistema A2A
        message = {
            "user_input": "Tengo dolor en la rodilla",
            "context": {"user_id": "test_user", "session_id": "test_session"},
        }

        # Obtener el callback registrado
        callback = a2a_adapter.registered_agents[recovery_corrective_adapter.agent_id][
            "message_callback"
        ]

        # Crear una tarea para llamar al callback
        callback_task = asyncio.create_task(callback(message))

        # Esperar a que se complete la tarea
        await asyncio.sleep(0.1)

        # Verificar que se llamó al método run_async_impl
        mock_run_async.assert_called_once()


@pytest.mark.asyncio
async def test_get_metrics():
    """Prueba la obtención de métricas del adaptador."""
    # Obtener métricas
    metrics = await recovery_corrective_adapter.get_metrics()

    # Verificar resultado
    assert metrics is not None
    assert "agent_id" in metrics
    assert "agent_name" in metrics
    assert "metrics" in metrics
    assert "queries_processed" in metrics["metrics"]
    assert "successful_queries" in metrics["metrics"]
    assert "failed_queries" in metrics["metrics"]
    assert "average_processing_time" in metrics["metrics"]
    assert "query_types" in metrics["metrics"]

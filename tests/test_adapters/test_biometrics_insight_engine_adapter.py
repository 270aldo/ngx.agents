"""
Pruebas para el adaptador del agente BiometricsInsightEngine.

Este módulo contiene pruebas para verificar el funcionamiento
del adaptador del agente BiometricsInsightEngine con el sistema A2A optimizado.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from infrastructure.adapters.biometrics_insight_engine_adapter import (
    biometrics_insight_engine_adapter,
)
from infrastructure.adapters.a2a_adapter import a2a_adapter


@pytest.mark.asyncio
async def test_initialize():
    """Prueba la inicialización del adaptador."""
    # Mockear las dependencias
    with (
        patch(
            "infrastructure.adapters.biometrics_insight_engine_adapter.intent_analyzer_adapter"
        ) as mock_intent_analyzer,
        patch(
            "infrastructure.adapters.biometrics_insight_engine_adapter.state_manager_adapter"
        ) as mock_state_manager,
        patch(
            "infrastructure.adapters.biometrics_insight_engine_adapter.a2a_adapter"
        ) as mock_a2a_adapter,
    ):

        # Configurar mocks
        mock_intent_analyzer.initialize.return_value = asyncio.Future()
        mock_intent_analyzer.initialize.return_value.set_result(True)

        mock_state_manager.initialize.return_value = asyncio.Future()
        mock_state_manager.initialize.return_value.set_result(True)

        mock_a2a_adapter.register_agent.return_value = None

        # Inicializar adaptador
        result = await biometrics_insight_engine_adapter.initialize()

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
            "infrastructure.adapters.biometrics_insight_engine_adapter.intent_analyzer_adapter"
        ) as mock_intent_analyzer,
        patch(
            "infrastructure.adapters.biometrics_insight_engine_adapter.telemetry_adapter"
        ) as mock_telemetry,
        patch(
            "infrastructure.adapters.biometrics_insight_engine_adapter.vertex_ai_client"
        ) as mock_vertex_ai,
    ):

        # Configurar mocks
        mock_intent_analyzer.analyze_intent.return_value = asyncio.Future()
        mock_intent_analyzer.analyze_intent.return_value.set_result(
            [MagicMock(intent_type="biometric_analysis", confidence=0.9)]
        )

        mock_telemetry.start_span.return_value = "test_span"
        mock_telemetry.set_span_attribute.return_value = None
        mock_telemetry.end_span.return_value = None

        mock_vertex_ai.generate_text.return_value = (
            "Análisis biométrico generado por el modelo"
        )

        # Datos de prueba
        query = "Analiza mis datos de sueño y frecuencia cardíaca"
        user_id = "test_user"
        session_id = "test_session"
        program_type = "general"
        state = {}
        profile = {"age": 30, "gender": "male", "fitness_level": "intermediate"}

        # Procesar consulta
        response = await biometrics_insight_engine_adapter._process_query(
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
        assert response["agent_id"] == biometrics_insight_engine_adapter.agent_id
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
        ([MagicMock(intent_type="biometric_analysis")], "", "biometric_analysis"),
        ([MagicMock(intent_type="pattern_recognition")], "", "pattern_recognition"),
        ([MagicMock(intent_type="trend_identification")], "", "trend_identification"),
        ([MagicMock(intent_type="data_visualization")], "", "data_visualization"),
        ([], "analiza mis datos biométricos", "biometric_analysis"),
        ([], "identifica patrones en mis datos", "pattern_recognition"),
        ([], "muestra las tendencias de mi sueño", "trend_identification"),
        ([], "visualiza mi frecuencia cardíaca", "data_visualization"),
        ([], "consulta genérica", "biometric_analysis"),
    ]

    # Probar cada caso
    for intent_result, query, expected_type in test_cases:
        result = biometrics_insight_engine_adapter._determine_query_type(
            intent_result, query
        )
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
            "medical_conditions": ["hipertensión"],
        },
        "analyses": [
            {
                "date": "2025-05-14T10:00:00",
                "query": "análisis previo",
                "analysis": "Análisis biométrico previo",
            }
        ],
        "pattern_analyses": [
            {
                "date": "2025-05-14T11:00:00",
                "query": "patrones previos",
                "analysis": "Análisis de patrones previo",
            }
        ],
    }
    profile = {
        "age": 35,
        "gender": "female",
        "fitness_level": "advanced",
        "medical_conditions": ["hipertensión"],
    }
    program_type = "elite"

    # Construir prompt
    result = biometrics_insight_engine_adapter._build_prompt_with_context(
        prompt, context, profile, program_type
    )

    # Verificar resultado
    assert "Como especialista en análisis de datos biométricos" in result
    assert "responde a esta consulta" in result
    assert "Información del usuario" in result
    assert "Edad: 35" in result
    assert "Género: female" in result
    assert "Nivel de condición física: advanced" in result
    assert "Condiciones médicas: hipertensión" in result
    assert "Tipo de programa: elite" in result
    assert "Análisis biométrico previo" in result
    assert "Análisis de patrones previo" in result


@pytest.mark.asyncio
async def test_a2a_integration():
    """Prueba la integración con el sistema A2A."""
    # Mockear las dependencias
    with (
        patch("infrastructure.adapters.a2a_adapter.a2a_server") as mock_a2a_server,
        patch.object(
            biometrics_insight_engine_adapter, "run_async_impl"
        ) as mock_run_async,
    ):

        # Configurar mocks
        mock_a2a_server.send_message.return_value = asyncio.Future()
        mock_a2a_server.send_message.return_value.set_result(True)

        mock_run_async.return_value = asyncio.Future()
        mock_run_async.return_value.set_result(
            {
                "status": "success",
                "output": "Respuesta de prueba",
                "agent_id": biometrics_insight_engine_adapter.agent_id,
            }
        )

        # Registrar el adaptador con el sistema A2A
        a2a_adapter.register_agent(
            agent_id=biometrics_insight_engine_adapter.agent_id,
            agent_info={
                "name": biometrics_insight_engine_adapter.name,
                "description": biometrics_insight_engine_adapter.description,
                "message_callback": lambda x: asyncio.Future(),
            },
        )

        # Verificar que el agente está registrado
        assert (
            biometrics_insight_engine_adapter.agent_id in a2a_adapter.registered_agents
        )

        # Simular una llamada al agente a través del sistema A2A
        message = {
            "user_input": "Analiza mis datos de sueño",
            "context": {"user_id": "test_user", "session_id": "test_session"},
        }

        # Obtener el callback registrado
        callback = a2a_adapter.registered_agents[
            biometrics_insight_engine_adapter.agent_id
        ]["message_callback"]

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
    metrics = await biometrics_insight_engine_adapter.get_metrics()

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


@pytest.mark.asyncio
async def test_handle_biometric_analysis():
    """Prueba el manejo de consultas de análisis biométrico."""
    # Mockear las dependencias
    with patch.object(
        biometrics_insight_engine_adapter, "_generate_response"
    ) as mock_generate_response:

        # Configurar mocks
        mock_generate_response.return_value = "Análisis biométrico generado"

        # Datos de prueba
        query = "Analiza mis datos de sueño"
        context = biometrics_insight_engine_adapter._create_default_context()
        profile = {"age": 30, "gender": "male", "fitness_level": "intermediate"}
        program_type = "general"

        # Procesar consulta
        result = await biometrics_insight_engine_adapter._handle_biometric_analysis(
            query=query, context=context, profile=profile, program_type=program_type
        )

        # Verificar resultado
        assert result is not None
        assert "response" in result
        assert result["response"] == "Análisis biométrico generado"
        assert "context" in result
        assert "analyses" in result["context"]
        assert len(result["context"]["analyses"]) == 1
        assert result["context"]["analyses"][0]["query"] == query
        assert (
            result["context"]["analyses"][0]["analysis"]
            == "Análisis biométrico generado"
        )

        # Verificar que se llamó al método _generate_response
        mock_generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_handle_pattern_recognition():
    """Prueba el manejo de consultas de reconocimiento de patrones."""
    # Mockear las dependencias
    with patch.object(
        biometrics_insight_engine_adapter, "_generate_response"
    ) as mock_generate_response:

        # Configurar mocks
        mock_generate_response.return_value = "Análisis de patrones generado"

        # Datos de prueba
        query = "Identifica patrones en mis datos"
        context = biometrics_insight_engine_adapter._create_default_context()
        profile = {"age": 30, "gender": "male", "fitness_level": "intermediate"}

        # Procesar consulta
        result = await biometrics_insight_engine_adapter._handle_pattern_recognition(
            query=query, context=context, profile=profile
        )

        # Verificar resultado
        assert result is not None
        assert "response" in result
        assert result["response"] == "Análisis de patrones generado"
        assert "context" in result
        assert "pattern_analyses" in result["context"]
        assert len(result["context"]["pattern_analyses"]) == 1
        assert result["context"]["pattern_analyses"][0]["query"] == query
        assert (
            result["context"]["pattern_analyses"][0]["analysis"]
            == "Análisis de patrones generado"
        )

        # Verificar que se llamó al método _generate_response
        mock_generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_handle_trend_identification():
    """Prueba el manejo de consultas de identificación de tendencias."""
    # Mockear las dependencias
    with patch.object(
        biometrics_insight_engine_adapter, "_generate_response"
    ) as mock_generate_response:

        # Configurar mocks
        mock_generate_response.return_value = "Análisis de tendencias generado"

        # Datos de prueba
        query = "Muestra las tendencias de mi sueño"
        context = biometrics_insight_engine_adapter._create_default_context()
        profile = {"age": 30, "gender": "male", "fitness_level": "intermediate"}

        # Procesar consulta
        result = await biometrics_insight_engine_adapter._handle_trend_identification(
            query=query, context=context, profile=profile
        )

        # Verificar resultado
        assert result is not None
        assert "response" in result
        assert result["response"] == "Análisis de tendencias generado"
        assert "context" in result
        assert "trend_analyses" in result["context"]
        assert len(result["context"]["trend_analyses"]) == 1
        assert result["context"]["trend_analyses"][0]["query"] == query
        assert (
            result["context"]["trend_analyses"][0]["analysis"]
            == "Análisis de tendencias generado"
        )

        # Verificar que se llamó al método _generate_response
        mock_generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_handle_data_visualization():
    """Prueba el manejo de consultas de visualización de datos."""
    # Mockear las dependencias
    with patch.object(
        biometrics_insight_engine_adapter, "_generate_response"
    ) as mock_generate_response:

        # Configurar mocks
        mock_generate_response.return_value = "Descripción de visualización generada"

        # Datos de prueba
        query = "Visualiza mi frecuencia cardíaca"
        context = biometrics_insight_engine_adapter._create_default_context()
        profile = {"age": 30, "gender": "male", "fitness_level": "intermediate"}

        # Procesar consulta
        result = await biometrics_insight_engine_adapter._handle_data_visualization(
            query=query, context=context, profile=profile
        )

        # Verificar resultado
        assert result is not None
        assert "response" in result
        assert result["response"] == "Descripción de visualización generada"
        assert "context" in result
        assert "visualizations" in result["context"]
        assert len(result["context"]["visualizations"]) == 1
        assert result["context"]["visualizations"][0]["query"] == query
        assert (
            result["context"]["visualizations"][0]["description"]
            == "Descripción de visualización generada"
        )

        # Verificar que se llamó al método _generate_response
        mock_generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_handle_generic_query():
    """Prueba el manejo de consultas genéricas."""
    # Mockear las dependencias
    with patch.object(
        biometrics_insight_engine_adapter, "_generate_response"
    ) as mock_generate_response:

        # Configurar mocks
        mock_generate_response.return_value = "Respuesta genérica generada"

        # Datos de prueba
        query = "Consulta genérica"
        context = biometrics_insight_engine_adapter._create_default_context()
        profile = {"age": 30, "gender": "male", "fitness_level": "intermediate"}
        program_type = "general"

        # Procesar consulta
        result = await biometrics_insight_engine_adapter._handle_generic_query(
            query=query, context=context, profile=profile, program_type=program_type
        )

        # Verificar resultado
        assert result is not None
        assert "response" in result
        assert result["response"] == "Respuesta genérica generada"
        assert "context" in result
        assert "conversation_history" in result["context"]
        assert len(result["context"]["conversation_history"]) == 1
        assert result["context"]["conversation_history"][0]["query"] == query
        assert (
            result["context"]["conversation_history"][0]["response"]
            == "Respuesta genérica generada"
        )

        # Verificar que se llamó al método _generate_response
        mock_generate_response.assert_called_once()

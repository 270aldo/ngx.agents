"""
Pruebas unitarias para el adaptador SystemsIntegrationOps.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from infrastructure.adapters.systems_integration_ops_adapter import (
    SystemsIntegrationOpsAdapter,
)


class TestSystemsIntegrationOpsAdapter:
    """Pruebas para SystemsIntegrationOpsAdapter."""

    @pytest.fixture
    def adapter(self):
        """Fixture que proporciona una instancia del adaptador."""
        with patch(
            "infrastructure.adapters.systems_integration_ops_adapter.SystemsIntegrationOps.__init__",
            return_value=None,
        ):
            adapter = SystemsIntegrationOpsAdapter()
            adapter._generate_response = AsyncMock(return_value="Respuesta simulada")
            return adapter

    def test_create_default_context(self, adapter):
        """Prueba la creación del contexto predeterminado."""
        context = adapter._create_default_context()

        assert "conversation_history" in context
        assert "user_profile" in context
        assert "integration_requests" in context
        assert "automation_requests" in context
        assert "api_requests" in context
        assert "infrastructure_requests" in context
        assert "data_pipeline_requests" in context
        assert "last_updated" in context

    def test_get_intent_to_query_type_mapping(self, adapter):
        """Prueba el mapeo de intenciones a tipos de consulta."""
        mapping = adapter._get_intent_to_query_type_mapping()

        assert "integración" in mapping
        assert "automatización" in mapping
        assert "api" in mapping
        assert "infraestructura" in mapping
        assert "pipeline" in mapping

        assert mapping["integración"] == "integration_request"
        assert mapping["automatización"] == "automation_request"
        assert mapping["api"] == "api_request"
        assert mapping["infraestructura"] == "infrastructure_request"
        assert mapping["pipeline"] == "data_pipeline_request"

    def test_determine_query_type(self, adapter):
        """Prueba la determinación del tipo de consulta."""
        # Prueba para integración de sistemas
        query_type = adapter._determine_query_type(
            "Necesito integrar mi aplicación con Apple Health"
        )
        assert query_type == "integration_request"

        # Prueba para automatización de flujos de trabajo
        query_type = adapter._determine_query_type(
            "¿Cómo puedo automatizar el envío de notificaciones?"
        )
        assert query_type == "automation_request"

        # Prueba para gestión de APIs
        query_type = adapter._determine_query_type(
            "Necesito información sobre la API de Fitbit"
        )
        assert query_type == "api_request"

        # Prueba para optimización de infraestructura
        query_type = adapter._determine_query_type(
            "¿Qué arquitectura recomendarías para una app de fitness?"
        )
        assert query_type == "infrastructure_request"

        # Prueba para diseño de pipelines de datos
        query_type = adapter._determine_query_type(
            "Necesito un pipeline para procesar datos de entrenamiento"
        )
        assert query_type == "data_pipeline_request"

        # Prueba para palabras clave adicionales de integración
        query_type = adapter._determine_query_type(
            "¿Cómo puedo conectar mi sistema con otros servicios?"
        )
        assert query_type == "integration_request"

        # Prueba para consulta sin tipo específico (debería devolver general_request)
        query_type = adapter._determine_query_type("¿Puedes ayudarme con mi proyecto?")
        assert query_type == "general_request"

    @pytest.mark.asyncio
    async def test_process_query_integration_request(self, adapter):
        """Prueba el procesamiento de una consulta de tipo integration_request."""
        query = "Necesito integrar mi aplicación con Apple Health"
        user_id = "user123"
        session_id = "session456"
        program_type = "elite"
        state = {}
        profile = {"name": "Test User", "age": 30}

        result = await adapter._process_query(
            query, user_id, session_id, program_type, state, profile
        )

        assert result["success"] is True
        assert "output" in result
        assert result["query_type"] == "integration_request"
        assert result["program_type"] == "elite"
        assert "integration_context" in state
        assert "integration_requests" in state["integration_context"]
        assert len(state["integration_context"]["integration_requests"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_automation_request(self, adapter):
        """Prueba el procesamiento de una consulta de tipo automation_request."""
        query = "¿Cómo puedo automatizar el envío de notificaciones?"
        user_id = "user123"
        session_id = "session456"
        program_type = "elite"
        state = {}
        profile = {"name": "Test User", "age": 30}

        result = await adapter._process_query(
            query, user_id, session_id, program_type, state, profile
        )

        assert result["success"] is True
        assert "output" in result
        assert result["query_type"] == "automation_request"
        assert result["program_type"] == "elite"
        assert "integration_context" in state
        assert "automation_requests" in state["integration_context"]
        assert len(state["integration_context"]["automation_requests"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_api_request(self, adapter):
        """Prueba el procesamiento de una consulta de tipo api_request."""
        query = "Necesito información sobre la API de Fitbit"
        user_id = "user123"
        session_id = "session456"
        program_type = "elite"
        state = {}
        profile = {"name": "Test User", "age": 30}

        result = await adapter._process_query(
            query, user_id, session_id, program_type, state, profile
        )

        assert result["success"] is True
        assert "output" in result
        assert result["query_type"] == "api_request"
        assert result["program_type"] == "elite"
        assert "integration_context" in state
        assert "api_requests" in state["integration_context"]
        assert len(state["integration_context"]["api_requests"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_infrastructure_request(self, adapter):
        """Prueba el procesamiento de una consulta de tipo infrastructure_request."""
        query = "¿Qué arquitectura recomendarías para una app de fitness?"
        user_id = "user123"
        session_id = "session456"
        program_type = "elite"
        state = {}
        profile = {"name": "Test User", "age": 30}

        result = await adapter._process_query(
            query, user_id, session_id, program_type, state, profile
        )

        assert result["success"] is True
        assert "output" in result
        assert result["query_type"] == "infrastructure_request"
        assert result["program_type"] == "elite"
        assert "integration_context" in state
        assert "infrastructure_requests" in state["integration_context"]
        assert len(state["integration_context"]["infrastructure_requests"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_data_pipeline_request(self, adapter):
        """Prueba el procesamiento de una consulta de tipo data_pipeline_request."""
        query = "Necesito un pipeline para procesar datos de entrenamiento"
        user_id = "user123"
        session_id = "session456"
        program_type = "elite"
        state = {}
        profile = {"name": "Test User", "age": 30}

        result = await adapter._process_query(
            query, user_id, session_id, program_type, state, profile
        )

        assert result["success"] is True
        assert "output" in result
        assert result["query_type"] == "data_pipeline_request"
        assert result["program_type"] == "elite"
        assert "integration_context" in state
        assert "data_pipeline_requests" in state["integration_context"]
        assert len(state["integration_context"]["data_pipeline_requests"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_general_request(self, adapter):
        """Prueba el procesamiento de una consulta de tipo general_request."""
        query = "¿Puedes ayudarme con mi proyecto?"
        user_id = "user123"
        session_id = "session456"
        program_type = "elite"
        state = {}
        profile = {"name": "Test User", "age": 30}

        result = await adapter._process_query(
            query, user_id, session_id, program_type, state, profile
        )

        assert result["success"] is True
        assert "output" in result
        assert result["query_type"] == "general_request"
        assert result["program_type"] == "elite"
        assert "integration_context" in state
        assert "conversation_history" in state["integration_context"]
        assert len(state["integration_context"]["conversation_history"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, adapter):
        """Prueba el manejo de errores durante el procesamiento de consultas."""
        query = "Necesito integrar mi aplicación con Apple Health"
        user_id = "user123"
        session_id = "session456"
        program_type = "elite"
        state = {}
        profile = {"name": "Test User", "age": 30}

        # Simular un error en _determine_query_type
        adapter._determine_query_type = MagicMock(
            side_effect=Exception("Error simulado")
        )

        result = await adapter._process_query(
            query, user_id, session_id, program_type, state, profile
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Error simulado"

    @pytest.mark.asyncio
    async def test_handle_integration_request(self, adapter):
        """Prueba el método _handle_integration_request."""
        query = "Necesito integrar mi aplicación con Apple Health"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_integration_request(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "systems" in result
        assert "integration_report" in result
        assert "context" in result
        assert len(result["context"]["integration_requests"]) == 1
        assert result["context"]["integration_requests"][0]["query"] == query
        assert "date" in result["context"]["integration_requests"][0]
        assert "systems" in result["context"]["integration_requests"][0]
        assert "integration_report" in result["context"]["integration_requests"][0]
        assert "Apple HealthKit" in result["systems"]

    @pytest.mark.asyncio
    async def test_handle_automation_request(self, adapter):
        """Prueba el método _handle_automation_request."""
        query = "¿Cómo puedo automatizar el envío de notificaciones?"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_automation_request(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "automation_plan" in result
        assert "context" in result
        assert len(result["context"]["automation_requests"]) == 1
        assert result["context"]["automation_requests"][0]["query"] == query
        assert "date" in result["context"]["automation_requests"][0]
        assert "automation_plan" in result["context"]["automation_requests"][0]

    @pytest.mark.asyncio
    async def test_handle_api_request(self, adapter):
        """Prueba el método _handle_api_request."""
        query = "Necesito información sobre la API de Fitbit"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_api_request(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "apis" in result
        assert "api_guide" in result
        assert "context" in result
        assert len(result["context"]["api_requests"]) == 1
        assert result["context"]["api_requests"][0]["query"] == query
        assert "date" in result["context"]["api_requests"][0]
        assert "apis" in result["context"]["api_requests"][0]
        assert "api_guide" in result["context"]["api_requests"][0]
        assert "Fitbit API" in result["apis"]

    @pytest.mark.asyncio
    async def test_handle_infrastructure_request(self, adapter):
        """Prueba el método _handle_infrastructure_request."""
        query = "¿Qué arquitectura recomendarías para una app de fitness?"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_infrastructure_request(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "infrastructure_report" in result
        assert "context" in result
        assert len(result["context"]["infrastructure_requests"]) == 1
        assert result["context"]["infrastructure_requests"][0]["query"] == query
        assert "date" in result["context"]["infrastructure_requests"][0]
        assert (
            "infrastructure_report" in result["context"]["infrastructure_requests"][0]
        )

    @pytest.mark.asyncio
    async def test_handle_data_pipeline_request(self, adapter):
        """Prueba el método _handle_data_pipeline_request."""
        query = "Necesito un pipeline para procesar datos de entrenamiento"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_data_pipeline_request(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "pipeline_design" in result
        assert "context" in result
        assert len(result["context"]["data_pipeline_requests"]) == 1
        assert result["context"]["data_pipeline_requests"][0]["query"] == query
        assert "date" in result["context"]["data_pipeline_requests"][0]
        assert "pipeline_design" in result["context"]["data_pipeline_requests"][0]

    @pytest.mark.asyncio
    async def test_handle_general_request(self, adapter):
        """Prueba el método _handle_general_request."""
        query = "¿Puedes ayudarme con mi proyecto?"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_general_request(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["conversation_history"]) == 1
        assert result["context"]["conversation_history"][0]["query"] == query
        assert "date" in result["context"]["conversation_history"][0]
        assert "response" in result["context"]["conversation_history"][0]

    @pytest.mark.asyncio
    async def test_generate_response(self, adapter):
        """Prueba el método _generate_response."""
        prompt = "Este es un prompt de prueba"
        context = adapter._create_default_context()

        # Restablecer el mock para esta prueba específica
        adapter._generate_response.reset_mock()
        adapter._generate_response.side_effect = None
        adapter._generate_response.return_value = (
            "Respuesta generada para el prompt de prueba"
        )

        result = await adapter._generate_response(prompt, context)

        assert result == "Respuesta generada para el prompt de prueba"

        # Probar manejo de errores
        adapter._generate_response.side_effect = Exception("Error en la generación")
        result = await adapter._generate_response(prompt, context)

        assert "Error al generar respuesta" in result

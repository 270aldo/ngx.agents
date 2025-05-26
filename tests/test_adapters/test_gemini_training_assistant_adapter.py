"""
Pruebas unitarias para el adaptador GeminiTrainingAssistant.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from infrastructure.adapters.gemini_training_assistant_adapter import (
    GeminiTrainingAssistantAdapter,
)


class TestGeminiTrainingAssistantAdapter:
    """Pruebas para GeminiTrainingAssistantAdapter."""

    @pytest.fixture
    def adapter(self):
        """Fixture que proporciona una instancia del adaptador."""
        with patch(
            "infrastructure.adapters.gemini_training_assistant_adapter.GeminiTrainingAssistant.__init__",
            return_value=None,
        ):
            adapter = GeminiTrainingAssistantAdapter()
            adapter._generate_response = AsyncMock(return_value="Respuesta simulada")
            return adapter

    def test_create_default_context(self, adapter):
        """Prueba la creación del contexto predeterminado."""
        context = adapter._create_default_context()

        assert "conversation_history" in context
        assert "user_profile" in context
        assert "training_plans" in context
        assert "nutrition_recommendations" in context
        assert "progress_analyses" in context
        assert "last_updated" in context

    def test_get_intent_to_query_type_mapping(self, adapter):
        """Prueba el mapeo de intenciones a tipos de consulta."""
        mapping = adapter._get_intent_to_query_type_mapping()

        assert "plan" in mapping
        assert "entrenamiento" in mapping
        assert "nutrición" in mapping
        assert "progreso" in mapping

        assert mapping["plan"] == "generate_training_plan"
        assert mapping["entrenamiento"] == "generate_training_plan"
        assert mapping["nutrición"] == "recommend_nutrition"
        assert mapping["progreso"] == "analyze_progress"

    def test_determine_query_type(self, adapter):
        """Prueba la determinación del tipo de consulta."""
        # Prueba para plan de entrenamiento
        query_type = adapter._determine_query_type("Necesito un plan de entrenamiento")
        assert query_type == "generate_training_plan"

        # Prueba para recomendación nutricional
        query_type = adapter._determine_query_type(
            "Dame consejos de nutrición para ganar masa muscular"
        )
        assert query_type == "recommend_nutrition"

        # Prueba para análisis de progreso
        query_type = adapter._determine_query_type(
            "¿Cómo va mi progreso en el gimnasio?"
        )
        assert query_type == "analyze_progress"

        # Prueba para consulta sin tipo específico (debería devolver answer_fitness_question por defecto)
        query_type = adapter._determine_query_type("¿Cuál es el mejor ejercicio?")
        assert query_type == "answer_fitness_question"

    @pytest.mark.asyncio
    async def test_process_query_training_plan(self, adapter):
        """Prueba el procesamiento de una consulta de tipo generate_training_plan."""
        query = "Necesito un plan de entrenamiento para ganar masa muscular"
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
        assert result["query_type"] == "generate_training_plan"
        assert result["program_type"] == "elite"
        assert "training_context" in state
        assert "training_plans" in state["training_context"]
        assert len(state["training_context"]["training_plans"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_nutrition(self, adapter):
        """Prueba el procesamiento de una consulta de tipo recommend_nutrition."""
        query = "Dame consejos de nutrición para ganar masa muscular"
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
        assert result["query_type"] == "recommend_nutrition"
        assert result["program_type"] == "elite"
        assert "training_context" in state
        assert "nutrition_recommendations" in state["training_context"]
        assert len(state["training_context"]["nutrition_recommendations"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_progress(self, adapter):
        """Prueba el procesamiento de una consulta de tipo analyze_progress."""
        query = "¿Cómo va mi progreso en el gimnasio?"
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
        assert result["query_type"] == "analyze_progress"
        assert result["program_type"] == "elite"
        assert "training_context" in state
        assert "progress_analyses" in state["training_context"]
        assert len(state["training_context"]["progress_analyses"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_fitness_question(self, adapter):
        """Prueba el procesamiento de una consulta de tipo answer_fitness_question."""
        query = "¿Cuál es el mejor ejercicio para bíceps?"
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
        assert result["query_type"] == "answer_fitness_question"
        assert result["program_type"] == "elite"
        assert "training_context" in state
        assert "conversation_history" in state["training_context"]
        assert len(state["training_context"]["conversation_history"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, adapter):
        """Prueba el manejo de errores durante el procesamiento de consultas."""
        query = "Necesito un plan de entrenamiento"
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
    async def test_handle_training_plan(self, adapter):
        """Prueba el método _handle_training_plan."""
        query = "Necesito un plan de entrenamiento para ganar masa muscular"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_training_plan(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["training_plans"]) == 1
        assert result["context"]["training_plans"][0]["query"] == query
        assert "date" in result["context"]["training_plans"][0]
        assert "plan" in result["context"]["training_plans"][0]
        assert result["context"]["training_plans"][0]["program_type"] == program_type

    @pytest.mark.asyncio
    async def test_handle_nutrition_recommendation(self, adapter):
        """Prueba el método _handle_nutrition_recommendation."""
        query = "Dame consejos de nutrición para ganar masa muscular"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_nutrition_recommendation(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["nutrition_recommendations"]) == 1
        assert result["context"]["nutrition_recommendations"][0]["query"] == query
        assert "date" in result["context"]["nutrition_recommendations"][0]
        assert "recommendation" in result["context"]["nutrition_recommendations"][0]
        assert (
            result["context"]["nutrition_recommendations"][0]["program_type"]
            == program_type
        )

    @pytest.mark.asyncio
    async def test_handle_progress_analysis(self, adapter):
        """Prueba el método _handle_progress_analysis."""
        query = "¿Cómo va mi progreso en el gimnasio?"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_progress_analysis(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["progress_analyses"]) == 1
        assert result["context"]["progress_analyses"][0]["query"] == query
        assert "date" in result["context"]["progress_analyses"][0]
        assert "analysis" in result["context"]["progress_analyses"][0]
        assert result["context"]["progress_analyses"][0]["program_type"] == program_type

    @pytest.mark.asyncio
    async def test_handle_fitness_question(self, adapter):
        """Prueba el método _handle_fitness_question."""
        query = "¿Cuál es el mejor ejercicio para bíceps?"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_fitness_question(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["conversation_history"]) == 1
        assert result["context"]["conversation_history"][0]["query"] == query
        assert "date" in result["context"]["conversation_history"][0]
        assert "response" in result["context"]["conversation_history"][0]

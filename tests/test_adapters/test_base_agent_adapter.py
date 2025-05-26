"""
Pruebas para la clase BaseAgentAdapter.

Este módulo contiene pruebas unitarias para verificar el funcionamiento
de la clase base BaseAgentAdapter.
"""

import pytest
from unittest.mock import AsyncMock

from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter


class TestBaseAgentAdapter:
    """Pruebas para la clase BaseAgentAdapter."""

    @pytest.fixture
    def mock_intent_analyzer(self):
        """Fixture para simular IntentAnalyzer."""
        mock = AsyncMock()
        mock.analyze = AsyncMock(return_value=0.8)
        return mock

    @pytest.fixture
    def mock_state_manager(self):
        """Fixture para simular StateManager."""
        mock = AsyncMock()
        mock.get_state = AsyncMock(return_value={})
        mock.update_state = AsyncMock()
        return mock

    @pytest.fixture
    def mock_program_classification_service(self):
        """Fixture para simular ProgramClassificationService."""
        mock = AsyncMock()
        mock.classify_profile = AsyncMock(return_value="elite")
        return mock

    @pytest.fixture
    def adapter(
        self,
        mock_intent_analyzer,
        mock_state_manager,
        mock_program_classification_service,
    ):
        """Fixture para crear una instancia de BaseAgentAdapter con mocks."""

        # Crear una subclase concreta de BaseAgentAdapter para pruebas
        class ConcreteAdapter(BaseAgentAdapter):
            async def _process_query(
                self, query, user_id, session_id, program_type, state, profile, **kwargs
            ):
                return {
                    "success": True,
                    "output": f"Respuesta para {query}",
                    "query_type": "test",
                    "program_type": program_type,
                }

            def _create_default_context(self):
                return {"test": "context"}

            def _get_intent_to_query_type_mapping(self):
                return {"test": "test_query"}

        adapter = ConcreteAdapter()
        adapter.intent_analyzer = mock_intent_analyzer
        adapter.state_manager = mock_state_manager
        adapter.program_classification_service = mock_program_classification_service
        adapter.fallback_keywords = ["test", "keyword"]
        return adapter

    @pytest.mark.asyncio
    async def test_classify_query(self, adapter):
        """Prueba para el método _classify_query."""
        score, metadata = await adapter._classify_query("test query", "user123")

        # Verificar que se llamó al analizador de intenciones
        adapter.intent_analyzer.analyze.assert_called_once()

        # Verificar que la puntuación es mayor que 0
        assert score > 0

        # Verificar que los metadatos contienen los campos esperados
        assert "intent_score" in metadata
        assert "keyword_score" in metadata
        assert "combined_score" in metadata
        assert "final_score" in metadata
        assert "agent" in metadata
        assert "timestamp" in metadata

    @pytest.mark.asyncio
    async def test_get_program_type_from_profile(self, adapter):
        """Prueba para el método _get_program_type_from_profile."""
        profile = {"user_id": "user123", "goals": ["muscle", "strength"]}
        program_type = await adapter._get_program_type_from_profile(profile)

        # Verificar que se llamó al servicio de clasificación
        adapter.program_classification_service.classify_profile.assert_called_once_with(
            profile
        )

        # Verificar que el tipo de programa es el esperado
        assert program_type == "elite"

        # Probar manejo de errores
        adapter.program_classification_service.classify_profile.side_effect = Exception(
            "Test error"
        )
        program_type = await adapter._get_program_type_from_profile(profile)

        # Verificar que se devuelve el valor por defecto en caso de error
        assert program_type == "general"

    @pytest.mark.asyncio
    async def test_run_async_impl(self, adapter):
        """Prueba para el método run_async_impl."""
        # Configurar el mock para get_state
        adapter.state_manager.get_state.return_value = {"history": []}

        # Ejecutar el método
        response = await adapter.run_async_impl(
            "test query",
            user_id="user123",
            session_id="session456",
            profile={"user_id": "user123"},
        )

        # Verificar que se llamó a get_state
        adapter.state_manager.get_state.assert_called_once_with("user123", "session456")

        # Verificar que se llamó a update_state
        adapter.state_manager.update_state.assert_called_once()

        # Verificar la respuesta
        assert response["success"] is True
        assert "output" in response
        assert "query_type" in response
        assert response["program_type"] == "elite"

    @pytest.mark.asyncio
    async def test_run_async_impl_error(self, adapter):
        """Prueba para el manejo de errores en run_async_impl."""
        # Configurar el mock para _process_query para que lance una excepción
        adapter._process_query = AsyncMock(side_effect=Exception("Test error"))

        # Ejecutar el método
        response = await adapter.run_async_impl(
            "test query", user_id="user123", session_id="session456"
        )

        # Verificar la respuesta de error
        assert response["success"] is False
        assert "error" in response
        assert response["error"] == "Test error"
        assert "agent" in response
        assert "timestamp" in response

    def test_check_keywords(self, adapter):
        """Prueba para el método _check_keywords."""
        # Consulta con palabras clave
        score = adapter._check_keywords("Esta es una consulta de test")
        assert score > 0

        # Consulta sin palabras clave
        score = adapter._check_keywords("Esta es una consulta sin coincidencias")
        assert score == 0

        # Caso con lista de palabras clave vacía
        adapter.fallback_keywords = []
        score = adapter._check_keywords("Esta es una consulta de test")
        assert score == 0

    def test_has_excluded_keywords(self, adapter):
        """Prueba para el método _has_excluded_keywords."""
        # Configurar palabras clave excluidas
        adapter.excluded_keywords = ["excluir", "ignorar"]

        # Consulta con palabras clave excluidas
        result = adapter._has_excluded_keywords(
            "Esta consulta debe excluir ciertos términos"
        )
        assert result is True

        # Consulta sin palabras clave excluidas
        result = adapter._has_excluded_keywords("Esta es una consulta normal")
        assert result is False

        # Caso con lista de palabras clave excluidas vacía
        adapter.excluded_keywords = []
        result = adapter._has_excluded_keywords(
            "Esta consulta debe excluir ciertos términos"
        )
        assert result is False

    def test_adjust_score_based_on_context(self, adapter):
        """Prueba para el método _adjust_score_based_on_context."""
        # La implementación base no realiza ajustes
        score = adapter._adjust_score_based_on_context(0.8, {})
        assert score == 0.8

        # Probar con un contexto no vacío
        score = adapter._adjust_score_based_on_context(0.8, {"key": "value"})
        assert score == 0.8

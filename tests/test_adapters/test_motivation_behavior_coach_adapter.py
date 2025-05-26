"""
Pruebas unitarias para el adaptador MotivationBehaviorCoach.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from infrastructure.adapters.motivation_behavior_coach_adapter import (
    MotivationBehaviorCoachAdapter,
)


class TestMotivationBehaviorCoachAdapter:
    """Pruebas para MotivationBehaviorCoachAdapter."""

    @pytest.fixture
    def adapter(self):
        """Fixture que proporciona una instancia del adaptador."""
        with patch(
            "infrastructure.adapters.motivation_behavior_coach_adapter.MotivationBehaviorCoach.__init__",
            return_value=None,
        ):
            adapter = MotivationBehaviorCoachAdapter()
            adapter._generate_response = AsyncMock(return_value="Respuesta simulada")
            return adapter

    def test_create_default_context(self, adapter):
        """Prueba la creación del contexto predeterminado."""
        context = adapter._create_default_context()

        assert "conversation_history" in context
        assert "user_profile" in context
        assert "habit_plans" in context
        assert "goal_plans" in context
        assert "motivation_strategies" in context
        assert "behavior_change_plans" in context
        assert "obstacle_management_plans" in context
        assert "last_updated" in context

    def test_get_intent_to_query_type_mapping(self, adapter):
        """Prueba el mapeo de intenciones a tipos de consulta."""
        mapping = adapter._get_intent_to_query_type_mapping()

        assert "hábito" in mapping
        assert "motivación" in mapping
        assert "comportamiento" in mapping
        assert "meta" in mapping
        assert "obstáculo" in mapping

        assert mapping["hábito"] == "habit_formation"
        assert mapping["motivación"] == "motivation_strategies"
        assert mapping["comportamiento"] == "behavior_change"
        assert mapping["meta"] == "goal_setting"
        assert mapping["obstáculo"] == "obstacle_management"

    def test_determine_query_type(self, adapter):
        """Prueba la determinación del tipo de consulta."""
        # Prueba para formación de hábitos
        query_type = adapter._determine_query_type(
            "Quiero crear un hábito de meditación diaria"
        )
        assert query_type == "habit_formation"

        # Prueba para estrategias de motivación
        query_type = adapter._determine_query_type(
            "Necesito motivación para seguir con mi dieta"
        )
        assert query_type == "motivation_strategies"

        # Prueba para cambio de comportamiento
        query_type = adapter._determine_query_type(
            "Quiero cambiar mi comportamiento sedentario"
        )
        assert query_type == "behavior_change"

        # Prueba para establecimiento de metas
        query_type = adapter._determine_query_type(
            "Ayúdame a establecer una meta para correr un maratón"
        )
        assert query_type == "goal_setting"

        # Prueba para manejo de obstáculos
        query_type = adapter._determine_query_type(
            "Tengo un obstáculo para mantener mi rutina de ejercicio"
        )
        assert query_type == "obstacle_management"

        # Prueba para consulta sin tipo específico (debería devolver habit_formation por defecto)
        query_type = adapter._determine_query_type("¿Cómo puedo mejorar mi vida?")
        assert query_type == "habit_formation"

    @pytest.mark.asyncio
    async def test_process_query_habit_formation(self, adapter):
        """Prueba el procesamiento de una consulta de tipo habit_formation."""
        query = "Quiero crear un hábito de meditación diaria"
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
        assert result["query_type"] == "habit_formation"
        assert result["program_type"] == "elite"
        assert "motivation_context" in state
        assert "habit_plans" in state["motivation_context"]
        assert len(state["motivation_context"]["habit_plans"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_motivation_strategies(self, adapter):
        """Prueba el procesamiento de una consulta de tipo motivation_strategies."""
        query = "Necesito motivación para seguir con mi dieta"
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
        assert result["query_type"] == "motivation_strategies"
        assert result["program_type"] == "elite"
        assert "motivation_context" in state
        assert "motivation_strategies" in state["motivation_context"]
        assert len(state["motivation_context"]["motivation_strategies"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_behavior_change(self, adapter):
        """Prueba el procesamiento de una consulta de tipo behavior_change."""
        query = "Quiero cambiar mi comportamiento sedentario"
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
        assert result["query_type"] == "behavior_change"
        assert result["program_type"] == "elite"
        assert "motivation_context" in state
        assert "behavior_change_plans" in state["motivation_context"]
        assert len(state["motivation_context"]["behavior_change_plans"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_goal_setting(self, adapter):
        """Prueba el procesamiento de una consulta de tipo goal_setting."""
        query = "Ayúdame a establecer una meta para correr un maratón"
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
        assert result["query_type"] == "goal_setting"
        assert result["program_type"] == "elite"
        assert "motivation_context" in state
        assert "goal_plans" in state["motivation_context"]
        assert len(state["motivation_context"]["goal_plans"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_obstacle_management(self, adapter):
        """Prueba el procesamiento de una consulta de tipo obstacle_management."""
        query = "Tengo un obstáculo para mantener mi rutina de ejercicio"
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
        assert result["query_type"] == "obstacle_management"
        assert result["program_type"] == "elite"
        assert "motivation_context" in state
        assert "obstacle_management_plans" in state["motivation_context"]
        assert len(state["motivation_context"]["obstacle_management_plans"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_generic(self, adapter):
        """Prueba el procesamiento de una consulta genérica."""
        query = "¿Cómo puedo mejorar mi vida?"
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
        assert result["program_type"] == "elite"
        assert "motivation_context" in state
        assert "conversation_history" in state["motivation_context"]
        assert len(state["motivation_context"]["conversation_history"]) == 1

    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, adapter):
        """Prueba el manejo de errores durante el procesamiento de consultas."""
        query = "Quiero crear un hábito de meditación diaria"
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
    async def test_handle_habit_formation(self, adapter):
        """Prueba el método _handle_habit_formation."""
        query = "Quiero crear un hábito de meditación diaria"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_habit_formation(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["habit_plans"]) == 1
        assert result["context"]["habit_plans"][0]["query"] == query
        assert "date" in result["context"]["habit_plans"][0]
        assert "plan" in result["context"]["habit_plans"][0]
        assert result["context"]["habit_plans"][0]["program_type"] == program_type

    @pytest.mark.asyncio
    async def test_handle_motivation_strategies(self, adapter):
        """Prueba el método _handle_motivation_strategies."""
        query = "Necesito motivación para seguir con mi dieta"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_motivation_strategies(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["motivation_strategies"]) == 1
        assert result["context"]["motivation_strategies"][0]["query"] == query
        assert "date" in result["context"]["motivation_strategies"][0]
        assert "strategies" in result["context"]["motivation_strategies"][0]
        assert (
            result["context"]["motivation_strategies"][0]["program_type"]
            == program_type
        )

    @pytest.mark.asyncio
    async def test_handle_behavior_change(self, adapter):
        """Prueba el método _handle_behavior_change."""
        query = "Quiero cambiar mi comportamiento sedentario"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_behavior_change(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["behavior_change_plans"]) == 1
        assert result["context"]["behavior_change_plans"][0]["query"] == query
        assert "date" in result["context"]["behavior_change_plans"][0]
        assert "plan" in result["context"]["behavior_change_plans"][0]
        assert (
            result["context"]["behavior_change_plans"][0]["program_type"]
            == program_type
        )

    @pytest.mark.asyncio
    async def test_handle_goal_setting(self, adapter):
        """Prueba el método _handle_goal_setting."""
        query = "Ayúdame a establecer una meta para correr un maratón"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_goal_setting(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["goal_plans"]) == 1
        assert result["context"]["goal_plans"][0]["query"] == query
        assert "date" in result["context"]["goal_plans"][0]
        assert "plan" in result["context"]["goal_plans"][0]
        assert result["context"]["goal_plans"][0]["program_type"] == program_type

    @pytest.mark.asyncio
    async def test_handle_obstacle_management(self, adapter):
        """Prueba el método _handle_obstacle_management."""
        query = "Tengo un obstáculo para mantener mi rutina de ejercicio"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_obstacle_management(
            query, context, profile, program_type
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["obstacle_management_plans"]) == 1
        assert result["context"]["obstacle_management_plans"][0]["query"] == query
        assert "date" in result["context"]["obstacle_management_plans"][0]
        assert "plan" in result["context"]["obstacle_management_plans"][0]
        assert (
            result["context"]["obstacle_management_plans"][0]["program_type"]
            == program_type
        )

    @pytest.mark.asyncio
    async def test_handle_generic_query(self, adapter):
        """Prueba el método _handle_generic_query."""
        query = "¿Cómo puedo mejorar mi vida?"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"

        result = await adapter._handle_generic_query(
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

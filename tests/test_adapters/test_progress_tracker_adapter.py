"""
Pruebas unitarias para el adaptador ProgressTracker.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from infrastructure.adapters.progress_tracker_adapter import ProgressTrackerAdapter


class TestProgressTrackerAdapter:
    """Pruebas para ProgressTrackerAdapter."""

    @pytest.fixture
    def adapter(self):
        """Fixture que proporciona una instancia del adaptador."""
        with patch(
            "infrastructure.adapters.progress_tracker_adapter.ProgressTracker.__init__",
            return_value=None,
        ):
            adapter = ProgressTrackerAdapter()
            adapter._generate_response = AsyncMock(return_value="Respuesta simulada")
            return adapter

    def test_create_default_context(self, adapter):
        """Prueba la creación del contexto predeterminado."""
        context = adapter._create_default_context()

        assert "conversation_history" in context
        assert "user_profile" in context
        assert "progress_analyses" in context
        assert "progress_visualizations" in context
        assert "progress_comparisons" in context
        assert "metrics_tracked" in context
        assert "last_updated" in context

    def test_get_intent_to_query_type_mapping(self, adapter):
        """Prueba el mapeo de intenciones a tipos de consulta."""
        mapping = adapter._get_intent_to_query_type_mapping()

        assert "análisis" in mapping
        assert "gráfico" in mapping
        assert "comparar" in mapping

        assert mapping["análisis"] == "analyze_progress"
        assert mapping["gráfico"] == "visualize_progress"
        assert mapping["comparar"] == "compare_progress"

    def test_determine_query_type(self, adapter):
        """Prueba la determinación del tipo de consulta."""
        # Prueba para análisis de progreso
        query_type = adapter._determine_query_type("Analiza mi progreso de peso")
        assert query_type == "analyze_progress"

        # Prueba para visualización de progreso
        query_type = adapter._determine_query_type(
            "Muéstrame un gráfico de mi progreso"
        )
        assert query_type == "visualize_progress"

        # Prueba para comparación de progreso
        query_type = adapter._determine_query_type(
            "Compara mi progreso entre la semana pasada y este mes"
        )
        assert query_type == "compare_progress"

        # Prueba para palabras clave adicionales de visualización
        query_type = adapter._determine_query_type(
            "Quiero ver una gráfica de mi progreso"
        )
        assert query_type == "visualize_progress"

        # Prueba para palabras clave adicionales de comparación
        query_type = adapter._determine_query_type(
            "Diferencia entre mi rendimiento de la semana pasada y este mes"
        )
        assert query_type == "compare_progress"

        # Prueba para consulta sin tipo específico (debería devolver analyze_progress por defecto)
        query_type = adapter._determine_query_type("¿Cómo voy con mi entrenamiento?")
        assert query_type == "analyze_progress"

    def test_extract_metrics_from_query(self, adapter):
        """Prueba la extracción de métricas de la consulta."""
        # Prueba con una métrica en español
        metrics = adapter._extract_metrics_from_query("Analiza mi progreso de peso")
        assert "weight" in metrics

        # Prueba con una métrica en inglés
        metrics = adapter._extract_metrics_from_query("Show my weight progress")
        assert "weight" in metrics

        # Prueba con múltiples métricas
        metrics = adapter._extract_metrics_from_query(
            "Compara mi peso y fuerza durante el último mes"
        )
        assert "weight" in metrics
        assert "strength" in metrics

        # Prueba con métricas que requieren normalización
        metrics = adapter._extract_metrics_from_query(
            "Analiza mi masa muscular y grasa corporal"
        )
        assert "muscle_mass" in metrics
        assert "body_fat" in metrics

        # Prueba sin métricas específicas (debería devolver weight por defecto)
        metrics = adapter._extract_metrics_from_query("¿Cómo voy con mi progreso?")
        assert metrics == ["weight"]

    def test_extract_time_periods_from_query(self, adapter):
        """Prueba la extracción de periodos de tiempo de la consulta."""
        # Prueba con un periodo en español
        periods = adapter._extract_time_periods_from_query(
            "Analiza mi progreso de la última semana"
        )
        assert "last_week" in periods

        # Prueba con un periodo en inglés
        periods = adapter._extract_time_periods_from_query(
            "Show my progress from last month"
        )
        assert "last_month" in periods

        # Prueba con múltiples periodos
        periods = adapter._extract_time_periods_from_query(
            "Compara mi progreso entre la última semana y el último mes"
        )
        assert "last_week" in periods
        assert "last_month" in periods

        # Prueba para consulta de comparación con un solo periodo (debería añadir otro)
        with patch.object(
            adapter, "_determine_query_type", return_value="compare_progress"
        ):
            periods = adapter._extract_time_periods_from_query(
                "Compara mi progreso de la última semana"
            )
            assert len(periods) == 2
            assert "last_week" in periods
            assert "last_month" in periods

        # Prueba sin periodos específicos (debería devolver last_week por defecto)
        periods = adapter._extract_time_periods_from_query("¿Cómo voy con mi progreso?")
        assert periods == ["last_week"]

    @pytest.mark.asyncio
    async def test_process_query_analyze_progress(self, adapter):
        """Prueba el procesamiento de una consulta de tipo analyze_progress."""
        query = "Analiza mi progreso de peso de la última semana"
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
        assert "progress_context" in state
        assert "progress_analyses" in state["progress_context"]
        assert len(state["progress_context"]["progress_analyses"]) == 1
        assert "metrics_tracked" in state["progress_context"]
        assert "weight" in state["progress_context"]["metrics_tracked"]

    @pytest.mark.asyncio
    async def test_process_query_visualize_progress(self, adapter):
        """Prueba el procesamiento de una consulta de tipo visualize_progress."""
        query = "Muéstrame un gráfico de mi peso del último mes"
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
        assert result["query_type"] == "visualize_progress"
        assert result["program_type"] == "elite"
        assert "visualization_url" in result
        assert "progress_context" in state
        assert "progress_visualizations" in state["progress_context"]
        assert len(state["progress_context"]["progress_visualizations"]) == 1
        assert "metrics_tracked" in state["progress_context"]
        assert "weight" in state["progress_context"]["metrics_tracked"]

    @pytest.mark.asyncio
    async def test_process_query_compare_progress(self, adapter):
        """Prueba el procesamiento de una consulta de tipo compare_progress."""
        query = "Compara mi progreso de peso entre la última semana y el último mes"
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
        assert result["query_type"] == "compare_progress"
        assert result["program_type"] == "elite"
        assert "progress_context" in state
        assert "progress_comparisons" in state["progress_context"]
        assert len(state["progress_context"]["progress_comparisons"]) == 1
        assert "metrics_tracked" in state["progress_context"]
        assert "weight" in state["progress_context"]["metrics_tracked"]

    @pytest.mark.asyncio
    async def test_process_query_error_handling(self, adapter):
        """Prueba el manejo de errores durante el procesamiento de consultas."""
        query = "Analiza mi progreso de peso"
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
    async def test_handle_analyze_progress(self, adapter):
        """Prueba el método _handle_analyze_progress."""
        query = "Analiza mi progreso de peso de la última semana"
        user_id = "user123"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"
        metrics = ["weight"]
        time_periods = ["last_week"]

        result = await adapter._handle_analyze_progress(
            query, user_id, context, profile, program_type, metrics, time_periods
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["progress_analyses"]) == 1
        assert result["context"]["progress_analyses"][0]["query"] == query
        assert "date" in result["context"]["progress_analyses"][0]
        assert "metrics" in result["context"]["progress_analyses"][0]
        assert "time_period" in result["context"]["progress_analyses"][0]
        assert "analysis" in result["context"]["progress_analyses"][0]
        assert result["context"]["progress_analyses"][0]["program_type"] == program_type
        assert "metrics_tracked" in result["context"]
        assert "weight" in result["context"]["metrics_tracked"]

    @pytest.mark.asyncio
    async def test_handle_visualize_progress(self, adapter):
        """Prueba el método _handle_visualize_progress."""
        query = "Muéstrame un gráfico de mi peso del último mes"
        user_id = "user123"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"
        metrics = ["weight"]
        time_periods = ["last_month"]

        result = await adapter._handle_visualize_progress(
            query, user_id, context, profile, program_type, metrics, time_periods
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "visualization_url" in result
        assert "context" in result
        assert len(result["context"]["progress_visualizations"]) == 1
        assert result["context"]["progress_visualizations"][0]["query"] == query
        assert "date" in result["context"]["progress_visualizations"][0]
        assert "metric" in result["context"]["progress_visualizations"][0]
        assert "time_period" in result["context"]["progress_visualizations"][0]
        assert "chart_type" in result["context"]["progress_visualizations"][0]
        assert "visualization_url" in result["context"]["progress_visualizations"][0]
        assert "description" in result["context"]["progress_visualizations"][0]
        assert (
            result["context"]["progress_visualizations"][0]["program_type"]
            == program_type
        )
        assert "metrics_tracked" in result["context"]
        assert "weight" in result["context"]["metrics_tracked"]

    @pytest.mark.asyncio
    async def test_handle_compare_progress(self, adapter):
        """Prueba el método _handle_compare_progress."""
        query = "Compara mi progreso de peso entre la última semana y el último mes"
        user_id = "user123"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"
        metrics = ["weight"]
        time_periods = ["last_week", "last_month"]

        result = await adapter._handle_compare_progress(
            query, user_id, context, profile, program_type, metrics, time_periods
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["progress_comparisons"]) == 1
        assert result["context"]["progress_comparisons"][0]["query"] == query
        assert "date" in result["context"]["progress_comparisons"][0]
        assert "metrics" in result["context"]["progress_comparisons"][0]
        assert "period1" in result["context"]["progress_comparisons"][0]
        assert "period2" in result["context"]["progress_comparisons"][0]
        assert "comparison" in result["context"]["progress_comparisons"][0]
        assert (
            result["context"]["progress_comparisons"][0]["program_type"] == program_type
        )
        assert "metrics_tracked" in result["context"]
        assert "weight" in result["context"]["metrics_tracked"]

    @pytest.mark.asyncio
    async def test_handle_compare_progress_with_single_period(self, adapter):
        """Prueba el método _handle_compare_progress con un solo periodo."""
        query = "Compara mi progreso de peso de la última semana"
        user_id = "user123"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"
        metrics = ["weight"]
        time_periods = ["last_week"]

        result = await adapter._handle_compare_progress(
            query, user_id, context, profile, program_type, metrics, time_periods
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["progress_comparisons"]) == 1
        assert "period1" in result["context"]["progress_comparisons"][0]
        assert "period2" in result["context"]["progress_comparisons"][0]
        assert result["context"]["progress_comparisons"][0]["period1"] == "last_week"
        assert result["context"]["progress_comparisons"][0]["period2"] == "last_month"

    @pytest.mark.asyncio
    async def test_handle_compare_progress_with_no_periods(self, adapter):
        """Prueba el método _handle_compare_progress sin periodos."""
        query = "Compara mi progreso de peso"
        user_id = "user123"
        context = adapter._create_default_context()
        profile = {"name": "Test User", "age": 30}
        program_type = "elite"
        metrics = ["weight"]
        time_periods = []

        result = await adapter._handle_compare_progress(
            query, user_id, context, profile, program_type, metrics, time_periods
        )

        adapter._generate_response.assert_called_once()
        assert "response" in result
        assert "context" in result
        assert len(result["context"]["progress_comparisons"]) == 1
        assert "period1" in result["context"]["progress_comparisons"][0]
        assert "period2" in result["context"]["progress_comparisons"][0]
        assert result["context"]["progress_comparisons"][0]["period1"] == "last_week"
        assert result["context"]["progress_comparisons"][0]["period2"] == "last_month"

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

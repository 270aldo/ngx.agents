"""
Pruebas para el adaptador del agente ProgressTracker.

Este módulo contiene pruebas unitarias para verificar el correcto funcionamiento
del adaptador del agente ProgressTracker con los componentes optimizados.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime
import numpy as np
import os

from infrastructure.adapters.progress_tracker_adapter import ProgressTrackerAdapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter

# Fixtures
@pytest.fixture
def progress_tracker_adapter():
    """Fixture que proporciona una instancia del adaptador ProgressTracker."""
    # Crear mocks para las dependencias
    gemini_client_mock = AsyncMock()
    gemini_client_mock.generate_response = AsyncMock(return_value="Respuesta simulada")
    gemini_client_mock.generate_structured_output = AsyncMock(return_value={
        "analysis_summary": "Tendencia positiva en rendimiento",
        "metrics": {
            "weight": {
                "trend": "decreasing",
                "change_percentage": "-2.5%"
            },
            "performance": {
                "trend": "increasing",
                "change_percentage": "+5.8%"
            }
        },
        "recommendations": ["Mantener la rutina actual", "Aumentar hidratación"]
    })
    
    supabase_client_mock = MagicMock()
    
    mcp_toolkit_mock = MagicMock()
    
    # Crear instancia del adaptador con mocks
    adapter = ProgressTrackerAdapter(
        agent_id="test_progress_tracker",
        gemini_client=gemini_client_mock,
        supabase_client=supabase_client_mock,
        mcp_toolkit=mcp_toolkit_mock
    )
    
    # Mock para matplotlib
    with patch('matplotlib.pyplot.savefig'):
        with patch('matplotlib.pyplot.close'):
            yield adapter

# Pruebas
@pytest.mark.asyncio
async def test_get_context(progress_tracker_adapter):
    """Prueba el método _get_context del adaptador."""
    # Mock para state_manager_adapter.load_state
    with patch.object(state_manager_adapter, 'load_state', new_callable=AsyncMock) as mock_load_state:
        # Configurar el mock para devolver un contexto de prueba
        mock_load_state.return_value = {
            "history": [
                {"role": "user", "content": "Muéstrame mi progreso de peso"}
            ],
            "analyses": [{"id": "analysis_123", "date": "2025-10-01", "metric": "weight"}],
            "visualizations": [{"id": "viz_123", "date": "2025-10-01", "metric": "weight"}],
            "comparisons": [],
            "last_updated": datetime.now().isoformat()
        }
        
        # Llamar al método a probar
        context = await progress_tracker_adapter._get_context("test_user", "test_session")
        
        # Verificar que se llamó al método load_state del adaptador
        mock_load_state.assert_called_once_with("test_user", "test_session")
        
        # Verificar que el contexto devuelto es el esperado
        assert "history" in context
        assert "analyses" in context
        assert "visualizations" in context
        assert "comparisons" in context
        assert len(context["analyses"]) == 1
        assert context["analyses"][0]["id"] == "analysis_123"

@pytest.mark.asyncio
async def test_update_context(progress_tracker_adapter):
    """Prueba el método _update_context del adaptador."""
    # Mock para state_manager_adapter.save_state
    with patch.object(state_manager_adapter, 'save_state', new_callable=AsyncMock) as mock_save_state:
        # Crear un contexto de prueba
        test_context = {
            "history": [
                {"role": "user", "content": "Muéstrame mi progreso de peso"},
                {"role": "assistant", "content": "Aquí tienes el análisis de tu progreso..."}
            ],
            "analyses": [
                {"id": "analysis_123", "date": "2025-10-01", "metric": "weight", "result": {"trend": "decreasing"}}
            ],
            "visualizations": [
                {"id": "viz_123", "date": "2025-10-01", "metric": "weight", "url": "file:///tmp/viz.png"}
            ],
            "comparisons": [],
            "last_updated": datetime.now().isoformat()
        }
        
        # Llamar al método a probar
        await progress_tracker_adapter._update_context(test_context, "test_user", "test_session")
        
        # Verificar que se llamó al método save_state del adaptador
        mock_save_state.assert_called_once()
        
        # Verificar que se pasaron los argumentos correctos
        args, kwargs = mock_save_state.call_args
        assert args[0] == "test_user"
        assert args[1] == "test_session"
        assert "history" in args[2]
        assert "analyses" in args[2]
        assert "visualizations" in args[2]
        assert "last_updated" in args[2]

@pytest.mark.asyncio
async def test_classify_query(progress_tracker_adapter):
    """Prueba el método _classify_query del adaptador."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(intent_analyzer_adapter, 'analyze_intent', new_callable=AsyncMock) as mock_analyze_intent:
        # Configurar el mock para devolver un análisis de intención
        mock_analyze_intent.return_value = {
            "primary_intent": "visualize",
            "confidence": 0.85,
            "entities": [
                {"type": "metric", "value": "peso"},
                {"type": "time_period", "value": "último mes"}
            ]
        }
        
        # Llamar al método a probar
        query_type = await progress_tracker_adapter._classify_query("Muéstrame una gráfica de mi peso del último mes")
        
        # Verificar que se llamó al método analyze_intent del adaptador
        mock_analyze_intent.assert_called_once()
        
        # Verificar que el tipo de consulta devuelto es el esperado
        assert query_type == "visualize_progress"

@pytest.mark.asyncio
async def test_consult_other_agent(progress_tracker_adapter):
    """Prueba el método _consult_other_agent del adaptador."""
    # Mock para a2a_adapter.call_agent
    with patch.object(a2a_adapter, 'call_agent', new_callable=AsyncMock) as mock_call_agent:
        # Configurar el mock para devolver una respuesta simulada
        mock_call_agent.return_value = {
            "status": "success",
            "output": "Respuesta del agente consultado",
            "agent_id": "test_agent",
            "agent_name": "Test Agent"
        }
        
        # Llamar al método a probar
        response = await progress_tracker_adapter._consult_other_agent(
            agent_id="test_agent",
            query="¿Qué ejercicios recomiendas para mejorar mi rendimiento?",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Verificar que se llamó al método call_agent del adaptador
        mock_call_agent.assert_called_once()
        
        # Verificar que la respuesta devuelta es la esperada
        assert response["status"] == "success"
        assert "Respuesta del agente consultado" in response["output"]
        assert response["agent_id"] == "test_agent"

@pytest.mark.asyncio
async def test_skill_analyze_progress(progress_tracker_adapter):
    """Prueba el método _skill_analyze_progress del adaptador."""
    # Importar la clase de entrada para la skill
    from agents.progress_tracker.schemas import AnalyzeProgressInput
    
    # Mock para _get_user_data
    with patch.object(progress_tracker_adapter, '_get_user_data', new_callable=AsyncMock) as mock_get_user_data:
        # Configurar el mock para devolver datos simulados
        mock_get_user_data.return_value = {
            "weight": [
                {"date": "2025-09-01", "value": 75.5},
                {"date": "2025-09-15", "value": 74.8},
                {"date": "2025-10-01", "value": 73.9}
            ],
            "performance": [
                {"date": "2025-09-01", "value": 82.0},
                {"date": "2025-09-15", "value": 85.5},
                {"date": "2025-10-01", "value": 87.2}
            ]
        }
        
        # Crear datos de entrada para la skill
        input_data = AnalyzeProgressInput(
            user_id="test_user",
            time_period="last_month",
            metrics=["weight", "performance"]
        )
        
        # Llamar al método a probar
        result = await progress_tracker_adapter._skill_analyze_progress(input_data)
        
        # Verificar que se llamó al método _get_user_data
        mock_get_user_data.assert_called_once()
        
        # Verificar que el resultado tiene la estructura esperada
        assert hasattr(result, "analysis_id")
        assert hasattr(result, "result")
        assert hasattr(result, "status")
        assert result.status == "success"

@pytest.mark.asyncio
async def test_skill_visualize_progress(progress_tracker_adapter):
    """Prueba el método _skill_visualize_progress del adaptador."""
    # Importar la clase de entrada para la skill
    from agents.progress_tracker.schemas import VisualizeProgressInput
    
    # Mock para _get_user_data
    with patch.object(progress_tracker_adapter, '_get_user_data', new_callable=AsyncMock) as mock_get_user_data:
        # Configurar el mock para devolver datos simulados
        mock_get_user_data.return_value = {
            "weight": [
                {"date": "2025-09-01", "value": 75.5},
                {"date": "2025-09-15", "value": 74.8},
                {"date": "2025-10-01", "value": 73.9}
            ]
        }
        
        # Mock para matplotlib
        with patch('matplotlib.pyplot.figure'):
            with patch('matplotlib.pyplot.plot'):
                with patch('matplotlib.pyplot.savefig'):
                    with patch('matplotlib.pyplot.close'):
                        # Crear datos de entrada para la skill
                        input_data = VisualizeProgressInput(
                            user_id="test_user",
                            metric="weight",
                            time_period="last_month",
                            chart_type="line"
                        )
                        
                        # Llamar al método a probar
                        result = await progress_tracker_adapter._skill_visualize_progress(input_data)
                        
                        # Verificar que se llamó al método _get_user_data
                        mock_get_user_data.assert_called_once()
                        
                        # Verificar que el resultado tiene la estructura esperada
                        assert hasattr(result, "visualization_url")
                        assert hasattr(result, "filepath")
                        assert hasattr(result, "status")
                        assert result.status == "success"

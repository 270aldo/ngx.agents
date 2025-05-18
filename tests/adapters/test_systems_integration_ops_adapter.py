"""
Pruebas para el adaptador del agente SystemsIntegrationOps.

Este módulo contiene pruebas unitarias para verificar el correcto funcionamiento
del adaptador del agente SystemsIntegrationOps con los componentes optimizados.
"""


import os
# Configurar modo mock para pruebas
os.environ["MOCK_MODE"] = "True"
os.environ["MOCK_VERTEX_AI"] = "True"
os.environ["MOCK_A2A"] = "True"

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime

from infrastructure.adapters.systems_integration_ops_adapter import SystemsIntegrationOpsAdapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter

# Fixtures
@pytest.fixture
def systems_integration_ops_adapter():
    """Fixture que proporciona una instancia del adaptador SystemsIntegrationOps."""
    # Crear mocks para las dependencias
    gemini_client_mock = AsyncMock()
    gemini_client_mock.generate_response = AsyncMock(return_value="Respuesta simulada")
    gemini_client_mock.generate_structured_output = AsyncMock(return_value={
        "integration_plan": {
            "systems": ["Garmin Connect", "Apple HealthKit"],
            "steps": ["Configurar API keys", "Implementar OAuth", "Desarrollar endpoints"]
        }
    })
    
    supabase_client_mock = MagicMock()
    
    mcp_toolkit_mock = MagicMock()
    
    # Crear instancia del adaptador con mocks
    adapter = SystemsIntegrationOpsAdapter(
        gemini_client=gemini_client_mock,
        supabase_client=supabase_client_mock
    )
    
    return adapter

# Pruebas
@pytest.mark.asyncio
async def test_get_context(systems_integration_ops_adapter):
    """Prueba el método _get_context del adaptador."""
    # Mock para state_manager_adapter.load_state
    with patch.object(state_manager_adapter, 'load_state', new_callable=AsyncMock) as mock_load_state:
        # Configurar el mock para devolver un contexto de prueba
        mock_load_state.return_value = {
            "conversation_history": [
                {"role": "user", "content": "¿Cómo puedo integrar mi aplicación con Garmin Connect?"}
            ],
            "user_profile": {"company": "FitTech", "industry": "Fitness"},
            "integration_requests": [{"timestamp": "2025-10-01T12:00:00", "systems": ["Garmin Connect"]}],
            "automation_requests": [],
            "api_requests": [],
            "infrastructure_requests": [],
            "data_pipeline_requests": [],
            "last_updated": datetime.now().isoformat()
        }
        
        # Llamar al método a probar
        context = await systems_integration_ops_adapter._get_context("test_user", "test_session")
        
        # Verificar que se llamó al método load_state del adaptador
        mock_load_state.assert_called_once_with("test_user", "test_session")
        
        # Verificar que el contexto devuelto es el esperado
        assert "conversation_history" in context
        assert "user_profile" in context
        assert "integration_requests" in context
        assert len(context["integration_requests"]) == 1
        assert context["integration_requests"][0]["systems"][0] == "Garmin Connect"

@pytest.mark.asyncio
async def test_update_context(systems_integration_ops_adapter):
    """Prueba el método _update_context del adaptador."""
    # Mock para state_manager_adapter.save_state
    with patch.object(state_manager_adapter, 'save_state', new_callable=AsyncMock) as mock_save_state:
        # Crear un contexto de prueba
        test_context = {
            "conversation_history": [
                {"role": "user", "content": "¿Cómo puedo integrar mi aplicación con Garmin Connect?"},
                {"role": "assistant", "content": "Para integrar tu aplicación con Garmin Connect, necesitarás..."}
            ],
            "user_profile": {"company": "FitTech", "industry": "Fitness"},
            "integration_requests": [{"timestamp": "2025-10-01T12:00:00", "systems": ["Garmin Connect"]}],
            "automation_requests": [],
            "api_requests": [],
            "infrastructure_requests": [],
            "data_pipeline_requests": [],
            "last_updated": datetime.now().isoformat()
        }
        
        # Llamar al método a probar
        await systems_integration_ops_adapter._update_context(test_context, "test_user", "test_session")
        
        # Verificar que se llamó al método save_state del adaptador
        mock_save_state.assert_called_once()
        
        # Verificar que se pasaron los argumentos correctos
        args, kwargs = mock_save_state.call_args
        assert args[0] == "test_user"
        assert args[1] == "test_session"
        assert "conversation_history" in args[2]
        assert "user_profile" in args[2]
        assert "integration_requests" in args[2]
        assert "last_updated" in args[2]

@pytest.mark.asyncio
async def test_classify_query_with_intent_analyzer(systems_integration_ops_adapter):
    """Prueba el método _classify_query_with_intent_analyzer del adaptador."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(intent_analyzer_adapter, 'analyze_intent', new_callable=AsyncMock) as mock_analyze_intent:
        # Configurar el mock para devolver un análisis de intención
        mock_analyze_intent.return_value = {
            "primary_intent": "integration",
            "confidence": 0.85,
            "entities": [
                {"type": "system", "value": "garmin"},
                {"type": "action", "value": "connect"}
            ]
        }
        
        # Llamar al método a probar
        query_type = await systems_integration_ops_adapter._classify_query_with_intent_analyzer("¿Cómo puedo integrar mi aplicación con Garmin Connect?")
        
        # Verificar que se llamó al método analyze_intent del adaptador
        mock_analyze_intent.assert_called_once()
        
        # Verificar que el tipo de consulta devuelto es el esperado
        assert query_type == "integration_request"

@pytest.mark.asyncio
async def test_classify_query_with_intent_analyzer_fallback(systems_integration_ops_adapter):
    """Prueba el fallback al método _classify_query cuando el Intent Analyzer falla."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(intent_analyzer_adapter, 'analyze_intent', new_callable=AsyncMock) as mock_analyze_intent:
        # Configurar el mock para lanzar una excepción
        mock_analyze_intent.side_effect = Exception("Error simulado en el Intent Analyzer")
        
        # Mock para el método _classify_query original
        with patch.object(systems_integration_ops_adapter, '_classify_query', return_value="automation_request") as mock_classify_query:
            # Llamar al método a probar
            query_type = await systems_integration_ops_adapter._classify_query_with_intent_analyzer("¿Cómo puedo automatizar el envío de notificaciones?")
            
            # Verificar que se llamó al método analyze_intent del adaptador
            mock_analyze_intent.assert_called_once()
            
            # Verificar que se llamó al método _classify_query como fallback
            mock_classify_query.assert_called_once()
            
            # Verificar que el tipo de consulta devuelto es el esperado del fallback
            assert query_type == "automation_request"

@pytest.mark.asyncio
async def test_consult_other_agent(systems_integration_ops_adapter):
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
        response = await systems_integration_ops_adapter._consult_other_agent(
            agent_id="test_agent",
            query="¿Qué consideraciones de seguridad debo tener para mi integración con Garmin?",
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
async def test_run_async_impl(systems_integration_ops_adapter):
    """Prueba el método _run_async_impl del adaptador."""
    # Mock para _classify_query_with_intent_analyzer
    with patch.object(systems_integration_ops_adapter, '_classify_query_with_intent_analyzer', new_callable=AsyncMock) as mock_classify_query:
        # Configurar el mock para devolver un tipo de consulta
        mock_classify_query.return_value = "api_request"
        
        # Mock para _get_context
        with patch.object(systems_integration_ops_adapter, '_get_context', new_callable=AsyncMock) as mock_get_context:
            # Configurar el mock para devolver un contexto
            mock_get_context.return_value = {
                "conversation_history": [],
                "user_profile": {},
                "integration_requests": [],
                "automation_requests": [],
                "api_requests": [],
                "infrastructure_requests": [],
                "data_pipeline_requests": [],
                "last_updated": datetime.now().isoformat()
            }
            
            # Mock para super()._run_async_impl
            with patch.object(systems_integration_ops_adapter, '_update_context', new_callable=AsyncMock) as mock_update_context:
                # Configurar el mock para no hacer nada
                mock_update_context.return_value = None
                
                # Mock para la implementación original
                with patch('agents.systems_integration_ops.agent.SystemsIntegrationOps._run_async_impl', new_callable=AsyncMock) as mock_original_run:
                    # Configurar el mock para devolver una respuesta simulada
                    mock_original_run.return_value = {
                        "response": "Respuesta sobre APIs",
                        "capabilities_used": ["api_management"],
                        "metadata": {
                            "query_type": "api_request",
                            "execution_time": 0.5,
                            "session_id": "test_session"
                        }
                    }
                    
                    # Llamar al método a probar
                    result = await systems_integration_ops_adapter._run_async_impl(
                        "¿Cómo puedo utilizar la API de Garmin Connect?",
                        user_id="test_user",
                        session_id="test_session"
                    )
                    
                    # Verificar que se llamó al método _classify_query_with_intent_analyzer
                    mock_classify_query.assert_called_once()
                    
                    # Verificar que se llamó al método original
                    mock_original_run.assert_called_once()
                    
                    # Verificar que el resultado tiene la estructura esperada
                    assert "response" in result
                    assert "capabilities_used" in result
                    assert "metadata" in result
                    assert "query_type" in result["metadata"]
                    assert result["metadata"]["query_type"] == "api_request"

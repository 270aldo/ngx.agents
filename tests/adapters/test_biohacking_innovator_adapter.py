"""
Pruebas para el adaptador del agente BiohackingInnovator.

Este módulo contiene pruebas unitarias para verificar el correcto funcionamiento
del adaptador del agente BiohackingInnovator con los componentes optimizados.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import json

from infrastructure.adapters.biohacking_innovator_adapter import BiohackingInnovatorAdapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter

# Fixtures
@pytest.fixture
def biohacking_innovator_adapter():
    """Fixture que proporciona una instancia del adaptador BiohackingInnovator."""
    # Crear mocks para las dependencias
    gemini_client_mock = AsyncMock()
    gemini_client_mock.generate_response = AsyncMock(return_value="Respuesta simulada")
    gemini_client_mock.generate_structured_output = AsyncMock(return_value={
        "objective": "Protocolo de biohacking personalizado",
        "duration": "4-8 semanas",
        "interventions": {
            "diet": "Alimentación basada en alimentos enteros",
            "supplements": "Omega-3, Vitamina D, Magnesio",
            "exercise": "Entrenamiento de alta intensidad 3 veces por semana",
            "sleep": "Optimización del sueño con 7-9 horas por noche"
        }
    })
    
    supabase_client_mock = MagicMock()
    supabase_client_mock.get_user_profile = MagicMock(return_value={
        "age": 35,
        "gender": "masculino",
        "health_conditions": ["estrés crónico"],
        "goals": ["optimización cognitiva", "energía"]
    })
    
    mcp_toolkit_mock = MagicMock()
    
    # Crear instancia del adaptador con mocks
    adapter = BiohackingInnovatorAdapter(
        agent_id="test_biohacking_innovator",
        gemini_client=gemini_client_mock,
        supabase_client=supabase_client_mock,
        mcp_toolkit=mcp_toolkit_mock
    )
    
    return adapter

# Pruebas
@pytest.mark.asyncio
async def test_get_context(biohacking_innovator_adapter):
    """Prueba el método _get_context del adaptador."""
    # Mock para state_manager_adapter.load_state
    with patch.object(state_manager_adapter, 'load_state', new_callable=AsyncMock) as mock_load_state:
        # Configurar el mock para devolver un contexto de prueba
        mock_load_state.return_value = {
            "conversation_history": [
                {"role": "user", "content": "¿Qué suplementos me recomiendas para mejorar la cognición?"}
            ],
            "user_profile": {"age": 35, "gender": "masculino"},
            "protocols": [],
            "resources_used": [],
            "last_updated": "2025-10-05 21:00:00"
        }
        
        # Llamar al método a probar
        context = await biohacking_innovator_adapter._get_context("test_user", "test_session")
        
        # Verificar que se llamó al método load_state del adaptador
        mock_load_state.assert_called_once_with("test_user", "test_session")
        
        # Verificar que el contexto devuelto es el esperado
        assert "conversation_history" in context
        assert "user_profile" in context
        assert "protocols" in context
        assert context["user_profile"]["age"] == 35

@pytest.mark.asyncio
async def test_update_context(biohacking_innovator_adapter):
    """Prueba el método _update_context del adaptador."""
    # Mock para state_manager_adapter.save_state
    with patch.object(state_manager_adapter, 'save_state', new_callable=AsyncMock) as mock_save_state:
        # Crear un contexto de prueba
        test_context = {
            "conversation_history": [
                {"role": "user", "content": "¿Qué suplementos me recomiendas para mejorar la cognición?"},
                {"role": "assistant", "content": "Para mejorar la cognición, recomiendo..."}
            ],
            "user_profile": {"age": 35, "gender": "masculino"},
            "protocols": [
                {
                    "type": "cognitive_enhancement",
                    "protocol": {
                        "objective": "Mejora cognitiva",
                        "supplements": ["Bacopa Monnieri", "Lion's Mane", "Omega-3"]
                    }
                }
            ],
            "resources_used": [],
            "last_updated": "2025-10-05 21:00:00"
        }
        
        # Llamar al método a probar
        await biohacking_innovator_adapter._update_context(test_context, "test_user", "test_session")
        
        # Verificar que se llamó al método save_state del adaptador
        mock_save_state.assert_called_once()
        
        # Verificar que se pasaron los argumentos correctos
        args, kwargs = mock_save_state.call_args
        assert args[0] == "test_user"
        assert args[1] == "test_session"
        assert "conversation_history" in args[2]
        assert "protocols" in args[2]
        assert "last_updated" in args[2]

@pytest.mark.asyncio
async def test_classify_query(biohacking_innovator_adapter):
    """Prueba el método _classify_query del adaptador."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(intent_analyzer_adapter, 'analyze_intent', new_callable=AsyncMock) as mock_analyze_intent:
        # Configurar el mock para devolver un análisis de intención
        mock_analyze_intent.return_value = {
            "primary_intent": "cognitive_enhancement",
            "confidence": 0.85,
            "entities": [
                {"type": "supplement", "value": "bacopa monnieri"},
                {"type": "goal", "value": "memoria"}
            ]
        }
        
        # Llamar al método a probar
        query_type = await biohacking_innovator_adapter._classify_query("¿Qué suplementos puedo tomar para mejorar mi memoria?")
        
        # Verificar que se llamó al método analyze_intent del adaptador
        mock_analyze_intent.assert_called_once()
        
        # Verificar que el tipo de consulta devuelto es el esperado
        assert query_type == "cognitive_enhancement"

@pytest.mark.asyncio
async def test_consult_other_agent(biohacking_innovator_adapter):
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
        response = await biohacking_innovator_adapter._consult_other_agent(
            agent_id="test_agent",
            query="¿Cuál es el mejor ejercicio para optimizar la testosterona?",
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
async def test_run_async_impl_biohacking_protocol(biohacking_innovator_adapter):
    """Prueba el método _run_async_impl del adaptador para un protocolo de biohacking."""
    # Configurar mocks para los métodos del adaptador
    with patch.object(biohacking_innovator_adapter, '_get_context', new_callable=AsyncMock) as mock_get_context, \
         patch.object(biohacking_innovator_adapter, '_update_context', new_callable=AsyncMock) as mock_update_context, \
         patch.object(biohacking_innovator_adapter, '_classify_query', new_callable=AsyncMock) as mock_classify_query:
        
        # Configurar el mock para _get_context
        mock_get_context.return_value = {
            "conversation_history": [],
            "user_profile": {"age": 35, "gender": "masculino"},
            "protocols": [],
            "resources_used": [],
            "last_updated": "2025-10-05 21:00:00"
        }
        
        # Configurar el mock para _classify_query
        mock_classify_query.return_value = "biohacking"
        
        # Llamar al método a probar
        response = await biohacking_innovator_adapter._run_async_impl(
            input_text="Necesito un protocolo de biohacking para mejorar mi energía y rendimiento",
            user_id="test_user",
            session_id="test_session"
        )
        
        # Verificar que se llamaron los métodos esperados
        mock_get_context.assert_called_once()
        mock_classify_query.assert_called_once()
        mock_update_context.assert_called_once()
        
        # Verificar que la respuesta tiene la estructura esperada
        assert "response" in response
        assert "capabilities_used" in response
        assert "metadata" in response
        assert "biohacking" in response["capabilities_used"]

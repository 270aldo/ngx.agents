"""
Pruebas para el adaptador del agente SecurityComplianceGuardian.

Este módulo contiene pruebas unitarias para verificar el correcto funcionamiento
del adaptador del agente SecurityComplianceGuardian con los componentes optimizados.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime

from infrastructure.adapters.security_compliance_guardian_adapter import SecurityComplianceGuardianAdapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter

# Fixtures
@pytest.fixture
def security_compliance_guardian_adapter():
    """Fixture que proporciona una instancia del adaptador SecurityComplianceGuardian."""
    # Crear mocks para las dependencias
    gemini_client_mock = AsyncMock()
    gemini_client_mock.generate_response = AsyncMock(return_value="Respuesta simulada")
    gemini_client_mock.generate_structured_output = AsyncMock(return_value={
        "risks": [
            {"severity": "alta", "description": "Vulnerabilidad en autenticación", "impact": "Acceso no autorizado"},
            {"severity": "media", "description": "Falta de cifrado", "impact": "Interceptación de datos"}
        ],
        "recommendations": [
            "Implementar autenticación multifactor",
            "Configurar TLS para todas las comunicaciones"
        ]
    })
    
    supabase_client_mock = MagicMock()
    
    mcp_toolkit_mock = MagicMock()
    
    # Crear instancia del adaptador con mocks
    adapter = SecurityComplianceGuardianAdapter(
        agent_id="test_security_guardian",
        gemini_client=gemini_client_mock,
        supabase_client=supabase_client_mock,
        mcp_toolkit=mcp_toolkit_mock
    )
    
    return adapter

# Pruebas
@pytest.mark.asyncio
async def test_get_context(security_compliance_guardian_adapter):
    """Prueba el método _get_context del adaptador."""
    # Mock para state_manager_adapter.load_state
    with patch.object(state_manager_adapter, 'load_state', new_callable=AsyncMock) as mock_load_state:
        # Configurar el mock para devolver un contexto de prueba
        mock_load_state.return_value = {
            "conversation_history": [
                {"role": "user", "content": "¿Puedes realizar una evaluación de seguridad para mi aplicación web?"}
            ],
            "user_profile": {"company": "Tech Corp", "industry": "Fintech"},
            "security_queries": [{"timestamp": "2025-10-01T12:00:00", "query": "Evaluación de seguridad"}],
            "security_assessments": [{"timestamp": "2025-10-01T12:00:00", "risks": [{"severity": "alta"}]}],
            "compliance_checks": [],
            "vulnerability_scans": [],
            "data_protections": [],
            "general_recommendations": [],
            "query_types": {"security_assessment": 1},
            "last_updated": datetime.now().isoformat()
        }
        
        # Llamar al método a probar
        context = await security_compliance_guardian_adapter._get_context("test_user", "test_session")
        
        # Verificar que se llamó al método load_state del adaptador
        mock_load_state.assert_called_once_with("test_user", "test_session")
        
        # Verificar que el contexto devuelto es el esperado
        assert "conversation_history" in context
        assert "user_profile" in context
        assert "security_queries" in context
        assert "security_assessments" in context
        assert "query_types" in context
        assert len(context["security_assessments"]) == 1
        assert context["security_assessments"][0]["risks"][0]["severity"] == "alta"

@pytest.mark.asyncio
async def test_update_context(security_compliance_guardian_adapter):
    """Prueba el método _update_context del adaptador."""
    # Mock para state_manager_adapter.save_state
    with patch.object(state_manager_adapter, 'save_state', new_callable=AsyncMock) as mock_save_state:
        # Crear un contexto de prueba
        test_context = {
            "conversation_history": [
                {"role": "user", "content": "¿Puedes realizar una evaluación de seguridad para mi aplicación web?"},
                {"role": "assistant", "content": "Aquí tienes una evaluación de seguridad detallada..."}
            ],
            "user_profile": {"company": "Tech Corp", "industry": "Fintech"},
            "security_queries": [{"timestamp": "2025-10-01T12:00:00", "query": "Evaluación de seguridad"}],
            "security_assessments": [{"timestamp": "2025-10-01T12:00:00", "risks": [{"severity": "alta"}]}],
            "compliance_checks": [],
            "vulnerability_scans": [],
            "data_protections": [],
            "general_recommendations": [],
            "query_types": {"security_assessment": 1},
            "last_updated": datetime.now().isoformat()
        }
        
        # Llamar al método a probar
        await security_compliance_guardian_adapter._update_context(test_context, "test_user", "test_session")
        
        # Verificar que se llamó al método save_state del adaptador
        mock_save_state.assert_called_once()
        
        # Verificar que se pasaron los argumentos correctos
        args, kwargs = mock_save_state.call_args
        assert args[0] == "test_user"
        assert args[1] == "test_session"
        assert "conversation_history" in args[2]
        assert "user_profile" in args[2]
        assert "security_queries" in args[2]
        assert "security_assessments" in args[2]
        assert "last_updated" in args[2]

@pytest.mark.asyncio
async def test_classify_query_with_intent_analyzer(security_compliance_guardian_adapter):
    """Prueba el método _classify_query_with_intent_analyzer del adaptador."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(intent_analyzer_adapter, 'analyze_intent', new_callable=AsyncMock) as mock_analyze_intent:
        # Configurar el mock para devolver un análisis de intención
        mock_analyze_intent.return_value = {
            "primary_intent": "security_assessment",
            "confidence": 0.85,
            "entities": [
                {"type": "app_type", "value": "web"},
                {"type": "security_aspect", "value": "authentication"}
            ]
        }
        
        # Llamar al método a probar
        query_type = await security_compliance_guardian_adapter._classify_query_with_intent_analyzer("¿Puedes realizar una evaluación de seguridad para mi aplicación web?")
        
        # Verificar que se llamó al método analyze_intent del adaptador
        mock_analyze_intent.assert_called_once()
        
        # Verificar que el tipo de consulta devuelto es el esperado
        assert query_type == "security_assessment"

@pytest.mark.asyncio
async def test_classify_query_with_intent_analyzer_fallback(security_compliance_guardian_adapter):
    """Prueba el fallback al método _classify_query cuando el Intent Analyzer falla."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(intent_analyzer_adapter, 'analyze_intent', new_callable=AsyncMock) as mock_analyze_intent:
        # Configurar el mock para lanzar una excepción
        mock_analyze_intent.side_effect = Exception("Error simulado en el Intent Analyzer")
        
        # Mock para el método _classify_query original
        with patch.object(security_compliance_guardian_adapter, '_classify_query', return_value="vulnerability_scan") as mock_classify_query:
            # Llamar al método a probar
            query_type = await security_compliance_guardian_adapter._classify_query_with_intent_analyzer("¿Qué vulnerabilidades tiene mi sistema?")
            
            # Verificar que se llamó al método analyze_intent del adaptador
            mock_analyze_intent.assert_called_once()
            
            # Verificar que se llamó al método _classify_query como fallback
            mock_classify_query.assert_called_once()
            
            # Verificar que el tipo de consulta devuelto es el esperado del fallback
            assert query_type == "vulnerability_scan"

@pytest.mark.asyncio
async def test_consult_other_agent(security_compliance_guardian_adapter):
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
        response = await security_compliance_guardian_adapter._consult_other_agent(
            agent_id="test_agent",
            query="¿Qué medidas de seguridad recomiendas para proteger datos sensibles?",
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
async def test_run_async_impl(security_compliance_guardian_adapter):
    """Prueba el método _run_async_impl del adaptador."""
    # Mock para _classify_query_with_intent_analyzer
    with patch.object(security_compliance_guardian_adapter, '_classify_query_with_intent_analyzer', new_callable=AsyncMock) as mock_classify_query:
        # Configurar el mock para devolver un tipo de consulta
        mock_classify_query.return_value = "data_protection"
        
        # Mock para _get_context
        with patch.object(security_compliance_guardian_adapter, '_get_context', new_callable=AsyncMock) as mock_get_context:
            # Configurar el mock para devolver un contexto
            mock_get_context.return_value = {
                "conversation_history": [],
                "user_profile": {},
                "security_queries": [],
                "security_assessments": [],
                "compliance_checks": [],
                "vulnerability_scans": [],
                "data_protections": [],
                "general_recommendations": [],
                "query_types": {},
                "last_updated": datetime.now().isoformat()
            }
            
            # Mock para super()._run_async_impl
            with patch.object(security_compliance_guardian_adapter, '_update_context', new_callable=AsyncMock) as mock_update_context:
                # Configurar el mock para no hacer nada
                mock_update_context.return_value = None
                
                # Mock para la implementación original
                with patch('agents.security_compliance_guardian.agent.SecurityComplianceGuardian._run_async_impl', new_callable=AsyncMock) as mock_original_run:
                    # Configurar el mock para devolver una respuesta simulada
                    mock_original_run.return_value = {
                        "response": "Respuesta sobre protección de datos",
                        "capabilities_used": ["data_protection"],
                        "metadata": {
                            "query_type": "data_protection",
                            "execution_time": 0.5,
                            "session_id": "test_session"
                        }
                    }
                    
                    # Llamar al método a probar
                    result = await security_compliance_guardian_adapter._run_async_impl(
                        "¿Cómo puedo proteger datos sensibles en mi aplicación?",
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
                    assert result["metadata"]["query_type"] == "data_protection"

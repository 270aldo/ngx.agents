"""
Pruebas para el adaptador del agente ClientSuccessLiaison.

Este módulo contiene pruebas unitarias para verificar el correcto funcionamiento
del adaptador del agente ClientSuccessLiaison con los componentes optimizados.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from infrastructure.adapters.client_success_liaison_adapter import (
    ClientSuccessLiaisonAdapter,
)
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter


# Fixtures
@pytest.fixture
def client_success_liaison_adapter():
    """Fixture que proporciona una instancia del adaptador ClientSuccessLiaison."""
    # Crear mocks para las dependencias
    gemini_client_mock = AsyncMock()
    gemini_client_mock.generate_response = AsyncMock(return_value="Respuesta simulada")
    gemini_client_mock.generate_structured_output = AsyncMock(
        return_value={
            "objective": "Construir una comunidad activa y comprometida",
            "target_audience": "Usuarios del producto/servicio",
            "engagement_strategies": [
                "Programa de embajadores",
                "Contenido generado por usuarios",
                "Gamificación (puntos, insignias)",
                "Eventos regulares",
            ],
        }
    )

    supabase_client_mock = MagicMock()

    mcp_toolkit_mock = MagicMock()
    mcp_toolkit_mock.invoke = AsyncMock(
        return_value={
            "results": [
                {
                    "title": "Resultado 1",
                    "snippet": "Descripción 1",
                    "url": "https://example.com/1",
                },
                {
                    "title": "Resultado 2",
                    "snippet": "Descripción 2",
                    "url": "https://example.com/2",
                },
            ]
        }
    )

    # Crear instancia del adaptador con mocks
    adapter = ClientSuccessLiaisonAdapter(
        gemini_client=gemini_client_mock,
        supabase_client=supabase_client_mock,
        mcp_toolkit=mcp_toolkit_mock,
    )

    return adapter


# Pruebas
@pytest.mark.asyncio
async def test_get_context(client_success_liaison_adapter):
    """Prueba el método _get_context del adaptador."""
    # Mock para state_manager_adapter.load_state
    with patch.object(
        state_manager_adapter, "load_state", new_callable=AsyncMock
    ) as mock_load_state:
        # Configurar el mock para devolver un contexto de prueba
        mock_load_state.return_value = {
            "conversation_history": [
                {
                    "role": "user",
                    "content": "¿Cómo puedo mejorar la retención de usuarios?",
                }
            ],
            "user_profile": {"company": "Tech Startup", "industry": "SaaS"},
            "calendars": [
                {
                    "timestamp": "2025-10-01T12:00:00",
                    "community_plan": {"objective": "Construir comunidad"},
                }
            ],
            "journey_maps": [
                {
                    "timestamp": "2025-10-01T12:00:00",
                    "journey_map": {"stages": ["Descubrimiento", "Onboarding"]},
                }
            ],
            "support_requests": [
                {
                    "timestamp": "2025-10-01T12:00:00",
                    "ticket": {"ticket_id": "123", "status": "open"},
                }
            ],
            "last_updated": datetime.now().isoformat(),
        }

        # Llamar al método a probar
        context = await client_success_liaison_adapter._get_context(
            "test_user", "test_session"
        )

        # Verificar que se llamó al método load_state del adaptador
        mock_load_state.assert_called_once_with("test_user", "test_session")

        # Verificar que el contexto devuelto es el esperado
        assert "conversation_history" in context
        assert "user_profile" in context
        assert "calendars" in context
        assert "journey_maps" in context
        assert "support_requests" in context
        assert len(context["calendars"]) == 1
        assert (
            context["calendars"][0]["community_plan"]["objective"]
            == "Construir comunidad"
        )


@pytest.mark.asyncio
async def test_update_context(client_success_liaison_adapter):
    """Prueba el método _update_context del adaptador."""
    # Mock para state_manager_adapter.save_state
    with patch.object(
        state_manager_adapter, "save_state", new_callable=AsyncMock
    ) as mock_save_state:
        # Crear un contexto de prueba
        test_context = {
            "conversation_history": [
                {
                    "role": "user",
                    "content": "¿Cómo puedo mejorar la retención de usuarios?",
                },
                {
                    "role": "assistant",
                    "content": "Aquí tienes algunas estrategias para mejorar la retención...",
                },
            ],
            "user_profile": {"company": "Tech Startup", "industry": "SaaS"},
            "calendars": [
                {
                    "timestamp": "2025-10-01T12:00:00",
                    "community_plan": {"objective": "Construir comunidad"},
                }
            ],
            "journey_maps": [],
            "support_requests": [],
            "last_updated": datetime.now().isoformat(),
        }

        # Llamar al método a probar
        await client_success_liaison_adapter._update_context(
            test_context, "test_user", "test_session"
        )

        # Verificar que se llamó al método save_state del adaptador
        mock_save_state.assert_called_once()

        # Verificar que se pasaron los argumentos correctos
        args, kwargs = mock_save_state.call_args
        assert args[0] == "test_user"
        assert args[1] == "test_session"
        assert "conversation_history" in args[2]
        assert "user_profile" in args[2]
        assert "calendars" in args[2]
        assert "last_updated" in args[2]


@pytest.mark.asyncio
async def test_classify_query_with_intent_analyzer(client_success_liaison_adapter):
    """Prueba el método _classify_query_with_intent_analyzer del adaptador."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(
        intent_analyzer_adapter, "analyze_intent", new_callable=AsyncMock
    ) as mock_analyze_intent:
        # Configurar el mock para devolver un análisis de intención
        mock_analyze_intent.return_value = {
            "primary_intent": "community",
            "confidence": 0.85,
            "entities": [
                {"type": "community_type", "value": "online"},
                {"type": "platform", "value": "forum"},
            ],
        }

        # Llamar al método a probar
        query_type = (
            await client_success_liaison_adapter._classify_query_with_intent_analyzer(
                "¿Cómo puedo construir una comunidad online para mi producto?"
            )
        )

        # Verificar que se llamó al método analyze_intent del adaptador
        mock_analyze_intent.assert_called_once()

        # Verificar que el tipo de consulta devuelto es el esperado
        assert query_type == "community_building"


@pytest.mark.asyncio
async def test_classify_query_with_intent_analyzer_fallback(
    client_success_liaison_adapter,
):
    """Prueba el fallback al método _classify_query cuando el Intent Analyzer falla."""
    # Mock para intent_analyzer_adapter.analyze_intent
    with patch.object(
        intent_analyzer_adapter, "analyze_intent", new_callable=AsyncMock
    ) as mock_analyze_intent:
        # Configurar el mock para lanzar una excepción
        mock_analyze_intent.side_effect = Exception(
            "Error simulado en el Intent Analyzer"
        )

        # Mock para el método _classify_query original
        with patch.object(
            client_success_liaison_adapter,
            "_classify_query",
            return_value="retention_strategies",
        ) as mock_classify_query:
            # Llamar al método a probar
            query_type = await client_success_liaison_adapter._classify_query_with_intent_analyzer(
                "¿Cómo puedo mejorar la retención de usuarios?"
            )

            # Verificar que se llamó al método analyze_intent del adaptador
            mock_analyze_intent.assert_called_once()

            # Verificar que se llamó al método _classify_query como fallback
            mock_classify_query.assert_called_once()

            # Verificar que el tipo de consulta devuelto es el esperado del fallback
            assert query_type == "retention_strategies"


@pytest.mark.asyncio
async def test_consult_other_agent(client_success_liaison_adapter):
    """Prueba el método _consult_other_agent del adaptador."""
    # Mock para a2a_adapter.call_agent
    with patch.object(
        a2a_adapter, "call_agent", new_callable=AsyncMock
    ) as mock_call_agent:
        # Configurar el mock para devolver una respuesta simulada
        mock_call_agent.return_value = {
            "status": "success",
            "output": "Respuesta del agente consultado",
            "agent_id": "test_agent",
            "agent_name": "Test Agent",
        }

        # Llamar al método a probar
        response = await client_success_liaison_adapter._consult_other_agent(
            agent_id="test_agent",
            query="¿Qué estrategias de retención recomiendas para una app de fitness?",
            user_id="test_user",
            session_id="test_session",
        )

        # Verificar que se llamó al método call_agent del adaptador
        mock_call_agent.assert_called_once()

        # Verificar que la respuesta devuelta es la esperada
        assert response["status"] == "success"
        assert "Respuesta del agente consultado" in response["output"]
        assert response["agent_id"] == "test_agent"


@pytest.mark.asyncio
async def test_run_async_impl(client_success_liaison_adapter):
    """Prueba el método _run_async_impl del adaptador."""
    # Mock para _classify_query_with_intent_analyzer
    with patch.object(
        client_success_liaison_adapter,
        "_classify_query_with_intent_analyzer",
        new_callable=AsyncMock,
    ) as mock_classify_query:
        # Configurar el mock para devolver un tipo de consulta
        mock_classify_query.return_value = "community_building"

        # Mock para super()._run_async_impl
        with patch.object(
            client_success_liaison_adapter, "_get_context", new_callable=AsyncMock
        ) as mock_get_context:
            # Configurar el mock para devolver un contexto
            mock_get_context.return_value = {
                "conversation_history": [],
                "user_profile": {},
                "calendars": [],
                "journey_maps": [],
                "support_requests": [],
                "last_updated": datetime.now().isoformat(),
            }

            # Mock para la skill de community_building
            community_skill_mock = AsyncMock()
            community_skill_mock.handler = AsyncMock(
                return_value=MagicMock(
                    response="Respuesta sobre construcción de comunidad",
                    community_plan={"objective": "Construir comunidad"},
                )
            )

            # Reemplazar la skill en el adaptador
            original_skills = client_success_liaison_adapter.skills
            client_success_liaison_adapter.skills = [community_skill_mock]
            community_skill_mock.name = "community_building"

            try:
                # Llamar al método a probar
                with patch.object(
                    client_success_liaison_adapter,
                    "_update_context",
                    new_callable=AsyncMock,
                ) as mock_update_context:
                    # Configurar el mock para no hacer nada
                    mock_update_context.return_value = None

                    # Llamar al método a probar
                    with patch.object(
                        client_success_liaison_adapter,
                        "_classify_query",
                        return_value="community_building",
                    ):
                        result = await client_success_liaison_adapter._run_async_impl(
                            "¿Cómo puedo construir una comunidad online para mi producto?",
                            user_id="test_user",
                            session_id="test_session",
                        )

                        # Verificar que se llamó al método _classify_query_with_intent_analyzer
                        mock_classify_query.assert_called_once()

                        # Verificar que el resultado tiene la estructura esperada
                        assert "response" in result
                        assert "capabilities_used" in result
                        assert "metadata" in result
                        assert "query_type" in result["metadata"]
            finally:
                # Restaurar las skills originales
                client_success_liaison_adapter.skills = original_skills

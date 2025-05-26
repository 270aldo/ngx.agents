"""
Tests para el manejo de errores en los endpoints de la API.

Este módulo contiene tests para verificar que los endpoints manejan
correctamente diferentes escenarios de error.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import json

from app.main import app


class TestChatEndpointErrors:
    """Tests para errores en el endpoint de chat."""

    @pytest.fixture
    def client(self):
        """Cliente de test para la API."""
        return TestClient(app)

    def test_chat_with_empty_text(self, client):
        """Test que el chat rechaza texto vacío."""
        response = client.post(
            "/api/v1/chat",
            json={"text": ""},
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422
        assert "El texto no puede estar vacío" in response.text

    def test_chat_with_whitespace_only(self, client):
        """Test que el chat rechaza texto con solo espacios."""
        response = client.post(
            "/api/v1/chat",
            json={"text": "   \n\t   "},
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422

    def test_chat_with_text_too_long(self, client):
        """Test que el chat rechaza texto demasiado largo."""
        long_text = "a" * 10001  # Más de 10000 caracteres
        response = client.post(
            "/api/v1/chat",
            json={"text": long_text},
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422

    def test_chat_with_invalid_user_id(self, client):
        """Test que el chat rechaza user_id inválido."""
        response = client.post(
            "/api/v1/chat",
            json={
                "text": "Test message",
                "user_id": "invalid@user#id",  # Caracteres no permitidos
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422

    def test_chat_with_invalid_session_id(self, client):
        """Test que el chat rechaza session_id inválido."""
        response = client.post(
            "/api/v1/chat",
            json={
                "text": "Test message",
                "session_id": "invalid session id",  # Espacios no permitidos
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422

    def test_chat_with_invalid_context(self, client):
        """Test que el chat rechaza contexto inválido."""
        response = client.post(
            "/api/v1/chat",
            json={
                "text": "Test message",
                "context": "not a dict",  # Debe ser un diccionario
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422

    @patch("app.routers.chat.get_orchestrator")
    def test_chat_orchestrator_initialization_failure(
        self, mock_get_orchestrator, client
    ):
        """Test cuando falla la inicialización del orchestrator."""
        mock_get_orchestrator.side_effect = Exception(
            "Orchestrator initialization failed"
        )

        response = client.post(
            "/api/v1/chat",
            json={"text": "Test message"},
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 500
        assert "Error al procesar mensaje" in response.json()["detail"]

    @patch("app.routers.chat.NGXNexusOrchestrator")
    def test_chat_orchestrator_connection_failure(
        self, mock_orchestrator_class, client
    ):
        """Test cuando falla la conexión del orchestrator."""
        mock_orchestrator = AsyncMock()
        mock_orchestrator.is_connected = False
        mock_orchestrator.connect.side_effect = Exception("Connection failed")
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("app.routers.chat._orchestrator_instance", mock_orchestrator):
            response = client.post(
                "/api/v1/chat",
                json={"text": "Test message"},
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 500

    def test_chat_without_authentication(self, client):
        """Test que el chat requiere autenticación."""
        response = client.post("/api/v1/chat", json={"text": "Test message"})
        assert response.status_code == 401


class TestAgentEndpointErrors:
    """Tests para errores en los endpoints de agentes."""

    @pytest.fixture
    def client(self):
        """Cliente de test para la API."""
        return TestClient(app)

    def test_run_agent_with_invalid_id(self, client):
        """Test ejecutar agente con ID inválido."""
        response = client.post(
            "/api/v1/agents/invalid@agent#id/run",
            json={"input_text": "Test"},
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422  # Validación de path parameter

    def test_run_agent_not_found(self, client):
        """Test ejecutar agente que no existe."""
        response = client.post(
            "/api/v1/agents/non_existent_agent/run",
            json={"input_text": "Test"},
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"].lower()

    def test_run_agent_with_empty_input(self, client):
        """Test ejecutar agente con entrada vacía."""
        response = client.post(
            "/api/v1/agents/test_agent/run",
            json={"input_text": ""},
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422

    @patch("app.routers.agents.discover_agents")
    def test_list_agents_discovery_failure(self, mock_discover, client):
        """Test listar agentes cuando falla el descubrimiento."""
        mock_discover.side_effect = Exception("Discovery failed")

        response = client.get(
            "/api/v1/agents", headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 500


class TestCircuitBreakerEndpointErrors:
    """Tests para errores relacionados con circuit breakers."""

    @pytest.fixture
    def client(self):
        """Cliente de test para la API."""
        return TestClient(app)

    def test_reset_circuit_breaker_not_found(self, client):
        """Test resetear un circuit breaker que no existe."""
        response = client.post(
            "/api/v1/circuit-breakers/non_existent/reset",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 404

    @patch("core.circuit_breaker.get_all_circuit_breakers")
    def test_get_circuit_breakers_error(self, mock_get_all, client):
        """Test obtener circuit breakers cuando hay un error."""
        mock_get_all.side_effect = Exception("Failed to get breakers")

        response = client.get(
            "/api/v1/circuit-breakers", headers={"Authorization": "Bearer test_token"}
        )
        assert response.status_code == 500


class TestValidationErrors:
    """Tests para errores de validación en general."""

    @pytest.fixture
    def client(self):
        """Cliente de test para la API."""
        return TestClient(app)

    def test_invalid_json_body(self, client):
        """Test enviar JSON inválido."""
        response = client.post(
            "/api/v1/chat",
            data="not valid json",
            headers={
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test omitir campos requeridos."""
        response = client.post(
            "/api/v1/chat",
            json={},  # Falta el campo 'text' requerido
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422
        error_detail = response.json()["detail"][0]
        assert error_detail["loc"] == ["body", "text"]
        assert error_detail["type"] == "value_error.missing"

    def test_wrong_field_type(self, client):
        """Test enviar tipo de campo incorrecto."""
        response = client.post(
            "/api/v1/chat",
            json={
                "text": 123,  # Debería ser string
                "context": "not a dict",  # Debería ser dict
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422


class TestConcurrencyErrors:
    """Tests para errores de concurrencia."""

    @pytest.fixture
    def client(self):
        """Cliente de test para la API."""
        return TestClient(app)

    @patch("app.routers.chat.NGXNexusOrchestrator")
    def test_concurrent_chat_requests(self, mock_orchestrator_class, client):
        """Test múltiples requests concurrentes al chat."""

        # Simular procesamiento lento
        async def slow_run_async(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {
                "response": "Test response",
                "agents_used": ["test_agent"],
                "metadata": {},
            }

        mock_orchestrator = AsyncMock()
        mock_orchestrator.is_connected = True
        mock_orchestrator.run_async = slow_run_async
        mock_orchestrator_class.return_value = mock_orchestrator

        import concurrent.futures

        def make_request():
            return client.post(
                "/api/v1/chat",
                json={"text": "Test message"},
                headers={"Authorization": "Bearer test_token"},
            )

        # Hacer múltiples requests concurrentes
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [f.result() for f in futures]

        # Todas deberían ser exitosas
        for response in responses:
            assert response.status_code == 200

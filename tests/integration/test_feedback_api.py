"""
Tests de integración para el sistema de feedback.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from httpx import AsyncClient
from fastapi import status

from app.main import app
from core.auth import create_access_token
from app.schemas.feedback import FeedbackType, FeedbackCategory


@pytest.fixture
async def auth_headers():
    """Fixture para obtener headers de autenticación."""
    token = create_access_token(
        {"sub": "test_user_123", "id": "test_user_123", "is_admin": False}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_headers():
    """Fixture para obtener headers de autenticación de admin."""
    token = create_access_token(
        {"sub": "admin_user_123", "id": "admin_user_123", "is_admin": True}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def async_client():
    """Fixture para cliente HTTP asíncrono."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestMessageFeedback:
    """Tests para feedback de mensajes."""

    @pytest.mark.asyncio
    async def test_submit_thumbs_up(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para enviar un thumbs up."""
        request_data = {
            "conversation_id": "test-conv-123",
            "message_id": "test-msg-456",
            "feedback_type": FeedbackType.THUMBS_UP.value,
        }

        response = await async_client.post(
            "/feedback/message", json=request_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "feedback_id" in data
        assert data["feedback_id"] != ""

    @pytest.mark.asyncio
    async def test_submit_rating_feedback(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para enviar feedback con rating."""
        request_data = {
            "conversation_id": "test-conv-123",
            "message_id": "test-msg-789",
            "feedback_type": FeedbackType.RATING.value,
            "rating": 4,
            "categories": [
                FeedbackCategory.ACCURACY.value,
                FeedbackCategory.HELPFULNESS.value,
            ],
        }

        response = await async_client.post(
            "/feedback/message", json=request_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_submit_issue_feedback(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para reportar un problema."""
        request_data = {
            "conversation_id": "test-conv-123",
            "message_id": "test-msg-999",
            "feedback_type": FeedbackType.ISSUE.value,
            "comment": "La respuesta contiene información incorrecta sobre el ejercicio",
            "categories": [
                FeedbackCategory.ACCURACY.value,
                FeedbackCategory.TECHNICAL_ISSUE.value,
            ],
        }

        response = await async_client.post(
            "/feedback/message", json=request_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_invalid_rating_feedback(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para validación de rating requerido."""
        request_data = {
            "conversation_id": "test-conv-123",
            "message_id": "test-msg-111",
            "feedback_type": FeedbackType.RATING.value,
            # Falta el rating
        }

        response = await async_client.post(
            "/feedback/message", json=request_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_invalid_comment_feedback(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para validación de comentario requerido."""
        request_data = {
            "conversation_id": "test-conv-123",
            "message_id": "test-msg-222",
            "feedback_type": FeedbackType.COMMENT.value,
            "comment": "",  # Comentario vacío
        }

        response = await async_client.post(
            "/feedback/message", json=request_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSessionFeedback:
    """Tests para feedback de sesiones."""

    @pytest.mark.asyncio
    async def test_submit_session_feedback(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para enviar feedback de sesión completa."""
        request_data = {
            "conversation_id": "test-conv-123",
            "overall_rating": 5,
            "categories_feedback": {
                FeedbackCategory.ACCURACY.value: 5,
                FeedbackCategory.HELPFULNESS.value: 4,
                FeedbackCategory.SPEED.value: 5,
            },
            "would_recommend": True,
            "comment": "Excelente experiencia general",
            "improvement_suggestions": [
                "Agregar más ejemplos visuales",
                "Incluir referencias a estudios",
            ],
        }

        response = await async_client.post(
            "/feedback/session", json=request_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "feedback_id" in data

    @pytest.mark.asyncio
    async def test_invalid_category_rating(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para validación de ratings de categorías."""
        request_data = {
            "conversation_id": "test-conv-123",
            "overall_rating": 4,
            "categories_feedback": {
                FeedbackCategory.ACCURACY.value: 6  # Rating inválido (> 5)
            },
        }

        response = await async_client.post(
            "/feedback/session", json=request_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestFeedbackStats:
    """Tests para estadísticas de feedback."""

    @pytest.mark.asyncio
    async def test_get_feedback_stats(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para obtener estadísticas de feedback."""
        response = await async_client.get("/feedback/stats", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_feedbacks" in data
        assert "time_period" in data
        assert "start" in data["time_period"]
        assert "end" in data["time_period"]

    @pytest.mark.asyncio
    async def test_get_stats_with_date_range(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para obtener estadísticas con rango de fechas."""
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end_date = datetime.utcnow().isoformat()

        response = await async_client.get(
            f"/feedback/stats?start_date={start_date}&end_date={end_date}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["time_period"]["start"] == start_date
        assert data["time_period"]["end"] == end_date

    @pytest.mark.asyncio
    async def test_get_stats_for_conversation(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para obtener estadísticas de una conversación específica."""
        conversation_id = "test-conv-123"

        response = await async_client.get(
            f"/feedback/stats?conversation_id={conversation_id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK


class TestFeedbackSearch:
    """Tests para búsqueda de feedback."""

    @pytest.mark.asyncio
    async def test_search_feedback(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para buscar feedback con filtros."""
        filters = {
            "feedback_type": FeedbackType.THUMBS_UP.value,
            "limit": 10,
            "offset": 0,
        }

        response = await async_client.post(
            "/feedback/search", json=filters, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "has_more" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_search_with_rating_range(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test para buscar feedback por rango de rating."""
        filters = {"rating_min": 3, "rating_max": 5, "limit": 20}

        response = await async_client.post(
            "/feedback/search", json=filters, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Verificar que todos los items tengan rating en el rango correcto
        for item in data["items"]:
            if item["rating"]:
                assert 3 <= item["rating"] <= 5


class TestFeedbackAnalytics:
    """Tests para analytics de feedback."""

    @pytest.mark.asyncio
    async def test_get_analytics_requires_admin(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test que verifica que analytics requiere permisos de admin."""
        response = await async_client.get("/feedback/analytics", headers=auth_headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_analytics_as_admin(
        self, async_client: AsyncClient, admin_headers: Dict[str, str]
    ):
        """Test para obtener analytics como admin."""
        response = await async_client.get("/feedback/analytics", headers=admin_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "sentiment_analysis" in data
        assert "trending_topics" in data
        assert "agent_performance" in data
        assert "user_satisfaction_trend" in data
        assert "improvement_areas" in data


class TestFeedbackMetadata:
    """Tests para endpoints de metadatos."""

    @pytest.mark.asyncio
    async def test_get_feedback_types(self, async_client: AsyncClient):
        """Test para obtener tipos de feedback disponibles."""
        response = await async_client.get("/feedback/types")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "feedback_types" in data
        assert "feedback_categories" in data
        assert len(data["feedback_types"]) > 0
        assert len(data["feedback_categories"]) > 0

    @pytest.mark.asyncio
    async def test_feedback_health(self, async_client: AsyncClient):
        """Test para verificar salud del servicio de feedback."""
        response = await async_client.get("/feedback/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "feedback"
        assert data["features"]["message_feedback"] is True
        assert data["features"]["session_feedback"] is True


class TestFeedbackWithMetrics:
    """Tests para verificar integración con métricas."""

    @pytest.mark.asyncio
    async def test_feedback_updates_metrics(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test que verifica que el feedback actualiza las métricas de Prometheus."""
        # Enviar feedback
        request_data = {
            "conversation_id": "test-conv-metrics",
            "message_id": "test-msg-metrics",
            "feedback_type": FeedbackType.THUMBS_UP.value,
        }

        response = await async_client.post(
            "/feedback/message", json=request_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK

        # Verificar métricas (esto requeriría acceso al endpoint /metrics)
        metrics_response = await async_client.get("/metrics")
        metrics_text = metrics_response.text

        # Verificar que las métricas de feedback estén presentes
        assert "ngx_agents_feedback_received_total" in metrics_text

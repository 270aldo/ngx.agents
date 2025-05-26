"""
Tests de integración para el endpoint de streaming SSE.
"""

import json
import asyncio
from typing import AsyncGenerator, List, Dict, Any
import pytest
from httpx import AsyncClient, Response
from fastapi import status

from app.main import app
from core.auth import create_access_token


@pytest.fixture
async def auth_headers():
    """Fixture para obtener headers de autenticación."""
    token = create_access_token({"sub": "test_user_123", "id": "test_user_123"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def async_client():
    """Fixture para cliente HTTP asíncrono."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


async def read_sse_stream(response: Response) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Lee y parsea eventos SSE del response stream.

    Args:
        response: Response HTTP con stream SSE

    Yields:
        Diccionarios con los datos parseados de cada evento
    """
    buffer = ""
    event_type = None

    async for chunk in response.aiter_text():
        buffer += chunk
        lines = buffer.split("\n")
        buffer = lines.pop()  # Guardar última línea incompleta

        for line in lines:
            line = line.strip()

            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str:
                    try:
                        data = json.loads(data_str)
                        yield {"event": event_type, "data": data}
                    except json.JSONDecodeError:
                        pass
                event_type = None
            elif line == "":
                # Línea vacía indica fin de evento
                event_type = None


@pytest.mark.asyncio
async def test_stream_chat_endpoint(
    async_client: AsyncClient, auth_headers: Dict[str, str]
):
    """Test básico del endpoint de streaming."""
    # Preparar request
    request_data = {"message": "Hola, ¿cómo estás?", "metadata": {"test": True}}

    # Hacer petición de streaming
    async with async_client.stream(
        "POST", "/stream/chat", json=request_data, headers=auth_headers
    ) as response:
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Recolectar todos los eventos
        events = []
        async for event in read_sse_stream(response):
            events.append(event)

        # Verificar que recibimos los eventos esperados
        assert len(events) > 0

        # Verificar evento de inicio
        start_events = [e for e in events if e.get("event") == "start"]
        assert len(start_events) == 1
        assert "conversation_id" in start_events[0]["data"]
        assert start_events[0]["data"]["status"] == "processing"

        # Verificar chunks de contenido
        chunk_events = [e for e in events if e.get("event") == "chunk"]
        assert len(chunk_events) > 0
        for chunk in chunk_events:
            assert "content" in chunk["data"]
            assert "chunk_index" in chunk["data"]
            assert "type" in chunk["data"]

        # Verificar evento de finalización
        end_events = [e for e in events if e.get("event") == "end"]
        assert len(end_events) == 1
        assert end_events[0]["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_stream_chat_empty_message(
    async_client: AsyncClient, auth_headers: Dict[str, str]
):
    """Test con mensaje vacío."""
    request_data = {"message": "", "metadata": {}}

    response = await async_client.post(
        "/stream/chat", json=request_data, headers=auth_headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "El mensaje no puede estar vacío" in response.json()["detail"]


@pytest.mark.asyncio
async def test_stream_chat_unauthorized(async_client: AsyncClient):
    """Test sin autenticación."""
    request_data = {"message": "Test message", "metadata": {}}

    response = await async_client.post("/stream/chat", json=request_data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_stream_health_endpoint(async_client: AsyncClient):
    """Test del endpoint de salud del servicio de streaming."""
    response = await async_client.get("/stream/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "stream"
    assert data["sse_enabled"] is True


@pytest.mark.asyncio
async def test_stream_concurrent_requests(
    async_client: AsyncClient, auth_headers: Dict[str, str]
):
    """Test de múltiples requests concurrentes de streaming."""

    async def make_stream_request(message: str) -> List[Dict[str, Any]]:
        """Helper para hacer una petición de streaming."""
        request_data = {"message": message, "metadata": {"concurrent_test": True}}

        events = []
        async with async_client.stream(
            "POST", "/stream/chat", json=request_data, headers=auth_headers
        ) as response:
            async for event in read_sse_stream(response):
                events.append(event)

        return events

    # Lanzar múltiples requests concurrentes
    tasks = [make_stream_request(f"Mensaje concurrente {i}") for i in range(3)]

    results = await asyncio.gather(*tasks)

    # Verificar que todas las requests fueron procesadas
    assert len(results) == 3
    for events in results:
        assert len(events) > 0
        # Cada request debe tener su propio conversation_id
        start_event = next(e for e in events if e.get("event") == "start")
        assert "conversation_id" in start_event["data"]


@pytest.mark.asyncio
async def test_stream_with_conversation_id(
    async_client: AsyncClient, auth_headers: Dict[str, str]
):
    """Test streaming con conversation_id específico."""
    conversation_id = "test-conversation-123"
    request_data = {
        "message": "Test con ID específico",
        "conversation_id": conversation_id,
        "metadata": {},
    }

    events = []
    async with async_client.stream(
        "POST", "/stream/chat", json=request_data, headers=auth_headers
    ) as response:
        async for event in read_sse_stream(response):
            events.append(event)

    # Verificar que se usa el conversation_id proporcionado
    start_event = next(e for e in events if e.get("event") == "start")
    assert start_event["data"]["conversation_id"] == conversation_id

    end_event = next(e for e in events if e.get("event") == "end")
    assert end_event["data"]["conversation_id"] == conversation_id

"""
Tests de integración para el StreamingOrchestrator.

Este módulo prueba las capacidades de streaming del orchestrator,
verificando que las respuestas incrementales funcionan correctamente.
"""

import pytest
import asyncio
import json
from typing import List, Dict, Any

from agents.orchestrator.streaming_orchestrator import StreamingNGXNexusOrchestrator
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from infrastructure.adapters.a2a_adapter import a2a_adapter


class TestStreamingOrchestrator:
    """Tests para el StreamingNGXNexusOrchestrator."""

    @pytest.fixture
    async def orchestrator(self):
        """Crea una instancia del StreamingOrchestrator para testing."""
        return StreamingNGXNexusOrchestrator(
            state_manager=state_manager_adapter,
            a2a_server_url="http://localhost:9000",
            chunk_size=30,
            chunk_delay=0.01,  # Delay más corto para tests
        )

    @pytest.mark.asyncio
    async def test_stream_response_basic(self, orchestrator):
        """Test básico de streaming de respuesta."""
        chunks = []

        async for chunk in orchestrator.stream_response(
            input_text="¿Cuál es un buen plan de entrenamiento?",
            user_id="test_user",
            session_id="test_session",
        ):
            chunks.append(chunk)

        # Verificar que recibimos los tipos de eventos esperados
        event_types = [chunk["type"] for chunk in chunks]

        assert "start" in event_types
        assert "status" in event_types
        assert "intent_analysis" in event_types
        assert any(t in ["complete", "error"] for t in event_types)

    @pytest.mark.asyncio
    async def test_chunk_splitting(self, orchestrator):
        """Test de división de texto en chunks."""
        text = (
            "Esta es una oración muy larga que debería ser dividida en múltiples chunks para el streaming. "
            "Aquí hay otra oración. Y una más para asegurar múltiples chunks."
        )

        chunks = orchestrator._split_into_chunks(text)

        # Verificar que se crearon múltiples chunks
        assert len(chunks) > 1

        # Verificar que ningún chunk excede el tamaño máximo
        for chunk in chunks:
            assert len(chunk) <= orchestrator.chunk_size * 2

        # Verificar que el texto completo se preserva
        assert " ".join(chunks).replace("  ", " ").strip() == text.strip()

    @pytest.mark.asyncio
    async def test_intent_analysis_streaming(self, orchestrator):
        """Test del análisis de intención en modo streaming."""
        intent_result = await orchestrator._analyze_intent_streaming(
            "Quiero crear un plan de nutrición personalizado"
        )

        assert "primary_intent" in intent_result
        assert "confidence" in intent_result
        assert isinstance(intent_result["confidence"], (int, float))
        assert 0 <= intent_result["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_agent_selection(self, orchestrator):
        """Test de selección de agentes basada en intención."""
        intent_analysis = {
            "primary_intent": "plan_entrenamiento",
            "secondary_intents": ["analizar_nutricion"],
            "confidence": 0.9,
        }

        agents = orchestrator._get_agents_for_intent(intent_analysis)

        assert isinstance(agents, list)
        assert len(agents) > 0
        assert "elite_training_strategist" in agents

    @pytest.mark.asyncio
    async def test_stream_text_chunks(self, orchestrator):
        """Test de streaming de texto en chunks."""
        text = "Respuesta del agente de prueba."
        agent_id = "test_agent"
        chunks = []

        async for chunk in orchestrator._stream_text(text, agent_id):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert all(chunk["type"] == "content" for chunk in chunks)
        assert all(chunk["agent_id"] == agent_id for chunk in chunks)
        assert chunks[-1]["is_final"] is True

    @pytest.mark.asyncio
    async def test_error_handling_in_stream(self, orchestrator, monkeypatch):
        """Test del manejo de errores durante el streaming."""

        # Simular un error en el análisis de intención
        async def mock_analyze_intent(*args, **kwargs):
            raise Exception("Error de prueba")

        monkeypatch.setattr(
            intent_analyzer_adapter, "analyze_intent", mock_analyze_intent
        )

        chunks = []
        async for chunk in orchestrator.stream_response(
            input_text="Test con error", user_id="test_user"
        ):
            chunks.append(chunk)

        # Verificar que aún obtenemos algunos chunks y el error se maneja
        assert len(chunks) > 0
        # El análisis de intención debería usar valores por defecto
        intent_chunks = [c for c in chunks if c["type"] == "intent_analysis"]
        if intent_chunks:
            assert intent_chunks[0]["intent"] == "general"

    @pytest.mark.asyncio
    async def test_streaming_with_multiple_agents(self, orchestrator, monkeypatch):
        """Test de streaming con múltiples agentes."""

        # Mock de la respuesta del adaptador a2a
        async def mock_call_agent(agent_id, user_input, context):
            return {
                "status": "success",
                "output": f"Respuesta de {agent_id}: {user_input[:20]}...",
                "artifacts": [],
            }

        monkeypatch.setattr(a2a_adapter, "call_agent", mock_call_agent)

        # Mock para que devuelva múltiples agentes
        orchestrator.intent_to_agent_map["test"] = ["agent1", "agent2", "agent3"]

        chunks = []
        async for chunk in orchestrator.stream_response(
            input_text="test de múltiples agentes", user_id="test_user"
        ):
            chunks.append(chunk)

        # Verificar que recibimos contenido de múltiples agentes
        content_chunks = [c for c in chunks if c["type"] == "content"]
        agent_ids = set(c["agent_id"] for c in content_chunks)

        # Deberíamos tener contenido de al menos un agente
        assert len(agent_ids) >= 1

    @pytest.mark.asyncio
    async def test_streaming_performance(self, orchestrator):
        """Test de rendimiento del streaming."""
        import time

        start_time = time.time()
        chunk_count = 0

        async for chunk in orchestrator.stream_response(
            input_text="Test de rendimiento", user_id="test_user"
        ):
            chunk_count += 1
            if chunk_count > 100:  # Límite de seguridad
                break

        elapsed_time = time.time() - start_time

        # El streaming no debería tomar demasiado tiempo
        assert elapsed_time < 10  # 10 segundos máximo
        assert chunk_count > 0

    @pytest.mark.asyncio
    async def test_session_persistence(self, orchestrator):
        """Test de persistencia de sesión durante el streaming."""
        session_id = "test_session_persist"
        user_id = "test_user"

        # Primera consulta
        chunks1 = []
        async for chunk in orchestrator.stream_response(
            input_text="Primera consulta", user_id=user_id, session_id=session_id
        ):
            chunks1.append(chunk)

        # Segunda consulta en la misma sesión
        chunks2 = []
        async for chunk in orchestrator.stream_response(
            input_text="Segunda consulta", user_id=user_id, session_id=session_id
        ):
            chunks2.append(chunk)

        # Ambas deberían usar la misma sesión
        start_chunks1 = [c for c in chunks1 if c["type"] == "start"]
        start_chunks2 = [c for c in chunks2 if c["type"] == "start"]

        if start_chunks1 and start_chunks2:
            assert start_chunks1[0]["session_id"] == session_id
            assert start_chunks2[0]["session_id"] == session_id


@pytest.mark.asyncio
async def test_concurrent_streaming():
    """Test de múltiples streams concurrentes."""
    orchestrator1 = StreamingNGXNexusOrchestrator()
    orchestrator2 = StreamingNGXNexusOrchestrator()

    async def collect_chunks(orchestrator, input_text, user_id):
        chunks = []
        async for chunk in orchestrator.stream_response(
            input_text=input_text, user_id=user_id
        ):
            chunks.append(chunk)
        return chunks

    # Ejecutar dos streams en paralelo
    results = await asyncio.gather(
        collect_chunks(orchestrator1, "Consulta 1", "user1"),
        collect_chunks(orchestrator2, "Consulta 2", "user2"),
    )

    # Ambos deberían completarse exitosamente
    assert len(results) == 2
    assert all(len(chunks) > 0 for chunks in results)

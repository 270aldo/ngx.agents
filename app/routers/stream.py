"""
Router de streaming para la API de NGX Agents.

Este módulo proporciona endpoints para streaming de respuestas en tiempo real
usando Server-Sent Events (SSE).
"""

import asyncio
import json
import uuid
import time
from typing import AsyncGenerator, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from core.auth import get_current_user
from core.logging_config import get_logger
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from app.schemas.chat import ChatRequest
from agents.orchestrator.agent import NGXNexusOrchestrator
from agents.orchestrator.streaming_orchestrator import StreamingNGXNexusOrchestrator
from config import settings
from core.metrics import (
    chat_sessions_total,
    chat_messages_total,
    stream_chunks_sent_total,
    stream_ttfb_seconds,
    track_time,
    metrics_collector,
)

# Configurar logger
logger = get_logger(__name__)

# Crear router
router = APIRouter(
    prefix="/stream",
    tags=["stream"],
    responses={401: {"description": "No autorizado"}},
)

# Variable global para el orquestador (Singleton)
_orchestrator_instance: Optional[StreamingNGXNexusOrchestrator] = None
_orchestrator_lock = asyncio.Lock()


async def get_orchestrator() -> StreamingNGXNexusOrchestrator:
    """
    Dependencia asíncrona para obtener una instancia del Streaming Orchestrator.
    Utiliza un patrón Singleton con bloqueo asíncrono.

    Returns:
        Instancia del Streaming Orchestrator
    """
    global _orchestrator_instance

    async with _orchestrator_lock:
        if _orchestrator_instance is None:
            logger.info("Creando nueva instancia de StreamingNGXNexusOrchestrator.")
            state_manager = state_manager_adapter

            # Crear instancia del orquestador con streaming
            _orchestrator_instance = StreamingNGXNexusOrchestrator(
                state_manager=state_manager,
                a2a_server_url=settings.A2A_SERVER_URL,
                use_optimized=True,
                chunk_size=50,  # Tamaño de chunk configurable
                chunk_delay=0.05,  # Delay entre chunks configurable
            )
            logger.info("StreamingNGXNexusOrchestrator creado exitosamente.")

        return _orchestrator_instance


async def generate_stream_response(
    orchestrator: StreamingNGXNexusOrchestrator,
    request: ChatRequest,
    current_user: Dict[str, Any],
    conversation_id: str,
) -> AsyncGenerator[str, None]:
    """
    Genera respuestas de streaming para el chat usando el StreamingOrchestrator.

    Args:
        orchestrator: Instancia del orquestador con capacidades de streaming
        request: Petición de chat
        current_user: Usuario actual
        conversation_id: ID de la conversación

    Yields:
        Eventos SSE con los chunks de respuesta
    """
    try:
        # Registrar inicio de sesión de streaming
        session_start_time = time.time()
        chat_sessions_total.labels(type="streaming", status="started").inc()
        chat_messages_total.labels(direction="user").inc()

        # Yield evento inicial
        yield f"event: start\\ndata: {json.dumps({'conversation_id': conversation_id, 'status': 'processing'})}\\n\\n"

        # Registrar time to first byte
        ttfb = time.time() - session_start_time
        stream_ttfb_seconds.observe(ttfb)

        # Usar el nuevo método de streaming del orchestrator
        chunk_count = 0
        async for chunk in orchestrator.stream_response(
            input_text=request.message,
            user_id=current_user["id"],
            session_id=conversation_id,
            metadata=request.metadata,
        ):
            # Convertir el chunk del orchestrator al formato SSE
            if chunk["type"] == "start":
                # Ya enviamos el evento start arriba
                continue
            elif chunk["type"] == "status":
                yield f"event: status\\ndata: {json.dumps(chunk)}\\n\\n"
            elif chunk["type"] == "intent_analysis":
                yield f"event: intent\\ndata: {json.dumps(chunk)}\\n\\n"
            elif chunk["type"] == "agents_selected":
                yield f"event: agents\\ndata: {json.dumps(chunk)}\\n\\n"
            elif chunk["type"] == "agent_start":
                yield f"event: agent_start\\ndata: {json.dumps(chunk)}\\n\\n"
            elif chunk["type"] == "content":
                # Incrementar contador de chunks
                chunk_count += 1
                stream_chunks_sent_total.inc()
                yield f"event: chunk\\ndata: {json.dumps(chunk)}\\n\\n"
            elif chunk["type"] == "artifacts":
                yield f"event: artifacts\\ndata: {json.dumps(chunk)}\\n\\n"
            elif chunk["type"] == "agent_error":
                yield f"event: agent_error\\ndata: {json.dumps(chunk)}\\n\\n"
            elif chunk["type"] == "complete":
                # Añadir información adicional al evento de finalización
                chunk["conversation_id"] = conversation_id
                chunk["chunk_count"] = chunk_count
                yield f"event: end\\ndata: {json.dumps(chunk)}\\n\\n"
            elif chunk["type"] == "error":
                yield f"event: error\\ndata: {json.dumps(chunk)}\\n\\n"

        # Registrar sesión completada
        session_duration = time.time() - session_start_time
        chat_sessions_total.labels(type="streaming", status="completed").inc()
        chat_messages_total.labels(direction="agent").inc()
        metrics_collector.record_chat_session(
            "streaming", "completed", session_duration
        )

    except Exception as e:
        logger.error(f"Error en generate_stream_response: {str(e)}")
        error_data = {
            "error": str(e),
            "conversation_id": conversation_id,
            "status": "error",
        }
        yield f"event: error\\ndata: {json.dumps(error_data)}\\n\\n"


@router.post("/chat", response_class=EventSourceResponse)
async def stream_chat(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    orchestrator: StreamingNGXNexusOrchestrator = Depends(get_orchestrator),
):
    """
    Endpoint de streaming para chat con SSE.

    Este endpoint permite recibir respuestas en tiempo real mientras
    el sistema procesa la consulta del usuario.

    Args:
        request: Petición de chat con el mensaje del usuario
        current_user: Usuario autenticado
        orchestrator: Instancia del orquestador

    Returns:
        EventSourceResponse con los chunks de respuesta
    """
    try:
        # Validar entrada
        if not request.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El mensaje no puede estar vacío",
            )

        # Generar ID de conversación
        conversation_id = request.conversation_id or str(uuid.uuid4())

        logger.info(
            f"Iniciando streaming de chat para usuario {current_user['id']}, conversación {conversation_id}"
        )

        # Retornar respuesta SSE
        return EventSourceResponse(
            generate_stream_response(
                orchestrator=orchestrator,
                request=request,
                current_user=current_user,
                conversation_id=conversation_id,
            ),
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(f"Error en stream_chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la solicitud: {str(e)}",
        )


@router.get("/health")
async def stream_health():
    """
    Endpoint de salud para verificar que el servicio de streaming está funcionando.

    Returns:
        Estado del servicio de streaming
    """
    return {"status": "healthy", "service": "stream", "sse_enabled": True}

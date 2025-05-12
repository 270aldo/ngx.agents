"""
Router de chat para la API de NGX Agents.

Este módulo proporciona endpoints para interactuar con el sistema de agentes
a través del Orchestrator, que coordina la comunicación entre agentes.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, BackgroundTasks, Request

from core.auth import get_current_user
from core.logging_config import get_logger
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from app.schemas.chat import ChatRequest, ChatResponse, AgentResponse
from agents.orchestrator.agent import NGXNexusOrchestrator
from config import settings

# Configurar logger
logger = get_logger(__name__)

# Crear router
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={401: {"description": "No autorizado"}},
)

# Variable global para el orquestador (Singleton)
_orchestrator_instance: Optional[NGXNexusOrchestrator] = None
_orchestrator_lock = asyncio.Lock()

def get_orchestrator() -> NGXNexusOrchestrator:
    """
    Dependencia para obtener una instancia del Orchestrator.
    Utiliza un patrón Singleton simple para la instancia del orquestador.
    
    Returns:
        Instancia del Orchestrator
    """
    global _orchestrator_instance

    if _orchestrator_instance is None:
        logger.info("Creando nueva instancia de NGXNexusOrchestrator.")
        state_manager = state_manager_adapter
        
        # La URL para las llamadas HTTP A2A del Orquestador debe apuntar
        # al servidor FastAPI principal donde se exponen los endpoints /a2a/{agent_id}/process
        http_a2a_target_url = f"http://{settings.API_HOST}:{settings.API_PORT}"
        logger.debug(f"NGXNexusOrchestrator se inicializará con a2a_server_url (para HTTP A2A) = {http_a2a_target_url}")

        _orchestrator_instance = NGXNexusOrchestrator(
            a2a_server_url=http_a2a_target_url, # Esta URL es para las llamadas HTTP A2A salientes
            state_manager=state_manager
            # mcp_toolkit, model, instruction, etc., tomarán sus valores por defecto
            # o podrían configurarse aquí si es necesario.
        )
        # No llamamos a orchestrator.connect() aquí. 
        # El Orchestrator se conectará (si necesita WebSocket) cuando sea necesario,
        # o sus llamadas HTTP no requieren una conexión persistente explícita de este tipo.
    
    return _orchestrator_instance


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Depends(get_current_user),
    orchestrator: NGXNexusOrchestrator = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """
    Procesa un mensaje de chat utilizando el Orchestrator.
    
    El Orchestrator analiza la intención del mensaje y coordina con los agentes
    especializados para generar una respuesta completa.
    
    Args:
        request: Datos de la solicitud
        background_tasks: Tareas en segundo plano
        user_id: ID del usuario autenticado
        orchestrator: Instancia del Orchestrator
        
    Returns:
        Respuesta del chat
    """
    try:
        # Usar el user_id de la solicitud si está presente, de lo contrario usar el autenticado
        effective_user_id = request.user_id or user_id
        
        # Obtener o generar session_id
        session_id = request.session_id or str(uuid.uuid4())
        
        logger.info(f"Procesando mensaje de chat para usuario {effective_user_id}, sesión {session_id}")
        
        # Preparar contexto
        context = request.context or {}
        context.update({
            "user_id": effective_user_id,
            "session_id": session_id
        })
        
        # Conectar al servidor A2A si es necesario
        if not orchestrator.is_connected:
            background_tasks.add_task(orchestrator.connect)
            # Esperar brevemente para que se establezca la conexión
            await asyncio.sleep(1)
        
        # Ejecutar el Orchestrator
        result = await orchestrator.run_async(
            input_text=request.text,
            user_id=effective_user_id,
            session_id=session_id,
            context=context
        )
        
        # Extraer información de la respuesta
        response_text = result.get("response", "")
        agents_used = result.get("agents_used", [])
        metadata = result.get("metadata", {})
        
        # Construir respuestas de agentes individuales
        agent_responses = []
        for agent_data in result.get("agent_responses", []):
            agent_responses.append(
                AgentResponse(
                    agent_id=agent_data.get("agent_id", ""),
                    agent_name=agent_data.get("agent_name", ""),
                    response=agent_data.get("response", ""),
                    confidence=agent_data.get("confidence", 1.0),
                    artifacts=agent_data.get("artifacts", [])
                )
            )
        
        # Construir respuesta final
        response = ChatResponse(
            response=response_text,
            session_id=session_id,
            agents_used=agents_used,
            agent_responses=agent_responses,
            metadata=metadata
        )
        
        logger.info(f"Mensaje de chat procesado correctamente para usuario {effective_user_id}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error al procesar mensaje de chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar mensaje: {str(e)}"
        )


@router.post("/stream", response_model=None)
async def chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Depends(get_current_user),
    orchestrator: NGXNexusOrchestrator = Depends(get_orchestrator)
):
    """
    Procesa un mensaje de chat y devuelve la respuesta como un stream.
    
    Este endpoint es similar a /chat, pero devuelve la respuesta como un stream
    de eventos SSE (Server-Sent Events), lo que permite mostrar la respuesta
    de forma incremental al usuario.
    
    Args:
        request: Datos de la solicitud
        background_tasks: Tareas en segundo plano
        user_id: ID del usuario autenticado
        orchestrator: Instancia del Orchestrator
        
    Returns:
        Stream de eventos SSE con la respuesta
    """
    # Esta funcionalidad se implementará en una fase posterior
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint no implementado todavía"
    )

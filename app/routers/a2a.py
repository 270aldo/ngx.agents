"""
Router para la comunicación Agent-to-Agent (A2A) interna.

Este router maneja las solicitudes HTTP que el NGXNexusOrchestrator
envía a otros agentes.
"""

from fastapi import APIRouter, HTTPException, Body, Path, status
from typing import Dict, Any
import logging

# Importar esquemas desde app.schemas.a2a
from app.schemas.a2a import A2AProcessRequest, A2AResponse

# Importar BaseAgent y get_agent desde la ubicación correcta
from agents.base.base_agent import BaseAgent
from app.routers.agents import get_agent

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/a2a",
    tags=["A2A Communication"],
)


@router.post(
    "/{agent_path_id}/process",
    response_model=A2AResponse,
    summary="Procesa una solicitud para un agente específico",
    description="Recibe una entrada de usuario y contexto, la dirige al agente especificado y devuelve su respuesta.",
)
async def process_agent_request(
    agent_path_id: str = Path(..., description="El ID o path_id del agente a invocar"),
    request_body: A2AProcessRequest = Body(...),
):
    logger.info(f"A2A Router: Solicitud recibida para el agente: {agent_path_id}")
    logger.debug(f"A2A Router: Cuerpo de la solicitud: {request_body.dict()}")

    try:
        agent: BaseAgent = get_agent(agent_id=agent_path_id)
    except HTTPException as e:
        logger.warning(
            f"A2A Router: Agente {agent_path_id} no encontrado. Detalle: {e.detail}"
        )
        raise e
    except Exception as e:
        logger.error(
            f"A2A Router: Error inesperado al obtener el agente {agent_path_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al intentar obtener el agente {agent_path_id}",
        )

    try:
        run_kwargs = request_body.kwargs or {}

        agent_result: Dict[str, Any] = await agent.run(
            user_input=request_body.user_input,
            user_id=request_body.user_id,
            session_id=request_body.session_id,
            **run_kwargs,
        )

        logger.debug(
            f"A2A Router: Resultado del agente {agent_path_id}: {agent_result}"
        )

        if agent_result.get("status") == "success":
            return A2AResponse(
                response=str(agent_result.get("response", "")),
                artifacts=agent_result.get("artifacts", []),
            )
        else:
            error_detail = agent_result.get("error", "Error desconocido del agente")
            response_content = agent_result.get(
                "response",
                f"Error al procesar la solicitud por el agente {agent_path_id}.",
            )
            logger.error(
                f"A2A Router: Agente {agent_path_id} devolvió un error: {error_detail}. Respuesta: {response_content}"
            )
            # Devolvemos una respuesta exitosa (200) pero con el contenido del error,
            # ya que el orquestador espera un 200 y maneja la respuesta.
            return A2AResponse(response=response_content, artifacts=[])

    except Exception as e:
        logger.error(
            f"A2A Router: Error inesperado al ejecutar el agente {agent_path_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al procesar la solicitud por el agente {agent_path_id}",
        )

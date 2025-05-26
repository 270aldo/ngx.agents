"""
API para el sistema de simulaciones de caos.

Este módulo proporciona endpoints para gestionar simulaciones de caos,
registrar eventos y consultar su estado.
"""

from typing import Dict, Any, Optional
import uuid
from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel, Field

from core.chaos_testing import chaos_testing_manager, ChaosEventType, ChaosEvent
from core.auth import get_current_user

# Crear router
router = APIRouter(
    prefix="/api/chaos",
    tags=["chaos"],
    responses={404: {"description": "No encontrado"}},
)


# Modelos de datos para la API
class ChaosEventRequest(BaseModel):
    """Solicitud para registrar un evento de caos."""

    event_type: str = Field(..., description="Tipo de evento")
    target: str = Field(..., description="Objetivo del evento")
    duration: int = Field(..., description="Duración en segundos")
    intensity: float = Field(default=1.0, description="Intensidad del evento (0.0-1.0)")
    delay: int = Field(
        default=0, description="Retraso antes de iniciar el evento en segundos"
    )
    description: Optional[str] = Field(
        default=None, description="Descripción del evento"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Parámetros adicionales para el evento"
    )


class ChaosEventResponse(BaseModel):
    """Respuesta con información de un evento de caos."""

    event_id: str = Field(..., description="ID del evento")
    event_type: str = Field(..., description="Tipo de evento")
    target: str = Field(..., description="Objetivo del evento")
    duration: int = Field(..., description="Duración en segundos")
    intensity: float = Field(..., description="Intensidad del evento (0.0-1.0)")
    delay: int = Field(
        ..., description="Retraso antes de iniciar el evento en segundos"
    )
    description: str = Field(..., description="Descripción del evento")
    parameters: Dict[str, Any] = Field(
        ..., description="Parámetros adicionales para el evento"
    )
    start_time: Optional[str] = Field(default=None, description="Fecha de inicio")
    end_time: Optional[str] = Field(default=None, description="Fecha de finalización")
    status: str = Field(..., description="Estado del evento")
    result: Optional[Any] = Field(default=None, description="Resultado del evento")
    error: Optional[str] = Field(default=None, description="Error del evento")


class ChaosEnableRequest(BaseModel):
    """Solicitud para habilitar las pruebas de caos."""

    safe_mode: bool = Field(
        default=True,
        description="Si se debe ejecutar en modo seguro (sin eventos destructivos)",
    )


@router.post("/enable", response_model=Dict[str, Any])
async def enable_chaos_testing(
    request: ChaosEnableRequest, user_id: str = Depends(get_current_user)
):
    """
    Habilita las pruebas de caos.

    Args:
        request: Solicitud con los parámetros
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    await chaos_testing_manager.enable(safe_mode=request.safe_mode)

    return {
        "success": True,
        "message": f"Pruebas de caos habilitadas (modo seguro: {request.safe_mode})",
    }


@router.post("/disable", response_model=Dict[str, Any])
async def disable_chaos_testing(user_id: str = Depends(get_current_user)):
    """
    Deshabilita las pruebas de caos.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    await chaos_testing_manager.disable()

    return {"success": True, "message": "Pruebas de caos deshabilitadas"}


@router.post("/events", response_model=ChaosEventResponse)
async def register_chaos_event(
    request: ChaosEventRequest, user_id: str = Depends(get_current_user)
):
    """
    Registra un evento de caos.

    Args:
        request: Solicitud con los datos del evento
        user_id: ID del usuario autenticado

    Returns:
        Información del evento registrado
    """
    try:
        # Convertir tipo de evento
        event_type = ChaosEventType(request.event_type)

        # Crear evento
        event_id = str(uuid.uuid4())
        event = ChaosEvent(
            event_id=event_id,
            event_type=event_type,
            target=request.target,
            duration=request.duration,
            intensity=request.intensity,
            delay=request.delay,
            description=request.description,
            parameters=request.parameters,
        )

        # Registrar evento
        await chaos_testing_manager.register_event(event)

        return ChaosEventResponse(**event.to_dict())

    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Tipo de evento no válido: {request.event_type}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al registrar evento: {str(e)}"
        )


@router.post("/events/{event_id}/start", response_model=Dict[str, Any])
async def start_chaos_event(
    event_id: str = Path(..., description="ID del evento"),
    user_id: str = Depends(get_current_user),
):
    """
    Inicia un evento de caos.

    Args:
        event_id: ID del evento
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    success = await chaos_testing_manager.start_event(event_id)

    if not success:
        raise HTTPException(
            status_code=400, detail=f"No se pudo iniciar el evento {event_id}"
        )

    return {
        "success": True,
        "event_id": event_id,
        "message": f"Evento {event_id} iniciado",
    }


@router.post("/events/{event_id}/cancel", response_model=Dict[str, Any])
async def cancel_chaos_event(
    event_id: str = Path(..., description="ID del evento"),
    user_id: str = Depends(get_current_user),
):
    """
    Cancela un evento de caos en ejecución.

    Args:
        event_id: ID del evento
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    success = await chaos_testing_manager.cancel_event(event_id)

    if not success:
        raise HTTPException(
            status_code=400, detail=f"No se pudo cancelar el evento {event_id}"
        )

    return {
        "success": True,
        "event_id": event_id,
        "message": f"Evento {event_id} cancelado",
    }


@router.get("/events/{event_id}", response_model=ChaosEventResponse)
async def get_chaos_event(
    event_id: str = Path(..., description="ID del evento"),
    user_id: str = Depends(get_current_user),
):
    """
    Obtiene información sobre un evento de caos.

    Args:
        event_id: ID del evento
        user_id: ID del usuario autenticado

    Returns:
        Información del evento
    """
    event = await chaos_testing_manager.get_event(event_id)

    if not event:
        raise HTTPException(status_code=404, detail=f"Evento {event_id} no encontrado")

    return ChaosEventResponse(**event)


@router.get("/events", response_model=Dict[str, ChaosEventResponse])
async def get_all_chaos_events(user_id: str = Depends(get_current_user)):
    """
    Obtiene información sobre todos los eventos de caos.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Información de todos los eventos
    """
    events = await chaos_testing_manager.get_all_events()
    return {event_id: ChaosEventResponse(**event) for event_id, event in events.items()}


@router.get("/event-types", response_model=Dict[str, str])
async def get_chaos_event_types(user_id: str = Depends(get_current_user)):
    """
    Obtiene los tipos de eventos de caos disponibles.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Tipos de eventos disponibles
    """
    return {event_type.value: event_type.name for event_type in ChaosEventType}

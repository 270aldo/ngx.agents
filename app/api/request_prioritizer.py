"""
API para el sistema de priorización de solicitudes basado en SLAs.

Este módulo proporciona endpoints para gestionar solicitudes priorizadas,
consultar su estado y obtener resultados.
"""

from typing import Dict, Any, Optional
import asyncio
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field

from core.request_prioritizer import request_prioritizer, SLATier
from core.auth import get_current_user

# Crear router
router = APIRouter(
    prefix="/api/priority",
    tags=["priority"],
    responses={404: {"description": "No encontrado"}},
)


# Modelos de datos para la API
class RequestSubmitRequest(BaseModel):
    """Solicitud para enviar una solicitud priorizada."""

    data: Any = Field(..., description="Datos de la solicitud")
    handler_name: str = Field(..., description="Nombre del handler a utilizar")
    agent_id: Optional[str] = Field(default=None, description="ID del agente asociado")
    sla_tier: Optional[str] = Field(
        default=None, description="Nivel de SLA (platinum, gold, silver, bronze, free)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Metadatos adicionales"
    )


class RequestSubmitResponse(BaseModel):
    """Respuesta a una solicitud de envío de solicitud."""

    request_id: str = Field(..., description="ID de la solicitud")
    status: str = Field(..., description="Estado inicial de la solicitud")
    sla_tier: str = Field(..., description="Nivel de SLA asignado")


class RequestStatusResponse(BaseModel):
    """Respuesta con el estado de una solicitud."""

    request_id: str = Field(..., description="ID de la solicitud")
    user_id: str = Field(..., description="ID del usuario")
    agent_id: Optional[str] = Field(default=None, description="ID del agente asociado")
    sla_tier: str = Field(..., description="Nivel de SLA")
    status: str = Field(..., description="Estado de la solicitud")
    priority: int = Field(..., description="Prioridad de la solicitud")
    created_at: Optional[str] = Field(default=None, description="Fecha de creación")
    started_at: Optional[str] = Field(default=None, description="Fecha de inicio")
    completed_at: Optional[str] = Field(
        default=None, description="Fecha de finalización"
    )
    wait_time: float = Field(..., description="Tiempo de espera en segundos")
    processing_time: float = Field(
        ..., description="Tiempo de procesamiento en segundos"
    )
    has_result: bool = Field(..., description="Si la solicitud tiene resultado")
    has_error: bool = Field(..., description="Si la solicitud tiene error")
    metadata: Dict[str, Any] = Field(default={}, description="Metadatos adicionales")


class RequestResultResponse(BaseModel):
    """Respuesta con el resultado de una solicitud."""

    request_id: str = Field(..., description="ID de la solicitud")
    status: str = Field(..., description="Estado de la solicitud")
    result: Optional[Any] = Field(default=None, description="Resultado de la solicitud")
    error: Optional[str] = Field(default=None, description="Error de la solicitud")
    wait_time: float = Field(..., description="Tiempo de espera en segundos")
    processing_time: float = Field(
        ..., description="Tiempo de procesamiento en segundos"
    )
    total_time: Optional[float] = Field(
        default=None, description="Tiempo total en segundos"
    )


class PrioritizerStatsResponse(BaseModel):
    """Respuesta con estadísticas del priorizador."""

    total_requests: int = Field(..., description="Número total de solicitudes")
    completed_requests: int = Field(
        ..., description="Número de solicitudes completadas"
    )
    failed_requests: int = Field(..., description="Número de solicitudes fallidas")
    timeout_requests: int = Field(..., description="Número de solicitudes con timeout")
    rejected_requests: int = Field(..., description="Número de solicitudes rechazadas")
    avg_wait_time: float = Field(..., description="Tiempo medio de espera")
    avg_processing_time: float = Field(..., description="Tiempo medio de procesamiento")
    max_wait_time: float = Field(..., description="Tiempo máximo de espera")
    max_processing_time: float = Field(
        ..., description="Tiempo máximo de procesamiento"
    )
    queue_size: int = Field(..., description="Tamaño de la cola")
    status_counts: Dict[str, int] = Field(
        ..., description="Número de solicitudes por estado"
    )
    sla_counts: Dict[str, int] = Field(
        ..., description="Número de solicitudes por nivel de SLA"
    )
    agent_counts: Dict[str, int] = Field(
        ..., description="Número de solicitudes por agente"
    )
    active_workers: int = Field(..., description="Número de workers activos")
    max_workers: int = Field(..., description="Número máximo de workers")
    user_count: int = Field(..., description="Número de usuarios")


class SLAConfigResponse(BaseModel):
    """Respuesta con la configuración de SLA."""

    tier: str = Field(..., description="Nivel de SLA")
    max_wait_time: int = Field(..., description="Tiempo máximo de espera en segundos")
    priority_boost: int = Field(
        ..., description="Incremento de prioridad por segundo de espera"
    )
    max_concurrent: int = Field(..., description="Máximo de solicitudes concurrentes")
    daily_quota: Optional[int] = Field(default=None, description="Cuota diaria")
    rate_limit: Optional[int] = Field(
        default=None, description="Límite de solicitudes por minuto"
    )
    timeout: Optional[int] = Field(default=None, description="Timeout en segundos")


# Registro de handlers disponibles
# Esto es un ejemplo, en una implementación real se registrarían dinámicamente
AVAILABLE_HANDLERS = {
    "analyze_sentiment": {
        "module": "clients.gemini_client",
        "function": "analyze_sentiment",
        "description": "Analiza el sentimiento de un texto",
    },
    "summarize_text": {
        "module": "clients.gemini_client",
        "function": "summarize",
        "description": "Genera un resumen de un texto",
    },
    "analyze_image": {
        "module": "clients.gemini_client",
        "function": "analyze_image",
        "description": "Analiza una imagen",
    },
    "analyze_pdf": {
        "module": "clients.gemini_client",
        "function": "analyze_pdf",
        "description": "Analiza un documento PDF",
    },
    "analyze_csv": {
        "module": "clients.gemini_client",
        "function": "analyze_csv",
        "description": "Analiza un archivo CSV",
    },
}


@router.post("/requests", response_model=RequestSubmitResponse)
async def submit_request(
    request: RequestSubmitRequest, user_id: str = Depends(get_current_user)
):
    """
    Envía una solicitud para procesamiento priorizado.

    Args:
        request: Solicitud con los datos
        user_id: ID del usuario autenticado

    Returns:
        ID de la solicitud creada
    """
    # Verificar si el handler está disponible
    if request.handler_name not in AVAILABLE_HANDLERS:
        raise HTTPException(
            status_code=400, detail=f"Handler '{request.handler_name}' no disponible"
        )

    try:
        # Obtener información del handler
        handler_info = AVAILABLE_HANDLERS[request.handler_name]

        # Importar dinámicamente la función
        module_name = handler_info["module"]
        function_name = handler_info["function"]

        module = __import__(module_name, fromlist=[function_name])
        func = getattr(module, function_name)

        # Convertir nivel de SLA de string a enum si se proporciona
        sla_tier = None
        if request.sla_tier:
            try:
                sla_tier = SLATier[request.sla_tier.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Nivel de SLA '{request.sla_tier}' no válido",
                )

        # Añadir metadatos
        metadata = request.metadata or {}
        metadata["handler_name"] = request.handler_name

        # Enviar solicitud
        request_id = await request_prioritizer.submit_request(
            user_id=user_id,
            data=request.data,
            handler=func,
            agent_id=request.agent_id,
            sla_tier=sla_tier,
            metadata=metadata,
        )

        # Obtener estado inicial
        status = await request_prioritizer.get_request_status(request_id)

        return RequestSubmitResponse(
            request_id=request_id, status=status["status"], sla_tier=status["sla_tier"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al enviar solicitud: {str(e)}"
        )


@router.get("/requests/{request_id}", response_model=RequestStatusResponse)
async def get_request_status(
    request_id: str = Path(..., description="ID de la solicitud"),
    user_id: str = Depends(get_current_user),
):
    """
    Obtiene el estado de una solicitud.

    Args:
        request_id: ID de la solicitud
        user_id: ID del usuario autenticado

    Returns:
        Estado de la solicitud
    """
    status = await request_prioritizer.get_request_status(request_id)

    if not status:
        raise HTTPException(
            status_code=404, detail=f"Solicitud {request_id} no encontrada"
        )

    # Verificar que la solicitud pertenezca al usuario
    if status["user_id"] != user_id:
        raise HTTPException(
            status_code=403, detail="No tienes permiso para acceder a esta solicitud"
        )

    return RequestStatusResponse(**status)


@router.get("/requests/{request_id}/result", response_model=RequestResultResponse)
async def get_request_result(
    request_id: str = Path(..., description="ID de la solicitud"),
    wait: bool = Query(False, description="Esperar a que la solicitud termine"),
    timeout: Optional[float] = Query(
        None, description="Tiempo máximo de espera en segundos"
    ),
    user_id: str = Depends(get_current_user),
):
    """
    Obtiene el resultado de una solicitud.

    Args:
        request_id: ID de la solicitud
        wait: Si se debe esperar a que la solicitud termine
        timeout: Tiempo máximo de espera en segundos
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la solicitud
    """
    # Verificar que la solicitud pertenezca al usuario
    status = await request_prioritizer.get_request_status(request_id)
    if not status:
        raise HTTPException(
            status_code=404, detail=f"Solicitud {request_id} no encontrada"
        )

    if status["user_id"] != user_id:
        raise HTTPException(
            status_code=403, detail="No tienes permiso para acceder a esta solicitud"
        )

    try:
        result = await request_prioritizer.get_request_result(
            request_id, wait=wait, timeout=timeout
        )
        return RequestResultResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except asyncio.TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener resultado: {str(e)}"
        )


@router.get("/stats", response_model=PrioritizerStatsResponse)
async def get_prioritizer_stats(user_id: str = Depends(get_current_user)):
    """
    Obtiene estadísticas del priorizador de solicitudes.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Estadísticas del priorizador
    """
    stats = await request_prioritizer.get_stats()
    return PrioritizerStatsResponse(**stats)


@router.post("/clear", response_model=Dict[str, Any])
async def clear_completed_requests(
    older_than: Optional[int] = Query(
        None, description="Eliminar solicitudes completadas hace más de X segundos"
    ),
    user_id: str = Depends(get_current_user),
):
    """
    Elimina solicitudes completadas del priorizador.

    Args:
        older_than: Eliminar solicitudes completadas hace más de X segundos
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    removed_count = await request_prioritizer.clear_completed_requests(older_than)

    return {
        "success": True,
        "removed_count": removed_count,
        "message": f"Eliminadas {removed_count} solicitudes completadas",
    }


@router.get("/sla-configs", response_model=Dict[str, SLAConfigResponse])
async def get_sla_configs(user_id: str = Depends(get_current_user)):
    """
    Obtiene las configuraciones de SLA disponibles.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Configuraciones de SLA
    """
    configs = {}

    for tier, config in request_prioritizer.sla_configs.items():
        configs[tier.value] = SLAConfigResponse(**config.to_dict())

    return configs


@router.get("/handlers", response_model=Dict[str, Dict[str, str]])
async def get_available_handlers(user_id: str = Depends(get_current_user)):
    """
    Obtiene la lista de handlers disponibles.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Lista de handlers disponibles
    """
    return AVAILABLE_HANDLERS

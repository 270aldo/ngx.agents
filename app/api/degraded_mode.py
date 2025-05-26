"""
API para el sistema de modos degradados.

Este módulo proporciona endpoints para gestionar modos degradados,
registrar servicios y consultar su estado.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path
from pydantic import BaseModel, Field

from core.degraded_mode import (
    degraded_mode_manager,
    DegradationLevel,
    DegradationReason,
)
from core.auth import get_current_user

# Crear router
router = APIRouter(
    prefix="/api/degraded-mode",
    tags=["degraded-mode"],
    responses={404: {"description": "No encontrado"}},
)


# Modelos de datos para la API
class ServiceStatusResponse(BaseModel):
    """Respuesta con el estado de un servicio."""

    service_id: str = Field(..., description="ID del servicio")
    name: str = Field(..., description="Nombre del servicio")
    description: str = Field(..., description="Descripción del servicio")
    is_critical: bool = Field(..., description="Si el servicio es crítico")
    dependencies: List[str] = Field(
        ..., description="IDs de servicios de los que depende"
    )
    is_available: bool = Field(..., description="Si el servicio está disponible")
    degradation_level: int = Field(..., description="Nivel de degradación")
    degradation_reason: Optional[str] = Field(
        default=None, description="Razón de la degradación"
    )
    last_status_change: str = Field(
        ..., description="Fecha del último cambio de estado"
    )
    last_check: str = Field(..., description="Fecha de la última comprobación")
    failure_count: int = Field(..., description="Contador de fallos")
    success_count: int = Field(..., description="Contador de éxitos")
    metadata: Dict[str, Any] = Field(..., description="Metadatos adicionales")


class SystemStatusResponse(BaseModel):
    """Respuesta con el estado global del sistema."""

    degradation_level: int = Field(..., description="Nivel de degradación")
    degradation_level_name: str = Field(
        ..., description="Nombre del nivel de degradación"
    )
    degradation_reason: Optional[str] = Field(
        default=None, description="Razón de la degradación"
    )
    degradation_start: Optional[str] = Field(
        default=None, description="Fecha de inicio de la degradación"
    )
    degradation_message: Optional[str] = Field(
        default=None, description="Mensaje de degradación"
    )
    degradation_duration: float = Field(
        ..., description="Duración de la degradación en segundos"
    )
    services_total: int = Field(..., description="Número total de servicios")
    services_available: int = Field(..., description="Número de servicios disponibles")
    services_unavailable: int = Field(
        ..., description="Número de servicios no disponibles"
    )
    critical_services_total: int = Field(
        ..., description="Número total de servicios críticos"
    )
    critical_services_available: int = Field(
        ..., description="Número de servicios críticos disponibles"
    )
    critical_services_unavailable: int = Field(
        ..., description="Número de servicios críticos no disponibles"
    )


class ServiceRegisterRequest(BaseModel):
    """Solicitud para registrar un servicio."""

    service_id: str = Field(..., description="ID del servicio")
    name: str = Field(..., description="Nombre del servicio")
    description: str = Field(..., description="Descripción del servicio")
    is_critical: bool = Field(default=False, description="Si el servicio es crítico")
    dependencies: List[str] = Field(
        default=[], description="IDs de servicios de los que depende"
    )


class ServiceStatusUpdateRequest(BaseModel):
    """Solicitud para actualizar el estado de un servicio."""

    is_available: bool = Field(..., description="Si el servicio está disponible")
    reason: Optional[str] = Field(default=None, description="Razón de la degradación")
    message: Optional[str] = Field(default=None, description="Mensaje descriptivo")
    level: Optional[int] = Field(default=None, description="Nivel de degradación")


class FeatureUpdateRequest(BaseModel):
    """Solicitud para actualizar el estado de una funcionalidad."""

    enabled: bool = Field(..., description="Si la funcionalidad está habilitada")


@router.get("/system", response_model=SystemStatusResponse)
async def get_system_status(user_id: str = Depends(get_current_user)):
    """
    Obtiene el estado global del sistema.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Estado global del sistema
    """
    status = await degraded_mode_manager.get_system_status()
    return SystemStatusResponse(**status)


@router.get("/services", response_model=Dict[str, ServiceStatusResponse])
async def get_all_services(user_id: str = Depends(get_current_user)):
    """
    Obtiene el estado de todos los servicios.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Estado de todos los servicios
    """
    services = await degraded_mode_manager.get_all_services()
    return services


@router.get("/services/{service_id}", response_model=ServiceStatusResponse)
async def get_service_status(
    service_id: str = Path(..., description="ID del servicio"),
    user_id: str = Depends(get_current_user),
):
    """
    Obtiene el estado de un servicio.

    Args:
        service_id: ID del servicio
        user_id: ID del usuario autenticado

    Returns:
        Estado del servicio
    """
    status = await degraded_mode_manager.get_service_status(service_id)

    if not status:
        raise HTTPException(
            status_code=404, detail=f"Servicio {service_id} no encontrado"
        )

    return ServiceStatusResponse(**status)


@router.post("/services", response_model=ServiceStatusResponse)
async def register_service(
    request: ServiceRegisterRequest, user_id: str = Depends(get_current_user)
):
    """
    Registra un nuevo servicio.

    Args:
        request: Datos del servicio
        user_id: ID del usuario autenticado

    Returns:
        Estado del servicio registrado
    """
    service = await degraded_mode_manager.register_service(
        service_id=request.service_id,
        name=request.name,
        description=request.description,
        is_critical=request.is_critical,
        dependencies=request.dependencies,
    )

    return ServiceStatusResponse(**service.to_dict())


@router.delete("/services/{service_id}", response_model=Dict[str, Any])
async def unregister_service(
    service_id: str = Path(..., description="ID del servicio"),
    user_id: str = Depends(get_current_user),
):
    """
    Elimina un servicio del registro.

    Args:
        service_id: ID del servicio
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    success = await degraded_mode_manager.unregister_service(service_id)

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Servicio {service_id} no encontrado"
        )

    return {"success": True, "message": f"Servicio {service_id} eliminado"}


@router.put("/services/{service_id}/status", response_model=ServiceStatusResponse)
async def update_service_status(
    service_id: str = Path(..., description="ID del servicio"),
    request: ServiceStatusUpdateRequest = Body(...),
    user_id: str = Depends(get_current_user),
):
    """
    Actualiza el estado de un servicio.

    Args:
        service_id: ID del servicio
        request: Datos del estado
        user_id: ID del usuario autenticado

    Returns:
        Estado actualizado del servicio
    """
    if request.is_available:
        success = await degraded_mode_manager.set_service_available(service_id)
    else:
        # Convertir strings a enums
        reason = (
            DegradationReason(request.reason)
            if request.reason
            else DegradationReason.MANUAL
        )
        level = (
            DegradationLevel(request.level)
            if request.level is not None
            else DegradationLevel.MEDIUM
        )

        success = await degraded_mode_manager.set_service_unavailable(
            service_id=service_id, reason=reason, message=request.message, level=level
        )

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Servicio {service_id} no encontrado"
        )

    status = await degraded_mode_manager.get_service_status(service_id)
    return ServiceStatusResponse(**status)


@router.put("/features/{feature_id}", response_model=Dict[str, Any])
async def update_feature_status(
    feature_id: str = Path(..., description="ID de la funcionalidad"),
    request: FeatureUpdateRequest = Body(...),
    user_id: str = Depends(get_current_user),
):
    """
    Actualiza el estado de una funcionalidad.

    Args:
        feature_id: ID de la funcionalidad
        request: Datos del estado
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    await degraded_mode_manager.set_feature_enabled(feature_id, request.enabled)

    return {"success": True, "feature_id": feature_id, "enabled": request.enabled}


@router.get("/features/{feature_id}", response_model=Dict[str, Any])
async def get_feature_status(
    feature_id: str = Path(..., description="ID de la funcionalidad"),
    default: bool = Query(
        True, description="Valor por defecto si la funcionalidad no está registrada"
    ),
    user_id: str = Depends(get_current_user),
):
    """
    Obtiene el estado de una funcionalidad.

    Args:
        feature_id: ID de la funcionalidad
        default: Valor por defecto si la funcionalidad no está registrada
        user_id: ID del usuario autenticado

    Returns:
        Estado de la funcionalidad
    """
    enabled = await degraded_mode_manager.is_feature_enabled(feature_id, default)

    return {"feature_id": feature_id, "enabled": enabled}


@router.post("/start-monitoring", response_model=Dict[str, Any])
async def start_monitoring(user_id: str = Depends(get_current_user)):
    """
    Inicia la monitorización de servicios.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    await degraded_mode_manager.start_monitoring()

    return {"success": True, "message": "Monitorización de servicios iniciada"}


@router.post("/stop-monitoring", response_model=Dict[str, Any])
async def stop_monitoring(user_id: str = Depends(get_current_user)):
    """
    Detiene la monitorización de servicios.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    await degraded_mode_manager.stop_monitoring()

    return {"success": True, "message": "Monitorización de servicios detenida"}

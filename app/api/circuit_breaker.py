"""
API para el sistema de circuit breaker.

Este módulo proporciona endpoints para gestionar circuit breakers,
consultar su estado y resetearlos.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel, Field

from core.circuit_breaker import circuit_breaker_registry, CircuitBreakerConfig
from core.auth import get_current_user

# Crear router
router = APIRouter(
    prefix="/api/circuit-breaker",
    tags=["circuit-breaker"],
    responses={404: {"description": "No encontrado"}},
)


# Modelos de datos para la API
class CircuitBreakerConfigRequest(BaseModel):
    """Solicitud para configurar un circuit breaker."""

    failure_threshold: int = Field(
        default=5, description="Número de fallos para abrir el circuito"
    )
    success_threshold: int = Field(
        default=2, description="Número de éxitos para cerrar el circuito"
    )
    timeout: int = Field(
        default=60, description="Tiempo en segundos que el circuito permanece abierto"
    )
    window_size: int = Field(
        default=10, description="Tamaño de la ventana para calcular la tasa de fallos"
    )
    error_threshold_percentage: float = Field(
        default=50.0, description="Porcentaje de fallos para abrir el circuito"
    )


class CircuitBreakerConfigResponse(BaseModel):
    """Respuesta con la configuración de un circuit breaker."""

    failure_threshold: int = Field(
        ..., description="Número de fallos para abrir el circuito"
    )
    success_threshold: int = Field(
        ..., description="Número de éxitos para cerrar el circuito"
    )
    timeout: int = Field(
        ..., description="Tiempo en segundos que el circuito permanece abierto"
    )
    has_fallback: bool = Field(..., description="Si tiene función de fallback")
    exclude_exceptions: List[str] = Field(
        ..., description="Excepciones que no cuentan como fallos"
    )
    include_exceptions: Optional[List[str]] = Field(
        default=None, description="Solo estas excepciones cuentan como fallos"
    )
    window_size: int = Field(
        ..., description="Tamaño de la ventana para calcular la tasa de fallos"
    )
    error_threshold_percentage: float = Field(
        ..., description="Porcentaje de fallos para abrir el circuito"
    )


class CircuitBreakerStateResponse(BaseModel):
    """Respuesta con el estado de un circuit breaker."""

    name: str = Field(..., description="Nombre del circuit breaker")
    state: str = Field(
        ..., description="Estado del circuit breaker (closed, open, half_open)"
    )
    failure_count: int = Field(..., description="Contador de fallos")
    success_count: int = Field(..., description="Contador de éxitos")
    last_failure_time: Optional[str] = Field(
        default=None, description="Fecha del último fallo"
    )
    last_state_change_time: str = Field(
        ..., description="Fecha del último cambio de estado"
    )
    results_window: List[bool] = Field(..., description="Historial de resultados")
    failure_rate: float = Field(..., description="Tasa de fallos")
    config: CircuitBreakerConfigResponse = Field(
        ..., description="Configuración del circuit breaker"
    )
    stats: Dict[str, Any] = Field(..., description="Estadísticas del circuit breaker")


class CircuitBreakerCreateRequest(BaseModel):
    """Solicitud para crear un circuit breaker."""

    name: str = Field(..., description="Nombre del circuit breaker")
    config: CircuitBreakerConfigRequest = Field(
        ..., description="Configuración del circuit breaker"
    )


@router.get("/", response_model=Dict[str, CircuitBreakerStateResponse])
async def get_all_circuit_breakers(user_id: str = Depends(get_current_user)):
    """
    Obtiene el estado de todos los circuit breakers.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Estado de todos los circuit breakers
    """
    states = await circuit_breaker_registry.get_all_states()
    return states


@router.get("/{name}", response_model=CircuitBreakerStateResponse)
async def get_circuit_breaker(
    name: str = Path(..., description="Nombre del circuit breaker"),
    user_id: str = Depends(get_current_user),
):
    """
    Obtiene el estado de un circuit breaker.

    Args:
        name: Nombre del circuit breaker
        user_id: ID del usuario autenticado

    Returns:
        Estado del circuit breaker
    """
    circuit_breaker = await circuit_breaker_registry.get(name)

    if not circuit_breaker:
        raise HTTPException(
            status_code=404, detail=f"Circuit breaker '{name}' no encontrado"
        )

    return circuit_breaker.get_state()


@router.post("/", response_model=CircuitBreakerStateResponse)
async def create_circuit_breaker(
    request: CircuitBreakerCreateRequest, user_id: str = Depends(get_current_user)
):
    """
    Crea un nuevo circuit breaker.

    Args:
        request: Solicitud con los datos del circuit breaker
        user_id: ID del usuario autenticado

    Returns:
        Estado del circuit breaker creado
    """
    # Crear configuración
    config = CircuitBreakerConfig(
        failure_threshold=request.config.failure_threshold,
        success_threshold=request.config.success_threshold,
        timeout=request.config.timeout,
        window_size=request.config.window_size,
        error_threshold_percentage=request.config.error_threshold_percentage,
    )

    # Crear circuit breaker
    circuit_breaker = await circuit_breaker_registry.get_or_create(request.name, config)

    return circuit_breaker.get_state()


@router.post("/{name}/reset", response_model=Dict[str, Any])
async def reset_circuit_breaker(
    name: str = Path(..., description="Nombre del circuit breaker"),
    user_id: str = Depends(get_current_user),
):
    """
    Resetea un circuit breaker.

    Args:
        name: Nombre del circuit breaker
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    success = await circuit_breaker_registry.reset(name)

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Circuit breaker '{name}' no encontrado"
        )

    return {"success": True, "message": f"Circuit breaker '{name}' reseteado"}


@router.post("/reset-all", response_model=Dict[str, Any])
async def reset_all_circuit_breakers(user_id: str = Depends(get_current_user)):
    """
    Resetea todos los circuit breakers.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    await circuit_breaker_registry.reset_all()

    return {"success": True, "message": "Todos los circuit breakers reseteados"}

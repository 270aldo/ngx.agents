"""
API para gestionar presupuestos de agentes.

Este módulo proporciona endpoints para consultar y gestionar los presupuestos
de tokens por agente.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from core.budget import budget_manager, AgentBudget
from core.settings import settings

# Crear router
router = APIRouter(
    prefix="/api/budgets",
    tags=["budgets"],
    responses={404: {"description": "No encontrado"}},
)


# Modelos de datos para la API
class BudgetStatusResponse(BaseModel):
    """Respuesta con el estado del presupuesto de un agente."""

    agent_id: str
    budget: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    percentage: float = 0.0
    remaining: int = 0
    period: str = ""
    next_reset: Optional[str] = None
    status: str = "ok"


class BudgetUpdateRequest(BaseModel):
    """Solicitud para actualizar el presupuesto de un agente."""

    max_tokens: Optional[int] = None
    period: Optional[str] = None
    action_on_limit: Optional[str] = None
    fallback_model: Optional[str] = None
    reset_day: Optional[int] = None


class BudgetSummaryResponse(BaseModel):
    """Resumen de presupuestos para todos los agentes."""

    total_agents: int
    total_usage: int
    total_cost: float
    agents: List[BudgetStatusResponse]


@router.get("/", response_model=BudgetSummaryResponse)
async def get_all_budgets():
    """
    Obtiene un resumen de los presupuestos de todos los agentes.
    """
    if not settings.enable_budgets:
        raise HTTPException(
            status_code=400, detail="Sistema de presupuestos deshabilitado"
        )

    # Obtener todos los agentes con presupuesto
    agent_ids = list(budget_manager.budgets.keys())

    # Obtener estado de presupuesto para cada agente
    agents_status = []
    total_usage = 0
    total_cost = 0.0

    for agent_id in agent_ids:
        status = budget_manager.get_budget_status(agent_id)

        # Convertir next_reset a string si existe
        if status.get("next_reset"):
            status["next_reset"] = status["next_reset"].isoformat()

        agents_status.append(BudgetStatusResponse(**status))

        # Acumular totales
        usage = status.get("usage", {})
        total_usage += usage.get("total_tokens", 0)
        total_cost += usage.get("estimated_cost_usd", 0.0)

    return BudgetSummaryResponse(
        total_agents=len(agent_ids),
        total_usage=total_usage,
        total_cost=total_cost,
        agents=agents_status,
    )


@router.get("/{agent_id}", response_model=BudgetStatusResponse)
async def get_agent_budget(agent_id: str = Path(..., description="ID del agente")):
    """
    Obtiene el estado del presupuesto para un agente específico.
    """
    if not settings.enable_budgets:
        raise HTTPException(
            status_code=400, detail="Sistema de presupuestos deshabilitado"
        )

    status = budget_manager.get_budget_status(agent_id)

    if status.get("status") == "no_budget":
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró presupuesto para el agente {agent_id}",
        )

    # Convertir next_reset a string si existe
    if status.get("next_reset"):
        status["next_reset"] = status["next_reset"].isoformat()

    return BudgetStatusResponse(**status)


@router.put("/{agent_id}", response_model=BudgetStatusResponse)
async def update_agent_budget(
    update_data: BudgetUpdateRequest,
    agent_id: str = Path(..., description="ID del agente"),
):
    """
    Actualiza el presupuesto para un agente específico.
    """
    if not settings.enable_budgets:
        raise HTTPException(
            status_code=400, detail="Sistema de presupuestos deshabilitado"
        )

    # Verificar si existe el presupuesto
    budget = budget_manager.get_budget(agent_id)
    if not budget:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró presupuesto para el agente {agent_id}",
        )

    # Actualizar campos si se proporcionan
    if update_data.max_tokens is not None:
        budget.max_tokens = update_data.max_tokens

    if update_data.period is not None:
        try:
            budget.period = update_data.period
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Período inválido: {update_data.period}"
            )

    if update_data.action_on_limit is not None:
        try:
            budget.action_on_limit = update_data.action_on_limit
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Acción inválida: {update_data.action_on_limit}",
            )

    if update_data.fallback_model is not None:
        budget.fallback_model = update_data.fallback_model

    if update_data.reset_day is not None:
        if update_data.reset_day < 1 or update_data.reset_day > 31:
            raise HTTPException(
                status_code=400, detail="El día de reset debe estar entre 1 y 31"
            )
        budget.reset_day = update_data.reset_day

    # Actualizar el presupuesto
    budget_manager.set_budget(budget)

    # Obtener el estado actualizado
    status = budget_manager.get_budget_status(agent_id)

    # Convertir next_reset a string si existe
    if status.get("next_reset"):
        status["next_reset"] = status["next_reset"].isoformat()

    return BudgetStatusResponse(**status)


@router.post("/{agent_id}/reset", response_model=BudgetStatusResponse)
async def reset_agent_usage(agent_id: str = Path(..., description="ID del agente")):
    """
    Resetea el contador de uso para un agente específico.
    """
    if not settings.enable_budgets:
        raise HTTPException(
            status_code=400, detail="Sistema de presupuestos deshabilitado"
        )

    # Verificar si existe el presupuesto
    budget = budget_manager.get_budget(agent_id)
    if not budget:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró presupuesto para el agente {agent_id}",
        )

    # Resetear el uso
    budget_manager._reset_usage(agent_id)

    # Obtener el estado actualizado
    status = budget_manager.get_budget_status(agent_id)

    # Convertir next_reset a string si existe
    if status.get("next_reset"):
        status["next_reset"] = status["next_reset"].isoformat()

    return BudgetStatusResponse(**status)


@router.post("/{agent_id}", response_model=BudgetStatusResponse)
async def create_agent_budget(
    budget_data: BudgetUpdateRequest,
    agent_id: str = Path(..., description="ID del agente"),
):
    """
    Crea un nuevo presupuesto para un agente.
    """
    if not settings.enable_budgets:
        raise HTTPException(
            status_code=400, detail="Sistema de presupuestos deshabilitado"
        )

    # Verificar si ya existe el presupuesto
    existing_budget = budget_manager.get_budget(agent_id)
    if existing_budget:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un presupuesto para el agente {agent_id}",
        )

    # Valores por defecto
    max_tokens = budget_data.max_tokens or 1000000
    period = budget_data.period or "monthly"
    action_on_limit = budget_data.action_on_limit or "warn"
    fallback_model = budget_data.fallback_model
    reset_day = budget_data.reset_day or 1

    try:
        # Crear nuevo presupuesto
        budget = AgentBudget(
            agent_id=agent_id,
            max_tokens=max_tokens,
            period=period,
            action_on_limit=action_on_limit,
            fallback_model=fallback_model,
            reset_day=reset_day,
        )

        # Establecer el presupuesto
        budget_manager.set_budget(budget)

        # Obtener el estado
        status = budget_manager.get_budget_status(agent_id)

        # Convertir next_reset a string si existe
        if status.get("next_reset"):
            status["next_reset"] = status["next_reset"].isoformat()

        return BudgetStatusResponse(**status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

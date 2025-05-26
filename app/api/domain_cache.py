"""
API para gestionar el sistema de caché por dominio.

Este módulo proporciona endpoints para gestionar el sistema de caché por dominio,
permitiendo consultar estadísticas, limpiar el caché y registrar reglas de dominio.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from core.domain_cache import domain_cache, CacheStrategy
from core.auth import get_current_user

# Crear router
router = APIRouter(
    prefix="/api/cache",
    tags=["cache"],
    responses={404: {"description": "No encontrado"}},
)


# Modelos de datos para la API
class CacheStats(BaseModel):
    """Estadísticas del caché."""

    total_entries: int = Field(..., description="Número total de entradas")
    max_size: int = Field(..., description="Tamaño máximo del caché")
    domains: Dict[str, int] = Field(..., description="Número de entradas por dominio")
    strategies: Dict[str, int] = Field(
        ..., description="Número de entradas por estrategia"
    )


class DomainRuleRequest(BaseModel):
    """Solicitud para registrar una regla de dominio."""

    domain: str = Field(..., description="Nombre del dominio")
    similarity_threshold: float = Field(
        default=0.9, description="Umbral de similitud para búsquedas semánticas"
    )
    default_ttl: Optional[int] = Field(
        default=None, description="TTL por defecto para este dominio"
    )


class CacheEntryRequest(BaseModel):
    """Solicitud para cachear un valor."""

    prompt: str = Field(..., description="Prompt a cachear")
    value: Any = Field(..., description="Valor a almacenar")
    domain: str = Field(..., description="Dominio del prompt")
    ttl: Optional[int] = Field(default=None, description="Tiempo de vida en segundos")
    strategy: CacheStrategy = Field(
        default=CacheStrategy.EXACT_MATCH, description="Estrategia de caché"
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None, description="Parámetros adicionales"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Metadatos adicionales"
    )


class CacheQueryRequest(BaseModel):
    """Solicitud para consultar el caché."""

    prompt: str = Field(..., description="Prompt a buscar")
    domain: str = Field(..., description="Dominio del prompt")
    strategy: CacheStrategy = Field(
        default=CacheStrategy.EXACT_MATCH, description="Estrategia de caché"
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None, description="Parámetros adicionales"
    )


class CacheQueryResponse(BaseModel):
    """Respuesta a una consulta de caché."""

    found: bool = Field(..., description="Si se encontró el valor en caché")
    value: Optional[Any] = Field(default=None, description="Valor encontrado")


@router.get("/stats", response_model=CacheStats)
async def get_cache_stats(user_id: str = Depends(get_current_user)):
    """
    Obtiene estadísticas del sistema de caché.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Estadísticas del caché
    """
    try:
        stats = domain_cache.get_stats()
        return CacheStats(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener estadísticas: {str(e)}"
        )


@router.post("/clear", response_model=Dict[str, Any])
async def clear_cache(
    domain: Optional[str] = Query(
        default=None, description="Dominio a limpiar (None = todos)"
    ),
    user_id: str = Depends(get_current_user),
):
    """
    Limpia el caché.

    Args:
        domain: Dominio a limpiar (None = todos)
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    try:
        removed_count = domain_cache.clear(domain)
        return {
            "success": True,
            "removed_count": removed_count,
            "domain": domain or "all",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al limpiar caché: {str(e)}")


@router.post("/cleanup", response_model=Dict[str, Any])
async def cleanup_cache(user_id: str = Depends(get_current_user)):
    """
    Elimina entradas expiradas del caché.

    Args:
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    try:
        removed_count = await domain_cache.cleanup()
        return {"success": True, "removed_count": removed_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al limpiar caché: {str(e)}")


@router.post("/domain-rule", response_model=Dict[str, Any])
async def register_domain_rule(
    rule: DomainRuleRequest, user_id: str = Depends(get_current_user)
):
    """
    Registra una regla para un dominio específico.

    Args:
        rule: Regla a registrar
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    try:
        # Nota: No podemos registrar funciones personalizadas a través de la API
        domain_cache.register_domain_rule(
            domain=rule.domain,
            similarity_threshold=rule.similarity_threshold,
            default_ttl=rule.default_ttl,
        )

        return {
            "success": True,
            "domain": rule.domain,
            "message": f"Regla registrada para dominio {rule.domain}",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al registrar regla: {str(e)}"
        )


@router.post("/set", response_model=Dict[str, Any])
async def set_cache_entry(
    entry: CacheEntryRequest, user_id: str = Depends(get_current_user)
):
    """
    Establece un valor en el caché.

    Args:
        entry: Entrada a cachear
        user_id: ID del usuario autenticado

    Returns:
        Resultado de la operación
    """
    try:
        await domain_cache.set(
            prompt=entry.prompt,
            value=entry.value,
            domain=entry.domain,
            ttl=entry.ttl,
            strategy=entry.strategy,
            params=entry.params,
            metadata=entry.metadata,
        )

        return {
            "success": True,
            "domain": entry.domain,
            "strategy": entry.strategy,
            "message": "Valor cacheado correctamente",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cachear valor: {str(e)}")


@router.post("/get", response_model=CacheQueryResponse)
async def get_cache_entry(
    query: CacheQueryRequest, user_id: str = Depends(get_current_user)
):
    """
    Obtiene un valor del caché.

    Args:
        query: Consulta de caché
        user_id: ID del usuario autenticado

    Returns:
        Valor encontrado o None
    """
    try:
        value = await domain_cache.get(
            prompt=query.prompt,
            domain=query.domain,
            strategy=query.strategy,
            params=query.params,
        )

        return CacheQueryResponse(found=value is not None, value=value)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al consultar caché: {str(e)}"
        )

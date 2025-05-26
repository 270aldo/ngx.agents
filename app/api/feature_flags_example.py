"""
Ejemplo de integración de Feature Flags en endpoints de la API.

Este módulo muestra cómo integrar el sistema de Feature Flags
en los endpoints de la API para habilitar/deshabilitar características
de forma controlada.
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any, Optional

from infrastructure.feature_flags import get_feature_flag_service
from infrastructure.adapters import get_telemetry_adapter

# Crear router
router = APIRouter(prefix="/api/v1", tags=["feature-flags"])

# Obtener adaptador de telemetría
telemetry = get_telemetry_adapter()


@router.get("/feature-flags")
async def list_feature_flags(request: Request) -> Dict[str, Any]:
    """
    Lista todos los feature flags configurados.

    Returns:
        Dict[str, Any]: Lista de feature flags con su configuración.
    """
    span = telemetry.start_span("api.list_feature_flags")

    try:
        # Obtener servicio de feature flags
        feature_flags = get_feature_flag_service()

        # Obtener lista de flags
        flags = await feature_flags.list_flags()

        return {"flags": flags}
    except Exception as e:
        telemetry.record_exception(span, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


@router.get("/feature-flags/{flag_name}")
async def get_feature_flag(flag_name: str, request: Request) -> Dict[str, Any]:
    """
    Obtiene la configuración de un feature flag.

    Args:
        flag_name: Nombre del feature flag.

    Returns:
        Dict[str, Any]: Configuración del feature flag.
    """
    span = telemetry.start_span("api.get_feature_flag", {"flag_name": flag_name})

    try:
        # Obtener servicio de feature flags
        feature_flags = get_feature_flag_service()

        # Obtener flag
        enabled, metadata = await feature_flags.store.get_flag(flag_name)

        # Obtener porcentaje de rollout
        rollout_percentage = await feature_flags.store.get_rollout_percentage(flag_name)

        return {
            "name": flag_name,
            "enabled": enabled,
            "rollout_percentage": rollout_percentage,
            "metadata": metadata,
        }
    except Exception as e:
        telemetry.record_exception(span, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


@router.post("/feature-flags/{flag_name}")
async def update_feature_flag(
    flag_name: str,
    request: Request,
    enabled: Optional[bool] = None,
    rollout_percentage: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Actualiza la configuración de un feature flag.

    Args:
        flag_name: Nombre del feature flag.
        enabled: Estado del feature flag (True=habilitado, False=deshabilitado).
        rollout_percentage: Porcentaje de rollout (0-100).
        metadata: Metadatos adicionales para el feature flag.

    Returns:
        Dict[str, Any]: Resultado de la operación.
    """
    span = telemetry.start_span("api.update_feature_flag", {"flag_name": flag_name})

    try:
        # Obtener servicio de feature flags
        feature_flags = get_feature_flag_service()

        # Actualizar estado global si se proporciona
        if enabled is not None:
            await feature_flags.set_enabled(flag_name, enabled, metadata)

        # Actualizar porcentaje de rollout si se proporciona
        if rollout_percentage is not None:
            await feature_flags.set_rollout_percentage(flag_name, rollout_percentage)

        return {
            "status": "success",
            "flag_name": flag_name,
            "updated": {
                "enabled": enabled is not None,
                "rollout_percentage": rollout_percentage is not None,
                "metadata": metadata is not None,
            },
        }
    except Exception as e:
        telemetry.record_exception(span, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


# Ejemplo de integración en un endpoint existente
@router.get("/advanced-processing")
async def advanced_processing(request: Request) -> Dict[str, Any]:
    """
    Endpoint que utiliza feature flags para habilitar/deshabilitar
    procesamiento avanzado.

    Returns:
        Dict[str, Any]: Resultado del procesamiento.
    """
    span = telemetry.start_span("api.advanced_processing")

    try:
        # Obtener servicio de feature flags
        feature_flags = get_feature_flag_service()

        # Obtener ID de usuario de la solicitud
        user_id = request.headers.get("X-User-ID")

        # Verificar si la característica está habilitada
        advanced_enabled = await feature_flags.is_enabled(
            "advanced_processing", user_id=user_id, default=False
        )

        # Registrar evento de telemetría
        telemetry.add_span_event(
            span,
            "feature_flag_check",
            {
                "flag_name": "advanced_processing",
                "enabled": advanced_enabled,
                "user_id": user_id,
            },
        )

        if advanced_enabled:
            # Implementación avanzada
            result = await _process_advanced(request)
        else:
            # Implementación estándar
            result = await _process_standard(request)

        return result
    except Exception as e:
        telemetry.record_exception(span, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


async def _process_standard(request: Request) -> Dict[str, Any]:
    """
    Implementación estándar del procesamiento.

    Args:
        request: Solicitud HTTP.

    Returns:
        Dict[str, Any]: Resultado del procesamiento.
    """
    # Simulación de procesamiento estándar
    return {
        "processing_type": "standard",
        "result": "Procesamiento estándar completado",
    }


async def _process_advanced(request: Request) -> Dict[str, Any]:
    """
    Implementación avanzada del procesamiento.

    Args:
        request: Solicitud HTTP.

    Returns:
        Dict[str, Any]: Resultado del procesamiento.
    """
    # Simulación de procesamiento avanzado
    return {
        "processing_type": "advanced",
        "result": "Procesamiento avanzado completado",
        "additional_data": {
            "optimization_level": "high",
            "enhanced_features": ["feature1", "feature2"],
        },
    }

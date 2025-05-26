"""
Router de health checks para FastAPI.

Este módulo proporciona un router de FastAPI para exponer endpoints de health check
que serán utilizados por Kubernetes y otros sistemas de monitoreo.
"""

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Local imports
from infrastructure.health import health_check

# Crear router
health_router = APIRouter(tags=["Health"])


@health_router.get("/health", summary="Verificar estado general de la aplicación")
async def health():
    """
    Endpoint para verificar el estado general de la aplicación.

    Este endpoint combina los checks de liveness y readiness para proporcionar
    una visión general del estado de la aplicación.

    Returns:
        JSONResponse: Estado de la aplicación y detalles.
    """
    is_alive, liveness_details = await health_check.check_liveness()
    is_ready, readiness_details = await health_check.check_readiness()

    status_code = status.HTTP_200_OK
    if not is_alive or not is_ready:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "UP" if (is_alive and is_ready) else "DOWN",
            "liveness": liveness_details,
            "readiness": readiness_details,
        },
    )


@health_router.get("/health/liveness", summary="Verificar si la aplicación está viva")
async def liveness():
    """
    Endpoint para verificar si la aplicación está viva.

    Este endpoint verifica si la aplicación está en ejecución y responde
    a solicitudes básicas. No verifica dependencias externas.

    Returns:
        JSONResponse: Estado de la aplicación y detalles.
    """
    is_alive, details = await health_check.check_liveness()

    status_code = (
        status.HTTP_200_OK if is_alive else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(status_code=status_code, content=details)


@health_router.get(
    "/health/readiness",
    summary="Verificar si la aplicación está lista para recibir tráfico",
)
async def readiness():
    """
    Endpoint para verificar si la aplicación está lista para recibir tráfico.

    Este endpoint verifica si la aplicación y sus dependencias críticas
    están listas para procesar solicitudes.

    Returns:
        JSONResponse: Estado de la aplicación y detalles.
    """
    is_ready, details = await health_check.check_readiness()

    status_code = (
        status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(status_code=status_code, content=details)


@health_router.get(
    "/health/startup",
    summary="Verificar si la aplicación se ha inicializado correctamente",
)
async def startup():
    """
    Endpoint para verificar si la aplicación se ha inicializado correctamente.

    Este endpoint verifica si la aplicación ha completado su inicialización
    y está lista para recibir tráfico. Se utiliza durante el inicio de la aplicación.

    Returns:
        JSONResponse: Estado de la aplicación y detalles.
    """
    is_started, details = await health_check.check_startup()

    status_code = (
        status.HTTP_200_OK if is_started else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(status_code=status_code, content=details)


@health_router.get(
    "/health/report", summary="Obtener informe completo del estado de la aplicación"
)
async def report():
    """
    Endpoint para obtener un informe completo del estado de la aplicación.

    Este endpoint recopila información detallada sobre el estado de la aplicación,
    incluyendo métricas, configuración y estado de las dependencias.

    Returns:
        JSONResponse: Informe completo del estado de la aplicación.
    """
    is_alive, liveness_details = await health_check.check_liveness()
    is_ready, readiness_details = await health_check.check_readiness()

    report = health_check.get_full_health_report()
    report.update(
        {
            "status": "UP" if (is_alive and is_ready) else "DOWN",
            "liveness": liveness_details,
            "readiness": readiness_details,
        }
    )

    return JSONResponse(content=report)


@health_router.get("/metrics", summary="Obtener métricas de Prometheus")
async def metrics():
    """
    Endpoint para obtener métricas en formato Prometheus.

    Este endpoint expone métricas en formato Prometheus para ser consumidas
    por sistemas de monitoreo como Prometheus.

    Returns:
        Response: Métricas en formato Prometheus.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def setup_health_router(app, prefix="/api/v1"):
    """
    Configura el router de health checks en una aplicación FastAPI.

    Args:
        app: La aplicación FastAPI.
        prefix: Prefijo para las rutas.
    """
    app.include_router(health_router, prefix=prefix)

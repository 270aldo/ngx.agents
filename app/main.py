"""API principal de NGX Agents.

Este módulo implementa un servidor FastAPI que proporciona endpoints
para interactuar con los agentes NGX y gestionar la autenticación
mediante JWT.
"""

import logging
from typing import Dict, Any, List
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from core.settings import settings
from core.logging_config import configure_logging
from core.telemetry import initialize_telemetry, instrument_fastapi, get_tracer, shutdown_telemetry
from core.auth import get_current_user
from app.routers import auth, agents, chat, a2a
from clients.supabase_client import SupabaseClient
from app.middleware.telemetry import setup_telemetry_middleware

# Configurar logging y telemetría
logger = configure_logging(__name__)
initialize_telemetry()

# Crear la aplicación FastAPI
app = FastAPI(
    title="NGX Agents API",
    description="API para interactuar con los agentes NGX",
    version="1.0.0",
    docs_url=None,  # Desactivar /docs por defecto
    redoc_url=None  # Desactivar /redoc por defecto
)

# Instrumentar FastAPI con OpenTelemetry
instrument_fastapi(app)

# Configurar middlewares
setup_telemetry_middleware(app)  # Telemetry debe ser el primer middleware para capturar todo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, limitar a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(chat.router)
app.include_router(a2a.router)

# Incluir health check router
from infrastructure.health_router import setup_health_router
setup_health_router(app, prefix="/api/v1")


# Obtener tracer para la aplicación principal
tracer = get_tracer("ngx_agents.api.main")

# Eventos de inicio y apagado de la aplicación
@app.on_event("startup")
async def startup_event():
    """Tareas a ejecutar al iniciar la aplicación."""
    with tracer.start_as_current_span("app_startup"):
        try:
            # Configurar mensaje de inicio
            logger.info(
                f"Iniciando la aplicación NGX Agents v{settings.APP_VERSION} en entorno {settings.ENVIRONMENT}",
                extra={
                    "environment": settings.ENVIRONMENT,
                    "version": settings.APP_VERSION
                }
            )
            
            # Inicializar clientes y servicios esenciales
            logger.info("Inicializando servicios y clientes...")
            
            # Inicializar cliente de Supabase
            supabase_client = SupabaseClient.get_instance()
            await supabase_client.initialize()
            logger.info("Cliente Supabase inicializado correctamente")
            
            # Registrar dependencias para health checks
            from infrastructure.health import health_check
            health_check.register_dependency("supabase", health_check.check_supabase, critical=True)
            health_check.register_dependency("vertex_ai", health_check.check_vertex_ai, critical=True)
            
            logger.info("Aplicación NGX Agents iniciada correctamente")
            
        except ValueError as e:
            logger.error(f"Error al inicializar servicios: {e}")
            # Considerar si la app debe fallar al iniciar o continuar con funcionalidad limitada
            # raise RuntimeError(f"No se pudo inicializar servicios: {e}")
            
        except Exception as e:
            logger.error(f"Error inesperado durante la inicialización: {e}", exc_info=True)
            # raise RuntimeError(f"Error inesperado durante la inicialización: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Tareas a ejecutar al apagar la aplicación."""
    logger.info("Cerrando la aplicación NGX Agents...")
    
    try:
        # Cerrar telemetría
        shutdown_telemetry()
        
        # Cerrar conexiones a servicios externos
        logger.info("Cerrando conexiones a servicios externos...")
        # TODO: Implementar cierre de conexiones a servicios externos
        
        logger.info("Aplicación NGX Agents cerrada correctamente")
    except Exception as e:
        logger.error(f"Error durante el apagado de la aplicación: {e}", exc_info=True)


# Nota: Los endpoints /health y /metrics ahora son manejados por el health_router


# Endpoint para la documentación (protegido con JWT)
@app.get("/docs", tags=["documentación"])
async def get_documentation(
    user_id: str = Depends(get_current_user)
) -> Any:
    """
    Muestra la documentación de la API (Swagger UI).
    
    Args:
        user_id: ID del usuario autenticado
        
    Returns:
        Página HTML con Swagger UI
    """
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Documentación",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


# Endpoint para el esquema OpenAPI (protegido con JWT)
@app.get("/openapi.json", tags=["documentación"])
async def get_openapi_schema(
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Devuelve el esquema OpenAPI de la API.
    
    Args:
        user_id: ID del usuario autenticado
        
    Returns:
        Esquema OpenAPI
    """
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


# Manejador de excepciones personalizado
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Manejador global de excepciones.
    
    Args:
        request: Solicitud HTTP
        exc: Excepción capturada
        
    Returns:
        Respuesta JSON con el error
    """
    import asyncio
    from core.telemetry import record_exception
    
    # Obtener información de la solicitud
    request_id = request.headers.get("X-Request-ID", "unknown")
    endpoint = request.url.path
    method = request.method
    
    # Registrar excepción en el span actual
    record_exception(exc, {
        "request_id": request_id,
        "path": endpoint,
        "method": method,
        "error_type": type(exc).__name__
    })
    
    # Registrar error con contexto mejorado
    logger.error(
        f"Error no controlado: {exc}",
        extra={
            "request_id": request_id,
            "path": endpoint,
            "method": method,
            "error_type": type(exc).__name__,
            "client_host": request.client.host if request.client else "unknown"
        },
        exc_info=True
    )
    
    # Si es un error crítico y estamos en producción, enviar alerta
    if (settings.ENVIRONMENT == "production" and 
        not isinstance(exc, HTTPException)):
        
        # Crear tarea para enviar alerta sin bloquear la respuesta
        asyncio.create_task(_send_error_alert(
            error_message=str(exc),
            error_type=type(exc).__name__,
            endpoint=endpoint,
            request_id=request_id
        ))
    
    # Si es un error de HTTP conocido, reutilizamos su código de estado
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "type": type(exc).__name__
            }
        )
    
    # Error interno del servidor
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Error interno del servidor",
            "type": type(exc).__name__,
            "request_id": request_id  # Incluir request_id para depuración
        }
    )

async def _send_error_alert(
    error_message: str,
    error_type: str, 
    endpoint: str,
    request_id: str
) -> None:
    """
    Envía una alerta por un error no controlado.
    
    Args:
        error_message: Mensaje de error
        error_type: Tipo de error
        endpoint: Endpoint donde ocurrió el error
        request_id: ID de la solicitud
    """
    try:
        from tools.pagerduty_tools import send_alert
        
        # Detalles del error
        details = (
            f"Error no controlado en {endpoint}: {error_message}. "
            f"Tipo: {error_type}. Request ID: {request_id}"
        )
        
        # Enviar alerta
        await send_alert(
            summary=f"Error en NGX Agents API: {error_type}",
            severity="critical",
            source="api",
            component="api",
            details=details
        )
    except Exception as e:
        # No queremos que un error al enviar la alerta cause más problemas
        logger.error(f"Error al enviar alerta de error: {e}", exc_info=True)


# Punto de entrada para ejecutar la aplicación
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

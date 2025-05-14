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
from app.routers import auth, agents, chat, a2a, budget, prompt_analyzer, domain_cache, async_processor, batch_processor, request_prioritizer, circuit_breaker, degraded_mode, chaos_testing
from clients.supabase_client import SupabaseClient
from app.middleware.telemetry import setup_telemetry_middleware

# Configurar logging
logger = configure_logging(__name__)

# Inicializar telemetría solo si está habilitada
if settings.telemetry_enabled:
    logger.info("Inicializando telemetría...")
    initialize_telemetry()
    logger.info("Telemetría inicializada correctamente")
else:
    logger.info("Telemetría deshabilitada. No se inicializará.")

# Crear la aplicación FastAPI
app = FastAPI(
    title="NGX Agents API",
    description="API para interactuar con los agentes NGX",
    version="1.0.0",
    docs_url=None,  # Desactivar /docs por defecto
    redoc_url=None  # Desactivar /redoc por defecto
)

# Instrumentar FastAPI con OpenTelemetry y configurar middleware de telemetría solo si está habilitada
if settings.telemetry_enabled:
    instrument_fastapi(app)
    logger.info("Aplicación FastAPI instrumentada con OpenTelemetry")

# Configurar middlewares
setup_telemetry_middleware(app)  # Esta función ya verifica si la telemetría está habilitada
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
app.include_router(budget.router)
app.include_router(prompt_analyzer.router)
app.include_router(domain_cache.router)
app.include_router(async_processor.router)
app.include_router(batch_processor.router)
app.include_router(request_prioritizer.router)
app.include_router(circuit_breaker.router)
app.include_router(degraded_mode.router)
app.include_router(chaos_testing.router)

# Incluir health check router
from infrastructure.health_router import setup_health_router
setup_health_router(app, prefix="/api/v1")

# Incluir manejador de alertas
from app.handlers.alert_handler import setup_alert_handler
setup_alert_handler(app)


# Obtener tracer para la aplicación principal
tracer = get_tracer("ngx_agents.api.main")

# Eventos de inicio y apagado de la aplicación
@app.on_event("startup")
async def startup_event():
    """Tareas a ejecutar al iniciar la aplicación."""
    # Usar span solo si la telemetría está habilitada
    if settings.telemetry_enabled and tracer:
        context_manager = tracer.start_as_current_span("app_startup")
    else:
        # Usar un context manager nulo si la telemetría está deshabilitada
        from contextlib import nullcontext
        context_manager = nullcontext()
        
    with context_manager:
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
            
            # Inicializar sistema de presupuestos si está habilitado
            if settings.enable_budgets:
                from core.budget import budget_manager
                logger.info("Sistema de presupuestos inicializado correctamente")
                
            # Inicializar analizador de prompts
            from core.prompt_analyzer import prompt_analyzer
            logger.info("Analizador de prompts inicializado correctamente")
            
            # Inicializar sistema de caché por dominio
            from core.domain_cache import domain_cache
            logger.info("Sistema de caché por dominio inicializado correctamente")
            
            # Inicializar procesador asíncrono
            from core.async_processor import async_processor
            asyncio.create_task(async_processor.start())
            logger.info("Procesador asíncrono iniciado correctamente")
            
            # Inicializar procesador por lotes
            from core.batch_processor import batch_processor
            logger.info("Procesador por lotes inicializado correctamente")
            
            # Inicializar sistema de priorización de solicitudes
            from core.request_prioritizer import request_prioritizer
            asyncio.create_task(request_prioritizer.start())
            logger.info("Sistema de priorización de solicitudes iniciado correctamente")
            
            # Inicializar sistema de modos degradados
            from core.degraded_mode import degraded_mode_manager
            asyncio.create_task(degraded_mode_manager.start_monitoring())
            logger.info("Sistema de modos degradados iniciado correctamente")
            
            # Registrar dependencias para health checks
            from infrastructure.health import health_check
            health_check.register_dependency("supabase", health_check.check_supabase, critical=True)
            health_check.register_dependency("vertex_ai", health_check.check_vertex_ai, critical=True)
            
            # Inicializar sistema de runbooks
            from tools.runbooks import RunbookExecutor
            runbook_executor = RunbookExecutor()
            logger.info("Sistema de runbooks inicializado correctamente")
            
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
        # Cerrar telemetría solo si está habilitada
        if settings.telemetry_enabled:
            shutdown_telemetry()
            logger.info("Telemetría cerrada correctamente")
            
        # Detener procesador asíncrono
        try:
            from core.async_processor import async_processor
            await async_processor.stop()
            logger.info("Procesador asíncrono detenido correctamente")
        except Exception as e:
            logger.error(f"Error al detener procesador asíncrono: {e}")
        
        # Detener sistema de priorización de solicitudes
        try:
            from core.request_prioritizer import request_prioritizer
            await request_prioritizer.stop()
            logger.info("Sistema de priorización de solicitudes detenido correctamente")
        except Exception as e:
            logger.error(f"Error al detener sistema de priorización de solicitudes: {e}")
        
        # Detener sistema de modos degradados
        try:
            from core.degraded_mode import degraded_mode_manager
            await degraded_mode_manager.stop_monitoring()
            logger.info("Sistema de modos degradados detenido correctamente")
        except Exception as e:
            logger.error(f"Error al detener sistema de modos degradados: {e}")
        
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
    
    # Registrar excepción en el span actual solo si la telemetría está habilitada
    if settings.telemetry_enabled:
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
        from tools.runbooks import RunbookExecutor
        
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
        
        # Ejecutar runbook de respuesta a errores si existe
        try:
            runbook_executor = RunbookExecutor()
            import time
            await runbook_executor.execute_runbook("error_response", {
                "error_message": error_message,
                "error_type": error_type,
                "endpoint": endpoint,
                "request_id": request_id,
                "timestamp": time.time()
            })
        except Exception as runbook_error:
            logger.error(f"Error al ejecutar runbook de respuesta a errores: {runbook_error}", exc_info=True)
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

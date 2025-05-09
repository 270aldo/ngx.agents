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
from core.logging_config import setup_logging, get_logger
from core.auth import get_current_user
from app.routers import auth, agents, chat
from clients.supabase_client import supabase_client

# Configurar logger
setup_logging()
logger = get_logger(__name__)

# Crear la aplicación FastAPI
app = FastAPI(
    title="NGX Agents API",
    description="API para interactuar con los agentes NGX",
    version="1.0.0",
    docs_url=None,  # Desactivar /docs por defecto
    redoc_url=None  # Desactivar /redoc por defecto
)

# Configurar CORS
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


# Eventos de inicio y apagado de la aplicación
@app.on_event("startup")
async def startup_event():
    """Tareas a ejecutar al iniciar la aplicación."""
    logger.info("Iniciando la aplicación NGX Agents...")
    try:
        await supabase_client.initialize()
        logger.info("Cliente Supabase inicializado correctamente.")
    except ValueError as e:
        logger.error(f"Error al inicializar Supabase: {e}")
        # Podrías decidir si la app debe fallar al iniciar o continuar con funcionalidad limitada
        # raise RuntimeError(f"No se pudo inicializar Supabase: {e}")
    except Exception as e:
        logger.error(f"Error inesperado durante la inicialización de Supabase: {e}", exc_info=True)
        # raise RuntimeError(f"Error inesperado al inicializar Supabase: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Tareas a ejecutar al apagar la aplicación."""
    logger.info("Cerrando la aplicación NGX Agents...")
    # Aquí podrías añadir limpieza si es necesario, por ejemplo, cerrar conexiones


# Endpoint para verificar el estado de la API
@app.get("/health", tags=["sistema"])
async def health_check() -> Dict[str, str]:
    """
    Verifica el estado de la API.
    
    Returns:
        Diccionario con el estado de la API
    """
    return {"status": "ok", "version": app.version}


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
    logger.error(f"Error no controlado: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Error interno del servidor",
            "type": type(exc).__name__
        }
    )


# Punto de entrada para ejecutar la aplicación
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

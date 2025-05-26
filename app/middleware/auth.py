"""
Middleware de autenticación para la API de NGX Agents.

Este módulo proporciona funciones y clases para la autenticación
de solicitudes a la API mediante API keys.
"""

import logging
from typing import Optional, List, Callable
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from clients.supabase_client import SupabaseClient

# Configurar logging
logger = logging.getLogger(__name__)

# Definir el esquema de seguridad para la API key en el header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(request: Request) -> str:
    """
    Extrae y valida la API key del header de la solicitud.

    Args:
        request: Solicitud HTTP

    Returns:
        str: API key validada

    Raises:
        HTTPException: Si la API key no es válida o no está presente
    """
    api_key = await api_key_header(request)

    if not api_key:
        logger.warning(f"Intento de acceso sin API key a {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key no proporcionada",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validar la API key con Supabase
    supabase_client = SupabaseClient()
    user = supabase_client.get_or_create_user_by_api_key(api_key)

    if not user or not user.get("id"):
        logger.warning(
            f"Intento de acceso con API key inválida a {request.url.path}: {api_key[:5]}..."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Almacenar el user_id en request.state para uso posterior
    request.state.user_id = user.get("id")

    return api_key


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware para verificar la API key en todas las solicitudes.

    Este middleware verifica la presencia de una API key válida en el header
    X-API-Key de todas las solicitudes, excepto las rutas excluidas.
    """

    def __init__(self, app, excluded_paths: Optional[List[str]] = None):
        """
        Inicializa el middleware.

        Args:
            app: Aplicación FastAPI
            excluded_paths: Lista de rutas que no requieren autenticación
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/.well-known/agent.json",
            "/health",
            "/static",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Procesa la solicitud y verifica la API key.

        Args:
            request: Solicitud HTTP
            call_next: Función para continuar con el procesamiento de la solicitud

        Returns:
            Response: Respuesta HTTP
        """
        # Verificar si la ruta está excluida
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        # Obtener la API key del header
        api_key = request.headers.get("X-API-Key")

        # Verificar la API key
        if not api_key:
            logger.warning(f"Solicitud sin API key a {path}")
            return Response(
                content='{"detail":"API key no proporcionada"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={
                    "WWW-Authenticate": "ApiKey",
                    "Content-Type": "application/json",
                },
            )

        # Validar la API key con Supabase
        supabase_client = SupabaseClient()
        user = supabase_client.get_or_create_user_by_api_key(api_key)

        if not user or not user.get("id"):
            logger.warning(
                f"Intento de acceso con API key inválida a {path}: {api_key[:5]}..."
            )
            return Response(
                content='{"detail":"API key inválida"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={
                    "WWW-Authenticate": "ApiKey",
                    "Content-Type": "application/json",
                },
            )

        # Almacenar el user_id en request.state para uso posterior
        request.state.user_id = user.get("id")

        # Continuar con el procesamiento de la solicitud
        return await call_next(request)

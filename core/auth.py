"""
Autenticación JWT para la API de NGX Agents.

Este módulo proporciona funciones para la autenticación mediante JWT (JSON Web Tokens)
y la protección de endpoints de la API.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from core.logging_config import get_logger
from clients.supabase_client import SupabaseClient
from gotrue.errors import AuthApiError as AuthException

# Configurar logger
logger = get_logger(__name__)

# Esquema OAuth2 para la autenticación
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    supabase_client: SupabaseClient = Depends(
        SupabaseClient
    ),  # Inyectar SupabaseClient
) -> str:  # Devolverá el user_id como string
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        logger.warning("get_current_user: No token provided.")
        raise credentials_exception

    try:
        user_response = await supabase_client.client.auth.get_user(token)

        if not user_response or not user_response.user or not user_response.user.id:
            logger.warning(
                "get_current_user: Token inválido o usuario no encontrado en Supabase."
            )
            raise credentials_exception

        logger.debug(
            f"get_current_user: Token validado para user_id: {user_response.user.id}"
        )
        return str(user_response.user.id)

    except AuthException as e:
        logger.warning(
            f"get_current_user: AuthException durante validación de token: {e.message}"
        )
        raise credentials_exception
    except Exception as e:
        logger.error(
            f"get_current_user: Error inesperado durante validación de token: {e}"
        )
        raise credentials_exception


async def get_optional_user(
    token: str = Depends(oauth2_scheme),
    supabase_client: SupabaseClient = Depends(
        SupabaseClient
    ),  # Inyectar SupabaseClient
) -> Optional[str]:  # Devolverá el user_id como string o None
    if not token:
        return None

    try:
        user_response = await supabase_client.client.auth.get_user(token)

        if user_response and user_response.user and user_response.user.id:
            logger.debug(
                f"get_optional_user: Token validado para user_id: {user_response.user.id}"
            )
            return str(user_response.user.id)
        else:
            # Si el token no es válido pero no lanza AuthException (poco probable),
            # o si la respuesta es inesperada.
            logger.warning(
                "get_optional_user: Token pareció ser procesado por Supabase pero no se obtuvo usuario."
            )
            return None

    except AuthException:
        # Token inválido (expirado, malformado, etc.)
        logger.debug(
            "get_optional_user: AuthException, token inválido. Retornando None."
        )
        return None
    except Exception as e:
        # Otros errores inesperados
        logger.error(
            f"get_optional_user: Error inesperado durante validación de token: {e}. Retornando None."
        )
        return None

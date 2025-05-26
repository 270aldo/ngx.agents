"""
Router de autenticación para la API de NGX Agents.

Este módulo proporciona endpoints para la autenticación de usuarios
mediante JWT (JSON Web Tokens).
"""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from gotrue.errors import AuthApiError as AuthException

from core.logging_config import get_logger
from app.schemas.auth import Token, UserCreate, User
from clients.supabase_client import SupabaseClient

# Configurar logger
logger = get_logger(__name__)

# Crear router
router = APIRouter(
    prefix="/auth",
    tags=["autenticación"],
    responses={401: {"description": "No autorizado"}},
)


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    supabase_client: SupabaseClient = Depends(lambda: SupabaseClient()),
) -> Dict[str, str]:
    try:
        # Autenticar usuario con Supabase
        session = await supabase_client.client.auth.sign_in_with_password(
            {"email": form_data.username, "password": form_data.password}
        )

        if not session or not session.session or not session.session.access_token:
            # Esto no debería ocurrir si sign_in_with_password no lanza una excepción
            # pero es una comprobación de seguridad adicional.
            logger.error(
                f"Respuesta inesperada de Supabase al intentar login para: {form_data.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error en el servidor durante la autenticación",
            )

        logger.info(f"Login exitoso para usuario: {form_data.username}")

        return {"access_token": session.session.access_token, "token_type": "bearer"}

    except AuthException as e:
        logger.warning(f"Fallo de autenticación para {form_data.username}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message or "Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except Exception as e:
        logger.error(f"Error inesperado en login para {form_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en el servidor",
        )


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    supabase_client: SupabaseClient = Depends(lambda: SupabaseClient()),
) -> User:
    """
    Registra un nuevo usuario en Supabase.

    Args:
        user_data: Datos del usuario para crear (email y contraseña)
        supabase_client: Cliente de Supabase

    Returns:
        Los datos del usuario creado (sin incluir la sesión completa)

    Raises:
        HTTPException: Si el usuario ya existe o hay un error en Supabase.
    """
    try:
        response = await supabase_client.client.auth.sign_up(
            {"email": user_data.email, "password": user_data.password}
        )

        if not response or not response.user:
            # Esto podría ocurrir si Supabase tiene deshabilitado el auto-confirm y requiere
            # confirmación por email, pero sign_up no debería fallar silenciosamente.
            # O si hay algún otro problema inesperado.
            logger.error(
                f"Respuesta inesperada de Supabase durante el registro para: {user_data.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error en el servidor durante el registro",
            )

        # El objeto response.user es de tipo supabase.lib.auth.user.User,
        # que es compatible con el schema Pydantic User si los campos coinciden.
        # Asegurémonos de que la respuesta sea compatible con nuestro schema User.
        # Los campos esperados en response.user son id, email, created_at, etc.
        # Nuestro schema User espera id, email, is_active (que podemos asumir True para un nuevo usuario)
        logger.info(
            f"Usuario registrado exitosamente: {user_data.email}, ID: {response.user.id}"
        )

        # Adaptamos la respuesta de Supabase a nuestro modelo User Pydantic
        # El objeto User de Supabase tiene más campos, pero Pydantic solo tomará los que coincidan.
        # Si `response.user` no tiene `is_active`, Pydantic usará el default True.
        return User.model_validate(
            response.user
        )  # Usar model_validate para Pydantic v2

    except AuthException as e:
        logger.warning(f"Error de registro para {user_data.email}: {e.message}")
        # Supabase puede devolver errores específicos como "User already registered"
        # El código de estado 400 (Bad Request) o 422 (Unprocessable Entity) podría ser más apropiado
        # que 401 para errores de registro, dependiendo del mensaje de error.
        status_code = status.HTTP_400_BAD_REQUEST
        if "User already registered" in e.message:
            status_code = status.HTTP_409_CONFLICT  # Conflict

        raise HTTPException(
            status_code=status_code, detail=e.message or "Error durante el registro"
        )
    except Exception as e:
        logger.error(
            f"Error inesperado durante el registro para {user_data.email}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en el servidor",
        )

"""
Router de autenticación para la API de NGX Agents.

Este módulo proporciona endpoints para la autenticación de usuarios
mediante JWT (JSON Web Tokens).
"""
from datetime import timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from core.settings import settings
from core.auth import create_access_token
from core.logging_config import get_logger
from app.schemas.auth import Token
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
    supabase_client: SupabaseClient = Depends(lambda: SupabaseClient())
) -> Dict[str, str]:
    """
    Obtiene un token JWT para un usuario autenticado.
    
    Args:
        form_data: Formulario con email y contraseña
        supabase_client: Cliente de Supabase
        
    Returns:
        Token JWT
        
    Raises:
        HTTPException: Si las credenciales son inválidas
    """
    try:
        # Autenticar usuario con Supabase
        # Nota: Esto es una simplificación, en un entorno real deberías
        # usar la autenticación de Supabase directamente
        user = await supabase_client.execute_sql(
            sql="""
            SELECT id, email
            FROM auth.users
            WHERE email = $1
            """,
            params={"email": form_data.username}
        )
        
        if not user or len(user) == 0:
            logger.warning(f"Intento de login con email no registrado: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # En un entorno real, verificarías la contraseña aquí
        # Por ahora, simplemente generamos un token
        
        # Crear token JWT
        access_token = create_access_token(
            user_id=user[0]["id"],
            expires_delta=timedelta(minutes=settings.jwt_expiration_minutes)
        )
        
        logger.info(f"Login exitoso para usuario: {form_data.username}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en el servidor"
        )

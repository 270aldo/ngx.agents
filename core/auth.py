"""
Autenticación JWT para la API de NGX Agents.

Este módulo proporciona funciones para la autenticación mediante JWT (JSON Web Tokens)
y la protección de endpoints de la API.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from core.settings import settings
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)

# Esquema OAuth2 para la autenticación
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token",
    auto_error=False
)

# Modelo para los datos del token
class TokenData(BaseModel):
    """Datos contenidos en el token JWT."""
    sub: str
    exp: Optional[datetime] = None


def create_access_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token JWT para un usuario.
    
    Args:
        user_id: ID del usuario
        expires_delta: Tiempo de expiración del token (opcional)
        
    Returns:
        Token JWT generado
    """
    # Tiempo de expiración por defecto
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expiration_minutes)
    
    # Datos a codificar en el token
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": user_id,
        "exp": expire
    }
    
    # Codificar el token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[str]:
    """
    Obtiene el ID del usuario actual a partir del token JWT.
    
    Args:
        token: Token JWT (obtenido automáticamente de la solicitud)
        
    Returns:
        ID del usuario o None si el token no es válido
        
    Raises:
        HTTPException: Si el token no es válido o ha expirado
    """
    if not token:
        logger.warning("Intento de acceso sin token JWT")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se ha proporcionado un token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decodificar el token
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Extraer el ID del usuario
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token JWT sin ID de usuario")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticación inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar la expiración
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            logger.warning(f"Token JWT expirado para el usuario {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticación expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Crear objeto con los datos del token
        token_data = TokenData(sub=user_id, exp=datetime.fromtimestamp(exp) if exp else None)
        
        return token_data.sub
        
    except JWTError as e:
        logger.warning(f"Error al decodificar token JWT: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """
    Obtiene el ID del usuario actual a partir del token JWT, sin lanzar excepciones.
    
    Esta función es útil para endpoints que pueden ser accedidos tanto por usuarios
    autenticados como por usuarios anónimos.
    
    Args:
        token: Token JWT (obtenido automáticamente de la solicitud)
        
    Returns:
        ID del usuario o None si el token no es válido o no se proporciona
    """
    if not token:
        return None
    
    try:
        # Decodificar el token
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Extraer el ID del usuario
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        # Verificar la expiración
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return None
        
        return user_id
        
    except JWTError:
        return None

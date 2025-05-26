"""
Esquemas de datos para autenticación en la API de NGX Agents.

Este módulo define los modelos Pydantic para la autenticación y gestión de usuarios.
"""

from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """Modelo para el token de acceso."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Datos contenidos en el token."""

    sub: str
    exp: Optional[int] = None


class UserBase(BaseModel):
    """Datos base de un usuario."""

    email: str


class UserCreate(UserBase):
    """Datos para crear un usuario."""

    password: str


class User(UserBase):
    """Datos de un usuario."""

    id: str
    is_active: bool = True

    class Config:
        """Configuración del modelo."""

        from_attributes = True

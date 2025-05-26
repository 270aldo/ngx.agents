"""
Configuración para pruebas unitarias.

Este módulo proporciona una configuración por defecto para pruebas
que no requiere variables de entorno ni archivos .env.
"""

from pydantic import AnyUrl, Field
from pydantic_settings import SettingsConfigDict

from core.settings import Settings


# Renombrar la clase para evitar que pytest la recolecte como una clase de prueba
# (pytest busca clases que comienzan con 'Test')
class MockTestSettings(Settings):
    """Configuración para pruebas unitarias.

    Esta clase no es una clase de prueba, sino una configuración para pruebas.
    El comentario 'pytest: collect-ignore' evita que pytest intente recolectarla.
    """

    # Sobreescribir configuración que requiere valores obligatorios
    supabase_url: AnyUrl = Field(
        default="http://localhost:54321", json_schema_extra={"env": "SUPABASE_URL"}
    )
    supabase_anon_key: str = Field(
        default="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
        json_schema_extra={"env": "SUPABASE_ANON_KEY"},
    )
    jwt_secret: str = Field(
        default="test_secret_key", json_schema_extra={"env": "JWT_SECRET"}
    )

    # Configuración adicional para pruebas
    testing: bool = True

    # Configuración del modelo usando SettingsConfigDict
    model_config = SettingsConfigDict(
        env_file=None, extra="ignore", case_sensitive=False
    )

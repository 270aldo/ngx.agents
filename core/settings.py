"""
Configuración de la aplicación NGX Agents.

Este módulo utiliza pydantic-settings para cargar y validar la configuración
desde variables de entorno.
"""
import os
from typing import Optional
from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación NGX Agents."""
    
    # Configuración del modelo
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
    
    # Configuración del servidor
    host: str = Field(default="0.0.0.0", json_schema_extra={"env": "HOST"})
    port: int = Field(default=8000, json_schema_extra={"env": "PORT"})
    debug: bool = Field(default=False, json_schema_extra={"env": "DEBUG"})
    
    # Configuración de Supabase
    supabase_url: AnyUrl = Field(..., json_schema_extra={"env": "SUPABASE_URL"})
    supabase_anon_key: str = Field(..., json_schema_extra={"env": "SUPABASE_ANON_KEY"})
    
    # Configuración de Gemini
    gemini_api_key: str = Field(default="", json_schema_extra={"env": "GEMINI_API_KEY"})
    
    # Configuración de A2A
    a2a_server_url: AnyUrl = Field(default="http://localhost:9000", json_schema_extra={"env": "A2A_SERVER_URL"})
    
    # Configuración de JWT (Eliminadas ya que Supabase maneja los tokens)
    # jwt_secret: str = Field(..., json_schema_extra={"env": "JWT_SECRET"})
    # jwt_algorithm: str = Field(default="HS256", json_schema_extra={"env": "JWT_ALGORITHM"})
    # jwt_expiration_minutes: int = Field(default=60, json_schema_extra={"env": "JWT_EXPIRATION_MINUTES"})
    
    # Configuración del entorno
    env: str = Field(default="dev", json_schema_extra={"env": "ENV"})
    
    # Configuración de logging
    log_level: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})

    # Configuraciones específicas para pruebas (cargadas desde .env.test)
    test_user_email: Optional[str] = Field(default=None, json_schema_extra={"env": "TEST_USER_EMAIL"})
    test_user_id: Optional[str] = Field(default=None, json_schema_extra={"env": "TEST_USER_ID"})
    valid_test_token: Optional[str] = Field(default=None, json_schema_extra={"env": "VALID_TEST_TOKEN"})


# Instancia global de la configuración
settings = Settings()

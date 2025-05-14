"""
Configuración de la aplicación NGX Agents.

Este módulo utiliza pydantic-settings para cargar y validar la configuración
desde variables de entorno.
"""
import os
from typing import Optional
from pydantic import AnyUrl, Field, field_validator
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
    supabase_url: Optional[AnyUrl] = Field(default=None, json_schema_extra={"env": "SUPABASE_URL"})
    supabase_anon_key: Optional[str] = Field(default=None, json_schema_extra={"env": "SUPABASE_ANON_KEY"})
    
    # Configuración de Gemini
    gemini_api_key: str = Field(default="", json_schema_extra={"env": "GEMINI_API_KEY"})
    
    # Configuración de A2A
    a2a_server_url: AnyUrl = Field(default="http://localhost:9000", json_schema_extra={"env": "A2A_SERVER_URL"})
    
    # Configuración de presupuestos
    enable_budgets: bool = Field(default=False, json_schema_extra={"env": "ENABLE_BUDGETS"})
    budget_config_path: Optional[str] = Field(default="config/budgets.json", json_schema_extra={"env": "BUDGET_CONFIG_PATH"})
    default_budget_action: str = Field(default="warn", json_schema_extra={"env": "DEFAULT_BUDGET_ACTION"})
    
    # Configuración de JWT (Eliminadas ya que Supabase maneja los tokens)
    # jwt_secret: str = Field(..., json_schema_extra={"env": "JWT_SECRET"})
    # jwt_algorithm: str = Field(default="HS256", json_schema_extra={"env": "JWT_ALGORITHM"})
    # jwt_expiration_minutes: int = Field(default=60, json_schema_extra={"env": "JWT_EXPIRATION_MINUTES"})
    
    # Configuración del entorno
    env: str = Field(default="dev", json_schema_extra={"env": "ENV"})
    
    # Configuración de logging
    log_level: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})
    
    # Configuración de telemetría
    telemetry_enabled: bool = Field(default=False, json_schema_extra={"env": "ENABLE_TELEMETRY"})
    gcp_project_id: Optional[str] = Field(default=None, json_schema_extra={"env": "GCP_PROJECT_ID"})
    
    # Configuración del entorno de la aplicación
    environment: str = Field(default="development", json_schema_extra={"env": "ENVIRONMENT"})
    app_version: str = Field(default="0.1.0", json_schema_extra={"env": "APP_VERSION"})
    
    @field_validator('telemetry_enabled')
    def validate_telemetry_enabled(cls, v, info):
        """Valida que la telemetría solo se habilite si GCP_PROJECT_ID está configurado."""
        if v and not info.data.get('gcp_project_id'):
            raise ValueError("No se puede habilitar la telemetría sin configurar GCP_PROJECT_ID")
        return v

    # Configuraciones específicas para pruebas (cargadas desde .env.test)
    test_user_email: Optional[str] = Field(default=None, json_schema_extra={"env": "TEST_USER_EMAIL"})
    test_user_id: Optional[str] = Field(default=None, json_schema_extra={"env": "TEST_USER_ID"})
    valid_test_token: Optional[str] = Field(default=None, json_schema_extra={"env": "VALID_TEST_TOKEN"})
    
    # Configuración de reintentos y backoff
    max_retries: int = Field(default=3, json_schema_extra={"env": "MAX_RETRIES"})
    retry_backoff: float = Field(default=1.0, json_schema_extra={"env": "RETRY_BACKOFF"})


# Instancia global de la configuración
settings = Settings()

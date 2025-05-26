"""
Esquemas de datos para agentes en la API de NGX Agents.

Este módulo define los modelos Pydantic para la interacción con agentes.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class AgentRunRequest(BaseModel):
    """Solicitud para ejecutar un agente."""

    input_text: str = Field(
        ...,
        description="Texto de entrada para el agente",
        min_length=1,
        max_length=10000,
    )
    session_id: Optional[str] = Field(
        None,
        description="ID de la sesión (opcional)",
        regex="^[a-zA-Z0-9_-]+$",
        max_length=128,
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para el agente"
    )

    @validator("input_text")
    def input_text_must_not_be_empty(cls, v):
        """Valida que el texto de entrada no esté vacío."""
        if not v or not v.strip():
            raise ValueError("El texto de entrada no puede estar vacío")
        return v.strip()


class AgentRunResponse(BaseModel):
    """Respuesta de la ejecución de un agente."""

    agent_id: str = Field(..., description="ID del agente que generó la respuesta")
    response: str = Field(..., description="Respuesta generada por el agente")
    session_id: str = Field(..., description="ID de la sesión")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Metadatos adicionales"
    )


class AgentInfo(BaseModel):
    """Información básica de un agente."""

    agent_id: str = Field(..., description="ID único del agente")
    name: str = Field(..., description="Nombre del agente")
    description: str = Field(..., description="Descripción del agente")
    capabilities: List[str] = Field(..., description="Capacidades del agente")


class AgentListResponse(BaseModel):
    """Respuesta con la lista de agentes disponibles."""

    agents: List[AgentInfo] = Field(..., description="Lista de agentes disponibles")

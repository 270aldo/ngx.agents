"""
Esquemas de datos para agentes en la API de NGX Agents.

Este módulo define los modelos Pydantic para la interacción con agentes.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """Solicitud para ejecutar un agente."""
    input_text: str = Field(..., description="Texto de entrada para el agente")
    session_id: Optional[str] = Field(None, description="ID de la sesión (opcional)")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para el agente")


class AgentRunResponse(BaseModel):
    """Respuesta de la ejecución de un agente."""
    agent_id: str = Field(..., description="ID del agente que generó la respuesta")
    response: str = Field(..., description="Respuesta generada por el agente")
    session_id: str = Field(..., description="ID de la sesión")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales")


class AgentInfo(BaseModel):
    """Información básica de un agente."""
    agent_id: str = Field(..., description="ID único del agente")
    name: str = Field(..., description="Nombre del agente")
    description: str = Field(..., description="Descripción del agente")
    capabilities: List[str] = Field(..., description="Capacidades del agente")


class AgentListResponse(BaseModel):
    """Respuesta con la lista de agentes disponibles."""
    agents: List[AgentInfo] = Field(..., description="Lista de agentes disponibles")

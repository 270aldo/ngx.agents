"""
Esquemas para el endpoint de chat.

Este módulo define los esquemas de datos para las solicitudes y respuestas
del endpoint de chat, que utiliza el Orchestrator para coordinar agentes.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Solicitud para el endpoint de chat."""
    
    text: str = Field(
        ..., 
        description="Texto de entrada del usuario",
        examples=["¿Puedes ayudarme con mi entrenamiento?"]
    )
    user_id: Optional[str] = Field(
        None, 
        description="ID del usuario (opcional)"
    )
    session_id: Optional[str] = Field(
        None, 
        description="ID de la sesión (opcional, se genera uno nuevo si no se proporciona)"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, 
        description="Contexto adicional para el procesamiento (opcional)"
    )


class AgentResponse(BaseModel):
    """Respuesta de un agente específico."""
    
    agent_id: str = Field(
        ..., 
        description="ID del agente que generó la respuesta"
    )
    agent_name: str = Field(
        ..., 
        description="Nombre del agente que generó la respuesta"
    )
    response: str = Field(
        ..., 
        description="Texto de respuesta del agente"
    )
    confidence: float = Field(
        1.0, 
        description="Nivel de confianza del agente en su respuesta (0-1)"
    )
    artifacts: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Artefactos generados por el agente (opcional)"
    )


class ChatResponse(BaseModel):
    """Respuesta del endpoint de chat."""
    
    response: str = Field(
        ..., 
        description="Texto de respuesta final (sintetizado por el Orchestrator)"
    )
    session_id: str = Field(
        ..., 
        description="ID de la sesión (generado o proporcionado)"
    )
    agents_used: List[str] = Field(
        ..., 
        description="Lista de IDs de agentes utilizados para generar la respuesta"
    )
    agent_responses: Optional[List[AgentResponse]] = Field(
        None, 
        description="Respuestas individuales de cada agente (opcional)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Metadatos adicionales sobre la respuesta (opcional)"
    )

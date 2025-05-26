"""
API para el analizador de prompts.

Este módulo proporciona endpoints para analizar y optimizar prompts
con el objetivo de reducir el número de tokens utilizados.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field

from core.prompt_analyzer import prompt_analyzer
from core.auth import get_current_user

# Crear router
router = APIRouter(
    prefix="/api/prompt-analyzer",
    tags=["prompt-analyzer"],
    responses={404: {"description": "No encontrado"}},
)


# Modelos de datos para la API
class PromptAnalysisRequest(BaseModel):
    """Solicitud para analizar un prompt."""

    prompt: str = Field(..., description="Texto del prompt a analizar")
    optimize: bool = Field(default=True, description="Si se debe optimizar el prompt")


class PromptIssue(BaseModel):
    """Problema encontrado en un prompt."""

    type: str = Field(..., description="Tipo de problema")
    description: str = Field(..., description="Descripción del problema")
    severity: str = Field(..., description="Severidad del problema (alta, media, baja)")
    matches: Optional[List[str]] = Field(
        default=None, description="Ejemplos de coincidencias encontradas"
    )


class PromptAnalysisResponse(BaseModel):
    """Respuesta con el análisis de un prompt."""

    original_length: int = Field(..., description="Longitud original en caracteres")
    word_count: int = Field(..., description="Número de palabras")
    estimated_tokens: int = Field(..., description="Número estimado de tokens")
    issues: List[PromptIssue] = Field(..., description="Problemas encontrados")
    optimized_prompt: Optional[str] = Field(
        default=None, description="Prompt optimizado"
    )
    optimized_tokens: Optional[int] = Field(
        default=None, description="Número estimado de tokens en el prompt optimizado"
    )
    token_reduction: int = Field(..., description="Reducción de tokens")
    percentage_reduction: float = Field(
        ..., description="Porcentaje de reducción de tokens"
    )


class ChatMessagesRequest(BaseModel):
    """Solicitud para optimizar mensajes de chat."""

    messages: List[Dict[str, str]] = Field(
        ...,
        description="Lista de mensajes en formato [{'role': 'user|model', 'content': 'texto'}]",
    )


class ChatMessagesResponse(BaseModel):
    """Respuesta con los mensajes de chat optimizados."""

    original_messages: List[Dict[str, str]] = Field(
        ..., description="Mensajes originales"
    )
    optimized_messages: List[Dict[str, str]] = Field(
        ..., description="Mensajes optimizados"
    )
    token_reduction: int = Field(..., description="Reducción total de tokens")
    percentage_reduction: float = Field(
        ..., description="Porcentaje de reducción de tokens"
    )


@router.post("/analyze", response_model=PromptAnalysisResponse)
async def analyze_prompt(
    request: PromptAnalysisRequest, user_id: str = Depends(get_current_user)
):
    """
    Analiza un prompt y proporciona métricas y sugerencias de optimización.

    Args:
        request: Solicitud con el prompt a analizar
        user_id: ID del usuario autenticado

    Returns:
        Análisis del prompt
    """
    try:
        analysis = prompt_analyzer.analyze_prompt(request.prompt)

        # Si no se solicita optimización, eliminar el prompt optimizado
        if not request.optimize:
            analysis["optimized_prompt"] = None
            analysis["optimized_tokens"] = None
            analysis["token_reduction"] = 0
            analysis["percentage_reduction"] = 0.0

        return PromptAnalysisResponse(**analysis)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al analizar prompt: {str(e)}"
        )


@router.post("/optimize-chat", response_model=ChatMessagesResponse)
async def optimize_chat_messages(
    request: ChatMessagesRequest, user_id: str = Depends(get_current_user)
):
    """
    Optimiza una lista de mensajes de chat para reducir tokens.

    Args:
        request: Solicitud con los mensajes a optimizar
        user_id: ID del usuario autenticado

    Returns:
        Mensajes optimizados
    """
    try:
        original_messages = request.messages
        optimized_messages = prompt_analyzer.optimize_chat_messages(original_messages)

        # Calcular reducción de tokens
        original_tokens = sum(
            prompt_analyzer._estimate_tokens(msg.get("content", ""))
            for msg in original_messages
        )
        optimized_tokens = sum(
            prompt_analyzer._estimate_tokens(msg.get("content", ""))
            for msg in optimized_messages
        )
        token_reduction = original_tokens - optimized_tokens
        percentage_reduction = (
            (token_reduction / original_tokens) * 100 if original_tokens > 0 else 0.0
        )

        return ChatMessagesResponse(
            original_messages=original_messages,
            optimized_messages=optimized_messages,
            token_reduction=token_reduction,
            percentage_reduction=percentage_reduction,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al optimizar mensajes: {str(e)}"
        )


@router.post("/optimize-json", response_model=Dict[str, Any])
async def optimize_json_prompt(
    json_obj: Dict[str, Any] = Body(..., description="Objeto JSON a optimizar"),
    user_id: str = Depends(get_current_user),
):
    """
    Optimiza un prompt en formato JSON para reducir tokens.

    Args:
        json_obj: Objeto JSON a optimizar
        user_id: ID del usuario autenticado

    Returns:
        Objeto JSON optimizado
    """
    try:
        optimized = prompt_analyzer.optimize_json_prompt(json_obj)
        return optimized
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al optimizar JSON: {str(e)}"
        )

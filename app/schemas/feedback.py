"""
Esquemas Pydantic para el sistema de feedback.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class FeedbackType(str, Enum):
    """Tipos de feedback soportados."""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"
    COMMENT = "comment"
    ISSUE = "issue"
    SUGGESTION = "suggestion"


class FeedbackCategory(str, Enum):
    """Categorías de feedback para clasificación."""

    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    SPEED = "speed"
    HELPFULNESS = "helpfulness"
    USER_EXPERIENCE = "user_experience"
    TECHNICAL_ISSUE = "technical_issue"
    OTHER = "other"


class MessageFeedbackRequest(BaseModel):
    """Request para dar feedback sobre un mensaje específico."""

    conversation_id: str = Field(..., description="ID de la conversación")
    message_id: str = Field(..., description="ID del mensaje")
    feedback_type: FeedbackType = Field(..., description="Tipo de feedback")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating del 1 al 5")
    comment: Optional[str] = Field(
        None, max_length=1000, description="Comentario opcional"
    )
    categories: Optional[List[FeedbackCategory]] = Field(
        None, description="Categorías relacionadas con el feedback"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Metadatos adicionales"
    )

    @validator("rating")
    def validate_rating(cls, v, values):
        """Validar que el rating sea requerido para tipo RATING."""
        if values.get("feedback_type") == FeedbackType.RATING and v is None:
            raise ValueError("Rating es requerido para feedback tipo RATING")
        return v

    @validator("comment")
    def validate_comment(cls, v, values):
        """Validar que el comentario sea requerido para ciertos tipos."""
        feedback_type = values.get("feedback_type")
        if feedback_type in [
            FeedbackType.COMMENT,
            FeedbackType.ISSUE,
            FeedbackType.SUGGESTION,
        ]:
            if not v or not v.strip():
                raise ValueError(
                    f"Comentario es requerido para feedback tipo {feedback_type}"
                )
        return v


class SessionFeedbackRequest(BaseModel):
    """Request para dar feedback sobre una sesión completa."""

    conversation_id: str = Field(..., description="ID de la conversación")
    overall_rating: int = Field(
        ..., ge=1, le=5, description="Rating general de la sesión"
    )
    categories_feedback: Dict[FeedbackCategory, int] = Field(
        default_factory=dict, description="Rating por categoría (1-5)"
    )
    would_recommend: Optional[bool] = Field(
        None, description="¿Recomendaría el servicio?"
    )
    comment: Optional[str] = Field(
        None, max_length=2000, description="Comentario general"
    )
    improvement_suggestions: Optional[List[str]] = Field(
        None, description="Sugerencias de mejora"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Metadatos adicionales"
    )

    @validator("categories_feedback")
    def validate_categories_feedback(cls, v):
        """Validar que los ratings de categorías estén en rango válido."""
        for category, rating in v.items():
            if not 1 <= rating <= 5:
                raise ValueError(f"Rating para {category} debe estar entre 1 y 5")
        return v


class FeedbackResponse(BaseModel):
    """Response después de registrar feedback."""

    feedback_id: str = Field(..., description="ID del feedback registrado")
    status: Literal["success", "error"] = Field(..., description="Estado del registro")
    message: str = Field(..., description="Mensaje de confirmación o error")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class FeedbackStats(BaseModel):
    """Estadísticas agregadas de feedback."""

    total_feedbacks: int = Field(..., description="Total de feedbacks recibidos")
    average_rating: Optional[float] = Field(None, description="Rating promedio")
    thumbs_up_count: int = Field(default=0, description="Cantidad de thumbs up")
    thumbs_down_count: int = Field(default=0, description="Cantidad de thumbs down")
    satisfaction_rate: Optional[float] = Field(
        None, description="Tasa de satisfacción (thumbs_up / total)"
    )
    categories_breakdown: Dict[FeedbackCategory, Dict[str, Any]] = Field(
        default_factory=dict, description="Breakdown por categoría"
    )
    common_issues: List[Dict[str, Any]] = Field(
        default_factory=list, description="Problemas más comunes reportados"
    )
    time_period: Dict[str, datetime] = Field(
        ..., description="Período de tiempo de las estadísticas"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class FeedbackFilter(BaseModel):
    """Filtros para consultar feedback."""

    conversation_id: Optional[str] = Field(None, description="Filtrar por conversación")
    user_id: Optional[str] = Field(None, description="Filtrar por usuario")
    feedback_type: Optional[FeedbackType] = Field(None, description="Filtrar por tipo")
    categories: Optional[List[FeedbackCategory]] = Field(
        None, description="Filtrar por categorías"
    )
    rating_min: Optional[int] = Field(None, ge=1, le=5, description="Rating mínimo")
    rating_max: Optional[int] = Field(None, ge=1, le=5, description="Rating máximo")
    start_date: Optional[datetime] = Field(None, description="Fecha inicio")
    end_date: Optional[datetime] = Field(None, description="Fecha fin")
    limit: int = Field(100, ge=1, le=1000, description="Límite de resultados")
    offset: int = Field(0, ge=0, description="Offset para paginación")

    @validator("end_date")
    def validate_date_range(cls, v, values):
        """Validar que end_date sea posterior a start_date."""
        start_date = values.get("start_date")
        if start_date and v and v < start_date:
            raise ValueError("end_date debe ser posterior a start_date")
        return v


class FeedbackItem(BaseModel):
    """Item individual de feedback."""

    feedback_id: str = Field(..., description="ID del feedback")
    user_id: str = Field(..., description="ID del usuario")
    conversation_id: str = Field(..., description="ID de la conversación")
    message_id: Optional[str] = Field(None, description="ID del mensaje (si aplica)")
    feedback_type: FeedbackType = Field(..., description="Tipo de feedback")
    rating: Optional[int] = Field(None, description="Rating")
    comment: Optional[str] = Field(None, description="Comentario")
    categories: List[FeedbackCategory] = Field(
        default_factory=list, description="Categorías"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: Optional[datetime] = Field(None, description="Fecha de actualización")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class FeedbackList(BaseModel):
    """Lista paginada de feedback."""

    items: List[FeedbackItem] = Field(..., description="Lista de feedback")
    total: int = Field(..., description="Total de items")
    limit: int = Field(..., description="Límite aplicado")
    offset: int = Field(..., description="Offset aplicado")
    has_more: bool = Field(..., description="¿Hay más resultados?")


class FeedbackAnalytics(BaseModel):
    """Analytics avanzados de feedback."""

    sentiment_analysis: Dict[str, float] = Field(
        ..., description="Análisis de sentimiento (positivo, negativo, neutro)"
    )
    trending_topics: List[Dict[str, Any]] = Field(
        ..., description="Temas trending en feedback"
    )
    agent_performance: Dict[str, Dict[str, Any]] = Field(
        ..., description="Performance por agente"
    )
    user_satisfaction_trend: List[Dict[str, Any]] = Field(
        ..., description="Tendencia de satisfacción en el tiempo"
    )
    improvement_areas: List[Dict[str, Any]] = Field(
        ..., description="Áreas principales de mejora identificadas"
    )
    nps_score: Optional[float] = Field(None, description="Net Promoter Score calculado")

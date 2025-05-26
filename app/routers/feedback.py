"""
Router de feedback para la API de NGX Agents.

Este módulo proporciona endpoints para registrar y consultar
feedback de los usuarios sobre las interacciones con los agentes.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from core.auth import get_current_user
from core.logging_config import get_logger
from core.feedback_service import feedback_service
from app.schemas.feedback import (
    MessageFeedbackRequest,
    SessionFeedbackRequest,
    FeedbackResponse,
    FeedbackStats,
    FeedbackFilter,
    FeedbackList,
    FeedbackAnalytics,
    FeedbackType,
    FeedbackCategory,
)

# Configurar logger
logger = get_logger(__name__)

# Crear router
router = APIRouter(
    prefix="/feedback",
    tags=["feedback"],
    responses={401: {"description": "No autorizado"}},
)


@router.post("/message", response_model=FeedbackResponse)
async def submit_message_feedback(
    request: MessageFeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Registra feedback para un mensaje específico.

    Permite a los usuarios dar feedback sobre respuestas individuales
    de los agentes, incluyendo ratings, comentarios y categorización.

    Args:
        request: Datos del feedback del mensaje
        current_user: Usuario autenticado

    Returns:
        FeedbackResponse con el resultado del registro
    """
    try:
        logger.info(
            f"Registrando feedback de mensaje para usuario {current_user['id']}, "
            f"conversación {request.conversation_id}, mensaje {request.message_id}"
        )

        # Registrar feedback
        response = await feedback_service.record_message_feedback(
            user_id=current_user["id"], request=request
        )

        if response.status == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.message,
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al registrar feedback de mensaje: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar feedback: {str(e)}",
        )


@router.post("/session", response_model=FeedbackResponse)
async def submit_session_feedback(
    request: SessionFeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Registra feedback para una sesión completa de chat.

    Permite evaluar la experiencia general de una conversación,
    incluyendo múltiples aspectos y sugerencias de mejora.

    Args:
        request: Datos del feedback de la sesión
        current_user: Usuario autenticado

    Returns:
        FeedbackResponse con el resultado del registro
    """
    try:
        logger.info(
            f"Registrando feedback de sesión para usuario {current_user['id']}, "
            f"conversación {request.conversation_id}"
        )

        # Registrar feedback
        response = await feedback_service.record_session_feedback(
            user_id=current_user["id"], request=request
        )

        if response.status == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.message,
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al registrar feedback de sesión: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar feedback: {str(e)}",
        )


@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    start_date: Optional[datetime] = Query(None, description="Fecha de inicio"),
    end_date: Optional[datetime] = Query(None, description="Fecha de fin"),
    conversation_id: Optional[str] = Query(
        None, description="ID de conversación específica"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Obtiene estadísticas agregadas de feedback.

    Proporciona métricas como rating promedio, tasa de satisfacción,
    y breakdown por categorías para el período especificado.

    Args:
        start_date: Fecha de inicio (por defecto: últimos 7 días)
        end_date: Fecha de fin (por defecto: ahora)
        conversation_id: Filtrar por conversación específica
        current_user: Usuario autenticado

    Returns:
        FeedbackStats con las estadísticas agregadas
    """
    try:
        logger.info(
            f"Consultando estadísticas de feedback para usuario {current_user['id']}"
        )

        # Obtener estadísticas
        stats = await feedback_service.get_feedback_stats(
            start_date=start_date, end_date=end_date, conversation_id=conversation_id
        )

        return stats

    except Exception as e:
        logger.error(f"Error al obtener estadísticas de feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}",
        )


@router.post("/search", response_model=FeedbackList)
async def search_feedback(
    filters: FeedbackFilter, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Busca feedback con filtros específicos.

    Permite búsquedas avanzadas de feedback con múltiples criterios
    incluyendo tipo, rating, categorías y rango de fechas.

    Args:
        filters: Filtros de búsqueda
        current_user: Usuario autenticado

    Returns:
        FeedbackList con los resultados paginados
    """
    try:
        logger.info(f"Buscando feedback con filtros para usuario {current_user['id']}")

        # Solo permitir búsqueda del propio feedback del usuario
        # (a menos que sea admin)
        if not current_user.get("is_admin", False):
            filters.user_id = current_user["id"]

        # Buscar feedback
        results = await feedback_service.search_feedback(filters)

        return results

    except Exception as e:
        logger.error(f"Error al buscar feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al buscar feedback: {str(e)}",
        )


@router.get("/analytics", response_model=FeedbackAnalytics)
async def get_feedback_analytics(
    start_date: Optional[datetime] = Query(None, description="Fecha de inicio"),
    end_date: Optional[datetime] = Query(None, description="Fecha de fin"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Obtiene analytics avanzados del feedback.

    Proporciona análisis detallados incluyendo sentimiento,
    trending topics, performance por agente y áreas de mejora.

    Requiere permisos de administrador.

    Args:
        start_date: Fecha de inicio
        end_date: Fecha de fin
        current_user: Usuario autenticado (debe ser admin)

    Returns:
        FeedbackAnalytics con análisis detallado
    """
    try:
        # Verificar permisos de admin
        if not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Se requieren permisos de administrador para acceder a analytics",
            )

        logger.info("Generando analytics de feedback")

        # Obtener analytics
        analytics = await feedback_service.get_analytics(
            start_date=start_date, end_date=end_date
        )

        return analytics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al generar analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar analytics: {str(e)}",
        )


@router.get("/types", response_model=Dict[str, Any])
async def get_feedback_types():
    """
    Obtiene los tipos de feedback disponibles.

    Endpoint útil para poblar selects en el frontend.

    Returns:
        Diccionario con tipos y categorías disponibles
    """
    return {
        "feedback_types": [
            {"value": ft.value, "label": ft.value.replace("_", " ").title()}
            for ft in FeedbackType
        ],
        "feedback_categories": [
            {"value": fc.value, "label": fc.value.replace("_", " ").title()}
            for fc in FeedbackCategory
        ],
    }


@router.get("/health")
async def feedback_health():
    """
    Endpoint de salud para el servicio de feedback.

    Returns:
        Estado del servicio
    """
    try:
        # Verificar que el servicio esté inicializado
        if not hasattr(feedback_service, "supabase_client"):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "service": "feedback",
                    "message": "Servicio no inicializado",
                },
            )

        return {
            "status": "healthy",
            "service": "feedback",
            "features": {
                "message_feedback": True,
                "session_feedback": True,
                "analytics": True,
                "search": True,
            },
        }

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "service": "feedback", "error": str(e)},
        )

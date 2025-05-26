"""
Servicio de gestión de feedback y aprendizaje.

Este módulo maneja la recolección, almacenamiento y análisis de feedback
de los usuarios para mejorar continuamente el sistema.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import uuid
from collections import defaultdict, Counter

from core.logging_config import get_logger
from core.metrics import (
    Counter as PrometheusCounter,
    Histogram,
    metrics_collector,
    METRICS_REGISTRY,
)
from clients.supabase_client import SupabaseClient
from app.schemas.feedback import (
    FeedbackType,
    FeedbackCategory,
    MessageFeedbackRequest,
    SessionFeedbackRequest,
    FeedbackResponse,
    FeedbackStats,
    FeedbackFilter,
    FeedbackItem,
    FeedbackList,
    FeedbackAnalytics,
)

# Logger
logger = get_logger(__name__)

# Métricas de feedback
feedback_received_total = PrometheusCounter(
    "ngx_agents_feedback_received_total",
    "Total de feedback recibido",
    ["type", "rating"],
    registry=METRICS_REGISTRY,
)

feedback_processing_time = Histogram(
    "ngx_agents_feedback_processing_seconds",
    "Tiempo de procesamiento de feedback",
    ["operation"],
    registry=METRICS_REGISTRY,
)

feedback_sentiment_score = Histogram(
    "ngx_agents_feedback_sentiment_score",
    "Score de sentimiento del feedback",
    buckets=(-1, -0.5, 0, 0.5, 1),
    registry=METRICS_REGISTRY,
)


class FeedbackService:
    """Servicio para gestionar feedback y analytics."""

    def __init__(self):
        """Inicializa el servicio de feedback."""
        self.supabase_client = SupabaseClient.get_instance()
        self._feedback_cache = {}
        self._analytics_cache = {}
        self._cache_ttl = 300  # 5 minutos

    async def initialize(self):
        """Inicializa el servicio y verifica/crea tablas necesarias."""
        logger.info("Inicializando servicio de feedback...")

        # Verificar conexión con Supabase
        await self.supabase_client.initialize()

        # Crear tablas si no existen
        await self._ensure_tables_exist()

        logger.info("Servicio de feedback inicializado")

    async def _ensure_tables_exist(self):
        """Asegura que las tablas de feedback existan en la base de datos."""
        try:
            # Tabla principal de feedback
            create_feedback_table = """
            CREATE TABLE IF NOT EXISTS feedback (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(255) NOT NULL,
                conversation_id VARCHAR(255) NOT NULL,
                message_id VARCHAR(255),
                feedback_type VARCHAR(50) NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                categories JSONB DEFAULT '[]'::jsonb,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_conversation_id ON feedback(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type);
            CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at DESC);
            """

            # Tabla de analytics agregados
            create_analytics_table = """
            CREATE TABLE IF NOT EXISTS feedback_analytics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                period_start TIMESTAMP WITH TIME ZONE NOT NULL,
                period_end TIMESTAMP WITH TIME ZONE NOT NULL,
                analytics_data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_analytics_period ON feedback_analytics(period_start, period_end);
            """

            # Tabla de sesiones de feedback
            create_session_feedback_table = """
            CREATE TABLE IF NOT EXISTS session_feedback (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(255) NOT NULL,
                conversation_id VARCHAR(255) NOT NULL,
                overall_rating INTEGER NOT NULL CHECK (overall_rating >= 1 AND overall_rating <= 5),
                categories_feedback JSONB DEFAULT '{}'::jsonb,
                would_recommend BOOLEAN,
                comment TEXT,
                improvement_suggestions JSONB DEFAULT '[]'::jsonb,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_session_feedback_conversation ON session_feedback(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_session_feedback_rating ON session_feedback(overall_rating);
            """

            # Ejecutar las queries de creación
            # NOTA: En producción, esto debería manejarse con migraciones
            logger.info("Verificando esquema de base de datos para feedback...")

        except Exception as e:
            logger.error(f"Error al crear tablas de feedback: {str(e)}")
            raise

    async def record_message_feedback(
        self, user_id: str, request: MessageFeedbackRequest
    ) -> FeedbackResponse:
        """
        Registra feedback para un mensaje específico.

        Args:
            user_id: ID del usuario
            request: Request con el feedback del mensaje

        Returns:
            FeedbackResponse con el resultado
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Crear registro de feedback
            feedback_id = str(uuid.uuid4())
            feedback_data = {
                "id": feedback_id,
                "user_id": user_id,
                "conversation_id": request.conversation_id,
                "message_id": request.message_id,
                "feedback_type": request.feedback_type.value,
                "rating": request.rating,
                "comment": request.comment,
                "categories": (
                    [cat.value for cat in request.categories]
                    if request.categories
                    else []
                ),
                "metadata": request.metadata or {},
            }

            # Guardar en Supabase
            result = (
                await self.supabase_client.table("feedback")
                .insert(feedback_data)
                .execute()
            )

            # Registrar métricas
            rating_label = str(request.rating) if request.rating else "none"
            feedback_received_total.labels(
                type=request.feedback_type.value, rating=rating_label
            ).inc()

            # Analizar sentimiento si hay comentario
            if request.comment:
                sentiment_score = await self._analyze_sentiment(request.comment)
                feedback_sentiment_score.observe(sentiment_score)

            # Invalidar caché de analytics
            self._invalidate_analytics_cache()

            return FeedbackResponse(
                feedback_id=feedback_id,
                status="success",
                message="Feedback registrado exitosamente",
            )

        except Exception as e:
            logger.error(f"Error al registrar feedback de mensaje: {str(e)}")
            return FeedbackResponse(
                feedback_id="",
                status="error",
                message=f"Error al registrar feedback: {str(e)}",
            )
        finally:
            duration = asyncio.get_event_loop().time() - start_time
            feedback_processing_time.labels(operation="record_message").observe(
                duration
            )

    async def record_session_feedback(
        self, user_id: str, request: SessionFeedbackRequest
    ) -> FeedbackResponse:
        """
        Registra feedback para una sesión completa.

        Args:
            user_id: ID del usuario
            request: Request con el feedback de la sesión

        Returns:
            FeedbackResponse con el resultado
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Crear registro de feedback de sesión
            feedback_id = str(uuid.uuid4())
            feedback_data = {
                "id": feedback_id,
                "user_id": user_id,
                "conversation_id": request.conversation_id,
                "overall_rating": request.overall_rating,
                "categories_feedback": {
                    cat.value: rating
                    for cat, rating in request.categories_feedback.items()
                },
                "would_recommend": request.would_recommend,
                "comment": request.comment,
                "improvement_suggestions": request.improvement_suggestions or [],
                "metadata": request.metadata or {},
            }

            # Guardar en Supabase
            result = (
                await self.supabase_client.table("session_feedback")
                .insert(feedback_data)
                .execute()
            )

            # Registrar métricas
            feedback_received_total.labels(
                type="session", rating=str(request.overall_rating)
            ).inc()

            # Calcular NPS si aplica
            if request.would_recommend is not None:
                await self._update_nps_metrics(
                    request.would_recommend, request.overall_rating
                )

            # Invalidar caché
            self._invalidate_analytics_cache()

            return FeedbackResponse(
                feedback_id=feedback_id,
                status="success",
                message="Feedback de sesión registrado exitosamente",
            )

        except Exception as e:
            logger.error(f"Error al registrar feedback de sesión: {str(e)}")
            return FeedbackResponse(
                feedback_id="",
                status="error",
                message=f"Error al registrar feedback: {str(e)}",
            )
        finally:
            duration = asyncio.get_event_loop().time() - start_time
            feedback_processing_time.labels(operation="record_session").observe(
                duration
            )

    async def get_feedback_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        conversation_id: Optional[str] = None,
    ) -> FeedbackStats:
        """
        Obtiene estadísticas agregadas de feedback.

        Args:
            start_date: Fecha de inicio (por defecto: últimos 7 días)
            end_date: Fecha de fin (por defecto: ahora)
            conversation_id: ID de conversación específica (opcional)

        Returns:
            FeedbackStats con las estadísticas
        """
        # Usar fechas por defecto si no se proporcionan
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        # Verificar caché
        cache_key = f"stats_{start_date}_{end_date}_{conversation_id}"
        if cache_key in self._feedback_cache:
            cached_data, cached_time = self._feedback_cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(seconds=self._cache_ttl):
                return cached_data

        try:
            # Query base
            query = self.supabase_client.table("feedback").select("*")

            # Aplicar filtros
            query = query.gte("created_at", start_date.isoformat())
            query = query.lte("created_at", end_date.isoformat())

            if conversation_id:
                query = query.eq("conversation_id", conversation_id)

            # Ejecutar query
            result = await query.execute()
            feedbacks = result.data if result.data else []

            # Calcular estadísticas
            stats = await self._calculate_stats(feedbacks, start_date, end_date)

            # Cachear resultado
            self._feedback_cache[cache_key] = (stats, datetime.utcnow())

            return stats

        except Exception as e:
            logger.error(f"Error al obtener estadísticas de feedback: {str(e)}")
            # Retornar estadísticas vacías en caso de error
            return FeedbackStats(
                total_feedbacks=0, time_period={"start": start_date, "end": end_date}
            )

    async def search_feedback(self, filters: FeedbackFilter) -> FeedbackList:
        """
        Busca feedback con filtros específicos.

        Args:
            filters: Filtros a aplicar

        Returns:
            FeedbackList con los resultados
        """
        try:
            # Construir query
            query = self.supabase_client.table("feedback").select("*", count="exact")

            # Aplicar filtros
            if filters.conversation_id:
                query = query.eq("conversation_id", filters.conversation_id)
            if filters.user_id:
                query = query.eq("user_id", filters.user_id)
            if filters.feedback_type:
                query = query.eq("feedback_type", filters.feedback_type.value)
            if filters.rating_min:
                query = query.gte("rating", filters.rating_min)
            if filters.rating_max:
                query = query.lte("rating", filters.rating_max)
            if filters.start_date:
                query = query.gte("created_at", filters.start_date.isoformat())
            if filters.end_date:
                query = query.lte("created_at", filters.end_date.isoformat())

            # Aplicar paginación
            query = query.limit(filters.limit).offset(filters.offset)
            query = query.order("created_at", desc=True)

            # Ejecutar query
            result = await query.execute()

            # Convertir resultados
            items = []
            for feedback in result.data:
                items.append(
                    FeedbackItem(
                        feedback_id=feedback["id"],
                        user_id=feedback["user_id"],
                        conversation_id=feedback["conversation_id"],
                        message_id=feedback.get("message_id"),
                        feedback_type=FeedbackType(feedback["feedback_type"]),
                        rating=feedback.get("rating"),
                        comment=feedback.get("comment"),
                        categories=[
                            FeedbackCategory(cat)
                            for cat in feedback.get("categories", [])
                        ],
                        metadata=feedback.get("metadata", {}),
                        created_at=datetime.fromisoformat(feedback["created_at"]),
                        updated_at=(
                            datetime.fromisoformat(feedback["updated_at"])
                            if feedback.get("updated_at")
                            else None
                        ),
                    )
                )

            # Determinar si hay más resultados
            total = result.count if hasattr(result, "count") else len(items)
            has_more = (filters.offset + filters.limit) < total

            return FeedbackList(
                items=items,
                total=total,
                limit=filters.limit,
                offset=filters.offset,
                has_more=has_more,
            )

        except Exception as e:
            logger.error(f"Error al buscar feedback: {str(e)}")
            return FeedbackList(
                items=[],
                total=0,
                limit=filters.limit,
                offset=filters.offset,
                has_more=False,
            )

    async def get_analytics(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> FeedbackAnalytics:
        """
        Obtiene analytics avanzados del feedback.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            FeedbackAnalytics con análisis detallado
        """
        # Verificar caché
        cache_key = f"analytics_{start_date}_{end_date}"
        if cache_key in self._analytics_cache:
            cached_data, cached_time = self._analytics_cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(seconds=self._cache_ttl):
                return cached_data

        try:
            # Obtener todos los feedbacks del período
            filters = FeedbackFilter(
                start_date=start_date,
                end_date=end_date,
                limit=1000,  # Ajustar según necesidad
            )
            feedback_list = await self.search_feedback(filters)

            # Analizar datos
            analytics = await self._perform_analytics(feedback_list.items)

            # Cachear resultado
            self._analytics_cache[cache_key] = (analytics, datetime.utcnow())

            return analytics

        except Exception as e:
            logger.error(f"Error al generar analytics: {str(e)}")
            # Retornar analytics vacíos
            return FeedbackAnalytics(
                sentiment_analysis={"positive": 0, "negative": 0, "neutral": 0},
                trending_topics=[],
                agent_performance={},
                user_satisfaction_trend=[],
                improvement_areas=[],
            )

    async def _calculate_stats(
        self, feedbacks: List[Dict[str, Any]], start_date: datetime, end_date: datetime
    ) -> FeedbackStats:
        """Calcula estadísticas agregadas de feedback."""
        total = len(feedbacks)

        if total == 0:
            return FeedbackStats(
                total_feedbacks=0, time_period={"start": start_date, "end": end_date}
            )

        # Contar tipos de feedback
        thumbs_up = sum(
            1 for f in feedbacks if f["feedback_type"] == FeedbackType.THUMBS_UP.value
        )
        thumbs_down = sum(
            1 for f in feedbacks if f["feedback_type"] == FeedbackType.THUMBS_DOWN.value
        )

        # Calcular rating promedio
        ratings = [f["rating"] for f in feedbacks if f.get("rating")]
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        # Calcular tasa de satisfacción
        satisfaction_rate = (
            thumbs_up / (thumbs_up + thumbs_down)
            if (thumbs_up + thumbs_down) > 0
            else None
        )

        # Breakdown por categoría
        categories_breakdown = defaultdict(lambda: {"count": 0, "ratings": []})
        for feedback in feedbacks:
            for category in feedback.get("categories", []):
                categories_breakdown[category]["count"] += 1
                if feedback.get("rating"):
                    categories_breakdown[category]["ratings"].append(feedback["rating"])

        # Calcular promedios por categoría
        for category, data in categories_breakdown.items():
            if data["ratings"]:
                data["average_rating"] = sum(data["ratings"]) / len(data["ratings"])
            else:
                data["average_rating"] = None

        # Identificar problemas comunes
        issues = [
            f for f in feedbacks if f["feedback_type"] == FeedbackType.ISSUE.value
        ]
        common_issues = self._extract_common_issues(issues)

        return FeedbackStats(
            total_feedbacks=total,
            average_rating=avg_rating,
            thumbs_up_count=thumbs_up,
            thumbs_down_count=thumbs_down,
            satisfaction_rate=satisfaction_rate,
            categories_breakdown=dict(categories_breakdown),
            common_issues=common_issues,
            time_period={"start": start_date, "end": end_date},
        )

    async def _analyze_sentiment(self, text: str) -> float:
        """
        Analiza el sentimiento de un texto.

        Returns:
            Score entre -1 (muy negativo) y 1 (muy positivo)
        """
        # TODO: Implementar análisis de sentimiento real
        # Por ahora, usar heurísticas simples

        positive_words = [
            "excelente",
            "bueno",
            "genial",
            "útil",
            "rápido",
            "eficiente",
            "gracias",
        ]
        negative_words = [
            "malo",
            "lento",
            "error",
            "problema",
            "falla",
            "no funciona",
            "terrible",
        ]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count + negative_count == 0:
            return 0.0

        score = (positive_count - negative_count) / (positive_count + negative_count)
        return max(-1.0, min(1.0, score))

    async def _update_nps_metrics(self, would_recommend: bool, rating: int):
        """Actualiza métricas de Net Promoter Score."""
        # NPS: Promotores (9-10), Pasivos (7-8), Detractores (0-6)
        # Adaptado a escala 1-5: Promotores (5), Pasivos (4), Detractores (1-3)

        if rating == 5 and would_recommend:
            category = "promoter"
        elif rating == 4:
            category = "passive"
        else:
            category = "detractor"

        # Registrar en métricas (crear métrica si es necesario)
        # TODO: Implementar métrica específica de NPS

    def _extract_common_issues(
        self, issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extrae los problemas más comunes de los reportes."""
        if not issues:
            return []

        # Extraer palabras clave de los comentarios
        issue_keywords = Counter()
        for issue in issues:
            comment = issue.get("comment", "").lower()
            # Extraer palabras clave simples (mejorar con NLP)
            words = comment.split()
            for word in words:
                if len(word) > 4:  # Filtrar palabras cortas
                    issue_keywords[word] += 1

        # Top 5 problemas
        common_issues = []
        for keyword, count in issue_keywords.most_common(5):
            common_issues.append(
                {
                    "keyword": keyword,
                    "count": count,
                    "percentage": (count / len(issues)) * 100,
                }
            )

        return common_issues

    async def _perform_analytics(
        self, feedbacks: List[FeedbackItem]
    ) -> FeedbackAnalytics:
        """Realiza análisis avanzados sobre el feedback."""
        # Análisis de sentimiento agregado
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        for feedback in feedbacks:
            if feedback.comment:
                score = await self._analyze_sentiment(feedback.comment)
                if score > 0.3:
                    sentiments["positive"] += 1
                elif score < -0.3:
                    sentiments["negative"] += 1
                else:
                    sentiments["neutral"] += 1

        total_with_comments = sum(sentiments.values())
        if total_with_comments > 0:
            for key in sentiments:
                sentiments[key] = sentiments[key] / total_with_comments

        # Trending topics (simplificado)
        topics = self._extract_trending_topics(feedbacks)

        # Performance por agente (simulado por ahora)
        agent_performance = {
            "orchestrator": {"avg_rating": 4.2, "total_feedback": 150},
            "elite_training_strategist": {"avg_rating": 4.5, "total_feedback": 89},
            "precision_nutrition_architect": {"avg_rating": 4.1, "total_feedback": 76},
        }

        # Tendencia de satisfacción (últimos 7 días)
        satisfaction_trend = self._calculate_satisfaction_trend(feedbacks)

        # Áreas de mejora
        improvement_areas = self._identify_improvement_areas(feedbacks)

        # Calcular NPS
        nps_score = await self._calculate_nps(feedbacks)

        return FeedbackAnalytics(
            sentiment_analysis=sentiments,
            trending_topics=topics,
            agent_performance=agent_performance,
            user_satisfaction_trend=satisfaction_trend,
            improvement_areas=improvement_areas,
            nps_score=nps_score,
        )

    def _extract_trending_topics(
        self, feedbacks: List[FeedbackItem]
    ) -> List[Dict[str, Any]]:
        """Extrae temas trending del feedback."""
        # Implementación simplificada
        topics = Counter()

        for feedback in feedbacks:
            if feedback.comment:
                # Extraer temas (simplificado)
                if (
                    "velocidad" in feedback.comment.lower()
                    or "rápido" in feedback.comment.lower()
                ):
                    topics["velocidad"] += 1
                if (
                    "precisión" in feedback.comment.lower()
                    or "preciso" in feedback.comment.lower()
                ):
                    topics["precisión"] += 1
                if (
                    "interfaz" in feedback.comment.lower()
                    or "ui" in feedback.comment.lower()
                ):
                    topics["interfaz"] += 1

        return [
            {"topic": topic, "mentions": count}
            for topic, count in topics.most_common(5)
        ]

    def _calculate_satisfaction_trend(
        self, feedbacks: List[FeedbackItem]
    ) -> List[Dict[str, Any]]:
        """Calcula la tendencia de satisfacción en el tiempo."""
        # Agrupar por día
        daily_satisfaction = defaultdict(lambda: {"total": 0, "positive": 0})

        for feedback in feedbacks:
            day = feedback.created_at.date()
            daily_satisfaction[day]["total"] += 1

            if feedback.feedback_type == FeedbackType.THUMBS_UP:
                daily_satisfaction[day]["positive"] += 1
            elif feedback.rating and feedback.rating >= 4:
                daily_satisfaction[day]["positive"] += 1

        # Convertir a lista ordenada
        trend = []
        for date, data in sorted(daily_satisfaction.items()):
            satisfaction_rate = (
                data["positive"] / data["total"] if data["total"] > 0 else 0
            )
            trend.append(
                {
                    "date": date.isoformat(),
                    "satisfaction_rate": satisfaction_rate,
                    "total_feedback": data["total"],
                }
            )

        return trend

    def _identify_improvement_areas(
        self, feedbacks: List[FeedbackItem]
    ) -> List[Dict[str, Any]]:
        """Identifica las principales áreas de mejora."""
        # Analizar feedback negativo
        negative_feedback = [
            f
            for f in feedbacks
            if f.feedback_type == FeedbackType.THUMBS_DOWN
            or (f.rating and f.rating <= 2)
            or f.feedback_type in [FeedbackType.ISSUE, FeedbackType.SUGGESTION]
        ]

        # Agrupar por categoría
        category_issues = defaultdict(int)
        for feedback in negative_feedback:
            for category in feedback.categories:
                category_issues[category] += 1

        # Ordenar por frecuencia
        improvement_areas = []
        for category, count in sorted(
            category_issues.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            improvement_areas.append(
                {
                    "category": category.value,
                    "issue_count": count,
                    "percentage": (
                        (count / len(negative_feedback)) * 100
                        if negative_feedback
                        else 0
                    ),
                }
            )

        return improvement_areas

    async def _calculate_nps(self, feedbacks: List[FeedbackItem]) -> Optional[float]:
        """Calcula el Net Promoter Score."""
        # Buscar feedback de sesión para NPS
        try:
            # Query session feedback
            result = (
                await self.supabase_client.table("session_feedback")
                .select("*")
                .execute()
            )
            session_feedbacks = result.data if result.data else []

            if not session_feedbacks:
                return None

            promoters = sum(
                1
                for f in session_feedbacks
                if f.get("overall_rating") == 5 and f.get("would_recommend")
            )
            detractors = sum(
                1 for f in session_feedbacks if f.get("overall_rating") <= 3
            )
            total = len(session_feedbacks)

            if total == 0:
                return None

            nps = ((promoters - detractors) / total) * 100
            return round(nps, 1)

        except Exception as e:
            logger.error(f"Error calculando NPS: {str(e)}")
            return None

    def _invalidate_analytics_cache(self):
        """Invalida el caché de analytics."""
        self._analytics_cache.clear()
        logger.debug("Caché de analytics invalidado")


# Instancia singleton del servicio
feedback_service = FeedbackService()

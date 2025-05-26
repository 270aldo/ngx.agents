"""
Adaptador base para agentes.

Este módulo define una clase base para los adaptadores de agentes que contiene
la lógica común de clasificación y ejecución.
"""

import logging
from typing import Dict, Any, Tuple
from datetime import datetime

from adk.agent import Agent
from core.intent_analyzer_optimized import IntentAnalyzer
from core.state_manager_optimized import StateManager
from services.program_classification_service import ProgramClassificationService
from core.telemetry import get_tracer

# Configurar logging
logger = logging.getLogger(__name__)

# Obtener tracer para telemetría
tracer = get_tracer("ngx_agents.infrastructure.adapters.base_agent_adapter")


class BaseAgentAdapter(Agent):
    """
    Clase base para adaptadores de agentes.

    Esta clase implementa la lógica común de clasificación y ejecución
    que se comparte entre todos los adaptadores de agentes.
    """

    def __init__(self, *args, **kwargs):
        """
        Inicializa el adaptador base.

        Args:
            *args: Argumentos posicionales para la clase base Agent
            **kwargs: Argumentos de palabras clave para la clase base Agent
        """
        super().__init__(*args, **kwargs)
        self.intent_analyzer = IntentAnalyzer()
        self.state_manager = StateManager()
        self.program_classification_service = ProgramClassificationService()

        # Configuración de clasificación
        self.classification_threshold = 0.7
        self.fallback_keywords = []
        self.excluded_keywords = []

    async def _classify_query(
        self, query: str, user_id: str = None, context: Dict[str, Any] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Clasifica una consulta para determinar si este agente puede manejarla.

        Esta implementación base utiliza una combinación de análisis de intención
        y palabras clave para determinar la puntuación de clasificación.

        Args:
            query: La consulta del usuario a clasificar
            user_id: ID del usuario (opcional)
            context: Contexto adicional para la clasificación (opcional)

        Returns:
            Tupla con la puntuación de clasificación y metadatos adicionales
        """
        # Usar span de telemetría si está disponible
        if tracer:
            context_manager = tracer.start_as_current_span(
                f"{self.__class__.__name__}._classify_query"
            )
        else:
            # Usar un context manager nulo si la telemetría no está disponible
            from contextlib import nullcontext

            context_manager = nullcontext()

        with context_manager:
            try:
                # Inicializar contexto si no se proporciona
                if context is None:
                    context = {}

                # Registrar información de clasificación
                logger.debug(
                    f"Clasificando consulta para {self.__class__.__name__}: {query[:100]}...",
                    extra={"user_id": user_id, "agent": self.__class__.__name__},
                )

                # Paso 1: Análisis de intención mediante el analizador de intenciones
                intent_score = await self.intent_analyzer.analyze(
                    query, agent_type=self.__class__.__name__, user_id=user_id
                )

                # Paso 2: Verificar palabras clave de fallback
                keyword_score = self._check_keywords(query)

                # Paso 3: Combinar puntuaciones (70% intención, 30% palabras clave)
                combined_score = (0.7 * intent_score) + (0.3 * keyword_score)

                # Paso 4: Verificar palabras clave excluidas
                if self._has_excluded_keywords(query):
                    combined_score *= (
                        0.5  # Reducir puntuación si hay palabras clave excluidas
                    )

                # Paso 5: Aplicar ajustes específicos del contexto
                context_adjusted_score = self._adjust_score_based_on_context(
                    combined_score, context
                )

                # Crear metadatos de clasificación
                metadata = {
                    "intent_score": intent_score,
                    "keyword_score": keyword_score,
                    "combined_score": combined_score,
                    "final_score": context_adjusted_score,
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                logger.debug(
                    f"Clasificación completada para {self.__class__.__name__}: {context_adjusted_score:.4f}",
                    extra={"user_id": user_id, "score": context_adjusted_score},
                )

                return context_adjusted_score, metadata

            except Exception as e:
                logger.error(
                    f"Error al clasificar consulta para {self.__class__.__name__}: {str(e)}",
                    exc_info=True,
                    extra={"user_id": user_id, "agent": self.__class__.__name__},
                )
                return 0.0, {"error": str(e)}

    def _check_keywords(self, query: str) -> float:
        """
        Verifica si la consulta contiene palabras clave de fallback.

        Args:
            query: La consulta del usuario

        Returns:
            Puntuación basada en palabras clave (0.0 - 1.0)
        """
        if not self.fallback_keywords:
            return 0.0

        query_lower = query.lower()
        matched_keywords = [
            kw for kw in self.fallback_keywords if kw.lower() in query_lower
        ]

        if not matched_keywords:
            return 0.0

        # Calcular puntuación basada en el número de coincidencias y su relevancia
        return min(1.0, len(matched_keywords) / len(self.fallback_keywords) * 2)

    def _has_excluded_keywords(self, query: str) -> bool:
        """
        Verifica si la consulta contiene palabras clave excluidas.

        Args:
            query: La consulta del usuario

        Returns:
            True si la consulta contiene palabras clave excluidas, False en caso contrario
        """
        if not self.excluded_keywords:
            return False

        query_lower = query.lower()
        return any(kw.lower() in query_lower for kw in self.excluded_keywords)

    def _adjust_score_based_on_context(
        self, score: float, context: Dict[str, Any]
    ) -> float:
        """
        Ajusta la puntuación de clasificación basada en el contexto.

        Los adaptadores específicos pueden sobrescribir este método para implementar
        ajustes específicos basados en el contexto.

        Args:
            score: Puntuación de clasificación original
            context: Contexto adicional para la clasificación

        Returns:
            Puntuación ajustada
        """
        # Implementación base: sin ajustes
        return score

    async def _get_program_type_from_profile(self, profile: Dict[str, Any]) -> str:
        """
        Determina el tipo de programa basado en el perfil del usuario.

        Args:
            profile: Perfil del usuario

        Returns:
            Tipo de programa (general, elite, etc.)
        """
        try:
            # Usar el servicio de clasificación de programas
            program_type = await self.program_classification_service.classify_profile(
                profile
            )
            return program_type
        except Exception as e:
            logger.error(
                f"Error al determinar el tipo de programa: {str(e)}", exc_info=True
            )
            return "general"  # Valor por defecto en caso de error

    async def run_async_impl(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Implementación asíncrona de la ejecución del agente.

        Esta implementación base proporciona el flujo común de ejecución y manejo de errores.
        Los adaptadores específicos deben sobrescribir el método _process_query.

        Args:
            query: La consulta del usuario
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta del agente
        """
        # Usar span de telemetría si está disponible
        if tracer:
            context_manager = tracer.start_as_current_span(
                f"{self.__class__.__name__}.run_async_impl"
            )
        else:
            # Usar un context manager nulo si la telemetría no está disponible
            from contextlib import nullcontext

            context_manager = nullcontext()

        with context_manager:
            try:
                # Extraer parámetros comunes
                user_id = kwargs.get("user_id", "anonymous")
                session_id = kwargs.get("session_id", "")
                profile = kwargs.get("profile", {})

                # Registrar inicio de ejecución
                logger.info(
                    f"Ejecutando {self.__class__.__name__} para consulta: {query[:100]}...",
                    extra={"user_id": user_id, "session_id": session_id},
                )

                # Obtener tipo de programa si hay perfil disponible
                program_type = "general"
                if profile:
                    program_type = await self._get_program_type_from_profile(profile)
                    logger.debug(f"Tipo de programa determinado: {program_type}")

                # Obtener estado actual del usuario
                state = await self.state_manager.get_state(user_id, session_id)

                # Procesar la consulta (implementado por subclases)
                start_time = datetime.utcnow()
                response = await self._process_query(
                    query=query,
                    user_id=user_id,
                    session_id=session_id,
                    program_type=program_type,
                    state=state,
                    profile=profile,
                    **kwargs,
                )
                end_time = datetime.utcnow()

                # Calcular tiempo de procesamiento
                processing_time = (end_time - start_time).total_seconds()

                # Actualizar estado
                if response.get("update_state", True):
                    await self.state_manager.update_state(
                        user_id=user_id,
                        session_id=session_id,
                        query=query,
                        response=response,
                        metadata={
                            "agent": self.__class__.__name__,
                            "program_type": program_type,
                            "processing_time": processing_time,
                        },
                    )

                # Registrar finalización exitosa
                logger.info(
                    f"Ejecución completada para {self.__class__.__name__} en {processing_time:.2f}s",
                    extra={
                        "user_id": user_id,
                        "session_id": session_id,
                        "processing_time": processing_time,
                    },
                )

                return response

            except Exception as e:
                logger.error(
                    f"Error en ejecución de {self.__class__.__name__}: {str(e)}",
                    exc_info=True,
                    extra={"user_id": kwargs.get("user_id", "anonymous")},
                )

                # Devolver respuesta de error
                return {
                    "success": False,
                    "error": str(e),
                    "agent": self.__class__.__name__,
                    "timestamp": datetime.utcnow().isoformat(),
                }

    async def _process_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        program_type: str,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario.

        Este método debe ser implementado por las subclases.

        Args:
            query: La consulta del usuario
            user_id: ID del usuario
            session_id: ID de la sesión
            program_type: Tipo de programa (general, elite, etc.)
            state: Estado actual del usuario
            profile: Perfil del usuario
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta del agente
        """
        raise NotImplementedError("Las subclases deben implementar _process_query")

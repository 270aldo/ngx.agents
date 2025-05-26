"""
Adaptador para el agente ProgressTracker que utiliza los componentes optimizados.

Este adaptador extiende el agente ProgressTracker original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

import logging
import time
from typing import Dict, Any, List
from datetime import datetime

from agents.progress_tracker.agent import ProgressTracker
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.telemetry import get_telemetry
from clients.vertex_ai.client import VertexAIClient

# Configurar logger
logger = logging.getLogger(__name__)


class ProgressTrackerAdapter(ProgressTracker, BaseAgentAdapter):
    """
    Adaptador para el agente ProgressTracker que utiliza los componentes optimizados.

    Este adaptador extiende el agente ProgressTracker original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """

    def __init__(self):
        """
        Inicializa el adaptador ProgressTracker.
        """
        super().__init__()
        self.telemetry = get_telemetry()
        self.agent_name = "progress_tracker"
        self.vertex_ai_client = VertexAIClient()

        # Configuración de clasificación
        self.fallback_keywords = [
            "progreso",
            "progress",
            "análisis",
            "analysis",
            "gráfico",
            "chart",
            "visualización",
            "visualization",
            "comparar",
            "compare",
            "tendencia",
            "trend",
            "métrica",
            "metric",
            "datos",
            "data",
            "seguimiento",
            "tracking",
            "estadística",
            "statistic",
        ]

        self.excluded_keywords = [
            "nutrición",
            "nutrition",
            "entrenamiento",
            "training",
            "médico",
            "medical",
            "doctor",
            "lesión",
            "injury",
        ]

    def get_agent_name(self) -> str:
        """Devuelve el nombre del agente."""
        return self.agent_name

    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente ProgressTracker.

        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "progress_analyses": [],
            "progress_visualizations": [],
            "progress_comparisons": [],
            "metrics_tracked": [],
            "last_updated": datetime.now().isoformat(),
        }

    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para ProgressTracker.

        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "análisis": "analyze_progress",
            "analysis": "analyze_progress",
            "analizar": "analyze_progress",
            "analyze": "analyze_progress",
            "tendencia": "analyze_progress",
            "trend": "analyze_progress",
            "gráfico": "visualize_progress",
            "chart": "visualize_progress",
            "visualización": "visualize_progress",
            "visualization": "visualize_progress",
            "visualizar": "visualize_progress",
            "visualize": "visualize_progress",
            "mostrar": "visualize_progress",
            "show": "visualize_progress",
            "comparar": "compare_progress",
            "compare": "compare_progress",
            "comparación": "compare_progress",
            "comparison": "compare_progress",
            "diferencia": "compare_progress",
            "difference": "compare_progress",
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

        Args:
            query: La consulta del usuario
            user_id: ID del usuario
            session_id: ID de la sesión
            program_type: Tipo de programa (general, elite, etc.)
            state: Estado actual del usuario
            profile: Perfil del usuario
            **kwargs: Argumentos adicionales

        Returns:
            Dict[str, Any]: Respuesta del agente
        """
        try:
            # Registrar telemetría para el inicio del procesamiento
            if self.telemetry:
                with self.telemetry.start_as_current_span(
                    f"{self.__class__.__name__}._process_query"
                ) as span:
                    span.set_attribute("user_id", user_id)
                    span.set_attribute("session_id", session_id)
                    span.set_attribute("program_type", program_type)

            # Determinar el tipo de consulta basado en el mapeo de intenciones
            query_type = self._determine_query_type(query)
            logger.info(
                f"ProgressTrackerAdapter procesando consulta de tipo: {query_type}"
            )

            # Obtener o crear el contexto
            context = state.get("progress_context", self._create_default_context())

            # Extraer métricas mencionadas en la consulta
            metrics = self._extract_metrics_from_query(query)

            # Extraer periodos de tiempo mencionados en la consulta
            time_periods = self._extract_time_periods_from_query(query)

            # Procesar según el tipo de consulta
            if query_type == "analyze_progress":
                result = await self._handle_analyze_progress(
                    query,
                    user_id,
                    context,
                    profile,
                    program_type,
                    metrics,
                    time_periods,
                )
            elif query_type == "visualize_progress":
                result = await self._handle_visualize_progress(
                    query,
                    user_id,
                    context,
                    profile,
                    program_type,
                    metrics,
                    time_periods,
                )
            elif query_type == "compare_progress":
                result = await self._handle_compare_progress(
                    query,
                    user_id,
                    context,
                    profile,
                    program_type,
                    metrics,
                    time_periods,
                )
            else:
                # Tipo de consulta no reconocido, usar análisis por defecto
                result = await self._handle_analyze_progress(
                    query,
                    user_id,
                    context,
                    profile,
                    program_type,
                    metrics,
                    time_periods,
                )

            # Actualizar el contexto en el estado
            state["progress_context"] = context

            # Construir la respuesta
            response = {
                "success": True,
                "output": result.get("response", "No se pudo generar una respuesta"),
                "query_type": query_type,
                "program_type": program_type,
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat(),
                "context": context,
            }

            # Añadir URL de visualización si está disponible
            if "visualization_url" in result:
                response["visualization_url"] = result["visualization_url"]

            return response

        except Exception as e:
            logger.error(
                f"Error al procesar consulta en ProgressTrackerAdapter: {str(e)}",
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat(),
            }

    def _determine_query_type(self, query: str) -> str:
        """
        Determina el tipo de consulta basado en el texto.

        Args:
            query: Consulta del usuario

        Returns:
            str: Tipo de consulta identificado
        """
        query_lower = query.lower()
        intent_mapping = self._get_intent_to_query_type_mapping()

        for intent, query_type in intent_mapping.items():
            if intent.lower() in query_lower:
                return query_type

        # Si no se encuentra un tipo específico, verificar palabras clave adicionales
        if any(
            word in query_lower
            for word in ["gráfica", "gráfico", "visual", "ver", "mostrar"]
        ):
            return "visualize_progress"
        elif any(
            word in query_lower
            for word in ["comparar", "diferencia", "versus", "vs", "entre"]
        ):
            return "compare_progress"

        # Si no se encuentra un tipo específico, devolver análisis por defecto
        return "analyze_progress"

    def _extract_metrics_from_query(self, query: str) -> List[str]:
        """
        Extrae métricas mencionadas en la consulta del usuario.

        Args:
            query: Consulta del usuario

        Returns:
            List[str]: Lista de métricas mencionadas
        """
        query_lower = query.lower()

        # Lista de métricas comunes que el sistema puede rastrear
        common_metrics = [
            "peso",
            "weight",
            "fuerza",
            "strength",
            "resistencia",
            "endurance",
            "velocidad",
            "speed",
            "flexibilidad",
            "flexibility",
            "masa muscular",
            "muscle mass",
            "grasa corporal",
            "body fat",
            "presión arterial",
            "blood pressure",
            "frecuencia cardíaca",
            "heart rate",
            "sueño",
            "sleep",
            "calorías",
            "calories",
            "pasos",
            "steps",
            "distancia",
            "distance",
            "tiempo",
            "time",
            "repeticiones",
            "repetitions",
            "series",
            "sets",
            "vo2max",
            "vo2max",
        ]

        # Buscar métricas en la consulta
        found_metrics = []
        for metric in common_metrics:
            if metric in query_lower:
                # Normalizar nombres de métricas (usar versión en inglés)
                normalized_metric = metric
                if metric == "peso":
                    normalized_metric = "weight"
                elif metric == "fuerza":
                    normalized_metric = "strength"
                elif metric == "resistencia":
                    normalized_metric = "endurance"
                elif metric == "velocidad":
                    normalized_metric = "speed"
                elif metric == "flexibilidad":
                    normalized_metric = "flexibility"
                elif metric == "masa muscular":
                    normalized_metric = "muscle_mass"
                elif metric == "grasa corporal":
                    normalized_metric = "body_fat"
                elif metric == "presión arterial":
                    normalized_metric = "blood_pressure"
                elif metric == "frecuencia cardíaca":
                    normalized_metric = "heart_rate"
                elif metric == "sueño":
                    normalized_metric = "sleep"
                elif metric == "calorías":
                    normalized_metric = "calories"
                elif metric == "pasos":
                    normalized_metric = "steps"
                elif metric == "distancia":
                    normalized_metric = "distance"
                elif metric == "tiempo":
                    normalized_metric = "time"
                elif metric == "repeticiones":
                    normalized_metric = "repetitions"
                elif metric == "series":
                    normalized_metric = "sets"

                if normalized_metric not in found_metrics:
                    found_metrics.append(normalized_metric)

        # Si no se encontraron métricas, usar peso como predeterminado
        if not found_metrics:
            found_metrics = ["weight"]

        return found_metrics

    def _extract_time_periods_from_query(self, query: str) -> List[str]:
        """
        Extrae periodos de tiempo mencionados en la consulta del usuario.

        Args:
            query: Consulta del usuario

        Returns:
            List[str]: Lista de periodos de tiempo mencionados
        """
        query_lower = query.lower()

        # Lista de periodos de tiempo comunes
        time_periods = {
            "última semana": "last_week",
            "last week": "last_week",
            "semana pasada": "last_week",
            "último mes": "last_month",
            "last month": "last_month",
            "mes pasado": "last_month",
            "últimos 3 meses": "last_3_months",
            "last 3 months": "last_3_months",
            "últimos tres meses": "last_3_months",
            "último año": "last_year",
            "last year": "last_year",
            "año pasado": "last_year",
        }

        # Buscar periodos de tiempo en la consulta
        found_periods = []
        for period_text, period_id in time_periods.items():
            if period_text in query_lower and period_id not in found_periods:
                found_periods.append(period_id)

        # Si se trata de una comparación, asegurarse de tener dos periodos
        if (
            "compare_progress" in self._determine_query_type(query)
            and len(found_periods) < 2
        ):
            if len(found_periods) == 1:
                # Si solo hay un periodo, añadir otro diferente
                if found_periods[0] == "last_week":
                    found_periods.append("last_month")
                else:
                    found_periods.append("last_week")
            else:
                # Si no hay periodos, usar semana pasada y mes pasado
                found_periods = ["last_week", "last_month"]

        # Si no se encontraron periodos, usar última semana como predeterminado
        if not found_periods:
            found_periods = ["last_week"]

        return found_periods

    async def _handle_analyze_progress(
        self,
        query: str,
        user_id: str,
        context: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
        metrics: List[str],
        time_periods: List[str],
    ) -> Dict[str, Any]:
        """
        Maneja una consulta de análisis de progreso.

        Args:
            query: Consulta del usuario
            user_id: ID del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            metrics: Métricas a analizar
            time_periods: Periodos de tiempo a analizar

        Returns:
            Dict[str, Any]: Resultado del análisis de progreso
        """
        # Usar el primer periodo de tiempo
        time_period = time_periods[0] if time_periods else "last_week"

        # Generar el análisis de progreso
        analysis_response = await self._generate_response(
            prompt=f"""
            Como analista de datos especializado en seguimiento de progreso para programas {program_type}, 
            analiza los siguientes datos de progreso:
            
            CONSULTA DEL USUARIO:
            {query}
            
            USUARIO:
            ID: {user_id}
            Perfil: {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            MÉTRICAS A ANALIZAR:
            {', '.join(metrics)}
            
            PERIODO DE TIEMPO:
            {time_period}
            
            Proporciona un análisis detallado que incluya:
            1. Tendencias principales identificadas
            2. Patrones de progreso
            3. Áreas de mejora
            4. Recomendaciones específicas para el programa {program_type}
            """,
            context=context,
        )

        # Actualizar el contexto con el nuevo análisis
        if "progress_analyses" not in context:
            context["progress_analyses"] = []

        context["progress_analyses"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "metrics": metrics,
                "time_period": time_period,
                "program_type": program_type,
                "analysis": analysis_response,
            }
        )

        # Actualizar métricas rastreadas
        if "metrics_tracked" not in context:
            context["metrics_tracked"] = []

        for metric in metrics:
            if metric not in context["metrics_tracked"]:
                context["metrics_tracked"].append(metric)

        return {"response": analysis_response, "context": context}

    async def _handle_visualize_progress(
        self,
        query: str,
        user_id: str,
        context: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
        metrics: List[str],
        time_periods: List[str],
    ) -> Dict[str, Any]:
        """
        Maneja una consulta de visualización de progreso.

        Args:
            query: Consulta del usuario
            user_id: ID del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            metrics: Métricas a visualizar
            time_periods: Periodos de tiempo a visualizar

        Returns:
            Dict[str, Any]: Resultado de la visualización de progreso
        """
        # Usar el primer periodo de tiempo y la primera métrica
        time_period = time_periods[0] if time_periods else "last_week"
        metric = metrics[0] if metrics else "weight"

        # Determinar el tipo de gráfico basado en la consulta
        chart_type = "line"
        if any(
            word in query.lower()
            for word in ["barra", "barras", "bar", "columna", "columnas"]
        ):
            chart_type = "bar"

        # Generar la descripción de la visualización
        visualization_response = await self._generate_response(
            prompt=f"""
            Como analista de datos especializado en visualización de progreso para programas {program_type}, 
            describe la siguiente visualización:
            
            CONSULTA DEL USUARIO:
            {query}
            
            USUARIO:
            ID: {user_id}
            Perfil: {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            MÉTRICA A VISUALIZAR:
            {metric}
            
            PERIODO DE TIEMPO:
            {time_period}
            
            TIPO DE GRÁFICO:
            {chart_type}
            
            Proporciona una descripción detallada de la visualización que incluya:
            1. Tendencias visibles en el gráfico
            2. Patrones identificados
            3. Interpretación de los datos para el programa {program_type}
            4. Recomendaciones basadas en la visualización
            """,
            context=context,
        )

        # Simular URL de visualización (en una implementación real, se generaría un gráfico)
        visualization_url = f"https://example.com/visualizations/{user_id}_{metric}_{time_period}_{int(time.time())}.png"

        # Actualizar el contexto con la nueva visualización
        if "progress_visualizations" not in context:
            context["progress_visualizations"] = []

        context["progress_visualizations"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "metric": metric,
                "time_period": time_period,
                "chart_type": chart_type,
                "program_type": program_type,
                "visualization_url": visualization_url,
                "description": visualization_response,
            }
        )

        # Actualizar métricas rastreadas
        if "metrics_tracked" not in context:
            context["metrics_tracked"] = []

        if metric not in context["metrics_tracked"]:
            context["metrics_tracked"].append(metric)

        return {
            "response": visualization_response,
            "visualization_url": visualization_url,
            "context": context,
        }

    async def _handle_compare_progress(
        self,
        query: str,
        user_id: str,
        context: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
        metrics: List[str],
        time_periods: List[str],
    ) -> Dict[str, Any]:
        """
        Maneja una consulta de comparación de progreso.

        Args:
            query: Consulta del usuario
            user_id: ID del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            metrics: Métricas a comparar
            time_periods: Periodos de tiempo a comparar

        Returns:
            Dict[str, Any]: Resultado de la comparación de progreso
        """
        # Asegurarse de tener dos periodos de tiempo
        if len(time_periods) < 2:
            if len(time_periods) == 1:
                if time_periods[0] == "last_week":
                    time_periods.append("last_month")
                else:
                    time_periods.append("last_week")
            else:
                time_periods = ["last_week", "last_month"]

        period1 = time_periods[0]
        period2 = time_periods[1]

        # Generar la comparación de progreso
        comparison_response = await self._generate_response(
            prompt=f"""
            Como analista de datos especializado en comparación de progreso para programas {program_type}, 
            compara los siguientes datos de progreso:
            
            CONSULTA DEL USUARIO:
            {query}
            
            USUARIO:
            ID: {user_id}
            Perfil: {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            MÉTRICAS A COMPARAR:
            {', '.join(metrics)}
            
            PERIODOS DE TIEMPO A COMPARAR:
            Periodo 1: {period1}
            Periodo 2: {period2}
            
            Proporciona una comparación detallada que incluya:
            1. Diferencias principales entre ambos periodos
            2. Cambios porcentuales en las métricas
            3. Análisis de mejora o deterioro
            4. Recomendaciones específicas para el programa {program_type} basadas en la comparación
            """,
            context=context,
        )

        # Actualizar el contexto con la nueva comparación
        if "progress_comparisons" not in context:
            context["progress_comparisons"] = []

        context["progress_comparisons"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "metrics": metrics,
                "period1": period1,
                "period2": period2,
                "program_type": program_type,
                "comparison": comparison_response,
            }
        )

        # Actualizar métricas rastreadas
        if "metrics_tracked" not in context:
            context["metrics_tracked"] = []

        for metric in metrics:
            if metric not in context["metrics_tracked"]:
                context["metrics_tracked"].append(metric)

        return {"response": comparison_response, "context": context}

    async def _generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Genera una respuesta utilizando el modelo de lenguaje.

        Args:
            prompt: Prompt para el modelo
            context: Contexto actual

        Returns:
            str: Respuesta generada
        """
        try:
            # Llamar al cliente de Vertex AI optimizado
            response = await self.vertex_ai_client.generate_content(
                prompt=prompt, temperature=0.7, max_output_tokens=1024
            )

            # Extraer el texto de la respuesta
            return response["text"]
        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}", exc_info=True)
            return f"Error al generar respuesta: {str(e)}"

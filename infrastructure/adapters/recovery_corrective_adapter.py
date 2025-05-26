"""
Adaptador para el agente RecoveryCorrective que utiliza los componentes optimizados.

Este adaptador extiende el agente RecoveryCorrective original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

import time
from typing import Dict, Any
from datetime import datetime

from agents.recovery_corrective.agent import RecoveryCorrective
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from core.telemetry_adapter import telemetry_adapter
from core.logging_config import get_logger
from clients.vertex_ai_client_adapter import vertex_ai_client

# Configurar logger
logger = get_logger(__name__)


class RecoveryCorrectiveAdapter(RecoveryCorrective, BaseAgentAdapter):
    """
    Adaptador para el agente RecoveryCorrective que utiliza los componentes optimizados.

    Este adaptador extiende el agente RecoveryCorrective original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """

    def __init__(self, *args, **kwargs):
        """
        Inicializa el adaptador del RecoveryCorrective.

        Args:
            *args: Argumentos posicionales para la clase base
            **kwargs: Argumentos de palabras clave para la clase base
        """
        super().__init__(*args, **kwargs)

        # Configuración de clasificación específica para este agente
        self.fallback_keywords = [
            "lesión",
            "injury",
            "dolor",
            "pain",
            "recuperación",
            "recovery",
            "rehabilitación",
            "rehabilitation",
            "movilidad",
            "mobility",
            "ejercicio",
            "exercise",
            "terapia",
            "therapy",
            "corrección",
            "correction",
        ]

        self.excluded_keywords = [
            "nutrición",
            "nutrition",
            "dieta",
            "diet",
            "entrenamiento",
            "training",
            "programa",
            "program",
            "plan",
            "schedule",
        ]

        # Métricas de telemetría
        self.metrics = {
            "queries_processed": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_processing_time": 0,
            "total_processing_time": 0,
            "query_types": {},
        }

        logger.info(f"Adaptador del RecoveryCorrective inicializado: {self.agent_id}")

    async def initialize(self) -> bool:
        """
        Inicializa el adaptador y registra el agente con el servidor A2A.

        Returns:
            bool: True si la inicialización fue exitosa
        """
        try:
            # Registrar el agente con el servidor A2A
            await self._register_with_a2a_server()

            # Inicializar componentes
            await intent_analyzer_adapter.initialize()
            await state_manager_adapter.initialize()

            logger.info(
                f"Adaptador del RecoveryCorrective inicializado correctamente: {self.agent_id}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error al inicializar el adaptador del RecoveryCorrective: {e}",
                exc_info=True,
            )
            return False

    async def _register_with_a2a_server(self) -> None:
        """
        Registra el agente con el servidor A2A optimizado.
        """
        try:
            # Crear función de callback para recibir mensajes
            async def message_handler(message: Dict[str, Any]) -> Dict[str, Any]:
                try:
                    # Extraer información del mensaje
                    user_input = message.get("user_input", "")
                    context = message.get("context", {})
                    user_id = context.get("user_id", "anonymous")
                    session_id = context.get("session_id", "")

                    # Procesar la consulta
                    response = await self.run_async_impl(
                        query=user_input,
                        user_id=user_id,
                        session_id=session_id,
                        context=context,
                    )

                    return response
                except Exception as e:
                    logger.error(f"Error en message_handler: {e}", exc_info=True)
                    return {
                        "status": "error",
                        "error": str(e),
                        "output": "Lo siento, ha ocurrido un error al procesar tu solicitud.",
                    }

            # Registrar el agente con el adaptador A2A
            a2a_adapter.register_agent(
                agent_id=self.agent_id,
                agent_info={
                    "name": self.name,
                    "description": self.description,
                    "message_callback": message_handler,
                },
            )

            logger.info(
                f"Agente RecoveryCorrective registrado con el servidor A2A: {self.agent_id}"
            )
        except Exception as e:
            logger.error(
                f"Error al registrar el agente RecoveryCorrective con el servidor A2A: {e}",
                exc_info=True,
            )
            raise

    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente RecoveryCorrective.

        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "injury_assessments": [],
            "recovery_plans": [],
            "mobility_exercises": [],
            "last_updated": datetime.now().isoformat(),
        }

    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para RecoveryCorrective.

        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "injury": "assess_injury",
            "pain": "assess_pain",
            "mobility": "improve_mobility",
            "recovery": "create_recovery_plan",
            "exercise": "recommend_exercises",
            "rehabilitation": "rehabilitation_protocol",
        }

    def _adjust_score_based_on_context(
        self, score: float, context: Dict[str, Any]
    ) -> float:
        """
        Ajusta la puntuación de clasificación basada en el contexto.

        Args:
            score: Puntuación de clasificación original
            context: Contexto adicional para la clasificación

        Returns:
            float: Puntuación ajustada
        """
        # Puntuación base
        adjusted_score = score

        # Si hay evaluaciones de lesiones o planes de recuperación previos, aumentar la puntuación
        if context.get("injury_assessments") or context.get("recovery_plans"):
            adjusted_score += 0.15

        # Si hay ejercicios de movilidad previos, aumentar la puntuación
        if context.get("mobility_exercises"):
            adjusted_score += 0.1

        # Si el contexto menciona lesiones o dolor, aumentar la puntuación
        if context.get("mentions_injury", False) or context.get("mentions_pain", False):
            adjusted_score += 0.2

        # Limitar la puntuación máxima a 1.0
        return min(1.0, adjusted_score)

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

        Este método implementa la lógica específica del RecoveryCorrective utilizando la funcionalidad
        de la clase base BaseAgentAdapter.

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
            # Iniciar span de telemetría
            span = telemetry_adapter.start_span("recovery_corrective.process_query")

            # Incrementar contador de consultas procesadas
            self.metrics["queries_processed"] += 1

            # Registrar inicio de procesamiento
            start_time = time.time()

            # Analizar la intención para determinar el tipo de consulta
            intent_result = await intent_analyzer_adapter.analyze_intent(query)

            # Determinar el tipo de consulta basado en la intención
            query_type = self._determine_query_type(intent_result, query)

            # Registrar distribución de tipos de consulta
            self.metrics["query_types"][query_type] = (
                self.metrics["query_types"].get(query_type, 0) + 1
            )

            # Registrar información de telemetría
            telemetry_adapter.set_span_attribute(span, "query_type", query_type)
            telemetry_adapter.set_span_attribute(span, "user_id", user_id)
            telemetry_adapter.set_span_attribute(span, "session_id", session_id)

            # Procesar según el tipo de consulta
            if query_type == "assess_injury":
                result = self._assess_injury(query, state)
            elif query_type == "assess_pain":
                result = self._assess_pain(query, state)
            elif query_type == "improve_mobility":
                result = self._improve_mobility(query, state)
            elif query_type == "create_recovery_plan":
                result = self._create_recovery_plan(query, state)
            elif query_type == "recommend_exercises":
                result = self._recommend_exercises(query, state)
            elif query_type == "rehabilitation_protocol":
                result = self._create_rehabilitation_protocol(query, state)
            else:
                # Tipo de consulta no reconocido, usar procesamiento genérico
                result = self._process_generic_query(query, state)

            # Calcular tiempo de procesamiento
            end_time = time.time()
            processing_time = end_time - start_time

            # Actualizar métricas
            self.metrics["successful_queries"] += 1
            self.metrics["total_processing_time"] += processing_time
            self.metrics["average_processing_time"] = (
                self.metrics["total_processing_time"]
                / self.metrics["successful_queries"]
            )

            # Registrar información de telemetría
            telemetry_adapter.set_span_attribute(
                span, "processing_time", processing_time
            )
            telemetry_adapter.set_span_attribute(span, "success", True)

            # Finalizar span de telemetría
            telemetry_adapter.end_span(span)

            # Preparar respuesta final
            response = {
                "status": "success",
                "output": result.get("response", ""),
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "query_type": query_type,
                "processing_time": processing_time,
            }

            return response

        except Exception as e:
            # Incrementar contador de consultas fallidas
            self.metrics["failed_queries"] += 1

            # Registrar error en telemetría
            if "span" in locals():
                telemetry_adapter.set_span_attribute(span, "error", str(e))
                telemetry_adapter.set_span_attribute(span, "success", False)
                telemetry_adapter.end_span(span)

            logger.error(f"Error en _process_query: {e}", exc_info=True)

            # Devolver respuesta de error
            return {
                "status": "error",
                "error": str(e),
                "output": "Lo siento, ha ocurrido un error al procesar tu solicitud.",
                "agent_id": self.agent_id,
                "agent_name": self.name,
            }

    def _determine_query_type(self, intent_result: Dict[str, Any], query: str) -> str:
        """
        Determina el tipo de consulta basado en la intención y el texto.

        Args:
            intent_result: Resultado del análisis de intención
            query: Consulta del usuario

        Returns:
            str: Tipo de consulta determinado
        """
        # Obtener el mapeo de intenciones a tipos de consulta
        intent_mapping = self._get_intent_to_query_type_mapping()

        # Verificar si hay una intención reconocida
        if intent_result and len(intent_result) > 0:
            intent = intent_result[0]
            intent_type = intent.intent_type.lower()

            # Buscar en el mapeo
            for key, query_type in intent_mapping.items():
                if key in intent_type:
                    return query_type

        # Si no se encuentra una intención específica, determinar por palabras clave
        query_lower = query.lower()

        if "lesión" in query_lower or "injury" in query_lower:
            return "assess_injury"
        elif "dolor" in query_lower or "pain" in query_lower:
            return "assess_pain"
        elif "movilidad" in query_lower or "mobility" in query_lower:
            return "improve_mobility"
        elif "recuperación" in query_lower or "recovery" in query_lower:
            return "create_recovery_plan"
        elif "ejercicio" in query_lower or "exercise" in query_lower:
            return "recommend_exercises"
        elif "rehabilitación" in query_lower or "rehabilitation" in query_lower:
            return "rehabilitation_protocol"

        # Valor por defecto
        return "generic_query"

    def _generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Genera una respuesta utilizando el cliente Vertex AI optimizado.

        Args:
            prompt: Prompt para generar la respuesta
            context: Contexto adicional

        Returns:
            str: Respuesta generada
        """
        try:
            # Construir el prompt completo con contexto
            full_prompt = self._build_prompt_with_context(prompt, context)

            # Generar respuesta utilizando el cliente Vertex AI optimizado
            response = vertex_ai_client.generate_text(
                prompt=full_prompt, max_tokens=1024, temperature=0.7, model="gemini-pro"
            )

            return response
        except Exception as e:
            logger.error(f"Error al generar respuesta: {e}", exc_info=True)
            return f"Lo siento, ha ocurrido un error al generar la respuesta: {str(e)}"

    def _build_prompt_with_context(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Construye un prompt completo incluyendo el contexto relevante.

        Args:
            prompt: Prompt base
            context: Contexto para incluir

        Returns:
            str: Prompt completo con contexto
        """
        # Iniciar con el prompt base
        full_prompt = (
            f"Como especialista en recuperación y corrección de lesiones, {prompt}\n\n"
        )

        # Añadir información del perfil del usuario si está disponible
        if "user_profile" in context and context["user_profile"]:
            profile = context["user_profile"]
            full_prompt += "Información del usuario:\n"

            if "age" in profile:
                full_prompt += f"- Edad: {profile['age']}\n"
            if "gender" in profile:
                full_prompt += f"- Género: {profile['gender']}\n"
            if "fitness_level" in profile:
                full_prompt += (
                    f"- Nivel de condición física: {profile['fitness_level']}\n"
                )
            if "medical_conditions" in profile:
                full_prompt += f"- Condiciones médicas: {', '.join(profile['medical_conditions'])}\n"

            full_prompt += "\n"

        # Añadir evaluaciones de lesiones previas si están disponibles
        if "injury_assessments" in context and context["injury_assessments"]:
            # Tomar solo la evaluación más reciente para no sobrecargar el prompt
            latest_assessment = context["injury_assessments"][-1]
            full_prompt += (
                f"Evaluación de lesión previa ({latest_assessment['date']}):\n"
            )
            full_prompt += f"{latest_assessment['assessment']}\n\n"

        # Añadir planes de recuperación previos si están disponibles
        if "recovery_plans" in context and context["recovery_plans"]:
            # Tomar solo el plan más reciente
            latest_plan = context["recovery_plans"][-1]
            full_prompt += f"Plan de recuperación previo ({latest_plan['date']}):\n"
            full_prompt += f"{latest_plan['plan']}\n\n"

        return full_prompt

    def _assess_injury(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa una lesión basada en la consulta del usuario.

        Args:
            query: Consulta del usuario
            context: Contexto actual del agente

        Returns:
            Dict[str, Any]: Resultado de la evaluación
        """
        # Implementación específica para evaluar lesiones
        assessment = self._generate_response(
            prompt=f"Evalúa la siguiente lesión y proporciona un análisis detallado: {query}",
            context=context,
        )

        # Actualizar el contexto con la nueva evaluación
        if "injury_assessments" not in context:
            context["injury_assessments"] = []

        context["injury_assessments"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "assessment": assessment,
            }
        )

        return {"response": assessment, "context": context}

    def _assess_pain(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa el dolor basado en la consulta del usuario.

        Args:
            query: Consulta del usuario
            context: Contexto actual del agente

        Returns:
            Dict[str, Any]: Resultado de la evaluación
        """
        # Implementación específica para evaluar dolor
        assessment = self._generate_response(
            prompt=f"Evalúa el siguiente dolor y proporciona un análisis detallado: {query}",
            context=context,
        )

        # Actualizar el contexto con la nueva evaluación
        if "pain_assessments" not in context:
            context["pain_assessments"] = []

        context["pain_assessments"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "assessment": assessment,
            }
        )

        return {"response": assessment, "context": context}

    def _improve_mobility(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera recomendaciones para mejorar la movilidad.

        Args:
            query: Consulta del usuario
            context: Contexto actual del agente

        Returns:
            Dict[str, Any]: Resultado con recomendaciones
        """
        # Implementación específica para mejorar movilidad
        recommendations = self._generate_response(
            prompt=f"Proporciona ejercicios y recomendaciones para mejorar la movilidad en base a: {query}",
            context=context,
        )

        # Actualizar el contexto con las nuevas recomendaciones
        if "mobility_exercises" not in context:
            context["mobility_exercises"] = []

        context["mobility_exercises"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "recommendations": recommendations,
            }
        )

        return {"response": recommendations, "context": context}

    def _create_recovery_plan(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Crea un plan de recuperación personalizado.

        Args:
            query: Consulta del usuario
            context: Contexto actual del agente

        Returns:
            Dict[str, Any]: Plan de recuperación
        """
        # Implementación específica para crear plan de recuperación
        plan = self._generate_response(
            prompt=f"Crea un plan de recuperación detallado para: {query}",
            context=context,
        )

        # Actualizar el contexto con el nuevo plan
        if "recovery_plans" not in context:
            context["recovery_plans"] = []

        context["recovery_plans"].append(
            {"date": datetime.now().isoformat(), "query": query, "plan": plan}
        )

        return {"response": plan, "context": context}

    def _recommend_exercises(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recomienda ejercicios específicos basados en la consulta.

        Args:
            query: Consulta del usuario
            context: Contexto actual del agente

        Returns:
            Dict[str, Any]: Recomendaciones de ejercicios
        """
        # Implementación específica para recomendar ejercicios
        exercises = self._generate_response(
            prompt=f"Recomienda ejercicios específicos para: {query}", context=context
        )

        # Actualizar el contexto con los nuevos ejercicios
        if "recommended_exercises" not in context:
            context["recommended_exercises"] = []

        context["recommended_exercises"].append(
            {"date": datetime.now().isoformat(), "query": query, "exercises": exercises}
        )

        return {"response": exercises, "context": context}

    def _create_rehabilitation_protocol(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Crea un protocolo de rehabilitación personalizado.

        Args:
            query: Consulta del usuario
            context: Contexto actual del agente

        Returns:
            Dict[str, Any]: Protocolo de rehabilitación
        """
        # Implementación específica para crear protocolo de rehabilitación
        protocol = self._generate_response(
            prompt=f"Crea un protocolo de rehabilitación detallado para: {query}",
            context=context,
        )

        # Actualizar el contexto con el nuevo protocolo
        if "rehabilitation_protocols" not in context:
            context["rehabilitation_protocols"] = []

        context["rehabilitation_protocols"].append(
            {"date": datetime.now().isoformat(), "query": query, "protocol": protocol}
        )

        return {"response": protocol, "context": context}

    def _process_generic_query(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Procesa una consulta genérica cuando no se identifica un tipo específico.

        Args:
            query: Consulta del usuario
            context: Contexto actual del agente

        Returns:
            Dict[str, Any]: Resultado del procesamiento
        """
        # Implementación para consultas genéricas
        response = self._generate_response(
            prompt=f"Como especialista en recuperación y corrección, responde a la siguiente consulta: {query}",
            context=context,
        )

        return {"response": response, "context": context}

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas de rendimiento del adaptador.

        Returns:
            Dict[str, Any]: Métricas de rendimiento
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "metrics": self.metrics,
        }


# Crear instancia del adaptador
recovery_corrective_adapter = RecoveryCorrectiveAdapter()


# Función para inicializar el adaptador
async def initialize_recovery_corrective_adapter():
    """
    Inicializa el adaptador del RecoveryCorrective y lo registra con el servidor A2A optimizado.
    """
    try:
        await recovery_corrective_adapter.initialize()
        logger.info(
            "Adaptador del RecoveryCorrective inicializado y registrado correctamente."
        )
    except Exception as e:
        logger.error(
            f"Error al inicializar el adaptador del RecoveryCorrective: {e}",
            exc_info=True,
        )

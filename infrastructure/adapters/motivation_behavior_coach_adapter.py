"""
Adaptador para el agente MotivationBehaviorCoach que utiliza los componentes optimizados.

Este adaptador extiende el agente MotivationBehaviorCoach original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from agents.motivation_behavior_coach.agent import MotivationBehaviorCoach
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.telemetry import get_telemetry
from clients.vertex_ai.client import VertexAIClient

# Configurar logger
logger = logging.getLogger(__name__)


class MotivationBehaviorCoachAdapter(MotivationBehaviorCoach, BaseAgentAdapter):
    """
    Adaptador para el agente MotivationBehaviorCoach que utiliza los componentes optimizados.

    Este adaptador extiende el agente MotivationBehaviorCoach original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """

    def __init__(self):
        """
        Inicializa el adaptador MotivationBehaviorCoach.
        """
        super().__init__()
        self.telemetry = get_telemetry()
        self.agent_name = "motivation_behavior_coach"
        self.vertex_ai_client = VertexAIClient()

        # Configuración de clasificación
        self.fallback_keywords = [
            "motivación",
            "motivation",
            "hábito",
            "habit",
            "comportamiento",
            "behavior",
            "cambio",
            "change",
            "meta",
            "goal",
            "objetivo",
            "objective",
            "obstáculo",
            "obstacle",
            "barrera",
            "barrier",
            "psicología",
            "psychology",
            "mentalidad",
            "mindset",
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
        Crea un contexto predeterminado para el agente MotivationBehaviorCoach.

        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "habit_plans": [],
            "goal_plans": [],
            "motivation_strategies": [],
            "behavior_change_plans": [],
            "obstacle_management_plans": [],
            "last_updated": datetime.now().isoformat(),
        }

    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para MotivationBehaviorCoach.

        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "hábito": "habit_formation",
            "habit": "habit_formation",
            "rutina": "habit_formation",
            "routine": "habit_formation",
            "motivación": "motivation_strategies",
            "motivation": "motivation_strategies",
            "inspiración": "motivation_strategies",
            "inspiration": "motivation_strategies",
            "comportamiento": "behavior_change",
            "behavior": "behavior_change",
            "cambio": "behavior_change",
            "change": "behavior_change",
            "meta": "goal_setting",
            "goal": "goal_setting",
            "objetivo": "goal_setting",
            "objective": "goal_setting",
            "obstáculo": "obstacle_management",
            "obstacle": "obstacle_management",
            "barrera": "obstacle_management",
            "barrier": "obstacle_management",
            "problema": "obstacle_management",
            "problem": "obstacle_management",
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
                f"MotivationBehaviorCoachAdapter procesando consulta de tipo: {query_type}"
            )

            # Obtener o crear el contexto
            context = state.get("motivation_context", self._create_default_context())

            # Procesar según el tipo de consulta
            if query_type == "habit_formation":
                result = await self._handle_habit_formation(
                    query, context, profile, program_type
                )
            elif query_type == "motivation_strategies":
                result = await self._handle_motivation_strategies(
                    query, context, profile, program_type
                )
            elif query_type == "behavior_change":
                result = await self._handle_behavior_change(
                    query, context, profile, program_type
                )
            elif query_type == "goal_setting":
                result = await self._handle_goal_setting(
                    query, context, profile, program_type
                )
            elif query_type == "obstacle_management":
                result = await self._handle_obstacle_management(
                    query, context, profile, program_type
                )
            else:
                # Tipo de consulta no reconocido, usar procesamiento genérico
                result = await self._handle_generic_query(
                    query, context, profile, program_type
                )

            # Actualizar el contexto en el estado
            state["motivation_context"] = context

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

            return response

        except Exception as e:
            logger.error(
                f"Error al procesar consulta en MotivationBehaviorCoachAdapter: {str(e)}",
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

        # Si no se encuentra un tipo específico, devolver formación de hábitos por defecto
        return "habit_formation"

    async def _handle_habit_formation(
        self,
        query: str,
        context: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Maneja una consulta de formación de hábitos.

        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Resultado del plan de hábitos
        """
        # Generar el plan de hábitos
        habit_plan_response = await self._generate_response(
            prompt=f"""
            Como experto en formación de hábitos y cambio de comportamiento, genera un plan estructurado para desarrollar un nuevo hábito basado en la siguiente información:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            Crea un plan estructurado para desarrollar este hábito siguiendo el modelo de las 3R (Recordatorio, Rutina, Recompensa).
            Proporciona un análisis detallado, 3 estrategias específicas con pasos de implementación,
            recomienda la estrategia más adecuada y ofrece 3 consejos para el éxito a largo plazo.
            Asegúrate de que las estrategias estén respaldadas por la ciencia y clasifica su dificultad (Baja, Media, Alta).
            """,
            context=context,
        )

        # Actualizar el contexto con el nuevo plan de hábitos
        if "habit_plans" not in context:
            context["habit_plans"] = []

        context["habit_plans"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "plan": habit_plan_response,
                "program_type": program_type,
            }
        )

        return {"response": habit_plan_response, "context": context}

    async def _handle_motivation_strategies(
        self,
        query: str,
        context: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Maneja una consulta de estrategias de motivación.

        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Resultado de las estrategias de motivación
        """
        # Generar las estrategias de motivación
        motivation_response = await self._generate_response(
            prompt=f"""
            Como experto en motivación y cambio de comportamiento, genera estrategias de motivación personalizadas basadas en la siguiente información:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            El resultado debe incluir:
            1. Análisis motivacional de la situación específico para el programa {program_type}
            2. Lista de estrategias de motivación aplicables (mínimo 3) adaptadas al programa {program_type}
            3. Prácticas diarias recomendadas para mantener la motivación en este programa
            4. Enfoque a largo plazo para sostener el progreso
            
            Para cada estrategia, incluye:
            - Nombre de la estrategia
            - Descripción detallada
            - Pasos para implementarla
            - Ciencia detrás de la estrategia
            - Ejemplo de aplicación específico para el programa {program_type}
            """,
            context=context,
        )

        # Actualizar el contexto con las nuevas estrategias de motivación
        if "motivation_strategies" not in context:
            context["motivation_strategies"] = []

        context["motivation_strategies"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "strategies": motivation_response,
                "program_type": program_type,
            }
        )

        return {"response": motivation_response, "context": context}

    async def _handle_behavior_change(
        self,
        query: str,
        context: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Maneja una consulta de cambio de comportamiento.

        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Resultado del plan de cambio de comportamiento
        """
        # Generar el plan de cambio de comportamiento
        behavior_change_response = await self._generate_response(
            prompt=f"""
            Como experto en cambio de comportamiento, genera un plan personalizado basado en la siguiente información:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            El resultado debe incluir:
            1. Comportamiento objetivo a cambiar
            2. Estado actual del comportamiento
            3. Estado deseado del comportamiento
            4. Etapas del cambio (mínimo 3)
            5. Técnicas psicológicas recomendadas
            6. Ajustes ambientales recomendados
            7. Sistemas de apoyo recomendados
            8. Línea de tiempo estimada
            9. Factores que afectan la probabilidad de éxito
            
            Para cada etapa, incluye:
            - Nombre de la etapa
            - Descripción detallada
            - Estrategias específicas
            - Duración estimada
            - Indicadores de éxito
            """,
            context=context,
        )

        # Actualizar el contexto con el nuevo plan de cambio de comportamiento
        if "behavior_change_plans" not in context:
            context["behavior_change_plans"] = []

        context["behavior_change_plans"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "plan": behavior_change_response,
                "program_type": program_type,
            }
        )

        return {"response": behavior_change_response, "context": context}

    async def _handle_goal_setting(
        self,
        query: str,
        context: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Maneja una consulta de establecimiento de metas.

        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Resultado del plan de metas
        """
        # Generar el plan de metas
        goal_setting_response = await self._generate_response(
            prompt=f"""
            Como experto en establecimiento de metas, genera un plan estructurado basado en la siguiente información:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            El plan debe incluir:
            1. Meta principal (siguiendo el formato SMART)
            2. Razón profunda o propósito de la meta
            3. Submetas o hitos intermedios
            4. Cronograma con fechas específicas
            5. Recursos necesarios
            6. Posibles obstáculos y estrategias para superarlos
            7. Sistema de seguimiento del progreso
            """,
            context=context,
        )

        # Actualizar el contexto con el nuevo plan de metas
        if "goal_plans" not in context:
            context["goal_plans"] = []

        context["goal_plans"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "plan": goal_setting_response,
                "program_type": program_type,
            }
        )

        return {"response": goal_setting_response, "context": context}

    async def _handle_obstacle_management(
        self,
        query: str,
        context: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Maneja una consulta de manejo de obstáculos.

        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Resultado del plan de manejo de obstáculos
        """
        # Generar el plan de manejo de obstáculos
        obstacle_management_response = await self._generate_response(
            prompt=f"""
            Como experto en manejo de obstáculos y superación de barreras, genera un plan personalizado basado en la siguiente información:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            El resultado debe incluir:
            1. Análisis del obstáculo (naturaleza, impacto, frecuencia, desencadenantes, intentos previos)
            2. Solución principal (estrategia, implementación, resultado esperado, enfoques alternativos, recursos necesarios)
            3. Soluciones alternativas (mínimo 2)
            4. Estrategias de prevención
            5. Ajustes de mentalidad recomendados
            """,
            context=context,
        )

        # Actualizar el contexto con el nuevo plan de manejo de obstáculos
        if "obstacle_management_plans" not in context:
            context["obstacle_management_plans"] = []

        context["obstacle_management_plans"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "plan": obstacle_management_response,
                "program_type": program_type,
            }
        )

        return {"response": obstacle_management_response, "context": context}

    async def _handle_generic_query(
        self,
        query: str,
        context: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Maneja una consulta genérica.

        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Resultado de la respuesta genérica
        """
        # Generar respuesta genérica
        generic_response = await self._generate_response(
            prompt=f"""
            Como coach especializado en motivación y cambio de comportamiento, responde a la siguiente consulta:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            Proporciona una respuesta detallada, basada en principios de psicología positiva, ciencia del comportamiento y técnicas de coaching validadas.
            Incluye ejemplos prácticos y recomendaciones específicas cuando sea apropiado.
            """,
            context=context,
        )

        # Actualizar el historial de conversación
        if "conversation_history" not in context:
            context["conversation_history"] = []

        context["conversation_history"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "response": generic_response,
            }
        )

        return {"response": generic_response, "context": context}

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

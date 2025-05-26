"""
Adaptador para el agente EliteTrainingStrategist que utiliza los componentes optimizados.

Este adaptador extiende el agente EliteTrainingStrategist original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

from typing import Dict, Any
from datetime import datetime

from agents.elite_training_strategist.agent import EliteTrainingStrategist
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.logging_config import get_logger
from clients.vertex_ai.client import VertexAIClient

# Configurar logger
logger = get_logger(__name__)


class EliteTrainingStrategistAdapter(EliteTrainingStrategist, BaseAgentAdapter):
    """
    Adaptador para el agente EliteTrainingStrategist que utiliza los componentes optimizados.

    Este adaptador extiende el agente EliteTrainingStrategist original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """

    def __init__(self, *args, **kwargs):
        """
        Inicializa el adaptador del EliteTrainingStrategist.

        Args:
            *args: Argumentos posicionales para la clase base
            **kwargs: Argumentos de palabras clave para la clase base
        """
        super().__init__(*args, **kwargs)
        self.vertex_ai_client = VertexAIClient()

        # Configuración de clasificación específica para este agente
        self.fallback_keywords = [
            "entrenamiento",
            "training",
            "ejercicio",
            "exercise",
            "rutina",
            "routine",
            "programa",
            "program",
            "intensidad",
            "intensity",
            "volumen",
            "volume",
            "periodización",
            "periodization",
            "rendimiento",
            "performance",
        ]

        self.excluded_keywords = [
            "nutrición",
            "nutrition",
            "dieta",
            "diet",
            "suplemento",
            "supplement",
            "lesión",
            "injury",
            "recuperación",
            "recovery",
        ]

    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente EliteTrainingStrategist.

        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "training_plans": [],
            "performance_data": {},
            "last_updated": datetime.now().isoformat(),
        }

    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para EliteTrainingStrategist.

        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "training_plan": "generate_training_plan",
            "adapt_program": "adapt_training_program",
            "performance_analysis": "analyze_performance_data",
            "intensity_volume": "set_training_intensity_volume",
            "exercise_routine": "prescribe_exercise_routines",
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
        # Verificar si hay un perfil de usuario con información de entrenamiento
        if context.get("user_profile", {}).get("training_level"):
            score += 0.1  # Aumentar la puntuación si hay información de entrenamiento

        # Verificar si hay planes de entrenamiento previos
        if context.get("training_plans") and len(context.get("training_plans", [])) > 0:
            score += (
                0.1  # Aumentar la puntuación si hay planes de entrenamiento previos
            )

        # Verificar si hay datos de rendimiento
        if (
            context.get("performance_data")
            and len(context.get("performance_data", {})) > 0
        ):
            score += 0.1  # Aumentar la puntuación si hay datos de rendimiento

        # Limitar la puntuación máxima a 1.0
        return min(1.0, score)

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

        Este método implementa la lógica específica del EliteTrainingStrategist.

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
            # Determinar el tipo de consulta
            query_type = await self._classify_query(query)
            logger.info(f"Tipo de consulta determinado: {query_type}")

            # Procesar según el tipo de consulta
            if query_type == "generate_training_plan":
                response = await self._generate_training_plan(
                    query, state, profile, program_type
                )
            elif query_type == "adapt_training_program":
                response = await self._adapt_training_program(
                    query, state, profile, program_type
                )
            elif query_type == "analyze_performance_data":
                response = await self._analyze_performance_data(
                    query, state, profile, program_type
                )
            elif query_type == "set_training_intensity_volume":
                response = await self._set_training_intensity_volume(
                    query, state, profile, program_type
                )
            elif query_type == "prescribe_exercise_routines":
                response = await self._prescribe_exercise_routines(
                    query, state, profile, program_type
                )
            else:
                # Tipo de consulta no reconocido, usar procesamiento genérico
                response = await self._process_generic_query(
                    query, state, profile, program_type
                )

            return response

        except Exception as e:
            logger.error(f"Error al procesar consulta: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": f"Lo siento, ha ocurrido un error al procesar tu consulta: {str(e)}",
                "agent": self.__class__.__name__,
            }

    async def _generate_training_plan(
        self,
        query: str,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Genera un plan de entrenamiento personalizado.

        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Plan de entrenamiento generado
        """
        # Implementación específica para generar un plan de entrenamiento
        prompt = f"""
        Como Elite Training Strategist, genera un plan de entrenamiento personalizado basado en:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        Perfil: {profile.get('training_level', 'No especificado')}
        
        Proporciona un plan detallado con:
        1. Objetivos del entrenamiento
        2. Estructura semanal
        3. Ejercicios específicos con series, repeticiones y descansos
        4. Progresión recomendada
        5. Métricas para seguimiento
        """

        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)

        # Actualizar el estado con el nuevo plan
        if "training_plans" not in state:
            state["training_plans"] = []

        state["training_plans"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "plan": response_text,
                "program_type": program_type,
            }
        )

        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__,
        }

    async def _adapt_training_program(
        self,
        query: str,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Adapta un programa de entrenamiento existente.

        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Programa adaptado
        """
        # Obtener el último plan de entrenamiento si existe
        last_plan = None
        if state.get("training_plans") and len(state["training_plans"]) > 0:
            last_plan = state["training_plans"][-1].get("plan", "")

        # Implementación específica para adaptar un programa de entrenamiento
        prompt = f"""
        Como Elite Training Strategist, adapta el programa de entrenamiento existente basado en:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        Perfil: {profile.get('training_level', 'No especificado')}
        
        {"Plan existente: " + last_plan if last_plan else "No hay plan existente, crea uno nuevo."}
        
        Proporciona un plan adaptado con:
        1. Cambios específicos y su justificación
        2. Nueva estructura semanal
        3. Ejercicios modificados con series, repeticiones y descansos
        4. Progresión recomendada
        5. Métricas para seguimiento
        """

        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)

        # Actualizar el estado con el plan adaptado
        if "training_plans" not in state:
            state["training_plans"] = []

        state["training_plans"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "plan": response_text,
                "program_type": program_type,
                "type": "adaptation",
            }
        )

        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__,
        }

    async def _analyze_performance_data(
        self,
        query: str,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Analiza datos de rendimiento del usuario.

        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Análisis de rendimiento
        """
        # Obtener datos de rendimiento si existen
        performance_data = state.get("performance_data", {})

        # Implementación específica para analizar datos de rendimiento
        prompt = f"""
        Como Elite Training Strategist, analiza los datos de rendimiento basado en:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        Perfil: {profile.get('training_level', 'No especificado')}
        
        Datos de rendimiento: {performance_data}
        
        Proporciona un análisis detallado con:
        1. Tendencias identificadas
        2. Áreas de mejora
        3. Recomendaciones específicas
        4. Comparación con estándares para el nivel del usuario
        5. Próximos objetivos recomendados
        """

        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)

        # Actualizar el estado con el análisis
        if "performance_analyses" not in state:
            state["performance_analyses"] = []

        state["performance_analyses"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "analysis": response_text,
            }
        )

        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__,
        }

    async def _set_training_intensity_volume(
        self,
        query: str,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Establece la intensidad y volumen de entrenamiento.

        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Recomendaciones de intensidad y volumen
        """
        # Implementación específica para establecer intensidad y volumen
        prompt = f"""
        Como Elite Training Strategist, establece la intensidad y volumen de entrenamiento basado en:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        Perfil: {profile.get('training_level', 'No especificado')}
        
        Proporciona recomendaciones detalladas con:
        1. Intensidad recomendada (% de 1RM, RPE, etc.)
        2. Volumen semanal (series por grupo muscular)
        3. Distribución del volumen a lo largo de la semana
        4. Estrategias de periodización
        5. Ajustes basados en la recuperación
        """

        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)

        # Actualizar el estado con las recomendaciones
        if "intensity_volume_recommendations" not in state:
            state["intensity_volume_recommendations"] = []

        state["intensity_volume_recommendations"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "recommendations": response_text,
            }
        )

        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__,
        }

    async def _prescribe_exercise_routines(
        self,
        query: str,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Prescribe rutinas de ejercicios específicas.

        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Rutinas de ejercicios prescritas
        """
        # Implementación específica para prescribir rutinas de ejercicios
        prompt = f"""
        Como Elite Training Strategist, prescribe rutinas de ejercicios específicas basado en:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        Perfil: {profile.get('training_level', 'No especificado')}
        
        Proporciona rutinas detalladas con:
        1. Ejercicios específicos para cada grupo muscular
        2. Técnica correcta de ejecución
        3. Series, repeticiones y descansos
        4. Variaciones para diferentes niveles
        5. Progresiones y regresiones
        """

        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)

        # Actualizar el estado con las rutinas
        if "exercise_routines" not in state:
            state["exercise_routines"] = []

        state["exercise_routines"].append(
            {
                "date": datetime.now().isoformat(),
                "query": query,
                "routines": response_text,
            }
        )

        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__,
        }

    async def _process_generic_query(
        self,
        query: str,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        program_type: str,
    ) -> Dict[str, Any]:
        """
        Procesa una consulta genérica cuando no se identifica un tipo específico.

        Args:
            query: Consulta del usuario
            state: Estado actual del usuario
            profile: Perfil del usuario
            program_type: Tipo de programa

        Returns:
            Dict[str, Any]: Respuesta a la consulta genérica
        """
        # Implementación para consultas genéricas
        prompt = f"""
        Como Elite Training Strategist, responde a la siguiente consulta:
        
        Consulta: {query}
        Tipo de programa: {program_type}
        Perfil: {profile.get('training_level', 'No especificado')}
        
        Proporciona una respuesta detallada y útil basada en principios de entrenamiento avanzados.
        """

        # Generar respuesta utilizando el método de la clase base
        response_text = await self._generate_response(prompt=prompt, context=state)

        return {
            "success": True,
            "response": response_text,
            "context": state,
            "agent": self.__class__.__name__,
        }

    async def _generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Genera una respuesta utilizando el cliente Vertex AI.

        Args:
            prompt: Prompt para generar la respuesta
            context: Contexto para la generación

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

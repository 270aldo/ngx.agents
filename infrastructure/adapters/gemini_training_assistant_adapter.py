"""
Adaptador para el agente GeminiTrainingAssistant que utiliza los componentes optimizados.

Este adaptador extiende el agente GeminiTrainingAssistant original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from agents.gemini_training_assistant.agent import GeminiTrainingAssistant
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.telemetry import get_telemetry
from clients.vertex_ai.client import VertexAIClient

# Configurar logger
logger = logging.getLogger(__name__)

class GeminiTrainingAssistantAdapter(GeminiTrainingAssistant, BaseAgentAdapter):
    """
    Adaptador para el agente GeminiTrainingAssistant que utiliza los componentes optimizados.
    
    Este adaptador extiende el agente GeminiTrainingAssistant original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """
    
    def __init__(self):
        """
        Inicializa el adaptador GeminiTrainingAssistant.
        """
        super().__init__()
        self.telemetry = get_telemetry()
        self.agent_name = "gemini_training_assistant"
        self.vertex_ai_client = VertexAIClient()
        
        # Configuración de clasificación
        self.fallback_keywords = [
            "entrenamiento", "training", "ejercicio", "exercise", 
            "rutina", "routine", "plan", "programa", "program",
            "fitness", "gimnasio", "gym", "deporte", "sport",
            "nutrición", "nutrition", "dieta", "diet", "alimentación",
            "progreso", "progress", "resultados", "results"
        ]
        
        self.excluded_keywords = [
            "biométricos", "biometrics", "recuperación", "recovery",
            "lesión", "injury", "médico", "medical", "doctor"
        ]
    
    def get_agent_name(self) -> str:
        """Devuelve el nombre del agente."""
        return self.agent_name
    
    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente GeminiTrainingAssistant.
        
        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "training_plans": [],
            "nutrition_recommendations": [],
            "progress_analyses": [],
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para GeminiTrainingAssistant.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "plan": "generate_training_plan",
            "entrenamiento": "generate_training_plan",
            "training": "generate_training_plan",
            "rutina": "generate_training_plan",
            "ejercicio": "generate_training_plan",
            "programa": "generate_training_plan",
            "nutrición": "recommend_nutrition",
            "nutrition": "recommend_nutrition",
            "dieta": "recommend_nutrition",
            "alimentación": "recommend_nutrition",
            "comer": "recommend_nutrition",
            "comida": "recommend_nutrition",
            "progreso": "analyze_progress",
            "progress": "analyze_progress",
            "avance": "analyze_progress",
            "resultados": "analyze_progress",
            "meseta": "analyze_progress",
            "estancamiento": "analyze_progress"
        }
    
    async def _process_query(self, query: str, user_id: str, session_id: str,
                           program_type: str, state: Dict[str, Any], profile: Dict[str, Any],
                           **kwargs) -> Dict[str, Any]:
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
                with self.telemetry.start_as_current_span(f"{self.__class__.__name__}._process_query") as span:
                    span.set_attribute("user_id", user_id)
                    span.set_attribute("session_id", session_id)
                    span.set_attribute("program_type", program_type)
            
            # Determinar el tipo de consulta basado en el mapeo de intenciones
            query_type = self._determine_query_type(query)
            logger.info(f"GeminiTrainingAssistantAdapter procesando consulta de tipo: {query_type}")
            
            # Obtener o crear el contexto
            context = state.get("training_context", self._create_default_context())
            
            # Procesar según el tipo de consulta
            if query_type == "generate_training_plan":
                result = await self._handle_training_plan(query, context, profile, program_type)
            elif query_type == "recommend_nutrition":
                result = await self._handle_nutrition_recommendation(query, context, profile, program_type)
            elif query_type == "analyze_progress":
                result = await self._handle_progress_analysis(query, context, profile, program_type)
            else:
                # Tipo de consulta no reconocido, usar procesamiento genérico
                result = await self._handle_fitness_question(query, context, profile, program_type)
            
            # Actualizar el contexto en el estado
            state["training_context"] = context
            
            # Construir la respuesta
            response = {
                "success": True,
                "output": result.get("response", "No se pudo generar una respuesta"),
                "query_type": query_type,
                "program_type": program_type,
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat(),
                "context": context
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error al procesar consulta en GeminiTrainingAssistantAdapter: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
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
        
        # Si no se encuentra un tipo específico, devolver respuesta a pregunta de fitness por defecto
        return "answer_fitness_question"
    
    async def _handle_training_plan(self, query: str, context: Dict[str, Any], 
                                  profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta de generación de plan de entrenamiento.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado del plan de entrenamiento
        """
        # Generar el plan de entrenamiento
        training_plan_response = await self._generate_response(
            prompt=f"""
            Como experto en entrenamiento físico, genera un plan de entrenamiento personalizado basado en la siguiente información:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            Proporciona un plan de entrenamiento detallado que incluya:
            1. Resumen de objetivos y enfoque
            2. Estructura semanal (días de entrenamiento y descanso)
            3. Desglose detallado de cada sesión de entrenamiento
            4. Progresión recomendada
            5. Consejos para maximizar resultados
            
            Tu plan debe ser claro, estructurado y adaptado al nivel y objetivos del usuario.
            """,
            context=context
        )
        
        # Actualizar el contexto con el nuevo plan de entrenamiento
        if "training_plans" not in context:
            context["training_plans"] = []
            
        context["training_plans"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "plan": training_plan_response,
            "program_type": program_type
        })
        
        return {
            "response": training_plan_response,
            "context": context
        }
    
    async def _handle_nutrition_recommendation(self, query: str, context: Dict[str, Any], 
                                             profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta de recomendación nutricional.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado de la recomendación nutricional
        """
        # Generar la recomendación nutricional
        nutrition_response = await self._generate_response(
            prompt=f"""
            Como experto en nutrición deportiva, genera recomendaciones nutricionales personalizadas basadas en la siguiente información:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            Proporciona recomendaciones nutricionales detalladas que incluyan:
            1. Resumen de enfoque nutricional recomendado
            2. Distribución de macronutrientes sugerida
            3. Ejemplos de comidas para diferentes momentos del día
            4. Suplementos recomendados (si aplica)
            5. Estrategias de nutrición alrededor del entrenamiento
            6. Consejos para adherencia y sostenibilidad
            
            Tus recomendaciones deben ser claras, estructuradas y adaptadas al nivel y objetivos del usuario.
            """,
            context=context
        )
        
        # Actualizar el contexto con la nueva recomendación nutricional
        if "nutrition_recommendations" not in context:
            context["nutrition_recommendations"] = []
            
        context["nutrition_recommendations"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "recommendation": nutrition_response,
            "program_type": program_type
        })
        
        return {
            "response": nutrition_response,
            "context": context
        }
    
    async def _handle_progress_analysis(self, query: str, context: Dict[str, Any], 
                                      profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta de análisis de progreso.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado del análisis de progreso
        """
        # Generar el análisis de progreso
        progress_analysis_response = await self._generate_response(
            prompt=f"""
            Como experto en entrenamiento físico, analiza el progreso basado en la siguiente información:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            CONTEXTO PREVIO:
            {context}
            
            Proporciona un análisis detallado que incluya:
            1. Evaluación del progreso actual
            2. Identificación de fortalezas y áreas de mejora
            3. Recomendaciones para ajustar el entrenamiento
            4. Proyección de progreso futuro si se mantiene la trayectoria actual
            5. Sugerencias específicas para superar mesetas o barreras
            
            Tu análisis debe ser claro, estructurado y basado en la información disponible.
            """,
            context=context
        )
        
        # Actualizar el contexto con el nuevo análisis de progreso
        if "progress_analyses" not in context:
            context["progress_analyses"] = []
            
        context["progress_analyses"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "analysis": progress_analysis_response,
            "program_type": program_type
        })
        
        return {
            "response": progress_analysis_response,
            "context": context
        }
    
    async def _handle_fitness_question(self, query: str, context: Dict[str, Any], 
                                     profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una pregunta general sobre fitness.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado de la respuesta a la pregunta
        """
        # Generar respuesta a la pregunta de fitness
        fitness_response = await self._generate_response(
            prompt=f"""
            Como experto en fitness, entrenamiento y nutrición, responde a la siguiente pregunta:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            Proporciona una respuesta detallada, precisa y basada en evidencia científica.
            Incluye ejemplos prácticos y recomendaciones específicas cuando sea apropiado.
            """,
            context=context
        )
        
        # Actualizar el historial de conversación
        if "conversation_history" not in context:
            context["conversation_history"] = []
            
        context["conversation_history"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "response": fitness_response
        })
        
        return {
            "response": fitness_response,
            "context": context
        }
    
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
                prompt=prompt,
                temperature=0.7,
                max_output_tokens=1024
            )
            
            # Extraer el texto de la respuesta
            return response["text"]
        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}", exc_info=True)
            return f"Error al generar respuesta: {str(e)}"

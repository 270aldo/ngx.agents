"""
Agente de asistencia de entrenamiento potenciado por Vertex AI Gemini.

Este agente utiliza los modelos de Gemini a través de Vertex AI para proporcionar
recomendaciones personalizadas de entrenamiento y nutrición.

Implementa los protocolos oficiales A2A y ADK para comunicación entre agentes.
"""
import logging
import json
import time
import uuid
from typing import Dict, Any, List, Optional

from adk.toolkit import Toolkit
from agents.base.a2a_agent import A2AAgent
from tools.vertex_gemini_tools import (
    VertexGeminiGenerateSkill,
    VertexGeminiChatSkill,
    VertexGeminiModelsSkill
)
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager
from clients.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class GeminiTrainingAssistant(A2AAgent):
    """
    Agente de asistencia de entrenamiento potenciado por Vertex AI Gemini.
    
    Utiliza los modelos de Gemini para proporcionar recomendaciones personalizadas
    de entrenamiento y nutrición, basadas en los objetivos y características del usuario.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None):
        """
        Inicializa el agente de asistencia de entrenamiento.
        
        Args:
            toolkit: Toolkit con herramientas disponibles para el agente
            a2a_server_url: URL del servidor A2A (opcional)
        """
        # Definir capacidades y habilidades
        capabilities = [
            "generate_training_plan",
            "recommend_nutrition",
            "answer_fitness_questions",
            "analyze_progress"
        ]
        
        skills = [
            {"name": "vertex_gemini_generate", "description": "Genera texto utilizando los modelos Gemini"},
            {"name": "vertex_gemini_chat", "description": "Mantiene conversaciones utilizando los modelos Gemini"},
            {"name": "vertex_gemini_models", "description": "Obtiene información sobre los modelos de Gemini disponibles"}
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "Necesito un plan de entrenamiento para un maratón"},
                "output": {"response": "Aquí tienes un plan de entrenamiento de 16 semanas para prepararte para un maratón..."}
            },
            {
                "input": {"message": "¿Qué debo comer antes de entrenar?"},
                "output": {"response": "Antes de entrenar, es recomendable consumir carbohidratos complejos y proteínas magras..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="gemini_training_assistant",
            name="Asistente de Entrenamiento con Gemini",
            description="Asistente de entrenamiento potenciado por Vertex AI Gemini que proporciona recomendaciones personalizadas de entrenamiento y nutrición",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.0.0",
            a2a_server_url=a2a_server_url,
            skills=skills
        )
        
        # Registrar las skills específicas de Vertex AI Gemini
        self.register_skill(VertexGeminiGenerateSkill())
        self.register_skill(VertexGeminiChatSkill())
        self.register_skill(VertexGeminiModelsSkill())
        
        # Almacenar sesiones de chat activas por usuario
        self.chat_sessions = {}
        
        # Inicializar estado del agente
        self.update_state("training_plans", {})  # Almacenar planes de entrenamiento generados
        self.update_state("nutrition_recommendations", {})  # Almacenar recomendaciones nutricionales
        self.update_state("progress_analyses", {})  # Almacenar análisis de progreso
        
        # Inicializar clientes y StateManager
        self.supabase_client = SupabaseClient()
        self.state_manager = StateManager(self.supabase_client)
        
        logger.info(f"GeminiTrainingAssistant inicializado con {len(capabilities)} capacidades")
    
    async def _handle_task(self, task_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa una tarea recibida.
        
        Args:
            task_id: ID de la tarea
            content: Contenido de la tarea
            
        Returns:
            Resultado de la tarea
        """
        try:
            # Extraer información de la tarea
            task_type = content.get("type", "")
            user_input = content.get("input", "")
            user_id = content.get("user_id", "anonymous")
            context = content.get("context", {})
            
            logger.info(f"Procesando tarea {task_id} de tipo {task_type} para usuario {user_id}")
            
            # Procesar según el tipo de tarea
            if task_type == "generate_training_plan":
                return await self._generate_training_plan(user_input, context)
            elif task_type == "recommend_nutrition":
                return await self._recommend_nutrition(user_input, context)
            elif task_type == "answer_fitness_question":
                return await self._answer_fitness_question(user_input, user_id)
            elif task_type == "analyze_progress":
                return await self._analyze_progress(user_input, context)
            else:
                # Tarea genérica o desconocida
                return await self._process_generic_task(user_input, user_id)
        except Exception as e:
            logger.error(f"Error al procesar tarea {task_id}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud."
            }
    
    async def _generate_training_plan(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un plan de entrenamiento personalizado utilizando Gemini.
        
        Args:
            user_input: Solicitud del usuario
            context: Contexto adicional (objetivos, nivel, limitaciones, etc.)
            
        Returns:
            Plan de entrenamiento generado
        """
        # Construir prompt para Gemini
        prompt = f"""Genera un plan de entrenamiento personalizado basado en la siguiente información:

Solicitud del usuario: {user_input}

"""
        # Añadir contexto si está disponible
        if context:
            if "fitness_level" in context:
                prompt += f"Nivel de condición física: {context['fitness_level']}\n"
            if "goals" in context:
                prompt += f"Objetivos: {context['goals']}\n"
            if "limitations" in context:
                prompt += f"Limitaciones o lesiones: {context['limitations']}\n"
            if "available_equipment" in context:
                prompt += f"Equipo disponible: {context['available_equipment']}\n"
            if "time_available" in context:
                prompt += f"Tiempo disponible: {context['time_available']}\n"
        
        prompt += """
Proporciona un plan de entrenamiento detallado que incluya:
1. Resumen de objetivos y enfoque
2. Estructura semanal (días de entrenamiento y descanso)
3. Desglose detallado de cada sesión de entrenamiento
4. Progresión recomendada
5. Consejos para maximizar resultados

Formato el plan de forma clara y estructurada.
"""
        
        # Ejecutar skill de generación
        generate_skill = self.registered_skills.get("vertex_gemini_generate")
        if not generate_skill:
            return {"status": "failed", "error": "Skill de generación no disponible"}
        
        result = await generate_skill.execute({
            "prompt": prompt,
            "temperature": 0.7
        })
        
        return {
            "status": "completed",
            "training_plan": result.get("text", ""),
            "model_used": result.get("model", ""),
            "execution_time": result.get("execution_time", 0)
        }
    
    async def _recommend_nutrition(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera recomendaciones nutricionales personalizadas utilizando Gemini.
        
        Args:
            user_input: Solicitud del usuario
            context: Contexto adicional (objetivos, preferencias, alergias, etc.)
            
        Returns:
            Recomendaciones nutricionales generadas
        """
        # Construir prompt para Gemini
        prompt = f"""Genera recomendaciones nutricionales personalizadas basadas en la siguiente información:

Solicitud del usuario: {user_input}

"""
        # Añadir contexto si está disponible
        if context:
            if "goals" in context:
                prompt += f"Objetivos: {context['goals']}\n"
            if "dietary_preferences" in context:
                prompt += f"Preferencias dietéticas: {context['dietary_preferences']}\n"
            if "allergies" in context:
                prompt += f"Alergias o intolerancias: {context['allergies']}\n"
            if "current_diet" in context:
                prompt += f"Dieta actual: {context['current_diet']}\n"
            if "training_regimen" in context:
                prompt += f"Régimen de entrenamiento: {context['training_regimen']}\n"
        
        prompt += """
Proporciona recomendaciones nutricionales detalladas que incluyan:
1. Resumen de enfoque nutricional recomendado
2. Distribución de macronutrientes sugerida
3. Ejemplos de comidas para diferentes momentos del día
4. Suplementos recomendados (si aplica)
5. Estrategias de nutrición alrededor del entrenamiento
6. Consejos para adherencia y sostenibilidad

Formato las recomendaciones de forma clara y estructurada.
"""
        
        # Ejecutar skill de generación
        generate_skill = self.registered_skills.get("vertex_gemini_generate")
        if not generate_skill:
            return {"status": "failed", "error": "Skill de generación no disponible"}
        
        result = await generate_skill.execute({
            "prompt": prompt,
            "temperature": 0.7
        })
        
        return {
            "status": "completed",
            "nutrition_recommendations": result.get("text", ""),
            "model_used": result.get("model", ""),
            "execution_time": result.get("execution_time", 0)
        }
    
    async def _answer_fitness_question(self, question: str, user_id: str) -> Dict[str, Any]:
        """
        Responde a preguntas sobre fitness utilizando una conversación con Gemini.
        
        Args:
            question: Pregunta del usuario
            user_id: ID del usuario para mantener la sesión
            
        Returns:
            Respuesta a la pregunta
        """
        # Obtener la sesión de chat del usuario o crear una nueva
        session_id = self.chat_sessions.get(user_id)
        
        # Ejecutar skill de chat
        chat_skill = self.registered_skills.get("vertex_gemini_chat")
        if not chat_skill:
            return {"status": "failed", "error": "Skill de chat no disponible"}
        
        result = await chat_skill.execute({
            "message": question,
            "temperature": 0.7,
            "session_id": session_id
        })
        
        # Guardar la sesión para futuras interacciones
        self.chat_sessions[user_id] = result.get("session_id")
        
        return {
            "status": "completed",
            "answer": result.get("text", ""),
            "model_used": result.get("model", ""),
            "execution_time": result.get("execution_time", 0),
            "session_id": result.get("session_id")
        }
    
    async def _analyze_progress(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza el progreso del usuario utilizando Gemini.
        
        Args:
            user_input: Solicitud del usuario
            context: Contexto adicional (métricas anteriores, objetivos, etc.)
            
        Returns:
            Análisis del progreso
        """
        # Construir prompt para Gemini
        prompt = f"""Analiza el progreso de entrenamiento basado en la siguiente información:

Solicitud del usuario: {user_input}

"""
        # Añadir contexto si está disponible
        if context:
            if "previous_metrics" in context:
                metrics = context["previous_metrics"]
                prompt += "Métricas anteriores:\n"
                for date, data in metrics.items():
                    prompt += f"- {date}: {json.dumps(data)}\n"
            if "goals" in context:
                prompt += f"Objetivos: {context['goals']}\n"
            if "training_history" in context:
                prompt += f"Historial de entrenamiento: {context['training_history']}\n"
        
        prompt += """
Proporciona un análisis detallado que incluya:
1. Evaluación del progreso actual
2. Identificación de fortalezas y áreas de mejora
3. Recomendaciones para ajustar el entrenamiento
4. Proyección de progreso futuro si se mantiene la trayectoria actual
5. Sugerencias específicas para superar mesetas o barreras

Formato el análisis de forma clara y estructurada.
"""
        
        # Ejecutar skill de generación
        generate_skill = self.registered_skills.get("vertex_gemini_generate")
        if not generate_skill:
            return {"status": "failed", "error": "Skill de generación no disponible"}
        
        result = await generate_skill.execute({
            "prompt": prompt,
            "temperature": 0.7
        })
        
        return {
            "status": "completed",
            "progress_analysis": result.get("text", ""),
            "model_used": result.get("model", ""),
            "execution_time": result.get("execution_time", 0)
        }
    
    async def _process_generic_task(self, user_input: str, user_id: str) -> Dict[str, Any]:
        """
        Procesa una tarea genérica utilizando una conversación con Gemini.
        
        Args:
            user_input: Entrada del usuario
            user_id: ID del usuario para mantener la sesión
            
        Returns:
            Respuesta generada
        """
        # Utilizar el mismo flujo que para responder preguntas
        return await self._answer_fitness_question(user_input, user_id)
        
    async def _get_context(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el StateManager.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            
        Returns:
            Dict[str, Any]: Contexto de la conversación
        """
        try:
            # Intentar cargar el contexto desde el StateManager
            context = await self.state_manager.load_state(user_id, session_id)
            
            if not context or not context.get("state_data"):
                logger.info(f"No se encontró contexto en StateManager para user_id={user_id}, session_id={session_id}. Creando nuevo contexto.")
                # Si no hay contexto, crear uno nuevo
                context = {
                    "conversation_history": [],
                    "user_profile": {},
                    "training_plans": [],
                    "nutrition_recommendations": [],
                    "progress_analyses": [],
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                # Si hay contexto, usar el state_data
                context = context.get("state_data", {})
                logger.info(f"Contexto cargado desde StateManager para user_id={user_id}, session_id={session_id}")
            
            return context
        except Exception as e:
            logger.error(f"Error al obtener contexto: {e}", exc_info=True)
            # En caso de error, devolver un contexto vacío
            return {
                "conversation_history": [],
                "user_profile": {},
                "training_plans": [],
                "nutrition_recommendations": [],
                "progress_analyses": [],
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    async def _update_context(self, context: Dict[str, Any], user_id: str, session_id: str) -> None:
        """
        Actualiza el contexto de la conversación en el StateManager.
        
        Args:
            context: Contexto actualizado
            user_id: ID del usuario
            session_id: ID de la sesión
        """
        try:
            # Actualizar la marca de tiempo
            context["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Guardar el contexto en el StateManager
            await self.state_manager.save_state(context, user_id, session_id)
            logger.info(f"Contexto actualizado en StateManager para user_id={user_id}, session_id={session_id}")
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)
    
    async def _run_async_impl(self, input_text: str, user_id: Optional[str] = None, 
                           session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Implementación asíncrona del procesamiento del agente GeminiTrainingAssistant.
        
        Sobrescribe el método de la clase base para proporcionar la implementación
        específica del agente especializado en entrenamiento con Gemini.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            **kwargs: Argumentos adicionales como context, parameters, etc.
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        try:
            start_time = time.time()
            logger.info(f"Ejecutando GeminiTrainingAssistant con input: {input_text[:50]}...")
            
            # Generar session_id si no se proporciona
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Obtener el contexto de la conversación
            context = await self._get_context(user_id, session_id) if user_id else {}
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                # Intentar obtener el perfil del usuario del contexto primero
                user_profile = context.get("user_profile", {})
                if not user_profile:
                    # Aquí se implementaría la lógica para obtener el perfil del usuario desde Supabase
                    try:
                        user_profile = self.supabase_client.get_user_profile(user_id)
                        if user_profile:
                            context["user_profile"] = user_profile
                    except Exception as e:
                        logger.warning(f"No se pudo obtener el perfil del usuario {user_id}: {e}")
            
            # Determinar el tipo de tarea basado en el input del usuario
            if "plan de entrenamiento" in input_text.lower() or "rutina" in input_text.lower():
                task_type = "generate_training_plan"
                result = await self._generate_training_plan(input_text, context)
            elif "nutrición" in input_text.lower() or "comida" in input_text.lower() or "dieta" in input_text.lower():
                task_type = "recommend_nutrition"
                result = await self._recommend_nutrition(input_text, context)
            elif "progreso" in input_text.lower() or "avance" in input_text.lower() or "resultados" in input_text.lower():
                task_type = "analyze_progress"
                result = await self._analyze_progress(input_text, context)
            else:
                task_type = "answer_question"
                result = await self._answer_fitness_question(input_text, user_id or "anonymous")
            
            # Preparar la respuesta
            artifacts = []
            
            # Procesar el resultado según el tipo de tarea
            if task_type == "generate_training_plan":
                response = result.get("training_plan", "")
                if "training_plan_structure" in result:
                    artifacts.append({
                        "type": "training_plan",
                        "content": result.get("training_plan_structure", {})
                    })
                    
                    # Guardar el plan en el contexto
                    if user_id:
                        context["training_plans"].append({
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "query": input_text,
                            "plan": result.get("training_plan_structure", {})
                        })
                    
                # Guardar el plan en el estado del agente
                if user_id:
                    plans = self.get_state("training_plans", {})
                    plans[user_id] = plans.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "plan": result.get("training_plan_structure", {})
                    }]
                    self.update_state("training_plans", plans)
                    
            elif task_type == "recommend_nutrition":
                response = result.get("nutrition_recommendations", "")
                if "nutrition_plan" in result:
                    artifacts.append({
                        "type": "nutrition_plan",
                        "content": result.get("nutrition_plan", {})
                    })
                    
                    # Guardar la recomendación en el contexto
                    if user_id:
                        context["nutrition_recommendations"].append({
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "query": input_text,
                            "recommendation": result.get("nutrition_plan", {})
                        })
                    
                # Guardar la recomendación en el estado del agente
                if user_id:
                    recommendations = self.get_state("nutrition_recommendations", {})
                    recommendations[user_id] = recommendations.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "recommendation": result.get("nutrition_plan", {})
                    }]
                    self.update_state("nutrition_recommendations", recommendations)
                    
            elif task_type == "analyze_progress":
                response = result.get("progress_analysis", "")
                if "metrics" in result:
                    artifacts.append({
                        "type": "progress_metrics",
                        "content": result.get("metrics", {})
                    })
                    
                    # Guardar el análisis en el contexto
                    if user_id:
                        context["progress_analyses"].append({
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "query": input_text,
                            "analysis": result.get("metrics", {})
                        })
                    
                # Guardar el análisis en el estado del agente
                if user_id:
                    analyses = self.get_state("progress_analyses", {})
                    analyses[user_id] = analyses.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "analysis": result.get("metrics", {})
                    }]
                    self.update_state("progress_analyses", analyses)
                    
            else:
                response = result.get("answer", "")
            
            # Añadir la interacción al historial interno del agente
            self.add_to_history(input_text, response)
            
            # Añadir la interacción al historial de conversación en el contexto
            if user_id:
                context["conversation_history"].append({
                    "user": input_text,
                    "agent": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "task_type": task_type
                })
                
                # Actualizar el contexto en el StateManager
                await self._update_context(context, user_id, session_id)
            
            # Devolver respuesta final
            return {
                "status": "success",
                "response": response,
                "artifacts": artifacts,
                "agent_id": self.agent_id,
                "metadata": {
                    "task_type": task_type,
                    "user_id": user_id,
                    "session_id": session_id,
                    "model_used": result.get("model_used", "gemini-pro")
                }
            }
            
        except Exception as e:
            logger.error(f"Error en GeminiTrainingAssistant: {e}", exc_info=True)
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud sobre entrenamiento y nutrición.",
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()

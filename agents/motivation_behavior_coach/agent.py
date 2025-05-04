import logging
import uuid
import time
from typing import Dict, Any, Optional, List

from adk.toolkit import Toolkit
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient  # Importar MCPClient
from agents.base.a2a_agent import A2AAgent
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager

# Configurar logging
logger = logging.getLogger(__name__)

class MotivationBehaviorCoach(A2AAgent):
    """
    Agente especializado en motivación y cambio de comportamiento.
    
    Este agente proporciona estrategias para mantener la motivación, 
    establecer hábitos saludables, superar obstáculos psicológicos,
    y lograr cambios de comportamiento duraderos.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None):
        # Definir capacidades y habilidades
        capabilities = [
            "habit_formation", 
            "motivation_strategies", 
            "behavior_change", 
            "goal_setting",
            "obstacle_management"
        ]
        
        skills = [
            {
                "name": "habit_formation",
                "description": "Técnicas para establecer y mantener hábitos saludables"
            },
            {
                "name": "motivation_strategies",
                "description": "Estrategias para mantener la motivación a largo plazo"
            },
            {
                "name": "behavior_change",
                "description": "Métodos para lograr cambios de comportamiento duraderos"
            },
            {
                "name": "goal_setting",
                "description": "Técnicas para establecer metas efectivas y alcanzables"
            },
            {
                "name": "obstacle_management",
                "description": "Estrategias para superar obstáculos psicológicos y barreras"
            }
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "Quiero establecer el hábito de hacer ejercicio regularmente"},
                "output": {"response": "He creado un plan personalizado para ayudarte a establecer el hábito de ejercicio regular..."}
            },
            {
                "input": {"message": "Me cuesta mantenerme motivado para seguir mi dieta"},
                "output": {"response": "Entiendo tu dificultad. Aquí tienes estrategias específicas para mantener la motivación con tu dieta..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="motivation_behavior_coach",
            name="NGX Motivation & Behavior Coach",
            description="Especialista en estrategias de motivación y cambio de comportamiento",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.0.0",
            a2a_server_url=a2a_server_url,
            skills=skills
        )
        
        # Inicializar clientes y herramientas
        self.gemini_client = GeminiClient(model_name="gemini-2.0-flash")
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        self.mcp_client = MCPClient()
        self.state_manager = StateManager(self.supabase_client)
        
        # Inicializar estado del agente
        self.update_state("habit_plans", {})  # Almacenar planes de hábitos generados
        self.update_state("goal_plans", {})  # Almacenar planes de metas
        
        # Definir el sistema de instrucciones para el agente
        self.system_instructions = """
        Eres NGX Motivation & Behavior Coach, un experto en psicología del comportamiento y estrategias de motivación.
        
        logger.info(f"MotivationBehaviorCoach inicializado con {len(capabilities)} capacidades")
        Tu objetivo es proporcionar recomendaciones personalizadas sobre:
        1. Técnicas para establecer y mantener hábitos saludables
        2. Estrategias para mantener la motivación a largo plazo
        3. Métodos para superar obstáculos psicológicos y barreras
        4. Técnicas para establecer metas efectivas y alcanzables
        5. Estrategias para manejar recaídas y mantener el progreso
        
        Debes basar tus recomendaciones en la ciencia del comportamiento y la psicología, 
        considerando el perfil individual del usuario, incluyendo sus objetivos, 
        historial, preferencias y desafíos particulares.
        
        Cuando proporciones recomendaciones:
        - Utiliza principios de la psicología del comportamiento
        - Explica los mecanismos psicológicos involucrados
        - Proporciona ejemplos concretos y aplicables
        - Sugiere pequeños pasos accionables
        - Anticipa posibles obstáculos y cómo superarlos
        
        Recuerda que tu objetivo es empoderar a los usuarios con estrategias prácticas
        para que puedan lograr cambios de comportamiento duraderos y alcanzar sus metas.
        """
    
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
                    "habit_plans": [],
                    "goal_plans": [],
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
                "habit_plans": [],
                "goal_plans": [],
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
        Implementación asíncrona del procesamiento del agente MotivationBehaviorCoach.
        
        Sobrescribe el método de la clase base para proporcionar la implementación
        específica del agente especializado en motivación y cambio de comportamiento.
        
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
            logger.info(f"Ejecutando MotivationBehaviorCoach con input: {input_text[:50]}...")
            
            # Generar session_id si no se proporciona
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Generando nuevo session_id: {session_id}")
            
            # Obtener el contexto de la conversación
            context = await self._get_context(user_id, session_id) if user_id else {}
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                # Intentar obtener el perfil del usuario del contexto primero
                user_profile = context.get("user_profile", {})
                if not user_profile:
                    try:
                        user_profile = self.supabase_client.get_user_profile(user_id)
                        if user_profile:
                            context["user_profile"] = user_profile
                    except Exception as e:
                        logger.warning(f"No se pudo obtener el perfil del usuario {user_id}: {e}")
            
            # Determinar el tipo de tarea basado en palabras clave
            lower_input = input_text.lower()
            
            # Clasificar la consulta
            if any(kw in lower_input for kw in ["hábito", "costumbre", "rutina", "consistencia"]):
                # Generar un plan de hábitos estructurado
                result = await self._generate_habit_plan(input_text, user_profile)
                
                # Generar un resumen textual para la respuesta
                response = self._summarize_habit_plan(result)
                
                # Guardar el plan en el contexto
                if user_id:
                    context["habit_plans"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "plan": result
                    })
                
                # Guardar el plan en el estado del agente
                if user_id:
                    habit_plans = self.get_state("habit_plans", {})
                    habit_plans[user_id] = habit_plans.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "plan": result
                    }]
                    self.update_state("habit_plans", habit_plans)
                    
                # Preparar artefactos para la respuesta
                artifacts = [{
                    "type": "habit_plan",
                    "content": result
                }]
                
                task_type = "habit_formation"
                
            elif any(kw in lower_input for kw in ["meta", "objetivo", "lograr", "alcanzar"]):
                # Generar un plan de metas estructurado
                result = await self._generate_goal_plan(input_text, user_profile)
                
                # Generar un resumen textual para la respuesta
                response = self._summarize_goal_plan(result)
                
                # Guardar el plan en el contexto
                if user_id:
                    context["goal_plans"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "plan": result
                    })
                
                # Guardar el plan en el estado del agente
                if user_id:
                    goal_plans = self.get_state("goal_plans", {})
                    goal_plans[user_id] = goal_plans.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "plan": result
                    }]
                    self.update_state("goal_plans", goal_plans)
                    
                # Preparar artefactos para la respuesta
                artifacts = [{
                    "type": "goal_plan",
                    "content": result
                }]
                
                task_type = "goal_setting"
                
            else:
                # Para otras consultas, generar una respuesta general sobre motivación
                prompt = self._build_prompt(input_text, user_profile)
                response = await self.gemini_client.generate_content(prompt)
                
                # Sin artefactos estructurados para respuestas generales
                artifacts = []
                
                # Determinar el tipo de tarea basado en palabras clave
                if any(kw in lower_input for kw in ["motivación", "inspiración", "animar", "impulso"]):
                    task_type = "motivation_strategies"
                elif any(kw in lower_input for kw in ["cambio", "transformación", "modificar", "ajustar"]):
                    task_type = "behavior_change"
                elif any(kw in lower_input for kw in ["obstáculo", "barrera", "dificultad", "desafío"]):
                    task_type = "obstacle_management"
                else:
                    task_type = "general_motivation"
            
            # Añadir la interacción al historial de conversación
            if user_id:
                context["conversation_history"].append({
                    "user": input_text,
                    "agent": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "task_type": task_type
                })
                
                # Actualizar el contexto en el StateManager
                await self._update_context(context, user_id, session_id)
            
            # Registrar la interacción si hay un usuario identificado
            if user_id:
                self.supabase_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=input_text,
                    response=response
                )
            
            # Calcular tiempo de ejecución
            execution_time = time.time() - start_time
            
            # Formatear respuesta según el protocolo ADK
            return {
                "status": "success",
                "response": response,
                "confidence": 0.9,
                "execution_time": execution_time,
                "agent_id": self.agent_id,
                "artifacts": artifacts,
                "metadata": {
                    "task_type": task_type,
                    "user_id": user_id,
                    "session_id": session_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error en MotivationBehaviorCoach: {e}", exc_info=True)
            execution_time = time.time() - start_time if 'start_time' in locals() else 0.0
            
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud sobre motivación y cambio de comportamiento.",
                "error": str(e),
                "execution_time": execution_time,
                "confidence": 0.0,
                "agent_id": self.agent_id,
                "metadata": {
                    "error_type": type(e).__name__,
                    "user_id": user_id
                }
            }
    
    def _summarize_habit_plan(self, habit_plan: Dict[str, Any]) -> str:
        """Genera un resumen textual del plan de hábitos para la respuesta al usuario."""
        summary_parts = []
        
        if "habit" in habit_plan:
            summary_parts.append(f"El hábito a desarrollar es: {habit_plan['habit']}.")
        
        if "implementation_intention" in habit_plan:
            summary_parts.append(f"La intención de implementación es: {habit_plan['implementation_intention']}.")
        
        if "small_steps" in habit_plan and habit_plan["small_steps"]:
            steps = habit_plan["small_steps"]
            if isinstance(steps, list) and len(steps) > 0:
                summary_parts.append(f"Primer paso: {steps[0]}.")
        
        if "reminders" in habit_plan and habit_plan["reminders"]:
            reminders = habit_plan["reminders"]
            if isinstance(reminders, list) and len(reminders) > 0:
                summary_parts.append(f"Recordatorio clave: {reminders[0]}.")
        
        if not summary_parts:
            return "Revisa el plan detallado para más información."
            
        return " ".join(summary_parts)
    
    def _summarize_goal_plan(self, goal_plan: Dict[str, Any]) -> str:
        """Genera un resumen textual del plan de metas para la respuesta al usuario."""
        summary_parts = []
        
        if "main_goal" in goal_plan:
            main_goal = goal_plan["main_goal"]
            if isinstance(main_goal, dict) and "specific" in main_goal:
                summary_parts.append(f"Tu meta principal es: {main_goal['specific']}.")
            elif isinstance(main_goal, str):
                summary_parts.append(f"Tu meta principal es: {main_goal}.")
        
        if "purpose" in goal_plan:
            summary_parts.append(f"Tu propósito es: {goal_plan['purpose']}.")
        
        if "milestones" in goal_plan and goal_plan["milestones"]:
            milestones = goal_plan["milestones"]
            if isinstance(milestones, list) and len(milestones) > 0:
                milestone = milestones[0]
                if isinstance(milestone, dict) and "description" in milestone:
                    summary_parts.append(f"Primer hito: {milestone['description']}.")
                elif isinstance(milestone, str):
                    summary_parts.append(f"Primer hito: {milestone}.")
        
        if not summary_parts:
            return "Revisa el plan detallado para más información."
            
        return " ".join(summary_parts)
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()
    
    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """
        Ejecuta una tarea solicitada por el servidor A2A.
        
        Args:
            task: Tarea a ejecutar
            
        Returns:
            Any: Resultado de la tarea
        """
        try:
            user_input = task.get("input", "")
            context = task.get("context", {})
            user_id = context.get("user_id")
            session_id = context.get("session_id")
            
            logger.info(f"Procesando consulta de motivación y comportamiento: {user_input}")
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                user_profile = self.supabase_client.get_user_profile(user_id)
                logger.info(f"Perfil de usuario obtenido: {user_profile is not None}")
            
            # Construir el prompt para el modelo
            prompt = self._build_prompt(user_input, user_profile)
            
            # Generar respuesta utilizando Gemini
            response = await self.gemini_client.generate_response(
                prompt=prompt,
                temperature=0.7
            )
            
            # Registrar la interacción en Supabase si hay ID de usuario
            if user_id:
                self.supabase_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=user_input,
                    response=response
                )
                
                # Interactuar con MCPClient
                await self.mcp_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=user_input,
                    response=response
                )
                logger.info("Interacción con MCPClient registrada")
            
            # Crear artefactos si es necesario
            artifacts = []
            
            # Si se menciona hábitos o rutinas, crear un artefacto de plan de hábitos
            if any(keyword in user_input.lower() for keyword in ["hábito", "rutina", "costumbre", "disciplina"]):
                habit_plan = await self._generate_habit_plan(user_input, user_profile)
                
                artifact_id = f"habit_plan_{uuid.uuid4().hex[:8]}"
                artifact = self.create_artifact(
                    artifact_id=artifact_id,
                    artifact_type="habit_plan",
                    parts=[
                        self.create_data_part(habit_plan)
                    ]
                )
                artifacts.append(artifact)
            
            # Si se menciona metas u objetivos, crear un artefacto de plan de metas
            if any(keyword in user_input.lower() for keyword in ["meta", "objetivo", "propósito", "logro"]):
                goal_plan = await self._generate_goal_plan(user_input, user_profile)
                
                artifact_id = f"goal_plan_{uuid.uuid4().hex[:8]}"
                artifact = self.create_artifact(
                    artifact_id=artifact_id,
                    artifact_type="goal_plan",
                    parts=[
                        self.create_data_part(goal_plan)
                    ]
                )
                artifacts.append(artifact)
            
            # Crear mensaje de respuesta
            response_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(response)
                ]
            )
            
            # Devolver respuesta estructurada según el protocolo A2A
            return {
                "response": response,
                "message": response_message,
                "artifacts": artifacts
            }
            
        except Exception as e:
            logger.error(f"Error en MotivationBehaviorCoach: {e}")
            return {
                "error": str(e), 
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud sobre motivación y comportamiento."
            }
    
    async def process_message(self, from_agent: str, content: Dict[str, Any]) -> Any:
        """
        Procesa un mensaje recibido de otro agente.
        
        Args:
            from_agent: ID del agente que envió el mensaje
            content: Contenido del mensaje
            
        Returns:
            Any: Respuesta al mensaje
        """
        try:
            # Extraer información del mensaje
            message_text = content.get("text", "")
            context = content.get("context", {})
            
            logger.info(f"Procesando mensaje de agente {from_agent}: {message_text}")
            
            # Generar respuesta basada en el contenido del mensaje
            prompt = f"""
            Has recibido un mensaje del agente {from_agent}:
            
            "{message_text}"
            
            Responde con información relevante sobre motivación y cambio de comportamiento relacionada con este mensaje.
            """
            
            response = await self.gemini_client.generate_response(prompt, temperature=0.7)
            
            # Crear mensaje de respuesta
            response_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(response)
                ]
            )
            
            return {
                "status": "success",
                "response": response,
                "message": response_message
            }
        except Exception as e:
            logger.error(f"Error al procesar mensaje de agente: {e}")
            return {"error": str(e)}
    
    def _build_prompt(self, user_input: str, user_profile: Optional[Dict[str, Any]] = None) -> str:
        """
        Construye el prompt para el modelo de Gemini.
        
        Args:
            user_input: La consulta del usuario
            user_profile: Perfil del usuario con datos relevantes
            
        Returns:
            str: Prompt completo para el modelo
        """
        prompt = f"{self.system_instructions}\n\n"
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += "Información del usuario:\n"
            prompt += f"- Objetivos: {user_profile.get('goals', 'No disponible')}\n"
            prompt += f"- Desafíos: {user_profile.get('challenges', 'No disponible')}\n"
            prompt += f"- Preferencias: {user_profile.get('preferences', 'No disponible')}\n"
            prompt += f"- Historial: {user_profile.get('history', 'No disponible')}\n\n"
        
        prompt += f"Consulta del usuario: {user_input}\n\n"
        prompt += "Proporciona una respuesta detallada y personalizada basada en la ciencia del comportamiento."
        
        return prompt
    
    async def _generate_habit_plan(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un plan de hábitos estructurado.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Plan de hábitos estructurado
        """
        prompt = f"""
        Genera un plan de formación de hábitos estructurado basado en la siguiente solicitud:
        
        "{user_input}"
        
        El plan debe incluir:
        1. Hábito principal a desarrollar
        2. Duración recomendada para la formación del hábito
        3. Desencadenantes o señales para el hábito
        4. Pasos específicos y accionables
        5. Sistema de seguimiento y rendición de cuentas
        6. Estrategias para manejar recaídas
        7. Recompensas para reforzar el comportamiento
        
        Devuelve el plan en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Objetivos: {user_profile.get('goals', 'No disponible')}
            - Desafíos: {user_profile.get('challenges', 'No disponible')}
            - Preferencias: {user_profile.get('preferences', 'No disponible')}
            - Historial: {user_profile.get('history', 'No disponible')}
            """
        
        # Generar el plan de hábitos
        response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                import json
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "habit": "Hábito principal a desarrollar",
                    "duration": "66 días (tiempo promedio para formar un hábito)",
                    "triggers": [
                        "Después de una actividad existente",
                        "A una hora específica del día",
                        "En un lugar específico"
                    ],
                    "steps": [
                        "Paso 1: Comenzar con una versión mínima del hábito",
                        "Paso 2: Incrementar gradualmente la dificultad",
                        "Paso 3: Mantener consistencia diaria"
                    ],
                    "tracking": {
                        "method": "Registro diario en aplicación o diario",
                        "metrics": "Consistencia, no perfección"
                    },
                    "relapse_strategies": [
                        "Regla de nunca fallar dos veces seguidas",
                        "Identificar y eliminar obstáculos",
                        "Ajustar el hábito si es demasiado difícil"
                    ],
                    "rewards": [
                        "Recompensa inmediata después de completar el hábito",
                        "Celebrar hitos (7 días, 30 días, etc.)",
                        "Recompensas alineadas con los valores personales"
                    ]
                }
        
        return response
    
    async def _generate_goal_plan(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un plan de metas estructurado.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Plan de metas estructurado
        """
        prompt = f"""
        Genera un plan de metas estructurado basado en la siguiente solicitud:
        
        "{user_input}"
        
        El plan debe incluir:
        1. Meta principal (siguiendo el formato SMART)
        2. Razón profunda o propósito de la meta
        3. Submetas o hitos intermedios
        4. Cronograma con fechas específicas
        5. Recursos necesarios
        6. Posibles obstáculos y estrategias para superarlos
        7. Sistema de seguimiento del progreso
        
        Devuelve el plan en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Objetivos: {user_profile.get('goals', 'No disponible')}
            - Desafíos: {user_profile.get('challenges', 'No disponible')}
            - Preferencias: {user_profile.get('preferences', 'No disponible')}
            - Historial: {user_profile.get('history', 'No disponible')}
            """
        
        # Generar el plan de metas
        response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                import json
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "main_goal": {
                        "specific": "Meta específica",
                        "measurable": "Cómo se medirá el éxito",
                        "achievable": "Por qué es alcanzable",
                        "relevant": "Por qué es relevante",
                        "time_bound": "Fecha límite"
                    },
                    "purpose": "Razón profunda para alcanzar esta meta",
                    "milestones": [
                        {
                            "description": "Primer hito",
                            "target_date": "Fecha objetivo",
                            "metrics": "Cómo medir el éxito"
                        },
                        {
                            "description": "Segundo hito",
                            "target_date": "Fecha objetivo",
                            "metrics": "Cómo medir el éxito"
                        }
                    ],
                    "timeline": {
                        "start_date": "Fecha de inicio",
                        "end_date": "Fecha de finalización",
                        "key_dates": ["Fecha 1", "Fecha 2", "Fecha 3"]
                    },
                    "resources": [
                        "Recurso 1 necesario",
                        "Recurso 2 necesario",
                        "Recurso 3 necesario"
                    ],
                    "obstacles": [
                        {
                            "description": "Posible obstáculo 1",
                            "strategy": "Estrategia para superarlo"
                        },
                        {
                            "description": "Posible obstáculo 2",
                            "strategy": "Estrategia para superarlo"
                        }
                    ],
                    "tracking": {
                        "frequency": "Diaria/Semanal/Mensual",
                        "method": "Método de seguimiento",
                        "review_points": ["Punto de revisión 1", "Punto de revisión 2"]
                    }
                }
        
        return response

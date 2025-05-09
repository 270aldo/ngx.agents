"""Agente especializado en motivación y cambio de comportamiento.

Este agente proporciona estrategias para mantener la motivación, 
establece hábitos saludables, supera obstáculos psicológicos,
y logra cambios de comportamiento duraderos.

Implementa los protocolos oficiales ADK y A2A para comunicación entre agentes.
"""
import logging
import uuid
import time
import json
import os
from typing import Dict, Any, Optional, List, Union
import asyncio
from datetime import datetime, timezone
from google.cloud import aiplatform
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from agents.base.adk_agent import ADKAgent
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

# Importar Skill desde adk.agent
try:
    from adk.agent import Skill
except ImportError:
    # Stub para Skill si no está disponible
    from adk.agent import Skill

# Importar esquemas para las skills
from agents.motivation_behavior_coach.schemas import (
    HabitFormationInput, HabitFormationOutput,
    GoalSettingInput, GoalSettingOutput,
    MotivationStrategiesInput, MotivationStrategiesOutput,
    BehaviorChangeInput, BehaviorChangeOutput,
    ObstacleManagementInput, ObstacleManagementOutput,
    HabitPlanArtifact, GoalPlanArtifact,
    MotivationStrategiesArtifact, BehaviorChangePlanArtifact,
    ObstacleManagementArtifact
)

# Configurar logger
logger = get_logger(__name__)

class MotivationBehaviorCoach(ADKAgent):
    """
    Agente especializado en motivación y cambio de comportamiento.
    
    Este agente proporciona estrategias para mantener la motivación, 
    establecer hábitos saludables, superar obstáculos psicológicos,
    y lograr cambios de comportamiento duraderos.
    
    Implementa los protocolos oficiales ADK y A2A para comunicación entre agentes.
    """
    gemini_client: Optional[GeminiClient] = None
    supabase_client: Optional[SupabaseClient] = None
    
    def __init__(self, 
                 toolkit: Optional[MCPToolkit] = None, 
                 state_manager: Optional[StateManager] = None,
                 system_instructions: Optional[str] = None,
                 gemini_client: Optional[GeminiClient] = None,
                 model: str = "gemini-1.5-flash",
                 **kwargs):
        """
        Inicializa el agente MotivationBehaviorCoach.
        
        Args:
            toolkit: Toolkit de ADK para registro de habilidades
            state_manager: Gestor de estado para persistencia
            system_instructions: Instrucciones del sistema
            gemini_client: Cliente de Gemini para generación de texto
            model: Modelo de Gemini a utilizar
            **kwargs: Argumentos adicionales para la clase base
        """
        # Definir instrucciones del sistema
        self.system_instructions = system_instructions or """
        Eres un coach especializado en motivación y cambio de comportamiento. 
        Tu función es ayudar a los usuarios a establecer hábitos saludables, 
        mantener la motivación, superar obstáculos psicológicos y lograr 
        cambios de comportamiento duraderos. Utiliza principios de psicología 
        positiva, ciencia del comportamiento y técnicas de coaching validadas.
        """
        
        # Definir capacidades
        capabilities = [
            "habit_formation", 
            "motivation_strategies", 
            "behavior_change", 
            "goal_setting",
            "obstacle_management"
        ]
        
        # Inicializar clientes
        self.gemini_client = gemini_client or GeminiClient(model=model)
        
        # Inicializar StateManager si no se proporciona
        self.state_manager = state_manager or StateManager()
        
        # Definir skills usando la clase Skill para compatibilidad con ADK y A2A
        self.skills = {
            "habit_formation": Skill(
                name="Formación de Hábitos",
                description="Técnicas para establecer y mantener hábitos saludables basadas en ciencia del comportamiento",
                handler=self._skill_habit_formation,
                input_schema=HabitFormationInput,
                output_schema=HabitFormationOutput
            ),
            "motivation_strategies": Skill(
                name="Estrategias de Motivación",
                description="Estrategias basadas en evidencia para mantener la motivación a largo plazo y superar barreras psicológicas",
                handler=self._skill_motivation_strategies,
                input_schema=MotivationStrategiesInput,
                output_schema=MotivationStrategiesOutput
            ),
            "behavior_change": Skill(
                name="Cambio de Comportamiento",
                description="Métodos para lograr cambios de comportamiento duraderos basados en modelos psicológicos validados",
                handler=self._skill_behavior_change,
                input_schema=BehaviorChangeInput,
                output_schema=BehaviorChangeOutput
            ),
            "goal_setting": Skill(
                name="Establecimiento de Metas",
                description="Técnicas para establecer metas efectivas usando el marco SMART y otros modelos validados",
                handler=self._skill_goal_setting,
                input_schema=GoalSettingInput,
                output_schema=GoalSettingOutput
            ),
            "obstacle_management": Skill(
                name="Gestión de Obstáculos",
                description="Estrategias para identificar, anticipar y superar obstáculos en el camino hacia los objetivos",
                handler=self._skill_obstacle_management,
                input_schema=ObstacleManagementInput,
                output_schema=ObstacleManagementOutput
            )
        }
        
        # Inicializar la clase base ADKAgent
        super().__init__(
            agent_id="motivation_behavior_coach",
            name="NGX Motivation & Behavior Coach",
            description="Especialista en motivación, formación de hábitos y cambio de comportamiento",
            capabilities=capabilities,
            toolkit=toolkit,
            state_manager=state_manager,
            version="1.2.0",
            system_instructions=self.system_instructions,
            skills=self.skills,
            model=model,
            **kwargs
        )
    
    async def _get_context(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el StateManager.

        Args:
            user_id (str): ID del usuario.
            session_id (str): ID de la sesión.

        Returns:
            Dict[str, Any]: Contexto de la conversación.
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
            context (Dict[str, Any]): Contexto actualizado.
            user_id (str): ID del usuario.
            session_id (str): ID de la sesión.
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
            input_text (str): Texto de entrada del usuario.
            user_id (Optional[str]): ID del usuario (opcional).
            session_id (Optional[str]): ID de la sesión (opcional).
            **kwargs: Argumentos adicionales como context, parameters, etc.
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente.
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
            metadata = {
                "status": "success",
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            payload = {
                "response": response,
                "message": response,
                "artifacts": artifacts
            }
            return {"metadata": metadata, "payload": payload}
            
        except Exception as e:
            logger.error(f"Error en MotivationBehaviorCoach: {e}", exc_info=True)
            execution_time = time.time() - start_time if 'start_time' in locals() else 0.0
            
            metadata = {
                "status": "error",
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            payload = {
                "error": str(e),
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud sobre motivación y comportamiento."
            }
            return {"metadata": metadata, "payload": payload}
    
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
                # Intentar obtener el perfil del usuario del contexto primero
                user_profile = context.get("user_profile", {})
                if not user_profile:
                    try:
                        user_profile = self.supabase_client.get_user_profile(user_id)
                        if user_profile:
                            context["user_profile"] = user_profile
                    except Exception as e:
                        logger.warning(f"No se pudo obtener el perfil del usuario {user_id}: {e}")
            
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
            
            metadata = {
                "status": "success",
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            payload = {
                "response": response,
                "message": response_message,
                "artifacts": artifacts
            }
            return {"metadata": metadata, "payload": payload}
            
        except Exception as e:
            logger.error(f"Error en MotivationBehaviorCoach: {e}")
            metadata = {
                "status": "error",
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            payload = {
                "error": str(e),
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud sobre motivación y comportamiento."
            }
            return {"metadata": metadata, "payload": payload}
    
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
            
            metadata = {
                "status": "success",
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            payload = {
                "response": response,
                "message": response_message
            }
            return {"metadata": metadata, "payload": payload}
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje de agente {from_agent}: {e}")
            metadata = {
                "status": "error",
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            payload = {
                "error": str(e),
                "response": f"Error procesando mensaje del agente {from_agent}."
            }
            return {"metadata": metadata, "payload": payload}
    
    def _build_prompt(self, user_input: str, user_profile: Optional[Dict[str, Any]] = None) -> str:
        """
        Construye el prompt para el modelo de Gemini.
        
        Args:
            user_input: La consulta del usuario
            user_profile: Perfil del usuario
            
        Returns:
            str: Prompt completo para el modelo
        """
        prompt = f"{self.system_instructions}\n\n"
        
        # Añadir información del perfil si está disponible
        if user_profile:
            user_info = (
                f"Información del usuario:\n"
                f"- Edad: {user_profile.get('age', 'No disponible')}\n"
                f"- Género: {user_profile.get('gender', 'No disponible')}\n"
                f"- Objetivos: {user_profile.get('goals', 'No disponible')}\n"
                f"- Preferencias: {user_profile.get('preferences', 'No disponible')}\n"
                f"- Historial: {user_profile.get('history', 'No disponible')}"
            )
            prompt += user_info
        
        prompt += f"\n\nConsulta del usuario: {user_input}\n\n"
        prompt += "Proporciona una respuesta detallada y personalizada basada en la ciencia del comportamiento."
        
        return prompt
    
    async def _skill_habit_formation(self, params: HabitFormationInput) -> HabitFormationOutput:
        """
        Skill para generar un plan de hábitos estructurado usando Pydantic.
        """
        logger.info(f"Skill 'habit_formation' llamada con user_input: {params.user_input[:30]}")
        try:
            plan_data = await self._generate_habit_plan(params.user_input, params.user_profile or {})
            return HabitFormationOutput(**{"habit_plan": plan_data, "tips": plan_data.get("tips", []), "obstacles": plan_data.get("obstacles", []), "consistency_strategies": plan_data.get("consistency_strategies", [])})
        except Exception as e:
            logger.error(f"Error en skill 'habit_formation': {e}", exc_info=True)
            return HabitFormationOutput(
                habit_plan=plan_data if 'plan_data' in locals() else None,
                tips=[],
                obstacles=[],
                consistency_strategies=[]
            )
    
    async def _generate_habit_plan(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un plan de hábitos estructurado.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Plan de hábitos estructurado
        """
        # TODO: Integrar RAG para buscar estrategias específicas de formación de hábitos de la filosofía NGX.
        # TODO: Usar mcp7_query para obtener historial de hábitos/preferencias del usuario desde Supabase.
        # TODO: Usar mcp8_think si la definición de la meta SMART requiere varios pasos de refinamiento.
        prompt = (
            f"Eres un experto en formación de hábitos y cambio de comportamiento. "
            f"Un usuario quiere desarrollar un nuevo hábito: {user_input}\n\n"
            f"{user_info if user_profile else 'No hay información del usuario disponible.'}\n\n"
            f"Crea un plan estructurado para desarrollar este hábito siguiendo el modelo de las 3R (Recordatorio, Rutina, Recompensa). "
            f"Proporciona un análisis detallado, 3 estrategias específicas con pasos de implementación, "
            f"recomienda la estrategia más adecuada y ofrece 3 consejos para el éxito a largo plazo. "
            f"Asegúrate de que las estrategias estén respaldadas por la ciencia y clasifica su dificultad (Baja, Media, Alta)."
        )
        
        try:
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
        except Exception as e:
            logger.error(f"Error en _generate_habit_plan: {str(e)}")
            # Devolver un plan de hábitos básico en caso de error
            return {
                "habit": "Hábito personalizado",
                "duration": "66 días (tiempo promedio para formar un hábito)",
                "triggers": ["Después de una actividad existente"],
                "steps": ["Comenzar con una versión mínima del hábito"],
                "tracking": {"method": "Registro diario"},
                "relapse_strategies": ["Regla de nunca fallar dos veces seguidas"],
                "rewards": ["Recompensa inmediata después de completar el hábito"]
            }
    
    async def _skill_goal_setting(self, params: GoalSettingInput) -> GoalSettingOutput:
        """
        Skill para el establecimiento de metas.
        
        Genera un plan estructurado para establecer y alcanzar metas siguiendo el formato SMART.
        
        Args:
            params: Parámetros de entrada para la skill
                
        Returns:
            GoalSettingOutput: Plan de metas generado
        """
        try:
            # Generar el plan de metas usando el input de Pydantic
            goal_plan_data = await self._generate_goal_plan(
                params.user_input, 
                params.user_profile
            )
            
            # Convertir la respuesta al formato esperado
            # Crear el objeto SmartGoal
            main_goal_data = goal_plan_data.get("main_goal", {})
            smart_goal = SmartGoal(
                specific=main_goal_data.get("specific", "Meta específica"),
                measurable=main_goal_data.get("measurable", "Cómo se medirá el éxito"),
                achievable=main_goal_data.get("achievable", "Por qué es alcanzable"),
                relevant=main_goal_data.get("relevant", "Por qué es relevante"),
                time_bound=main_goal_data.get("time_bound", "Fecha límite")
            )
            
            # Crear los hitos
            milestones = []
            for milestone_data in goal_plan_data.get("milestones", []):
                if isinstance(milestone_data, dict):
                    milestones.append(Milestone(
                        description=milestone_data.get("description", "Hito"),
                        target_date=milestone_data.get("target_date", "Fecha objetivo"),
                        metrics=milestone_data.get("metrics", "Métricas")
                    ))
            
            # Si no hay hitos, crear al menos uno predeterminado
            if not milestones:
                milestones.append(Milestone(
                    description="Hito intermedio",
                    target_date="Fecha objetivo",
                    metrics="Métricas de éxito"
                ))
            
            # Crear la línea de tiempo
            timeline_data = goal_plan_data.get("timeline", {})
            timeline = Timeline(
                start_date=timeline_data.get("start_date", "Fecha de inicio"),
                end_date=timeline_data.get("end_date", "Fecha de finalización"),
                key_dates=timeline_data.get("key_dates", ["Fecha clave 1", "Fecha clave 2"])
            )
            
            # Crear los obstáculos
            obstacles = []
            for obstacle_data in goal_plan_data.get("obstacles", []):
                if isinstance(obstacle_data, dict):
                    obstacles.append(Obstacle(
                        description=obstacle_data.get("description", "Obstáculo"),
                        strategy=obstacle_data.get("strategy", "Estrategia")
                    ))
            
            # Si no hay obstáculos, crear al menos uno predeterminado
            if not obstacles:
                obstacles.append(Obstacle(
                    description="Posible obstáculo",
                    strategy="Estrategia para superarlo"
                ))
            
            # Crear el sistema de seguimiento
            tracking_data = goal_plan_data.get("tracking", {})
            tracking = TrackingSystem(
                frequency=tracking_data.get("frequency", "Semanal"),
                method=tracking_data.get("method", "Registro en diario"),
                review_points=tracking_data.get("review_points", ["Revisión semanal", "Revisión mensual"])
            )
            
            # Crear el plan de metas completo
            goal_plan = GoalPlan(
                main_goal=smart_goal,
                purpose=goal_plan_data.get("purpose", "Propósito de la meta"),
                milestones=milestones,
                timeline=timeline,
                resources=goal_plan_data.get("resources", ["Recurso necesario"]),
                obstacles=obstacles,
                tracking=tracking
            )
            
            # Devolver directamente el objeto GoalSettingOutput
            return GoalSettingOutput(
                goal_plan=goal_plan
            )
        except Exception as e:
            logger.error(f"Error en _skill_goal_setting: {str(e)}")
            # Devolver un objeto GoalSettingOutput con valores predeterminados en caso de error
            return GoalSettingOutput(
                goal_plan=GoalPlan(
                    main_goal=SmartGoal(
                        specific="No se pudo generar un objetivo específico debido a un error",
                        measurable="N/A",
                        achievable="N/A",
                        relevant="N/A",
                        time_bound="N/A"
                    ),
                    purpose=f"Error: {str(e)}",
                    milestones=[Milestone(
                        description="No disponible debido a un error",
                        target_date="N/A",
                        metrics="N/A"
                    )],
                    timeline=Timeline(
                        start_date="Hoy",
                        end_date="No definido",
                        key_dates=[]
                    ),
                    resources=["Consulta a un profesional"],
                    obstacles=[Obstacle(
                        description="Error en la generación del plan",
                        strategy="Intenta nuevamente con más detalles"
                    )],
                    tracking=TrackingSystem(
                        frequency="N/A",
                        method="N/A",
                        review_points=[]
                    )
                )
            )
    
    async def _generate_goal_plan(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un plan de metas estructurado.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Plan de metas estructurado
        """
        # TODO: Integrar RAG para buscar marcos de establecimiento de metas (ej. WOOP, OKR) adaptados por NGX.
        # TODO: Usar mcp7_query para obtener metas previas o métricas de progreso del usuario desde Supabase.
        # TODO: Usar mcp8_think si la definición de la meta SMART requiere varios pasos de refinamiento.
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
        except Exception as e:
            logger.error(f"Error en _generate_goal_plan: {str(e)}")
            # Devolver un plan de metas básico en caso de error
            return {
                "main_goal": {
                    "specific": "Meta específica",
                    "measurable": "Cómo se medirá el éxito",
                    "achievable": "Por qué es alcanzable",
                    "relevant": "Por qué es relevante",
                    "time_bound": "Fecha límite"
                },
                "purpose": "Propósito de la meta",
                "milestones": [{"description": "Hito", "target_date": "Fecha", "metrics": "Métricas"}],
                "timeline": {"start_date": "Inicio", "end_date": "Fin", "key_dates": ["Fecha clave"]},
                "resources": ["Recurso necesario"],
                "obstacles": [{"description": "Obstáculo", "strategy": "Estrategia"}],
                "tracking": {"frequency": "Semanal", "method": "Método", "review_points": ["Revisión"]}
            }

    async def _skill_motivation_strategies(self, params: MotivationStrategiesInput) -> MotivationStrategiesOutput:
        """
        Skill para generar estrategias de motivación personalizadas.
        
        Genera estrategias de motivación basadas en la ciencia del comportamiento y la psicología positiva.
        
        Args:
            params: Parámetros de entrada para la skill
                
        Returns:
            MotivationStrategiesOutput: Estrategias de motivación generadas
        """
        try:
            # Generar las estrategias de motivación usando el input de Pydantic
            motivation_data = await self._generate_motivation_strategies(
                params.user_input, 
                params.user_profile
            )
            
            # Convertir la respuesta al formato esperado
            strategies = []
            for strategy_data in motivation_data.get("strategies", []):
                if isinstance(strategy_data, dict):
                    strategies.append(MotivationStrategy(
                        name=strategy_data.get("name", "Estrategia de motivación"),
                        description=strategy_data.get("description", "Descripción de la estrategia"),
                        implementation=strategy_data.get("implementation", "Pasos para implementar"),
                        science_backed=strategy_data.get("science_backed", True),
                        difficulty=strategy_data.get("difficulty", "Media")
                    ))
                elif isinstance(strategy_data, str):
                    strategies.append(MotivationStrategy(
                        name=f"Estrategia: {strategy_data[:30]}...",
                        description=strategy_data,
                        implementation="Implementar según las circunstancias personales",
                        science_backed=True,
                        difficulty="Media"
                    ))
            
            # Si no hay estrategias, crear al menos una predeterminada
            if not strategies:
                strategies.append(MotivationStrategy(
                    name="Visualización del éxito",
                    description="Visualizar el resultado deseado para aumentar la motivación",
                    implementation="Dedica 5 minutos cada mañana a visualizar el logro de tus objetivos",
                    science_backed=True,
                    difficulty="Baja"
                ))
            
            # Devolver directamente el objeto MotivationStrategiesOutput
            return MotivationStrategiesOutput(
                strategies=strategies,
                analysis=motivation_data.get("analysis", "Análisis motivacional personalizado"),
                recommended_strategy=motivation_data.get("recommended_strategy", strategies[0].name),
                long_term_tips=motivation_data.get("long_term_tips", [
                    "Mantén un registro de tus éxitos",
                    "Celebra los pequeños logros",
                    "Conecta tus acciones con tus valores personales"
                ])
            )
        except Exception as e:
            logger.error(f"Error en _skill_motivation_strategies: {str(e)}")
            # Devolver un objeto MotivationStrategiesOutput con valores predeterminados en caso de error
            return MotivationStrategiesOutput(
                strategies=[
                    MotivationStrategy(
                        name="Visualización del éxito",
                        description="Visualizar el resultado deseado para aumentar la motivación",
                        implementation="Dedica 5 minutos cada mañana a visualizar el logro de tus objetivos",
                        science_backed=True,
                        difficulty="Baja"
                    )
                ],
                analysis=f"Error al generar análisis: {str(e)}",
                recommended_strategy="Visualización del éxito",
                long_term_tips=[
                    "Mantén un registro de tus éxitos",
                    "Celebra los pequeños logros",
                    "Conecta tus acciones con tus valores personales"
                ]
            )
    
    async def _generate_motivation_strategies(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera estrategias de motivación personalizadas.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Estrategias de motivación estructuradas
        """
        prompt = (
            f"Genera estrategias de motivación personalizadas basadas en la siguiente solicitud:\n\n"
            f"\"{user_input}\"\n\n"
            f"El resultado debe incluir:\n"
            f"1. Análisis motivacional de la situación\n"
            f"2. Lista de estrategias de motivación aplicables (mínimo 3)\n"
            f"3. Estrategia más recomendada\n"
            f"4. Consejos para mantener la motivación a largo plazo\n\n"
            f"Para cada estrategia, incluye:\n"
            f"- Nombre de la estrategia\n"
            f"- Descripción detallada\n"
            f"- Pasos para implementarla\n"
            f"- Si está respaldada por la ciencia (true/false)\n"
            f"- Nivel de dificultad (Baja/Media/Alta)\n\n"
            f"Devuelve el resultado en formato JSON estructurado."
        )
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += (
                "\n\nConsidera la siguiente información del usuario:\n"
                f"- Objetivos: {user_profile.get('goals', 'No disponible')}\n"
                f"- Desafíos: {user_profile.get('challenges', 'No disponible')}\n"
                f"- Preferencias: {user_profile.get('preferences', 'No disponible')}\n"
                f"- Historial: {user_profile.get('history', 'No disponible')}"
            )
        
        try:
            # Generar las estrategias de motivación
            response = await self.gemini_client.generate_structured_output(prompt)
            
            # Si la respuesta no es un diccionario, intentar convertirla
            if not isinstance(response, dict):
                try:
                    import json
                    response = json.loads(response)
                except Exception:
                    # Si no se puede convertir, crear un diccionario básico
                    response = {
                        "analysis": "Análisis motivacional personalizado",
                        "strategies": [
                            {
                                "name": "Visualización del éxito",
                                "description": "Visualizar el resultado deseado para aumentar la motivación",
                                "implementation": "Dedica 5 minutos cada mañana a visualizar el logro de tus objetivos",
                                "science_backed": True,
                                "difficulty": "Baja"
                            },
                            {
                                "name": "Establecimiento de micro-metas",
                                "description": "Dividir objetivos grandes en pequeñas metas alcanzables",
                                "implementation": "Identifica el próximo paso más pequeño y concéntrate solo en él",
                                "science_backed": True,
                                "difficulty": "Media"
                            },
                            {
                                "name": "Técnica Pomodoro",
                                "description": "Trabajar en intervalos de tiempo enfocados",
                                "implementation": "Trabaja durante 25 minutos, luego descansa 5 minutos",
                                "science_backed": True,
                                "difficulty": "Baja"
                            }
                        ],
                        "recommended_strategy": "Establecimiento de micro-metas",
                        "long_term_tips": [
                            "Mantén un registro de tus éxitos",
                            "Celebra los pequeños logros",
                            "Conecta tus acciones con tus valores personales"
                        ]
                    }
            
            return response
        except Exception as e:
            logger.error(f"Error en _generate_motivation_strategies: {str(e)}")
            # Devolver estrategias de motivación básicas en caso de error
            return {
                "analysis": "Análisis motivacional personalizado",
                "strategies": [
                    {
                        "name": "Visualización del éxito",
                        "description": "Visualizar el resultado deseado para aumentar la motivación",
                        "implementation": "Dedica 5 minutos cada mañana a visualizar el logro de tus objetivos",
                        "science_backed": True,
                        "difficulty": "Baja"
                    }
                ],
                "recommended_strategy": "Visualización del éxito",
                "long_term_tips": ["Mantén un registro de tus éxitos"]
            }
    
    async def _skill_behavior_change(self, params: BehaviorChangeInput) -> BehaviorChangeOutput:
        """
        Skill para generar un plan de cambio de comportamiento personalizado.
        
        Genera un plan estructurado para cambiar comportamientos basado en la ciencia del comportamiento.
        
        Args:
            params: Parámetros de entrada para la skill
                
        Returns:
            BehaviorChangeOutput: Plan de cambio de comportamiento generado
        """
        try:
            # Generar el plan de cambio de comportamiento usando el input de Pydantic
            behavior_data = await self._generate_behavior_change_plan(
                params.user_input, 
                params.user_profile
            )
            
            # Crear las fases del plan
            phases = []
            for phase_data in behavior_data.get("phases", []):
                if isinstance(phase_data, dict):
                    steps = []
                    for step_data in phase_data.get("steps", []):
                        if isinstance(step_data, dict):
                            steps.append(BehaviorChangeStep(
                                description=step_data.get("description", "Paso del plan"),
                                duration=step_data.get("duration", "1 semana"),
                                metrics=step_data.get("metrics", ["Progreso general"]),
                                resources=step_data.get("resources", [])
                            ))
                        elif isinstance(step_data, str):
                            steps.append(BehaviorChangeStep(
                                description=step_data,
                                duration="Según sea necesario",
                                metrics=["Progreso general"],
                                resources=[]
                            ))
                    
                    phases.append(BehaviorChangePhase(
                        name=phase_data.get("name", "Fase del plan"),
                        description=phase_data.get("description", "Descripción de la fase"),
                        duration=phase_data.get("duration", "2-4 semanas"),
                        steps=steps
                    ))
                elif isinstance(phase_data, str):
                    phases.append(BehaviorChangePhase(
                        name=f"Fase: {phase_data[:30]}...",
                        description=phase_data,
                        duration="Según sea necesario",
                        steps=[BehaviorChangeStep(
                            description="Implementar según las circunstancias personales",
                            duration="Variable",
                            metrics=["Progreso general"],
                            resources=[]
                        )]
                    ))
            
            # Si no hay fases, crear al menos una predeterminada
            if not phases:
                phases.append(BehaviorChangePhase(
                    name="Fase de preparación",
                    description="Preparación para el cambio de comportamiento",
                    duration="2 semanas",
                    steps=[
                        BehaviorChangeStep(
                            description="Identificar el comportamiento específico a cambiar",
                            duration="3 días",
                            metrics=["Claridad del objetivo"],
                            resources=[]
                        ),
                        BehaviorChangeStep(
                            description="Establecer una meta SMART",
                            duration="2 días",
                            metrics=["Calidad de la meta"],
                            resources=[]
                        )
                    ]
                ))
            
            # Devolver directamente el objeto BehaviorChangeOutput
            return BehaviorChangeOutput(
                target_behavior=behavior_data.get("target_behavior", "Comportamiento objetivo"),
                current_state=behavior_data.get("current_state", "Estado actual del comportamiento"),
                desired_state=behavior_data.get("desired_state", "Estado deseado del comportamiento"),
                motivation_factors=behavior_data.get("motivation_factors", ["Factor motivacional"]),
                potential_obstacles=behavior_data.get("potential_obstacles", ["Obstáculo potencial"]),
                phases=phases,
                tracking_method=behavior_data.get("tracking_method", "Método de seguimiento diario"),
                support_resources=behavior_data.get("support_resources", ["Recurso de apoyo"])
            )
        except Exception as e:
            logger.error(f"Error en _skill_behavior_change: {str(e)}")
            # Devolver un objeto BehaviorChangeOutput con valores predeterminados en caso de error
            return BehaviorChangeOutput(
                target_behavior="Comportamiento no especificado",
                current_state=f"Error: {str(e)}",
                desired_state="Estado deseado no especificado",
                motivation_factors=["Factor motivacional no especificado"],
                potential_obstacles=["Error en la generación del plan"],
                phases=[BehaviorChangePhase(
                    name="Fase de error",
                    description=f"No se pudo generar el plan debido a: {str(e)}",
                    duration="N/A",
                    steps=[BehaviorChangeStep(
                        description="Intenta nuevamente con más detalles",
                        duration="N/A",
                        metrics=["N/A"],
                        resources=["Consulta a un profesional"]
                    )]
                )],
                tracking_method="No disponible",
                support_resources=["Consulta a un profesional"]
            )
    
    async def _generate_behavior_change_plan(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un plan de cambio de comportamiento personalizado.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Plan de cambio de comportamiento estructurado
        """
        prompt = (
            f"Genera un plan de cambio de comportamiento basado en la siguiente solicitud:\n\n"
            f"\"{user_input}\"\n\n"
            f"El resultado debe incluir:\n"
            f"1. Comportamiento objetivo a cambiar\n"
            f"2. Estado actual del comportamiento\n"
            f"3. Estado deseado del comportamiento\n"
            f"4. Factores motivacionales (qué motiva al usuario)\n"
            f"5. Obstáculos potenciales\n"
            f"6. Fases del plan de cambio (mínimo 3 fases)\n"
            f"7. Método de seguimiento\n"
            f"8. Recursos de apoyo\n\n"
            f"Para cada fase, incluye:\n"
            f"- Nombre de la fase\n"
            f"- Descripción detallada\n"
            f"- Duración estimada\n"
            f"- Pasos específicos a seguir\n\n"
            f"Para cada paso, incluye:\n"
            f"- Descripción detallada\n"
            f"- Duración estimada\n"
            f"- Métricas para medir el progreso\n"
            f"- Recursos necesarios\n\n"
            f"Devuelve el resultado en formato JSON estructurado."
        )
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += (
                "\n\nConsidera la siguiente información del usuario:\n"
                f"- Objetivos: {user_profile.get('goals', 'No disponible')}\n"
                f"- Desafíos: {user_profile.get('challenges', 'No disponible')}\n"
                f"- Preferencias: {user_profile.get('preferences', 'No disponible')}\n"
                f"- Historial: {user_profile.get('history', 'No disponible')}"
            )
        
        try:
            # Generar el plan de cambio de comportamiento
            response = await self.gemini_client.generate_structured_output(prompt)
            
            # Si la respuesta no es un diccionario, intentar convertirla
            if not isinstance(response, dict):
                try:
                    import json
                    response = json.loads(response)
                except Exception:
                    # Si no se puede convertir, crear un diccionario básico
                    response = {
                        "target_behavior": "Comportamiento objetivo",
                        "current_state": "Estado actual del comportamiento",
                        "desired_state": "Estado deseado del comportamiento",
                        "motivation_factors": ["Salud", "Bienestar", "Productividad"],
                        "potential_obstacles": ["Falta de tiempo", "Distracciones", "Falta de apoyo"],
                        "phases": [
                            {
                                "name": "Fase de preparación",
                                "description": "Preparación para el cambio de comportamiento",
                                "duration": "2 semanas",
                                "steps": [
                                    {
                                        "description": "Identificar el comportamiento específico a cambiar",
                                        "duration": "3 días",
                                        "metrics": ["Claridad del objetivo"],
                                        "resources": []
                                    },
                                    {
                                        "description": "Establecer una meta SMART",
                                        "duration": "2 días",
                                        "metrics": ["Calidad de la meta"],
                                        "resources": []
                                    }
                                ]
                            },
                            {
                                "name": "Fase de acción",
                                "description": "Implementación del cambio de comportamiento",
                                "duration": "4 semanas",
                                "steps": [
                                    {
                                        "description": "Implementar el nuevo comportamiento diariamente",
                                        "duration": "4 semanas",
                                        "metrics": ["Frecuencia", "Consistencia"],
                                        "resources": ["Aplicación de seguimiento"]
                                    }
                                ]
                            },
                            {
                                "name": "Fase de mantenimiento",
                                "description": "Consolidar el nuevo comportamiento",
                                "duration": "Continua",
                                "steps": [
                                    {
                                        "description": "Revisar y ajustar el plan según sea necesario",
                                        "duration": "Semanal",
                                        "metrics": ["Sostenibilidad"],
                                        "resources": []
                                    }
                                ]
                            }
                        ],
                        "tracking_method": "Registro diario en aplicación",
                        "support_resources": ["Grupo de apoyo", "Aplicación de seguimiento", "Coach personal"]
                    }
            
            return response
        except Exception as e:
            logger.error(f"Error en _generate_behavior_change_plan: {str(e)}")
            # Devolver un plan básico en caso de error
            return {
                "target_behavior": "Comportamiento objetivo",
                "current_state": "Estado actual del comportamiento",
                "desired_state": "Estado deseado del comportamiento",
                "motivation_factors": ["Salud", "Bienestar"],
                "potential_obstacles": ["Falta de tiempo"],
                "phases": [
                    {
                        "name": "Fase de preparación",
                        "description": "Preparación para el cambio de comportamiento",
                        "duration": "2 semanas",
                        "steps": [
                            {
                                "description": "Identificar el comportamiento específico a cambiar",
                                "duration": "3 días",
                                "metrics": ["Claridad del objetivo"],
                                "resources": []
                            }
                        ]
                    }
                ],
                "tracking_method": "Registro diario",
                "support_resources": ["Grupo de apoyo"]
            }
    
    async def _skill_obstacle_management(self, params: ObstacleManagementInput) -> ObstacleManagementOutput:
        """
        Skill para generar estrategias de manejo de obstáculos personalizadas.
        
        Genera estrategias para superar obstáculos específicos que impiden el logro de metas.
        
        Args:
            params: Parámetros de entrada para la skill
                
        Returns:
            ObstacleManagementOutput: Estrategias de manejo de obstáculos generadas
        """
        try:
            # Generar el plan de manejo de obstáculos usando el input de Pydantic
            obstacle_data = await self._generate_obstacle_management_plan(
                params.user_input, 
                params.user_profile
            )
            
            # Crear los obstáculos y estrategias
            obstacles = []
            for obstacle_info in obstacle_data.get("obstacles", []):
                if isinstance(obstacle_info, dict):
                    strategies = []
                    for strategy_info in obstacle_info.get("strategies", []):
                        if isinstance(strategy_info, dict):
                            strategies.append(ObstacleStrategy(
                                description=strategy_info.get("description", "Estrategia para superar el obstáculo"),
                                implementation=strategy_info.get("implementation", "Pasos para implementar la estrategia"),
                                effectiveness=strategy_info.get("effectiveness", "Media"),
                                effort_required=strategy_info.get("effort_required", "Medio")
                            ))
                        elif isinstance(strategy_info, str):
                            strategies.append(ObstacleStrategy(
                                description=strategy_info,
                                implementation="Implementar según las circunstancias personales",
                                effectiveness="Media",
                                effort_required="Medio"
                            ))
                    
                    obstacles.append(Obstacle(
                        name=obstacle_info.get("name", "Obstáculo"),
                        description=obstacle_info.get("description", "Descripción del obstáculo"),
                        impact=obstacle_info.get("impact", "Medio"),
                        strategies=strategies
                    ))
                elif isinstance(obstacle_info, str):
                    obstacles.append(Obstacle(
                        name=f"Obstáculo: {obstacle_info[:30]}...",
                        description=obstacle_info,
                        impact="Medio",
                        strategies=[ObstacleStrategy(
                            description="Estrategia genérica para superar el obstáculo",
                            implementation="Implementar según las circunstancias personales",
                            effectiveness="Media",
                            effort_required="Medio"
                        )]
                    ))
            
            # Si no hay obstáculos, crear al menos uno predeterminado
            if not obstacles:
                obstacles.append(Obstacle(
                    name="Falta de tiempo",
                    description="Dificultad para encontrar tiempo para dedicar a la meta",
                    impact="Alto",
                    strategies=[
                        ObstacleStrategy(
                            description="Priorizar y programar",
                            implementation="Reservar bloques de tiempo específicos en el calendario",
                            effectiveness="Alta",
                            effort_required="Bajo"
                        )
                    ]
                ))
            
            # Devolver directamente el objeto ObstacleManagementOutput
            return ObstacleManagementOutput(
                goal=obstacle_data.get("goal", "Meta relacionada"),
                obstacles=obstacles,
                general_approach=obstacle_data.get("general_approach", "Enfoque general para manejar obstáculos"),
                prevention_strategies=obstacle_data.get("prevention_strategies", ["Estrategia de prevención"]),
                contingency_plan=obstacle_data.get("contingency_plan", "Plan de contingencia general")
            )
        except Exception as e:
            logger.error(f"Error en _skill_obstacle_management: {str(e)}")
            # Devolver un objeto ObstacleManagementOutput con valores predeterminados en caso de error
            return ObstacleManagementOutput(
                goal="Meta no especificada",
                obstacles=[
                    Obstacle(
                        name="Error en la generación",
                        description=f"No se pudo generar el plan debido a: {str(e)}",
                        impact="Alto",
                        strategies=[
                            ObstacleStrategy(
                                description="Intenta nuevamente con más detalles",
                                implementation="Proporciona información más específica sobre el obstáculo",
                                effectiveness="Media",
                                effort_required="Bajo"
                            )
                        ]
                    )
                ],
                general_approach="Enfoque no disponible debido a un error",
                prevention_strategies=["Intenta nuevamente con más detalles"],
                contingency_plan="Plan de contingencia no disponible"
            )
    
    async def _generate_obstacle_management_plan(self, user_input: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un plan de manejo de obstáculos personalizado.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Plan de manejo de obstáculos estructurado
        """
        prompt = (
            f"Genera un plan de manejo de obstáculos basado en la siguiente solicitud:\n\n"
            f"\"{user_input}\"\n\n"
            f"El resultado debe incluir:\n"
            f"1. Meta relacionada\n"
            f"2. Lista de obstáculos potenciales (mínimo 3)\n"
            f"3. Enfoque general para manejar obstáculos\n"
            f"4. Estrategias de prevención\n"
            f"5. Plan de contingencia general\n\n"
            f"Para cada obstáculo, incluye:\n"
            f"- Nombre del obstáculo\n"
            f"- Descripción detallada\n"
            f"- Nivel de impacto (Bajo/Medio/Alto)\n"
            f"- Estrategias específicas para superarlo (mínimo 2 por obstáculo)\n\n"
            f"Para cada estrategia, incluye:\n"
            f"- Descripción detallada\n"
            f"- Pasos para implementarla\n"
            f"- Nivel de efectividad esperada (Baja/Media/Alta)\n"
            f"- Nivel de esfuerzo requerido (Bajo/Medio/Alto)\n\n"
            f"Devuelve el resultado en formato JSON estructurado."
        )
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += (
                "\n\nConsidera la siguiente información del usuario:\n"
                f"- Objetivos: {user_profile.get('goals', 'No disponible')}\n"
                f"- Desafíos: {user_profile.get('challenges', 'No disponible')}\n"
                f"- Preferencias: {user_profile.get('preferences', 'No disponible')}\n"
                f"- Historial: {user_profile.get('history', 'No disponible')}"
            )
        
        try:
            # Generar el plan de manejo de obstáculos
            response = await self.gemini_client.generate_structured_output(prompt)
            
            # Si la respuesta no es un diccionario, intentar convertirla
            if not isinstance(response, dict):
                try:
                    import json
                    response = json.loads(response)
                except Exception:
                    # Si no se puede convertir, crear un diccionario básico
                    response = {
                        "goal": "Meta relacionada",
                        "obstacles": [
                            {
                                "name": "Falta de tiempo",
                                "description": "Dificultad para encontrar tiempo para dedicar a la meta",
                                "impact": "Alto",
                                "strategies": [
                                    {
                                        "description": "Priorizar y programar",
                                        "implementation": "Reservar bloques de tiempo específicos en el calendario",
                                        "effectiveness": "Alta",
                                        "effort_required": "Bajo"
                                    },
                                    {
                                        "description": "Eliminar distracciones",
                                        "implementation": "Identificar y minimizar las actividades que consumen tiempo innecesariamente",
                                        "effectiveness": "Media",
                                        "effort_required": "Medio"
                                    }
                                ]
                            },
                            {
                                "name": "Falta de motivación",
                                "description": "Dificultad para mantener la motivación a lo largo del tiempo",
                                "impact": "Alto",
                                "strategies": [
                                    {
                                        "description": "Establecer recompensas",
                                        "implementation": "Crear un sistema de recompensas para celebrar los logros",
                                        "effectiveness": "Alta",
                                        "effort_required": "Bajo"
                                    },
                                    {
                                        "description": "Buscar apoyo social",
                                        "implementation": "Compartir metas con amigos o familiares para aumentar la responsabilidad",
                                        "effectiveness": "Alta",
                                        "effort_required": "Medio"
                                    }
                                ]
                            },
                            {
                                "name": "Falta de conocimiento",
                                "description": "Carencia de habilidades o conocimientos necesarios para lograr la meta",
                                "impact": "Medio",
                                "strategies": [
                                    {
                                        "description": "Buscar educación",
                                        "implementation": "Identificar recursos educativos relevantes y dedicar tiempo al aprendizaje",
                                        "effectiveness": "Alta",
                                        "effort_required": "Alto"
                                    },
                                    {
                                        "description": "Buscar mentoría",
                                        "implementation": "Encontrar un mentor o coach que pueda proporcionar orientación",
                                        "effectiveness": "Alta",
                                        "effort_required": "Medio"
                                    }
                                ]
                            }
                        ],
                        "general_approach": "Enfoque proactivo para identificar obstáculos potenciales y desarrollar estrategias para superarlos antes de que ocurran",
                        "prevention_strategies": [
                            "Planificación regular y revisión de progreso",
                            "Mantener una mentalidad flexible y adaptable",
                            "Construir un sistema de apoyo sólido"
                        ],
                        "contingency_plan": "Si se encuentra con un obstáculo imprevisto, tomar un paso atrás, evaluar la situación, ajustar el plan según sea necesario y continuar avanzando"
                    }
            
            return response
        except Exception as e:
            logger.error(f"Error en _generate_obstacle_management_plan: {str(e)}")
            # Devolver un plan básico en caso de error
            return {
                "goal": "Meta relacionada",
                "obstacles": [
                    {
                        "name": "Falta de tiempo",
                        "description": "Dificultad para encontrar tiempo para dedicar a la meta",
                        "impact": "Alto",
                        "strategies": [
                            {
                                "description": "Priorizar y programar",
                                "implementation": "Reservar bloques de tiempo específicos en el calendario",
                                "effectiveness": "Alta",
                                "effort_required": "Bajo"
                            }
                        ]
                    }
                ],
                "general_approach": "Enfoque proactivo para identificar y superar obstáculos",
                "prevention_strategies": ["Planificación regular"],
                "contingency_plan": "Ajustar el plan según sea necesario"
            }
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()

    async def process_async(self, input_text: str, user_id: Optional[str] = None, session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Implementación asíncrona del procesamiento del agente MotivationBehaviorCoach.

        Sobrescribe el método de la clase base para proporcionar la implementación
        específica del agente especializado en motivación y cambio de comportamiento.

        Args:
            input_text (str): Texto de entrada del usuario.
            user_id (Optional[str]): ID del usuario (opcional).
            session_id (Optional[str]): ID de la sesión (opcional).
            **kwargs: Argumentos adicionales como context, parameters, etc.

        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente.
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
            metadata = {
                "status": "success",
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            payload = {
                "response": response,
                "message": response,
                "artifacts": artifacts
            }
            return {"metadata": metadata, "payload": payload}
            
        except Exception as e:
            logger.error(f"Error en MotivationBehaviorCoach: {e}", exc_info=True)
            execution_time = time.time() - start_time if 'start_time' in locals() else 0.0
            
            metadata = {
                "status": "error",
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            payload = {
                "error": str(e),
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud sobre motivación y comportamiento."
            }
            return {"metadata": metadata, "payload": payload}

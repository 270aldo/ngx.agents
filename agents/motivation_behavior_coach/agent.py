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
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from core.logging_config import get_logger

# Importar Skill y Toolkit desde adk.agent
from adk.agent import Skill
from adk.toolkit import Toolkit

# Importar el servicio de clasificación de programas y definiciones
from services.program_classification_service import ProgramClassificationService
from agents.shared.program_definitions import get_program_definition

# Importar esquemas para las skills
from agents.motivation_behavior_coach.schemas import (
    HabitFormationInput, HabitFormationOutput,
    GoalSettingInput, GoalSettingOutput,
    MotivationStrategiesInput, MotivationStrategiesOutput,
    BehaviorChangeInput, BehaviorChangeOutput,
    ObstacleManagementInput, ObstacleManagementOutput,
    HabitPlanArtifact, GoalPlanArtifact,
    MotivationStrategiesArtifact, BehaviorChangePlanArtifact,
    ObstacleManagementArtifact,
    # Importar modelos adicionales para las skills
    HabitPlan, HabitStep,
    SmartGoal, Milestone, Timeline, Obstacle, TrackingSystem, GoalPlan,
    MotivationStrategy,
    BehaviorChangeStage, BehaviorChangePlan,
    ObstacleAnalysis, ObstacleSolution
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
    
    AGENT_ID = "motivation_behavior_coach"
    AGENT_NAME = "NGX Motivation & Behavior Coach"
    AGENT_DESCRIPTION = "Especialista en motivación, formación de hábitos y cambio de comportamiento"
    DEFAULT_INSTRUCTION = "Eres un coach especializado en motivación y cambio de comportamiento. Tu función es ayudar a los usuarios a establecer hábitos saludables, mantener la motivación, superar obstáculos psicológicos y lograr cambios de comportamiento duraderos."
    DEFAULT_MODEL = "gemini-1.5-flash"
    
    def __init__(
        self,
        state_manager = None,
        mcp_toolkit: Optional[MCPToolkit] = None,
        a2a_server_url: Optional[str] = None,
        model: Optional[str] = None,
        instruction: Optional[str] = None,
        agent_id: str = AGENT_ID,
        name: str = AGENT_NAME,
        description: str = AGENT_DESCRIPTION,
        **kwargs
    ):
        """
        Inicializa el agente MotivationBehaviorCoach.
        
        Args:
            state_manager: Gestor de estado para persistencia
            mcp_toolkit: Toolkit de MCP para herramientas adicionales
            a2a_server_url: URL del servidor A2A
            model: Modelo de Gemini a utilizar
            instruction: Instrucciones del sistema
            agent_id: ID del agente
            name: Nombre del agente
            description: Descripción del agente
            **kwargs: Argumentos adicionales para la clase base
        """
        _model = model or self.DEFAULT_MODEL
        _instruction = instruction or self.DEFAULT_INSTRUCTION
        _mcp_toolkit = mcp_toolkit if mcp_toolkit is not None else MCPToolkit()
        
        # Definir las skills antes de llamar al constructor de ADKAgent
        self.skills = [
            Skill(
                name="habit_formation",
                description="Técnicas para establecer y mantener hábitos saludables basadas en ciencia del comportamiento",
                handler=self._skill_habit_formation,
                input_schema=HabitFormationInput,
                output_schema=HabitFormationOutput
            ),
            Skill(
                name="motivation_strategies",
                description="Estrategias basadas en evidencia para mantener la motivación a largo plazo y superar barreras psicológicas",
                handler=self._skill_motivation_strategies,
                input_schema=MotivationStrategiesInput,
                output_schema=MotivationStrategiesOutput
            ),
            Skill(
                name="behavior_change",
                description="Métodos para lograr cambios de comportamiento duraderos basados en modelos psicológicos validados",
                handler=self._skill_behavior_change,
                input_schema=BehaviorChangeInput,
                output_schema=BehaviorChangeOutput
            ),
            Skill(
                name="goal_setting",
                description="Técnicas para establecer metas efectivas usando el marco SMART y otros modelos validados",
                handler=self._skill_goal_setting,
                input_schema=GoalSettingInput,
                output_schema=GoalSettingOutput
            ),
            Skill(
                name="obstacle_management",
                description="Estrategias para identificar, anticipar y superar obstáculos en el camino hacia los objetivos",
                handler=self._skill_obstacle_management,
                input_schema=ObstacleManagementInput,
                output_schema=ObstacleManagementOutput
            )
        ]
        
        # Definir las capacidades del agente
        _capabilities = [
            "habit_formation", 
            "motivation_strategies", 
            "behavior_change", 
            "goal_setting",
            "obstacle_management"
        ]
        
        # Crear un toolkit de ADK
        adk_toolkit = Toolkit()
        
        # Inicializar el agente ADK
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            model=_model,
            instruction=_instruction,
            state_manager=None,  # Ya no usamos el state_manager original
            adk_toolkit=adk_toolkit,
            capabilities=_capabilities,
            a2a_server_url=a2a_server_url,
            **kwargs
        )
        
        # Configurar clientes adicionales
        self.gemini_client = GeminiClient(model_name=self.model)
        self.supabase_client = SupabaseClient()
        
        # Inicializar el servicio de clasificación de programas
        self.program_classification_service = ProgramClassificationService(self.gemini_client)
        
        # Configurar sistema de instrucciones para Gemini
        self.system_instructions = """Eres un coach especializado en motivación y cambio de comportamiento. 
        Tu función es ayudar a los usuarios a establecer hábitos saludables, 
        mantener la motivación, superar obstáculos psicológicos y lograr 
        cambios de comportamiento duraderos. Utiliza principios de psicología 
        positiva, ciencia del comportamiento y técnicas de coaching validadas."""
        
        # Inicializar Vertex AI
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform (Vertex AI SDK) inicializado correctamente para MotivationBehaviorCoach.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform para MotivationBehaviorCoach: {e}", exc_info=True)
            
        logger.info(f"{self.name} ({self.agent_id}) inicializado con integración oficial de Google ADK.")
    
    async def _get_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el adaptador del StateManager.

        Args:
            user_id (Optional[str]): ID del usuario.
            session_id (Optional[str]): ID de la sesión.

        Returns:
            Dict[str, Any]: Contexto de la conversación.
        """
        try:
            # Intentar cargar desde el adaptador del StateManager
            if user_id and session_id:
                try:
                    state_data = await state_manager_adapter.load_state(user_id, session_id)
                    if state_data and isinstance(state_data, dict):
                        logger.debug(f"Contexto cargado desde adaptador del StateManager para user_id={user_id}, session_id={session_id}")
                        return state_data
                except Exception as e:
                    logger.warning(f"Error al cargar contexto desde adaptador del StateManager: {e}")
            
            # Si no hay contexto o hay error, crear uno nuevo
            return {
                "conversation_history": [],
                "user_profile": {},
                "habit_plans": [],
                "goal_plans": [],
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
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
        Actualiza el contexto de la conversación en el adaptador del StateManager.

        Args:
            context (Dict[str, Any]): Contexto actualizado.
            user_id (str): ID del usuario.
            session_id (str): ID de la sesión.
        """
        try:
            # Actualizar la marca de tiempo
            context["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Guardar el contexto en el adaptador del StateManager
            await state_manager_adapter.save_state(user_id, session_id, context)
            logger.info(f"Contexto actualizado en adaptador del StateManager para user_id={user_id}, session_id={session_id}")
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)
    
    async def _consult_other_agent(self, agent_id: str, query: str, user_id: Optional[str] = None, session_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta a otro agente utilizando el adaptador de A2A.
        
        Args:
            agent_id: ID del agente a consultar
            query: Consulta a enviar al agente
            user_id: ID del usuario
            session_id: ID de la sesión
            context: Contexto adicional para la consulta
            
        Returns:
            Dict[str, Any]: Respuesta del agente consultado
        """
        try:
            # Crear contexto para la consulta
            task_context = {
                "user_id": user_id,
                "session_id": session_id,
                "additional_context": context or {}
            }
            
            # Llamar al agente utilizando el adaptador de A2A
            response = await a2a_adapter.call_agent(
                agent_id=agent_id,
                user_input=query,
                context=task_context
            )
            
            logger.info(f"Respuesta recibida del agente {agent_id}")
            return response
        except Exception as e:
            logger.error(f"Error al consultar al agente {agent_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "output": f"Error al consultar al agente {agent_id}",
                "agent_id": agent_id,
                "agent_name": agent_id
            }
    
    # --- Métodos de Habilidades (Skills) ---
    
    async def _skill_habit_formation(self, input_data: HabitFormationInput) -> HabitFormationOutput:
        """
        Skill para generar un plan de hábitos estructurado.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            HabitFormationOutput: Plan de hábitos generado
        """
        logger.info(f"Ejecutando habilidad: _skill_habit_formation con input: {input_data.user_input[:30]}...")
        
        try:
            # Generar el plan de hábitos
            habit_data = await self._generate_habit_plan(input_data.user_input, input_data.user_profile)
            
            # Crear los pasos del hábito
            steps = []
            for step_data in habit_data.get("steps", []):
                if isinstance(step_data, dict):
                    steps.append(HabitStep(
                        description=step_data.get("description", "Paso del hábito"),
                        timeframe=step_data.get("timeframe", "1 semana"),
                        difficulty=step_data.get("difficulty", "Media")
                    ))
                elif isinstance(step_data, str):
                    steps.append(HabitStep(
                        description=step_data,
                        timeframe="Según sea necesario",
                        difficulty="Media"
                    ))
            
            # Si no hay pasos, crear al menos uno predeterminado
            if not steps:
                steps.append(HabitStep(
                    description="Comenzar con una versión mínima del hábito",
                    timeframe="1 semana",
                    difficulty="Baja"
                ))
            
            # Crear el plan de hábitos
            habit_plan = HabitPlan(
                habit_name=habit_data.get("habit", "Hábito personalizado"),
                cue=habit_data.get("cue", "Señal para iniciar el hábito"),
                routine=habit_data.get("routine", "Acción a realizar"),
                reward=habit_data.get("reward", "Recompensa por completar el hábito"),
                implementation_intention=habit_data.get("implementation_intention", "Cuando X, haré Y"),
                steps=steps,
                tracking_method=habit_data.get("tracking_method", "Registro diario")
            )
            
            # Crear la salida de la skill
            return HabitFormationOutput(
                habit_plan=habit_plan,
                tips=habit_data.get("tips", ["Comienza pequeño", "Sé consistente", "Celebra los éxitos"]),
                obstacles=habit_data.get("obstacles", [{"obstacle": "Falta de tiempo", "strategy": "Priorizar"}]),
                consistency_strategies=habit_data.get("consistency_strategies", ["Establecer recordatorios"])
            )
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_habit_formation': {e}", exc_info=True)
            # En caso de error, devolver un plan básico
            return HabitFormationOutput(
                habit_plan=HabitPlan(
                    habit_name="Hábito personalizado",
                    cue="Señal para iniciar el hábito",
                    routine="Acción a realizar",
                    reward="Recompensa por completar el hábito",
                    implementation_intention="Cuando X, haré Y",
                    steps=[HabitStep(
                        description="Comenzar con una versión mínima del hábito",
                        timeframe="1 semana",
                        difficulty="Baja"
                    )],
                    tracking_method="Registro diario"
                ),
                tips=["Comienza pequeño", "Sé consistente", "Celebra los éxitos"],
                obstacles=[{"obstacle": "Falta de tiempo", "strategy": "Priorizar"}],
                consistency_strategies=["Establecer recordatorios"]
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
        # Preparar información del usuario si está disponible
        user_info = ""
        if user_profile:
            user_info = (
                f"Información del usuario:\n"
                f"- Edad: {user_profile.get('age', 'No disponible')}\n"
                f"- Género: {user_profile.get('gender', 'No disponible')}\n"
                f"- Objetivos: {user_profile.get('goals', 'No disponible')}\n"
                f"- Preferencias: {user_profile.get('preferences', 'No disponible')}\n"
                f"- Historial: {user_profile.get('history', 'No disponible')}"
            )
        
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
                        "cue": "Después de una actividad existente",
                        "routine": "Acción específica a realizar",
                        "reward": "Recompensa inmediata después de completar el hábito",
                        "implementation_intention": "Cuando [situación específica], yo [acción específica]",
                        "duration": "66 días (tiempo promedio para formar un hábito)",
                        "steps": [
                            {
                                "description": "Paso 1: Comenzar con una versión mínima del hábito",
                                "timeframe": "Semana 1-2",
                                "difficulty": "Baja"
                            },
                            {
                                "description": "Paso 2: Incrementar gradualmente la dificultad",
                                "timeframe": "Semana 3-4",
                                "difficulty": "Media"
                            },
                            {
                                "description": "Paso 3: Mantener consistencia diaria",
                                "timeframe": "Semana 5-10",
                                "difficulty": "Alta"
                            }
                        ],
                        "tracking_method": "Registro diario en aplicación o diario",
                        "tips": [
                            "Comienza con una versión tan pequeña del hábito que sea imposible fallar",
                            "Ancla el nuevo hábito a uno existente para crear un recordatorio natural",
                            "Celebra inmediatamente después de completar el hábito para reforzar la conducta"
                        ],
                        "obstacles": [
                            {"obstacle": "Falta de tiempo", "strategy": "Reducir el hábito a su versión mínima viable"},
                            {"obstacle": "Olvido", "strategy": "Establecer recordatorios visuales en el entorno"},
                            {"obstacle": "Pérdida de motivación", "strategy": "Conectar el hábito con valores personales profundos"}
                        ],
                        "consistency_strategies": [
                            "Regla de nunca fallar dos veces seguidas",
                            "Seguimiento visual del progreso (ej. calendario marcado)",
                            "Compromiso público con amigos o familia"
                        ]
                    }
            
            return response
        except Exception as e:
            logger.error(f"Error en _generate_habit_plan: {str(e)}")
            # Devolver un plan de hábitos básico en caso de error
            return {
                "habit": "Hábito personalizado",
                "cue": "Después de una actividad existente",
                "routine": "Acción específica a realizar",
                "reward": "Recompensa inmediata",
                "implementation_intention": "Cuando [situación], yo [acción]",
                "duration": "66 días",
                "steps": [
                    {
                        "description": "Comenzar con una versión mínima del hábito",
                        "timeframe": "Semana 1-2",
                        "difficulty": "Baja"
                    }
                ],
                "tracking_method": "Registro diario",
                "tips": ["Comienza pequeño", "Sé consistente", "Celebra los éxitos"],
                "obstacles": [{"obstacle": "Falta de tiempo", "strategy": "Priorizar"}],
                "consistency_strategies": ["Establecer recordatorios"]
            }
    
    async def _skill_goal_setting(self, input_data: GoalSettingInput) -> GoalSettingOutput:
        """
        Skill para el establecimiento de metas.
        
        Genera un plan estructurado para establecer y alcanzar metas siguiendo el formato SMART.
        
        Args:
            input_data: Parámetros de entrada para la skill
                
        Returns:
            GoalSettingOutput: Plan de metas generado
        """
        logger.info(f"Ejecutando habilidad: _skill_goal_setting con input: {input_data.user_input[:30]}...")
        
        try:
            # Generar el plan de metas usando el input de Pydantic
            goal_plan_data = await self._generate_goal_plan(
                input_data.user_input, 
                input_data.user_profile
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
        try:
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
            
            Devuelve el resultado en formato JSON estructurado.
            """
            
            # Añadir información del perfil si está disponible
            if user_profile:
                prompt += (
                    "\n\nConsidera la siguiente información del usuario:\n"
                    f"- Objetivos: {user_profile.get('goals', 'No disponible')}\n"
                    f"- Desafíos: {user_profile.get('challenges', 'No disponible')}\n"
                    f"- Preferencias: {user_profile.get('preferences', 'No disponible')}\n"
                    f"- Historial: {user_profile.get('history', 'No disponible')}"
                )
            
            # Generar el plan de metas
            response = await self.gemini_client.generate_structured_output(prompt)
            
            # Si la respuesta no es un diccionario, intentar convertirla
            if not isinstance(response, dict):
                try:
                    import json
                    response = json.loads(response)
                except Exception:
                    # Si no se puede convertir, crear un diccionario básico
                    response = {
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
    
    async def _skill_motivation_strategies(self, input_data: MotivationStrategiesInput) -> MotivationStrategiesOutput:
        """
        Skill para generar estrategias de motivación personalizadas.
        
        Genera estrategias de motivación basadas en la ciencia del comportamiento y la psicología positiva.
        
        Args:
            input_data: Parámetros de entrada para la skill
                
        Returns:
            MotivationStrategiesOutput: Estrategias de motivación generadas
        """
        logger.info(f"Ejecutando habilidad: _skill_motivation_strategies con input: {input_data.user_input[:30]}...")
        
        try:
            # Generar las estrategias de motivación
            motivation_data = await self._generate_motivation_strategies(
                input_data.user_input, 
                input_data.user_profile
            )
            
            # Obtener el tipo de programa utilizado para las estrategias
            program_type = motivation_data.get("program_type", "GENERAL")
            program_objective = motivation_data.get("program_objective", "")
            
            # Crear las estrategias de motivación
            strategies = []
            for strategy_data in motivation_data.get("strategies", []):
                if isinstance(strategy_data, dict):
                    strategies.append(MotivationStrategy(
                        name=strategy_data.get("name", "Estrategia de motivación"),
                        description=strategy_data.get("description", "Descripción de la estrategia"),
                        implementation=strategy_data.get("implementation", "Pasos para implementar"),
                        science_behind=strategy_data.get("science_behind", "Respaldado por investigaciones en psicología positiva"),
                        example=strategy_data.get("example", f"Ejemplo de aplicación para programa {program_type}")
                    ))
                elif isinstance(strategy_data, str):
                    strategies.append(MotivationStrategy(
                        name=f"Estrategia: {strategy_data[:30]}...",
                        description=strategy_data,
                        implementation="Implementar según las circunstancias personales",
                        science_behind="Basado en principios de psicología positiva",
                        example=f"Ejemplo personalizado para programa {program_type}"
                    ))
            
            # Si no hay estrategias, crear al menos una predeterminada
            if not strategies:
                strategies.append(MotivationStrategy(
                    name="Visualización del éxito",
                    description="Visualizar el resultado deseado para aumentar la motivación",
                    implementation="Dedica 5 minutos cada mañana a visualizar el logro de tus objetivos",
                    science_behind="Basado en investigaciones sobre neuroplasticidad y priming mental",
                    example=f"Un atleta de programa {program_type} que visualiza su victoria antes de la competencia"
                ))
            
            # Personalizar el análisis según el programa
            analysis = motivation_data.get("analysis", "Análisis motivacional personalizado")
            if program_objective:
                analysis = f"[{program_type}] {analysis}\n\nObjetivo del programa: {program_objective}"
            
            # Personalizar el enfoque a largo plazo según el programa
            long_term_approach = motivation_data.get("long_term_approach", "Enfoque a largo plazo para mantener la motivación")
            if program_type == "PRIME":
                long_term_approach = f"[PRIME] {long_term_approach}\n\nEnfoque en rendimiento sostenible y progresión continua."
            elif program_type == "LONGEVITY":
                long_term_approach = f"[LONGEVITY] {long_term_approach}\n\nEnfoque en hábitos sostenibles y mejora de biomarcadores a largo plazo."
            
            # Crear la salida de la skill
            return MotivationStrategiesOutput(
                analysis=analysis,
                strategies=strategies,
                daily_practices=motivation_data.get("daily_practices", ["Práctica diaria recomendada"]),
                long_term_approach=long_term_approach,
                program_type=program_type
            )
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_motivation_strategies': {e}", exc_info=True)
            # En caso de error, devolver estrategias básicas
            return MotivationStrategiesOutput(
                analysis="No se pudo generar un análisis completo debido a un error",
                strategies=[MotivationStrategy(
                    name="Visualización del éxito",
                    description="Visualizar el resultado deseado para aumentar la motivación",
                    implementation="Dedica 5 minutos cada mañana a visualizar el logro de tus objetivos",
                    science_behind="Basado en investigaciones sobre neuroplasticidad y priming mental",
                    example="Un atleta que visualiza su victoria antes de la competencia"
                )],
                daily_practices=["Práctica de gratitud diaria", "Meditación de 5 minutos", "Registro de logros"],
                long_term_approach="Enfoque gradual y consistente, celebrando pequeños logros en el camino"
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
        # Determinar el tipo de programa del usuario para personalizar las estrategias
        context = {
            "user_profile": user_profile or {},
            "goals": user_profile.get("goals", []) if user_profile else []
        }
        
        try:
            # Clasificar el tipo de programa del usuario
            program_type = await self.program_classification_service.classify_program_type(context)
            logger.info(f"Tipo de programa determinado para estrategias de motivación: {program_type}")
            
            # Obtener definición del programa para personalizar las estrategias
            program_def = get_program_definition(program_type)
            
            # Preparar contexto específico del programa
            program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
            
            if program_def:
                program_context += f"- {program_def.get('description', '')}\n"
                program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                
                # Añadir consideraciones especiales para las estrategias según el programa
                if program_type == "PRIME":
                    program_context += "\nConsideraciones especiales para motivación en PRIME:\n"
                    program_context += "- Enfoque en motivación para rendimiento y superación personal\n"
                    program_context += "- Estrategias para mantener la consistencia en entrenamientos intensos\n"
                    program_context += "- Técnicas para superar mesetas de rendimiento\n"
                    program_context += "- Motivación basada en logros y mejoras medibles\n"
                elif program_type == "LONGEVITY":
                    program_context += "\nConsideraciones especiales para motivación en LONGEVITY:\n"
                    program_context += "- Enfoque en motivación para hábitos sostenibles a largo plazo\n"
                    program_context += "- Estrategias para mantener la consistencia en prácticas de bienestar\n"
                    program_context += "- Técnicas para valorar mejoras en biomarcadores y salud general\n"
                    program_context += "- Motivación basada en calidad de vida y bienestar\n"
        except Exception as e:
            logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando estrategias generales.")
            program_type = "GENERAL"
            program_context = ""
            program_def = None
        
        prompt = (
            f"{self.system_instructions}\n\n"
            f"Eres un coach especializado en motivación y cambio de comportamiento para programas {program_type}.\n\n"
            f"Genera estrategias de motivación personalizadas basadas en la siguiente solicitud:\n\n"
            f"\"{user_input}\"\n\n"
            f"{program_context}\n\n"
            f"El resultado debe incluir:\n"
            f"1. Análisis motivacional de la situación específico para el programa {program_type}\n"
            f"2. Lista de estrategias de motivación aplicables (mínimo 3) adaptadas al programa {program_type}\n"
            f"3. Prácticas diarias recomendadas para mantener la motivación en este programa\n"
            f"4. Enfoque a largo plazo para sostener el progreso\n\n"
            f"Para cada estrategia, incluye:\n"
            f"- Nombre de la estrategia\n"
            f"- Descripción detallada\n"
            f"- Pasos para implementarla\n"
            f"- Ciencia detrás de la estrategia\n"
            f"- Ejemplo de aplicación específico para el programa {program_type}\n\n"
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
                                "science_behind": "Basado en investigaciones sobre neuroplasticidad y priming mental",
                                "example": "Un atleta que visualiza su victoria antes de la competencia"
                            },
                            {
                                "name": "Establecimiento de micro-metas",
                                "description": "Dividir objetivos grandes en pequeñas metas alcanzables",
                                "implementation": "Identifica el próximo paso más pequeño y concéntrate solo en él",
                                "science_behind": "Basado en la teoría del flujo y la psicología del logro",
                                "example": "Escribir 100 palabras al día en lugar de proponerse terminar un libro"
                            },
                            {
                                "name": "Técnica Pomodoro",
                                "description": "Trabajar en intervalos de tiempo enfocados",
                                "implementation": "Trabaja durante 25 minutos, luego descansa 5 minutos",
                                "science_behind": "Basado en investigaciones sobre atención y productividad",
                                "example": "Estudiar con intervalos de descanso programados"
                            }
                        ],
                        "daily_practices": [
                            "Práctica de gratitud diaria",
                            "Meditación de 5 minutos",
                            "Registro de logros"
                        ],
                        "long_term_approach": "Enfoque gradual y consistente, celebrando pequeños logros en el camino"
                    }
            
            # Añadir información del programa al resultado
            try:
                response["program_type"] = program_type
                if program_def:
                    response["program_objective"] = program_def.get("objective", "")
            except Exception as e:
                logger.error(f"Error al añadir información del programa: {str(e)}")
            
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
                        "science_behind": "Basado en investigaciones sobre neuroplasticidad y priming mental",
                        "example": "Un atleta que visualiza su victoria antes de la competencia"
                    }
                ],
                "daily_practices": ["Práctica de gratitud diaria"],
                "long_term_approach": "Enfoque gradual y consistente"
            }
    
    async def _skill_behavior_change(self, input_data: BehaviorChangeInput) -> BehaviorChangeOutput:
        """
        Skill para generar un plan de cambio de comportamiento personalizado.
        
        Genera un plan estructurado para cambiar comportamientos basado en la ciencia del comportamiento.
        
        Args:
            input_data: Parámetros de entrada para la skill
                
        Returns:
            BehaviorChangeOutput: Plan de cambio de comportamiento generado
        """
        logger.info(f"Ejecutando habilidad: _skill_behavior_change con input: {input_data.user_input[:30]}...")
        
        try:
            # Generar el plan de cambio de comportamiento
            behavior_data = await self._generate_behavior_change_plan(
                input_data.user_input, 
                input_data.user_profile
            )
            
            # Crear las etapas del plan
            stages = []
            for stage_data in behavior_data.get("stages", []):
                if isinstance(stage_data, dict):
                    stages.append(BehaviorChangeStage(
                        stage_name=stage_data.get("stage_name", "Etapa del cambio"),
                        description=stage_data.get("description", "Descripción de la etapa"),
                        strategies=stage_data.get("strategies", ["Estrategia recomendada"]),
                        duration=stage_data.get("duration", "2-4 semanas"),
                        success_indicators=stage_data.get("success_indicators", ["Indicador de éxito"])
                    ))
                elif isinstance(stage_data, str):
                    stages.append(BehaviorChangeStage(
                        stage_name=f"Etapa: {stage_data[:30]}...",
                        description=stage_data,
                        strategies=["Estrategia personalizada"],
                        duration="Variable",
                        success_indicators=["Progreso visible"]
                    ))
            
            # Si no hay etapas, crear al menos una predeterminada
            if not stages:
                stages.append(BehaviorChangeStage(
                    stage_name="Etapa de preparación",
                    description="Preparación para el cambio de comportamiento",
                    strategies=["Identificar desencadenantes", "Establecer metas claras"],
                    duration="2 semanas",
                    success_indicators=["Plan detallado completado", "Compromiso establecido"]
                ))
            
            # Crear el plan de cambio de comportamiento
            behavior_plan = BehaviorChangePlan(
                target_behavior=behavior_data.get("target_behavior", "Comportamiento objetivo"),
                current_state=behavior_data.get("current_state", "Estado actual del comportamiento"),
                desired_state=behavior_data.get("desired_state", "Estado deseado del comportamiento"),
                stages=stages,
                psychological_techniques=behavior_data.get("psychological_techniques", ["Técnica psicológica recomendada"]),
                environmental_adjustments=behavior_data.get("environmental_adjustments", ["Ajuste ambiental recomendado"]),
                support_systems=behavior_data.get("support_systems", ["Sistema de apoyo recomendado"])
            )
            
            # Crear la salida de la skill
            return BehaviorChangeOutput(
                behavior_plan=behavior_plan,
                estimated_timeline=behavior_data.get("estimated_timeline", "3-6 meses"),
                success_probability_factors=behavior_data.get("success_probability_factors", ["Factor que afecta la probabilidad de éxito"])
            )
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_behavior_change': {e}", exc_info=True)
            # En caso de error, devolver un plan básico
            return BehaviorChangeOutput(
                behavior_plan=BehaviorChangePlan(
                    target_behavior="Comportamiento objetivo",
                    current_state="Estado actual",
                    desired_state="Estado deseado",
                    stages=[BehaviorChangeStage(
                        stage_name="Etapa de preparación",
                        description="Preparación para el cambio",
                        strategies=["Identificar desencadenantes"],
                        duration="2 semanas",
                        success_indicators=["Plan completado"]
                    )],
                    psychological_techniques=["Técnica recomendada"],
                    environmental_adjustments=["Ajuste recomendado"],
                    support_systems=["Sistema de apoyo"]
                ),
                estimated_timeline="3-6 meses",
                success_probability_factors=["Compromiso personal"]
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
            f"4. Etapas del cambio (mínimo 3)\n"
            f"5. Técnicas psicológicas recomendadas\n"
            f"6. Ajustes ambientales recomendados\n"
            f"7. Sistemas de apoyo recomendados\n"
            f"8. Línea de tiempo estimada\n"
            f"9. Factores que afectan la probabilidad de éxito\n\n"
            f"Para cada etapa, incluye:\n"
            f"- Nombre de la etapa\n"
            f"- Descripción detallada\n"
            f"- Estrategias específicas\n"
            f"- Duración estimada\n"
            f"- Indicadores de éxito\n\n"
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
                        "stages": [
                            {
                                "stage_name": "Etapa de preparación",
                                "description": "Preparación para el cambio de comportamiento",
                                "strategies": ["Identificar desencadenantes", "Establecer metas claras"],
                                "duration": "2 semanas",
                                "success_indicators": ["Plan detallado completado", "Compromiso establecido"]
                            },
                            {
                                "stage_name": "Etapa de acción",
                                "description": "Implementación activa del cambio",
                                "strategies": ["Práctica diaria", "Seguimiento de progreso"],
                                "duration": "4-8 semanas",
                                "success_indicators": ["Consistencia en nuevos comportamientos", "Reducción de comportamientos antiguos"]
                            },
                            {
                                "stage_name": "Etapa de mantenimiento",
                                "description": "Consolidación del nuevo comportamiento",
                                "strategies": ["Prevención de recaídas", "Integración en la rutina diaria"],
                                "duration": "3-6 meses",
                                "success_indicators": ["Automatización del comportamiento", "Resistencia a tentaciones"]
                            }
                        ],
                        "psychological_techniques": [
                            "Reestructuración cognitiva",
                            "Establecimiento de intenciones de implementación",
                            "Técnicas de mindfulness"
                        ],
                        "environmental_adjustments": [
                            "Modificación del entorno físico",
                            "Eliminación de desencadenantes",
                            "Creación de recordatorios visuales"
                        ],
                        "support_systems": [
                            "Grupo de apoyo",
                            "Mentor o coach",
                            "Aplicación de seguimiento"
                        ],
                        "estimated_timeline": "3-6 meses para cambio sostenible",
                        "success_probability_factors": [
                            "Nivel de compromiso personal",
                            "Calidad del sistema de apoyo",
                            "Manejo efectivo de recaídas"
                        ]
                    }
            
            return response
        except Exception as e:
            logger.error(f"Error en _generate_behavior_change_plan: {str(e)}")
            # Devolver un plan básico en caso de error
            return {
                "target_behavior": "Comportamiento objetivo",
                "current_state": "Estado actual",
                "desired_state": "Estado deseado",
                "stages": [
                    {
                        "stage_name": "Etapa de preparación",
                        "description": "Preparación para el cambio",
                        "strategies": ["Identificar desencadenantes"],
                        "duration": "2 semanas",
                        "success_indicators": ["Plan completado"]
                    }
                ],
                "psychological_techniques": ["Técnica recomendada"],
                "environmental_adjustments": ["Ajuste recomendado"],
                "support_systems": ["Sistema de apoyo"],
                "estimated_timeline": "3-6 meses",
                "success_probability_factors": ["Compromiso personal"]
            }
    
    async def _skill_obstacle_management(self, input_data: ObstacleManagementInput) -> ObstacleManagementOutput:
        """
        Skill para generar estrategias de manejo de obstáculos personalizadas.
        
        Genera estrategias para superar obstáculos específicos que impiden el logro de metas.
        
        Args:
            input_data: Parámetros de entrada para la skill
                
        Returns:
            ObstacleManagementOutput: Estrategias de manejo de obstáculos generadas
        """
        logger.info(f"Ejecutando habilidad: _skill_obstacle_management con input: {input_data.user_input[:30]}...")
        
        try:
            # Generar el plan de manejo de obstáculos
            obstacle_data = await self._generate_obstacle_management_plan(
                input_data.user_input, 
                input_data.user_profile
            )
            
            # Crear el análisis del obstáculo
            obstacle_analysis = ObstacleAnalysis(
                nature=obstacle_data.get("nature", "Naturaleza del obstáculo"),
                impact=obstacle_data.get("impact", "Impacto del obstáculo"),
                frequency=obstacle_data.get("frequency", "Frecuencia con la que aparece"),
                triggers=obstacle_data.get("triggers", ["Desencadenante del obstáculo"]),
                past_attempts=obstacle_data.get("past_attempts", "No hay intentos previos registrados")
            )
            
            # Crear la solución principal
            primary_solution_data = obstacle_data.get("primary_solution", {})
            primary_solution = ObstacleSolution(
                strategy=primary_solution_data.get("strategy", "Estrategia principal"),
                implementation=primary_solution_data.get("implementation", "Pasos para implementar"),
                expected_outcome=primary_solution_data.get("expected_outcome", "Resultado esperado"),
                alternative_approaches=primary_solution_data.get("alternative_approaches", ["Enfoque alternativo"]),
                resources_needed=primary_solution_data.get("resources_needed", ["Recurso necesario"])
            )
            
            # Crear soluciones alternativas
            alternative_solutions = []
            for solution_data in obstacle_data.get("alternative_solutions", []):
                if isinstance(solution_data, dict):
                    alternative_solutions.append(ObstacleSolution(
                        strategy=solution_data.get("strategy", "Estrategia alternativa"),
                        implementation=solution_data.get("implementation", "Pasos para implementar"),
                        expected_outcome=solution_data.get("expected_outcome", "Resultado esperado"),
                        alternative_approaches=solution_data.get("alternative_approaches", ["Enfoque alternativo"]),
                        resources_needed=solution_data.get("resources_needed", ["Recurso necesario"])
                    ))
            
            # Si no hay soluciones alternativas, crear al menos una predeterminada
            if not alternative_solutions:
                alternative_solutions.append(ObstacleSolution(
                    strategy="Enfoque alternativo",
                    implementation="Implementación alternativa",
                    expected_outcome="Resultado esperado alternativo",
                    alternative_approaches=["Otro enfoque posible"],
                    resources_needed=["Recurso adicional"]
                ))
            
            # Crear la salida de la skill
            return ObstacleManagementOutput(
                obstacle_analysis=obstacle_analysis,
                primary_solution=primary_solution,
                alternative_solutions=alternative_solutions,
                prevention_strategies=obstacle_data.get("prevention_strategies", ["Estrategia de prevención"]),
                mindset_adjustments=obstacle_data.get("mindset_adjustments", ["Ajuste de mentalidad recomendado"])
            )
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_obstacle_management': {e}", exc_info=True)
            # En caso de error, devolver estrategias básicas
            return ObstacleManagementOutput(
                obstacle_analysis=ObstacleAnalysis(
                    nature="Naturaleza del obstáculo",
                    impact="Impacto del obstáculo",
                    frequency="Frecuencia con la que aparece",
                    triggers=["Desencadenante del obstáculo"],
                    past_attempts="No hay intentos previos registrados"
                ),
                primary_solution=ObstacleSolution(
                    strategy="Estrategia principal",
                    implementation="Pasos para implementar",
                    expected_outcome="Resultado esperado",
                    alternative_approaches=["Enfoque alternativo"],
                    resources_needed=["Recurso necesario"]
                ),
                alternative_solutions=[
                    ObstacleSolution(
                        strategy="Enfoque alternativo",
                        implementation="Implementación alternativa",
                        expected_outcome="Resultado esperado alternativo",
                        alternative_approaches=["Otro enfoque posible"],
                        resources_needed=["Recurso adicional"]
                    )
                ],
                prevention_strategies=["Estrategia de prevención"],
                mindset_adjustments=["Ajuste de mentalidad recomendado"]
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
            f"1. Análisis del obstáculo (naturaleza, impacto, frecuencia, desencadenantes, intentos previos)\n"
            f"2. Solución principal (estrategia, implementación, resultado esperado, enfoques alternativos, recursos necesarios)\n"
            f"3. Soluciones alternativas (mínimo 2)\n"
            f"4. Estrategias de prevención\n"
            f"5. Ajustes de mentalidad recomendados\n\n"
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
                        "nature": "Naturaleza del obstáculo",
                        "impact": "Alto",
                        "frequency": "Frecuente",
                        "triggers": ["Situación estresante", "Falta de tiempo", "Presión social"],
                        "past_attempts": "Intentos previos con éxito limitado",
                        "primary_solution": {
                            "strategy": "Estrategia principal recomendada",
                            "implementation": "Pasos detallados para implementar la estrategia",
                            "expected_outcome": "Resultado esperado de la implementación",
                            "alternative_approaches": ["Variación 1", "Variación 2"],
                            "resources_needed": ["Tiempo", "Apoyo social", "Herramientas específicas"]
                        },
                        "alternative_solutions": [
                            {
                                "strategy": "Estrategia alternativa 1",
                                "implementation": "Pasos para implementar esta alternativa",
                                "expected_outcome": "Resultado esperado de esta alternativa",
                                "alternative_approaches": ["Variación A", "Variación B"],
                                "resources_needed": ["Recursos para esta alternativa"]
                            },
                            {
                                "strategy": "Estrategia alternativa 2",
                                "implementation": "Pasos para implementar esta segunda alternativa",
                                "expected_outcome": "Resultado esperado de esta segunda alternativa",
                                "alternative_approaches": ["Variación X", "Variación Y"],
                                "resources_needed": ["Recursos para esta segunda alternativa"]
                            }
                        ],
                        "prevention_strategies": [
                            "Estrategia preventiva 1",
                            "Estrategia preventiva 2",
                            "Estrategia preventiva 3"
                        ],
                        "mindset_adjustments": [
                            "Ajuste de mentalidad 1",
                            "Ajuste de mentalidad 2",
                            "Ajuste de mentalidad 3"
                        ]
                    }
            
            return response
        except Exception as e:
            logger.error(f"Error en _generate_obstacle_management_plan: {str(e)}")
            # Devolver un plan básico en caso de error
            return {
                "nature": "Naturaleza del obstáculo",
                "impact": "Impacto del obstáculo",
                "frequency": "Frecuencia con la que aparece",
                "triggers": ["Desencadenante del obstáculo"],
                "past_attempts": "No hay intentos previos registrados",
                "primary_solution": {
                    "strategy": "Estrategia principal",
                    "implementation": "Pasos para implementar",
                    "expected_outcome": "Resultado esperado",
                    "alternative_approaches": ["Enfoque alternativo"],
                    "resources_needed": ["Recurso necesario"]
                },
                "alternative_solutions": [
                    {
                        "strategy": "Estrategia alternativa",
                        "implementation": "Implementación alternativa",
                        "expected_outcome": "Resultado esperado alternativo",
                        "alternative_approaches": ["Otro enfoque posible"],
                        "resources_needed": ["Recurso adicional"]
                    }
                ],
                "prevention_strategies": ["Estrategia de prevención"],
                "mindset_adjustments": ["Ajuste de mentalidad recomendado"]
            }

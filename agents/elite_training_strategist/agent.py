"""
Agente especializado en diseñar y periodizar programas de entrenamiento 
para atletas de alto rendimiento.

Este agente utiliza el modelo Gemini para generar planes de entrenamiento
personalizados basados en los objetivos, nivel y restricciones del atleta.
Implementa los protocolos oficiales A2A y ADK para comunicación entre agentes.
"""
import logging
import json
import os
from typing import Any, Dict, Optional, List, Type, Union
from datetime import datetime

from pydantic import BaseModel, Field

from agents.base.adk_agent import ADKAgent, Skill, create_result
from agents.elite_training_strategist.schemas import (
    GenerateTrainingPlanInput,
    GenerateTrainingPlanOutput,
    AdaptTrainingProgramInput,
    AdaptTrainingProgramOutput,
    AnalyzePerformanceDataInput,
    AnalyzePerformanceDataOutput,
    SetTrainingIntensityVolumeInput,
    SetTrainingIntensityVolumeOutput,
    PrescribeExerciseRoutinesInput,
    PrescribeExerciseRoutinesOutput,
    TrainingPlanArtifact,
)

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from core.state_manager import StateManager
from core.logging_config import get_logger
from google.cloud import aiplatform

# Configurar logger
logger = get_logger(__name__)

# Configurar OpenTelemetry para observabilidad
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    
    # Configurar TracerProvider para trazas
    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer("elite_training_strategist")
    
    # Configurar MeterProvider para métricas
    prometheus_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(metric_readers=[prometheus_reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter("elite_training_strategist")
    
    # Crear contadores y medidores
    request_counter = meter.create_counter(
        name="agent_requests",
        description="Número de solicitudes recibidas por el agente",
        unit="1"
    )
    
    response_time = meter.create_histogram(
        name="agent_response_time",
        description="Tiempo de respuesta del agente en segundos",
        unit="s"
    )
    
    error_count = meter.create_counter(
        name="agent_errors",
        description="Número de errores en el agente",
        unit="1"
    )
    
    has_telemetry = True
except ImportError:
    # Fallback si OpenTelemetry no está disponible
    has_telemetry = False
    tracer = None
    request_counter = None
    response_time = None
    error_count = None

class EliteTrainingStrategist(ADKAgent):
    """
    Agente especializado en el diseño y periodización de programas de entrenamiento
    para atletas de élite y usuarios avanzados, integrando análisis de rendimiento y
    prescripción de ejercicios.
    """

    def __init__(
        self,
        agent_id: str = "elite_training_strategist",
        name: str = "Elite Training Strategist",
        description: str = "Specializes in designing and periodizing training programs for elite athletes.",
        program_type: str = "PRIME",
        mcp_toolkit: Optional[Any] = None,
        a2a_server_url: Optional[str] = None,
        state_manager: Optional[Any] = None,
        model: str = "gemini-1.5-flash",
        instruction: str = "Eres un estratega experto en entrenamiento deportivo.",
        **kwargs
    ):
        agent_id_val = agent_id
        name_val = name
        description_val = description
        
        # Capacidades para BaseAgent y A2A
        capabilities_val = [
            "generate_training_plan", 
            "adapt_training_program", 
            "analyze_performance_data", 
            "set_training_intensity_volume", 
            "prescribe_exercise_routines"
        ]
        
        # Herramientas para Google ADK
        google_adk_tools_val = [
            # Aquí irían las herramientas específicas de Google ADK si se necesitan
        ]
        
        # Skills para A2A
        a2a_skills_val = [
            {
                "name": "generate_training_plan",
                "description": "Genera un plan de entrenamiento completo basado en el perfil y objetivos del usuario.",
                "input_schema": { "type": "object", "properties": { "input_text": {"type": "string"}, "goals": {"type": "array"}, "preferences": {"type": "object"} }, "required": ["input_text"] },
                "output_schema": { "type": "object", "properties": { "training_plan": {"type": "object"} } }
            },
            {
                "name": "adapt_training_program",
                "description": "Adapta un programa de entrenamiento existente basado en nuevos inputs o feedback.",
                "input_schema": { "type": "object", "properties": { "input_text": {"type": "string"}, "existing_plan_id": {"type": "string"}, "adaptation_reason": {"type": "string"} }, "required": ["input_text", "existing_plan_id"] },
                "output_schema": { "type": "object", "properties": { "adapted_plan": {"type": "object"} } }
            },
            {
                "name": "analyze_performance_data",
                "description": "Analiza datos de rendimiento para proporcionar insights y recomendaciones.",
                "input_schema": { "type": "object", "properties": { "input_text": {"type": "string"}, "performance_data": {"type": "object"} }, "required": ["input_text", "performance_data"] },
                "output_schema": { "type": "object", "properties": { "performance_analysis": {"type": "object"} } }
            },
            {
                "name": "set_training_intensity_volume",
                "description": "Establece o ajusta la intensidad y volumen de entrenamiento basado en la periodización y estado del usuario.",
                "input_schema": { "type": "object", "properties": { "input_text": {"type": "string"}, "current_phase": {"type": "string"}, "athlete_feedback": {"type": "object"} }, "required": ["input_text"] },
                "output_schema": { "type": "object", "properties": { "intensity_volume_settings": {"type": "object"} } }
            },
            {
                "name": "prescribe_exercise_routines",
                "description": "Prescribe rutinas de ejercicios específicas, incluyendo variaciones y progresiones.",
                "input_schema": { "type": "object", "properties": { "input_text": {"type": "string"}, "focus_area": {"type": "string"}, "equipment_available": {"type": "array"} }, "required": ["input_text"] },
                "output_schema": { "type": "object", "properties": { "exercise_routines": {"type": "object"} } }
            }
        ]
        
        # Instanciar MCPToolkit si no se provee
        actual_adk_toolkit = mcp_toolkit if mcp_toolkit is not None else MCPToolkit()
        
        # Asegurar que state_manager se pasa a través de kwargs si está presente
        if state_manager:
            kwargs['state_manager'] = state_manager
            
        super().__init__(
            agent_id=agent_id_val,
            name=name_val,
            description=description_val,
            capabilities=capabilities_val,
            model=model,
            instruction=instruction,
            google_adk_tools=google_adk_tools_val,
            a2a_skills=a2a_skills_val,
            adk_toolkit=actual_adk_toolkit,
            a2a_server_url=a2a_server_url,
            endpoint=f"/agents/{agent_id_val}",
            program_type=program_type,
            **kwargs
        )
        
        # Inicializar clientes específicos del agente
        self.gemini_client = GeminiClient(model_name=self.model)
        self.supabase_client = SupabaseClient()
        
        # Configurar telemetría
        self.tracer = tracer
        self.request_counter = request_counter
        self.response_time_metric = response_time
        
        # Inicializar AI Platform si es necesario
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform (Vertex AI SDK) inicializado correctamente para ETS.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform para ETS: {e}", exc_info=True)
            
        if has_telemetry:
            logger.info("OpenTelemetry configurado para EliteTrainingStrategist.")
        else:
            logger.warning("OpenTelemetry no está disponible. EliteTrainingStrategist funcionará sin telemetría detallada.")
            
        # Definir skills
        self.skills = {
            "generate_training_plan": Skill(
                name="generate_training_plan",
                description="Genera un plan de entrenamiento completo basado en el perfil y objetivos del usuario.",
                method=self._skill_generate_training_plan,
                input_schema=GenerateTrainingPlanInput,
                output_schema=GenerateTrainingPlanOutput,
            ),
            "adapt_training_program": Skill(
                name="adapt_training_program",
                description="Adapta un programa de entrenamiento existente basado en nuevos inputs o feedback.",
                method=self._skill_adapt_training_program,
                input_schema=AdaptTrainingProgramInput,
                output_schema=AdaptTrainingProgramOutput,
            ),
            "analyze_performance_data": Skill(
                name="analyze_performance_data",
                description="Analiza datos de rendimiento para proporcionar insights y recomendaciones.",
                method=self._skill_analyze_performance_data,
                input_schema=AnalyzePerformanceDataInput,
                output_schema=AnalyzePerformanceDataOutput,
            ),
            "set_training_intensity_volume": Skill(
                name="set_training_intensity_volume",
                description="Establece o ajusta la intensidad y volumen de entrenamiento basado en la periodización y estado del usuario.",
                method=self._skill_set_training_intensity_volume,
                input_schema=SetTrainingIntensityVolumeInput,
                output_schema=SetTrainingIntensityVolumeOutput,
            ),
            "prescribe_exercise_routines": Skill(
                name="prescribe_exercise_routines",
                description="Prescribe rutinas de ejercicios específicas, incluyendo variaciones y progresiones.",
                method=self._skill_prescribe_exercise_routines,
                input_schema=PrescribeExerciseRoutinesInput,
                output_schema=PrescribeExerciseRoutinesOutput,
            ),
        }
        logger.info(f"Agente {self.name} inicializado con {len(self.skills)} skills: {list(self.skills.keys())}")

    async def _skill_generate_training_plan(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Skill para generar un plan de entrenamiento.
        """
        logger.info(f"Skill '{self._skill_generate_training_plan.__name__}' llamada con entrada: '{input_text[:50]}...'")
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id")
        
        try:
            # Obtener client_profile del contexto
            full_context = await self._get_context(user_id, session_id)
            client_profile_from_context = full_context.get("client_profile", {})

            # Obtener parámetros relevantes de kwargs
            goals = kwargs.get("goals", [input_text] if input_text else [])
            preferences = kwargs.get("preferences", {})
            training_history = kwargs.get("training_history", {})
            duration_weeks = kwargs.get("duration_weeks", 8)

            # Llamar a la lógica interna
            plan_details = await self._generate_training_plan_logic(
                user_profile=client_profile_from_context,
                current_goals=goals,
                current_preferences=preferences,
                training_history=training_history,
                duration_weeks=duration_weeks
            )

            # Crear artefacto
            artifact = self.create_artifact(
                label="TrainingPlan", 
                content_type="application/json",
                data=plan_details
            )

            return create_result(
                status="success", 
                response_data=plan_details,
                artifacts=[artifact]
            )
        except Exception as e:
            logger.error(f"Error en skill '{self._skill_generate_training_plan.__name__}': {e}", exc_info=True)
            return create_result(status="error", error_message=str(e))

    async def _generate_training_plan_logic(
        self, 
        user_profile: Dict[str, Any], 
        current_goals: List[str],
        current_preferences: Optional[Dict[str, Any]] = None,
        training_history: Optional[Dict[str, Any]] = None,
        duration_weeks: int = 8
    ) -> Dict[str, Any]:
        """
        Lógica interna para generar el plan de entrenamiento.
        """
        program_type = self._get_program_type_from_profile(user_profile)

        # Construir prompt para Gemini
        prompt_parts = [
            f"Eres un entrenador de élite. Genera un plan de entrenamiento detallado para un programa tipo '{program_type}'.",
        ]

        # Información del perfil de usuario
        prompt_parts.append("Considera el siguiente perfil de atleta:")
        if user_profile.get("age"): prompt_parts.append(f"- Edad: {user_profile.get('age')}")
        if user_profile.get("gender"): prompt_parts.append(f"- Género: {user_profile.get('gender')}")
        if user_profile.get("weight_kg"): prompt_parts.append(f"- Peso: {user_profile.get('weight_kg')} kg")
        if user_profile.get("height_cm"): prompt_parts.append(f"- Altura: {user_profile.get('height_cm')} cm")
        if user_profile.get("activity_level"): prompt_parts.append(f"- Nivel de Actividad: {user_profile.get('activity_level')}")
        if user_profile.get("experience_level"): prompt_parts.append(f"- Nivel de Experiencia: {user_profile.get('experience_level')}")

        prompt_parts.append(f"\nObjetivos Actuales del Atleta: {', '.join(current_goals)}")
        prompt_parts.append(f"Duración del Plan: {duration_weeks} semanas")

        if current_preferences:
            prompt_parts.append(f"Preferencias: {json.dumps(current_preferences)}")
        if training_history:
            prompt_parts.append(f"Historial de Entrenamiento Relevante: {json.dumps(training_history)}")
        
        prompt_parts.append("\nEl plan debe ser estructurado, detallado, y adecuado para el tipo de programa y objetivos.")
        prompt_parts.append("Incluye fases, microciclos, mesociclos si aplica, ejercicios específicos, series, repeticiones, descansos, y notas sobre intensidad y volumen.")
        prompt_parts.append("Formato de Salida Esperado: JSON con claves como 'plan_name', 'program_type', 'duration_weeks', 'phases' (lista de fases), etc.")
        prompt_parts.append("Cada fase debe tener 'phase_name', 'duration', 'description', y 'weekly_schedule'.")
        prompt_parts.append("Cada 'weekly_schedule' debe ser una lista de días, cada día con 'day_name', 'focus', y 'workouts' (lista de workouts).")
        prompt_parts.append("Cada 'workout' debe tener 'exercise_name', 'sets', 'reps', 'rest_seconds', 'intensity_notes'.")
        
        # Ejemplo para Gemini (Output Schema)
        prompt_parts.append(
            "\nEjemplo de la estructura JSON de salida deseada (GenerateTrainingPlanOutput):\n"
            "{\n"
            "  \"plan_name\": \"Plan de Fuerza Máxima para Powerlifter Avanzado\",\n"
            "  \"program_type\": \"PRIME\",\n"
            "  \"duration_weeks\": 12,\n"
            "  \"description\": \"Un plan de 12 semanas enfocado en incrementar la fuerza máxima en sentadilla, press de banca y peso muerto.\",\n"
            "  \"phases\": [\n"
            "    {\n"
            "      \"phase_name\": \"Fase de Acumulación (Semanas 1-4)\",\n"
            "      \"duration_weeks\": 4,\n"
            "      \"description\": \"Enfoque en volumen alto y técnica.\",\n"
            "      \"weekly_schedule\": [\n" # Array de schedules diarios
            "        {\n"
            "          \"day_of_week\": \"Lunes\",\n" # e.g., Lunes, Martes, etc.
            "          \"focus\": \"Sentadilla y Accesorios de Pierna\",\n"
            "          \"sessions\": [\n" # Array de sesiones/bloques de entrenamiento para ese día
            "            {\n"
            "              \"session_name\": \"Entrenamiento Principal\",\n"
            "              \"exercises\": [\n" # Array de ejercicios
            "                { \"exercise_name\": \"Sentadilla Trasera\", \"sets\": 5, \"reps_range\": \"4-6\", \"rest_seconds\": 180, \"intensity_notes\": \"RPE 8-9\" },\n"
            "                { \"exercise_name\": \"Prensa de Piernas\", \"sets\": 4, \"reps_range\": \"8-10\", \"rest_seconds\": 120, \"intensity_notes\": \"RPE 7-8\" }\n"
            "              ]\n"
            "            }\n"
            "          ]\n"
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        final_prompt = "\n".join(prompt_parts)
        logger.debug(f"Prompt para Gemini (generar plan): {final_prompt[:500]}...")

        # Llamada a Gemini
        if not self.gemini_client or not hasattr(self.gemini_client, 'generate_structured_output'):
             logger.error("GeminiClient no está configurado correctamente. No se puede generar el plan de entrenamiento.")
             return {"error": "GeminiClient not configured", "message": "Unable to generate training plan."}

        generated_plan = await self.gemini_client.generate_structured_output(final_prompt)
        
        # Validar la estructura del plan generado
        if not isinstance(generated_plan, dict) or not all(k in generated_plan for k in ["plan_name", "program_type", "duration_weeks", "phases"]):
            logger.error(f"La salida de Gemini para el plan de entrenamiento no tiene la estructura esperada. Salida: {generated_plan}")
            return {"error": "Invalid plan structure from LLM", "details": generated_plan}

        return generated_plan

    async def _skill_adapt_training_program(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Skill para adaptar un programa de entrenamiento existente.
        """
        logger.info(f"Skill '{self._skill_adapt_training_program.__name__}' llamada con entrada: '{input_text[:50]}...'")
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id")
        
        try:
            # Obtener client_profile del contexto
            full_context = await self._get_context(user_id, session_id)
            client_profile_from_context = full_context.get("client_profile", {})

            # Obtener parámetros relevantes de kwargs
            existing_plan_id = kwargs.get("existing_plan_id", "N/A")
            adaptation_reason = kwargs.get("adaptation_reason", input_text if input_text else "No especificado")
            feedback = kwargs.get("feedback", {})
            new_goals = kwargs.get("new_goals", [])

            # Llamar a la lógica interna
            adapted_plan_details = await self._adapt_training_program_logic(
                user_profile=client_profile_from_context,
                existing_plan_id=existing_plan_id,
                adaptation_reason=adaptation_reason,
                feedback=feedback,
                new_goals=new_goals
            )

            # Crear artefacto
            artifact = self.create_artifact(
                label="AdaptedTrainingProgram",
                content_type="application/json",
                data=adapted_plan_details
            )

            return create_result(
                status="success",
                response_data=adapted_plan_details,
                artifacts=[artifact]
            )
        except Exception as e:
            logger.error(f"Error en skill '{self._skill_adapt_training_program.__name__}': {e}", exc_info=True)
            return create_result(status="error", error_message=str(e))

    async def _adapt_training_program_logic(
        self, 
        user_profile: Dict[str, Any],
        existing_plan_id: str,
        adaptation_reason: str,
        feedback: Optional[Dict[str, Any]] = None,
        new_goals: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Lógica interna para adaptar un programa de entrenamiento.
        """
        program_type = self._get_program_type_from_profile(user_profile)

        prompt_parts = [
            f"Eres un entrenador de élite. Adapta un plan de entrenamiento existente para un programa tipo '{program_type}'.",
            f"Plan Existente (ID o descripción): {existing_plan_id}",
            f"Razón para la Adaptación: {adaptation_reason}",
        ]
        
        # Información del perfil de usuario
        prompt_parts.append("Considera el siguiente perfil de atleta:")
        if user_profile.get("age"): prompt_parts.append(f"- Edad: {user_profile.get('age')}")
        if user_profile.get("gender"): prompt_parts.append(f"- Género: {user_profile.get('gender')}")
        if user_profile.get("weight_kg"): prompt_parts.append(f"- Peso: {user_profile.get('weight_kg')} kg")
        if user_profile.get("height_cm"): prompt_parts.append(f"- Altura: {user_profile.get('height_cm')} cm")
        if user_profile.get("activity_level"): prompt_parts.append(f"- Nivel de Actividad: {user_profile.get('activity_level')}")
        if user_profile.get("experience_level"): prompt_parts.append(f"- Nivel de Experiencia: {user_profile.get('experience_level')}")

        if feedback:
            prompt_parts.append(f"Feedback del Atleta sobre el Plan Actual: {json.dumps(feedback)}")
        if new_goals:
            prompt_parts.append(f"Nuevos Objetivos o Ajustes a Objetivos: {', '.join(new_goals)}")

        prompt_parts.append("\nEl plan adaptado debe reflejar los cambios solicitados manteniendo una estructura coherente y efectiva.")
        prompt_parts.append("Modifica fases, ejercicios, volumen, intensidad según sea necesario.")
        prompt_parts.append("Formato de Salida Esperado: JSON similar a GenerateTrainingPlanOutput, pero con una sección 'adaptation_summary'.")
        prompt_parts.append(
             "\nEjemplo de la estructura JSON de salida deseada (AdaptTrainingProgramOutput):\n"
            "{\n"
            "  \"adapted_plan_name\": \"Plan de Fuerza Adaptado - Enfoque Hipertrofia\",\n"
            "  \"program_type\": \"PRIME\",\n"
            "  \"adaptation_summary\": \"Se ajustó el volumen de accesorios y se modificó el rango de repeticiones para enfocarse más en hipertrofia, basado en el feedback del atleta.\",\n"
            "  \"duration_weeks\": 8,\n"
            "  \"description\": \"Plan adaptado de 8 semanas...\",\n"
            "  \"phases\": [\n"
            "    // ... estructura similar a GenerateTrainingPlanOutput ...\n"
            "  ]\n"
            "}"
        )

        final_prompt = "\n".join(prompt_parts)
        logger.debug(f"Prompt para Gemini (adaptar plan): {final_prompt[:500]}...")

        # Llamada a Gemini
        if not self.gemini_client or not hasattr(self.gemini_client, 'generate_structured_output'):
             logger.error("GeminiClient no está configurado correctamente. No se puede adaptar el plan.")
             return {"error": "GeminiClient not configured", "message": "Unable to adapt training plan."}

        adapted_plan = await self.gemini_client.generate_structured_output(final_prompt)

        # Validar la estructura del plan adaptado
        if not isinstance(adapted_plan, dict) or "adapted_plan_name" not in adapted_plan:
            logger.error(f"La salida de Gemini para la adaptación del plan no tiene la estructura esperada. Salida: {adapted_plan}")
            return {"error": "Invalid adapted plan structure from LLM", "details": adapted_plan}
            
        return adapted_plan

    async def _skill_analyze_performance_data(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Skill para analizar datos de rendimiento.
        """
        logger.info(f"Skill '{self._skill_analyze_performance_data.__name__}' llamada con entrada: '{input_text[:50]}...'")
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id")
        
        try:
            # Obtener client_profile del contexto
            full_context = await self._get_context(user_id, session_id)
            client_profile_from_context = full_context.get("client_profile", {})

            # Obtener parámetros relevantes de kwargs
            performance_data = kwargs.get("performance_data", {})
            metrics_to_focus = kwargs.get("metrics_to_focus", [])
            comparison_period = kwargs.get("comparison_period", {})

            # Llamar a la lógica interna
            analysis_results = await self._analyze_performance_data_logic(
                user_profile=client_profile_from_context,
                performance_data=performance_data,
                metrics_to_focus=metrics_to_focus,
                comparison_period=comparison_period,
                user_query=input_text
            )

            # Crear artefacto
            artifact = self.create_artifact(
                label="PerformanceAnalysis",
                content_type="application/json",
                data=analysis_results
            )

            return create_result(
                status="success",
                response_data=analysis_results,
                artifacts=[artifact]
            )
        except Exception as e:
            logger.error(f"Error en skill '{self._skill_analyze_performance_data.__name__}': {e}", exc_info=True)
            return create_result(status="error", error_message=str(e))

    async def _analyze_performance_data_logic(
        self, 
        user_profile: Dict[str, Any],
        performance_data: Dict[str, Any],
        metrics_to_focus: Optional[List[str]] = None,
        comparison_period: Optional[Dict[str, Any]] = None,
        user_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lógica interna para analizar datos de rendimiento.
        """
        program_type = self._get_program_type_from_profile(user_profile)

        prompt_parts = [
            f"Eres un analista de rendimiento deportivo de élite. Analiza los siguientes datos para un programa tipo '{program_type}'.",
            f"Datos de Rendimiento Proporcionados: {json.dumps(performance_data)}",
        ]

        # Información del perfil de usuario
        prompt_parts.append("Considera el siguiente perfil de atleta:")
        if user_profile.get("age"): prompt_parts.append(f"- Edad: {user_profile.get('age')}")
        if user_profile.get("gender"): prompt_parts.append(f"- Género: {user_profile.get('gender')}")
        if user_profile.get("weight_kg"): prompt_parts.append(f"- Peso: {user_profile.get('weight_kg')} kg")
        if user_profile.get("height_cm"): prompt_parts.append(f"- Altura: {user_profile.get('height_cm')} cm")
        if user_profile.get("activity_level"): prompt_parts.append(f"- Nivel de Actividad: {user_profile.get('activity_level')}")
        if user_profile.get("experience_level"): prompt_parts.append(f"- Nivel de Experiencia: {user_profile.get('experience_level')}")

        if user_query:
            prompt_parts.append(f"Pregunta Específica del Usuario sobre los Datos: {user_query}")
        if metrics_to_focus:
            prompt_parts.append(f"Métricas Clave para Enfocar el Análisis: {', '.join(metrics_to_focus)}")
        if comparison_period:
            prompt_parts.append(f"Período de Comparación (si aplica): {json.dumps(comparison_period)}")

        prompt_parts.append("\nProporciona un análisis detallado, identifica tendencias, fortalezas, debilidades y recomendaciones accionables.")
        prompt_parts.append("Formato de Salida Esperado: JSON con 'analysis_summary', 'key_observations' (lista), 'recommendations' (lista).")
        prompt_parts.append(
             "\nEjemplo de la estructura JSON de salida deseada (AnalyzePerformanceDataOutput):\n"
            "{\n"
            "  \"analysis_summary\": \"Se observa una mejora del 10% en el máximo de sentadilla en el último mes, pero un estancamiento en los tiempos de carrera 5k.\",\n"
            "  \"key_observations\": [\n"
            "    { \"metric\": \"Máximo Sentadilla (kg)\", \"current_value\": 150, \"previous_value\": 135, \"change_percentage\": 11.1, \"observation\": \"Progreso significativo.\" },\n"
            "    { \"metric\": \"Tiempo 5k (min)\", \"current_value\": \"25:00\", \"previous_value\": \"24:50\", \"change_percentage\": -0.67, \"observation\": \"Ligero retroceso, posible sobreentrenamiento o necesidad de ajuste en cardio.\" }\n"
            "  ],\n"
            "  \"recommendations\": [\n"
            "    { \"recommendation_type\": \"Entrenamiento\", \"description\": \"Considerar un microciclo de descarga para la carrera y luego reintroducir series de velocidad.\" },\n"
            "    { \"recommendation_type\": \"Nutrición/Recuperación\", \"description\": \"Asegurar ingesta calórica adecuada y sueño de calidad para soportar el entrenamiento de fuerza.\" }\n"
            "  ]\n"
            "}"
        )
        final_prompt = "\n".join(prompt_parts)
        logger.debug(f"Prompt para Gemini (analizar rendimiento): {final_prompt[:500]}...")

        # Llamada a Gemini
        if not self.gemini_client or not hasattr(self.gemini_client, 'generate_structured_output'):
             logger.error("GeminiClient no está configurado correctamente. No se puede analizar el rendimiento.")
             return {"error": "GeminiClient not configured", "message": "Unable to analyze performance."}

        analysis = await self.gemini_client.generate_structured_output(final_prompt)
        
        # Validar la estructura del análisis
        if not isinstance(analysis, dict) or "analysis_summary" not in analysis:
            logger.error(f"La salida de Gemini para el análisis de rendimiento no tiene la estructura esperada. Salida: {analysis}")
            return {"error": "Invalid analysis structure from LLM", "details": analysis}

        return analysis

    async def _skill_set_training_intensity_volume(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Skill para establecer o ajustar la intensidad y volumen del entrenamiento.
        """
        logger.info(f"Skill '{self._skill_set_training_intensity_volume.__name__}' llamada con entrada: '{input_text[:50]}...'")
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id")
        
        try:
            # Obtener client_profile del contexto
            full_context = await self._get_context(user_id, session_id)
            client_profile_from_context = full_context.get("client_profile", {})

            # Obtener parámetros relevantes de kwargs
            current_phase = kwargs.get("current_phase", "No especificada")
            athlete_feedback = kwargs.get("athlete_feedback", {})
            performance_metrics = kwargs.get("performance_metrics", {})
            goal_adjustment_reason = kwargs.get("goal_adjustment_reason", input_text if input_text else "Ajuste rutinario")

            # Llamar a la lógica interna
            intensity_volume_settings = await self._set_training_intensity_volume_logic(
                user_profile=client_profile_from_context,
                current_phase=current_phase,
                athlete_feedback=athlete_feedback,
                performance_metrics=performance_metrics,
                goal_adjustment_reason=goal_adjustment_reason
            )

            # Crear artefacto
            artifact = self.create_artifact(
                label="TrainingIntensityVolumeSettings",
                content_type="application/json",
                data=intensity_volume_settings
            )

            return create_result(
                status="success",
                response_data=intensity_volume_settings,
                artifacts=[artifact]
            )
        except Exception as e:
            logger.error(f"Error en skill '{self._skill_set_training_intensity_volume.__name__}': {e}", exc_info=True)
            return create_result(status="error", error_message=str(e))

    async def _set_training_intensity_volume_logic(
        self, 
        user_profile: Dict[str, Any],
        current_phase: str,
        athlete_feedback: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        goal_adjustment_reason: str
    ) -> Dict[str, Any]:
        """
        Lógica interna para establecer la intensidad y volumen del entrenamiento.
        """
        program_type = self._get_program_type_from_profile(user_profile)

        prompt_parts = [
            f"Eres un coach experto en periodización. Determina los ajustes óptimos de intensidad y volumen para un atleta en un programa '{program_type}'.",
            f"Fase Actual del Entrenamiento: {current_phase}",
            f"Feedback del Atleta: {json.dumps(athlete_feedback)}",
            f"Métricas de Rendimiento Recientes: {json.dumps(performance_metrics)}",
            f"Razón para el Ajuste (o tipo de ajuste): {goal_adjustment_reason}",
        ]

        # Información del perfil de usuario
        prompt_parts.append("Considera el siguiente perfil de atleta:")
        if user_profile.get("age"): prompt_parts.append(f"- Edad: {user_profile.get('age')}")
        if user_profile.get("gender"): prompt_parts.append(f"- Género: {user_profile.get('gender')}")
        if user_profile.get("weight_kg"): prompt_parts.append(f"- Peso: {user_profile.get('weight_kg')} kg")
        if user_profile.get("height_cm"): prompt_parts.append(f"- Altura: {user_profile.get('height_cm')} cm")
        if user_profile.get("activity_level"): prompt_parts.append(f"- Nivel de Actividad: {user_profile.get('activity_level')}")
        if user_profile.get("experience_level"): prompt_parts.append(f"- Nivel de Experiencia: {user_profile.get('experience_level')}")

        prompt_parts.append("\nProporciona recomendaciones específicas para porcentajes de 1RM, RPE, series, repeticiones y volumen total semanal para los principales levantamientos o tipo de actividad.")
        prompt_parts.append("Formato de Salida Esperado: JSON con 'adjustment_summary', 'recommended_intensity' (dict), 'recommended_volume' (dict).")
        prompt_parts.append(
            "\nEjemplo de la estructura JSON de salida deseada (SetTrainingIntensityVolumeOutput):\n"
            "{\n"
            "  \"adjustment_summary\": \"Se recomienda un ligero aumento en la intensidad y mantener el volumen para la fase de intensificación, basado en el buen RPE y progreso en métricas.\",\n"
            "  \"recommended_intensity\": {\n"
            "    \"primary_lifts_percentage_1rm\": \"80-90%\",\n"
            "    \"accessory_rpe_target\": \"RPE 7-8\",\n"
            "    \"cardio_zones\": \"Zonas 2-3 con picos en Zona 4\"\n"
            "  },\n"
            "  \"recommended_volume\": {\n"
            "    \"primary_lifts_sets_per_week\": \"10-15 sets por grupo muscular principal\",\n"
            "    \"accessory_lifts_reps_range\": \"8-12 reps\",\n"
            "    \"total_training_hours_per_week\": \"8-10 horas\"\n"
            "  },\n"
            "  \"notes\": \"Monitorear la recuperación y ajustar si es necesario.\"\n"
            "}"
        )

        final_prompt = "\n".join(prompt_parts)
        logger.debug(f"Prompt para Gemini (ajustar I/V): {final_prompt[:500]}...")

        # Llamada a Gemini
        if not self.gemini_client or not hasattr(self.gemini_client, 'generate_structured_output'):
             logger.error("GeminiClient no está configurado correctamente. No se pueden establecer I/V.")
             return {"error": "GeminiClient not configured", "message": "Unable to set intensity/volume."}

        settings = await self.gemini_client.generate_structured_output(final_prompt)
        
        # Validar la estructura de los ajustes
        if not isinstance(settings, dict) or "adjustment_summary" not in settings:
            logger.error(f"La salida de Gemini para el ajuste de I/V no tiene la estructura esperada. Salida: {settings}")
            return {"error": "Invalid I/V settings structure from LLM", "details": settings}

        return settings

    async def _skill_prescribe_exercise_routines(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Skill para prescribir rutinas de ejercicios específicas.
        """
        logger.info(f"Skill '{self._skill_prescribe_exercise_routines.__name__}' llamada con entrada: '{input_text[:50]}...'")
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id")

        try:
            # Obtener client_profile del contexto
            full_context = await self._get_context(user_id, session_id)
            client_profile_from_context = full_context.get("client_profile", {})

            # Obtener parámetros relevantes de kwargs
            focus_area = kwargs.get("focus_area", input_text if input_text else "Entrenamiento general de fuerza")
            exercise_type = kwargs.get("exercise_type", "compound")
            equipment_available = kwargs.get("equipment_available", ["full_gym"])
            experience_level = kwargs.get("experience_level", client_profile_from_context.get("experience_level", "intermediate"))

            # Llamar a la lógica interna
            routines = await self._prescribe_exercise_routines_logic(
                user_profile=client_profile_from_context,
                focus_area=focus_area,
                exercise_type=exercise_type,
                equipment_available=equipment_available,
                experience_level=experience_level
            )

            # Crear artefacto
            artifact = self.create_artifact(
                label="ExerciseRoutine",
                content_type="application/json",
                data=routines
            )

            return create_result(
                status="success",
                response_data=routines,
                artifacts=[artifact]
            )
        except Exception as e:
            logger.error(f"Error en skill '{self._skill_prescribe_exercise_routines.__name__}': {e}", exc_info=True)
            return create_result(status="error", error_message=str(e))

    async def _prescribe_exercise_routines_logic(
        self, 
        user_profile: Dict[str, Any],
        focus_area: str,
        exercise_type: str,
        equipment_available: List[str],
        experience_level: str
    ) -> Dict[str, Any]:
        """
        Lógica interna para prescribir rutinas de ejercicios.
        """
        program_type = self._get_program_type_from_profile(user_profile)

        prompt_parts = [
            f"Eres un especialista en ejercicios. Prescribe rutinas de ejercicios para un programa '{program_type}'.",
            f"Área de Enfoque: {focus_area}",
            f"Tipo de Ejercicio: {exercise_type}",
            f"Equipamiento Disponible: {', '.join(equipment_available)}",
            f"Nivel de Experiencia del Atleta: {experience_level}",
        ]

        # Información del perfil de usuario
        prompt_parts.append("Considera el siguiente perfil de atleta:")
        if user_profile.get("age"): prompt_parts.append(f"- Edad: {user_profile.get('age')}")
        if user_profile.get("gender"): prompt_parts.append(f"- Género: {user_profile.get('gender')}")
        if user_profile.get("weight_kg"): prompt_parts.append(f"- Peso: {user_profile.get('weight_kg')} kg")
        if user_profile.get("height_cm"): prompt_parts.append(f"- Altura: {user_profile.get('height_cm')} cm")
        if user_profile.get("activity_level"): prompt_parts.append(f"- Nivel de Actividad: {user_profile.get('activity_level')}")

        prompt_parts.append("\nProporciona una lista de ejercicios con detalles sobre series, repeticiones, tempo, descanso y notas técnicas o de seguridad.")
        prompt_parts.append("Si es relevante, incluye progresiones o regresiones.")
        prompt_parts.append("Formato de Salida Esperado: JSON con 'routine_name', 'focus_area', 'exercises' (lista).")
        prompt_parts.append(
            "\nEjemplo de la estructura JSON de salida deseada (PrescribeExerciseRoutinesOutput):\n"
            "{\n"
            "  \"routine_name\": \"Rutina de Empuje Tren Superior - Intermedio\",\n"
            "  \"focus_area\": \"Fuerza de tren superior (empuje)\",\n"
            "  \"exercise_type\": \"compound_isolation_mix\",\n"
            "  \"estimated_duration_minutes\": 60,\n"
            "  \"exercises\": [\n"
            "    { \"exercise_name\": \"Press de Banca con Barra\", \"sets\": 4, \"reps_range\": \"6-8\", \"rest_seconds\": 90, \"tempo\": \"2-0-1-0\", \"notes\": \"Mantener retracción escapular.\" },\n"
            "    { \"exercise_name\": \"Press Inclinado con Mancuernas\", \"sets\": 3, \"reps_range\": \"8-10\", \"rest_seconds\": 75, \"tempo\": \"2-0-1-0\", \"notes\": \"Ajustar inclinación a 30-45 grados.\" },\n"
            "    { \"exercise_name\": \"Aperturas con Mancuernas\", \"sets\": 3, \"reps_range\": \"10-12\", \"rest_seconds\": 60, \"tempo\": \"3-0-1-0\", \"notes\": \"Controlar el estiramiento.\" }\n"
            "  ],\n"
            "  \"warm_up\": [\"Movilidad articular general\", \"Activación de manguito rotador\"],\n"
            "  \"cool_down\": [\"Estiramientos estáticos para pectoral, hombros, tríceps\"]\n"
            "}"
        )
        final_prompt = "\n".join(prompt_parts)
        logger.debug(f"Prompt para Gemini (prescribir ejercicios): {final_prompt[:500]}...")

        # Llamada a Gemini
        if not self.gemini_client or not hasattr(self.gemini_client, 'generate_structured_output'):
             logger.error("GeminiClient no está configurado correctamente. No se pueden prescribir rutinas.")
             return {"error": "GeminiClient not configured", "message": "Unable to prescribe routines."}

        routines = await self.gemini_client.generate_structured_output(final_prompt)
        
        # Validar la estructura de la rutina
        if not isinstance(routines, dict) or "routine_name" not in routines:
            logger.error(f"La salida de Gemini para la prescripción de rutinas no tiene la estructura esperada. Salida: {routines}")
            return {"error": "Invalid routine structure from LLM", "details": routines}
            
        return routines

    def _get_completion_message(self, skill_name: str, response_data: Dict[str, Any]) -> Optional[str]:
        """
        Genera un mensaje de finalización personalizado para la skill, si es necesario.
        """
        # Implementación específica si se necesita un mensaje de finalización personalizado
        # Por ahora, devolvemos None para usar el mensaje por defecto
        return None

    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Maneja errores y devuelve un resultado formateado.
        """
        # Registrar el error
        logger.error(f"Error en EliteTrainingStrategist: {error}", exc_info=True)
        
        # Si hay telemetría disponible, incrementar contador de errores
        if hasattr(self, 'error_count') and self.error_count:
            self.error_count.add(1, {"agent": "EliteTrainingStrategist", "error_type": type(error).__name__})
            
        # Crear un mensaje de error amigable
        error_message = str(error)
        if isinstance(error, ValueError):
            friendly_message = f"Error de valor: {error_message}"
        elif isinstance(error, TypeError):
            friendly_message = f"Error de tipo: {error_message}"
        elif isinstance(error, KeyError):
            friendly_message = f"Error de clave: {error_message}"
        else:
            friendly_message = f"Error inesperado: {error_message}"
            
        # Devolver un resultado formateado con el error
        return create_result(status="error", error_message=friendly_message)

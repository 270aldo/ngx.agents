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

from agents.base.adk_agent import ADKAgent
from adk.agent import Skill 
from adk.toolkit import Toolkit
from core.contracts import create_result 

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
    AnalyzeExerciseFormInput,
    AnalyzeExerciseFormOutput,
    FormCorrectionPoint,
    CompareExerciseProgressInput,
    CompareExerciseProgressOutput,
    ExerciseFormAnalysisArtifact
)

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from services.program_classification_service import ProgramClassificationService
from agents.shared.program_definitions import (
    get_program_definition,
    get_program_keywords,
    get_age_range,
    get_all_program_types
)
from infrastructure.adapters.a2a_adapter import a2a_adapter
from core.logging_config import get_logger
from google.cloud import aiplatform

# Configurar logger
logger = get_logger(__name__)

class EliteTrainingStrategist(ADKAgent):
    """
    Agente especializado en el diseño y periodización de programas de entrenamiento
    para atletas de élite y usuarios avanzados, integrando análisis de rendimiento y
    prescripción de ejercicios.
    
    Esta implementación utiliza la integración oficial con Google ADK.
    """

    AGENT_ID = "elite_training_strategist"
    AGENT_NAME = "Elite Training Strategist"
    AGENT_DESCRIPTION = "Specializes in designing and periodizing training programs for elite athletes."
    DEFAULT_INSTRUCTION = "Eres un estratega experto en entrenamiento deportivo."
    DEFAULT_MODEL = "gemini-1.5-flash" # o settings.ELITE_TRAINING_STRATEGIST_MODEL_ID

    def __init__(
        self,
        state_manager = None, 
        mcp_toolkit: Optional[MCPToolkit] = None, 
        model: Optional[str] = None,
        instruction: Optional[str] = None,
        agent_id: str = AGENT_ID,
        name: str = AGENT_NAME,
        description: str = AGENT_DESCRIPTION,
        **kwargs 
    ):
        _model = model or self.DEFAULT_MODEL
        _instruction = instruction or self.DEFAULT_INSTRUCTION
        _mcp_toolkit = mcp_toolkit if mcp_toolkit is not None else MCPToolkit()
        
        # Inicializar el servicio de clasificación de programas
        self.gemini_client = GeminiClient()
        self.program_classification_service = ProgramClassificationService(self.gemini_client)

        # Definir las skills antes de llamar al constructor de ADKAgent
        self.skills = [
            Skill(
                name="generate_training_plan",
                description="Genera un plan de entrenamiento completo basado en el perfil y objetivos del usuario.",
                handler=self._skill_generate_training_plan,
                input_schema=GenerateTrainingPlanInput,
                output_schema=GenerateTrainingPlanOutput
            ),
            Skill(
                name="adapt_training_program",
                description="Adapta un programa de entrenamiento existente basado en nuevos inputs o feedback.",
                handler=self._skill_adapt_training_program,
                input_schema=AdaptTrainingProgramInput,
                output_schema=AdaptTrainingProgramOutput
            ),
            Skill(
                name="analyze_performance_data",
                description="Analiza datos de rendimiento para proporcionar insights y recomendaciones.",
                handler=self._skill_analyze_performance_data,
                input_schema=AnalyzePerformanceDataInput,
                output_schema=AnalyzePerformanceDataOutput
            ),
            Skill(
                name="set_training_intensity_volume",
                description="Establece o ajusta la intensidad y volumen de entrenamiento basado en la periodización y estado del usuario.",
                handler=self._skill_set_training_intensity_volume,
                input_schema=SetTrainingIntensityVolumeInput,
                output_schema=SetTrainingIntensityVolumeOutput
            ),
            Skill(
                name="prescribe_exercise_routines",
                description="Prescribe rutinas de ejercicios específicas, incluyendo variaciones y progresiones.",
                handler=self._skill_prescribe_exercise_routines,
                input_schema=PrescribeExerciseRoutinesInput,
                output_schema=PrescribeExerciseRoutinesOutput
            ),
            Skill(
                name="analyze_exercise_form",
                description="Analiza la forma y técnica de ejercicios mediante imágenes para proporcionar correcciones y recomendaciones.",
                handler=self._skill_analyze_exercise_form,
                input_schema=AnalyzeExerciseFormInput,
                output_schema=AnalyzeExerciseFormOutput
            ),
            Skill(
                name="compare_exercise_progress",
                description="Compara imágenes de ejercicios para evaluar el progreso y cambios en la técnica a lo largo del tiempo.",
                handler=self._skill_compare_exercise_progress,
                input_schema=CompareExerciseProgressInput,
                output_schema=CompareExerciseProgressOutput
            )
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
            capabilities=[skill.name for skill in self.skills],
            **kwargs
        )
        
        # Configurar clientes adicionales
        self.gemini_client = GeminiClient(model_name=self.model)
        self.supabase_client = SupabaseClient()
        
        # Inicializar Vertex AI
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform (Vertex AI SDK) inicializado correctamente para ETS.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform para ETS: {e}", exc_info=True)
        
        # Inicializar procesadores de visión y multimodales
        try:
            from core.vision_processor import VisionProcessor
            from infrastructure.adapters.multimodal_adapter import MultimodalAdapter
            from clients.vertex_ai.vision_client import VertexAIVisionClient
            from clients.vertex_ai.multimodal_client import VertexAIMultimodalClient
            
            # Inicializar procesador de visión
            self.vision_processor = VisionProcessor()
            logger.info("Procesador de visión inicializado correctamente")
            
            # Inicializar adaptador multimodal
            self.multimodal_adapter = MultimodalAdapter()
            logger.info("Adaptador multimodal inicializado correctamente")
            
            # Inicializar clientes especializados
            self.vision_client = VertexAIVisionClient()
            self.multimodal_client = VertexAIMultimodalClient()
            logger.info("Clientes de visión y multimodal inicializados correctamente")
            
            # Inicializar tracer para telemetría
            from opentelemetry import trace
            self.tracer = trace.get_tracer(__name__)
            logger.info("Tracer para telemetría inicializado correctamente")
            
            # Marcar capacidades como disponibles
            self._vision_capabilities_available = True
        except ImportError as e:
            logger.warning(f"No se pudieron inicializar algunos componentes para capacidades avanzadas: {e}")
            # Crear implementaciones simuladas para mantener la compatibilidad
            self._vision_capabilities_available = False
            
            # Crear implementaciones simuladas
            self.vision_processor = type('DummyVisionProcessor', (), {
                'analyze_image': lambda self, image_data, prompt=None: {"text": "Análisis de imagen simulado"},
                'describe_image': lambda self, image_data, detail_level=None, focus_aspect=None: {"text": "Descripción de imagen simulada"}
            })()
            
            self.multimodal_adapter = type('DummyMultimodalAdapter', (), {
                'process_multimodal': lambda self, prompt, image_data, temperature=0.2, max_output_tokens=1024:
                    {"text": "Análisis multimodal simulado"},
                'compare_images': lambda self, image_data1, image_data2, comparison_prompt=None, temperature=0.2, max_output_tokens=1024:
                    {"text": "Comparación de imágenes simulada", "comparison": "", "similarities": [], "differences": []}
            })()
            
            self.tracer = type('DummyTracer', (), {
                'start_as_current_span': lambda name: type('DummySpan', (), {'__enter__': lambda self: None, '__exit__': lambda self, *args: None})()
            })
            
        logger.info(f"{self.name} ({self.agent_id}) inicializado con integración oficial de Google ADK.")

    # --- Métodos de Habilidades (Skills) ---
    async def _skill_generate_training_plan(self, input_data: GenerateTrainingPlanInput) -> GenerateTrainingPlanOutput:
        logger.info(f"Ejecutando habilidad: _skill_generate_training_plan con input: {input_data}")
        # Aquí iría la lógica real, por ahora un mock
        # Ejemplo: plan_details = await self._generate_training_plan(input_data.user_query, input_data.user_profile)
        # return GenerateTrainingPlanOutput(training_plan=TrainingPlanArtifact(**plan_details))
        mock_plan_details = {
            "plan_name": "Mock Plan", 
            "description": "Plan de entrenamiento simulado",
            "duration_weeks": 4,
            "sessions_per_week": 3,
            "daily_sessions": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return GenerateTrainingPlanOutput(
            plan_name="Mock Plan",
            program_type="PRIME",
            duration_weeks=4,
            description="Plan de entrenamiento simulado",
            phases=[],
            artifacts=None,
            response="Este es un plan de entrenamiento simulado"
        )

    async def _skill_adapt_training_program(self, input_data: AdaptTrainingProgramInput) -> AdaptTrainingProgramOutput:
        logger.info(f"Ejecutando habilidad: _skill_adapt_training_program con input: {input_data}")
        # Lógica de adaptación...
        return AdaptTrainingProgramOutput(
            adapted_plan_name="Mock Adapted Plan",
            program_type="PRIME",
            adaptation_summary="Adaptación simulada",
            duration_weeks=4,
            description="Plan adaptado simulado",
            phases=[]
        )

    async def _skill_analyze_performance_data(self, input_data: AnalyzePerformanceDataInput) -> AnalyzePerformanceDataOutput:
        logger.info(f"Ejecutando habilidad: _skill_analyze_performance_data con input: {input_data}")
        # Lógica de análisis...
        return AnalyzePerformanceDataOutput(
            analysis_summary="Análisis de rendimiento simulado.",
            key_observations=[{"metric": "metric1", "value": 100, "observation": "Bueno"}],
            recommendations=[{"recommendation_type": "Entrenamiento", "description": "Continuar con el buen trabajo"}]
        )

    async def _skill_set_training_intensity_volume(self, input_data: SetTrainingIntensityVolumeInput) -> SetTrainingIntensityVolumeOutput:
        logger.info(f"Ejecutando habilidad: _skill_set_training_intensity_volume con input: {input_data}")
        # Lógica de ajuste de intensidad/volumen...
        return SetTrainingIntensityVolumeOutput(
            adjustment_summary="Ajustes simulados",
            recommended_intensity={"intensity_level": "Alto"},
            recommended_volume={"volume_description": "Volumen moderado"},
            notes="Ajustes basados en la fase actual y feedback."
        )

    async def _skill_prescribe_exercise_routines(self, input_data: PrescribeExerciseRoutinesInput) -> PrescribeExerciseRoutinesOutput:
        logger.info(f"Ejecutando habilidad: _skill_prescribe_exercise_routines con input: {input_data}")
        # Lógica de prescripción de rutinas...
        return PrescribeExerciseRoutinesOutput(
            routine_name="Rutina de Fuerza General",
            focus_area=input_data.focus_area,
            exercise_type=input_data.exercise_type,
            estimated_duration_minutes=60,
            exercises=[
                {"name": "Sentadilla", "sets": 3, "reps": 10},
                {"name": "Press de Banca", "sets": 3, "reps": 10}
            ],
            warm_up=["Movilidad articular general"],
            cool_down=["Estiramientos estáticos"]
        )

    # --- Métodos para gestión de estado ---
    async def _get_context(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el adaptador del StateManager.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            
        Returns:
            Dict[str, Any]: Contexto de la conversación
        """
        try:
            # Intentar cargar el contexto desde el adaptador del StateManager
            context = await state_manager_adapter.load_state(user_id, session_id)
            
            if not context or not context.get("state_data"):
                logger.info(f"No se encontró contexto en el adaptador del StateManager para user_id={user_id}, session_id={session_id}. Creando nuevo contexto.")
                # Si no hay contexto, crear uno nuevo
                context = {
                    "conversation_history": [],
                    "user_profile": {},
                    "training_plans": [],
                    "performance_data": {},
                    "last_updated": datetime.now().isoformat()
                }
            else:
                # Si hay contexto, usar el state_data
                context = context.get("state_data", {})
                logger.info(f"Contexto cargado desde el adaptador del StateManager para user_id={user_id}, session_id={session_id}")
            
            return context
        except Exception as e:
            logger.error(f"Error al obtener contexto: {e}", exc_info=True)
            # En caso de error, devolver un contexto vacío
            return {
                "conversation_history": [],
                "user_profile": {},
                "training_plans": [],
                "performance_data": {},
                "last_updated": datetime.now().isoformat()
            }

    async def _update_context(self, context: Dict[str, Any], user_id: str, session_id: str) -> None:
        """
        Actualiza el contexto de la conversación en el adaptador del StateManager.
        
        Args:
            context: Contexto actualizado
            user_id: ID del usuario
            session_id: ID de la sesión
        """
        try:
            # Actualizar la marca de tiempo
            context["last_updated"] = datetime.now().isoformat()
            
            # Guardar el contexto en el adaptador del StateManager
            await state_manager_adapter.save_state(context, user_id, session_id)
            logger.info(f"Contexto actualizado en el adaptador del StateManager para user_id={user_id}, session_id={session_id}")
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)
    
    # --- Métodos para análisis de intenciones ---
    async def _classify_query(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario utilizando el adaptador del Intent Analyzer.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta clasificada
        """
        try:
            # Utilizar el adaptador del Intent Analyzer para analizar la intención
            intent_analysis = await intent_analyzer_adapter.analyze_intent(query)
            
            # Mapear la intención primaria a los tipos de consulta del agente
            primary_intent = intent_analysis.get("primary_intent", "").lower()
            
            # Mapeo de intenciones a tipos de consulta
            intent_to_query_type = {
                "training_plan": "generate_training_plan",
                "adapt_program": "adapt_training_program",
                "performance_analysis": "analyze_performance_data",
                "intensity_volume": "set_training_intensity_volume",
                "exercise_routine": "prescribe_exercise_routines"
            }
            
            # Buscar coincidencias exactas
            if primary_intent in intent_to_query_type:
                return intent_to_query_type[primary_intent]
            
            # Buscar coincidencias parciales
            for intent, query_type in intent_to_query_type.items():
                if intent in primary_intent:
                    return query_type
            
            # Si no hay coincidencias, usar el método de palabras clave como fallback
            return self._classify_query_by_keywords(query)
        except Exception as e:
            logger.error(f"Error al clasificar consulta con Intent Analyzer: {e}", exc_info=True)
            # En caso de error, usar el método de palabras clave como fallback
            return self._classify_query_by_keywords(query)
    
    def _classify_query_by_keywords(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario utilizando palabras clave.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta clasificada
        """
        query_lower = query.lower()
        
        # Palabras clave para generar plan de entrenamiento
        training_plan_keywords = [
            "plan", "programa", "entrenamiento", "rutina", "crear", "generar", 
            "diseñar", "nuevo", "comenzar"
        ]
        
        # Palabras clave para adaptar programa
        adapt_program_keywords = [
            "adaptar", "modificar", "ajustar", "cambiar", "actualizar", 
            "revisar", "mejorar", "personalizar"
        ]
        
        # Palabras clave para análisis de rendimiento
        performance_analysis_keywords = [
            "analizar", "análisis", "rendimiento", "progreso", "resultados", 
            "métricas", "datos", "evaluar", "evaluación"
        ]
        
        # Palabras clave para intensidad y volumen
        intensity_volume_keywords = [
            "intensidad", "volumen", "carga", "peso", "series", "repeticiones", 
            "descanso", "recuperación", "periodización"
        ]
        
        # Palabras clave para rutinas de ejercicios
        exercise_routine_keywords = [
            "ejercicio", "rutina", "movimiento", "técnica", "forma", 
            "variación", "alternativa", "sustitución", "progresión"
        ]
        
        # Verificar coincidencias con palabras clave
        for keyword in exercise_routine_keywords:
            if keyword in query_lower:
                return "prescribe_exercise_routines"
                
        for keyword in intensity_volume_keywords:
            if keyword in query_lower:
                return "set_training_intensity_volume"
                
        for keyword in performance_analysis_keywords:
            if keyword in query_lower:
                return "analyze_performance_data"
                
        for keyword in adapt_program_keywords:
            if keyword in query_lower:
                return "adapt_training_program"
                
        for keyword in training_plan_keywords:
            if keyword in query_lower:
                return "generate_training_plan"
                
        # Si no hay coincidencias, devolver tipo general
        return "generate_training_plan"
    async def _consult_other_agent(self, agent_id: str, query: str, user_id: Optional[str] = None, session_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta a otro agente utilizando el adaptador de A2A.
        Enriquece la consulta con información específica del programa del usuario.
        
        Args:
            agent_id: ID del agente a consultar
            query: Consulta a enviar al agente
            user_id: ID del usuario
            session_id: ID de la sesión
            context: Contexto adicional para la consulta
            
        Returns:
            Dict[str, Any]: Respuesta del agente consultado
        """
        if not a2a_adapter:
            logger.error("Adaptador A2A no disponible. No se puede consultar a otros agentes.")
            return {"error": "A2A adapter not available"}
            
        try:
            # Preparar contexto para la consulta
            if context is None:
                context = {}
            
            # Enriquecer la consulta con información del programa si está disponible
            enriched_query = query
            if context and "program_type" in context:
                program_type = context["program_type"]
                try:
                    # Usar el servicio para enriquecer la consulta
                    enriched_query = self.program_classification_service.enrich_query_with_program_context(
                        query, program_type
                    )
                    logger.info(f"Consulta enriquecida con información del programa {program_type}")
                except Exception as e:
                    logger.warning(f"No se pudo enriquecer la consulta con información del programa: {e}")
                    
            # Realizar la consulta al otro agente
            response = await a2a_adapter.consult_agent(
                agent_id=agent_id,
                query=enriched_query,
                user_id=user_id,
                session_id=session_id,
                context=context
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error al consultar al agente {agent_id}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "output": f"Error al consultar al agente {agent_id}",
                "agent_id": agent_id,
                "agent_name": agent_id
            }
    
    # --- Métodos Internos del Agente --- 
    def _prepare_context(
        self, 
        user_input: str, 
        user_profile: Optional[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> str:
        """
        Prepara el contexto para la generación de la respuesta o plan.
        Combina la instrucción base del agente, detalles del perfil del usuario y contexto adicional.
        """
        # Instrucción base específica para EliteTrainingStrategist
        prompt_context = (
            "Eres EliteTrainingStrategist, un especialista en diseñar programas de entrenamiento "
            "para atletas de élite y alto rendimiento. Tu objetivo es crear planes optimizados, "
            "basados en la ciencia y completamente personalizados para maximizar el potencial del atleta, "
            "considerando sus metas, nivel actual, y cualquier restricción o preferencia. "
            "Debes ser preciso, detallado y proponer estrategias innovadoras."
        )

        # Añadir detalles del perfil del usuario
        if user_profile:
            profile_details_str = self._extract_profile_details(user_profile)
            prompt_context += f"\n\nInformación del Atleta:\n{profile_details_str}"
        else:
            prompt_context += "\n\nInformación del Atleta: No disponible."
        
        # Añadir contexto adicional si está disponible y es relevante
        if context:
            # Filtrar claves que no queremos directamente en el prompt o que ya están en user_profile
            # Esto es un ejemplo, se puede ajustar según necesidad
            relevant_context_keys = [k for k in context.keys() if k not in ["user_id", "session_id", "client_profile", "history"]]
            additional_context_parts = []
            for key in relevant_context_keys:
                # Podríamos querer formatear o seleccionar partes específicas del contexto adicional
                # Por ahora, simplemente añadimos el par clave-valor si el valor no es muy grande
                value_str = str(context[key])
                if len(value_str) < 200: # Evitar contextos demasiado largos
                    additional_context_parts.append(f"- {key}: {value_str}")
            
            if additional_context_parts:
                additional_context_str = "\n".join(additional_context_parts)
                prompt_context += f"\n\nContexto Adicional Relevante:\n{additional_context_str}"

        # Añadir la entrada del usuario al final como la solicitud específica
        prompt_context += f"\n\nSolicitud Específica del Usuario:\n{user_input}"
        
        logger.debug(f"Contexto preparado para EliteTrainingStrategist: {prompt_context}")
        return prompt_context

    async def _generate_training_plan(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Lógica interna para generar el plan de entrenamiento.
        """
        if context is None:
            context = {}
            
        program_type = await self._get_program_type_from_profile(context)

        # Construir prompt para Gemini
        prompt_parts = [
            f"Eres un entrenador de élite. Genera un plan de entrenamiento detallado para un programa tipo '{program_type}'.",
        ]

        # Información del perfil de usuario
        prompt_parts.append("Considera el siguiente perfil de atleta:")
        if context.get("age"): prompt_parts.append(f"- Edad: {context.get('age')}")
        if context.get("gender"): prompt_parts.append(f"- Género: {context.get('gender')}")
        if context.get("weight_kg"): prompt_parts.append(f"- Peso: {context.get('weight_kg')} kg")
        if context.get("height_cm"): prompt_parts.append(f"- Altura: {context.get('height_cm')} cm")
        if context.get("activity_level"): prompt_parts.append(f"- Nivel de Actividad: {context.get('activity_level')}")
        if context.get("experience_level"): prompt_parts.append(f"- Nivel de Experiencia: {context.get('experience_level')}")

        prompt_parts.append(f"\nObjetivos Actuales del Atleta: {user_input}")
        prompt_parts.append("\nEl plan debe ser estructurado, detallado, y adecuado para el tipo de programa y objetivos.")
        prompt_parts.append("Incluye fases, microciclos, mesociclos si aplica, ejercicios específicos, series, repeticiones, descansos, y notas sobre intensidad y volumen.")
        prompt_parts.append("Formato de Salida Esperado: JSON con claves como 'plan_name', 'program_type', 'duration_weeks', 'phases' (lista), etc.")
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

        # Crear un artefacto para el plan generado
        plan_text_content = generated_plan.get("response", f"Plan de entrenamiento {generated_plan['program_type']} de {generated_plan['duration_weeks']} semanas")
        artifact = TrainingPlanArtifact(
            label=f"Plan de Entrenamiento ({generated_plan['program_type']}) - {generated_plan['duration_weeks']} Semanas",
            content_type="text/markdown",
            data={
                "content": plan_text_content,
                "user_id": context.get("user_id", "unknown_user"),
                "session_id": context.get("session_id", "unknown_session"),
                "program_type": generated_plan['program_type'],
                "duration_weeks": generated_plan['duration_weeks']
            }
        )
        
        # Asegurar que generated_plan tiene una lista de artifacts
        if "artifacts" not in generated_plan or generated_plan["artifacts"] is None:
            generated_plan["artifacts"] = []
        
        # Añadir el artefacto creado a la lista de artifacts
        generated_plan["artifacts"].append(artifact.model_dump())
        
        return generated_plan

    async def _adapt_training_program(self, existing_plan_id: str, adaptation_reason: str, feedback: Optional[Dict[str, Any]] = None, new_goals: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Lógica interna para adaptar un programa de entrenamiento.
        """
        program_type = await self._get_program_type_from_profile({})

        prompt_parts = [
            f"Eres un entrenador de élite. Adapta un plan de entrenamiento existente para un programa tipo '{program_type}'.",
            f"Plan Existente (ID o descripción): {existing_plan_id}",
            f"Razón para la Adaptación: {adaptation_reason}",
        ]
        
        # Información del perfil de usuario
        prompt_parts.append("Considera el siguiente perfil de atleta:")
        prompt_parts.append("- Sin información disponible.")

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

    async def _analyze_performance_data(self, performance_data: Dict[str, Any], metrics_to_focus: Optional[List[str]] = None, comparison_period: Optional[Dict[str, Any]] = None, user_query: Optional[str] = None) -> Dict[str, Any]:
        """
        Lógica interna para analizar datos de rendimiento.
        """
        program_type = await self._get_program_type_from_profile({})

        prompt_parts = [
            f"Eres un analista de rendimiento deportivo de élite. Analiza los siguientes datos para un programa '{program_type}'.",
            f"Datos de Rendimiento Proporcionados: {json.dumps(performance_data)}",
        ]

        # Información del perfil de usuario
        prompt_parts.append("Considera el siguiente perfil de atleta:")
        prompt_parts.append("- Sin información disponible.")

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

    async def _get_program_type_from_profile(self, context: Dict[str, Any]) -> str:
        """
        Determina el tipo de programa basado en el perfil del usuario utilizando el servicio
        centralizado de clasificación de programas.
        
        Args:
            context: Contexto del usuario que puede incluir program_type, user_profile, goals, etc.
            
        Returns:
            str: Tipo de programa (PRIME, LONGEVITY, STRENGTH, HYPERTROPHY, ENDURANCE, ATHLETIC, PERFORMANCE)
        """
        logger.debug(f"Determinando tipo de programa desde contexto usando servicio centralizado: {context}")
        
        # Utilizar el servicio de clasificación de programas
        program_type = await self.program_classification_service.classify_program_type(context)
        logger.info(f"Tipo de programa determinado por el servicio de clasificación: {program_type}")
        
        return program_type
    
    # Método eliminado: _classify_program_type_with_llm
    # Ahora se utiliza el servicio centralizado de clasificación de programas

    async def _set_training_intensity_volume(self, current_phase: str, athlete_feedback: Dict[str, Any], performance_metrics: Dict[str, Any], goal_adjustment_reason: str) -> Dict[str, Any]:
        """
        Lógica interna para establecer la intensidad y volumen del entrenamiento.
        """
        program_type = await self._get_program_type_from_profile({})

        prompt_parts = [
            f"Eres un coach experto en periodización. Determina los ajustes óptimos de intensidad y volumen para un atleta en un programa '{program_type}'.",
            f"Fase Actual del Entrenamiento: {current_phase}",
            f"Feedback del Atleta: {json.dumps(athlete_feedback)}",
            f"Métricas de Rendimiento Recientes: {json.dumps(performance_metrics)}",
            f"Razón para el Ajuste (o tipo de ajuste): {goal_adjustment_reason}",
        ]

        # Información del perfil de usuario
        prompt_parts.append("Considera el siguiente perfil de atleta:")
        prompt_parts.append("- Sin información disponible.")

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
        
    async def _skill_analyze_exercise_form(self, input_data: AnalyzeExerciseFormInput) -> AnalyzeExerciseFormOutput:
        """
        Skill para analizar la forma y técnica de ejercicios mediante imágenes.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            AnalyzeExerciseFormOutput: Análisis de la forma del ejercicio
        """
        logger.info(f"Ejecutando habilidad: _skill_analyze_exercise_form para ejercicio: {input_data.exercise_name}")
        
        try:
            # Obtener datos de la imagen
            image_data = input_data.image_data
            exercise_name = input_data.exercise_name or "Ejercicio no especificado"
            exercise_type = input_data.exercise_type or "No especificado"
            user_profile = input_data.user_profile or {}
            analysis_focus = input_data.analysis_focus or ["postura", "alineación", "rango de movimiento"]
            
            # Verificar si las capacidades de visión están disponibles
            if not hasattr(self, '_vision_capabilities_available') or not self._vision_capabilities_available:
                logger.warning("Capacidades de visión no disponibles. Usando análisis simulado.")
                return self._generate_mock_exercise_form_analysis(input_data)
            
            # Utilizar las capacidades de visión del agente base
            with self.tracer.start_as_current_span("exercise_form_analysis"):
                # Analizar la imagen utilizando el procesador de visión
                vision_result = await self.vision_processor.analyze_image(
                    image_data=image_data,
                    prompt=f"Analiza esta imagen de un atleta realizando {exercise_name} y describe la técnica y postura."
                )
                
                # Generar una descripción detallada de la imagen
                description_result = await self.vision_processor.analyze_image(
                    image_data=image_data,
                    prompt="Describe detalladamente la postura y alineación corporal de la persona en esta imagen."
                )
                
                # Extraer análisis de forma de ejercicio usando el modelo multimodal
                prompt = f"""
                Eres un entrenador experto en biomecánica y técnica de ejercicios. Analiza esta imagen de un atleta
                realizando {exercise_name} ({exercise_type}) y proporciona un análisis detallado de su forma.
                
                Enfócate específicamente en los siguientes aspectos:
                {', '.join(analysis_focus)}
                
                Proporciona:
                1. Una evaluación general de la calidad de la forma (escala 0-10)
                2. Análisis detallado de la técnica
                3. Puntos específicos de corrección (parte del cuerpo, problema, corrección recomendada)
                4. Aspectos positivos de la forma
                5. Recomendaciones para mejorar
                6. Evaluación de riesgos potenciales de lesión
                
                Sé específico, detallado y proporciona feedback accionable basado en principios de biomecánica.
                """
                
                multimodal_result = await self.multimodal_adapter.process_multimodal(
                    prompt=prompt,
                    image_data=image_data,
                    temperature=0.2,
                    max_output_tokens=1024
                )
                
                # Extraer puntos de corrección estructurados
                correction_points_prompt = f"""
                Basándote en el siguiente análisis de forma de ejercicio, extrae puntos específicos de corrección
                en formato estructurado. Para cada punto, incluye:
                1. Parte del cuerpo relacionada
                2. Problema identificado
                3. Corrección recomendada
                4. Severidad del problema (leve, moderada, grave)
                5. Nivel de confianza en la detección (0.0-1.0)
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """
                
                correction_points_response = await self.gemini_client.generate_structured_output(correction_points_prompt)
                
                # Procesar puntos de corrección
                correction_points = []
                if isinstance(correction_points_response, list):
                    for point in correction_points_response:
                        if isinstance(point, dict) and "body_part" in point:
                            correction_points.append(FormCorrectionPoint(
                                body_part=point.get("body_part", "No especificado"),
                                issue=point.get("issue", "No especificado"),
                                correction=point.get("correction", "No especificado"),
                                severity=point.get("severity", "moderada"),
                                confidence=point.get("confidence", 0.7)
                            ))
                elif isinstance(correction_points_response, dict) and "correction_points" in correction_points_response:
                    for point in correction_points_response["correction_points"]:
                        if isinstance(point, dict) and "body_part" in point:
                            correction_points.append(FormCorrectionPoint(
                                body_part=point.get("body_part", "No especificado"),
                                issue=point.get("issue", "No especificado"),
                                correction=point.get("correction", "No especificado"),
                                severity=point.get("severity", "moderada"),
                                confidence=point.get("confidence", 0.7)
                            ))
                
                # Si no hay puntos de corrección, crear uno genérico
                if not correction_points:
                    correction_points.append(FormCorrectionPoint(
                        body_part="General",
                        issue="No se pudieron identificar problemas específicos",
                        correction="Consulta a un entrenador personal para una evaluación detallada",
                        severity="leve",
                        confidence=0.5
                    ))
                
                # Extraer aspectos positivos y recomendaciones
                strengths_recommendations_prompt = f"""
                Basándote en el siguiente análisis de forma de ejercicio, extrae:
                1. 3-5 aspectos positivos de la forma
                2. 3-5 recomendaciones específicas para mejorar
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado con las claves "strengths" y "recommendations".
                """
                
                strengths_recommendations_response = await self.gemini_client.generate_structured_output(strengths_recommendations_prompt)
                
                # Procesar aspectos positivos y recomendaciones
                strengths = []
                recommendations = []
                
                if isinstance(strengths_recommendations_response, dict):
                    strengths = strengths_recommendations_response.get("strengths", [])
                    recommendations = strengths_recommendations_response.get("recommendations", [])
                
                # Si no hay aspectos positivos o recomendaciones, crear genéricos
                if not strengths:
                    strengths = ["Disposición para mejorar la técnica", "Interés en el análisis de forma"]
                
                if not recommendations:
                    recommendations = ["Consulta a un entrenador personal para una evaluación detallada", "Practica frente a un espejo para mayor conciencia corporal"]
                
                # Extraer puntuación de calidad de forma
                form_quality_score = 7.5  # Valor por defecto
                try:
                    # Intentar extraer la puntuación del análisis
                    score_prompt = f"""
                    Basándote en el siguiente análisis de forma de ejercicio, extrae la puntuación de calidad de forma (0-10).
                    Si no hay una puntuación explícita, asigna una basada en el análisis general.
                    
                    Análisis:
                    {multimodal_result.get("text", "")}
                    
                    Devuelve solo el número (por ejemplo, 7.5).
                    """
                    
                    score_response = await self.gemini_client.generate_text(score_prompt)
                    try:
                        # Intentar convertir la respuesta a un número
                        form_quality_score = float(score_response.strip())
                        # Asegurar que está en el rango 0-10
                        form_quality_score = max(0, min(10, form_quality_score))
                    except:
                        # Si no se puede convertir, usar el valor por defecto
                        pass
                except:
                    # Si hay algún error, usar el valor por defecto
                    pass
                
                # Crear artefacto con el análisis
                import uuid
                artifact_id = str(uuid.uuid4())
                artifact = ExerciseFormAnalysisArtifact(
                    analysis_id=artifact_id,
                    exercise_name=exercise_name,
                    timestamp=datetime.now().isoformat(),
                    form_quality_score=form_quality_score,
                    processed_image_url=""  # En un caso real, aquí iría la URL de la imagen procesada
                )
                
                # Crear la salida de la skill
                return AnalyzeExerciseFormOutput(
                    exercise_name=exercise_name,
                    form_quality_score=form_quality_score,
                    form_analysis=multimodal_result.get("text", ""),
                    correction_points=correction_points,
                    strengths=strengths,
                    recommendations=recommendations,
                    risk_assessment={"risk_level": "moderado", "areas_of_concern": [p.body_part for p in correction_points if p.severity == "grave"]}
                )
                
        except Exception as e:
            logger.error(f"Error al analizar forma de ejercicio: {e}", exc_info=True)
            
            # En caso de error, devolver un análisis básico
            return self._generate_mock_exercise_form_analysis(input_data)
    
    def _generate_mock_exercise_form_analysis(self, input_data: AnalyzeExerciseFormInput) -> AnalyzeExerciseFormOutput:
        """
        Genera un análisis simulado de forma de ejercicio cuando no se pueden utilizar las capacidades de visión.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            AnalyzeExerciseFormOutput: Análisis simulado de la forma del ejercicio
        """
        exercise_name = input_data.exercise_name or "Ejercicio no especificado"
        
        return AnalyzeExerciseFormOutput(
            exercise_name=exercise_name,
            form_quality_score=5.0,
            form_analysis=f"Análisis simulado para {exercise_name}. No se pudo realizar un análisis real de la imagen.",
            correction_points=[
                FormCorrectionPoint(
                    body_part="General",
                    issue="No se pudo analizar la imagen",
                    correction="Consulta a un entrenador personal para una evaluación detallada",
                    severity="moderada",
                    confidence=0.0
                )
            ],
            strengths=["No se pudieron identificar aspectos positivos"],
            recommendations=["Consulta a un entrenador personal para una evaluación detallada"],
            risk_assessment={"risk_level": "desconocido", "areas_of_concern": []}
        )
    
    async def _skill_compare_exercise_progress(self, input_data: CompareExerciseProgressInput) -> CompareExerciseProgressOutput:
        """
        Skill para comparar el progreso en ejercicios a través de imágenes.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            CompareExerciseProgressOutput: Comparación del progreso en ejercicios
        """
        logger.info(f"Ejecutando habilidad: _skill_compare_exercise_progress para ejercicio: {input_data.exercise_name}")
        
        try:
            # Obtener datos de las imágenes
            before_image = input_data.before_image
            after_image = input_data.after_image
            exercise_name = input_data.exercise_name or "Ejercicio no especificado"
            time_between_images = input_data.time_between_images or "No especificado"
            metrics_to_compare = input_data.metrics_to_compare or ["postura", "técnica", "rango de movimiento", "estabilidad"]
            
            # Verificar si las capacidades de visión están disponibles
            if not hasattr(self, '_vision_capabilities_available') or not self._vision_capabilities_available:
                logger.warning("Capacidades de visión no disponibles. Usando comparación simulada.")
                return self._generate_mock_exercise_progress_comparison(input_data)
            
            # Utilizar las capacidades multimodales del agente base
            with self.tracer.start_as_current_span("exercise_progress_comparison"):
                # Comparar las imágenes utilizando el adaptador multimodal
                comparison_prompt = f"""
                Compara estas dos imágenes de un atleta realizando {exercise_name}.
                La primera imagen es de ANTES y la segunda es de DESPUÉS, con un intervalo de tiempo de {time_between_images}.
                
                Identifica y describe:
                1. Similitudes en la técnica y postura
                2. Diferencias y cambios observados
                3. Mejoras o retrocesos en la forma
                
                Enfócate en los siguientes aspectos: {', '.join(metrics_to_compare)}
                """
                
                comparison_result = await self.multimodal_adapter.compare_images(
                    image_data1=before_image,
                    image_data2=after_image,
                    comparison_prompt=comparison_prompt,
                    temperature=0.2,
                    max_output_tokens=1024
                )
                
                # Extraer análisis de progreso usando el modelo multimodal
                detailed_prompt = f"""
                Eres un entrenador experto en biomecánica y técnica de ejercicios. Compara estas dos imágenes de un atleta
                realizando {exercise_name} y proporciona un análisis detallado del progreso.
                
                La primera imagen es de ANTES y la segunda es de DESPUÉS, con un intervalo de tiempo de {time_between_images}.
                
                Enfócate específicamente en los siguientes aspectos:
                {', '.join(metrics_to_compare)}
                
                Proporciona:
                1. Un resumen del progreso observado
                2. Mejoras clave identificadas
                3. Cambios en la forma del ejercicio
                4. Recomendaciones basadas en el progreso
                5. Una puntuación cuantitativa del progreso (0-10)
                
                Sé específico, detallado y proporciona feedback accionable basado en principios de biomecánica.
                """
                
                # Realizar un análisis detallado con ambas imágenes
                detailed_analysis = await self.multimodal_adapter.compare_images(
                    image_data1=before_image,
                    image_data2=after_image,
                    comparison_prompt=detailed_prompt,
                    temperature=0.2,
                    max_output_tokens=1024
                )
                
                # Usar el resultado de la comparación para generar un análisis estructurado
                progress_analysis_prompt = f"""
                Basándote en la siguiente comparación de imágenes de ejercicio, genera un análisis estructurado
                del progreso.
                
                Comparación inicial:
                {comparison_result.get("text", "")}
                
                Análisis detallado:
                {detailed_analysis.get("text", "")}
                
                Genera un análisis estructurado con:
                1. Resumen del progreso
                2. Mejoras clave identificadas (lista de diccionarios con "area" y "improvement")
                3. Cambios en la forma del ejercicio (lista de diccionarios con "aspect" y "change")
                4. Recomendaciones basadas en el progreso (lista de strings)
                5. Puntuación de progreso (0-10)
                
                Devuelve la información en formato JSON estructurado.
                """
                
                progress_analysis = await self.gemini_client.generate_structured_output(progress_analysis_prompt)
                
                # Procesar el análisis de progreso
                if not isinstance(progress_analysis, dict):
                    progress_analysis = {
                        "progress_summary": "No se pudo generar un análisis estructurado",
                        "key_improvements": [],
                        "form_changes": [],
                        "recommendations": ["Consulta a un entrenador personal para una evaluación detallada"],
                        "progress_score": 5.0
                    }
                
                # Asegurar que todas las claves necesarias estén presentes
                progress_summary = progress_analysis.get("progress_summary", "No disponible")
                key_improvements = progress_analysis.get("key_improvements", [])
                form_changes = progress_analysis.get("form_changes", [])
                recommendations = progress_analysis.get("recommendations", [])
                progress_score = progress_analysis.get("progress_score", 5.0)
                
                # Si no hay mejoras clave o cambios en la forma, crear genéricos
                if not key_improvements:
                    key_improvements = [{"area": "General", "improvement": "No se pudieron identificar mejoras específicas"}]
                
                if not form_changes:
                    form_changes = [{"aspect": "General", "change": "No se pudieron identificar cambios específicos en la forma"}]
                
                if not recommendations:
                    recommendations = ["Continúa con la práctica regular", "Consulta a un entrenador personal para una evaluación detallada"]
                
                # Crear la salida de la skill
                return CompareExerciseProgressOutput(
                    exercise_name=exercise_name,
                    progress_summary=progress_summary,
                    key_improvements=key_improvements,
                    form_changes=form_changes,
                    recommendations=recommendations,
                    progress_score=float(progress_score) if isinstance(progress_score, (int, float)) else 5.0
                )
                
        except Exception as e:
            logger.error(f"Error al comparar progreso en ejercicio: {e}", exc_info=True)
            
            # En caso de error, devolver una comparación básica
            return self._generate_mock_exercise_progress_comparison(input_data)
    
    def _generate_mock_exercise_progress_comparison(self, input_data: CompareExerciseProgressInput) -> CompareExerciseProgressOutput:
        """
        Genera una comparación simulada de progreso en ejercicios cuando no se pueden utilizar las capacidades de visión.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            CompareExerciseProgressOutput: Comparación simulada del progreso en ejercicios
        """
        exercise_name = input_data.exercise_name or "Ejercicio no especificado"
        
        return CompareExerciseProgressOutput(
            exercise_name=exercise_name,
            progress_summary=f"Comparación simulada para {exercise_name}. No se pudo realizar un análisis real de las imágenes.",
            key_improvements=[{"area": "General", "improvement": "No se pudieron identificar mejoras específicas"}],
            form_changes=[{"aspect": "General", "change": "No se pudieron identificar cambios específicos"}],
            recommendations=["Consulta a un entrenador personal para una evaluación detallada"],
            progress_score=5.0
        )

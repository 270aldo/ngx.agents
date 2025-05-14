"""
Agente especializado en nutrición de precisión.

Este agente genera planes alimenticios detallados, recomendaciones de suplementación
y estrategias de crononutrición basadas en biomarcadores y perfil del usuario.

Implementa los protocolos oficiales ADK y A2A para comunicación entre agentes.
"""

import logging
import uuid
import time
import json
import os
from typing import Dict, Any, Optional, List, Union
from google.cloud import aiplatform

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from agents.base.adk_agent import ADKAgent
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from core.logging_config import get_logger
from services.program_classification_service import ProgramClassificationService
from agents.shared.program_definitions import get_program_definition

# Importar Skill y Toolkit desde adk.agent
from adk.agent import Skill
from adk.toolkit import Toolkit

# Importar esquemas para las skills
from agents.precision_nutrition_architect.schemas import (
    CreateMealPlanInput, CreateMealPlanOutput,
    RecommendSupplementsInput, RecommendSupplementsOutput,
    AnalyzeBiomarkersInput, AnalyzeBiomarkersOutput,
    BiomarkerAnalysis,
    PlanChrononutritionInput, PlanChrononutritionOutput,
    AnalyzeFoodImageInput, AnalyzeFoodImageOutput,
    MealPlanArtifact, SupplementRecommendationArtifact,
    BiomarkerAnalysisArtifact, ChrononutritionPlanArtifact,
    FoodImageAnalysisArtifact
)

# Configurar logger
logger = get_logger(__name__)

class PrecisionNutritionArchitect(ADKAgent):
    """
    Agente especializado en nutrición de precisión.

    Este agente genera planes alimenticios detallados, recomendaciones de suplementación
    y estrategias de crononutrición basadas en biomarcadores y perfil del usuario.

    Implementa los protocolos oficiales ADK y A2A para comunicación entre agentes.
    """
    
    AGENT_ID = "precision_nutrition_architect"
    AGENT_NAME = "NGX Precision Nutrition Architect"
    AGENT_DESCRIPTION = "Genera planes alimenticios detallados, recomendaciones de suplementación y estrategias de crononutrición basadas en biomarcadores y perfil del usuario."
    DEFAULT_INSTRUCTION = """
    Eres un arquitecto de nutrición de precisión altamente especializado. 
    Tu función es analizar perfiles de usuario, datos biométricos y objetivos para generar 
    planes de alimentación detallados, recomendaciones de suplementación basadas en evidencia 
    y estrategias de crononutrición optimizadas. 
    Prioriza la salud, el rendimiento y la adherencia del usuario.
    """
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
        Inicializa el agente PrecisionNutritionArchitect.
        
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
        
        # Inicializar el servicio de clasificación de programas con caché
        self.gemini_client = GeminiClient()
        
        # Configurar caché para el servicio de clasificación de programas
        use_redis = os.environ.get('USE_REDIS_CACHE', 'false').lower() == 'true'
        cache_ttl = int(os.environ.get('PROGRAM_CACHE_TTL', '3600'))  # 1 hora por defecto
        self.program_classification_service = ProgramClassificationService(
            gemini_client=self.gemini_client,
            use_cache=use_redis,  # Habilitar caché según la configuración
            cache_ttl=cache_ttl  # Establecer el tiempo de vida de la caché
        )
        
        # Definir las skills antes de llamar al constructor de ADKAgent
        self.skills = [
            Skill(
                name="create_meal_plan",
                description="Crea un plan de comidas personalizado basado en el perfil, preferencias y objetivos del usuario.",
                handler=self._skill_create_meal_plan,
                input_schema=CreateMealPlanInput,
                output_schema=CreateMealPlanOutput
            ),
            Skill(
                name="recommend_supplements",
                description="Recomienda suplementos basados en el perfil, biomarcadores y objetivos del usuario.",
                handler=self._skill_recommend_supplements,
                input_schema=RecommendSupplementsInput,
                output_schema=RecommendSupplementsOutput
            ),
            Skill(
                name="analyze_biomarkers",
                description="Analiza biomarcadores y genera recomendaciones nutricionales personalizadas.",
                handler=self._skill_analyze_biomarkers,
                input_schema=AnalyzeBiomarkersInput,
                output_schema=AnalyzeBiomarkersOutput
            ),
            Skill(
                name="plan_chrononutrition",
                description="Planifica el timing nutricional para optimizar el rendimiento y la recuperación.",
                handler=self._skill_plan_chrononutrition,
                input_schema=PlanChrononutritionInput,
                output_schema=PlanChrononutritionOutput
            ),
            Skill(
                name="analyze_food_image",
                description="Analiza imágenes de alimentos para identificar componentes, estimar valores nutricionales y proporcionar recomendaciones.",
                handler=self._skill_analyze_food_image,
                input_schema=AnalyzeFoodImageInput,
                output_schema=AnalyzeFoodImageOutput
            )
        ]
        
        # Definir las capacidades del agente
        _capabilities = [
            "meal_plan_creation",
            "nutrition_assessment",
            "supplement_recommendation",
            "chrononutrition_planning",
            "biomarker_analysis",
            "food_image_analysis",
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
        
        # Inicializar Vertex AI
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform (Vertex AI SDK) inicializado correctamente para PrecisionNutritionArchitect.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform para PrecisionNutritionArchitect: {e}", exc_info=True)
        
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
                'analyze_food_image': lambda self, image_data: {"detected_foods": [], "text": "Análisis de imagen simulado"}
            })()
            
            self.multimodal_adapter = type('DummyMultimodalAdapter', (), {
                'process_multimodal': lambda self, prompt, image_data, temperature=0.2, max_output_tokens=1024:
                    {"text": "Análisis multimodal simulado"}
            })()
            
            self.tracer = type('DummyTracer', (), {
                'start_as_current_span': lambda name: type('DummySpan', (), {'__enter__': lambda self: None, '__exit__': lambda self, *args: None})()
            })
            
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
        context_key = f"context_{user_id}_{session_id}" if user_id and session_id else f"context_default_{uuid.uuid4().hex[:6]}"
        
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
                "meal_plans": [],
                "supplement_recommendations": [],
                "biomarker_analyses": [],
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.error(f"Error al obtener contexto: {e}", exc_info=True)
            # En caso de error, devolver un contexto vacío
            return {
                "conversation_history": [],
                "user_profile": {},
                "meal_plans": [],
                "supplement_recommendations": [],
                "biomarker_analyses": [],
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
                "meal_plan": "create_meal_plan",
                "supplement": "recommend_supplements",
                "biomarker": "analyze_biomarkers",
                "chrononutrition": "plan_chrononutrition"
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
        
        # Palabras clave para plan de comidas
        meal_plan_keywords = [
            "plan", "comida", "alimentación", "dieta", "menú", "receta", 
            "comer", "alimento", "nutrición", "macros", "calorías"
        ]
        
        # Palabras clave para suplementos
        supplements_keywords = [
            "suplemento", "vitamina", "mineral", "proteína", "creatina", 
            "omega", "aminoácido", "bcaa", "pre-entreno", "post-entreno"
        ]
        
        # Palabras clave para biomarcadores
        biomarkers_keywords = [
            "biomarcador", "análisis", "sangre", "laboratorio", "glucosa", 
            "colesterol", "triglicéridos", "hormona", "enzima", "vitamina d"
        ]
        
        # Palabras clave para crononutrición
        chrononutrition_keywords = [
            "crononutrición", "ayuno", "intermitente", "ventana", "timing", 
            "horario", "comida", "pre-entreno", "post-entreno", "desayuno", "cena"
        ]
        
        # Verificar coincidencias con palabras clave
        for keyword in chrononutrition_keywords:
            if keyword in query_lower:
                return "plan_chrononutrition"
                
        for keyword in biomarkers_keywords:
            if keyword in query_lower:
                return "analyze_biomarkers"
                
        for keyword in supplements_keywords:
            if keyword in query_lower:
                return "recommend_supplements"
                
        for keyword in meal_plan_keywords:
            if keyword in query_lower:
                return "create_meal_plan"
                
        # Si no hay coincidencias, devolver tipo general
        return "create_meal_plan"
    
    # --- Métodos para comunicación entre agentes ---
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
    
    async def _skill_create_meal_plan(self, input_data: CreateMealPlanInput) -> CreateMealPlanOutput:
        """
        Skill para generar un plan de comidas personalizado.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            CreateMealPlanOutput: Plan de comidas generado
        """
        logger.info(f"Ejecutando habilidad: _skill_create_meal_plan con input: {input_data.user_input[:30]}...")
        
        try:
            # Generar el plan de comidas
            meal_plan_dict = await self._generate_meal_plan(
                input_data.user_input,
                input_data.user_profile
            )
            
            # Crear la salida de la skill
            return CreateMealPlanOutput(**meal_plan_dict)
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_create_meal_plan': {e}", exc_info=True)
            # En caso de error, devolver un plan básico
            return CreateMealPlanOutput(
                daily_plan=[],
                total_calories=None,
                macronutrient_distribution=None,
                recommendations=["Error al generar el plan de comidas. Consulte a un profesional."],
                notes=str(e)
            )
    
    async def _skill_recommend_supplements(self, input_data: RecommendSupplementsInput) -> RecommendSupplementsOutput:
        """
        Skill para recomendar suplementos personalizados.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            RecommendSupplementsOutput: Recomendaciones de suplementos generadas
        """
        logger.info(f"Ejecutando habilidad: _skill_recommend_supplements con input: {input_data.user_input[:30]}...")
        
        try:
            # Determinar el tipo de programa del usuario para personalizar las recomendaciones
            context = {
                "user_profile": input_data.user_profile or {},
                "goals": input_data.user_profile.get("goals", []) if input_data.user_profile else []
            }
            
            try:
                # Clasificar el tipo de programa del usuario
                program_type = await self.program_classification_service.classify_program_type(context)
                logger.info(f"Tipo de programa determinado para recomendaciones de suplementos: {program_type}")
                
                # Obtener definición del programa para personalizar las recomendaciones
                program_def = get_program_definition(program_type)
                
                # Verificar si hay recomendaciones de suplementos específicas para el programa
                program_supplements = []
                if program_def and program_def.get("key_protocols") and "supplementation" in program_def.get("key_protocols", {}):
                    program_supplements = program_def.get("key_protocols", {}).get("supplementation", [])
                    logger.info(f"Encontradas {len(program_supplements)} recomendaciones de suplementos para el programa {program_type}")
            except Exception as e:
                logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando recomendaciones generales.")
                program_type = "GENERAL"
                program_supplements = []
            
            # Generar recomendaciones de suplementos
            rec_dict = await self._generate_supplement_recommendation(
                input_data.user_input,
                input_data.user_profile,
                program_type=program_type,
                program_supplements=program_supplements
            )
            
            # Crear la salida de la skill
            return RecommendSupplementsOutput(**rec_dict)
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_recommend_supplements': {e}", exc_info=True)
            # En caso de error, devolver recomendaciones básicas
            return RecommendSupplementsOutput(
                supplements=[],
                general_recommendations="Error al generar recomendaciones de suplementos. Consulte a un profesional.",
                notes=str(e)
            )
    
    async def _skill_analyze_biomarkers(self, input_data: AnalyzeBiomarkersInput) -> AnalyzeBiomarkersOutput:
        """
        Skill para analizar biomarcadores y proporcionar recomendaciones nutricionales.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            AnalyzeBiomarkersOutput: Análisis de biomarcadores generado
        """
        logger.info(f"Ejecutando habilidad: _skill_analyze_biomarkers con input: {input_data.user_input[:30]}...")
        
        try:
            # Generar el análisis de biomarcadores
            biomarker_data = await self._generate_biomarker_analysis(
                input_data.user_input,
                input_data.biomarkers
            )
            
            # Crear la lista de análisis de biomarcadores
            analyses_list = []
            for analysis in biomarker_data.get("analyses", []):
                analyses_list.append(BiomarkerAnalysis(
                    name=analysis.get("name", "No especificado"),
                    value=analysis.get("value", "No disponible"),
                    status=analysis.get("status", "No evaluado"),
                    reference_range=analysis.get("reference_range", "No disponible"),
                    interpretation=analysis.get("interpretation", "No disponible"),
                    nutritional_implications=analysis.get("nutritional_implications", ["No especificado"]),
                    recommendations=analysis.get("recommendations", ["Consulte a un profesional"])
                ))
            
            # Si no hay análisis, crear al menos uno predeterminado
            if not analyses_list:
                analyses_list.append(BiomarkerAnalysis(
                    name="Análisis general",
                    value="N/A",
                    status="No evaluado",
                    reference_range="N/A",
                    interpretation="No se proporcionaron biomarcadores específicos para analizar",
                    nutritional_implications=["Mantener una dieta equilibrada"],
                    recommendations=["Consulte a un profesional de la salud para un análisis detallado"]
                ))
            
            # Crear la salida de la skill
            return AnalyzeBiomarkersOutput(
                analyses=analyses_list,
                overall_assessment=biomarker_data.get("overall_assessment", "No se pudo realizar una evaluación completa."),
                nutritional_priorities=biomarker_data.get("nutritional_priorities", ["Mantener una dieta equilibrada"]),
                supplement_considerations=biomarker_data.get("supplement_considerations", ["Consulte a un profesional"])
            )
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_analyze_biomarkers': {e}", exc_info=True)
            # En caso de error, devolver un análisis básico
            return AnalyzeBiomarkersOutput(
                analyses=[
                    BiomarkerAnalysis(
                        name="Error en análisis",
                        value="N/A",
                        status="No evaluado",
                        reference_range="N/A",
                        interpretation="No se pudo analizar debido a un error",
                        nutritional_implications=["Mantener una dieta equilibrada"],
                        recommendations=["Consulte a un profesional de la salud"]
                    )
                ],
                overall_assessment="No se pudo realizar el análisis debido a un error en el procesamiento.",
                nutritional_priorities=["Mantener una dieta equilibrada", "Consultar con un profesional"],
                supplement_considerations=["Consulte a un profesional antes de tomar cualquier suplemento"]
            )
    
    async def _skill_plan_chrononutrition(self, input_data: PlanChrononutritionInput) -> PlanChrononutritionOutput:
        """
        Skill para planificar estrategias de crononutrición personalizadas.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            PlanChrononutritionOutput: Plan de crononutrición generado
        """
        logger.info(f"Ejecutando habilidad: _skill_plan_chrononutrition con input: {input_data.user_input[:30]}...")
        
        try:
            # Generar el plan de crononutrición
            chronoplan_dict = await self._generate_chrononutrition_plan(
                input_data.user_input,
                input_data.user_profile
            )
            
            # Crear la salida de la skill
            return PlanChrononutritionOutput(**chronoplan_dict)
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_plan_chrononutrition': {e}", exc_info=True)
            # En caso de error, devolver un plan básico
            return PlanChrononutritionOutput(
                time_windows=[],
                fasting_period=None,
                eating_period=None,
                pre_workout_nutrition=None,
                post_workout_nutrition=None,
                general_recommendations="Error al generar el plan de crononutrición. Consulte a un profesional."
            )
    
    # --- Métodos de generación de contenido ---
    
    async def _generate_meal_plan(
        self, user_input: str, user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Genera un plan de comidas personalizado basado en la entrada del usuario y su perfil.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario con información relevante (opcional)
            
        Returns:
            Dict[str, Any]: Plan de comidas generado
        """
        logger.info(f"Generando plan de comidas para entrada: {user_input[:50]}...")
        
        try:
            # Determinar el tipo de programa del usuario para personalizar el plan
            context = {
                "user_profile": user_profile or {},
                "goals": user_profile.get("goals", []) if user_profile else []
            }
            
            try:
                # Clasificar el tipo de programa del usuario utilizando el servicio con caché
                start_time = time.time()
                program_type = await self.program_classification_service.classify_program_type(context)
                elapsed_time = time.time() - start_time
                logger.info(f"Tipo de programa determinado para plan de comidas: {program_type} (tiempo: {elapsed_time:.2f}s)")
                
                # Obtener estadísticas de caché para monitoreo
                cache_stats = await self.program_classification_service.get_cache_stats()
                logger.debug(f"Estadísticas de caché del servicio de clasificación: {cache_stats}")
                
                # Obtener definición del programa para personalizar el plan
                program_def = get_program_definition(program_type)
                program_context = f"""\nCONTEXTO DEL PROGRAMA {program_type}:\n"""
                
                if program_def:
                    program_context += f"- {program_def.get('description', '')}\n"
                    program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                    
                    # Añadir necesidades nutricionales específicas del programa si están disponibles
                    if program_def.get("nutritional_needs"):
                        program_context += "- Necesidades nutricionales específicas:\n"
                        for need in program_def.get("nutritional_needs", []):
                            program_context += f"  * {need}\n"
                    
                    # Añadir estrategias nutricionales si están disponibles
                    if program_def.get("key_protocols") and "nutrition" in program_def.get("key_protocols", {}):
                        program_context += "- Estrategias nutricionales recomendadas:\n"
                        # Obtener recomendaciones específicas del programa utilizando el servicio con caché
                        nutrition_recommendations = await self.program_classification_service.get_program_specific_recommendations(
                            program_type, "nutrition"
                        )
                        
                        # Usar las recomendaciones obtenidas del servicio o caer en el fallback
                        if nutrition_recommendations:
                            for strategy in nutrition_recommendations:
                                program_context += f"  * {strategy}\n"
                        else:
                            # Fallback a las recomendaciones del programa_def si el servicio no devuelve datos
                            for strategy in program_def.get("key_protocols", {}).get("nutrition", []):
                                program_context += f"  * {strategy}\n"
                
            except Exception as e:
                logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando plan general.")
                program_type = "GENERAL"
                program_context = ""
            
            # Preparar prompt para el modelo
            prompt = f"""
            Eres un nutricionista experto especializado en nutrición de precisión. 
            Genera un plan de comidas detallado y personalizado basado en la siguiente solicitud:
            
            "{user_input}"
            {program_context}
            
            El plan debe incluir:
            1. Comidas para 7 días (desayuno, almuerzo, cena y snacks)
            2. Cantidades aproximadas de cada ingrediente
            3. Macronutrientes estimados por comida
            4. Recomendaciones generales alineadas con el programa {program_type}
            
            Devuelve el plan en formato JSON estructurado.
            """
            
            # Añadir información del perfil si está disponible
            if user_profile:
                prompt += f"""
                
                Considera la siguiente información del usuario:
                - Edad: {user_profile.get('age', 'No disponible')}
                - Género: {user_profile.get('gender', 'No disponible')}
                - Peso: {user_profile.get('weight', 'No disponible')} {user_profile.get('weight_unit', 'kg')}
                - Altura: {user_profile.get('height', 'No disponible')} {user_profile.get('height_unit', 'cm')}
                - Nivel de actividad: {user_profile.get('activity_level', 'No disponible')}
                - Objetivos: {', '.join(user_profile.get('goals', ['No disponible']))}
                - Restricciones dietéticas: {', '.join(user_profile.get('dietary_restrictions', ['Ninguna']))}
                - Alergias: {', '.join(user_profile.get('allergies', ['Ninguna']))}
                - Preferencias: {', '.join(user_profile.get('preferences', ['Ninguna']))}
                """
            
            # Generar el plan nutricional usando generate_text
            response_text = await self.gemini_client.generate_text(prompt)

            # Intentar extraer el JSON de la respuesta
            try:
                # Buscar un objeto JSON en la respuesta
                import re
                json_match = re.search(r'({.*})', response_text, re.DOTALL)
                if json_match:
                    response = json.loads(json_match.group(1))
                else:
                    # Si no se encuentra un objeto JSON, intentar parsear toda la respuesta
                    response = json.loads(response_text)
            except Exception as json_error:
                logger.error(f"Error al parsear JSON de la respuesta: {json_error}")
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "objective": "Plan nutricional personalizado",
                    "macronutrients": {
                        "protein": "25-30%",
                        "carbs": "40-50%",
                        "fats": "20-30%",
                    },
                    "calories": "Estimación personalizada pendiente",
                    "meals": [
                        {
                            "name": "Desayuno",
                            "examples": ["Ejemplo de desayuno balanceado"],
                        },
                        {
                            "name": "Almuerzo",
                            "examples": ["Ejemplo de almuerzo balanceado"],
                        },
                        {"name": "Cena", "examples": ["Ejemplo de cena balanceada"]},
                    ],
                    "recommended_foods": ["Alimentos saludables recomendados"],
                    "foods_to_avoid": ["Alimentos a evitar"],
                }
            
            # Formatear la respuesta según el esquema esperado
            formatted_response = {
                "daily_plan": [],
                "total_calories": response.get("calories", "No especificado"),
                "macronutrient_distribution": response.get("macronutrients", {}),
                "recommendations": [
                    f"Objetivo: {response.get('objective', 'No especificado')}",
                    "Alimentos recomendados: " + ", ".join(response.get("recommended_foods", [])),
                    "Alimentos a evitar: " + ", ".join(response.get("foods_to_avoid", [])),
                ],
                "notes": response.get("notes", "")
            }
            
            # Convertir las comidas al formato esperado
            for meal in response.get("meals", []):
                meal_items = []
                for example in meal.get("examples", []):
                    meal_items.append({
                        "name": example,
                        "portion": "Porción estándar",
                        "calories": None,
                        "macros": None
                    })
                
                formatted_response["daily_plan"].append({
                    "name": meal.get("name", "Comida"),
                    "time": meal.get("time", "No especificado"),
                    "items": meal_items,
                    "notes": meal.get("notes", "")
                })
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error al generar plan de comidas: {e}", exc_info=True)
            # Devolver un plan básico en caso de error
            return {
                "daily_plan": [
                    {
                        "name": "Desayuno",
                        "time": "8:00 AM",
                        "items": [
                            {
                                "name": "Ejemplo de desayuno balanceado",
                                "portion": "Porción estándar",
                                "calories": None,
                                "macros": None
                            }
                        ],
                        "notes": "Plan generado como respaldo debido a un error."
                    }
                ],
                "total_calories": "No disponible debido a un error",
                "macronutrient_distribution": {},
                "recommendations": ["Consulte con un nutricionista para un plan personalizado."],
                "notes": f"Error al generar plan: {str(e)}"
            }

    async def _generate_supplement_recommendation(
        self, user_input: str, user_profile: Optional[Dict[str, Any]] = None,
        program_type: str = "GENERAL", program_supplements: List[str] = None
    ) -> Dict[str, Any]:
        """
        Genera recomendaciones de suplementación personalizadas basadas en la entrada del usuario, su perfil y tipo de programa.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario con información relevante (opcional)
            program_type: Tipo de programa del usuario (PRIME, LONGEVITY, etc.)
            program_supplements: Lista de suplementos recomendados para el programa específico
            
        Returns:
            Dict[str, Any]: Recomendaciones de suplementación generadas
        """
        logger.info(f"Generando recomendaciones de suplementos para programa: {program_type}")
        
        # Inicializar la lista de suplementos del programa si es None
        if program_supplements is None:
            program_supplements = []
        
        # Preparar contexto específico del programa para el prompt
        program_context = ""
        if program_type != "GENERAL" and program_supplements:
            program_context = f"""
            
            CONTEXTO DEL PROGRAMA {program_type}:
            Este usuario sigue un programa {program_type}, que tiene las siguientes recomendaciones específicas de suplementación:
            {', '.join(program_supplements)}
            
            
            Asegúrate de incluir estos suplementos en tus recomendaciones si son apropiados para la solicitud del usuario,
            y explica cómo se alinean con los objetivos del programa {program_type}.
            """
        
        # Preparar prompt para el modelo
        prompt = f"""
        Eres un experto en nutrición y suplementación personalizada.
        
        Genera recomendaciones de suplementación personalizadas basadas en la siguiente solicitud:
        
        "{user_input}"
        {program_context}
        
        Las recomendaciones deben incluir:
        1. Suplementos principales recomendados (prioriza los específicos del programa {program_type} si son relevantes)
        2. Dosis sugerida para cada suplemento
        3. Timing óptimo de consumo
        4. Beneficios esperados, especialmente en relación con los objetivos del programa {program_type}
        5. Posibles interacciones o precauciones
        6. Alternativas naturales cuando sea posible
        
        Devuelve las recomendaciones en formato JSON estructurado.
        """

        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Edad: {user_profile.get('age', 'No disponible')}
            - Género: {user_profile.get('gender', 'No disponible')}
            - Peso: {user_profile.get('weight', 'No disponible')} {user_profile.get('weight_unit', 'kg')}
            - Altura: {user_profile.get('height', 'No disponible')} {user_profile.get('height_unit', 'cm')}
            - Nivel de actividad: {user_profile.get('activity_level', 'No disponible')}
            - Objetivos: {', '.join(user_profile.get('goals', ['No disponible']))}
            - Restricciones dietéticas: {', '.join(user_profile.get('dietary_restrictions', ['Ninguna']))}
            - Alergias: {', '.join(user_profile.get('allergies', ['Ninguna']))}
            - Condiciones médicas: {', '.join(user_profile.get('medical_conditions', ['Ninguna']))}
            """

        try:
            # Generar recomendaciones de suplementación usando generate_text
            response_text = await self.gemini_client.generate_text(prompt)

            # Intentar extraer el JSON de la respuesta
            try:
                # Buscar un objeto JSON en la respuesta
                import re
                json_match = re.search(r'({.*})', response_text, re.DOTALL)
                if json_match:
                    response = json.loads(json_match.group(1))
                else:
                    # Si no se encuentra un objeto JSON, intentar parsear toda la respuesta
                    response = json.loads(response_text)
            except Exception as json_error:
                logger.error(f"Error al parsear JSON de la respuesta: {json_error}")
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "supplements": [
                        {
                            "name": "Ejemplo de suplemento",
                            "dosage": "Dosis recomendada",
                            "timing": "Momento óptimo de consumo",
                            "benefits": ["Beneficios esperados"],
                            "precautions": ["Precauciones a considerar"],
                            "natural_alternatives": ["Alternativas naturales"],
                        }
                    ],
                    "general_recommendations": "Estas recomendaciones son generales y deben ser validadas por un profesional de la salud.",
                }
            
            # Formatear la respuesta según el esquema esperado
            formatted_response = {
                "supplements": [],
                "general_recommendations": response.get("general_recommendations", 
                    "Estas recomendaciones son generales y deben ser validadas por un profesional de la salud."),
                "notes": response.get("notes", "")
            }
            
            # Convertir los suplementos al formato esperado
            for supplement in response.get("supplements", []):
                formatted_supplement = {
                    "name": supplement.get("name", "Suplemento"),
                    "dosage": supplement.get("dosage", "Consulte a un profesional"),
                    "timing": supplement.get("timing", "Según indicaciones"),
                    "benefits": supplement.get("benefits", ["No especificado"]),
                    "precautions": supplement.get("precautions", []),
                    "natural_alternatives": supplement.get("natural_alternatives", [])
                }
                
                formatted_response["supplements"].append(formatted_supplement)
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error al generar recomendaciones de suplementos: {e}", exc_info=True)
            # Devolver recomendaciones básicas en caso de error
            return {
                "supplements": [
                    {
                        "name": "Multivitamínico general",
                        "dosage": "Según indicaciones del fabricante",
                        "timing": "Con las comidas",
                        "benefits": ["Apoyo nutricional básico"],
                        "precautions": ["Consulte a un profesional de la salud antes de comenzar cualquier suplementación"],
                        "natural_alternatives": ["Dieta variada rica en frutas y verduras"]
                    }
                ],
                "general_recommendations": "Debido a un error en el procesamiento, se proporcionan recomendaciones básicas. Por favor, consulte a un profesional de la salud para recomendaciones personalizadas.",
                "notes": f"Error al generar recomendaciones: {str(e)}"
            }
    
    async def _generate_biomarker_analysis(self, user_input: str, biomarkers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un análisis detallado de biomarcadores con recomendaciones personalizadas.
        
        Args:
            user_input: Texto de entrada del usuario
            biomarkers: Diccionario con los datos de biomarcadores
            
        Returns:
            Dict[str, Any]: Análisis detallado de biomarcadores
        """
        # Preparar prompt para el modelo
        prompt = f"""
        {self.instruction}
        
        Analiza los siguientes datos de biomarcadores y proporciona recomendaciones nutricionales y de estilo de vida basadas en ellos.
        Solicitud del usuario: "{user_input}"
        Datos de biomarcadores: {json.dumps(biomarkers, indent=2)}

        Proporciona un análisis detallado, identifica posibles áreas de mejora y sugiere acciones concretas.
        Devuelve el análisis y las recomendaciones en formato JSON estructurado.
        Ejemplo de estructura deseada:
        {{ 
          "analyses": [
            {{ 
              "name": "Glucosa en ayunas", 
              "value": "105", 
              "status": "Elevado", 
              "reference_range": "70-99 mg/dL", 
              "interpretation": "Ligeramente elevado, indica posible prediabetes", 
              "nutritional_implications": ["Reducir consumo de azúcares simples", "Aumentar fibra soluble"], 
              "recommendations": ["Incorporar más vegetales", "Limitar carbohidratos refinados"] 
            }},
            {{ 
              "name": "Vitamina D", 
              "value": "25", 
              "status": "Insuficiente", 
              "reference_range": "30-100 ng/mL", 
              "interpretation": "Niveles subóptimos que pueden afectar la salud ósea e inmunológica", 
              "nutritional_implications": ["Baja absorción de calcio", "Posible impacto en inmunidad"], 
              "recommendations": ["Exposición solar moderada", "Consumir pescados grasos", "Considerar suplementación"] 
            }}
          ],
          "overall_assessment": "Evaluación general del perfil biométrico",
          "nutritional_priorities": ["Prioridad 1", "Prioridad 2"],
          "supplement_considerations": ["Consideración 1", "Consideración 2"]
        }}
        """
        
        try:
            logger.debug(f"Generando prompt para análisis de biomarcadores: {prompt[:500]}...") # Loguea una parte del prompt
            response_text = await self.gemini_client.generate_text(prompt)
            
            # Intentar extraer el JSON de la respuesta
            try:
                # Buscar un objeto JSON en la respuesta
                import re
                json_match = re.search(r'({.*})', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group(1))
                else:
                    # Si no se encuentra un objeto JSON, intentar parsear toda la respuesta
                    analysis = json.loads(response_text)
            except Exception as json_error:
                logger.error(f"Error al parsear JSON de la respuesta: {json_error}")
                analysis = { 
                    "analyses": [
                        {
                            "name": "Error en análisis",
                            "value": "N/A",
                            "status": "No evaluado",
                            "reference_range": "N/A",
                            "interpretation": "No se pudo analizar debido a un error",
                            "nutritional_implications": ["Mantener una dieta equilibrada"],
                            "recommendations": ["Consulte a un profesional de la salud"]
                        }
                    ],
                    "overall_assessment": "No se pudo realizar una evaluación completa debido a un error",
                    "nutritional_priorities": ["Mantener una dieta equilibrada"],
                    "supplement_considerations": ["Consulte a un profesional antes de tomar cualquier suplemento"]
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error al generar análisis de biomarcadores: {e}", exc_info=True)
            # Devolver un análisis básico en caso de error
            return {
                "analyses": [
                    {
                        "name": "Error en análisis",
                        "value": "N/A",
                        "status": "No evaluado",
                        "reference_range": "N/A",
                        "interpretation": "No se pudo analizar debido a un error",
                        "nutritional_implications": ["Mantener una dieta equilibrada"],
                        "recommendations": ["Consulte a un profesional de la salud"]
                    }
                ],
                "overall_assessment": "No se pudo realizar una evaluación completa debido a un error",
                "nutritional_priorities": ["Mantener una dieta equilibrada"],
                "supplement_considerations": ["Consulte a un profesional antes de tomar cualquier suplemento"]
            }
    
    async def _generate_chrononutrition_plan(self, user_input: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un plan de crononutrición optimizado basado en la entrada del usuario y su perfil.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario con información relevante
            
        Returns:
            Dict[str, Any]: Plan de crononutrición detallado
        """
        # Extraer información relevante del perfil
        profile_summary = ""
        if user_profile:
            profile_items = []
            if user_profile.get("name"):
                profile_items.append(f"Nombre: {user_profile['name']}")
            if user_profile.get("age"):
                profile_items.append(f"Edad: {user_profile['age']}")
            if user_profile.get("weight"):
                profile_items.append(f"Peso: {user_profile['weight']} kg")
            if user_profile.get("height"):
                profile_items.append(f"Altura: {user_profile['height']} cm")
            if user_profile.get("goals"):
                profile_items.append(f"Objetivos: {user_profile['goals']}")
            if user_profile.get("dietary_restrictions"):
                profile_items.append(f"Restricciones alimenticias: {user_profile['dietary_restrictions']}")
            if user_profile.get("allergies"):
                profile_items.append(f"Alergias: {user_profile['allergies']}")
            if user_profile.get("activity_level"):
                profile_items.append(f"Nivel de actividad: {user_profile['activity_level']}")
            if user_profile.get("training_schedule"):
                profile_items.append(f"Horario de entrenamiento: {user_profile['training_schedule']}")
            
            profile_summary = "\n".join(profile_items)
        
        # Preparar prompt para el modelo
        prompt = f"""
        {self.instruction}
        
        Diseña un plan de crononutrición optimizado basado en la siguiente solicitud y perfil del usuario.
        Solicitud del usuario: "{user_input}"
        
        Perfil del usuario:
        {profile_summary}

        El plan debe incluir recomendaciones sobre el timing de las comidas principales, snacks, y la ingesta de macronutrientes alrededor de los entrenamientos (si aplica) y a lo largo del día para optimizar energía, rendimiento y recuperación.
        Considera los objetivos, nivel de actividad y preferencias del usuario si están disponibles en el perfil.
        
        Devuelve el plan en formato JSON estructurado.
        Ejemplo de estructura deseada:
        {{ 
          "time_windows": [
            {{ "time": "06:00-07:00", "meal": "Desayuno", "description": "Comida rica en proteínas y carbohidratos complejos", "examples": ["Avena con frutas y nueces", "Huevos revueltos con tostada integral"] }},
            {{ "time": "10:00-10:30", "meal": "Snack", "description": "Snack ligero con proteínas", "examples": ["Yogur griego con frutas", "Puñado de frutos secos"] }},
            {{ "time": "12:30-13:30", "meal": "Almuerzo", "description": "Comida balanceada con proteínas, carbohidratos y grasas saludables", "examples": ["Pechuga de pollo con arroz integral y vegetales", "Ensalada con salmón y quinoa"] }},
            {{ "time": "16:00-16:30", "meal": "Snack pre-entreno", "description": "Carbohidratos de rápida absorción", "examples": ["Plátano", "Batido de frutas"] }},
            {{ "time": "19:00-20:00", "meal": "Cena", "description": "Comida ligera rica en proteínas y vegetales", "examples": ["Pescado al horno con vegetales asados", "Tofu salteado con verduras"] }}
          ],
          "fasting_period": "20:30-06:00 (10 horas)",
          "eating_period": "06:00-20:30 (14 horas)",
          "pre_workout_nutrition": "Consumir carbohidratos de fácil digestión 30-60 minutos antes del ejercicio",
          "post_workout_nutrition": "Consumir proteínas y carbohidratos dentro de los 30-60 minutos posteriores al ejercicio",
          "general_recommendations": [
            "Mantener una hidratación adecuada a lo largo del día",
            "Ajustar la ingesta calórica según los días de entrenamiento y descanso",
            "Evitar comidas pesadas antes de dormir"
          ]
        }}
        """
        
        try:
            logger.debug(f"Generando prompt para plan de crononutrición: {prompt[:500]}...") # Loguea una parte del prompt
            response_text = await self.gemini_client.generate_text(prompt)
            
            # Intentar extraer el JSON de la respuesta
            try:
                # Buscar un objeto JSON en la respuesta
                import re
                json_match = re.search(r'({.*})', response_text, re.DOTALL)
                if json_match:
                    chronoplan = json.loads(json_match.group(1))
                else:
                    # Si no se encuentra un objeto JSON, intentar parsear toda la respuesta
                    chronoplan = json.loads(response_text)
            except Exception as json_error:
                logger.error(f"Error al parsear JSON de la respuesta: {json_error}")
                chronoplan = { 
                    "time_windows": [
                        {
                            "time": "07:00-08:00",
                            "meal": "Desayuno",
                            "description": "Comida rica en proteínas y carbohidratos complejos",
                            "examples": ["Avena con frutas y nueces", "Huevos revueltos con tostada integral"]
                        },
                        {
                            "time": "12:00-13:00",
                            "meal": "Almuerzo",
                            "description": "Comida balanceada con proteínas, carbohidratos y grasas saludables",
                            "examples": ["Pechuga de pollo con arroz integral y vegetales", "Ensalada con salmón y quinoa"]
                        },
                        {
                            "time": "19:00-20:00",
                            "meal": "Cena",
                            "description": "Comida ligera rica en proteínas y vegetales",
                            "examples": ["Pescado al horno con vegetales asados", "Tofu salteado con verduras"]
                        }
                    ],
                    "fasting_period": "20:00-07:00 (11 horas)",
                    "eating_period": "07:00-20:00 (13 horas)",
                    "pre_workout_nutrition": "Consumir carbohidratos de fácil digestión 30-60 minutos antes del ejercicio",
                    "post_workout_nutrition": "Consumir proteínas y carbohidratos dentro de los 30-60 minutos posteriores al ejercicio",
                    "general_recommendations": [
                        "Mantener una hidratación adecuada a lo largo del día",
                        "Ajustar la ingesta calórica según los días de entrenamiento y descanso",
                        "Evitar comidas pesadas antes de dormir"
                    ]
                }
            
            return chronoplan
            
        except Exception as e:
            logger.error(f"Error al generar plan de crononutrición: {e}", exc_info=True)
            # Devolver un plan básico en caso de error
            return {
                "time_windows": [
                    {
                        "time": "07:00-08:00",
                        "meal": "Desayuno",
                        "description": "Comida rica en proteínas y carbohidratos complejos",
                        "examples": ["Avena con frutas y nueces", "Huevos revueltos con tostada integral"]
                    },
                    {
                        "time": "12:00-13:00",
                        "meal": "Almuerzo",
                        "description": "Comida balanceada con proteínas, carbohidratos y grasas saludables",
                        "examples": ["Pechuga de pollo con arroz integral y vegetales", "Ensalada con salmón y quinoa"]
                    },
                    {
                        "time": "19:00-20:00",
                        "meal": "Cena",
                        "description": "Comida ligera rica en proteínas y vegetales",
                        "examples": ["Pescado al horno con vegetales asados", "Tofu salteado con verduras"]
                    }
                ],
                "fasting_period": "20:00-07:00 (11 horas)",
                "eating_period": "07:00-20:00 (13 horas)",
                "pre_workout_nutrition": "Consumir carbohidratos de fácil digestión 30-60 minutos antes del ejercicio",
                "post_workout_nutrition": "Consumir proteínas y carbohidratos dentro de los 30-60 minutos posteriores al ejercicio",
                "general_recommendations": [
                    "Mantener una hidratación adecuada a lo largo del día",
                    "Ajustar la ingesta calórica según los días de entrenamiento y descanso",
                    "Evitar comidas pesadas antes de dormir"
                ]
            }
    
    async def _skill_analyze_food_image(self, input_data: AnalyzeFoodImageInput) -> AnalyzeFoodImageOutput:
        """
        Skill para analizar imágenes de alimentos.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            AnalyzeFoodImageOutput: Análisis de la imagen de alimentos
        """
        logger.info(f"Ejecutando skill de análisis de imágenes de alimentos")
        
        try:
            # Obtener datos de la imagen
            image_data = input_data.image_data
            user_profile = input_data.user_profile or {}
            dietary_preferences = input_data.dietary_preferences or []
            
            # Determinar el tipo de programa del usuario para personalizar el análisis
            context = {
                "user_profile": user_profile,
                "goals": user_profile.get("goals", []) if user_profile else []
            }
            
            try:
                # Clasificar el tipo de programa del usuario
                program_type = await self.program_classification_service.classify_program_type(context)
                logger.info(f"Tipo de programa determinado para análisis de imagen de alimentos: {program_type}")
                
                # Obtener definición del programa para personalizar el análisis
                program_def = get_program_definition(program_type)
                program_context = f"""\nCONTEXTO DEL PROGRAMA {program_type}:\n"""
                
                if program_def:
                    program_context += f"- {program_def.get('description', '')}\n"
                    program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                    
                    # Añadir necesidades nutricionales específicas del programa si están disponibles
                    if program_def.get("nutritional_needs"):
                        program_context += "- Necesidades nutricionales específicas:\n"
                        for need in program_def.get("nutritional_needs", []):
                            program_context += f"  * {need}\n"
            except Exception as e:
                logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando análisis general.")
                program_type = "GENERAL"
                program_context = ""
            
            # Utilizar las capacidades de visión del agente base
            with self.tracer.start_as_current_span("food_image_analysis"):
                # Verificar si las capacidades de visión están disponibles
                if not hasattr(self, '_vision_capabilities_available') or not self._vision_capabilities_available:
                    logger.warning("Capacidades de visión no disponibles. Usando análisis simulado.")
                    vision_result = {"detected_foods": [], "text": "Análisis de imagen simulado"}
                else:
                    # Analizar la imagen utilizando el procesador de visión
                    vision_result = await self.vision_processor.analyze_image(
                        image_data=image_data,
                        prompt="Analiza esta imagen de alimentos e identifica todos los alimentos visibles."
                    )
                
                # Extraer información de alimentos de la imagen usando el modelo multimodal
                prompt = f"""
                Eres un experto en nutrición y análisis de alimentos. Analiza esta imagen de alimentos y proporciona:
                
                1. Identificación precisa de todos los alimentos visibles
                2. Estimación de calorías y macronutrientes (proteínas, carbohidratos, grasas)
                3. Evaluación nutricional general (qué tan saludable es esta comida)
                4. Recomendaciones para mejorar el valor nutricional
                
                Considera que este análisis es para un usuario con programa tipo {program_type}.
                {program_context}
                
                Proporciona un análisis detallado y objetivo basado únicamente en lo que es visible en la imagen.
                """
                
                multimodal_result = await self.multimodal_adapter.process_multimodal(
                    prompt=prompt,
                    image_data=image_data,
                    temperature=0.2,
                    max_output_tokens=1024
                )
                
                # Extraer información de alimentos detectados
                food_items = []
                for food in vision_result.get("detected_foods", []):
                    food_item = {
                        "name": food,
                        "confidence_score": 0.85,  # Valor simulado
                        "estimated_calories": "No disponible",
                        "estimated_portion": "Porción estándar",
                        "macronutrients": {
                            "proteínas": "No disponible",
                            "carbohidratos": "No disponible",
                            "grasas": "No disponible"
                        }
                    }
                    food_items.append(food_item)
                
                # Si no se detectaron alimentos, extraer de la respuesta multimodal
                if not food_items:
                    # Analizar la respuesta multimodal para extraer alimentos
                    analysis_text = multimodal_result.get("text", "")
                    
                    # Generar prompt para extraer alimentos estructurados
                    extraction_prompt = f"""
                    Basándote en el siguiente análisis de una imagen de alimentos, extrae una lista estructurada
                    de los alimentos identificados con sus propiedades nutricionales estimadas.
                    
                    Análisis:
                    {analysis_text}
                    
                    Devuelve la información en formato JSON estructurado con los siguientes campos para cada alimento:
                    - name: nombre del alimento
                    - estimated_calories: calorías estimadas (si es posible)
                    - estimated_portion: porción estimada
                    - macronutrients: macronutrientes estimados (proteínas, carbohidratos, grasas)
                    
                    Ejemplo de formato:
                    [
                      {
                        "name": "Pollo a la parrilla",
                        "estimated_calories": "150-200 kcal",
                        "estimated_portion": "100g",
                        "macronutrients": {
                          "proteínas": "25-30g",
                          "carbohidratos": "0g",
                          "grasas": "8-10g"
                        }
                      }
                    ]
                    """
                    
                    extraction_response = await self.gemini_client.generate_structured_output(extraction_prompt)
                    
                    # Procesar la respuesta
                    if isinstance(extraction_response, list):
                        for food in extraction_response:
                            if isinstance(food, dict) and "name" in food:
                                food_items.append({
                                    "name": food.get("name", "Alimento no identificado"),
                                    "confidence_score": 0.7,  # Valor por defecto
                                    "estimated_calories": food.get("estimated_calories", "No disponible"),
                                    "estimated_portion": food.get("estimated_portion", "Porción estándar"),
                                    "macronutrients": food.get("macronutrients", {
                                        "proteínas": "No disponible",
                                        "carbohidratos": "No disponible",
                                        "grasas": "No disponible"
                                    })
                                })
                
                # Si aún no hay alimentos identificados, crear uno genérico
                if not food_items:
                    food_items.append({
                        "name": "Comida no identificada específicamente",
                        "confidence_score": 0.5,
                        "estimated_calories": "No disponible",
                        "estimated_portion": "No disponible",
                        "macronutrients": {
                            "proteínas": "No disponible",
                            "carbohidratos": "No disponible",
                            "grasas": "No disponible"
                        }
                    })
                
                # Generar evaluación nutricional
                nutritional_assessment_prompt = f"""
                Basándote en el siguiente análisis de una imagen de alimentos, genera una evaluación nutricional
                concisa y objetiva. Considera el contexto del programa {program_type} del usuario.
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                La evaluación debe ser de 2-3 párrafos y debe incluir:
                1. Valoración general de la calidad nutricional
                2. Aspectos positivos de la comida
                3. Áreas de mejora
                """
                
                nutritional_assessment = await self.gemini_client.generate_text(nutritional_assessment_prompt)
                
                # Generar recomendaciones
                recommendations_prompt = f"""
                Basándote en el siguiente análisis de una imagen de alimentos, genera 3-5 recomendaciones
                nutricionales específicas y accionables. Considera el contexto del programa {program_type} del usuario
                y sus preferencias dietéticas: {', '.join(dietary_preferences) if dietary_preferences else 'No especificadas'}.
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Las recomendaciones deben ser concretas, prácticas y enfocadas en mejorar el valor nutricional
                manteniendo el tipo de comida similar.
                """
                
                recommendations_response = await self.gemini_client.generate_text(recommendations_prompt)
                recommendations = [rec.strip() for rec in recommendations_response.split("\n") if rec.strip()]
                
                # Generar alternativas más saludables
                alternatives_prompt = f"""
                Basándote en el siguiente análisis de una imagen de alimentos, sugiere 2-3 alternativas más saludables
                para los alimentos identificados. Considera el contexto del programa {program_type} del usuario.
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Para cada alternativa, proporciona:
                1. El alimento original
                2. La alternativa más saludable
                3. Beneficio nutricional de la alternativa
                
                Devuelve la información en formato JSON estructurado.
                """
                
                alternatives_response = await self.gemini_client.generate_structured_output(alternatives_prompt)
                
                # Procesar alternativas
                alternatives = []
                if isinstance(alternatives_response, list):
                    alternatives = alternatives_response
                elif isinstance(alternatives_response, dict) and "alternatives" in alternatives_response:
                    alternatives = alternatives_response["alternatives"]
                else:
                    # Crear alternativas genéricas
                    for food in food_items:
                        alternatives.append({
                            "original": food["name"],
                            "alternative": f"Versión más saludable de {food['name']}",
                            "benefit": "Mayor valor nutricional y menos calorías"
                        })
                
                # Calcular puntuación de salud (simulada)
                health_score = 7.5  # Valor simulado entre 0-10
                
                # Crear artefacto con el análisis
                artifact_id = str(uuid.uuid4())
                artifact = FoodImageAnalysisArtifact(
                    analysis_id=artifact_id,
                    created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                    food_count=len(food_items),
                    health_score=health_score,
                    processed_image_url=""  # En un caso real, aquí iría la URL de la imagen procesada
                )
                
                # Determinar tipo de comida
                meal_type = "No determinado"
                if "desayuno" in multimodal_result.get("text", "").lower():
                    meal_type = "Desayuno"
                elif "almuerzo" in multimodal_result.get("text", "").lower() or "comida" in multimodal_result.get("text", "").lower():
                    meal_type = "Almuerzo"
                elif "cena" in multimodal_result.get("text", "").lower():
                    meal_type = "Cena"
                elif "snack" in multimodal_result.get("text", "").lower() or "merienda" in multimodal_result.get("text", "").lower():
                    meal_type = "Snack"
                
                # Crear la salida de la skill
                return AnalyzeFoodImageOutput(
                    identified_foods=food_items,
                    total_calories="No disponible con precisión desde la imagen",
                    meal_type=meal_type,
                    nutritional_assessment=nutritional_assessment,
                    health_score=health_score,
                    recommendations=recommendations,
                    alternatives=alternatives
                )
                
        except Exception as e:
            logger.error(f"Error al analizar imagen de alimentos: {e}", exc_info=True)
            
            # En caso de error, devolver un análisis básico
            return AnalyzeFoodImageOutput(
                identified_foods=[
                    {
                        "name": "Error en análisis",
                        "confidence_score": 0.0,
                        "estimated_calories": "No disponible",
                        "estimated_portion": "No disponible",
                        "macronutrients": {
                            "proteínas": "No disponible",
                            "carbohidratos": "No disponible",
                            "grasas": "No disponible"
                        }
                    }
                ],
                total_calories="No disponible",
                meal_type="No determinado",
                nutritional_assessment="No se pudo realizar el análisis debido a un error en el procesamiento.",
                health_score=None,
                recommendations=["Consulte a un nutricionista para un análisis preciso de su alimentación."],
                alternatives=[]
            )

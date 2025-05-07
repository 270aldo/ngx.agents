import logging
import uuid
import time
import json
from typing import Dict, Any, Optional, List, Union
import os
from google.cloud import aiplatform

# from adk.toolkit import Toolkit # No se usa directamente, se pasa MCPToolkit como adk_toolkit
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
# from tools.vertex_gemini_tools import VertexGeminiGenerateSkill # No se usa directamente
from agents.base.adk_agent import ADKAgent
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

# Importar esquemas para las skills
from agents.precision_nutrition_architect.schemas import (
    CreateMealPlanInput, CreateMealPlanOutput,
    RecommendSupplementsInput, RecommendSupplementsOutput,
    AnalyzeBiomarkersInput, AnalyzeBiomarkersOutput,
    PlanChrononutritionInput, PlanChrononutritionOutput,
    MealPlanArtifact, SupplementRecommendationArtifact,
    BiomarkerAnalysisArtifact, ChrononutritionPlanArtifact
)

# Configurar OpenTelemetry para observabilidad
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    # Configurar TracerProvider para trazas
    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer("precision_nutrition_architect")

    # Configurar MeterProvider para métricas
    prometheus_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(metric_readers=[prometheus_reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter("precision_nutrition_architect")

    # Crear contadores y medidores
    request_counter = meter.create_counter(
        name="agent_requests",
        description="Número de solicitudes recibidas por el agente",
        unit="1",
    )

    response_time = meter.create_histogram(
        name="agent_response_time",
        description="Tiempo de respuesta del agente en segundos",
        unit="s",
    )

    has_telemetry = True
except ImportError:
    # Fallback si OpenTelemetry no está disponible
    has_telemetry = False
    tracer = None
    request_counter = None
    response_time = None

# Configurar logger
logger = get_logger(__name__)

class PrecisionNutritionArchitect(ADKAgent):
    """
    Agente Precision Nutrition Architect compatible con ADK/A2A

    Genera planes alimenticios, crononutrición y suplementación basada en biomarcadores.
    """
    gemini_client: Optional[GeminiClient] = None
    supabase_client: Optional[SupabaseClient] = None
    tracer: Optional[trace.Tracer] = None # Para OpenTelemetry
    request_counter: Optional[metrics.Counter] = None
    response_time_metric: Optional[metrics.Histogram] = None # Renombrado para evitar confusión

    def __init__(
        self,
        toolkit: Optional[MCPToolkit] = None,
        state_manager: Optional[StateManager] = None,
        system_instructions: Optional[str] = None,
        gemini_client: Optional[GeminiClient] = None,
        model: str = "gemini-1.5-flash",
        **kwargs
    ):
        # Definir instrucciones del sistema
        self.system_instructions = system_instructions or """
        Eres un arquitecto de nutrición de precisión altamente especializado. 
        Tu función es analizar perfiles de usuario, datos biométricos y objetivos para generar 
        planes de alimentación detallados, recomendaciones de suplementación basadas en evidencia 
        y estrategias de crononutrición optimizadas. 
        Prioriza la salud, el rendimiento y la adherencia del usuario.
        """
        
        # Definir capacidades
        capabilities = [
            "meal_plan_creation",
            "nutrition_assessment",
            "supplement_recommendation",
            "chrononutrition_planning",
            "biomarker_analysis",
        ]
        
        # Inicializar clientes
        self.gemini_client = gemini_client or GeminiClient(model_name=model)
        self.supabase_client = SupabaseClient()
        
        # Configurar telemetría
        self.tracer = tracer
        self.request_counter = request_counter
        self.response_time_metric = response_time
        
        # Definir skills directamente
        self.skills = {
            "create_meal_plan": {
                "skill_id": "create_meal_plan",
                "name": "Creación de Plan de Comidas",
                "description": "Crea un plan de comidas personalizado basado en el perfil, preferencias y objetivos del usuario.",
                "method": self._skill_create_meal_plan,
                "input_schema": CreateMealPlanInput,
                "output_schema": CreateMealPlanOutput,
                "examples": [
                    "Crea un plan de comidas para un atleta de resistencia",
                    "Necesito un plan de alimentación para perder peso",
                    "Diseña un menú semanal para una dieta cetogénica"
                ],
            },
            "recommend_supplements": {
                "skill_id": "recommend_supplements",
                "name": "Recomendación de Suplementos",
                "description": "Recomienda suplementos basados en el perfil, biomarcadores y objetivos del usuario.",
                "method": self._skill_recommend_supplements,
                "input_schema": RecommendSupplementsInput,
                "output_schema": RecommendSupplementsOutput,
                "examples": [
                    "Qué suplementos debería tomar para mejorar mi recuperación",
                    "Recomienda suplementos para optimizar mi rendimiento cognitivo",
                    "Necesito suplementos para corregir mi deficiencia de hierro"
                ],
            },
            "analyze_biomarkers": {
                "skill_id": "analyze_biomarkers",
                "name": "Análisis de Biomarcadores",
                "description": "Analiza biomarcadores y genera recomendaciones nutricionales personalizadas.",
                "method": self._skill_analyze_biomarkers,
                "input_schema": AnalyzeBiomarkersInput,
                "output_schema": AnalyzeBiomarkersOutput,
                "examples": [
                    "Analiza mis niveles de vitamina D y B12",
                    "Qué significan mis valores de glucosa en ayunas",
                    "Interpreta mis resultados de perfil lipídico"
                ],
            },
            "plan_chrononutrition": {
                "skill_id": "plan_chrononutrition",
                "name": "Planificación de Crononutrición",
                "description": "Planifica el timing nutricional para optimizar el rendimiento y la recuperación.",
                "method": self._skill_plan_chrononutrition,
                "input_schema": PlanChrononutritionInput,
                "output_schema": PlanChrononutritionOutput,
                "examples": [
                    "Cuál es el mejor momento para comer carbohidratos",
                    "Diseña un plan de alimentación con ventana de ayuno intermitente",
                    "Optimiza mi nutrición alrededor de mis entrenamientos"
                ],
            },
        }

        # Inicializar agente base
        super().__init__(
            agent_id="precision_nutrition_architect",
            name="NGX Precision Nutrition Architect",
            description="Genera planes alimenticios detallados, recomendaciones de suplementación y estrategias de crononutrición basadas en biomarcadores y perfil del usuario.",
            capabilities=capabilities,
            toolkit=toolkit,
            state_manager=state_manager,
            version="1.2.0",
            system_instructions=self.system_instructions,
            skills=self.skills,
            model=model,
            **kwargs
        )

        # Inicializar AI Platform
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform (Vertex AI SDK) inicializado correctamente para PNA.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform para PNA: {e}", exc_info=True)

        # Configurar telemetría
        if has_telemetry:
            logger.info("OpenTelemetry configurado para PrecisionNutritionArchitect.")
        else:
            logger.warning("OpenTelemetry no está disponible. PrecisionNutritionArchitect funcionará sin telemetría detallada.")

        logger.info(f"{self.name} ({self.agent_id}) inicializado y listo.")

    def start(self):
        super().start()
        logger.info(f"{self.name} ({self.agent_id}) iniciado y conectado/registrado.")

    # --- Stubs de Métodos de Skill --- 
    async def _skill_create_meal_plan(self, params: CreateMealPlanInput) -> CreateMealPlanOutput:
        """
        Genera un plan de comidas personalizado basado en el perfil y preferencias del usuario.
        Args:
            params: CreateMealPlanInput
        Returns:
            CreateMealPlanOutput
        """
        try:
            # Uso de los datos del modelo Pydantic
            meal_plan_dict = await self._generate_meal_plan(
                params.input_text,
                params.user_profile or {}
            )
            return CreateMealPlanOutput(**meal_plan_dict)
        except Exception as e:
            logger.error(f"Error en _skill_create_meal_plan: {e}", exc_info=True)
            # Devolver salida básica en caso de error
            return CreateMealPlanOutput(
                daily_plan=[],
                total_calories=None,
                macronutrient_distribution=None,
                recommendations=["Error al generar el plan de comidas. Consulte a un profesional."],
                notes=str(e)
            )

    async def _skill_recommend_supplements(self, params: RecommendSupplementsInput) -> RecommendSupplementsOutput:
        """
        Recomienda suplementos personalizados según el perfil y biomarcadores del usuario.
        Args:
            params: RecommendSupplementsInput
        Returns:
            RecommendSupplementsOutput
        """
        try:
            rec_dict = await self._generate_supplement_recommendation(
                params.input_text,
                params.user_profile or {}
            )
            return RecommendSupplementsOutput(**rec_dict)
        except Exception as e:
            logger.error(f"Error en _skill_recommend_supplements: {e}", exc_info=True)
            return RecommendSupplementsOutput(
                supplements=[],
                general_recommendations="Error al generar recomendaciones de suplementos. Consulte a un profesional.",
                notes=str(e)
            )

    async def _skill_analyze_biomarkers(self, params: AnalyzeBiomarkersInput) -> AnalyzeBiomarkersOutput:
        """
        Analiza biomarcadores y proporciona recomendaciones nutricionales y de estilo de vida.
        
        Args:
            params: Parámetros de entrada para el análisis de biomarcadores
        
        Returns:
            AnalyzeBiomarkersOutput: Resultado del análisis de biomarcadores
        """
        try:
            # Generar análisis de biomarcadores usando el método interno (debe devolver un dict compatible)
            biomarker_data = await self._generate_biomarker_analysis(params.input_text, params.biomarkers)
            
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
            
            return AnalyzeBiomarkersOutput(
                analyses=analyses_list,
                overall_assessment=biomarker_data.get("overall_assessment", "No se pudo realizar una evaluación completa."),
                nutritional_priorities=biomarker_data.get("nutritional_priorities", ["Mantener una dieta equilibrada"]),
                supplement_considerations=biomarker_data.get("supplement_considerations")
            )
        except Exception as e:
            logger.error(f"Error en skill_analyze_biomarkers: {e}", exc_info=True)
            # Devolver análisis básico en caso de error
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
                nutritional_priorities=["Mantener una dieta equilibrada", "Consultar con un profesional"]
            )

    async def _skill_plan_chrononutrition(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Planifica estrategias de crononutrición personalizadas basadas en la entrada del usuario y su perfil.
        
        Args:
            input_text: Texto de entrada del usuario
            **kwargs: Argumentos adicionales como user_id, session_id, user_profile, etc.
            
        Returns:
            Dict[str, Any]: Resultado del plan de crononutrición
        """
        user_id = kwargs.get('user_id')
        session_id = kwargs.get('session_id')
        user_profile = kwargs.get('user_profile')
        logger.info(f"Skill: Planificando crononutrición para '{input_text[:30]}...' (user_id={user_id}, session_id={session_id})")

        if user_profile is None:
            logger.debug("User profile no proporcionado directamente para crononutrición. Intentando obtener del contexto.")
            full_context = await self._get_context(user_id, session_id)
            user_profile = full_context.get("client_profile", {})
            if not user_profile:
                logger.warning("User profile sigue vacío después de obtener del contexto para crononutrición. Procediendo con perfil vacío.")
            else:
                logger.debug(f"User profile obtenido del contexto para crononutrición: {bool(user_profile)}")
        else:
            logger.debug(f"User profile proporcionado directamente para crononutrición: {bool(user_profile)}")

        try:
            chronoplan = await self._generate_chrononutrition_plan(input_text, user_profile or {})
            return create_result(status="success", response_data=chronoplan, artifacts=[self.create_artifact("chrononutrition_plan", chronoplan)])
        except Exception as e:
            logger.error(f"Error en _skill_plan_chrononutrition: {e}", exc_info=True)
            return create_result(status="error", error_message=str(e))
            
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
        {self.system_instructions}
        
        Analiza los siguientes datos de biomarcadores y proporciona recomendaciones nutricionales y de estilo de vida basadas en ellos.
        Solicitud del usuario: "{user_input}"
        Datos de biomarcadores: {json.dumps(biomarkers, indent=2)}

        Proporciona un análisis detallado, identifica posibles áreas de mejora y sugiere acciones concretas.
        Devuelve el análisis y las recomendaciones en formato JSON estructurado.
        Ejemplo de estructura deseada:
        {{ 
          "analysis_summary": "Resumen del análisis de biomarcadores clave. Por ejemplo: Los niveles de Vitamina D son bajos, mientras que el colesterol HDL es óptimo. Se observa una ligera elevación de la glucosa en ayunas.",
          "key_findings": [
            {{ "parameter": "Glucosa en ayunas", "value": "{biomarkers.get('glucose', 'N/A')}", "unit": "mg/dL", "interpretation": "Interpretación basada en el valor y rangos de referencia.", "recommendation": "Recomendación específica, ej: Reducir ingesta de azúcares simples, aumentar fibra y considerar ejercicio regular." }},
            {{ "parameter": "Vitamina D", "value": "{biomarkers.get('vitamin_d', 'N/A')}", "unit": "ng/mL", "interpretation": "Interpretación del nivel de Vitamina D.", "recommendation": "Recomendación específica, ej: Suplementar con Vitamina D3 2000-4000 UI/día, aumentar exposición solar segura si es posible." }},
            {{ "parameter": "Colesterol Total", "value": "{biomarkers.get('cholesterol', {}).get('total', 'N/A')}", "unit": "mg/dL", "interpretation": "Interpretación del colesterol total.", "recommendation": "Recomendación relacionada con dieta y estilo de vida." }}
            
          ],
          "overall_recommendations": [
            "Recomendación general 1, basada en el análisis holístico. Ej: Incrementar el consumo de vegetales de hoja verde.",
            "Recomendación general 2. Ej: Realizar al menos 150 minutos de actividad física moderada por semana."
          ],
          "lifestyle_suggestions": [
             "Sugerencia de estilo de vida 1. Ej: Mejorar la calidad del sueño, apuntando a 7-8 horas.",
             "Sugerencia de estilo de vida 2. Ej: Incorporar técnicas de manejo del estrés como meditación o yoga."
          ]
        }}
        Considera los siguientes rangos de referencia generales (pueden variar según laboratorio y población):
        - Glucosa en ayunas: Normal <100 mg/dL, Pre-diabetes 100-125 mg/dL, Diabetes >=126 mg/dL
        - Vitamina D: Deficiencia <20 ng/mL, Insuficiencia 20-29 ng/mL, Suficiencia 30-100 ng/mL
        - Colesterol Total: Deseable <200 mg/dL, Límite alto 200-239 mg/dL, Alto >=240 mg/dL
        - HDL Colesterol: Deseable >60 mg/dL (protector), Aceptable 40-59 mg/dL, Bajo <40 mg/dL
        - LDL Colesterol: Óptimo <100 mg/dL, Cercano a óptimo 100-129 mg/dL, Límite alto 130-159 mg/dL, Alto 160-189 mg/dL, Muy alto >=190 mg/dL
        - Triglicéridos: Normal <150 mg/dL, Límite alto 150-199 mg/dL, Alto 200-499 mg/dL, Muy alto >=500 mg/dL
        Adapta las interpretaciones y recomendaciones a los valores específicos proporcionados.
        """
        
        try:
            logger.debug(f"Generando prompt para análisis de biomarcadores: {prompt[:500]}...") # Loguea una parte del prompt
            analysis = await self.gemini_client.generate_structured_output(prompt)
            
            # Si la respuesta no es un diccionario, intentar convertirla
            if not isinstance(analysis, dict):
                try:
                    analysis = json.loads(analysis) if isinstance(analysis, str) else { 
                        "error": "Respuesta no estructurada de Gemini", 
                        "raw_response": str(analysis)[:500] # Truncar para evitar logs demasiado grandes
                    }
                except json.JSONDecodeError:
                    analysis = { 
                        "error": "Respuesta string no JSON de Gemini", 
                        "raw_response": str(analysis)[:500] # Truncar para evitar logs demasiado grandes
                    }
            
            # Formatear la respuesta según el esquema esperado
            formatted_analysis = {
                "analysis_summary": analysis.get("analysis_summary", "No se pudo generar un resumen del análisis"),
                "key_findings": analysis.get("key_findings", []),
                "overall_recommendations": analysis.get("overall_recommendations", []),
                "lifestyle_suggestions": analysis.get("lifestyle_suggestions", []),
                "notes": analysis.get("notes", "")
            }
            
            return formatted_analysis
            
        except Exception as e:
            logger.error(f"Error al generar análisis de biomarcadores: {e}", exc_info=True)
            # Devolver un análisis básico en caso de error
            return {
                "analysis_summary": "No se pudo generar un análisis completo debido a un error",
                "key_findings": [
                    {
                        "parameter": "Error",
                        "value": "N/A",
                        "unit": "N/A",
                        "interpretation": "Se produjo un error al analizar los biomarcadores",
                        "recommendation": "Por favor, consulte con un profesional de la salud para un análisis detallado"
                    }
                ],
                "overall_recommendations": [
                    "Consulte con un profesional de la salud para un análisis detallado de sus biomarcadores"
                ],
                "lifestyle_suggestions": [
                    "Mantener una dieta balanceada y realizar actividad física regular"
                ],
                "notes": f"Error al generar análisis: {str(e)}"
            }

    async def _skill_plan_chrononutrition(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Planifica estrategias de crononutrición personalizadas basadas en la entrada del usuario y su perfil.
        
        Args:
            input_text: Texto de entrada del usuario
            **kwargs: Argumentos adicionales como user_id, session_id, user_profile, etc.
            
        Returns:
            Dict[str, Any]: Resultado del plan de crononutrición
        """
        user_id = kwargs.get('user_id')
        session_id = kwargs.get('session_id')
        user_profile = kwargs.get('user_profile')
        logger.info(f"Skill: Planificando crononutrición para '{input_text[:30]}...' (user_id={user_id}, session_id={session_id})")

        if user_profile is None:
            logger.debug("User profile no proporcionado directamente para crononutrición. Intentando obtener del contexto.")
            full_context = await self._get_context(user_id, session_id)
            user_profile = full_context.get("client_profile", {})
            if not user_profile:
                logger.warning("User profile sigue vacío después de obtener del contexto para crononutrición. Procediendo con perfil vacío.")
            else:
                logger.debug(f"User profile obtenido del contexto para crononutrición: {bool(user_profile)}")
        else:
            logger.debug(f"User profile proporcionado directamente para crononutrición: {bool(user_profile)}")

        try:
            chronoplan = await self._generate_chrononutrition_plan(input_text, user_profile or {})
            return create_result(status="success", response_data=chronoplan, artifacts=[self.create_artifact("chrononutrition_plan", chronoplan)])
        except Exception as e:
            logger.error(f"Error en _skill_plan_chrononutrition: {e}", exc_info=True)
            return create_result(status="error", error_message=str(e))
            
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
        profile_summary = self._extract_profile_details(user_profile) 
        
        # Preparar prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        Diseña un plan de crononutrición optimizado basado en la siguiente solicitud y perfil del usuario.
        Solicitud del usuario: "{user_input}"
        Perfil del usuario:
        {profile_summary}

        El plan debe incluir recomendaciones sobre el timing de las comidas principales, snacks, y la ingesta de macronutrientes alrededor de los entrenamientos (si aplica) y a lo largo del día para optimizar energía, rendimiento y recuperación.
        Considera los objetivos, nivel de actividad y preferencias del usuario si están disponibles en el perfil.
        Devuelve el plan en formato JSON estructurado.
        Ejemplo de estructura deseada:
        {{ 
          "objective": "Optimizar energía y recuperación para entrenamiento de resistencia",
          "daily_schedule": [
            {{ "time_range": "07:00-08:00", "activity": "Desayuno", "description": "Comida rica en proteínas y carbohidratos complejos. Ej: Avena con frutas y nueces, huevos revueltos con tostada integral." }},
            {{ "time_range": "10:00-10:30", "activity": "Snack Pre-Entreno (si entrena a mediodía)", "description": "Carbohidratos de rápida absorción y algo de proteína. Ej: Batido de frutas con proteína whey, o una banana con un puñado de almendras." }},
            {{ "time_range": "12:00-13:00", "activity": "Almuerzo", "description": "Comida balanceada, rica en proteínas, carbohidratos complejos y grasas saludables. Ej: Pollo a la parrilla con quinoa y ensalada mixta con aguacate." }},
            {{ "time_range": "16:00-16:30", "activity": "Snack Post-Entreno (si entrena por la tarde)", "description": "Proteínas y carbohidratos para recuperación. Ej: Yogur griego con miel y plátano, o batido de proteína con dextrosa." }},
            {{ "time_range": "19:00-20:00", "activity": "Cena", "description": "Comida ligera y nutritiva, rica en proteínas y vegetales. Evitar carbohidratos pesados si el objetivo es control de peso o si se es sensible por la noche. Ej: Salmón al horno con espárragos y ensalada." }}
          ],
          "nutrient_timing_notes": [
            "Consumir carbohidratos de fácil digestión 30-60 minutos antes del ejercicio si es intenso y de duración superior a 60 minutos.",
            "Priorizar la ventana de 30-90 minutos post-ejercicio para reponer glucógeno y reparar músculo con una combinación de proteínas (20-30g) y carbohidratos (0.8-1.2g/kg de peso corporal).",
            "Ajustar la ingesta calórica y de macronutrientes según los días de entrenamiento y descanso.",
            "Mantener una hidratación adecuada a lo largo del día, especialmente antes, durante y después del ejercicio.",
            "Evitar comidas pesadas y ricas en grasa al menos 2-3 horas antes de dormir para mejorar la calidad del sueño."
          ]
        }}
        """
        
        try:
            logger.debug(f"Generando prompt para plan de crononutrición: {prompt[:500]}...") # Loguea una parte del prompt
            chronoplan = await self.gemini_client.generate_structured_output(prompt)
            
            # Si la respuesta no es un diccionario, intentar convertirla
            if not isinstance(chronoplan, dict):
                try:
                    chronoplan = json.loads(chronoplan) if isinstance(chronoplan, str) else { 
                        "error": "Respuesta no estructurada de Gemini", 
                        "raw_response": str(chronoplan)[:500] # Truncar para evitar logs demasiado grandes
                    }
                except json.JSONDecodeError:
                    chronoplan = { 
                        "error": "Respuesta string no JSON de Gemini", 
                        "raw_response": str(chronoplan)[:500] # Truncar para evitar logs demasiado grandes
                    }
            
            # Formatear la respuesta según el esquema esperado
            formatted_plan = {
                "objective": chronoplan.get("objective", "Plan de crononutrición personalizado"),
                "daily_schedule": chronoplan.get("daily_schedule", []),
                "nutrient_timing_notes": chronoplan.get("nutrient_timing_notes", []),
                "notes": chronoplan.get("notes", "")
            }
            
            return formatted_plan
            
        except Exception as e:
            logger.error(f"Error al generar plan de crononutrición: {e}", exc_info=True)
            # Devolver un plan básico en caso de error
            return {
                "objective": "Plan de crononutrición básico (generado debido a un error)",
                "daily_schedule": [
                    {
                        "time_range": "07:00-08:00",
                        "activity": "Desayuno",
                        "description": "Comida rica en proteínas y carbohidratos complejos. Ej: Avena con frutas y nueces, huevos revueltos con tostada integral."
                    },
                    {
                        "time_range": "12:00-13:00",
                        "activity": "Almuerzo",
                        "description": "Comida balanceada, rica en proteínas, carbohidratos complejos y grasas saludables."
                    },
                    {
                        "time_range": "19:00-20:00",
                        "activity": "Cena",
                        "description": "Comida ligera y nutritiva, rica en proteínas y vegetales."
                    }
                ],
                "nutrient_timing_notes": [
                    "Mantener una hidratación adecuada a lo largo del día.",
                    "Evitar comidas pesadas y ricas en grasa al menos 2-3 horas antes de dormir."
                ],
                "notes": f"Error al generar plan detallado: {str(e)}"
            }

    # Los métodos _generate_meal_plan y _generate_supplement_recommendation 
    # se mantendrán y serán llamados por los _skill_ methods.
    # El método _register_skills se eliminará en la Parte 2.

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
        # TODO: Integrar RAG para buscar plantillas de planes NGX o guías nutricionales específicas.
        # TODO: Usar mcp7_query para obtener preferencias alimentarias, alergias, o datos biométricos desde Supabase.
        
        # Preparar prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        Genera un plan nutricional personalizado basado en la siguiente solicitud:
        
        "{user_input}"
        
        El plan debe incluir:
        1. Objetivo nutricional principal
        2. Distribución de macronutrientes recomendada
        3. Calorías diarias estimadas
        4. Comidas diarias con ejemplos específicos
        5. Alimentos recomendados y alimentos a evitar
        6. Estrategia de hidratación
        7. Consideraciones de timing nutricional (crononutrición)
        
        Devuelve el plan en formato JSON estructurado.
        """

        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Nombre: {user_profile.get('name', 'N/A')}
            - Edad: {user_profile.get('age', 'N/A')}
            - Peso: {user_profile.get('weight', 'N/A')}
            - Altura: {user_profile.get('height', 'N/A')}
            - Objetivos: {user_profile.get('goals', 'N/A')}
            - Restricciones alimenticias: {user_profile.get('dietary_restrictions', 'N/A')}
            - Alergias: {user_profile.get('allergies', 'N/A')}
            """

        try:
            # Generar el plan nutricional
            response = await self.gemini_client.generate_structured_output(prompt)

            # Si la respuesta no es un diccionario, intentar convertirla
            if not isinstance(response, dict):
                try:
                    response = json.loads(response)
                except:
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
        self, user_input: str, user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Genera recomendaciones de suplementación personalizadas basadas en la entrada del usuario y su perfil.
        
        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario con información relevante (opcional)
            
        Returns:
            Dict[str, Any]: Recomendaciones de suplementación generadas
        """
        # TODO: Integrar RAG para consultar base de datos de suplementos NGX, estudios de eficacia y seguridad.
        # TODO: Usar mcp7_query para obtener datos de biomarcadores o deficiencias nutricionales del usuario desde Supabase.
        
        # Preparar prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        Genera recomendaciones de suplementación personalizadas basadas en la siguiente solicitud:
        
        "{user_input}"
        
        Las recomendaciones deben incluir:
        1. Suplementos principales recomendados
        2. Dosis sugerida para cada suplemento
        3. Timing óptimo de consumo
        4. Beneficios esperados
        5. Posibles interacciones o precauciones
        6. Alternativas naturales cuando sea posible
        
        Devuelve las recomendaciones en formato JSON estructurado.
        """

        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Nombre: {user_profile.get('name', 'N/A')}
            - Edad: {user_profile.get('age', 'N/A')}
            - Peso: {user_profile.get('weight', 'N/A')}
            - Altura: {user_profile.get('height', 'N/A')}
            - Objetivos: {user_profile.get('goals', 'N/A')}
            - Restricciones alimenticias: {user_profile.get('dietary_restrictions', 'N/A')}
            - Alergias: {user_profile.get('allergies', 'N/A')}
            """

        try:
            # Generar recomendaciones de suplementación
            response = await self.gemini_client.generate_structured_output(prompt)

            # Si la respuesta no es un diccionario, intentar convertirla
            if not isinstance(response, dict):
                try:
                    response = json.loads(response)
                except:
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

    # ---- Métodos de Lógica Interna (potencialmente privados) ----

    # Estas funciones son llamadas por las skills registradas
    # def _extract_profile_details(self, user_profile: Dict[str, Any]) -> str:
    #     """Extrae detalles relevantes del perfil del usuario."""
    #     details = []
    #     if user_profile.get("name"):
    #         details.append(f"Nombre: {user_profile['name']}")
    #     if user_profile.get("age"):
    #         details.append(f"Edad: {user_profile['age']}")
    #     if user_profile.get("weight"):
    #         details.append(f"Peso: {user_profile['weight']} kg")
    #     if user_profile.get("height"):
    #         details.append(f"Altura: {user_profile['height']} cm")
    #     if user_profile.get("goals"):
    #         details.append(f"Objetivos: {user_profile['goals']}")
    #     if user_profile.get("dietary_restrictions"):
    #         details.append(f"Restricciones alimenticias: {user_profile['dietary_restrictions']}")
    #     if user_profile.get("allergies"):
    #         details.append(f"Alergias: {user_profile['allergies']}")

    #     return "\n".join(details)

    # ---- Gestión de Estado y Contexto ----
    # async def _get_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
    #     """Recupera el contexto completo del usuario y sesión."""
    #     # Implementación de recuperación de contexto
    #     # Por ahora, devuelve un contexto vacío
    #     context_data = {}
    #     logger.debug(f"Contexto recuperado para user_id={user_id}, session_id={session_id}: {list(context_data.keys())}")
    #     return context_data

    # ---- Funciones de utilidad ----
    # Heredadas de ADKAgent: _extract_profile_details, _get_program_type_from_profile

# Ejemplo de uso (si se ejecuta directamente, para pruebas básicas)
if __name__ == "__main__":
    # logger.info("Ejemplo de uso de PrecisionNutritionArchitect")
    # agent = PrecisionNutritionArchitect()
    # logger.info("PrecisionNutritionArchitect creado")
    pass

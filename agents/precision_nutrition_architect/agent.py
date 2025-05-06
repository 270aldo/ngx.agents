import logging
import uuid
import time
import json
from typing import Dict, Any, Optional, List, Union
import os
from google.cloud import aiplatform

from adk.toolkit import Toolkit
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from tools.vertex_gemini_tools import VertexGeminiGenerateSkill
from agents.base.adk_agent import ADKAgent
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

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

    def __init__(
        self,
        toolkit: Optional[Toolkit] = None,
        a2a_server_url: Optional[str] = None,
        state_manager: Optional[StateManager] = None,
        **kwargs
    ):
        # Definir IDs, nombres, descripciones, etc. aquí
        agent_id = "precision_nutrition_architect"
        name = "Precision Nutrition Architect"
        description = "Genera planes alimenticios, crononutrición y suplementación basada en biomarcadores."
        capabilities = [
            "meal_plan_creation",
            "nutrition_assessment",
            "supplement_recommendation",
            "chrononutrition_planning",
            "biomarker_analysis",
        ]
        version = "1.0.0"
        # Definir la estructura de las skills para la Agent Card (sin la lógica de ejecución aún)
        # El registro real se hará en _register_skills
        agent_skills_definition = [
            {
                "name": "create_meal_plan",
                "description": "Crea un plan de comidas personalizado.",
                "input_schema": { # Ejemplo de esquema
                    "type": "object",
                    "properties": {
                        "input_text": {"type": "string", "description": "Solicitud del usuario"},
                        "user_profile": {"type": "object", "description": "Perfil del usuario"},
                        "context": {"type": "object", "description": "Contexto de la conversación"}
                    },
                    "required": ["input_text"]
                },
                "output_schema": {"type": "object", "description": "Plan de comidas JSON"}
            },
             {
                "name": "recommend_supplements",
                "description": "Recomienda suplementos basados en necesidades.",
                "input_schema": { # Ejemplo
                     "type": "object",
                     "properties": {
                        "input_text": {"type": "string"},
                        "user_profile": {"type": "object"},
                        "context": {"type": "object"}
                    },
                     "required": ["input_text"]
                },
                "output_schema": {"type": "object", "description": "Recomendaciones JSON"}
            },
             {
                "name": "analyze_biomarkers",
                "description": "Analiza biomarcadores y genera recomendaciones.",
                 "input_schema": { # Ejemplo
                     "type": "object",
                     "properties": {
                         "input_text": {"type": "string"},
                         "biomarkers": {"type": "object"},
                         "context": {"type": "object"}
                     },
                     "required": ["input_text", "biomarkers"]
                 },
                 "output_schema": {"type": "object", "description": "Análisis JSON"}
             },
             {
                 "name": "plan_chrononutrition",
                 "description": "Planifica el timing nutricional (crononutrición).",
                 "input_schema": { # Ejemplo
                     "type": "object",
                     "properties": {
                         "input_text": {"type": "string"},
                         "user_profile": {"type": "object"},
                         "context": {"type": "object"}
                     },
                     "required": ["input_text"]
                 },
                 "output_schema": {"type": "object", "description": "Plan de crononutrición JSON"}
             }
        ]

        # Llamar al constructor de la clase base (ADKAgent)
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities,
            toolkit=toolkit,
            version=version,
            a2a_server_url=a2a_server_url,
            state_manager=state_manager,
            # Pasar la definición de skills para la Agent Card
            skills=agent_skills_definition,
            **kwargs # Pasar kwargs adicionales
        )

        # ---- Inicialización de AI Platform ----
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform: {e}", exc_info=True)

        # ---- Inicialización de Clientes y Herramientas ----
        self.gemini_client = GeminiClient(model_name="gemini-1.5-flash") # Actualizado a 1.5 flash
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        self.mcp_client = MCPClient()

        # Inicializar el StateManager para persistencia
        self.state_manager = state_manager or StateManager()

        # Inicializar estado del agente
        self.update_state(
            "nutrition_plans", {}
        )  # Almacenar planes nutricionales generados
        self.update_state(
            "supplement_recommendations", {}
        )  # Almacenar recomendaciones de suplementos
        self.update_state(
            "conversation_contexts", {}
        )  # Almacenar contextos de conversación

    async def start(self) -> None:
        """
        Inicia el agente, conectándolo al servidor ADK y registrando sus skills.
        """
        # Llamar al start de la clase base ADKAgent para conectar, etc.
        await super().start()
        
        # Registrar las skills después de que el agente base se haya iniciado
        # (el toolkit ya debería estar inicializado por el __init__ base)
        if self._running: # Solo registrar si el inicio base fue exitoso
             await self._register_skills()
             logger.info(f"Skills específicas de {self.agent_id} registradas.")
        else:
            logger.warning(f"No se registraron skills específicas para {self.agent_id} porque el inicio base falló.")

    async def _register_skills(self) -> None:
        """
        Registra las skills del agente en el toolkit.
        Nota: Las funciones de skill ahora se definen aquí mismo por simplicidad,
              pero idealmente serían métodos separados.
        """
        if not self.toolkit:
            logger.error(f"No se puede registrar skills para {self.agent_id}: Toolkit no inicializado.")
            return
            
        # --- Definición y Registro de Skills --- 
        
        # Skill: create_meal_plan
        async def create_meal_plan(
            input_text: str,
            user_profile: Dict[str, Any] = None,
            context: Dict[str, Any] = None,
        ) -> Dict[str, Any]:
            """Crea un plan de comidas personalizado basado en la entrada y perfil."""
            logger.info(f"Executing skill: create_meal_plan for user: {user_profile.get('id', 'N/A') if user_profile else 'N/A'}")
            # Lógica existente para generar el plan (usando _generate_meal_plan)
            nutrition_plan = await self._generate_meal_plan(input_text, user_profile)
            return nutrition_plan
        self.register_skill("create_meal_plan", create_meal_plan)

        # Skill: recommend_supplements
        async def recommend_supplements(
            input_text: str,
            user_profile: Dict[str, Any] = None,
            context: Dict[str, Any] = None,
        ) -> Dict[str, Any]:
            """Recomienda suplementos basados en la entrada y perfil."""
            logger.info(f"Executing skill: recommend_supplements for user: {user_profile.get('id', 'N/A') if user_profile else 'N/A'}")
            # Lógica existente (usando _generate_supplement_recommendation)
            supplement_rec = await self._generate_supplement_recommendation(input_text, user_profile)
            return supplement_rec
        self.register_skill("recommend_supplements", recommend_supplements)

        # Skill: analyze_biomarkers
        async def analyze_biomarkers(
            input_text: str,
            biomarkers: Dict[str, Any] = None,
            context: Dict[str, Any] = None,
        ) -> Dict[str, Any]:
            """Analiza biomarcadores y genera recomendaciones."""
            logger.info(f"Executing skill: analyze_biomarkers")
            # TODO: Implementar lógica de análisis de biomarcadores
            prompt = f"Analiza los siguientes biomarcadores y genera recomendaciones:\nBiomarcadores: {json.dumps(biomarkers)}\nContexto adicional: {input_text}"
            analysis = await self.gemini_client.generate_structured_output(prompt)
            # Simulación de análisis
            # analysis = {
            #     "summary": "Análisis de biomarcadores indica necesidad de ajustar X.",
            #     "recommendations": ["Recomendación 1", "Recomendación 2"]
            # }
            return analysis if isinstance(analysis, dict) else {"analysis": analysis}
        self.register_skill("analyze_biomarkers", analyze_biomarkers)
        
        # Skill: plan_chrononutrition
        async def plan_chrononutrition(
            input_text: str,
            user_profile: Dict[str, Any] = None,
            context: Dict[str, Any] = None,
        ) -> Dict[str, Any]:
            """Planifica el timing nutricional (crononutrición)."""
            logger.info(f"Executing skill: plan_chrononutrition for user: {user_profile.get('id', 'N/A') if user_profile else 'N/A'}")
            # TODO: Implementar lógica de planificación de crononutrición
            prompt = f"Crea un plan de crononutrición basado en:\nPerfil: {json.dumps(user_profile)}\nSolicitud: {input_text}"
            chrono_plan = await self.gemini_client.generate_structured_output(prompt)
            # Simulación de plan
            # chrono_plan = {
            #     "morning": "Alimentos recomendados por la mañana",
            #     "afternoon": "Alimentos recomendados por la tarde",
            #     "evening": "Alimentos recomendados por la noche",
            #     "notes": "Notas adicionales sobre el timing"
            # }
            return chrono_plan if isinstance(chrono_plan, dict) else {"plan": chrono_plan}
        self.register_skill("plan_chrononutrition", plan_chrononutrition)

        # Registrar otras skills si es necesario...
        logger.info(f"Skills registrados para {self.agent_id}")

    # ---- Métodos de Lógica Interna (potencialmente privados) ----

    # Estas funciones son llamadas por las skills registradas
    async def _generate_meal_plan(
        self, user_input: str, user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        # TODO: Integrar RAG para buscar plantillas de planes NGX o guías nutricionales específicas.
        # TODO: Usar mcp7_query para obtener preferencias alimentarias, alergias, o datos biométricos desde Supabase.
        prompt = f"""
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

        # Generar el plan nutricional
        response = await self.gemini_client.generate_structured_output(prompt)

        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                import json

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

        return response

    async def _generate_supplement_recommendation(
        self, user_input: str, user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        # TODO: Integrar RAG para consultar base de datos de suplementos NGX, estudios de eficacia y seguridad.
        # TODO: Usar mcp7_query para obtener datos de biomarcadores o deficiencias nutricionales del usuario desde Supabase.
        prompt = f"""
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

        # Generar recomendaciones de suplementación
        response = await self.gemini_client.generate_structured_output(prompt)

        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                import json

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

        return response

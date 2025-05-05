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
from agents.base.a2a_agent import A2AAgent
from core.agent_card import AgentCard, Example
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


class PrecisionNutritionArchitect(A2AAgent):
    """
    Agente Precision Nutrition Architect compatible con A2A

    Genera planes alimenticios, crononutrición y suplementación basada en biomarcadores.
    """

    def __init__(
        self,
        toolkit: Optional[Toolkit] = None,
        a2a_server_url: Optional[str] = None,
        state_manager: Optional[StateManager] = None,
    ):
        # Definir capacidades y habilidades según el protocolo A2A
        capabilities = [
            "meal_plan_creation",
            "nutrition_assessment",
            "supplement_recommendation",
            "chrononutrition_planning",
            "biomarker_analysis",
        ]

        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="precision_nutrition_architect",
            name="Precision Nutrition Architect",
            description="Genera planes alimenticios, crononutrición y suplementación basada en biomarcadores.",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.0.0",
            a2a_server_url=a2a_server_url,
            state_manager=state_manager,
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

        # Crear y configurar la tarjeta del agente
        self.agent_card = self._create_agent_card()

        logger.info(
            f"PrecisionNutritionArchitect inicializado con {len(capabilities)} capacidades"
        )

    async def _run_async_impl(
        self,
        input_text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        # Registrar métrica de solicitud si telemetría está disponible
        if has_telemetry and request_counter:
            request_counter.add(
                1, {"agent_id": self.agent_id, "user_id": user_id or "anonymous"}
            )

        # Crear span para trazar la ejecución si telemetría está disponible
        if has_telemetry and tracer:
            with tracer.start_as_current_span(
                "precision_nutrition_architect_process_request"
            ) as span:
                span.set_attribute("user_id", user_id or "anonymous")
                span.set_attribute("session_id", session_id or "none")
                span.set_attribute("input_length", len(input_text))

                # Medir tiempo de respuesta
                start_time = time.time()
                result = await self._process_request(
                    input_text, user_id, session_id, **kwargs
                )
                end_time = time.time()

                # Registrar métrica de tiempo de respuesta
                if response_time:
                    response_time.record(
                        end_time - start_time, {"agent_id": self.agent_id}
                    )

                return result
        else:
            # Ejecución sin telemetría
            return await self._process_request(
                input_text, user_id, session_id, **kwargs
            )

    async def _process_request(
        self,
        input_text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Implementación asíncrona del procesamiento del agente PrecisionNutritionArchitect.

        Sobrescribe el método de la clase base para proporcionar la implementación
        específica del agente especializado en nutrición de precisión, siguiendo
        el protocolo A2A y los estándares de Google ADK.

        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            **kwargs: Argumentos adicionales como context, parameters, etc.

        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente según el protocolo A2A
        """
        try:
            start_time = time.time()
            logger.info(
                f"Ejecutando PrecisionNutritionArchitect con input: {input_text[:50]}..."
            )

            # Generar ID de sesión si no se proporciona
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Generando nuevo session_id: {session_id}")

            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                user_profile = self.supabase_client.get_user_profile(user_id)

            # Cargar el contexto de la conversación utilizando el método _get_context
            # Este método ya maneja la carga desde StateManager o memoria según corresponda
            context = await self._get_context(user_id, session_id)

            # Determinar el tipo de solicitud basado en palabras clave
            if any(
                keyword in input_text.lower()
                for keyword in ["plan", "alimentación", "comida", "dieta", "nutrición"]
            ):
                # Generar plan nutricional
                nutrition_plan = await self._generate_nutrition_plan(
                    input_text, user_profile
                )
                response = self._summarize_plan(nutrition_plan)
                response_type = "nutrition_plan"

                # Guardar el plan en el estado del agente
                if user_id:
                    plans = self.get_state("nutrition_plans", {})
                    plans[user_id] = plans.get(user_id, []) + [
                        {
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "query": input_text,
                            "plan": nutrition_plan,
                        }
                    ]
                    self.update_state("nutrition_plans", plans)

                    # También guardar en Supabase si es necesario
                    self.supabase_client.save_nutrition_plan(user_id, nutrition_plan)

            elif any(
                keyword in input_text.lower()
                for keyword in ["suplemento", "vitamina", "mineral", "proteína"]
            ):
                # Generar recomendación de suplementos
                supplement_recommendation = (
                    await self._generate_supplement_recommendation(
                        input_text, user_profile
                    )
                )
                response = self._summarize_supplements(supplement_recommendation)
                response_type = "supplement_recommendation"

                # Guardar la recomendación en el estado del agente
                if user_id:
                    recommendations = self.get_state("supplement_recommendations", {})
                    recommendations[user_id] = recommendations.get(user_id, []) + [
                        {
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "query": input_text,
                            "recommendation": supplement_recommendation,
                        }
                    ]
                    self.update_state("supplement_recommendations", recommendations)

                    # También guardar en Supabase si es necesario
                    self.supabase_client.save_supplement_recommendation(
                        user_id, supplement_recommendation
                    )

            else:
                # Preparar contexto para respuesta general
                prompt_context = self._prepare_context(
                    input_text, user_profile, context
                )

                # Generar respuesta con Gemini
                response = await self.gemini_client.generate_content(prompt_context)
                response_type = "general_response"

            # Añadir la interacción al historial interno del agente
            self.add_to_history(input_text, response)

            # Actualizar contexto y persistir en StateManager
            await self._update_context(user_id, session_id, input_text, response)

            # Crear artefactos para la respuesta siguiendo el formato A2A
            artifacts = [
                {
                    "type": response_type,
                    "content": response,
                    "metadata": {
                        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "agent_version": "1.0.0",
                        "protocol": "a2a",
                    },
                }
            ]

            # Crear mensaje de respuesta según el protocolo A2A
            response_message = self.create_message(
                role="agent", parts=[self.create_text_part(response)]
            )

            # Convertir artefactos al formato A2A
            a2a_artifacts = []
            for artifact in artifacts:
                artifact_id = f"{artifact['type']}_{uuid.uuid4().hex[:8]}"
                a2a_artifact = self.create_artifact(
                    artifact_id=artifact_id,
                    artifact_type=artifact["type"],
                    parts=[self.create_data_part(artifact["content"])],
                )
                a2a_artifacts.append(a2a_artifact)

            # Devolver respuesta final según el protocolo A2A
            return {
                "status": "success",
                "response": response,
                "message": response_message,
                "artifacts": a2a_artifacts,
                "agent_id": self.agent_id,
                "metadata": {
                    "response_type": response_type,
                    "user_id": user_id,
                    "session_id": session_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }

        except Exception as e:
            logger.error(f"Error en PrecisionNutritionArchitect: {e}", exc_info=True)

            # Crear mensaje de error según el protocolo A2A
            error_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(
                        "Lo siento, ha ocurrido un error al procesar tu solicitud nutricional."
                    )
                ],
            )

            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud nutricional.",
                "message": error_message,
                "error": str(e),
                "agent_id": self.agent_id,
                "metadata": {
                    "error_type": type(e).__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }

    def _summarize_plan(self, nutrition_plan: Dict[str, Any]) -> str:
        """Genera un resumen textual del plan nutricional para la respuesta al usuario."""
        summary_parts = []

        if "objective" in nutrition_plan:
            summary_parts.append(
                f"El objetivo principal es: {nutrition_plan['objective']}."
            )

        if "macronutrients" in nutrition_plan:
            macros = nutrition_plan["macronutrients"]
            macro_text = []
            for key, value in macros.items():
                if key == "protein":
                    macro_text.append(f"proteínas {value}")
                elif key == "carbs":
                    macro_text.append(f"carbohidratos {value}")
                elif key == "fats":
                    macro_text.append(f"grasas {value}")
            if macro_text:
                summary_parts.append(
                    f"La distribución de macronutrientes recomendada es: {', '.join(macro_text)}."
                )

        if (
            "recommended_foods" in nutrition_plan
            and nutrition_plan["recommended_foods"]
        ):
            foods = nutrition_plan["recommended_foods"]
            if isinstance(foods, list) and len(foods) > 0:
                summary_parts.append(f"Alimentos recomendados incluyen: {foods[0]}")
                if len(foods) > 1:
                    summary_parts.append(f" y {foods[1]}.")
                else:
                    summary_parts.append(".")

        if not summary_parts:
            return "Revisa el plan detallado para más información."

        return " ".join(summary_parts)

    def _summarize_supplements(self, supplement_recommendation: Dict[str, Any]) -> str:
        """Genera un resumen textual de las recomendaciones de suplementos para la respuesta al usuario."""
        summary_parts = []

        if (
            "supplements" in supplement_recommendation
            and supplement_recommendation["supplements"]
        ):
            supplements = supplement_recommendation["supplements"]
            if isinstance(supplements, list) and len(supplements) > 0:
                supp_names = [s.get("name", "suplemento") for s in supplements[:2]]
                if supp_names:
                    summary_parts.append(
                        f"Te recomiendo principalmente: {supp_names[0]}"
                    )
                    if len(supp_names) > 1:
                        summary_parts.append(f" y {supp_names[1]}.")
                    else:
                        summary_parts.append(".")

        if "general_recommendations" in supplement_recommendation:
            summary_parts.append(
                f" {supplement_recommendation['general_recommendations']}"
            )

        if not summary_parts:
            return "Revisa las recomendaciones detalladas para más información."

        return " ".join(summary_parts)

    async def _get_context(
        self, user_id: Optional[str], session_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación para un usuario y sesión específicos.

        Este método intenta primero obtener el contexto del StateManager para persistencia.
        Si no está disponible, usa el almacenamiento en memoria como fallback.

        Args:
            user_id: ID del usuario
            session_id: ID de la sesión

        Returns:
            Dict[str, Any]: Contexto de la conversación
        """
        # Intentar cargar desde StateManager si hay user_id y session_id
        if user_id and session_id:
            try:
                state_data = await self.state_manager.load_state(user_id, session_id)
                if state_data and "context" in state_data:
                    logger.debug(
                        f"Contexto cargado desde StateManager para session_id={session_id}"
                    )
                    return state_data["context"]
            except Exception as e:
                logger.warning(f"Error al cargar contexto desde StateManager: {e}")

        # Fallback: Obtener contextos almacenados en memoria
        contexts = self.get_state("conversation_contexts") or {}

        # Generar clave de contexto
        context_key = f"{user_id}_{session_id}" if user_id and session_id else "default"

        # Obtener o inicializar contexto
        if context_key not in contexts:
            contexts[context_key] = {"history": []}
            self.update_state("conversation_contexts", contexts)

        return contexts[context_key]

    async def _update_context(
        self, user_id: Optional[str], session_id: Optional[str], msg: str, resp: str
    ) -> None:
        """
        Actualiza el contexto de la conversación con un nuevo mensaje y respuesta.

        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            msg: Mensaje del usuario
            resp: Respuesta del bot
        """
        # Obtener contexto actual
        context = await self._get_context(user_id, session_id)

        # Añadir nueva interacción al historial
        if "history" not in context:
            context["history"] = []

        context["history"].append({"user": msg, "bot": resp, "timestamp": time.time()})

        # Limitar el tamaño del historial (mantener últimas 10 interacciones)
        if len(context["history"]) > 10:
            context["history"] = context["history"][-10:]

        # Actualizar contexto en memoria
        contexts = self.get_state("conversation_contexts") or {}
        key = f"{user_id}_{session_id}" if user_id and session_id else "default"
        contexts[key] = context
        self.update_state("conversation_contexts", contexts)

        # Persistir en StateManager si hay user_id y session_id
        if user_id and session_id:
            try:
                # Guardar contexto en StateManager
                state_data = {"context": context}
                await self.state_manager.save_state(state_data, user_id, session_id)
                logger.debug(
                    f"Contexto actualizado en StateManager para session_id={session_id}"
                )
            except Exception as e:
                logger.warning(f"Error al guardar contexto en StateManager: {e}")

    def _create_agent_card(self) -> AgentCard:
        """
        Crea una tarjeta de agente estandarizada según el protocolo A2A.

        Returns:
            AgentCard: Tarjeta del agente estandarizada
        """
        # Crear ejemplos para la tarjeta del agente
        examples = [
            Example(
                input={
                    "message": "Necesito un plan de alimentación para mejorar mi rendimiento deportivo"
                },
                output={
                    "response": "He creado un plan nutricional enfocado en optimizar tu rendimiento deportivo. Se centra en una distribución de macronutrientes de 30% proteínas, 45% carbohidratos y 25% grasas, con énfasis en alimentos de alto valor nutricional y timing estratégico de nutrientes alrededor de tus entrenamientos."
                },
            ),
            Example(
                input={
                    "message": "¿Qué suplementos me recomiendas para mejorar mi recuperación muscular?"
                },
                output={
                    "response": "Basado en tus necesidades, te recomiendo los siguientes suplementos para optimizar tu recuperación muscular: proteína de suero (20-25g post-entrenamiento), creatina monohidrato (5g diarios), y aminoácidos de cadena ramificada (BCAAs) antes del entrenamiento. También considera magnesio (300-400mg) para reducir calambres y mejorar la calidad del sueño."
                },
            ),
            Example(
                input={
                    "message": "¿Cómo debería distribuir mis comidas durante el día para optimizar mi metabolismo?"
                },
                output={
                    "response": "Para optimizar tu metabolismo, te recomiendo un enfoque de crononutrición con 4-5 comidas distribuidas cada 3-4 horas. Concentra los carbohidratos en el desayuno y alrededor del entrenamiento, proteínas en cada comida (20-30g), y grasas saludables principalmente en la tarde/noche. Mantén una ventana de alimentación de 10-12 horas para alinearte con tu ritmo circadiano."
                },
            ),
            Example(
                input={
                    "message": "Mis análisis de sangre muestran niveles bajos de vitamina D y hierro. ¿Qué ajustes nutricionales debería hacer?"
                },
                output={
                    "response": "Para abordar tus niveles bajos de vitamina D y hierro, te recomiendo: 1) Aumentar el consumo de pescados grasos (salmón, caballa), huevos y hongos expuestos al sol para vitamina D; 2) Incorporar carnes rojas magras, legumbres y vegetales de hoja verde para el hierro; 3) Combinar fuentes de hierro con alimentos ricos en vitamina C para mejorar la absorción; 4) Considerar suplementación de vitamina D3 (1000-2000 UI) y hierro (consulta con tu médico para la dosis exacta)."
                },
            ),
        ]

        # Crear la tarjeta del agente
        return AgentCard(
            title="Precision Nutrition Architect",
            description="Especialista en nutrición personalizada que genera planes alimenticios, crononutrición y suplementación basada en biomarcadores.",
            instructions="Proporciona detalles sobre tus objetivos, restricciones alimentarias, horarios de entrenamiento y cualquier información relevante sobre tu salud para recibir un plan nutricional personalizado.",
            examples=examples,
            capabilities=[
                "Creación de planes alimenticios personalizados",
                "Análisis nutricional basado en perfil y objetivos",
                "Recomendación de suplementos según necesidades individuales",
                "Planificación de crononutrición optimizada",
                "Análisis de biomarcadores para nutrición de precisión",
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "user_profile": {"type": "object"},
                    "biomarkers": {"type": "object"},
                },
                "required": ["message"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                    "nutrition_plan": {"type": "object"},
                    "supplement_recommendation": {"type": "object"},
                    "biomarker_analysis": {"type": "object"},
                },
                "required": ["response"],
            },
        )

    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.

        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self._create_agent_card().to_dict()

    async def start(self):
        """
        Inicia el agente, conectándolo al servidor ADK y registrando sus skills.
        Implementa el protocolo A2A para la comunicación estandarizada.
        """
        try:
            # Registrar skills en el toolkit
            await self._register_skills()

            # Iniciar agente ADK (conectar al servidor ADK y registrar skills)
            await super().start()

            logger.info(
                f"Agente {self.agent_id} iniciado exitosamente con protocolo A2A"
            )
        except Exception as e:
            logger.error(
                f"Error al iniciar el agente {self.agent_id}: {e}", exc_info=True
            )
            raise

    async def _register_skills(self):
        """
        Registra las skills del agente en el toolkit.
        """

        # Skill para crear planes nutricionales
        async def create_meal_plan(
            input_text: str,
            user_profile: Dict[str, Any] = None,
            context: Dict[str, Any] = None,
        ) -> Dict[str, Any]:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un nutricionista especializado en planes alimenticios personalizados.
            Genera un plan nutricional detallado basado en la siguiente solicitud:
            
            "{input_text}"
            
            El plan debe incluir:
            1. Objetivo principal del plan
            2. Distribución de macronutrientes recomendada
            3. Estimación calórica diaria
            4. Estructura de comidas (4-6 comidas diarias)
            5. Ejemplos de alimentos para cada comida
            6. Alimentos recomendados y alimentos a evitar
            7. Estrategias de crononutrición (timing de comidas)
            8. Recomendaciones para hidratación
            
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

            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional de conversaciones previas:\n"
                for entry in context["history"][
                    -3:
                ]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"

            # Usar VertexGeminiGenerateSkill si está disponible
            try:
                vertex_skill = VertexGeminiGenerateSkill()
                result = await vertex_skill.execute(
                    {"prompt": prompt, "temperature": 0.7, "model": "gemini-2.0-flash"}
                )
                response_text = result.get("text", "")

                # Intentar extraer JSON de la respuesta
                try:
                    # Buscar patrón JSON en la respuesta
                    import re

                    json_match = re.search(r"({.*})", response_text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    else:
                        # Si no se encuentra JSON, devolver respuesta como texto
                        return {"response": response_text}
                except Exception as e:
                    logger.warning(f"Error al extraer JSON de la respuesta: {e}")
                    return {"response": response_text}
            except Exception as e:
                logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
                # Fallback a cliente Gemini directo
                response = await self.gemini_client.generate_structured_output(prompt)
                return (
                    response
                    if isinstance(response, dict)
                    else {"response": str(response)}
                )

        # Skill para recomendar suplementos
        async def recommend_supplements(
            input_text: str,
            user_profile: Dict[str, Any] = None,
            context: Dict[str, Any] = None,
        ) -> Dict[str, Any]:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un especialista en nutrición deportiva y suplementación.
            Genera recomendaciones de suplementación personalizadas basadas en la siguiente solicitud:
            
            "{input_text}"
            
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

            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional de conversaciones previas:\n"
                for entry in context["history"][
                    -3:
                ]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"

            # Usar VertexGeminiGenerateSkill si está disponible
            try:
                vertex_skill = VertexGeminiGenerateSkill()
                result = await vertex_skill.execute(
                    {"prompt": prompt, "temperature": 0.7, "model": "gemini-2.0-flash"}
                )
                response_text = result.get("text", "")

                # Intentar extraer JSON de la respuesta
                try:
                    # Buscar patrón JSON en la respuesta
                    import re

                    json_match = re.search(r"({.*})", response_text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    else:
                        # Si no se encuentra JSON, devolver respuesta como texto
                        return {"response": response_text}
                except Exception as e:
                    logger.warning(f"Error al extraer JSON de la respuesta: {e}")
                    return {"response": response_text}
            except Exception as e:
                logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
                # Fallback a cliente Gemini directo
                response = await self.gemini_client.generate_structured_output(prompt)
                return (
                    response
                    if isinstance(response, dict)
                    else {"response": str(response)}
                )

        # Skill para analizar biomarcadores
        async def analyze_biomarkers(
            input_text: str,
            biomarkers: Dict[str, Any] = None,
            context: Dict[str, Any] = None,
        ) -> Dict[str, Any]:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un especialista en análisis de biomarcadores y nutrición personalizada.
            Analiza los siguientes biomarcadores y proporciona recomendaciones nutricionales basadas en ellos:
            
            "{input_text}"
            
            El análisis debe incluir:
            1. Interpretación de cada biomarcador
            2. Implicaciones para la salud y rendimiento
            3. Recomendaciones nutricionales específicas
            4. Alimentos a aumentar o reducir
            5. Suplementos potencialmente beneficiosos
            6. Próximos pasos recomendados
            
            Devuelve el análisis en formato JSON estructurado.
            """

            # Añadir biomarcadores si están disponibles
            if biomarkers:
                prompt += "\n\nBiomarcadores disponibles:\n"
                for marker, value in biomarkers.items():
                    prompt += f"- {marker}: {value}\n"

            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional:\n"
                for entry in context["history"][
                    -3:
                ]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"

            # Usar VertexGeminiGenerateSkill si está disponible
            try:
                vertex_skill = VertexGeminiGenerateSkill()
                result = await vertex_skill.execute(
                    {"prompt": prompt, "temperature": 0.7, "model": "gemini-2.0-flash"}
                )
                response_text = result.get("text", "")

                # Intentar extraer JSON de la respuesta
                try:
                    # Buscar patrón JSON en la respuesta
                    import re

                    json_match = re.search(r"({.*})", response_text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    else:
                        # Si no se encuentra JSON, devolver respuesta como texto
                        return {"response": response_text}
                except Exception as e:
                    logger.warning(f"Error al extraer JSON de la respuesta: {e}")
                    return {"response": response_text}
            except Exception as e:
                logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
                # Fallback a cliente Gemini directo
                response = await self.gemini_client.generate_structured_output(prompt)
                return (
                    response
                    if isinstance(response, dict)
                    else {"response": str(response)}
                )

        # Skill para planificación de crononutrición
        async def plan_chrononutrition(
            input_text: str,
            user_profile: Dict[str, Any] = None,
            context: Dict[str, Any] = None,
        ) -> Dict[str, Any]:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un especialista en crononutrición y ritmos circadianos.
            Genera un plan de crononutrición personalizado basado en la siguiente solicitud:
            
            "{input_text}"
            
            El plan debe incluir:
            1. Distribución temporal óptima de comidas
            2. Ventana de alimentación recomendada
            3. Timing específico para macronutrientes
            4. Recomendaciones para pre/post entrenamiento
            5. Estrategias para optimizar el metabolismo
            6. Consideraciones para la calidad del sueño
            
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
                - Horario de entrenamiento: {user_profile.get('training_schedule', 'N/A')}
                - Horario de sueño: {user_profile.get('sleep_schedule', 'N/A')}
                """

            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional:\n"
                for entry in context["history"][
                    -3:
                ]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"

            # Usar VertexGeminiGenerateSkill si está disponible
            try:
                vertex_skill = VertexGeminiGenerateSkill()
                result = await vertex_skill.execute(
                    {"prompt": prompt, "temperature": 0.7, "model": "gemini-2.0-flash"}
                )
                response_text = result.get("text", "")

                # Intentar extraer JSON de la respuesta
                try:
                    # Buscar patrón JSON en la respuesta
                    import re

                    json_match = re.search(r"({.*})", response_text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    else:
                        # Si no se encuentra JSON, devolver respuesta como texto
                        return {"response": response_text}
                except Exception as e:
                    logger.warning(f"Error al extraer JSON de la respuesta: {e}")
                    return {"response": response_text}
            except Exception as e:
                logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
                # Fallback a cliente Gemini directo
                response = await self.gemini_client.generate_structured_output(prompt)
                return (
                    response
                    if isinstance(response, dict)
                    else {"response": str(response)}
                )

        # Registrar skills
        await self.register_skill("create_meal_plan", create_meal_plan)
        await self.register_skill("recommend_supplements", recommend_supplements)
        await self.register_skill("analyze_biomarkers", analyze_biomarkers)
        await self.register_skill("plan_chrononutrition", plan_chrononutrition)

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

            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                user_profile = self.supabase_client.get_user_profile(user_id)

            # Cargar el contexto de la conversación utilizando el método _get_context
            # Este método ya maneja la carga desde StateManager o memoria según corresponda
            conversation_context = await self._get_context(user_id, session_id)

            # Preparar contexto para la generación de respuesta
            prompt_context = self._prepare_context(
                user_input, user_profile, conversation_context
            )

            # Generar respuesta
            response = await self.gemini_client.generate_response(
                user_input, context=prompt_context, temperature=0.7
            )

            # Crear artefactos si es necesario (por ejemplo, un plan nutricional)
            artifacts = []
            if any(
                keyword in user_input.lower()
                for keyword in ["plan", "dieta", "comida", "menú", "alimentación"]
            ):
                # Crear un artefacto de plan nutricional
                nutrition_plan = await self._generate_nutrition_plan(
                    user_input, user_profile
                )

                artifact_id = f"nutrition_plan_{uuid.uuid4().hex[:8]}"
                artifact = self.create_artifact(
                    artifact_id=artifact_id,
                    artifact_type="nutrition_plan",
                    parts=[self.create_data_part(nutrition_plan)],
                )
                artifacts.append(artifact)

            # Si se mencionan suplementos, crear un artefacto de recomendación
            if any(
                keyword in user_input.lower()
                for keyword in ["suplemento", "vitamina", "mineral", "proteína"]
            ):
                supplement_rec = await self._generate_supplement_recommendation(
                    user_input, user_profile
                )

                artifact_id = f"supplement_rec_{uuid.uuid4().hex[:8]}"
                artifact = self.create_artifact(
                    artifact_id=artifact_id,
                    artifact_type="supplement_recommendation",
                    parts=[self.create_data_part(supplement_rec)],
                )
                artifacts.append(artifact)

            # Registrar la interacción
            if user_id:
                self.supabase_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=user_input,
                    response=response,
                )

                # Interactuar con MCPClient
                await self.mcp_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=user_input,
                    response=response,
                )
                logger.info("Interacción con MCPClient registrada")

            # Actualizar contexto y persistir en StateManager
            await self._update_context(user_id, session_id, user_input, response)

            # Crear mensaje de respuesta
            response_message = self.create_message(
                role="agent", parts=[self.create_text_part(response)]
            )

            # Devolver respuesta estructurada según el protocolo A2A
            return {
                "response": response,
                "message": response_message,
                "artifacts": artifacts,
            }

        except Exception as e:
            logger.error(f"Error en Precision Nutrition Architect: {e}")
            return {
                "error": str(e),
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de nutrición.",
            }

    async def process_message(self, from_agent: str, content: Dict[str, Any]) -> Any:
        msg = content.get("text", "")
        logger.info(f"{self.agent_id} procesando mensaje de {from_agent}: {msg}")

        try:
            start_time = time.time()
            # Respuesta simple inicial, podría ser más sofisticada
            response_text = f"Recibido mensaje de {from_agent}: '{msg}'. Procesando..."
            message = self.create_message(
                role="agent", parts=[self.create_text_part(response_text)]
            )
            execution_time = time.time() - start_time

            return {
                "status": "success",
                "response": response_text,
                "message": message,
                "agent_id": self.agent_id,
                "execution_time": execution_time,
                "metadata": {
                    "from_agent": from_agent,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "protocol": "a2a",
                    "agent_version": "1.0.0",
                },
            }

        except Exception as e:
            logger.error(
                f"Error en process_message de {self.agent_id} desde {from_agent}: {e}",
                exc_info=True,
            )
            error_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(f"Error procesando mensaje de {from_agent}.")
                ],
            )
            return {
                "status": "error",
                "response": f"Error procesando mensaje de {from_agent}: {str(e)}",
                "message": error_message,
                "error": str(e),
                "agent_id": self.agent_id,
                "metadata": {
                    "from_agent": from_agent,
                    "error_type": type(e).__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }

    def _prepare_context(
        self,
        user_input: str,
        user_profile: Optional[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> str:
        """
        Prepara el contexto para la generación de respuesta.

        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario
            context: Contexto adicional

        Returns:
            str: Contexto preparado para la generación de respuesta
        """
        prompt_context = """
        Eres el Precision Nutrition Architect de NGX, un experto en generar planes alimenticios, 
        crononutrición y suplementación basada en biomarcadores.
        
        Debes proporcionar recomendaciones nutricionales basadas en evidencia científica, 
        personalizadas para el usuario y sus objetivos específicos.
        Tus respuestas deben ser claras, concisas y accionables.
        """

        # Añadir información del perfil del usuario si está disponible
        if user_profile:
            prompt_context += f"""
            
            Información del usuario:
            - Nombre: {user_profile.get('name', 'N/A')}
            - Edad: {user_profile.get('age', 'N/A')}
            - Peso: {user_profile.get('weight', 'N/A')}
            - Altura: {user_profile.get('height', 'N/A')}
            - Objetivos: {user_profile.get('goals', 'N/A')}
            - Restricciones alimenticias: {user_profile.get('dietary_restrictions', 'N/A')}
            - Alergias: {user_profile.get('allergies', 'N/A')}
            """

        # Añadir contexto adicional si está disponible
        if context:
            additional_context = "\n".join(
                [
                    f"- {key}: {value}"
                    for key, value in context.items()
                    if key not in ["user_id", "session_id"]
                ]
            )
            if additional_context:
                prompt_context += f"""
                
                Contexto adicional:
                {additional_context}
                """

        return prompt_context

    async def _generate_nutrition_plan(
        self, user_input: str, user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Genera un plan nutricional estructurado.

        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario

        Returns:
            Dict[str, Any]: Plan nutricional estructurado
        """
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
        """
        Genera recomendaciones de suplementación personalizadas.

        Args:
            user_input: Texto de entrada del usuario
            user_profile: Perfil del usuario

        Returns:
            Dict[str, Any]: Recomendaciones de suplementación estructuradas
        """
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

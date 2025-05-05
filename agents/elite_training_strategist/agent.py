"""
Agente especializado en diseñar y periodizar programas de entrenamiento
para atletas de alto rendimiento.

Este agente implementa los protocolos oficiales A2A y ADK para comunicación
entre agentes y utiliza el modelo Gemini para generar planes personalizados.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional, Union
import json
import asyncio
import time
from datetime import datetime, timezone
import re
import os

from adk.toolkit import Toolkit
from agents.base.a2a_agent import A2AAgent
from clients.gemini_client import GeminiClient
from core.agent_card import AgentCard, Example
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from tools.vertex_gemini_tools import VertexGeminiGenerateSkill
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result
from google.cloud import aiplatform

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
    
    has_telemetry = True
except ImportError:
    # Fallback si OpenTelemetry no está disponible
    has_telemetry = False
    tracer = None
    request_counter = None
    response_time = None

# Configurar logger
logger = get_logger(__name__)

class EliteTrainingStrategist(A2AAgent):
    """
    Agente especializado en diseñar y periodizar programas de entrenamiento 
    para atletas de alto rendimiento.
    
    Este agente utiliza el modelo Gemini para generar planes de entrenamiento
    personalizados basados en los objetivos, nivel y restricciones del atleta.
    Implementa los protocolos oficiales A2A y ADK para comunicación entre agentes.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None, state_manager: Optional[StateManager] = None):
        """
        Inicializa el agente EliteTrainingStrategist.
        
        Args:
            toolkit: Toolkit con herramientas disponibles para el agente
            a2a_server_url: URL del servidor A2A (opcional)
            state_manager: Gestor de estados para persistencia (opcional)
        """
        # Definir capacidades y habilidades
        capabilities = [
            "elite_training",
            "performance_analysis",
            "periodization",
            "exercise_prescription"
        ]
        
        # Definir skills siguiendo el formato A2A con mejores prácticas
        skills = [
            {
                "id": "elite-training-generate-plan",
                "name": "Generación de Planes de Entrenamiento",
                "description": "Diseña planes de entrenamiento personalizados para atletas de alto rendimiento basados en objetivos específicos, historial de entrenamiento y limitaciones individuales",
                "tags": ["training-plan", "programming", "personalization", "high-performance", "sport-specific"],
                "examples": [
                    "Diseña un plan de entrenamiento para un corredor de 10K que busca mejorar su marca personal",
                    "Plan de entrenamiento para un jugador de baloncesto enfocado en mejorar la potencia de salto",
                    "Programa de entrenamiento para una nadadora de 200m estilo libre en fase de preparación para competición"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "elite-training-performance-analysis",
                "name": "Análisis de Rendimiento",
                "description": "Analiza datos de rendimiento deportivo para identificar fortalezas, debilidades, patrones y oportunidades de mejora en atletas de alto nivel",
                "tags": ["performance", "analysis", "metrics", "benchmarking", "improvement"],
                "examples": [
                    "Analiza mis datos de entrenamiento de los últimos 3 meses para identificar limitaciones",
                    "Evaluación de rendimiento basada en mis métricas de fuerza y potencia",
                    "Análisis de mis tiempos de carrera y factores limitantes para mejorar"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "elite-training-periodization",
                "name": "Periodización del Entrenamiento",
                "description": "Diseña estructuras de periodización a corto y largo plazo para optimizar las adaptaciones al entrenamiento y maximizar el rendimiento en momentos clave",
                "tags": ["periodization", "macrocycle", "mesocycle", "microcycle", "peaking"],
                "examples": [
                    "Diseña una periodización de 16 semanas para un levantador olímpico",
                    "Plan de periodización para una temporada completa de fútbol",
                    "Estructura de periodización no lineal para un atleta de CrossFit"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "elite-training-exercise-prescription",
                "name": "Prescripción de Ejercicios",
                "description": "Prescribe ejercicios específicos basados en objetivos y capacidades"
            }
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "Necesito un plan de entrenamiento para un maratón en 12 semanas"},
                "output": {"response": "Aquí tienes un plan de entrenamiento de 12 semanas para preparar un maratón..."}
            },
            {
                "input": {"message": "Analiza mi rendimiento en la última carrera: 10km en 45 minutos"},
                "output": {"response": "Basado en tu tiempo de 10km en 45 minutos, tu ritmo promedio es de 4:30 min/km..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="elite_training_strategist",
            name="NGX Elite Training Strategist",
            description="Especialista en diseño y periodización de programas de entrenamiento para atletas de alto rendimiento. Proporciona análisis de rendimiento, planes de entrenamiento personalizados, estrategias de periodización y prescripción de ejercicios basados en principios científicos y prácticas de élite.",
            capabilities=capabilities,
            toolkit=toolkit,
            a2a_server_url=a2a_server_url or "https://elite-training-api.ngx-agents.com/a2a",
            state_manager=state_manager,
            version="1.2.0",
            skills=skills,
            provider={
                "organization": "NGX Health & Performance",
                "url": "https://ngx-agents.com"
            },
            documentation_url="https://docs.ngx-agents.com/elite-training-strategist"
        )
        
        # Inicializar clientes y herramientas
        self.gemini_client = GeminiClient(model_name="gemini-2.0-flash")
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        self.mcp_client = MCPClient()
        
        # Inicializar el StateManager para persistencia
        self.state_manager = state_manager or StateManager()
        
        # Inicializar estado del agente
        self.update_state("training_plans", {})  # Almacenar planes de entrenamiento generados
        self.update_state("performance_analyses", {})  # Almacenar análisis de rendimiento
        self.update_state("conversation_contexts", {})  # Almacenar contextos de conversación
        
        # Inicializar AI Platform
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id") # Reemplazar con método de carga real
        gcp_region = os.getenv("GCP_REGION", "us-central1") # Reemplazar con método de carga real
        try:
            self.logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            self.logger.info("AI Platform inicializado correctamente.")
        except Exception as e:
            self.logger.error(f"Error al inicializar AI Platform: {e}", exc_info=True)
            # Considerar si el agente debe fallar o continuar sin Vertex AI
        
        logger.info(f"EliteTrainingStrategist inicializado con {len(capabilities)} capacidades")
    
    async def _run_async_impl(self, input_text: str, user_id: Optional[str] = None, 
                           session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        # Registrar métrica de solicitud si telemetría está disponible
        if has_telemetry and request_counter:
            request_counter.add(1, {"agent_id": self.agent_id, "user_id": user_id or "anonymous"})
            
        # Crear span para trazar la ejecución si telemetría está disponible
        if has_telemetry and tracer:
            with tracer.start_as_current_span("elite_training_strategist_process_request") as span:
                span.set_attribute("user_id", user_id or "anonymous")
                span.set_attribute("session_id", session_id or "none")
                span.set_attribute("input_length", len(input_text))
                
                # Medir tiempo de respuesta
                start_time = time.time()
                result = await self._process_request(input_text, user_id, session_id, **kwargs)
                end_time = time.time()
                
                # Registrar métrica de tiempo de respuesta
                if response_time:
                    response_time.record(end_time - start_time, {"agent_id": self.agent_id})
                    
                return result
        else:
            # Ejecución sin telemetría
            return await self._process_request(input_text, user_id, session_id, **kwargs)
    
    async def _process_request(self, input_text: str, user_id: Optional[str] = None, 
                           session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Procesa la solicitud del usuario y genera una respuesta utilizando las skills adecuadas.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        start_time = time.time()
        result = {}
        protocol_id = None
        response_text = ""
        response_type = "text"
        
        try:
            # Generar ID de usuario y sesión si no se proporcionan
            user_id = user_id or str(uuid.uuid4())
            session_id = session_id or str(uuid.uuid4())
            
            # Obtener contexto de la conversación
            context = await self._get_context(user_id, session_id)
            
            # Obtener perfil del usuario si está disponible
            user_profile = kwargs.get("user_profile", {})
            
            # Analizar la entrada del usuario para determinar la skill a utilizar
            if any(keyword in input_text.lower() for keyword in ["plan", "programa", "entrenamiento", "rutina"]):
                # Usar skill de generación de planes de entrenamiento
                try:
                    result = await self._generate_training_plan(input_text, context)
                    
                    # Generar respuesta
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        # Convertir resultado estructurado a texto
                        response_text = "Plan de entrenamiento personalizado:\n\n"
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if key != "response":
                                    response_text += f"**{key.replace('_', ' ').title()}**: {value}\n"
                        else:
                            response_text = str(result)
                    
                    # Almacenar resultado en el estado
                    training_plans = self._state.get("training_plans", {})
                    protocol_id = str(uuid.uuid4())
                    training_plans[protocol_id] = result
                    self.update_state("training_plans", training_plans)
                    response_type = "training_plan"
                    
                except Exception as e:
                    logger.error(f"Error al ejecutar skill generate_training_plan: {e}")
                    response_text = "Lo siento, ha ocurrido un error al generar el plan de entrenamiento."
                    result = {"error": str(e)}
                    protocol_id = None
                
            elif any(keyword in input_text.lower() for keyword in ["analiza", "análisis", "rendimiento", "métricas", "evalúa"]):
                # Usar skill de análisis de rendimiento
                try:
                    result = await self._analyze_performance(input_text, context)
                    
                    # Generar respuesta
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        # Convertir resultado estructurado a texto
                        response_text = "Análisis de rendimiento:\n\n"
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if key != "response":
                                    response_text += f"**{key.replace('_', ' ').title()}**: {value}\n"
                        else:
                            response_text = str(result)
                    
                    # Almacenar resultado en el estado
                    performance_analyses = self._state.get("performance_analyses", {})
                    protocol_id = str(uuid.uuid4())
                    performance_analyses[protocol_id] = result
                    self.update_state("performance_analyses", performance_analyses)
                    response_type = "performance_analysis"
                    
                except Exception as e:
                    logger.error(f"Error al ejecutar skill analyze_performance: {e}")
                    response_text = "Lo siento, ha ocurrido un error al analizar el rendimiento."
                    result = {"error": str(e)}
                    protocol_id = None
                
            elif any(keyword in input_text.lower() for keyword in ["periodización", "periodizar", "macrociclo", "mesociclo", "temporada"]):
                # Usar skill de diseño de periodización
                try:
                    # Extraer número de semanas si se especifica
                    weeks_match = re.search(r'(\d+)\s*semanas', input_text)
                    weeks = int(weeks_match.group(1)) if weeks_match else 12
                    
                    result = await self._design_periodization(input_text, weeks, context)
                    
                    # Generar respuesta
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        # Convertir resultado estructurado a texto
                        response_text = f"Plan de periodización ({weeks} semanas):\n\n"
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if key != "response":
                                    response_text += f"**{key.replace('_', ' ').title()}**: {value}\n"
                        else:
                            response_text = str(result)
                    
                    # Almacenar resultado en el estado
                    periodization_plans = self._state.get("periodization_plans", {})
                    protocol_id = str(uuid.uuid4())
                    periodization_plans[protocol_id] = result
                    self.update_state("periodization_plans", periodization_plans)
                    response_type = "periodization_plan"
                    
                except Exception as e:
                    logger.error(f"Error al ejecutar skill design_periodization: {e}")
                    response_text = "Lo siento, ha ocurrido un error al diseñar el plan de periodización."
                    result = {"error": str(e)}
                    protocol_id = None
            
            elif any(keyword in input_text.lower() for keyword in ["ejercicio", "ejercicios", "técnica", "biomecánica", "prescribe"]):
                # Usar skill de prescripción de ejercicios
                try:
                    result = await self._prescribe_exercises(input_text, context)
                    
                    # Generar respuesta
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        # Convertir resultado estructurado a texto
                        response_text = "Prescripción de ejercicios:\n\n"
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if key != "response":
                                    response_text += f"**{key.replace('_', ' ').title()}**: {value}\n"
                        else:
                            response_text = str(result)
                    
                    # Almacenar resultado en el estado
                    exercise_prescriptions = self._state.get("exercise_prescriptions", {})
                    protocol_id = str(uuid.uuid4())
                    exercise_prescriptions[protocol_id] = result
                    self.update_state("exercise_prescriptions", exercise_prescriptions)
                    response_type = "exercise_prescription"
                    
                except Exception as e:
                    logger.error(f"Error al ejecutar skill prescribe_exercises: {e}")
                    response_text = "Lo siento, ha ocurrido un error al prescribir los ejercicios."
                    result = {"error": str(e)}
                    protocol_id = None
            
            else:
                # Respuesta general sobre entrenamiento
                response = await self._generate_training_plan(input_text, context)
                response_type = "general_response"
            
            # Añadir la interacción al historial interno del agente
            self.add_to_history(input_text, response)
            
            # Actualizar contexto y persistir en StateManager
            await self._update_context(user_id, session_id, input_text, response)
            
            # Crear artefactos para la respuesta
            artifacts = [
                {
                    "type": response_type,
                    "content": response,
                    "metadata": {
                        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            ]
            
            # Devolver respuesta final
            return {
                "status": "success",
                "response": response,
                "artifacts": artifacts,
                "agent_id": self.agent_id,
                "metadata": {
                    "response_type": response_type,
                    "user_id": user_id,
                    "session_id": session_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error en EliteTrainingStrategist: {e}", exc_info=True)
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de entrenamiento.",
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    async def _generate_training_plan(self, input_text: str, context: Dict[str, Any]) -> str:
        """
        Genera un plan de entrenamiento personalizado utilizando el modelo Gemini.
        
        Args:
            input_text: Texto de entrada del usuario con la solicitud del plan
            context: Contexto adicional como historial, preferencias, etc.
            
        Returns:
            str: Plan de entrenamiento generado y formateado, o cadena vacía en caso de error.
        """
        try:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un entrenador de élite especializado en diseñar programas de entrenamiento personalizados.
            Genera un plan de entrenamiento detallado basado en la siguiente solicitud:
            
            {input_text}
            
            {f"Sus objetivos específicos son: {', '.join(context.get('goals', []))}" if 'goals' in context else ""}
            
            Tu respuesta debe incluir:
            1. Evaluación inicial de la solicitud
            2. Objetivos claros y medibles
            3. Periodización del entrenamiento
            4. Desglose semanal de sesiones
            5. Ejercicios específicos con series, repeticiones y descansos
            6. Recomendaciones de nutrición y recuperación
            7. Métricas para evaluar el progreso
            
            Formato tu respuesta de manera clara y profesional, utilizando encabezados y listas para mejorar la legibilidad.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional de conversaciones previas:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # Registrar la generación
            self.logger.info(f"Generando plan de entrenamiento para: {input_text[:50]}...")
            
            # Generar plan con Gemini
            plan = await self.gemini_client.generate_content(prompt)
            
            # Registrar éxito
            self.logger.info(f"Plan de entrenamiento generado exitosamente: {len(plan)} caracteres")
            
            return plan
        
        except Exception as e:
            self.logger.error(f"Error en _generate_training_plan al llamar a Gemini: {e}", exc_info=True)
            return "" # Devolver cadena vacía en caso de error
    
    async def _analyze_performance(self, input_text: str, context: Dict[str, Any]) -> str:
        """
        Analiza el rendimiento de un atleta utilizando el modelo Gemini.
        
        Args:
            input_text: Texto de entrada del usuario con los datos de rendimiento
            context: Contexto adicional como historial, métricas previas, etc.
            
        Returns:
            str: Análisis de rendimiento detallado y formateado
        """
        try:
            # Intentar usar la skill registrada
            result = await self.execute_skill("analyze_performance", 
                                             input_text=input_text, 
                                             context=context)
            return result
        except (ValueError, AttributeError) as e:
            # Fallback a implementación directa si la skill no está disponible
            self.logger.warning(f"Skill 'analyze_performance' no disponible, usando fallback: {e}")
            
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un analista de rendimiento deportivo especializado en evaluar datos de entrenamiento.
            Analiza los siguientes datos de rendimiento y proporciona insights detallados:
            
            {input_text}
            
            {f"Sus objetivos específicos son: {', '.join(context.get('goals', []))}" if 'goals' in context else ""}
            
            Tu respuesta debe incluir:
            1. Evaluación de los datos proporcionados
            2. Comparación con estándares para el nivel del atleta
            3. Identificación de fortalezas y áreas de mejora
            4. Recomendaciones específicas para mejorar
            5. Objetivos realistas a corto y medio plazo
            
            Formato tu respuesta de manera clara y profesional, utilizando encabezados y listas para mejorar la legibilidad.
            Incluye datos cuantitativos cuando sea posible.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional de análisis previos:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # Registrar el análisis
            self.logger.info(f"Analizando rendimiento para: {input_text[:50]}...")
            
            # Generar análisis con Gemini
            analysis = await self.gemini_client.generate_content(prompt)
            
            # Registrar éxito
            self.logger.info(f"Análisis de rendimiento generado exitosamente: {len(analysis)} caracteres")
            
            return analysis
    
    async def _get_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
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
                    logger.debug(f"Contexto cargado desde StateManager para session_id={session_id}")
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
        
    async def _update_context(self, user_id: Optional[str], session_id: Optional[str], msg: str, resp: str) -> None:
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
                logger.debug(f"Contexto actualizado en StateManager para session_id={session_id}")
            except Exception as e:
                logger.warning(f"Error al guardar contexto en StateManager: {e}")
    
    def _create_agent_card(self) -> AgentCard:
        """
        Crea un Agent Card estandarizado según el protocolo A2A.
        
        Returns:
            AgentCard: Objeto AgentCard con toda la información del agente
        """
        # Crear ejemplos de uso para el agente
        examples = [
            Example(
                input="Necesito un plan de entrenamiento para mejorar mi rendimiento en maratón. Actualmente corro 50km por semana y mi mejor tiempo es 3:45.",
                output="# Plan de Entrenamiento para Maratón\n\n## Objetivo\nMejorar tu tiempo de maratón por debajo de 3:30.\n\n## Estructura Semanal\n- **Lunes**: Recuperación activa - 6km a ritmo fácil + movilidad\n- **Martes**: Intervalos - 12km total con 6x800m a ritmo objetivo de 10K\n- **Miércoles**: Ritmo medio - 10km a ritmo moderado\n- **Jueves**: Recuperación - 6km fáciles + fuerza\n- **Viernes**: Tempo - 12km con 6km a ritmo de media maratón\n- **Sábado**: Recuperación - 5km muy suaves + movilidad\n- **Domingo**: Tirada larga - 22km aumentando progresivamente hasta 32km\n\n## Progresión\nAumentaremos el volumen semanal gradualmente hasta 70-75km, con énfasis en la calidad de las sesiones clave.\n\n## Métricas de Seguimiento\n- Ritmo en intervalos\n- Tiempo en tiradas largas\n- Variabilidad de frecuencia cardíaca\n- Sensaciones subjetivas (1-10)\n\n## Estrategias de Recuperación\n- Hidratación inmediata post-entreno\n- Nutrición rica en proteínas y carbohidratos\n- Sueño de calidad (8h mínimo)\n- Sesiones de espuma de rodillo 3x semana"
            ),
            Example(
                input="¿Puedes analizar mi rendimiento en levantamiento de pesas? Mis números actuales son: sentadilla 120kg, peso muerto 150kg, press banca 90kg. Entreno 4 días por semana desde hace 2 años.",
                output="# Análisis de Rendimiento en Levantamiento de Pesas\n\n## Evaluación de Números Actuales\nPara un atleta con 2 años de experiencia, tus números son sólidos y muestran una buena base de fuerza.\n\n## Fortalezas Identificadas\n- Excelente desarrollo en peso muerto (150kg), indicando buena fuerza posterior\n- Ratio sentadilla/peso muerto adecuado (1:1.25)\n- Consistencia de entrenamiento establecida (4 días/semana)\n\n## Áreas de Mejora\n- El press de banca (90kg) podría mejorar en relación a los levantamientos de tren inferior\n- Posible desequilibrio entre cadena anterior/posterior\n\n## Recomendaciones\n1. Incrementar frecuencia de entrenamiento de tren superior a 2x semana\n2. Implementar variaciones de press (inclinado, declinado, close-grip)\n3. Trabajar en el rango de 4-6 repeticiones para desarrollo de fuerza máxima\n4. Considerar bloques de especialización de 6 semanas para press de banca\n\n## Próximos Objetivos Realistas (6 meses)\n- Sentadilla: 135kg\n- Peso muerto: 170kg\n- Press banca: 110kg\n\n## Estrategias de Progresión\n- Periodización ondulante\n- Ciclos de intensidad progresiva\n- Deloads programados cada 6-8 semanas"
            ),
            Example(
                input="Diseña un plan de periodización para un jugador de fútbol de 16 semanas, desde pretemporada hasta competición.",
                output="# Periodización para Jugador de Fútbol (16 Semanas)\n\n## MACROCICLO (16 semanas)\n\n### MESOCICLO 1: PREPARACIÓN GENERAL (Semanas 1-4)\n**Objetivo**: Desarrollar base aeróbica y fuerza general\n\n| Semana | Volumen | Intensidad | Enfoque Principal |\n|--------|---------|------------|-------------------|\n| 1 | Alto | Baja | Resistencia aeróbica, técnica básica |\n| 2 | Alto | Baja-Media | Fuerza general, resistencia |\n| 3 | Alto | Media | Potencia aeróbica, coordinación |\n| 4 | Medio | Media | Técnica específica, velocidad |\n\n### MESOCICLO 2: PREPARACIÓN ESPECÍFICA (Semanas 5-8)\n**Objetivo**: Desarrollar capacidades específicas del fútbol\n\n| Semana | Volumen | Intensidad | Enfoque Principal |\n|--------|---------|------------|-------------------|\n| 5 | Medio-Alto | Media | Resistencia específica, táctica |\n| 6 | Medio | Media-Alta | Potencia, agilidad, velocidad |\n| 7 | Medio | Alta | Situaciones de juego, sprint |\n| 8 | Bajo | Media | Recuperación activa, técnica |\n\n### MESOCICLO 3: PRECOMPETITIVO (Semanas 9-12)\n**Objetivo**: Integrar componentes físicos y tácticos\n\n| Semana | Volumen | Intensidad | Enfoque Principal |\n|--------|---------|------------|-------------------|\n| 9 | Medio | Alta | Juegos reducidos, velocidad |\n| 10 | Medio-Bajo | Muy Alta | Potencia, sprint, táctica |\n| 11 | Bajo | Máxima | Partidos amistosos, situaciones |\n| 12 | Muy Bajo | Baja | Tapering, recuperación |\n\n### MESOCICLO 4: COMPETITIVO (Semanas 13-16)\n**Objetivo**: Mantener rendimiento y optimizar recuperación\n\n| Semana | Volumen | Intensidad | Enfoque Principal |\n|--------|---------|------------|-------------------|\n| 13 | Bajo | Alta | Competición, recuperación |\n| 14 | Bajo | Alta | Competición, mantenimiento |\n| 15 | Bajo | Alta | Competición, ajustes tácticos |\n| 16 | Bajo | Alta | Competición, pico de rendimiento |\n\n## DISTRIBUCIÓN SEMANAL (MICROCICLO TIPO - FASE COMPETITIVA)\n- **Lunes**: Recuperación activa + técnica\n- **Martes**: Alta intensidad (potencia/velocidad)\n- **Miércoles**: Intensidad media (táctico/técnico)\n- **Jueves**: Alta intensidad (específico posición)\n- **Viernes**: Baja intensidad (activación pre-partido)\n- **Sábado**: COMPETICIÓN\n- **Domingo**: Recuperación"
            ),
            Example(
                input="Necesito ejercicios específicos para mejorar la estabilidad de rodilla en un futbolista con historial de lesión de ligamento colateral medial.",
                output="# Ejercicios para Estabilidad de Rodilla Post-LCM\n\n## FASE 1: ESTABILIZACIÓN INICIAL\n\n### 1. Mini-Sentadilla Isométrica con Banda\n- **Músculos**: Cuádriceps, aductores, glúteo medio\n- **Ejecución**: Coloca una banda de resistencia justo por encima de las rodillas. Realiza una mini-sentadilla (30-45°) y mantén la posición empujando las rodillas contra la banda.\n- **Series/Tiempo**: 3 series de 30-45 segundos\n- **Consideraciones**: Mantén alineación rodilla-pie, evita valgo de rodilla\n\n### 2. Puente Lateral con Abducción\n- **Músculos**: Glúteo medio, TFL, core lateral\n- **Ejecución**: En posición de puente lateral, eleva la pierna superior manteniendo la cadera alineada\n- **Series/Repeticiones**: 2-3 series de 10-15 repeticiones por lado\n- **Progresión**: Añadir banda de resistencia alrededor de los tobillos\n\n## FASE 2: FORTALECIMIENTO FUNCIONAL\n\n### 3. Step-Down Controlado\n- **Músculos**: Cuádriceps, glúteos, isquiotibiales\n- **Ejecución**: Desde un step, realiza un descenso controlado con la pierna afectada, manteniendo la rodilla alineada con el segundo dedo del pie\n- **Series/Repeticiones**: 3 series de 8-12 repeticiones\n- **Consideraciones**: Controlar la rotación de cadera y rodilla durante todo el movimiento\n\n### 4. Sentadilla Búlgara\n- **Músculos**: Cuádriceps, glúteos, estabilizadores de rodilla\n- **Ejecución**: Con el pie trasero elevado sobre un banco, realiza una sentadilla unilateral\n- **Series/Repeticiones**: 3 series de 8-10 repeticiones por pierna\n- **Progresión**: Añadir peso cuando la técnica sea perfecta\n\n## FASE 3: ESTABILIDAD DINÁMICA\n\n### 5. Salto Lateral con Estabilización\n- **Músculos**: Complejo de cadera, cuádriceps, estabilizadores de rodilla\n- **Ejecución**: Salto lateral suave seguido de una pausa de 3 segundos en posición de semi-sentadilla\n- **Series/Repeticiones**: 2-3 series de 6-8 repeticiones por lado\n- **Consideraciones**: Aterrizar con rodilla ligeramente flexionada, absorber el impacto\n\n### 6. Ejercicio de Cambio de Dirección Controlado\n- **Músculos**: Cadena cinética completa, énfasis en estabilizadores\n- **Ejecución**: Trote suave con cambios de dirección a 45° y 90°, enfatizando el control de la rodilla\n- **Series/Distancia**: 2 series de 6-8 cambios de dirección por lado\n- **Progresión**: Aumentar velocidad gradualmente\n\n## RECOMENDACIONES ADICIONALES\n- Realizar estos ejercicios 3-4 veces por semana\n- Incorporar trabajo propioceptivo en superficie inestable\n- Complementar con liberación miofascial en banda iliotibial y aductores\n- Evaluar progreso cada 2 semanas y ajustar intensidad"
            )
        ]
        
        # Crear el Agent Card
        agent_card = AgentCard(
            name="NGX Elite Training Strategist",
            description="Especialista en diseño y periodización de programas de entrenamiento para atletas de alto rendimiento. Proporciona análisis de rendimiento, planes de entrenamiento personalizados, estrategias de periodización y prescripción de ejercicios basados en principios científicos y prácticas de élite.",
            version="1.2.0",
            agent_type="elite_training_strategist",
            capabilities=[
                "Diseño de planes de entrenamiento personalizados",
                "Análisis de rendimiento deportivo",
                "Periodización del entrenamiento a corto y largo plazo",
                "Prescripción de ejercicios específicos y técnicas correctas",
                "Optimización de rendimiento deportivo"
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta o solicitud del usuario relacionada con entrenamiento deportivo"
                    },
                    "user_profile": {
                        "type": "object",
                        "description": "Perfil del usuario con información relevante para personalizar respuestas",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                            "sport": {"type": "string"},
                            "experience_level": {"type": "string"},
                            "goals": {"type": "array", "items": {"type": "string"}},
                            "limitations": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "context": {
                        "type": "object",
                        "description": "Contexto adicional para la consulta"
                    }
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "response": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "type": {"type": "string"},
                            "protocol_id": {"type": "string"},
                            "metadata": {"type": "object"}
                        }
                    }
                }
            },
            examples=examples,
            provider={
                "name": "NGX Health & Performance",
                "url": "https://ngx-agents.com"
            },
            documentation_url="https://docs.ngx-agents.com/elite-training-strategist",
            contact_email="support@ngx-agents.com",
            tags=["training", "sports", "performance", "periodization", "exercise-prescription", "elite-athletes"]
        )
        
        return agent_card
    
    def get_agent_card(self):
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada que cumple con las especificaciones
            del protocolo A2A de Google, incluyendo metadatos enriquecidos, capacidades
            y habilidades detalladas.
        """
        return self._create_agent_card().to_dict()
        
    async def start(self):
        """
        Inicia el agente, conectándolo al servidor ADK y registrando sus skills.
        """
        # Registrar skills en el toolkit
        await self._register_skills()
        
        # Iniciar agente ADK (conectar al servidor ADK y registrar skills)
        await super().start()
        
    async def _register_skills(self):
        """
        Registra las habilidades del agente según el protocolo A2A con metadatos mejorados.
        """
        # Registrar skills en el toolkit si está disponible
        if self.toolkit:
            try:
                # Registrar skill de generación de planes de entrenamiento
                await self.register_skill(
                    "generate_training_plan",
                    "Diseña planes de entrenamiento personalizados para atletas de alto rendimiento basados en objetivos específicos, historial de entrenamiento y limitaciones individuales",
                    self._generate_training_plan,
                    tags=["training-plan", "programming", "personalization", "high-performance", "sport-specific"],
                    examples=[
                        "Diseña un plan de entrenamiento para un corredor de 10K que busca mejorar su marca personal",
                        "Plan de entrenamiento para un jugador de baloncesto enfocado en mejorar la potencia de salto",
                        "Programa de entrenamiento para una nadadora de 200m estilo libre en fase de preparación para competición"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de análisis de rendimiento
                await self.register_skill(
                    "analyze_performance",
                    "Analiza datos de rendimiento deportivo para identificar fortalezas, debilidades, patrones y oportunidades de mejora en atletas de alto nivel",
                    self._analyze_performance,
                    tags=["performance", "analysis", "metrics", "benchmarking", "improvement"],
                    examples=[
                        "Analiza mis datos de entrenamiento de los últimos 3 meses para identificar limitaciones",
                        "Evaluación de rendimiento basada en mis métricas de fuerza y potencia",
                        "Análisis de mis tiempos de carrera y factores limitantes para mejorar"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de diseño de periodización
                await self.register_skill(
                    "design_periodization",
                    "Diseña estructuras de periodización a corto y largo plazo para optimizar las adaptaciones al entrenamiento y maximizar el rendimiento en momentos clave",
                    self._design_periodization,
                    tags=["periodization", "macrocycle", "mesocycle", "microcycle", "peaking"],
                    examples=[
                        "Diseña una periodización de 16 semanas para un levantador olímpico",
                        "Plan de periodización para una temporada completa de fútbol",
                        "Estructura de periodización no lineal para un atleta de CrossFit"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de prescripción de ejercicios
                await self.register_skill(
                    "prescribe_exercises",
                    "Prescribe ejercicios específicos basados en objetivos y capacidades",
                    self._prescribe_exercises,
                    tags=["exercises", "biomechanics", "technique", "progression", "specificity"],
                    examples=[
                        "Prescribe ejercicios para mejorar la estabilidad de rodilla en un futbolista",
                        "Ejercicios específicos para desarrollar potencia en el tren superior para un lanzador de jabalina",
                        "Selección de ejercicios para un corredor con historial de fascitis plantar"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                logger.info(f"Skills registradas correctamente: {len(self.skills)}")
            except Exception as e:
                logger.error(f"Error al registrar skills: {e}")
        else:
            logger.warning("No se ha proporcionado un toolkit para registrar skills")
        
        # Skill para analizar rendimiento
        async def analyze_performance(input_text: str, context: Dict[str, Any] = None) -> str:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un analista de rendimiento deportivo especializado en evaluar datos de entrenamiento.
            Analiza los siguientes datos de rendimiento y proporciona insights detallados:
            
            {input_text}
            
            {f"Sus objetivos específicos son: {', '.join(context.get('goals', []))}" if 'goals' in context else ""}
            
            Tu respuesta debe incluir:
            1. Evaluación de los datos proporcionados
            2. Comparación con estándares para el nivel del atleta
            3. Identificación de fortalezas y áreas de mejora
            4. Recomendaciones específicas para mejorar
            5. Objetivos realistas a corto y medio plazo
            
            Formato tu respuesta de manera clara y profesional, utilizando encabezados y listas para mejorar la legibilidad.
            Incluye datos cuantitativos cuando sea posible.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional de análisis previos:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # TODO: Integrar RAG aquí para buscar ejemplos/principios de entrenamiento relevantes
            # O usar mcp7_query para obtener datos específicos del atleta si están en Supabase.
            result = await self.gemini_client.generate_content(prompt)
            return result
        
        # Skill para diseñar periodización
        async def design_periodization(input_text: str, weeks: int = 12, context: Dict[str, Any] = None) -> str:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un especialista en periodización del entrenamiento deportivo.
            Diseña un plan de periodización de {weeks} semanas basado en la siguiente solicitud:
            
            {input_text}
            
            Incluye:
            1. División en macrociclos, mesociclos y microciclos
            2. Distribución de volumen e intensidad a lo largo del tiempo
            3. Fases de acumulación, transformación y realización
            4. Picos de rendimiento planificados
            5. Estrategias de tapering y supercompensación
            
            Presenta el plan de periodización en formato de tabla con semanas, fases y objetivos principales.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # TODO: Usar mcp8_think para estructurar el diseño de la periodización si es complejo.
            # TODO: Integrar RAG para buscar filosofías/modelos de periodización específicos.
            result = await self.gemini_client.generate_content(prompt)
            return result
        
        # Skill para prescribir ejercicios
        async def prescribe_exercises(input_text: str, context: Dict[str, Any] = None) -> str:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un especialista en prescripción de ejercicios y biomecánica.
            Prescribe ejercicios específicos basados en la siguiente solicitud:
            
            {input_text}
            
            Para cada ejercicio incluye:
            1. Nombre y variante específica
            2. Músculos principales y secundarios trabajados
            3. Técnica correcta de ejecución
            4. Progresiones y regresiones
            5. Consideraciones de seguridad
            
            Presenta los ejercicios en formato de lista con instrucciones claras y precisas.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            # TODO: Usar mcp7_query para obtener historial/capacidades del atleta desde Supabase.
            # TODO: Integrar RAG para buscar descripciones/ejemplos de ejercicios específicos.
            result = await self.gemini_client.generate_content(prompt)
            return result
        
        # Registrar skills
        await self.register_skill("generate_training_plan", self._generate_training_plan)
        await self.register_skill("analyze_performance", self._analyze_performance)
        await self.register_skill("design_periodization", self._design_periodization)
        await self.register_skill("prescribe_exercises", self._prescribe_exercises)

    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """Ejecuta una tarea solicitada por el servidor A2A."""
        logger.info(f"EliteTrainingStrategist received task: {task.get('id', 'N/A')}")
        start_time = time.time()
        metadata = {
            "status": "error", # Default a error
            "agent_id": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        payload = {
            "error": "UnknownError",
            "response": "No se pudo procesar la solicitud."
        }
        artifacts = []
        
        try:
            input_text = task.get("input", "")
            context = task.get("context", {})
            user_id = context.get("user_id")
            session_id = context.get("session_id")
            user_profile = context.get("user_profile", {}) # Asumir que viene en contexto A2A
            
            if not input_text:
                raise ValueError("Input text is missing in the task.")
            
            response_text = ""
            skill_result = None
            artifact_type = "generic_result"
            artifact_content = {}
            
            # Analizar la entrada del usuario para determinar la skill a utilizar
            if any(keyword in input_text.lower() for keyword in ["plan", "programa", "entrenamiento", "rutina"]):
                logger.info("Executing skill: generate_training_plan")
                artifact_type = "training_plan"
                skill_result = await self._generate_training_plan(input_text, context) # Llamada directa
                response_text = f"Aquí tienes tu plan de entrenamiento personalizado: \n\n{skill_result}" # Simplificado por ahora
                artifact_content = skill_result if isinstance(skill_result, dict) else {"plan_text": skill_result}
            
            elif any(keyword in input_text.lower() for keyword in ["analiza", "análisis", "rendimiento", "métricas", "evalúa"]):
                logger.info("Executing skill: analyze_performance")
                artifact_type = "performance_analysis"
                skill_result = await self._analyze_performance(input_text, context) # Llamada directa
                response_text = f"Aquí tienes el análisis de rendimiento: \n\n{skill_result}" # Simplificado por ahora
                artifact_content = skill_result if isinstance(skill_result, dict) else {"analysis_text": skill_result}
            
            elif any(keyword in input_text.lower() for keyword in ["periodización", "periodizar", "macrociclo", "mesociclo"]):
                logger.info("Executing skill: design_periodization")
                artifact_type = "periodization_plan"
                # Extraer 'weeks' si se proporciona en el input o contexto, default a 12
                weeks = context.get("weeks", 12) # Simplificado, idealmente extraer del input
                skill_result = await self._design_periodization(input_text, weeks, context) # Llamada directa
                response_text = f"Aquí tienes el plan de periodización: \n\n{skill_result}" # Simplificado por ahora
                artifact_content = skill_result if isinstance(skill_result, dict) else {"periodization_text": skill_result}
            
            elif any(keyword in input_text.lower() for keyword in ["ejercicio", "prescribe", "técnica"]):
                logger.info("Executing skill: prescribe_exercises")
                artifact_type = "exercise_prescription"
                skill_result = await self._prescribe_exercises(input_text, context) # Llamada directa
                response_text = f"Aquí tienes la prescripción de ejercicios: \n\n{skill_result}" # Simplificado por ahora
                artifact_content = skill_result if isinstance(skill_result, dict) else {"prescription_text": skill_result}
            
            else:
                # No se reconoce la intención
                logger.warning(f"Intent not recognized for input: {input_text}")
                response_text = "Lo siento, no he entendido tu solicitud. ¿Podrías reformularla? Puedo ayudarte a generar planes de entrenamiento, analizar rendimiento, diseñar periodización o prescribir ejercicios."
                metadata["status"] = "no_match"
                payload = {"response": response_text}
                # No crear artefacto si no hay match
            
            # Si se ejecutó una skill con éxito
            if skill_result is not None:
                metadata["status"] = "success"
                execution_time = time.time() - start_time
                metadata["execution_time"] = execution_time
                
                # Crear mensaje de respuesta A2A
                response_message = self.create_message(
                    role="agent",
                    parts=[
                        self.create_text_part(response_text)
                    ]
                )
                
                # Crear artefacto A2A
                if artifact_content:
                    artifact_id = f"{artifact_type}_{uuid.uuid4().hex[:8]}"
                    artifact = self.create_artifact(
                        artifact_id=artifact_id,
                        artifact_type=artifact_type,
                        parts=[
                            self.create_data_part(artifact_content) # Asume que el contenido es serializable a JSON
                        ]
                    )
                    artifacts.append(artifact)
                
                payload = {
                    "response": response_text, 
                    "message": response_message,
                    "artifacts": artifacts
                }
        
        except ValueError as ve:
            logger.error(f"ValueError in EliteTrainingStrategist execute_task: {ve}")
            metadata["status"] = "error"
            payload = {"error": str(ve), "response": "Error en la solicitud: falta información necesaria."}
        except Exception as e:
            logger.error(f"Error in EliteTrainingStrategist execute_task: {e}", exc_info=True)
            metadata["status"] = "error"
            # Actualizar payload de error si no se estableció antes
            if payload.get("error") == "UnknownError":
                payload["error"] = f"{type(e).__name__}: {e}"
                payload["response"] = "Lo siento, ha ocurrido un error inesperado al procesar tu solicitud."
        
        # Siempre devolver la estructura metadata/payload
        return {"metadata": metadata, "payload": payload}
    
    async def process_message(self, from_agent: str, content: Dict[str, Any]) -> Any:
        """Procesa un mensaje recibido de otro agente."""
        logger.info(f"EliteTrainingStrategist received message from {from_agent}")
        metadata = {
            "status": "error",
            "agent_id": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "process_message not fully implemented yet for EliteTrainingStrategist."
        }
        payload = {
            "error": "NotImplementedError",
            "response": "La funcionalidad para procesar mensajes de otros agentes aún no está implementada."
        }
        return {"metadata": metadata, "payload": payload}

    async def _design_periodization(self, input_text: str, weeks: int, context: Dict[str, Any]) -> str:
        """
        Diseña un plan de periodización utilizando el modelo Gemini.
        
        Args:
            input_text: Texto de entrada del usuario con la solicitud
            weeks: Número de semanas para la periodización
            context: Contexto adicional
            
        Returns:
            str: Plan de periodización generado o cadena vacía en caso de error.
        """
        try:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un especialista en periodización del entrenamiento deportivo.
            Diseña un plan de periodización de {weeks} semanas basado en la siguiente solicitud:
            
            {input_text}
            
            Incluye:
            1. División en macrociclos, mesociclos y microciclos
            2. Distribución de volumen e intensidad a lo largo del tiempo
            3. Fases de acumulación, transformación y realización
            4. Picos de rendimiento planificados
            5. Estrategias de tapering y supercompensación
            
            Presenta el plan de periodización en formato de tabla con semanas, fases y objetivos principales.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            self.logger.info(f"Generando plan de periodización para: {input_text[:50]}...")
            
            # Usar el cliente Gemini configurado en el agente
            periodization_plan = await self.gemini_client.generate_content(prompt)
            
            self.logger.info(f"Plan de periodización generado exitosamente: {len(periodization_plan)} caracteres")
            return periodization_plan
        
        except Exception as e:
            self.logger.error(f"Error general en _design_periodization: {e}", exc_info=True)
            return "" # Devolver cadena vacía en caso de error general

    async def _prescribe_exercises(self, input_text: str, context: Dict[str, Any]) -> str:
        """
        Prescribe ejercicios específicos utilizando el modelo Gemini.
        
        Args:
            input_text: Texto de entrada del usuario con la solicitud
            context: Contexto adicional
            
        Returns:
            str: Prescripción de ejercicios generada o cadena vacía en caso de error.
        """
        try:
            # Construir prompt para Gemini
            prompt = f"""
            Actúa como un especialista en prescripción de ejercicios y biomecánica.
            Prescribe ejercicios específicos basados en la siguiente solicitud:
            
            {input_text}
            
            Para cada ejercicio incluye:
            1. Nombre y variante específica
            2. Músculos principales y secundarios trabajados
            3. Técnica correcta de ejecución
            4. Progresiones y regresiones
            5. Consideraciones de seguridad
            
            Presenta los ejercicios en formato de lista con instrucciones claras y precisas.
            """
            
            # Incluir contexto si está disponible
            if context and "history" in context and len(context["history"]) > 0:
                prompt += "\n\nContexto adicional:\n"
                for entry in context["history"][-3:]:  # Usar las últimas 3 interacciones
                    prompt += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
            
            self.logger.info(f"Generando prescripción de ejercicios para: {input_text[:50]}...")
            
            # Usar el cliente Gemini configurado en el agente
            prescription = await self.gemini_client.generate_content(prompt)
            
            self.logger.info(f"Prescripción de ejercicios generada exitosamente: {len(prescription)} caracteres")
            return prescription
        
        except Exception as e:
            self.logger.error(f"Error general en _prescribe_exercises: {e}", exc_info=True)
            return "" # Devolver cadena vacía en caso de error general

import logging
import json
import httpx
import uuid
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Callable
import os
from google.cloud import aiplatform

from adk.toolkit import Toolkit
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from tools.vertex_gemini_tools import VertexGeminiGenerateSkill
from agents.base.adk_agent import ADKAgent
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
    tracer = trace.get_tracer("orchestrator")
    
    # Configurar MeterProvider para métricas
    prometheus_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(metric_readers=[prometheus_reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter("orchestrator")
    
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


class NGXNexusOrchestrator(ADKAgent):
    """Agente Maestro que enruta consultas a agentes especializados usando A2A."""

    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None, state_manager: Optional[StateManager] = None):
        """
        Inicializa el orquestador de agentes NGX.
        
        Args:
            toolkit: Toolkit con herramientas disponibles para el agente
            a2a_server_url: URL del servidor A2A (opcional)
            state_manager: Gestor de estados para persistencia (opcional)
        """
        # Definir capacidades y habilidades
        capabilities = [
            "intent_analysis",
            "task_routing",
            "response_synthesis",
            "conversation_memory",
            "agent_coordination"
        ]
        
        skills = [
            {
                "name": "intent_analysis",
                "description": "Análisis de intención para determinar qué agentes especializados pueden responder mejor"
            },
            {
                "name": "task_routing",
                "description": "Enrutamiento de tareas a los agentes especializados adecuados"
            },
            {
                "name": "response_synthesis",
                "description": "Síntesis de respuestas de múltiples agentes en una respuesta coherente"
            },
            {
                "name": "conversation_memory",
                "description": "Mantenimiento del contexto de la conversación a lo largo del tiempo"
            },
            {
                "name": "agent_coordination",
                "description": "Coordinación de múltiples agentes para resolver tareas complejas"
            }
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "Necesito un plan de entrenamiento y nutrición para un maratón"},
                "output": {"response": "He coordinado con nuestros especialistas para crear un plan completo de entrenamiento y nutrición para tu maratón..."}
            },
            {
                "input": {"message": "Analiza mis últimos datos de entrenamiento y sugiere mejoras"},
                "output": {"response": "Después de analizar tus datos con nuestros especialistas, hemos identificado las siguientes áreas de mejora..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="orchestrator",
            name="NGX Nexus Orchestrator",
            description="Agente maestro que descompone consultas, enruta tareas y sintetiza respuestas.",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.0.0",
            a2a_server_url=a2a_server_url,
            state_manager=state_manager,
            skills=skills
        )
        
        # Inicializar clientes y herramientas
        self.gemini_client = GeminiClient(model_name="gemini-2.0-flash")
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        self.mcp_client = MCPClient()
        
        # Inicializar el StateManager para persistencia
        self.state_manager = state_manager or StateManager()
        
        # Estado y contexto del orquestador
        self.update_state("conversation_contexts", {})  # Usar el sistema de estado de BaseAgent
        
        # Tabla de enrutamiento de intenciones a agentes especializados
        self.intent_routing_table = {
            # Intención: [lista de IDs de agentes]
            "entrenamiento": ["elite_training_strategist", "gemini_training_assistant"],
            "nutrición": ["precision_nutrition_architect"],
            "recuperación": ["recovery_corrective"],
            "biohacking": ["biohacking_innovator"],
            "motivación": ["motivation_behavior_coach"],
            "progreso": ["progress_tracker"],
            "biometría": ["biometrics_insight_engine"],
            "general": ["gemini_training_assistant"]
        }
        
        # Mapeo de agentes especializados
        self.agent_map = {
            1: {"id": "elite_training_strategist", "name": "Elite Training Strategist"},
            2: {"id": "precision_nutrition_architect", "name": "Precision Nutrition Architect"},
            3: {"id": "biohacking_innovator", "name": "Biohacking Innovator"},
            4: {"id": "biometrics_insight_engine", "name": "Biometrics Insight Engine"},
            5: {"id": "recovery_corrective", "name": "Recovery & Corrective Specialist"},
            6: {"id": "motivation_behavior_coach", "name": "Motivation & Behavior Coach"},
            7: {"id": "progress_tracker", "name": "Progress Tracker"},
            8: {"id": "systems_integration_ops", "name": "Systems Integration & Ops"},
            9: {"id": "security_compliance_guardian", "name": "Security & Compliance Guardian"}
        }
        
        # Inicialización de AI Platform
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform: {e}", exc_info=True)
        
        logger.info(f"Orquestador NGX inicializado con {len(capabilities)} capacidades y {len(self.agent_map)} agentes disponibles")

    async def _run_async_impl(self, input_text: str, user_id: Optional[str] = None, 
                       session_id: Optional[str] = None, **kwargs):
        # Registrar métrica de solicitud si telemetría está disponible
        if has_telemetry and request_counter:
            request_counter.add(1, {"agent_id": self.agent_id, "user_id": user_id or "anonymous"})
            
        # Crear span para trazar la ejecución si telemetría está disponible
        if has_telemetry and tracer:
            with tracer.start_as_current_span("orchestrator_process_request") as span:
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
        Implementación asíncrona del procesamiento del agente orquestador.
        
        Sobrescribe el método de la clase base para proporcionar la implementación
        específica del orquestador que analiza intenciones, enruta a agentes
        especializados y sintetiza sus respuestas.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        # Generar session_id si no se proporciona
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.debug(f"Generando nuevo session_id: {session_id}")
        
        # Registrar el inicio de la ejecución
        logger.info(f"Orquestador procesando entrada: '{input_text[:50]}...' (user_id={user_id}, session_id={session_id})")
        
        try:
            # Cargar el contexto de la conversación utilizando el método _get_context
            # Este método ya maneja la carga desde StateManager o memoria según corresponda
            context = await self._get_context(user_id, session_id)
            
            # Analizar la intención del usuario para determinar qué agentes consultar
            intent_analysis_prompt = f"""
            Analiza la siguiente consulta del usuario y determina qué agentes especializados deberían responderla.
            Consulta: "{input_text}"
            
            Responde con un JSON que contenga:
            1. "primary_intent": La intención principal del usuario (entrenamiento, nutrición, recuperación, biohacking, motivación, progreso, biometría)
            2. "secondary_intents": Lista de intenciones secundarias si las hay
            3. "confidence": Nivel de confianza en la asignación (0.0-1.0)
            
            Formato de respuesta:
            {{
              "primary_intent": "intención principal",
              "secondary_intents": ["intención secundaria 1", "intención secundaria 2"],
              "confidence": 0.9
            }}
            """
            
            # Obtener análisis de intención usando skill de Vertex Gemini
            try:
                # Usar skill registrada si está disponible
                intent_analysis = await self.execute_skill("analyze_intent", prompt=intent_analysis_prompt)
            except (ValueError, AttributeError):
                # Fallback a cliente Gemini directo
                intent_analysis = await self.gemini_client.generate_response(intent_analysis_prompt, temperature=0.1)
            
            try:
                # Extraer JSON del resultado
                import re
                json_match = re.search(r'{.*}', intent_analysis, re.DOTALL)
                if json_match:
                    intent_data = json.loads(json_match.group(0))
                else:
                    # Fallback si no se encuentra JSON
                    intent_data = {
                        "primary_intent": "general",
                        "secondary_intents": [],
                        "confidence": 0.5
                    }
                
                # Obtener intenciones
                primary_intent = intent_data.get("primary_intent", "general").lower()
                secondary_intents = [intent.lower() for intent in intent_data.get("secondary_intents", [])]
                confidence = intent_data.get("confidence", 0.5)
                
                # Mapear intenciones a IDs de agentes usando la tabla de enrutamiento
                agent_ids_set = set()
                
                # Añadir agentes para la intención principal
                if primary_intent in self.intent_routing_table:
                    for agent_id in self.intent_routing_table[primary_intent]:
                        if agent_id in self.agent_map:
                            agent_ids_set.add(self.agent_map[agent_id])
                
                # Añadir agentes para intenciones secundarias
                for intent in secondary_intents:
                    if intent in self.intent_routing_table:
                        for agent_id in self.intent_routing_table[intent]:
                            if agent_id in self.agent_map:
                                agent_ids_set.add(self.agent_map[agent_id])
                
                # Si no se encontraron agentes, usar el agente general
                if not agent_ids_set and "general" in self.intent_routing_table:
                    for agent_id in self.intent_routing_table["general"]:
                        if agent_id in self.agent_map:
                            agent_ids_set.add(self.agent_map[agent_id])
                
                # Convertir a lista
                agent_ids = list(agent_ids_set) or [1]  # Fallback a Elite Training Strategist
                
                logger.info(f"Intención detectada: {primary_intent} (confianza: {confidence}), consultando agentes: {agent_ids}")
            except Exception as e:
                logger.error(f"Error al parsear análisis de intención: {e}")
                # Fallback a Elite Training Strategist
                agent_ids = [1]
                primary_intent = "general"
                confidence = 0.5
            
            # Consultar a los agentes relevantes
            agent_responses = await self._get_agent_responses(
                user_input=input_text,
                agent_ids=agent_ids,
                user_id=user_id,
                context=context
            )
            
            # Sintetizar respuestas
            synthesized_response, artifacts = await self._synthesize(
                user_input=input_text,
                agent_responses=agent_responses,
                context=context
            )
            
            # Actualizar contexto y persistir en StateManager
            await self._update_context(user_id, session_id, input_text, synthesized_response)
            
            # Construir respuesta final
            agents_consulted = [
                {"id": aid, "name": data["agent_name"]}
                for aid, data in agent_responses.items()
            ]
            
            # Actualizar estadísticas de uso de agentes
            if user_id:
                try:
                    # Obtener estadísticas actuales
                    stats = await self.state_manager.get_state_field(user_id, session_id, "agent_usage_stats") or {}
                    
                    # Actualizar estadísticas
                    for agent_id in agent_ids:
                        agent_name = self.agent_map.get(agent_id, {}).get("name", f"Agent-{agent_id}")
                        if agent_name not in stats:
                            stats[agent_name] = 0
                        stats[agent_name] += 1
                    
                    # Guardar estadísticas actualizadas
                    await self.state_manager.update_state_field(user_id, session_id, "agent_usage_stats", stats)
                    logger.debug(f"Estadísticas de uso de agentes actualizadas para session_id={session_id}")
                except Exception as e:
                    logger.warning(f"Error al actualizar estadísticas de uso de agentes: {e}")
            
            return {
                "response": synthesized_response,
                "session_id": session_id,
                "artifacts": artifacts,
                "metadata": {
                    "intent": primary_intent,
                    "agents_consulted": agents_consulted,
                    "processing_time": time.time() - start_time
                }
            }
            
        except Exception as e:
            logger.error(f"Error en el orquestador: {e}", exc_info=True)
            # Respuesta de error
            error_response = f"Lo siento, ha ocurrido un error al procesar tu solicitud. Por favor, inténtalo de nuevo más tarde."
            
            return {
                "response": error_response,
                "session_id": session_id,
                "metadata": {
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
            }

    # TODO: Mejorar análisis de intención con RAG consultando descripciones detalladas de agentes o ejemplos de interacciones previas.
    # TODO: Usar mcp8_think para razonar sobre qué combinación de agentes es óptima para consultas complejas.

    async def _get_agent_responses(self, user_input: str, agent_ids: List[int], user_id: Optional[str] = None, context: Dict[str, Any] = None) -> Dict[int, Dict[str, Any]]:
        """
        Obtiene respuestas de agentes especializados a través de A2A.
        
        Args:
            user_input: Texto de entrada del usuario
            agent_ids: Lista de IDs de agentes a consultar
            user_id: ID del usuario (opcional)
            context: Contexto adicional (opcional)
            
        Returns:
            Dict[int, Dict[str, Any]]: Respuestas de los agentes
        """
        # TODO: Enriquecer el contexto enviado a los agentes usando RAG sobre el perfil del usuario o historial NGX.
        # TODO: Usar mcp7_query para obtener datos relevantes adicionales del usuario desde Supabase antes de llamar a los agentes.
        tasks = {}
        responses = {}
        a2a_base_url = self.a2a_server_url.replace("ws://", "http://")
        
        for aid in agent_ids:
            agent_info = self.agent_map.get(aid, {"id": f"agent_{aid}", "name": f"Agente {aid}"})
            agent_id = agent_info["id"]
            agent_name = agent_info["name"]
            
            try:
                # Preparar contexto para la tarea
                task_context = {}
                if context:
                    task_context.update(context)
                if user_id:
                    task_context["user_id"] = user_id
                
                # Intentar solicitar respuesta a través de A2A
                task_request = {
                    "agent_id": agent_id,
                    "task": {
                        "input": user_input,
                        "context": task_context
                    }
                }
                
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.post(
                            f"{a2a_base_url}/agents/request", 
                            json=task_request,
                            timeout=10.0  # Aumentar timeout para dar más tiempo a los agentes
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            agent_response = result.get("response", "")
                            artifacts = result.get("artifacts", [])
                            
                            responses[aid] = {
                                "agent_name": agent_name,
                                "response": agent_response,
                                "artifacts": artifacts
                            }
                            continue
                    except (httpx.ConnectError, httpx.TimeoutException) as e:
                        logger.warning(f"Error de conexión A2A para {agent_id}: {e}")
                        # Si falla la conexión A2A, usar respuesta simulada
                        pass
                        
                # Si no se pudo obtener respuesta vía A2A, simular respuesta
                simulated_response = await self._simulate_agent_response(user_input, agent_name)
                responses[aid] = {
                    "agent_name": agent_name,
                    "response": simulated_response,
                    "artifacts": []
                }
                
            except Exception as e:
                logger.error(f"Error al obtener respuesta del agente {agent_id}: {e}")
                responses[aid] = {
                    "agent_name": agent_name,
                    "response": f"[Error al obtener respuesta del agente {agent_name}]",
                    "artifacts": []
                }
                
        return responses
        
    async def _synthesize(self, user_input: str, agent_responses: Dict[int, Dict[str, Any]], context: Dict[str, Any]) -> tuple[str, list]:
        """
        Sintetiza las respuestas de múltiples agentes en una única respuesta coherente.
        
        Args:
            user_input: Texto de entrada del usuario
            agent_responses: Respuestas de los agentes
            context: Contexto de la conversación
            
        Returns:
            tuple[str, list]: Respuesta sintetizada y lista de artefactos
        """
        # TODO: Mejorar la síntesis con RAG, consultando guías de estilo NGX o conocimiento general para enriquecer la respuesta final.
        # TODO: Usar mcp8_think para decidir cómo priorizar o combinar información conflictiva de diferentes agentes.
        # Preparar el prompt para la síntesis
        agent_responses_text = ""
        for agent_id, data in agent_responses.items():
            agent_responses_text += f"\n\n{data['agent_name']}:\n{data['response']}"
        
        # Incluir contexto de la conversación si está disponible
        conversation_history = ""
        if context and "history" in context and len(context["history"]) > 0:
            history = context["history"][-3:]  # Usar las últimas 3 interacciones
            conversation_history = "\n\nHistorial de conversación reciente:\n"
            for entry in history:
                conversation_history += f"Usuario: {entry['user']}\nAsistente: {entry['bot']}\n"
        
        synthesis_prompt = f"""
        Sintetiza las siguientes respuestas de agentes especializados en una única respuesta coherente
        que responda a la consulta del usuario. La respuesta debe ser clara, concisa y útil.
        
        Consulta del usuario: "{user_input}"{conversation_history}
        
        Respuestas de los agentes:{agent_responses_text}
        
        Respuesta sintetizada:
        """
        
        # Generar síntesis
        synthesized_response = await self.gemini_client.generate_response(synthesis_prompt, temperature=0.3)
        
        # Recopilar artefactos de todos los agentes
        artifacts = []
        for agent_id, data in agent_responses.items():
            if "artifacts" in data and data["artifacts"]:
                for artifact in data["artifacts"]:
                    # Añadir información del agente al artefacto
                    if isinstance(artifact, dict) and "metadata" not in artifact:
                        artifact["metadata"] = {"source_agent": data["agent_name"]}
                    artifacts.append(artifact)
        
        # Crear un artefacto de síntesis si hay múltiples agentes
        if len(agent_responses) > 1:
            synthesis_artifact = self.create_artifact(
                artifact_id=f"synthesis_{uuid.uuid4().hex[:8]}",
                artifact_type="synthesis",
                parts=[
                    self.create_data_part({
                        "query": user_input,
                        "agents_consulted": [data["agent_name"] for _, data in agent_responses.items()],
                        "synthesis": synthesized_response
                    })
                ]
            )
            artifacts.append(synthesis_artifact)
        
        return synthesized_response, artifacts

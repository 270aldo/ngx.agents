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

    def __init__(self, 
                 mcp_toolkit: Optional[MCPToolkit] = None,
                 a2a_server_url: Optional[str] = None, 
                 state_manager: Optional[StateManager] = None,
                 model: str = "gemini-1.5-flash", 
                 instruction: str = "Eres el orquestador principal de un sistema de IA multi-agente. Tu función es analizar la solicitud del usuario, coordinar con agentes especializados y sintetizar una respuesta completa.",
                 **kwargs):
        """
        Inicializa el orquestador de agentes NGX.
        
        Args:
            mcp_toolkit: Instancia de MCPToolkit (se pasará como adk_toolkit).
            a2a_server_url: URL del servidor A2A (opcional).
            state_manager: Gestor de estados para persistencia (opcional).
            model: Modelo LLM para usar en tareas de síntesis.
            instruction: Instrucción base para el agente ADK.
            **kwargs: Otros argumentos para las clases base.
        """
        agent_id_val = "ngx_nexus_orchestrator"
        name_val = "NGX_Nexus_Orchestrator"
        description_val = "Agente maestro que analiza las solicitudes, coordina con agentes especializados vía A2A y sintetiza una respuesta integral."
        
        capabilities_val = [
            "intent_analysis", "task_routing", "response_synthesis",
            "conversation_memory", "agent_coordination"
        ]
        
        google_adk_tools_val = [self._run_async_impl]
        
        a2a_skills_val = [
            {
                "name": "orchestrate_request", 
                "description": "Procesa una solicitud de usuario, la descompone, la enruta a agentes especializados y sintetiza una respuesta final.",
                "input_schema": {"input_text": "str", "user_id": "Optional[str]", "session_id": "Optional[str]"},
                "output_schema": {"status": "str", "response": "str", "error": "Optional[str]", "artifacts": "List[Dict]"}
            }
        ]
        
        actual_adk_toolkit = mcp_toolkit if mcp_toolkit is not None else MCPToolkit()

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
            **kwargs
        )
        
        self.gemini_client = GeminiClient() 
        self.mcp_client = MCPClient() 

        self.intent_to_agent_map = {
            "plan_entrenamiento": ["elite_training_strategist"],
            "analizar_rendimiento": ["elite_training_strategist", "progress_tracker"],
            "periodizacion": ["elite_training_strategist"],
            "prescribir_ejercicios": ["elite_training_strategist"],
            "plan_nutricional": ["precision_nutrition_architect"],
            "ajustar_dieta": ["precision_nutrition_architect"],
            "registrar_comida": ["precision_nutrition_architect", "progress_tracker"],
            "progreso_objetivos": ["progress_tracker", "client_success_liaison"],
            "soporte_cliente": ["client_success_liaison"],
            "feedback_general": ["client_success_liaison"],
            "consulta_general": ["elite_training_strategist", "precision_nutrition_architect", "progress_tracker"], 
            "saludo": ["client_success_liaison"], 
            "despedida": ["client_success_liaison"]
        }
        
        self.tracer = tracer
        self.request_counter = request_counter
        self.response_time_metric = response_time 

        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("Vertex AI SDK inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar Vertex AI SDK: {e}", exc_info=True)

        logger.info(f"{self.name} ({self.agent_id}) inicializado y listo para orquestar.")

    async def _run_async_impl(self, input_text: str, user_id: Optional[str] = None, 
                       session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Punto de entrada principal para el procesamiento de solicitudes del orquestador.
        Este método es la 'tool' principal registrada para google.adk.agents.Agent.
        Delega la lógica a _process_request.
        """
        if has_telemetry and self.request_counter:
            self.request_counter.add(1, { "agent.name": self.name })
        
        start_time_telemetry = time.monotonic()
        try:
            return await self._process_request(input_text, user_id, session_id, **kwargs)
        finally:
            if has_telemetry and self.response_time_metric:
                duration = time.monotonic() - start_time_telemetry
                self.response_time_metric.record(duration, { "agent.name": self.name })

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
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.debug(f"Generando nuevo session_id: {session_id}")
        
        logger.info(f"Orquestador procesando entrada: '{input_text[:50]}...' (user_id={user_id}, session_id={session_id})")
        
        try:
            context = await self._get_context(user_id, session_id)
            
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
            
            intent_analysis = await self.execute_skill("analyze_intent", prompt=intent_analysis_prompt)
            
            try:
                import re
                json_match = re.search(r'{.*}', intent_analysis, re.DOTALL)
                if json_match:
                    intent_data = json.loads(json_match.group(0))
                else:
                    intent_data = {
                        "primary_intent": "general",
                        "secondary_intents": [],
                        "confidence": 0.5
                    }
                
                primary_intent = intent_data.get("primary_intent", "general").lower()
                secondary_intents = [intent.lower() for intent in intent_data.get("secondary_intents", [])]
                confidence = intent_data.get("confidence", 0.5)
                
                agent_ids_set = set()
                
                if primary_intent in self.intent_to_agent_map:
                    for agent_id in self.intent_to_agent_map[primary_intent]:
                        agent_ids_set.add(agent_id)
                
                for intent in secondary_intents:
                    if intent in self.intent_to_agent_map:
                        for agent_id in self.intent_to_agent_map[intent]:
                            agent_ids_set.add(agent_id)
                
                if not agent_ids_set and "general" in self.intent_to_agent_map:
                    for agent_id in self.intent_to_agent_map["general"]:
                        agent_ids_set.add(agent_id)
                
                agent_ids = list(agent_ids_set) or [1]  
                
                logger.info(f"Intención detectada: {primary_intent} (confianza: {confidence}), consultando agentes: {agent_ids}")
            except Exception as e:
                logger.error(f"Error al parsear análisis de intención: {e}")
                agent_ids = [1]
                primary_intent = "general"
                confidence = 0.5
            
            agent_responses = await self._get_agent_responses(
                user_input=input_text,
                agent_ids=agent_ids,
                user_id=user_id,
                context=context
            )
            
            synthesized_response, artifacts = await self._synthesize(
                user_input=input_text,
                agent_responses=agent_responses,
                context=context
            )
            
            await self._update_context(user_id, session_id, input_text, synthesized_response)
            
            agents_consulted = [
                {"id": aid, "name": data["agent_name"]}
                for aid, data in agent_responses.items()
            ]
            
            if user_id:
                try:
                    stats = await self.state_manager.get_state_field(user_id, session_id, "agent_usage_stats") or {}
                    
                    for agent_id_stat in agent_ids: # Renombrar agent_id para evitar conflicto con el del bucle exterior si lo hubiera
                        agent_info = self.registered_agents.get(str(agent_id_stat), {}) # Asegurar que agent_id_stat sea string
                        agent_name = agent_info.get("name", str(agent_id_stat)) # Usar el ID como fallback
                        if agent_name not in stats:
                            stats[agent_name] = 0
                        stats[agent_name] += 1
                    
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
            error_response = f"Lo siento, ha ocurrido un error al procesar tu solicitud. Por favor, inténtalo de nuevo más tarde."
            
            return {
                "response": error_response,
                "session_id": session_id,
                "metadata": {
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
            }

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
        tasks = {}
        responses = {}
        a2a_base_url = self.a2a_server_url.replace("ws://", "http://")
        
        for aid in agent_ids:
            agent_info = self.registered_agents.get(str(aid), {}) # Asegurar que aid sea string
            agent_id = agent_info.get("id", str(aid)) # Usar el ID como fallback
            agent_name = agent_info.get("name", str(aid)) # Usar el ID como fallback
            
            try:
                task_context = {}
                if context:
                    task_context.update(context)
                if user_id:
                    task_context["user_id"] = user_id
                
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
                            timeout=10.0  
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
                        pass
                        
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
        agent_responses_text = ""
        for agent_id, data in agent_responses.items():
            agent_responses_text += f"\n\n{data['agent_name']}:\n{data['response']}"
        
        conversation_history = ""
        if context and "history" in context and len(context["history"]) > 0:
            history = context["history"][-3:]  
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
        
        synthesized_response = await self.gemini_client.generate_response(synthesis_prompt, temperature=0.3)
        
        artifacts = []
        for agent_id, data in agent_responses.items():
            if "artifacts" in data and data["artifacts"]:
                for artifact in data["artifacts"]:
                    artifact["metadata"] = {"source_agent": data["agent_name"]}
                    artifacts.append(artifact)
        
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

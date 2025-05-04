import logging
import json
import httpx
import uuid
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Callable

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

    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()
        
    async def _register_skills(self):
        """
        Registra las skills del orquestador en el toolkit.
        """
        # Registrar skill para analizar intenciones
        async def analyze_intent(prompt: str, temperature: float = 0.1) -> str:
            response = await self.gemini_client.generate_response(prompt, temperature=temperature)
            return response
        await self.register_skill("analyze_intent", analyze_intent)
        
        # Registrar skill para enrutar tareas a agentes especializados
        async def route_task(task: Dict[str, Any]) -> Dict[str, Any]:
            # Validar tarea
            if not validate_task(task):
                return create_result(
                    task_id=task.get("task_id", str(uuid.uuid4())),
                    agent_id=self.agent_id,
                    status="error",
                    data={"response": "Tarea inválida"},
                    error={"code": "invalid_task", "message": "La tarea no cumple con el esquema requerido"}
                )
                
            # Analizar intención para determinar agente destino
            input_text = task.get("data", {}).get("input_text", "")
            intent_analysis_prompt = f"""
            Analiza la siguiente consulta y determina qué agente especializado debería responderla.
            Consulta: "{input_text}"
            
            Responde con un JSON que contenga:
            1. "agent_id": ID del agente que debería responder
            2. "confidence": Nivel de confianza en la asignación (0.0-1.0)
            
            Agentes disponibles:
            - elite_training_strategist: Entrenamiento y periodización
            - precision_nutrition_architect: Nutrición y dieta
            - recovery_corrective: Recuperación y corrección
            - biohacking_innovator: Biohacking y optimización
            - motivation_behavior_coach: Motivación y comportamiento
            - progress_tracker: Seguimiento de progreso
            - biometrics_insight_engine: Análisis de biométricas
            - gemini_training_assistant: Asistente general de entrenamiento
            """
            
            # Usar la skill de análisis de intención
            intent_analysis = await self.execute_skill("analyze_intent", prompt=intent_analysis_prompt)
            
            # Extraer agente destino
            try:
                import re
                json_match = re.search(r'{.*}', intent_analysis, re.DOTALL)
                if json_match:
                    intent_data = json.loads(json_match.group(0))
                    target_agent_id = intent_data.get("agent_id", "gemini_training_assistant")
                else:
                    target_agent_id = "gemini_training_assistant"
            except Exception:
                target_agent_id = "gemini_training_assistant"
                
            # Crear nueva tarea para el agente destino
            routed_task = create_task(
                agent_id=self.agent_id,
                action=task.get("action", "process_input"),
                data=task.get("data", {}),
                task_id=task.get("task_id", str(uuid.uuid4())),
                target_agent_id=target_agent_id,
                metadata={"original_task": task, "router": self.agent_id}
            )
            
            # Enviar tarea al agente destino
            try:
                result = await self.send_task_to_agent(target_agent_id, routed_task)
                return result
            except Exception as e:
                logger.error(f"Error al enviar tarea a {target_agent_id}: {e}")
                return create_result(
                    task_id=task.get("task_id", str(uuid.uuid4())),
                    agent_id=self.agent_id,
                    status="error",
                    data={"response": f"Error al enrutar tarea: {str(e)}"},
                    error={"code": "routing_error", "message": str(e)}
                )
        await self.register_skill("route_task", route_task)
        
        # Registrar skill para sintetizar respuestas
        async def synthesize_responses(responses: List[Dict[str, Any]], query: str) -> str:
            synthesized, _ = await self._synthesize(query, {i: resp for i, resp in enumerate(responses)}, {})
            return synthesized
        await self.register_skill("synthesize_responses", synthesize_responses)
    
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
            
            logger.info(f"Orchestrator processing input: {user_input}")
            conversation_context = self._get_context(user_id, session_id)

            # Determinar agentes basado en el análisis de intención
            intent = await self.gemini_client.analyze_intent(user_input)
            agent_ids = intent.get("agents", [1]) if isinstance(intent, dict) else [1]

            # Obtener respuestas de agentes especializados
            responses = await self._get_agent_responses(user_input, agent_ids, user_id, context)

            # Sintetizar respuesta final
            final_response, artifacts = await self._synthesize(user_input, responses, conversation_context)

            # Registrar interacción
            if user_id:
                self.supabase_client.log_interaction(user_id, self.agent_id, user_input, final_response)

            # Actualizar contexto
            self._update_context(user_id, session_id, user_input, final_response)
            
            # Interactuar con MCPClient si hay ID de usuario
            if user_id:
                await self.mcp_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=user_input,
                    response=final_response
                )
                logger.info("Interacción con MCPClient registrada")
            
            # Crear mensaje de respuesta
            response_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(final_response)
                ]
            )
            
            # Devolver respuesta estructurada según el protocolo A2A
            return {
                "response": final_response,
                "message": response_message,
                "artifacts": artifacts,
                "agents_used": agent_ids
            }
            
        except Exception as e:
            logger.error(f"Error en Orchestrator: {e}")
            return {
                "error": str(e), 
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud."
            }

    async def process_message(self, from_agent: str, content: Dict[str, Any]) -> Any:
        """
        Procesa un mensaje recibido de otro agente.
        
        Args:
            from_agent: ID del agente que envió el mensaje
            content: Contenido del mensaje
            
        Returns:
            Any: Respuesta al mensaje
        """
        try:
            # Extraer información del mensaje
            message_text = content.get("text", "")
            context = content.get("context", {})
            
            # Generar respuesta basada en el contenido del mensaje
            prompt = f"""
            Has recibido un mensaje del agente {from_agent}:
            
            "{message_text}"
            
            Como orquestador, responde con instrucciones o información relevante para coordinar
            el trabajo de este agente con otros agentes del sistema.
            """
            
            response = await self.gemini_client.generate_response(prompt, temperature=0.7)
            
            # Crear mensaje de respuesta
            response_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(response)
                ]
            )
            
            return {
                "status": "success",
                "response": response,
                "message": response_message
            }
        except Exception as e:
            logger.error(f"Error al procesar mensaje de agente: {e}")
            return {"error": str(e)}

    # ---------------- Helpers -----------------
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
        
    async def _simulate_agent_response(self, user_input: str, agent_name: str) -> str:
        """
        Simula la respuesta de un agente especializado cuando A2A no está disponible.
        
        Args:
            user_input: Texto de entrada del usuario
            agent_name: Nombre del agente a simular
            
        Returns:
            str: Respuesta simulada del agente
        """
        prompt = f"""
        Actúa como el agente {agent_name} y responde a la siguiente consulta:
        
        "{user_input}"
        
        Responde con información relevante a tu especialidad.
        """
        
        return await self.gemini_client.generate_response(prompt, temperature=0.7)

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

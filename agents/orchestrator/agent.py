"""
Agente orquestador principal para NGX Nexus.

Este agente analiza la intención del usuario, enruta las solicitudes a agentes especializados
y sintetiza sus respuestas en una respuesta coherente. Implementa los protocolos oficiales
A2A y ADK para comunicación entre agentes.
"""
import logging
import json
import httpx
import uuid
import time
import asyncio
import os
from typing import Dict, Any, Optional, List, Tuple, Callable

from core.logging_config import get_logger
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from tools.mcp_toolkit import MCPToolkit
from agents.base.adk_agent import ADKAgent
from adk.agent import Skill
from adk.toolkit import Toolkit
from app.schemas.a2a import A2AProcessRequest, A2AResponse, A2ATaskContext
from config import settings

logger = get_logger(__name__)

class NGXNexusOrchestrator(ADKAgent):
    """
    Agente orquestador principal para NGX Nexus.
    
    Este agente analiza la intención del usuario, enruta las solicitudes a agentes especializados
    y sintetiza sus respuestas en una respuesta coherente. Implementa los protocolos oficiales
    A2A y ADK para comunicación entre agentes.
    """
    def __init__(
        self,
        mcp_toolkit: Optional[MCPToolkit] = None,
        a2a_server_url: Optional[str] = None,
        model: Optional[str] = None,
        instruction: Optional[str] = "Eres el orquestador principal de NGX Nexus. Tu función es analizar la solicitud del usuario, enrutarla a agentes especializados y sintetizar sus respuestas.",
        agent_id: str = "ngx_nexus_orchestrator",
        name: str = "NGX Nexus Orchestrator",
        description: str = "Orquesta las respuestas de múltiples agentes especializados.",
        version: str = "1.0.0",
        capabilities: Optional[List[str]] = None,
        **kwargs: Any
    ):
        _model = model or settings.ORCHESTRATOR_DEFAULT_MODEL_ID
        _mcp_toolkit = mcp_toolkit if mcp_toolkit is not None else MCPToolkit()
        _a2a_server_url = a2a_server_url or f"http://{settings.A2A_HOST}:{settings.A2A_PORT}"

        # Definir las skills antes de llamar al constructor de ADKAgent
        self.skills = [
            Skill(
                name="analyze_intent",
                description="Analiza la intención del usuario a partir de su entrada de texto.",
                handler=self._skill_analyze_intent
            ),
            Skill(
                name="synthesize_response",
                description="Sintetiza una respuesta coherente a partir de las respuestas de múltiples agentes.",
                handler=self._skill_synthesize_response
            )
        ]

        # Definir las capacidades del agente
        _capabilities = capabilities or [
            "analyze_user_intent",
            "route_to_specialized_agents",
            "synthesize_agent_responses",
            "manage_conversation_flow"
        ]

        # Crear un toolkit de ADK
        adk_toolkit = Toolkit()

        # Inicializar el agente ADK
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            model=_model,
            instruction=instruction,
            state_manager=None,  # Ya no usamos el state_manager original
            adk_toolkit=adk_toolkit,
            capabilities=_capabilities,
            a2a_server_url=_a2a_server_url,
            version=version,
            **kwargs
        )
        
        self.a2a_server_url = _a2a_server_url.rstrip('/')

        self.intent_to_agent_map: Dict[str, List[str]] = {
            "plan_entrenamiento": ["elite_training_strategist"],
            "elite_training_strategist": ["elite_training_strategist"],
            "generar_plan_entrenamiento": ["elite_training_strategist"],
            "consultar_ejercicio": ["exercise_expert"],
            "registrar_actividad": ["activity_logger"],
            "analizar_nutricion": ["nutrition_analyzer"],
            "recomendar_receta": ["recipe_suggester"],
            "wellbeing_coach": ["wellbeing_coach"],
            "hydration_coach": ["hydration_coach"],
            "sleep_coach": ["sleep_coach"],
            "general": ["wellbeing_coach"]
        }
        
        # Inicializar Vertex AI si es necesario
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            from google.cloud import aiplatform
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform (Vertex AI SDK) inicializado correctamente para el Orquestador.")
        except ImportError:
            logger.warning("Google Cloud AI Platform no está disponible. Algunas funcionalidades podrían estar limitadas.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform para el Orquestador: {e}", exc_info=True)
        
        # Inicializar procesadores de visión y multimodales
        try:
            from core.vision_processor import VisionProcessor
            from infrastructure.adapters.multimodal_adapter import MultimodalAdapter
            from infrastructure.adapters.vision_adapter import vision_adapter
            
            # Inicializar procesador de visión
            self.vision_processor = VisionProcessor()
            logger.info("Procesador de visión inicializado correctamente para el Orquestador")
            
            # Inicializar adaptador multimodal
            self.multimodal_adapter = MultimodalAdapter()
            logger.info("Adaptador multimodal inicializado correctamente para el Orquestador")
            
            # Marcar capacidades como disponibles
            self._vision_capabilities_available = True
            
            # Añadir capacidades de visión a la lista de capacidades
            _capabilities.extend([
                "process_visual_content",
                "analyze_multimodal_inputs",
                "coordinate_visual_analysis"
            ])
            
            # Añadir skills relacionadas con visión
            self.skills.extend([
                Skill(
                    name="analyze_visual_content",
                    description="Analiza contenido visual y coordina con agentes especializados para su procesamiento.",
                    handler=self._skill_analyze_visual_content
                ),
                Skill(
                    name="process_multimodal_input",
                    description="Procesa entradas multimodales (texto e imágenes) y coordina respuestas.",
                    handler=self._skill_process_multimodal_input
                )
            ])
            
            logger.info("Capacidades de visión añadidas al Orquestador")
        except ImportError as e:
            logger.warning(f"No se pudieron inicializar componentes para capacidades de visión: {e}")
            self._vision_capabilities_available = False
            logger.warning("El Orquestador funcionará sin capacidades de visión")
        except Exception as e:
            logger.error(f"Error al inicializar capacidades de visión para el Orquestador: {e}", exc_info=True)
            self._vision_capabilities_available = False
            logger.warning("El Orquestador funcionará sin capacidades de visión")
            
        logger.info(f"{self.name} ({self.agent_id}) inicializado con integración oficial de Google ADK.")

    async def _skill_analyze_visual_content(self, prompt: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Skill para analizar contenido visual y coordinar con agentes especializados.
        
        Args:
            prompt: El texto del usuario relacionado con el contenido visual.
            image_data: Los datos de la imagen en formato base64 o URL.
            
        Returns:
            Un diccionario con el análisis del contenido visual y los agentes recomendados.
        """
        try:
            # Verificar si las capacidades de visión están disponibles
            if not hasattr(self, '_vision_capabilities_available') or not self._vision_capabilities_available:
                logger.warning("Capacidades de visión no disponibles para el Orquestador")
                return {
                    "status": "error",
                    "message": "Capacidades de visión no disponibles",
                    "recommended_agents": ["elite_training_strategist", "biometrics_insight_engine"]
                }
            
            # Analizar la imagen utilizando el procesador de visión
            vision_result = await self.vision_processor.analyze_image(image_data)
            
            # Determinar qué agentes pueden manejar mejor este contenido visual
            image_description = vision_result.get("text", "")
            
            # Identificar posibles intenciones basadas en el contenido visual
            visual_intent_prompt = f"""
            Basándote en esta descripción de una imagen, identifica la intención principal y las posibles intenciones secundarias:
            
            {image_description}
            
            Devuelve un JSON con:
            - primary_intent: la intención principal
            - secondary_intents: lista de intenciones secundarias
            - confidence: nivel de confianza (0.0-1.0)
            """
            
            # Utilizar el adaptador del Intent Analyzer
            intent_analysis = await intent_analyzer_adapter.analyze_intent(visual_intent_prompt)
            
            # Determinar los agentes más adecuados según el contenido visual
            primary_intent = intent_analysis.get("primary_intent", "general").lower()
            secondary_intents = [intent.lower() for intent in intent_analysis.get("secondary_intents", [])]
            confidence = intent_analysis.get("confidence", 0.5)
            
            # Mapear intenciones a agentes
            agent_ids_set = set()
            if primary_intent in self.intent_to_agent_map:
                agent_ids_set.update(self.intent_to_agent_map[primary_intent])
            for intent_val in secondary_intents:
                if intent_val in self.intent_to_agent_map:
                    agent_ids_set.update(self.intent_to_agent_map[intent_val])
            
            # Si no se identificaron agentes específicos, usar agentes con capacidades visuales
            if not agent_ids_set:
                agent_ids_set.update(["elite_training_strategist", "biometrics_insight_engine", "progress_tracker"])
            
            return {
                "status": "success",
                "visual_analysis": image_description,
                "primary_intent": primary_intent,
                "secondary_intents": secondary_intents,
                "confidence": confidence,
                "recommended_agents": list(agent_ids_set)
            }
        except Exception as e:
            logger.error(f"Error en skill_analyze_visual_content: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error al analizar contenido visual: {str(e)}",
                "recommended_agents": ["elite_training_strategist", "biometrics_insight_engine"]
            }
    
    async def _skill_process_multimodal_input(self, prompt: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Skill para procesar entradas multimodales (texto e imágenes) y coordinar respuestas.
        
        Args:
            prompt: El texto del usuario.
            image_data: Los datos de la imagen en formato base64 o URL.
            
        Returns:
            Un diccionario con el procesamiento multimodal y los agentes recomendados.
        """
        try:
            # Verificar si las capacidades multimodales están disponibles
            if not hasattr(self, '_vision_capabilities_available') or not self._vision_capabilities_available:
                logger.warning("Capacidades multimodales no disponibles para el Orquestador")
                return {
                    "status": "error",
                    "message": "Capacidades multimodales no disponibles",
                    "recommended_agents": ["elite_training_strategist", "biometrics_insight_engine"]
                }
            
            # Procesar la entrada multimodal
            multimodal_result = await self.multimodal_adapter.process_multimodal(
                prompt=f"Analiza esta imagen en el contexto de la siguiente consulta: {prompt}",
                image_data=image_data,
                temperature=0.2,
                max_output_tokens=1024
            )
            
            # Determinar qué agentes pueden manejar mejor esta entrada multimodal
            multimodal_analysis = multimodal_result.get("text", "")
            
            # Identificar posibles intenciones basadas en el análisis multimodal
            multimodal_intent_prompt = f"""
            Basándote en este análisis multimodal, identifica la intención principal y las posibles intenciones secundarias:
            
            Consulta del usuario: {prompt}
            
            Análisis multimodal: {multimodal_analysis}
            
            Devuelve un JSON con:
            - primary_intent: la intención principal
            - secondary_intents: lista de intenciones secundarias
            - confidence: nivel de confianza (0.0-1.0)
            """
            
            # Utilizar el adaptador del Intent Analyzer
            intent_analysis = await intent_analyzer_adapter.analyze_intent(multimodal_intent_prompt)
            
            # Determinar los agentes más adecuados según el análisis multimodal
            primary_intent = intent_analysis.get("primary_intent", "general").lower()
            secondary_intents = [intent.lower() for intent in intent_analysis.get("secondary_intents", [])]
            confidence = intent_analysis.get("confidence", 0.5)
            
            # Mapear intenciones a agentes
            agent_ids_set = set()
            if primary_intent in self.intent_to_agent_map:
                agent_ids_set.update(self.intent_to_agent_map[primary_intent])
            for intent_val in secondary_intents:
                if intent_val in self.intent_to_agent_map:
                    agent_ids_set.update(self.intent_to_agent_map[intent_val])
            
            # Si no se identificaron agentes específicos, usar agentes con capacidades multimodales
            if not agent_ids_set:
                agent_ids_set.update(["elite_training_strategist", "biometrics_insight_engine", "progress_tracker"])
            
            return {
                "status": "success",
                "multimodal_analysis": multimodal_analysis,
                "primary_intent": primary_intent,
                "secondary_intents": secondary_intents,
                "confidence": confidence,
                "recommended_agents": list(agent_ids_set)
            }
        except Exception as e:
            logger.error(f"Error en skill_process_multimodal_input: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error al procesar entrada multimodal: {str(e)}",
                "recommended_agents": ["elite_training_strategist", "biometrics_insight_engine"]
            }
    
    async def _skill_analyze_intent(self, prompt: str) -> Dict[str, Any]:
        """
        Skill para analizar la intención del usuario a partir de su entrada de texto.
        
        Args:
            prompt: El texto del usuario a analizar.
            
        Returns:
            Un diccionario con la intención primaria, intenciones secundarias y confianza.
        """
        try:
            # Utilizar el adaptador del Intent Analyzer
            intent_analysis = await intent_analyzer_adapter.analyze_intent(prompt)
            
            # Convertir el resultado al formato esperado por el orquestador
            result = {
                "primary_intent": intent_analysis.get("primary_intent", "general"),
                "secondary_intents": intent_analysis.get("secondary_intents", []),
                "confidence": intent_analysis.get("confidence", 0.5)
            }
            
            logger.debug(f"Análisis de intención para '{prompt[:30]}...': {result}")
            return result
        except Exception as e:
            logger.error(f"Error en skill_analyze_intent: {e}", exc_info=True)
            return {
                "primary_intent": "general",
                "secondary_intents": [],
                "confidence": 0.5,
                "error": str(e)
            }

    async def _skill_synthesize_response(self, prompt: str, agent_responses: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
        """
        Skill para sintetizar una respuesta coherente a partir de las respuestas de múltiples agentes.
        
        Args:
            prompt: El texto del usuario original.
            agent_responses: Las respuestas de los agentes consultados.
            
        Returns:
            Una respuesta sintetizada.
        """
        try:
            # Si no hay respuestas de agentes, devolver un mensaje genérico
            if not agent_responses:
                return "Lo siento, no tengo suficiente información para responder a tu consulta en este momento."
            
            # Aquí iría la lógica real de síntesis de respuestas
            # Por ahora, un ejemplo simple que concatena las respuestas
            synthesized_response = ""
            for agent_id, resp_data in agent_responses.items():
                if resp_data.get("status") == "success" and resp_data.get("output"):
                    synthesized_response += f"{resp_data.get('output')}\n\n"
            
            if not synthesized_response:
                return "Lo siento, los agentes consultados no pudieron proporcionar una respuesta clara en este momento."
            
            return synthesized_response.strip()
        except Exception as e:
            logger.error(f"Error en skill_synthesize_response: {e}", exc_info=True)
            return "Lo siento, tuve dificultades para consolidar la información. Por favor, intenta de nuevo."

    async def run(self, input_text: str, user_id: Optional[str] = None, 
                  session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta el agente orquestador utilizando la implementación de Google ADK.
        
        Este método sobrescribe el método run de ADKAgent para proporcionar
        la funcionalidad específica del orquestador.
        
        Args:
            input_text: El texto de entrada del usuario.
            user_id: El ID del usuario.
            session_id: El ID de la sesión.
            **kwargs: Argumentos adicionales.
            
        Returns:
            Un diccionario con la respuesta del orquestador.
        """
        start_time = time.time()
        try:
            result = await self._process_request(input_text, user_id, session_id, start_time=start_time, **kwargs)
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['processing_time'] = result['metadata'].get('processing_time', time.time() - start_time)
            return result
        except Exception as e:
            logger.error(f"Error crítico en run del orquestador: {e}", exc_info=True)
            return {
                "status": "error_orchestrator_critical",
                "response": "Lo siento, ocurrió un error crítico al procesar tu solicitud.",
                "session_id": session_id,
                "details": str(e),
                "agents_consulted": [],
                "artifacts": [],
                "metadata": {"processing_time": time.time() - start_time}
            }

    async def _process_request(self, input_text: str, user_id: Optional[str] = None, 
                               session_id: Optional[str] = None, start_time: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        if start_time is None:
            start_time = time.time()

        if not session_id:
            session_id = str(uuid.uuid4())
            logger.debug(f"Generando nuevo session_id: {session_id}")
        
        logger.info(f"Orquestador procesando entrada: '{input_text[:50]}...' (user_id={user_id}, session_id={session_id})")
        
        primary_intent = "general"
        confidence = 0.0

        try:
            context = await self._get_context(user_id, session_id)
            
            # Analizar la intención del usuario utilizando la skill de Google ADK
            intent_analysis_result = await self.adk_toolkit.execute_skill("analyze_intent", prompt=input_text)
            
            try:
                if isinstance(intent_analysis_result, str):
                    intent_data = json.loads(intent_analysis_result)
                else:
                    intent_data = intent_analysis_result
            except json.JSONDecodeError:
                logger.warning(f"No se pudo decodificar JSON del análisis de intención: {intent_analysis_result}. Usando fallback.")
                intent_data = {"primary_intent": "general", "confidence": 0.5}
            
            primary_intent = intent_data.get("primary_intent", "general").lower()
            secondary_intents = [intent.lower() for intent in intent_data.get("secondary_intents", [])]
            confidence = intent_data.get("confidence", 0.5)
            
            agent_ids_set = set()
            if primary_intent in self.intent_to_agent_map:
                agent_ids_set.update(self.intent_to_agent_map[primary_intent])
            for intent_val in secondary_intents:
                if intent_val in self.intent_to_agent_map:
                    agent_ids_set.update(self.intent_to_agent_map[intent_val])
            
            if not agent_ids_set and "general" in self.intent_to_agent_map:
                agent_ids_set.update(self.intent_to_agent_map["general"])
            
            agent_ids_to_call = list(agent_ids_set)
            
            if not agent_ids_to_call:
                no_agent_response = "Lo siento, no estoy seguro de cómo ayudarte con esa consulta específica. ¿Podrías reformularla o ser más específico sobre lo que necesitas?"
                await self._update_context(user_id, session_id, input_text, no_agent_response)
                return {
                    "status": "success_no_agent_found",
                    "response": no_agent_response,
                    "session_id": session_id,
                    "agents_consulted": [],
                    "artifacts": [],
                    "metadata": {
                        "intent": primary_intent,
                        "confidence": confidence,
                        "processing_time": time.time() - start_time
                    }
                }
            
            logger.info(f"Intención: {primary_intent}, confianza: {confidence}, agentes: {agent_ids_to_call}")
        except Exception as e:
            logger.error(f"Error en análisis de intención: {e}", exc_info=True)
            return {
                "status": "error_intent_analysis",
                "response": "Lo siento, tuve un problema al entender tu consulta. ¿Podrías intentar expresarla de otra manera?",
                "session_id": session_id,
                "details": str(e),
                "agents_consulted": [],
                "artifacts": [],
                "metadata": {"processing_time": time.time() - start_time}
            }
        
        agent_responses = await self._get_agent_responses(
            user_input=input_text, agent_ids=agent_ids_to_call, user_id=user_id, context=context, session_id=session_id
        )
        
        # Sintetizar la respuesta utilizando la skill de Google ADK
        synthesized_response = await self.adk_toolkit.execute_skill(
            "synthesize_response", prompt=input_text, agent_responses=agent_responses
        )
        
        # Extraer artefactos de las respuestas de los agentes
        artifacts = []
        for agent_id, resp_data in agent_responses.items():
            if resp_data.get("artifacts"):
                artifacts.extend(resp_data["artifacts"])
        
        await self._update_context(user_id, session_id, input_text, synthesized_response)
        
        agents_consulted_for_response = [
            {"id": aid, "name": data.get("agent_name", aid)}
            for aid, data in agent_responses.items()
        ]
        
        if user_id:
            try:
                # Cargar el estado actual
                state = await state_manager_adapter.load_state(user_id, session_id)
                if not state:
                    state = {}
                
                # Obtener o inicializar las estadísticas de uso de agentes
                stats = state.get("agent_usage_stats", {})
                
                # Actualizar las estadísticas
                for agent_data in agents_consulted_for_response:
                    stats[agent_data["name"]] = stats.get(agent_data["name"], 0) + 1
                
                # Actualizar el estado con las nuevas estadísticas
                state["agent_usage_stats"] = stats
                
                # Guardar el estado actualizado
                await state_manager_adapter.save_state(user_id, session_id, state)
            except Exception as e:
                logger.warning(f"Error al actualizar estadísticas en el adaptador del StateManager: {e}", exc_info=True)
        
        return {
            "status": "success", 
            "response": synthesized_response, 
            "session_id": session_id,
            "artifacts": artifacts, 
            "agents_consulted": agents_consulted_for_response,
            "metadata": {
                "intent": primary_intent, 
                "confidence": confidence, 
                "processing_time": time.time() - start_time
            }
        }

    async def _get_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
        if not user_id or not session_id:
            return {"history": []}
        try:
            # Cargar el estado desde el adaptador del State Manager
            state = await state_manager_adapter.load_state(user_id, session_id)
            if not state or "conversation_history" not in state:
                return {"history": []}
            
            # Convertir el formato del historial de conversación al formato esperado
            history = []
            for entry in state.get("conversation_history", []):
                if "role" in entry and "content" in entry:
                    if entry["role"] == "user":
                        history.append({"user_input": entry["content"]})
                    elif entry["role"] == "assistant":
                        history.append({"bot_response": entry["content"]})
            
            return {"history": history}
        except Exception as e:
            logger.error(f"Error al obtener contexto del adaptador del StateManager: {e}", exc_info=True)
            return {"history": []}

    async def _update_context(self, user_id: Optional[str], session_id: Optional[str], user_input: str, bot_response: str):
        if not user_id or not session_id:
            return
        try:
            # Cargar el estado actual
            state = await state_manager_adapter.load_state(user_id, session_id)
            if not state:
                state = {"conversation_history": []}
            
            # Asegurarse de que existe la lista de historial de conversación
            if "conversation_history" not in state:
                state["conversation_history"] = []
            
            # Añadir la nueva entrada de usuario
            state["conversation_history"].append({
                "role": "user",
                "content": user_input,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Añadir la nueva respuesta del bot
            state["conversation_history"].append({
                "role": "assistant",
                "content": bot_response,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Guardar el estado actualizado
            await state_manager_adapter.save_state(user_id, session_id, state)
        except Exception as e:
            logger.error(f"Error al actualizar contexto en el adaptador del StateManager: {e}", exc_info=True)

    async def _get_agent_responses(
        self,
        user_input: str,
        agent_ids: List[str],
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        agent_responses_map: Dict[str, Dict[str, Any]] = {}
        
        # Crear el contexto de la tarea
        task_context_data = A2ATaskContext(
            session_id=session_id, user_id=user_id, additional_context=context if context else {}
        )
        
        # Llamar a múltiples agentes en paralelo utilizando el adaptador de A2A
        try:
            logger.info(f"Orquestador llamando a {len(agent_ids)} agentes: {agent_ids}")
            responses = await a2a_adapter.call_multiple_agents(
                user_input=user_input,
                agent_ids=agent_ids,
                context=task_context_data
            )
            
            # Procesar las respuestas
            for agent_id, response in responses.items():
                if response.get("status") == "success":
                    agent_responses_map[agent_id] = {
                        "agent_id": response.get("agent_id", agent_id),
                        "agent_name": response.get("agent_name", agent_id),
                        "status": "success",
                        "output": response.get("output"),
                        "artifacts": response.get("artifacts", [])
                    }
                else:
                    agent_responses_map[agent_id] = {
                        "agent_id": agent_id,
                        "agent_name": agent_id,
                        "status": response.get("status", "error"),
                        "error": response.get("error", "Error desconocido"),
                        "output": response.get("output", "Error al procesar la solicitud."),
                        "artifacts": []
                    }
        except Exception as e:
            logger.error(f"Error al llamar a múltiples agentes: {e}", exc_info=True)
            for agent_id in agent_ids:
                agent_responses_map[agent_id] = {
                    "agent_id": agent_id,
                    "agent_name": agent_id,
                    "status": "error_communication",
                    "error": str(e),
                    "output": "Error de comunicación con el agente.",
                    "artifacts": []
                }
        
        return agent_responses_map

    # El método _make_a2a_call ha sido eliminado ya que el adaptador de A2A
    # se encarga de las llamadas HTTP a través del método call_agent y call_multiple_agents

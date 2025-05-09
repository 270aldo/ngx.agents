import logging
import json
import httpx
import uuid
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Callable

from core.logging_config import get_logger
from core.state_manager import StateManager
from agents.base.base_agent import BaseAgent
from agents.base.models import AgentResponse, Artifact, Skill
from app.schemas.a2a import A2AProcessRequest, A2AResponse, A2ATaskContext
from config import settings

logger = get_logger(__name__)

class NGXNexusOrchestrator(BaseAgent):
    def __init__(
        self,
        a2a_server_url: str,
        state_manager: StateManager,
        model: Optional[Any] = None,
        instruction: Optional[str] = "Eres el orquestador principal de NGX Nexus. Tu función es analizar la solicitud del usuario, enrutarla a agentes especializados y sintetizar sus respuestas.",
        agent_id: str = "ngx_nexus_orchestrator",
        name: str = "NGX Nexus Orchestrator",
        description: str = "Orquesta las respuestas de múltiples agentes especializados.",
        version: str = "1.0.0",
        capabilities: Optional[List[str]] = None,
        **kwargs: Any
    ):
        orchestrator_skills = [
            Skill(name="analyze_intent", description="Analiza la intención del usuario a partir de su entrada de texto.", parameters={}),
            Skill(name="synthesize_response", description="Sintetiza una respuesta coherente a partir de las respuestas de múltiples agentes.", parameters={})
        ]

        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            version=version,
            capabilities=capabilities or ["orchestration", "intent_analysis", "response_synthesis"],
            instruction=instruction,
            model=model,
            skills=orchestrator_skills,
            state_manager=state_manager,
            **kwargs
        )
        
        self.a2a_server_url = a2a_server_url.rstrip('/')

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
        
        if self.model is None:
            try:
                from core.llm_manager import LLMManager
                default_model_id = getattr(settings, "ORCHESTRATOR_DEFAULT_MODEL_ID", "gemini/gemini-1.5-flash-latest")
                self.model = LLMManager().get_model(default_model_id)
                logger.info(f"NGXNexusOrchestrator: Modelo LLM '{default_model_id}' cargado por defecto para skills internas.")
            except ImportError as e:
                logger.warning(f"NGXNexusOrchestrator: No se pudo importar LLMManager o cargar modelo por defecto: {e}. Las skills internas podrían no funcionar.")
            except Exception as e:
                logger.error(f"NGXNexusOrchestrator: Error al cargar el modelo LLM por defecto: {e}", exc_info=True)

    async def _run_async_impl(self, input_text: str, user_id: Optional[str] = None, 
                              session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        start_time = time.time()
        try:
            result = await self._process_request(input_text, user_id, session_id, start_time=start_time, **kwargs)
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['processing_time'] = result['metadata'].get('processing_time', time.time() - start_time)
            return result
        except Exception as e:
            logger.error(f"Error crítico en _run_async_impl del orquestador: {e}", exc_info=True)
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
            
            intent_analysis_prompt = f"""...""" # Prompt de análisis de intención omitido por brevedad
            intent_analysis_result = await self.execute_skill(skill_name="analyze_intent", prompt=intent_analysis_prompt)
            intent_analysis = intent_analysis_result.get("output", "") if isinstance(intent_analysis_result, dict) else str(intent_analysis_result)

            try:
                intent_data = json.loads(intent_analysis)
            except json.JSONDecodeError:
                logger.warning(f"No se pudo decodificar JSON del análisis de intención: {intent_analysis}. Usando fallback.")
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
                # ... (manejo de no encontrar agentes, omitido por brevedad) ...
                no_agent_response = "Lo siento, no estoy seguro de cómo ayudarte..."
                await self._update_context(user_id, session_id, input_text, no_agent_response)
                return { "status": "success_no_agent_found", "response": no_agent_response, # ... resto ... 
                       }
            
            logger.info(f"Intención: {primary_intent}, confianza: {confidence}, agentes: {agent_ids_to_call}")
        except Exception as e:
            # ... (manejo de error en análisis de intención, omitido por brevedad) ...
            return { "status": "error_intent_analysis", # ... resto ... 
                   }
        
        agent_responses = await self._get_agent_responses(
            user_input=input_text, agent_ids=agent_ids_to_call, user_id=user_id, context=context, session_id=session_id
        )
        
        synthesized_response, artifacts = await self._synthesize(
            user_input=input_text, agent_responses=agent_responses, context=context
        )
        
        await self._update_context(user_id, session_id, input_text, synthesized_response)
        
        agents_consulted_for_response = [
            {"id": aid, "name": data.get("agent_name", aid)}
            for aid, data in agent_responses.items()
        ]
        
        if user_id and self.state_manager:
            try:
                stats = await self.state_manager.get_state_field(user_id, session_id, "agent_usage_stats") or {}
                for agent_data in agents_consulted_for_response:
                    stats[agent_data["name"]] = stats.get(agent_data["name"], 0) + 1
                await self.state_manager.update_state_field(user_id, session_id, "agent_usage_stats", stats)
            except Exception as e:
                logger.warning(f"Error al actualizar estadísticas: {e}", exc_info=True)
        
        return {
            "status": "success", "response": synthesized_response, "session_id": session_id,
            "artifacts": artifacts, "agents_consulted": agents_consulted_for_response,
            "metadata": {"intent": primary_intent, "confidence": confidence, "processing_time": time.time() - start_time}
        }

    async def _get_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
        if not user_id or not session_id or not self.state_manager:
            return {"history": []}
        try:
            history = await self.state_manager.get_conversation_history(user_id, session_id)
            # Adaptar al formato esperado si es necesario, aunque get_conversation_history ya debería devolver List[Dict[str, str]]
            return {"history": history} # Ejemplo: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        except Exception as e:
            logger.error(f"Error al obtener contexto de StateManager: {e}", exc_info=True)
            return {"history": []}

    async def _update_context(self, user_id: Optional[str], session_id: Optional[str], user_input: str, bot_response: str):
        if not user_id or not session_id or not self.state_manager:
            return
        try:
            # Asumiendo que StateManager tiene un método para añadir al historial. 
            # La estructura de add_to_conversation_history debe ser user_input y luego bot_response.
            await self.state_manager.add_to_conversation_history(user_id, session_id, user_input, bot_response)
        except Exception as e:
            logger.error(f"Error al actualizar contexto en StateManager: {e}", exc_info=True)

    async def _get_agent_responses(
        self,
        user_input: str,
        agent_ids: List[str],
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        tasks = []
        a2a_base_url = self.a2a_server_url
        
        task_context_data = A2ATaskContext(
            session_id=session_id, user_id=user_id, additional_context=context if context else {}
        )
        process_request_payload_model = A2AProcessRequest(
            user_input=user_input, context=task_context_data
        )
        process_request_payload = process_request_payload_model.dict(exclude_none=True)

        async with httpx.AsyncClient() as client:
            for agent_path_id in agent_ids:
                request_url = f"{a2a_base_url}/a2a/{agent_path_id}/process"
                logger.debug(f"Orquestador llamando al agente {agent_path_id} en {request_url} con payload: {process_request_payload}")
                tasks.append(
                    self._make_a2a_call(client, request_url, process_request_payload, agent_path_id)
                )
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        agent_responses_map: Dict[str, Dict[str, Any]] = {}
        for i, result in enumerate(results):
            agent_id_called = agent_ids[i]
            if isinstance(result, Exception):
                logger.error(f"Error al contactar al agente {agent_id_called}: {result}")
                agent_responses_map[agent_id_called] = {
                    "agent_id": agent_id_called, "agent_name": agent_id_called,
                    "status": "error_communication", "error": str(result),
                    "output": "Error de comunicación con el agente.", "artifacts": []
                }
            elif isinstance(result, httpx.Response): # Chequeo explícito de tipo
                if result.status_code == 200:
                    try:
                        response_data = result.json()
                        agent_responses_map[agent_id_called] = {
                            "agent_id": response_data.get("agent_id", agent_id_called),
                            "agent_name": response_data.get("agent_name", agent_id_called),
                            "status": "success",
                            "output": response_data.get("output"),
                            "artifacts": response_data.get("artifacts", [])
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"Error al decodificar JSON del agente {agent_id_called}: {e}. Respuesta: {result.text}")
                        agent_responses_map[agent_id_called] = {
                            "agent_id": agent_id_called, "agent_name": agent_id_called,
                            "status": "error_response_format", "error": f"Respuesta JSON inválida: {e}",
                            "output": "El agente devolvió una respuesta mal formada.", "artifacts": []
                        }
                    except Exception as e: 
                        logger.error(f"Error al procesar la respuesta del agente {agent_id_called}: {e}. Respuesta: {result.text}")
                        agent_responses_map[agent_id_called] = {
                            "agent_id": agent_id_called, "agent_name": agent_id_called,
                            "status": "error_processing_response", "error": f"Error al procesar respuesta: {e}",
                            "output": "Error al procesar la respuesta del agente.", "artifacts": []
                        }
                else:
                    logger.error(f"Error del agente {agent_id_called} (status {result.status_code}): {result.text}")
                    agent_responses_map[agent_id_called] = {
                        "agent_id": agent_id_called, "agent_name": agent_id_called,
                        "status": f"error_http_{result.status_code}", "error": result.text,
                        "output": f"El agente devolvió un error HTTP {result.status_code}.", "artifacts": []
                    }
            else: # Caso inesperado donde result no es ni Exception ni httpx.Response
                logger.error(f"Resultado inesperado para el agente {agent_id_called}: {type(result)} - {str(result)}")
                agent_responses_map[agent_id_called] = {
                    "agent_id": agent_id_called, "agent_name": agent_id_called,
                    "status": "error_unknown_result_type", "error": "Tipo de resultado desconocido de la llamada A2A",
                    "output": "Error desconocido al contactar al agente.", "artifacts": []
                }
        return agent_responses_map

    async def _make_a2a_call(self, client: httpx.AsyncClient, url: str, payload: Dict[str, Any], agent_id: str) -> httpx.Response:
        try:
            response = await client.post(url, json=payload, timeout=settings.AGENT_TIMEOUT)
            return response
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout al llamar a {url} (agente {agent_id}): {e}")
            error_content = {"error": f"Timeout llamando al agente {agent_id}", "details": str(e), "agent_id": agent_id, "output": "El agente tardó demasiado en responder."}
            return httpx.Response(status_code=408, json=error_content)
        except httpx.RequestError as e:
            logger.warning(f"Error de red al llamar a {url} (agente {agent_id}): {e}")
            error_content = {"error": f"Error de red llamando al agente {agent_id}", "details": str(e), "agent_id": agent_id, "output": "Error de red al contactar al agente."}
            return httpx.Response(status_code=503, json=error_content)

    async def _synthesize(self, user_input: str, agent_responses: Dict[str, Dict[str, Any]], context: Dict[str, Any]) -> Tuple[str, List[Artifact]]:
        if not self.model:
            logger.warning("Orquestador: No hay modelo LLM para sintetizar respuestas. Devolviendo respuestas concatenadas como fallback.")
            # Fallback si no hay modelo para síntesis, simplemente concatena las respuestas directas válidas.
            final_response = ""
            all_artifacts: List[Artifact] = []
            for agent_id, resp_data in agent_responses.items():
                if resp_data.get("status") == "success" and resp_data.get("output"):
                    final_response += f"{resp_data.get('agent_name', agent_id)}: {resp_data['output']}\n"
                elif resp_data.get("output"):
                    final_response += f"{resp_data.get('agent_name', agent_id)} (error): {resp_data['output']}\n"
                
                if resp_data.get("artifacts"):
                    for art_data in resp_data["artifacts"]:
                        # Asegurarse de que el artifacto sea un dict antes de intentar crear el objeto Artifact
                        if isinstance(art_data, dict):
                            try:
                                all_artifacts.append(Artifact(**art_data))
                            except Exception as e: # pydantic.error_wrappers.ValidationError u otros
                                logger.warning(f"No se pudo crear Artifact desde {art_data} para {agent_id}: {e}")
                        elif isinstance(art_data, Artifact):
                             all_artifacts.append(art_data)
                        else:
                            logger.warning(f"Artefacto de formato inesperado {type(art_data)} de {agent_id}: {art_data}")

            return final_response.strip() if final_response else "No se pudo generar una respuesta consolidada.", all_artifacts

        # Construcción del prompt para el modelo LLM (skill 'synthesize_response')
        prompt_parts = [f"Consulta original del usuario: {user_input}"]
        
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context.get("history", [])])
        if history_str:
            prompt_parts.append(f"\nHistorial de conversación previo:\n{history_str}")
            
        prompt_parts.append("\nRespuestas de los agentes consultados:")
        
        valid_responses_count = 0
        for agent_id, data in agent_responses.items():
            agent_name = data.get("agent_name", agent_id)
            output = data.get("output", "Sin respuesta.")
            status = data.get("status", "unknown")
            if status == "success" and output != "Sin respuesta.":
                valid_responses_count += 1
            prompt_parts.append(f"- {agent_name} (ID: {agent_id}, Estado: {status}): {output}")

        if valid_responses_count == 0:
             logger.warning(f"Ningún agente dio una respuesta válida para sintetizar para la entrada: '{user_input[:50]}...'")
             return "Lo siento, los agentes consultados no pudieron proporcionar una respuesta clara en este momento. Por favor, intenta reformular tu pregunta o inténtalo de nuevo más tarde.", []

        prompt_parts.append(
            "\nInstrucción: Sintetiza estas respuestas en un mensaje único, coherente y útil para el usuario. "
            "Evita la redundancia. Si hay errores de algunos agentes, menciónalo sutilmente si es relevante, o ignóralo si la información principal es clara. "
            "No inventes información. Tu principal objetivo es satisfacer la consulta original del usuario de la manera más directa y completa posible."
            "No menciones que eres un orquestador ni que estas sintetizando respuestas de otros agentes, simplemente da la respuesta final."
        )
        
        synthesis_prompt = "\n".join(prompt_parts)
        
        logger.debug(f"Enviando al LLM para síntesis (skill 'synthesize_response'):\n{synthesis_prompt}")
        
        try:
            # Usar el método execute_skill heredado de BaseAgent
            # Este método internamente usa self.model y el nombre de la skill.
            synthesis_skill_result = await self.execute_skill(skill_name="synthesize_response", prompt=synthesis_prompt)
            
            # El resultado de execute_skill es un dict que puede contener 'output' y 'artifacts'
            # o simplemente el string de texto si la skill no produce artefactos o estructura compleja.
            if isinstance(synthesis_skill_result, dict):
                final_response_text = synthesis_skill_result.get("output", "No se pudo generar una respuesta final.")
                # Los artefactos de la síntesis podrían añadirse aquí si la skill los produce
                # Por ahora, asumimos que los artefactos principales vienen de los agentes individuales.
            elif isinstance(synthesis_skill_result, str):
                final_response_text = synthesis_skill_result
            else:
                logger.warning(f"Resultado inesperado de la skill de síntesis: {type(synthesis_skill_result)}")
                final_response_text = "Hubo un problema al generar la respuesta final."

        except Exception as e:
            logger.error(f"Error durante la síntesis con el LLM (skill 'synthesize_response'): {e}", exc_info=True)
            final_response_text = "Lo siento, tuve dificultades para consolidar la información. Por favor, intenta de nuevo."
        
        # Recolectar artefactos de todas las respuestas de los agentes
        all_artifacts: List[Artifact] = []
        for agent_id, resp_data in agent_responses.items():
            if resp_data.get("artifacts"):
                for art_data in resp_data["artifacts"]:
                    if isinstance(art_data, dict):
                        try:
                            all_artifacts.append(Artifact(**art_data))
                        except Exception as e:
                            logger.warning(f"No se pudo crear Artifact desde {art_data} para {agent_id} durante la síntesis final: {e}")
                    elif isinstance(art_data, Artifact):
                        all_artifacts.append(art_data)
                    else:
                        logger.warning(f"Artefacto de formato inesperado {type(art_data)} de {agent_id} durante la síntesis final: {art_data}")
                        
        return final_response_text, all_artifacts

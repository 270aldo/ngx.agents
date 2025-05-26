"""
Adaptador para el agente Orchestrator.

Este adaptador permite que el Orchestrator sea utilizado a través del sistema A2A optimizado,
manteniendo la compatibilidad con la implementación original pero aprovechando las mejoras
de rendimiento y capacidades del nuevo sistema.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple

from core.logging_config import get_logger
from agents.orchestrator.agent import NGXNexusOrchestrator
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from core.telemetry import telemetry
from app.schemas.a2a import A2ATaskContext
from infrastructure.a2a_optimized import MessagePriority
from clients.vertex_ai.client import VertexAIClient

logger = get_logger(__name__)


class OrchestratorAdapter(NGXNexusOrchestrator, BaseAgentAdapter):
    """
    Adaptador para el agente Orchestrator.

    Este adaptador extiende la clase original NGXNexusOrchestrator y sobrescribe
    los métodos necesarios para utilizar los componentes optimizados.
    """

    # Definición de prioridades para diferentes tipos de mensajes
    PRIORITY_LEVELS = {
        "emergency": MessagePriority.CRITICAL,
        "high": MessagePriority.HIGH,
        "normal": MessagePriority.NORMAL,
        "low": MessagePriority.LOW,
        "background": MessagePriority.LOW,
    }

    # Definición de tiempos de espera para diferentes prioridades (en segundos)
    TIMEOUT_BY_PRIORITY = {
        MessagePriority.CRITICAL: 30,
        MessagePriority.HIGH: 45,
        MessagePriority.NORMAL: 60,
        MessagePriority.LOW: 90,
    }

    def __init__(self, **kwargs):
        """
        Inicializa el adaptador del Orchestrator.

        Args:
            **kwargs: Argumentos adicionales para el constructor de NGXNexusOrchestrator.
        """
        super().__init__(**kwargs)

        # Inicializar el cliente de Vertex AI
        self.vertex_ai_client = VertexAIClient()

        # Inicializar métricas de telemetría
        self.metrics = {
            "messages_routed": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "average_response_time": 0,
            "total_response_time": 0,
            "agent_calls": {},
            "priority_distribution": {"critical": 0, "high": 0, "normal": 0, "low": 0},
        }

        # Configuración de clasificación específica para este agente
        self.fallback_keywords = [
            "orquestar",
            "orchestrate",
            "coordinar",
            "coordinate",
            "múltiples",
            "multiple",
            "agentes",
            "agents",
            "integrar",
            "integrate",
            "combinar",
            "combine",
        ]

        logger.info(f"Adaptador del Orchestrator inicializado: {self.agent_id}")

    async def initialize(self) -> bool:
        """
        Inicializa el adaptador y registra el agente con el servidor A2A.

        Returns:
            bool: True si la inicialización fue exitosa
        """
        try:
            # Registrar el agente con el servidor A2A
            await self._register_with_a2a_server()

            # Inicializar componentes
            await intent_analyzer_adapter.initialize()
            await state_manager_adapter.initialize()

            logger.info(
                f"Adaptador del Orchestrator inicializado correctamente: {self.agent_id}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error al inicializar el adaptador del Orchestrator: {e}",
                exc_info=True,
            )
            return False

    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente Orchestrator.

        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "agent_interactions": [],
            "routing_decisions": [],
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para Orchestrator.

        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "route_message": "route_message",
            "coordinate_agents": "coordinate_agents",
            "aggregate_responses": "aggregate_responses",
            "prioritize_message": "prioritize_message",
            "analyze_intent": "analyze_intent",
        }

    def _adjust_score_based_on_context(
        self, score: float, context: Dict[str, Any]
    ) -> float:
        """
        Ajusta la puntuación de clasificación basada en el contexto.

        Args:
            score: Puntuación de clasificación original
            context: Contexto adicional para la clasificación

        Returns:
            float: Puntuación ajustada
        """
        # El Orchestrator siempre debe tener una puntuación base alta ya que es el coordinador principal
        base_score = max(0.3, score)

        # Si la consulta menciona múltiples agentes o coordinación, aumentar la puntuación
        if context.get("requires_coordination", False):
            base_score += 0.2

        # Si hay interacciones previas con múltiples agentes, aumentar la puntuación
        if len(context.get("agent_interactions", [])) > 2:
            base_score += 0.1

        # Limitar la puntuación máxima a 1.0
        return min(1.0, base_score)

    async def _process_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        program_type: str,
        state: Dict[str, Any],
        profile: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario.

        Este método implementa la lógica específica del Orchestrator utilizando la funcionalidad
        de la clase base BaseAgentAdapter.

        Args:
            query: La consulta del usuario
            user_id: ID del usuario
            session_id: ID de la sesión
            program_type: Tipo de programa (general, elite, etc.)
            state: Estado actual del usuario
            profile: Perfil del usuario
            **kwargs: Argumentos adicionales

        Returns:
            Dict[str, Any]: Respuesta del agente
        """
        try:
            with telemetry.start_span("orchestrator.process_query"):
                # Analizar la intención del usuario
                intent = await self._analyze_intent(query, state)

                # Determinar los agentes objetivo y prioridades
                target_agents, priority = await self._determine_target_agents(
                    intent, query, state
                )

                # Registrar la distribución de prioridades
                priority_name = self._get_priority_name(priority)
                self.metrics["priority_distribution"][priority_name] += 1

                # Enrutar el mensaje a los agentes objetivo
                start_time = time.time()
                response = await self._route_message(
                    query, target_agents, priority, user_id, session_id, state
                )
                end_time = time.time()

                # Actualizar métricas
                self._update_metrics(target_agents, end_time - start_time)

                # Registrar telemetría
                telemetry.record_event(
                    "orchestrator",
                    "message_routed",
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "target_agents": target_agents,
                        "priority": priority_name,
                        "response_time_ms": telemetry.get_current_span().duration_ms,
                    },
                )

                # Actualizar el estado con la información de enrutamiento
                if "routing_decisions" not in state:
                    state["routing_decisions"] = []

                state["routing_decisions"].append(
                    {
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": query,
                        "target_agents": target_agents,
                        "priority": priority_name,
                        "response_time": end_time - start_time,
                    }
                )

                return response
        except Exception as e:
            logger.error(f"Error en _process_query: {e}", exc_info=True)
            telemetry.record_error(
                "orchestrator",
                "process_query_failed",
                {"error": str(e), "user_id": user_id, "session_id": session_id},
            )
            return {
                "status": "error",
                "error": str(e),
                "output": "Lo siento, ha ocurrido un error al procesar tu solicitud.",
                "agent": self.__class__.__name__,
            }

    async def _run_async_impl(
        self,
        user_input: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Implementación asíncrona del método run que utiliza los componentes optimizados.

        Este método sobrescribe el método _run_async_impl de la clase base para utilizar
        los adaptadores de los componentes optimizados.

        Args:
            user_input: El texto de entrada del usuario.
            user_id: El ID del usuario.
            session_id: El ID de la sesión.
            **kwargs: Argumentos adicionales.

        Returns:
            Un diccionario con la respuesta del orquestador.
        """
        try:
            with telemetry.start_span("orchestrator.run"):
                # Obtener el contexto de la conversación
                context = kwargs.get("context", {})

                # Analizar la intención del usuario
                intent = await self._analyze_intent(user_input, context)

                # Determinar los agentes objetivo y prioridades
                target_agents, priority = await self._determine_target_agents(
                    intent, user_input, context
                )

                # Registrar la distribución de prioridades
                priority_name = self._get_priority_name(priority)
                self.metrics["priority_distribution"][priority_name] += 1

                # Enrutar el mensaje a los agentes objetivo
                start_time = time.time()
                response = await self._route_message(
                    user_input, target_agents, priority, user_id, session_id, context
                )
                end_time = time.time()

                # Actualizar métricas
                self._update_metrics(target_agents, end_time - start_time)

                # Registrar telemetría
                telemetry.record_event(
                    "orchestrator",
                    "message_routed",
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "target_agents": target_agents,
                        "priority": priority_name,
                        "response_time_ms": telemetry.get_current_span().duration_ms,
                    },
                )

                return response
        except Exception as e:
            logger.error(f"Error en _run_async_impl: {e}", exc_info=True)
            telemetry.record_error(
                "orchestrator",
                "run_failed",
                {"error": str(e), "user_id": user_id, "session_id": session_id},
            )
            return {
                "status": "error",
                "error": str(e),
                "output": "Lo siento, ha ocurrido un error al procesar tu solicitud.",
            }

    async def _analyze_intent(
        self, user_input: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analiza la intención del usuario utilizando el adaptador del Intent Analyzer optimizado.

        Args:
            user_input: El texto de entrada del usuario.
            context: Contexto adicional para el análisis.

        Returns:
            Dict[str, Any]: La intención analizada.
        """
        try:
            with telemetry.start_span("orchestrator.analyze_intent"):
                # Utilizar el adaptador del Intent Analyzer
                intent = await intent_analyzer_adapter.analyze(user_input, context)

                # Registrar telemetría
                telemetry.record_event(
                    "orchestrator",
                    "intent_analyzed",
                    {
                        "intent_type": intent.get("type", "unknown"),
                        "confidence": intent.get("confidence", 0),
                        "response_time_ms": telemetry.get_current_span().duration_ms,
                    },
                )

                return intent
        except Exception as e:
            logger.error(f"Error al analizar la intención: {e}", exc_info=True)
            telemetry.record_error(
                "orchestrator", "intent_analysis_failed", {"error": str(e)}
            )
            # Devolver una intención por defecto en caso de error
            return {
                "type": "unknown",
                "confidence": 0.0,
                "entities": [],
                "target_agents": ["fallback_agent"],
            }

    async def _determine_target_agents(
        self, intent: Dict[str, Any], user_input: str, context: Dict[str, Any]
    ) -> Tuple[List[str], MessagePriority]:
        """
        Determina los agentes objetivo y la prioridad del mensaje basado en la intención.

        Args:
            intent: La intención analizada.
            user_input: El texto de entrada del usuario.
            context: Contexto adicional.

        Returns:
            Tuple[List[str], MessagePriority]: Lista de agentes objetivo y prioridad del mensaje.
        """
        try:
            with telemetry.start_span("orchestrator.determine_target_agents"):
                # Obtener los agentes objetivo de la intención
                target_agents = intent.get("target_agents", [])

                # Si no hay agentes objetivo, utilizar un agente por defecto
                if not target_agents:
                    target_agents = ["fallback_agent"]

                # Determinar la prioridad del mensaje
                priority_str = intent.get("priority", "normal").lower()
                priority = self.PRIORITY_LEVELS.get(
                    priority_str, MessagePriority.NORMAL
                )

                # Optimización: Ajustar la prioridad basada en palabras clave de emergencia
                emergency_keywords = [
                    "emergencia",
                    "urgente",
                    "crítico",
                    "inmediato",
                    "peligro",
                ]
                if any(keyword in user_input.lower() for keyword in emergency_keywords):
                    priority = MessagePriority.CRITICAL

                # Optimización: Ajustar la prioridad basada en el contexto
                if context.get("is_emergency", False):
                    priority = MessagePriority.CRITICAL
                elif context.get("is_important", False):
                    priority = MessagePriority.HIGH

                # Registrar telemetría
                telemetry.record_event(
                    "orchestrator",
                    "target_agents_determined",
                    {
                        "target_agents": target_agents,
                        "priority": self._get_priority_name(priority),
                        "response_time_ms": telemetry.get_current_span().duration_ms,
                    },
                )

                return target_agents, priority
        except Exception as e:
            logger.error(
                f"Error al determinar los agentes objetivo: {e}", exc_info=True
            )
            telemetry.record_error(
                "orchestrator", "target_determination_failed", {"error": str(e)}
            )
            # Devolver un agente por defecto y prioridad normal en caso de error
            return ["fallback_agent"], MessagePriority.NORMAL

    async def _route_message(
        self,
        user_input: str,
        target_agents: List[str],
        priority: MessagePriority,
        user_id: Optional[str],
        session_id: Optional[str],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enruta el mensaje a los agentes objetivo con la prioridad especificada.

        Args:
            user_input: El texto de entrada del usuario.
            target_agents: Lista de agentes objetivo.
            priority: Prioridad del mensaje.
            user_id: ID del usuario.
            session_id: ID de la sesión.
            context: Contexto adicional.

        Returns:
            Dict[str, Any]: Respuesta combinada de los agentes.
        """
        try:
            with telemetry.start_span("orchestrator.route_message"):
                # Incrementar el contador de mensajes enrutados
                self.metrics["messages_routed"] += 1

                # Crear el contexto de la tarea
                task_context_data = A2ATaskContext(
                    session_id=session_id, user_id=user_id, additional_context=context
                )

                # Determinar si se deben llamar a múltiples agentes en paralelo
                if len(target_agents) > 1:
                    # Llamar a múltiples agentes en paralelo
                    responses = await self._call_multiple_agents_parallel(
                        user_input=user_input,
                        agent_ids=target_agents,
                        priority=priority,
                        context=task_context_data,
                    )

                    # Combinar las respuestas
                    combined_response = self._combine_responses(
                        responses, target_agents
                    )

                    # Incrementar el contador de rutas exitosas
                    self.metrics["successful_routes"] += 1

                    return combined_response
                else:
                    # Llamar a un solo agente
                    agent_id = target_agents[0]

                    # Obtener el tiempo de espera basado en la prioridad
                    timeout = self.TIMEOUT_BY_PRIORITY.get(priority, 60)

                    # Llamar al agente con timeout
                    try:
                        response = await asyncio.wait_for(
                            self._consult_other_agent(
                                agent_id=agent_id,
                                query=user_input,
                                user_id=user_id,
                                session_id=session_id,
                                context=context,
                            ),
                            timeout=timeout,
                        )

                        # Incrementar el contador de rutas exitosas
                        self.metrics["successful_routes"] += 1

                        return response
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout al llamar al agente {agent_id}")
                        telemetry.record_error(
                            "orchestrator",
                            "agent_call_timeout",
                            {"agent_id": agent_id, "timeout": timeout},
                        )

                        # Incrementar el contador de rutas fallidas
                        self.metrics["failed_routes"] += 1

                        return {
                            "status": "error",
                            "error": f"Timeout al llamar al agente {agent_id}",
                            "output": f"Lo siento, el agente {agent_id} no respondió a tiempo.",
                        }
        except Exception as e:
            logger.error(f"Error al enrutar el mensaje: {e}", exc_info=True)
            telemetry.record_error(
                "orchestrator",
                "message_routing_failed",
                {"error": str(e), "target_agents": target_agents},
            )

            # Incrementar el contador de rutas fallidas
            self.metrics["failed_routes"] += 1

            return {
                "status": "error",
                "error": str(e),
                "output": "Lo siento, ha ocurrido un error al enrutar tu mensaje.",
            }

    async def _call_multiple_agents_parallel(
        self,
        user_input: str,
        agent_ids: List[str],
        priority: MessagePriority,
        context: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Llama a múltiples agentes en paralelo con la prioridad especificada.

        Args:
            user_input: El texto de entrada del usuario.
            agent_ids: Lista de IDs de los agentes a llamar.
            priority: Prioridad del mensaje.
            context: Contexto de la tarea.

        Returns:
            Dict[str, Dict[str, Any]]: Diccionario con las respuestas de cada agente.
        """
        try:
            with telemetry.start_span("orchestrator.call_multiple_agents"):
                # Obtener el tiempo de espera basado en la prioridad
                timeout = self.TIMEOUT_BY_PRIORITY.get(priority, 60)

                # Crear tareas para llamar a cada agente
                tasks = []
                for agent_id in agent_ids:
                    # Incrementar el contador de llamadas al agente
                    self.metrics["agent_calls"][agent_id] = (
                        self.metrics["agent_calls"].get(agent_id, 0) + 1
                    )

                    # Crear la tarea
                    task = asyncio.create_task(
                        self._safe_call_agent(
                            agent_id=agent_id,
                            query=user_input,
                            context=context,
                            timeout=timeout,
                        )
                    )
                    tasks.append((agent_id, task))

                # Esperar a que todas las tareas se completen
                responses = {}
                for agent_id, task in tasks:
                    try:
                        response = await task
                        responses[agent_id] = response
                    except Exception as e:
                        logger.error(
                            f"Error al llamar al agente {agent_id}: {e}", exc_info=True
                        )
                        responses[agent_id] = {
                            "status": "error",
                            "error": str(e),
                            "output": f"Error al llamar al agente {agent_id}.",
                            "agent_id": agent_id,
                        }

                # Registrar telemetría
                telemetry.record_event(
                    "orchestrator",
                    "multiple_agents_called",
                    {
                        "agent_count": len(agent_ids),
                        "success_count": sum(
                            1 for r in responses.values() if r.get("status") != "error"
                        ),
                        "error_count": sum(
                            1 for r in responses.values() if r.get("status") == "error"
                        ),
                        "response_time_ms": telemetry.get_current_span().duration_ms,
                    },
                )

                return responses
        except Exception as e:
            logger.error(f"Error al llamar a múltiples agentes: {e}", exc_info=True)
            telemetry.record_error(
                "orchestrator",
                "multiple_agents_call_failed",
                {"error": str(e), "agent_ids": agent_ids},
            )

            # Crear respuestas de error para todos los agentes
            return {
                agent_id: {
                    "status": "error",
                    "error": str(e),
                    "output": f"Error al llamar al agente {agent_id}.",
                    "agent_id": agent_id,
                }
                for agent_id in agent_ids
            }

    async def _safe_call_agent(
        self, agent_id: str, query: str, context: Dict[str, Any], timeout: int
    ) -> Dict[str, Any]:
        """
        Llama a un agente con manejo de errores y timeout.

        Args:
            agent_id: ID del agente a llamar.
            query: Consulta para el agente.
            context: Contexto de la tarea.
            timeout: Tiempo de espera en segundos.

        Returns:
            Dict[str, Any]: Respuesta del agente.
        """
        try:
            # Llamar al agente con timeout
            response = await asyncio.wait_for(
                a2a_adapter.call_agent(
                    agent_id=agent_id, user_input=query, context=context
                ),
                timeout=timeout,
            )

            return response
        except asyncio.TimeoutError:
            logger.error(f"Timeout al llamar al agente {agent_id}")
            telemetry.record_error(
                "orchestrator",
                "agent_call_timeout",
                {"agent_id": agent_id, "timeout": timeout},
            )

            return {
                "status": "error",
                "error": f"Timeout al llamar al agente {agent_id}",
                "output": f"El agente {agent_id} no respondió a tiempo.",
                "agent_id": agent_id,
            }
        except Exception as e:
            logger.error(f"Error al llamar al agente {agent_id}: {e}", exc_info=True)
            telemetry.record_error(
                "orchestrator",
                "agent_call_failed",
                {"agent_id": agent_id, "error": str(e)},
            )

            return {
                "status": "error",
                "error": str(e),
                "output": f"Error al llamar al agente {agent_id}: {str(e)}",
                "agent_id": agent_id,
            }

    def _combine_responses(
        self, responses: Dict[str, Dict[str, Any]], agent_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Combina las respuestas de múltiples agentes en una sola respuesta.

        Args:
            responses: Diccionario con las respuestas de cada agente.
            agent_ids: Lista de IDs de los agentes.

        Returns:
            Dict[str, Any]: Respuesta combinada.
        """
        try:
            with telemetry.start_span("orchestrator.combine_responses"):
                # Verificar si todas las respuestas son errores
                all_errors = all(
                    response.get("status") == "error" for response in responses.values()
                )
                if all_errors:
                    return {
                        "status": "error",
                        "error": "Todos los agentes fallaron",
                        "output": "Lo siento, todos los agentes fallaron al procesar tu solicitud.",
                        "agent_responses": responses,
                    }

                # Combinar las respuestas
                combined_output = ""
                for agent_id in agent_ids:
                    response = responses.get(agent_id, {})
                    output = response.get("output", "")
                    if output:
                        combined_output += f"\n\n{output}"

                # Eliminar espacios en blanco adicionales
                combined_output = combined_output.strip()

                # Crear la respuesta combinada
                combined_response = {
                    "status": "success",
                    "output": combined_output,
                    "agent_responses": responses,
                }

                # Registrar telemetría
                telemetry.record_event(
                    "orchestrator",
                    "responses_combined",
                    {
                        "agent_count": len(responses),
                        "output_length": len(combined_output),
                        "response_time_ms": telemetry.get_current_span().duration_ms,
                    },
                )

                return combined_response
        except Exception as e:
            logger.error(f"Error al combinar respuestas: {e}", exc_info=True)
            telemetry.record_error(
                "orchestrator", "response_combination_failed", {"error": str(e)}
            )

            return {
                "status": "error",
                "error": str(e),
                "output": "Lo siento, ha ocurrido un error al combinar las respuestas de los agentes.",
                "agent_responses": responses,
            }

    def _update_metrics(self, target_agents: List[str], response_time: float) -> None:
        """
        Actualiza las métricas de rendimiento.

        Args:
            target_agents: Lista de agentes objetivo.
            response_time: Tiempo de respuesta en segundos.
        """
        try:
            # Actualizar el tiempo de respuesta total
            self.metrics["total_response_time"] += response_time

            # Actualizar el tiempo de respuesta promedio
            self.metrics["average_response_time"] = (
                self.metrics["total_response_time"] / self.metrics["messages_routed"]
            )

            # Actualizar las métricas de telemetría
            telemetry.record_event(
                "orchestrator",
                "metrics_updated",
                {
                    "messages_routed": self.metrics["messages_routed"],
                    "successful_routes": self.metrics["successful_routes"],
                    "failed_routes": self.metrics["failed_routes"],
                    "average_response_time": self.metrics["average_response_time"],
                    "priority_distribution": self.metrics["priority_distribution"],
                },
            )
        except Exception as e:
            logger.error(f"Error al actualizar métricas: {e}", exc_info=True)

    def _get_priority_name(self, priority: MessagePriority) -> str:
        """
        Obtiene el nombre de la prioridad.

        Args:
            priority: Prioridad del mensaje.

        Returns:
            str: Nombre de la prioridad.
        """
        priority_names = {
            MessagePriority.CRITICAL: "critical",
            MessagePriority.HIGH: "high",
            MessagePriority.NORMAL: "normal",
            MessagePriority.LOW: "low",
        }
        return priority_names.get(priority, "normal")

    async def _consult_other_agent(
        self,
        agent_id: str,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Consulta a otro agente utilizando el adaptador A2A optimizado.

        Args:
            agent_id: El ID del agente a consultar.
            query: La consulta a enviar al agente.
            user_id: El ID del usuario.
            session_id: El ID de la sesión.
            context: Contexto adicional para la consulta.

        Returns:
            La respuesta del agente consultado.
        """
        try:
            with telemetry.start_span(f"orchestrator.consult_{agent_id}"):
                # Incrementar el contador de llamadas al agente
                self.metrics["agent_calls"][agent_id] = (
                    self.metrics["agent_calls"].get(agent_id, 0) + 1
                )

                # Crear el contexto de la tarea
                task_context = {}
                if context:
                    task_context = context.copy()

                if user_id:
                    task_context["user_id"] = user_id
                if session_id:
                    task_context["session_id"] = session_id

                # Llamar al agente utilizando el adaptador A2A
                response = await a2a_adapter.call_agent(
                    agent_id=agent_id, user_input=query, context=task_context
                )

                # Registrar telemetría
                telemetry.record_event(
                    "orchestrator",
                    "agent_consulted",
                    {
                        "agent_id": agent_id,
                        "response_status": response.get("status", "unknown"),
                        "response_time_ms": telemetry.get_current_span().duration_ms,
                    },
                )

                return response
        except Exception as e:
            logger.error(f"Error al consultar al agente {agent_id}: {e}", exc_info=True)
            telemetry.record_error(
                "orchestrator",
                "agent_consultation_failed",
                {"agent_id": agent_id, "error": str(e)},
            )

            return {
                "status": "error",
                "error": str(e),
                "output": f"Error al consultar al agente {agent_id}: {str(e)}",
                "agent_id": agent_id,
            }

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas de rendimiento del adaptador.

        Returns:
            Dict[str, Any]: Métricas de rendimiento
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "metrics": self.metrics,
        }

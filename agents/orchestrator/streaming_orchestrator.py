"""
Extensión del Orchestrator con capacidades de streaming para respuestas incrementales.

Este módulo extiende el NGXNexusOrchestrator con capacidades de streaming,
permitiendo generar respuestas incrementales para mejorar la experiencia del usuario.
"""

import asyncio
import json
import time
import uuid
from typing import AsyncGenerator, Dict, Any, Optional, List, Tuple

from core.logging_config import get_logger
from agents.orchestrator.agent import NGXNexusOrchestrator
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from app.schemas.a2a import A2ATaskContext

logger = get_logger(__name__)


class StreamingNGXNexusOrchestrator(NGXNexusOrchestrator):
    """
    Versión extendida del Orchestrator con capacidades de streaming.

    Esta clase añade métodos para generar respuestas incrementales,
    permitiendo una experiencia más fluida para el usuario.
    """

    def __init__(self, *args, **kwargs):
        """Inicializa el orchestrator con capacidades de streaming."""
        super().__init__(*args, **kwargs)
        self.streaming_enabled = True
        self.chunk_size = kwargs.get("chunk_size", 50)  # Tamaño de chunk en caracteres
        self.chunk_delay = kwargs.get(
            "chunk_delay", 0.05
        )  # Delay entre chunks en segundos

    async def stream_response(
        self,
        input_text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Genera una respuesta de streaming para la entrada del usuario.

        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario
            session_id: ID de la sesión
            **kwargs: Argumentos adicionales

        Yields:
            Diccionarios con chunks de respuesta y metadatos
        """
        start_time = time.time()

        if not session_id:
            session_id = str(uuid.uuid4())
            logger.debug(f"Generando nuevo session_id para streaming: {session_id}")

        logger.info(
            f"Iniciando streaming para: '{input_text[:50]}...' (user_id={user_id}, session_id={session_id})"
        )

        try:
            # Yield evento de inicio
            yield {"type": "start", "session_id": session_id, "timestamp": time.time()}

            # Obtener contexto
            context = await self._get_context(user_id, session_id)

            # Yield evento de análisis de intención
            yield {
                "type": "status",
                "status": "analyzing_intent",
                "message": "Analizando tu consulta...",
            }

            # Analizar intención
            intent_analysis = await self._analyze_intent_streaming(input_text)
            primary_intent = intent_analysis.get("primary_intent", "general")
            confidence = intent_analysis.get("confidence", 0.5)

            # Yield resultado del análisis
            yield {
                "type": "intent_analysis",
                "intent": primary_intent,
                "confidence": confidence,
                "message": f"Entiendo que necesitas ayuda con: {self._get_intent_description(primary_intent)}",
            }

            # Determinar agentes a consultar
            agent_ids = self._get_agents_for_intent(intent_analysis)

            if not agent_ids:
                yield {
                    "type": "error",
                    "message": "No pude identificar agentes apropiados para tu consulta.",
                }
                return

            # Yield información sobre agentes
            yield {
                "type": "agents_selected",
                "agents": agent_ids,
                "message": f"Consultando con {len(agent_ids)} especialista(s)...",
            }

            # Obtener respuestas de agentes con streaming
            async for agent_chunk in self._stream_agent_responses(
                input_text, agent_ids, user_id, context, session_id
            ):
                yield agent_chunk

            # Yield evento de finalización
            processing_time = time.time() - start_time
            yield {
                "type": "complete",
                "session_id": session_id,
                "processing_time": processing_time,
                "message": "Respuesta completada.",
            }

        except Exception as e:
            logger.error(f"Error en stream_response: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "message": "Ocurrió un error al procesar tu solicitud.",
            }

    async def _analyze_intent_streaming(self, input_text: str) -> Dict[str, Any]:
        """Analiza la intención con soporte para streaming."""
        try:
            intent_analysis = await intent_analyzer_adapter.analyze_intent(input_text)
            return {
                "primary_intent": intent_analysis.get("primary_intent", "general"),
                "secondary_intents": intent_analysis.get("secondary_intents", []),
                "confidence": intent_analysis.get("confidence", 0.5),
            }
        except Exception as e:
            logger.error(f"Error en análisis de intención: {e}", exc_info=True)
            return {
                "primary_intent": "general",
                "secondary_intents": [],
                "confidence": 0.5,
            }

    def _get_agents_for_intent(self, intent_analysis: Dict[str, Any]) -> List[str]:
        """Determina qué agentes consultar basándose en el análisis de intención."""
        primary_intent = intent_analysis.get("primary_intent", "general")
        secondary_intents = intent_analysis.get("secondary_intents", [])

        agent_ids_set = set()

        # Mapear intención primaria
        if primary_intent in self.intent_to_agent_map:
            agent_ids_set.update(self.intent_to_agent_map[primary_intent])

        # Mapear intenciones secundarias
        for intent in secondary_intents:
            if intent in self.intent_to_agent_map:
                agent_ids_set.update(self.intent_to_agent_map[intent])

        # Fallback a agentes generales
        if not agent_ids_set and "general" in self.intent_to_agent_map:
            agent_ids_set.update(self.intent_to_agent_map["general"])

        return list(agent_ids_set)

    def _get_intent_description(self, intent: str) -> str:
        """Obtiene una descripción legible de la intención."""
        intent_descriptions = {
            "plan_entrenamiento": "planificación de entrenamiento",
            "analizar_nutricion": "análisis nutricional",
            "registrar_actividad": "registro de actividades",
            "consultar_progreso": "consulta de progreso",
            "general": "consultas generales de bienestar",
            "biometrics": "análisis de datos biométricos",
            "recovery": "recuperación y prevención de lesiones",
            "motivation": "motivación y cambio de comportamiento",
        }
        return intent_descriptions.get(intent, intent)

    async def _stream_agent_responses(
        self,
        user_input: str,
        agent_ids: List[str],
        user_id: Optional[str],
        context: Dict[str, Any],
        session_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Obtiene respuestas de agentes con streaming.

        Yields:
            Chunks de respuesta de cada agente
        """
        task_context = A2ATaskContext(
            session_id=session_id, user_id=user_id, additional_context=context
        )

        # Para cada agente, simular streaming de respuesta
        for agent_id in agent_ids:
            try:
                yield {
                    "type": "agent_start",
                    "agent_id": agent_id,
                    "message": f"Consultando con {agent_id}...",
                }

                # Llamar al agente
                response = await a2a_adapter.call_agent(
                    agent_id=agent_id, user_input=user_input, context=task_context
                )

                if response.get("status") == "success":
                    output = response.get("output", "")

                    # Simular streaming del output del agente
                    async for chunk in self._stream_text(output, agent_id):
                        yield chunk

                    # Yield artefactos si existen
                    artifacts = response.get("artifacts", [])
                    if artifacts:
                        yield {
                            "type": "artifacts",
                            "agent_id": agent_id,
                            "artifacts": artifacts,
                        }
                else:
                    yield {
                        "type": "agent_error",
                        "agent_id": agent_id,
                        "error": response.get("error", "Error desconocido"),
                    }

            except Exception as e:
                logger.error(
                    f"Error al consultar agente {agent_id}: {e}", exc_info=True
                )
                yield {"type": "agent_error", "agent_id": agent_id, "error": str(e)}

    async def _stream_text(
        self, text: str, agent_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Convierte texto en chunks para streaming.

        Args:
            text: Texto a dividir en chunks
            agent_id: ID del agente que generó el texto

        Yields:
            Chunks de texto
        """
        # Dividir el texto en oraciones o chunks
        chunks = self._split_into_chunks(text)

        for i, chunk in enumerate(chunks):
            yield {
                "type": "content",
                "agent_id": agent_id,
                "content": chunk,
                "chunk_index": i,
                "is_final": i == len(chunks) - 1,
            }

            # Pequeño delay para simular procesamiento natural
            await asyncio.sleep(self.chunk_delay)

    def _split_into_chunks(self, text: str) -> List[str]:
        """
        Divide el texto en chunks inteligentes.

        Intenta dividir por oraciones completas cuando es posible,
        o por tamaño de chunk si las oraciones son muy largas.
        """
        import re

        # Primero intentar dividir por oraciones
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # Si la oración es muy larga, dividirla por tamaño
            if len(sentence) > self.chunk_size * 2:
                # Guardar el chunk actual si existe
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # Dividir la oración larga
                words = sentence.split()
                temp_chunk = ""

                for word in words:
                    if len(temp_chunk) + len(word) + 1 <= self.chunk_size:
                        temp_chunk += word + " "
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = word + " "

                if temp_chunk:
                    chunks.append(temp_chunk.strip())
            else:
                # Si añadir la oración no excede el tamaño del chunk
                if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                    current_chunk += sentence + " "
                else:
                    # Guardar el chunk actual y empezar uno nuevo
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "

        # Añadir el último chunk si existe
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    async def parallel_stream_response(
        self,
        input_text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Versión avanzada que consulta agentes en paralelo y mezcla sus respuestas.

        Esta versión es más eficiente pero requiere lógica adicional
        para sintetizar las respuestas en tiempo real.
        """
        # TODO: Implementar streaming paralelo de múltiples agentes
        # Esta es una versión más avanzada que se puede implementar después
        pass

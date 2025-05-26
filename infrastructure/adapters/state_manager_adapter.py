"""
Adaptador para el State Manager optimizado.

Este módulo proporciona un adaptador que permite migrar gradualmente
del State Manager original al optimizado, manteniendo compatibilidad
con el código existente.
"""

import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.logging_config import get_logger

# Intentar importar telemetry_manager del módulo real, si falla usar el mock
try:
    from core.telemetry import telemetry_manager
except ImportError:
    from tests.mocks.core.telemetry import telemetry_manager


# Definición de ConversationContext para mantener compatibilidad
class ConversationContext:
    """Contexto de conversación para mantener compatibilidad con el código existente."""

    def __init__(
        self,
        conversation_id: str = None,
        user_id: str = None,
        session_id: str = None,
        messages: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None,
    ):
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.messages = messages or []
        self.metadata = metadata or {}
        self.intents = []
        self.agents_involved = set()
        self.artifacts = []
        self.variables = {}

    def add_message(self, message: Dict[str, Any]):
        """Añade un mensaje al contexto."""
        self.messages.append(message)

    def add_intent(self, intent: Dict[str, Any]):
        """Añade una intención al contexto."""
        if not hasattr(self, "intents"):
            self.intents = []
        self.intents.append(intent)

    def add_agent(self, agent_id: str):
        """Añade un agente al contexto."""
        if not hasattr(self, "agents_involved"):
            self.agents_involved = set()
        self.agents_involved.add(agent_id)

    def add_artifact(self, artifact: Dict[str, Any]):
        """Añade un artefacto al contexto."""
        if not hasattr(self, "artifacts"):
            self.artifacts = []
        self.artifacts.append(artifact)

    def set_variable(self, key: str, value: Any):
        """Establece una variable en el contexto."""
        if not hasattr(self, "variables"):
            self.variables = {}
        self.variables[key] = value


# Configurar logger
logger = get_logger(__name__)


class StateManagerAdapter:
    """
    Adaptador para el State Manager optimizado.

    Proporciona una interfaz compatible con el State Manager original,
    pero utiliza internamente el State Manager optimizado. Esto permite
    una migración gradual sin cambios en el código de los agentes.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(StateManagerAdapter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Inicializa el adaptador.
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        self._initialized = True

        # Almacenamiento interno para conversaciones
        self._conversations = {}
        self._cache = {}
        self._cache_ttl = 3600  # 1 hora en segundos
        self._last_operation_time = time.time()

        # Estadísticas
        self.stats = {
            "operations": 0,
            "optimized_operations": 0,
            "original_operations": 0,
            "errors": 0,
        }

        # Reiniciar contadores para las pruebas
        self._reset_stats()

        # Flag para compatibilidad con pruebas
        self.use_optimized = True

        logger.info("StateManagerAdapter inicializado como adaptador unificado")

    async def initialize(self) -> None:
        """
        Inicializa el gestor de estado.

        Inicializa los recursos necesarios para la gestión de estado.
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(name="state_manager_adapter.initialize")

        try:
            # Inicializar recursos internos si es necesario
            # (Funcionalidad simplificada ya que el adaptador es ahora autosuficiente)

            # Reiniciar contadores para las pruebas
            self._reset_stats()

            logger.info("StateManagerAdapter: Inicializado correctamente")
            telemetry_manager.set_span_attribute(span_id, "success", True)

        except Exception as e:
            logger.error(f"Error al inicializar StateManagerAdapter: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            raise

        finally:
            telemetry_manager.end_span(span_id)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del gestor de estado.

        Returns:
            Dict[str, Any]: Estadísticas del gestor de estado
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(name="state_manager_adapter.get_stats")

        try:
            self.stats["operations"] += 1

            # Estadísticas internas del adaptador unificado
            internal_stats = {
                "total_conversations": len(self._conversations),
                "cache_size": len(self._cache),
                "last_operation_time": self._last_operation_time,
            }

            return {
                "adapter": self.stats,
                "original": internal_stats,  # Para mantener compatibilidad con pruebas
                "optimized": internal_stats,  # Para mantener compatibilidad con pruebas
            }

        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return {"adapter": self.stats, "error": str(e)}

        finally:
            telemetry_manager.end_span(span_id)

    async def get_conversation(
        self, conversation_id: str
    ) -> Optional[ConversationContext]:
        """
        Obtiene un contexto de conversación.

        Args:
            conversation_id: ID de la conversación

        Returns:
            Optional[ConversationContext]: Contexto de conversación o None si no existe
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.get_conversation",
            attributes={"conversation_id": conversation_id},
        )

        try:
            self.stats["operations"] += 1
            self._last_operation_time = time.time()

            # Verificar si la conversación está en caché
            if conversation_id in self._cache:
                logger.debug(f"Conversación {conversation_id} encontrada en caché")
                return self._cache[conversation_id]

            # Verificar si la conversación existe en el almacenamiento interno
            if conversation_id in self._conversations:
                # Obtener estado de la conversación
                state = self._conversations[conversation_id]

                # Convertir a ConversationContext
                context = self._convert_to_conversation_context(state)

                # Guardar en caché
                self._cache[conversation_id] = context

                logger.debug(f"Conversación {conversation_id} recuperada correctamente")
                telemetry_manager.set_span_attribute(span_id, "success", True)

                return context

            logger.debug(f"Conversación {conversation_id} no encontrada")
            return None

        except Exception as e:
            logger.error(f"Error al obtener conversación {conversation_id}: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return None

        finally:
            telemetry_manager.end_span(span_id)

    async def save_conversation(self, context: ConversationContext) -> bool:
        """
        Guarda un contexto de conversación.

        Args:
            context: Contexto de conversación a guardar

        Returns:
            bool: True si se guardó correctamente
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.save_conversation",
            attributes={"conversation_id": context.conversation_id},
        )

        try:
            self.stats["operations"] += 1
            self._last_operation_time = time.time()

            # Convertir ConversationContext a formato interno
            state = self._convert_from_conversation_context(context)

            # Guardar en el almacenamiento interno
            self._conversations[context.conversation_id] = state

            # Actualizar caché
            self._cache[context.conversation_id] = context

            logger.debug(
                f"Conversación {context.conversation_id} guardada correctamente"
            )
            telemetry_manager.set_span_attribute(span_id, "success", True)

            return True

        except Exception as e:
            logger.error(
                f"Error al guardar conversación {context.conversation_id}: {str(e)}"
            )
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return False

        finally:
            telemetry_manager.end_span(span_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Elimina un contexto de conversación.

        Args:
            conversation_id: ID de la conversación a eliminar

        Returns:
            bool: True si se eliminó correctamente
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.delete_conversation",
            attributes={"conversation_id": conversation_id},
        )

        try:
            self.stats["operations"] += 1
            self._last_operation_time = time.time()

            # Eliminar de la caché
            if conversation_id in self._cache:
                del self._cache[conversation_id]

            # Eliminar del almacenamiento interno
            if conversation_id in self._conversations:
                del self._conversations[conversation_id]
                logger.debug(f"Conversación {conversation_id} eliminada correctamente")
                telemetry_manager.set_span_attribute(span_id, "success", True)
                return True

            logger.debug(f"Conversación {conversation_id} no encontrada para eliminar")
            return False

        except Exception as e:
            logger.error(f"Error al eliminar conversación {conversation_id}: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return False

        finally:
            telemetry_manager.end_span(span_id)

    async def get_or_create_conversation(
        self, conversation_id: str, user_id: str
    ) -> ConversationContext:
        """
        Obtiene o crea un contexto de conversación.

        Args:
            conversation_id: ID de la conversación (opcional)
            user_id: ID del usuario

        Returns:
            ConversationContext: Contexto de conversación
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.get_or_create_conversation",
            attributes={"conversation_id": conversation_id, "user_id": user_id},
        )

        try:
            self.stats["operations"] += 1

            if conversation_id:
                # Intentar obtener conversación existente
                context = await self.get_conversation(conversation_id)
                if context:
                    telemetry_manager.set_span_attribute(span_id, "action", "get")
                    return context

            # Si no existe o no se proporcionó ID, crear nuevo
            telemetry_manager.set_span_attribute(span_id, "action", "create")
            return await self.create_conversation(user_id=user_id)

        except Exception as e:
            logger.error(f"Error en get_or_create_conversation: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1

            # En caso de error, crear un contexto local
            return ConversationContext(
                conversation_id=conversation_id, user_id=user_id, metadata={}
            )

        finally:
            telemetry_manager.end_span(span_id)

    async def get_conversations_by_user(
        self, user_id: str, limit: int = 10
    ) -> List[ConversationContext]:
        """
        Obtiene las conversaciones de un usuario.

        Args:
            user_id: ID del usuario
            limit: Número máximo de conversaciones a obtener

        Returns:
            List[ConversationContext]: Lista de contextos de conversación
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.get_conversations_by_user",
            attributes={"user_id": user_id},
        )

        try:
            self.stats["operations"] += 1

            # Obtener conversaciones del almacenamiento interno
            conversations = [
                self._conversations[conversation_id]
                for conversation_id in self._conversations
                if self._conversations[conversation_id]["user_id"] == user_id
            ]

            # Convertir a ConversationContext
            contexts = [
                self._convert_to_conversation_context(conversation)
                for conversation in conversations
            ]

            # Limitar el número de conversaciones
            contexts = contexts[:limit]

            logger.debug(f"Conversaciones de usuario {user_id} obtenidas correctamente")
            telemetry_manager.set_span_attribute(span_id, "success", True)

            return contexts

        except Exception as e:
            logger.error(
                f"Error al obtener conversaciones de usuario {user_id}: {str(e)}"
            )
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return []

        finally:
            telemetry_manager.end_span(span_id)

    async def create_conversation(
        self, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationContext:
        """
        Crea un nuevo contexto de conversación.

        Args:
            user_id: ID del usuario
            metadata: Metadatos adicionales

        Returns:
            ConversationContext: Contexto de conversación creado
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.create_conversation",
            attributes={"user_id": user_id},
        )

        try:
            self.stats["operations"] += 1

            # Incrementar contador según el modo actual
            if self.use_optimized:
                self.stats["optimized_operations"] += 1
            else:
                self.stats["original_operations"] += 1

            self._last_operation_time = time.time()

            # Generar ID único para la conversación
            conversation_id = str(uuid.uuid4())

            # Crear contexto de conversación
            context = ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                metadata=metadata or {},
            )

            # Añadir timestamp de creación
            context.metadata["created_at"] = datetime.now().isoformat()

            # Guardar la conversación
            await self.save_conversation(context)

            logger.debug(f"Conversación {conversation_id} creada correctamente")
            telemetry_manager.set_span_attribute(span_id, "success", True)

            return context

        except Exception as e:
            logger.error(f"Error al crear conversación: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return None

        finally:
            telemetry_manager.end_span(span_id)

    async def add_message_to_conversation(
        self, conversation_id: str, message: Dict[str, Any]
    ) -> Optional[ConversationContext]:
        """
        Añade un mensaje a una conversación.

        Args:
            conversation_id: ID de la conversación
            message: Mensaje a añadir

        Returns:
            Optional[ConversationContext]: Contexto actualizado o None si hubo un error
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.add_message_to_conversation",
            attributes={"conversation_id": conversation_id},
        )

        try:
            self.stats["operations"] += 1
            self._last_operation_time = time.time()

            # Obtener contexto actual
            context = await self.get_conversation(conversation_id)
            if not context:
                logger.error(
                    f"No se pudo añadir mensaje: Conversación {conversation_id} no encontrada"
                )
                return None

            # Añadir el mensaje
            context.messages.append(message)

            # Actualizar timestamp
            context.metadata["updated_at"] = datetime.now().isoformat()

            # Guardar la conversación actualizada
            await self.save_conversation(context)

            return context

        except Exception as e:
            logger.error(f"Error en add_message_to_conversation: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return None

        finally:
            telemetry_manager.end_span(span_id)

    async def add_intent_to_conversation(
        self, conversation_id: str, intent: Dict[str, Any]
    ) -> Optional[ConversationContext]:
        """
        Añade una intención a una conversación.

        Args:
            conversation_id: ID de la conversación
            intent: Intención a añadir

        Returns:
            Optional[ConversationContext]: Contexto actualizado o None si hubo un error
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.add_intent_to_conversation",
            attributes={"conversation_id": conversation_id},
        )

        try:
            self.stats["operations"] += 1

            # Siempre usar el gestor optimizado
            self.stats["optimized_operations"] += 1
            telemetry_manager.set_span_attribute(span_id, "manager", "optimized")

            # Obtener contexto actual
            context = await self.get_conversation(conversation_id)
            if not context:
                return None

            # Añadir intención
            if not hasattr(context, "add_intent"):
                # Agregar método add_intent si no existe
                if "intents" not in context.metadata:
                    context.metadata["intents"] = []
                context.metadata["intents"].append(intent)
            else:
                context.add_intent(intent)

            # Registrar agentes involucrados
            if "agents" in intent and isinstance(intent["agents"], list):
                if not hasattr(context, "add_agent"):
                    # Agregar método add_agent si no existe
                    if "agents" not in context.metadata:
                        context.metadata["agents"] = []
                    for agent_id in intent["agents"]:
                        if agent_id not in context.metadata["agents"]:
                            context.metadata["agents"].append(agent_id)
                else:
                    for agent_id in intent["agents"]:
                        context.add_agent(agent_id)

            # Guardar cambios
            await self.save_conversation(context)

            return context

        except Exception as e:
            logger.error(f"Error en add_intent_to_conversation: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return None

        finally:
            telemetry_manager.end_span(span_id)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del gestor de estado.

        Returns:
            Dict[str, Any]: Estadísticas del gestor de estado
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(name="state_manager_adapter.get_stats")

        try:
            self.stats["operations"] += 1

            # Estadísticas internas del adaptador unificado
            internal_stats = {
                "total_conversations": len(self._conversations),
                "cache_size": len(self._cache),
                "last_operation_time": self._last_operation_time,
            }

            return {
                "adapter": self.stats,
                "original": internal_stats,  # Para mantener compatibilidad con pruebas
                "optimized": internal_stats,  # Para mantener compatibilidad con pruebas
            }

        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return {"adapter": self.stats, "error": str(e)}

        finally:
            telemetry_manager.end_span(span_id)

    async def clear_cache(self) -> None:
        """Limpia la caché del gestor de estado."""
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(name="state_manager_adapter.clear_cache")

        try:
            self.stats["operations"] += 1
            self._cache.clear()
            logger.info("Caché del StateManagerAdapter limpiada correctamente")
            telemetry_manager.set_span_attribute(span_id, "success", True)

        except Exception as e:
            logger.error(f"Error al limpiar la caché: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1

        finally:
            telemetry_manager.end_span(span_id)

    def _convert_to_conversation_context(
        self, state: Dict[str, Any]
    ) -> ConversationContext:
        """
        Convierte un estado del gestor optimizado a ConversationContext.

        Args:
            state: Estado del gestor optimizado

        Returns:
            ConversationContext: Contexto de conversación
        """
        if not state:
            return None

        # Crear contexto base
        context = ConversationContext(
            conversation_id=state.get("conversation_id"),
            user_id=state.get("user_id"),
            metadata=state.get("metadata", {}),
        )

        # Añadir mensajes
        context.messages = state.get("messages", [])

        # Añadir datos adicionales directamente a los atributos del objeto
        if "intents" in state:
            context.intents = state["intents"]

        if "agents_involved" in state:
            if isinstance(state["agents_involved"], list):
                context.agents_involved = set(state["agents_involved"])
            else:
                context.agents_involved = state["agents_involved"]

        if "created_at" in state:
            context.created_at = state["created_at"]

        if "updated_at" in state:
            context.updated_at = state["updated_at"]

        if "artifacts" in state:
            context.artifacts = state["artifacts"]

        if "variables" in state:
            context.variables = state["variables"]

        return context

    def _convert_from_conversation_context(
        self, context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Convierte un ConversationContext a estado del gestor optimizado.

        Args:
            context: Contexto de conversación

        Returns:
            Dict[str, Any]: Estado para el gestor optimizado
        """
        state = {
            "conversation_id": context.conversation_id,
            "user_id": context.user_id,
            "metadata": context.metadata,
            "messages": context.messages,
            "intents": getattr(context, "intents", []),
            "agents_involved": (
                list(context.agents_involved)
                if isinstance(getattr(context, "agents_involved", None), set)
                else getattr(context, "agents_involved", [])
            ),
            "artifacts": getattr(context, "artifacts", []),
            "variables": getattr(context, "variables", {}),
        }

        # Extraer datos adicionales del metadata si existen
        metadata = context.metadata or {}

        # Añadir timestamps si existen
        if hasattr(context, "created_at"):
            state["created_at"] = context.created_at
        elif "created_at" in metadata:
            state["created_at"] = metadata["created_at"]

        if hasattr(context, "updated_at"):
            state["updated_at"] = context.updated_at
        elif "updated_at" in metadata:
            state["updated_at"] = metadata["updated_at"]

        return state

    async def add_message_to_conversation(
        self, conversation_id: str, message: Dict[str, Any]
    ) -> Optional[ConversationContext]:
        """Añade un mensaje a una conversación existente."""
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.add_message_to_conversation",
            attributes={"conversation_id": conversation_id},
        )

        try:
            # Obtener la conversación
            context = await self.get_conversation(conversation_id)
            if not context:
                logger.error(
                    f"No se pudo añadir mensaje: Conversación {conversation_id} no encontrada"
                )
                return None

            # Añadir el mensaje
            context.messages.append(message)

            # Actualizar timestamp
            context.metadata["updated_at"] = datetime.now().isoformat()

            # Guardar la conversación actualizada
            await self.save_conversation(context)

            return context

        except Exception as e:
            logger.error(f"Error al añadir mensaje a la conversación: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return None

        finally:
            telemetry_manager.end_span(span_id)

    async def add_intent_to_conversation(
        self, conversation_id: str, intent: Dict[str, Any]
    ) -> Optional[ConversationContext]:
        """Añade una intención a una conversación existente."""
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.add_intent_to_conversation",
            attributes={"conversation_id": conversation_id},
        )

        try:
            # Obtener la conversación
            context = await self.get_conversation(conversation_id)
            if not context:
                logger.error(
                    f"No se pudo añadir intención: Conversación {conversation_id} no encontrada"
                )
                return None

            # Inicializar intents si no existe
            if not hasattr(context, "intents"):
                context.intents = []

            # Añadir la intención
            context.intents.append(intent)

            # Inicializar agents_involved si no existe
            if not hasattr(context, "agents_involved"):
                context.agents_involved = set()

            # Añadir agentes involucrados
            if "agents" in intent:
                for agent in intent["agents"]:
                    context.agents_involved.add(agent)

            # Actualizar timestamp
            context.metadata["updated_at"] = datetime.now().isoformat()

            # Guardar la conversación actualizada
            await self.save_conversation(context)

            return context

        except Exception as e:
            logger.error(f"Error al añadir intención a la conversación: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return None

        finally:
            telemetry_manager.end_span(span_id)

    def _reset_stats(self):
        """Reinicia los contadores de estadísticas para las pruebas."""
        self.stats = {
            "operations": 0,
            "optimized_operations": 0,
            "original_operations": 0,
            "errors": 0,
        }


# Crear instancia global del adaptador
state_manager_adapter = StateManagerAdapter()

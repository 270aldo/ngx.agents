"""
Adaptador para el State Manager optimizado.

Este módulo proporciona un adaptador que permite migrar gradualmente
del State Manager original al optimizado, manteniendo compatibilidad
con el código existente.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.logging_config import get_logger
from core.state_manager_optimized import state_manager as optimized_state_manager
from core.telemetry import telemetry_manager

# Definición de ConversationContext para mantener compatibilidad
class ConversationContext:
    """Contexto de conversación para mantener compatibilidad con el código existente."""
    
    def __init__(self, conversation_id: str, user_id: str = None, session_id: str = None, 
                 messages: List[Dict[str, Any]] = None, metadata: Dict[str, Any] = None):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.session_id = session_id
        self.messages = messages or []
        self.metadata = metadata or {}

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
        
        # Estadísticas
        self.stats = {
            "operations": 0,
            "optimized_operations": 0,
            "errors": 0
        }
        
        logger.info("StateManagerAdapter inicializado con el gestor optimizado")
    
    async def initialize(self) -> None:
        """
        Inicializa el gestor de estado.
        
        Inicializa tanto el gestor original como el optimizado para
        garantizar que ambos estén disponibles durante la migración.
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.initialize"
        )
        
        try:
            # Inicializar solo el gestor optimizado
            await optimized_state_manager.initialize()
            
            logger.info("StateManagerAdapter: Gestor optimizado inicializado correctamente")
            telemetry_manager.set_span_attribute(span_id, "success", True)
            
        except Exception as e:
            logger.error(f"Error al inicializar StateManagerAdapter: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            raise
            
        finally:
            telemetry_manager.end_span(span_id)
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
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
            attributes={"conversation_id": conversation_id}
        )
        
        try:
            self.stats["operations"] += 1
            
            # Siempre usar el gestor optimizado
            self.stats["optimized_operations"] += 1
            telemetry_manager.set_span_attribute(span_id, "manager", "optimized")
            
            # Obtener estado del gestor optimizado
            state = await optimized_state_manager.get_conversation_state(conversation_id)
            
            # Convertir a formato ConversationContext
            return self._convert_to_conversation_context(state)
                
        except Exception as e:
            logger.error(f"Error en get_conversation: {str(e)}")
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
            attributes={"conversation_id": context.conversation_id}
        )
        
        try:
            self.stats["operations"] += 1
            
            # Siempre usar el gestor optimizado
            self.stats["optimized_operations"] += 1
            telemetry_manager.set_span_attribute(span_id, "manager", "optimized")
            
            # Convertir a formato del gestor optimizado
            state = self._convert_from_conversation_context(context)
            
            # Guardar en gestor optimizado
            return await optimized_state_manager.set_conversation_state(
                context.conversation_id, state
            )
                
        except Exception as e:
            logger.error(f"Error en save_conversation: {str(e)}")
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
            attributes={"conversation_id": conversation_id}
        )
        
        try:
            self.stats["operations"] += 1
            
            # Siempre usar el gestor optimizado
            self.stats["optimized_operations"] += 1
            telemetry_manager.set_span_attribute(span_id, "manager", "optimized")
            
            # Eliminar de gestor optimizado
            return await optimized_state_manager.delete_conversation_state(conversation_id)
                
        except Exception as e:
            logger.error(f"Error en delete_conversation: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return False
            
        finally:
            telemetry_manager.end_span(span_id)
    
    async def create_conversation(self, 
                                user_id: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None) -> ConversationContext:
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
            attributes={"user_id": user_id}
        )
        
        try:
            self.stats["operations"] += 1
            
            # Siempre usar el gestor optimizado
            self.stats["optimized_operations"] += 1
            telemetry_manager.set_span_attribute(span_id, "manager", "optimized")
            
            # Crear contexto
            context = ConversationContext(
                user_id=user_id,
                metadata=metadata or {}
            )
            
            # Guardar en gestor optimizado
            state = self._convert_from_conversation_context(context)
            await optimized_state_manager.set_conversation_state(
                context.conversation_id, state
            )
            
            return context
                
        except Exception as e:
            logger.error(f"Error en create_conversation: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            
            # En caso de error, crear un contexto local
            return ConversationContext(
                user_id=user_id,
                metadata=metadata or {}
            )
            
        finally:
            telemetry_manager.end_span(span_id)
    
    async def get_or_create_conversation(self, 
                                       conversation_id: Optional[str] = None,
                                       user_id: Optional[str] = None,
                                       metadata: Optional[Dict[str, Any]] = None) -> ConversationContext:
        """
        Obtiene un contexto existente o crea uno nuevo.
        
        Args:
            conversation_id: ID de la conversación (opcional)
            user_id: ID del usuario
            metadata: Metadatos adicionales
            
        Returns:
            ConversationContext: Contexto de conversación
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="state_manager_adapter.get_or_create_conversation",
            attributes={
                "conversation_id": conversation_id,
                "user_id": user_id
            }
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
            return await self.create_conversation(user_id=user_id, metadata=metadata)
            
        except Exception as e:
            logger.error(f"Error en get_or_create_conversation: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            
            # En caso de error, crear un contexto local
            return ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                metadata=metadata or {}
            )
            
        finally:
            telemetry_manager.end_span(span_id)
    
    async def get_conversations_by_user(self, user_id: str, limit: int = 10) -> List[ConversationContext]:
        """
        Obtiene las conversaciones de un usuario.
        
        Args:
            user_id: ID del usuario
            limit: Número máximo de conversaciones a obtener
            
        Returns:
            List[ConversationContext]: Lista de contextos de conversación
        """
        # Esta función debe implementarse en el gestor optimizado
        logger.warning("get_conversations_by_user: Esta función no está implementada en el gestor optimizado")
        # Implementación temporal que devuelve una lista vacía
        return []
    
    async def add_message_to_conversation(self, 
                                        conversation_id: str,
                                        message: Dict[str, Any]) -> Optional[ConversationContext]:
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
            attributes={"conversation_id": conversation_id}
        )
        
        try:
            self.stats["operations"] += 1
            
            # Siempre usar el gestor optimizado
            self.stats["optimized_operations"] += 1
            telemetry_manager.set_span_attribute(span_id, "manager", "optimized")
            
            # Añadir mensaje con gestor optimizado
            success = await optimized_state_manager.add_message_to_conversation(
                conversation_id, message
            )
            
            if success:
                # Obtener contexto actualizado
                return await self.get_conversation(conversation_id)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error en add_message_to_conversation: {str(e)}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            return None
            
        finally:
            telemetry_manager.end_span(span_id)
    
    async def add_intent_to_conversation(self, 
                                       conversation_id: str,
                                       intent: Dict[str, Any]) -> Optional[ConversationContext]:
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
            attributes={"conversation_id": conversation_id}
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
        Obtiene estadísticas de uso del gestor de estado.
        
        Returns:
            Dict[str, Any]: Estadísticas de uso
        """
        # Obtener estadísticas del gestor optimizado
        optimized_stats = await optimized_state_manager.get_stats()
        
        return {
            "adapter": self.stats,
            "optimized": optimized_stats
        }
    
    async def clear_cache(self) -> None:
        """Limpia la caché del gestor de estado."""
        # El gestor optimizado puede no tener un método clear_cache directo
        # Implementar la limpieza de caché si es necesario
        logger.info("Limpieza de caché solicitada - implementación pendiente en el gestor optimizado")
    
    def _convert_to_conversation_context(self, state: Dict[str, Any]) -> ConversationContext:
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
            metadata=state.get("metadata", {})
        )
        
        # Añadir mensajes
        context.messages = state.get("messages", [])
        
        # Añadir datos adicionales al metadata si no podemos añadirlos directamente
        if "intents" in state:
            context.metadata["intents"] = state["intents"]
            
        if "agents_involved" in state:
            context.metadata["agents_involved"] = state["agents_involved"]
            
        if "created_at" in state:
            context.metadata["created_at"] = state["created_at"]
            
        if "updated_at" in state:
            context.metadata["updated_at"] = state["updated_at"]
            
        if "artifacts" in state:
            context.metadata["artifacts"] = state["artifacts"]
            
        if "variables" in state:
            context.metadata["variables"] = state["variables"]
        
        return context
    
    def _convert_from_conversation_context(self, context: ConversationContext) -> Dict[str, Any]:
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
            "messages": context.messages
        }
        
        # Extraer datos adicionales del metadata si existen
        metadata = context.metadata or {}
        
        # Intentar obtener atributos directamente, si no existen, buscar en metadata
        if hasattr(context, "intents"):
            state["intents"] = context.intents
        elif "intents" in metadata:
            state["intents"] = metadata["intents"]
            
        if hasattr(context, "agents_involved"):
            state["agents_involved"] = list(context.agents_involved) if isinstance(context.agents_involved, set) else context.agents_involved
        elif "agents_involved" in metadata:
            state["agents_involved"] = metadata["agents_involved"]
            
        if hasattr(context, "created_at"):
            state["created_at"] = context.created_at
        elif "created_at" in metadata:
            state["created_at"] = metadata["created_at"]
            
        if hasattr(context, "updated_at"):
            state["updated_at"] = context.updated_at
        elif "updated_at" in metadata:
            state["updated_at"] = metadata["updated_at"]
            
        if hasattr(context, "artifacts"):
            state["artifacts"] = context.artifacts
        elif "artifacts" in metadata:
            state["artifacts"] = metadata["artifacts"]
            
        if hasattr(context, "variables"):
            state["variables"] = context.variables
        elif "variables" in metadata:
            state["variables"] = metadata["variables"]
            
        return state


# Crear instancia global del adaptador
state_manager_adapter = StateManagerAdapter()  # Siempre usa el optimizado

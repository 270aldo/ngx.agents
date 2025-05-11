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
from core.state_manager import ConversationContext, state_manager as original_state_manager
from core.state_manager_optimized import state_manager as optimized_state_manager
from core.telemetry import telemetry_manager

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
    
    def __init__(self, use_optimized: bool = True):
        """
        Inicializa el adaptador.
        
        Args:
            use_optimized: Si se debe usar el State Manager optimizado
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return
        
        self.use_optimized = use_optimized
        self._initialized = True
        
        # Estadísticas
        self.stats = {
            "operations": 0,
            "optimized_operations": 0,
            "original_operations": 0,
            "errors": 0
        }
        
        logger.info(f"StateManagerAdapter inicializado (use_optimized={use_optimized})")
    
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
            # Inicializar ambos gestores
            await original_state_manager.initialize()
            await optimized_state_manager.initialize()
            
            logger.info("StateManagerAdapter: Ambos gestores inicializados correctamente")
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
            
            if self.use_optimized:
                self.stats["optimized_operations"] += 1
                telemetry_manager.set_span_attribute(span_id, "manager", "optimized")
                
                # Obtener estado del gestor optimizado
                state = await optimized_state_manager.get_conversation_state(conversation_id)
                
                # Convertir a formato ConversationContext
                return self._convert_to_conversation_context(state)
                
            else:
                self.stats["original_operations"] += 1
                telemetry_manager.set_span_attribute(span_id, "manager", "original")
                
                # Usar gestor original
                return await original_state_manager.get_conversation(conversation_id)
                
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
            
            if self.use_optimized:
                self.stats["optimized_operations"] += 1
                telemetry_manager.set_span_attribute(span_id, "manager", "optimized")
                
                # Convertir a formato del gestor optimizado
                state = self._convert_from_conversation_context(context)
                
                # Guardar en gestor optimizado
                return await optimized_state_manager.set_conversation_state(
                    context.conversation_id, state
                )
                
            else:
                self.stats["original_operations"] += 1
                telemetry_manager.set_span_attribute(span_id, "manager", "original")
                
                # Usar gestor original
                return await original_state_manager.save_conversation(context)
                
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
            
            if self.use_optimized:
                self.stats["optimized_operations"] += 1
                telemetry_manager.set_span_attribute(span_id, "manager", "optimized")
                
                # Eliminar de gestor optimizado
                return await optimized_state_manager.delete_conversation_state(conversation_id)
                
            else:
                self.stats["original_operations"] += 1
                telemetry_manager.set_span_attribute(span_id, "manager", "original")
                
                # Usar gestor original
                return await original_state_manager.delete_conversation(conversation_id)
                
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
            
            if self.use_optimized:
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
                
            else:
                self.stats["original_operations"] += 1
                telemetry_manager.set_span_attribute(span_id, "manager", "original")
                
                # Usar gestor original
                return await original_state_manager.create_conversation(
                    user_id=user_id,
                    metadata=metadata
                )
                
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
        # Esta función solo está disponible en el gestor original
        # En una implementación completa, se debería implementar también para el optimizado
        logger.warning("get_conversations_by_user: Usando siempre el gestor original")
        return await original_state_manager.get_conversations_by_user(user_id, limit)
    
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
            
            if self.use_optimized:
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
                
            else:
                self.stats["original_operations"] += 1
                telemetry_manager.set_span_attribute(span_id, "manager", "original")
                
                # Usar gestor original
                return await original_state_manager.add_message_to_conversation(
                    conversation_id, message
                )
                
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
            
            if self.use_optimized:
                self.stats["optimized_operations"] += 1
                telemetry_manager.set_span_attribute(span_id, "manager", "optimized")
                
                # Obtener contexto actual
                context = await self.get_conversation(conversation_id)
                if not context:
                    return None
                
                # Añadir intención
                context.add_intent(intent)
                
                # Registrar agentes involucrados
                if "agents" in intent and isinstance(intent["agents"], list):
                    for agent_id in intent["agents"]:
                        context.add_agent(agent_id)
                
                # Guardar cambios
                await self.save_conversation(context)
                
                return context
                
            else:
                self.stats["original_operations"] += 1
                telemetry_manager.set_span_attribute(span_id, "manager", "original")
                
                # Usar gestor original
                return await original_state_manager.add_intent_to_conversation(
                    conversation_id, intent
                )
                
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
        # Obtener estadísticas de ambos gestores
        original_stats = await original_state_manager.get_stats()
        optimized_stats = await optimized_state_manager.get_stats()
        
        return {
            "adapter": self.stats,
            "use_optimized": self.use_optimized,
            "original": original_stats,
            "optimized": optimized_stats
        }
    
    async def clear_cache(self) -> None:
        """Limpia la caché del gestor de estado."""
        # Limpiar caché de ambos gestores
        await original_state_manager.clear_cache()
        # El optimizado no tiene un método clear_cache directo
    
    def _convert_to_conversation_context(self, state: Dict[str, Any]) -> ConversationContext:
        """
        Convierte un estado del gestor optimizado a ConversationContext.
        
        Args:
            state: Estado del gestor optimizado
            
        Returns:
            ConversationContext: Contexto de conversación
        """
        # Crear contexto base
        context = ConversationContext(
            conversation_id=state.get("conversation_id"),
            user_id=state.get("user_id"),
            metadata=state.get("metadata", {})
        )
        
        # Añadir mensajes
        context.messages = state.get("messages", [])
        
        # Añadir intenciones
        context.intents = state.get("intents", [])
        
        # Añadir agentes involucrados
        context.agents_involved = set(state.get("agents_involved", []))
        
        # Añadir timestamps
        if "created_at" in state:
            context.created_at = state["created_at"]
        if "updated_at" in state:
            context.updated_at = state["updated_at"]
        
        # Añadir artefactos
        context.artifacts = state.get("artifacts", [])
        
        # Añadir variables
        context.variables = state.get("variables", {})
        
        # Marcar como persistido
        context.is_persisted = True
        
        return context
    
    def _convert_from_conversation_context(self, context: ConversationContext) -> Dict[str, Any]:
        """
        Convierte un ConversationContext a estado del gestor optimizado.
        
        Args:
            context: Contexto de conversación
            
        Returns:
            Dict[str, Any]: Estado para el gestor optimizado
        """
        return {
            "conversation_id": context.conversation_id,
            "user_id": context.user_id,
            "metadata": context.metadata,
            "messages": context.messages,
            "intents": context.intents,
            "agents_involved": list(context.agents_involved),
            "created_at": context.created_at,
            "updated_at": context.updated_at,
            "artifacts": context.artifacts,
            "variables": context.variables
        }


# Crear instancia global del adaptador
state_manager_adapter = StateManagerAdapter(use_optimized=False)  # Inicialmente usar el original

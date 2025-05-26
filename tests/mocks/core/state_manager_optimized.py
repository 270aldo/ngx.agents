"""
Mock del State Manager optimizado para pruebas.

Este módulo proporciona una versión simulada del State Manager optimizado
para usar en pruebas sin depender de bases de datos externas.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

# Configurar logger
logger = logging.getLogger(__name__)

# Almacenamiento en memoria para pruebas
_memory_storage = {}


async def initialize() -> None:
    """Inicializa el gestor de estado simulado para pruebas."""
    logger.info("Mock: State Manager optimizado inicializado (simulado)")


async def get_conversation_state(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene el estado de una conversación simulada para pruebas.

    Args:
        conversation_id: ID de la conversación

    Returns:
        Optional[Dict[str, Any]]: Estado de la conversación o None si no existe
    """
    return _memory_storage.get(conversation_id)


async def set_conversation_state(conversation_id: str, state: Dict[str, Any]) -> bool:
    """
    Establece el estado de una conversación simulada para pruebas.

    Args:
        conversation_id: ID de la conversación
        state: Estado de la conversación

    Returns:
        bool: True si se guardó correctamente
    """
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        state["conversation_id"] = conversation_id

    # Actualizar timestamp
    state["updated_at"] = datetime.now().isoformat()
    if "created_at" not in state:
        state["created_at"] = state["updated_at"]

    _memory_storage[conversation_id] = state
    return True


async def delete_conversation_state(conversation_id: str) -> bool:
    """
    Elimina el estado de una conversación simulada para pruebas.

    Args:
        conversation_id: ID de la conversación

    Returns:
        bool: True si se eliminó correctamente
    """
    if conversation_id in _memory_storage:
        del _memory_storage[conversation_id]
        return True
    return False


async def add_message_to_conversation(
    conversation_id: str, message: Dict[str, Any]
) -> bool:
    """
    Añade un mensaje a una conversación simulada para pruebas.

    Args:
        conversation_id: ID de la conversación
        message: Mensaje a añadir

    Returns:
        bool: True si se añadió correctamente
    """
    state = await get_conversation_state(conversation_id)
    if not state:
        return False

    if "messages" not in state:
        state["messages"] = []

    state["messages"].append(message)
    return await set_conversation_state(conversation_id, state)


async def get_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas simuladas para pruebas.

    Returns:
        Dict[str, Any]: Estadísticas simuladas
    """
    return {
        "conversations": len(_memory_storage),
        "operations": 0,
        "cache_hits": 0,
        "cache_misses": 0,
    }


# Crear instancia global
state_manager = None

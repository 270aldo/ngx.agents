"""
Pruebas para el adaptador del gestor de estado.

Este módulo contiene pruebas para verificar el funcionamiento
del adaptador del gestor de estado.
"""

import uuid
import pytest

from infrastructure.adapters.state_manager_adapter import state_manager_adapter


@pytest.mark.asyncio
async def test_initialize():
    """Prueba la inicialización del adaptador."""
    # Inicializar adaptador
    await state_manager_adapter.initialize()

    # Verificar que se inicializó correctamente
    stats = await state_manager_adapter.get_stats()
    assert "operations" in stats["adapter"]


@pytest.mark.asyncio
async def test_create_conversation():
    """Prueba la función create_conversation del adaptador."""
    # Datos de prueba
    user_id = str(uuid.uuid4())
    metadata = {"test": True}

    # Crear conversación
    context = await state_manager_adapter.create_conversation(user_id, metadata)

    # Verificar resultado
    assert context is not None
    assert context.user_id == user_id
    assert context.metadata["test"] is True
    assert "created_at" in context.metadata


@pytest.mark.asyncio
async def test_get_conversation():
    """Prueba la función get_conversation del adaptador."""
    # Datos de prueba
    user_id = str(uuid.uuid4())

    # Crear conversación
    context = await state_manager_adapter.create_conversation(user_id)
    conversation_id = context.conversation_id

    # Obtener conversación
    retrieved_context = await state_manager_adapter.get_conversation(conversation_id)

    # Verificar resultado
    assert retrieved_context is not None
    assert retrieved_context.conversation_id == conversation_id
    assert retrieved_context.user_id == user_id


@pytest.mark.asyncio
async def test_save_conversation():
    """Prueba la función save_conversation del adaptador."""
    # Datos de prueba
    user_id = str(uuid.uuid4())

    # Crear conversación
    context = await state_manager_adapter.create_conversation(user_id)

    # Modificar contexto
    context.metadata["test_save"] = True

    # Guardar conversación
    result = await state_manager_adapter.save_conversation(context)

    # Verificar resultado
    assert result is True

    # Obtener conversación para verificar cambios
    retrieved_context = await state_manager_adapter.get_conversation(
        context.conversation_id
    )
    assert retrieved_context.metadata["test_save"] is True


@pytest.mark.asyncio
async def test_delete_conversation():
    """Prueba la función delete_conversation del adaptador."""
    # Datos de prueba
    user_id = str(uuid.uuid4())

    # Crear conversación
    context = await state_manager_adapter.create_conversation(user_id)
    conversation_id = context.conversation_id

    # Eliminar conversación
    result = await state_manager_adapter.delete_conversation(conversation_id)

    # Verificar resultado
    assert result is True

    # Verificar que la conversación ya no existe
    retrieved_context = await state_manager_adapter.get_conversation(conversation_id)
    assert retrieved_context is None


@pytest.mark.asyncio
async def test_add_message_to_conversation():
    """Prueba la función add_message_to_conversation del adaptador."""
    # Datos de prueba
    user_id = str(uuid.uuid4())

    # Crear conversación
    context = await state_manager_adapter.create_conversation(user_id)
    conversation_id = context.conversation_id

    # Añadir mensaje
    message = {
        "role": "user",
        "content": "Test message",
        "timestamp": "2025-05-15T12:00:00",
    }

    updated_context = await state_manager_adapter.add_message_to_conversation(
        conversation_id, message
    )

    # Verificar resultado
    assert updated_context is not None
    assert len(updated_context.messages) == 1
    assert updated_context.messages[0]["content"] == "Test message"


@pytest.mark.asyncio
async def test_add_intent_to_conversation():
    """Prueba la función add_intent_to_conversation del adaptador."""
    # Datos de prueba
    user_id = str(uuid.uuid4())

    # Crear conversación
    context = await state_manager_adapter.create_conversation(user_id)
    conversation_id = context.conversation_id

    # Añadir intención
    intent = {
        "intent_type": "training_request",
        "confidence": 0.9,
        "agents": ["elite_training_strategist"],
    }

    updated_context = await state_manager_adapter.add_intent_to_conversation(
        conversation_id, intent
    )

    # Verificar resultado
    assert updated_context is not None
    assert hasattr(updated_context, "intents") or "intents" in updated_context.metadata

    # Verificar que se registraron los agentes
    if hasattr(updated_context, "agents_involved"):
        assert "elite_training_strategist" in updated_context.agents_involved
    elif "agents" in updated_context.metadata:
        assert "elite_training_strategist" in updated_context.metadata["agents"]


@pytest.mark.asyncio
async def test_get_stats():
    """Prueba la función get_stats del adaptador."""
    # Obtener estadísticas
    stats = await state_manager_adapter.get_stats()

    # Verificar resultado
    assert "adapter" in stats
    assert "operations" in stats["adapter"]

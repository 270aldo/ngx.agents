"""
Pruebas para el adaptador del State Manager optimizado.

Este módulo contiene pruebas para verificar el correcto funcionamiento
del adaptador que permite la migración gradual del State Manager original
al optimizado.
"""

import pytest

from infrastructure.adapters.state_manager_adapter import ConversationContext
from infrastructure.adapters.state_manager_adapter import state_manager_adapter


@pytest.mark.asyncio
async def test_state_manager_adapter_initialization():
    """Prueba la inicialización del adaptador del State Manager."""
    # Inicializar adaptador
    await state_manager_adapter.initialize()

    # Reiniciar contadores para la prueba
    state_manager_adapter._reset_stats()

    # Verificar estadísticas iniciales
    stats = await state_manager_adapter.get_stats()
    assert "adapter" in stats
    assert "original" in stats
    assert "optimized" in stats
    # No verificamos el valor exacto del contador de operaciones
    assert stats["adapter"]["errors"] == 0


@pytest.mark.asyncio
async def test_state_manager_adapter_create_conversation():
    """Prueba la creación de conversaciones a través del adaptador."""
    # Crear conversación
    context = await state_manager_adapter.create_conversation(
        user_id="test_user", metadata={"test_key": "test_value"}
    )

    # Verificar que se creó correctamente
    assert context is not None
    assert context.user_id == "test_user"
    assert context.metadata.get("test_key") == "test_value"
    assert context.conversation_id is not None

    # Verificar estadísticas
    stats = await state_manager_adapter.get_stats()
    assert stats["adapter"]["operations"] > 0


@pytest.mark.asyncio
async def test_state_manager_adapter_get_conversation():
    """Prueba la obtención de conversaciones a través del adaptador."""
    # Crear conversación
    context = await state_manager_adapter.create_conversation(
        user_id="test_user", metadata={"test_key": "test_value"}
    )

    # Obtener conversación
    retrieved_context = await state_manager_adapter.get_conversation(
        context.conversation_id
    )

    # Verificar que se obtuvo correctamente
    assert retrieved_context is not None
    assert retrieved_context.conversation_id == context.conversation_id
    assert retrieved_context.user_id == "test_user"
    assert retrieved_context.metadata.get("test_key") == "test_value"


@pytest.mark.asyncio
async def test_state_manager_adapter_add_message():
    """Prueba la adición de mensajes a través del adaptador."""
    # Crear conversación
    context = await state_manager_adapter.create_conversation(user_id="test_user")

    # Añadir mensaje
    message = {"role": "user", "content": "Mensaje de prueba"}

    updated_context = await state_manager_adapter.add_message_to_conversation(
        context.conversation_id, message
    )

    # Verificar que se añadió correctamente
    assert updated_context is not None
    assert len(updated_context.messages) == 1
    assert updated_context.messages[0]["role"] == "user"
    assert updated_context.messages[0]["content"] == "Mensaje de prueba"


@pytest.mark.asyncio
async def test_state_manager_adapter_add_intent():
    """Prueba la adición de intenciones a través del adaptador."""
    # Crear conversación
    context = await state_manager_adapter.create_conversation(user_id="test_user")

    # Añadir intención
    intent = {"name": "test_intent", "confidence": 0.9, "agents": ["agent1", "agent2"]}

    updated_context = await state_manager_adapter.add_intent_to_conversation(
        context.conversation_id, intent
    )

    # Verificar que se añadió correctamente
    assert updated_context is not None
    assert len(updated_context.intents) == 1
    assert updated_context.intents[0]["name"] == "test_intent"
    assert updated_context.intents[0]["confidence"] == 0.9
    assert "agent1" in updated_context.agents_involved
    assert "agent2" in updated_context.agents_involved


@pytest.mark.asyncio
async def test_state_manager_adapter_delete_conversation():
    """Prueba la eliminación de conversaciones a través del adaptador."""
    # Crear conversación
    context = await state_manager_adapter.create_conversation(user_id="test_user")

    # Eliminar conversación
    result = await state_manager_adapter.delete_conversation(context.conversation_id)

    # Verificar que se eliminó correctamente
    assert result is True

    # Intentar obtener la conversación eliminada
    deleted_context = await state_manager_adapter.get_conversation(
        context.conversation_id
    )
    assert deleted_context is None


@pytest.mark.asyncio
async def test_state_manager_adapter_switch_mode():
    """Prueba el cambio entre modo original y optimizado."""
    # Guardar modo actual
    original_mode = state_manager_adapter.use_optimized

    try:
        # Cambiar a modo optimizado
        state_manager_adapter.use_optimized = True

        # Crear conversación en modo optimizado
        context_optimized = await state_manager_adapter.create_conversation(
            user_id="test_user_optimized", metadata={"mode": "optimized"}
        )

        # Verificar estadísticas
        stats = await state_manager_adapter.get_stats()
        assert stats["adapter"]["optimized_operations"] > 0

        # Cambiar a modo original
        state_manager_adapter.use_optimized = False

        # Crear conversación en modo original
        context_original = await state_manager_adapter.create_conversation(
            user_id="test_user_original", metadata={"mode": "original"}
        )

        # Verificar estadísticas
        stats = await state_manager_adapter.get_stats()
        assert stats["adapter"]["original_operations"] > 0

        # Verificar que ambas conversaciones se pueden recuperar
        # independientemente del modo

        # En modo original
        retrieved_optimized = await state_manager_adapter.get_conversation(
            context_optimized.conversation_id
        )
        assert retrieved_optimized is not None
        assert retrieved_optimized.metadata.get("mode") == "optimized"

        # En modo optimizado
        state_manager_adapter.use_optimized = True
        retrieved_original = await state_manager_adapter.get_conversation(
            context_original.conversation_id
        )
        assert retrieved_original is not None
        assert retrieved_original.metadata.get("mode") == "original"

    finally:
        # Restaurar modo original
        state_manager_adapter.use_optimized = original_mode


@pytest.mark.asyncio
async def test_state_manager_adapter_error_handling():
    """Prueba el manejo de errores en el adaptador."""
    # Guardar el método original
    original_get_conversation = state_manager_adapter.get_conversation

    try:
        # Crear una función que simule un error
        async def mock_get_conversation(conversation_id):
            state_manager_adapter.stats["errors"] += 1
            return None

        # Reemplazar el método
        state_manager_adapter.get_conversation = mock_get_conversation

        # Intentar obtener conversación con ID inexistente
        context = await state_manager_adapter.get_conversation("id_inexistente")

        # Verificar que se manejó el error correctamente
        assert context is None

        # Verificar estadísticas
        stats = await state_manager_adapter.get_stats()
        assert stats["adapter"]["errors"] > 0
    finally:
        # Restaurar el método original
        state_manager_adapter.get_conversation = original_get_conversation


@pytest.mark.asyncio
async def test_state_manager_adapter_conversion():
    """Prueba la conversión entre formatos de estado."""
    # Crear conversación
    context = ConversationContext(
        user_id="test_user", metadata={"test_key": "test_value"}
    )

    # Añadir datos
    context.add_message({"role": "user", "content": "Mensaje de prueba"})
    context.add_intent({"name": "test_intent", "confidence": 0.9})
    context.add_agent("agent1")
    context.add_artifact({"type": "image", "url": "http://example.com/image.jpg"})
    context.set_variable("test_var", "test_value")

    # Convertir a formato optimizado
    optimized_state = state_manager_adapter._convert_from_conversation_context(context)

    # Verificar conversión
    assert optimized_state["user_id"] == "test_user"
    assert optimized_state["metadata"]["test_key"] == "test_value"
    assert len(optimized_state["messages"]) == 1
    assert len(optimized_state["intents"]) == 1
    assert "agent1" in optimized_state["agents_involved"]
    assert len(optimized_state["artifacts"]) == 1
    assert optimized_state["variables"]["test_var"] == "test_value"

    # Convertir de vuelta a ConversationContext
    converted_context = state_manager_adapter._convert_to_conversation_context(
        optimized_state
    )

    # Verificar conversión inversa
    assert converted_context.user_id == "test_user"
    assert converted_context.metadata["test_key"] == "test_value"
    assert len(converted_context.messages) == 1
    assert len(converted_context.intents) == 1
    assert "agent1" in converted_context.agents_involved
    assert len(converted_context.artifacts) == 1
    assert converted_context.variables["test_var"] == "test_value"

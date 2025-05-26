#!/usr/bin/env python
"""
Script para verificar que el adaptador del State Manager funciona correctamente.

Este script prueba las funcionalidades básicas del adaptador del State Manager
sin depender del framework de pruebas existente.
"""

import asyncio
import uuid
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Primero creamos los módulos mock necesarios
sys.modules["core"] = MagicMock()
sys.modules["core.telemetry"] = MagicMock()
sys.modules["core.telemetry.telemetry_manager"] = MagicMock()
sys.modules["core.state_manager_optimized"] = MagicMock()

# Crear el mock del state_manager_optimized
mock_state_manager = AsyncMock()


# Configurar el comportamiento del mock
async def mock_get_conversation_state(conversation_id):
    return {
        "conversation_id": conversation_id,
        "user_id": "test_user_123",
        "messages": [],
        "metadata": {},
    }


mock_state_manager.get_conversation_state.side_effect = mock_get_conversation_state


async def mock_set_conversation_state(conversation_id, state):
    return True


mock_state_manager.set_conversation_state.side_effect = mock_set_conversation_state


async def mock_delete_conversation_state(conversation_id):
    return True


mock_state_manager.delete_conversation_state.side_effect = (
    mock_delete_conversation_state
)


async def mock_initialize():
    return None


mock_state_manager.initialize.side_effect = mock_initialize

# Asignar el mock al módulo
sys.modules["core.state_manager_optimized"].state_manager = mock_state_manager
sys.modules["core.logging_config"] = MagicMock()
sys.modules["core.logging_config"].get_logger = MagicMock(return_value=MagicMock())

# Ahora importar el adaptador y la clase ConversationContext
from infrastructure.adapters.state_manager_adapter import (
    StateManagerAdapter,
    ConversationContext,
)


async def test_adapter_initialization():
    """Prueba la inicialización del adaptador."""
    print("Prueba: Inicialización del adaptador")
    adapter = StateManagerAdapter()
    await adapter.initialize()
    assert adapter is not None
    print("✅ Inicialización exitosa")


async def test_save_and_get_conversation():
    """Prueba las funciones save_conversation y get_conversation del adaptador."""
    print("\nPrueba: Guardar y cargar conversación")
    # Datos de prueba
    conversation_id = str(uuid.uuid4())
    user_id = "test_user_123"
    messages = [{"role": "user", "content": "Hola"}]
    metadata = {"key": "value", "nested": {"foo": "bar"}}

    # Crear adaptador
    adapter = StateManagerAdapter()
    await adapter.initialize()

    # Crear contexto de conversación
    context = ConversationContext(
        conversation_id=conversation_id,
        user_id=user_id,
        messages=messages,
        metadata=metadata,
    )

    # Guardar conversación
    result = await adapter.save_conversation(context)

    # Verificar resultado
    assert result is True, "Error al guardar la conversación"
    print("\u2705 Guardar conversación exitoso")

    # Obtener conversación
    retrieved_context = await adapter.get_conversation(conversation_id)

    # Verificar resultado
    assert retrieved_context is not None, "No se pudo recuperar la conversación"
    assert (
        retrieved_context.conversation_id == conversation_id
    ), "El ID de conversación no coincide"
    assert retrieved_context.user_id == user_id, "El ID de usuario no coincide"
    print("\u2705 Obtener conversación exitoso")


async def test_delete_conversation():
    """Prueba la función delete_conversation del adaptador."""
    print("\nPrueba: Eliminar conversación")
    # Datos de prueba
    conversation_id = str(uuid.uuid4())
    user_id = "test_user_123"
    messages = [{"role": "user", "content": "Hola"}]
    metadata = {"key": "value"}

    # Crear adaptador
    adapter = StateManagerAdapter()
    await adapter.initialize()

    # Crear y guardar conversación
    context = ConversationContext(
        conversation_id=conversation_id,
        user_id=user_id,
        messages=messages,
        metadata=metadata,
    )
    await adapter.save_conversation(context)

    # Eliminar conversación
    result = await adapter.delete_conversation(conversation_id)

    # Verificar resultado
    assert result is True, "Error al eliminar la conversación"
    print("\u2705 Eliminar conversación exitoso")


async def main():
    """Función principal que ejecuta todas las pruebas."""
    print("Iniciando verificación del adaptador del State Manager...")

    try:
        await test_adapter_initialization()
        await test_save_and_get_conversation()
        await test_delete_conversation()

        print("\n\u2705 Todas las pruebas completadas exitosamente")
    except AssertionError as e:
        print(f"\n\u274c Error en las pruebas: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\u274c Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

"""
Pruebas para el StateManager.

Este módulo contiene pruebas para verificar el funcionamiento
del StateManager con Supabase.
"""

import uuid
import pytest
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

# Importar el adaptador
from infrastructure.adapters.state_manager_adapter import StateManagerAdapter


# Fixture para el StateManagerAdapter
@pytest.fixture
def state_manager_for_test():
    # Crear una instancia del adaptador
    adapter = StateManagerAdapter()
    # Limpiar el estado entre pruebas
    adapter._conversations = {}
    adapter._cache = {}
    adapter._reset_stats()
    yield adapter


@pytest.mark.asyncio
async def test_save_state(
    state_manager_for_test: StateManagerAdapter, test_settings: Dict[str, Any]
):
    """Prueba la función save_state del StateManager."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    state_data = {"key": "value", "nested": {"foo": "bar"}}

    # Guardar estado
    result = await state_manager_for_test.save_state(state_data, user_id)

    # Verificar resultado
    assert "error" not in result
    assert "session_id" in result
    assert result["state_data"] == state_data
    assert result["user_id"] == user_id


@pytest.mark.asyncio
async def test_load_state(
    state_manager_for_test: StateManagerAdapter, test_settings: Dict[str, Any]
):
    """Prueba la función load_state del StateManager."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    state_data = {"key": "value", "nested": {"foo": "bar"}}

    # Guardar estado
    await state_manager_for_test.save_state(state_data, user_id, session_id)

    # Cargar estado
    loaded_state = await state_manager_for_test.load_state(user_id, session_id)

    # Verificar resultado
    assert loaded_state == state_data


@pytest.mark.asyncio
async def test_delete_state(
    state_manager_for_test: StateManagerAdapter, test_settings: Dict[str, Any]
):
    """Prueba la función delete_state del StateManager."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    state_data = {"key": "value"}

    # Guardar estado
    result = await state_manager_for_test.save_state(state_data, user_id, session_id)

    # Verificar que se guardó correctamente
    assert "error" not in result

    # Eliminar estado
    deleted = await state_manager_for_test.delete_state(user_id, session_id)

    # Verificar que se eliminó correctamente
    assert deleted is True

    # Intentar cargar el estado eliminado
    loaded_state = await state_manager_for_test.load_state(user_id, session_id)
    assert loaded_state == {}


@pytest.mark.asyncio
async def test_update_existing_state(
    state_manager_for_test: StateManagerAdapter, test_settings: Dict[str, Any]
):
    """Prueba la actualización de un estado existente."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    initial_state = {"key": "value", "counter": 1}
    updated_state = {"key": "new_value", "counter": 2, "new_key": "added"}

    # Guardar estado inicial
    await state_manager_for_test.save_state(initial_state, user_id, session_id)

    # Actualizar estado
    result = await state_manager_for_test.save_state(updated_state, user_id, session_id)

    # Verificar resultado
    assert "error" not in result
    assert result["session_id"] == session_id

    # Cargar estado actualizado
    loaded_state = await state_manager_for_test.load_state(user_id, session_id)

    # Verificar que el estado se actualizó correctamente
    assert loaded_state == updated_state
    assert loaded_state["key"] == "new_value"
    assert loaded_state["counter"] == 2
    assert "new_key" in loaded_state


@pytest.mark.asyncio
async def test_get_state_field(state_manager_for_test, test_settings: Dict[str, Any]):
    """Prueba la función get_state_field del StateManager."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    state_data = {
        "user": {
            "name": "Test User",
            "preferences": {"theme": "dark", "language": "es"},
        },
        "conversation": {"messages": ["Hello", "World"], "count": 2},
    }

    # Guardar estado
    await state_manager_for_test.save_state(state_data, user_id, session_id)

    # Obtener campos específicos
    theme = await state_manager_for_test.get_state_field(
        user_id, session_id, "user.preferences.theme"
    )
    count = await state_manager_for_test.get_state_field(
        user_id, session_id, "conversation.count"
    )
    messages = await state_manager_for_test.get_state_field(
        user_id, session_id, "conversation.messages"
    )

    # Verificar resultados
    assert theme == "dark"
    assert count == 2
    assert messages == ["Hello", "World"]

    # Campo que no existe
    non_existent = await state_manager_for_test.get_state_field(
        user_id, session_id, "user.age"
    )
    assert non_existent is None


@pytest.mark.asyncio
async def test_update_state_field(
    state_manager_for_test, test_settings: Dict[str, Any]
):
    """Prueba la función update_state_field del StateManager."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    state_data = {
        "user": {"name": "Test User", "preferences": {"theme": "light"}},
        "conversation": {"messages": [], "count": 0},
    }

    # Guardar estado
    await state_manager_for_test.save_state(state_data, user_id, session_id)

    # Actualizar campos específicos
    await state_manager_for_test.update_state_field(
        user_id, session_id, "user.preferences.theme", "dark"
    )
    await state_manager_for_test.update_state_field(
        user_id, session_id, "conversation.messages", ["New message"]
    )
    await state_manager_for_test.update_state_field(
        user_id, session_id, "conversation.count", 1
    )

    # Cargar estado actualizado
    loaded_state = await state_manager_for_test.load_state(user_id, session_id)

    # Verificar resultados
    assert loaded_state["user"]["preferences"]["theme"] == "dark"
    assert loaded_state["conversation"]["messages"] == ["New message"]
    assert loaded_state["conversation"]["count"] == 1

    # Actualizar campo que no existe (debe crearlo)
    await state_manager_for_test.update_state_field(user_id, session_id, "user.age", 30)
    loaded_state = await state_manager_for_test.load_state(user_id, session_id)
    assert loaded_state["user"]["age"] == 30


@pytest.mark.asyncio
async def test_list_user_sessions(
    state_manager_for_test, test_settings: Dict[str, Any]
):
    """Prueba la función list_user_sessions del StateManager."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id1 = str(uuid.uuid4())
    session_id2 = str(uuid.uuid4())

    # Guardar estados
    await state_manager_for_test.save_state({"data": "session1"}, user_id, session_id1)
    await state_manager_for_test.save_state({"data": "session2"}, user_id, session_id2)

    # Listar sesiones
    sessions = await state_manager_for_test.list_user_sessions(user_id)

    # Verificar resultado
    assert len(sessions) >= 2  # Puede haber más sesiones de pruebas anteriores
    session_ids = [s["session_id"] for s in sessions]
    assert session_id1 in session_ids
    assert session_id2 in session_ids

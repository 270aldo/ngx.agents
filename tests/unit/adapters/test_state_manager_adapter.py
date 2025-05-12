"""
Pruebas para el StateManagerAdapter.

Este módulo contiene pruebas para verificar el funcionamiento
del StateManagerAdapter.
"""
import uuid
import pytest
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

# Aplicar patches antes de importar el adaptador
with patch('core.telemetry.telemetry_manager') as mock_telemetry:
    with patch('core.state_manager_optimized.state_manager') as mock_state_manager:
        # Configurar el mock del state_manager_optimized
        async def mock_get_conversation_state(conversation_id):
            return {
                "conversation_id": conversation_id,
                "user_id": "test_user_123",
                "messages": [],
                "metadata": {}
            }
        mock_state_manager.get_conversation_state.side_effect = mock_get_conversation_state
        
        async def mock_set_conversation_state(conversation_id, state):
            return True
        mock_state_manager.set_conversation_state.side_effect = mock_set_conversation_state
        
        async def mock_delete_conversation_state(conversation_id):
            return True
        mock_state_manager.delete_conversation_state.side_effect = mock_delete_conversation_state
        
        async def mock_initialize():
            return None
        mock_state_manager.initialize.side_effect = mock_initialize
        
        # Ahora importar el adaptador
        from infrastructure.adapters.state_manager_adapter import StateManagerAdapter


# Fixture para las configuraciones de prueba
@pytest.fixture
def test_settings() -> Dict[str, Any]:
    return {
        "test_user_id": "test_user_123",
        "test_conversation_id": "test_conversation_456"
    }


@pytest.mark.asyncio
async def test_adapter_initialization():
    """Prueba la inicialización del adaptador."""
    adapter = StateManagerAdapter()
    await adapter.initialize()
    assert adapter is not None


@pytest.mark.asyncio
async def test_save_and_load_state(test_settings):
    """Prueba las funciones save_state y load_state del adaptador."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    state_data = {"key": "value", "nested": {"foo": "bar"}}
    
    # Crear adaptador
    adapter = StateManagerAdapter()
    await adapter.initialize()
    
    # Guardar estado
    result = await adapter.save_state(state_data, user_id, session_id)
    
    # Verificar resultado
    assert "error" not in result
    assert "session_id" in result
    assert result["state_data"] == state_data
    assert result["user_id"] == user_id


@pytest.mark.asyncio
async def test_delete_state(test_settings):
    """Prueba la función delete_state del adaptador."""
    # Datos de prueba
    user_id = test_settings["test_user_id"]
    session_id = str(uuid.uuid4())
    state_data = {"key": "value"}
    
    # Crear adaptador
    adapter = StateManagerAdapter()
    await adapter.initialize()
    
    # Guardar estado
    await adapter.save_state(state_data, user_id, session_id)
    
    # Eliminar estado
    result = await adapter.delete_state(user_id, session_id)
    
    # Verificar resultado
    assert result is True

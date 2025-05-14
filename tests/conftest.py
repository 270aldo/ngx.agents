"""
Configuración de pruebas para el proyecto NGX Agents.

Este módulo contiene fixtures y configuraciones comunes para las pruebas.
"""
import os
import pytest
import json
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Importar componentes del proyecto
from core.settings import Settings
from infrastructure.adapters.state_manager_adapter import StateManagerAdapter

# Alias para compatibilidad con pruebas existentes
StateManager = StateManagerAdapter


@pytest.fixture
def test_settings() -> Dict[str, Any]:
    """
    Fixture que proporciona configuraciones de prueba.
    
    Returns:
        Dict[str, Any]: Configuraciones de prueba
    """
    return {
        "test_user_id": "test-user-id",
        "test_user_email": "test@example.com",
        "valid_test_token": "test-token"
    }


@pytest.fixture
async def state_manager() -> StateManagerAdapter:
    """
    Fixture que proporciona un StateManager para pruebas.
    
    Returns:
        StateManagerAdapter: Instancia de StateManagerAdapter para pruebas
    """
    # Crear un mock del StateManagerAdapter
    manager = MagicMock(spec=StateManagerAdapter)
    
    # Configurar métodos asíncronos
    manager.save_state = AsyncMock()
    manager.load_state = AsyncMock(return_value={})
    manager.delete_state = AsyncMock(return_value=True)
    manager.get_state_field = AsyncMock(return_value=None)
    manager.update_state_field = AsyncMock()
    manager.list_user_sessions = AsyncMock(return_value=[])
    
    # Configurar comportamiento específico
    async def mock_save_state(state_data, user_id, session_id=None):
        session_id = session_id or "test-session-id"
        return {
            "session_id": session_id,
            "user_id": user_id,
            "state_data": state_data
        }
    
    async def mock_load_state(user_id, session_id=None):
        if not session_id:
            return {}
        return {"key": "value"}
    
    # Asignar comportamiento a los mocks
    manager.save_state.side_effect = mock_save_state
    manager.load_state.side_effect = mock_load_state
    
    return manager


@pytest.fixture
def mock_supabase_client():
    """
    Fixture que proporciona un cliente Supabase simulado.
    
    Returns:
        MagicMock: Cliente Supabase simulado
    """
    with patch("clients.supabase_client.SupabaseClient") as mock_client:
        # Configurar métodos del cliente
        mock_instance = MagicMock()
        mock_instance.initialize = AsyncMock()
        mock_instance.get_user = AsyncMock(return_value={"id": "test-user-id", "email": "test@example.com"})
        mock_instance.verify_token = AsyncMock(return_value=True)
        
        # Configurar el método get_instance para devolver la instancia simulada
        mock_client.get_instance.return_value = mock_instance
        
        yield mock_instance

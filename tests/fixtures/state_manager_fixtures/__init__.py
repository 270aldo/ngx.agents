"""Fixtures para el State Manager."""

import pytest
import sys
import os
from typing import Dict, Any
from unittest.mock import patch

# Asegurarse de que el directorio de mocks esté en el path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../mocks"))
)

# Importar el mock de telemetría antes de importar el adaptador
from core.telemetry import telemetry_manager as mock_telemetry_manager


# Aplicar el patch para telemetry_manager
@pytest.fixture
def mock_telemetry():
    with patch("core.telemetry.telemetry_manager", mock_telemetry_manager):
        yield mock_telemetry_manager


# Fixture para las configuraciones de prueba
@pytest.fixture
def test_settings() -> Dict[str, Any]:
    return {
        "test_user_id": "test_user_123",
        "test_conversation_id": "test_conversation_456",
    }


# Fixture para el StateManagerAdapter
@pytest.fixture
async def state_manager(mock_telemetry) -> Any:
    """Fixture para el StateManagerAdapter."""
    # Importar después del patch para asegurar que use el mock
    from infrastructure.adapters.state_manager_adapter import state_manager_adapter

    # Inicializar el adaptador
    await state_manager_adapter.initialize()

    return state_manager_adapter

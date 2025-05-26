"""
Configuración de pruebas para NGX Agents.

Este módulo proporciona fixtures y configuraciones para las pruebas.
"""

import pytest
import uuid
from typing import Dict, Any

from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter


@pytest.fixture
async def state_manager():
    """
    Fixture para el gestor de estado.

    Returns:
        StateManager: Instancia del gestor de estado
    """
    # Inicializar el gestor de estado
    await state_manager_adapter.initialize()

    # Reiniciar contadores para las pruebas
    state_manager_adapter.stats = {
        "operations": 0,
        "optimized_operations": 0,
        "original_operations": 0,
        "errors": 0,
    }

    return state_manager_adapter


@pytest.fixture
async def intent_analyzer():
    """
    Fixture para el analizador de intenciones.

    Returns:
        IntentAnalyzer: Instancia del analizador de intenciones
    """
    # Inicializar el analizador de intenciones
    await intent_analyzer_adapter.initialize()

    return intent_analyzer_adapter


@pytest.fixture
def test_settings() -> Dict[str, Any]:
    """
    Fixture para configuraciones de prueba.

    Returns:
        Dict[str, Any]: Configuraciones de prueba
    """
    return {
        "test_user_id": str(uuid.uuid4()),
        "test_conversation_id": str(uuid.uuid4()),
        "test_session_id": str(uuid.uuid4()),
    }

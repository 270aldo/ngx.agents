"""
Archivo conftest.py unificado para todas las pruebas del proyecto NGX Agents.
Este archivo contiene fixtures compartidos por múltiples pruebas.
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Agregar directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Asegurarse de que el directorio raíz y el directorio de mocks estén en el path
import sys
import os
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, AsyncMock

# No aplicamos patches globales aquí para evitar errores de importación
# Los patches se aplicarán en cada archivo de prueba según sea necesario

# Ahora importar fixtures específicos
from .fixtures.vertex_ai_fixtures import *
from .fixtures.a2a_fixtures import *

# Definir fixtures básicos aquí en lugar de importarlos
@pytest.fixture
def test_settings() -> Dict[str, Any]:
    return {
        "test_user_id": "test_user_123",
        "test_conversation_id": "test_conversation_456"
    }

# Fixtures comunes
@pytest.fixture
def mock_response():
    """Fixture para crear un mock de respuesta HTTP."""
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            self.text = str(json_data)
            
        def json(self):
            return self.json_data
            
    return MockResponse

@pytest.fixture
def mock_vertex_client():
    """Fixture para crear un mock del cliente Vertex AI."""
    with patch('clients.vertex_ai_client.VertexAIClient') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

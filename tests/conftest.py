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

# Importar fixtures específicos
from .fixtures.vertex_ai_fixtures import *
from .fixtures.state_manager_fixtures import *
from .fixtures.a2a_fixtures import *

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

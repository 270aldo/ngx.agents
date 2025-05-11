#!/bin/bash
# Script para limpiar y consolidar pruebas redundantes en el proyecto NGX Agents

set -e  # Salir si hay errores

echo "Iniciando limpieza de pruebas redundantes..."

# Crear directorio para archivos obsoletos (por si acaso)
mkdir -p .obsolete/tests

# 1. Consolidar pruebas de adaptadores
echo "Consolidando pruebas de adaptadores..."

# Crear directorio para pruebas de adaptadores
mkdir -p tests/adapters

# Mover pruebas de adaptadores a un directorio específico
find tests -name "test_*_adapter.py" -exec mv {} tests/adapters/ \;

# 2. Consolidar pruebas de componentes
echo "Consolidando pruebas de componentes..."

# Crear directorio para pruebas de componentes
mkdir -p tests/components

# Mover pruebas de componentes específicos
find tests -name "test_*_optimized.py" -exec mv {} tests/components/ \;
find tests -name "test_*_integration.py" -exec mv {} tests/components/ \;

# 3. Limpiar pruebas duplicadas
echo "Limpiando pruebas duplicadas..."

# Identificar pruebas duplicadas (misma funcionalidad, diferentes nombres)
# Esto requiere análisis manual, pero podemos mover algunas obvias
for file in tests/test_*.py; do
  if [[ -f "tests/components/$(basename $file)" ]]; then
    mv "$file" .obsolete/tests/
  fi
done

# 4. Actualizar imports en archivos de prueba
echo "Actualizando imports en archivos de prueba..."

# Crear script temporal para actualizar imports
cat > update_test_imports.py << 'EOF'
import os
import re

def update_imports_in_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Actualizar imports para adaptadores movidos
    content = re.sub(
        r'from tests import (test_\w+_adapter)',
        r'from tests.adapters import \1',
        content
    )
    
    # Actualizar imports para componentes movidos
    content = re.sub(
        r'from tests import (test_\w+_optimized|test_\w+_integration)',
        r'from tests.components import \1',
        content
    )
    
    with open(file_path, 'w') as file:
        file.write(content)

# Procesar todos los archivos de prueba
for root, _, files in os.walk('tests'):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            update_imports_in_file(file_path)
EOF

python update_test_imports.py
rm update_test_imports.py

# 5. Crear archivo conftest.py unificado
echo "Creando archivo conftest.py unificado..."

# Respaldar conftest.py actual
if [[ -f "tests/conftest.py" ]]; then
  cp tests/conftest.py .obsolete/tests/
fi

# Consolidar todos los archivos conftest
find tests -name "conftest*.py" -not -path "tests/conftest.py" | xargs cat > .obsolete/tests/all_conftest.py

# Crear nuevo conftest.py unificado
cat > tests/conftest.py << 'EOF'
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
EOF

# Crear directorios para fixtures específicos
mkdir -p tests/fixtures/vertex_ai_fixtures
mkdir -p tests/fixtures/state_manager_fixtures
mkdir -p tests/fixtures/a2a_fixtures

# Crear archivos de fixtures básicos
touch tests/fixtures/__init__.py
touch tests/fixtures/vertex_ai_fixtures/__init__.py
touch tests/fixtures/state_manager_fixtures/__init__.py
touch tests/fixtures/a2a_fixtures/__init__.py

echo "Limpieza de pruebas completada."
echo "Revisa que todo funcione correctamente antes de eliminar la carpeta .obsolete/"

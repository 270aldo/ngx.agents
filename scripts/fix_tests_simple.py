#!/usr/bin/env python
"""
Script simplificado para corregir problemas en las pruebas.
"""

import os
import re
from pathlib import Path

def fix_mock_mode():
    """Configura el modo mock en los archivos de prueba."""
    # Directorio raíz del proyecto
    project_root = Path(__file__).parent.parent
    
    # Crear archivo de entorno para pruebas
    env_test_path = project_root / ".env.test"
    
    env_content = """
# Configuración para pruebas
MOCK_MODE=True
MOCK_VERTEX_AI=True
MOCK_A2A=True
ENV=test
LOG_LEVEL=INFO
"""
    
    with open(env_test_path, "w") as f:
        f.write(env_content)
    
    print(f"Creado archivo de entorno para pruebas: {env_test_path}")
    
    # Crear script de ejecución de pruebas
    run_tests_path = project_root / "run_tests_fixed.sh"
    
    run_tests_content = """#!/bin/bash
# Script para ejecutar pruebas con configuración adecuada

# Cargar variables de entorno para pruebas
export MOCK_MODE=True
export MOCK_VERTEX_AI=True
export MOCK_A2A=True
export ENV=test
export LOG_LEVEL=INFO

# Ejecutar pruebas
python -m pytest tests/integration/test_full_system_integration.py -v
"""
    
    with open(run_tests_path, "w") as f:
        f.write(run_tests_content)
    
    # Hacer ejecutable el script
    os.chmod(run_tests_path, 0o755)
    
    print(f"Creado script para ejecutar pruebas: {run_tests_path}")

def create_simple_mock():
    """Crea un mock simple para las pruebas."""
    # Directorio raíz del proyecto
    project_root = Path(__file__).parent.parent
    
    # Crear directorio para mocks si no existe
    mocks_dir = project_root / "tests" / "mocks"
    mocks_dir.mkdir(exist_ok=True, parents=True)
    
    # Crear archivo de mock
    mock_path = mocks_dir / "mock_clients.py"
    
    mock_content = """
# Mock simple para clientes externos

class MockVertexAIClient:
    # Cliente mock para Vertex AI
    
    def __init__(self, settings=None):
        self.settings = settings
        self._initialized = False
    
    async def initialize(self):
        # Inicializar el cliente
        self._initialized = True
        return True
    
    async def generate_content(self, prompt, temperature=0.7, max_tokens=1024):
        # Generar contenido
        return {
            "text": f"Respuesta simulada para: {prompt[:30]}...",
            "finish_reason": "STOP",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            },
            "model": "gemini-1.0-pro"
        }
    
    async def generate_embedding(self, text):
        # Generar embedding
        return [0.1] * 768  # Vector de 768 dimensiones
    
    async def process_multimodal(self, prompt, image_data, temperature=0.7):
        # Procesar contenido multimodal
        return {
            "text": f"Respuesta multimodal simulada para: {prompt[:30]}...",
            "finish_reason": "STOP",
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 30,
                "total_tokens": 50
            },
            "model": "gemini-1.0-pro-vision"
        }
    
    async def get_stats(self):
        # Obtener estadísticas
        return {
            "content_requests": 1,
            "embedding_requests": 1,
            "multimodal_requests": 0,
            "initialized": self._initialized
        }

# Crear archivo __init__.py
with open(Path(__file__).parent / "__init__.py", "w") as f:
    f.write("# Paquete de mocks para pruebas\\n")
"""
    
    with open(mock_path, "w") as f:
        f.write(mock_content)
    
    # Crear archivo __init__.py
    init_path = mocks_dir / "__init__.py"
    with open(init_path, "w") as f:
        f.write("# Paquete de mocks para pruebas\n")
    
    print(f"Creado mock simple en: {mock_path}")

def create_test_helper():
    """Crea un helper para las pruebas."""
    # Directorio raíz del proyecto
    project_root = Path(__file__).parent.parent
    
    # Crear directorio para helpers si no existe
    helpers_dir = project_root / "tests" / "helpers"
    helpers_dir.mkdir(exist_ok=True, parents=True)
    
    # Crear archivo de helper
    helper_path = helpers_dir / "test_helper.py"
    
    helper_content = """
# Helper para pruebas

import os
import asyncio
from pathlib import Path

# Configurar modo mock
os.environ["MOCK_MODE"] = "True"
os.environ["MOCK_VERTEX_AI"] = "True"
os.environ["MOCK_A2A"] = "True"
os.environ["ENV"] = "test"

def get_new_event_loop():
    """Obtiene un nuevo bucle de eventos."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop

def run_async(coro):
    """Ejecuta una corutina de forma síncrona."""
    loop = get_new_event_loop()
    return loop.run_until_complete(coro)
"""
    
    with open(helper_path, "w") as f:
        f.write(helper_content)
    
    # Crear archivo __init__.py
    init_path = helpers_dir / "__init__.py"
    with open(init_path, "w") as f:
        f.write("# Paquete de helpers para pruebas\n")
    
    print(f"Creado helper para pruebas: {helper_path}")

def create_conftest():
    """Crea un archivo conftest.py para configurar pytest."""
    # Directorio raíz del proyecto
    project_root = Path(__file__).parent.parent
    
    # Crear archivo conftest.py
    conftest_path = project_root / "tests" / "conftest.py"
    
    conftest_content = """
# Configuración global para pytest

import os
import pytest
import asyncio

# Configurar modo mock
os.environ["MOCK_MODE"] = "True"
os.environ["MOCK_VERTEX_AI"] = "True"
os.environ["MOCK_A2A"] = "True"
os.environ["ENV"] = "test"

@pytest.fixture(scope="session")
def event_loop():
    """Crear un nuevo bucle de eventos para cada sesión de prueba."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
"""
    
    with open(conftest_path, "w") as f:
        f.write(conftest_content)
    
    print(f"Creado archivo conftest.py: {conftest_path}")

def main():
    """Función principal."""
    print("Aplicando correcciones simples para las pruebas...")
    
    # Configurar modo mock
    fix_mock_mode()
    
    # Crear mock simple
    create_simple_mock()
    
    # Crear helper para pruebas
    create_test_helper()
    
    # Crear conftest.py
    create_conftest()
    
    print("\n¡Listo! Ahora puedes ejecutar las pruebas con la configuración adecuada.")
    print("Ejecuta: bash run_tests_fixed.sh")

if __name__ == "__main__":
    main()

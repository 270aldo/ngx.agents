#!/usr/bin/env python
"""
Script para crear un mock completo de Vertex AI para las pruebas.

Este script crea un archivo mock_vertex_ai_client.py en el directorio tests/fixtures
que implementa un cliente mock completo de Vertex AI para las pruebas.
"""

import os
from pathlib import Path

def create_mock_vertex_ai_client():
    """
    Crea un cliente mock completo de Vertex AI para las pruebas.
    """
    # Directorio raíz del proyecto
    project_root = Path(__file__).parent.parent
    
    # Crear directorio de fixtures si no existe
    fixtures_dir = project_root / "tests" / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    
    # Crear directorio de fixtures de Vertex AI si no existe
    vertex_fixtures_dir = fixtures_dir / "vertex_ai_fixtures"
    vertex_fixtures_dir.mkdir(exist_ok=True)
    
    # Archivo de cliente mock
    mock_client_path = vertex_fixtures_dir / "mock_vertex_ai_client.py"
    
    # Contenido del cliente mock
    mock_client_content = """
import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Union

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockVertexAIClient:
    # Cliente mock de Vertex AI para pruebas
    
    def __init__(self, settings=None):
        """Inicializa el cliente mock."""
        self.settings = settings
        self._initialized = False
        self._stats = {
            "content_requests": 0,
            "embedding_requests": 0,
            "multimodal_requests": 0,
            "batch_embedding_requests": 0,
            "document_requests": 0,
            "latency_ms": {
                "content_generation": [],
                "embedding_generation": [],
                "multimodal_processing": []
            },
            "latency_avg_ms": {
                "content_generation": 0,
                "embedding_generation": 0,
                "multimodal_processing": 0
            },
            "tokens": {
                "prompt": 0,
                "completion": 0,
                "total": 0
            },
            "errors": {},
            "cache": {
                "hits": 0,
                "misses": 0,
                "size": 0,
                "evictions": 0,
                "hit_ratio": 0
            },
            "connection_pool": {
                "created": 0,
                "reused": 0,
                "acquired": 0,
                "released": 0,
                "current_in_use": 0
            },
            "initialized": False
        }
        
        # Crear caché en memoria
        self._cache = {}
        
        # Simular inicialización
        logger.info("MockVertexAIClient: Inicializado")
    
    async def initialize(self):
        """Inicializa el cliente mock."""
        logger.info("MockVertexAIClient: initialize() llamado")
        self._initialized = True
        self._stats["initialized"] = True
        return True
    
    async def generate_content(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1024):
        """Genera contenido a partir de un prompt."""
        logger.info(f"MockVertexAIClient: generate_content() llamado con prompt: {prompt[:50]}...")
        
        # Simular latencia
        start_time = time.time()
        await asyncio.sleep(0.1)  # Simular latencia de 100ms
        
        # Incrementar contador de solicitudes
        self._stats["content_requests"] += 1
        
        # Calcular latencia
        latency = (time.time() - start_time) * 1000
        self._stats["latency_ms"]["content_generation"].append(latency)
        
        # Calcular promedio de latencia
        if self._stats["latency_ms"]["content_generation"]:
            self._stats["latency_avg_ms"]["content_generation"] = sum(self._stats["latency_ms"]["content_generation"]) / len(self._stats["latency_ms"]["content_generation"])
        
        # Simular tokens
        prompt_tokens = len(prompt.split())
        completion_tokens = 50  # Valor arbitrario para pruebas
        total_tokens = prompt_tokens + completion_tokens
        
        # Actualizar estadísticas de tokens
        self._stats["tokens"]["prompt"] += prompt_tokens
        self._stats["tokens"]["completion"] += completion_tokens
        self._stats["tokens"]["total"] += total_tokens
        
        # Generar respuesta simulada
        response = {
            "text": f"Respuesta simulada para: {prompt[:30]}...",
            "finish_reason": "STOP",
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            "model": "gemini-1.0-pro"
        }
        
        return response
    
    async def generate_embedding(self, text: str):
        """Genera un embedding a partir de un texto."""
        logger.info(f"MockVertexAIClient: generate_embedding() llamado con texto: {text[:50]}...")
        
        # Simular latencia
        start_time = time.time()
        await asyncio.sleep(0.05)  # Simular latencia de 50ms
        
        # Incrementar contador de solicitudes
        self._stats["embedding_requests"] += 1
        
        # Calcular latencia
        latency = (time.time() - start_time) * 1000
        self._stats["latency_ms"]["embedding_generation"].append(latency)
        
        # Calcular promedio de latencia
        if self._stats["latency_ms"]["embedding_generation"]:
            self._stats["latency_avg_ms"]["embedding_generation"] = sum(self._stats["latency_ms"]["embedding_generation"]) / len(self._stats["latency_ms"]["embedding_generation"])
        
        # Generar embedding simulado (vector de 768 dimensiones con valores aleatorios)
        import random
        embedding = [random.uniform(-1, 1) for _ in range(768)]
        
        return embedding
    
    async def process_multimodal(self, prompt: str, image_data: bytes, temperature: float = 0.7):
        """Procesa contenido multimodal."""
        logger.info(f"MockVertexAIClient: process_multimodal() llamado con prompt: {prompt[:50]}...")
        
        # Simular latencia
        start_time = time.time()
        await asyncio.sleep(0.2)  # Simular latencia de 200ms
        
        # Incrementar contador de solicitudes
        self._stats["multimodal_requests"] += 1
        
        # Calcular latencia
        latency = (time.time() - start_time) * 1000
        self._stats["latency_ms"]["multimodal_processing"].append(latency)
        
        # Calcular promedio de latencia
        if self._stats["latency_ms"]["multimodal_processing"]:
            self._stats["latency_avg_ms"]["multimodal_processing"] = sum(self._stats["latency_ms"]["multimodal_processing"]) / len(self._stats["latency_ms"]["multimodal_processing"])
        
        # Simular tokens
        prompt_tokens = len(prompt.split()) + 100  # Añadir tokens para la imagen
        completion_tokens = 80  # Valor arbitrario para pruebas
        total_tokens = prompt_tokens + completion_tokens
        
        # Actualizar estadísticas de tokens
        self._stats["tokens"]["prompt"] += prompt_tokens
        self._stats["tokens"]["completion"] += completion_tokens
        self._stats["tokens"]["total"] += total_tokens
        
        # Generar respuesta simulada
        response = {
            "text": f"Respuesta multimodal simulada para: {prompt[:30]}...",
            "finish_reason": "STOP",
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            "model": "gemini-1.0-pro-vision"
        }
        
        return response
    
    async def get_stats(self):
        """Obtiene estadísticas del cliente."""
        return self._stats
    
    async def _get_from_cache(self, key):
        """Obtiene un valor de la caché."""
        if key in self._cache:
            self._stats["cache"]["hits"] += 1
            return self._cache[key]
        else:
            self._stats["cache"]["misses"] += 1
            return None
    
    async def _save_to_cache(self, key, value):
        """Guarda un valor en la caché."""
        self._cache[key] = value
        self._stats["cache"]["size"] = len(self._cache)
        
        # Calcular hit ratio
        total = self._stats["cache"]["hits"] + self._stats["cache"]["misses"]
        if total > 0:
            self._stats["cache"]["hit_ratio"] = self._stats["cache"]["hits"] / total
        
        return True
"""
    
    # Escribir el archivo
    with open(mock_client_path, "w") as f:
        f.write(mock_client_content)
    
    print(f"Creado cliente mock de Vertex AI en: {mock_client_path}")
    
    # Crear archivo __init__.py para que el directorio sea un paquete
    init_path = vertex_fixtures_dir / "__init__.py"
    if not init_path.exists():
        with open(init_path, "w") as f:
            f.write("# Paquete de fixtures de Vertex AI\n")
        print(f"Creado archivo __init__.py en: {vertex_fixtures_dir}")

def create_mock_import_patch():
    """
    Crea un archivo de parche para importar el cliente mock en las pruebas.
    """
    # Directorio raíz del proyecto
    project_root = Path(__file__).parent.parent
    
    # Directorio de fixtures
    fixtures_dir = project_root / "tests" / "fixtures"
    
    # Archivo de parche
    patch_path = fixtures_dir / "patch_vertex_ai.py"
    
    # Contenido del archivo de parche
    patch_content = """
import sys
from pathlib import Path

# Obtener la ruta del directorio actual
current_dir = Path(__file__).parent

# Añadir el directorio de fixtures al path
vertex_fixtures_dir = current_dir / "vertex_ai_fixtures"
sys.path.insert(0, str(vertex_fixtures_dir))

# Importar el cliente mock
from mock_vertex_ai_client import MockVertexAIClient

# Parchar el módulo clients.vertex_ai.client
import sys
sys.modules["clients.vertex_ai.client"] = type("", (), {})
sys.modules["clients.vertex_ai.client"].VertexAIClient = MockVertexAIClient

print("Parchado clients.vertex_ai.client.VertexAIClient con MockVertexAIClient")
"""
    
    # Escribir el archivo
    with open(patch_path, "w") as f:
        f.write(patch_content)
    
    print(f"Creado archivo de parche en: {patch_path}")

def patch_test_files():
    """
    Parcha los archivos de prueba para usar el cliente mock.
    """
    # Directorio raíz del proyecto
    project_root = Path(__file__).parent.parent
    
    # Buscar archivos de prueba de integración
    integration_test_files = []
    for pattern in ["**/test_*integration*.py", "**/test_*system*.py"]:
        for file_path in project_root.glob(pattern):
            if file_path.is_file():
                integration_test_files.append(file_path)
    
    # Parchar cada archivo
    for file_path in integration_test_files:
        print(f"Parchando archivo: {file_path}")
        
        with open(file_path, "r") as f:
            content = f.read()
        
        # Verificar si ya está parchado
        if "patch_vertex_ai" not in content:
            # Añadir importación del parche al inicio del archivo
            import_patch = """
import os
# Configurar modo mock para pruebas
os.environ["MOCK_MODE"] = "True"
os.environ["MOCK_VERTEX_AI"] = "True"
os.environ["MOCK_A2A"] = "True"

# Importar parche para Vertex AI
import sys
from pathlib import Path
# Añadir directorio de fixtures al path
fixtures_dir = Path(__file__).parent.parent / "fixtures"
if fixtures_dir.exists():
    sys.path.insert(0, str(fixtures_dir))
    try:
        import patch_vertex_ai
    except ImportError:
        print("No se pudo importar patch_vertex_ai")

"""
            
            # Encontrar la primera importación
            import_pattern = "import "
            import_index = content.find(import_pattern)
            
            if import_index >= 0:
                # Insertar antes de la primera importación
                modified_content = content[:import_index] + import_patch + content[import_index:]
                
                with open(file_path, "w") as f:
                    f.write(modified_content)
                
                print(f"Parchado archivo: {file_path}")
            else:
                print(f"No se encontró un punto de inserción adecuado en {file_path}")
        else:
            print(f"El archivo {file_path} ya está parchado")

def main():
    """Función principal."""
    print("Creando cliente mock de Vertex AI...")
    create_mock_vertex_ai_client()
    
    print("\nCreando archivo de parche...")
    create_mock_import_patch()
    
    print("\nParchando archivos de prueba...")
    patch_test_files()
    
    print("\n¡Listo! Ahora puedes ejecutar las pruebas con el cliente mock de Vertex AI.")

if __name__ == "__main__":
    main()

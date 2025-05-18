#!/usr/bin/env python
"""
Script para corregir problemas de bucles de eventos asíncronos en las pruebas.

Este script modifica los fixtures de prueba para usar un único bucle de eventos
y evitar problemas de bloqueo entre diferentes bucles.
"""

import os
import re
from pathlib import Path

def fix_async_event_loop_in_tests():
    """
    Modifica los archivos de prueba para usar un único bucle de eventos.
    """
    # Directorio raíz del proyecto
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"
    
    # Patrón para buscar la obtención del bucle de eventos
    get_event_loop_pattern = r"loop\s*=\s*asyncio\.get_event_loop\(\)"
    
    # Reemplazo que usa new_event_loop en su lugar
    replacement = "loop = asyncio.new_event_loop()\n    asyncio.set_event_loop(loop)"
    
    # Contador de archivos modificados
    modified_files = 0
    
    # Recorrer todos los archivos de prueba
    for root, _, files in os.walk(tests_dir):
        for file in files:
            if file.endswith(".py") and file.startswith("test_"):
                file_path = os.path.join(root, file)
                
                # Leer el contenido del archivo
                with open(file_path, "r") as f:
                    content = f.read()
                
                # Verificar si necesita modificación
                if re.search(get_event_loop_pattern, content):
                    # Aplicar el reemplazo
                    modified_content = re.sub(get_event_loop_pattern, replacement, content)
                    
                    # Guardar el archivo modificado
                    with open(file_path, "w") as f:
                        f.write(modified_content)
                    
                    modified_files += 1
                    print(f"Modificado: {file_path}")
    
    print(f"\nTotal de archivos modificados: {modified_files}")

def fix_intent_analyzer_cache():
    """
    Corrige la implementación del método _get_from_intent_cache en IntentAnalyzerOptimized.
    """
    intent_analyzer_path = Path(__file__).parent.parent / "core" / "intent_analyzer_optimized.py"
    
    if not intent_analyzer_path.exists():
        print(f"No se encontró el archivo: {intent_analyzer_path}")
        return
    
    with open(intent_analyzer_path, "r") as f:
        content = f.read()
    
    # Verificar si ya existe el método
    if "_get_from_intent_cache" not in content:
        # Buscar la clase IntentAnalyzerOptimized
        class_pattern = r"class IntentAnalyzerOptimized\(.*?\):"
        class_match = re.search(class_pattern, content)
        
        if class_match:
            # Encontrar el final de la clase (aproximadamente)
            class_start = class_match.start()
            
            # Método a añadir
            cache_method = """
    async def _get_from_intent_cache(self, query_hash):
        # Obtiene una intención desde la caché si existe
        if not hasattr(self, '_intent_cache'):
            self._intent_cache = {}
        
        return self._intent_cache.get(query_hash)
    
    async def _save_to_intent_cache(self, query_hash, intents):
        # Guarda una intención en la caché
        if not hasattr(self, '_intent_cache'):
            self._intent_cache = {}
            
        self._intent_cache[query_hash] = intents
"""
            
            # Insertar el método cerca del final de la clase
            # Esto es una aproximación, idealmente se analizaría la estructura completa
            lines = content.split("\n")
            insertion_point = len(lines) - 5  # Aproximadamente antes del final del archivo
            
            lines.insert(insertion_point, cache_method)
            modified_content = "\n".join(lines)
            
            with open(intent_analyzer_path, "w") as f:
                f.write(modified_content)
            
            print(f"Añadido método _get_from_intent_cache a {intent_analyzer_path}")
        else:
            print(f"No se encontró la clase IntentAnalyzerOptimized en {intent_analyzer_path}")
    else:
        print(f"El método _get_from_intent_cache ya existe en {intent_analyzer_path}")

def fix_mock_vertex_ai_client():
    """
    Corrige la implementación del cliente mock de Vertex AI.
    """
    # Buscar el archivo del cliente mock
    project_root = Path(__file__).parent.parent
    mock_files = []
    
    for root, _, files in os.walk(project_root / "tests"):
        for file in files:
            if "mock" in file.lower() and "vertex" in file.lower() and file.endswith(".py"):
                mock_files.append(os.path.join(root, file))
    
    if not mock_files:
        print("No se encontraron archivos mock de Vertex AI")
        return
    
    for mock_file in mock_files:
        with open(mock_file, "r") as f:
            content = f.read()
        
        # Verificar si ya existe el método initialize
        if "def initialize" not in content and "MockVertexAIClient" in content:
            # Buscar la clase MockVertexAIClient
            class_pattern = r"class MockVertexAIClient\(.*?\):"
            class_match = re.search(class_pattern, content)
            
            if class_match:
                # Método a añadir
                initialize_method = """
    async def initialize(self):
        # Método de inicialización para compatibilidad
        return True
"""
                
                # Insertar el método después de la definición de la clase
                modified_content = content[:class_match.end()] + initialize_method + content[class_match.end():]
                
                with open(mock_file, "w") as f:
                    f.write(modified_content)
                
                print(f"Añadido método initialize a {mock_file}")
            else:
                print(f"No se encontró la clase MockVertexAIClient en {mock_file}")
        else:
            print(f"El método initialize ya existe o no se requiere en {mock_file}")

def main():
    """Función principal que ejecuta todas las correcciones."""
    print("Iniciando correcciones para las pruebas...")
    
    # Corregir problemas de bucles de eventos
    fix_async_event_loop_in_tests()
    
    # Corregir implementación de caché en IntentAnalyzer
    fix_intent_analyzer_cache()
    
    # Corregir cliente mock de Vertex AI
    fix_mock_vertex_ai_client()
    
    print("\nCorrecciones completadas. Ejecuta las pruebas nuevamente para verificar.")

if __name__ == "__main__":
    main()

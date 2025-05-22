"""
Script para actualizar las referencias a los modelos de Gemini en el proyecto.

Este script actualiza las referencias a los modelos de Gemini en el código,
para usar Gemini 2.5 Pro para el orquestador y Gemini 2.5 Flash para los agentes especializados.
"""

import os
import re
import sys
from typing import Dict, List, Any, Tuple

# Añadir directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Archivos a modificar para actualizar referencias a modelos de Gemini
FILES_TO_MODIFY = {
    'clients/vertex_ai/client.py': [
        # Actualizar modelo por defecto
        (r'DEFAULT_MODEL = "gemini-1.5-pro"', 'DEFAULT_MODEL = "gemini-2.5-pro"'),
        # Actualizar lista de modelos disponibles
        (r'AVAILABLE_MODELS = \["gemini-1.0-pro", "gemini-1.5-pro", "gemini-1.5-flash"\]', 
         'AVAILABLE_MODELS = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]'),
    ],
    'infrastructure/adapters/orchestrator_adapter.py': [
        # Actualizar modelo para el orquestador
        (r'model_name = os\.environ\.get\("VERTEX_MODEL", "gemini-1.5-pro"\)', 
         'model_name = os.environ.get("VERTEX_ORCHESTRATOR_MODEL", "gemini-2.5-pro")'),
    ],
    # Actualizar modelos para agentes especializados
    'infrastructure/adapters/biometrics_insight_engine_adapter.py': [
        (r'model_name = os\.environ\.get\("VERTEX_MODEL", "gemini-1.5-pro"\)', 
         'model_name = os.environ.get("VERTEX_AGENT_MODEL", "gemini-2.5-flash")'),
    ],
    'infrastructure/adapters/recovery_corrective_adapter.py': [
        (r'model_name = os\.environ\.get\("VERTEX_MODEL", "gemini-1.5-pro"\)', 
         'model_name = os.environ.get("VERTEX_AGENT_MODEL", "gemini-2.5-flash")'),
    ],
    'infrastructure/adapters/embedding_adapter.py': [
        (r'model_name = os\.environ\.get\("VERTEX_EMBEDDING_MODEL", "textembedding-gecko"\)', 
         'model_name = os.environ.get("VERTEX_EMBEDDING_MODEL", "text-embedding-large-exp-03-07")'),
    ],
    # Actualizar archivos de configuración
    '.env.example': [
        (r'VERTEX_MODEL=gemini-1.5-pro', 'VERTEX_ORCHESTRATOR_MODEL=gemini-2.5-pro\nVERTEX_AGENT_MODEL=gemini-2.5-flash'),
        (r'VERTEX_EMBEDDING_MODEL=textembedding-gecko', 'VERTEX_EMBEDDING_MODEL=text-embedding-large-exp-03-07'),
    ],
    '.env.example.updated': [
        (r'VERTEX_MODEL=gemini-1.5-pro', 'VERTEX_ORCHESTRATOR_MODEL=gemini-2.5-pro\nVERTEX_AGENT_MODEL=gemini-2.5-flash'),
        (r'VERTEX_EMBEDDING_MODEL=textembedding-gecko', 'VERTEX_EMBEDDING_MODEL=text-embedding-large-exp-03-07'),
    ],
}

def modify_files() -> Dict[str, int]:
    """
    Modifica archivos para actualizar referencias a modelos de Gemini.
    
    Returns:
        Dict[str, int]: Diccionario con archivos modificados y número de cambios
    """
    modified_files = {}
    
    for file_path, patterns in FILES_TO_MODIFY.items():
        full_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                changes = 0
                
                for pattern, replacement in patterns:
                    # Reemplazar el patrón con el reemplazo
                    new_content = re.sub(pattern, replacement, content)
                    if new_content != content:
                        changes += 1
                        content = new_content
                
                if content != original_content:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    modified_files[file_path] = changes
                    print(f"Archivo modificado: {file_path} ({changes} cambios)")
                else:
                    print(f"No se encontraron referencias a modelos de Gemini en: {file_path}")
            except Exception as e:
                print(f"Error al modificar archivo {file_path}: {str(e)}")
        else:
            print(f"Archivo no encontrado: {file_path}")
    
    return modified_files

def find_all_model_references() -> Dict[str, List[str]]:
    """
    Busca todas las referencias a modelos de Gemini en el proyecto.
    
    Returns:
        Dict[str, List[str]]: Diccionario con archivos y líneas que contienen referencias
    """
    references = {}
    
    # Patrones a buscar
    patterns = [
        r'gemini-1\.0',
        r'gemini-1\.5',
        r'textembedding-gecko',
    ]
    
    # Directorios a excluir
    exclude_dirs = [
        '.git',
        'venv',
        'env',
        '__pycache__',
        'node_modules',
    ]
    
    # Extensiones a incluir
    include_extensions = [
        '.py',
        '.md',
        '.env',
        '.example',
        '.json',
        '.yaml',
        '.yml',
    ]
    
    # Recorrer directorios y archivos
    for root, dirs, files in os.walk(os.getcwd()):
        # Excluir directorios
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            # Verificar extensión
            if not any(file.endswith(ext) for ext in include_extensions):
                continue
            
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                file_references = []
                for i, line in enumerate(lines):
                    for pattern in patterns:
                        if re.search(pattern, line):
                            file_references.append(f"Línea {i+1}: {line.strip()}")
                
                if file_references:
                    # Convertir a ruta relativa
                    rel_path = os.path.relpath(file_path, os.getcwd())
                    references[rel_path] = file_references
            except Exception as e:
                print(f"Error al leer archivo {file_path}: {str(e)}")
    
    return references

def main():
    """Función principal."""
    print("Iniciando actualización de modelos de Gemini...")
    
    # Buscar todas las referencias a modelos de Gemini
    print("Buscando referencias a modelos de Gemini...")
    references = find_all_model_references()
    
    print(f"Se encontraron referencias en {len(references)} archivos:")
    for file, lines in references.items():
        print(f"  - {file}: {len(lines)} referencias")
    
    # Preguntar si se quiere continuar con la actualización
    response = input("\n¿Desea continuar con la actualización de modelos? (s/n): ")
    if response.lower() != 's':
        print("Actualización cancelada.")
        return
    
    # Modificar archivos para actualizar referencias
    modified_files = modify_files()
    
    # Resumen
    print("\nResumen de la actualización:")
    print(f"Archivos modificados: {len(modified_files)}")
    for file, changes in modified_files.items():
        print(f"  - {file} ({changes} cambios)")
    
    print("\nActualización completada.")
    print("\nNota: Es posible que haya más referencias a modelos de Gemini en el proyecto.")
    print("Revise los archivos listados anteriormente para actualizar manualmente si es necesario.")

if __name__ == "__main__":
    main()

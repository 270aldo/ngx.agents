"""
Script para limpiar todo lo relacionado con Pinecone del proyecto.

Este script elimina archivos, directorios y referencias a Pinecone en el código,
ya que se ha migrado completamente a Vertex AI Vector Search.
"""

import os
import re
import shutil
import sys
from typing import List, Dict, Any, Tuple

# Añadir directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Archivos y directorios a eliminar
FILES_TO_REMOVE = [
    'scripts/test_pinecone_integration.py',
    'tests/test_clients/test_pinecone_client.py',
]

DIRS_TO_REMOVE = [
    'clients/pinecone',
]

# Archivos a modificar para eliminar referencias a Pinecone
FILES_TO_MODIFY = {
    'core/embeddings_manager.py': [
        # Patrones para eliminar importaciones
        r'from clients\.pinecone\.pinecone_client import PineconeClient\n',
        # Patrones para eliminar la configuración de Pinecone
        r'            "pinecone": \{\n                "api_key": os\.environ\.get\("PINECONE_API_KEY"\),\n                "environment": os\.environ\.get\("PINECONE_ENVIRONMENT", "[^"]+"\),\n                "index_name": os\.environ\.get\("PINECONE_INDEX_NAME", "[^"]+"\),\n                "dimension": get_env_int\("PINECONE_DIMENSION", \d+\),\n                "metric": os\.environ\.get\("PINECONE_METRIC", "[^"]+"\)\n            \}(,?)\n',
        # Patrones para eliminar código relacionado con Pinecone en _initialize_vector_store
        r'        elif vector_store_type == "pinecone":\n            # Verificar si hay una API key de Pinecone\n            if not self\.config\.get\("pinecone", \{\}\)\.get\("api_key"\):\n                logger\.warning\("No se encontró API key de Pinecone\. Usando almacenamiento en memoria\."\)\n                return MemoryVectorStore\(\)\n            \n            # Inicializar cliente de Pinecone\n            pinecone_client = PineconeClient\(self\.config\.get\("pinecone"\)\)\n            return PineconeVectorStore\(pinecone_client\)\n',
    ],
    'infrastructure/adapters/vector_store_adapter.py': [
        # Patrones para eliminar la clase PineconeVectorStore
        r'class PineconeVectorStore\(VectorStoreAdapter\):.*?def get_stats.*?return stats\n\n',
    ],
    '.env.example': [
        # Patrones para eliminar variables de entorno de Pinecone
        r'# Configuración de Pinecone\nPINECONE_API_KEY=tu-api-key-pinecone\nPINECONE_ENVIRONMENT=us-west1-gcp\nPINECONE_INDEX_NAME=ngx-embeddings\nPINECONE_DIMENSION=768\nPINECONE_METRIC=cosine\n\n',
    ],
    '.env.example.updated': [
        # Patrones para eliminar variables de entorno de Pinecone
        r'# Configuración de Pinecone\nPINECONE_API_KEY=tu-api-key-pinecone\nPINECONE_ENVIRONMENT=us-west1-gcp\nPINECONE_INDEX_NAME=ngx-embeddings\nPINECONE_DIMENSION=768\nPINECONE_METRIC=cosine\n\n',
    ],
    '.env.example.vertex_ai_rag': [
        # Patrones para eliminar variables de entorno de Pinecone
        r'# Configuración de Pinecone \(legacy\)\nPINECONE_API_KEY=tu-api-key-pinecone\nPINECONE_ENVIRONMENT=us-west1-gcp\nPINECONE_INDEX_NAME=ngx-embeddings\nPINECONE_DIMENSION=768\nPINECONE_METRIC=cosine\n\n',
    ],
}

def remove_files_and_dirs() -> Tuple[List[str], List[str]]:
    """
    Elimina archivos y directorios relacionados con Pinecone.
    
    Returns:
        Tuple[List[str], List[str]]: Listas de archivos y directorios eliminados
    """
    removed_files = []
    removed_dirs = []
    
    # Eliminar archivos
    for file_path in FILES_TO_REMOVE:
        full_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                removed_files.append(file_path)
                print(f"Archivo eliminado: {file_path}")
            except Exception as e:
                print(f"Error al eliminar archivo {file_path}: {str(e)}")
        else:
            print(f"Archivo no encontrado: {file_path}")
    
    # Eliminar directorios
    for dir_path in DIRS_TO_REMOVE:
        full_path = os.path.join(os.getcwd(), dir_path)
        if os.path.exists(full_path):
            try:
                shutil.rmtree(full_path)
                removed_dirs.append(dir_path)
                print(f"Directorio eliminado: {dir_path}")
            except Exception as e:
                print(f"Error al eliminar directorio {dir_path}: {str(e)}")
        else:
            print(f"Directorio no encontrado: {dir_path}")
    
    return removed_files, removed_dirs

def modify_files() -> Dict[str, int]:
    """
    Modifica archivos para eliminar referencias a Pinecone.
    
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
                
                for pattern in patterns:
                    # Usar re.DOTALL para que '.' coincida con saltos de línea
                    new_content = re.sub(pattern, '', content, flags=re.DOTALL)
                    if new_content != content:
                        changes += 1
                        content = new_content
                
                if content != original_content:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    modified_files[file_path] = changes
                    print(f"Archivo modificado: {file_path} ({changes} cambios)")
                else:
                    print(f"No se encontraron referencias a Pinecone en: {file_path}")
            except Exception as e:
                print(f"Error al modificar archivo {file_path}: {str(e)}")
        else:
            print(f"Archivo no encontrado: {file_path}")
    
    return modified_files

def main():
    """Función principal."""
    print("Iniciando limpieza de Pinecone...")
    
    # Eliminar archivos y directorios
    removed_files, removed_dirs = remove_files_and_dirs()
    
    # Modificar archivos para eliminar referencias a Pinecone
    modified_files = modify_files()
    
    # Resumen
    print("\nResumen de la limpieza:")
    print(f"Archivos eliminados: {len(removed_files)}")
    for file in removed_files:
        print(f"  - {file}")
    
    print(f"Directorios eliminados: {len(removed_dirs)}")
    for directory in removed_dirs:
        print(f"  - {directory}")
    
    print(f"Archivos modificados: {len(modified_files)}")
    for file, changes in modified_files.items():
        print(f"  - {file} ({changes} cambios)")
    
    print("\nLimpieza completada.")

if __name__ == "__main__":
    main()

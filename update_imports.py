#!/usr/bin/env python3
"""
Script para actualizar las importaciones en todos los archivos del proyecto
para reflejar la nueva estructura de directorios.
"""
import os
import re
import glob

def update_imports_in_file(file_path):
    """Actualiza las importaciones en un archivo."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Definir los patrones de reemplazo
    replacements = [
        (r'from utils\.gemini_client import', 'from clients.gemini_client import'),
        (r'from utils\.supabase_client import', 'from clients.supabase_client import'),
        (r'from utils\.mcp_toolkit import', 'from tools.mcp_toolkit import'),
        (r'from utils\.mcp_client import', 'from tools.mcp_client import'),
        (r'from utils\.protocol_compliance import', 'from tools.protocol_compliance import'),
        (r'from \.a2a_agent import A2AAgent', 'from agents.base.a2a_agent import A2AAgent'),
        (r'from skills\.supabase_skills import', 'from tools.supabase_tools import'),
        (r'from skills\.gcs_skills import', 'from tools.gcs_tools import'),
        (r'from skills\.gemini_skills import', 'from tools.gemini_tools import'),
        (r'from skills\.vertex_skills import', 'from tools.vertex_tools import'),
        (r'from skills\.vertex_gemini_skills import', 'from tools.vertex_gemini_tools import'),
        (r'from skills\.perplexity_skills import', 'from tools.perplexity_tools import'),
    ]
    
    # Aplicar los reemplazos
    modified = False
    new_content = content
    for pattern, replacement in replacements:
        if re.search(pattern, new_content):
            new_content = re.sub(pattern, replacement, new_content)
            modified = True
    
    # Guardar el archivo si se modificó
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Actualizado: {file_path}")
    
    return modified

def main():
    """Función principal."""
    # Obtener todos los archivos Python en el proyecto
    python_files = glob.glob('agents/**/*.py', recursive=True)
    python_files += glob.glob('app/**/*.py', recursive=True)
    python_files += glob.glob('tools/**/*.py', recursive=True)
    python_files += glob.glob('core/**/*.py', recursive=True)
    python_files += glob.glob('clients/**/*.py', recursive=True)
    python_files += glob.glob('tests/**/*.py', recursive=True)
    
    # Eliminar duplicados
    python_files = list(set(python_files))
    
    # Actualizar las importaciones en cada archivo
    updated_count = 0
    for file_path in python_files:
        if update_imports_in_file(file_path):
            updated_count += 1
    
    print(f"Total de archivos actualizados: {updated_count}")

if __name__ == "__main__":
    main()

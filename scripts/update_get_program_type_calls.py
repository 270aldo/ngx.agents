#!/usr/bin/env python
"""
Script para actualizar las llamadas al método _get_program_type_from_profile
para que utilicen la versión asíncrona correctamente.
"""
import re
import sys
import os

def update_file(file_path):
    """
    Actualiza las llamadas a _get_program_type_from_profile en el archivo especificado.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patrón para encontrar llamadas al método _get_program_type_from_profile
    pattern = r'(\s+)program_type = self\._get_program_type_from_profile\((.*?)\)'
    replacement = r'\1program_type = await self._get_program_type_from_profile(\2)'
    
    # Realizar la sustitución
    updated_content = re.sub(pattern, replacement, content)
    
    # Guardar el archivo actualizado
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"Archivo actualizado: {file_path}")

def main():
    """
    Función principal.
    """
    if len(sys.argv) < 2:
        print("Uso: python update_get_program_type_calls.py <ruta_al_archivo>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: El archivo {file_path} no existe.")
        sys.exit(1)
    
    update_file(file_path)
    print("Proceso completado.")

if __name__ == "__main__":
    main()

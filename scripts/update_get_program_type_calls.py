#!/usr/bin/env python
"""
Script para actualizar las llamadas a _get_program_type_from_profile en los adaptadores.

Este script busca y actualiza las implementaciones de _get_program_type_from_profile
en los adaptadores para que utilicen la implementación de BaseAgentAdapter.
"""

import os
import re
import argparse
from typing import List, Tuple


def find_adapter_files(directory: str) -> List[str]:
    """
    Encuentra todos los archivos de adaptadores en el directorio especificado.

    Args:
        directory: Directorio donde buscar los archivos de adaptadores

    Returns:
        Lista de rutas a los archivos de adaptadores
    """
    adapter_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith("_adapter.py"):
                adapter_files.append(os.path.join(root, file))
    return adapter_files


def check_file_for_method(file_path: str) -> Tuple[bool, bool]:
    """
    Verifica si un archivo contiene una implementación de _get_program_type_from_profile.

    Args:
        file_path: Ruta al archivo a verificar

    Returns:
        Tupla con dos booleanos:
        - El primero indica si el archivo importa BaseAgentAdapter
        - El segundo indica si el archivo contiene una implementación de _get_program_type_from_profile
    """
    with open(file_path, "r") as f:
        content = f.read()

    # Verificar si importa BaseAgentAdapter
    imports_base_adapter = (
        re.search(
            r"from\s+infrastructure\.adapters\.base_agent_adapter\s+import\s+BaseAgentAdapter",
            content,
        )
        is not None
    )

    # Verificar si implementa _get_program_type_from_profile
    implements_method = (
        re.search(r"async\s+def\s+_get_program_type_from_profile\s*\(", content)
        is not None
    )

    return imports_base_adapter, implements_method


def update_file(file_path: str, dry_run: bool = False) -> bool:
    """
    Actualiza un archivo para eliminar la implementación de _get_program_type_from_profile.

    Args:
        file_path: Ruta al archivo a actualizar
        dry_run: Si es True, no se realizan cambios en el archivo

    Returns:
        True si se actualizó el archivo, False en caso contrario
    """
    with open(file_path, "r") as f:
        content = f.read()

    # Buscar la implementación de _get_program_type_from_profile
    method_pattern = re.compile(
        r"(\s+async\s+def\s+_get_program_type_from_profile\s*\([^)]*\)\s*->\s*str\s*:.*?)(\s+async\s+def|\s*$)",
        re.DOTALL,
    )
    match = method_pattern.search(content)

    if not match:
        print(
            f"No se encontró implementación de _get_program_type_from_profile en {file_path}"
        )
        return False

    # Extraer el método completo
    method_code = match.group(1)

    # Verificar si el método simplemente devuelve "general"
    returns_general = re.search(r"return\s+[\"']general[\"']", method_code) is not None

    if returns_general:
        # Eliminar el método
        new_content = content.replace(method_code, "")

        if dry_run:
            print(
                f"[DRY RUN] Se eliminaría _get_program_type_from_profile de {file_path}"
            )
            return True

        # Escribir el archivo actualizado
        with open(file_path, "w") as f:
            f.write(new_content)

        print(f"Se eliminó _get_program_type_from_profile de {file_path}")
        return True
    else:
        print(
            f"La implementación de _get_program_type_from_profile en {file_path} no devuelve 'general'. Se mantiene."
        )
        return False


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Actualiza las llamadas a _get_program_type_from_profile en los adaptadores"
    )
    parser.add_argument(
        "--directory",
        "-d",
        default="infrastructure/adapters",
        help="Directorio donde buscar los adaptadores",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No realizar cambios, solo mostrar qué se haría",
    )
    args = parser.parse_args()

    # Encontrar archivos de adaptadores
    adapter_files = find_adapter_files(args.directory)
    print(f"Se encontraron {len(adapter_files)} archivos de adaptadores")

    # Verificar y actualizar cada archivo
    updated_files = 0
    for file_path in adapter_files:
        imports_base, implements_method = check_file_for_method(file_path)

        if imports_base and implements_method:
            # El archivo importa BaseAgentAdapter y tiene una implementación de _get_program_type_from_profile
            if update_file(file_path, args.dry_run):
                updated_files += 1
        elif implements_method and not imports_base:
            print(
                f"ADVERTENCIA: {file_path} implementa _get_program_type_from_profile pero no importa BaseAgentAdapter"
            )

    # Mostrar resumen
    if args.dry_run:
        print(f"\n[DRY RUN] Se actualizarían {updated_files} archivos")
    else:
        print(f"\nSe actualizaron {updated_files} archivos")


if __name__ == "__main__":
    main()

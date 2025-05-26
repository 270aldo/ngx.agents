#!/usr/bin/env python
"""
Script para verificar que todas las referencias al State Manager original
han sido reemplazadas por referencias al State Manager optimizado.

Este script busca en el código fuente referencias al State Manager original
y genera un informe de los archivos que aún contienen referencias.
"""

import os
import re
import sys
from typing import List, Dict, Tuple
import argparse
import json

# Patrones de búsqueda
ORIGINAL_IMPORT_PATTERNS = [
    r"from\s+core\.state_manager\s+import",
    r"import\s+core\.state_manager",
]

OPTIMIZED_IMPORT_PATTERNS = [
    r"from\s+core\.state_manager_optimized\s+import",
    r"import\s+core\.state_manager_optimized",
]

# Archivos y directorios a ignorar
IGNORE_DIRS = [
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
    ".pytest_cache",
]

IGNORE_FILES = [
    "verify_all_migrations.py",
    "verify_all_state_manager_references.py",
]


def should_ignore(path: str) -> bool:
    """Determina si un archivo o directorio debe ser ignorado."""
    path_parts = path.split(os.sep)

    # Ignorar directorios específicos
    for part in path_parts:
        if part in IGNORE_DIRS:
            return True

    # Ignorar archivos específicos
    filename = os.path.basename(path)
    if filename in IGNORE_FILES:
        return True

    # Solo procesar archivos Python
    if os.path.isfile(path) and not filename.endswith(".py"):
        return True

    return False


def find_references(file_path: str) -> Tuple[List[str], List[str]]:
    """
    Busca referencias al State Manager original y optimizado en un archivo.

    Returns:
        Tuple con listas de líneas que contienen referencias al original y al optimizado.
    """
    original_refs = []
    optimized_refs = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

            # Buscar referencias al original
            for pattern in ORIGINAL_IMPORT_PATTERNS:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    line_start = content[: match.start()].rfind("\n") + 1
                    line_end = content.find("\n", match.start())
                    if line_end == -1:  # Última línea sin salto de línea
                        line_end = len(content)
                    line = content[line_start:line_end].strip()
                    original_refs.append(line)

            # Buscar referencias al optimizado
            for pattern in OPTIMIZED_IMPORT_PATTERNS:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    line_start = content[: match.start()].rfind("\n") + 1
                    line_end = content.find("\n", match.start())
                    if line_end == -1:  # Última línea sin salto de línea
                        line_end = len(content)
                    line = content[line_start:line_end].strip()
                    optimized_refs.append(line)

    except Exception as e:
        print(f"Error al procesar {file_path}: {e}")

    return original_refs, optimized_refs


def scan_directory(directory: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Escanea un directorio en busca de referencias al State Manager.

    Returns:
        Diccionario con archivos y sus referencias.
    """
    results = {}

    for root, dirs, files in os.walk(directory):
        # Filtrar directorios a ignorar
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]

        for file in files:
            file_path = os.path.join(root, file)

            if should_ignore(file_path):
                continue

            original_refs, optimized_refs = find_references(file_path)

            if original_refs or optimized_refs:
                rel_path = os.path.relpath(file_path, directory)
                results[rel_path] = {
                    "original_references": original_refs,
                    "optimized_references": optimized_refs,
                }

    return results


def generate_report(results: Dict[str, Dict[str, List[str]]]) -> str:
    """
    Genera un informe de los resultados del escaneo.

    Returns:
        Informe en formato string.
    """
    report = []
    report.append("# Informe de referencias al State Manager")
    report.append("")

    # Estadísticas
    total_files = len(results)
    files_with_original = sum(
        1 for file_data in results.values() if file_data["original_references"]
    )
    files_with_optimized = sum(
        1 for file_data in results.values() if file_data["optimized_references"]
    )

    report.append(f"## Estadísticas")
    report.append(f"- Total de archivos con referencias: {total_files}")
    report.append(
        f"- Archivos con referencias al State Manager original: {files_with_original}"
    )
    report.append(
        f"- Archivos con referencias al State Manager optimizado: {files_with_optimized}"
    )
    report.append("")

    # Archivos con referencias al original
    if files_with_original > 0:
        report.append("## Archivos con referencias al State Manager original")
        report.append("")
        for file_path, file_data in sorted(results.items()):
            if file_data["original_references"]:
                report.append(f"### {file_path}")
                for ref in file_data["original_references"]:
                    report.append(f"- `{ref}`")
                report.append("")

    # Archivos con referencias al optimizado
    if files_with_optimized > 0:
        report.append("## Archivos con referencias al State Manager optimizado")
        report.append("")
        for file_path, file_data in sorted(results.items()):
            if file_data["optimized_references"]:
                report.append(f"### {file_path}")
                for ref in file_data["optimized_references"]:
                    report.append(f"- `{ref}`")
                report.append("")

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Verificar referencias al State Manager"
    )
    parser.add_argument("--directory", "-d", default=".", help="Directorio a escanear")
    parser.add_argument("--output", "-o", help="Archivo de salida para el informe")
    parser.add_argument(
        "--json", "-j", action="store_true", help="Generar salida en formato JSON"
    )

    args = parser.parse_args()

    print(f"Escaneando directorio: {args.directory}")
    results = scan_directory(args.directory)

    if args.json:
        output = json.dumps(results, indent=2)
    else:
        output = generate_report(results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Informe guardado en: {args.output}")
    else:
        print(output)

    # Determinar si hay archivos que aún usan el State Manager original
    files_with_original = sum(
        1 for file_data in results.values() if file_data["original_references"]
    )

    if files_with_original > 0:
        print(
            f"\n⚠️ Se encontraron {files_with_original} archivos que aún utilizan el State Manager original."
        )
        return 1
    else:
        print("\n✅ Todos los archivos utilizan el State Manager optimizado.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

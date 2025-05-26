#!/usr/bin/env python3
"""
Script para actualizar las importaciones de vertex_ai_client a la nueva estructura modular.

Este script busca todas las importaciones de clients.vertex_ai_client y las actualiza
from core.logging_config import get_logger

para que utilicen la nueva estructura modular clients.vertex_ai.
"""

import os
import re
import argparse
from pathlib import Path
from typing import List, Tuple

# Patrones de importación a buscar y reemplazar
IMPORT_PATTERNS = [
    # from clients.vertex_ai import vertex_ai_client
    (
        r"from\s+clients\.vertex_ai_client\s+import\s+vertex_ai_client",
        "from clients.vertex_ai import vertex_ai_client",
    ),
    # from clients.vertex_ai import vertex_ai_client as optimized_client
    (
        r"from\s+clients\.vertex_ai_client\s+import\s+vertex_ai_client\s+as\s+(\w+)",
        lambda match: f"from clients.vertex_ai import vertex_ai_client as {match.group(1)}",
    ),
    # from clients.vertex_ai import (...)
    (
        r"from\s+clients\.vertex_ai_client\s+import\s+\(",
        "from clients.vertex_ai import (",
    ),
    # from clients.vertex_ai import VertexAIClient
    (
        r"from\s+clients\.vertex_ai_client\s+import\s+VertexAIClient",
        "from clients.vertex_ai import VertexAIClient",
    ),
    # from clients.vertex_ai import check_vertex_ai_connection
    (
        r"from\s+clients\.vertex_ai_client\s+import\s+check_vertex_ai_connection",
        "from clients.vertex_ai import check_vertex_ai_connection",
    ),
    # from clients.vertex_ai import CacheManager
    (
        r"from\s+clients\.vertex_ai_client\s+import\s+CacheManager",
        "from clients.vertex_ai import CacheManager",
    ),
    # from clients.vertex_ai import ConnectionPool
    (
        r"from\s+clients\.vertex_ai_client\s+import\s+ConnectionPool",
        "from clients.vertex_ai import ConnectionPool",
    ),
    # from clients.vertex_ai import with_retries
    (
        r"from\s+clients\.vertex_ai_client\s+import\s+with_retries",
        "from clients.vertex_ai import with_retries",
    ),
    # import clients.vertex_ai
    (r"import\s+clients\.vertex_ai_client", "import clients.vertex_ai"),
]

# Extensiones de archivo a procesar
FILE_EXTENSIONS = [".py", ".md", ".sh"]

# Directorios a excluir
EXCLUDE_DIRS = [
    ".git",
    "__pycache__",
    "venv",
    "env",
    ".venv",
    ".env",
    "node_modules",
]

logger = get_logger(__name__)


def should_process_file(file_path: Path) -> bool:
    """Determina si un archivo debe ser procesado."""
    # Verificar extensión
    if file_path.suffix not in FILE_EXTENSIONS:
        return False

    # Verificar si está en un directorio excluido
    for exclude_dir in EXCLUDE_DIRS:
        if exclude_dir in file_path.parts:
            return False

    # No procesar el archivo vertex_ai_client.py original
    if file_path.name == "vertex_ai_client.py" and "clients" in file_path.parts:
        return False

    return True


def update_imports_in_file(
    file_path: Path, dry_run: bool = False
) -> Tuple[bool, List[str]]:
    """
    Actualiza las importaciones en un archivo.

    Args:
        file_path: Ruta al archivo a procesar
        dry_run: Si es True, no realiza cambios, solo muestra lo que haría

    Returns:
        Tuple[bool, List[str]]: (Se realizaron cambios, Lista de cambios realizados)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Ignorar archivos binarios
        return False, []

    original_content = content
    changes = []

    for pattern, replacement in IMPORT_PATTERNS:
        if callable(replacement):
            # Si el reemplazo es una función, aplicarla a cada coincidencia
            matches = list(re.finditer(pattern, content))
            for match in reversed(
                matches
            ):  # Procesar en reversa para no afectar índices
                start, end = match.span()
                replacement_text = replacement(match)
                if content[start:end] != replacement_text:
                    changes.append(f"  {content[start:end]} -> {replacement_text}")
                    content = content[:start] + replacement_text + content[end:]
        else:
            # Si el reemplazo es un string, usar re.sub
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                for line in re.finditer(pattern, content):
                    original = line.group(0)
                    changes.append(
                        f"  {original} -> {re.sub(pattern, replacement, original)}"
                    )
                content = new_content

    if content != original_content and not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    return content != original_content, changes


def update_imports_in_directory(
    directory: Path, dry_run: bool = False
) -> Tuple[int, int, List[Tuple[Path, List[str]]]]:
    """
    Actualiza las importaciones en todos los archivos de un directorio.

    Args:
        directory: Directorio a procesar
        dry_run: Si es True, no realiza cambios, solo muestra lo que haría

    Returns:
        Tuple[int, int, List[Tuple[Path, List[str]]]]:
            (Archivos procesados, Archivos modificados, Lista de (archivo, cambios))
    """
    processed = 0
    modified = 0
    changes_by_file = []

    for root, dirs, files in os.walk(directory):
        # Excluir directorios
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            file_path = Path(root) / file
            if should_process_file(file_path):
                processed += 1
                changed, changes = update_imports_in_file(file_path, dry_run)
                if changed:
                    modified += 1
                    changes_by_file.append((file_path, changes))

    return processed, modified, changes_by_file


def main():
    parser = argparse.ArgumentParser(
        description="Actualiza las importaciones de vertex_ai_client a la nueva estructura modular."
    )
    parser.add_argument(
        "--directory", "-d", type=str, default=".", help="Directorio a procesar"
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="No realizar cambios, solo mostrar lo que se haría",
    )
    args = parser.parse_args()

    directory = Path(args.directory).resolve()
    logger.info(f"Procesando directorio: {directory}")
    logger.info(f"Modo: {'Simulación' if args.dry_run else 'Actualización'}")

    processed, modified, changes_by_file = update_imports_in_directory(
        directory, args.dry_run
    )

    logger.info(f"\nResumen:")
    logger.info(f"  Archivos procesados: {processed}")
    logger.info(f"  Archivos modificados: {modified}")

    if changes_by_file:
        logger.info("\nCambios realizados:")
        for file_path, changes in changes_by_file:
            logger.info(f"\n{file_path}:")
            for change in changes:
                logger.info(change)

    if args.dry_run and modified > 0:
        logger.info("\nEjecuta sin --dry-run para aplicar estos cambios.")


if __name__ == "__main__":
    main()

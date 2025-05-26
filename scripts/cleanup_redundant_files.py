#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para limpiar archivos redundantes después de la migración del cliente Vertex AI.

Este script identifica y elimina archivos redundantes o desactualizados relacionados
con la implementación anterior del cliente Vertex AI, después de confirmar que la
nueva implementación funciona correctamente.
"""

import os
import argparse
import shutil
import json
import sys
from typing import List, Dict, Tuple
from datetime import datetime

# Añadir directorio raíz al path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
from core.logging_config import get_logger

logger = get_logger(__name__)

# Archivos potencialmente redundantes
REDUNDANT_FILES = [
    # Archivos de cliente antiguos o temporales
    "clients/vertex_ai_client.py",
    "clients/vertex_ai_client_old.py",
    "clients/vertex_ai_client_backup.py",
    "clients/vertex_ai_client_optimized.py",
    "clients/vertex_ai_client_temp.py",
    # Archivos de caché antiguos o temporales
    "clients/vertex_ai_cache.py",
    "clients/vertex_ai_cache_old.py",
    "clients/vertex_ai_cache_backup.py",
    "clients/vertex_ai_cache_optimized.py",
    "clients/vertex_ai_cache_temp.py",
    # Scripts de prueba temporales o antiguos
    "scripts/test_vertex_ai_old.py",
    "scripts/test_vertex_ai_temp.py",
    "scripts/test_vertex_cache_old.py",
    "scripts/test_vertex_cache_temp.py",
    # Archivos de mock temporales
    "scripts/mock_telemetry_old.py",
    "scripts/mock_telemetry_temp.py",
]

# Directorio para backup
BACKUP_DIR = "backups/vertex_ai_migration"


def create_backup_dir() -> str:
    """
    Crea un directorio de backup con timestamp.

    Returns:
        str: Ruta al directorio de backup
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{BACKUP_DIR}_{timestamp}"

    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
        print(f"Directorio de backup creado: {backup_path}")

    return backup_path


def scan_files(base_dir: str) -> Tuple[List[str], List[str]]:
    """
    Escanea el directorio base para encontrar archivos redundantes.

    Args:
        base_dir: Directorio base del proyecto

    Returns:
        Tuple[List[str], List[str]]: Lista de archivos existentes y no existentes
    """
    existing_files = []
    non_existing_files = []

    for file_path in REDUNDANT_FILES:
        full_path = os.path.join(base_dir, file_path)
        if os.path.exists(full_path):
            existing_files.append(full_path)
        else:
            non_existing_files.append(full_path)

    return existing_files, non_existing_files


def backup_files(files: List[str], backup_dir: str) -> Dict[str, str]:
    """
    Hace backup de los archivos especificados.

    Args:
        files: Lista de rutas de archivos
        backup_dir: Directorio de backup

    Returns:
        Dict[str, str]: Mapeo de archivo original a archivo de backup
    """
    backup_map = {}

    for file_path in files:
        filename = os.path.basename(file_path)
        backup_path = os.path.join(backup_dir, filename)

        # Copiar archivo al backup
        shutil.copy2(file_path, backup_path)
        backup_map[file_path] = backup_path
        print(f"Backup creado: {file_path} -> {backup_path}")

    return backup_map


def remove_files(files: List[str], dry_run: bool = False) -> List[str]:
    """
    Elimina los archivos especificados.

    Args:
        files: Lista de rutas de archivos
        dry_run: Si es True, solo simula la eliminación

    Returns:
        List[str]: Lista de archivos eliminados
    """
    removed_files = []

    for file_path in files:
        if dry_run:
            print(f"[SIMULACIÓN] Eliminando: {file_path}")
            removed_files.append(file_path)
        else:
            try:
                os.remove(file_path)
                print(f"Eliminado: {file_path}")
                removed_files.append(file_path)
            except Exception as e:
                print(f"Error al eliminar {file_path}: {str(e)}")

    return removed_files


def export_report(
    backup_dir: str,
    existing_files: List[str],
    non_existing_files: List[str],
    backup_map: Dict[str, str],
    removed_files: List[str],
) -> str:
    """
    Exporta un informe de la limpieza.

    Args:
        backup_dir: Directorio de backup
        existing_files: Lista de archivos existentes
        non_existing_files: Lista de archivos no existentes
        backup_map: Mapeo de archivo original a archivo de backup
        removed_files: Lista de archivos eliminados

    Returns:
        str: Ruta al archivo de informe
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "backup_directory": backup_dir,
        "scanned_files": len(existing_files) + len(non_existing_files),
        "existing_files": existing_files,
        "non_existing_files": non_existing_files,
        "backed_up_files": backup_map,
        "removed_files": removed_files,
    }

    report_path = os.path.join(backup_dir, "cleanup_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Informe exportado a: {report_path}")
    return report_path


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Limpiar archivos redundantes después de la migración del cliente Vertex AI"
    )

    parser.add_argument(
        "--base-dir",
        type=str,
        default=".",
        help="Directorio base del proyecto (default: directorio actual)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular la eliminación sin realizar cambios",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="No crear backup de los archivos antes de eliminarlos",
    )
    parser.add_argument(
        "--force", action="store_true", help="Forzar la eliminación sin confirmación"
    )

    args = parser.parse_args()

    # Normalizar ruta base
    base_dir = os.path.abspath(args.base_dir)
    print(f"Directorio base: {base_dir}")

    # Escanear archivos
    existing_files, non_existing_files = scan_files(base_dir)

    print(f"\nArchivos redundantes encontrados: {len(existing_files)}")
    for file in existing_files:
        print(f"  - {file}")

    print(f"\nArchivos no encontrados: {len(non_existing_files)}")
    for file in non_existing_files:
        print(f"  - {os.path.join(base_dir, file)}")

    # Si no hay archivos para eliminar, salir
    if not existing_files:
        print("\nNo hay archivos redundantes para eliminar.")
        return

    # Confirmar eliminación
    if not args.force and not args.dry_run:
        confirm = input("\n¿Desea continuar con la eliminación? (s/N): ")
        if confirm.lower() not in ["s", "si", "sí", "y", "yes"]:
            print("Operación cancelada.")
            return

    # Crear backup si es necesario
    backup_map = {}
    backup_dir = ""
    if not args.no_backup:
        backup_dir = create_backup_dir()
        backup_map = backup_files(existing_files, backup_dir)

    # Eliminar archivos
    removed_files = remove_files(existing_files, args.dry_run)

    # Exportar informe
    if not args.no_backup:
        report_path = export_report(
            backup_dir, existing_files, non_existing_files, backup_map, removed_files
        )

    # Mostrar resumen
    print("\nResumen de la operación:")
    print(f"  - Archivos escaneados: {len(existing_files) + len(non_existing_files)}")
    print(f"  - Archivos encontrados: {len(existing_files)}")
    print(f"  - Archivos eliminados: {len(removed_files)}")

    if not args.no_backup:
        print(f"  - Archivos respaldados: {len(backup_map)}")
        print(f"  - Directorio de backup: {backup_dir}")
        print(f"  - Informe: {report_path}")

    if args.dry_run:
        print("\nNOTA: Esta fue una simulación. No se eliminaron archivos realmente.")


if __name__ == "__main__":
    main()

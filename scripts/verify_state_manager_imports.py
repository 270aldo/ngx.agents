#!/usr/bin/env python3
"""
Script para verificar que todos los adaptadores estén utilizando el State Manager optimizado.

Este script analiza todos los archivos Python en el directorio de adaptadores
y verifica que estén importando el State Manager optimizado en lugar del original.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Configuración
ADAPTERS_DIR = Path(__file__).parent.parent / "infrastructure" / "adapters"
AGENTS_DIR = Path(__file__).parent.parent / "agents"

# Patrones de importación
ORIGINAL_IMPORT_PATTERN = re.compile(r"from\s+core\.state_manager\s+import")
OPTIMIZED_IMPORT_PATTERN = re.compile(r"from\s+core\.state_manager_optimized\s+import")
ADAPTER_IMPORT_PATTERN = re.compile(
    r"from\s+infrastructure\.adapters\.state_manager_adapter\s+import"
)


def check_file(file_path: Path) -> Dict[str, bool]:
    """
    Verifica los imports de State Manager en un archivo.

    Args:
        file_path: Ruta al archivo a verificar

    Returns:
        Dict[str, bool]: Resultados de la verificación
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "uses_original": bool(ORIGINAL_IMPORT_PATTERN.search(content)),
        "uses_optimized": bool(OPTIMIZED_IMPORT_PATTERN.search(content)),
        "uses_adapter": bool(ADAPTER_IMPORT_PATTERN.search(content)),
    }


def analyze_directory(directory: Path) -> Tuple[List[Dict], int, int, int]:
    """
    Analiza todos los archivos Python en un directorio.

    Args:
        directory: Directorio a analizar

    Returns:
        Tuple[List[Dict], int, int, int]: Resultados, total, correctos, incorrectos
    """
    results = []
    total_files = 0
    correct_files = 0
    incorrect_files = 0

    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = Path(root) / file
            total_files += 1

            check_result = check_file(file_path)

            # Determinar si el archivo está utilizando la versión correcta
            is_correct = (
                check_result["uses_adapter"]
                or check_result["uses_optimized"]
                or not check_result["uses_original"]
            )

            if is_correct:
                correct_files += 1
            else:
                incorrect_files += 1

            results.append(
                {
                    "file": str(file_path.relative_to(Path(__file__).parent.parent)),
                    "uses_original": check_result["uses_original"],
                    "uses_optimized": check_result["uses_optimized"],
                    "uses_adapter": check_result["uses_adapter"],
                    "is_correct": is_correct,
                }
            )

    return results, total_files, correct_files, incorrect_files


def print_results(
    results: List[Dict], total: int, correct: int, incorrect: int, directory_name: str
) -> None:
    """
    Imprime los resultados del análisis.

    Args:
        results: Resultados del análisis
        total: Total de archivos analizados
        correct: Número de archivos correctos
        incorrect: Número de archivos incorrectos
        directory_name: Nombre del directorio analizado
    """
    print(f"\n=== Resultados para {directory_name} ===")
    print(f"Total de archivos analizados: {total}")
    print(
        f"Archivos correctos: {correct} ({(correct/total*100) if total > 0 else 0:.2f}%)"
    )
    print(
        f"Archivos incorrectos: {incorrect} ({(incorrect/total*100) if total > 0 else 0:.2f}%)"
    )

    if incorrect > 0:
        print("\nArchivos que necesitan ser actualizados:")
        for result in results:
            if not result["is_correct"]:
                print(f"  - {result['file']}")

                # Mostrar recomendación
                if result["uses_original"]:
                    print(
                        "    Recomendación: Utilizar 'from infrastructure.adapters.state_manager_adapter import' para acceder a la funcionalidad del State Manager"
                    )


def main() -> int:
    """
    Función principal.

    Returns:
        int: Código de salida
    """
    print("Verificando imports de State Manager...")

    # Analizar adaptadores
    adapter_results, adapter_total, adapter_correct, adapter_incorrect = (
        analyze_directory(ADAPTERS_DIR)
    )
    print_results(
        adapter_results,
        adapter_total,
        adapter_correct,
        adapter_incorrect,
        "Adaptadores",
    )

    # Analizar agentes
    agent_results, agent_total, agent_correct, agent_incorrect = analyze_directory(
        AGENTS_DIR
    )
    print_results(agent_results, agent_total, agent_correct, agent_incorrect, "Agentes")

    # Resultados totales
    total = adapter_total + agent_total
    correct = adapter_correct + agent_correct
    incorrect = adapter_incorrect + agent_incorrect

    print("\n=== Resultados Totales ===")
    print(f"Total de archivos analizados: {total}")
    print(
        f"Archivos correctos: {correct} ({(correct/total*100) if total > 0 else 0:.2f}%)"
    )
    print(
        f"Archivos incorrectos: {incorrect} ({(incorrect/total*100) if total > 0 else 0:.2f}%)"
    )

    # Determinar código de salida
    return 1 if incorrect > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

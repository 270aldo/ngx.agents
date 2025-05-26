#!/usr/bin/env python3
"""
Script para verificar que todas las migraciones se hayan completado correctamente.

Este script verifica:
1. Que todos los adaptadores estén utilizando el cliente Vertex AI refactorizado
2. Que todos los adaptadores estén utilizando el State Manager optimizado
3. Que todas las dependencias necesarias estén instaladas
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Configuración
PROJECT_ROOT = Path(__file__).parent.parent
ADAPTERS_DIR = PROJECT_ROOT / "infrastructure" / "adapters"
AGENTS_DIR = PROJECT_ROOT / "agents"

# Patrones para Vertex AI
VERTEX_OLD_IMPORT_PATTERN = re.compile(r"from\s+clients\.vertex_ai_client\s+import")
VERTEX_NEW_IMPORT_PATTERN = re.compile(r"from\s+clients\.vertex_ai\s+import")
VERTEX_ADAPTER_IMPORT_PATTERN = re.compile(
    r"from\s+infrastructure\.adapters\.vertex_ai_client_adapter\s+import"
)

# Patrones para State Manager
STATE_ORIGINAL_IMPORT_PATTERN = re.compile(r"from\s+core\.state_manager\s+import")
STATE_OPTIMIZED_IMPORT_PATTERN = re.compile(
    r"from\s+core\.state_manager_optimized\s+import"
)
STATE_ADAPTER_IMPORT_PATTERN = re.compile(
    r"from\s+infrastructure\.adapters\.state_manager_adapter\s+import"
)


def check_file_vertex_ai(file_path: Path) -> Dict[str, bool]:
    """
    Verifica los imports de Vertex AI en un archivo.

    Args:
        file_path: Ruta al archivo a verificar

    Returns:
        Dict[str, bool]: Resultados de la verificación
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "uses_old": bool(VERTEX_OLD_IMPORT_PATTERN.search(content)),
        "uses_new": bool(VERTEX_NEW_IMPORT_PATTERN.search(content)),
        "uses_adapter": bool(VERTEX_ADAPTER_IMPORT_PATTERN.search(content)),
    }


def check_file_state_manager(file_path: Path) -> Dict[str, bool]:
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
        "uses_original": bool(STATE_ORIGINAL_IMPORT_PATTERN.search(content)),
        "uses_optimized": bool(STATE_OPTIMIZED_IMPORT_PATTERN.search(content)),
        "uses_adapter": bool(STATE_ADAPTER_IMPORT_PATTERN.search(content)),
    }


def analyze_directory(
    directory: Path,
) -> Tuple[List[Dict], List[Dict], int, int, int, int]:
    """
    Analiza todos los archivos Python en un directorio.

    Args:
        directory: Directorio a analizar

    Returns:
        Tuple: Resultados de Vertex AI, State Manager, totales y correctos
    """
    vertex_results = []
    state_results = []
    total_files = 0
    vertex_correct = 0
    vertex_incorrect = 0
    state_correct = 0
    state_incorrect = 0

    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = Path(root) / file
            total_files += 1

            # Verificar Vertex AI
            vertex_check = check_file_vertex_ai(file_path)

            # Determinar si el archivo está utilizando la versión correcta de Vertex AI
            vertex_is_correct = vertex_check["uses_new"] or not (
                vertex_check["uses_old"] or vertex_check["uses_adapter"]
            )

            if vertex_is_correct:
                vertex_correct += 1
            else:
                vertex_incorrect += 1

            vertex_results.append(
                {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "uses_old": vertex_check["uses_old"],
                    "uses_new": vertex_check["uses_new"],
                    "uses_adapter": vertex_check["uses_adapter"],
                    "is_correct": vertex_is_correct,
                }
            )

            # Verificar State Manager
            state_check = check_file_state_manager(file_path)

            # Determinar si el archivo está utilizando la versión correcta de State Manager
            state_is_correct = (
                state_check["uses_adapter"]
                or state_check["uses_optimized"]
                or not state_check["uses_original"]
            )

            if state_is_correct:
                state_correct += 1
            else:
                state_incorrect += 1

            state_results.append(
                {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "uses_original": state_check["uses_original"],
                    "uses_optimized": state_check["uses_optimized"],
                    "uses_adapter": state_check["uses_adapter"],
                    "is_correct": state_is_correct,
                }
            )

    return (
        vertex_results,
        state_results,
        total_files,
        vertex_correct,
        vertex_incorrect,
        state_correct,
        state_incorrect,
    )


def print_vertex_results(
    results: List[Dict], total: int, correct: int, incorrect: int, directory_name: str
) -> None:
    """
    Imprime los resultados del análisis de Vertex AI.

    Args:
        results: Resultados del análisis
        total: Total de archivos analizados
        correct: Número de archivos correctos
        incorrect: Número de archivos incorrectos
        directory_name: Nombre del directorio analizado
    """
    print(f"\n=== Resultados de Vertex AI para {directory_name} ===")
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
                if result["uses_old"]:
                    print(
                        "    Recomendación: Reemplazar 'from clients.vertex_ai_client import' por 'from clients.vertex_ai import'"
                    )
                elif result["uses_adapter"]:
                    print(
                        "    Recomendación: Reemplazar 'from infrastructure.adapters.vertex_ai_client_adapter import' por 'from clients.vertex_ai import'"
                    )


def print_state_results(
    results: List[Dict], total: int, correct: int, incorrect: int, directory_name: str
) -> None:
    """
    Imprime los resultados del análisis de State Manager.

    Args:
        results: Resultados del análisis
        total: Total de archivos analizados
        correct: Número de archivos correctos
        incorrect: Número de archivos incorrectos
        directory_name: Nombre del directorio analizado
    """
    print(f"\n=== Resultados de State Manager para {directory_name} ===")
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
                        "    Recomendación: Reemplazar 'from core.state_manager import' por 'from infrastructure.adapters.state_manager_adapter import'"
                    )


def check_dependencies() -> int:
    """
    Verifica las dependencias utilizando el script check_dependencies.py.

    Returns:
        int: Código de salida del script
    """
    print("\n=== Verificando dependencias ===")

    # Verificar si el script existe
    deps_script = PROJECT_ROOT / "scripts" / "check_dependencies.py"
    if not deps_script.exists():
        print("ERROR: No se encontró el script check_dependencies.py")
        return 1

    # Ejecutar el script
    try:
        result = subprocess.run(
            [sys.executable, str(deps_script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )

        # Mostrar salida
        print(result.stdout)

        return result.returncode

    except Exception as e:
        print(f"ERROR: No se pudo ejecutar el script check_dependencies.py: {str(e)}")
        return 1


def main() -> int:
    """
    Función principal.

    Returns:
        int: Código de salida
    """
    print("Verificando migraciones...")

    # Analizar adaptadores
    (
        adapter_vertex_results,
        adapter_state_results,
        adapter_total,
        adapter_vertex_correct,
        adapter_vertex_incorrect,
        adapter_state_correct,
        adapter_state_incorrect,
    ) = analyze_directory(ADAPTERS_DIR)

    # Analizar agentes
    (
        agent_vertex_results,
        agent_state_results,
        agent_total,
        agent_vertex_correct,
        agent_vertex_incorrect,
        agent_state_correct,
        agent_state_incorrect,
    ) = analyze_directory(AGENTS_DIR)

    # Imprimir resultados de Vertex AI
    print_vertex_results(
        adapter_vertex_results,
        adapter_total,
        adapter_vertex_correct,
        adapter_vertex_incorrect,
        "Adaptadores",
    )
    print_vertex_results(
        agent_vertex_results,
        agent_total,
        agent_vertex_correct,
        agent_vertex_incorrect,
        "Agentes",
    )

    # Resultados totales de Vertex AI
    total = adapter_total + agent_total
    vertex_correct = adapter_vertex_correct + agent_vertex_correct
    vertex_incorrect = adapter_vertex_incorrect + agent_vertex_incorrect

    print("\n=== Resultados Totales de Vertex AI ===")
    print(f"Total de archivos analizados: {total}")
    print(
        f"Archivos correctos: {vertex_correct} ({(vertex_correct/total*100) if total > 0 else 0:.2f}%)"
    )
    print(
        f"Archivos incorrectos: {vertex_incorrect} ({(vertex_incorrect/total*100) if total > 0 else 0:.2f}%)"
    )

    # Imprimir resultados de State Manager
    print_state_results(
        adapter_state_results,
        adapter_total,
        adapter_state_correct,
        adapter_state_incorrect,
        "Adaptadores",
    )
    print_state_results(
        agent_state_results,
        agent_total,
        agent_state_correct,
        agent_state_incorrect,
        "Agentes",
    )

    # Resultados totales de State Manager
    state_correct = adapter_state_correct + agent_state_correct
    state_incorrect = adapter_state_incorrect + agent_state_incorrect

    print("\n=== Resultados Totales de State Manager ===")
    print(f"Total de archivos analizados: {total}")
    print(
        f"Archivos correctos: {state_correct} ({(state_correct/total*100) if total > 0 else 0:.2f}%)"
    )
    print(
        f"Archivos incorrectos: {state_incorrect} ({(state_incorrect/total*100) if total > 0 else 0:.2f}%)"
    )

    # Verificar dependencias
    deps_result = check_dependencies()

    # Determinar código de salida
    return 1 if (vertex_incorrect > 0 or state_incorrect > 0 or deps_result != 0) else 0


if __name__ == "__main__":
    sys.exit(main())

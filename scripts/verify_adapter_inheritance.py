#!/usr/bin/env python
"""
Script para verificar qué adaptadores de agentes necesitan ser actualizados para heredar de BaseAgentAdapter.

Este script analiza los archivos de adaptadores de agentes en infrastructure/adapters/
y verifica si ya heredan de BaseAgentAdapter o necesitan ser actualizados.
"""

import os
import re
import sys
import argparse
from typing import List, Dict, Tuple


# Colores para la salida en terminal
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def parse_args():
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Verifica qué adaptadores necesitan ser actualizados."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Intenta corregir automáticamente los adaptadores",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Muestra información detallada"
    )
    return parser.parse_args()


# Lista de adaptadores de infraestructura que deben ser excluidos
INFRASTRUCTURE_ADAPTERS = [
    "a2a_adapter.py",
    "intent_analyzer_adapter.py",
    "state_manager_adapter.py",
    "telemetry_adapter.py",
]


def find_adapter_files(directory: str = "infrastructure/adapters") -> List[str]:
    """
    Encuentra los archivos de adaptadores de agentes en el directorio especificado.

    Excluye los adaptadores de infraestructura y el adaptador base.

    Args:
        directory: Directorio donde buscar los adaptadores

    Returns:
        Lista de rutas a los archivos de adaptadores de agentes
    """
    adapter_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if (
                file.endswith("_adapter.py")
                and file != "base_agent_adapter.py"
                and file not in INFRASTRUCTURE_ADAPTERS
            ):
                adapter_files.append(os.path.join(root, file))
    return adapter_files


def check_adapter_inheritance(file_path: str) -> Tuple[bool, str, str]:
    """
    Verifica si un adaptador hereda de BaseAgentAdapter.

    Args:
        file_path: Ruta al archivo del adaptador

    Returns:
        Tupla con (hereda_de_base, nombre_clase, nombre_agente)
    """
    with open(file_path, "r") as f:
        content = f.read()

    # Buscar la importación de BaseAgentAdapter
    has_import = bool(
        re.search(
            r"from\s+infrastructure\.adapters\.base_agent_adapter\s+import\s+BaseAgentAdapter",
            content,
        )
    )

    # Buscar la definición de la clase
    class_match = re.search(r"class\s+(\w+)\((\w+)(?:,\s*(\w+))?\):", content)
    if not class_match:
        return False, "Unknown", "Unknown"

    adapter_class = class_match.group(1)
    agent_class = class_match.group(2)
    second_parent = class_match.group(3) if class_match.group(3) else None

    # Verificar si hereda de BaseAgentAdapter
    inherits_from_base = (
        second_parent == "BaseAgentAdapter" or agent_class == "BaseAgentAdapter"
    )

    return inherits_from_base, adapter_class, agent_class


def analyze_adapters() -> Dict[str, Dict]:
    """
    Analiza todos los adaptadores y devuelve su estado.

    Returns:
        Diccionario con información sobre cada adaptador
    """
    adapter_files = find_adapter_files()
    results = {}

    for file_path in adapter_files:
        inherits_from_base, adapter_class, agent_class = check_adapter_inheritance(
            file_path
        )
        results[file_path] = {
            "inherits_from_base": inherits_from_base,
            "adapter_class": adapter_class,
            "agent_class": agent_class,
        }

    return results


def print_results(results: Dict[str, Dict], verbose: bool = False):
    """
    Imprime los resultados del análisis.

    Args:
        results: Resultados del análisis
        verbose: Si es True, muestra información detallada
    """
    total = len(results)
    updated = sum(1 for info in results.values() if info["inherits_from_base"])
    pending = total - updated

    print(f"\n{Colors.HEADER}Análisis de Adaptadores de Agentes{Colors.ENDC}")
    print(f"{Colors.BOLD}Total de adaptadores:{Colors.ENDC} {total}")
    print(f"{Colors.GREEN}Adaptadores actualizados:{Colors.ENDC} {updated}")
    print(f"{Colors.YELLOW}Adaptadores pendientes:{Colors.ENDC} {pending}")

    if verbose or pending > 0:
        print(f"\n{Colors.BOLD}Detalle:{Colors.ENDC}")

        if updated > 0 and verbose:
            print(
                f"\n{Colors.GREEN}Adaptadores de agentes que ya heredan de BaseAgentAdapter:{Colors.ENDC}"
            )
            for file_path, info in results.items():
                if info["inherits_from_base"]:
                    print(
                        f"  ✓ {info['adapter_class']} ({os.path.basename(file_path)})"
                    )

        if pending > 0:
            print(
                f"\n{Colors.YELLOW}Adaptadores de agentes que necesitan ser actualizados:{Colors.ENDC}"
            )
            for file_path, info in results.items():
                if not info["inherits_from_base"]:
                    print(
                        f"  ✗ {info['adapter_class']} ({os.path.basename(file_path)})"
                    )
                    if verbose:
                        print(f"    - Archivo: {file_path}")
                        print(f"    - Hereda de: {info['agent_class']}")


def main():
    """Función principal."""
    args = parse_args()
    results = analyze_adapters()
    print_results(results, args.verbose)

    # Si se especificó --fix, intentar corregir automáticamente
    if args.fix:
        print(
            f"\n{Colors.BLUE}La corrección automática no está implementada aún.{Colors.ENDC}"
        )
        print(
            "Por favor, actualiza manualmente los adaptadores de agentes siguiendo el ejemplo de ClientSuccessLiaisonAdapter."
        )

    # Mostrar información sobre adaptadores de infraestructura excluidos
    print(
        f"\n{Colors.BLUE}Nota:{Colors.ENDC} Los siguientes adaptadores de infraestructura han sido excluidos de la verificación:"
    )
    for adapter in INFRASTRUCTURE_ADAPTERS:
        print(f"  - {adapter}")
    print(
        "Estos adaptadores no necesitan heredar de BaseAgentAdapter porque son componentes de infraestructura, no agentes."
    )

    # Devolver código de salida 1 si hay adaptadores pendientes
    pending = sum(1 for info in results.values() if not info["inherits_from_base"])
    return 1 if pending > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

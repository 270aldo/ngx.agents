#!/usr/bin/env python3
"""
Script para ejecutar pruebas de integración en el proyecto NGX Agents.

Este script facilita la ejecución de pruebas de integración con diferentes opciones,
permitiendo ejecutar pruebas específicas o todas las pruebas, así como configurar
el nivel de detalle de la salida.

Uso:
    ./scripts/run_integration_tests.py [opciones]

Opciones:
    --all                Ejecutar todas las pruebas de integración
    --a2a                Ejecutar solo las pruebas de integración del servidor A2A
    --state-intent       Ejecutar solo las pruebas de integración entre State Manager e Intent Analyzer
    --full               Ejecutar solo las pruebas de integración completa del sistema
    --fixed              Usar la versión corregida de las pruebas (solo aplica con --full)
    --verbose            Mostrar salida detallada
    --xvs                Mostrar más detalles con el flag -xvs
    --help               Mostrar este mensaje de ayuda
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def parse_arguments():
    """Analiza los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Ejecutar pruebas de integración para NGX Agents"
    )
    parser.add_argument(
        "--all", action="store_true", help="Ejecutar todas las pruebas de integración"
    )
    parser.add_argument(
        "--a2a",
        action="store_true",
        help="Ejecutar solo las pruebas de integración del servidor A2A",
    )
    parser.add_argument(
        "--state-intent",
        action="store_true",
        help="Ejecutar solo las pruebas de integración entre State Manager e Intent Analyzer",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Ejecutar solo las pruebas de integración completa del sistema",
    )
    parser.add_argument(
        "--fixed",
        action="store_true",
        help="Usar la versión corregida de las pruebas (solo aplica con --full)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Mostrar salida detallada"
    )
    parser.add_argument(
        "--xvs", action="store_true", help="Mostrar más detalles con el flag -xvs"
    )
    return parser.parse_args()


def get_project_root():
    """Obtiene la ruta raíz del proyecto."""
    # Asumimos que este script está en la carpeta scripts/ del proyecto
    return Path(__file__).parent.parent


def run_tests(test_paths, verbose=False, xvs=False):
    """Ejecuta las pruebas especificadas."""
    project_root = get_project_root()
    
    # Construir el comando de pytest
    cmd = ["python", "-m", "pytest"]
    
    # Agregar opciones de verbosidad
    if verbose:
        cmd.append("-v")
    if xvs:
        cmd.append("-xvs")
    
    # Agregar las rutas de las pruebas
    cmd.extend(test_paths)
    
    print(f"Ejecutando: {' '.join(cmd)}")
    
    # Ejecutar el comando
    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar las pruebas: {e}")
        return False


def main():
    """Función principal."""
    args = parse_arguments()
    
    # Si no se especifica ninguna opción, mostrar la ayuda
    if not (args.all or args.a2a or args.state_intent or args.full):
        print(__doc__)
        return 0
    
    test_paths = []
    
    # Determinar qué pruebas ejecutar
    if args.all:
        test_paths.append("tests/integration/")
    else:
        if args.a2a:
            test_paths.append("tests/integration/test_a2a_integration.py")
        
        if args.state_intent:
            test_paths.append("tests/integration/test_state_intent_integration.py")
        
        if args.full:
            if args.fixed:
                test_paths.append("tests/integration/test_full_system_integration_fixed.py")
            else:
                test_paths.append("tests/integration/test_full_system_integration.py")
    
    # Ejecutar las pruebas
    success = run_tests(test_paths, args.verbose, args.xvs)
    
    # Generar informe de resultados
    if success:
        print("\n✅ Todas las pruebas pasaron correctamente.")
    else:
        print("\n❌ Algunas pruebas fallaron. Revise la salida para más detalles.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

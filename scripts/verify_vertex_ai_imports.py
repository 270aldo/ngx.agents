#!/usr/bin/env python
"""
Script para verificar que todos los adaptadores estén utilizando el cliente Vertex AI refactorizado.

Este script busca en todos los archivos de adaptadores y verifica que estén importando
el cliente Vertex AI desde el paquete refactorizado en lugar del adaptador.
"""

import re
import sys
from pathlib import Path

# Añadir el directorio raíz al path para poder importar los módulos
sys.path.append(str(Path(__file__).parent.parent))

# Patrones de importación
OLD_IMPORT_PATTERN = r"from\s+clients\.vertex_ai_client_adapter\s+import"
NEW_IMPORT_PATTERN = r"from\s+clients\.vertex_ai\s+import"

# Directorio de adaptadores
ADAPTERS_DIR = Path(__file__).parent.parent / "infrastructure" / "adapters"


def check_imports():
    """
    Verifica las importaciones en todos los archivos de adaptadores.

    Returns:
        tuple: (adaptadores_correctos, adaptadores_incorrectos)
    """
    adaptadores_correctos = []
    adaptadores_incorrectos = []

    for file_path in ADAPTERS_DIR.glob("*_adapter.py"):
        with open(file_path, "r") as f:
            content = f.read()

            # Verificar si el archivo importa el cliente Vertex AI
            if re.search(OLD_IMPORT_PATTERN, content):
                adaptadores_incorrectos.append(file_path.name)
            elif re.search(NEW_IMPORT_PATTERN, content):
                adaptadores_correctos.append(file_path.name)

    return adaptadores_correctos, adaptadores_incorrectos


def main():
    """Función principal."""
    print("Verificando importaciones del cliente Vertex AI en adaptadores...")

    adaptadores_correctos, adaptadores_incorrectos = check_imports()

    print("\nAdaptadores que utilizan el cliente Vertex AI refactorizado:")
    for adapter in sorted(adaptadores_correctos):
        print(f"  ✅ {adapter}")

    print("\nAdaptadores que todavía utilizan el adaptador del cliente Vertex AI:")
    if adaptadores_incorrectos:
        for adapter in sorted(adaptadores_incorrectos):
            print(f"  ❌ {adapter}")
    else:
        print(
            "  ¡Ninguno! Todos los adaptadores están utilizando el cliente refactorizado."
        )

    print(
        f"\nResumen: {len(adaptadores_correctos)} correctos, {len(adaptadores_incorrectos)} incorrectos"
    )

    return len(adaptadores_incorrectos)


if __name__ == "__main__":
    sys.exit(main())

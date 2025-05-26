#!/usr/bin/env python3
"""
Script para verificar que todas las dependencias necesarias estén instaladas correctamente.

Este script verifica que todas las dependencias especificadas en pyproject.toml
estén instaladas y con las versiones correctas.
"""

import sys
import pkg_resources
import tomli
from pathlib import Path
from typing import Dict, Tuple, Optional

# Configuración
PROJECT_ROOT = Path(__file__).parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


def parse_pyproject_dependencies() -> Dict[str, str]:
    """
    Parsea las dependencias del archivo pyproject.toml usando tomli.

    Returns:
        Dict[str, str]: Diccionario con las dependencias y sus versiones
    """
    dependencies = {}

    try:
        with open(PYPROJECT_PATH, "rb") as f:
            pyproject = tomli.load(f)

        # Obtener dependencias principales
        main_deps = pyproject.get("tool", {}).get("poetry", {}).get("dependencies", {})
        for package, version in main_deps.items():
            if isinstance(version, dict) and "version" in version:
                # Formato complejo como uvicorn = {extras = ["standard"], version = "^0.27.0"}
                dependencies[package] = version["version"]
            elif isinstance(version, str):
                # Formato simple como fastapi = "^0.115.0"
                dependencies[package] = version

        # Obtener dependencias de grupos opcionales
        groups = pyproject.get("tool", {}).get("poetry", {}).get("group", {})
        for group_name, group_data in groups.items():
            group_deps = group_data.get("dependencies", {})
            for package, version in group_deps.items():
                if isinstance(version, dict) and "version" in version:
                    dependencies[f"{group_name}:{package}"] = version["version"]
                elif isinstance(version, str):
                    dependencies[f"{group_name}:{package}"] = version

    except Exception as e:
        print(f"Error al parsear pyproject.toml: {str(e)}")

    return dependencies


def get_installed_packages() -> Dict[str, str]:
    """
    Obtiene las dependencias instaladas en el entorno actual.

    Returns:
        Dict[str, str]: Diccionario con las dependencias instaladas y sus versiones
    """
    installed = {}

    for package in pkg_resources.working_set:
        installed[package.key] = package.version

    return installed


def check_package_installed(
    package: str, required_version: str, installed_packages: Dict[str, str]
) -> Tuple[bool, Optional[str]]:
    """
    Verifica si un paquete está instalado y con la versión correcta.

    Args:
        package: Nombre del paquete
        required_version: Versión requerida
        installed_packages: Diccionario con los paquetes instalados

    Returns:
        Tuple[bool, Optional[str]]: (está_instalado, versión_instalada)
    """
    # Normalizar nombre del paquete
    normalized_package = package.lower().replace("-", "_")

    # Verificar si está instalado
    if normalized_package not in installed_packages:
        # Intentar con el nombre original
        if package not in installed_packages:
            return False, None
        else:
            installed_version = installed_packages[package]
    else:
        installed_version = installed_packages[normalized_package]

    return True, installed_version


def parse_version_requirement(version_str: str) -> Tuple[str, str, str]:
    """
    Parsea un requisito de versión.

    Args:
        version_str: String con el requisito de versión

    Returns:
        Tuple[str, str, str]: (operador, versión, descripción)
    """
    # Extraer operador y versión
    if version_str.startswith("^"):
        operator = "^"
        version = version_str[1:]
        description = f"Compatible con {version} (misma versión mayor)"
    elif version_str.startswith("~"):
        operator = "~"
        version = version_str[1:]
        description = f"Compatible con {version} (misma versión menor)"
    elif version_str.startswith(">="):
        operator = ">="
        version = version_str[2:]
        description = f"Mayor o igual a {version}"
    elif version_str.startswith(">"):
        operator = ">"
        version = version_str[1:]
        description = f"Mayor que {version}"
    elif version_str.startswith("=="):
        operator = "=="
        version = version_str[2:]
        description = f"Exactamente {version}"
    elif version_str.startswith("<="):
        operator = "<="
        version = version_str[2:]
        description = f"Menor o igual a {version}"
    elif version_str.startswith("<"):
        operator = "<"
        version = version_str[1:]
        description = f"Menor que {version}"
    else:
        operator = ""
        version = version_str
        description = f"Versión {version_str}"

    return operator, version, description


def main() -> int:
    """
    Función principal.

    Returns:
        int: Código de salida
    """
    print("Verificando dependencias...")

    # Verificar si tomli está instalado
    try:
        pass
    except ImportError:
        print("ERROR: El paquete 'tomli' no está instalado.")
        print("Instálalo con: pip install tomli")
        return 1

    # Obtener dependencias del pyproject.toml
    dependencies = parse_pyproject_dependencies()

    # Obtener paquetes instalados
    installed_packages = get_installed_packages()

    # Verificar dependencias
    missing_packages = []
    installed_packages_info = []

    for package, version in dependencies.items():
        # Verificar si es de un grupo opcional
        if ":" in package:
            group, package_name = package.split(":")
            is_optional = True
        else:
            package_name = package
            is_optional = False

        # Verificar si está instalado
        is_installed, installed_version = check_package_installed(
            package_name, version, installed_packages
        )

        # Parsear requisito de versión
        operator, version_num, description = parse_version_requirement(version)

        if is_installed:
            installed_packages_info.append(
                {
                    "package": package_name,
                    "required": version,
                    "installed": installed_version,
                    "description": description,
                    "is_optional": is_optional,
                }
            )
        else:
            missing_packages.append(
                {
                    "package": package_name,
                    "required": version,
                    "description": description,
                    "is_optional": is_optional,
                }
            )

    # Mostrar resultados
    print(f"\nTotal de dependencias: {len(dependencies)}")
    print(f"Dependencias instaladas: {len(installed_packages_info)}")
    print(f"Dependencias faltantes: {len(missing_packages)}")

    if missing_packages:
        print("\nDependencias faltantes:")
        for package in missing_packages:
            optional_str = " (opcional)" if package["is_optional"] else ""
            print(f"  - {package['package']}: {package['required']} {optional_str}")
            print(f"    {package['description']}")

    # Mostrar dependencias instaladas
    print("\nDependencias instaladas:")
    for package in installed_packages_info:
        optional_str = " (opcional)" if package["is_optional"] else ""
        print(
            f"  - {package['package']}: {package['installed']} (requerido: {package['required']}) {optional_str}"
        )

    # Determinar código de salida
    # Consideramos exitoso si solo faltan dependencias opcionales
    missing_required = [p for p in missing_packages if not p["is_optional"]]
    return 1 if missing_required else 0


if __name__ == "__main__":
    sys.exit(main())

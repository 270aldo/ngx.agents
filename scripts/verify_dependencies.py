#!/usr/bin/env python3
"""
Script para verificar que todas las dependencias necesarias estén instaladas correctamente.

Este script verifica que todas las dependencias especificadas en pyproject.toml
estén instaladas y con las versiones correctas.
"""

import sys
import pkg_resources
import re
from pathlib import Path
from typing import Dict, Tuple, Optional

# Configuración
PROJECT_ROOT = Path(__file__).parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


def parse_pyproject_dependencies() -> Dict[str, str]:
    """
    Parsea las dependencias del archivo pyproject.toml.

    Returns:
        Dict[str, str]: Diccionario con las dependencias y sus versiones
    """
    dependencies = {}

    with open(PYPROJECT_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Extraer sección de dependencias principales
    main_deps_match = re.search(
        r"\[tool\.poetry\.dependencies\](.*?)(?:\[tool\.poetry\.group|$)",
        content,
        re.DOTALL,
    )
    if main_deps_match:
        main_deps = main_deps_match.group(1)

        # Extraer pares de dependencia y versión
        for line in main_deps.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Manejar formato complejo como uvicorn = {extras = ["standard"], version = "^0.27.0"}
            extras_match = re.match(r"(\w+[-\w]*?)\s*=\s*\{(.*?)\}", line)
            if extras_match:
                package = extras_match.group(1).strip()
                extras_content = extras_match.group(2).strip()

                # Extraer versión
                version_match = re.search(
                    r'version\s*=\s*["\'](.*?)["\']\'', extras_content
                )
                if version_match:
                    version = version_match.group(1)
                    dependencies[package] = version
                else:
                    dependencies[package] = "extras-only"
                continue

            # Manejar formato simple como fastapi = "^0.115.0"
            parts = line.split("=")
            if len(parts) >= 2:
                package = parts[0].strip()
                version_part = "=".join(parts[1:]).strip()

                # Extraer versión entre comillas
                version_match = re.search(r'["\'](.*?)["\']\'', version_part)
                if version_match:
                    version = version_match.group(1)
                    dependencies[package] = version
                else:
                    dependencies[package] = version_part

    # Extraer secciones de grupos opcionales
    group_matches = re.finditer(
        r"\[tool\.poetry\.group\.(.*?)\.dependencies\](.*?)(?:\[|\Z)",
        content,
        re.DOTALL,
    )
    for match in group_matches:
        group_name = match.group(1)
        group_deps = match.group(2)

        # Extraer pares de dependencia y versión
        for line in group_deps.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("=")
            if len(parts) >= 2:
                package = parts[0].strip()
                version = parts[1].strip().strip("\"'")
                dependencies[f"{group_name}:{package}"] = version

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
    match = re.match(r"^([^0-9]*)(.*)$", version_str)
    if match:
        operator = match.group(1)
        version = match.group(2)

        # Determinar descripción
        if operator == "^":
            description = f"Compatible con {version} (misma versión mayor)"
        elif operator == "~":
            description = f"Compatible con {version} (misma versión menor)"
        elif operator == ">=":
            description = f"Mayor o igual a {version}"
        elif operator == ">":
            description = f"Mayor que {version}"
        elif operator == "==":
            description = f"Exactamente {version}"
        elif operator == "<=":
            description = f"Menor o igual a {version}"
        elif operator == "<":
            description = f"Menor que {version}"
        else:
            description = f"Versión {version}"

        return operator, version, description

    return "", version_str, f"Versión {version_str}"


def main() -> int:
    """
    Función principal.

    Returns:
        int: Código de salida
    """
    print("Verificando dependencias...")

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

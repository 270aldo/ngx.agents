"""
Pruebas de compatibilidad entre componentes.

Este módulo contiene pruebas que verifican que los componentes pueden
comunicarse correctamente a pesar de estar en entornos aislados.
"""

import importlib
import sys
from pathlib import Path
import pytest


def add_component_to_path(component_name):
    """Añade el directorio de un componente al path de Python."""
    component_path = Path(__file__).parent.parent.parent / component_name
    if component_path.exists() and str(component_path) not in sys.path:
        sys.path.insert(0, str(component_path))
    return component_path


@pytest.mark.compatibility
def test_agents_core_compatibility():
    """Verifica que los componentes agents y core pueden comunicarse."""
    # Añadir componentes al path
    add_component_to_path("agents")
    add_component_to_path("core")

    # Importar módulos de ambos componentes
    try:
        agents_module = importlib.import_module("agents")
        core_module = importlib.import_module("core")

        # Verificar que se pueden importar correctamente
        assert agents_module is not None
        assert core_module is not None

        # Aquí se pueden añadir verificaciones específicas de compatibilidad
        # Por ejemplo, verificar que un agente puede usar funcionalidades del core
    except ImportError as e:
        pytest.fail(f"Error de importación: {e}")


@pytest.mark.compatibility
def test_app_clients_compatibility():
    """Verifica que los componentes app y clients pueden comunicarse."""
    # Añadir componentes al path
    add_component_to_path("app")
    add_component_to_path("clients")

    try:
        app_module = importlib.import_module("app")
        clients_module = importlib.import_module("clients")

        assert app_module is not None
        assert clients_module is not None

        # Verificaciones específicas de compatibilidad
    except ImportError as e:
        pytest.fail(f"Error de importación: {e}")


@pytest.mark.compatibility
def test_tools_integration():
    """Verifica que el componente tools puede ser usado por otros componentes."""
    # Añadir componente al path
    add_component_to_path("tools")

    try:
        tools_module = importlib.import_module("tools")
        assert tools_module is not None

        # Verificar que otros componentes pueden usar tools
        for component in ["agents", "app", "core"]:
            add_component_to_path(component)
            component_module = importlib.import_module(component)
            assert component_module is not None
    except ImportError as e:
        pytest.fail(f"Error de importación: {e}")


@pytest.mark.compatibility
def test_version_compatibility():
    """Verifica la compatibilidad de versiones entre componentes."""
    # Crear un diccionario para almacenar las versiones de dependencias por componente
    component_deps = {}

    # Función para extraer versiones de dependencias
    def get_dependencies(component):
        venv_dir = Path(f".venvs/{component}")
        if not venv_dir.exists():
            pytest.skip(f"Entorno virtual para {component} no encontrado")

        # Usar pip freeze para obtener las dependencias instaladas
        import subprocess

        result = subprocess.run(
            [f"{venv_dir}/bin/pip", "freeze"], capture_output=True, text=True
        )

        deps = {}
        for line in result.stdout.splitlines():
            if "==" in line:
                package, version = line.split("==", 1)
                deps[package.lower()] = version
        return deps

    # Obtener dependencias para cada componente
    for component in ["agents", "app", "clients", "core", "tools"]:
        try:
            component_deps[component] = get_dependencies(component)
        except Exception as e:
            pytest.skip(f"No se pudieron obtener dependencias para {component}: {e}")

    # Verificar compatibilidad de versiones críticas
    critical_packages = ["pydantic", "httpx", "fastapi"]

    for package in critical_packages:
        versions = {}
        for component, deps in component_deps.items():
            if package in deps:
                versions[component] = deps[package]

        # Verificar que las versiones sean compatibles
        if len(set(versions.values())) > 1:
            # Si hay diferentes versiones, verificar que sean compatibles
            # (por ejemplo, misma versión mayor)
            major_versions = {v.split(".")[0] for v in versions.values()}
            assert (
                len(major_versions) == 1
            ), f"Versiones incompatibles de {package}: {versions}"

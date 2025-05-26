#!/usr/bin/env python
"""
Script para generar un resumen completo del proyecto NGX Agents.

Este script analiza el estado actual del proyecto, sus dependencias,
componentes principales y genera un informe detallado con recomendaciones
para solucionar problemas comunes.
"""

import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import argparse

# Configuración
PROJECT_ROOT = Path(__file__).parent.parent
COMPONENTS = ["clients", "core", "infrastructure", "agents", "app", "tools"]

MIGRATIONS = [
    {
        "name": "Vertex AI Client",
        "original": "clients/vertex_ai_client.py",
        "optimized": "clients/vertex_ai_client_optimized.py",
        "adapter": "infrastructure/adapters/vertex_ai_adapter.py",
        "status_script": "scripts/verify_vertex_ai_client.py",
    },
    {
        "name": "State Manager",
        "original": "core/state_manager.py",
        "optimized": "core/state_manager_optimized.py",
        "adapter": "infrastructure/adapters/state_manager_adapter.py",
        "status_script": "scripts/verify_all_state_manager_references.py",
    },
    {
        "name": "Intent Analyzer",
        "original": "core/intent_analyzer.py",
        "optimized": "core/intent_analyzer_optimized.py",
        "adapter": "infrastructure/adapters/intent_analyzer_adapter.py",
        "status_script": "scripts/verify_intent_analyzer_imports.py",
    },
    {
        "name": "A2A Server",
        "original": "infrastructure/a2a.py",
        "optimized": "infrastructure/a2a_optimized.py",
        "adapter": "infrastructure/adapters/a2a_adapter.py",
        "status_script": "scripts/verify_a2a_imports.py",
    },
]

COMMON_ERRORS = [
    {
        "pattern": r"AttributeError: module 'core' has no attribute 'telemetry'",
        "description": "Error de importación del módulo de telemetría",
        "solution": """
Este error ocurre cuando se intenta importar el módulo de telemetría que no está disponible o no está en el path.

Soluciones:
1. Asegúrate de que las dependencias de OpenTelemetry estén instaladas:
   ```
   pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-cloud-monitoring
   ```
2. Crea un mock para el módulo de telemetría en tus pruebas:
   ```python
   import sys
   from unittest.mock import MagicMock
   sys.modules['core.telemetry'] = MagicMock()
   sys.modules['core.telemetry.telemetry_manager'] = MagicMock()
   ```
3. Utiliza inyección de dependencias en lugar de importaciones directas.
""",
    },
    {
        "pattern": r"ImportError: cannot import name 'StateManager'",
        "description": "Error al importar StateManager",
        "solution": """
Este error ocurre cuando se intenta importar la clase StateManager del módulo original que ya no existe o ha sido migrado.

Soluciones:
1. Reemplaza las importaciones de `core.state_manager` por `infrastructure.adapters.state_manager_adapter`:
   ```python
   from infrastructure.adapters.state_manager_adapter import state_manager_adapter
   ```
2. Utiliza el adaptador en lugar de instanciar el StateManager directamente:
   ```python
   # Antes
   state_manager = StateManager()
   
   # Después
   state_manager = state_manager_adapter
   ```
3. Ejecuta el script de verificación para asegurarte de que todas las referencias han sido actualizadas:
   ```
   python scripts/verify_all_state_manager_references.py
   ```
""",
    },
    {
        "pattern": r"ModuleNotFoundError: No module named 'google.cloud.monitoring_v3.proto'",
        "description": "Error al importar el módulo de Google Cloud Monitoring",
        "solution": """
Este error ocurre cuando falta la dependencia de Google Cloud Monitoring.

Soluciones:
1. Instala la dependencia requerida:
   ```
   pip install google-cloud-monitoring
   ```
2. Asegúrate de que la versión de protobuf sea compatible:
   ```
   pip install protobuf==3.20.3
   ```
3. Si estás ejecutando pruebas, considera crear un mock para este módulo.
""",
    },
    {
        "pattern": r"TypeError: StateManagerAdapter.__init__\(\) got an unexpected keyword argument 'use_optimized'",
        "description": "Error al inicializar StateManagerAdapter con un parámetro obsoleto",
        "solution": """
Este error ocurre porque el adaptador del State Manager ha sido actualizado para siempre usar la versión optimizada, por lo que ya no acepta el parámetro `use_optimized`.

Soluciones:
1. Actualiza las instanciaciones del adaptador:
   ```python
   # Antes
   state_manager_adapter = StateManagerAdapter(use_optimized=True)
   
   # Después
   state_manager_adapter = StateManagerAdapter()
   ```
2. Si estás utilizando la instancia global, no necesitas crear una nueva:
   ```python
   from infrastructure.adapters.state_manager_adapter import state_manager_adapter
   ```
""",
    },
]


def run_command(command: List[str], cwd: Optional[Path] = None) -> Tuple[int, str]:
    """
    Ejecuta un comando y devuelve el código de salida y la salida.

    Args:
        command: Comando a ejecutar
        cwd: Directorio de trabajo

    Returns:
        Tuple[int, str]: Código de salida y salida
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return 1, str(e)


def check_dependencies() -> Dict[str, Any]:
    """
    Verifica las dependencias del proyecto.

    Returns:
        Dict[str, Any]: Información sobre las dependencias
    """
    # Verificar dependencias instaladas
    exit_code, output = run_command(["pip", "list"])
    installed_packages = {}

    if exit_code == 0:
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] != "Package":
                installed_packages[parts[0].lower()] = parts[1]

    # Leer dependencias requeridas
    required_packages = {}
    pyproject_path = PROJECT_ROOT / "pyproject.toml"

    if pyproject_path.exists():
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()

            # Extraer dependencias
            dependencies_match = re.search(
                r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL
            )
            if dependencies_match:
                dependencies_str = dependencies_match.group(1)
                dependencies = re.findall(r'"([^"]+)"', dependencies_str)

                for dep in dependencies:
                    parts = re.split(r"[=<>~]", dep, 1)
                    if len(parts) >= 1:
                        name = parts[0].strip().lower()
                        version = parts[1].strip() if len(parts) > 1 else "any"
                        required_packages[name] = version

    # Verificar dependencias faltantes o incompatibles
    missing_packages = []
    for package, version in required_packages.items():
        if package not in installed_packages:
            missing_packages.append(f"{package}{version if version != 'any' else ''}")

    return {
        "installed_packages": installed_packages,
        "required_packages": required_packages,
        "missing_packages": missing_packages,
    }


def check_migration_status() -> Dict[str, Any]:
    """
    Verifica el estado de las migraciones.

    Returns:
        Dict[str, Any]: Estado de las migraciones
    """
    results = {}

    for migration in MIGRATIONS:
        original_path = PROJECT_ROOT / migration["original"]
        optimized_path = PROJECT_ROOT / migration["optimized"]
        adapter_path = PROJECT_ROOT / migration["adapter"]
        status_script_path = PROJECT_ROOT / migration["status_script"]

        original_exists = original_path.exists()
        optimized_exists = optimized_path.exists()
        adapter_exists = adapter_path.exists()
        status_script_exists = status_script_path.exists()

        # Ejecutar script de verificación si existe
        status_output = ""
        status_success = False

        if status_script_exists:
            exit_code, output = run_command(["python", str(status_script_path)])
            status_output = output
            status_success = exit_code == 0

        results[migration["name"]] = {
            "original_exists": original_exists,
            "optimized_exists": optimized_exists,
            "adapter_exists": adapter_exists,
            "status_script_exists": status_script_exists,
            "status_output": status_output,
            "status_success": status_success,
            "migration_complete": (
                not original_exists
                or (optimized_exists and adapter_exists and status_success)
            ),
        }

    return results


def analyze_project_structure() -> Dict[str, Any]:
    """
    Analiza la estructura del proyecto.

    Returns:
        Dict[str, Any]: Información sobre la estructura del proyecto
    """
    structure = {}

    for component in COMPONENTS:
        component_path = PROJECT_ROOT / component
        if not component_path.exists():
            structure[component] = {"exists": False}
            continue

        # Contar archivos Python
        python_files = list(component_path.glob("**/*.py"))

        # Contar líneas de código
        total_lines = 0
        for file in python_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    total_lines += len(f.readlines())
            except Exception:
                pass

        structure[component] = {
            "exists": True,
            "python_files": len(python_files),
            "total_lines": total_lines,
        }

    return structure


def check_test_coverage() -> Dict[str, Any]:
    """
    Verifica la cobertura de pruebas.

    Returns:
        Dict[str, Any]: Información sobre la cobertura de pruebas
    """
    # Ejecutar pytest con cobertura
    exit_code, output = run_command(["python", "-m", "pytest", "--cov=."])

    # Extraer información de cobertura
    coverage_info = {}

    if exit_code == 0:
        # Extraer porcentaje de cobertura total
        total_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if total_match:
            coverage_info["total_percentage"] = int(total_match.group(1))

        # Extraer cobertura por componente
        for component in COMPONENTS:
            component_match = re.search(rf"{component}/\s+\d+\s+\d+\s+(\d+)%", output)
            if component_match:
                coverage_info[component] = int(component_match.group(1))

    return {"success": exit_code == 0, "output": output, "coverage": coverage_info}


def generate_error_solutions() -> Dict[str, Any]:
    """
    Genera soluciones para errores comunes.

    Returns:
        Dict[str, Any]: Soluciones para errores comunes
    """
    # Ejecutar pruebas para capturar errores
    exit_code, output = run_command(["python", "-m", "pytest"])

    # Identificar errores y sus soluciones
    identified_errors = []

    for error in COMMON_ERRORS:
        if re.search(error["pattern"], output):
            identified_errors.append(
                {"description": error["description"], "solution": error["solution"]}
            )

    return {
        "test_success": exit_code == 0,
        "test_output": output,
        "identified_errors": identified_errors,
    }


def generate_recommendations(
    dependencies: Dict[str, Any],
    migrations: Dict[str, Any],
    structure: Dict[str, Any],
    test_coverage: Dict[str, Any],
    error_solutions: Dict[str, Any],
) -> List[str]:
    """
    Genera recomendaciones basadas en el análisis.

    Args:
        dependencies: Información sobre dependencias
        migrations: Estado de las migraciones
        structure: Estructura del proyecto
        test_coverage: Cobertura de pruebas
        error_solutions: Soluciones para errores

    Returns:
        List[str]: Lista de recomendaciones
    """
    recommendations = []

    # Recomendaciones sobre dependencias
    if dependencies["missing_packages"]:
        recommendations.append(
            "### Dependencias Faltantes\n"
            "Instala las siguientes dependencias para resolver problemas de importación:\n"
            "```\n"
            f"pip install {' '.join(dependencies['missing_packages'])}\n"
            "```"
        )

    # Recomendaciones sobre migraciones
    incomplete_migrations = [
        name for name, info in migrations.items() if not info["migration_complete"]
    ]
    if incomplete_migrations:
        recommendations.append(
            "### Migraciones Incompletas\n"
            "Completa las siguientes migraciones para mejorar la estabilidad y rendimiento:\n"
            + "\n".join(f"- {name}" for name in incomplete_migrations)
        )

    # Recomendaciones sobre pruebas
    if (
        test_coverage.get("success")
        and test_coverage.get("coverage", {}).get("total_percentage", 0) < 70
    ):
        recommendations.append(
            "### Cobertura de Pruebas Baja\n"
            "Aumenta la cobertura de pruebas para mejorar la calidad del código y reducir errores:\n"
            "- Agrega pruebas unitarias para componentes críticos\n"
            "- Implementa pruebas de integración para verificar la interacción entre componentes\n"
            "- Utiliza mocks para aislar las pruebas de dependencias externas"
        )

    # Recomendaciones sobre estructura
    if any(not info["exists"] for component, info in structure.items()):
        missing_components = [
            component for component, info in structure.items() if not info["exists"]
        ]
        recommendations.append(
            "### Componentes Faltantes\n"
            "Los siguientes componentes no existen o no están en la ubicación esperada:\n"
            + "\n".join(f"- {component}" for component in missing_components)
        )

    # Recomendaciones sobre errores
    if error_solutions["identified_errors"]:
        recommendations.append(
            "### Errores Identificados\n"
            "Se han identificado los siguientes errores con sus soluciones:\n"
            + "\n".join(
                f"- {error['description']}"
                for error in error_solutions["identified_errors"]
            )
        )

    return recommendations


def generate_summary_report(
    dependencies: Dict[str, Any],
    migrations: Dict[str, Any],
    structure: Dict[str, Any],
    test_coverage: Dict[str, Any],
    error_solutions: Dict[str, Any],
    recommendations: List[str],
) -> str:
    """
    Genera un informe de resumen del proyecto.

    Args:
        dependencies: Información sobre dependencias
        migrations: Estado de las migraciones
        structure: Estructura del proyecto
        test_coverage: Cobertura de pruebas
        error_solutions: Soluciones para errores
        recommendations: Recomendaciones

    Returns:
        str: Informe de resumen
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = [
        f"# Resumen del Proyecto NGX Agents",
        f"Generado el: {now}",
        "",
        "## Estado del Proyecto",
        "",
        "### Estructura del Proyecto",
        "| Componente | Archivos Python | Líneas de Código | Estado |",
        "|------------|-----------------|------------------|--------|",
    ]

    for component, info in structure.items():
        status = "✅ Presente" if info["exists"] else "❌ Faltante"
        files = info.get("python_files", 0) if info["exists"] else 0
        lines = info.get("total_lines", 0) if info["exists"] else 0
        report.append(f"| {component} | {files} | {lines} | {status} |")

    report.extend(
        [
            "",
            "### Estado de las Migraciones",
            "| Componente | Estado | Detalles |",
            "|------------|--------|----------|",
        ]
    )

    for name, info in migrations.items():
        status = "✅ Completa" if info["migration_complete"] else "❌ Incompleta"
        details = []

        if info["original_exists"]:
            details.append("Original presente")
        if info["optimized_exists"]:
            details.append("Optimizado presente")
        if info["adapter_exists"]:
            details.append("Adaptador presente")
        if info["status_script_exists"] and info["status_success"]:
            details.append("Verificación exitosa")

        report.append(f"| {name} | {status} | {', '.join(details)} |")

    report.extend(
        [
            "",
            "### Dependencias",
            f"- Total de dependencias requeridas: {len(dependencies['required_packages'])}",
            f"- Dependencias instaladas: {len(dependencies['installed_packages'])}",
            f"- Dependencias faltantes: {len(dependencies['missing_packages'])}",
            "",
        ]
    )

    if dependencies["missing_packages"]:
        report.extend(
            [
                "#### Dependencias Faltantes",
                "```",
                "\n".join(dependencies["missing_packages"]),
                "```",
                "",
            ]
        )

    report.extend(
        [
            "### Cobertura de Pruebas",
        ]
    )

    if test_coverage.get("success"):
        report.extend(
            [
                f"- Cobertura total: {test_coverage.get('coverage', {}).get('total_percentage', 0)}%",
                "",
                "| Componente | Cobertura |",
                "|------------|-----------|",
            ]
        )

        for component in COMPONENTS:
            coverage = test_coverage.get("coverage", {}).get(component, 0)
            report.append(f"| {component} | {coverage}% |")
    else:
        report.append("No se pudo determinar la cobertura de pruebas.")

    report.extend(
        [
            "",
            "## Problemas Identificados y Soluciones",
            "",
        ]
    )

    if error_solutions["identified_errors"]:
        for error in error_solutions["identified_errors"]:
            report.extend(
                [
                    f"### {error['description']}",
                    error["solution"],
                    "",
                ]
            )
    else:
        report.append("No se identificaron errores conocidos.")

    report.extend(
        [
            "",
            "## Recomendaciones",
            "",
        ]
    )

    if recommendations:
        report.extend(recommendations)
    else:
        report.append("No hay recomendaciones específicas en este momento.")

    report.extend(
        [
            "",
            "## Guía de Desarrollo",
            "",
            "### Flujo de Trabajo Recomendado",
            "",
            "1. **Completar las migraciones pendientes**",
            "   - Finalizar una migración a la vez",
            "   - Verificar que todo funciona correctamente antes de pasar a la siguiente",
            "   - Ejecutar los scripts de verificación para asegurar que no queden referencias a componentes antiguos",
            "",
            "2. **Resolver problemas de dependencias**",
            "   - Instalar todas las dependencias faltantes",
            "   - Asegurarse de que las versiones sean compatibles",
            "   - Considerar el uso de entornos virtuales para aislar las dependencias",
            "",
            "3. **Mejorar el sistema de pruebas**",
            "   - Implementar mocks robustos para componentes externos",
            "   - Separar pruebas unitarias de pruebas de integración",
            "   - Utilizar inyección de dependencias en lugar de importaciones directas",
            "",
            "4. **Refactorizar la arquitectura**",
            "   - Reducir dependencias circulares",
            "   - Definir interfaces claras entre componentes",
            "   - Documentar la arquitectura y las decisiones de diseño",
            "",
            "### Mejores Prácticas",
            "",
            "- **Gestión de Dependencias**",
            "  - Mantener un registro de versiones compatibles",
            "  - Crear scripts de verificación de compatibilidad",
            "  - Documentar las dependencias externas",
            "",
            "- **Arquitectura**",
            "  - Utilizar patrones de diseño como inyección de dependencias",
            "  - Evitar dependencias circulares",
            "  - Definir interfaces claras entre componentes",
            "",
            "- **Pruebas**",
            "  - Implementar pruebas unitarias para componentes críticos",
            "  - Utilizar mocks para aislar las pruebas de dependencias externas",
            "  - Separar pruebas unitarias de pruebas de integración",
            "",
            "- **Documentación**",
            "  - Documentar la arquitectura y las decisiones de diseño",
            "  - Mantener un registro de cambios",
            "  - Documentar los procesos de migración",
        ]
    )

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Generar resumen del proyecto NGX Agents"
    )
    parser.add_argument("--output", "-o", help="Archivo de salida para el informe")
    parser.add_argument(
        "--json", "-j", action="store_true", help="Generar salida en formato JSON"
    )

    args = parser.parse_args()

    print("Analizando el proyecto...")

    # Recopilar información
    dependencies = check_dependencies()
    migrations = check_migration_status()
    structure = analyze_project_structure()
    test_coverage = check_test_coverage()
    error_solutions = generate_error_solutions()

    # Generar recomendaciones
    recommendations = generate_recommendations(
        dependencies, migrations, structure, test_coverage, error_solutions
    )

    # Generar informe
    if args.json:
        data = {
            "dependencies": dependencies,
            "migrations": migrations,
            "structure": structure,
            "test_coverage": test_coverage,
            "error_solutions": error_solutions,
            "recommendations": recommendations,
        }
        output = json.dumps(data, indent=2)
    else:
        output = generate_summary_report(
            dependencies,
            migrations,
            structure,
            test_coverage,
            error_solutions,
            recommendations,
        )

    # Guardar o imprimir el informe
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Informe guardado en: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()

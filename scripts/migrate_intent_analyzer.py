#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para completar la migración del Intent Analyzer.

Este script realiza las siguientes tareas:
1. Verifica que todas las dependencias necesarias estén instaladas
2. Realiza pruebas de compatibilidad entre el Intent Analyzer original y el optimizado
3. Actualiza las referencias en el código para usar el Intent Analyzer optimizado
4. Genera un informe de la migración
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import importlib.util
import shutil

# Añadir directorio raíz al path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuración de logging
from core.logging_config import get_logger
logger = get_logger(__name__)

# Constantes
BACKUP_DIR = "backups/intent_analyzer_migration"
MIGRATION_REPORT_FILE = "intent_analyzer_migration_report.json"

# Archivos a verificar/actualizar
FILES_TO_CHECK = [
    "core/intent_analyzer.py",
    "core/intent_analyzer_optimized.py",
    "infrastructure/adapters/intent_analyzer_adapter.py",
    "tests/test_adapters/test_intent_analyzer_adapter.py"
]

# Dependencias requeridas
REQUIRED_DEPENDENCIES = [
    "asyncio",
    "json",
    "uuid"
]

# Dependencias opcionales
OPTIONAL_DEPENDENCIES = [
    "numpy",
    "opentelemetry-api",
    "opentelemetry-sdk",
    "opentelemetry-instrumentation"
]

class IntentAnalyzerMigrationTool:
    """Herramienta para migrar el Intent Analyzer."""
    
    def __init__(
        self,
        base_dir: str,
        backup: bool = True,
        test_mode: bool = False,
        force: bool = False,
        report_file: str = MIGRATION_REPORT_FILE
    ):
        """
        Inicializa la herramienta de migración.
        
        Args:
            base_dir: Directorio base del proyecto
            backup: Si es True, crea un backup de los archivos antes de modificarlos
            test_mode: Si es True, solo realiza pruebas sin modificar archivos
            force: Si es True, fuerza la migración sin confirmación
            report_file: Nombre del archivo de informe
        """
        self.base_dir = os.path.abspath(base_dir)
        self.backup = backup
        self.test_mode = test_mode
        self.force = force
        self.report_file = report_file
        
        self.backup_dir = os.path.join(self.base_dir, f"{BACKUP_DIR}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.migration_report = {
            "timestamp": datetime.now().isoformat(),
            "base_dir": self.base_dir,
            "backup_dir": self.backup_dir if backup else None,
            "test_mode": test_mode,
            "dependencies": {
                "required": {},
                "optional": {}
            },
            "files": {
                "checked": [],
                "modified": [],
                "errors": []
            },
            "tests": {
                "passed": [],
                "failed": []
            },
            "status": "pending"
        }
    
    async def run(self) -> Dict[str, Any]:
        """
        Ejecuta la migración completa.
        
        Returns:
            Dict[str, Any]: Informe de la migración
        """
        try:
            logger.info("Iniciando migración del Intent Analyzer")
            
            # Verificar dependencias
            self._check_dependencies()
            
            # Crear directorio de backup si es necesario
            if self.backup and not self.test_mode:
                self._create_backup_dir()
            
            # Verificar archivos necesarios
            self._check_required_files()
            
            # Ejecutar pruebas de compatibilidad
            await self._run_compatibility_tests()
            
            # Actualizar referencias en el código
            if not self.test_mode:
                self._update_references()
            
            # Generar informe
            self.migration_report["status"] = "completed"
            self._generate_report()
            
            logger.info(f"Migración completada. Informe generado en {self.report_file}")
            return self.migration_report
            
        except Exception as e:
            logger.error(f"Error durante la migración: {str(e)}")
            self.migration_report["status"] = "failed"
            self.migration_report["error"] = str(e)
            self._generate_report()
            return self.migration_report
    
    def _check_dependencies(self) -> None:
        """Verifica que todas las dependencias necesarias estén instaladas."""
        logger.info("Verificando dependencias...")
        
        # Verificar dependencias requeridas
        for dep in REQUIRED_DEPENDENCIES:
            try:
                importlib.import_module(dep.split('.')[0])
                self.migration_report["dependencies"]["required"][dep] = "installed"
                logger.info(f"Dependencia requerida {dep}: Instalada")
            except ImportError:
                self.migration_report["dependencies"]["required"][dep] = "missing"
                logger.warning(f"Dependencia requerida {dep}: Faltante")
                if not self.force:
                    raise ImportError(f"Dependencia requerida {dep} no está instalada")
        
        # Verificar dependencias opcionales
        for dep in OPTIONAL_DEPENDENCIES:
            try:
                importlib.import_module(dep.split('.')[0])
                self.migration_report["dependencies"]["optional"][dep] = "installed"
                logger.info(f"Dependencia opcional {dep}: Instalada")
            except ImportError:
                self.migration_report["dependencies"]["optional"][dep] = "missing"
                logger.warning(f"Dependencia opcional {dep}: Faltante")
    
    def _create_backup_dir(self) -> None:
        """Crea el directorio de backup."""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.info(f"Directorio de backup creado: {self.backup_dir}")
    
    def _check_required_files(self) -> None:
        """Verifica que todos los archivos necesarios existan."""
        logger.info("Verificando archivos necesarios...")
        
        for file_path in FILES_TO_CHECK:
            full_path = os.path.join(self.base_dir, file_path)
            if os.path.exists(full_path):
                self.migration_report["files"]["checked"].append(file_path)
                logger.info(f"Archivo {file_path}: Encontrado")
                
                # Crear backup si es necesario
                if self.backup and not self.test_mode:
                    backup_path = os.path.join(self.backup_dir, file_path)
                    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                    shutil.copy2(full_path, backup_path)
                    logger.info(f"Backup creado: {backup_path}")
            else:
                self.migration_report["files"]["errors"].append({
                    "file": file_path,
                    "error": "not_found"
                })
                logger.error(f"Archivo {file_path}: No encontrado")
                if not self.force:
                    raise FileNotFoundError(f"Archivo requerido {file_path} no encontrado")
    
    async def _run_compatibility_tests(self) -> None:
        """Ejecuta pruebas de compatibilidad entre el Intent Analyzer original y el optimizado."""
        logger.info("Ejecutando pruebas de compatibilidad...")
        
        try:
            # Importar adaptador del Intent Analyzer
            from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
            
            # Pruebas básicas
            test_cases = [
                self._test_analyze_intent,
                self._test_analyze_intents_with_embeddings,
                self._test_switching_analyzers,
                self._test_error_handling
            ]
            
            for test_case in test_cases:
                test_name = test_case.__name__
                try:
                    await test_case()
                    self.migration_report["tests"]["passed"].append(test_name)
                    logger.info(f"Prueba {test_name}: Pasada")
                except Exception as e:
                    self.migration_report["tests"]["failed"].append({
                        "test": test_name,
                        "error": str(e)
                    })
                    logger.error(f"Prueba {test_name}: Fallida - {str(e)}")
                    if not self.force:
                        raise
            
        except Exception as e:
            logger.error(f"Error durante las pruebas de compatibilidad: {str(e)}")
            if not self.force:
                raise
    
    async def _test_analyze_intent(self) -> None:
        """Prueba el análisis de intención básico."""
        from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
        
        # Inicializar adaptador
        await intent_analyzer_adapter.initialize()
        
        # Probar con el analizador original
        intent_analyzer_adapter.set_use_optimized(False)
        intents_original = await intent_analyzer_adapter.analyze_intent(
            user_query="Necesito un plan de entrenamiento para ganar masa muscular",
            conversation_id="test_conversation"
        )
        
        # Probar con el analizador optimizado
        intent_analyzer_adapter.set_use_optimized(True)
        intents_optimized = await intent_analyzer_adapter.analyze_intent(
            user_query="Necesito un plan de entrenamiento para ganar masa muscular",
            conversation_id="test_conversation"
        )
        
        # Verificar resultados
        assert intents_original is not None
        assert intents_optimized is not None
        assert len(intents_original) > 0
        assert len(intents_optimized) > 0
        
        # Verificar que ambos analizadores detecten intenciones similares
        original_types = [intent.intent_type for intent in intents_original]
        optimized_types = [intent.intent_type for intent in intents_optimized]
        
        # No es necesario que sean exactamente iguales, pero debería haber alguna coincidencia
        assert len(set(original_types).intersection(set(optimized_types))) > 0 or \
               "training_request" in original_types or "training_request" in optimized_types
    
    async def _test_analyze_intents_with_embeddings(self) -> None:
        """Prueba el análisis de intenciones con embeddings."""
        from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
        
        # Inicializar adaptador
        await intent_analyzer_adapter.initialize()
        
        # Probar con el analizador original
        intent_analyzer_adapter.set_use_optimized(False)
        intents_original = await intent_analyzer_adapter.analyze_intents_with_embeddings(
            user_query="¿Cuál es la mejor dieta para perder peso?",
            conversation_id="test_conversation"
        )
        
        # Probar con el analizador optimizado
        intent_analyzer_adapter.set_use_optimized(True)
        intents_optimized = await intent_analyzer_adapter.analyze_intents_with_embeddings(
            user_query="¿Cuál es la mejor dieta para perder peso?",
            conversation_id="test_conversation"
        )
        
        # Verificar resultados
        assert intents_original is not None
        assert intents_optimized is not None
        assert len(intents_original) > 0
        assert len(intents_optimized) > 0
    
    async def _test_switching_analyzers(self) -> None:
        """Prueba cambiar entre analizadores."""
        from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
        
        # Inicializar adaptador
        await intent_analyzer_adapter.initialize()
        
        # Cambiar a original
        intent_analyzer_adapter.set_use_optimized(False)
        assert intent_analyzer_adapter.use_optimized is False
        
        # Analizar con original
        intents1 = await intent_analyzer_adapter.analyze_intent(
            user_query="Necesito motivación para entrenar",
            conversation_id="test_conversation"
        )
        
        # Cambiar a optimizado
        intent_analyzer_adapter.set_use_optimized(True)
        assert intent_analyzer_adapter.use_optimized is True
        
        # Analizar con optimizado
        intents2 = await intent_analyzer_adapter.analyze_intent(
            user_query="Necesito motivación para entrenar",
            conversation_id="test_conversation"
        )
        
        # Verificar que ambos funcionan
        assert intents1 is not None and len(intents1) > 0
        assert intents2 is not None and len(intents2) > 0
    
    async def _test_error_handling(self) -> None:
        """Prueba el manejo de errores."""
        from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
        
        # Inicializar adaptador
        await intent_analyzer_adapter.initialize()
        
        # Probar con consulta vacía (debería manejar el error)
        intents = await intent_analyzer_adapter.analyze_intent(
            user_query="",
            conversation_id="test_conversation"
        )
        
        # Verificar que devuelve una intención de fallback
        assert intents is not None
        assert len(intents) > 0
        
        # Al menos una intención debe tener metadata con fallback=True
        fallback_found = False
        for intent in intents:
            if hasattr(intent, "metadata") and intent.metadata.get("fallback") is True:
                fallback_found = True
                break
        
        assert fallback_found
    
    def _update_references(self) -> None:
        """Actualiza las referencias en el código para usar el Intent Analyzer optimizado."""
        logger.info("Actualizando referencias en el código...")
        
        # Archivos a actualizar y sus patrones de búsqueda/reemplazo
        files_to_update = [
            {
                "path": "infrastructure/adapters/orchestrator_adapter.py",
                "patterns": [
                    {
                        "search": "from core.intent_analyzer import intent_analyzer",
                        "replace": "from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter as intent_analyzer"
                    },
                    {
                        "search": "from core.intent_analyzer import Intent, IntentEntity",
                        "replace": "from core.intent_analyzer_optimized import Intent, IntentEntity"
                    }
                ]
            },
            {
                "path": "agents/base_agent.py",
                "patterns": [
                    {
                        "search": "from core.intent_analyzer import intent_analyzer",
                        "replace": "from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter as intent_analyzer"
                    }
                ]
            },
            {
                "path": "infrastructure/adapters/intent_analyzer_adapter.py",
                "patterns": [
                    {
                        "search": "def __init__(self, use_optimized: bool = False):",
                        "replace": "def __init__(self, use_optimized: bool = True):"
                    }
                ]
            }
        ]
        
        for file_info in files_to_update:
            file_path = os.path.join(self.base_dir, file_info["path"])
            if os.path.exists(file_path):
                try:
                    # Leer contenido actual
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Aplicar patrones de reemplazo
                    original_content = content
                    for pattern in file_info["patterns"]:
                        content = content.replace(pattern["search"], pattern["replace"])
                    
                    # Si hubo cambios, guardar el archivo actualizado
                    if content != original_content:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        
                        self.migration_report["files"]["modified"].append(file_info["path"])
                        logger.info(f"Archivo actualizado: {file_info['path']}")
                    else:
                        logger.info(f"No se requieren cambios en: {file_info['path']}")
                        
                except Exception as e:
                    self.migration_report["files"]["errors"].append({
                        "file": file_info["path"],
                        "error": str(e)
                    })
                    logger.error(f"Error al actualizar {file_info['path']}: {str(e)}")
            else:
                logger.warning(f"Archivo no encontrado: {file_info['path']}")
    
    def _generate_report(self) -> None:
        """Genera un informe de la migración."""
        # Añadir timestamp de finalización
        self.migration_report["end_timestamp"] = datetime.now().isoformat()
        
        # Calcular estadísticas
        self.migration_report["summary"] = {
            "files_checked": len(self.migration_report["files"]["checked"]),
            "files_modified": len(self.migration_report["files"]["modified"]),
            "files_with_errors": len(self.migration_report["files"]["errors"]),
            "tests_passed": len(self.migration_report["tests"]["passed"]),
            "tests_failed": len(self.migration_report["tests"]["failed"])
        }
        
        # Guardar informe
        report_path = os.path.join(self.base_dir, self.report_file)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.migration_report, f, indent=2)
        
        logger.info(f"Informe de migración generado: {report_path}")
        
        # Mostrar resumen
        print("\nResumen de la migración:")
        print(f"  - Archivos verificados: {self.migration_report['summary']['files_checked']}")
        print(f"  - Archivos modificados: {self.migration_report['summary']['files_modified']}")
        print(f"  - Archivos con errores: {self.migration_report['summary']['files_with_errors']}")
        print(f"  - Pruebas pasadas: {self.migration_report['summary']['tests_passed']}")
        print(f"  - Pruebas fallidas: {self.migration_report['summary']['tests_failed']}")
        print(f"  - Estado: {self.migration_report['status']}")
        
        if self.migration_report["status"] == "failed":
            print(f"  - Error: {self.migration_report.get('error', 'Desconocido')}")
        
        if self.backup:
            print(f"  - Directorio de backup: {self.backup_dir}")
        
        print(f"  - Informe completo: {report_path}")

async def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Herramienta para migrar el Intent Analyzer")
    
    parser.add_argument("--base-dir", type=str, default=".",
                        help="Directorio base del proyecto (default: directorio actual)")
    parser.add_argument("--no-backup", action="store_true",
                        help="No crear backup de los archivos antes de modificarlos")
    parser.add_argument("--test-mode", action="store_true",
                        help="Ejecutar en modo de prueba sin modificar archivos")
    parser.add_argument("--force", action="store_true",
                        help="Forzar la migración incluso si hay errores")
    parser.add_argument("--report-file", type=str, default=MIGRATION_REPORT_FILE,
                        help=f"Nombre del archivo de informe (default: {MIGRATION_REPORT_FILE})")
    
    args = parser.parse_args()
    
    # Crear y ejecutar la herramienta de migración
    migration_tool = IntentAnalyzerMigrationTool(
        base_dir=args.base_dir,
        backup=not args.no_backup,
        test_mode=args.test_mode,
        force=args.force,
        report_file=args.report_file
    )
    
    await migration_tool.run()

if __name__ == "__main__":
    asyncio.run(main())

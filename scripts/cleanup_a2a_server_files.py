#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para limpiar archivos redundantes después de la migración del servidor A2A.

Este script realiza las siguientes tareas:
1. Identifica archivos redundantes relacionados con el servidor A2A original
2. Verifica que todos los componentes estén utilizando el servidor A2A optimizado
3. Elimina o mueve a un directorio de archivado los archivos redundantes
4. Genera un informe de la limpieza
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
import re
from typing import Dict, Any, List, Set, Tuple
from datetime import datetime
import importlib.util
import shutil

# Añadir directorio raíz al path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuración de logging
from core.logging_config import get_logger
logger = get_logger(__name__)

# Constantes
ARCHIVE_DIR = "archived/a2a_server"
CLEANUP_REPORT_FILE = "a2a_server_cleanup_report.json"

# Archivos potencialmente redundantes
REDUNDANT_FILES = [
    "infrastructure/a2a_server.py",
    "tests/test_a2a_server.py"
]

# Directorios a escanear para referencias
DIRS_TO_SCAN = [
    "agents",
    "app",
    "core",
    "infrastructure",
    "tests"
]

# Patrones para buscar referencias al servidor A2A original
REFERENCE_PATTERNS = [
    r"from\s+infrastructure\.a2a_server\s+import",
    r"import\s+infrastructure\.a2a_server",
    r"infrastructure\.a2a_server\."
]

class A2ACleanupTool:
    """Herramienta para limpiar archivos redundantes del servidor A2A."""
    
    def __init__(
        self,
        base_dir: str,
        archive: bool = True,
        test_mode: bool = False,
        force: bool = False,
        report_file: str = CLEANUP_REPORT_FILE
    ):
        """
        Inicializa la herramienta de limpieza.
        
        Args:
            base_dir: Directorio base del proyecto
            archive: Si es True, archiva los archivos en lugar de eliminarlos
            test_mode: Si es True, solo realiza pruebas sin modificar archivos
            force: Si es True, fuerza la limpieza sin confirmación
            report_file: Nombre del archivo de informe
        """
        self.base_dir = os.path.abspath(base_dir)
        self.archive = archive
        self.test_mode = test_mode
        self.force = force
        self.report_file = report_file
        
        self.archive_dir = os.path.join(self.base_dir, f"{ARCHIVE_DIR}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.cleanup_report = {
            "timestamp": datetime.now().isoformat(),
            "base_dir": self.base_dir,
            "archive_dir": self.archive_dir if archive else None,
            "test_mode": test_mode,
            "files": {
                "redundant": [],
                "with_references": [],
                "archived": [],
                "deleted": [],
                "errors": []
            },
            "references": {
                "total": 0,
                "files": []
            },
            "status": "pending"
        }
    
    async def run(self) -> Dict[str, Any]:
        """
        Ejecuta la limpieza completa.
        
        Returns:
            Dict[str, Any]: Informe de la limpieza
        """
        try:
            logger.info("Iniciando limpieza de archivos redundantes del servidor A2A")
            
            # Identificar archivos redundantes
            redundant_files = self._identify_redundant_files()
            
            # Buscar referencias a los archivos redundantes
            references = self._find_references()
            
            # Crear directorio de archivado si es necesario
            if self.archive and not self.test_mode and redundant_files:
                self._create_archive_dir()
            
            # Eliminar o archivar archivos redundantes
            if not self.test_mode:
                self._cleanup_files(redundant_files, references)
            
            # Generar informe
            self.cleanup_report["status"] = "completed"
            self._generate_report()
            
            logger.info(f"Limpieza completada. Informe generado en {self.report_file}")
            return self.cleanup_report
            
        except Exception as e:
            logger.error(f"Error durante la limpieza: {str(e)}")
            self.cleanup_report["status"] = "failed"
            self.cleanup_report["error"] = str(e)
            self._generate_report()
            return self.cleanup_report
    
    def _identify_redundant_files(self) -> List[str]:
        """
        Identifica archivos redundantes relacionados con el servidor A2A.
        
        Returns:
            List[str]: Lista de archivos redundantes
        """
        logger.info("Identificando archivos redundantes...")
        
        redundant_files = []
        
        for file_path in REDUNDANT_FILES:
            full_path = os.path.join(self.base_dir, file_path)
            if os.path.exists(full_path):
                redundant_files.append(file_path)
                self.cleanup_report["files"]["redundant"].append(file_path)
                logger.info(f"Archivo redundante identificado: {file_path}")
        
        return redundant_files
    
    def _find_references(self) -> Dict[str, List[str]]:
        """
        Busca referencias a los archivos redundantes en el código.
        
        Returns:
            Dict[str, List[str]]: Diccionario con archivos y sus referencias
        """
        logger.info("Buscando referencias a archivos redundantes...")
        
        references = {}
        total_references = 0
        
        # Compilar patrones de búsqueda
        patterns = [re.compile(pattern) for pattern in REFERENCE_PATTERNS]
        
        # Escanear directorios
        for dir_path in DIRS_TO_SCAN:
            full_dir_path = os.path.join(self.base_dir, dir_path)
            if not os.path.exists(full_dir_path):
                logger.warning(f"Directorio no encontrado: {dir_path}")
                continue
            
            # Recorrer archivos Python
            for root, _, files in os.walk(full_dir_path):
                for file in files:
                    if not file.endswith('.py'):
                        continue
                    
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.base_dir)
                    
                    # Verificar si es un archivo redundante (no buscar referencias en ellos)
                    if rel_path in REDUNDANT_FILES:
                        continue
                    
                    # Buscar referencias
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            found_references = []
                            for pattern in patterns:
                                matches = pattern.findall(content)
                                if matches:
                                    found_references.extend(matches)
                            
                            if found_references:
                                references[rel_path] = found_references
                                total_references += len(found_references)
                                
                                self.cleanup_report["references"]["files"].append({
                                    "file": rel_path,
                                    "references": found_references
                                })
                                
                                logger.info(f"Referencias encontradas en {rel_path}: {len(found_references)}")
                    
                    except Exception as e:
                        logger.error(f"Error al analizar {rel_path}: {str(e)}")
        
        self.cleanup_report["references"]["total"] = total_references
        logger.info(f"Total de referencias encontradas: {total_references}")
        
        return references
    
    def _create_archive_dir(self) -> None:
        """Crea el directorio de archivado."""
        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir)
            logger.info(f"Directorio de archivado creado: {self.archive_dir}")
    
    def _cleanup_files(self, redundant_files: List[str], references: Dict[str, List[str]]) -> None:
        """
        Elimina o archiva archivos redundantes.
        
        Args:
            redundant_files: Lista de archivos redundantes
            references: Diccionario con archivos y sus referencias
        """
        logger.info("Limpiando archivos redundantes...")
        
        for file_path in redundant_files:
            full_path = os.path.join(self.base_dir, file_path)
            
            # Verificar si hay referencias a este archivo
            has_references = False
            for ref_file, ref_list in references.items():
                if any(file_path.replace('/', '.').replace('.py', '') in ref for ref in ref_list):
                    has_references = True
                    self.cleanup_report["files"]["with_references"].append({
                        "file": file_path,
                        "referenced_by": ref_file
                    })
                    logger.warning(f"Archivo {file_path} tiene referencias en {ref_file}")
                    break
            
            if has_references and not self.force:
                logger.warning(f"No se puede eliminar {file_path} porque tiene referencias")
                continue
            
            try:
                if self.archive:
                    # Archivar archivo
                    archive_path = os.path.join(self.archive_dir, file_path)
                    os.makedirs(os.path.dirname(archive_path), exist_ok=True)
                    shutil.copy2(full_path, archive_path)
                    
                    self.cleanup_report["files"]["archived"].append(file_path)
                    logger.info(f"Archivo archivado: {file_path} -> {archive_path}")
                
                # Eliminar archivo
                os.remove(full_path)
                
                self.cleanup_report["files"]["deleted"].append(file_path)
                logger.info(f"Archivo eliminado: {file_path}")
                
            except Exception as e:
                self.cleanup_report["files"]["errors"].append({
                    "file": file_path,
                    "error": str(e)
                })
                logger.error(f"Error al limpiar {file_path}: {str(e)}")
    
    def _generate_report(self) -> None:
        """Genera un informe de la limpieza."""
        # Añadir timestamp de finalización
        self.cleanup_report["end_timestamp"] = datetime.now().isoformat()
        
        # Calcular estadísticas
        self.cleanup_report["summary"] = {
            "redundant_files": len(self.cleanup_report["files"]["redundant"]),
            "files_with_references": len(self.cleanup_report["files"]["with_references"]),
            "archived_files": len(self.cleanup_report["files"]["archived"]),
            "deleted_files": len(self.cleanup_report["files"]["deleted"]),
            "files_with_errors": len(self.cleanup_report["files"]["errors"]),
            "total_references": self.cleanup_report["references"]["total"]
        }
        
        # Guardar informe
        report_path = os.path.join(self.base_dir, self.report_file)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.cleanup_report, f, indent=2)
        
        logger.info(f"Informe de limpieza generado: {report_path}")
        
        # Mostrar resumen
        print("\nResumen de la limpieza:")
        print(f"  - Archivos redundantes: {self.cleanup_report['summary']['redundant_files']}")
        print(f"  - Archivos con referencias: {self.cleanup_report['summary']['files_with_references']}")
        print(f"  - Archivos archivados: {self.cleanup_report['summary']['archived_files']}")
        print(f"  - Archivos eliminados: {self.cleanup_report['summary']['deleted_files']}")
        print(f"  - Archivos con errores: {self.cleanup_report['summary']['files_with_errors']}")
        print(f"  - Total de referencias: {self.cleanup_report['summary']['total_references']}")
        print(f"  - Estado: {self.cleanup_report['status']}")
        
        if self.cleanup_report["status"] == "failed":
            print(f"  - Error: {self.cleanup_report.get('error', 'Desconocido')}")
        
        if self.archive:
            print(f"  - Directorio de archivado: {self.archive_dir}")
        
        print(f"  - Informe completo: {report_path}")

async def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Herramienta para limpiar archivos redundantes del servidor A2A")
    
    parser.add_argument("--base-dir", type=str, default=".",
                        help="Directorio base del proyecto (default: directorio actual)")
    parser.add_argument("--no-archive", action="store_true",
                        help="Eliminar archivos en lugar de archivarlos")
    parser.add_argument("--test-mode", action="store_true",
                        help="Ejecutar en modo de prueba sin modificar archivos")
    parser.add_argument("--force", action="store_true",
                        help="Forzar la limpieza incluso si hay referencias")
    parser.add_argument("--report-file", type=str, default=CLEANUP_REPORT_FILE,
                        help=f"Nombre del archivo de informe (default: {CLEANUP_REPORT_FILE})")
    
    args = parser.parse_args()
    
    # Crear y ejecutar la herramienta de limpieza
    cleanup_tool = A2ACleanupTool(
        base_dir=args.base_dir,
        archive=not args.no_archive,
        test_mode=args.test_mode,
        force=args.force,
        report_file=args.report_file
    )
    
    await cleanup_tool.run()

if __name__ == "__main__":
    asyncio.run(main())

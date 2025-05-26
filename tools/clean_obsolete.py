import os
import shutil
from core.logging_config import get_logger


# Lista de archivos y directorios a eliminar
# Asegúrate de que estas rutas son relativas al directorio raíz del proyecto
# o utiliza rutas absolutas si es necesario.
# Para este script, asumimos que se ejecuta desde la raíz del proyecto.
# Si no, ajusta las rutas según sea necesario.

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

paths_to_remove = [
    os.path.join(PROJECT_ROOT, ".obsolete"),
    os.path.join(
        PROJECT_ROOT, "clients", "vertex_ai_client.py"
    ),  # Archivo original refactorizado
    os.path.join(PROJECT_ROOT, "core", "state_manager.py"),
    os.path.join(PROJECT_ROOT, "core", "intent_analyzer.py"),
    # Archivos de prueba obsoletos relacionados con Vertex AI
    os.path.join(PROJECT_ROOT, "tests", "test_vertex_ai_client_optimized_simple.py"),
    os.path.join(PROJECT_ROOT, "tests", "conftest_vertex.py"),
]

logger = get_logger(__name__)


def clean_obsolete_files():
    """
    Elimina archivos y directorios obsoletos especificados en paths_to_remove.
    """
    logger.info("Iniciando limpieza de archivos y directorios obsoletos...")
    for path_to_delete in paths_to_remove:
        absolute_path = os.path.abspath(path_to_delete)
        if os.path.exists(absolute_path):
            try:
                if os.path.isfile(absolute_path):
                    os.remove(absolute_path)
                    logger.info(f"Archivo eliminado: {absolute_path}")
                elif os.path.isdir(absolute_path):
                    shutil.rmtree(absolute_path)
                    logger.info(f"Directorio eliminado: {absolute_path}")
            except OSError as e:
                logger.error(f"Error eliminando {absolute_path}: {e.strerror}")
        else:
            logger.info(f"Ruta no encontrada, omitiendo: {absolute_path}")
    logger.info("Limpieza completada.")


if __name__ == "__main__":
    # Confirmación antes de ejecutar
    # Comentado para ejecución automática por el agente,
    # pero es buena práctica tener una confirmación si se ejecuta manualmente.
    # confirm = input("¿Estás seguro de que deseas eliminar los archivos y directorios obsoletos listados? (s/N): ")
    # if confirm.lower() == 's':
    #     clean_obsolete_files()
    # else:
    #     print("Limpieza cancelada por el usuario.")
    clean_obsolete_files()

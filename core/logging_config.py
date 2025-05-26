"""
Configuración de logging para NGX Agents.

Este módulo configura el sistema de logging para generar logs en formato JSON.
"""

import logging
import sys

# Importar JsonFormatter con fallback elegante
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    # Fallback para entornos donde python-json-logger no está disponible
    # Solo para desarrollo y pruebas, no para producción
    class _JsonFormatterFallback(logging.Formatter):
        """Formatter de respaldo que emula JsonFormatter."""

        def __init__(self, fmt=None, datefmt=None, **kwargs):
            super().__init__(fmt=fmt, datefmt=datefmt)

    class jsonlogger:
        JsonFormatter = _JsonFormatterFallback


from core.settings import settings


def setup_logging() -> None:
    """
    Configura el sistema de logging con formato JSON.

    Esta función debe llamarse al inicio de la aplicación para configurar
    el sistema de logging correctamente.
    """
    # Obtener el nivel de logging de la configuración
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Crear el formatter JSON
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configurar el handler para la salida estándar
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Eliminar handlers existentes
    for h in root_logger.handlers:
        root_logger.removeHandler(h)

    # Añadir el nuevo handler
    root_logger.addHandler(handler)

    # Configurar loggers específicos
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("fastapi").setLevel(log_level)

    # Mensaje de inicio
    logging.info(
        "Logging configurado",
        extra={"environment": settings.env, "log_level": settings.log_level},
    )


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado para el módulo especificado.

    Args:
        name: Nombre del módulo o componente

    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


# Alias para compatibilidad con código existente
def configure_logging(name: str = None) -> logging.Logger:
    """
    Alias de setup_logging para compatibilidad con código existente.

    Si se proporciona un nombre, configura el logging y devuelve un logger para ese módulo.
    Si no se proporciona nombre, solo configura el logging.

    Args:
        name: Nombre del módulo o componente (opcional)

    Returns:
        Logger configurado si se proporciona un nombre, None en caso contrario
    """
    setup_logging()
    if name:
        return get_logger(name)
    return None

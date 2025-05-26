"""
Módulo para cargar la telemetría según el entorno.

Este módulo proporciona una forma de cargar la telemetría adecuada según el entorno
(desarrollo, pruebas o producción) y las variables de configuración.
"""

import os
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Constantes para configuración
USE_MOCK = os.environ.get("USE_TELEMETRY_MOCK", "true").lower() == "true"
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")


def load_telemetry():
    """
    Carga el módulo de telemetría adecuado según el entorno.

    Returns:
        module: Módulo de telemetría cargado
    """
    if USE_MOCK or ENVIRONMENT == "dev":
        logger.info("Cargando telemetría mock para entorno de desarrollo")
        try:
            from core.telemetry_mock import telemetry

            return telemetry
        except ImportError as e:
            logger.error(f"Error al cargar telemetría mock: {e}")
            # Fallback a un objeto vacío
            return type(
                "EmptyTelemetry",
                (),
                {
                    "start_span": lambda *args, **kwargs: None,
                    "record_event": lambda *args, **kwargs: None,
                    "record_error": lambda *args, **kwargs: None,
                    "get_current_span": lambda: None,
                },
            )()
    else:
        logger.info(f"Cargando telemetría real para entorno {ENVIRONMENT}")
        try:
            from core.telemetry import telemetry

            return telemetry
        except ImportError as e:
            logger.error(f"Error al cargar telemetría real: {e}")
            # Intentar cargar telemetría mock como fallback
            try:
                from core.telemetry_mock import telemetry

                logger.warning("Usando telemetría mock como fallback")
                return telemetry
            except ImportError:
                # Fallback a un objeto vacío
                logger.error("No se pudo cargar ningún módulo de telemetría")
                return type(
                    "EmptyTelemetry",
                    (),
                    {
                        "start_span": lambda *args, **kwargs: None,
                        "record_event": lambda *args, **kwargs: None,
                        "record_error": lambda *args, **kwargs: None,
                        "get_current_span": lambda: None,
                    },
                )()


# Cargar telemetría al importar el módulo
telemetry = load_telemetry()

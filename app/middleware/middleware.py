"""
Middleware para la API de NGX Agents (DEPRECATED).

Este módulo ha sido reemplazado por middleware/auth.py.
Se mantiene por compatibilidad, pero no debe usarse en código nuevo.
"""

import logging

# Importar desde la ubicación correcta

logger = logging.getLogger(__name__)
logger.warning(
    "El módulo middleware.py está obsoleto y será eliminado en futuras versiones. "
    "Utilice middleware.auth en su lugar."
)

"""
Router para el sistema de modos degradados.

Este módulo importa y expone el router del sistema de modos degradados
definido en app/api/degraded_mode.py.
"""

from app.api.degraded_mode import router

# Exportar el router para que pueda ser importado desde app.routers.degraded_mode
__all__ = ["router"]

"""
Router para el sistema de simulaciones de caos.

Este módulo importa y expone el router del sistema de simulaciones de caos
definido en app/api/chaos_testing.py.
"""

from app.api.chaos_testing import router

# Exportar el router para que pueda ser importado desde app.routers.chaos_testing
__all__ = ["router"]

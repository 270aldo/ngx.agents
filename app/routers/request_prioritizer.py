"""
Router para el sistema de priorización de solicitudes.

Este módulo importa y expone el router del sistema de priorización de solicitudes
definido en app/api/request_prioritizer.py.
"""

from app.api.request_prioritizer import router

# Exportar el router para que pueda ser importado desde app.routers.request_prioritizer
__all__ = ["router"]

"""
Router para gestionar presupuestos de agentes.

Este módulo importa y expone el router de presupuestos definido en app/api/budget.py.
"""

from app.api.budget import router

# Exportar el router para que pueda ser importado desde app.routers.budget
__all__ = ["router"]

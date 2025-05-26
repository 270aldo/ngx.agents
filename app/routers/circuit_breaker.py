"""
Router para el sistema de circuit breaker.

Este módulo importa y expone el router del sistema de circuit breaker
definido en app/api/circuit_breaker.py.
"""

from app.api.circuit_breaker import router

# Exportar el router para que pueda ser importado desde app.routers.circuit_breaker
__all__ = ["router"]

"""
Router para el sistema de caché por dominio.

Este módulo importa y expone el router del sistema de caché por dominio definido en app/api/domain_cache.py.
"""

from app.api.domain_cache import router

# Exportar el router para que pueda ser importado desde app.routers.domain_cache
__all__ = ["router"]

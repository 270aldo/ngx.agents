"""
Router para el procesador asíncrono.

Este módulo importa y expone el router del procesador asíncrono definido en app/api/async_processor.py.
"""

from app.api.async_processor import router

# Exportar el router para que pueda ser importado desde app.routers.async_processor
__all__ = ["router"]

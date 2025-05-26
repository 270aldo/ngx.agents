"""
Router para el procesador por lotes.

Este módulo importa y expone el router del procesador por lotes definido en app/api/batch_processor.py.
"""

from app.api.batch_processor import router

# Exportar el router para que pueda ser importado desde app.routers.batch_processor
__all__ = ["router"]

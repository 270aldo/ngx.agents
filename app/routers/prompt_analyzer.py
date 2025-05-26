"""
Router para el analizador de prompts.

Este módulo importa y expone el router del analizador de prompts definido en app/api/prompt_analyzer.py.
"""

from app.api.prompt_analyzer import router

# Exportar el router para que pueda ser importado desde app.routers.prompt_analyzer
__all__ = ["router"]

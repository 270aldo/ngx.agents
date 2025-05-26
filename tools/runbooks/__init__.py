"""
Sistema de Runbooks Automatizados para NGX Agents.

Este módulo proporciona herramientas para la ejecución automatizada de
procedimientos operativos (runbooks) para responder a incidentes y
realizar tareas de mantenimiento.
"""

from tools.runbooks.runbook_executor import RunbookExecutor

__all__ = ["RunbookExecutor"]

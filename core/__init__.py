"""
Componentes centrales del sistema de agentes NGX.

Este paquete contiene las clases e interfaces base que definen
la arquitectura del sistema de agentes NGX, incluyendo la configuración,
gestión de estado, y utilidades comunes.
"""

from core.settings import settings
from core.logging_config import setup_logging, get_logger
from core.agent_card import AgentCard
from core.skill import Skill

__all__ = [
    "settings",
    "setup_logging",
    "get_logger",
    "AgentCard",
    "Skill",
]

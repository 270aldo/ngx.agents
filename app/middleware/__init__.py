"""
Módulo de middleware para la API de NGX Agents.

Este módulo contiene middleware para autenticación, logging,
y otras funcionalidades transversales de la API.
"""

from .auth import get_api_key, APIKeyMiddleware

__all__ = [
    "get_api_key",
    "APIKeyMiddleware",
]

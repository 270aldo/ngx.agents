"""
Paquete vertex_ai refactorizado para NGX Agents.

Este paquete proporciona una interfaz optimizada para interactuar con Vertex AI,
incluyendo funcionalidades para generación de texto, embeddings y procesamiento multimodal
con caché avanzado, pooling de conexiones y telemetría detallada.
"""

from .cache import CacheManager
from .connection import ConnectionPool, VERTEX_AI_AVAILABLE
from .decorators import with_retries, measure_execution_time
from .client import (
    VertexAIClient,
    vertex_ai_client,  # Instancia global pre-configurada
    check_vertex_ai_connection,
)

__all__ = [
    "CacheManager",
    "ConnectionPool",
    "VertexAIClient",
    "vertex_ai_client",
    "check_vertex_ai_connection",
    "with_retries",
    "measure_execution_time",
    "VERTEX_AI_AVAILABLE",
]

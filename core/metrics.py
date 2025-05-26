"""
Sistema de métricas para NGX Agents con Prometheus.

Este módulo proporciona métricas personalizadas y automáticas
para monitorear el rendimiento y comportamiento del sistema.
"""

from typing import Dict, Any, Optional, Callable
from functools import wraps
import time
import asyncio
from contextlib import contextmanager

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse

from core.logging_config import get_logger
from config.settings import settings

# Logger
logger = get_logger(__name__)

# Registry personalizado para evitar conflictos
METRICS_REGISTRY = CollectorRegistry()

# =============================================================================
# MÉTRICAS DE SISTEMA
# =============================================================================

# Información del sistema
system_info = Info(
    "ngx_agents_system", "Información del sistema NGX Agents", registry=METRICS_REGISTRY
)

# Contador de requests HTTP
http_requests_total = Counter(
    "ngx_agents_http_requests_total",
    "Total de requests HTTP",
    ["method", "endpoint", "status"],
    registry=METRICS_REGISTRY,
)

# Histograma de duración de requests
http_request_duration_seconds = Histogram(
    "ngx_agents_http_request_duration_seconds",
    "Duración de requests HTTP en segundos",
    ["method", "endpoint"],
    registry=METRICS_REGISTRY,
)

# Gauge de requests activos
http_requests_active = Gauge(
    "ngx_agents_http_requests_active",
    "Número de requests HTTP activos",
    registry=METRICS_REGISTRY,
)

# =============================================================================
# MÉTRICAS DE AGENTES
# =============================================================================

# Contador de invocaciones de agentes
agent_invocations_total = Counter(
    "ngx_agents_agent_invocations_total",
    "Total de invocaciones de agentes",
    ["agent_id", "status"],
    registry=METRICS_REGISTRY,
)

# Histograma de tiempo de respuesta de agentes
agent_response_time_seconds = Histogram(
    "ngx_agents_agent_response_time_seconds",
    "Tiempo de respuesta de agentes en segundos",
    ["agent_id"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=METRICS_REGISTRY,
)

# Gauge de agentes activos
agents_active = Gauge(
    "ngx_agents_agents_active",
    "Número de agentes activos",
    ["agent_id"],
    registry=METRICS_REGISTRY,
)

# =============================================================================
# MÉTRICAS DE CHAT Y STREAMING
# =============================================================================

# Contador de sesiones de chat
chat_sessions_total = Counter(
    "ngx_agents_chat_sessions_total",
    "Total de sesiones de chat",
    ["type", "status"],  # type: regular, streaming
    registry=METRICS_REGISTRY,
)

# Histograma de duración de sesiones
chat_session_duration_seconds = Histogram(
    "ngx_agents_chat_session_duration_seconds",
    "Duración de sesiones de chat en segundos",
    ["type"],
    registry=METRICS_REGISTRY,
)

# Contador de mensajes
chat_messages_total = Counter(
    "ngx_agents_chat_messages_total",
    "Total de mensajes de chat",
    ["direction"],  # direction: user, agent
    registry=METRICS_REGISTRY,
)

# Métricas específicas de streaming
stream_chunks_sent_total = Counter(
    "ngx_agents_stream_chunks_sent_total",
    "Total de chunks enviados en streaming",
    registry=METRICS_REGISTRY,
)

stream_ttfb_seconds = Histogram(
    "ngx_agents_stream_ttfb_seconds",
    "Time to First Byte en streaming",
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0),
    registry=METRICS_REGISTRY,
)

# =============================================================================
# MÉTRICAS DE CACHÉ
# =============================================================================

cache_operations_total = Counter(
    "ngx_agents_cache_operations_total",
    "Total de operaciones de caché",
    ["operation", "result"],  # operation: get, set, delete; result: hit, miss
    registry=METRICS_REGISTRY,
)

cache_size_bytes = Gauge(
    "ngx_agents_cache_size_bytes",
    "Tamaño del caché en bytes",
    ["cache_name"],
    registry=METRICS_REGISTRY,
)

# =============================================================================
# MÉTRICAS DE CIRCUIT BREAKER
# =============================================================================

circuit_breaker_state_changes = Counter(
    "ngx_agents_circuit_breaker_state_changes_total",
    "Total de cambios de estado del circuit breaker",
    ["service", "from_state", "to_state"],
    registry=METRICS_REGISTRY,
)

circuit_breaker_failures = Counter(
    "ngx_agents_circuit_breaker_failures_total",
    "Total de fallos registrados por circuit breaker",
    ["service"],
    registry=METRICS_REGISTRY,
)

# =============================================================================
# MÉTRICAS DE BASE DE DATOS
# =============================================================================

db_operations_total = Counter(
    "ngx_agents_db_operations_total",
    "Total de operaciones de base de datos",
    ["operation", "table", "status"],
    registry=METRICS_REGISTRY,
)

db_operation_duration_seconds = Histogram(
    "ngx_agents_db_operation_duration_seconds",
    "Duración de operaciones de base de datos",
    ["operation", "table"],
    registry=METRICS_REGISTRY,
)

# =============================================================================
# MÉTRICAS DE REDIS
# =============================================================================

redis_operations_total = Counter(
    "ngx_agents_redis_operations_total",
    "Total de operaciones de Redis",
    ["operation", "status"],
    registry=METRICS_REGISTRY,
)

redis_pool_connections = Gauge(
    "ngx_agents_redis_pool_connections",
    "Conexiones en el pool de Redis",
    ["state"],  # state: active, idle
    registry=METRICS_REGISTRY,
)

# =============================================================================
# FUNCIONES HELPER
# =============================================================================


def track_time(metric: Histogram, labels: Dict[str, str] = None):
    """
    Decorator para medir el tiempo de ejecución de una función.

    Args:
        metric: Histograma de Prometheus para registrar el tiempo
        labels: Etiquetas adicionales para la métrica
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


@contextmanager
def track_operation_time(metric: Histogram, **labels):
    """
    Context manager para medir el tiempo de una operación.

    Usage:
        with track_operation_time(db_operation_duration_seconds, operation="select", table="users"):
            # realizar operación
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        metric.labels(**labels).observe(duration)


class MetricsMiddleware:
    """Middleware personalizado para métricas más detalladas."""

    async def __call__(self, request: Request, call_next):
        # Incrementar requests activos
        http_requests_active.inc()

        # Medir tiempo de request
        start_time = time.time()

        try:
            # Procesar request
            response = await call_next(request)

            # Registrar métricas
            duration = time.time() - start_time

            # Obtener información del endpoint
            endpoint = request.url.path
            method = request.method
            status = response.status_code

            # Actualizar métricas
            http_requests_total.labels(
                method=method, endpoint=endpoint, status=status
            ).inc()

            http_request_duration_seconds.labels(
                method=method, endpoint=endpoint
            ).observe(duration)

            return response

        finally:
            # Decrementar requests activos
            http_requests_active.dec()


# =============================================================================
# INICIALIZACIÓN
# =============================================================================


def initialize_metrics(app: FastAPI) -> None:
    """
    Inicializa el sistema de métricas para la aplicación.

    Args:
        app: Instancia de FastAPI
    """
    logger.info("Inicializando sistema de métricas con Prometheus")

    # Establecer información del sistema
    system_info.info(
        {
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "service": "ngx-agents",
        }
    )

    # Instrumentador automático de FastAPI
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health", "/docs", "/redoc"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="ngx_agents_http_requests_inprogress",
        inprogress_labels=True,
    )

    # Personalizar métricas del instrumentador
    @instrumentator.add
    async def add_custom_metrics(info):
        """Agregar métricas personalizadas por request."""
        # Aquí se pueden agregar métricas adicionales basadas en el request/response
        pass

    # Instrumentar la aplicación
    instrumentator.instrument(app)

    # Agregar middleware personalizado
    app.middleware("http")(MetricsMiddleware())

    # Agregar endpoint de métricas
    @app.get("/metrics", include_in_schema=False)
    async def get_metrics():
        """Endpoint para que Prometheus scrape las métricas."""
        return PlainTextResponse(
            generate_latest(METRICS_REGISTRY), media_type=CONTENT_TYPE_LATEST
        )

    logger.info("Sistema de métricas inicializado correctamente")


# =============================================================================
# UTILIDADES DE MÉTRICAS
# =============================================================================


class MetricsCollector:
    """Clase helper para recolectar métricas de manera consistente."""

    @staticmethod
    def record_agent_invocation(agent_id: str, status: str, duration: float):
        """Registra una invocación de agente."""
        agent_invocations_total.labels(agent_id=agent_id, status=status).inc()
        agent_response_time_seconds.labels(agent_id=agent_id).observe(duration)

    @staticmethod
    def record_chat_session(session_type: str, status: str, duration: float):
        """Registra una sesión de chat."""
        chat_sessions_total.labels(type=session_type, status=status).inc()
        chat_session_duration_seconds.labels(type=session_type).observe(duration)

    @staticmethod
    def record_cache_operation(operation: str, hit: bool):
        """Registra una operación de caché."""
        result = "hit" if hit else "miss"
        cache_operations_total.labels(operation=operation, result=result).inc()

    @staticmethod
    def record_circuit_breaker_change(service: str, from_state: str, to_state: str):
        """Registra un cambio de estado del circuit breaker."""
        circuit_breaker_state_changes.labels(
            service=service, from_state=from_state, to_state=to_state
        ).inc()

    @staticmethod
    def record_db_operation(operation: str, table: str, status: str, duration: float):
        """Registra una operación de base de datos."""
        db_operations_total.labels(
            operation=operation, table=table, status=status
        ).inc()
        db_operation_duration_seconds.labels(operation=operation, table=table).observe(
            duration
        )


# Instancia global del collector
metrics_collector = MetricsCollector()

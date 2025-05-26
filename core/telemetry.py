"""
Módulo de telemetría para NGX Agents.

Este módulo proporciona funcionalidades para instrumentar la aplicación con
OpenTelemetry, incluyendo tracing, métricas y logging.
"""

import socket
from typing import Dict, Optional, Union

# OpenTelemetry
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor

# Exportadores para Google Cloud
try:
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
except ImportError:
    CloudTraceSpanExporter = None

try:
    from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricExporter
except ImportError:
    CloudMonitoringMetricExporter = None

# Local imports
from core.settings import settings
from core.logging_config import configure_logging

# Configurar logger
logger = configure_logging(__name__)

# Variables globales para telemetría
_tracer_provider = None
_meter_provider = None
_propagator = TraceContextTextMapPropagator()


def initialize_telemetry() -> None:
    """
    Inicializa la telemetría con OpenTelemetry.

    Esta función configura los proveedores de tracing y métricas,
    y registra los instrumentadores para las bibliotecas comunes.
    """
    global _tracer_provider, _meter_provider

    # Crear recurso con información del servicio
    resource = Resource.create(
        {
            "service.name": "ngx-agents",
            "service.version": settings.APP_VERSION,
            "service.instance.id": socket.gethostname(),
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    # Configurar tracing
    _tracer_provider = TracerProvider(resource=resource)

    # Configurar exportador de traces según el entorno
    if settings.ENVIRONMENT in ["production", "staging"] and CloudTraceSpanExporter:
        # Exportador para Google Cloud Trace
        cloud_trace_exporter = CloudTraceSpanExporter(
            project_id=settings.GCP_PROJECT_ID
        )
        _tracer_provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))
        logger.info("Configurado exportador de traces para Google Cloud Trace")
    else:
        # Exportador para consola en desarrollo
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        _tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("Configurado exportador de traces para consola (desarrollo)")

    # Registrar proveedor de tracing
    trace.set_tracer_provider(_tracer_provider)

    # Configurar métricas
    metric_readers = []

    # Configurar exportador de métricas según el entorno
    if (
        settings.ENVIRONMENT in ["production", "staging"]
        and CloudMonitoringMetricExporter
    ):
        # Exportador para Google Cloud Monitoring
        cloud_monitoring_reader = PeriodicExportingMetricReader(
            CloudMonitoringMetricExporter(
                project_id=settings.GCP_PROJECT_ID, prefix="ngx_agents"
            )
        )
        metric_readers.append(cloud_monitoring_reader)
        logger.info("Configurado exportador de métricas para Google Cloud Monitoring")
    else:
        # Exportador para consola en desarrollo
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

        console_reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(), export_interval_millis=30000  # 30 segundos
        )
        metric_readers.append(console_reader)
        logger.info("Configurado exportador de métricas para consola (desarrollo)")

    # Registrar proveedor de métricas
    _meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(_meter_provider)

    # Instrumentar bibliotecas comunes
    HTTPXClientInstrumentor().instrument()
    LoggingInstrumentor().instrument()
    AioHttpClientInstrumentor().instrument()

    logger.info("Telemetría inicializada correctamente")


def shutdown_telemetry() -> None:
    """
    Cierra la telemetría y exporta los datos pendientes.

    Esta función debe llamarse al apagar la aplicación para
    asegurar que todos los datos de telemetría se exporten.
    """
    global _tracer_provider, _meter_provider

    if _tracer_provider:
        _tracer_provider.shutdown()
        logger.info("Proveedor de tracing cerrado correctamente")

    if _meter_provider:
        _meter_provider.shutdown()
        logger.info("Proveedor de métricas cerrado correctamente")


def get_tracer(name: str) -> trace.Tracer:
    """
    Obtiene un tracer para un componente específico.

    Args:
        name: Nombre del componente

    Returns:
        trace.Tracer: Tracer para el componente
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """
    Obtiene un meter para un componente específico.

    Args:
        name: Nombre del componente

    Returns:
        metrics.Meter: Meter para el componente
    """
    return metrics.get_meter(name)


def extract_trace_context(carrier: Dict[str, str]) -> Optional[trace.SpanContext]:
    """
    Extrae el contexto de trace de los headers HTTP.

    Args:
        carrier: Headers HTTP

    Returns:
        Optional[trace.SpanContext]: Contexto de trace
    """
    return _propagator.extract(carrier=carrier)


def inject_trace_context(carrier: Dict[str, str]) -> None:
    """
    Inyecta el contexto de trace en los headers HTTP.

    Args:
        carrier: Headers HTTP
    """
    _propagator.inject(carrier=carrier)


def record_exception(
    exception: Exception, attributes: Optional[Dict[str, str]] = None
) -> None:
    """
    Registra una excepción en el span actual.

    Args:
        exception: Excepción a registrar
        attributes: Atributos adicionales
    """
    current_span = trace.get_current_span()
    if current_span:
        current_span.record_exception(exception, attributes=attributes)
        current_span.set_status(trace.Status(trace.StatusCode.ERROR))


def instrument_fastapi(app) -> None:
    """
    Instrumenta una aplicación FastAPI con OpenTelemetry.

    Args:
        app: Aplicación FastAPI
    """
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=_tracer_provider,
        excluded_urls="/health,/metrics",
        meter_provider=_meter_provider,
    )
    logger.info("Aplicación FastAPI instrumentada con OpenTelemetry")


def create_span(
    name: str,
    attributes: Optional[Dict[str, str]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
) -> trace.Span:
    """
    Crea un nuevo span.

    Args:
        name: Nombre del span
        attributes: Atributos del span
        kind: Tipo de span

    Returns:
        trace.Span: Span creado
    """
    tracer = get_tracer("ngx_agents.manual")
    return tracer.start_span(name=name, attributes=attributes, kind=kind)


def add_span_event(name: str, attributes: Optional[Dict[str, str]] = None) -> None:
    """
    Añade un evento al span actual.

    Args:
        name: Nombre del evento
        attributes: Atributos del evento
    """
    current_span = trace.get_current_span()
    if current_span:
        current_span.add_event(name=name, attributes=attributes)


def set_span_attribute(key: str, value: Union[str, int, float, bool]) -> None:
    """
    Establece un atributo en el span actual.

    Args:
        key: Clave del atributo
        value: Valor del atributo
    """
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute(key, value)


def get_current_trace_id() -> Optional[str]:
    """
    Obtiene el ID de trace actual.

    Returns:
        Optional[str]: ID de trace actual
    """
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().trace_id:
        return format(current_span.get_span_context().trace_id, "032x")
    return None


def get_current_span_id() -> Optional[str]:
    """
    Obtiene el ID de span actual.

    Returns:
        Optional[str]: ID de span actual
    """
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().span_id:
        return format(current_span.get_span_context().span_id, "016x")
    return None

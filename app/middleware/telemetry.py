"""
Middleware de telemetría para FastAPI.

Este módulo proporciona middleware para instrumentar aplicaciones FastAPI
con telemetría, incluyendo métricas, tracing y logging.
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Local imports
from core.telemetry import (
    get_meter,
    get_tracer,
    record_exception,
    extract_trace_context,
)
from core.logging_config import configure_logging

# Configurar logger
logger = configure_logging(__name__)

# Importar configuración
from core.settings import settings

# Variables globales para telemetría
tracer = None
meter = None
http_requests_counter = None
http_request_duration = None
http_request_size = None
http_response_size = None

# Inicializar métricas solo si la telemetría está habilitada
if settings.telemetry_enabled:
    # Obtener tracer y meter
    tracer = get_tracer("ngx_agents.api")
    meter = get_meter("ngx_agents.api")

    # Crear métricas
    http_requests_counter = meter.create_counter(
        name="http.requests",
        description="Número de solicitudes HTTP recibidas",
        unit="1",
    )

    http_request_duration = meter.create_histogram(
        name="http.request.duration",
        description="Duración de las solicitudes HTTP",
        unit="ms",
    )

    http_request_size = meter.create_histogram(
        name="http.request.size",
        description="Tamaño de las solicitudes HTTP",
        unit="bytes",
    )

    http_response_size = meter.create_histogram(
        name="http.response.size",
        description="Tamaño de las respuestas HTTP",
        unit="bytes",
    )


class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    Middleware para añadir telemetría a las solicitudes HTTP.

    Este middleware captura métricas de solicitudes HTTP, añade información
    de contexto a los spans, registra errores y excepciones, y proporciona
    correlación entre logs y traces.
    """

    def __init__(self, app: ASGIApp):
        """
        Inicializa el middleware de telemetría.

        Args:
            app: La aplicación ASGI a instrumentar.
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Procesa una solicitud HTTP y añade telemetría.

        Args:
            request: La solicitud HTTP.
            call_next: La función para procesar la solicitud.

        Returns:
            Response: La respuesta HTTP.
        """
        # Generar ID de solicitud si no existe
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
            # Añadir el ID de solicitud a los headers
            request.headers.__dict__["_list"].append(
                (b"x-request-id", request_id.encode())
            )

        # Extraer contexto de trace de los headers
        trace_context = extract_trace_context(dict(request.headers))

        # Iniciar span para la solicitud
        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}",
            context=trace_context,
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.scheme": request.url.scheme,
                "http.host": request.url.hostname,
                "http.target": request.url.path,
                "http.request_id": request_id,
                "http.user_agent": request.headers.get("user-agent", ""),
                "http.client_ip": request.client.host if request.client else "",
            },
        ) as span:
            start_time = time.time()

            # Registrar información de la solicitud
            content_length = request.headers.get("content-length")
            if content_length:
                span.set_attribute("http.request_content_length", int(content_length))
                http_request_size.record(int(content_length))

            try:
                # Procesar la solicitud
                response = await call_next(request)

                # Registrar información de la respuesta
                span.set_attribute("http.status_code", response.status_code)

                # Añadir el ID de solicitud a la respuesta
                response.headers["X-Request-ID"] = request_id

                # Registrar métricas
                duration_ms = (time.time() - start_time) * 1000
                http_request_duration.record(
                    duration_ms,
                    {
                        "http.method": request.method,
                        "http.route": request.url.path,
                        "http.status_code": str(response.status_code),
                    },
                )

                http_requests_counter.add(
                    1,
                    {
                        "http.method": request.method,
                        "http.route": request.url.path,
                        "http.status_code": str(response.status_code),
                    },
                )

                # Registrar tamaño de la respuesta
                resp_content_length = response.headers.get("content-length")
                if resp_content_length:
                    span.set_attribute(
                        "http.response_content_length", int(resp_content_length)
                    )
                    http_response_size.record(int(resp_content_length))

                return response

            except Exception as e:
                # Registrar la excepción en el span
                record_exception(e, {"error.type": type(e).__name__})
                span.set_attribute("http.status_code", 500)

                # Registrar métricas de error
                duration_ms = (time.time() - start_time) * 1000
                http_request_duration.record(
                    duration_ms,
                    {
                        "http.method": request.method,
                        "http.route": request.url.path,
                        "http.status_code": "500",
                        "error": True,
                    },
                )

                http_requests_counter.add(
                    1,
                    {
                        "http.method": request.method,
                        "http.route": request.url.path,
                        "http.status_code": "500",
                        "error": True,
                    },
                )

                # Registrar el error
                logger.exception(
                    f"Error procesando solicitud: {request.method} {request.url.path}",
                    extra={
                        "request_id": request_id,
                        "http.method": request.method,
                        "http.url": str(request.url),
                    },
                )

                # Re-lanzar la excepción para que FastAPI la maneje
                raise


class TelemetryRoute(APIRoute):
    """
    Ruta de API con telemetría integrada.

    Esta clase extiende APIRoute para añadir telemetría a nivel de endpoint.
    """

    def get_route_handler(self) -> Callable:
        """
        Obtiene el manejador de ruta con telemetría añadida.

        Returns:
            Callable: El manejador de ruta con telemetría.
        """
        original_route_handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            # Obtener el nombre de la operación
            operation_name = (
                f"{self.name}" if self.name else f"{request.method} {request.url.path}"
            )

            # Iniciar span para la operación
            with tracer.start_as_current_span(
                operation_name,
                attributes={
                    "endpoint.name": self.name or "",
                    "endpoint.path": self.path,
                    "endpoint.methods": ",".join(self.methods),
                },
            ):
                return await original_route_handler(request)

        return route_handler


def setup_telemetry_middleware(app: FastAPI) -> None:
    """
    Configura el middleware de telemetría para una aplicación FastAPI.
    Solo configura el middleware si la telemetría está habilitada.

    Args:
        app: La aplicación FastAPI a instrumentar.
    """
    if not settings.telemetry_enabled:
        logger.info("Telemetría deshabilitada. No se configurará el middleware.")
        return

    # Añadir middleware de telemetría
    app.add_middleware(TelemetryMiddleware)

    # Configurar rutas con telemetría
    app.router.route_class = TelemetryRoute

    logger.info("Middleware de telemetría configurado")

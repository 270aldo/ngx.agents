import asyncio
import functools
from core.logging_config import get_logger
import time

# Intentar importar telemetry_adapter, con fallback a un mock
try:
    from core.telemetry_adapter import telemetry_adapter
except ImportError:
    logger = get_logger(__name__)
    logger.warning("telemetry_adapter no encontrado. Usando mock.")

    class MockTelemetryAdapter:
        def start_span(self, name, attributes=None):
            logger.debug(f"Mock span started: {name}")
            return name  # Devuelve algo simple para 'span'

        def end_span(self, span):
            logger.debug(f"Mock span ended: {span}")

        def record_exception(self, span, exception):
            logger.debug(f"Mock exception recorded for span {span}: {exception}")

        def set_span_attribute(self, span, key, value):
            logger.debug(f"Mock span attribute set for {span}: {key}={value}")

        def add_span_event(self, span, event_name, attributes=None):
            logger.debug(f"Mock span event added for {span}: {event_name}")

        def record_metric(self, name, value, attributes=None):
            logger.debug(f"Mock metric recorded: {name}={value}")

    telemetry_adapter = MockTelemetryAdapter()

logger = get_logger(__name__)


def with_retries(max_retries=3, base_delay=0.5, backoff_factor=2):
    """
    Decorador para implementar reintentos automáticos con backoff exponencial.

    Args:
        max_retries: Número máximo de reintentos
        base_delay: Retraso inicial entre reintentos (segundos)
        backoff_factor: Factor de incremento para el retraso
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor**attempt)
                        logger.warning(
                            f"Reintento {attempt+1}/{max_retries} para {func.__name__} después de {delay:.2f}s. Error: {str(e)}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Máximo de reintentos alcanzado para {func.__name__}. Error: {str(e)}"
                        )
                        raise
            if last_exception is not None:
                raise last_exception

        return wrapper

    return decorator


def measure_execution_time(metric_base_name: str):
    """
    Decorador para medir el tiempo de ejecución de una función asíncrona y
    registrar métricas y trazas usando telemetry_adapter.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            span_name = f"{metric_base_name}.{func.__name__}"
            span = telemetry_adapter.start_span(span_name)
            start_time = time.time()
            try:
                telemetry_adapter.add_span_event(span, f"{func.__name__}.start")
                result = await func(*args, **kwargs)
                telemetry_adapter.add_span_event(span, f"{func.__name__}.success")
                return result
            except Exception as e:
                telemetry_adapter.record_exception(span, e)
                telemetry_adapter.set_span_attribute(span, "error", True)
                telemetry_adapter.add_span_event(span, f"{func.__name__}.error")
                raise
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                telemetry_adapter.set_span_attribute(span, "duration_ms", duration_ms)
                telemetry_adapter.record_metric(
                    f"{metric_base_name}.duration_ms",
                    duration_ms,
                    {"function": func.__name__},
                )
                telemetry_adapter.end_span(span)

        return wrapper

    return decorator

"""
Manejador de alertas para NGX Agents.

Este módulo proporciona funcionalidades para manejar alertas
y ejecutar runbooks automatizados en respuesta a incidentes.
"""

import logging
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks

from tools.runbooks import RunbookExecutor
from infrastructure.adapters import get_telemetry_adapter

# Configurar logger
logger = logging.getLogger(__name__)

# Obtener adaptador de telemetría
telemetry = get_telemetry_adapter()

# Crear router
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

# Mapeo de tipos de alerta a runbooks
ALERT_RUNBOOK_MAPPING = {
    "high_latency": "incident_response",
    "high_error_rate": "error_rate_response",
    "high_cpu_usage": "resource_optimization",
    "high_memory_usage": "resource_optimization",
    "low_cache_hit_rate": "cache_optimization",
    "api_availability": "availability_response",
}

# Ejecutor de runbooks
runbook_executor = RunbookExecutor()

# Cola de alertas para procesamiento asíncrono
alert_queue = asyncio.Queue()

# Flag para indicar si el worker está ejecutándose
worker_running = False


@router.post("/webhook")
async def receive_alert_webhook(
    request: Request, background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Recibe alertas de sistemas de monitoreo (Prometheus, Cloud Monitoring, etc.)
    y ejecuta runbooks automatizados en respuesta.

    Args:
        request: Solicitud HTTP con la alerta.
        background_tasks: Tareas en segundo plano.

    Returns:
        Dict[str, Any]: Resultado del procesamiento de la alerta.
    """
    span = telemetry.start_span("alert_handler.receive_alert_webhook")

    try:
        # Obtener datos de la alerta
        alert_data = await request.json()

        # Registrar evento de telemetría
        telemetry.add_span_event(
            span,
            "alert_received",
            {
                "alert_source": request.headers.get("X-Alert-Source", "unknown"),
                "alert_type": alert_data.get("type", "unknown"),
            },
        )

        # Procesar la alerta en segundo plano
        background_tasks.add_task(process_alert, alert_data)

        # Asegurar que el worker está ejecutándose
        ensure_alert_worker()

        return {
            "status": "accepted",
            "message": "Alerta recibida y encolada para procesamiento",
        }
    except Exception as e:
        telemetry.record_exception(span, e)
        logger.error(f"Error al procesar alerta: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


@router.get("/status")
async def get_alert_status() -> Dict[str, Any]:
    """
    Obtiene el estado del sistema de alertas.

    Returns:
        Dict[str, Any]: Estado del sistema de alertas.
    """
    return {
        "queue_size": alert_queue.qsize(),
        "worker_running": worker_running,
        "runbook_mappings": ALERT_RUNBOOK_MAPPING,
    }


@router.get("/history")
async def get_alert_history() -> Dict[str, Any]:
    """
    Obtiene el historial de alertas procesadas.

    Returns:
        Dict[str, Any]: Historial de alertas.
    """
    # Implementación pendiente - se podría almacenar en base de datos
    return {"alerts": []}


@router.post("/test")
async def test_alert_handler(
    alert_type: str, background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Envía una alerta de prueba para verificar el funcionamiento del sistema.

    Args:
        alert_type: Tipo de alerta a probar.
        background_tasks: Tareas en segundo plano.

    Returns:
        Dict[str, Any]: Resultado de la prueba.
    """
    span = telemetry.start_span(
        "alert_handler.test_alert_handler", {"alert_type": alert_type}
    )

    try:
        # Crear alerta de prueba
        test_alert = {
            "type": alert_type,
            "severity": "warning",
            "summary": f"Alerta de prueba: {alert_type}",
            "description": f"Esta es una alerta de prueba para verificar el funcionamiento del sistema de alertas.",
            "test": True,
            "timestamp": "2025-05-13T17:30:00Z",
        }

        # Procesar la alerta en segundo plano
        background_tasks.add_task(process_alert, test_alert)

        # Asegurar que el worker está ejecutándose
        ensure_alert_worker()

        return {
            "status": "accepted",
            "message": f"Alerta de prueba '{alert_type}' encolada para procesamiento",
        }
    except Exception as e:
        telemetry.record_exception(span, e)
        logger.error(f"Error al procesar alerta de prueba: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        telemetry.end_span(span)


async def process_alert(alert_data: Dict[str, Any]) -> None:
    """
    Procesa una alerta y la encola para su procesamiento asíncrono.

    Args:
        alert_data: Datos de la alerta.
    """
    span = telemetry.start_span(
        "alert_handler.process_alert", {"alert_type": alert_data.get("type", "unknown")}
    )

    try:
        # Enriquecer alerta con información adicional
        enriched_alert = await enrich_alert(alert_data)

        # Encolar para procesamiento asíncrono
        await alert_queue.put(enriched_alert)

        # Registrar evento de telemetría
        telemetry.add_span_event(
            span,
            "alert_enqueued",
            {
                "alert_type": enriched_alert.get("type", "unknown"),
                "queue_size": alert_queue.qsize(),
            },
        )

        logger.info(
            f"Alerta encolada para procesamiento: {enriched_alert.get('type', 'unknown')}"
        )
    except Exception as e:
        telemetry.record_exception(span, e)
        logger.error(f"Error al procesar alerta: {str(e)}")
    finally:
        telemetry.end_span(span)


async def enrich_alert(alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriquece una alerta con información adicional.

    Args:
        alert_data: Datos de la alerta.

    Returns:
        Dict[str, Any]: Alerta enriquecida.
    """
    # Clonar alerta para no modificar la original
    enriched = alert_data.copy()

    # Añadir timestamp si no existe
    if "timestamp" not in enriched:
        from datetime import datetime

        enriched["timestamp"] = datetime.utcnow().isoformat() + "Z"

    # Determinar runbook a ejecutar
    alert_type = enriched.get("type", "unknown")
    enriched["runbook_id"] = ALERT_RUNBOOK_MAPPING.get(alert_type)

    # Añadir información de contexto
    # Aquí se podría añadir información adicional como métricas relacionadas,
    # estado del sistema, etc.

    return enriched


def ensure_alert_worker() -> None:
    """
    Asegura que el worker de procesamiento de alertas está ejecutándose.
    """
    global worker_running

    if not worker_running:
        # Iniciar worker en una tarea de fondo
        asyncio.create_task(alert_worker())


async def alert_worker() -> None:
    """
    Worker para procesar alertas de forma asíncrona.
    """
    global worker_running

    # Marcar como ejecutándose
    worker_running = True

    try:
        logger.info("Iniciando worker de procesamiento de alertas")

        while True:
            try:
                # Obtener alerta de la cola
                alert = await alert_queue.get()

                # Procesar alerta
                await handle_alert(alert)

                # Marcar como completada
                alert_queue.task_done()
            except asyncio.CancelledError:
                # El worker fue cancelado
                break
            except Exception as e:
                logger.error(f"Error en worker de alertas: {str(e)}")
                # Continuar con la siguiente alerta
    finally:
        # Marcar como no ejecutándose
        worker_running = False
        logger.info("Worker de procesamiento de alertas detenido")


async def handle_alert(alert: Dict[str, Any]) -> None:
    """
    Maneja una alerta ejecutando el runbook correspondiente.

    Args:
        alert: Datos de la alerta.
    """
    span = telemetry.start_span(
        "alert_handler.handle_alert", {"alert_type": alert.get("type", "unknown")}
    )

    try:
        # Obtener ID del runbook a ejecutar
        runbook_id = alert.get("runbook_id")

        if not runbook_id:
            logger.warning(
                f"No se encontró runbook para la alerta: {alert.get('type', 'unknown')}"
            )
            return

        # Registrar evento de telemetría
        telemetry.add_span_event(
            span,
            "executing_runbook",
            {"runbook_id": runbook_id, "alert_type": alert.get("type", "unknown")},
        )

        logger.info(
            f"Ejecutando runbook {runbook_id} para alerta {alert.get('type', 'unknown')}"
        )

        # Ejecutar runbook
        result = await runbook_executor.execute_runbook(runbook_id, {"alert": alert})

        # Registrar resultado
        telemetry.add_span_event(
            span,
            "runbook_executed",
            {
                "runbook_id": runbook_id,
                "execution_id": result.get("execution_id", ""),
                "status": result.get("status", ""),
            },
        )

        logger.info(
            f"Runbook {runbook_id} ejecutado con resultado: {result.get('status', '')}"
        )
    except Exception as e:
        telemetry.record_exception(span, e)
        logger.error(f"Error al manejar alerta: {str(e)}")
    finally:
        telemetry.end_span(span)


# Función para integrar el router en la aplicación principal
def setup_alert_handler(app):
    """
    Configura el manejador de alertas en la aplicación principal.

    Args:
        app: Aplicación FastAPI.
    """
    app.include_router(router)
    logger.info("Manejador de alertas configurado")

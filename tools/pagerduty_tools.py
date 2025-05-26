"""
Herramientas para interactuar con PagerDuty.

Este módulo proporciona funciones para enviar alertas y eventos a PagerDuty,
permitiendo la integración con el sistema de monitoreo y alertas.
"""

import os
import uuid
import httpx
from typing import Dict, Any, Optional, List

# Local imports
from core.logging_config import configure_logging

# Configurar logger
logger = configure_logging(__name__)

# Constantes
PAGERDUTY_API_URL = "https://api.pagerduty.com"
PAGERDUTY_EVENTS_API_URL = "https://events.pagerduty.com/v2/enqueue"
PAGERDUTY_API_KEY = os.environ.get("PAGERDUTY_API_KEY", "")
PAGERDUTY_SERVICE_ID = os.environ.get("PAGERDUTY_SERVICE_ID", "")
PAGERDUTY_INTEGRATION_KEY = os.environ.get("PAGERDUTY_INTEGRATION_KEY", "")
PAGERDUTY_FROM_EMAIL = os.environ.get("PAGERDUTY_FROM_EMAIL", "ngx-agents@example.com")

# Verificar si PagerDuty está configurado
PAGERDUTY_ENABLED = all(
    [PAGERDUTY_API_KEY, PAGERDUTY_SERVICE_ID, PAGERDUTY_INTEGRATION_KEY]
)


async def send_alert(
    summary: str,
    severity: str = "warning",
    source: str = "ngx-agents",
    component: str = "api",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Envía una alerta a PagerDuty.

    Args:
        summary: Resumen de la alerta
        severity: Severidad de la alerta (critical, error, warning, info)
        source: Fuente de la alerta
        component: Componente que generó la alerta
        details: Detalles adicionales de la alerta

    Returns:
        Dict[str, Any]: Respuesta de PagerDuty
    """
    if not PAGERDUTY_ENABLED:
        logger.warning("PagerDuty no está configurado. No se enviará la alerta.")
        return {"status": "skipped", "message": "PagerDuty no está configurado"}

    # Normalizar severidad
    severity = severity.lower()
    if severity not in ["critical", "error", "warning", "info"]:
        severity = "warning"

    # Crear payload para el evento
    payload = {
        "routing_key": PAGERDUTY_INTEGRATION_KEY,
        "event_action": "trigger",
        "dedup_key": str(uuid.uuid4()),
        "payload": {
            "summary": summary,
            "severity": severity,
            "source": source,
            "component": component,
            "custom_details": details or {},
        },
    }

    try:
        # Enviar evento a PagerDuty
        async with httpx.AsyncClient() as client:
            response = await client.post(
                PAGERDUTY_EVENTS_API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )

            response_data = response.json()

            if response.status_code == 202:
                logger.info(
                    f"Alerta enviada a PagerDuty: {summary}",
                    extra={
                        "pagerduty_status": "success",
                        "pagerduty_event_id": response_data.get("dedup_key"),
                        "severity": severity,
                    },
                )
                return {
                    "status": "success",
                    "message": "Alerta enviada correctamente",
                    "event_id": response_data.get("dedup_key"),
                }
            else:
                logger.error(
                    f"Error al enviar alerta a PagerDuty: {response.text}",
                    extra={
                        "pagerduty_status": "error",
                        "status_code": response.status_code,
                        "response": response.text,
                    },
                )
                return {
                    "status": "error",
                    "message": f"Error al enviar alerta: {response.text}",
                    "status_code": response.status_code,
                }

    except Exception as e:
        logger.exception(
            f"Excepción al enviar alerta a PagerDuty: {e}",
            extra={"pagerduty_status": "exception", "error_type": type(e).__name__},
        )
        return {
            "status": "error",
            "message": f"Excepción al enviar alerta: {str(e)}",
            "error_type": type(e).__name__,
        }


async def resolve_alert(dedup_key: str) -> Dict[str, Any]:
    """
    Resuelve una alerta en PagerDuty.

    Args:
        dedup_key: Clave de deduplicación de la alerta

    Returns:
        Dict[str, Any]: Respuesta de PagerDuty
    """
    if not PAGERDUTY_ENABLED:
        logger.warning("PagerDuty no está configurado. No se resolverá la alerta.")
        return {"status": "skipped", "message": "PagerDuty no está configurado"}

    # Crear payload para el evento
    payload = {
        "routing_key": PAGERDUTY_INTEGRATION_KEY,
        "event_action": "resolve",
        "dedup_key": dedup_key,
    }

    try:
        # Enviar evento a PagerDuty
        async with httpx.AsyncClient() as client:
            response = await client.post(
                PAGERDUTY_EVENTS_API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )

            if response.status_code == 202:
                logger.info(
                    f"Alerta resuelta en PagerDuty: {dedup_key}",
                    extra={
                        "pagerduty_status": "resolved",
                        "pagerduty_event_id": dedup_key,
                    },
                )
                return {"status": "success", "message": "Alerta resuelta correctamente"}
            else:
                logger.error(
                    f"Error al resolver alerta en PagerDuty: {response.text}",
                    extra={
                        "pagerduty_status": "error",
                        "status_code": response.status_code,
                        "response": response.text,
                    },
                )
                return {
                    "status": "error",
                    "message": f"Error al resolver alerta: {response.text}",
                    "status_code": response.status_code,
                }

    except Exception as e:
        logger.exception(
            f"Excepción al resolver alerta en PagerDuty: {e}",
            extra={"pagerduty_status": "exception", "error_type": type(e).__name__},
        )
        return {
            "status": "error",
            "message": f"Excepción al resolver alerta: {str(e)}",
            "error_type": type(e).__name__,
        }


async def get_incidents(
    statuses: Optional[List[str]] = None,
    service_ids: Optional[List[str]] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    """
    Obtiene incidentes de PagerDuty.

    Args:
        statuses: Lista de estados de incidentes (triggered, acknowledged, resolved)
        service_ids: Lista de IDs de servicios
        since: Fecha de inicio (ISO 8601)
        until: Fecha de fin (ISO 8601)
        limit: Límite de incidentes a obtener

    Returns:
        Dict[str, Any]: Respuesta de PagerDuty
    """
    if not PAGERDUTY_ENABLED:
        logger.warning("PagerDuty no está configurado. No se obtendrán incidentes.")
        return {"status": "skipped", "message": "PagerDuty no está configurado"}

    # Parámetros de la consulta
    params = {"limit": limit}

    if statuses:
        params["statuses[]"] = statuses

    if service_ids:
        params["service_ids[]"] = service_ids
    else:
        params["service_ids[]"] = [PAGERDUTY_SERVICE_ID]

    if since:
        params["since"] = since

    if until:
        params["until"] = until

    try:
        # Obtener incidentes de PagerDuty
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PAGERDUTY_API_URL}/incidents",
                params=params,
                headers={
                    "Accept": "application/vnd.pagerduty+json;version=2",
                    "Authorization": f"Token token={PAGERDUTY_API_KEY}",
                    "From": PAGERDUTY_FROM_EMAIL,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                incidents = response.json()
                logger.info(
                    f"Incidentes obtenidos de PagerDuty: {len(incidents.get('incidents', []))}",
                    extra={
                        "pagerduty_status": "success",
                        "incident_count": len(incidents.get("incidents", [])),
                    },
                )
                return {
                    "status": "success",
                    "incidents": incidents.get("incidents", []),
                    "total": incidents.get("total", 0),
                }
            else:
                logger.error(
                    f"Error al obtener incidentes de PagerDuty: {response.text}",
                    extra={
                        "pagerduty_status": "error",
                        "status_code": response.status_code,
                        "response": response.text,
                    },
                )
                return {
                    "status": "error",
                    "message": f"Error al obtener incidentes: {response.text}",
                    "status_code": response.status_code,
                }

    except Exception as e:
        logger.exception(
            f"Excepción al obtener incidentes de PagerDuty: {e}",
            extra={"pagerduty_status": "exception", "error_type": type(e).__name__},
        )
        return {
            "status": "error",
            "message": f"Excepción al obtener incidentes: {str(e)}",
            "error_type": type(e).__name__,
        }


async def acknowledge_incident(incident_id: str) -> Dict[str, Any]:
    """
    Reconoce un incidente en PagerDuty.

    Args:
        incident_id: ID del incidente

    Returns:
        Dict[str, Any]: Respuesta de PagerDuty
    """
    if not PAGERDUTY_ENABLED:
        logger.warning("PagerDuty no está configurado. No se reconocerá el incidente.")
        return {"status": "skipped", "message": "PagerDuty no está configurado"}

    # Crear payload para el incidente
    payload = {"incident": {"type": "incident_reference", "status": "acknowledged"}}

    try:
        # Actualizar incidente en PagerDuty
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{PAGERDUTY_API_URL}/incidents/{incident_id}",
                json=payload,
                headers={
                    "Accept": "application/vnd.pagerduty+json;version=2",
                    "Authorization": f"Token token={PAGERDUTY_API_KEY}",
                    "From": PAGERDUTY_FROM_EMAIL,
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                logger.info(
                    f"Incidente reconocido en PagerDuty: {incident_id}",
                    extra={
                        "pagerduty_status": "acknowledged",
                        "incident_id": incident_id,
                    },
                )
                return {
                    "status": "success",
                    "message": "Incidente reconocido correctamente",
                }
            else:
                logger.error(
                    f"Error al reconocer incidente en PagerDuty: {response.text}",
                    extra={
                        "pagerduty_status": "error",
                        "status_code": response.status_code,
                        "response": response.text,
                    },
                )
                return {
                    "status": "error",
                    "message": f"Error al reconocer incidente: {response.text}",
                    "status_code": response.status_code,
                }

    except Exception as e:
        logger.exception(
            f"Excepción al reconocer incidente en PagerDuty: {e}",
            extra={"pagerduty_status": "exception", "error_type": type(e).__name__},
        )
        return {
            "status": "error",
            "message": f"Excepción al reconocer incidente: {str(e)}",
            "error_type": type(e).__name__,
        }


async def resolve_incident(incident_id: str) -> Dict[str, Any]:
    """
    Resuelve un incidente en PagerDuty.

    Args:
        incident_id: ID del incidente

    Returns:
        Dict[str, Any]: Respuesta de PagerDuty
    """
    if not PAGERDUTY_ENABLED:
        logger.warning("PagerDuty no está configurado. No se resolverá el incidente.")
        return {"status": "skipped", "message": "PagerDuty no está configurado"}

    # Crear payload para el incidente
    payload = {"incident": {"type": "incident_reference", "status": "resolved"}}

    try:
        # Actualizar incidente en PagerDuty
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{PAGERDUTY_API_URL}/incidents/{incident_id}",
                json=payload,
                headers={
                    "Accept": "application/vnd.pagerduty+json;version=2",
                    "Authorization": f"Token token={PAGERDUTY_API_KEY}",
                    "From": PAGERDUTY_FROM_EMAIL,
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                logger.info(
                    f"Incidente resuelto en PagerDuty: {incident_id}",
                    extra={"pagerduty_status": "resolved", "incident_id": incident_id},
                )
                return {
                    "status": "success",
                    "message": "Incidente resuelto correctamente",
                }
            else:
                logger.error(
                    f"Error al resolver incidente en PagerDuty: {response.text}",
                    extra={
                        "pagerduty_status": "error",
                        "status_code": response.status_code,
                        "response": response.text,
                    },
                )
                return {
                    "status": "error",
                    "message": f"Error al resolver incidente: {response.text}",
                    "status_code": response.status_code,
                }

    except Exception as e:
        logger.exception(
            f"Excepción al resolver incidente en PagerDuty: {e}",
            extra={"pagerduty_status": "exception", "error_type": type(e).__name__},
        )
        return {
            "status": "error",
            "message": f"Excepción al resolver incidente: {str(e)}",
            "error_type": type(e).__name__,
        }

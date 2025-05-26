#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Módulo de monitoreo para el cliente Vertex AI.

Este módulo proporciona funcionalidades para monitorear el rendimiento del sistema de caché
y generar alertas cuando sea necesario.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
import os

from core.logging_config import get_logger

# Configuración de logger
logger = get_logger(__name__)

# Umbrales predeterminados para alertas (configurables mediante variables de entorno)
DEFAULT_HIT_RATIO_THRESHOLD = float(
    os.environ.get("VERTEX_ALERT_HIT_RATIO_THRESHOLD", "0.4")
)  # 40%
DEFAULT_MEMORY_USAGE_THRESHOLD = float(
    os.environ.get("VERTEX_ALERT_MEMORY_USAGE_THRESHOLD", "0.85")
)  # 85%
DEFAULT_LATENCY_THRESHOLD_MS = float(
    os.environ.get("VERTEX_ALERT_LATENCY_THRESHOLD_MS", "500")
)  # 500ms
DEFAULT_ERROR_RATE_THRESHOLD = float(
    os.environ.get("VERTEX_ALERT_ERROR_RATE_THRESHOLD", "0.05")
)  # 5%

# Intervalo de verificación para alertas (en segundos)
MONITORING_INTERVAL = int(
    os.environ.get("VERTEX_MONITORING_INTERVAL", "300")
)  # 5 minutos por defecto


class CacheMonitor:
    """
    Monitor para el sistema de caché del cliente Vertex AI.

    Esta clase proporciona funcionalidades para monitorear el rendimiento del sistema de caché
    y generar alertas cuando sea necesario.
    """

    def __init__(
        self,
        client=None,
        hit_ratio_threshold: float = DEFAULT_HIT_RATIO_THRESHOLD,
        memory_usage_threshold: float = DEFAULT_MEMORY_USAGE_THRESHOLD,
        latency_threshold_ms: float = DEFAULT_LATENCY_THRESHOLD_MS,
        error_rate_threshold: float = DEFAULT_ERROR_RATE_THRESHOLD,
        alert_handlers: Optional[List[Callable]] = None,
    ):
        """
        Inicializa el monitor de caché.

        Args:
            client: Cliente Vertex AI a monitorear (si es None, usa la instancia global)
            hit_ratio_threshold: Umbral mínimo para el hit ratio (0.0-1.0)
            memory_usage_threshold: Umbral máximo para el uso de memoria (0.0-1.0)
            latency_threshold_ms: Umbral máximo para la latencia en ms
            error_rate_threshold: Umbral máximo para la tasa de errores (0.0-1.0)
            alert_handlers: Lista de funciones para manejar alertas
        """
        # Importar aquí para evitar dependencias circulares
        from .client import vertex_ai_client

        self.client = client or vertex_ai_client
        self.hit_ratio_threshold = hit_ratio_threshold
        self.memory_usage_threshold = memory_usage_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.alert_handlers = alert_handlers or [self._log_alert]

        self.monitoring_task = None
        self.previous_stats = None
        self.is_running = False
        self.alert_history = []

    async def start_monitoring(self, interval_seconds: int = MONITORING_INTERVAL):
        """
        Inicia el monitoreo periódico.

        Args:
            interval_seconds: Intervalo entre verificaciones en segundos
        """
        if self.is_running:
            logger.warning("El monitoreo ya está en ejecución")
            return

        self.is_running = True
        logger.info(
            f"Iniciando monitoreo de caché con intervalo de {interval_seconds} segundos"
        )

        # Obtener estadísticas iniciales como referencia
        self.previous_stats = await self.client.get_stats()

        # Crear tarea de monitoreo
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )

    async def stop_monitoring(self):
        """Detiene el monitoreo."""
        if not self.is_running:
            logger.warning("El monitoreo no está en ejecución")
            return

        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Monitoreo de caché detenido")

    async def _monitoring_loop(self, interval_seconds: int):
        """
        Bucle principal de monitoreo.

        Args:
            interval_seconds: Intervalo entre verificaciones en segundos
        """
        while self.is_running:
            try:
                await self._check_metrics()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en el bucle de monitoreo: {e}")
                await asyncio.sleep(interval_seconds)

    async def _check_metrics(self):
        """Verifica las métricas y genera alertas si es necesario."""
        try:
            # Obtener estadísticas actuales
            current_stats = await self.client.get_stats()

            # Verificar hit ratio
            cache_stats = current_stats.get("cache", {})
            hit_ratio = cache_stats.get("hit_ratio", 0)

            if hit_ratio < self.hit_ratio_threshold:
                await self._trigger_alert(
                    "hit_ratio_low",
                    f"Hit ratio bajo: {hit_ratio:.2%} (umbral: {self.hit_ratio_threshold:.2%})",
                    {"hit_ratio": hit_ratio, "threshold": self.hit_ratio_threshold},
                )

            # Verificar uso de memoria
            memory_stats = cache_stats.get("current_memory_bytes", {})
            l1_usage = memory_stats.get("l1", 0)
            l1_max = cache_stats.get("config", {}).get("l1_max_bytes", 1)
            memory_usage_ratio = l1_usage / l1_max if l1_max > 0 else 0

            if memory_usage_ratio > self.memory_usage_threshold:
                await self._trigger_alert(
                    "memory_usage_high",
                    f"Uso de memoria alto: {memory_usage_ratio:.2%} (umbral: {self.memory_usage_threshold:.2%})",
                    {
                        "memory_usage": memory_usage_ratio,
                        "threshold": self.memory_usage_threshold,
                    },
                )

            # Verificar latencia promedio
            latency_avg = current_stats.get("latency_avg_ms", {})
            content_latency = latency_avg.get("content_generation", 0)

            if content_latency > self.latency_threshold_ms:
                await self._trigger_alert(
                    "latency_high",
                    f"Latencia alta: {content_latency:.2f}ms (umbral: {self.latency_threshold_ms:.2f}ms)",
                    {
                        "latency": content_latency,
                        "threshold": self.latency_threshold_ms,
                    },
                )

            # Verificar tasa de errores
            total_requests = current_stats.get("content_requests", 0)
            if self.previous_stats:
                new_requests = total_requests - self.previous_stats.get(
                    "content_requests", 0
                )
                if new_requests > 0:
                    errors = current_stats.get("errors", {})
                    total_errors = (
                        sum(errors.values()) if isinstance(errors, dict) else errors
                    )
                    previous_errors = (
                        sum(self.previous_stats.get("errors", {}).values())
                        if isinstance(self.previous_stats.get("errors", {}), dict)
                        else self.previous_stats.get("errors", 0)
                    )
                    new_errors = total_errors - previous_errors
                    error_rate = new_errors / new_requests if new_requests > 0 else 0

                    if error_rate > self.error_rate_threshold:
                        await self._trigger_alert(
                            "error_rate_high",
                            f"Tasa de errores alta: {error_rate:.2%} (umbral: {self.error_rate_threshold:.2%})",
                            {
                                "error_rate": error_rate,
                                "threshold": self.error_rate_threshold,
                            },
                        )

            # Actualizar estadísticas previas
            self.previous_stats = current_stats

        except Exception as e:
            logger.error(f"Error al verificar métricas: {e}")

    async def _trigger_alert(self, alert_type: str, message: str, data: Dict[str, Any]):
        """
        Genera una alerta.

        Args:
            alert_type: Tipo de alerta
            message: Mensaje descriptivo
            data: Datos adicionales para la alerta
        """
        alert = {
            "type": alert_type,
            "message": message,
            "timestamp": time.time(),
            "data": data,
        }

        # Añadir a historial
        self.alert_history.append(alert)
        if len(self.alert_history) > 100:  # Limitar historial a 100 alertas
            self.alert_history.pop(0)

        # Notificar a todos los manejadores
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error en manejador de alertas: {e}")

    def _log_alert(self, alert: Dict[str, Any]):
        """
        Manejador de alertas predeterminado que registra en el log.

        Args:
            alert: Información de la alerta
        """
        logger.warning(f"ALERTA DE CACHÉ: {alert['message']}")

    def get_alert_history(self) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de alertas.

        Returns:
            List[Dict[str, Any]]: Historial de alertas
        """
        return self.alert_history

    async def get_health_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas de salud del sistema de caché.

        Returns:
            Dict[str, Any]: Métricas de salud
        """
        try:
            stats = await self.client.get_stats()
            cache_stats = stats.get("cache", {})

            return {
                "hit_ratio": cache_stats.get("hit_ratio", 0),
                "memory_usage": {
                    "l1_bytes": cache_stats.get("current_memory_bytes", {}).get(
                        "l1", 0
                    ),
                    "l1_max_bytes": cache_stats.get("config", {}).get(
                        "l1_max_bytes", 0
                    ),
                    "usage_ratio": (
                        cache_stats.get("current_memory_bytes", {}).get("l1", 0)
                        / cache_stats.get("config", {}).get("l1_max_bytes", 1)
                        if cache_stats.get("config", {}).get("l1_max_bytes", 0) > 0
                        else 0
                    ),
                },
                "latency_ms": stats.get("latency_avg_ms", {}).get(
                    "content_generation", 0
                ),
                "error_rate": (
                    sum(stats.get("errors", {}).values())
                    / stats.get("content_requests", 1)
                    if isinstance(stats.get("errors", {}), dict)
                    and stats.get("content_requests", 0) > 0
                    else 0
                ),
                "items_count": cache_stats.get("current_items", {}).get("total", 0),
                "evictions": cache_stats.get("evictions", {}).get("total", 0),
                "compression_ratio": cache_stats.get("compression", {}).get(
                    "compression_ratio", 0
                ),
                "status": "healthy",  # Por defecto asumimos que está saludable
            }
        except Exception as e:
            logger.error(f"Error al obtener métricas de salud: {e}")
            return {"status": "error", "error": str(e)}


# Instancia global del monitor
cache_monitor = None


async def initialize_monitoring(client=None):
    """
    Inicializa el monitoreo global.

    Args:
        client: Cliente Vertex AI a monitorear (si es None, usa la instancia global)
    """
    global cache_monitor

    if cache_monitor is None:
        cache_monitor = CacheMonitor(client=client)
        await cache_monitor.start_monitoring()
        logger.info("Monitoreo de caché inicializado")
    else:
        logger.warning("El monitoreo de caché ya está inicializado")


async def get_monitoring_status() -> Dict[str, Any]:
    """
    Obtiene el estado actual del monitoreo.

    Returns:
        Dict[str, Any]: Estado del monitoreo
    """
    if cache_monitor is None:
        return {"status": "not_initialized"}

    metrics = await cache_monitor.get_health_metrics()
    alerts = cache_monitor.get_alert_history()
    recent_alerts = alerts[-5:] if alerts else []

    return {
        "status": "running" if cache_monitor.is_running else "stopped",
        "health_metrics": metrics,
        "recent_alerts": recent_alerts,
        "alert_count": len(alerts),
        "thresholds": {
            "hit_ratio": cache_monitor.hit_ratio_threshold,
            "memory_usage": cache_monitor.memory_usage_threshold,
            "latency_ms": cache_monitor.latency_threshold_ms,
            "error_rate": cache_monitor.error_rate_threshold,
        },
    }


# Clase para integración con sistemas de monitoreo externos
class MonitoringIntegration:
    """Base para integraciones con sistemas de monitoreo externos."""

    async def send_alert(self, alert: Dict[str, Any]):
        """
        Envía una alerta al sistema externo.

        Args:
            alert: Información de la alerta
        """
        raise NotImplementedError("Debe ser implementado por las subclases")

    async def send_metrics(self, metrics: Dict[str, Any]):
        """
        Envía métricas al sistema externo.

        Args:
            metrics: Métricas a enviar
        """
        raise NotImplementedError("Debe ser implementado por las subclases")


# Ejemplo de integración con Prometheus (para implementar según necesidades)
class PrometheusIntegration(MonitoringIntegration):
    """Integración con Prometheus."""

    def __init__(self, push_gateway_url: str):
        """
        Inicializa la integración con Prometheus.

        Args:
            push_gateway_url: URL del Push Gateway de Prometheus
        """
        self.push_gateway_url = push_gateway_url

    async def send_alert(self, alert: Dict[str, Any]):
        """
        Envía una alerta a Prometheus.

        Args:
            alert: Información de la alerta
        """
        # Implementar según necesidades
        logger.info(f"Enviando alerta a Prometheus: {alert}")

    async def send_metrics(self, metrics: Dict[str, Any]):
        """
        Envía métricas a Prometheus.

        Args:
            metrics: Métricas a enviar
        """
        # Implementar según necesidades
        logger.info(f"Enviando métricas a Prometheus: {metrics}")


# Ejemplo de integración con Slack (para implementar según necesidades)
class SlackIntegration(MonitoringIntegration):
    """Integración con Slack."""

    def __init__(self, webhook_url: str):
        """
        Inicializa la integración con Slack.

        Args:
            webhook_url: URL del webhook de Slack
        """
        self.webhook_url = webhook_url

    async def send_alert(self, alert: Dict[str, Any]):
        """
        Envía una alerta a Slack.

        Args:
            alert: Información de la alerta
        """
        # Implementar según necesidades
        logger.info(f"Enviando alerta a Slack: {alert}")

    async def send_metrics(self, metrics: Dict[str, Any]):
        """
        Envía métricas a Slack.

        Args:
            metrics: Métricas a enviar
        """
        # Implementar según necesidades
        logger.info(f"Enviando métricas a Slack: {metrics}")

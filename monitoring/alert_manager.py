"""
Gestor de alertas para capacidades de visión y multimodales.

Este módulo proporciona funcionalidades para gestionar alertas basadas en
umbrales configurables, permitiendo la notificación de problemas o situaciones
que requieren atención.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Callable

from core.logging_config import get_logger
from core.vision_metrics import vision_metrics

# Configurar logger
logger = get_logger(__name__)


class AlertManager:
    """
    Gestor de alertas para capacidades de visión y multimodales.

    Proporciona métodos para configurar umbrales, generar alertas y
    gestionar notificaciones.
    """

    def __init__(self):
        """Inicializa el gestor de alertas."""
        self.lock = asyncio.Lock()

        # Umbrales para alertas
        self.thresholds = {
            "error_rate": {"value": 0.05, "enabled": True},  # 5% de tasa de error
            "latency_p95_ms": {"value": 2000, "enabled": True},  # 2 segundos para p95
            "timeout_rate": {"value": 0.02, "enabled": True},  # 2% de tasa de timeout
            "retry_rate": {"value": 0.1, "enabled": True},  # 10% de tasa de reintentos
            "cache_hit_rate_min": {
                "value": 0.3,
                "enabled": True,
            },  # Mínimo 30% de hit rate
            "api_error_spike": {
                "value": 10,
                "enabled": True,
            },  # Spike de 10 errores en 5 minutos
        }

        # Historial de alertas
        self.alerts_history: List[Dict[str, Any]] = []

        # Callbacks para notificaciones
        self.notification_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # Configurar callback en vision_metrics
        vision_metrics.register_alert_callback(self._handle_vision_alert)

        # Iniciar tarea de verificación periódica
        self.check_task = asyncio.create_task(self._periodic_check())

        logger.info("AlertManager inicializado")

    async def update_threshold(
        self, threshold_name: str, value: float, enabled: bool = True
    ) -> bool:
        """
        Actualiza un umbral para alertas.

        Args:
            threshold_name: Nombre del umbral
            value: Valor del umbral
            enabled: Si el umbral está habilitado

        Returns:
            bool: True si se actualizó correctamente
        """
        async with self.lock:
            if threshold_name in self.thresholds:
                self.thresholds[threshold_name] = {"value": value, "enabled": enabled}

                # Actualizar también en vision_metrics si corresponde
                if threshold_name in [
                    "error_rate",
                    "latency_p95_ms",
                    "timeout_rate",
                    "retry_rate",
                ]:
                    await vision_metrics.set_threshold(threshold_name, value)

                logger.info(
                    f"Umbral '{threshold_name}' actualizado: valor={value}, enabled={enabled}"
                )
                return True
            else:
                logger.warning(
                    f"Intento de actualizar umbral desconocido: {threshold_name}"
                )
                return False

    async def get_thresholds(self) -> Dict[str, Any]:
        """
        Obtiene la configuración actual de umbrales.

        Returns:
            Dict[str, Any]: Configuración de umbrales
        """
        async with self.lock:
            return self.thresholds.copy()

    async def generate_alert(
        self, severity: str, title: str, message: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera una alerta.

        Args:
            severity: Nivel de severidad (critical, high, medium, low)
            title: Título de la alerta
            message: Mensaje detallado
            data: Datos adicionales

        Returns:
            Dict[str, Any]: Alerta generada
        """
        timestamp = datetime.now().isoformat()

        alert = {
            "id": f"alert_{int(time.time() * 1000)}",
            "severity": severity,
            "title": title,
            "message": message,
            "timestamp": timestamp,
            "data": data,
        }

        # Registrar alerta en el historial
        async with self.lock:
            self.alerts_history.append(alert)

            # Limitar tamaño del historial (máximo 1000 alertas)
            if len(self.alerts_history) > 1000:
                self.alerts_history = self.alerts_history[-1000:]

        # Notificar a los callbacks registrados
        for callback in self.notification_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error en callback de notificación: {e}", exc_info=True)

        logger.info(f"Alerta generada: {severity} - {title}")
        return alert

    async def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene las alertas más recientes.

        Args:
            limit: Número máximo de alertas a devolver

        Returns:
            List[Dict[str, Any]]: Alertas recientes
        """
        async with self.lock:
            return self.alerts_history[-limit:][
                ::-1
            ]  # Últimas 'limit' alertas, más recientes primero

    async def register_notification_callback(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Registra un callback para recibir notificaciones de alertas.

        Args:
            callback: Función que recibirá las alertas
        """
        self.notification_callbacks.append(callback)

    async def _handle_vision_alert(self, alert: Dict[str, Any]) -> None:
        """
        Maneja alertas provenientes de vision_metrics.

        Args:
            alert: Datos de la alerta
        """
        # Convertir formato de alerta de vision_metrics al formato de AlertManager
        await self.generate_alert(
            severity=alert.get("severity", "medium"),
            title=alert.get("title", "Alerta de visión"),
            message=alert.get(
                "message", "Se ha generado una alerta en el sistema de visión"
            ),
            data=alert.get("data", {}),
        )

    async def _check_metrics(self) -> None:
        """
        Verifica métricas actuales contra umbrales configurados.
        """
        try:
            # Obtener métricas actuales
            metrics = await vision_metrics.get_metrics()

            # Verificar tasa de error
            if self.thresholds["error_rate"]["enabled"]:
                error_rate = metrics["quality"]["error_rate"]
                threshold = self.thresholds["error_rate"]["value"]

                if error_rate > threshold:
                    await self.generate_alert(
                        severity="high",
                        title="Tasa de error elevada",
                        message=f"La tasa de error ({error_rate:.2%}) ha superado el umbral configurado ({threshold:.2%})",
                        data={
                            "metric": "error_rate",
                            "current_value": error_rate,
                            "threshold": threshold,
                            "api_calls": metrics["api_calls"],
                        },
                    )

            # Verificar tasa de hit de caché
            if self.thresholds["cache_hit_rate_min"]["enabled"]:
                cache_hit_rate = metrics["cache"]["hit_rate"]
                threshold = self.thresholds["cache_hit_rate_min"]["value"]

                if (
                    cache_hit_rate < threshold
                    and (metrics["cache"]["hits"] + metrics["cache"]["misses"]) > 50
                ):
                    await self.generate_alert(
                        severity="medium",
                        title="Tasa de aciertos de caché baja",
                        message=f"La tasa de aciertos de caché ({cache_hit_rate:.2%}) está por debajo del umbral mínimo ({threshold:.2%})",
                        data={
                            "metric": "cache_hit_rate",
                            "current_value": cache_hit_rate,
                            "threshold": threshold,
                            "cache_stats": metrics["cache"],
                        },
                    )

            # Otras verificaciones se pueden agregar aquí

        except Exception as e:
            logger.error(f"Error al verificar métricas: {e}", exc_info=True)

    async def _periodic_check(self) -> None:
        """
        Tarea periódica para verificar métricas y generar alertas.
        """
        while True:
            try:
                await self._check_metrics()

                # Esperar antes de la siguiente verificación
                await asyncio.sleep(60)  # Verificar cada minuto

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en verificación periódica: {e}", exc_info=True)
                await asyncio.sleep(60)  # Esperar antes de reintentar

    async def close(self) -> None:
        """
        Cierra el gestor de alertas y libera recursos.
        """
        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass


# Instancia global del gestor de alertas
alert_manager = AlertManager()

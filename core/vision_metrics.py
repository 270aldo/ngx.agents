"""
Sistema de monitoreo y métricas para capacidades de visión y multimodales.

Este módulo proporciona herramientas para monitorear el rendimiento, uso y calidad
de los servicios de visión y multimodales, permitiendo la generación de alertas
y la visualización de métricas clave.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable

from core.logging_config import get_logger
from core.telemetry import Telemetry

# Configurar logger
logger = get_logger(__name__)


class VisionMetrics:
    """
    Sistema de monitoreo y métricas para capacidades de visión y multimodales.

    Recopila, almacena y analiza métricas sobre el uso de los servicios de visión
    y multimodales, permitiendo la detección de problemas y la optimización del rendimiento.
    """

    def __init__(self, telemetry: Optional[Telemetry] = None):
        """
        Inicializa el sistema de métricas de visión.

        Args:
            telemetry: Instancia de Telemetry para exportar métricas (opcional)
        """
        self.telemetry = telemetry
        self.lock = asyncio.Lock()

        # Métricas generales
        self.metrics = {
            "api_calls": {
                "total": 0,
                "success": 0,
                "error": 0,
                "by_operation": {},
                "by_agent": {},
            },
            "latency": {
                "total_ms": 0,
                "count": 0,
                "min_ms": float("inf"),
                "max_ms": 0,
                "by_operation": {},
            },
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "images": {
                "processed": 0,
                "by_size": {
                    "small": 0,  # < 100KB
                    "medium": 0,  # 100KB - 1MB
                    "large": 0,  # > 1MB
                },
                "by_type": {"jpeg": 0, "png": 0, "webp": 0, "other": 0},
            },
            "cache": {"hits": 0, "misses": 0, "hit_rate": 0.0},
            "quality": {"error_rate": 0.0, "timeout_rate": 0.0, "retry_rate": 0.0},
            "alerts": {
                "total": 0,
                "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            },
        }

        # Historial de métricas para tendencias
        self.history = {"hourly": [], "daily": []}

        # Umbrales para alertas
        self.thresholds = {
            "error_rate": 0.05,  # 5% de tasa de error
            "latency_p95_ms": 2000,  # 2 segundos para p95
            "timeout_rate": 0.02,  # 2% de tasa de timeout
            "retry_rate": 0.1,  # 10% de tasa de reintentos
        }

        # Callbacks para alertas
        self.alert_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        logger.info("VisionMetrics inicializado")

    async def record_api_call(
        self,
        operation: str,
        agent_id: str,
        success: bool,
        latency_ms: float,
        tokens: Optional[Dict[str, int]] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Registra una llamada a la API de visión.

        Args:
            operation: Tipo de operación (analyze_image, extract_text, etc.)
            agent_id: ID del agente que realizó la llamada
            success: Si la llamada fue exitosa
            latency_ms: Latencia de la llamada en milisegundos
            tokens: Información sobre tokens utilizados (opcional)
            error_type: Tipo de error si la llamada falló (opcional)
        """
        span = None
        if self.telemetry:
            span = self.telemetry.start_span("vision_metrics.record_api_call")
            self.telemetry.add_span_attribute(span, "operation", operation)
            self.telemetry.add_span_attribute(span, "agent_id", agent_id)
            self.telemetry.add_span_attribute(span, "success", success)
            self.telemetry.add_span_attribute(span, "latency_ms", latency_ms)
            if error_type:
                self.telemetry.add_span_attribute(span, "error_type", error_type)

        try:
            async with self.lock:
                # Actualizar métricas generales
                self.metrics["api_calls"]["total"] += 1

                if success:
                    self.metrics["api_calls"]["success"] += 1
                else:
                    self.metrics["api_calls"]["error"] += 1

                # Actualizar métricas por operación
                if operation not in self.metrics["api_calls"]["by_operation"]:
                    self.metrics["api_calls"]["by_operation"][operation] = {
                        "total": 0,
                        "success": 0,
                        "error": 0,
                    }

                self.metrics["api_calls"]["by_operation"][operation]["total"] += 1
                if success:
                    self.metrics["api_calls"]["by_operation"][operation]["success"] += 1
                else:
                    self.metrics["api_calls"]["by_operation"][operation]["error"] += 1

                # Actualizar métricas por agente
                if agent_id not in self.metrics["api_calls"]["by_agent"]:
                    self.metrics["api_calls"]["by_agent"][agent_id] = {
                        "total": 0,
                        "success": 0,
                        "error": 0,
                    }

                self.metrics["api_calls"]["by_agent"][agent_id]["total"] += 1
                if success:
                    self.metrics["api_calls"]["by_agent"][agent_id]["success"] += 1
                else:
                    self.metrics["api_calls"]["by_agent"][agent_id]["error"] += 1

                # Actualizar métricas de latencia
                self.metrics["latency"]["total_ms"] += latency_ms
                self.metrics["latency"]["count"] += 1
                self.metrics["latency"]["min_ms"] = min(
                    self.metrics["latency"]["min_ms"], latency_ms
                )
                self.metrics["latency"]["max_ms"] = max(
                    self.metrics["latency"]["max_ms"], latency_ms
                )

                # Actualizar latencia por operación
                if operation not in self.metrics["latency"]["by_operation"]:
                    self.metrics["latency"]["by_operation"][operation] = {
                        "total_ms": 0,
                        "count": 0,
                        "min_ms": float("inf"),
                        "max_ms": 0,
                    }

                self.metrics["latency"]["by_operation"][operation][
                    "total_ms"
                ] += latency_ms
                self.metrics["latency"]["by_operation"][operation]["count"] += 1
                self.metrics["latency"]["by_operation"][operation]["min_ms"] = min(
                    self.metrics["latency"]["by_operation"][operation]["min_ms"],
                    latency_ms,
                )
                self.metrics["latency"]["by_operation"][operation]["max_ms"] = max(
                    self.metrics["latency"]["by_operation"][operation]["max_ms"],
                    latency_ms,
                )

                # Actualizar métricas de tokens si se proporcionan
                if tokens:
                    if "prompt" in tokens:
                        self.metrics["tokens"]["prompt"] += tokens["prompt"]
                    if "completion" in tokens:
                        self.metrics["tokens"]["completion"] += tokens["completion"]
                    if "total" in tokens:
                        self.metrics["tokens"]["total"] += tokens["total"]

                # Actualizar métricas de calidad
                self.metrics["quality"]["error_rate"] = (
                    self.metrics["api_calls"]["error"]
                    / self.metrics["api_calls"]["total"]
                    if self.metrics["api_calls"]["total"] > 0
                    else 0.0
                )

                # Verificar umbrales para alertas
                await self._check_thresholds()

                # Exportar métricas a telemetría si está disponible
                if self.telemetry:
                    self.telemetry.record_metric(
                        "vision.api_calls",
                        1,
                        {
                            "operation": operation,
                            "agent_id": agent_id,
                            "success": success,
                            "error_type": error_type or "none",
                        },
                    )

                    self.telemetry.record_metric(
                        "vision.latency_ms",
                        latency_ms,
                        {"operation": operation, "agent_id": agent_id},
                    )

                    if tokens:
                        if "prompt" in tokens:
                            self.telemetry.record_metric(
                                "vision.tokens.prompt",
                                tokens["prompt"],
                                {"operation": operation, "agent_id": agent_id},
                            )
                        if "completion" in tokens:
                            self.telemetry.record_metric(
                                "vision.tokens.completion",
                                tokens["completion"],
                                {"operation": operation, "agent_id": agent_id},
                            )
                        if "total" in tokens:
                            self.telemetry.record_metric(
                                "vision.tokens.total",
                                tokens["total"],
                                {"operation": operation, "agent_id": agent_id},
                            )

        except Exception as e:
            logger.error(
                f"Error al registrar llamada a API de visión: {e}", exc_info=True
            )

            if self.telemetry and span:
                self.telemetry.record_exception(span, e)
        finally:
            if self.telemetry and span:
                self.telemetry.end_span(span)

    async def record_image_processed(
        self, image_size_bytes: int, image_type: str
    ) -> None:
        """
        Registra una imagen procesada.

        Args:
            image_size_bytes: Tamaño de la imagen en bytes
            image_type: Tipo de imagen (jpeg, png, webp, etc.)
        """
        async with self.lock:
            # Actualizar contador de imágenes procesadas
            self.metrics["images"]["processed"] += 1

            # Clasificar por tamaño
            if image_size_bytes < 102400:  # < 100KB
                self.metrics["images"]["by_size"]["small"] += 1
            elif image_size_bytes < 1048576:  # < 1MB
                self.metrics["images"]["by_size"]["medium"] += 1
            else:  # > 1MB
                self.metrics["images"]["by_size"]["large"] += 1

            # Clasificar por tipo
            image_type = image_type.lower()
            if image_type in ["jpg", "jpeg"]:
                self.metrics["images"]["by_type"]["jpeg"] += 1
            elif image_type == "png":
                self.metrics["images"]["by_type"]["png"] += 1
            elif image_type == "webp":
                self.metrics["images"]["by_type"]["webp"] += 1
            else:
                self.metrics["images"]["by_type"]["other"] += 1

            # Exportar métricas a telemetría si está disponible
            if self.telemetry:
                self.telemetry.record_metric(
                    "vision.images.processed",
                    1,
                    {
                        "size_category": (
                            "small"
                            if image_size_bytes < 102400
                            else "medium" if image_size_bytes < 1048576 else "large"
                        ),
                        "image_type": image_type,
                    },
                )

                self.telemetry.record_metric(
                    "vision.images.size_bytes",
                    image_size_bytes,
                    {"image_type": image_type},
                )

    async def record_cache_operation(self, hit: bool) -> None:
        """
        Registra una operación de caché.

        Args:
            hit: True si fue un hit de caché, False si fue un miss
        """
        async with self.lock:
            if hit:
                self.metrics["cache"]["hits"] += 1
            else:
                self.metrics["cache"]["misses"] += 1

            # Actualizar tasa de hits
            total_cache_ops = (
                self.metrics["cache"]["hits"] + self.metrics["cache"]["misses"]
            )
            self.metrics["cache"]["hit_rate"] = (
                self.metrics["cache"]["hits"] / total_cache_ops
                if total_cache_ops > 0
                else 0.0
            )

            # Exportar métricas a telemetría si está disponible
            if self.telemetry:
                self.telemetry.record_metric(
                    "vision.cache.operation", 1, {"result": "hit" if hit else "miss"}
                )

                self.telemetry.record_metric(
                    "vision.cache.hit_rate", self.metrics["cache"]["hit_rate"]
                )

    async def record_timeout(self, operation: str, agent_id: str) -> None:
        """
        Registra un timeout en una operación de visión.

        Args:
            operation: Tipo de operación (analyze_image, extract_text, etc.)
            agent_id: ID del agente que realizó la llamada
        """
        async with self.lock:
            # Actualizar tasa de timeout
            self.metrics["quality"]["timeout_rate"] = (
                self.metrics["quality"]["timeout_rate"]
                * self.metrics["api_calls"]["total"]
                + 1
            ) / (self.metrics["api_calls"]["total"] + 1)

            # Exportar métricas a telemetría si está disponible
            if self.telemetry:
                self.telemetry.record_metric(
                    "vision.timeout", 1, {"operation": operation, "agent_id": agent_id}
                )

                self.telemetry.record_metric(
                    "vision.quality.timeout_rate",
                    self.metrics["quality"]["timeout_rate"],
                )

            # Verificar umbrales para alertas
            await self._check_thresholds()

    async def record_retry(self, operation: str, agent_id: str, attempt: int) -> None:
        """
        Registra un reintento en una operación de visión.

        Args:
            operation: Tipo de operación (analyze_image, extract_text, etc.)
            agent_id: ID del agente que realizó la llamada
            attempt: Número de intento
        """
        async with self.lock:
            # Actualizar tasa de reintentos
            self.metrics["quality"]["retry_rate"] = (
                self.metrics["quality"]["retry_rate"]
                * self.metrics["api_calls"]["total"]
                + 1
            ) / (self.metrics["api_calls"]["total"] + 1)

            # Exportar métricas a telemetría si está disponible
            if self.telemetry:
                self.telemetry.record_metric(
                    "vision.retry",
                    1,
                    {"operation": operation, "agent_id": agent_id, "attempt": attempt},
                )

                self.telemetry.record_metric(
                    "vision.quality.retry_rate", self.metrics["quality"]["retry_rate"]
                )

            # Verificar umbrales para alertas
            await self._check_thresholds()

    async def _check_thresholds(self) -> None:
        """
        Verifica si se han superado los umbrales para generar alertas.
        """
        # Verificar tasa de error
        if self.metrics["quality"]["error_rate"] > self.thresholds["error_rate"]:
            await self._generate_alert(
                "high",
                "Error rate threshold exceeded",
                f"Error rate is {self.metrics['quality']['error_rate']:.2%}, threshold is {self.thresholds['error_rate']:.2%}",
                {"error_rate": self.metrics["quality"]["error_rate"]},
            )

        # Verificar tasa de timeout
        if self.metrics["quality"]["timeout_rate"] > self.thresholds["timeout_rate"]:
            await self._generate_alert(
                "high",
                "Timeout rate threshold exceeded",
                f"Timeout rate is {self.metrics['quality']['timeout_rate']:.2%}, threshold is {self.thresholds['timeout_rate']:.2%}",
                {"timeout_rate": self.metrics["quality"]["timeout_rate"]},
            )

        # Verificar tasa de reintentos
        if self.metrics["quality"]["retry_rate"] > self.thresholds["retry_rate"]:
            await self._generate_alert(
                "medium",
                "Retry rate threshold exceeded",
                f"Retry rate is {self.metrics['quality']['retry_rate']:.2%}, threshold is {self.thresholds['retry_rate']:.2%}",
                {"retry_rate": self.metrics["quality"]["retry_rate"]},
            )

        # Verificar latencia p95
        if (
            self.metrics["latency"]["count"] > 20
            and self.metrics["latency"]["max_ms"] > self.thresholds["latency_p95_ms"]
        ):
            await self._generate_alert(
                "medium",
                "Latency threshold exceeded",
                f"Maximum latency is {self.metrics['latency']['max_ms']}ms, threshold is {self.thresholds['latency_p95_ms']}ms",
                {"max_latency_ms": self.metrics["latency"]["max_ms"]},
            )

    async def _generate_alert(
        self, severity: str, title: str, message: str, data: Dict[str, Any]
    ) -> None:
        """
        Genera una alerta.

        Args:
            severity: Nivel de severidad (critical, high, medium, low)
            title: Título de la alerta
            message: Mensaje detallado
            data: Datos adicionales
        """
        # Crear objeto de alerta
        alert = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "title": title,
            "message": message,
            "data": data,
        }

        # Actualizar contadores de alertas
        self.metrics["alerts"]["total"] += 1
        self.metrics["alerts"]["by_severity"][severity] += 1

        # Registrar alerta
        logger.warning(f"Alerta de visión: {severity.upper()} - {title}: {message}")

        # Notificar a los callbacks registrados
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(
                    f"Error al notificar alerta a callback: {e}", exc_info=True
                )

        # Exportar alerta a telemetría si está disponible
        if self.telemetry:
            self.telemetry.record_metric(
                "vision.alert", 1, {"severity": severity, "title": title}
            )

    async def register_alert_callback(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Registra un callback para recibir alertas.

        Args:
            callback: Función que recibirá las alertas
        """
        self.alert_callbacks.append(callback)

    async def set_threshold(self, threshold_name: str, value: float) -> None:
        """
        Establece un umbral para alertas.

        Args:
            threshold_name: Nombre del umbral
            value: Valor del umbral
        """
        if threshold_name in self.thresholds:
            self.thresholds[threshold_name] = value
            logger.info(f"Umbral {threshold_name} establecido en {value}")
        else:
            logger.warning(f"Umbral desconocido: {threshold_name}")

    async def snapshot_metrics(self) -> None:
        """
        Toma una instantánea de las métricas actuales para análisis histórico.
        """
        async with self.lock:
            # Crear instantánea
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "api_calls": {
                    "total": self.metrics["api_calls"]["total"],
                    "success": self.metrics["api_calls"]["success"],
                    "error": self.metrics["api_calls"]["error"],
                },
                "latency": {
                    "avg_ms": (
                        self.metrics["latency"]["total_ms"]
                        / self.metrics["latency"]["count"]
                        if self.metrics["latency"]["count"] > 0
                        else 0
                    ),
                    "min_ms": (
                        self.metrics["latency"]["min_ms"]
                        if self.metrics["latency"]["min_ms"] != float("inf")
                        else 0
                    ),
                    "max_ms": self.metrics["latency"]["max_ms"],
                },
                "tokens": {"total": self.metrics["tokens"]["total"]},
                "images": {"processed": self.metrics["images"]["processed"]},
                "cache": {"hit_rate": self.metrics["cache"]["hit_rate"]},
                "quality": {
                    "error_rate": self.metrics["quality"]["error_rate"],
                    "timeout_rate": self.metrics["quality"]["timeout_rate"],
                    "retry_rate": self.metrics["quality"]["retry_rate"],
                },
            }

            # Añadir a histórico horario
            self.history["hourly"].append(snapshot)

            # Limitar tamaño del histórico horario (24 horas)
            if len(self.history["hourly"]) > 24:
                self.history["hourly"].pop(0)

            # Añadir a histórico diario si es medianoche
            current_hour = datetime.now().hour
            if current_hour == 0:
                # Calcular métricas diarias
                daily_snapshot = snapshot.copy()
                daily_snapshot["type"] = "daily"
                self.history["daily"].append(daily_snapshot)

                # Limitar tamaño del histórico diario (30 días)
                if len(self.history["daily"]) > 30:
                    self.history["daily"].pop(0)

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas actuales.

        Returns:
            Dict[str, Any]: Métricas actuales
        """
        async with self.lock:
            # Calcular métricas derivadas
            avg_latency = (
                self.metrics["latency"]["total_ms"] / self.metrics["latency"]["count"]
                if self.metrics["latency"]["count"] > 0
                else 0
            )

            # Crear objeto de métricas
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "api_calls": self.metrics["api_calls"],
                "latency": {**self.metrics["latency"], "avg_ms": avg_latency},
                "tokens": self.metrics["tokens"],
                "images": self.metrics["images"],
                "cache": self.metrics["cache"],
                "quality": self.metrics["quality"],
                "alerts": self.metrics["alerts"],
            }

            return metrics

    async def get_history(self, period: str = "hourly") -> List[Dict[str, Any]]:
        """
        Obtiene el historial de métricas.

        Args:
            period: Período de tiempo (hourly, daily)

        Returns:
            List[Dict[str, Any]]: Historial de métricas
        """
        async with self.lock:
            if period == "hourly":
                return self.history["hourly"]
            elif period == "daily":
                return self.history["daily"]
            else:
                return []

    async def reset_metrics(self) -> None:
        """
        Reinicia las métricas.
        """
        async with self.lock:
            # Guardar histórico antes de reiniciar
            await self.snapshot_metrics()

            # Reiniciar métricas
            self.metrics = {
                "api_calls": {
                    "total": 0,
                    "success": 0,
                    "error": 0,
                    "by_operation": {},
                    "by_agent": {},
                },
                "latency": {
                    "total_ms": 0,
                    "count": 0,
                    "min_ms": float("inf"),
                    "max_ms": 0,
                    "by_operation": {},
                },
                "tokens": {"prompt": 0, "completion": 0, "total": 0},
                "images": {
                    "processed": 0,
                    "by_size": {"small": 0, "medium": 0, "large": 0},
                    "by_type": {"jpeg": 0, "png": 0, "webp": 0, "other": 0},
                },
                "cache": {"hits": 0, "misses": 0, "hit_rate": 0.0},
                "quality": {"error_rate": 0.0, "timeout_rate": 0.0, "retry_rate": 0.0},
                "alerts": {
                    "total": 0,
                    "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                },
            }

            logger.info("Métricas de visión reiniciadas")


# Instancia global de métricas
vision_metrics = VisionMetrics()

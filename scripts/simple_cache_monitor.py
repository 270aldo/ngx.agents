#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para monitoreo simple del sistema de caché de Vertex AI.

Este script proporciona un monitoreo básico del sistema de caché sin depender
de las bibliotecas de OpenTelemetry completas.
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, Any

# Añadir directorio raíz al path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("cache_monitoring.log")],
)
logger = logging.getLogger("cache_monitor")

# Umbrales predeterminados
DEFAULT_HIT_RATIO_THRESHOLD = 0.5  # 50%
DEFAULT_MEMORY_USAGE_THRESHOLD = 0.8  # 80%
DEFAULT_LATENCY_THRESHOLD_MS = 400  # 400ms
DEFAULT_ERROR_RATE_THRESHOLD = 0.03  # 3%
DEFAULT_CHECK_INTERVAL = 120  # 2 minutos


class SimpleCacheMonitor:
    """Monitor simple para el sistema de caché de Vertex AI."""

    def __init__(
        self,
        hit_ratio_threshold: float = DEFAULT_HIT_RATIO_THRESHOLD,
        memory_usage_threshold: float = DEFAULT_MEMORY_USAGE_THRESHOLD,
        latency_threshold_ms: float = DEFAULT_LATENCY_THRESHOLD_MS,
        error_rate_threshold: float = DEFAULT_ERROR_RATE_THRESHOLD,
        check_interval: int = DEFAULT_CHECK_INTERVAL,
        export_metrics: bool = True,
        metrics_file: str = "cache_metrics.json",
    ):
        """
        Inicializa el monitor simple.

        Args:
            hit_ratio_threshold: Umbral mínimo para el hit ratio (0.0-1.0)
            memory_usage_threshold: Umbral máximo para el uso de memoria (0.0-1.0)
            latency_threshold_ms: Umbral máximo para la latencia en ms
            error_rate_threshold: Umbral máximo para la tasa de errores (0.0-1.0)
            check_interval: Intervalo entre verificaciones en segundos
            export_metrics: Si es True, exporta las métricas a un archivo
            metrics_file: Ruta al archivo de métricas
        """
        self.hit_ratio_threshold = hit_ratio_threshold
        self.memory_usage_threshold = memory_usage_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.check_interval = check_interval
        self.export_metrics = export_metrics
        self.metrics_file = metrics_file

        self.metrics_history = []
        self.alerts = []
        self.running = False

    def start(self):
        """Inicia el monitoreo."""
        self.running = True
        logger.info(
            f"Iniciando monitoreo simple con intervalo de {self.check_interval} segundos"
        )

        try:
            while self.running:
                self._check_metrics()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Monitoreo detenido por el usuario")
            self.running = False

    def stop(self):
        """Detiene el monitoreo."""
        self.running = False
        logger.info("Monitoreo detenido")

    def _check_metrics(self):
        """Verifica las métricas y genera alertas si es necesario."""
        # Obtener métricas actuales
        metrics = self._collect_metrics()

        # Guardar métricas en el historial
        self.metrics_history.append(metrics)

        # Limitar el historial a las últimas 100 métricas
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]

        # Verificar umbrales y generar alertas
        self._check_thresholds(metrics)

        # Exportar métricas si es necesario
        if self.export_metrics:
            self._export_metrics()

        # Mostrar métricas actuales
        self._print_metrics(metrics)

    def _collect_metrics(self) -> Dict[str, Any]:
        """
        Recolecta métricas del sistema de caché.

        Returns:
            Dict[str, Any]: Métricas recolectadas
        """
        # Aquí normalmente obtendríamos métricas reales del sistema de caché
        # Como es un ejemplo, generamos métricas simuladas

        # Obtener datos del archivo de resultados de optimización si existe
        cache_metrics = {}
        try:
            if os.path.exists("cache_optimization_results.json"):
                with open("cache_optimization_results.json", "r") as f:
                    cache_data = json.load(f)
                    if "results" in cache_data and len(cache_data["results"]) > 0:
                        best_config = cache_data["results"][0]
                        cache_metrics = {
                            "hit_ratio": best_config.get("hit_ratio", 0.0) / 100.0,
                            "memory_usage": best_config.get("memory_usage", 0.0)
                            / 100.0,
                            "avg_latency_ms": best_config.get("latency", 0.0),
                            "error_rate": 0.01,  # Valor simulado
                            "throughput": best_config.get("throughput", 0.0),
                            "policy": best_config.get("policy", "unknown"),
                            "partitions": best_config.get("partitions", 0),
                        }
        except Exception as e:
            logger.warning(f"Error al leer datos de optimización: {str(e)}")

        # Si no hay datos de optimización, usar valores simulados
        if not cache_metrics:
            cache_metrics = {
                "hit_ratio": 0.7,  # 70%
                "memory_usage": 0.6,  # 60%
                "avg_latency_ms": 250.0,  # 250ms
                "error_rate": 0.01,  # 1%
                "throughput": 10.0,  # 10 req/s
                "policy": "hybrid",
                "partitions": 4,
            }

        # Añadir timestamp
        cache_metrics["timestamp"] = datetime.now().isoformat()

        return cache_metrics

    def _check_thresholds(self, metrics: Dict[str, Any]):
        """
        Verifica si las métricas superan los umbrales y genera alertas.

        Args:
            metrics: Métricas a verificar
        """
        # Verificar hit ratio
        if metrics.get("hit_ratio", 1.0) < self.hit_ratio_threshold:
            self._trigger_alert(
                "low_hit_ratio",
                f"Hit ratio bajo: {metrics.get('hit_ratio', 0.0):.2%} (umbral: {self.hit_ratio_threshold:.2%})",
                metrics,
            )

        # Verificar uso de memoria
        if metrics.get("memory_usage", 0.0) > self.memory_usage_threshold:
            self._trigger_alert(
                "high_memory_usage",
                f"Uso de memoria alto: {metrics.get('memory_usage', 0.0):.2%} (umbral: {self.memory_usage_threshold:.2%})",
                metrics,
            )

        # Verificar latencia
        if metrics.get("avg_latency_ms", 0.0) > self.latency_threshold_ms:
            self._trigger_alert(
                "high_latency",
                f"Latencia alta: {metrics.get('avg_latency_ms', 0.0):.2f}ms (umbral: {self.latency_threshold_ms:.2f}ms)",
                metrics,
            )

        # Verificar tasa de errores
        if metrics.get("error_rate", 0.0) > self.error_rate_threshold:
            self._trigger_alert(
                "high_error_rate",
                f"Tasa de errores alta: {metrics.get('error_rate', 0.0):.2%} (umbral: {self.error_rate_threshold:.2%})",
                metrics,
            )

    def _trigger_alert(self, alert_type: str, message: str, data: Dict[str, Any]):
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
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        self.alerts.append(alert)

        # Limitar el historial de alertas a las últimas 50
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]

        # Registrar alerta en el log
        logger.warning(f"ALERTA: {message}")

    def _export_metrics(self):
        """Exporta las métricas y alertas a un archivo JSON."""
        export_data = {
            "metrics": self.metrics_history,
            "alerts": self.alerts,
            "thresholds": {
                "hit_ratio": self.hit_ratio_threshold,
                "memory_usage": self.memory_usage_threshold,
                "latency_ms": self.latency_threshold_ms,
                "error_rate": self.error_rate_threshold,
            },
            "last_updated": datetime.now().isoformat(),
        }

        with open(self.metrics_file, "w") as f:
            json.dump(export_data, f, indent=2)

    def _print_metrics(self, metrics: Dict[str, Any]):
        """
        Muestra las métricas actuales en la consola.

        Args:
            metrics: Métricas a mostrar
        """
        print("\n=== Métricas de Caché ===")
        print(f"Timestamp: {metrics.get('timestamp', 'N/A')}")
        print(f"Hit ratio: {metrics.get('hit_ratio', 0.0):.2%}")
        print(f"Uso de memoria: {metrics.get('memory_usage', 0.0):.2%}")
        print(f"Latencia promedio: {metrics.get('avg_latency_ms', 0.0):.2f} ms")
        print(f"Tasa de errores: {metrics.get('error_rate', 0.0):.2%}")
        print(f"Throughput: {metrics.get('throughput', 0.0):.2f} req/s")
        print(f"Política: {metrics.get('policy', 'N/A')}")
        print(f"Particiones: {metrics.get('partitions', 0)}")

        # Mostrar alertas recientes
        if self.alerts:
            print("\n=== Alertas Recientes ===")
            for alert in self.alerts[-3:]:  # Mostrar las últimas 3 alertas
                print(f"[{alert['timestamp']}] {alert['type']}: {alert['message']}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Monitor simple para el sistema de caché de Vertex AI"
    )

    parser.add_argument(
        "--hit-ratio",
        type=float,
        default=DEFAULT_HIT_RATIO_THRESHOLD,
        help=f"Umbral mínimo para el hit ratio (0.0-1.0, default: {DEFAULT_HIT_RATIO_THRESHOLD})",
    )
    parser.add_argument(
        "--memory-usage",
        type=float,
        default=DEFAULT_MEMORY_USAGE_THRESHOLD,
        help=f"Umbral máximo para el uso de memoria (0.0-1.0, default: {DEFAULT_MEMORY_USAGE_THRESHOLD})",
    )
    parser.add_argument(
        "--latency",
        type=float,
        default=DEFAULT_LATENCY_THRESHOLD_MS,
        help=f"Umbral máximo para la latencia en ms (default: {DEFAULT_LATENCY_THRESHOLD_MS})",
    )
    parser.add_argument(
        "--error-rate",
        type=float,
        default=DEFAULT_ERROR_RATE_THRESHOLD,
        help=f"Umbral máximo para la tasa de errores (0.0-1.0, default: {DEFAULT_ERROR_RATE_THRESHOLD})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_CHECK_INTERVAL,
        help=f"Intervalo entre verificaciones en segundos (default: {DEFAULT_CHECK_INTERVAL})",
    )
    parser.add_argument(
        "--no-export", action="store_true", help="No exportar métricas a un archivo"
    )
    parser.add_argument(
        "--metrics-file",
        type=str,
        default="cache_metrics.json",
        help="Ruta al archivo de métricas (default: cache_metrics.json)",
    )

    args = parser.parse_args()

    # Validar argumentos
    if not 0 <= args.hit_ratio <= 1:
        parser.error("El umbral de hit ratio debe estar entre 0.0 y 1.0")
    if not 0 <= args.memory_usage <= 1:
        parser.error("El umbral de uso de memoria debe estar entre 0.0 y 1.0")
    if not 0 <= args.error_rate <= 1:
        parser.error("El umbral de tasa de errores debe estar entre 0.0 y 1.0")
    if args.latency <= 0:
        parser.error("El umbral de latencia debe ser mayor que 0")
    if args.interval <= 0:
        parser.error("El intervalo de verificación debe ser mayor que 0")

    # Crear y ejecutar monitor
    monitor = SimpleCacheMonitor(
        hit_ratio_threshold=args.hit_ratio,
        memory_usage_threshold=args.memory_usage,
        latency_threshold_ms=args.latency,
        error_rate_threshold=args.error_rate,
        check_interval=args.interval,
        export_metrics=not args.no_export,
        metrics_file=args.metrics_file,
    )

    print("\nMonitor simple de caché iniciado con los siguientes umbrales:")
    print(f"Hit ratio mínimo: {args.hit_ratio:.2%}")
    print(f"Uso de memoria máximo: {args.memory_usage:.2%}")
    print(f"Latencia máxima: {args.latency:.2f} ms")
    print(f"Tasa de errores máxima: {args.error_rate:.2%}")
    print(f"Intervalo de verificación: {args.interval} segundos")
    print(f"Exportar métricas: {'No' if args.no_export else 'Sí'}")
    if not args.no_export:
        print(f"Archivo de métricas: {args.metrics_file}")

    print("\nPresione Ctrl+C para detener el monitoreo.")

    # Iniciar monitoreo
    monitor.start()


if __name__ == "__main__":
    main()

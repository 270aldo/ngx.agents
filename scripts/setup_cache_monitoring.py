#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para configurar el monitoreo y alertas del sistema de caché de Vertex AI.

Este script configura el monitoreo del sistema de caché de Vertex AI y establece
alertas basadas en umbrales definidos para detectar problemas de rendimiento.
"""

import asyncio
import argparse
import os
import json
import logging
import sys
from typing import Dict, Any, Optional, List

# Añadir directorio raíz al path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
from core.logging_config import get_logger
logger = get_logger(__name__)

# Importar módulos necesarios
from clients.vertex_ai.monitoring import (
    CacheMonitor, 
    PrometheusIntegration, 
    SlackIntegration,
    initialize_monitoring,
    get_monitoring_status
)
from clients.vertex_ai.client import VertexAIClient

# Valores predeterminados para umbrales
DEFAULT_HIT_RATIO_THRESHOLD = 0.4  # 40%
DEFAULT_MEMORY_USAGE_THRESHOLD = 0.85  # 85%
DEFAULT_LATENCY_THRESHOLD_MS = 500  # 500ms
DEFAULT_ERROR_RATE_THRESHOLD = 0.05  # 5%
DEFAULT_MONITORING_INTERVAL = 300  # 5 minutos

class MonitoringSetup:
    """Clase para configurar el monitoreo y alertas del sistema de caché."""
    
    def __init__(
        self,
        client: Optional[VertexAIClient] = None,
        hit_ratio_threshold: float = DEFAULT_HIT_RATIO_THRESHOLD,
        memory_usage_threshold: float = DEFAULT_MEMORY_USAGE_THRESHOLD,
        latency_threshold_ms: float = DEFAULT_LATENCY_THRESHOLD_MS,
        error_rate_threshold: float = DEFAULT_ERROR_RATE_THRESHOLD,
        monitoring_interval: int = DEFAULT_MONITORING_INTERVAL,
        prometheus_url: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
        export_config: bool = False,
        config_file: str = "monitoring_config.json"
    ):
        """
        Inicializa la configuración de monitoreo.
        
        Args:
            client: Cliente Vertex AI a monitorear
            hit_ratio_threshold: Umbral mínimo para el hit ratio (0.0-1.0)
            memory_usage_threshold: Umbral máximo para el uso de memoria (0.0-1.0)
            latency_threshold_ms: Umbral máximo para la latencia en ms
            error_rate_threshold: Umbral máximo para la tasa de errores (0.0-1.0)
            monitoring_interval: Intervalo entre verificaciones en segundos
            prometheus_url: URL del Push Gateway de Prometheus (opcional)
            slack_webhook_url: URL del webhook de Slack (opcional)
            export_config: Si es True, exporta la configuración a un archivo
            config_file: Ruta al archivo de configuración
        """
        self.client = client
        self.hit_ratio_threshold = hit_ratio_threshold
        self.memory_usage_threshold = memory_usage_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.monitoring_interval = monitoring_interval
        self.prometheus_url = prometheus_url
        self.slack_webhook_url = slack_webhook_url
        self.export_config = export_config
        self.config_file = config_file
        
        self.monitor = None
        self.integrations = []
    
    async def setup(self):
        """Configura el monitoreo y las alertas."""
        # Configurar integraciones externas
        if self.prometheus_url:
            logger.info(f"Configurando integración con Prometheus: {self.prometheus_url}")
            self.integrations.append(PrometheusIntegration(self.prometheus_url))
        
        if self.slack_webhook_url:
            logger.info(f"Configurando integración con Slack")
            self.integrations.append(SlackIntegration(self.slack_webhook_url))
        
        # Configurar variables de entorno para umbrales
        os.environ["VERTEX_ALERT_HIT_RATIO_THRESHOLD"] = str(self.hit_ratio_threshold)
        os.environ["VERTEX_ALERT_MEMORY_USAGE_THRESHOLD"] = str(self.memory_usage_threshold)
        os.environ["VERTEX_ALERT_LATENCY_THRESHOLD_MS"] = str(self.latency_threshold_ms)
        os.environ["VERTEX_ALERT_ERROR_RATE_THRESHOLD"] = str(self.error_rate_threshold)
        os.environ["VERTEX_MONITORING_INTERVAL"] = str(self.monitoring_interval)
        
        # Inicializar monitoreo
        logger.info("Inicializando monitoreo de caché")
        await initialize_monitoring(self.client)
        
        # Exportar configuración si es necesario
        if self.export_config:
            self._export_config()
        
        # Mostrar estado del monitoreo
        status = await get_monitoring_status()
        logger.info(f"Estado del monitoreo: {json.dumps(status, indent=2)}")
        
        return status
    
    def _export_config(self):
        """Exporta la configuración a un archivo JSON."""
        config = {
            "thresholds": {
                "hit_ratio": self.hit_ratio_threshold,
                "memory_usage": self.memory_usage_threshold,
                "latency_ms": self.latency_threshold_ms,
                "error_rate": self.error_rate_threshold
            },
            "monitoring_interval": self.monitoring_interval,
            "integrations": {
                "prometheus": self.prometheus_url is not None,
                "slack": self.slack_webhook_url is not None
            },
            "environment_variables": {
                "VERTEX_ALERT_HIT_RATIO_THRESHOLD": str(self.hit_ratio_threshold),
                "VERTEX_ALERT_MEMORY_USAGE_THRESHOLD": str(self.memory_usage_threshold),
                "VERTEX_ALERT_LATENCY_THRESHOLD_MS": str(self.latency_threshold_ms),
                "VERTEX_ALERT_ERROR_RATE_THRESHOLD": str(self.error_rate_threshold),
                "VERTEX_MONITORING_INTERVAL": str(self.monitoring_interval)
            }
        }
        
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Configuración exportada a {self.config_file}")

async def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Configurar monitoreo y alertas para el sistema de caché de Vertex AI")
    
    parser.add_argument("--hit-ratio", type=float, default=DEFAULT_HIT_RATIO_THRESHOLD,
                        help=f"Umbral mínimo para el hit ratio (0.0-1.0, default: {DEFAULT_HIT_RATIO_THRESHOLD})")
    parser.add_argument("--memory-usage", type=float, default=DEFAULT_MEMORY_USAGE_THRESHOLD,
                        help=f"Umbral máximo para el uso de memoria (0.0-1.0, default: {DEFAULT_MEMORY_USAGE_THRESHOLD})")
    parser.add_argument("--latency", type=float, default=DEFAULT_LATENCY_THRESHOLD_MS,
                        help=f"Umbral máximo para la latencia en ms (default: {DEFAULT_LATENCY_THRESHOLD_MS})")
    parser.add_argument("--error-rate", type=float, default=DEFAULT_ERROR_RATE_THRESHOLD,
                        help=f"Umbral máximo para la tasa de errores (0.0-1.0, default: {DEFAULT_ERROR_RATE_THRESHOLD})")
    parser.add_argument("--interval", type=int, default=DEFAULT_MONITORING_INTERVAL,
                        help=f"Intervalo entre verificaciones en segundos (default: {DEFAULT_MONITORING_INTERVAL})")
    parser.add_argument("--prometheus", type=str, default=None,
                        help="URL del Push Gateway de Prometheus")
    parser.add_argument("--slack", type=str, default=None,
                        help="URL del webhook de Slack")
    parser.add_argument("--export", action="store_true",
                        help="Exportar configuración a un archivo")
    parser.add_argument("--config-file", type=str, default="monitoring_config.json",
                        help="Ruta al archivo de configuración (default: monitoring_config.json)")
    
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
        parser.error("El intervalo de monitoreo debe ser mayor que 0")
    
    # Configurar monitoreo
    setup = MonitoringSetup(
        hit_ratio_threshold=args.hit_ratio,
        memory_usage_threshold=args.memory_usage,
        latency_threshold_ms=args.latency,
        error_rate_threshold=args.error_rate,
        monitoring_interval=args.interval,
        prometheus_url=args.prometheus,
        slack_webhook_url=args.slack,
        export_config=args.export,
        config_file=args.config_file
    )
    
    # Iniciar monitoreo
    status = await setup.setup()
    
    # Mostrar mensaje de éxito
    print("\nMonitoreo configurado exitosamente")
    print(f"Hit ratio threshold: {args.hit_ratio * 100:.1f}%")
    print(f"Memory usage threshold: {args.memory_usage * 100:.1f}%")
    print(f"Latency threshold: {args.latency} ms")
    print(f"Error rate threshold: {args.error_rate * 100:.1f}%")
    print(f"Monitoring interval: {args.interval} segundos")
    
    if args.prometheus:
        print(f"Prometheus integration: Enabled ({args.prometheus})")
    else:
        print("Prometheus integration: Disabled")
    
    if args.slack:
        print(f"Slack integration: Enabled")
    else:
        print("Slack integration: Disabled")
    
    if args.export:
        print(f"Configuration exported to: {args.config_file}")
    
    # Mantener el script en ejecución para que el monitoreo continúe
    print("\nMonitoreo en ejecución. Presione Ctrl+C para detener.")
    try:
        while True:
            await asyncio.sleep(10)
            # Cada 10 segundos, mostrar el estado actual
            status = await get_monitoring_status()
            if "health_metrics" in status:
                metrics = status["health_metrics"]
                print(f"\nMétricas actuales:")
                print(f"  Hit ratio: {metrics.get('hit_ratio', 'N/A'):.2%}")
                print(f"  Memory usage: {metrics.get('memory_usage', 'N/A'):.2%}")
                print(f"  Latency: {metrics.get('avg_latency_ms', 'N/A'):.2f} ms")
                print(f"  Error rate: {metrics.get('error_rate', 'N/A'):.2%}")
                
                # Mostrar alertas recientes
                if "recent_alerts" in status and status["recent_alerts"]:
                    print("\nAlertas recientes:")
                    for alert in status["recent_alerts"]:
                        print(f"  [{alert['timestamp']}] {alert['type']}: {alert['message']}")
    except KeyboardInterrupt:
        print("\nMonitoreo detenido.")

if __name__ == "__main__":
    asyncio.run(main())

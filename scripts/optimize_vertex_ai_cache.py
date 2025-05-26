#!/usr/bin/env python3
"""
Script para optimizar la configuración de caché del cliente Vertex AI.

Este script analiza el uso del cliente Vertex AI y ajusta los parámetros de caché
para optimizar el rendimiento y reducir costos.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("vertex-ai-optimizer")

# Intentar importar el cliente Vertex AI
try:
    from clients.vertex_ai import vertex_ai_client
except ImportError:
    logger.error(
        "No se pudo importar el cliente Vertex AI. Asegúrate de ejecutar este script desde el directorio raíz del proyecto."
    )
    sys.exit(1)

# Configuración por defecto
DEFAULT_CONFIG = {
    "cache_ttl": {
        "content_generation": 3600,  # 1 hora
        "embedding": 86400,  # 24 horas
        "multimodal": 7200,  # 2 horas
        "document": 86400,  # 24 horas
        "batch_embedding": 43200,  # 12 horas
    },
    "max_cache_size": 5000,
    "compression_threshold": 1024,  # Comprimir respuestas mayores a 1KB
    "invalidation_patterns": [
        # Patrones para invalidación selectiva
        {
            "type": "content",
            "contains": "tiempo actual",
            "ttl": 300,
        },  # 5 minutos para consultas sobre tiempo actual
        {
            "type": "content",
            "contains": "noticias",
            "ttl": 1800,
        },  # 30 minutos para consultas sobre noticias
        {
            "type": "content",
            "contains": "clima",
            "ttl": 3600,
        },  # 1 hora para consultas sobre clima
    ],
}


async def get_current_stats() -> Dict[str, Any]:
    """Obtiene estadísticas actuales del cliente Vertex AI."""
    try:
        # Inicializar cliente si es necesario
        if not vertex_ai_client.is_initialized:
            await vertex_ai_client.initialize()

        # Obtener estadísticas
        stats = await vertex_ai_client.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}")
        return {}


async def analyze_usage_patterns(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analiza patrones de uso para recomendar configuraciones óptimas.

    Args:
        stats: Estadísticas del cliente Vertex AI

    Returns:
        Dict con recomendaciones
    """
    recommendations = {
        "cache_ttl": {},
        "max_cache_size": DEFAULT_CONFIG["max_cache_size"],
        "compression": True,
        "invalidation_patterns": [],
    }

    # Analizar latencia por operación
    latency_avg = stats.get("latency_avg_ms", {})

    # Analizar uso de caché
    cache_stats = stats.get("cache", {})
    hit_ratio = cache_stats.get("hit_ratio", 0)

    # Ajustar TTL basado en tipos de operación
    if "content_requests" in stats and stats["content_requests"] > 0:
        # Si hay muchas solicitudes de contenido, ajustar TTL
        recommendations["cache_ttl"]["content_generation"] = 7200  # 2 horas

    if "embedding_requests" in stats and stats["embedding_requests"] > 0:
        # Los embeddings cambian menos, pueden tener TTL más largo
        recommendations["cache_ttl"]["embedding"] = 172800  # 48 horas

    # Ajustar tamaño de caché basado en uso
    if hit_ratio < 0.5:  # Si la tasa de aciertos es menor al 50%
        # Aumentar tamaño de caché
        recommendations["max_cache_size"] = min(
            10000, DEFAULT_CONFIG["max_cache_size"] * 2
        )

    return recommendations


async def apply_optimizations(
    recommendations: Dict[str, Any], dry_run: bool = True
) -> None:
    """
    Aplica las optimizaciones recomendadas.

    Args:
        recommendations: Recomendaciones de optimización
        dry_run: Si es True, solo muestra las recomendaciones sin aplicarlas
    """
    if dry_run:
        logger.info("Modo dry-run: mostrando recomendaciones sin aplicarlas")
        logger.info(f"Recomendaciones: {json.dumps(recommendations, indent=2)}")
        return

    try:
        # Inicializar cliente si es necesario
        if not vertex_ai_client.is_initialized:
            await vertex_ai_client.initialize()

        # Aplicar configuración de TTL
        for operation, ttl in recommendations.get("cache_ttl", {}).items():
            logger.info(f"Configurando TTL para {operation}: {ttl} segundos")
            # En un entorno real, aquí se aplicaría la configuración

        # Configurar tamaño máximo de caché
        max_cache_size = recommendations.get("max_cache_size")
        if max_cache_size:
            logger.info(
                f"Configurando tamaño máximo de caché: {max_cache_size} entradas"
            )
            # En un entorno real, aquí se aplicaría la configuración

        # Configurar compresión
        if recommendations.get("compression", False):
            logger.info("Habilitando compresión de datos para respuestas grandes")
            # En un entorno real, aquí se aplicaría la configuración

        # Guardar configuración en archivo
        config_path = os.path.join(
            os.path.dirname(__file__), "../config/vertex_ai_cache_config.json"
        )
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(recommendations, f, indent=2)

        logger.info(f"Configuración guardada en {config_path}")

        # Actualizar variables de entorno
        logger.info(
            "Para aplicar esta configuración, actualiza las siguientes variables de entorno:"
        )
        logger.info(
            f"VERTEX_CACHE_TTL={recommendations.get('cache_ttl', {}).get('content_generation', 3600)}"
        )
        logger.info(
            f"VERTEX_MAX_CACHE_SIZE={recommendations.get('max_cache_size', 5000)}"
        )
        logger.info("Y reinicia los servicios que utilizan el cliente Vertex AI")

    except Exception as e:
        logger.error(f"Error al aplicar optimizaciones: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Optimiza la configuración de caché del cliente Vertex AI"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Aplicar las optimizaciones recomendadas"
    )
    parser.add_argument(
        "--config", type=str, help="Ruta a un archivo de configuración personalizado"
    )
    args = parser.parse_args()

    # Cargar configuración personalizada si se proporciona
    config = DEFAULT_CONFIG
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, "r") as f:
                custom_config = json.load(f)
                config.update(custom_config)
            logger.info(f"Configuración cargada desde {args.config}")
        except Exception as e:
            logger.error(f"Error al cargar configuración: {e}")

    # Obtener estadísticas actuales
    logger.info("Obteniendo estadísticas del cliente Vertex AI...")
    stats = await get_current_stats()

    if not stats:
        logger.error("No se pudieron obtener estadísticas. Saliendo.")
        return

    logger.info("Analizando patrones de uso...")
    recommendations = await analyze_usage_patterns(stats)

    # Aplicar optimizaciones
    await apply_optimizations(recommendations, dry_run=not args.apply)

    if not args.apply:
        logger.info("Para aplicar estas optimizaciones, ejecuta el script con --apply")


if __name__ == "__main__":
    asyncio.run(main())

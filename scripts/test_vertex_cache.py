#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para probar el rendimiento del sistema de caché avanzado en el cliente Vertex AI.
"""

import asyncio
import time
import random
import sys
import os
from typing import Dict, List, Any

# Añadir directorio raíz al path para importaciones
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Parchear módulo de telemetría para evitar dependencias faltantes
sys.modules["core.telemetry"] = __import__("scripts.mock_telemetry", fromlist=["*"])

# Importar cliente Vertex AI después del parche
from clients.vertex_ai.client import VertexAIClient

# Configuración de logging
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_vertex_cache")

# Configuración de pruebas
TEST_CONFIGS = [
    {
        "policy": "lru",
        "partitions": 2,
        "l1_ratio": 0.2,
        "prefetch": 0.7,
        "compression": 1024,
    },
    {
        "policy": "lfu",
        "partitions": 2,
        "l1_ratio": 0.2,
        "prefetch": 0.7,
        "compression": 1024,
    },
    {
        "policy": "fifo",
        "partitions": 2,
        "l1_ratio": 0.2,
        "prefetch": 0.7,
        "compression": 1024,
    },
    {
        "policy": "hybrid",
        "partitions": 4,
        "l1_ratio": 0.3,
        "prefetch": 0.8,
        "compression": 1024,
    },
]

# Datos de prueba
TEST_PROMPTS = [
    "¿Cuál es la capital de Francia?",
    "Explica la teoría de la relatividad",
    "¿Cómo funciona un motor de combustión interna?",
    "Escribe un poema sobre la naturaleza",
    "¿Cuáles son los beneficios de la meditación?",
    "Describe el proceso de fotosíntesis",
    "¿Qué es la inteligencia artificial?",
    "Explica la diferencia entre machine learning y deep learning",
    "¿Cómo afecta el cambio climático a los océanos?",
    "Describe la estructura del ADN",
]


# Función para crear un cliente con configuración específica
def create_client(config: Dict[str, Any]) -> VertexAIClient:
    """Crea un cliente Vertex AI con la configuración especificada."""
    return VertexAIClient(
        use_redis_cache=False,  # Usar solo caché en memoria para pruebas
        cache_ttl=3600,
        max_cache_size=100,  # 100 MB
        max_connections=5,
        cache_policy=config["policy"],
        cache_partitions=config["partitions"],
        l1_size_ratio=config["l1_ratio"],
        prefetch_threshold=config["prefetch"],
        compression_threshold=config["compression"],
        compression_level=6,
    )


# Función para ejecutar pruebas de caché
async def run_cache_test(
    config: Dict[str, Any], iterations: int = 50
) -> Dict[str, Any]:
    """Ejecuta pruebas de caché con la configuración especificada."""
    client = create_client(config)

    # Inicializar cliente
    await client.initialize()

    # Estadísticas
    stats = {
        "config": config,
        "total_requests": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "total_latency_ms": 0,
        "avg_latency_ms": 0,
        "hit_ratio": 0,
        "pattern_invalidations": 0,
        "prefetches": 0,
        "l1_hits": 0,
        "l2_hits": 0,
        "compression_savings_bytes": 0,
    }

    # Ejecutar pruebas
    logger.info(
        f"Iniciando prueba con política {config['policy']}, {iterations} iteraciones"
    )

    start_time = time.time()

    # Fase 1: Llenar caché con solicitudes iniciales
    logger.info("Fase 1: Llenando caché inicial")
    for i in range(len(TEST_PROMPTS)):
        prompt = TEST_PROMPTS[i]
        namespace = f"test_{i % 3}"  # Usar 3 namespaces diferentes

        response = await client.generate_content(
            prompt=prompt,
            temperature=0.7,
            max_output_tokens=50,
            cache_namespace=namespace,
        )

        stats["total_requests"] += 1
        stats["total_latency_ms"] += client.stats["latency_ms"]["content_generation"][
            -1
        ]

    # Fase 2: Pruebas de acceso con patrones
    logger.info("Fase 2: Pruebas de acceso con patrones")
    for i in range(iterations):
        # Seleccionar prompt con distribución sesgada (algunos prompts se acceden más)
        weights = [3, 2, 2, 1, 1, 1, 1, 1, 1, 1]
        idx = random.choices(range(len(TEST_PROMPTS)), weights=weights, k=1)[0]
        prompt = TEST_PROMPTS[idx]
        namespace = f"test_{i % 3}"

        # Cada 10 iteraciones, invalidar un namespace
        if i > 0 and i % 10 == 0:
            logger.info(f"Invalidando namespace test_{i % 3}")
            pattern = f"vertex:generate_content:test_{i % 3}:*"
            await client.cache_manager.invalidate_pattern(pattern)
            stats["pattern_invalidations"] += 1

        # Realizar solicitud
        before = time.time()
        response = await client.generate_content(
            prompt=prompt,
            temperature=0.7,
            max_output_tokens=50,
            cache_namespace=namespace,
        )
        latency_ms = (time.time() - before) * 1000

        # Actualizar estadísticas
        stats["total_requests"] += 1
        stats["total_latency_ms"] += latency_ms

        # Verificar si fue hit o miss de caché
        if latency_ms < 10:  # Asumimos que menos de 10ms es un hit de caché
            stats["cache_hits"] += 1
        else:
            stats["cache_misses"] += 1

    # Obtener estadísticas finales del caché
    cache_stats = await client.cache_manager.get_stats()

    # Actualizar estadísticas con datos del caché
    stats["l1_hits"] = cache_stats.get("l1_hits", 0)
    stats["l2_hits"] = cache_stats.get("l2_hits", 0)
    stats["prefetches"] = cache_stats.get("prefetches", 0)
    stats["compression_savings_bytes"] = cache_stats.get("compression_savings_bytes", 0)

    # Calcular métricas finales
    total_time = time.time() - start_time
    stats["total_time_seconds"] = total_time
    stats["requests_per_second"] = stats["total_requests"] / total_time
    stats["hit_ratio"] = (
        stats["cache_hits"] / stats["total_requests"]
        if stats["total_requests"] > 0
        else 0
    )
    stats["avg_latency_ms"] = (
        stats["total_latency_ms"] / stats["total_requests"]
        if stats["total_requests"] > 0
        else 0
    )

    # Cerrar cliente
    await client.close()

    return stats


# Función para comparar resultados
def compare_results(results: List[Dict[str, Any]]) -> None:
    """Compara los resultados de diferentes configuraciones."""
    print("\n" + "=" * 80)
    print("COMPARACIÓN DE POLÍTICAS DE CACHÉ")
    print("=" * 80)

    # Tabla de resultados
    headers = [
        "Política",
        "Hit Ratio",
        "Latencia Prom.",
        "L1 Hits",
        "L2 Hits",
        "Prefetches",
        "Ahorro Compresión",
    ]
    print(
        f"{headers[0]:<10} {headers[1]:<10} {headers[2]:<15} {headers[3]:<10} {headers[4]:<10} {headers[5]:<10} {headers[6]:<20}"
    )
    print("-" * 80)

    for result in results:
        config = result["config"]
        print(
            f"{config['policy']:<10} {result['hit_ratio']:.2%} {result['avg_latency_ms']:.2f}ms {result['l1_hits']:<10} {result['l2_hits']:<10} {result['prefetches']:<10} {result['compression_savings_bytes']/1024:.2f} KB"
        )

    # Encontrar la mejor configuración
    best_hit_ratio = max(results, key=lambda x: x["hit_ratio"])
    best_latency = min(results, key=lambda x: x["avg_latency_ms"])

    print(
        "\nMejor Hit Ratio: "
        + best_hit_ratio["config"]["policy"]
        + f" ({best_hit_ratio['hit_ratio']:.2%})"
    )
    print(
        "Mejor Latencia: "
        + best_latency["config"]["policy"]
        + f" ({best_latency['avg_latency_ms']:.2f}ms)"
    )

    # Recomendación
    print("\nRecomendación para este patrón de acceso:")
    if best_hit_ratio["config"]["policy"] == best_latency["config"]["policy"]:
        print(
            f"Usar política {best_hit_ratio['config']['policy']} que ofrece el mejor rendimiento general"
        )
    else:
        print(f"Para priorizar hit ratio: {best_hit_ratio['config']['policy']}")
        print(f"Para priorizar latencia: {best_latency['config']['policy']}")


# Función principal
async def main():
    """Función principal."""
    logger.info("Iniciando pruebas de caché avanzado para Vertex AI")

    results = []

    # Ejecutar pruebas para cada configuración
    for config in TEST_CONFIGS:
        logger.info(f"Probando política: {config['policy']}")
        result = await run_cache_test(config, iterations=50)
        results.append(result)

        # Mostrar resultados individuales
        logger.info(f"Resultados para {config['policy']}:")
        logger.info(f"  Hit Ratio: {result['hit_ratio']:.2%}")
        logger.info(f"  Latencia Promedio: {result['avg_latency_ms']:.2f}ms")
        logger.info(f"  L1 Hits: {result['l1_hits']}")
        logger.info(f"  L2 Hits: {result['l2_hits']}")
        logger.info(f"  Prefetches: {result['prefetches']}")
        logger.info(
            f"  Ahorro por Compresión: {result['compression_savings_bytes']/1024:.2f} KB"
        )

        # Esperar un poco entre pruebas
        await asyncio.sleep(1)

    # Comparar resultados
    compare_results(results)

    logger.info("Pruebas completadas")


if __name__ == "__main__":
    asyncio.run(main())

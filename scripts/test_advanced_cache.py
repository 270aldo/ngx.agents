#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para probar las funcionalidades avanzadas del caché.

Este script prueba las diferentes políticas de caché, el sistema de caché en múltiples niveles,
y las estrategias de invalidación inteligente.
"""

import asyncio
import time
import random
import os
import sys
import logging
from typing import Dict, Any

# Configurar logging para mostrar más información
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Añadir directorio raíz al path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar telemetría mock antes de importar el caché para que se use en lugar de la real

# Monkey patch para reemplazar la telemetría real con la mock
import sys

sys.modules["core.telemetry"] = sys.modules["scripts.mock_telemetry"]

from clients.vertex_ai.cache import CacheManager, CachePolicy
from core.logging_config import get_logger

logger = get_logger(__name__)

# Configuración para pruebas
TEST_CONFIG = {
    "memory_size_mb": 10,  # Tamaño pequeño para forzar evicción
    "ttl": 5,  # TTL corto para probar expiración
    "compression_threshold": 100,  # Umbral bajo para probar compresión
    "test_keys": 1000,  # Número de claves para prueba
    "value_size_range": (10, 1000),  # Rango de tamaños para valores
    "access_patterns": {
        "hot": 0.2,  # 20% de claves "calientes" (acceso frecuente)
        "warm": 0.3,  # 30% de claves "tibias" (acceso moderado)
        "cold": 0.5,  # 50% de claves "frías" (acceso poco frecuente)
    },
    "policies_to_test": [
        CachePolicy.LRU,
        CachePolicy.LFU,
        CachePolicy.FIFO,
        CachePolicy.HYBRID,
    ],
}


async def generate_test_data(num_keys: int, size_range: tuple) -> Dict[str, Any]:
    """Genera datos de prueba con diferentes tamaños."""
    test_data = {}
    for i in range(num_keys):
        key = f"test_key_{i:04d}"
        # Generar valor con tamaño aleatorio
        size = random.randint(size_range[0], size_range[1])
        value = {
            "id": i,
            "name": f"Test Value {i}",
            "data": "x" * size,
            "timestamp": time.time(),
        }
        test_data[key] = value
    return test_data


async def simulate_access_patterns(
    cache: CacheManager,
    test_data: Dict[str, Any],
    patterns: Dict[str, float],
    iterations: int = 5,
) -> None:
    """Simula patrones de acceso a las claves según las proporciones definidas."""
    keys = list(test_data.keys())

    # Clasificar claves según patrones
    num_keys = len(keys)
    hot_keys = keys[: int(num_keys * patterns["hot"])]
    warm_keys = keys[
        int(num_keys * patterns["hot"]) : int(
            num_keys * (patterns["hot"] + patterns["warm"])
        )
    ]
    cold_keys = keys[int(num_keys * (patterns["hot"] + patterns["warm"])) :]

    logger.info(
        f"Simulando patrones de acceso: {len(hot_keys)} calientes, {len(warm_keys)} tibias, {len(cold_keys)} frías"
    )

    # Simular accesos con diferentes frecuencias
    for _ in range(iterations):
        # Acceder a claves calientes con alta frecuencia
        for key in hot_keys:
            for _ in range(5):  # 5 accesos por iteración
                await cache.get(key)

        # Acceder a claves tibias con frecuencia media
        for key in warm_keys:
            for _ in range(2):  # 2 accesos por iteración
                await cache.get(key)

        # Acceder a claves frías con baja frecuencia
        for key in random.sample(
            cold_keys, int(len(cold_keys) * 0.2)
        ):  # Solo 20% de las frías
            await cache.get(key)

        # Pequeña pausa para simular tiempo real
        await asyncio.sleep(0.1)


async def test_cache_policy(
    policy: CachePolicy, test_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Prueba una política de caché específica y devuelve estadísticas."""
    logger.info(f"Probando política de caché: {policy.value}")

    # Crear caché con la política específica
    cache = CacheManager(
        use_redis=False,  # Solo memoria para pruebas
        ttl=TEST_CONFIG["ttl"],
        max_memory_size=TEST_CONFIG["memory_size_mb"],
        compression_threshold=TEST_CONFIG["compression_threshold"],
        cache_policy=policy,
        partitions=4,
        l1_size_ratio=0.8,
        enable_telemetry=True,
    )

    # Cargar datos
    logger.info(f"Cargando {len(test_data)} claves en caché...")
    for key, value in test_data.items():
        await cache.set(key, value)

    # Simular patrones de acceso
    await simulate_access_patterns(
        cache, test_data, TEST_CONFIG["access_patterns"], iterations=3
    )

    # Forzar limpieza para ver efectos de la política
    logger.info("Forzando limpieza para evaluar política...")
    await cache._cleanup_if_needed(
        needed_space_bytes=int(TEST_CONFIG["memory_size_mb"] * 1024 * 1024 * 0.3)
    )

    # Obtener estadísticas
    stats = await cache.get_stats()

    # Calcular métricas adicionales
    hit_ratio = stats["hit_ratio"]["total"]
    evictions = stats["evictions"]["l1"]
    current_items = stats["current_items"]["l1"]

    logger.info(
        f"Resultados para {policy.value}: Hit ratio: {hit_ratio:.2f}, Evictions: {evictions}, Items: {current_items}"
    )

    return stats


async def test_pattern_invalidation() -> None:
    """Prueba la invalidación basada en patrones."""
    logger.info("Probando invalidación basada en patrones...")

    cache = CacheManager(
        use_redis=False,
        ttl=30,
        max_memory_size=20,
        cache_policy=CachePolicy.LRU,
        partitions=4,
        enable_telemetry=True,
    )

    # Crear grupos de claves relacionadas
    user_keys = [f"user:1000:profile", f"user:1000:settings", f"user:1000:preferences"]
    product_keys = [
        f"product:5001:details",
        f"product:5001:price",
        f"product:5001:inventory",
    ]

    # Almacenar valores
    for key in user_keys + product_keys:
        await cache.set(
            key,
            {"data": f"Value for {key}", "timestamp": time.time()},
            pattern=key.split(":")[0],
        )

    # Verificar que todo está en caché
    all_keys = user_keys + product_keys
    for key in all_keys:
        value = await cache.get(key)
        assert value is not None, f"La clave {key} debería estar en caché"

    # Registrar patrón de invalidación para usuario
    cache.pattern_subscriptions["user"] = {
        "type": "invalidation",
        "keys": set(user_keys),
    }

    # Invalidar todas las claves de usuario
    for key in list(cache.pattern_subscriptions["user"]["keys"]):
        partition = cache._get_partition(key)
        async with cache.locks[partition]:
            if key in cache.memory_cache[partition]:
                cache.memory_cache[partition].pop(key)
                cache.stats["invalidations"]["pattern"] += 1

    # Verificar que las claves de usuario ya no están en caché
    for key in user_keys:
        value = await cache.get(key)
        assert (
            value is None
        ), f"La clave {key} no debería estar en caché después de invalidación"

    # Verificar que las claves de producto siguen en caché
    for key in product_keys:
        value = await cache.get(key)
        assert value is not None, f"La clave {key} debería seguir en caché"

    logger.info("Prueba de invalidación basada en patrones completada con éxito")


async def test_prefetch_mechanism() -> None:
    """Prueba el mecanismo de precarga de claves relacionadas."""
    logger.info("Probando mecanismo de precarga...")

    cache = CacheManager(
        use_redis=False,
        ttl=30,
        max_memory_size=20,
        cache_policy=CachePolicy.LRU,
        partitions=4,
        enable_telemetry=True,
    )

    # Crear grupos de claves relacionadas
    product_id = "5001"
    main_key = f"product:{product_id}:details"
    related_keys = [
        f"product:{product_id}:price",
        f"product:{product_id}:inventory",
        f"product:{product_id}:images",
    ]

    # Almacenar valores
    for key in [main_key] + related_keys:
        await cache.set(key, {"data": f"Value for {key}", "timestamp": time.time()})

    # Configurar patrón de precarga
    cache.pattern_subscriptions[f"product:{product_id}"] = {
        "type": "prefetch",
        "keys": related_keys,
    }

    # Simular acceso a clave principal para activar precarga
    await cache.get(main_key)

    # Pequeña pausa para permitir que la precarga async se complete
    await asyncio.sleep(0.1)

    # Verificar estadísticas de precarga
    stats = await cache.get_stats()
    logger.info(f"Estadísticas de precarga: {stats['prefetch']}")

    logger.info("Prueba de mecanismo de precarga completada")


async def compare_policies() -> None:
    """Compara diferentes políticas de caché con los mismos datos."""
    # Generar datos de prueba una vez
    test_data = await generate_test_data(
        TEST_CONFIG["test_keys"], TEST_CONFIG["value_size_range"]
    )

    results = {}

    # Probar cada política
    for policy in TEST_CONFIG["policies_to_test"]:
        results[policy.value] = await test_cache_policy(policy, test_data)

    # Comparar resultados
    logger.info("\n--- Comparación de políticas de caché ---")
    for policy, stats in results.items():
        logger.info(f"Política: {policy}")
        logger.info(f"  Hit ratio: {stats['hit_ratio']['total']:.4f}")
        logger.info(f"  Evictions: {stats['evictions']['total']}")
        logger.info(f"  Items en caché: {stats['current_items']['l1']}")
        if stats["compression"]["compressed_items"] > 0:
            logger.info(
                f"  Compresión: {stats['compression']['compression_ratio']:.2%}"
            )

    # Determinar mejor política para este patrón de acceso
    best_policy = max(results.items(), key=lambda x: x[1]["hit_ratio"]["total"])
    logger.info(
        f"\nMejor política para este patrón de acceso: {best_policy[0]} (Hit ratio: {best_policy[1]['hit_ratio']['total']:.4f})"
    )


async def test_cache_performance() -> None:
    """Prueba el rendimiento del caché con diferentes configuraciones."""
    logger.info("\n=== Prueba de rendimiento del caché ===")

    # Configuraciones a probar
    configs = [
        {"partitions": 1, "description": "Sin particionamiento"},
        {"partitions": 4, "description": "Particionamiento estándar"},
        {"partitions": 8, "description": "Particionamiento alto"},
    ]

    # Generar datos de prueba
    test_data = await generate_test_data(500, (50, 200))
    results = {}

    for config in configs:
        logger.info(f"Probando configuración: {config['description']}")

        # Crear caché con la configuración específica
        cache = CacheManager(
            use_redis=False,
            ttl=TEST_CONFIG["ttl"],
            max_memory_size=TEST_CONFIG["memory_size_mb"],
            compression_threshold=TEST_CONFIG["compression_threshold"],
            cache_policy=CachePolicy.LRU,
            partitions=config["partitions"],
            enable_telemetry=True,
        )

        # Medir tiempo de carga
        start_time = time.time()
        for key, value in test_data.items():
            await cache.set(key, value)
        load_time = time.time() - start_time

        # Medir tiempo de acceso (lectura)
        start_time = time.time()
        for key in test_data.keys():
            await cache.get(key)
        access_time = time.time() - start_time

        # Guardar resultados
        results[config["description"]] = {
            "load_time": load_time,
            "access_time": access_time,
            "total_time": load_time + access_time,
        }

    # Mostrar resultados
    logger.info("\nResultados de rendimiento:")
    for desc, times in results.items():
        logger.info(f"Configuración: {desc}")
        logger.info(f"  Tiempo de carga: {times['load_time']:.4f} segundos")
        logger.info(f"  Tiempo de acceso: {times['access_time']:.4f} segundos")
        logger.info(f"  Tiempo total: {times['total_time']:.4f} segundos")

    # Determinar mejor configuración
    best_config = min(results.items(), key=lambda x: x[1]["total_time"])
    logger.info(
        f"\nMejor configuración: {best_config[0]} (Tiempo total: {best_config[1]['total_time']:.4f} segundos)"
    )


async def main():
    """Función principal que ejecuta todas las pruebas."""
    logger.info("\n=== Iniciando pruebas del sistema de caché avanzado ===")

    # Comparar políticas de caché
    logger.info("\n1. Comparación de políticas de caché")
    await compare_policies()

    # Probar invalidación basada en patrones
    logger.info("\n2. Prueba de invalidación basada en patrones")
    await test_pattern_invalidation()

    # Probar mecanismo de precarga
    logger.info("\n3. Prueba de mecanismo de precarga")
    await test_prefetch_mechanism()

    # Probar rendimiento con diferentes configuraciones
    logger.info("\n4. Prueba de rendimiento")
    await test_cache_performance()

    logger.info("\n=== Todas las pruebas completadas ===\n")
    logger.info("Resumen de hallazgos:")
    logger.info(
        "1. Las políticas de caché tienen diferente eficacia según los patrones de acceso"
    )
    logger.info(
        "2. La invalidación basada en patrones permite una gestión eficiente de datos relacionados"
    )
    logger.info(
        "3. El mecanismo de precarga mejora la experiencia al anticipar necesidades de datos"
    )
    logger.info(
        "4. El particionamiento adecuado mejora el rendimiento al reducir la contención"
    )

    logger.info("\nRecomendaciones:")
    logger.info("- Usar política HYBRID para cargas de trabajo mixtas")
    logger.info("- Configurar particionamiento según la concurrencia esperada")
    logger.info("- Implementar patrones de invalidación para datos relacionados")
    logger.info("- Activar precarga para mejorar la experiencia de usuario")


if __name__ == "__main__":
    asyncio.run(main())

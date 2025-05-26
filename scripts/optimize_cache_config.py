#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para optimizar la configuración del sistema de caché del cliente Vertex AI.

Este script ejecuta pruebas de rendimiento con diferentes configuraciones de caché
y recomienda la configuración óptima según los resultados.
"""

import asyncio
import time
import random
import sys
import os
import json
import argparse
from typing import Dict, Any
import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate

# Añadir directorio raíz al path para importaciones
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Parchear módulo de telemetría para evitar dependencias faltantes
sys.modules["core.telemetry"] = __import__("scripts.mock_telemetry", fromlist=["*"])

# Importar cliente Vertex AI después del parche
from clients.vertex_ai.client import VertexAIClient


# Mock para monitoreo
class MockMonitoring:
    @staticmethod
    async def initialize_monitoring():
        logger.info("Mock de monitoreo inicializado")
        return True

    @staticmethod
    async def get_monitoring_status():
        return {
            "health_metrics": {
                "hit_ratio": 0.6,
                "latency_ms": 50,
                "memory_usage": {"usage_ratio": 0.3},
                "error_rate": 0.01,
            },
            "recent_alerts": [],
        }


# Reemplazar funciones de monitoreo con mocks
initialize_monitoring = MockMonitoring.initialize_monitoring
get_monitoring_status = MockMonitoring.get_monitoring_status

# Configuración de logging
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("optimize_cache_config")

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
    "¿Cuáles son los principales componentes de una computadora?",
    "Explica el ciclo del agua",
    "¿Qué es el efecto invernadero?",
    "Describe el proceso de la fotosíntesis",
    "¿Cómo funciona una vacuna?",
    "Explica la diferencia entre virus y bacterias",
    "¿Qué es la programación orientada a objetos?",
    "Describe el sistema solar",
    "¿Qué es la inteligencia emocional?",
    "Explica cómo funciona Internet",
]

# Configuraciones a probar
DEFAULT_CONFIGS = [
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

# Patrones de acceso a probar
ACCESS_PATTERNS = {
    "uniform": lambda prompts: random.choice(prompts),
    "zipf": lambda prompts: prompts[
        min(int(np.random.zipf(1.5)) % len(prompts), len(prompts) - 1)
    ],
    "repeated": lambda prompts: prompts[random.randint(0, min(3, len(prompts) - 1))],
    "sequential": lambda prompts, i=None: prompts[
        i % len(prompts) if i is not None else 0
    ],
}


class CacheOptimizer:
    """Optimizador de configuración de caché."""

    def __init__(self, configs=None, prompts=None, iterations=50, warm_up=10):
        """
        Inicializa el optimizador.

        Args:
            configs: Lista de configuraciones a probar
            prompts: Lista de prompts para pruebas
            iterations: Número de iteraciones por prueba
            warm_up: Número de iteraciones de calentamiento
        """
        self.configs = configs or DEFAULT_CONFIGS
        self.prompts = prompts or TEST_PROMPTS
        self.iterations = iterations
        self.warm_up = warm_up
        self.results = []

    async def run_tests(self, access_pattern="uniform"):
        """
        Ejecuta pruebas con todas las configuraciones.

        Args:
            access_pattern: Patrón de acceso a usar (uniform, zipf, repeated, sequential)

        Returns:
            List[Dict[str, Any]]: Resultados de las pruebas
        """
        logger.info(f"Iniciando pruebas con patrón de acceso: {access_pattern}")

        pattern_func = ACCESS_PATTERNS.get(access_pattern, ACCESS_PATTERNS["uniform"])

        self.results = []
        for config in self.configs:
            logger.info(f"Probando configuración: {config}")
            result = await self.test_config(config, pattern_func)
            self.results.append(result)

            # Esperar un poco entre pruebas
            await asyncio.sleep(1)

        return self.results

    async def test_config(self, config: Dict[str, Any], pattern_func):
        """
        Prueba una configuración específica.

        Args:
            config: Configuración a probar
            pattern_func: Función para seleccionar prompts según patrón

        Returns:
            Dict[str, Any]: Resultados de la prueba
        """
        # Crear cliente con la configuración a probar
        client = VertexAIClient(
            use_redis_cache=True,
            cache_ttl=3600,
            max_cache_size=1000,
            cache_policy=config["policy"],
            cache_partitions=config["partitions"],
            l1_size_ratio=config["l1_ratio"],
            prefetch_threshold=config["prefetch"],
            compression_threshold=config["compression"],
            compression_level=4,
        )

        try:
            # Inicializar cliente y monitoreo
            await client.initialize()
            await initialize_monitoring()
            logger.info(f"Probando configuración: {config}")

            # Variables para estadísticas
            latencies = []
            hits = 0
            misses = 0
            start_time = time.time()

            # Fase de calentamiento
            logger.info(f"Fase de calentamiento: {self.warm_up} iteraciones")
            for i in range(self.warm_up):
                prompt = (
                    pattern_func(self.prompts, i)
                    if pattern_func.__code__.co_argcount > 1
                    else pattern_func(self.prompts)
                )
                await client.generate_content(
                    prompt=prompt, temperature=0.7, max_output_tokens=50
                )

            # No podemos usar reset_stats porque no existe, pero podemos ignorar las estadísticas del calentamiento
            # y solo contar las de la fase de prueba

            # Fase de prueba
            logger.info(f"Fase de prueba: {self.iterations} iteraciones")
            for i in range(self.iterations):
                prompt = (
                    pattern_func(self.prompts, i)
                    if pattern_func.__code__.co_argcount > 1
                    else pattern_func(self.prompts)
                )

                # Medir latencia
                start = time.time()
                response = await client.generate_content(
                    prompt=prompt, temperature=0.7, max_output_tokens=50
                )
                end = time.time()

                latency = (end - start) * 1000  # ms
                latencies.append(latency)

                # Estimar si fue hit o miss basado en la latencia
                if latency < 10:  # Asumimos que menos de 10ms es un hit de caché
                    hits += 1
                else:
                    misses += 1

                # Mostrar progreso
                if (i + 1) % 10 == 0:
                    logger.info(f"Progreso: {i + 1}/{self.iterations} iteraciones")

            # Obtener estadísticas
            end_time = time.time()
            monitoring_status = await get_monitoring_status()

            # Calcular métricas derivadas
            total_requests = hits + misses
            hit_ratio = hits / total_requests if total_requests > 0 else 0
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            throughput = self.iterations / (end_time - start_time)

            # Extraer métricas de monitoreo
            health_metrics = monitoring_status.get("health_metrics", {})
            memory_usage = health_metrics.get("memory_usage", {}).get("usage_ratio", 0)
            error_rate = health_metrics.get("error_rate", 0)

            # Resultados
            result = {
                "config": config,
                "hits": hits,
                "misses": misses,
                "hit_ratio": hit_ratio,
                "avg_latency_ms": avg_latency,
                "min_latency_ms": min(latencies) if latencies else 0,
                "max_latency_ms": max(latencies) if latencies else 0,
                "latencies": latencies,
                "requests_per_second": throughput,
                "total_time_seconds": end_time - start_time,
                "monitoring": {
                    "memory_usage": memory_usage,
                    "error_rate": error_rate,
                    "alerts": monitoring_status.get("recent_alerts", []),
                },
            }

            logger.info(
                f"Resultados para {config['policy']}: Hit ratio={hit_ratio:.2%}, Latencia={avg_latency:.2f}ms, Memoria={memory_usage:.2%}"
            )
            return result

        except Exception as e:
            logger.error(f"Error al probar configuración {config}: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return {
                "config": config,
                "error": str(e),
                "hit_ratio": 0,
                "avg_latency_ms": 0,
                "requests_per_second": 0,
            }
        finally:
            # Cerrar cliente
            await client.close()
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

    def print_results(self):
        """Imprime los resultados de las pruebas en formato tabular."""
        if not self.results:
            logger.warning("No hay resultados para imprimir")
            return

        # Ordenar resultados por hit ratio (descendente)
        sorted_results = sorted(
            self.results, key=lambda r: r.get("hit_ratio", 0), reverse=True
        )

        # Preparar tabla de resultados
        headers = [
            "Política",
            "Particiones",
            "Ratio L1",
            "Prefetch",
            "Compresión",
            "Hit Ratio",
            "Latencia (ms)",
            "Throughput",
            "Hits",
            "Misses",
            "Memoria",
        ]

        rows = []
        for result in sorted_results:
            if "error" in result and not result.get("hit_ratio"):
                # Mostrar error para configuraciones fallidas
                row = [
                    result["config"]["policy"],
                    result["config"]["partitions"],
                    result["config"]["l1_ratio"],
                    result["config"]["prefetch"],
                    result["config"]["compression"],
                    "ERROR",
                    "ERROR",
                    "ERROR",
                    "ERROR",
                    "ERROR",
                    "ERROR",
                ]
            else:
                # Mostrar métricas para configuraciones exitosas
                row = [
                    result["config"]["policy"],
                    result["config"]["partitions"],
                    result["config"]["l1_ratio"],
                    result["config"]["prefetch"],
                    result["config"]["compression"],
                    f"{result.get('hit_ratio', 0):.2%}",
                    f"{result.get('avg_latency_ms', 0):.2f}",
                    f"{result.get('requests_per_second', 0):.2f}",
                    result.get("hits", 0),
                    result.get("misses", 0),
                    f"{result.get('monitoring', {}).get('memory_usage', 0):.2%}",
                ]
            rows.append(row)

        # Imprimir tabla
        print("\nResultados de optimización de caché:")
        print(tabulate(rows, headers=headers, tablefmt="grid"))

        # Mostrar mejor configuración
        if sorted_results and "error" not in sorted_results[0]:
            best_config = sorted_results[0]["config"]
            print("\nMejor configuración:")
            print(f"Política: {best_config['policy']}")
            print(f"Particiones: {best_config['partitions']}")
            print(f"Ratio L1: {best_config['l1_ratio']}")
            print(f"Prefetch: {best_config['prefetch']}")
            print(f"Compresión: {best_config['compression']} bytes")
            print(f"Hit Ratio: {sorted_results[0].get('hit_ratio', 0):.2%}")
            print(f"Latencia: {sorted_results[0].get('avg_latency_ms', 0):.2f} ms")

            # Puntuación ponderada (ajustar pesos según prioridades)
            score = hit_ratio_norm * 0.5 + latency_norm * 0.3 + throughput_norm * 0.2
            weighted_scores.append((result["config"]["policy"], score))

        # Ordenar por puntuación
        weighted_scores.sort(key=lambda x: x[1], reverse=True)

        print(
            f"Configuración recomendada: {weighted_scores[0][0]} (puntuación: {weighted_scores[0][1]:.2f})"
        )

        # Configuración específica recomendada
        best_config = next(
            r["config"]
            for r in self.results
            if r["config"]["policy"] == weighted_scores[0][0]
        )
        print("\nConfiguración óptima para .env:")
        print(f"VERTEX_CACHE_POLICY={best_config['policy']}")
        print(f"VERTEX_CACHE_PARTITIONS={best_config['partitions']}")
        print(f"VERTEX_L1_SIZE_RATIO={best_config['l1_ratio']}")
        print(f"VERTEX_PREFETCH_THRESHOLD={best_config['prefetch']}")
        print(f"VERTEX_COMPRESSION_THRESHOLD={best_config['compression']}")

    def plot_results(self):
        """Genera gráficos de los resultados."""
        if not self.results or not plt:
            logger.warning("No se pueden generar gráficos")
            return

        # Preparar datos
        policies = [r["config"]["policy"] for r in self.results]
        hit_ratios = [r["hit_ratio"] * 100 for r in self.results]
        latencies = [r["avg_latency_ms"] for r in self.results]
        throughputs = [r["requests_per_second"] for r in self.results]

        # Crear figura con subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 15))

        # Gráfico de hit ratio
        ax1.bar(policies, hit_ratios, color="skyblue")
        ax1.set_title("Hit Ratio por Política de Caché")
        ax1.set_ylabel("Hit Ratio (%)")
        ax1.set_ylim(0, 100)

        # Gráfico de latencia
        ax2.bar(policies, latencies, color="salmon")
        ax2.set_title("Latencia Promedio por Política de Caché")
        ax2.set_ylabel("Latencia (ms)")

        # Gráfico de throughput
        ax3.bar(policies, throughputs, color="lightgreen")
        ax3.set_title("Throughput por Política de Caché")
        ax3.set_ylabel("Solicitudes por segundo")

        plt.tight_layout()

        # Guardar gráfico
        plt.savefig("cache_optimization_results.png")
        logger.info("Gráfico guardado como cache_optimization_results.png")

        # Gráfico de distribución de latencias
        plt.figure(figsize=(10, 6))

        for result in self.results:
            latencies = result["latencies"]
            if latencies:
                plt.hist(
                    latencies, alpha=0.5, label=result["config"]["policy"], bins=20
                )

        plt.title("Distribución de Latencias por Política")
        plt.xlabel("Latencia (ms)")
        plt.ylabel("Frecuencia")
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Guardar gráfico de distribución
        plt.savefig("cache_latency_distribution.png")
        logger.info(
            "Gráfico de distribución guardado como cache_latency_distribution.png"
        )

    def export_results(self, filename="cache_optimization_results.json"):
        """
        Exporta los resultados a un archivo JSON.

        Args:
            filename: Nombre del archivo para exportar
        """
        if not self.results:
            logger.warning("No hay resultados para exportar")
            return

        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Resultados exportados a {filename}")


async def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Optimizador de configuración de caché"
    )
    parser.add_argument(
        "--iterations", type=int, default=50, help="Número de iteraciones por prueba"
    )
    parser.add_argument(
        "--warm-up", type=int, default=10, help="Número de iteraciones de calentamiento"
    )
    parser.add_argument(
        "--pattern",
        choices=list(ACCESS_PATTERNS.keys()),
        default="uniform",
        help="Patrón de acceso",
    )
    parser.add_argument(
        "--export", action="store_true", help="Exportar resultados a JSON"
    )
    parser.add_argument("--plot", action="store_true", help="Generar gráficos")

    args = parser.parse_args()

    logger.info("Iniciando optimización de configuración de caché")

    optimizer = CacheOptimizer(iterations=args.iterations, warm_up=args.warm_up)

    await optimizer.run_tests(access_pattern=args.pattern)
    optimizer.print_results()

    if args.export:
        optimizer.export_results()

    if args.plot:
        try:
            optimizer.plot_results()
        except Exception as e:
            logger.error(f"Error al generar gráficos: {e}")

    logger.info("Optimización completada")


if __name__ == "__main__":
    asyncio.run(main())

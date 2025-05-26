#!/usr/bin/env python3
"""
Script para realizar pruebas de carga en el cliente Vertex AI.

Este script permite simular diferentes escenarios de carga para evaluar
el rendimiento y la estabilidad del cliente Vertex AI optimizado.
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import random
import statistics
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("vertex-ai-load-test")

# Intentar importar el cliente Vertex AI
try:
    from clients.vertex_ai import vertex_ai_client
except ImportError:
    logger.error(
        "No se pudo importar el cliente Vertex AI. Asegúrate de ejecutar este script desde el directorio raíz del proyecto."
    )
    sys.exit(1)

# Escenarios de prueba predefinidos
SCENARIOS = {
    "normal": {
        "description": "Carga normal (50 req/s)",
        "requests_per_second": 50,
        "duration_seconds": 60,
        "distribution": "constant",
    },
    "high": {
        "description": "Carga alta (200 req/s)",
        "requests_per_second": 200,
        "duration_seconds": 60,
        "distribution": "constant",
    },
    "spike": {
        "description": "Pico de tráfico (500 req/s durante 1 minuto)",
        "requests_per_second": 500,
        "duration_seconds": 60,
        "distribution": "constant",
    },
    "ramp": {
        "description": "Rampa de carga (10-100 req/s en 5 minutos)",
        "requests_per_second": (10, 100),
        "duration_seconds": 300,
        "distribution": "ramp",
    },
    "sawtooth": {
        "description": "Patrón sierra (50-200-50 req/s, ciclos de 1 minuto)",
        "requests_per_second": (50, 200),
        "duration_seconds": 180,
        "distribution": "sawtooth",
        "cycle_seconds": 60,
    },
}

# Prompts de ejemplo para pruebas
SAMPLE_PROMPTS = [
    "Explica brevemente cómo funciona la fotosíntesis",
    "¿Cuáles son los beneficios de la meditación?",
    "Escribe un párrafo sobre la importancia del ejercicio físico",
    "Describe las principales características de una dieta saludable",
    "¿Qué es el aprendizaje automático y cómo funciona?",
    "Explica la diferencia entre proteínas, carbohidratos y grasas",
    "¿Cuáles son las mejores prácticas para dormir bien?",
    "Describe tres ejercicios efectivos para fortalecer el core",
    "¿Qué alimentos son ricos en vitamina D?",
    "Explica cómo funciona el sistema inmunológico",
]


class LoadTestResult:
    """Clase para almacenar y analizar resultados de pruebas de carga."""

    def __init__(self):
        self.latencies = []
        self.errors = []
        self.requests_sent = 0
        self.requests_successful = 0
        self.tokens_used = 0
        self.start_time = time.time()
        self.end_time = None
        self.cache_hits = 0
        self.cache_misses = 0

    def add_result(
        self,
        latency: float,
        success: bool,
        error: Optional[str] = None,
        tokens: int = 0,
        cache_hit: bool = False,
    ):
        """Añade el resultado de una solicitud."""
        self.latencies.append(latency)
        self.requests_sent += 1

        if success:
            self.requests_successful += 1
            self.tokens_used += tokens
            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
        else:
            self.errors.append(error or "Unknown error")

    def complete(self):
        """Marca la prueba como completada."""
        self.end_time = time.time()

    def get_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen de los resultados de la prueba."""
        if not self.latencies:
            return {"error": "No se registraron resultados"}

        duration = (self.end_time or time.time()) - self.start_time

        return {
            "total_requests": self.requests_sent,
            "successful_requests": self.requests_successful,
            "error_rate": (
                (self.requests_sent - self.requests_successful) / self.requests_sent
                if self.requests_sent > 0
                else 0
            ),
            "duration_seconds": duration,
            "requests_per_second": self.requests_sent / duration if duration > 0 else 0,
            "tokens_used": self.tokens_used,
            "tokens_per_second": self.tokens_used / duration if duration > 0 else 0,
            "latency_ms": {
                "min": min(self.latencies) if self.latencies else 0,
                "max": max(self.latencies) if self.latencies else 0,
                "avg": statistics.mean(self.latencies) if self.latencies else 0,
                "p50": statistics.median(self.latencies) if self.latencies else 0,
                "p95": (
                    statistics.quantiles(self.latencies, n=20)[19]
                    if len(self.latencies) >= 20
                    else max(self.latencies) if self.latencies else 0
                ),
                "p99": (
                    statistics.quantiles(self.latencies, n=100)[99]
                    if len(self.latencies) >= 100
                    else max(self.latencies) if self.latencies else 0
                ),
            },
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_ratio": (
                    self.cache_hits / (self.cache_hits + self.cache_misses)
                    if (self.cache_hits + self.cache_misses) > 0
                    else 0
                ),
            },
            "errors": self.errors[
                :10
            ],  # Limitar a 10 errores para no sobrecargar el resumen
        }

    def save_to_csv(self, filename: str):
        """Guarda los resultados detallados en un archivo CSV."""
        try:
            with open(filename, "w", newline="") as csvfile:
                fieldnames = [
                    "timestamp",
                    "latency_ms",
                    "success",
                    "tokens",
                    "cache_hit",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                # Escribir cada resultado
                for i, latency in enumerate(self.latencies):
                    success = i < self.requests_successful
                    writer.writerow(
                        {
                            "timestamp": self.start_time + (i * 0.1),  # Aproximación
                            "latency_ms": latency,
                            "success": success,
                            "tokens": 0,  # No tenemos esta información por solicitud individual
                            "cache_hit": False,  # No tenemos esta información por solicitud individual
                        }
                    )

                logger.info(f"Resultados guardados en {filename}")
        except Exception as e:
            logger.error(f"Error al guardar resultados en CSV: {e}")


async def generate_load(
    scenario: Dict[str, Any],
    result: LoadTestResult,
    custom_prompts: Optional[List[str]] = None,
) -> None:
    """
    Genera carga según el escenario especificado.

    Args:
        scenario: Configuración del escenario de carga
        result: Objeto para almacenar resultados
        custom_prompts: Lista de prompts personalizados (opcional)
    """
    # Usar prompts personalizados o los de ejemplo
    prompts = custom_prompts or SAMPLE_PROMPTS

    # Inicializar cliente
    if not vertex_ai_client.is_initialized:
        await vertex_ai_client.initialize()

    # Parámetros del escenario
    duration = scenario.get("duration_seconds", 60)
    distribution = scenario.get("distribution", "constant")

    # Calcular total de solicitudes
    if distribution == "constant":
        rps = scenario.get("requests_per_second", 10)
        total_requests = rps * duration
    elif distribution in ["ramp", "sawtooth"]:
        min_rps, max_rps = scenario.get("requests_per_second", (10, 50))
        avg_rps = (min_rps + max_rps) / 2
        total_requests = int(avg_rps * duration)
    else:
        total_requests = 100  # Valor por defecto

    logger.info(
        f"Iniciando prueba de carga: {scenario.get('description', 'Personalizada')}"
    )
    logger.info(
        f"Duración: {duration} segundos, Total de solicitudes estimadas: {total_requests}"
    )

    # Crear tareas para solicitudes
    tasks = []
    start_time = time.time()

    for i in range(total_requests):
        # Calcular tiempo de espera según distribución
        if distribution == "constant":
            delay = i / scenario.get("requests_per_second", 10)
        elif distribution == "ramp":
            min_rps, max_rps = scenario.get("requests_per_second", (10, 50))
            progress = i / total_requests
            current_rps = min_rps + (max_rps - min_rps) * progress
            delay = i / current_rps
        elif distribution == "sawtooth":
            min_rps, max_rps = scenario.get("requests_per_second", (10, 50))
            cycle_seconds = scenario.get("cycle_seconds", 60)
            cycle_position = (
                i / scenario.get("requests_per_second", 10)
            ) % cycle_seconds
            cycle_progress = cycle_position / cycle_seconds
            if cycle_progress < 0.5:
                # Subiendo
                current_rps = min_rps + (max_rps - min_rps) * (cycle_progress * 2)
            else:
                # Bajando
                current_rps = max_rps - (max_rps - min_rps) * (
                    (cycle_progress - 0.5) * 2
                )
            delay = i / current_rps
        else:
            delay = i / 10  # Valor por defecto

        # Seleccionar prompt aleatorio
        prompt = random.choice(prompts)

        # Crear tarea con retraso
        task = asyncio.create_task(
            send_request_with_delay(prompt, delay, start_time, result)
        )
        tasks.append(task)

    # Esperar a que todas las tareas se completen o hasta que se alcance la duración
    try:
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=duration + 10)
    except asyncio.TimeoutError:
        logger.warning("Algunas tareas no se completaron dentro del tiempo límite")

    # Marcar prueba como completada
    result.complete()

    # Mostrar resumen
    summary = result.get_summary()
    logger.info("Resumen de la prueba de carga:")
    logger.info(f"Solicitudes totales: {summary['total_requests']}")
    logger.info(f"Tasa de errores: {summary['error_rate']:.2%}")
    logger.info(f"Latencia promedio: {summary['latency_ms']['avg']:.2f} ms")
    logger.info(f"Latencia p95: {summary['latency_ms']['p95']:.2f} ms")
    logger.info(f"Tasa de aciertos de caché: {summary['cache']['hit_ratio']:.2%}")


async def send_request_with_delay(
    prompt: str, delay: float, start_time: float, result: LoadTestResult
) -> None:
    """
    Envía una solicitud al cliente Vertex AI con un retraso específico.

    Args:
        prompt: Prompt para generar contenido
        delay: Retraso en segundos desde el inicio
        start_time: Tiempo de inicio de la prueba
        result: Objeto para almacenar resultados
    """
    # Calcular tiempo de espera
    current_time = time.time()
    target_time = start_time + delay
    wait_time = max(0, target_time - current_time)

    if wait_time > 0:
        await asyncio.sleep(wait_time)

    # Enviar solicitud
    request_start = time.time()
    try:
        response = await vertex_ai_client.generate_content(
            prompt=prompt, temperature=0.7, max_output_tokens=100
        )

        request_end = time.time()
        latency = (request_end - request_start) * 1000  # Convertir a ms

        # Verificar si hay error en la respuesta
        if "error" in response:
            result.add_result(latency, False, response["error"])
        else:
            # Determinar si fue un acierto de caché (aproximación)
            cache_hit = (
                latency < 100
            )  # Asumimos que respuestas muy rápidas son de caché
            tokens = response.get("usage", {}).get("total_tokens", 0)
            result.add_result(latency, True, tokens=tokens, cache_hit=cache_hit)

    except Exception as e:
        request_end = time.time()
        latency = (request_end - request_start) * 1000  # Convertir a ms
        result.add_result(latency, False, str(e))


async def main():
    parser = argparse.ArgumentParser(
        description="Realiza pruebas de carga en el cliente Vertex AI"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=list(SCENARIOS.keys()),
        default="normal",
        help="Escenario de prueba predefinido",
    )
    parser.add_argument(
        "--custom", type=str, help="Ruta a un archivo JSON con escenario personalizado"
    )
    parser.add_argument(
        "--prompts",
        type=str,
        help="Ruta a un archivo de texto con prompts personalizados (uno por línea)",
    )
    parser.add_argument("--output", type=str, help="Directorio para guardar resultados")
    args = parser.parse_args()

    # Determinar escenario
    if args.custom and os.path.exists(args.custom):
        try:
            with open(args.custom, "r") as f:
                scenario = json.load(f)
            logger.info(f"Usando escenario personalizado desde {args.custom}")
        except Exception as e:
            logger.error(f"Error al cargar escenario personalizado: {e}")
            scenario = SCENARIOS[args.scenario]
    else:
        scenario = SCENARIOS[args.scenario]

    # Cargar prompts personalizados si se proporcionan
    custom_prompts = None
    if args.prompts and os.path.exists(args.prompts):
        try:
            with open(args.prompts, "r") as f:
                custom_prompts = [line.strip() for line in f if line.strip()]
            logger.info(
                f"Cargados {len(custom_prompts)} prompts personalizados desde {args.prompts}"
            )
        except Exception as e:
            logger.error(f"Error al cargar prompts personalizados: {e}")

    # Crear directorio de salida si es necesario
    output_dir = args.output or "load_test_results"
    os.makedirs(output_dir, exist_ok=True)

    # Generar nombre de archivo para resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scenario_name = args.scenario if not args.custom else "custom"
    results_file = os.path.join(
        output_dir, f"vertex_ai_load_test_{scenario_name}_{timestamp}.csv"
    )
    summary_file = os.path.join(
        output_dir, f"vertex_ai_load_test_{scenario_name}_{timestamp}_summary.json"
    )

    # Inicializar objeto de resultados
    result = LoadTestResult()

    # Ejecutar prueba de carga
    await generate_load(scenario, result, custom_prompts)

    # Guardar resultados
    result.save_to_csv(results_file)

    # Guardar resumen
    try:
        with open(summary_file, "w") as f:
            json.dump(result.get_summary(), f, indent=2)
        logger.info(f"Resumen guardado en {summary_file}")
    except Exception as e:
        logger.error(f"Error al guardar resumen: {e}")

    logger.info("Prueba de carga completada")


if __name__ == "__main__":
    asyncio.run(main())

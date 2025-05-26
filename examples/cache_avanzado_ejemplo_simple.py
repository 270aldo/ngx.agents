#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ejemplo simplificado del sistema de caché avanzado para Vertex AI.

Este script muestra cómo utilizar las características avanzadas del sistema de caché
sin depender de OpenTelemetry, utilizando un mock de telemetría.
"""

import asyncio
import os
import sys
import time
import logging

# Añadir directorio raíz al path para importaciones
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Mock para telemetría
class MockTelemetry:
    def __init__(self):
        self.logger = logging.getLogger("mock_telemetry")

    def start_span(self, name, context=None):
        self.logger.debug(f"[MOCK] Iniciando span: {name}")
        return MockSpan(name)

    def record_event(self, name, attributes=None):
        attrs = attributes or {}
        self.logger.debug(f"[MOCK] Evento registrado: {name}, atributos: {attrs}")


class MockSpan:
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger("mock_span")

    def __enter__(self):
        self.logger.debug(f"[MOCK] Entrando en span: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug(f"[MOCK] Saliendo de span: {self.name}")

    def set_attribute(self, key, value):
        self.logger.debug(f"[MOCK] Atributo establecido: {key}={value}")

    def record_exception(self, exception):
        self.logger.debug(f"[MOCK] Excepción registrada: {exception}")


# Reemplazar el módulo de telemetría real con nuestro mock
sys.modules["core.telemetry"] = type(
    "MockTelemetryModule",
    (),
    {"telemetry": MockTelemetry(), "Telemetry": MockTelemetry},
)

# Ahora podemos importar los módulos que dependen de telemetría
from clients.vertex_ai.client import VertexAIClient

# Configuración de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cache_avanzado_ejemplo_simple")

# Crear una instancia del cliente con configuración personalizada
vertex_ai_client = VertexAIClient(
    use_redis_cache=False,  # Solo caché en memoria para simplificar
    cache_ttl=3600,
    max_cache_size=1000,
    cache_policy="lru",
    cache_partitions=4,
    l1_size_ratio=1.0,
    compression_threshold=1024,
    compression_level=4,
)


# Ejemplo 1: Uso básico con diferentes namespaces
async def ejemplo_basico():
    """Ejemplo básico de uso del caché con diferentes namespaces."""
    logger.info("=== EJEMPLO 1: USO BÁSICO CON NAMESPACES ===")

    # Simulación de respuestas para evitar llamadas reales a Vertex AI
    respuestas_simuladas = {
        "ciencia": "La fotosíntesis es el proceso por el cual las plantas convierten la luz solar en energía química.",
        "historia": "La Revolución Francesa fue un período de cambios políticos y sociales radicales en Francia entre 1789 y 1799.",
        "tecnologia": "La inteligencia artificial es la simulación de procesos de inteligencia humana por sistemas informáticos.",
    }

    # Monkey patch para simular generate_content
    original_generate = vertex_ai_client.generate_content

    async def mock_generate_content(
        prompt, temperature=0.7, max_output_tokens=100, cache_namespace=None
    ):
        # Simular latencia de API
        await asyncio.sleep(0.5)

        # Determinar la categoría basada en el prompt
        for categoria, respuesta in respuestas_simuladas.items():
            if categoria in prompt.lower():
                return {"text": respuesta, "finish_reason": "STOP"}

        return {"text": "Respuesta genérica para: " + prompt, "finish_reason": "STOP"}

    # Reemplazar temporalmente el método
    vertex_ai_client.generate_content = mock_generate_content

    # Generar contenido para diferentes categorías usando namespaces
    categorias = ["ciencia", "historia", "tecnologia"]
    prompts = {
        "ciencia": "Explica brevemente qué es la fotosíntesis",
        "historia": "Describe los eventos principales de la Revolución Francesa",
        "tecnologia": "¿Qué es la inteligencia artificial y cómo funciona?",
    }

    # Primera ejecución (todo será caché miss)
    logger.info("Primera ejecución (caché miss esperado):")
    for categoria in categorias:
        start_time = time.time()
        response = await vertex_ai_client.generate_content(
            prompt=prompts[categoria],
            temperature=0.7,
            max_output_tokens=100,
            cache_namespace=categoria,
        )
        duration = (time.time() - start_time) * 1000

        logger.info(f"Categoría: {categoria}, Duración: {duration:.2f}ms")
        logger.info(f"Respuesta: {response['text'][:50]}...\n")

    # Segunda ejecución (todo debería ser caché hit)
    logger.info("Segunda ejecución (caché hit esperado):")
    for categoria in categorias:
        start_time = time.time()
        response = await vertex_ai_client.generate_content(
            prompt=prompts[categoria],
            temperature=0.7,
            max_output_tokens=100,
            cache_namespace=categoria,
        )
        duration = (time.time() - start_time) * 1000

        logger.info(f"Categoría: {categoria}, Duración: {duration:.2f}ms")

    # Restaurar el método original
    vertex_ai_client.generate_content = original_generate


# Ejemplo 2: Invalidación de caché por patrones
async def ejemplo_invalidacion():
    """Ejemplo de invalidación de caché por patrones."""
    logger.info("\n=== EJEMPLO 2: INVALIDACIÓN DE CACHÉ POR PATRONES ===")

    # Simulación de respuestas para usuarios
    respuestas_usuario = {
        "usuario1": "Recomendación para usuario1: Nuevos dispositivos tecnológicos y eventos deportivos.",
        "usuario2": "Recomendación para usuario2: Destinos de viaje y gadgets tecnológicos.",
        "usuario3": "Recomendación para usuario3: Eventos deportivos locales y consejos de viaje.",
    }

    # Monkey patch para simular generate_content
    original_generate = vertex_ai_client.generate_content

    async def mock_generate_content(
        prompt, temperature=0.7, max_output_tokens=100, cache_namespace=None
    ):
        # Simular latencia de API
        await asyncio.sleep(0.5)

        # Determinar el usuario basado en el prompt
        for usuario, respuesta in respuestas_usuario.items():
            if usuario in prompt:
                return {"text": respuesta, "finish_reason": "STOP"}

        return {"text": "Recomendación genérica", "finish_reason": "STOP"}

    # Reemplazar temporalmente el método
    vertex_ai_client.generate_content = mock_generate_content

    # Generar contenido para usuarios diferentes
    usuarios = ["usuario1", "usuario2", "usuario3"]
    prompt_base = "Genera una recomendación personalizada para el usuario basada en sus intereses: deportes, tecnología, viajes"

    # Primera ejecución para llenar caché
    logger.info("Llenando caché para múltiples usuarios:")
    for usuario in usuarios:
        namespace = f"user_{usuario}"
        await vertex_ai_client.generate_content(
            prompt=f"{prompt_base} (Usuario: {usuario})",
            temperature=0.7,
            max_output_tokens=100,
            cache_namespace=namespace,
        )

    # Verificar que están en caché
    logger.info("Verificando caché hits:")
    for usuario in usuarios:
        namespace = f"user_{usuario}"
        start_time = time.time()
        await vertex_ai_client.generate_content(
            prompt=f"{prompt_base} (Usuario: {usuario})",
            temperature=0.7,
            max_output_tokens=100,
            cache_namespace=namespace,
        )
        duration = (time.time() - start_time) * 1000
        logger.info(f"Usuario: {usuario}, Duración: {duration:.2f}ms")

    # Invalidar caché para un usuario específico
    target_usuario = "usuario2"
    logger.info(f"Invalidando caché para {target_usuario}:")
    pattern = f"vertex:generate_content:user_{target_usuario}:*"
    invalidated = await vertex_ai_client.cache_manager.invalidate_pattern(pattern)
    logger.info(f"Claves invalidadas: {invalidated}")

    # Verificar después de invalidación
    logger.info("Verificando después de invalidación:")
    for usuario in usuarios:
        namespace = f"user_{usuario}"
        start_time = time.time()
        await vertex_ai_client.generate_content(
            prompt=f"{prompt_base} (Usuario: {usuario})",
            temperature=0.7,
            max_output_tokens=100,
            cache_namespace=namespace,
        )
        duration = (time.time() - start_time) * 1000
        expected = "miss" if usuario == target_usuario else "hit"
        logger.info(
            f"Usuario: {usuario}, Duración: {duration:.2f}ms (esperado: {expected})"
        )

    # Restaurar el método original
    vertex_ai_client.generate_content = original_generate


# Ejemplo 3: Estadísticas de caché
async def ejemplo_estadisticas():
    """Ejemplo de estadísticas de caché."""
    logger.info("\n=== EJEMPLO 3: ESTADÍSTICAS DE CACHÉ ===")

    # Obtener estadísticas actuales
    stats = await vertex_ai_client.get_stats()

    # Asegurarse de que stats es un diccionario
    if not isinstance(stats, dict):
        logger.warning(
            f"Las estadísticas no son un diccionario: {type(stats).__name__}"
        )
        stats = {}

    # Obtener el diccionario de caché o un diccionario vacío si no existe
    cache_stats = stats.get("cache", {})
    if not isinstance(cache_stats, dict):
        logger.warning(
            f"Las estadísticas de caché no son un diccionario: {type(cache_stats).__name__}"
        )
        cache_stats = {}

    # Mostrar estadísticas
    logger.info("Estadísticas de caché:")

    # Obtener valores con valores predeterminados seguros
    hit_ratio = cache_stats.get("hit_ratio", 0)
    hits = cache_stats.get("hits", 0)
    misses = cache_stats.get("misses", 0)
    entries = cache_stats.get("entries", 0)

    # Asegurarse de que los valores son del tipo correcto
    try:
        hit_ratio = float(hit_ratio)
        logger.info(f"- Hit ratio: {hit_ratio:.2%}")
    except (TypeError, ValueError):
        logger.info(f"- Hit ratio: {hit_ratio} (no formateado)")

    logger.info(f"- Hits: {hits}")
    logger.info(f"- Misses: {misses}")
    logger.info(f"- Entradas en caché: {entries}")

    # Mostrar estadísticas por política de evicción
    eviction_stats = cache_stats.get("eviction", {})
    if eviction_stats and isinstance(eviction_stats, dict):
        logger.info("Estadísticas de evicción:")
        for policy, count in eviction_stats.items():
            logger.info(f"- {policy}: {count}")

    # Mostrar estadísticas de invalidación por patrón
    pattern_stats = cache_stats.get("pattern_invalidations", {})
    if pattern_stats and isinstance(pattern_stats, dict):
        logger.info("Estadísticas de invalidación por patrón:")
        for pattern, count in pattern_stats.items():
            logger.info(f"- {pattern}: {count}")


# Función principal
async def main():
    """Función principal."""
    logger.info(
        "Iniciando ejemplos de uso del sistema de caché avanzado (versión simplificada)"
    )

    try:
        # Inicializar cliente
        await vertex_ai_client.initialize()

        # Ejecutar ejemplos
        await ejemplo_basico()
        await ejemplo_invalidacion()
        await ejemplo_estadisticas()

        # Mostrar estadísticas finales
        stats = await vertex_ai_client.get_stats()
        logger.info("\n=== ESTADÍSTICAS FINALES ===")

        # Verificar que stats es un diccionario
        if not isinstance(stats, dict):
            logger.warning(
                f"Las estadísticas finales no son un diccionario: {type(stats).__name__}"
            )
            stats = {}

        # Obtener el diccionario de caché o un diccionario vacío si no existe
        cache_stats = stats.get("cache", {})
        if not isinstance(cache_stats, dict):
            logger.warning(
                f"Las estadísticas finales de caché no son un diccionario: {type(cache_stats).__name__}"
            )
            cache_stats = {}

        # Obtener valores con valores predeterminados seguros
        hit_ratio = cache_stats.get("hit_ratio", 0)
        hits = cache_stats.get("hits", 0)
        misses = cache_stats.get("misses", 0)

        # Mostrar estadísticas formateadas correctamente
        try:
            hit_ratio = float(hit_ratio)
            logger.info(f"Hit Ratio: {hit_ratio:.2%}")
        except (TypeError, ValueError):
            logger.info(f"Hit Ratio: {hit_ratio} (no formateado)")

        logger.info(f"Hits: {hits}")
        logger.info(f"Misses: {misses}")

    except Exception as e:
        logger.error(f"Error en ejemplos: {e}")
        import traceback

        logger.error(traceback.format_exc())
    finally:
        # Cerrar cliente
        await vertex_ai_client.close()
        logger.info("Ejemplos completados")


if __name__ == "__main__":
    asyncio.run(main())

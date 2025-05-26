#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ejemplo de uso del sistema de caché avanzado para Vertex AI.

Este script muestra cómo utilizar las características avanzadas del sistema de caché
en una aplicación real, incluyendo la integración con telemetría y monitoreo.
"""

import asyncio
import os
import sys
import time
import logging

# Añadir directorio raíz al path para importaciones
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importaciones del proyecto
from clients.vertex_ai.client import vertex_ai_client
from clients.vertex_ai.monitoring import initialize_monitoring, get_monitoring_status

# Configuración de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cache_avanzado_ejemplo")


# Ejemplo 1: Uso básico con diferentes namespaces
async def ejemplo_basico():
    """Ejemplo básico de uso del caché con diferentes namespaces."""
    logger.info("=== EJEMPLO 1: USO BÁSICO CON NAMESPACES ===")

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

    # Obtener estadísticas de caché
    stats = await vertex_ai_client.get_stats()
    logger.info(f"Estadísticas de caché: {stats['cache']['hit_ratio']:.2%} hit ratio")


# Ejemplo 2: Invalidación de caché por patrones
async def ejemplo_invalidacion():
    """Ejemplo de invalidación de caché por patrones."""
    logger.info("\n=== EJEMPLO 2: INVALIDACIÓN DE CACHÉ POR PATRONES ===")

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


# Ejemplo 3: Monitoreo y alertas
async def ejemplo_monitoreo():
    """Ejemplo de monitoreo y alertas."""
    logger.info("\n=== EJEMPLO 3: MONITOREO Y ALERTAS ===")

    # Inicializar monitoreo
    await initialize_monitoring()
    logger.info("Monitoreo inicializado")

    # Generar algunas solicitudes para tener datos
    logger.info("Generando solicitudes para monitoreo...")
    prompts = [
        "¿Cuál es la capital de Francia?",
        "¿Cuántos planetas hay en el sistema solar?",
        "Explica brevemente la teoría de la relatividad",
    ]

    for prompt in prompts:
        await vertex_ai_client.generate_content(
            prompt=prompt, temperature=0.7, max_output_tokens=50
        )

    # Obtener estado del monitoreo
    logger.info("Obteniendo estado del monitoreo:")
    status = await get_monitoring_status()

    # Mostrar métricas de salud
    health = status["health_metrics"]
    logger.info(f"Hit Ratio: {health['hit_ratio']:.2%}")
    logger.info(f"Latencia: {health['latency_ms']:.2f}ms")
    logger.info(f"Uso de memoria: {health['memory_usage']['usage_ratio']:.2%}")

    # Mostrar alertas recientes
    if status["recent_alerts"]:
        logger.info("Alertas recientes:")
        for alert in status["recent_alerts"]:
            logger.info(f"- {alert['message']} ({alert['timestamp']})")
    else:
        logger.info("No hay alertas recientes")


# Ejemplo 4: Configuración avanzada
async def ejemplo_configuracion():
    """Ejemplo de configuración avanzada del cliente."""
    logger.info("\n=== EJEMPLO 4: CONFIGURACIÓN AVANZADA ===")

    # Crear cliente con configuración personalizada
    from clients.vertex_ai.client import VertexAIClient

    # Cliente optimizado para alto rendimiento
    cliente_alto_rendimiento = VertexAIClient(
        use_redis_cache=False,
        cache_ttl=7200,  # 2 horas
        max_cache_size=2000,  # 2 GB
        cache_policy="lru",
        cache_partitions=8,
        l1_size_ratio=1.0,  # Todo en memoria
        compression_threshold=4096,  # Solo comprimir valores grandes
        compression_level=4,  # Compresión moderada
    )

    # Cliente optimizado para memoria limitada
    cliente_memoria_limitada = VertexAIClient(
        use_redis_cache=True,
        redis_url="redis://localhost:6379/0",  # Ejemplo, ajustar según entorno
        cache_ttl=1800,  # 30 minutos
        max_cache_size=500,  # 500 MB
        cache_policy="lfu",
        cache_partitions=4,
        l1_size_ratio=0.2,  # Solo 20% en memoria
        compression_threshold=512,  # Comprimir valores más pequeños
        compression_level=9,  # Máxima compresión
    )

    # Inicializar clientes
    await cliente_alto_rendimiento.initialize()

    # Ejemplo de uso
    logger.info("Usando cliente optimizado para alto rendimiento:")
    start_time = time.time()
    response = await cliente_alto_rendimiento.generate_content(
        prompt="Explica la diferencia entre caché L1 y L2 en sistemas de computación",
        temperature=0.7,
        max_output_tokens=100,
    )
    duration = (time.time() - start_time) * 1000
    logger.info(f"Duración: {duration:.2f}ms")
    logger.info(f"Respuesta: {response['text'][:50]}...")

    # Cerrar clientes
    await cliente_alto_rendimiento.close()
    logger.info("Cliente cerrado correctamente")


# Función principal
async def main():
    """Función principal."""
    logger.info("Iniciando ejemplos de uso del sistema de caché avanzado")

    try:
        # Ejecutar ejemplos
        await ejemplo_basico()
        await ejemplo_invalidacion()
        await ejemplo_monitoreo()
        await ejemplo_configuracion()

        # Mostrar estadísticas finales
        stats = await vertex_ai_client.get_stats()
        logger.info("\n=== ESTADÍSTICAS FINALES ===")
        logger.info(f"Hit Ratio: {stats['cache']['hit_ratio']:.2%}")
        logger.info(f"Solicitudes: {stats['content_requests']}")
        logger.info(f"Tokens generados: {stats['tokens']['total']}")

    except Exception as e:
        logger.error(f"Error en ejemplos: {e}")
    finally:
        # Cerrar cliente
        await vertex_ai_client.close()
        logger.info("Ejemplos completados")


if __name__ == "__main__":
    asyncio.run(main())

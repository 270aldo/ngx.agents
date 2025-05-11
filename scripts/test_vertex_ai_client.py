#!/usr/bin/env python
"""
Script para probar el cliente Vertex AI en un entorno real.
Este script inicializa el cliente Vertex AI y realiza algunas operaciones básicas.
"""

import asyncio
import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path para poder importar los módulos
sys.path.append(str(Path(__file__).parent.parent))

from clients.vertex_ai import vertex_ai_client


async def test_vertex_ai_client():
    """Prueba el cliente Vertex AI en un entorno real."""
    print("Inicializando cliente Vertex AI...")
    await vertex_ai_client.initialize()
    
    print("\n=== Generación de Contenido ===")
    response = await vertex_ai_client.generate_content(
        prompt="Explica brevemente qué es la inteligencia artificial",
        temperature=0.7
    )
    print(f"Respuesta: {response['text']}")
    print(f"Tokens utilizados: {response['usage']['total_tokens']}")
    
    print("\n=== Generación de Embedding ===")
    embedding = await vertex_ai_client.generate_embedding(
        text="Ejemplo de texto para embedding"
    )
    print(f"Dimensiones del embedding: {len(embedding)}")
    print(f"Primeros 5 valores: {embedding[:5]}")
    
    print("\n=== Estadísticas del Cliente ===")
    stats = await vertex_ai_client.get_stats()
    print(f"Solicitudes de contenido: {stats['content_requests']}")
    print(f"Solicitudes de embedding: {stats['embedding_requests']}")
    print(f"Caché - hits: {stats['cache']['hits']}, misses: {stats['cache']['misses']}")
    print(f"Pool de conexiones - creadas: {stats['connection_pool']['created']}, reutilizadas: {stats['connection_pool']['reused']}")
    
    # Probar caché
    print("\n=== Prueba de Caché ===")
    print("Generando contenido con el mismo prompt (debería usar caché)...")
    response2 = await vertex_ai_client.generate_content(
        prompt="Explica brevemente qué es la inteligencia artificial",
        temperature=0.7
    )
    stats2 = await vertex_ai_client.get_stats()
    print(f"Caché - hits: {stats2['cache']['hits']}, misses: {stats2['cache']['misses']}")
    
    print("\n=== Cerrando Cliente ===")
    await vertex_ai_client.close()
    print("Cliente cerrado correctamente")


if __name__ == "__main__":
    # Verificar que las variables de entorno necesarias están configuradas
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("ADVERTENCIA: La variable de entorno GOOGLE_APPLICATION_CREDENTIALS no está configurada.")
        print("Es posible que necesites configurarla para autenticarte con Google Cloud.")
        print("Ejemplo: export GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/tu/archivo-credenciales.json")
    
    # Ejecutar la prueba
    asyncio.run(test_vertex_ai_client())

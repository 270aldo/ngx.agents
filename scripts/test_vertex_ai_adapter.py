#!/usr/bin/env python
"""
Script para probar el adaptador del cliente Vertex AI.
Este script inicializa el adaptador del cliente Vertex AI y realiza algunas operaciones básicas.
"""

import asyncio
import os
import sys
from pathlib import Path
import pytest

# Añadir el directorio raíz al path para poder importar los módulos
sys.path.append(str(Path(__file__).parent.parent))

from clients.vertex_ai.client import VertexAIClient


@pytest.mark.asyncio
async def test_vertex_ai_client(monkeypatch):
    """Prueba el cliente Vertex AI."""
    monkeypatch.setenv("MOCK_VERTEX_AI", "true")
    print("Inicializando cliente Vertex AI...")
    client = VertexAIClient()

    print("\n=== Generación de Contenido ===")
    response = await client.generate_content(
        prompt="Explica brevemente qué es la inteligencia artificial", temperature=0.7
    )
    print(f"Respuesta: {response['text']}")
    print(f"Tokens utilizados: {response['usage']['total_tokens']}")

    print("\n=== Generación de Embedding ===")
    response_data = await client.generate_embedding(
        text="Ejemplo de texto para embedding"
    )
    actual_embedding_vector = response_data["embedding"]
    print(f"Dimensiones del embedding: {len(actual_embedding_vector)}")
    if actual_embedding_vector and len(actual_embedding_vector) > 0:
        print(f"Primeros 5 valores: {actual_embedding_vector[:5]}")
    else:
        print("No se obtuvieron valores de embedding")

    print("\n=== Estadísticas del Cliente ===")
    stats = await client.get_stats()
    print(f"Solicitudes de contenido: {stats.get('content_requests', 0)}")
    print(f"Solicitudes de embedding: {stats.get('embedding_requests', 0)}")

    cache_stats = stats.get("cache", {})
    print(
        f"Caché - hits: {cache_stats.get('hits', 0)}, misses: {cache_stats.get('misses', 0)}"
    )

    # Probar caché
    print("\n=== Prueba de Caché ===")
    print("Generando contenido con el mismo prompt (debería usar caché)...")
    response2 = await client.generate_content(
        prompt="Explica brevemente qué es la inteligencia artificial", temperature=0.7
    )
    stats2 = await client.get_stats()

    cache_stats2 = stats2.get("cache", {})
    print(
        f"Caché - hits: {cache_stats2.get('hits', 0)}, misses: {cache_stats2.get('misses', 0)}"
    )

    print("\n=== Cerrando Cliente ===")
    await client.close()
    print("Cliente cerrado correctamente")


if __name__ == "__main__":
    # Verificar que las variables de entorno necesarias están configuradas
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print(
            "ADVERTENCIA: La variable de entorno GOOGLE_APPLICATION_CREDENTIALS no está configurada."
        )
        print(
            "Es posible que necesites configurarla para autenticarte con Google Cloud."
        )
        print(
            "Ejemplo: export GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/tu/archivo-credenciales.json"
        )

    # Ejecutar la prueba
    asyncio.run(test_vertex_ai_client())

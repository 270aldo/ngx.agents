"""
Script para probar el Gestor de Embeddings.

Este script demuestra cómo utilizar el Gestor de Embeddings para generar,
almacenar y buscar embeddings, así como realizar clustering de textos.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# Agregar directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.adapters.embedding_adapter import embedding_adapter

async def generate_and_store_embeddings():
    """Genera y almacena embeddings para textos de ejemplo."""
    print("\n=== Generando y almacenando embeddings ===")
    
    # Textos de ejemplo (consultas de fitness)
    texts = [
        "¿Cuál es mi plan de entrenamiento para hoy?",
        "Muéstrame mi rutina de ejercicios",
        "¿Cuántas calorías he quemado esta semana?",
        "Quiero ver mi progreso en levantamiento de pesas",
        "¿Cuándo es mi próxima sesión de cardio?",
        "Necesito modificar mi dieta",
        "¿Puedes mostrarme ejercicios para fortalecer la espalda?",
        "¿Cómo puedo mejorar mi resistencia?",
        "Quiero aumentar mi masa muscular",
        "¿Cuáles son mis métricas de sueño?"
    ]
    
    # Categorías para metadatos
    categories = [
        "plan_entrenamiento", "plan_entrenamiento", "métricas", 
        "progreso", "plan_entrenamiento", "nutrición", 
        "ejercicios", "rendimiento", "objetivos", "bienestar"
    ]
    
    # Almacenar cada texto con su embedding y metadatos
    stored_ids = []
    for i, (text, category) in enumerate(zip(texts, categories)):
        # Crear metadatos
        metadata = {
            "category": category,
            "priority": i % 3 + 1,  # Prioridad 1-3
            "timestamp": datetime.now().isoformat(),
            "user_id": "user_test_123"
        }
        
        # Almacenar texto
        embedding_id = await embedding_adapter.store_text(text, metadata, "fitness_queries")
        stored_ids.append(embedding_id)
        
        print(f"Almacenado: '{text}' con ID: {embedding_id}")
    
    return stored_ids

async def search_similar_texts(query: str, namespace: str = "fitness_queries"):
    """Busca textos similares a una consulta."""
    print(f"\n=== Buscando textos similares a: '{query}' ===")
    
    # Buscar similares
    results = await embedding_adapter.find_similar(query, namespace, top_k=3)
    
    # Mostrar resultados
    for i, result in enumerate(results):
        print(f"{i+1}. '{result['text']}' (Similitud: {result['similarity']:.4f})")
        print(f"   Categoría: {result['metadata'].get('category', 'N/A')}")
    
    return results

async def cluster_texts():
    """Agrupa textos en clusters basados en similitud semántica."""
    print("\n=== Agrupando textos en clusters ===")
    
    # Textos para clustering
    texts = [
        "Ejercicios para aumentar fuerza",
        "Rutinas para ganar músculo",
        "Cómo mejorar mi resistencia cardiovascular",
        "Entrenamientos para correr más rápido",
        "Dieta para ganar masa muscular",
        "Plan de alimentación para definición",
        "Ejercicios para mejorar flexibilidad",
        "Rutina de estiramientos post-entrenamiento",
        "Cómo recuperarme mejor después de entrenar",
        "Suplementos para recuperación muscular"
    ]
    
    # Realizar clustering
    result = await embedding_adapter.cluster_texts(texts, n_clusters=3)
    
    # Mostrar clusters
    for cluster_id, items in result["clusters"].items():
        print(f"\nCluster {cluster_id}:")
        for item in items:
            print(f"  - {item['text']}")
    
    return result

async def generate_embeddings_batch():
    """Genera embeddings en batch para múltiples textos."""
    print("\n=== Generando embeddings en batch ===")
    
    # Textos para generar embeddings
    texts = [
        "Entrenamiento de alta intensidad",
        "Ejercicios de fuerza",
        "Nutrición deportiva",
        "Recuperación muscular"
    ]
    
    # Generar embeddings en batch
    start_time = datetime.now()
    embeddings = await embedding_adapter.batch_generate_embeddings(texts)
    end_time = datetime.now()
    
    # Mostrar resultados
    print(f"Generados {len(embeddings)} embeddings en {(end_time - start_time).total_seconds():.2f} segundos")
    print(f"Dimensiones: {len(embeddings[0])}")
    
    return embeddings

async def show_stats():
    """Muestra estadísticas del gestor de embeddings."""
    print("\n=== Estadísticas del Gestor de Embeddings ===")
    
    # Obtener estadísticas
    stats = await embedding_adapter.get_stats()
    
    # Mostrar estadísticas principales
    print(f"Tamaño del almacén: {stats.get('store_size', 'N/A')}")
    print(f"Dimensión de vectores: {stats.get('vector_dimension', 'N/A')}")
    print(f"Umbral de similitud: {stats.get('similarity_threshold', 'N/A')}")
    
    # Mostrar estadísticas del gestor
    manager_stats = stats.get("manager_stats", {})
    print("\nOperaciones:")
    print(f"  - Generaciones de embedding: {manager_stats.get('embedding_generations', 0)}")
    print(f"  - Generaciones en batch: {manager_stats.get('batch_generations', 0)}")
    print(f"  - Operaciones de almacenamiento: {manager_stats.get('storage_operations', 0)}")
    print(f"  - Operaciones de búsqueda: {manager_stats.get('search_operations', 0)}")
    print(f"  - Errores: {manager_stats.get('errors', 0)}")
    
    # Mostrar estadísticas del cliente
    client_stats = stats.get("client_stats", {})
    print("\nEstadísticas del cliente:")
    print(f"  - Solicitudes de embedding: {client_stats.get('embedding_requests', 0)}")
    print(f"  - Solicitudes de batch: {client_stats.get('batch_embedding_requests', 0)}")
    print(f"  - Cache hits: {client_stats.get('cache_hits', 0)}")
    print(f"  - Cache misses: {client_stats.get('cache_misses', 0)}")
    
    return stats

async def main():
    """Función principal."""
    try:
        print("=== Demostración del Gestor de Embeddings ===")
        
        # Generar y almacenar embeddings
        stored_ids = await generate_and_store_embeddings()
        
        # Buscar textos similares
        await search_similar_texts("¿Qué ejercicios debo hacer hoy?")
        await search_similar_texts("Quiero mejorar mi dieta")
        
        # Agrupar textos en clusters
        await cluster_texts()
        
        # Generar embeddings en batch
        await generate_embeddings_batch()
        
        # Mostrar estadísticas
        await show_stats()
        
        print("\n=== Demostración completada ===")
        
    except Exception as e:
        print(f"Error en la demostración: {e}")

if __name__ == "__main__":
    # Ejecutar función principal
    asyncio.run(main())

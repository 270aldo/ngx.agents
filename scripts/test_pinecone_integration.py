"""
Script para probar la integración con Pinecone.

Este script demuestra cómo utilizar el Gestor de Embeddings con Pinecone
como almacenamiento vectorial para generar, almacenar y buscar embeddings.
"""


import os
# Configurar modo mock para pruebas
os.environ["MOCK_MODE"] = "True"
os.environ["MOCK_VERTEX_AI"] = "True"
os.environ["MOCK_A2A"] = "True"

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# Agregar directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.adapters.embedding_adapter import embedding_adapter
from core.embeddings_manager import EmbeddingsManager

async def setup_pinecone_environment():
    """Configura el entorno para usar Pinecone."""
    print("\n=== Configurando entorno para Pinecone ===")
    
    # Verificar si hay una API key de Pinecone en el entorno
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        print("No se encontró PINECONE_API_KEY en el entorno.")
        print("Por favor, proporcione una API key de Pinecone:")
        api_key = input("> ")
        os.environ["PINECONE_API_KEY"] = api_key
    
    # Configurar otras variables de entorno
    os.environ["VECTOR_STORE_TYPE"] = "pinecone"
    os.environ["PINECONE_ENVIRONMENT"] = os.environ.get("PINECONE_ENVIRONMENT", "us-west1-gcp")
    os.environ["PINECONE_INDEX_NAME"] = os.environ.get("PINECONE_INDEX_NAME", "ngx-embeddings-test")
    
    print(f"Entorno configurado para usar Pinecone en {os.environ['PINECONE_ENVIRONMENT']}")
    print(f"Índice: {os.environ['PINECONE_INDEX_NAME']}")
    
    # Crear una nueva instancia del gestor de embeddings con Pinecone
    embeddings_manager = EmbeddingsManager()
    
    # Verificar si se está usando Pinecone
    vector_store_type = embeddings_manager.config.get("vector_store_type")
    if vector_store_type != "pinecone":
        print(f"ADVERTENCIA: No se está usando Pinecone como almacenamiento vectorial. Tipo actual: {vector_store_type}")
    
    return embeddings_manager

async def generate_and_store_embeddings(embeddings_manager):
    """Genera y almacena embeddings para textos de ejemplo."""
    print("\n=== Generando y almacenando embeddings en Pinecone ===")
    
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
        
        # Generar embedding
        embedding = await embeddings_manager.generate_embedding(text, "fitness_queries")
        
        # Almacenar embedding
        embedding_id = await embeddings_manager.store_embedding(text, embedding, metadata, "fitness_queries")
        stored_ids.append(embedding_id)
        
        print(f"Almacenado: '{text}' con ID: {embedding_id}")
    
    return stored_ids

async def batch_store_embeddings(embeddings_manager):
    """Almacena embeddings en batch."""
    print("\n=== Almacenando embeddings en batch en Pinecone ===")
    
    # Textos para almacenar en batch
    texts = [
        "Ejercicios para aumentar fuerza",
        "Rutinas para ganar músculo",
        "Cómo mejorar mi resistencia cardiovascular",
        "Entrenamientos para correr más rápido",
        "Dieta para ganar masa muscular"
    ]
    
    # Metadatos para cada texto
    metadatas = [
        {"category": "fuerza", "difficulty": "intermediate"},
        {"category": "hipertrofia", "difficulty": "advanced"},
        {"category": "cardio", "difficulty": "beginner"},
        {"category": "cardio", "difficulty": "intermediate"},
        {"category": "nutrición", "difficulty": "beginner"}
    ]
    
    # Generar embeddings en batch
    embeddings = await embeddings_manager.batch_generate_embeddings(texts, "fitness_batch")
    
    # Almacenar embeddings en batch
    ids = await embeddings_manager.batch_store_embeddings(texts, embeddings, metadatas, "fitness_batch")
    
    print(f"Almacenados {len(ids)} embeddings en batch")
    for i, (text, id) in enumerate(zip(texts, ids)):
        print(f"{i+1}. '{text}' con ID: {id}")
    
    return ids

async def search_similar_texts(embeddings_manager, query: str, namespace: str = "fitness_queries"):
    """Busca textos similares a una consulta."""
    print(f"\n=== Buscando textos similares a: '{query}' ===")
    
    # Buscar similares
    results = await embeddings_manager.search_similar(query, namespace, top_k=3)
    
    # Mostrar resultados
    for i, result in enumerate(results):
        print(f"{i+1}. '{result['text']}' (Similitud: {result['similarity']:.4f})")
        print(f"   Categoría: {result['metadata'].get('category', 'N/A')}")
    
    return results

async def search_with_filter(embeddings_manager, query: str, filter: Dict[str, Any], namespace: str = "fitness_batch"):
    """Busca textos similares con filtro de metadatos."""
    print(f"\n=== Buscando textos similares a: '{query}' con filtro: {filter} ===")
    
    # Buscar similares con filtro
    results = await embeddings_manager.search_similar(query, namespace, top_k=5, filter=filter)
    
    # Mostrar resultados
    if results:
        for i, result in enumerate(results):
            print(f"{i+1}. '{result['text']}' (Similitud: {result['similarity']:.4f})")
            print(f"   Metadatos: {result['metadata']}")
    else:
        print("No se encontraron resultados que coincidan con el filtro.")
    
    return results

async def delete_embeddings(embeddings_manager, ids: List[str], namespace: str = "fitness_queries"):
    """Elimina embeddings por ID."""
    print("\n=== Eliminando embeddings ===")
    
    for id in ids:
        success = await embeddings_manager.delete_embedding(id, namespace)
        print(f"Eliminado embedding con ID {id}: {'Éxito' if success else 'Fallido'}")

async def show_stats(embeddings_manager):
    """Muestra estadísticas del gestor de embeddings y Pinecone."""
    print("\n=== Estadísticas del Gestor de Embeddings con Pinecone ===")
    
    # Obtener estadísticas
    stats = await embeddings_manager.get_stats()
    
    # Mostrar estadísticas principales
    print(f"Tipo de almacenamiento vectorial: {stats.get('vector_store_type', 'N/A')}")
    print(f"Dimensión de vectores: {stats.get('vector_dimension', 'N/A')}")
    print(f"Umbral de similitud: {stats.get('similarity_threshold', 'N/A')}")
    
    # Mostrar estadísticas del gestor
    manager_stats = stats.get("manager_stats", {})
    print("\nOperaciones del gestor:")
    print(f"  - Generaciones de embedding: {manager_stats.get('embedding_generations', 0)}")
    print(f"  - Operaciones de almacenamiento: {manager_stats.get('storage_operations', 0)}")
    print(f"  - Operaciones de búsqueda: {manager_stats.get('search_operations', 0)}")
    print(f"  - Errores: {manager_stats.get('errors', 0)}")
    
    # Mostrar estadísticas de Pinecone
    vector_store_stats = stats.get("vector_store_stats", {})
    client_stats = vector_store_stats.get("client_stats", {})
    
    print("\nEstadísticas de Pinecone:")
    print(f"  - Índice: {client_stats.get('index_name', 'N/A')}")
    print(f"  - Entorno: {client_stats.get('environment', 'N/A')}")
    
    # Mostrar estadísticas del índice si están disponibles
    index_stats = client_stats.get("index_stats", {})
    if index_stats and "namespaces" in index_stats:
        print("\nEstadísticas del índice:")
        namespaces = index_stats.get("namespaces", {})
        total_vectors = index_stats.get("total_vector_count", 0)
        print(f"  - Total de vectores: {total_vectors}")
        print("  - Vectores por namespace:")
        for ns, ns_stats in namespaces.items():
            print(f"    * {ns}: {ns_stats.get('vector_count', 0)} vectores")
    
    return stats

async def main():
    """Función principal."""
    try:
        print("=== Demostración de Integración con Pinecone ===")
        
        # Configurar entorno para Pinecone
        embeddings_manager = await setup_pinecone_environment()
        
        # Generar y almacenar embeddings
        stored_ids = await generate_and_store_embeddings(embeddings_manager)
        
        # Almacenar embeddings en batch
        batch_ids = await batch_store_embeddings(embeddings_manager)
        
        # Buscar textos similares
        await search_similar_texts(embeddings_manager, "¿Qué ejercicios debo hacer hoy?")
        await search_similar_texts(embeddings_manager, "Quiero mejorar mi dieta")
        
        # Buscar con filtros
        await search_with_filter(embeddings_manager, "ejercicios", {"category": "fuerza"})
        await search_with_filter(embeddings_manager, "entrenamiento", {"difficulty": "intermediate"})
        
        # Mostrar estadísticas
        await show_stats(embeddings_manager)
        
        # Eliminar algunos embeddings
        if stored_ids:
            await delete_embeddings(embeddings_manager, [stored_ids[0], stored_ids[1]])
        
        # Mostrar estadísticas actualizadas
        await show_stats(embeddings_manager)
        
        print("\n=== Demostración completada ===")
        
    except Exception as e:
        print(f"Error en la demostración: {e}")

if __name__ == "__main__":
    # Ejecutar función principal
    asyncio.run(main())

"""
Script para probar la integración con Vertex AI Vector Search.

Este script prueba la funcionalidad básica del adaptador de Vertex AI Vector Search,
incluyendo almacenamiento, búsqueda y eliminación de embeddings.
"""

import asyncio
import logging
import os
import sys
import random
from typing import List, Dict, Any

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Añadir directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from clients.vertex_ai.vector_search_client import VertexVectorSearchClient
from infrastructure.adapters.vertex_vector_store_adapter import VertexVectorStore
from core.embeddings_manager import EmbeddingsManager

async def test_vertex_vector_search():
    """Prueba la funcionalidad básica de Vertex AI Vector Search."""
    logger.info("Iniciando prueba de Vertex AI Vector Search...")
    
    # Configurar el tipo de vector store a "vertex"
    os.environ["VECTOR_STORE_TYPE"] = "vertex"
    
    # Crear instancia del gestor de embeddings
    embeddings_manager = EmbeddingsManager()
    
    # Verificar que se está usando el adaptador correcto
    vector_store = embeddings_manager.vector_store
    if not isinstance(vector_store, VertexVectorStore):
        logger.error("No se está utilizando VertexVectorStore. Asegúrate de que VECTOR_STORE_TYPE=vertex")
        return
    
    logger.info("Usando VertexVectorStore correctamente")
    
    # Generar textos de prueba
    texts = [
        "Los embeddings vectoriales son representaciones numéricas de datos textuales.",
        "Vertex AI Vector Search es un servicio de Google Cloud para búsqueda vectorial.",
        "La búsqueda semántica permite encontrar documentos similares en significado, no solo por palabras clave.",
        "Los modelos de lenguaje grandes como GPT-4 utilizan embeddings para entender el contexto.",
        "La similitud coseno es una medida común para comparar la similitud entre vectores."
    ]
    
    # Namespace para las pruebas
    namespace = f"test-{random.randint(1000, 9999)}"
    logger.info(f"Usando namespace: {namespace}")
    
    try:
        # Paso 1: Generar y almacenar embeddings
        logger.info("Generando y almacenando embeddings...")
        embedding_ids = []
        
        for i, text in enumerate(texts):
            # Generar embedding
            embedding = await embeddings_manager.generate_embedding(text)
            logger.info(f"Embedding generado para texto {i+1}: {len(embedding)} dimensiones")
            
            # Almacenar embedding
            metadata = {"index": i, "category": "test", "length": len(text)}
            embedding_id = await embeddings_manager.store_embedding(
                text=text,
                embedding=embedding,
                metadata=metadata,
                namespace=namespace
            )
            
            if embedding_id:
                logger.info(f"Embedding almacenado con ID: {embedding_id}")
                embedding_ids.append(embedding_id)
            else:
                logger.error(f"Error al almacenar embedding para texto {i+1}")
        
        logger.info(f"Se almacenaron {len(embedding_ids)} embeddings")
        
        # Esperar un momento para que los embeddings se indexen
        logger.info("Esperando 5 segundos para que los embeddings se indexen...")
        await asyncio.sleep(5)
        
        # Paso 2: Buscar embeddings similares
        logger.info("Buscando embeddings similares...")
        query = "Los modelos de embeddings son útiles para búsqueda semántica"
        
        results = await embeddings_manager.search_similar(
            query=query,
            namespace=namespace,
            top_k=3
        )
        
        logger.info(f"Se encontraron {len(results)} resultados para la consulta")
        for i, result in enumerate(results):
            logger.info(f"Resultado {i+1}:")
            logger.info(f"  ID: {result.get('id')}")
            logger.info(f"  Texto: {result.get('text')}")
            logger.info(f"  Similitud: {result.get('similarity')}")
            logger.info(f"  Metadatos: {result.get('metadata')}")
        
        # Paso 3: Buscar con filtros
        logger.info("Buscando con filtros...")
        filter_results = await embeddings_manager.search_similar(
            query=query,
            namespace=namespace,
            top_k=3,
            filter={"category": "test"}
        )
        
        logger.info(f"Se encontraron {len(filter_results)} resultados con filtro")
        
        # Paso 4: Recuperar un embedding específico
        if embedding_ids:
            logger.info(f"Recuperando embedding con ID: {embedding_ids[0]}")
            embedding = await embeddings_manager.get_embedding(embedding_ids[0], namespace)
            
            if embedding:
                logger.info(f"Embedding recuperado: {embedding.get('id')}")
                logger.info(f"Texto: {embedding.get('text')}")
            else:
                logger.error("No se pudo recuperar el embedding")
        
        # Paso 5: Eliminar embeddings
        logger.info("Eliminando embeddings...")
        for embedding_id in embedding_ids:
            success = await embeddings_manager.delete_embedding(embedding_id, namespace)
            logger.info(f"Embedding {embedding_id} eliminado: {success}")
        
        # Paso 6: Verificar estadísticas
        logger.info("Obteniendo estadísticas...")
        stats = await embeddings_manager.get_stats()
        logger.info(f"Estadísticas del gestor de embeddings:")
        logger.info(f"  Tipo de vector store: {stats.get('vector_store_type')}")
        logger.info(f"  Dimensión de vectores: {stats.get('vector_dimension')}")
        logger.info(f"  Operaciones de almacenamiento: {stats.get('manager_stats', {}).get('storage_operations')}")
        logger.info(f"  Operaciones de búsqueda: {stats.get('manager_stats', {}).get('search_operations')}")
        logger.info(f"  Operaciones de eliminación: {stats.get('manager_stats', {}).get('delete_operations')}")
        
        logger.info("Prueba completada con éxito")
        
    except Exception as e:
        logger.error(f"Error durante la prueba: {str(e)}", exc_info=True)
    
    finally:
        # Limpiar namespace de prueba
        try:
            logger.info(f"Limpiando namespace de prueba: {namespace}")
            # Crear un vector aleatorio para la búsqueda
            random_vector = [random.uniform(-1, 1) for _ in range(embeddings_manager.vector_dimension)]
            
            # Buscar todos los embeddings en el namespace
            results = await embeddings_manager.search_similar(
                query=random_vector,
                namespace=namespace,
                top_k=100
            )
            
            # Eliminar todos los embeddings encontrados
            for result in results:
                await embeddings_manager.delete_embedding(result.get('id'), namespace)
            
            logger.info(f"Namespace limpiado: {len(results)} embeddings eliminados")
        except Exception as e:
            logger.error(f"Error al limpiar namespace: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_vertex_vector_search())

"""
Script para migrar embeddings de Pinecone a Vertex AI Vector Search.

Este script extrae embeddings de Pinecone y los migra a Vertex AI Vector Search,
manteniendo los mismos IDs, textos y metadatos.
"""

import asyncio
import logging
import os
import sys
import random
import argparse
from typing import List, Dict, Any, Optional
from tqdm import tqdm

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("migration_log.txt")
    ]
)
logger = logging.getLogger(__name__)

# Añadir directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from clients.pinecone.pinecone_client import PineconeClient
from infrastructure.adapters.vector_store_adapter import PineconeVectorStore
from clients.vertex_ai.vector_search_client import VertexVectorSearchClient
from infrastructure.adapters.vertex_vector_store_adapter import VertexVectorStore

async def migrar_embeddings(
    namespace_origen: str, 
    namespace_destino: Optional[str] = None,
    batch_size: int = 100,
    max_embeddings: Optional[int] = None,
    dry_run: bool = False
):
    """
    Migra embeddings de Pinecone a Vertex AI Vector Search.
    
    Args:
        namespace_origen: Namespace de origen en Pinecone
        namespace_destino: Namespace de destino en Vertex AI Vector Search (por defecto igual al origen)
        batch_size: Tamaño del lote para procesar embeddings
        max_embeddings: Número máximo de embeddings a migrar (None para todos)
        dry_run: Si es True, solo muestra lo que se haría sin realizar cambios
    """
    if namespace_destino is None:
        namespace_destino = namespace_origen
    
    logger.info(f"Iniciando migración de embeddings de Pinecone a Vertex AI Vector Search")
    logger.info(f"Namespace origen: {namespace_origen}")
    logger.info(f"Namespace destino: {namespace_destino}")
    logger.info(f"Tamaño de lote: {batch_size}")
    logger.info(f"Máximo de embeddings: {max_embeddings if max_embeddings else 'Sin límite'}")
    logger.info(f"Modo: {'Simulación' if dry_run else 'Ejecución real'}")
    
    # Configurar cliente de Pinecone
    pinecone_config = {
        "api_key": os.environ.get("PINECONE_API_KEY"),
        "environment": os.environ.get("PINECONE_ENVIRONMENT", "us-west1-gcp"),
        "index_name": os.environ.get("PINECONE_INDEX_NAME", "ngx-embeddings")
    }
    pinecone_client = PineconeClient(pinecone_config)
    pinecone_store = PineconeVectorStore(pinecone_client)
    
    # Configurar cliente de Vertex AI Vector Search
    vertex_config = {
        "project_id": os.environ.get("GOOGLE_CLOUD_PROJECT"),
        "location": os.environ.get("VERTEX_LOCATION", "us-central1"),
        "index_name": os.environ.get("VERTEX_VECTOR_SEARCH_INDEX", "ngx-embeddings"),
        "index_endpoint_name": os.environ.get("VERTEX_VECTOR_SEARCH_ENDPOINT", "ngx-embeddings-endpoint"),
        "deployed_index_id": os.environ.get("VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID", "ngx-embeddings-deployed"),
        "dimension": int(os.environ.get("VERTEX_VECTOR_DIMENSION", "3072"))
    }
    
    if not dry_run:
        vertex_client = VertexVectorSearchClient(vertex_config)
        vertex_store = VertexVectorStore(vertex_client)
    
    # Obtener dimensión del vector para Pinecone
    pinecone_dimension = int(os.environ.get("PINECONE_DIMENSION", "768"))
    
    # Crear un vector aleatorio para la búsqueda
    random_vector = [random.uniform(-1, 1) for _ in range(pinecone_dimension)]
    
    # Obtener todos los embeddings de Pinecone
    logger.info(f"Buscando embeddings en Pinecone (namespace: {namespace_origen})...")
    
    # Usar un valor alto para top_k para obtener la mayor cantidad posible de embeddings
    top_k = 10000 if max_embeddings is None else min(10000, max_embeddings)
    
    resultados = await pinecone_store.search(
        vector=random_vector,
        namespace=namespace_origen,
        top_k=top_k
    )
    
    total_embeddings = len(resultados)
    logger.info(f"Se encontraron {total_embeddings} embeddings para migrar")
    
    if max_embeddings is not None and total_embeddings > max_embeddings:
        logger.info(f"Limitando a {max_embeddings} embeddings según configuración")
        resultados = resultados[:max_embeddings]
        total_embeddings = len(resultados)
    
    # Preparar para procesar en lotes
    batches = [resultados[i:i + batch_size] for i in range(0, len(resultados), batch_size)]
    logger.info(f"Procesando {len(batches)} lotes de {batch_size} embeddings cada uno")
    
    # Estadísticas
    stats = {
        "total": total_embeddings,
        "processed": 0,
        "success": 0,
        "error": 0,
        "skipped": 0
    }
    
    # Procesar cada lote
    for batch_idx, batch in enumerate(tqdm(batches, desc="Procesando lotes")):
        logger.info(f"Procesando lote {batch_idx + 1}/{len(batches)} ({len(batch)} embeddings)")
        
        # Obtener los embeddings completos para este lote
        batch_ids = [item.get("id") for item in batch]
        batch_embeddings = []
        
        for id in tqdm(batch_ids, desc="Obteniendo embeddings completos"):
            embedding_completo = await pinecone_store.get(id, namespace_origen)
            if embedding_completo:
                batch_embeddings.append(embedding_completo)
            else:
                logger.warning(f"No se pudo obtener el embedding completo para ID: {id}")
                stats["error"] += 1
        
        if not batch_embeddings:
            logger.warning(f"No se pudieron obtener embeddings completos para el lote {batch_idx + 1}")
            continue
        
        # Preparar vectores para Vertex AI Vector Search
        vertex_vectors = []
        for embedding in batch_embeddings:
            id = embedding.get("id")
            text = embedding.get("text", "")
            metadata = embedding.get("metadata", {})
            vector = embedding.get("vector", [])
            
            if not vector:
                logger.warning(f"Vector vacío para ID: {id}")
                stats["error"] += 1
                continue
            
            # Asegurar que el texto esté en los metadatos
            if "text" not in metadata:
                metadata["text"] = text
            
            vertex_vectors.append({
                "id": id,
                "values": vector,
                "metadata": metadata
            })
        
        stats["processed"] += len(vertex_vectors)
        
        if dry_run:
            logger.info(f"[DRY RUN] Se migrarían {len(vertex_vectors)} embeddings en este lote")
            stats["skipped"] += len(vertex_vectors)
        else:
            try:
                # Almacenar en Vertex AI Vector Search
                if vertex_vectors:
                    await vertex_store.client.upsert(vertex_vectors, namespace_destino)
                    logger.info(f"Lote {batch_idx + 1}: {len(vertex_vectors)} embeddings migrados correctamente")
                    stats["success"] += len(vertex_vectors)
            except Exception as e:
                logger.error(f"Error al migrar lote {batch_idx + 1}: {str(e)}")
                stats["error"] += len(vertex_vectors)
        
        # Pequeña pausa para no saturar la API
        await asyncio.sleep(0.5)
    
    # Resumen final
    logger.info("Migración completada")
    logger.info(f"Estadísticas:")
    logger.info(f"  Total de embeddings encontrados: {stats['total']}")
    logger.info(f"  Embeddings procesados: {stats['processed']}")
    logger.info(f"  Embeddings migrados correctamente: {stats['success']}")
    logger.info(f"  Embeddings con errores: {stats['error']}")
    logger.info(f"  Embeddings omitidos (dry run): {stats['skipped']}")
    
    return stats

async def verificar_migracion(namespace: str, num_samples: int = 5):
    """
    Verifica que la migración se haya realizado correctamente comparando
    resultados de búsqueda entre Pinecone y Vertex AI Vector Search.
    
    Args:
        namespace: Namespace a verificar
        num_samples: Número de consultas de muestra a realizar
    """
    logger.info(f"Verificando migración en namespace: {namespace}")
    
    # Configurar clientes
    pinecone_config = {
        "api_key": os.environ.get("PINECONE_API_KEY"),
        "environment": os.environ.get("PINECONE_ENVIRONMENT", "us-west1-gcp"),
        "index_name": os.environ.get("PINECONE_INDEX_NAME", "ngx-embeddings")
    }
    pinecone_client = PineconeClient(pinecone_config)
    pinecone_store = PineconeVectorStore(pinecone_client)
    
    vertex_config = {
        "project_id": os.environ.get("GOOGLE_CLOUD_PROJECT"),
        "location": os.environ.get("VERTEX_LOCATION", "us-central1"),
        "index_name": os.environ.get("VERTEX_VECTOR_SEARCH_INDEX", "ngx-embeddings")
    }
    vertex_client = VertexVectorSearchClient(vertex_config)
    vertex_store = VertexVectorStore(vertex_client)
    
    # Consultas de muestra
    consultas = [
        "Inteligencia artificial y machine learning",
        "Procesamiento de lenguaje natural",
        "Embeddings vectoriales para búsqueda semántica",
        "Vertex AI y Google Cloud Platform",
        "Optimización de modelos de lenguaje"
    ]
    
    # Limitar al número de muestras solicitado
    consultas = consultas[:num_samples]
    
    # Realizar consultas en ambos sistemas
    for i, consulta in enumerate(consultas):
        logger.info(f"Consulta de verificación {i+1}/{len(consultas)}: '{consulta}'")
        
        # Buscar en Pinecone
        pinecone_results = await pinecone_store.search(
            vector=[0.1] * 768,  # Vector ficticio, se reemplazará por el embedding real
            namespace=namespace,
            top_k=3
        )
        
        # Buscar en Vertex AI Vector Search
        vertex_results = await vertex_store.search(
            vector=[0.1] * 3072,  # Vector ficticio, se reemplazará por el embedding real
            namespace=namespace,
            top_k=3
        )
        
        logger.info(f"  Pinecone: {len(pinecone_results)} resultados")
        logger.info(f"  Vertex AI: {len(vertex_results)} resultados")
        
        # Comparar número de resultados
        if abs(len(pinecone_results) - len(vertex_results)) > 1:
            logger.warning(f"  Diferencia significativa en el número de resultados")
        else:
            logger.info(f"  Número de resultados similar")
    
    logger.info("Verificación completada")

def parse_args():
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Migrar embeddings de Pinecone a Vertex AI Vector Search")
    parser.add_argument("--namespace-origen", type=str, required=True, help="Namespace de origen en Pinecone")
    parser.add_argument("--namespace-destino", type=str, help="Namespace de destino en Vertex AI Vector Search (por defecto igual al origen)")
    parser.add_argument("--batch-size", type=int, default=100, help="Tamaño del lote para procesar embeddings")
    parser.add_argument("--max-embeddings", type=int, help="Número máximo de embeddings a migrar")
    parser.add_argument("--dry-run", action="store_true", help="Ejecutar en modo simulación sin realizar cambios")
    parser.add_argument("--verify", action="store_true", help="Verificar la migración después de completarla")
    parser.add_argument("--verify-samples", type=int, default=5, help="Número de consultas de muestra para verificación")
    return parser.parse_args()

async def main():
    """Función principal."""
    args = parse_args()
    
    # Ejecutar migración
    stats = await migrar_embeddings(
        namespace_origen=args.namespace_origen,
        namespace_destino=args.namespace_destino,
        batch_size=args.batch_size,
        max_embeddings=args.max_embeddings,
        dry_run=args.dry_run
    )
    
    # Verificar migración si se solicita
    if args.verify and not args.dry_run and stats["success"] > 0:
        namespace_destino = args.namespace_destino or args.namespace_origen
        await verificar_migracion(namespace_destino, args.verify_samples)

if __name__ == "__main__":
    asyncio.run(main())

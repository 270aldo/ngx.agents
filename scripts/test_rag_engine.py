"""
Script para probar la integración con Vertex AI RAG Engine.

Este script prueba la funcionalidad básica del adaptador de Vertex AI RAG Engine,
incluyendo la carga de documentos, creación de corpus y aplicaciones RAG, y consultas.
"""

import asyncio
import logging
import os
import sys
import argparse
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

from infrastructure.adapters.rag_engine_adapter import rag_engine_adapter

async def test_rag_engine(document_paths: List[str], corpus_name: str, application_name: str, queries: List[str]):
    """
    Prueba la funcionalidad básica de Vertex AI RAG Engine.
    
    Args:
        document_paths: Lista de rutas a documentos para cargar
        corpus_name: Nombre del corpus a crear
        application_name: Nombre de la aplicación RAG a crear
        queries: Lista de consultas para probar
    """
    logger.info("Iniciando prueba de Vertex AI RAG Engine...")
    
    try:
        # Paso 1: Subir documentos
        logger.info(f"Subiendo {len(document_paths)} documentos...")
        document_uris = []
        
        for i, doc_path in enumerate(document_paths):
            logger.info(f"Subiendo documento {i+1}/{len(document_paths)}: {doc_path}")
            uri = await rag_engine_adapter.upload_document(doc_path)
            
            if uri:
                logger.info(f"Documento subido correctamente: {uri}")
                document_uris.append(uri)
            else:
                logger.error(f"Error al subir documento: {doc_path}")
        
        if not document_uris:
            logger.error("No se pudo subir ningún documento. Abortando prueba.")
            return
        
        logger.info(f"Se subieron {len(document_uris)} documentos correctamente")
        
        # Paso 2: Crear corpus
        logger.info(f"Creando corpus: {corpus_name}")
        corpus_id = await rag_engine_adapter.create_corpus(corpus_name, document_uris)
        
        if not corpus_id:
            logger.error("Error al crear corpus. Abortando prueba.")
            return
        
        logger.info(f"Corpus creado correctamente con ID: {corpus_id}")
        
        # Paso 3: Crear aplicación RAG
        logger.info(f"Creando aplicación RAG: {application_name}")
        app_id = await rag_engine_adapter.create_rag_application(corpus_id, application_name)
        
        if not app_id:
            logger.error("Error al crear aplicación RAG. Abortando prueba.")
            return
        
        logger.info(f"Aplicación RAG creada correctamente con ID: {app_id}")
        
        # Esperar a que la aplicación esté lista
        logger.info("Esperando 10 segundos para que la aplicación esté lista...")
        await asyncio.sleep(10)
        
        # Paso 4: Realizar consultas
        logger.info(f"Realizando {len(queries)} consultas...")
        
        for i, query in enumerate(queries):
            logger.info(f"Consulta {i+1}/{len(queries)}: '{query}'")
            
            result = await rag_engine_adapter.query_rag(
                query=query,
                application_id=app_id,
                top_k=3,
                temperature=0.2,
                max_output_tokens=1024
            )
            
            if "error" in result:
                logger.error(f"Error en la consulta: {result.get('error')}")
                continue
            
            logger.info(f"Respuesta: {result.get('answer')}")
            logger.info(f"Citas: {len(result.get('citations', []))}")
            
            for j, citation in enumerate(result.get("citations", [])):
                logger.info(f"  Cita {j+1}:")
                logger.info(f"    Texto: {citation.get('text', '')[:100]}...")
                logger.info(f"    URI: {citation.get('uri', '')}")
                logger.info(f"    Página: {citation.get('page', '')}")
        
        # Paso 5: Obtener estadísticas
        logger.info("Obteniendo estadísticas...")
        stats = await rag_engine_adapter.get_stats()
        
        logger.info(f"Estadísticas:")
        logger.info(f"  Operaciones de corpus: {stats.get('corpus_operations', 0)}")
        logger.info(f"  Operaciones de consulta: {stats.get('query_operations', 0)}")
        logger.info(f"  Errores: {stats.get('errors', 0)}")
        logger.info(f"  Latencia promedio: {stats.get('avg_latency_ms', 0)} ms")
        logger.info(f"  Modelo de embeddings: {stats.get('embedding_model', '')}")
        logger.info(f"  Modelo de orquestador: {stats.get('orchestrator_model', '')}")
        logger.info(f"  Modelo de agente: {stats.get('agent_model', '')}")
        
        logger.info("Prueba completada con éxito")
        
    except Exception as e:
        logger.error(f"Error durante la prueba: {str(e)}", exc_info=True)

def parse_args():
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Probar la integración con Vertex AI RAG Engine")
    parser.add_argument("--documents", nargs="+", required=True, help="Rutas a los documentos a cargar")
    parser.add_argument("--corpus", type=str, default="test-corpus", help="Nombre del corpus a crear")
    parser.add_argument("--application", type=str, default="test-app", help="Nombre de la aplicación RAG a crear")
    parser.add_argument("--queries", nargs="+", default=["¿Qué información contienen estos documentos?"], 
                        help="Consultas para probar")
    return parser.parse_args()

async def main():
    """Función principal."""
    args = parse_args()
    
    await test_rag_engine(
        document_paths=args.documents,
        corpus_name=args.corpus,
        application_name=args.application,
        queries=args.queries
    )

if __name__ == "__main__":
    asyncio.run(main())

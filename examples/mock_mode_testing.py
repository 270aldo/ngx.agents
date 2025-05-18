#!/usr/bin/env python3
"""
Script de ejemplo para probar NGX Agents en modo simulado (mock mode).

Este script demuestra cómo utilizar el modo simulado para probar las diferentes
funcionalidades del sistema sin necesidad de tener credenciales reales para
los servicios externos como Vertex AI, Pinecone, etc.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Añadir el directorio raíz al path para importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mock_mode_testing")

# Importar componentes necesarios
from clients.vertex_ai.document.document_client import DocumentClient
from clients.vertex_ai.document.entity_extractor_client import EntityExtractorClient
from clients.vertex_ai.document.classifier_client import ClassifierClient
from core.document_processor import DocumentProcessor
from infrastructure.adapters.document_adapter import document_adapter

from clients.vertex_ai.voice.stt_client import STTClient
from clients.vertex_ai.voice.tts_client import TTSClient
from clients.vertex_ai.voice.emotion_analyzer import EmotionAnalyzer
from core.voice_processor import VoiceProcessor
from infrastructure.adapters.voice_adapter import voice_adapter

from clients.vertex_ai.embedding_client import EmbeddingClient
from clients.pinecone.pinecone_client import PineconeClient
from core.embeddings_manager import EmbeddingsManager
from infrastructure.adapters.embedding_adapter import embedding_adapter
from infrastructure.adapters.vector_store_adapter import vector_store_adapter

async def test_document_processing():
    """Prueba las funcionalidades de procesamiento de documentos en modo simulado."""
    logger.info("=== Probando procesamiento de documentos en modo simulado ===")
    
    # Activar modo simulado en el adaptador de documentos
    document_adapter.mock_mode = True
    await document_adapter.initialize()
    
    # Crear un documento de prueba (simulado)
    mock_document = b"%PDF-1.5\nMock PDF document for testing"
    
    # 1. Clasificar documento
    logger.info("1. Clasificando documento...")
    result = await document_adapter.classify_document(mock_document, {"mime_type": "application/pdf"})
    logger.info(f"Tipo de documento: {result.get('document_type')}")
    logger.info(f"Confianza: {result.get('confidence')}")
    
    # 2. Extraer texto
    logger.info("\n2. Extrayendo texto...")
    result = await document_adapter.extract_text(mock_document, {"mime_type": "application/pdf"})
    logger.info(f"Texto extraído: {result.get('text')[:100]}...")
    
    # 3. Extraer entidades
    logger.info("\n3. Extrayendo entidades...")
    result = await document_adapter.extract_entities(
        mock_document,
        {
            "mime_type": "application/pdf",
            "document_type": "invoice",
            "entity_types": ["supplier_name", "customer_name", "total_amount"]
        }
    )
    logger.info(f"Entidades extraídas: {len(result.get('entities', []))}")
    
    # 4. Análisis completo
    logger.info("\n4. Realizando análisis completo...")
    result = await document_adapter.analyze_document(mock_document, {"mime_type": "application/pdf"})
    logger.info(f"Tipo de documento: {result.get('document_type')}")
    logger.info(f"Entidades extraídas: {len(result.get('entities', []))}")
    
    logger.info("=== Prueba de procesamiento de documentos completada ===")

async def test_voice_processing():
    """Prueba las funcionalidades de procesamiento de voz en modo simulado."""
    logger.info("\n=== Probando procesamiento de voz en modo simulado ===")
    
    # Activar modo simulado en el adaptador de voz
    voice_adapter.mock_mode = True
    await voice_adapter.initialize()
    
    # Crear un audio de prueba (simulado)
    mock_audio = b"Mock audio data for testing"
    
    # 1. Convertir voz a texto
    logger.info("1. Convirtiendo voz a texto...")
    result = await voice_adapter.speech_to_text(mock_audio)
    logger.info(f"Texto transcrito: {result.get('text')}")
    logger.info(f"Confianza: {result.get('confidence')}")
    
    # 2. Convertir texto a voz
    logger.info("\n2. Convirtiendo texto a voz...")
    text = "Este es un texto de prueba para convertir a voz."
    result = await voice_adapter.text_to_speech(text)
    logger.info(f"Audio generado: {len(result.get('audio', b''))} bytes")
    
    # 3. Analizar emociones en voz
    logger.info("\n3. Analizando emociones en voz...")
    result = await voice_adapter.analyze_emotion(mock_audio)
    logger.info(f"Emoción detectada: {result.get('emotion')}")
    logger.info(f"Confianza: {result.get('confidence')}")
    
    # 4. Procesar conversación
    logger.info("\n4. Procesando conversación...")
    result = await voice_adapter.process_conversation(mock_audio, "es-MX")
    logger.info(f"Texto transcrito: {result.get('text')}")
    logger.info(f"Emoción detectada: {result.get('emotion')}")
    logger.info(f"Respuesta generada: {result.get('response_text')}")
    
    logger.info("=== Prueba de procesamiento de voz completada ===")

async def test_embeddings_and_vector_search():
    """Prueba las funcionalidades de embeddings y búsqueda vectorial en modo simulado."""
    logger.info("\n=== Probando embeddings y búsqueda vectorial en modo simulado ===")
    
    # Activar modo simulado en los adaptadores
    embedding_adapter.mock_mode = True
    vector_store_adapter.mock_mode = True
    
    await embedding_adapter.initialize()
    await vector_store_adapter.initialize()
    
    # 1. Generar embeddings
    logger.info("1. Generando embeddings...")
    texts = [
        "Este es un texto de ejemplo para generar embeddings.",
        "Los embeddings son representaciones vectoriales de texto.",
        "La búsqueda vectorial permite encontrar textos semánticamente similares."
    ]
    result = await embedding_adapter.generate_embeddings(texts)
    logger.info(f"Embeddings generados: {len(result)}")
    logger.info(f"Dimensión de embeddings: {len(result[0]) if result else 0}")
    
    # 2. Almacenar vectores
    logger.info("\n2. Almacenando vectores...")
    vectors = [
        {
            "id": "doc1",
            "values": [0.1] * 768,  # Vector simulado
            "metadata": {"text": texts[0], "source": "example"}
        },
        {
            "id": "doc2",
            "values": [0.2] * 768,  # Vector simulado
            "metadata": {"text": texts[1], "source": "example"}
        },
        {
            "id": "doc3",
            "values": [0.3] * 768,  # Vector simulado
            "metadata": {"text": texts[2], "source": "example"}
        }
    ]
    result = await vector_store_adapter.upsert_vectors(vectors)
    logger.info(f"Vectores almacenados: {result.get('upserted_count')}")
    
    # 3. Buscar vectores similares
    logger.info("\n3. Buscando vectores similares...")
    query_vector = [0.2] * 768  # Vector de consulta simulado
    result = await vector_store_adapter.query_vectors(query_vector, top_k=2)
    logger.info(f"Resultados encontrados: {len(result.get('matches', []))}")
    for i, match in enumerate(result.get("matches", [])):
        logger.info(f"  Match {i+1}: ID={match.get('id')}, Score={match.get('score')}")
        logger.info(f"    Texto: {match.get('metadata', {}).get('text', '')}")
    
    logger.info("=== Prueba de embeddings y búsqueda vectorial completada ===")

async def test_all_components():
    """Prueba todos los componentes en modo simulado."""
    logger.info("Iniciando pruebas en modo simulado para todos los componentes...")
    
    # Probar procesamiento de documentos
    await test_document_processing()
    
    # Probar procesamiento de voz
    await test_voice_processing()
    
    # Probar embeddings y búsqueda vectorial
    await test_embeddings_and_vector_search()
    
    logger.info("\n=== Todas las pruebas en modo simulado completadas con éxito ===")

async def main():
    """Función principal."""
    # Configurar variables de entorno para modo simulado
    os.environ["MOCK_EXTERNAL_SERVICES"] = "true"
    
    # Ejecutar pruebas
    await test_all_components()

if __name__ == "__main__":
    asyncio.run(main())

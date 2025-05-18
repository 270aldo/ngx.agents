"""
Prueba de integración entre el Adaptador de Embeddings y el Analizador de Intenciones.
"""


import os
# Configurar modo mock para pruebas
os.environ["MOCK_MODE"] = "True"
os.environ["MOCK_VERTEX_AI"] = "True"
os.environ["MOCK_A2A"] = "True"

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from core.intent_analyzer_optimized import IntentAnalyzerOptimized
from infrastructure.adapters.embedding_adapter import embedding_adapter

@pytest.fixture
def embedding_adapter_mock():
    """Mock para el adaptador de embeddings."""
    mock = MagicMock()
    
    # Configurar métodos asíncronos
    mock.generate_embedding.return_value = asyncio.Future()
    mock.generate_embedding.return_value.set_result([0.1, 0.2, 0.3, 0.4])
    
    mock.find_similar.return_value = asyncio.Future()
    mock.find_similar.return_value.set_result([
        {"id": "1", "text": "¿Cuál es mi plan de entrenamiento?", "similarity": 0.95, "metadata": {"intent": "consultar_plan"}},
        {"id": "2", "text": "Muéstrame mi rutina de hoy", "similarity": 0.85, "metadata": {"intent": "consultar_plan"}}
    ])
    
    return mock

@pytest.fixture
def intent_analyzer(embedding_adapter_mock):
    """Fixture para el analizador de intenciones con mock del adaptador de embeddings."""
    with patch('infrastructure.adapters.embedding_adapter.embedding_adapter', embedding_adapter_mock):
        # Crear analizador de intenciones
        analyzer = IntentAnalyzerOptimized()
        
        # Inyectar adaptador de embeddings mockeado
        analyzer.embedding_adapter = embedding_adapter_mock
        
        return analyzer

@pytest.mark.asyncio
async def test_intent_analyzer_with_embeddings(intent_analyzer, embedding_adapter_mock):
    """
    Prueba la integración del analizador de intenciones con el adaptador de embeddings.
    
    Esta prueba simula cómo el analizador de intenciones puede utilizar embeddings
    para mejorar la comprensión de las consultas de los usuarios.
    """
    # Consulta de usuario
    query = "Necesito ver mi plan de ejercicios"
    
    # Analizar intención
    result = await intent_analyzer.analyze(query)
    
    # Verificar que se llamó al adaptador de embeddings
    embedding_adapter_mock.find_similar.assert_called_once()
    
    # Verificar que se detectó la intención correcta basada en similitud semántica
    assert result["intent"] == "consultar_plan"
    assert result["confidence"] > 0.8
    
    # Verificar que se incluyeron los ejemplos similares en el resultado
    assert "similar_queries" in result
    assert len(result["similar_queries"]) == 2
    assert result["similar_queries"][0]["text"] == "¿Cuál es mi plan de entrenamiento?"

@pytest.mark.asyncio
async def test_intent_analyzer_embedding_fallback(intent_analyzer, embedding_adapter_mock):
    """
    Prueba el uso de embeddings como fallback cuando la clasificación tradicional falla.
    
    Esta prueba simula un escenario donde la clasificación tradicional no puede
    determinar la intención, pero el análisis de similitud semántica sí.
    """
    # Configurar mock para simular que no se encontró intención por métodos tradicionales
    intent_analyzer._classify_intent = MagicMock(return_value=(None, 0.0))
    
    # Consulta de usuario con formulación poco común
    query = "¿Podrías indicarme qué ejercicios tengo programados?"
    
    # Analizar intención
    result = await intent_analyzer.analyze(query)
    
    # Verificar que se llamó al adaptador de embeddings como fallback
    embedding_adapter_mock.find_similar.assert_called_once()
    
    # Verificar que se detectó la intención correcta basada en similitud semántica
    assert result["intent"] == "consultar_plan"
    assert "semantic_match" in result
    assert result["semantic_match"] is True

@pytest.mark.asyncio
async def test_store_user_queries_for_training(intent_analyzer, embedding_adapter_mock):
    """
    Prueba el almacenamiento de consultas de usuario para entrenamiento futuro.
    
    Esta prueba simula cómo las consultas de los usuarios pueden almacenarse
    con sus embeddings para mejorar el sistema con el tiempo.
    """
    # Configurar mock para almacenar texto
    embedding_adapter_mock.store_text.return_value = asyncio.Future()
    embedding_adapter_mock.store_text.return_value.set_result("query-id-123")
    
    # Consulta de usuario
    query = "¿Cuándo debo hacer mi próximo entrenamiento?"
    intent = "consultar_plan"
    confidence = 0.92
    
    # Almacenar consulta para entrenamiento
    result = await intent_analyzer.store_query_for_training(query, intent, confidence)
    
    # Verificar que se llamó al adaptador de embeddings para almacenar
    embedding_adapter_mock.store_text.assert_called_once()
    
    # Verificar los argumentos del llamado
    call_args = embedding_adapter_mock.store_text.call_args[0]
    assert call_args[0] == query  # Texto
    
    # Verificar metadatos
    metadata = call_args[1]
    assert metadata["intent"] == intent
    assert metadata["confidence"] == confidence
    assert "timestamp" in metadata
    
    # Verificar namespace
    assert call_args[2] == "intent_queries"  # Namespace
    
    # Verificar resultado
    assert result == "query-id-123"

# Función auxiliar para el analizador de intenciones
async def store_query_for_training(self, query: str, intent: str, confidence: float) -> str:
    """
    Almacena una consulta de usuario con su intención para entrenamiento futuro.
    
    Args:
        query: Consulta del usuario
        intent: Intención detectada
        confidence: Confianza de la detección
        
    Returns:
        str: ID de la consulta almacenada
    """
    # Crear metadatos
    metadata = {
        "intent": intent,
        "confidence": confidence,
        "timestamp": datetime.now().isoformat()
    }
    
    # Almacenar texto con su embedding
    return await embedding_adapter.store_text(query, metadata, "intent_queries")

# Agregar método al IntentAnalyzerOptimized para la prueba
IntentAnalyzerOptimized.store_query_for_training = store_query_for_training

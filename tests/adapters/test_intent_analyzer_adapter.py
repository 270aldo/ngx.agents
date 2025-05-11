"""
Pruebas para el adaptador del analizador de intenciones.

Este módulo contiene pruebas para verificar el funcionamiento
del adaptador que permite la migración gradual del analizador
de intenciones original al optimizado.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from core.intent_analyzer import Intent, IntentEntity
from infrastructure.adapters.intent_analyzer_adapter import IntentAnalyzerAdapter, intent_analyzer_adapter


@pytest.fixture
def mock_original_analyzer():
    """Fixture para simular el analizador original."""
    with patch('core.intent_analyzer_adapter.intent_analyzer') as mock:
        # Configurar el mock para devolver intenciones simuladas
        mock.analyze_intent = AsyncMock(return_value=[
            Intent(
                intent_type="training_request",
                confidence=0.9,
                agents=["elite_training_strategist"],
                entities=[
                    IntentEntity(
                        entity_type="exercise",
                        value="push-up",
                        confidence=0.95
                    )
                ]
            )
        ])
        
        mock.analyze_intents_with_embeddings = AsyncMock(return_value=[
            Intent(
                intent_type="nutrition_query",
                confidence=0.85,
                agents=["precision_nutrition_architect"]
            )
        ])
        
        mock.get_stats = AsyncMock(return_value={
            "total_queries": 10,
            "cached_embeddings": 5,
            "api_calls": 8
        })
        
        mock.initialize = AsyncMock(return_value=None)
        
        yield mock


@pytest.fixture
def mock_optimized_analyzer():
    """Fixture para simular el analizador optimizado."""
    with patch('core.intent_analyzer_adapter.IntentAnalyzerOptimized') as mock_class:
        mock = MagicMock()
        mock_class.return_value = mock
        
        # Configurar el mock para devolver intenciones simuladas
        mock.analyze_query = AsyncMock(return_value=[
            Intent(
                intent_type="biometric_analysis",
                confidence=0.95,
                agents=["biometrics_insight_engine"],
                entities=[
                    IntentEntity(
                        entity_type="metric",
                        value="heart_rate",
                        confidence=0.98
                    )
                ]
            )
        ])
        
        mock.initialize = AsyncMock(return_value=True)
        
        mock.stats = {
            "total_queries": 15,
            "embedding_cache_hits": 8,
            "embedding_cache_misses": 7,
            "llm_calls": 12
        }
        
        yield mock


@pytest.fixture
def adapter(mock_original_analyzer, mock_optimized_analyzer):
    """Fixture para crear una instancia del adaptador con mocks."""
    adapter = IntentAnalyzerAdapter()
    adapter._original_analyzer = mock_original_analyzer
    adapter._optimized_analyzer = mock_optimized_analyzer
    return adapter


class TestIntentAnalyzerAdapter:
    """Pruebas para el adaptador del analizador de intenciones."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, adapter):
        """Prueba la inicialización del adaptador."""
        # Verificar que el adaptador se inicializa correctamente
        assert adapter._initialized is True
        assert adapter.use_optimized is False
        
        # Inicializar el adaptador
        result = await adapter.initialize()
        assert result is True
        
        # Verificar que se llamó a initialize en el analizador original
        adapter._original_analyzer.initialize.assert_called_once()
        
        # Verificar que no se llamó a initialize en el analizador optimizado
        adapter._optimized_analyzer.initialize.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_initialization_with_optimized(self, adapter):
        """Prueba la inicialización del adaptador con el analizador optimizado."""
        # Configurar para usar el analizador optimizado
        adapter.use_optimized = True
        
        # Inicializar el adaptador
        result = await adapter.initialize()
        assert result is True
        
        # Verificar que se llamó a initialize en ambos analizadores
        adapter._original_analyzer.initialize.assert_called_once()
        adapter._optimized_analyzer.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_intent_with_original(self, adapter):
        """Prueba el análisis de intenciones con el analizador original."""
        # Configurar para usar el analizador original
        adapter.use_optimized = False
        
        # Analizar una consulta
        result = await adapter.analyze_intent(
            user_query="Necesito un programa de entrenamiento",
            conversation_id="conv123",
            user_id="user456"
        )
        
        # Verificar que se llamó al método correcto en el analizador original
        adapter._original_analyzer.analyze_intent.assert_called_once_with(
            user_query="Necesito un programa de entrenamiento",
            conversation_id="conv123",
            user_id="user456",
            context=None,
            multimodal_data=None
        )
        
        # Verificar que no se llamó al analizador optimizado
        adapter._optimized_analyzer.analyze_query.assert_not_called()
        
        # Verificar el resultado
        assert len(result) == 1
        assert result[0].intent_type == "training_request"
        assert result[0].confidence == 0.9
        assert result[0].agents == ["elite_training_strategist"]
        assert len(result[0].entities) == 1
        assert result[0].entities[0].entity_type == "exercise"
        assert result[0].entities[0].value == "push-up"
    
    @pytest.mark.asyncio
    async def test_analyze_intent_with_optimized(self, adapter):
        """Prueba el análisis de intenciones con el analizador optimizado."""
        # Configurar para usar el analizador optimizado
        adapter.use_optimized = True
        
        # Analizar una consulta
        result = await adapter.analyze_intent(
            user_query="Analiza mis datos de frecuencia cardíaca",
            conversation_id="conv789",
            user_id="user012",
            context={"additional": "context"},
            multimodal_data={"image": "base64data"}
        )
        
        # Verificar que se llamó al método correcto en el analizador optimizado
        adapter._optimized_analyzer.analyze_query.assert_called_once_with(
            user_query="Analiza mis datos de frecuencia cardíaca",
            conversation_id="conv789",
            user_id="user012",
            context={"additional": "context"},
            multimodal_data={"image": "base64data"}
        )
        
        # Verificar que no se llamó al analizador original
        adapter._original_analyzer.analyze_intent.assert_not_called()
        
        # Verificar el resultado
        assert len(result) == 1
        assert result[0].intent_type == "biometric_analysis"
        assert result[0].confidence == 0.95
        assert result[0].agents == ["biometrics_insight_engine"]
        assert len(result[0].entities) == 1
        assert result[0].entities[0].entity_type == "metric"
        assert result[0].entities[0].value == "heart_rate"
    
    @pytest.mark.asyncio
    async def test_analyze_intents_with_embeddings_original(self, adapter):
        """Prueba el análisis de intenciones con embeddings usando el analizador original."""
        # Configurar para usar el analizador original
        adapter.use_optimized = False
        
        # Analizar una consulta
        result = await adapter.analyze_intents_with_embeddings(
            user_query="¿Qué debería comer antes de entrenar?",
            conversation_id="conv345"
        )
        
        # Verificar que se llamó al método correcto en el analizador original
        adapter._original_analyzer.analyze_intents_with_embeddings.assert_called_once_with(
            user_query="¿Qué debería comer antes de entrenar?",
            conversation_id="conv345"
        )
        
        # Verificar que no se llamó al analizador optimizado
        adapter._optimized_analyzer.analyze_query.assert_not_called()
        
        # Verificar el resultado
        assert len(result) == 1
        assert result[0].intent_type == "nutrition_query"
        assert result[0].confidence == 0.85
        assert result[0].agents == ["precision_nutrition_architect"]
    
    @pytest.mark.asyncio
    async def test_analyze_intents_with_embeddings_optimized(self, adapter):
        """Prueba el análisis de intenciones con embeddings usando el analizador optimizado."""
        # Configurar para usar el analizador optimizado
        adapter.use_optimized = True
        
        # Analizar una consulta
        result = await adapter.analyze_intents_with_embeddings(
            user_query="Analiza mis datos de frecuencia cardíaca",
            conversation_id="conv678"
        )
        
        # Verificar que se llamó al método correcto en el analizador optimizado
        adapter._optimized_analyzer.analyze_query.assert_called_once_with(
            user_query="Analiza mis datos de frecuencia cardíaca",
            conversation_id="conv678"
        )
        
        # Verificar que no se llamó al analizador original
        adapter._original_analyzer.analyze_intents_with_embeddings.assert_not_called()
        
        # Verificar el resultado
        assert len(result) == 1
        assert result[0].intent_type == "biometric_analysis"
    
    @pytest.mark.asyncio
    async def test_set_use_optimized(self, adapter):
        """Prueba el cambio entre analizadores."""
        # Verificar estado inicial
        assert adapter.use_optimized is False
        
        # Cambiar a optimizado
        adapter.set_use_optimized(True)
        assert adapter.use_optimized is True
        
        # Cambiar a original
        adapter.set_use_optimized(False)
        assert adapter.use_optimized is False
    
    @pytest.mark.asyncio
    async def test_get_stats(self, adapter):
        """Prueba la obtención de estadísticas."""
        # Configurar estadísticas del adaptador
        adapter.stats = {
            "total_queries": 25,
            "original_analyzer_calls": 15,
            "optimized_analyzer_calls": 10,
            "errors": 2,
            "processing_time": 5.0
        }
        
        # Obtener estadísticas usando el analizador original
        adapter.use_optimized = False
        stats = await adapter.get_stats()
        
        # Verificar que se incluyen las estadísticas del adaptador y del analizador original
        assert stats["total_queries"] == 25
        assert stats["original_analyzer_calls"] == 15
        assert stats["optimized_analyzer_calls"] == 10
        assert stats["errors"] == 2
        assert stats["avg_processing_time"] == 0.2  # 5.0 / 25
        assert "original_analyzer" in stats
        assert stats["original_analyzer"]["total_queries"] == 10
        assert "optimized_analyzer" not in stats
        
        # Obtener estadísticas usando el analizador optimizado
        adapter.use_optimized = True
        stats = await adapter.get_stats()
        
        # Verificar que se incluyen las estadísticas del adaptador, del analizador original y del optimizado
        assert stats["total_queries"] == 25
        assert "original_analyzer" in stats
        assert "optimized_analyzer" in stats
        assert stats["optimized_analyzer"]["total_queries"] == 15
        assert stats["optimized_analyzer"]["embedding_cache_hits"] == 8
    
    @pytest.mark.asyncio
    async def test_error_handling_in_analyze_intent(self, adapter):
        """Prueba el manejo de errores en analyze_intent."""
        # Configurar el analizador original para lanzar una excepción
        adapter.use_optimized = False
        adapter._original_analyzer.analyze_intent.side_effect = Exception("Error simulado")
        
        # Analizar una consulta
        result = await adapter.analyze_intent(
            user_query="Consulta que genera error",
            conversation_id="conv_error"
        )
        
        # Verificar que se devuelve una intención de fallback
        assert len(result) == 1
        assert result[0].intent_type == "general_query"
        assert result[0].confidence == 0.5
        assert "fallback" in result[0].metadata
        assert result[0].metadata["fallback"] is True
        assert "error" in result[0].metadata
        assert "from_adapter" in result[0].metadata
        
        # Verificar que se incrementó el contador de errores
        assert adapter.stats["errors"] > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_in_analyze_intents_with_embeddings(self, adapter):
        """Prueba el manejo de errores en analyze_intents_with_embeddings."""
        # Configurar el analizador original para lanzar una excepción
        adapter.use_optimized = False
        adapter._original_analyzer.analyze_intents_with_embeddings.side_effect = Exception("Error simulado")
        
        # Analizar una consulta
        result = await adapter.analyze_intents_with_embeddings(
            user_query="Consulta que genera error",
            conversation_id="conv_error"
        )
        
        # Verificar que se devuelve una intención de fallback
        assert len(result) == 1
        assert result[0].intent_type == "general_query"
        assert result[0].confidence == 0.5
        assert "fallback" in result[0].metadata
        assert result[0].metadata["fallback"] is True
        assert "error" in result[0].metadata
        assert "from_adapter" in result[0].metadata


@pytest.mark.asyncio
async def test_singleton_pattern():
    """Prueba que el adaptador implementa correctamente el patrón Singleton."""
    # Obtener dos instancias del adaptador
    adapter1 = IntentAnalyzerAdapter()
    adapter2 = IntentAnalyzerAdapter()
    
    # Verificar que son la misma instancia
    assert adapter1 is adapter2
    
    # Verificar que la instancia global también es la misma
    assert adapter1 is intent_analyzer_adapter
    
    # Cambiar una propiedad en una instancia
    adapter1.use_optimized = True
    
    # Verificar que el cambio se refleja en todas las instancias
    assert adapter2.use_optimized is True
    assert intent_analyzer_adapter.use_optimized is True

"""
Pruebas para el Cliente de Embeddings de Vertex AI.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from clients.vertex_ai.embedding_client import EmbeddingClient

@pytest.fixture
def cache_manager_mock():
    """Mock para el gestor de caché."""
    mock = MagicMock()
    
    # Configurar métodos asíncronos
    mock.get.return_value = asyncio.Future()
    mock.get.return_value.set_result(None)  # Simular caché vacío inicialmente
    
    mock.set.return_value = asyncio.Future()
    mock.set.return_value.set_result(True)
    
    mock.get_stats.return_value = asyncio.Future()
    mock.get_stats.return_value.set_result({"hits": {"total": 0}, "misses": {"total": 1}})
    
    return mock

@pytest.fixture
def vertex_ai_model_mock():
    """Mock para el modelo de embeddings de Vertex AI."""
    mock = MagicMock()
    
    # Configurar resultado de get_embeddings
    embedding_result = MagicMock()
    embedding_result.values = [0.1, 0.2, 0.3, 0.4]
    mock.get_embeddings.return_value = [embedding_result]
    
    return mock

@pytest.fixture
def embedding_client(cache_manager_mock, vertex_ai_model_mock):
    """Fixture para el cliente de embeddings con mocks."""
    with patch('clients.vertex_ai.embedding_client.CacheManager', return_value=cache_manager_mock):
        client = EmbeddingClient()
        client.cache = cache_manager_mock
        client.client = {"embedding_model": vertex_ai_model_mock, "mock": False}
        return client

@pytest.mark.asyncio
async def test_generate_embedding_cache_miss(embedding_client, cache_manager_mock, vertex_ai_model_mock):
    """Prueba la generación de embeddings con caché vacío."""
    # Configurar caché para simular miss
    cache_manager_mock.get.return_value = asyncio.Future()
    cache_manager_mock.get.return_value.set_result(None)
    
    # Generar embedding
    result = await embedding_client.generate_embedding("texto de prueba", "test_namespace")
    
    # Verificar que se llamó al modelo
    vertex_ai_model_mock.get_embeddings.assert_called_once_with(["texto de prueba"])
    
    # Verificar que se guardó en caché
    cache_manager_mock.set.assert_called_once()
    
    # Verificar resultado
    assert result == [0.1, 0.2, 0.3, 0.4]

@pytest.mark.asyncio
async def test_generate_embedding_cache_hit(embedding_client, cache_manager_mock, vertex_ai_model_mock):
    """Prueba la generación de embeddings con caché hit."""
    # Configurar caché para simular hit
    cache_manager_mock.get.return_value = asyncio.Future()
    cache_manager_mock.get.return_value.set_result([0.5, 0.6, 0.7, 0.8])
    
    # Generar embedding
    result = await embedding_client.generate_embedding("texto de prueba", "test_namespace")
    
    # Verificar que NO se llamó al modelo
    vertex_ai_model_mock.get_embeddings.assert_not_called()
    
    # Verificar que NO se guardó en caché
    cache_manager_mock.set.assert_not_called()
    
    # Verificar resultado (debe ser el del caché)
    assert result == [0.5, 0.6, 0.7, 0.8]

@pytest.mark.asyncio
async def test_batch_generate_embeddings(embedding_client, cache_manager_mock, vertex_ai_model_mock):
    """Prueba la generación de embeddings en batch."""
    # Configurar modelo para batch
    embedding_result1 = MagicMock()
    embedding_result1.values = [0.1, 0.2, 0.3, 0.4]
    
    embedding_result2 = MagicMock()
    embedding_result2.values = [0.5, 0.6, 0.7, 0.8]
    
    vertex_ai_model_mock.get_embeddings.return_value = [embedding_result1, embedding_result2]
    
    # Configurar caché para simular miss en todos
    cache_manager_mock.get.return_value = asyncio.Future()
    cache_manager_mock.get.return_value.set_result(None)
    
    # Generar embeddings en batch
    texts = ["texto uno", "texto dos"]
    result = await embedding_client.batch_generate_embeddings(texts, "test_namespace")
    
    # Verificar que se llamó al modelo
    vertex_ai_model_mock.get_embeddings.assert_called_once_with(texts)
    
    # Verificar que se guardó en caché (dos veces, una por texto)
    assert cache_manager_mock.set.call_count == 2
    
    # Verificar resultado
    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3, 0.4]
    assert result[1] == [0.5, 0.6, 0.7, 0.8]

@pytest.mark.asyncio
async def test_batch_generate_embeddings_partial_cache(embedding_client, cache_manager_mock, vertex_ai_model_mock):
    """Prueba la generación de embeddings en batch con caché parcial."""
    # Configurar modelo para batch (solo se llamará para el segundo texto)
    embedding_result = MagicMock()
    embedding_result.values = [0.5, 0.6, 0.7, 0.8]
    vertex_ai_model_mock.get_embeddings.return_value = [embedding_result]
    
    # Configurar caché para simular hit en el primer texto y miss en el segundo
    async def mock_get(key):
        if "texto uno" in key:
            return [0.1, 0.2, 0.3, 0.4]
        return None
    
    cache_manager_mock.get.side_effect = mock_get
    
    # Generar embeddings en batch
    texts = ["texto uno", "texto dos"]
    result = await embedding_client.batch_generate_embeddings(texts, "test_namespace")
    
    # Verificar que se llamó al modelo solo con el segundo texto
    vertex_ai_model_mock.get_embeddings.assert_called_once_with(["texto dos"])
    
    # Verificar que se guardó en caché solo el segundo texto
    assert cache_manager_mock.set.call_count == 1
    
    # Verificar resultado
    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3, 0.4]
    assert result[1] == [0.5, 0.6, 0.7, 0.8]

@pytest.mark.asyncio
async def test_mock_mode(cache_manager_mock):
    """Prueba el modo mock cuando Vertex AI no está disponible."""
    with patch('clients.vertex_ai.embedding_client.CacheManager', return_value=cache_manager_mock):
        # Crear cliente en modo mock
        client = EmbeddingClient()
        client.cache = cache_manager_mock
        client.client = {"mock": True}  # Forzar modo mock
        
        # Generar embedding
        result = await client.generate_embedding("texto de prueba")
        
        # Verificar que el resultado es un vector de 768 dimensiones
        assert len(result) == 768
        assert all(isinstance(x, float) for x in result)
        
        # Generar embeddings en batch
        batch_result = await client.batch_generate_embeddings(["texto uno", "texto dos"])
        
        # Verificar que el resultado son dos vectores de 768 dimensiones
        assert len(batch_result) == 2
        assert len(batch_result[0]) == 768
        assert len(batch_result[1]) == 768

@pytest.mark.asyncio
async def test_get_stats(embedding_client, cache_manager_mock):
    """Prueba la obtención de estadísticas."""
    # Configurar estadísticas de caché
    cache_manager_mock.get_stats.return_value = asyncio.Future()
    cache_manager_mock.get_stats.return_value.set_result({
        "hits": {"total": 10},
        "misses": {"total": 5}
    })
    
    # Obtener estadísticas
    stats = await embedding_client.get_stats()
    
    # Verificar que se llamó a get_stats del caché
    cache_manager_mock.get_stats.assert_called_once()
    
    # Verificar que las estadísticas contienen los campos esperados
    assert "embedding_requests" in stats
    assert "batch_embedding_requests" in stats
    assert "cache_hits" in stats
    assert "cache_misses" in stats
    assert "cache" in stats

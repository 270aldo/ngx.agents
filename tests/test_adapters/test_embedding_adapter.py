"""
Pruebas para el Adaptador de Embeddings.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from infrastructure.adapters.embedding_adapter import EmbeddingAdapter, embedding_adapter

@pytest.fixture
def embeddings_manager_mock():
    """Mock para el gestor de embeddings."""
    mock = MagicMock()
    
    # Configurar métodos asíncronos
    mock.generate_embedding.return_value = asyncio.Future()
    mock.generate_embedding.return_value.set_result([0.1, 0.2, 0.3, 0.4])
    
    mock.search_similar.return_value = asyncio.Future()
    mock.search_similar.return_value.set_result([
        {"id": "1", "text": "texto similar", "similarity": 0.9, "metadata": {}}
    ])
    
    mock.store_embedding.return_value = asyncio.Future()
    mock.store_embedding.return_value.set_result("test-id-123")
    
    mock.batch_generate_embeddings.return_value = asyncio.Future()
    mock.batch_generate_embeddings.return_value.set_result([[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]])
    
    mock.cluster_embeddings.return_value = asyncio.Future()
    mock.cluster_embeddings.return_value.set_result([0, 1, 0])
    
    mock.get_stats.return_value = asyncio.Future()
    mock.get_stats.return_value.set_result({"manager_stats": {}, "client_stats": {}})
    
    return mock

@pytest.fixture
def embedding_adapter_instance(embeddings_manager_mock):
    """Fixture para el adaptador de embeddings con mocks."""
    with patch('infrastructure.adapters.embedding_adapter.embeddings_manager', embeddings_manager_mock):
        # Crear nueva instancia para evitar interferencia con el singleton global
        adapter = EmbeddingAdapter()
        adapter._initialized = False  # Forzar reinicialización
        adapter.__init__()
        return adapter

@pytest.mark.asyncio
async def test_generate_embedding(embedding_adapter_instance, embeddings_manager_mock):
    """Prueba la generación de embeddings a través del adaptador."""
    result = await embedding_adapter_instance.generate_embedding("texto de prueba", "test_namespace")
    
    embeddings_manager_mock.generate_embedding.assert_called_once_with("texto de prueba", "test_namespace")
    assert result == [0.1, 0.2, 0.3, 0.4]

@pytest.mark.asyncio
async def test_find_similar(embedding_adapter_instance, embeddings_manager_mock):
    """Prueba la búsqueda de textos similares a través del adaptador."""
    result = await embedding_adapter_instance.find_similar("consulta de prueba", "test_namespace", 10)
    
    embeddings_manager_mock.search_similar.assert_called_once_with("consulta de prueba", "test_namespace", 10)
    assert len(result) == 1
    assert result[0]["text"] == "texto similar"
    assert result[0]["similarity"] == 0.9

@pytest.mark.asyncio
async def test_store_text(embedding_adapter_instance, embeddings_manager_mock):
    """Prueba el almacenamiento de textos a través del adaptador."""
    metadata = {"source": "test"}
    result = await embedding_adapter_instance.store_text("texto de prueba", metadata, "test_namespace")
    
    embeddings_manager_mock.store_embedding.assert_called_once_with("texto de prueba", None, metadata, "test_namespace")
    assert result == "test-id-123"

@pytest.mark.asyncio
async def test_batch_generate_embeddings(embedding_adapter_instance, embeddings_manager_mock):
    """Prueba la generación de embeddings en batch a través del adaptador."""
    texts = ["texto uno", "texto dos"]
    result = await embedding_adapter_instance.batch_generate_embeddings(texts, "test_namespace")
    
    embeddings_manager_mock.batch_generate_embeddings.assert_called_once_with(texts, "test_namespace")
    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3, 0.4]
    assert result[1] == [0.5, 0.6, 0.7, 0.8]

@pytest.mark.asyncio
async def test_cluster_texts(embedding_adapter_instance, embeddings_manager_mock):
    """Prueba el clustering de textos a través del adaptador."""
    texts = ["texto uno", "texto dos", "texto tres"]
    result = await embedding_adapter_instance.cluster_texts(texts, 2, "test_namespace")
    
    # Verificar que se llamó a batch_generate_embeddings
    embeddings_manager_mock.batch_generate_embeddings.assert_called_once_with(texts, "test_namespace")
    
    # Verificar que se llamó a cluster_embeddings con los embeddings generados
    embeddings_manager_mock.cluster_embeddings.assert_called_once()
    
    # Verificar resultado
    assert "clusters" in result
    assert "labels" in result
    assert "n_clusters" in result
    assert result["labels"] == [0, 1, 0]

@pytest.mark.asyncio
async def test_get_stats(embedding_adapter_instance, embeddings_manager_mock):
    """Prueba la obtención de estadísticas a través del adaptador."""
    result = await embedding_adapter_instance.get_stats()
    
    embeddings_manager_mock.get_stats.assert_called_once()
    assert "manager_stats" in result
    assert "client_stats" in result

@pytest.mark.asyncio
async def test_singleton_pattern():
    """Prueba que el adaptador implementa correctamente el patrón Singleton."""
    # Obtener dos instancias
    adapter1 = EmbeddingAdapter()
    adapter2 = EmbeddingAdapter()
    
    # Verificar que son la misma instancia
    assert adapter1 is adapter2
    
    # Verificar que la instancia global también es la misma
    assert adapter1 is embedding_adapter

"""
Pruebas para el Gestor de Embeddings.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from core.embeddings_manager import EmbeddingsManager

@pytest.fixture
def embedding_client_mock():
    """Mock para el cliente de embeddings."""
    mock = MagicMock()
    mock.generate_embedding.return_value = asyncio.Future()
    mock.generate_embedding.return_value.set_result([0.1, 0.2, 0.3, 0.4])
    
    mock.batch_generate_embeddings.return_value = asyncio.Future()
    mock.batch_generate_embeddings.return_value.set_result([[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]])
    
    mock.get_stats.return_value = asyncio.Future()
    mock.get_stats.return_value.set_result({"embedding_requests": 1, "batch_embedding_requests": 1})
    
    return mock

@pytest.fixture
def embeddings_manager(embedding_client_mock):
    """Fixture para el gestor de embeddings con mocks."""
    with patch('clients.vertex_ai.embedding_client.EmbeddingClient', return_value=embedding_client_mock):
        manager = EmbeddingsManager()
        manager.embedding_client = embedding_client_mock
        return manager

@pytest.mark.asyncio
async def test_generate_embedding(embeddings_manager, embedding_client_mock):
    """Prueba la generación de embeddings."""
    result = await embeddings_manager.generate_embedding("texto de prueba")
    
    embedding_client_mock.generate_embedding.assert_called_once()
    assert result == [0.1, 0.2, 0.3, 0.4]

@pytest.mark.asyncio
async def test_store_embedding(embeddings_manager, embedding_client_mock):
    """Prueba el almacenamiento de embeddings."""
    # Almacenar con embedding pre-calculado
    embedding = [0.1, 0.2, 0.3, 0.4]
    metadata = {"source": "test"}
    
    embedding_id = await embeddings_manager.store_embedding(
        "texto de prueba", 
        embedding=embedding,
        metadata=metadata,
        namespace="test"
    )
    
    # Verificar que se generó un ID
    assert embedding_id != ""
    
    # Verificar que se almacenó correctamente
    assert embedding_id in embeddings_manager.vector_store
    stored_item = embeddings_manager.vector_store[embedding_id]
    assert stored_item["text"] == "texto de prueba"
    assert stored_item["embedding"] == embedding
    assert stored_item["metadata"] == metadata
    assert stored_item["namespace"] == "test"
    
    # Almacenar sin embedding pre-calculado
    embedding_id2 = await embeddings_manager.store_embedding("otro texto")
    
    # Verificar que se generó un ID
    assert embedding_id2 != ""
    assert embedding_id2 != embedding_id
    
    # Verificar que se llamó al cliente para generar el embedding
    embedding_client_mock.generate_embedding.assert_called()

@pytest.mark.asyncio
async def test_search_similar(embeddings_manager):
    """Prueba la búsqueda de textos similares."""
    # Almacenar algunos embeddings para buscar
    await embeddings_manager.store_embedding(
        "texto uno", 
        embedding=[0.1, 0.2, 0.3, 0.4],
        metadata={"index": 1}
    )
    
    await embeddings_manager.store_embedding(
        "texto dos", 
        embedding=[0.5, 0.6, 0.7, 0.8],
        metadata={"index": 2}
    )
    
    # Buscar similares usando texto
    results = await embeddings_manager.search_similar("consulta de prueba")
    
    # Verificar resultados
    assert len(results) > 0
    assert "text" in results[0]
    assert "similarity" in results[0]
    assert "metadata" in results[0]
    
    # Buscar similares usando embedding
    results2 = await embeddings_manager.search_similar([0.1, 0.2, 0.3, 0.4])
    
    # Verificar resultados
    assert len(results2) > 0

@pytest.mark.asyncio
async def test_batch_generate_embeddings(embeddings_manager, embedding_client_mock):
    """Prueba la generación de embeddings en batch."""
    texts = ["texto uno", "texto dos"]
    results = await embeddings_manager.batch_generate_embeddings(texts)
    
    embedding_client_mock.batch_generate_embeddings.assert_called_once()
    assert len(results) == 2
    assert results[0] == [0.1, 0.2, 0.3, 0.4]
    assert results[1] == [0.5, 0.6, 0.7, 0.8]

@pytest.mark.asyncio
async def test_delete_embedding(embeddings_manager):
    """Prueba la eliminación de embeddings."""
    # Almacenar un embedding
    embedding_id = await embeddings_manager.store_embedding(
        "texto para eliminar", 
        embedding=[0.1, 0.2, 0.3, 0.4]
    )
    
    # Verificar que existe
    assert embedding_id in embeddings_manager.vector_store
    
    # Eliminar
    result = await embeddings_manager.delete_embedding(embedding_id)
    
    # Verificar que se eliminó
    assert result is True
    assert embedding_id not in embeddings_manager.vector_store
    
    # Intentar eliminar uno que no existe
    result2 = await embeddings_manager.delete_embedding("id_inexistente")
    assert result2 is False

@pytest.mark.asyncio
async def test_get_embedding(embeddings_manager):
    """Prueba la recuperación de embeddings específicos."""
    # Almacenar un embedding
    embedding = [0.1, 0.2, 0.3, 0.4]
    metadata = {"source": "test"}
    
    embedding_id = await embeddings_manager.store_embedding(
        "texto de prueba", 
        embedding=embedding,
        metadata=metadata
    )
    
    # Recuperar
    result = await embeddings_manager.get_embedding(embedding_id)
    
    # Verificar
    assert result is not None
    assert result["id"] == embedding_id
    assert result["text"] == "texto de prueba"
    assert result["embedding"] == embedding
    assert result["metadata"] == metadata
    
    # Intentar recuperar uno que no existe
    result2 = await embeddings_manager.get_embedding("id_inexistente")
    assert result2 is None

@pytest.mark.asyncio
async def test_get_stats(embeddings_manager, embedding_client_mock):
    """Prueba la obtención de estadísticas."""
    stats = await embeddings_manager.get_stats()
    
    assert "manager_stats" in stats
    assert "client_stats" in stats
    assert "store_size" in stats
    assert "vector_dimension" in stats
    assert "similarity_threshold" in stats

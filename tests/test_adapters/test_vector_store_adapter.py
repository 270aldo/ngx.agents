"""
Pruebas para el adaptador de almacenamiento vectorial.

Este módulo contiene pruebas unitarias para el adaptador de almacenamiento vectorial,
verificando su funcionamiento con implementaciones en memoria y Pinecone.
"""

import asyncio
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from infrastructure.adapters.vector_store_adapter import MemoryVectorStore, PineconeVectorStore, VectorStoreAdapter
from clients.pinecone.pinecone_client import PineconeClient

@pytest.fixture
def memory_store():
    """Fixture para crear un almacén vectorial en memoria."""
    return MemoryVectorStore()

@pytest.fixture
def mock_pinecone_client():
    """Fixture para crear un cliente de Pinecone mock."""
    client = MagicMock(spec=PineconeClient)
    client.upsert = AsyncMock(return_value={"upserted_count": 1})
    client.query = AsyncMock(return_value={
        "matches": [
            {
                "id": "test1",
                "score": 0.9,
                "metadata": {"text": "Texto de prueba 1", "category": "test"}
            },
            {
                "id": "test2",
                "score": 0.8,
                "metadata": {"text": "Texto de prueba 2", "category": "test"}
            }
        ]
    })
    client.delete = AsyncMock(return_value={"deleted_count": 1})
    client.get_stats = AsyncMock(return_value={"mock": True})
    return client

@pytest.fixture
def pinecone_store(mock_pinecone_client):
    """Fixture para crear un almacén vectorial de Pinecone con cliente mock."""
    return PineconeVectorStore(mock_pinecone_client)

# Pruebas para MemoryVectorStore

@pytest.mark.asyncio
async def test_memory_store_store(memory_store):
    """Prueba el almacenamiento de un vector en memoria."""
    # Almacenar un vector
    vector = [0.1] * 768
    text = "Texto de prueba"
    metadata = {"category": "test"}
    
    id = await memory_store.store(vector, text, metadata, "test_namespace")
    
    # Verificar que se generó un ID
    assert id is not None
    assert isinstance(id, str)
    
    # Verificar estadísticas
    assert memory_store.stats["store_operations"] == 1

@pytest.mark.asyncio
async def test_memory_store_search(memory_store):
    """Prueba la búsqueda de vectores similares en memoria."""
    # Almacenar algunos vectores
    await memory_store.store([0.1] * 768, "Texto 1", {"category": "test"}, "test_namespace")
    await memory_store.store([0.2] * 768, "Texto 2", {"category": "test"}, "test_namespace")
    await memory_store.store([0.3] * 768, "Texto 3", {"category": "other"}, "test_namespace")
    
    # Buscar vectores similares
    results = await memory_store.search([0.15] * 768, "test_namespace", 2)
    
    # Verificar resultados
    assert len(results) == 2
    assert all("id" in result for result in results)
    assert all("text" in result for result in results)
    assert all("metadata" in result for result in results)
    assert all("score" in result for result in results)
    
    # Verificar estadísticas
    assert memory_store.stats["search_operations"] == 1

@pytest.mark.asyncio
async def test_memory_store_search_with_filter(memory_store):
    """Prueba la búsqueda de vectores con filtro en memoria."""
    # Almacenar algunos vectores
    await memory_store.store([0.1] * 768, "Texto 1", {"category": "test"}, "test_namespace")
    await memory_store.store([0.2] * 768, "Texto 2", {"category": "test"}, "test_namespace")
    await memory_store.store([0.3] * 768, "Texto 3", {"category": "other"}, "test_namespace")
    
    # Buscar vectores con filtro
    results = await memory_store.search([0.15] * 768, "test_namespace", 10, {"category": "test"})
    
    # Verificar resultados
    assert len(results) == 2
    assert all(result["metadata"]["category"] == "test" for result in results)

@pytest.mark.asyncio
async def test_memory_store_delete(memory_store):
    """Prueba la eliminación de un vector en memoria."""
    # Almacenar un vector
    id = await memory_store.store([0.1] * 768, "Texto de prueba", {"category": "test"}, "test_namespace")
    
    # Eliminar el vector
    success = await memory_store.delete(id, "test_namespace")
    
    # Verificar resultado
    assert success is True
    
    # Verificar que el vector ya no existe
    result = await memory_store.get(id, "test_namespace")
    assert result is None
    
    # Verificar estadísticas
    assert memory_store.stats["delete_operations"] == 1

@pytest.mark.asyncio
async def test_memory_store_batch_store(memory_store):
    """Prueba el almacenamiento en batch en memoria."""
    # Preparar datos
    vectors = [[0.1] * 768, [0.2] * 768, [0.3] * 768]
    texts = ["Texto 1", "Texto 2", "Texto 3"]
    metadatas = [{"category": "test"}, {"category": "test"}, {"category": "other"}]
    
    # Almacenar en batch
    ids = await memory_store.batch_store(vectors, texts, metadatas, "test_namespace")
    
    # Verificar resultados
    assert len(ids) == 3
    assert all(isinstance(id, str) for id in ids)
    
    # Verificar estadísticas
    assert memory_store.stats["batch_store_operations"] == 1

@pytest.mark.asyncio
async def test_memory_store_get(memory_store):
    """Prueba la recuperación de un vector en memoria."""
    # Almacenar un vector
    vector = [0.1] * 768
    text = "Texto de prueba"
    metadata = {"category": "test"}
    
    id = await memory_store.store(vector, text, metadata, "test_namespace")
    
    # Recuperar el vector
    result = await memory_store.get(id, "test_namespace")
    
    # Verificar resultado
    assert result is not None
    assert result["id"] == id
    assert result["text"] == text
    assert result["metadata"] == metadata
    assert result["vector"] == vector
    
    # Verificar estadísticas
    assert memory_store.stats["get_operations"] == 1

@pytest.mark.asyncio
async def test_memory_store_get_stats(memory_store):
    """Prueba la obtención de estadísticas en memoria."""
    # Realizar algunas operaciones
    await memory_store.store([0.1] * 768, "Texto 1", {"category": "test"}, "namespace1")
    await memory_store.store([0.2] * 768, "Texto 2", {"category": "test"}, "namespace2")
    await memory_store.search([0.15] * 768, "namespace1", 2)
    
    # Obtener estadísticas
    stats = await memory_store.get_stats()
    
    # Verificar estadísticas
    assert "store_operations" in stats
    assert stats["store_operations"] == 2
    assert "search_operations" in stats
    assert stats["search_operations"] == 1
    assert "total_vectors" in stats
    assert stats["total_vectors"] == 2
    assert "namespaces" in stats
    assert stats["namespaces"] == 2
    assert "namespace_counts" in stats
    assert len(stats["namespace_counts"]) == 2

# Pruebas para PineconeVectorStore

@pytest.mark.asyncio
async def test_pinecone_store_store(pinecone_store, mock_pinecone_client):
    """Prueba el almacenamiento de un vector en Pinecone."""
    # Almacenar un vector
    vector = [0.1] * 768
    text = "Texto de prueba"
    metadata = {"category": "test"}
    
    id = await pinecone_store.store(vector, text, metadata, "test_namespace")
    
    # Verificar que se generó un ID
    assert id is not None
    assert isinstance(id, str)
    
    # Verificar que se llamó al cliente de Pinecone
    mock_pinecone_client.upsert.assert_called_once()
    
    # Verificar estadísticas
    assert pinecone_store.stats["store_operations"] == 1

@pytest.mark.asyncio
async def test_pinecone_store_search(pinecone_store, mock_pinecone_client):
    """Prueba la búsqueda de vectores similares en Pinecone."""
    # Buscar vectores similares
    results = await pinecone_store.search([0.15] * 768, "test_namespace", 2)
    
    # Verificar que se llamó al cliente de Pinecone
    mock_pinecone_client.query.assert_called_once()
    
    # Verificar resultados
    assert len(results) == 2
    assert all("id" in result for result in results)
    assert all("text" in result for result in results)
    assert all("metadata" in result for result in results)
    assert all("score" in result for result in results)
    
    # Verificar estadísticas
    assert pinecone_store.stats["search_operations"] == 1

@pytest.mark.asyncio
async def test_pinecone_store_search_with_filter(pinecone_store, mock_pinecone_client):
    """Prueba la búsqueda de vectores con filtro en Pinecone."""
    # Buscar vectores con filtro
    filter = {"category": "test"}
    results = await pinecone_store.search([0.15] * 768, "test_namespace", 10, filter)
    
    # Verificar que se llamó al cliente de Pinecone con el filtro
    mock_pinecone_client.query.assert_called_with([0.15] * 768, 10, "test_namespace", filter)
    
    # Verificar resultados
    assert len(results) == 2

@pytest.mark.asyncio
async def test_pinecone_store_delete(pinecone_store, mock_pinecone_client):
    """Prueba la eliminación de un vector en Pinecone."""
    # Eliminar un vector
    success = await pinecone_store.delete("test_id", "test_namespace")
    
    # Verificar que se llamó al cliente de Pinecone
    mock_pinecone_client.delete.assert_called_once_with(["test_id"], "test_namespace")
    
    # Verificar resultado
    assert success is True
    
    # Verificar estadísticas
    assert pinecone_store.stats["delete_operations"] == 1

@pytest.mark.asyncio
async def test_pinecone_store_batch_store(pinecone_store, mock_pinecone_client):
    """Prueba el almacenamiento en batch en Pinecone."""
    # Preparar datos
    vectors = [[0.1] * 768, [0.2] * 768, [0.3] * 768]
    texts = ["Texto 1", "Texto 2", "Texto 3"]
    metadatas = [{"category": "test"}, {"category": "test"}, {"category": "other"}]
    
    # Almacenar en batch
    ids = await pinecone_store.batch_store(vectors, texts, metadatas, "test_namespace")
    
    # Verificar que se llamó al cliente de Pinecone
    mock_pinecone_client.upsert.assert_called_once()
    
    # Verificar resultados
    assert len(ids) == 3
    assert all(isinstance(id, str) for id in ids)
    
    # Verificar estadísticas
    assert pinecone_store.stats["batch_store_operations"] == 1

@pytest.mark.asyncio
async def test_pinecone_store_get_stats(pinecone_store, mock_pinecone_client):
    """Prueba la obtención de estadísticas en Pinecone."""
    # Obtener estadísticas
    stats = await pinecone_store.get_stats()
    
    # Verificar que se llamó al cliente de Pinecone
    mock_pinecone_client.get_stats.assert_called_once()
    
    # Verificar estadísticas
    assert "store_operations" in stats
    assert "search_operations" in stats
    assert "client_stats" in stats

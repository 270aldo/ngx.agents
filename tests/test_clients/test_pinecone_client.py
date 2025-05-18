"""
Pruebas para el cliente de Pinecone.

Este módulo contiene pruebas unitarias para el cliente de Pinecone,
verificando su funcionamiento con mocks y en modo real.
"""

import asyncio
import os
import pytest
from unittest.mock import MagicMock, patch

from clients.pinecone.pinecone_client import PineconeClient

@pytest.fixture
def mock_pinecone_client():
    """Fixture para crear un cliente de Pinecone en modo mock."""
    client = PineconeClient({
        "api_key": "test_api_key",
        "environment": "test-env",
        "index_name": "test-index",
        "dimension": 768,
        "metric": "cosine"
    })
    # Asegurar que estamos en modo mock
    client.client = {"mock": True}
    return client

@pytest.fixture
def real_pinecone_client():
    """
    Fixture para crear un cliente de Pinecone real.
    
    Este fixture solo se usa si hay una API key de Pinecone en el entorno.
    """
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        pytest.skip("No se encontró PINECONE_API_KEY en el entorno. Saltando pruebas reales.")
    
    client = PineconeClient({
        "api_key": api_key,
        "environment": os.environ.get("PINECONE_ENVIRONMENT", "us-west1-gcp"),
        "index_name": os.environ.get("PINECONE_INDEX_NAME", "ngx-embeddings-test"),
        "dimension": 768,
        "metric": "cosine"
    })
    
    # Verificar que no estamos en modo mock
    if client.client.get("mock", True):
        pytest.skip("No se pudo inicializar el cliente de Pinecone. Saltando pruebas reales.")
    
    return client

@pytest.mark.asyncio
async def test_upsert_mock(mock_pinecone_client):
    """Prueba la operación de upsert en modo mock."""
    # Preparar vectores de prueba
    vectors = [
        {
            "id": "test1",
            "values": [0.1] * 768,
            "metadata": {"text": "Texto de prueba 1"}
        },
        {
            "id": "test2",
            "values": [0.2] * 768,
            "metadata": {"text": "Texto de prueba 2"}
        }
    ]
    
    # Ejecutar upsert
    result = await mock_pinecone_client.upsert(vectors, "test_namespace")
    
    # Verificar resultado
    assert "upserted_count" in result
    assert result["upserted_count"] == 2
    
    # Verificar estadísticas
    assert mock_pinecone_client.stats["upsert_operations"] == 1
    assert len(mock_pinecone_client.stats["latency_ms"]) == 1

@pytest.mark.asyncio
async def test_query_mock(mock_pinecone_client):
    """Prueba la operación de query en modo mock."""
    # Preparar vector de consulta
    vector = [0.1] * 768
    
    # Ejecutar query
    result = await mock_pinecone_client.query(vector, 3, "test_namespace")
    
    # Verificar resultado
    assert "matches" in result
    assert len(result["matches"]) <= 3
    
    # Verificar estadísticas
    assert mock_pinecone_client.stats["query_operations"] == 1
    assert len(mock_pinecone_client.stats["latency_ms"]) == 1

@pytest.mark.asyncio
async def test_delete_mock(mock_pinecone_client):
    """Prueba la operación de delete en modo mock."""
    # Preparar IDs a eliminar
    ids = ["test1", "test2"]
    
    # Ejecutar delete
    result = await mock_pinecone_client.delete(ids, "test_namespace")
    
    # Verificar resultado
    assert "deleted_count" in result
    assert result["deleted_count"] == 2
    
    # Verificar estadísticas
    assert mock_pinecone_client.stats["delete_operations"] == 1
    assert len(mock_pinecone_client.stats["latency_ms"]) == 1

@pytest.mark.asyncio
async def test_get_stats_mock(mock_pinecone_client):
    """Prueba la obtención de estadísticas en modo mock."""
    # Ejecutar get_stats
    stats = await mock_pinecone_client.get_stats()
    
    # Verificar resultado
    assert "index_name" in stats
    assert stats["index_name"] == "test-index"
    assert "environment" in stats
    assert stats["environment"] == "test-env"
    assert "dimension" in stats
    assert stats["dimension"] == 768
    assert "metric" in stats
    assert stats["metric"] == "cosine"
    assert "mock_mode" in stats
    assert stats["mock_mode"] is True

@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get("PINECONE_API_KEY"), reason="No se encontró PINECONE_API_KEY en el entorno")
async def test_real_pinecone_operations(real_pinecone_client):
    """
    Prueba operaciones reales en Pinecone.
    
    Esta prueba solo se ejecuta si hay una API key de Pinecone en el entorno.
    """
    # Preparar vectores de prueba
    vectors = [
        {
            "id": "test_real_1",
            "values": [0.1] * 768,
            "metadata": {"text": "Texto de prueba real 1", "test": True}
        },
        {
            "id": "test_real_2",
            "values": [0.2] * 768,
            "metadata": {"text": "Texto de prueba real 2", "test": True}
        }
    ]
    
    namespace = "test_namespace_real"
    
    try:
        # 1. Upsert
        upsert_result = await real_pinecone_client.upsert(vectors, namespace)
        assert "upserted_count" in upsert_result
        
        # Esperar a que Pinecone indexe los vectores
        await asyncio.sleep(1)
        
        # 2. Query
        query_result = await real_pinecone_client.query([0.1] * 768, 5, namespace, {"test": True})
        assert "matches" in query_result
        assert len(query_result["matches"]) > 0
        
        # 3. Get stats
        stats = await real_pinecone_client.get_stats()
        assert "index_name" in stats
        assert "mock_mode" in stats
        assert stats["mock_mode"] is False
        
    finally:
        # 4. Cleanup - Delete
        await real_pinecone_client.delete(["test_real_1", "test_real_2"], namespace)

@pytest.mark.asyncio
async def test_initialize_client_with_invalid_credentials():
    """Prueba la inicialización del cliente con credenciales inválidas."""
    # Crear cliente con API key inválida
    client = PineconeClient({
        "api_key": "invalid_api_key",
        "environment": "test-env",
        "index_name": "test-index"
    })
    
    # Verificar que estamos en modo mock debido a credenciales inválidas
    assert client.client.get("mock", False) is True
    
    # Verificar que las operaciones funcionan en modo mock
    result = await client.query([0.1] * 768, 3, "test_namespace")
    assert "matches" in result

@pytest.mark.asyncio
async def test_error_handling(mock_pinecone_client):
    """Prueba el manejo de errores en el cliente."""
    # Simular un error en la operación de upsert
    with patch.object(mock_pinecone_client, "upsert", side_effect=Exception("Error simulado")):
        # Intentar ejecutar una operación que fallará
        result = await mock_pinecone_client.upsert([], "test_namespace")
        
        # Verificar que se devuelve un resultado de error
        assert "error" in result
        assert "Error simulado" in result["error"]
        
        # Verificar que se incrementa el contador de errores
        assert mock_pinecone_client.stats["errors"] == 1

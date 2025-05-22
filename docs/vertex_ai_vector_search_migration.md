# Migración de Pinecone a Vertex AI Vector Search

Este documento describe el proceso de migración del almacenamiento vectorial de Pinecone a Vertex AI Vector Search, aprovechando la integración nativa con el ecosistema de Google Cloud.

## Ventajas de Vertex AI Vector Search

1. **Integración nativa con el modelo text-embedding-large-exp-03-07**:
   - Optimización específica para los embeddings de Google
   - Menor latencia al mantener todo dentro del mismo ecosistema
   - Procesamiento más eficiente de vectores de alta dimensionalidad (3072)

2. **Vertex AI RAG Engine**:
   - Pipeline completo y optimizado para Retrieval Augmented Generation
   - Chunking inteligente que preserva mejor el contexto semántico
   - Indexación y recuperación optimizadas específicamente para los modelos de Google
   - Capacidades avanzadas de filtrado y ranking de resultados

3. **Ventajas operativas**:
   - Gestión unificada (un solo proveedor para embeddings y almacenamiento vectorial)
   - Monitoreo y telemetría integrados con el resto de servicios de Google
   - Escalabilidad automática sin necesidad de gestionar infraestructura adicional

4. **Consideraciones de costo-beneficio**:
   - Reducción de costos al eliminar la transferencia de datos entre servicios
   - Optimizaciones específicas que pueden reducir el número total de llamadas necesarias

## Componentes implementados

### 1. Cliente de Vertex AI Vector Search

El cliente `VertexVectorSearchClient` proporciona una interfaz para interactuar con Vertex AI Vector Search, con funcionalidades para:

- Crear y gestionar índices vectoriales
- Insertar y actualizar vectores (upsert)
- Consultar vectores similares
- Eliminar vectores
- Obtener estadísticas

### 2. Adaptador de Vector Store

El adaptador `VertexVectorStore` implementa la interfaz `VectorStoreAdapter` utilizando Vertex AI Vector Search, manteniendo compatibilidad con el resto del sistema.

### 3. Integración con EmbeddingsManager

Se ha actualizado el `EmbeddingsManager` para soportar Vertex AI Vector Search como opción de almacenamiento vectorial, permitiendo una migración transparente.

## Configuración

Para utilizar Vertex AI Vector Search, se deben configurar las siguientes variables de entorno:

```bash
# Configuración general
VECTOR_STORE_TYPE=vertex  # Usar Vertex AI Vector Search en lugar de Pinecone o memoria

# Configuración de Google Cloud
GOOGLE_CLOUD_PROJECT=tu-proyecto-id
VERTEX_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/credenciales.json

# Configuración de Vertex AI Vector Search
VERTEX_VECTOR_SEARCH_INDEX=ngx-embeddings
VERTEX_VECTOR_SEARCH_ENDPOINT=ngx-embeddings-endpoint
VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID=ngx-embeddings-deployed
VERTEX_VECTOR_DIMENSION=3072
VERTEX_VECTOR_DISTANCE_MEASURE=DOT_PRODUCT_DISTANCE

# Configuración del modelo de embeddings
VERTEX_EMBEDDING_MODEL=text-embedding-large-exp-03-07
```

## Uso

El uso del sistema de embeddings sigue siendo el mismo, ya que la migración es transparente para los componentes que utilizan el `EmbeddingsManager`:

```python
from core.embeddings_manager import embeddings_manager

# Generar embedding
embedding = await embeddings_manager.generate_embedding("Texto de ejemplo")

# Almacenar embedding
embedding_id = await embeddings_manager.store_embedding(
    text="Texto de ejemplo",
    embedding=embedding,
    metadata={"categoria": "ejemplo"},
    namespace="mi-namespace"
)

# Buscar embeddings similares
resultados = await embeddings_manager.search_similar(
    query="Consulta de ejemplo",
    namespace="mi-namespace",
    top_k=5,
    filter={"categoria": "ejemplo"}
)
```

## Migración de datos existentes

Para migrar datos existentes de Pinecone a Vertex AI Vector Search, se puede utilizar el siguiente enfoque:

1. Configurar temporalmente ambos sistemas (Pinecone y Vertex AI Vector Search)
2. Extraer embeddings de Pinecone
3. Insertar embeddings en Vertex AI Vector Search
4. Verificar la migración
5. Cambiar la configuración para usar exclusivamente Vertex AI Vector Search

Ejemplo de script de migración:

```python
import asyncio
import os
from core.embeddings_manager import EmbeddingsManager
from clients.pinecone.pinecone_client import PineconeClient
from infrastructure.adapters.vector_store_adapter import PineconeVectorStore
from clients.vertex_ai.vector_search_client import VertexVectorSearchClient
from infrastructure.adapters.vertex_vector_store_adapter import VertexVectorStore

async def migrar_embeddings(namespace_origen, namespace_destino=None):
    """Migra embeddings de Pinecone a Vertex AI Vector Search."""
    if namespace_destino is None:
        namespace_destino = namespace_origen
    
    # Configurar cliente de Pinecone
    pinecone_config = {
        "api_key": os.environ.get("PINECONE_API_KEY"),
        "environment": os.environ.get("PINECONE_ENVIRONMENT"),
        "index_name": os.environ.get("PINECONE_INDEX_NAME")
    }
    pinecone_client = PineconeClient(pinecone_config)
    pinecone_store = PineconeVectorStore(pinecone_client)
    
    # Configurar cliente de Vertex AI Vector Search
    vertex_config = {
        "project_id": os.environ.get("GOOGLE_CLOUD_PROJECT"),
        "location": os.environ.get("VERTEX_LOCATION"),
        "index_name": os.environ.get("VERTEX_VECTOR_SEARCH_INDEX")
    }
    vertex_client = VertexVectorSearchClient(vertex_config)
    vertex_store = VertexVectorStore(vertex_client)
    
    # Obtener todos los embeddings de Pinecone
    # Nota: Esto es una simplificación, en la práctica se necesitaría
    # paginar los resultados para manejar grandes volúmenes de datos
    import random
    random_vector = [random.uniform(-1, 1) for _ in range(768)]
    resultados = await pinecone_store.search(
        vector=random_vector,
        namespace=namespace_origen,
        top_k=10000  # Ajustar según el volumen de datos
    )
    
    print(f"Se encontraron {len(resultados)} embeddings para migrar")
    
    # Migrar embeddings a Vertex AI Vector Search
    for resultado in resultados:
        id = resultado.get("id")
        texto = resultado.get("text")
        metadata = resultado.get("metadata", {})
        
        # Obtener el vector original
        embedding_completo = await pinecone_store.get(id, namespace_origen)
        if not embedding_completo:
            print(f"No se pudo obtener el embedding completo para ID: {id}")
            continue
        
        vector = embedding_completo.get("vector", [])
        
        # Almacenar en Vertex AI Vector Search
        await vertex_store.store(
            vector=vector,
            text=texto,
            metadata=metadata,
            namespace=namespace_destino,
            id=id  # Mantener el mismo ID para facilitar la transición
        )
    
    print(f"Migración completada: {len(resultados)} embeddings migrados")

if __name__ == "__main__":
    asyncio.run(migrar_embeddings("mi-namespace"))
```

## Pruebas

Se ha implementado un script de prueba `scripts/test_vertex_vector_search.py` que verifica la funcionalidad básica del adaptador de Vertex AI Vector Search, incluyendo:

- Generación y almacenamiento de embeddings
- Búsqueda de embeddings similares
- Búsqueda con filtros
- Recuperación de embeddings específicos
- Eliminación de embeddings
- Obtención de estadísticas

Para ejecutar las pruebas:

```bash
python scripts/test_vertex_vector_search.py
```

## Consideraciones para producción

1. **Escalabilidad**: Vertex AI Vector Search escala automáticamente, pero es importante monitorear el uso y los costos.

2. **Latencia**: La latencia puede variar según la región y la carga. Se recomienda realizar pruebas de rendimiento en condiciones similares a producción.

3. **Costos**: Monitorear los costos asociados con:
   - Almacenamiento de vectores
   - Operaciones de consulta
   - Operaciones de upsert
   - Transferencia de datos

4. **Respaldo**: Implementar estrategias de respaldo para los datos críticos.

5. **Monitoreo**: Utilizar Cloud Monitoring para supervisar el rendimiento y la disponibilidad del servicio.

## Conclusión

La migración a Vertex AI Vector Search proporciona una solución más integrada y optimizada para el almacenamiento y búsqueda de embeddings, aprovechando al máximo el ecosistema de Google Cloud. La implementación mantiene la compatibilidad con el resto del sistema, permitiendo una migración transparente y sin interrupciones.

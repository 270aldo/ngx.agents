# Guía del Gestor de Embeddings

## Introducción

El Gestor de Embeddings es un componente fundamental que permite mejorar la comprensión semántica, implementar búsqueda basada en similitud y habilitar recomendaciones personalizadas en todo el sistema NGX Agents.

Esta guía explica cómo utilizar el Gestor de Embeddings y su Adaptador para integrar capacidades de embeddings en diferentes componentes del sistema.

## Arquitectura

El sistema de embeddings está compuesto por tres componentes principales:

1. **EmbeddingClient**: Cliente específico para Vertex AI Embeddings que maneja la generación de embeddings y la caché.
2. **EmbeddingsManager**: Componente central que gestiona la generación, almacenamiento y búsqueda de embeddings.
3. **EmbeddingAdapter**: Adaptador que proporciona una interfaz simplificada para otros componentes del sistema.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Componentes    │     │  Embedding      │     │  Embeddings     │
│  del Sistema    │────▶│  Adapter        │────▶│  Manager        │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │                 │
                                               │  Embedding      │
                                               │  Client         │
                                               │                 │
                                               └────────┬────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │                 │
                                               │  Vertex AI      │
                                               │  API            │
                                               │                 │
                                               └─────────────────┘
```

## Configuración

### Variables de Entorno

El sistema de embeddings utiliza las siguientes variables de entorno:

#### Configuración General

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `EMBEDDING_SIMILARITY_THRESHOLD` | Umbral de similitud para búsquedas | `0.7` |
| `EMBEDDING_VECTOR_DIMENSION` | Dimensión de los vectores de embedding | `768` |
| `VECTOR_STORE_TYPE` | Tipo de almacenamiento vectorial (`memory` o `pinecone`) | `memory` |

#### Configuración de Vertex AI

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Ruta al archivo de credenciales de Google Cloud | - |
| `GOOGLE_CLOUD_PROJECT` | ID del proyecto de Google Cloud | - |
| `VERTEX_LOCATION` | Ubicación de Vertex AI | `us-central1` |
| `VERTEX_EMBEDDING_MODEL` | Modelo de embeddings a utilizar | `textembedding-gecko` |

#### Configuración de Caché

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `USE_REDIS_CACHE` | Usar Redis para caché | `false` |
| `REDIS_URL` | URL de conexión a Redis | - |
| `EMBEDDING_CACHE_TTL` | Tiempo de vida del caché en segundos | `86400` (24 horas) |

#### Configuración de Pinecone

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `PINECONE_API_KEY` | API key de Pinecone | - |
| `PINECONE_ENVIRONMENT` | Entorno de Pinecone | `us-west1-gcp` |
| `PINECONE_INDEX_NAME` | Nombre del índice de Pinecone | `ngx-embeddings` |
| `PINECONE_DIMENSION` | Dimensión de los vectores en Pinecone | `768` |
| `PINECONE_METRIC` | Métrica de similitud en Pinecone | `cosine` |

## Almacenamiento Vectorial

El Gestor de Embeddings soporta dos tipos de almacenamiento vectorial:

### Almacenamiento en Memoria

El almacenamiento en memoria es la opción por defecto y es adecuado para desarrollo y pruebas. Los embeddings se almacenan en memoria RAM y se pierden cuando se reinicia la aplicación.

Para usar el almacenamiento en memoria:

```python
# No se requiere configuración adicional, es el valor por defecto
os.environ["VECTOR_STORE_TYPE"] = "memory"
```

### Almacenamiento en Pinecone

[Pinecone](https://www.pinecone.io/) es una base de datos vectorial escalable y gestionada en la nube. Es adecuada para entornos de producción y permite búsquedas eficientes en grandes colecciones de embeddings.

Para usar Pinecone:

```python
# Configurar Pinecone
os.environ["VECTOR_STORE_TYPE"] = "pinecone"
os.environ["PINECONE_API_KEY"] = "tu-api-key"
os.environ["PINECONE_ENVIRONMENT"] = "us-west1-gcp"
os.environ["PINECONE_INDEX_NAME"] = "ngx-embeddings"
```

## Uso Básico

### Generación de Embeddings

Para generar embeddings para un texto:

```python
from infrastructure.adapters.embedding_adapter import embedding_adapter

# Generar embedding para un texto
embedding = await embedding_adapter.generate_embedding("Texto de ejemplo")

# Generar embeddings en batch
texts = ["Texto 1", "Texto 2", "Texto 3"]
embeddings = await embedding_adapter.batch_generate_embeddings(texts)
```

### Almacenamiento de Embeddings

Para almacenar textos con sus embeddings:

```python
# Almacenar texto con metadatos
metadata = {
    "category": "ejemplo",
    "priority": 1,
    "user_id": "user123"
}
embedding_id = await embedding_adapter.store_text("Texto de ejemplo", metadata, "namespace_ejemplo")
```

### Búsqueda por Similitud

Para buscar textos similares:

```python
# Búsqueda básica
results = await embedding_adapter.find_similar("Consulta de ejemplo", "namespace_ejemplo", top_k=5)

# Búsqueda con filtro de metadatos (útil con Pinecone)
filter = {"category": "ejemplo", "priority": 1}
results = await embedding_adapter.find_similar("Consulta de ejemplo", "namespace_ejemplo", top_k=5, filter=filter)

# Procesar resultados
for result in results:
    print(f"Texto: {result['text']}")
    print(f"Similitud: {result['similarity']}")
    print(f"Metadatos: {result['metadata']}")
```

### Clustering de Textos

Para agrupar textos en clusters basados en similitud semántica:

```python
# Textos para clustering
texts = [
    "Ejemplo 1",
    "Ejemplo 2",
    "Ejemplo 3",
    # ...
]

# Realizar clustering
result = await embedding_adapter.cluster_texts(texts, n_clusters=3)

# Procesar clusters
for cluster_id, items in result["clusters"].items():
    print(f"Cluster {cluster_id}:")
    for item in items:
        print(f"  - {item['text']}")
```

## Integración con Otros Componentes

### Integración con Analizador de Intenciones

El Gestor de Embeddings puede integrarse con el Analizador de Intenciones para mejorar la comprensión de las consultas de los usuarios:

```python
from core.intent_analyzer_optimized import IntentAnalyzerOptimized
from infrastructure.adapters.embedding_adapter import embedding_adapter

class EnhancedIntentAnalyzer(IntentAnalyzerOptimized):
    async def analyze(self, query, context=None):
        # Intentar análisis tradicional
        result = await super().analyze(query, context)
        
        # Si la confianza es baja, usar embeddings como fallback
        if result["confidence"] < 0.5:
            similar_queries = await embedding_adapter.find_similar(query, "intent_queries", top_k=3)
            
            if similar_queries and similar_queries[0]["similarity"] > 0.8:
                # Usar la intención de la consulta más similar
                result["intent"] = similar_queries[0]["metadata"]["intent"]
                result["confidence"] = similar_queries[0]["similarity"]
                result["semantic_match"] = True
                result["similar_queries"] = similar_queries
        
        return result
```

### Integración con Gestor de Estado

El Gestor de Embeddings puede integrarse con el Gestor de Estado para almacenar y recuperar embeddings de usuario:

```python
from core.state_manager_optimized import StateManagerOptimized
from infrastructure.adapters.embedding_adapter import embedding_adapter

class EnhancedStateManager(StateManagerOptimized):
    async def store_user_embedding(self, user_id, text, metadata=None):
        """Almacena embedding de usuario en el estado."""
        if metadata is None:
            metadata = {}
        
        metadata["user_id"] = user_id
        metadata["timestamp"] = datetime.now().isoformat()
        
        return await embedding_adapter.store_text(text, metadata, f"user_{user_id}")
    
    async def find_similar_user_queries(self, user_id, query, top_k=5):
        """Encuentra consultas similares del usuario."""
        return await embedding_adapter.find_similar(query, f"user_{user_id}", top_k)
```

## Casos de Uso Avanzados

### Recomendaciones Personalizadas

```python
async def generate_personalized_recommendations(user_id, user_preferences):
    # Generar embedding para las preferencias del usuario
    preferences_embedding = await embedding_adapter.generate_embedding(user_preferences)
    
    # Buscar contenido similar basado en el embedding
    similar_content = await embedding_adapter.find_similar_by_embedding(
        preferences_embedding, 
        namespace="content_library",
        top_k=10
    )
    
    return similar_content
```

### Detección de Duplicados

```python
async def detect_duplicates(new_content, threshold=0.95):
    # Generar embedding para el nuevo contenido
    new_embedding = await embedding_adapter.generate_embedding(new_content)
    
    # Buscar contenido similar
    similar_content = await embedding_adapter.find_similar_by_embedding(
        new_embedding,
        namespace="content_library",
        top_k=5
    )
    
    # Filtrar por umbral de similitud
    duplicates = [item for item in similar_content if item["similarity"] >= threshold]
    
    return duplicates
```

### Análisis de Tendencias

```python
async def analyze_trends(queries, n_clusters=5):
    # Realizar clustering de consultas
    clusters = await embedding_adapter.cluster_texts(queries, n_clusters)
    
    # Analizar cada cluster
    trends = []
    for cluster_id, items in clusters["clusters"].items():
        # Encontrar la consulta más representativa del cluster
        representative = items[0]["text"]
        
        # Contar items en el cluster
        count = len(items)
        
        trends.append({
            "cluster_id": cluster_id,
            "representative": representative,
            "count": count,
            "percentage": count / len(queries) * 100
        })
    
    # Ordenar por frecuencia
    trends.sort(key=lambda x: x["count"], reverse=True)
    
    return trends
```

## Monitoreo y Telemetría

El Gestor de Embeddings incluye telemetría detallada para monitorear su rendimiento:

```python
# Obtener estadísticas
stats = await embedding_adapter.get_stats()

# Estadísticas del gestor
manager_stats = stats["manager_stats"]
print(f"Generaciones de embedding: {manager_stats['embedding_generations']}")
print(f"Operaciones de búsqueda: {manager_stats['search_operations']}")

# Estadísticas del cliente
client_stats = stats["client_stats"]
print(f"Cache hits: {client_stats['cache_hits']}")
print(f"Cache misses: {client_stats['cache_misses']}")
```

## Consideraciones de Rendimiento

### Caché

El sistema utiliza caché en memoria y opcionalmente Redis para mejorar el rendimiento de la generación de embeddings:

```python
# Configurar caché con Redis
os.environ["USE_REDIS_CACHE"] = "true"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["EMBEDDING_CACHE_TTL"] = "86400"  # 24 horas
```

### Batch Processing

Utilice los métodos batch para procesar múltiples textos en una sola llamada:

```python
# Generar embeddings en batch
texts = ["Texto 1", "Texto 2", "Texto 3"]
embeddings = await embedding_adapter.batch_generate_embeddings(texts)

# Almacenar embeddings en batch
metadatas = [{"category": "cat1"}, {"category": "cat2"}, {"category": "cat3"}]
ids = await embeddings_manager.batch_store_embeddings(texts, embeddings, metadatas, "namespace_ejemplo")
```

### Namespaces

Organice sus embeddings en namespaces para mejorar la eficiencia de las búsquedas:

```python
# Almacenar en diferentes namespaces
await embedding_adapter.store_text("Texto de producto", metadata, "productos")
await embedding_adapter.store_text("Texto de usuario", metadata, "usuarios")

# Buscar solo en un namespace específico
results = await embedding_adapter.find_similar("Consulta", "productos", top_k=5)
```

### Dimensionalidad

El modelo predeterminado genera embeddings de 768 dimensiones. Esta dimensión debe coincidir con la configurada en Pinecone:

```python
os.environ["EMBEDDING_VECTOR_DIMENSION"] = "768"
os.environ["PINECONE_DIMENSION"] = "768"
```

## Solución de Problemas

### Errores Comunes

#### Errores de Vertex AI

- **Error de Autenticación**: Verifique que las credenciales de Google Cloud estén correctamente configuradas.
- **Error de Conexión**: Verifique la conectividad con la API de Vertex AI.
- **Error de Caché**: Si utiliza Redis, verifique que el servicio esté disponible y correctamente configurado.

#### Errores de Pinecone

- **Error de API Key**: Verifique que la API key de Pinecone sea válida.
- **Error de Índice**: Verifique que el índice exista en Pinecone y tenga la dimensión correcta.
- **Error de Dimensión**: Asegúrese de que la dimensión de los embeddings coincida con la configurada en Pinecone.
- **Error de Cuota**: Verifique que no haya excedido la cuota de su plan de Pinecone.

### Verificación de Configuración

Para verificar la configuración actual del Gestor de Embeddings:

```python
stats = await embedding_adapter.get_stats()
print(f"Tipo de almacenamiento: {stats.get('vector_store_type')}")
print(f"Dimensión de vectores: {stats.get('vector_dimension')}")
```

### Logging

El sistema registra información detallada en los logs:

```python
import logging
logging.getLogger('core.embeddings_manager').setLevel(logging.DEBUG)
```

## Ejemplo de Integración con Pinecone

```python
import os
import asyncio
from infrastructure.adapters.embedding_adapter import embedding_adapter

async def main():
    # Configurar Pinecone
    os.environ["VECTOR_STORE_TYPE"] = "pinecone"
    os.environ["PINECONE_API_KEY"] = "tu-api-key"
    os.environ["PINECONE_ENVIRONMENT"] = "us-west1-gcp"
    os.environ["PINECONE_INDEX_NAME"] = "ngx-embeddings"
    
    # Almacenar textos con metadatos
    texts = ["Texto 1", "Texto 2", "Texto 3"]
    metadatas = [
        {"category": "cat1", "priority": 1},
        {"category": "cat2", "priority": 2},
        {"category": "cat1", "priority": 3}
    ]
    
    # Generar y almacenar embeddings
    embeddings = await embedding_adapter.batch_generate_embeddings(texts)
    ids = await embeddings_manager.batch_store_embeddings(texts, embeddings, metadatas, "ejemplo")
    
    # Buscar con filtro
    filter = {"category": "cat1"}
    results = await embedding_adapter.find_similar("Consulta", "ejemplo", top_k=5, filter=filter)
    
    # Mostrar resultados
    for result in results:
        print(f"Texto: {result['text']}")
        print(f"Similitud: {result['similarity']}")
        print(f"Metadatos: {result['metadata']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Conclusión

El Gestor de Embeddings proporciona una base sólida para implementar capacidades de comprensión semántica en NGX Agents. Con la integración de Pinecone, ahora es posible escalar el almacenamiento y búsqueda de embeddings para aplicaciones de producción. Utilice el Adaptador de Embeddings para integrar estas capacidades en sus componentes de manera sencilla y eficiente.

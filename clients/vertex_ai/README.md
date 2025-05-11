# Cliente Vertex AI

## Descripción
Este módulo proporciona un cliente optimizado para interactuar con Vertex AI de Google Cloud, ofreciendo funcionalidades para generación de texto, embeddings y procesamiento multimodal con caché avanzado, pooling de conexiones y telemetría detallada.

## Características
- **Caché avanzado**: Soporte para caché en memoria y Redis con TTL configurable
- **Pool de conexiones**: Gestión eficiente de conexiones a Vertex AI
- **Telemetría integrada**: Integración con OpenTelemetry para monitoreo y observabilidad
- **Soporte multimodal**: Procesamiento de texto e imágenes
- **Gestión de errores robusta**: Reintentos automáticos y manejo de errores
- **Configuración flexible**: Personalización de parámetros de conexión y caché

## Estructura
- `__init__.py`: Exporta las clases y funciones principales
- `client.py`: Implementación del cliente VertexAIClient
- `cache.py`: Implementación del gestor de caché (CacheManager)
- `connection.py`: Implementación del pool de conexiones (ConnectionPool)
- `decorators.py`: Decoradores útiles como with_retries

## Uso

```python
from clients.vertex_ai import vertex_ai_client

# Inicializar el cliente
await vertex_ai_client.initialize()

# Generar contenido de texto
response = await vertex_ai_client.generate_content(
    prompt="Explica la inteligencia artificial",
    temperature=0.7
)

# Generar embedding
embedding = await vertex_ai_client.generate_embedding(
    text="Ejemplo de texto para embedding"
)

# Procesar contenido multimodal (texto + imagen)
multimodal_response = await vertex_ai_client.process_multimodal(
    prompt="Describe esta imagen:",
    image_data=image_bytes,
    temperature=0.7
)

# Obtener estadísticas
stats = await vertex_ai_client.get_stats()
```

## Configuración
El cliente se puede configurar mediante variables de entorno:

- `USE_REDIS_CACHE`: Habilitar caché Redis (true/false)
- `REDIS_URL`: URL de conexión a Redis
- `VERTEX_CACHE_TTL`: Tiempo de vida para entradas de caché (segundos)
- `VERTEX_MAX_CACHE_SIZE`: Tamaño máximo del caché en memoria (MB)
- `VERTEX_MAX_CONNECTIONS`: Número máximo de conexiones en el pool

## Pruebas
Las pruebas del cliente se encuentran en `tests/components/test_vertex_ai_client_optimized.py` y se pueden ejecutar con:

```bash
python -m pytest tests/components/test_vertex_ai_client_optimized.py -v
```

## Dependencias
- `google-cloud-aiplatform`: SDK de Vertex AI
- `opentelemetry-*`: Paquetes para telemetría
- `redis`: Opcional, para soporte de caché Redis

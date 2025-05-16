# Cliente Vertex AI

## Descripción
Este módulo proporciona un cliente optimizado para interactuar con Vertex AI de Google Cloud, ofreciendo funcionalidades para generación de texto, embeddings y procesamiento multimodal con caché avanzado, pooling de conexiones y telemetría detallada.

## Características
- **Sistema de caché avanzado**:
  - Arquitectura multinivel (L1: memoria, L2: Redis)
  - Múltiples políticas de evicción (LRU, LFU, FIFO, Híbrida)
  - Compresión automática para valores grandes
  - Particionamiento para mejor rendimiento
  - Invalidación por patrones
  - Prefetching de claves relacionadas
  - Telemetría detallada
- **Pool de conexiones**: Gestión eficiente de conexiones a Vertex AI
- **Telemetría integrada**: Integración con OpenTelemetry para monitoreo y observabilidad
- **Soporte multimodal**: Procesamiento de texto e imágenes
- **Gestión de errores robusta**: Reintentos automáticos y manejo de errores
- **Configuración flexible**: Personalización de parámetros de conexión y caché
- **Monitoreo y alertas**: Sistema de monitoreo para detectar problemas de rendimiento

## Estructura
- `__init__.py`: Exporta las clases y funciones principales
- `client.py`: Implementación del cliente VertexAIClient
- `cache.py`: Implementación del gestor de caché (CacheManager)
- `connection.py`: Implementación del pool de conexiones (ConnectionPool)
- `decorators.py`: Decoradores útiles como with_retries

## Uso

### Uso Básico

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

### Uso Avanzado del Sistema de Caché

```python
# Uso de namespaces para separar caché por usuario
response = await vertex_ai_client.generate_content(
    prompt="Explica la inteligencia artificial",
    temperature=0.7,
    cache_namespace="user_123"
)

# Invalidar caché por patrón
pattern = "vertex:generate_content:user_123:*"
invalidated_count = await vertex_ai_client.cache_manager.invalidate_pattern(pattern)
print(f"Se invalidaron {invalidated_count} entradas de caché")

# Inicializar monitoreo
from clients.vertex_ai.monitoring import initialize_monitoring, get_monitoring_status
await initialize_monitoring()

# Obtener métricas de salud del caché
status = await get_monitoring_status()
print(f"Hit ratio: {status['health_metrics']['hit_ratio']:.2%}")

# Cliente personalizado con configuración específica
from clients.vertex_ai.client import VertexAIClient

cliente_personalizado = VertexAIClient(
    use_redis_cache=True,
    cache_policy="lru",  # Política LRU (mejor rendimiento en pruebas)
    cache_partitions=8,  # Más particiones para mejor concurrencia
    l1_size_ratio=0.3,   # 30% del caché en memoria (L1)
    prefetch_threshold=0.7,  # Umbral para prefetching
    compression_threshold=1024  # Comprimir valores mayores a 1KB
)
```

## Configuración
El cliente se puede configurar mediante variables de entorno:

### Configuración Básica
- `USE_REDIS_CACHE`: Habilitar caché Redis (true/false)
- `REDIS_URL`: URL de conexión a Redis
- `VERTEX_CACHE_TTL`: Tiempo de vida para entradas de caché (segundos)
- `VERTEX_MAX_CACHE_SIZE`: Tamaño máximo del caché en memoria (MB)
- `VERTEX_MAX_CONNECTIONS`: Número máximo de conexiones en el pool

### Configuración Avanzada de Caché
- `VERTEX_CACHE_POLICY`: Política de evicción ("lru", "lfu", "fifo", "hybrid")
- `VERTEX_CACHE_PARTITIONS`: Número de particiones para el caché
- `VERTEX_L1_SIZE_RATIO`: Proporción del tamaño para caché L1 (0.0-1.0)
- `VERTEX_PREFETCH_THRESHOLD`: Umbral para precarga de claves relacionadas
- `VERTEX_COMPRESSION_THRESHOLD`: Tamaño mínimo para compresión (bytes)
- `VERTEX_COMPRESSION_LEVEL`: Nivel de compresión (1-9)

### Configuración de Monitoreo
- `VERTEX_ALERT_HIT_RATIO_THRESHOLD`: Umbral mínimo para hit ratio (0.0-1.0)
- `VERTEX_ALERT_MEMORY_USAGE_THRESHOLD`: Umbral máximo para uso de memoria (0.0-1.0)
- `VERTEX_ALERT_LATENCY_THRESHOLD_MS`: Umbral máximo para latencia (ms)
- `VERTEX_ALERT_ERROR_RATE_THRESHOLD`: Umbral máximo para tasa de errores (0.0-1.0)
- `VERTEX_MONITORING_INTERVAL`: Intervalo de verificación para alertas (segundos)

## Pruebas
Las pruebas del cliente se encuentran en `tests/components/test_vertex_ai_client_optimized.py` y se pueden ejecutar con:

```bash
python -m pytest tests/components/test_vertex_ai_client_optimized.py -v
```

## Dependencias
- `google-cloud-aiplatform`: SDK de Vertex AI
- `opentelemetry-*`: Paquetes para telemetría
- `redis`: Opcional, para soporte de caché Redis

# Cliente Vertex AI Optimizado

## Introducción

El cliente Vertex AI optimizado proporciona una interfaz centralizada para interactuar con los servicios de Vertex AI de Google Cloud, con características avanzadas como caché, pooling de conexiones, telemetría detallada y manejo robusto de errores.

Este documento describe la API completa del cliente, sus opciones de configuración, patrones de uso recomendados y estrategias de optimización.

## Características Principales

- **Caché avanzado**: Reduce costos y latencia mediante caché en memoria y Redis
- **Pooling de conexiones**: Reutiliza conexiones para mejorar rendimiento
- **Telemetría detallada**: Métricas de uso, latencia y errores
- **Manejo robusto de errores**: Reintentos automáticos y circuit breakers
- **Soporte multimodal**: Procesamiento de texto, imágenes y documentos
- **Compresión de datos**: Optimiza el almacenamiento de respuestas grandes

## Instalación y Configuración

### Requisitos

- Python 3.8+
- Acceso a Google Cloud con permisos para Vertex AI
- Credenciales configuradas en el entorno

### Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `USE_REDIS_CACHE` | Usar Redis para caché | `false` |
| `REDIS_URL` | URL de conexión a Redis | `None` |
| `VERTEX_CACHE_TTL` | Tiempo de vida del caché (segundos) | `3600` |
| `VERTEX_MAX_CACHE_SIZE` | Tamaño máximo del caché en memoria | `1000` |
| `VERTEX_MAX_CONNECTIONS` | Máximo de conexiones en el pool | `10` |

## API del Cliente

### Inicialización

```python
from clients.vertex_ai import vertex_ai_client

# Inicializar el cliente (debe hacerse antes de cualquier operación)
await vertex_ai_client.initialize()

# Al finalizar, cerrar el cliente para liberar recursos
await vertex_ai_client.close()
```

### Generación de Contenido

```python
response = await vertex_ai_client.generate_content(
    prompt="Explica la inteligencia artificial",
    system_instruction="Responde de manera concisa y clara",  # Opcional
    temperature=0.7,  # Opcional, controla aleatoriedad (0.0-1.0)
    max_output_tokens=1024,  # Opcional, limita longitud de respuesta
    top_p=0.95,  # Opcional, núcleo de probabilidad
    top_k=40  # Opcional, top-k sampling
)

# Acceder al texto generado
text = response["text"]

# Acceder a estadísticas de uso
tokens_used = response["usage"]["total_tokens"]
```

#### Parámetros

| Parámetro | Tipo | Descripción | Valor por defecto |
|-----------|------|-------------|-------------------|
| `prompt` | `str` | Texto de entrada para el modelo | (requerido) |
| `system_instruction` | `str` | Instrucción de sistema para el modelo | `None` |
| `temperature` | `float` | Control de aleatoriedad (0.0-1.0) | `0.7` |
| `max_output_tokens` | `int` | Límite de tokens de salida | `None` |
| `top_p` | `float` | Núcleo de probabilidad para muestreo | `None` |
| `top_k` | `int` | Top-k para muestreo | `None` |

#### Respuesta

```json
{
  "text": "La inteligencia artificial (IA) es la simulación de procesos de inteligencia humana por máquinas...",
  "finish_reason": "STOP",
  "usage": {
    "prompt_tokens": 5,
    "completion_tokens": 42,
    "total_tokens": 47
  }
}
```

### Generación de Embeddings

```python
# Generar embedding para un texto
result = await vertex_ai_client.generate_embedding(
    text="Ejemplo de texto para embedding"
)

# Acceder al vector de embedding
embedding = result["embedding"]
dimensions = result["dimensions"]

# Generar embeddings para múltiples textos
batch_result = await vertex_ai_client.batch_embeddings(
    texts=["Texto 1", "Texto 2", "Texto 3"]
)

# Acceder a los vectores
embeddings = batch_result["embeddings"]
```

#### Parámetros para `generate_embedding`

| Parámetro | Tipo | Descripción | Valor por defecto |
|-----------|------|-------------|-------------------|
| `text` | `str` | Texto para generar embedding | (requerido) |

#### Respuesta de `generate_embedding`

```json
{
  "embedding": [0.1, 0.2, ...],
  "dimensions": 768,
  "model": "textembedding-gecko"
}
```

#### Parámetros para `batch_embeddings`

| Parámetro | Tipo | Descripción | Valor por defecto |
|-----------|------|-------------|-------------------|
| `texts` | `List[str]` | Lista de textos para generar embeddings | (requerido) |

#### Respuesta de `batch_embeddings`

```json
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...], ...],
  "dimensions": 768,
  "count": 3,
  "model": "textembedding-gecko"
}
```

### Procesamiento Multimodal

```python
# Procesar imagen y texto
response = await vertex_ai_client.process_multimodal(
    prompt="Describe esta imagen:",
    image_data=image_bytes_or_base64,  # Bytes o string base64
    temperature=0.7,
    max_output_tokens=1024
)

# Acceder al texto generado
description = response["text"]
```

#### Parámetros

| Parámetro | Tipo | Descripción | Valor por defecto |
|-----------|------|-------------|-------------------|
| `prompt` | `str` | Texto de prompt | (requerido) |
| `image_data` | `Union[str, bytes]` | Datos de imagen (base64 o bytes) | (requerido) |
| `temperature` | `float` | Control de aleatoriedad (0.0-1.0) | `0.7` |
| `max_output_tokens` | `int` | Límite de tokens de salida | `None` |

#### Respuesta

```json
{
  "text": "La imagen muestra un paisaje montañoso con un lago en primer plano...",
  "finish_reason": "STOP",
  "usage": {
    "prompt_tokens": 1005,
    "completion_tokens": 42,
    "total_tokens": 1047
  }
}
```

### Procesamiento de Documentos

```python
# Procesar un documento
response = await vertex_ai_client.process_document(
    document_content=document_bytes,
    mime_type="application/pdf",
    processor_id="general-processor"
)

# Acceder al texto extraído
text = response["text"]

# Acceder a entidades extraídas
entities = response["entities"]
```

#### Parámetros

| Parámetro | Tipo | Descripción | Valor por defecto |
|-----------|------|-------------|-------------------|
| `document_content` | `bytes` | Contenido del documento en bytes | (requerido) |
| `mime_type` | `str` | Tipo MIME del documento | (requerido) |
| `processor_id` | `str` | ID del procesador de Document AI | `"general-processor"` |

#### Respuesta

```json
{
  "text": "Contenido extraído del documento...",
  "pages": 5,
  "entities": [
    {
      "type": "person",
      "mention_text": "Juan Pérez",
      "confidence": 0.95
    },
    ...
  ],
  "mime_type": "application/pdf",
  "processor_id": "general-processor"
}
```

### Estadísticas y Monitoreo

```python
# Obtener estadísticas del cliente
stats = await vertex_ai_client.get_stats()

# Limpiar caché
success = await vertex_ai_client.flush_cache()
```

#### Respuesta de `get_stats`

```json
{
  "content_requests": 150,
  "embedding_requests": 75,
  "multimodal_requests": 10,
  "batch_embedding_requests": 5,
  "document_requests": 3,
  "latency_ms": {
    "content_generation": [120, 150, ...],
    "embedding": [50, 45, ...],
    "multimodal": [200, 220, ...]
  },
  "latency_avg_ms": {
    "content_generation": 135.5,
    "embedding": 47.2,
    "multimodal": 210.3
  },
  "tokens": {
    "prompt": 5000,
    "completion": 12000,
    "total": 17000
  },
  "errors": {
    "TimeoutError": 2,
    "ConnectionError": 1
  },
  "cache": {
    "size": 250,
    "max_size": 1000,
    "hits": 80,
    "misses": 160,
    "hit_ratio": 0.33
  },
  "connection_pool": {
    "created": 5,
    "reused": 235,
    "active": 2,
    "max_size": 10
  },
  "initialized": true
}
```

## Manejo de Errores

El cliente implementa un sistema robusto de manejo de errores con reintentos automáticos para errores transitorios.

### Tipos de Errores Comunes

- **TimeoutError**: Tiempo de espera agotado para la solicitud
- **ConnectionError**: Error de conexión con la API
- **ResourceExhaustedError**: Cuota o límite de recursos excedido
- **InvalidArgumentError**: Parámetros de solicitud inválidos
- **PermissionDeniedError**: Permisos insuficientes

### Estrategia de Reintentos

El cliente utiliza una estrategia de backoff exponencial para reintentos:

- Errores de red: 3 reintentos con backoff exponencial
- Errores de cuota: 2 reintentos con backoff exponencial
- Errores de timeout: 2 reintentos con backoff exponencial

### Ejemplo de Manejo de Errores

```python
try:
    response = await vertex_ai_client.generate_content(prompt="Ejemplo")
    if "error" in response:
        # Manejar error en la respuesta
        print(f"Error en la respuesta: {response['error']}")
    else:
        # Procesar respuesta exitosa
        print(response["text"])
except Exception as e:
    # Manejar excepción
    print(f"Error al generar contenido: {e}")
```

## Optimización de Rendimiento

### Estrategias de Caché

El cliente implementa varias estrategias de caché para optimizar rendimiento y costos:

1. **Caché en memoria**: Almacena respuestas recientes en memoria para acceso rápido
2. **Caché distribuido con Redis**: Opcional, permite compartir caché entre instancias
3. **TTL configurable**: Tiempo de vida ajustable por tipo de operación
4. **Invalidación selectiva**: Patrones para invalidar entradas específicas
5. **Compresión**: Comprime respuestas grandes para optimizar almacenamiento

### Configuración Recomendada

| Tipo de Operación | TTL Recomendado | Notas |
|-------------------|-----------------|-------|
| Generación de contenido | 1-24 horas | Depende de la naturaleza del contenido |
| Embeddings | 1-7 días | Los embeddings cambian poco con el tiempo |
| Multimodal | 1-24 horas | Depende del tipo de análisis |
| Documentos | 1-30 días | Los resultados de extracción son estables |

### Optimización de Conexiones

El cliente utiliza un pool de conexiones para reutilizar conexiones y reducir latencia:

1. **Tamaño de pool configurable**: Ajustable según carga esperada
2. **TTL de conexiones**: Renovación periódica para evitar conexiones obsoletas
3. **Distribución equitativa**: Balanceo de carga entre conexiones

## Patrones de Integración

### Patrón 1: Inicialización Temprana

```python
async def startup_event():
    # Inicializar cliente al inicio de la aplicación
    await vertex_ai_client.initialize()

async def shutdown_event():
    # Cerrar cliente al detener la aplicación
    await vertex_ai_client.close()
```

### Patrón 2: Caché Personalizado por Dominio

```python
# Configurar TTL específico para diferentes tipos de consultas
os.environ["VERTEX_CACHE_TTL"] = "7200"  # 2 horas para consultas generales

# Para consultas que requieren datos actualizados, invalidar caché
async def get_weather_forecast(location):
    # Generar clave de caché personalizada
    cache_key = f"weather_{location}_{datetime.now().strftime('%Y%m%d')}"
    
    # Verificar caché manualmente
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Generar respuesta
    prompt = f"Proporciona el pronóstico del tiempo para {location} hoy"
    response = await vertex_ai_client.generate_content(prompt)
    
    # Guardar en caché con TTL corto (1 hora)
    await redis_client.set(cache_key, json.dumps(response), ex=3600)
    
    return response
```

### Patrón 3: Procesamiento por Lotes

```python
async def process_documents(document_urls):
    # Descargar documentos en paralelo
    documents = await download_documents(document_urls)
    
    # Procesar en lotes para optimizar rendimiento
    batch_size = 5
    results = []
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        batch_tasks = [
            vertex_ai_client.process_document(
                document_content=doc["content"],
                mime_type=doc["mime_type"]
            )
            for doc in batch
        ]
        
        # Ejecutar lote en paralelo
        batch_results = await asyncio.gather(*batch_tasks)
        results.extend(batch_results)
    
    return results
```

### Patrón 4: Circuit Breaker

```python
# Implementar circuit breaker para evitar sobrecarga
class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=30):
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = "closed"  # closed, open, half-open
        self.last_failure_time = 0

    async def execute(self, func, *args, **kwargs):
        if self.state == "open":
            # Verificar si ha pasado el tiempo de reset
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker open")
        
        try:
            result = await func(*args, **kwargs)
            
            # Si estaba en half-open y tuvo éxito, cerrar el circuit breaker
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
                
            return result
            
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                self.state = "open"
                
            raise e

# Uso con el cliente Vertex AI
cb = CircuitBreaker()

async def generate_with_circuit_breaker(prompt):
    try:
        return await cb.execute(
            vertex_ai_client.generate_content,
            prompt=prompt
        )
    except Exception as e:
        # Manejar error o usar fallback
        return {"text": "Servicio temporalmente no disponible", "error": str(e)}
```

## Monitoreo y Observabilidad

El cliente emite métricas detalladas que pueden ser monitoreadas en Prometheus, Grafana o Google Cloud Monitoring:

### Métricas Principales

| Métrica | Descripción | Etiquetas |
|---------|-------------|-----------|
| `vertex_ai.client.initializations` | Inicializaciones del cliente | `status` |
| `vertex_ai.client.cache_hits` | Aciertos de caché | `operation` |
| `vertex_ai.client.cache_misses` | Fallos de caché | `operation` |
| `vertex_ai.client.latency` | Latencia de operaciones (ms) | `operation` |
| `vertex_ai.client.tokens` | Tokens utilizados | `type` |
| `vertex_ai.client.errors` | Errores | `operation`, `error_type` |
| `vertex_ai.client.batch_size` | Tamaño de lotes | `operation` |

### Dashboard Recomendado

Se recomienda configurar un dashboard en Grafana con las siguientes visualizaciones:

1. **Tasa de solicitudes**: Solicitudes por minuto por tipo de operación
2. **Latencia**: Percentiles p50, p95, p99 por tipo de operación
3. **Tasa de errores**: Errores por minuto por tipo de operación
4. **Uso de tokens**: Tokens totales por hora/día
5. **Tasa de aciertos de caché**: Ratio de aciertos vs. fallos
6. **Costos estimados**: Basado en uso de tokens

## Herramientas de Diagnóstico

El cliente incluye herramientas para diagnóstico y optimización:

### Script de Optimización de Caché

El script `scripts/optimize_vertex_ai_cache.py` analiza patrones de uso y recomienda configuraciones óptimas:

```bash
# Analizar y mostrar recomendaciones
python scripts/optimize_vertex_ai_cache.py

# Aplicar recomendaciones
python scripts/optimize_vertex_ai_cache.py --apply
```

### Script de Pruebas de Carga

El script `scripts/vertex_ai_load_test.py` permite realizar pruebas de carga con diferentes escenarios:

```bash
# Prueba con carga normal (50 req/s)
python scripts/vertex_ai_load_test.py --scenario normal

# Prueba con carga alta (200 req/s)
python scripts/vertex_ai_load_test.py --scenario high

# Prueba con pico de tráfico (500 req/s durante 1 minuto)
python scripts/vertex_ai_load_test.py --scenario spike
```

## Preguntas Frecuentes

### ¿Cómo puedo reducir costos de Vertex AI?

1. **Optimizar caché**: Aumentar TTL para tipos de consultas estables
2. **Comprimir respuestas**: Habilitar compresión para respuestas grandes
3. **Limitar tokens**: Configurar `max_output_tokens` para limitar respuestas
4. **Batch processing**: Usar `batch_embeddings` en lugar de llamadas individuales

### ¿Cómo puedo mejorar la latencia?

1. **Aumentar pool de conexiones**: Configurar `VERTEX_MAX_CONNECTIONS`
2. **Optimizar caché**: Usar Redis para caché distribuido
3. **Reducir tamaño de prompts**: Prompts más concisos reducen tiempo de procesamiento
4. **Procesamiento asíncrono**: Usar `asyncio.gather` para operaciones en paralelo

### ¿Cómo manejar errores de cuota excedida?

1. **Implementar backoff exponencial**: Aumentar tiempo entre reintentos
2. **Monitorear uso**: Configurar alertas para uso cercano a límites
3. **Solicitar aumento de cuota**: Contactar a Google Cloud para aumentar límites
4. **Distribuir carga**: Distribuir solicitudes a lo largo del tiempo

## Soporte y Contacto

Para problemas o consultas sobre el cliente Vertex AI optimizado, contactar al equipo de infraestructura:

- **Email**: infra-team@example.com
- **Slack**: #vertex-ai-support
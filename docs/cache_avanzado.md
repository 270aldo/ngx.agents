# Sistema de Caché Avanzado para Vertex AI

## Descripción General

El sistema de caché avanzado implementado para el cliente Vertex AI proporciona un mecanismo eficiente para almacenar y recuperar respuestas de la API, reduciendo la latencia y el consumo de recursos. Este documento describe las características, configuración y uso del sistema.

## Características Principales

### Arquitectura Multinivel (L1/L2)

El sistema implementa una arquitectura de caché en dos niveles:

- **L1 (Memoria)**: Almacenamiento rápido en memoria para acceso inmediato.
- **L2 (Redis)**: Almacenamiento distribuido persistente para compartir entre instancias.

### Políticas de Evicción

El sistema soporta múltiples políticas de evicción para adaptarse a diferentes patrones de acceso:

- **LRU (Least Recently Used)**: Elimina los elementos menos usados recientemente.
- **LFU (Least Frequently Used)**: Elimina los elementos menos frecuentemente usados.
- **FIFO (First In First Out)**: Elimina los elementos más antiguos primero.
- **Híbrida**: Combina LRU con factores de frecuencia para un enfoque balanceado.

### Características Avanzadas

- **Compresión Automática**: Comprime automáticamente valores grandes para optimizar el uso de memoria.
- **Particionamiento**: Divide el caché en particiones para mejorar el rendimiento concurrente.
- **Invalidación por Patrones**: Permite invalidar grupos de claves relacionadas con un solo comando.
- **Prefetching**: Precarga claves relacionadas para mejorar la experiencia del usuario.
- **Telemetría Detallada**: Proporciona métricas completas sobre el rendimiento del caché.

## Configuración

### Variables de Entorno

| Variable | Descripción | Valor Predeterminado |
|----------|-------------|---------------------|
| `USE_REDIS_CACHE` | Habilitar caché Redis | `false` |
| `REDIS_URL` | URL de conexión a Redis | `None` |
| `VERTEX_CACHE_TTL` | Tiempo de vida de entradas en segundos | `3600` |
| `VERTEX_MAX_CACHE_SIZE` | Tamaño máximo de caché en MB | `1000` |
| `VERTEX_MAX_CONNECTIONS` | Máximo de conexiones en el pool | `10` |
| `VERTEX_CACHE_POLICY` | Política de evicción (lru, lfu, fifo, hybrid) | `lru` |
| `VERTEX_CACHE_PARTITIONS` | Número de particiones | `4` |
| `VERTEX_L1_SIZE_RATIO` | Proporción del tamaño para L1 | `0.3` |
| `VERTEX_PREFETCH_THRESHOLD` | Umbral para prefetching | `0.7` |
| `VERTEX_COMPRESSION_THRESHOLD` | Umbral para compresión en bytes | `1024` |
| `VERTEX_COMPRESSION_LEVEL` | Nivel de compresión (1-9) | `6` |

### Monitoreo y Alertas

| Variable | Descripción | Valor Predeterminado |
|----------|-------------|---------------------|
| `VERTEX_ALERT_HIT_RATIO_THRESHOLD` | Umbral mínimo para hit ratio | `0.4` (40%) |
| `VERTEX_ALERT_MEMORY_USAGE_THRESHOLD` | Umbral máximo para uso de memoria | `0.85` (85%) |
| `VERTEX_ALERT_LATENCY_THRESHOLD_MS` | Umbral máximo para latencia | `500` ms |
| `VERTEX_ALERT_ERROR_RATE_THRESHOLD` | Umbral máximo para tasa de errores | `0.05` (5%) |
| `VERTEX_MONITORING_INTERVAL` | Intervalo de verificación en segundos | `300` |

## Ejemplos de Configuración

### Escenario 1: Aplicación con Alta Carga y Memoria Limitada

```python
# .env
USE_REDIS_CACHE=true
REDIS_URL=redis://redis:6379/0
VERTEX_CACHE_TTL=1800
VERTEX_MAX_CACHE_SIZE=500
VERTEX_CACHE_POLICY=lfu
VERTEX_COMPRESSION_THRESHOLD=512
VERTEX_COMPRESSION_LEVEL=9
VERTEX_L1_SIZE_RATIO=0.2
```

Este escenario prioriza la eficiencia de memoria:
- Usa Redis para compartir caché entre instancias
- Reduce el TTL a 30 minutos para mantener el caché fresco
- Usa LFU para mantener solo los elementos más frecuentemente accedidos
- Comprime agresivamente (nivel 9) y desde tamaños más pequeños (512 bytes)
- Mantiene solo el 20% del caché en memoria (L1)

### Escenario 2: Aplicación de Alto Rendimiento

```python
# .env
USE_REDIS_CACHE=false
VERTEX_CACHE_TTL=7200
VERTEX_MAX_CACHE_SIZE=2000
VERTEX_CACHE_POLICY=lru
VERTEX_CACHE_PARTITIONS=8
VERTEX_L1_SIZE_RATIO=1.0
VERTEX_COMPRESSION_THRESHOLD=4096
```

Este escenario prioriza la velocidad:
- Usa solo caché en memoria para máxima velocidad
- Aumenta el TTL a 2 horas para maximizar hits
- Usa LRU que tiene mejor rendimiento general
- Aumenta el número de particiones para mejor concurrencia
- Usa todo el espacio para L1 (memoria)
- Solo comprime valores muy grandes (>4KB)

### Escenario 3: Microservicios Distribuidos

```python
# .env
USE_REDIS_CACHE=true
REDIS_URL=redis://redis-master:6379/0
VERTEX_CACHE_TTL=3600
VERTEX_MAX_CACHE_SIZE=500
VERTEX_CACHE_POLICY=hybrid
VERTEX_L1_SIZE_RATIO=0.3
VERTEX_PREFETCH_THRESHOLD=0.8
VERTEX_MONITORING_INTERVAL=60
```

Este escenario está optimizado para un entorno de microservicios:
- Usa Redis para compartir caché entre múltiples servicios
- Usa política híbrida para balancear frecuencia y recencia
- Monitoreo más frecuente (cada minuto)
- Prefetching agresivo para mejorar la experiencia del usuario

## Uso en el Código

### Ejemplo Básico

```python
from clients.vertex_ai.client import vertex_ai_client

async def generate_text(prompt: str):
    response = await vertex_ai_client.generate_content(
        prompt=prompt,
        temperature=0.7,
        max_output_tokens=100
    )
    return response["text"]
```

### Uso Avanzado con Namespaces

```python
async def generate_text_for_user(prompt: str, user_id: str):
    # Usar namespace para separar caché por usuario
    response = await vertex_ai_client.generate_content(
        prompt=prompt,
        temperature=0.7,
        max_output_tokens=100,
        cache_namespace=f"user_{user_id}"
    )
    return response["text"]
```

### Invalidación de Caché

```python
async def invalidate_user_cache(user_id: str):
    # Invalidar todo el caché relacionado con un usuario
    pattern = f"vertex:generate_content:user_{user_id}:*"
    invalidated = await vertex_ai_client.cache_manager.invalidate_pattern(pattern)
    return f"Invalidadas {invalidated} entradas de caché"
```

### Monitoreo

```python
from clients.vertex_ai.monitoring import initialize_monitoring, get_monitoring_status

# Inicializar monitoreo
await initialize_monitoring()

# Obtener estado del monitoreo
status = await get_monitoring_status()
print(f"Hit ratio: {status['health_metrics']['hit_ratio']:.2%}")
```

## Mejores Prácticas

1. **Ajustar Política de Caché**: Usar LRU para la mayoría de los casos, LFU para cuando hay elementos muy populares, y FIFO para datos que cambian constantemente.

2. **Dimensionar Correctamente**: Ajustar el tamaño del caché según la memoria disponible y el volumen de datos.

3. **Usar Namespaces**: Organizar el caché por namespaces para facilitar la invalidación selectiva.

4. **Monitorear Rendimiento**: Vigilar el hit ratio y ajustar la configuración según sea necesario.

5. **Comprimir Selectivamente**: Ajustar el umbral de compresión según el tamaño promedio de las respuestas.

## Diagnóstico y Solución de Problemas

### Hit Ratio Bajo

Posibles causas:
- TTL demasiado corto
- Tamaño de caché insuficiente
- Patrón de acceso muy disperso

Soluciones:
- Aumentar TTL
- Aumentar tamaño de caché
- Revisar patrones de acceso y ajustar política

### Uso de Memoria Alto

Posibles causas:
- Tamaño de caché demasiado grande
- Compresión insuficiente
- Fugas de memoria

Soluciones:
- Reducir tamaño de caché
- Reducir umbral de compresión
- Verificar código para fugas

### Latencia Alta

Posibles causas:
- Sobrecarga de compresión
- Contención en particiones
- Problemas con Redis

Soluciones:
- Ajustar umbral de compresión
- Aumentar número de particiones
- Verificar conexión a Redis

## Conclusión

El sistema de caché avanzado proporciona un mecanismo flexible y eficiente para optimizar el rendimiento del cliente Vertex AI. Al ajustar la configuración según las necesidades específicas de la aplicación, se puede lograr un equilibrio óptimo entre rendimiento, uso de recursos y frescura de los datos.

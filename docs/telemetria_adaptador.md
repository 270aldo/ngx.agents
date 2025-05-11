# Adaptador de Telemetría para NGX Agents

## Descripción General

El adaptador de telemetría proporciona una capa de abstracción para la instrumentación y monitoreo de componentes en NGX Agents. Está diseñado para simplificar la integración con el sistema de telemetría, ofreciendo una interfaz unificada para:

- Medición de tiempos de ejecución
- Seguimiento de operaciones (spans)
- Registro de métricas y eventos
- Monitoreo de errores

El adaptador implementa un patrón de fallback que permite al sistema funcionar incluso cuando el sistema de telemetría no está disponible, registrando información en logs como alternativa.

## Ubicación

```
infrastructure/adapters/telemetry_adapter.py
```

## Características Principales

1. **Singleton global**: Proporciona una instancia única accesible desde cualquier parte del código
2. **Decorador para medición de tiempo**: Facilita la medición del tiempo de ejecución de funciones
3. **Gestión de spans**: Permite crear, anotar y finalizar spans para seguimiento de operaciones
4. **Registro de métricas**: Interfaz simplificada para registrar métricas, contadores e histogramas
5. **Modo mock**: Funciona incluso cuando la telemetría no está disponible

## Uso Básico

### Obtener el Adaptador

```python
from infrastructure.adapters import get_telemetry_adapter

# Obtener la instancia global
telemetry = get_telemetry_adapter()
```

### Medir Tiempo de Ejecución con Decorador

```python
from infrastructure.adapters import measure_execution_time

@measure_execution_time("vertex_ai.generate_content", {"model": "gemini-pro"})
async def generate_content(prompt):
    # Implementación...
    return result
```

### Crear y Gestionar Spans

```python
# Iniciar un span
span = telemetry.start_span("process_user_query", {
    "user_id": user_id,
    "query_length": len(query)
})

try:
    # Añadir atributos
    telemetry.set_span_attribute(span, "intent", intent)
    
    # Registrar eventos
    telemetry.add_span_event(span, "intent_detected", {
        "intent": intent,
        "confidence": confidence
    })
    
    # Procesar...
    result = await process_query(query)
    
    return result
except Exception as e:
    # Registrar excepción
    telemetry.record_exception(span, e)
    raise
finally:
    # Finalizar span
    telemetry.end_span(span)
```

### Registrar Métricas

```python
# Registrar una métrica
telemetry.record_metric("vertex_ai.tokens_used", tokens_used, {
    "model": model_name,
    "operation": operation_type
})

# Incrementar un contador
telemetry.record_counter("vertex_ai.api_calls", 1, {
    "model": model_name,
    "status": "success"
})

# Registrar un valor en un histograma
telemetry.record_histogram("vertex_ai.response_time", response_time, {
    "model": model_name
})
```

## Integración con Vertex AI Client

El cliente Vertex AI está integrado con el adaptador de telemetría para proporcionar métricas detalladas sobre:

1. **Tiempos de respuesta**: Medición del tiempo que tarda cada llamada a la API
2. **Uso de tokens**: Seguimiento del número de tokens utilizados por modelo
3. **Tasas de éxito/error**: Monitoreo de errores y excepciones
4. **Uso de caché**: Efectividad del sistema de caché

Ejemplo de integración:

```python
from infrastructure.adapters import get_telemetry_adapter, measure_execution_time

class VertexAIClient:
    def __init__(self):
        self.telemetry = get_telemetry_adapter()
        
    @measure_execution_time("vertex_ai.generate_content")
    async def generate_content(self, prompt, model="gemini-pro"):
        span = self.telemetry.start_span("vertex_ai.generate_content", {
            "model": model,
            "prompt_length": len(prompt)
        })
        
        try:
            # Verificar caché
            cache_key = self._generate_cache_key(prompt, model)
            cached_result = self._check_cache(cache_key)
            
            if cached_result:
                self.telemetry.add_span_event(span, "cache_hit")
                self.telemetry.record_counter("vertex_ai.cache_hits", 1, {"model": model})
                return cached_result
            
            self.telemetry.add_span_event(span, "cache_miss")
            self.telemetry.record_counter("vertex_ai.cache_misses", 1, {"model": model})
            
            # Llamar a la API
            result = await self._call_api(prompt, model)
            
            # Actualizar caché
            self._update_cache(cache_key, result)
            
            # Registrar uso de tokens
            tokens_used = self._count_tokens(prompt, result)
            self.telemetry.record_metric("vertex_ai.tokens_used", tokens_used, {
                "model": model
            })
            
            return result
        except Exception as e:
            self.telemetry.record_exception(span, e)
            self.telemetry.record_counter("vertex_ai.errors", 1, {
                "model": model,
                "error_type": type(e).__name__
            })
            raise
        finally:
            self.telemetry.end_span(span)
```

## Configuración de Alertas

Se recomienda configurar alertas para las siguientes métricas:

1. **Uso excesivo de tokens**: Alertar cuando el uso de tokens supere un umbral predefinido
2. **Tiempos de respuesta elevados**: Alertar cuando los tiempos de respuesta superen un umbral
3. **Tasas de error elevadas**: Alertar cuando la tasa de errores supere un umbral
4. **Baja tasa de caché**: Alertar cuando la tasa de aciertos de caché sea demasiado baja

## Visualización de Métricas

Las métricas registradas pueden visualizarse en dashboards que muestren:

1. **Uso de API por modelo**: Gráficos de uso de cada modelo a lo largo del tiempo
2. **Tiempos de respuesta**: Histogramas y percentiles de tiempos de respuesta
3. **Tasas de error**: Gráficos de tasas de error por modelo y tipo de error
4. **Efectividad de caché**: Tasas de aciertos y fallos de caché

## Consideraciones para el Futuro

1. **Integración con OpenTelemetry**: Migrar a OpenTelemetry para mayor compatibilidad
2. **Exportación a múltiples backends**: Permitir exportar métricas a diferentes sistemas
3. **Muestreo adaptativo**: Implementar muestreo adaptativo para reducir el volumen de datos
4. **Correlación entre servicios**: Mejorar la correlación de spans entre diferentes servicios

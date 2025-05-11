# Estrategia de Telemetría para NGX Agents

## Introducción

Este documento describe la estrategia de telemetría implementada en el proyecto NGX Agents, utilizando OpenTelemetry para el seguimiento distribuido, métricas y logging.

## Componentes de Telemetría

### 1. Dependencias

Las siguientes dependencias de OpenTelemetry han sido añadidas al proyecto:

```toml
# Telemetría OpenTelemetry
opentelemetry-api = "^1.33.0"
opentelemetry-sdk = "^1.33.0"
opentelemetry-instrumentation-fastapi = "^0.54b0"
opentelemetry-instrumentation-httpx = "^0.54b0"
opentelemetry-instrumentation-logging = "^0.54b0"
opentelemetry-instrumentation-aiohttp-client = "^0.54b0"
opentelemetry-exporter-cloud-trace = "^0.10b1"
```

### 2. Distribución de Dependencias por Componente

- **Componente App (FastAPI)**
  - `opentelemetry-api`
  - `opentelemetry-sdk`
  - `opentelemetry-instrumentation-fastapi`
  - `opentelemetry-exporter-cloud-trace`

- **Componente Clients**
  - `opentelemetry-api`
  - `opentelemetry-sdk`
  - `opentelemetry-instrumentation-httpx`
  - `opentelemetry-instrumentation-aiohttp-client`

- **Componente Core**
  - `opentelemetry-api`
  - `opentelemetry-sdk`
  - `opentelemetry-instrumentation-logging`

### 3. Implementación Mock para Pruebas

Para facilitar las pruebas sin depender de servicios externos de telemetría, se ha implementado un módulo mock en `core/telemetry_mock.py`. Este módulo proporciona:

- Gestión de spans (inicio, fin, atributos, eventos)
- Registro de excepciones
- Métricas básicas
- Estadísticas de telemetría

## Configuración por Entorno

### Desarrollo

En entorno de desarrollo, se recomienda utilizar el módulo mock de telemetría o configurar OpenTelemetry para exportar a la consola:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# Configuración para desarrollo
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
```

### Pruebas

Para pruebas unitarias y de integración, se debe utilizar el módulo mock de telemetría:

```python
from core.telemetry_mock import telemetry_manager

# Limpiar datos de telemetría antes de cada prueba
def setup_function():
    telemetry_manager.clear()

# Ejemplo de uso en pruebas
def test_something():
    span_id = telemetry_manager.start_span("test_operation")
    # Operaciones...
    telemetry_manager.end_span(span_id)
    
    # Verificar telemetría
    stats = telemetry_manager.get_stats()
    assert stats["spans_count"] == 1
    assert stats["error_spans"] == 0
```

### Producción

En producción, se debe configurar OpenTelemetry para exportar a Google Cloud Trace:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

# Configuración para producción
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter()))
```

## Mejores Prácticas

1. **Nombrado de Spans**: Utilizar nombres descriptivos que indiquen la operación realizada.
2. **Atributos**: Incluir información relevante como IDs de usuario, IDs de sesión, etc.
3. **Eventos**: Registrar eventos importantes dentro de un span para facilitar el debugging.
4. **Manejo de Errores**: Registrar excepciones y errores con detalles suficientes para diagnóstico.
5. **Propagación de Contexto**: Asegurar que el contexto de telemetría se propague correctamente entre servicios.

## Próximos Pasos

1. Implementar un módulo de configuración de telemetría que seleccione automáticamente la implementación adecuada según el entorno.
2. Crear decoradores para instrumentar funciones y métodos importantes.
3. Añadir métricas clave para monitoreo de rendimiento.
4. Implementar dashboards para visualización de telemetría.

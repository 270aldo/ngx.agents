# Guía de Observabilidad para NGX Agents

Este documento describe la configuración de observabilidad para NGX Agents, incluyendo métricas, logging, tracing y alertas.

## Arquitectura de Observabilidad

La observabilidad en NGX Agents se basa en tres pilares fundamentales:

1. **Métricas**: Datos cuantitativos sobre el rendimiento y comportamiento del sistema
2. **Logs**: Registros detallados de eventos y actividades
3. **Tracing**: Seguimiento de solicitudes a través de los diferentes componentes

## Componentes de Observabilidad

### Telemetría

La telemetría está implementada en `core/telemetry.py` y proporciona:

- Inicialización de OpenTelemetry
- Exportadores para métricas y traces
- Instrumentación automática para FastAPI y otras bibliotecas
- Métricas personalizadas para los agentes

```python
# Ejemplo de uso de telemetría
from core.telemetry import get_tracer, get_meter

# Obtener un tracer para spans personalizados
tracer = get_tracer("ngx_agents.custom_component")

# Crear un span personalizado
with tracer.start_as_current_span("operation_name") as span:
    span.set_attribute("attribute_key", "attribute_value")
    # Operación a trazar
    result = perform_operation()
    span.set_attribute("result", str(result))

# Obtener un meter para métricas personalizadas
meter = get_meter("ngx_agents.custom_metrics")

# Crear un contador
request_counter = meter.create_counter(
    name="requests",
    description="Número de solicitudes procesadas",
    unit="1"
)

# Incrementar el contador
request_counter.add(1, {"endpoint": "/api/v1/chat", "status": "success"})
```

### Middleware de Telemetría

El middleware de telemetría en `app/middleware/telemetry.py` se encarga de:

- Capturar métricas de solicitudes HTTP
- Añadir información de contexto a los spans
- Registrar errores y excepciones
- Proporcionar correlación entre logs y traces

### Health Checks

Los health checks están implementados en `infrastructure/health.py` y proporcionan:

- Endpoint de liveness para verificar que la aplicación está en ejecución
- Endpoint de readiness para verificar que la aplicación puede procesar solicitudes
- Endpoint de startup para verificar que la aplicación se ha inicializado correctamente
- Verificaciones de dependencias (Supabase, Vertex AI, etc.)

## Configuración en Kubernetes

La configuración de Kubernetes incluye anotaciones y configuraciones para observabilidad:

- **Prometheus**: Anotaciones para scraping de métricas
  ```yaml
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/path: "/metrics"
    prometheus.io/port: "8000"
  ```

- **Logging**: Habilitado en BackendConfig
  ```yaml
  logging:
    enable: true
  ```

- **Health Checks**: Configurados para todos los servicios
  ```yaml
  livenessProbe:
    httpGet:
      path: /api/v1/health/liveness
      port: 8000
  readinessProbe:
    httpGet:
      path: /api/v1/health/readiness
      port: 8000
  ```

## Integración con Google Cloud Operations (anteriormente Stackdriver)

NGX Agents está configurado para integrarse con Google Cloud Operations:

### Logging

- Los logs se envían a Cloud Logging
- Se utilizan niveles de severidad estándar (INFO, WARNING, ERROR, etc.)
- Se incluyen metadatos como service, version, trace_id, etc.

```python
# Ejemplo de logging estructurado
import logging
from core.logging_config import configure_logging

# Configurar logging
logger = configure_logging(__name__)

# Log con contexto estructurado
logger.info("Mensaje informativo", extra={
    "user_id": "123",
    "request_id": "abc-123",
    "component": "auth_service"
})
```

### Monitoring

- Las métricas se envían a Cloud Monitoring
- Se crean dashboards personalizados para visualizar el rendimiento
- Se configuran alertas basadas en umbrales y condiciones

### Tracing

- Los traces se envían a Cloud Trace
- Se visualizan los diagramas de Gantt para analizar la latencia
- Se correlacionan los traces con logs y métricas

## Dashboards y Alertas

### Dashboards Principales

1. **Dashboard de Visión General**
   - Métricas clave de rendimiento
   - Estado de los servicios
   - Errores y latencia

2. **Dashboard de Agentes**
   - Métricas específicas de cada agente
   - Tiempos de respuesta
   - Tasas de éxito y error

3. **Dashboard de Infraestructura**
   - Uso de CPU y memoria
   - Tráfico de red
   - Estado de los pods y nodos

### Alertas Recomendadas

1. **Alertas de Disponibilidad**
   - Error en health checks
   - Alta tasa de errores 5xx
   - Pods no disponibles

2. **Alertas de Rendimiento**
   - Latencia elevada (p95 > 500ms)
   - Uso de CPU > 80%
   - Uso de memoria > 80%

3. **Alertas de Negocio**
   - Tasa de error en comunicación entre agentes
   - Fallos en integraciones externas
   - Anomalías en patrones de uso

## Mejores Prácticas

1. **Logging**
   - Utilizar logging estructurado
   - Incluir contexto relevante
   - Evitar información sensible
   - Usar niveles de log apropiados

2. **Métricas**
   - Definir métricas significativas para el negocio
   - Agregar dimensiones útiles
   - Mantener cardinalidad controlada
   - Documentar unidades y significado

3. **Tracing**
   - Propagar contexto entre servicios
   - Añadir atributos relevantes a los spans
   - Crear spans personalizados para operaciones importantes
   - Correlacionar con logs y métricas

## Herramientas de Diagnóstico

### Comandos Útiles

```bash
# Ver logs de un pod específico
kubectl logs -f deployment/ngx-agents-api -n ngx-agents

# Ver métricas de un pod
kubectl top pod -n ngx-agents

# Verificar health checks
kubectl exec -it <pod-name> -n ngx-agents -- curl localhost:8000/api/v1/health

# Obtener eventos del namespace
kubectl get events -n ngx-agents
```

### Troubleshooting Común

1. **Problemas de Comunicación entre Agentes**
   - Verificar logs del servidor A2A
   - Comprobar NetworkPolicy
   - Validar configuración de DNS

2. **Latencia Elevada**
   - Analizar traces en Cloud Trace
   - Verificar uso de recursos
   - Comprobar dependencias externas

3. **Errores en Integraciones**
   - Verificar credenciales y permisos
   - Comprobar conectividad de red
   - Validar formato de solicitudes

## Conclusión

Una estrategia de observabilidad bien implementada es crucial para operar NGX Agents en producción. Esta guía proporciona las bases para monitorear, diagnosticar y mantener el sistema de manera efectiva.

Para más detalles sobre la implementación específica, consultar los archivos de código fuente mencionados y la documentación de Google Cloud Operations.

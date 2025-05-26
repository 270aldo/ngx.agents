# Sistema de Métricas y Monitoreo con Prometheus

## Resumen

Se ha implementado un sistema completo de métricas y monitoreo utilizando Prometheus y Grafana para NGX Agents, proporcionando visibilidad en tiempo real del rendimiento y comportamiento del sistema.

## Arquitectura de Monitoreo

```
NGX Agents → Métricas → /metrics → Prometheus → Grafana
    ↓                                   ↓            ↓
Custom Metrics                    Alertmanager  Dashboards
```

## Componentes Implementados

### 1. Cliente de Métricas (`core/metrics.py`)

#### Métricas de Sistema
- `ngx_agents_http_requests_total`: Total de requests HTTP
- `ngx_agents_http_request_duration_seconds`: Duración de requests
- `ngx_agents_http_requests_active`: Requests activos

#### Métricas de Agentes
- `ngx_agents_agent_invocations_total`: Invocaciones de agentes
- `ngx_agents_agent_response_time_seconds`: Tiempo de respuesta
- `ngx_agents_agents_active`: Agentes activos

#### Métricas de Chat/Streaming
- `ngx_agents_chat_sessions_total`: Sesiones de chat
- `ngx_agents_chat_session_duration_seconds`: Duración de sesiones
- `ngx_agents_stream_chunks_sent_total`: Chunks enviados
- `ngx_agents_stream_ttfb_seconds`: Time to First Byte

#### Métricas de Infraestructura
- `ngx_agents_cache_operations_total`: Operaciones de caché
- `ngx_agents_circuit_breaker_state_changes`: Cambios de circuit breaker
- `ngx_agents_db_operation_duration_seconds`: Duración de operaciones DB
- `ngx_agents_redis_pool_connections`: Conexiones Redis

### 2. Endpoint de Métricas

```bash
GET /metrics
```

Expone todas las métricas en formato Prometheus.

### 3. Configuración de Prometheus

- Scraping cada 15 segundos
- Targets configurados para API y A2A server
- Reglas de alertas organizadas por categoría

### 4. Alertas Configuradas

#### API Alerts
- Alta latencia HTTP (P95 > 2s)
- Alta tasa de errores (> 5%)
- Muchos requests activos (> 100)
- API no disponible

#### Agent Alerts
- Respuesta lenta de agentes (P95 > 5s)
- Alta tasa de fallos (> 10%)
- Agente no responde

#### Streaming Alerts
- Alto TTFB (P95 > 1s)
- Baja tasa de éxito (< 95%)
- Exceso de chunks por sesión

#### Infrastructure Alerts
- Circuit breaker abierto
- Alta tasa de cache miss (> 30%)
- Pool de Redis saturado (> 90%)
- Operaciones DB lentas

## Instalación y Configuración

### 1. Instalar Dependencias

```bash
poetry add prometheus-client prometheus-fastapi-instrumentator
```

### 2. Iniciar Stack de Monitoreo

```bash
./scripts/start_monitoring.sh
```

Esto levanta:
- Prometheus (puerto 9090)
- Grafana (puerto 3000)
- Node Exporter (puerto 9100)
- Redis Exporter (puerto 9121)
- Alertmanager (puerto 9093)

### 3. Acceder a las Interfaces

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Alertmanager**: http://localhost:9093

## Uso de Métricas en el Código

### Ejemplo 1: Registrar Operación de Agente

```python
from core.metrics import metrics_collector

# En tu código de agente
start_time = time.time()
try:
    result = await agent.process(request)
    duration = time.time() - start_time
    metrics_collector.record_agent_invocation(
        agent_id="orchestrator",
        status="success",
        duration=duration
    )
except Exception as e:
    duration = time.time() - start_time
    metrics_collector.record_agent_invocation(
        agent_id="orchestrator",
        status="error",
        duration=duration
    )
```

### Ejemplo 2: Usar Decorador de Tiempo

```python
from core.metrics import track_time, agent_response_time_seconds

@track_time(
    agent_response_time_seconds,
    labels={"agent_id": "elite_training_strategist"}
)
async def process_training_request(request):
    # Tu código aquí
    pass
```

### Ejemplo 3: Context Manager para Operaciones

```python
from core.metrics import track_operation_time, db_operation_duration_seconds

async def get_user_data(user_id: str):
    with track_operation_time(
        db_operation_duration_seconds,
        operation="select",
        table="users"
    ):
        # Operación de base de datos
        result = await db.fetch_one(...)
    return result
```

## Dashboards de Grafana

### NGX Agents Overview

Dashboard principal con:
- Request rate por método
- Success rate general
- Latencia P95 por endpoint
- Requests activos
- Tasa de invocación de agentes
- Cache hit rate

### Creación de Dashboards Personalizados

1. Acceder a Grafana
2. Crear nuevo dashboard
3. Agregar panel con query Prometheus
4. Guardar en la carpeta "NGX Agents"

## Queries Prometheus Útiles

### Top 5 Endpoints Más Lentos
```promql
topk(5, 
  histogram_quantile(0.95,
    sum(rate(ngx_agents_http_request_duration_seconds_bucket[5m])) 
    by (endpoint, le)
  )
)
```

### Tasa de Error por Agente
```promql
sum(rate(ngx_agents_agent_invocations_total{status="error"}[5m])) by (agent_id)
/
sum(rate(ngx_agents_agent_invocations_total[5m])) by (agent_id)
```

### Eficiencia del Cache
```promql
sum(rate(ngx_agents_cache_operations_total{result="hit"}[5m]))
/
sum(rate(ngx_agents_cache_operations_total[5m]))
```

### Estado de Circuit Breakers
```promql
sum(increase(ngx_agents_circuit_breaker_state_changes_total{to_state="open"}[1h])) 
by (service)
```

## Mejores Prácticas

1. **Nombrado de Métricas**
   - Usar prefijo `ngx_agents_`
   - Seguir convención: `<namespace>_<subsystem>_<metric>_<unit>`

2. **Labels**
   - No usar labels de alta cardinalidad (IDs únicos)
   - Mantener labels consistentes
   - Usar labels para dimensiones importantes

3. **Histogramas**
   - Definir buckets apropiados para tu caso de uso
   - Considerar percentiles importantes (P50, P95, P99)

4. **Alertas**
   - Definir umbrales basados en SLOs
   - Incluir contexto en las anotaciones
   - Evitar alertas ruidosas

## Troubleshooting

### Métricas No Aparecen

1. Verificar que el endpoint `/metrics` responde
2. Verificar configuración de scraping en Prometheus
3. Revisar logs de Prometheus

### Grafana No Muestra Datos

1. Verificar datasource configurado
2. Probar query directamente en Prometheus
3. Verificar permisos y conectividad

### Alertas No Se Disparan

1. Verificar reglas en Prometheus UI
2. Revisar configuración de Alertmanager
3. Verificar que las métricas existen

## Monitoreo en Producción

### Recomendaciones

1. **Retención de Datos**
   ```yaml
   # prometheus.yml
   global:
     retention_time: 30d
   ```

2. **Almacenamiento Remoto**
   - Considerar Thanos o Cortex para largo plazo
   - Configurar write/read endpoints

3. **Alta Disponibilidad**
   - Ejecutar múltiples instancias de Prometheus
   - Usar Alertmanager en cluster

4. **Seguridad**
   - Proteger endpoints con autenticación
   - Usar TLS para comunicaciones
   - Limitar acceso a métricas sensibles

## Referencias

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [FastAPI Prometheus Integration](https://github.com/trallnag/prometheus-fastapi-instrumentator)
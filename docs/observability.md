# Estrategia de Observabilidad para NGX Agents

## Visión General

Este documento describe la estrategia de observabilidad implementada para el sistema NGX Agents. La observabilidad es crucial para entender el comportamiento del sistema en producción, detectar problemas proactivamente y mantener un alto nivel de disponibilidad y rendimiento.

## Componentes Principales

La estrategia de observabilidad para NGX Agents se basa en tres pilares fundamentales:

1. **Métricas**: Datos numéricos que representan estados y comportamientos del sistema
2. **Logs**: Registros estructurados y detallados de eventos del sistema
3. **Trazas**: Flujos de ejecución a través de múltiples componentes del sistema

## Implementación Técnica

### Telemetría en el Núcleo del Sistema

El módulo `core/telemetry.py` proporciona la base para la recolección de métricas, trazas y logs. Implementa:

- Integración con OpenTelemetry para estándares abiertos de observabilidad
- Sistema fallback para entornos sin OpenTelemetry
- API unificada para instrumentación consistente
- Integración con Google Cloud Monitoring y Trace

### Middleware de Telemetría

El middleware `app/middleware/telemetry.py` intercepta cada solicitud HTTP para:

- Generar IDs únicos para cada solicitud (Request ID)
- Medir latencia y volumen de solicitudes
- Rastrear errores y excepciones
- Propagar contexto a través de los límites de los servicios
- Enriquecer logs con metadatos contextuales

### Monitoreo de Estado del Sistema

El módulo `infrastructure/health.py` y el router `infrastructure/health_router.py` implementan:

- Endpoints `/health` y `/health/metrics` para monitoreo del estado
- Verificación periódica de componentes internos y servicios externos
- Recopilación de métricas del sistema (CPU, memoria, disco)
- Formato estandarizado para respuestas de estado

### Alertas Inteligentes

La integración con PagerDuty mediante `tools/pagerduty_tools.py`:

- Alertas basadas en políticas configurables
- Diferentes niveles de severidad (info, warning, error, critical)
- Correlación de eventos relacionados
- Resolución automática cuando los problemas se corrigen

### Infraestructura como Código para Observabilidad

Los archivos de Terraform (`terraform/monitoring.tf` y `terraform/variables.tf`):

- Configuran dashboards predefinidos para visualización de métricas
- Establecen políticas de alertas para detectar condiciones anómalas
- Definen la integración con sistemas de notificación
- Configuran la retención y el ciclo de vida de los datos de observabilidad

## Dashboards y Visualizaciones

### Dashboard Principal de NGX Agents

Este dashboard proporciona una visión general del estado del sistema, incluyendo:

- Estado de disponibilidad de los servicios
- Volumen de solicitudes y tasa de errores
- Latencia de API (p50, p95, p99)
- Uso de recursos del sistema (CPU, memoria)

### Dashboard de Comunicación A2A

Este dashboard se enfoca en la comunicación entre agentes:

- Volumen de mensajes A2A
- Latencia de comunicación entre agentes
- Tasa de errores en comunicaciones A2A

### Dashboard de Rendimiento de Agentes

Este dashboard muestra el rendimiento específico de cada agente:

- Tiempo de procesamiento por agente
- Uso de skills por agente
- Latencia de procesamiento de consultas

## Métricas Clave

| Métrica | Descripción | Umbral de Alerta |
|---------|-------------|------------------|
| `ngx_agents_health_status` | Estado general del sistema (1=OK, 0=Degradado) | < 1 durante 1 minuto |
| `ngx_agents_requests_total` | Número total de solicitudes recibidas | N/A (métrica de volumen) |
| `ngx_agents_request_duration_seconds` | Latencia de las solicitudes | p95 > 2s durante 5 minutos |
| `ngx_agents_errors_total` | Número total de errores | Tasa > 5% durante 5 minutos |
| `ngx_agents_a2a_messages_total` | Mensajes entre agentes | N/A (métrica de volumen) |
| `ngx_agents_a2a_latency_seconds` | Latencia en la comunicación entre agentes | Promedio > 1s durante 5 minutos |
| `ngx_agents_cpu_usage` | Porcentaje de uso de CPU | > 80% durante 10 minutos |
| `ngx_agents_memory_usage` | Porcentaje de uso de memoria | > 80% durante 10 minutos |

## Niveles de Logging

Se han implementado los siguientes niveles de logging con propósitos específicos:

- **DEBUG**: Información detallada para el desarrollo y depuración
- **INFO**: Eventos normales del sistema que confirman el funcionamiento correcto
- **WARNING**: Eventos inesperados pero que no impiden el funcionamiento correcto
- **ERROR**: Errores que impiden el funcionamiento correcto de una funcionalidad
- **CRITICAL**: Errores graves que impiden el funcionamiento del sistema

## Integración con Google Cloud

### Cloud Monitoring

- Métricas personalizadas para monitoreo detallado
- Integración con dashboards en Cloud Monitoring
- Alertas integradas con sistemas de notificación

### Cloud Logging

- Logs estructurados con niveles de severidad
- Enriquecimiento de logs con metadatos contextuales
- Búsqueda y filtrado avanzado de logs

### Cloud Trace

- Trazas distribuidas a través de múltiples servicios
- Análisis de rendimiento y detección de cuellos de botella
- Visualización de flujos de ejecución

## Guía de Diagnóstico de Problemas

### Validación del Estado del Sistema

1. Verificar el endpoint `/health` para obtener el estado general del sistema
2. Consultar `/health/metrics` para obtener métricas detalladas
3. Verificar los dashboards en Cloud Monitoring para tendencias históricas

### Diagnóstico de Problemas de Rendimiento

1. Identificar las métricas de latencia en el dashboard principal
2. Analizar los logs para errores o advertencias relacionadas
3. Consultar las trazas para identificar componentes lentos
4. Verificar el uso de recursos (CPU, memoria) durante el período afectado

### Diagnóstico de Errores

1. Consultar los logs del sistema para errores específicos
2. Verificar las alertas activas en PagerDuty o Cloud Monitoring
3. Analizar el contexto de los errores (Request ID, endpoint afectado)
4. Consultar las métricas de errores por tipo y componente

## Mejores Prácticas

1. **Centralización de logs**: Todos los logs deben enviarse a Cloud Logging
2. **Correlación con Request ID**: Utilizar el Request ID para relacionar logs, métricas y trazas
3. **Logs estructurados**: Utilizar la función `logger.info/error/etc` con el parámetro `extra` para metadatos
4. **Enriquecimiento de contexto**: Propagar el contexto en todas las llamadas entre servicios
5. **Instrumentación de código**: Utilizar los decoradores de trazas para funciones críticas
6. **Validación periódica**: Verificar regularmente que los endpoints de health check responden correctamente

## Próximos Pasos y Mejoras Futuras

1. Implementación de detección de anomalías basada en machine learning
2. Mejora de la correlación entre logs, métricas y trazas
3. Expansión de dashboards para análisis más detallado de componentes específicos
4. Integración con herramientas adicionales de observabilidad (Grafana, Prometheus)
5. Mejora de la instrumentación de código con métricas más granulares

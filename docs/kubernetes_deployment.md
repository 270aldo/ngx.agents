# Despliegue en Kubernetes para NGX Agents

Este documento describe la configuración de Kubernetes para el despliegue de NGX Agents en Google Kubernetes Engine (GKE).

## Estructura de Archivos

La configuración de Kubernetes se divide en varios archivos para facilitar su mantenimiento:

- `namespace-config.yaml`: Configuración del namespace, ConfigMap, ResourceQuota y LimitRange
- `deployment.yaml`: Deployments, Services, HPA, BackendConfig, ServiceAccount y PodDisruptionBudget
- `network-policy.yaml`: Políticas de red para restringir el tráfico
- `ingress.yaml`: Configuración de Ingress, FrontendConfig y ManagedCertificate

## Componentes Principales

### API Principal

El componente principal de NGX Agents es una API REST implementada con FastAPI que expone los endpoints para interactuar con los agentes.

- **Deployment**: `ngx-agents-api`
- **Service**: `ngx-agents-api`
- **HPA**: Escalado automático basado en CPU y memoria
- **Recursos**: Solicita 100m CPU y 256Mi memoria, con límites de 500m CPU y 512Mi memoria
- **Probes**: Liveness, readiness y startup probes configurados para garantizar disponibilidad
- **Afinidad**: Configurada para distribuir pods en diferentes nodos

### Servidor A2A

El servidor A2A (Agent-to-Agent) facilita la comunicación entre los diferentes agentes especializados.

- **Deployment**: `ngx-agents-a2a`
- **Service**: `ngx-agents-a2a`
- **HPA**: Escalado automático basado en CPU y memoria
- **Recursos**: Solicita 200m CPU y 512Mi memoria, con límites de 1000m CPU y 1Gi memoria
- **Probes**: Liveness y readiness probes configurados
- **Afinidad**: Configurada para ejecutarse en nodos específicos con el rol `a2a-server`

## Seguridad

La configuración incluye varias medidas de seguridad:

- **NetworkPolicy**: Restringe el tráfico entrante y saliente
- **ServiceAccount**: Con anotaciones para usar una cuenta de servicio de GCP
- **BackendConfig**: Configura políticas de seguridad para los backends
- **FrontendConfig**: Configura HTTPS y redirección desde HTTP
- **ManagedCertificate**: Gestiona certificados TLS para los dominios

## Escalabilidad

La configuración está diseñada para escalar automáticamente:

- **HorizontalPodAutoscaler**: Configura el escalado automático basado en CPU y memoria
- **Comportamiento de escalado**: Configurado para escalar rápidamente hacia arriba y lentamente hacia abajo
- **PodDisruptionBudget**: Garantiza disponibilidad durante actualizaciones y mantenimiento

## Observabilidad

La configuración incluye anotaciones y configuraciones para observabilidad:

- **Prometheus**: Anotaciones para scraping de métricas
- **Logging**: Habilitado en BackendConfig
- **Health Checks**: Configurados para todos los servicios

## Recursos y Límites

Se han configurado cuotas y límites para el namespace:

- **ResourceQuota**: Limita el uso total de recursos en el namespace
- **LimitRange**: Establece límites predeterminados para contenedores sin límites explícitos

## Despliegue

Para desplegar esta configuración en GKE:

1. Crear el namespace y configuraciones básicas:
   ```bash
   kubectl apply -f kubernetes/namespace-config.yaml
   ```

2. Aplicar las políticas de red:
   ```bash
   kubectl apply -f kubernetes/network-policy.yaml
   ```

3. Desplegar los servicios y deployments:
   ```bash
   kubectl apply -f kubernetes/deployment.yaml
   ```

4. Configurar el ingress:
   ```bash
   kubectl apply -f kubernetes/ingress.yaml
   ```

## Consideraciones

- Reemplazar `PROJECT_ID` en los archivos con el ID real del proyecto de GCP
- Actualizar los dominios en `ingress.yaml` con los dominios reales
- Asegurarse de que existan los secretos referenciados en los deployments
- Configurar la política SSL referenciada en el FrontendConfig

## Monitoreo y Mantenimiento

- Utilizar Cloud Monitoring para monitorear los recursos
- Configurar alertas basadas en métricas de CPU, memoria y latencia
- Realizar actualizaciones utilizando la estrategia de RollingUpdate configurada
- Monitorear los logs a través de Cloud Logging

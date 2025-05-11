# Guía de Despliegue de NGX Agents en Google Cloud Platform

## Visión General

Este documento describe el proceso de despliegue del sistema NGX Agents en Google Cloud Platform (GCP), utilizando Kubernetes (GKE) y servicios gestionados para garantizar alta disponibilidad, escalabilidad y observabilidad.

## Requisitos Previos

Antes de comenzar el despliegue, asegúrate de tener:

1. Una cuenta de Google Cloud con privilegios de administrador
2. Google Cloud SDK instalado y configurado
3. Terraform v1.0.0 o superior
4. kubectl configurado para interactuar con GKE
5. Variables de entorno y secretos necesarios

## Arquitectura de Despliegue

El despliegue de NGX Agents en GCP sigue esta arquitectura:

```
                                 +---------------+
                                 |   Cloud Load  |
                                 |   Balancer    |
                                 +-------+-------+
                                         |
                  +---------------------+----------------------+
                  |                     |                      |
         +--------v--------+   +--------v--------+    +--------v--------+
         |    GKE Node     |   |    GKE Node     |    |    GKE Node     |
         |  +----------+   |   |  +----------+   |    |  +----------+   |
         |  | NGX API  |   |   |  | NGX API  |   |    |  | NGX API  |   |
         |  +----------+   |   |  +----------+   |    |  +----------+   |
         |  +----------+   |   |  +----------+   |    |  +----------+   |
         |  | A2A Serv.|   |   |  | A2A Serv.|   |    |  | A2A Serv.|   |
         |  +----------+   |   |  +----------+   |    |  +----------+   |
         +-----------------+   +-----------------+    +-----------------+
                  |                     |                      |
                  v                     v                      v
         +----------------------------------------------------------+
         |                      Cloud Monitoring                     |
         +----------------------------------------------------------+
                  |                     |                      |
         +--------v--------+   +--------v--------+    +--------v--------+
         |                 |   |                 |    |                 |
         |  Cloud SQL DB   |   |   Vertex AI     |    |  Supabase      |
         |                 |   |                 |    |                 |
         +-----------------+   +-----------------+    +-----------------+
```

## Componentes de Infraestructura

| Componente | Servicio GCP | Propósito |
|------------|--------------|-----------|
| API y Lógica de Aplicación | Google Kubernetes Engine (GKE) | Ejecutar los servicios de API y los agentes NGX |
| Servidor A2A | Google Kubernetes Engine (GKE) | Facilitar la comunicación entre agentes |
| Base de Datos | Cloud SQL | Almacenamiento persistente de datos |
| Modelos de IA | Vertex AI | Procesamiento de modelos de lenguaje |
| Autenticación | Supabase | Gestión de usuarios y autenticación |
| Monitoreo y Observabilidad | Cloud Monitoring, Cloud Logging | Monitoreo del estado del sistema y logs |
| Almacenamiento | Cloud Storage | Almacenamiento de archivos |
| Red | VPC, Cloud NAT | Conectividad segura entre servicios |

## Procedimiento de Despliegue

### 1. Configuración del Proyecto GCP

```bash
# Crear proyecto (si no existe)
gcloud projects create ngx-agents-${ENVIRONMENT} --name="NGX Agents ${ENVIRONMENT}"

# Configurar proyecto actual
gcloud config set project ngx-agents-${ENVIRONMENT}

# Habilitar APIs necesarias
gcloud services enable container.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    compute.googleapis.com \
    sqladmin.googleapis.com \
    aiplatform.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    cloudtrace.googleapis.com
```

### 2. Despliegue con Terraform

```bash
# Navegar al directorio de Terraform
cd terraform/

# Inicializar Terraform
terraform init

# Crear espacio de trabajo para el entorno
terraform workspace new ${ENVIRONMENT}

# Planificar el despliegue
terraform plan -var-file="${ENVIRONMENT}.tfvars" -out=plan.out

# Aplicar el despliegue
terraform apply plan.out
```

### 3. Configuración de Kubernetes

```bash
# Obtener credenciales del cluster
gcloud container clusters get-credentials ngx-agents-cluster --zone ${ZONE} --project ngx-agents-${ENVIRONMENT}

# Aplicar configuración base
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/configmap.yaml

# Aplicar secrets (después de crearlos con los valores correctos)
kubectl apply -f k8s/secrets.yaml

# Desplegar aplicación
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

### 4. Validación del Despliegue

```bash
# Verificar pods en ejecución
kubectl get pods -n ngx-agents

# Verificar servicios
kubectl get services -n ngx-agents

# Verificar endpoints de salud
IP_ADDRESS=$(kubectl get service ngx-api -n ngx-agents -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://${IP_ADDRESS}/api/v1/health
```

## Gestión de Secretos

Los secretos de la aplicación se gestionan utilizando Kubernetes Secrets en producción y Google Secret Manager para secretos más sensibles.

### Configuración de Secretos en Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ngx-agents-secrets
  namespace: ngx-agents
type: Opaque
data:
  SUPABASE_URL: <base64-encoded-value>
  SUPABASE_KEY: <base64-encoded-value>
  GCP_PROJECT_ID: <base64-encoded-value>
  VERTEX_LOCATION: <base64-encoded-value>
  GEMINI_API_KEY: <base64-encoded-value>
  JWT_SECRET: <base64-encoded-value>
  PAGERDUTY_SERVICE_KEY: <base64-encoded-value>
```

### Integración con Google Secret Manager

Para secretos más sensibles:

```bash
# Crear secreto en Secret Manager
echo -n "valor-secreto" | gcloud secrets create ngx-agents-api-key \
  --replication-policy="automatic" \
  --data-file=-

# Conceder acceso a la cuenta de servicio de GKE
gcloud secrets add-iam-policy-binding ngx-agents-api-key \
  --member="serviceAccount:${GKE_SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"
```

## Configuración de Observabilidad

Los componentes de observabilidad se despliegan automáticamente con Terraform, pero es posible que necesiten configuración adicional:

### 1. Verificar el Despliegue de Dashboards

```bash
# Listar dashboards creados
gcloud monitoring dashboards list --filter="displayName:NGX Agents"
```

### 2. Configurar Alertas y Notificaciones

Verificar que las políticas de alertas estén correctamente configuradas:

```bash
# Listar políticas de alertas
gcloud alpha monitoring policies list --project=ngx-agents-${ENVIRONMENT}
```

### 3. Configurar Integración con PagerDuty

Para configurar la integración con PagerDuty, añade la clave de servicio al archivo de variables de Terraform (`terraform/${ENVIRONMENT}.tfvars`):

```hcl
pagerduty_service_key = "tu-clave-de-servicio-pagerduty"
```

## Escalado y Alta Disponibilidad

### Configuración de Escalado Automático

El sistema está configurado para escalar automáticamente basado en métricas de CPU y memoria:

```yaml
apiVersion: autoscaling/v2beta2
kind: HorizontalPodAutoscaler
metadata:
  name: ngx-api-hpa
  namespace: ngx-agents
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ngx-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 65
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
```

### Configuración de Anti-Afinidad

Para garantizar alta disponibilidad, los pods se distribuyen entre nodos diferentes:

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - ngx-api
        topologyKey: "kubernetes.io/hostname"
```

## Gestión de Despliegues

### Estrategia de Despliegue Azul/Verde

Para los despliegues, se utiliza una estrategia azul/verde:

1. Desplegar nueva versión en un nuevo conjunto de pods
2. Validar funcionamiento mediante health checks
3. Cambiar el tráfico a la nueva versión
4. Mantener la versión anterior por un período de seguridad
5. Eliminar la versión anterior si todo funciona correctamente

### Configuración de Rollback

En caso de problemas, se puede realizar un rollback rápido:

```bash
# Verificar historial de despliegues
kubectl rollout history deployment/ngx-api -n ngx-agents

# Realizar rollback a la versión anterior
kubectl rollout undo deployment/ngx-api -n ngx-agents
```

## Configuración de Base de Datos

### Migración de Base de Datos

Las migraciones de base de datos se ejecutan automáticamente al desplegar:

```bash
# Ejecutar migraciones manualmente si es necesario
kubectl exec -it $(kubectl get pod -l app=ngx-api -n ngx-agents -o jsonpath='{.items[0].metadata.name}') -n ngx-agents -- python -m scripts.run_migrations
```

### Backups de Base de Datos

Los backups están configurados automáticamente en Cloud SQL:

```bash
# Verificar configuración de backups
gcloud sql backups list --instance=ngx-agents-db
```

## Configuración de Red

### Ingress y SSL

La configuración de Ingress incluye manejo automático de certificados SSL:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ngx-agents-ingress
  namespace: ngx-agents
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "ngx-agents-ip"
    networking.gke.io/managed-certificates: "ngx-agents-cert"
spec:
  rules:
  - host: api.ngx-agents.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: ngx-api
            port:
              number: 80
```

### Configuración de Firewall

```bash
# Verificar reglas de firewall
gcloud compute firewall-rules list --filter="network:ngx-agents-network"
```

## Mantenimiento y Operaciones Continuas

### Monitoreo y Observabilidad

1. Visitar la consola de Cloud Monitoring para ver los dashboards
2. Comprobar alertas y estado de salud del sistema
3. Revisar logs estructurados en Cloud Logging

### Actualización de Componentes

```bash
# Actualizar imagen de contenedor
kubectl set image deployment/ngx-api ngx-api=gcr.io/ngx-agents-${ENVIRONMENT}/ngx-api:nueva-versión -n ngx-agents

# Verificar estado del despliegue
kubectl rollout status deployment/ngx-api -n ngx-agents
```

### Actualización de Infraestructura

Para actualizar la infraestructura:

```bash
# Actualizar código Terraform
cd terraform/

# Planificar cambios
terraform plan -var-file="${ENVIRONMENT}.tfvars" -out=plan.out

# Aplicar cambios
terraform apply plan.out
```

## Troubleshooting

### Problemas Comunes y Soluciones

1. **Fallo en health checks**:
   ```bash
   # Verificar logs del pod
   kubectl logs $(kubectl get pod -l app=ngx-api -n ngx-agents -o jsonpath='{.items[0].metadata.name}') -n ngx-agents
   ```

2. **Problemas de conexión a servicios externos**:
   ```bash
   # Verificar conectividad desde un pod
   kubectl exec -it $(kubectl get pod -l app=ngx-api -n ngx-agents -o jsonpath='{.items[0].metadata.name}') -n ngx-agents -- curl -v https://api.supabase.io
   ```

3. **Problemas de rendimiento**:
   - Verificar dashboards de rendimiento en Cloud Monitoring
   - Analizar trazas en Cloud Trace

### Recursos y Soporte

- Documentación oficial del proyecto: `/docs`
- Google Cloud Support: https://cloud.google.com/support
- Repositorio de código: [GitHub Repository URL]

## Conclusión

Siguiendo esta guía, deberías poder desplegar y mantener el sistema NGX Agents en Google Cloud Platform. Para cualquier problema o duda adicional, consulta la documentación completa o contacta al equipo de desarrollo.

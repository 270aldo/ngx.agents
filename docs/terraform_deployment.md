# Despliegue de NGX Agents con Terraform

Este documento describe el proceso para desplegar la infraestructura de NGX Agents en Google Cloud Platform utilizando Terraform.

## Arquitectura de la Infraestructura

La infraestructura de NGX Agents está diseñada para proporcionar un entorno escalable, seguro y altamente disponible para la ejecución de agentes de IA. La arquitectura incluye:

- **Cluster de Kubernetes (GKE)**: Entorno de ejecución principal para los agentes
- **Vertex AI**: Integración con modelos de IA avanzados
- **Networking seguro**: VPC, subredes y reglas de firewall
- **Observabilidad**: Monitoreo, logging y alertas
- **Seguridad**: Gestión de secretos, encriptación y políticas IAM

![Arquitectura de Infraestructura](../assets/infrastructure_architecture.png)

## Prerrequisitos

Antes de comenzar el despliegue, asegúrate de tener:

1. **Cuenta de Google Cloud** con permisos de administrador
2. **Proyecto de Google Cloud** creado
3. **Terraform** instalado (versión 1.0.0 o superior)
4. **Google Cloud SDK** instalado y configurado
5. **Supabase** proyecto configurado (para persistencia de datos)

## Configuración Inicial

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-organizacion/ngx-agents.git
cd ngx-agents
```

### 2. Configurar Variables de Entorno

Crea un archivo `terraform.tfvars` en el directorio `terraform/` con las siguientes variables:

```hcl
# Configuración del proyecto
project_id         = "tu-proyecto-id"
region             = "us-central1"
environment        = "development" # o "staging", "production"

# Configuración de seguridad
security_level     = "basic" # o "enhanced", "strict"
project_number     = "123456789012" # Número de tu proyecto de GCP

# Configuración de Vertex AI
vertex_ai_region   = "us-central1"

# Configuración de red
subnetwork_cidr    = "10.0.0.0/16"

# Configuración de Kubernetes
cluster_name       = "ngx-agents-cluster"
min_node_count     = 1
max_node_count     = 5
machine_type       = "e2-standard-2"

# Configuración de observabilidad
enable_monitoring  = true
enable_logging     = true
enable_trace       = true
```

### 3. Inicializar Terraform

```bash
cd terraform
terraform init
```

## Despliegue de la Infraestructura

### 1. Plan de Ejecución

Genera un plan de ejecución para verificar los cambios que se realizarán:

```bash
terraform plan -out=tfplan
```

Revisa cuidadosamente el plan para asegurarte de que los recursos que se crearán son los esperados.

### 2. Aplicar Cambios

Aplica los cambios para crear la infraestructura:

```bash
terraform apply tfplan
```

El proceso de creación puede tomar entre 15-30 minutos, dependiendo de la cantidad de recursos.

### 3. Verificar Despliegue

Una vez completado el despliegue, verifica que todos los recursos se hayan creado correctamente:

```bash
terraform output
```

Esto mostrará información importante como:
- Endpoint del cluster de GKE
- Nombre del namespace de Kubernetes
- ID del keyring KMS
- Endpoint de Vertex AI

## Configuración Post-Despliegue

### 1. Configurar kubectl

Configura kubectl para conectarte al cluster de GKE:

```bash
gcloud container clusters get-credentials $(terraform output -raw gke_cluster_name) --region $(terraform output -raw region) --project $(terraform output -raw project_id)
```

### 2. Cargar Secretos

Carga los secretos necesarios en Secret Manager:

```bash
# Ejemplo para Supabase URL
echo -n "https://tu-proyecto.supabase.co" | \
  gcloud secrets versions add ngx-agents-supabase-url --data-file=-

# Ejemplo para Supabase Key
echo -n "tu-supabase-key" | \
  gcloud secrets versions add ngx-agents-supabase-key --data-file=-

# Ejemplo para JWT Secret
echo -n "tu-jwt-secret-muy-seguro" | \
  gcloud secrets versions add ngx-agents-jwt-secret --data-file=-

# Ejemplo para Gemini API Key
echo -n "tu-gemini-api-key" | \
  gcloud secrets versions add ngx-agents-gemini-api-key --data-file=-
```

### 3. Desplegar la Aplicación

Despliega la aplicación NGX Agents en el cluster de GKE:

```bash
kubectl apply -f kubernetes/
```

## Niveles de Seguridad

NGX Agents soporta tres niveles de seguridad que puedes configurar mediante la variable `security_level`:

1. **basic**: Configuración estándar para entornos de desarrollo
   - Encriptación en reposo para secretos
   - Autenticación básica
   - Firewall configurado

2. **enhanced**: Configuración recomendada para entornos de staging y producción
   - Todo lo de "basic" más:
   - VPC Service Controls
   - Shielded VMs
   - Workload Identity
   - Binary Authorization

3. **strict**: Configuración de máxima seguridad para datos sensibles
   - Todo lo de "enhanced" más:
   - Security Command Center
   - Cloud DLP
   - HSM para claves de encriptación
   - OS Login obligatorio
   - Restricción de IPs externas

## Observabilidad

La infraestructura incluye una configuración completa de observabilidad:

1. **Logging**: Todos los logs se envían a Cloud Logging
   - Logs de aplicación
   - Logs de sistema
   - Logs de seguridad (con retención extendida)

2. **Monitoring**: Dashboards preconfigurados para:
   - Rendimiento del cluster
   - Uso de Vertex AI
   - Métricas de agentes
   - Latencia de API

3. **Alerting**: Alertas configuradas para:
   - Alta utilización de CPU/memoria
   - Errores en llamadas a Vertex AI
   - Problemas de salud de servicios
   - Anomalías de seguridad

## Mantenimiento y Actualizaciones

### Actualizar la Infraestructura

Para actualizar la infraestructura después de cambios en la configuración:

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

### Destruir la Infraestructura

Para destruir toda la infraestructura (¡usar con precaución!):

```bash
terraform destroy
```

## Solución de Problemas

### Problemas Comunes

1. **Error de permisos**: Asegúrate de que la cuenta de servicio tiene los permisos necesarios
2. **Cuotas excedidas**: Verifica las cuotas de GCP y solicita aumentos si es necesario
3. **Fallos en la creación de GKE**: Verifica la configuración de red y las APIs habilitadas

### Logs y Diagnóstico

Para ver los logs de la infraestructura:

```bash
# Logs de GKE
gcloud logging read "resource.type=k8s_cluster"

# Logs de Vertex AI
gcloud logging read "resource.type=aiplatform.googleapis.com"

# Logs de seguridad
gcloud logging read "logName:projects/$(gcloud config get-value project)/logs/cloudaudit.googleapis.com"
```

## Consideraciones para Producción

Para entornos de producción, considera las siguientes recomendaciones adicionales:

1. **Alta disponibilidad**: Configura `min_node_count` a al menos 3 para garantizar disponibilidad
2. **Backups**: Habilita backups automáticos para todos los datos críticos
3. **Seguridad**: Utiliza el nivel de seguridad "enhanced" o "strict"
4. **Monitoreo**: Configura alertas para todos los servicios críticos
5. **Escalado**: Ajusta los parámetros de autoescalado según las necesidades de carga

## Recursos Adicionales

- [Documentación de Terraform para GCP](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Mejores prácticas de GKE](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [Guía de seguridad de GCP](https://cloud.google.com/security/best-practices)
- [Documentación de Vertex AI](https://cloud.google.com/vertex-ai/docs)

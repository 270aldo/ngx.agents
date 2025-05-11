/**
 * NGX Agents - Variables de configuración para Terraform
 * 
 * Este archivo define las variables que se pueden configurar
 * para personalizar el despliegue de la infraestructura.
 */

# Configuración del proyecto

variable "project_id" {
  description = "ID del proyecto de Google Cloud"
  type        = string
}

variable "region" {
  description = "Región de Google Cloud para desplegar los recursos"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zona de Google Cloud para desplegar los recursos"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Entorno de despliegue (development, staging, production)"
  type        = string
  default     = "development"
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "El valor de environment debe ser 'development', 'staging' o 'production'."
  }
}

# Configuración de aplicaciones

variable "app_name" {
  description = "Nombre de la aplicación"
  type        = string
  default     = "ngx-agents"
}

variable "app_version" {
  description = "Versión de la aplicación"
  type        = string
  default     = "1.0.0"
}

variable "domain" {
  description = "Dominio para la aplicación (si aplica)"
  type        = string
  default     = ""
}

# Configuración de Kubernetes

variable "cluster_name" {
  description = "Nombre del cluster de GKE"
  type        = string
  default     = "ngx-agents-cluster"
}

variable "min_node_count" {
  description = "Número mínimo de nodos en el cluster"
  type        = number
  default     = 1
}

variable "max_node_count" {
  description = "Número máximo de nodos en el cluster"
  type        = number
  default     = 5
}

variable "machine_type" {
  description = "Tipo de máquina para los nodos del cluster"
  type        = string
  default     = "e2-standard-2"
}

# Configuración de observabilidad

variable "enable_monitoring" {
  description = "Activar monitoreo con Cloud Monitoring"
  type        = bool
  default     = true
}

variable "enable_logging" {
  description = "Activar logging con Cloud Logging"
  type        = bool
  default     = true
}

variable "retention_days" {
  description = "Días de retención de logs"
  type        = number
  default     = 30
}

variable "alert_notification_channels" {
  description = "Lista de canales de notificación para alertas"
  type        = list(string)
  default     = []
}

variable "pagerduty_service_key" {
  description = "Clave de servicio de PagerDuty para alertas"
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_profiler" {
  description = "Activar Cloud Profiler para analizar rendimiento de la aplicación"
  type        = bool
  default     = false
}

variable "enable_trace" {
  description = "Activar Cloud Trace para seguimiento distribuido"
  type        = bool
  default     = true
}

# Configuración de base de datos

variable "database_tier" {
  description = "Tipo de instancia para Cloud SQL"
  type        = string
  default     = "db-f1-micro"
}

variable "database_availability_type" {
  description = "Tipo de disponibilidad para Cloud SQL (REGIONAL o ZONAL)"
  type        = string
  default     = "ZONAL"
}

variable "enable_private_ip" {
  description = "Activar IP privada para Cloud SQL"
  type        = bool
  default     = true
}

variable "database_backup_enabled" {
  description = "Activar backups automáticos de base de datos"
  type        = bool
  default     = true
}

# Vertex AI

variable "enable_vertex_ai" {
  description = "Activar Vertex AI para procesamiento de modelos"
  type        = bool
  default     = true
}

variable "vertex_ai_region" {
  description = "Región para Vertex AI"
  type        = string
  default     = "us-central1"
}

variable "enforce_vertex_ai_quotas" {
  description = "Aplicar límites de cuota para el uso de Vertex AI"
  type        = bool
  default     = false
}

variable "gemini_token_quota" {
  description = "Cuota de tokens diaria para modelos Gemini (si enforce_vertex_ai_quotas=true)"
  type        = number
  default     = 1000000  # 1 millón de tokens por día
}

variable "vertex_ai_model_nombres" {
  description = "Mapa de nombres de modelos a utilizar en Vertex AI"
  type        = map(string)
  default     = {
    "gemini-pro"       = "gemini-1.0-pro",
    "gemini-pro-vision" = "gemini-1.0-pro-vision",
    "gemini-ultra"     = "gemini-1.0-ultra",
    "text-embedding"   = "textembedding-gecko@latest"
  }
}

variable "vertex_endpoint_scaling" {
  description = "Configuración de escalado para endpoints de Vertex AI"
  type = object({
    min_replica_count = number
    max_replica_count = number
  })
  default = {
    min_replica_count = 1
    max_replica_count = 5
  }
}

# Configuración de seguridad

variable "enable_vpc_service_controls" {
  description = "Activar VPC Service Controls para mejorar la seguridad"
  type        = bool
  default     = false
}

variable "enable_binary_authorization" {
  description = "Activar Binary Authorization para verificar imágenes de contenedores"
  type        = bool
  default     = false
}

variable "access_policy_id" {
  description = "ID de la política de acceso para VPC Service Controls (requerido si enable_vpc_service_controls = true)"
  type        = string
  default     = ""
}

variable "project_number" {
  description = "Número del proyecto de Google Cloud (requerido para VPC Service Controls)"
  type        = string
  default     = ""
}

variable "security_level" {
  description = "Nivel de seguridad para el proyecto (basic, enhanced, strict)"
  type        = string
  default     = "basic"
  
  validation {
    condition     = contains(["basic", "enhanced", "strict"], var.security_level)
    error_message = "El valor de security_level debe ser 'basic', 'enhanced' o 'strict'."
  }
}

variable "enable_shielded_nodes" {
  description = "Activar Shielded GKE Nodes para mejorar la seguridad"
  type        = bool
  default     = true
}

variable "enable_workload_identity" {
  description = "Activar Workload Identity para mejorar la seguridad"
  type        = bool
  default     = true
}

variable "org_id" {
  description = "ID de la organización de Google Cloud (requerido para Security Command Center)"
  type        = string
  default     = ""
}

variable "enable_security_command_center" {
  description = "Activar Security Command Center para monitoreo de seguridad avanzado"
  type        = bool
  default     = false
}

variable "enable_cloud_armor" {
  description = "Activar Cloud Armor para protección contra ataques DDoS y WAF"
  type        = bool
  default     = false
}

variable "cloud_armor_rules" {
  description = "Reglas de Cloud Armor para protección WAF"
  type = list(object({
    action      = string
    priority    = number
    description = string
    match       = map(string)
  }))
  default = []
}

variable "enable_data_loss_prevention" {
  description = "Activar Cloud DLP para protección de datos sensibles"
  type        = bool
  default     = false
}

# Configuración de redes

variable "network_name" {
  description = "Nombre de la red VPC"
  type        = string
  default     = "ngx-agents-network"
}

variable "subnetwork_name" {
  description = "Nombre de la subred"
  type        = string
  default     = "ngx-agents-subnetwork"
}

variable "subnetwork_cidr" {
  description = "CIDR de la subred"
  type        = string
  default     = "10.0.0.0/16"
}

# Configuración de CI/CD

variable "repository_name" {
  description = "Nombre del repositorio en Artifact Registry"
  type        = string
  default     = "ngx-agents"
}

variable "cloudbuild_trigger_branch" {
  description = "Rama que activa el proceso de CI/CD"
  type        = string
  default     = "main"
}

# Configuración de escalado automático

variable "cpu_utilization_target" {
  description = "Objetivo de utilización de CPU para autoescalado"
  type        = number
  default     = 0.65
}

# Configuración de tolerancia a fallos

variable "health_check_interval_sec" {
  description = "Intervalo para health checks en segundos"
  type        = number
  default     = 10
}

variable "health_check_timeout_sec" {
  description = "Timeout para health checks en segundos"
  type        = number
  default     = 5
}

variable "health_check_healthy_threshold" {
  description = "Número de intentos exitosos consecutivos para considerar healthy"
  type        = number
  default     = 2
}

variable "health_check_unhealthy_threshold" {
  description = "Número de intentos fallidos consecutivos para considerar unhealthy"
  type        = number
  default     = 2
}

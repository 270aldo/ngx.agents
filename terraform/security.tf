/**
 * NGX Agents - Security Configuration
 * 
 * Este módulo configura todos los aspectos de seguridad para la infraestructura,
 * incluyendo gestión de secretos, encriptación, y políticas IAM.
 */

# Secret Manager para almacenar secretos sensibles
resource "google_secret_manager_secret" "supabase_url" {
  secret_id = "ngx-agents-supabase-url"
  
  replication {
    auto {
      customer_managed_encryption {
        kms_key_name = google_kms_crypto_key.secrets_key.id
      }
    }
  }
  
  labels = {
    app         = var.app_name
    environment = var.environment
    type        = "api-key"
  }
}

resource "google_secret_manager_secret" "supabase_key" {
  secret_id = "ngx-agents-supabase-key"
  
  replication {
    auto {
      customer_managed_encryption {
        kms_key_name = google_kms_crypto_key.secrets_key.id
      }
    }
  }
  
  labels = {
    app         = var.app_name
    environment = var.environment
    type        = "api-key"
  }
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "ngx-agents-jwt-secret"
  
  replication {
    auto {
      customer_managed_encryption {
        kms_key_name = google_kms_crypto_key.secrets_key.id
      }
    }
  }
  
  labels = {
    app         = var.app_name
    environment = var.environment
    type        = "api-key"
  }
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "ngx-agents-gemini-api-key"
  
  replication {
    auto {
      customer_managed_encryption {
        kms_key_name = google_kms_crypto_key.secrets_key.id
      }
    }
  }
  
  labels = {
    app         = var.app_name
    environment = var.environment
    type        = "api-key"
  }
}

resource "google_secret_manager_secret" "pagerduty_service_key" {
  secret_id = "ngx-agents-pagerduty-service-key"
  
  replication {
    auto {
      customer_managed_encryption {
        kms_key_name = google_kms_crypto_key.secrets_key.id
      }
    }
  }
  
  labels = {
    app         = var.app_name
    environment = var.environment
    type        = "api-key"
  }
}

# Conceder acceso a los secretos a la cuenta de servicio de la aplicación
resource "google_secret_manager_secret_iam_member" "supabase_url_access" {
  secret_id = google_secret_manager_secret.supabase_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ngx_agents_service_account.email}"
}

resource "google_secret_manager_secret_iam_member" "supabase_key_access" {
  secret_id = google_secret_manager_secret.supabase_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ngx_agents_service_account.email}"
}

resource "google_secret_manager_secret_iam_member" "jwt_secret_access" {
  secret_id = google_secret_manager_secret.jwt_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ngx_agents_service_account.email}"
}

resource "google_secret_manager_secret_iam_member" "gemini_api_key_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ngx_agents_service_account.email}"
}

resource "google_secret_manager_secret_iam_member" "pagerduty_service_key_access" {
  secret_id = google_secret_manager_secret.pagerduty_service_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ngx_agents_service_account.email}"
}

# Configuración de Cloud KMS para encriptación de datos
resource "google_kms_key_ring" "ngx_agents_keyring" {
  name     = "ngx-agents-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "secrets_key" {
  name     = "ngx-agents-secrets-key"
  key_ring = google_kms_key_ring.ngx_agents_keyring.id
  
  # Configuración de rotación automática
  rotation_period = "2592000s" # 30 días
  
  lifecycle {
    prevent_destroy = true
  }
  
  version_template {
    algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
    protection_level = var.security_level == "strict" ? "HSM" : "SOFTWARE"
  }
}

# Políticas IAM para la clave KMS
resource "google_kms_crypto_key_iam_binding" "crypto_key_iam" {
  crypto_key_id = google_kms_crypto_key.secrets_key.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  
  members = [
    "serviceAccount:${google_service_account.ngx_agents_service_account.email}",
    "serviceAccount:service-${var.project_number}@gcp-sa-secretmanager.iam.gserviceaccount.com",
  ]
}

# Configuración de políticas de seguridad adicionales según el nivel de seguridad

# Política organizacional para requerir OS Login
resource "google_organization_policy" "require_os_login" {
  count = var.security_level == "strict" ? 1 : 0
  
  constraint = "compute.requireOsLogin"
  boolean_policy {
    enforced = true
  }
}

# Política organizacional para restringir IP externas
resource "google_organization_policy" "restrict_external_ip" {
  count = var.security_level == "strict" || var.security_level == "enhanced" ? 1 : 0
  
  constraint = "compute.vmExternalIpAccess"
  list_policy {
    deny {
      all = true
    }
  }
}

# Política organizacional para requerir shielded VMs
resource "google_organization_policy" "require_shielded_vm" {
  count = var.security_level == "strict" || var.security_level == "enhanced" ? 1 : 0
  
  constraint = "compute.requireShieldedVm"
  boolean_policy {
    enforced = true
  }
}

# Security Command Center - activar si estamos en modo de seguridad estricto
resource "google_project_service" "security_center" {
  count   = var.security_level == "strict" ? 1 : 0
  service = "securitycenter.googleapis.com"
  
  disable_on_destroy = false
}

resource "google_scc_notification_config" "scc_notification" {
  count        = var.security_level == "strict" ? 1 : 0
  config_id    = "ngx-agents-findings"
  organization = var.org_id
  description  = "Notificaciones de hallazgos de seguridad para NGX Agents"
  
  pubsub_topic  = google_pubsub_topic.scc_notifications[0].id
  
  streaming_config {
    filter = "state = \"ACTIVE\""
  }
  
  depends_on = [google_project_service.security_center]
}

# Crear tema de Pub/Sub para notificaciones de Security Command Center
resource "google_pubsub_topic" "scc_notifications" {
  count = var.security_level == "strict" ? 1 : 0
  name  = "ngx-agents-scc-notifications"
}

resource "google_pubsub_subscription" "scc_subscription" {
  count  = var.security_level == "strict" ? 1 : 0
  name   = "ngx-agents-scc-subscription"
  topic  = google_pubsub_topic.scc_notifications[0].name
  
  ack_deadline_seconds = 20
  
  push_config {
    push_endpoint = "https://${var.region}-${var.project_id}.cloudfunctions.net/handle-scc-notification"
    
    attributes = {
      x-goog-version = "v1"
    }
  }
  
  message_retention_duration = "604800s" # 7 días
}

# Política de retención de logs de seguridad
resource "google_logging_project_bucket_config" "security_logs_bucket" {
  project        = var.project_id
  location       = var.region
  bucket_id      = "security-logs"
  description    = "Bucket para almacenar logs de seguridad"
  retention_days = 365
}

resource "google_logging_project_sink" "security_logs_sink" {
  name        = "security-logs-sink"
  destination = "logging.googleapis.com/projects/${var.project_id}/locations/${var.region}/buckets/security-logs"
  filter      = "resource.type=\"k8s_cluster\" OR resource.type=\"gce_firewall_rule\" OR resource.type=\"audited_resource\""
  
  # Usar una cuenta de servicio única para el sink
  unique_writer_identity = true
}

# Gestión de RBAC para GKE
resource "kubernetes_cluster_role" "ngx_agents_admin" {
  metadata {
    name = "ngx-agents-admin"
  }
  
  rule {
    api_groups = [""]
    resources  = ["pods", "services", "configmaps", "secrets"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }
  
  rule {
    api_groups = ["apps"]
    resources  = ["deployments", "statefulsets"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }
  
  rule {
    api_groups = ["networking.k8s.io"]
    resources  = ["ingresses"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }
  
  rule {
    api_groups = ["autoscaling"]
    resources  = ["horizontalpodautoscalers"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }
  
  rule {
    api_groups = ["batch"]
    resources  = ["jobs", "cronjobs"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }
}

resource "kubernetes_cluster_role_binding" "ngx_agents_admin_binding" {
  metadata {
    name = "ngx-agents-admin-binding"
  }
  
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.ngx_agents_admin.metadata[0].name
  }
  
  subject {
    kind      = "ServiceAccount"
    name      = "ngx-agents"
    namespace = kubernetes_namespace.ngx_agents.metadata[0].name
  }
}

# Outputs para información de seguridad
output "kms_keyring_id" {
  description = "ID del keyring KMS para encriptación"
  value       = google_kms_key_ring.ngx_agents_keyring.id
}

output "security_level_configured" {
  description = "Nivel de seguridad configurado para el proyecto"
  value       = var.security_level
}

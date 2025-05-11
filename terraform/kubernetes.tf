/**
 * NGX Agents - Kubernetes Configuration
 * 
 * Este módulo configura el cluster de Kubernetes (GKE) optimizado para
 * ejecutar NGX Agents con soporte completo para observabilidad y alta disponibilidad.
 */

# GKE Cluster principal
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region
  
  # Eliminar el node pool por defecto, utilizaremos uno personalizado
  remove_default_node_pool = true
  initial_node_count       = 1
  
  # Configuración de networking
  network    = google_compute_network.ngx_agents_network.name
  subnetwork = google_compute_subnetwork.ngx_agents_subnetwork.name
  
  # Configurar IP Aliasing para los pods
  ip_allocation_policy {
    cluster_secondary_range_name  = "${var.subnetwork_name}-pods"
    services_secondary_range_name = "${var.subnetwork_name}-services"
  }
  
  # Habilitar VPC-native (usando IP Aliasing)
  networking_mode = "VPC_NATIVE"
  
  # Control de acceso privado
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false # Permitir acceso desde Internet al endpoint público
    master_ipv4_cidr_block  = "172.16.0.0/28" # Rango de IPs para el control plane
  }
  
  # Habilitar Workload Identity para integrar con GCP IAM
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  # Configuración de seguridad
  dynamic "binary_authorization" {
    for_each = var.enable_binary_authorization ? [1] : []
    content {
      evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
    }
  }
  
  # Configuración de observabilidad
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }
  
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
    
    managed_prometheus {
      enabled = true
    }
    
    advanced_datapath_observability_config {
      enable_metrics = true
      enable_relay   = true
    }
  }
  
  # Configurar addons
  addons_config {
    http_load_balancing {
      disabled = false
    }
    
    horizontal_pod_autoscaling {
      disabled = false
    }
    
    network_policy_config {
      disabled = false
    }
    
    gcp_filestore_csi_driver_config {
      enabled = true
    }
    
    config_connector_config {
      enabled = true
    }
    
    cloudrun_config {
      enabled = true
    }
    
    gke_backup_agent_config {
      enabled = true
    }
  }
  
  # Configuración de red
  network_policy {
    enabled  = true
    provider = "CALICO"
  }
  
  # Protección contra borrado accidental
  deletion_protection = true
  
  # Configuración de actualizaciones automáticas
  release_channel {
    channel = var.environment == "production" ? "STABLE" : "REGULAR"
  }
  
  maintenance_policy {
    daily_maintenance_window {
      start_time = "02:00"
    }
  }
  
  # Configurar security posture
  security_posture_config {
    vulnerability_mode = var.security_level == "strict" ? "VULNERABILITY_ENTERPRISE" : "VULNERABILITY_STANDARD"
    mode = var.security_level == "strict" ? "SECURITY_POSTURE_ENTERPRISE" : "SECURITY_POSTURE_STANDARD"
  }
  
  # Configurar nodos seguros (Shielded GKE Nodes)
  dynamic "node_config" {
    for_each = var.enable_shielded_nodes ? [1] : []
    content {
      shielded_instance_config {
        enable_secure_boot          = true
        enable_integrity_monitoring = true
      }
    }
  }
  
  # Configuración de reparación automática
  cluster_autoscaling {
    enabled = true
    
    resource_limits {
      resource_type = "cpu"
      minimum       = 2
      maximum       = 32
    }
    
    resource_limits {
      resource_type = "memory"
      minimum       = 4
      maximum       = 64
    }
    
    auto_provisioning_defaults {
      disk_size = 100
      disk_type = "pd-standard"
      
      oauth_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]
      
      service_account = google_service_account.gke_service_account.email
    }
  }
}

# Node pool principal para aplicaciones
resource "google_container_node_pool" "primary_nodes" {
  name       = "primary-nodes"
  cluster    = google_container_cluster.primary.name
  location   = var.region
  
  # Número inicial y máximo de nodos por zona
  initial_node_count = var.min_node_count
  
  # Configuración de autoescalado
  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }
  
  # Configuración de administración
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  # Configuración de los nodos
  node_config {
    machine_type = var.machine_type
    disk_size_gb = 100
    disk_type    = "pd-standard"
    
    # Etiquetas para organizar recursos
    labels = {
      env  = var.environment
      app  = var.app_name
      role = "primary"
    }
    
    # Tags para reglas de firewall
    tags = ["gke-node", "ngx-agents", "http-server", "https-server"]
    
    # OAuth Scopes para permisos
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    # Asignar cuenta de servicio a los nodos
    service_account = google_service_account.gke_service_account.email
    
    # Utilizar Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    # Configuración de nodos protegidos
    shielded_instance_config {
      enable_secure_boot          = var.enable_shielded_nodes
      enable_integrity_monitoring = true
    }
  }
}

# Node pool específico para A2A para escalar independientemente
resource "google_container_node_pool" "a2a_nodes" {
  name       = "a2a-nodes"
  cluster    = google_container_cluster.primary.name
  location   = var.region
  
  initial_node_count = 1
  
  autoscaling {
    min_node_count = 1
    max_node_count = var.max_node_count
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  node_config {
    machine_type = var.machine_type
    disk_size_gb = 100
    
    labels = {
      env  = var.environment
      app  = var.app_name
      role = "a2a-server"
    }
    
    taint {
      key    = "role"
      value  = "a2a"
      effect = "NO_SCHEDULE"
    }
    
    # OAuth Scopes para permisos
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    # Asignar cuenta de servicio a los nodos
    service_account = google_service_account.gke_service_account.email
    
    # Utilizar Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

# Cuenta de servicio para nodos de GKE
resource "google_service_account" "gke_service_account" {
  account_id   = "ngx-agents-gke-sa"
  display_name = "NGX Agents GKE Service Account"
  description  = "Cuenta de servicio para nodos de GKE del sistema NGX Agents"
}

# Asignar permisos requeridos para la cuenta de servicio
resource "google_project_iam_member" "gke_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.gke_service_account.email}"
}

resource "google_project_iam_member" "gke_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.gke_service_account.email}"
}

resource "google_project_iam_member" "artifact_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.gke_service_account.email}"
}

# Cuenta de servicio para Workload Identity de la aplicación
resource "google_service_account" "ngx_agents_service_account" {
  account_id   = "ngx-agents-app-sa"
  display_name = "NGX Agents Application Service Account"
  description  = "Cuenta de servicio para la aplicación NGX Agents"
}

resource "google_service_account_iam_binding" "workload_identity_binding" {
  service_account_id = google_service_account.ngx_agents_service_account.name
  role               = "roles/iam.workloadIdentityUser"
  
  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[default/ngx-agents]",
  ]
}

# Health checks para servicios de NGX Agents
resource "google_compute_health_check" "ngx_agents_health_check" {
  name                = "ngx-agents-health-check"
  timeout_sec         = var.health_check_timeout_sec
  check_interval_sec  = var.health_check_interval_sec
  healthy_threshold   = var.health_check_healthy_threshold
  unhealthy_threshold = var.health_check_unhealthy_threshold
  
  http_health_check {
    port         = 8000
    request_path = "/api/v1/health"
  }
}

resource "google_compute_health_check" "a2a_health_check" {
  name                = "ngx-agents-a2a-health-check"
  timeout_sec         = var.health_check_timeout_sec
  check_interval_sec  = var.health_check_interval_sec
  healthy_threshold   = var.health_check_healthy_threshold
  unhealthy_threshold = var.health_check_unhealthy_threshold
  
  http_health_check {
    port         = 8001
    request_path = "/health"
  }
}

# Kubernetes namespace para NGX Agents
resource "kubernetes_namespace" "ngx_agents" {
  metadata {
    name = "ngx-agents"
    
    labels = {
      name        = "ngx-agents"
      environment = var.environment
      managed-by  = "terraform"
    }
  }
}

# ConfigMap para aplicación
resource "kubernetes_config_map" "ngx_agents_config" {
  metadata {
    name      = "ngx-agents-config"
    namespace = kubernetes_namespace.ngx_agents.metadata[0].name
  }
  
  data = {
    "ENVIRONMENT"        = var.environment
    "LOG_LEVEL"          = var.environment == "production" ? "INFO" : "DEBUG"
    "SERVICE_NAME"       = var.app_name
    "VERSION"            = var.app_version
    "ENABLE_MONITORING"  = tostring(var.enable_monitoring)
    "ENABLE_TRACING"     = tostring(var.enable_trace)
    "VERTEX_AI_REGION"   = var.vertex_ai_region
  }
}

# Outputs para uso en otros pasos
output "gke_cluster_name" {
  value       = google_container_cluster.primary.name
  description = "Nombre del cluster GKE"
}

output "gke_cluster_endpoint" {
  value       = google_container_cluster.primary.endpoint
  description = "Endpoint del cluster GKE"
  sensitive   = true
}

output "gke_cluster_ca_certificate" {
  value       = google_container_cluster.primary.master_auth.0.cluster_ca_certificate
  description = "Certificado CA público del cluster GKE"
  sensitive   = true
}

output "kubernetes_service_account" {
  value       = google_service_account.ngx_agents_service_account.email
  description = "Email de la cuenta de servicio para la aplicación NGX Agents"
}

output "kubernetes_namespace" {
  value       = kubernetes_namespace.ngx_agents.metadata[0].name
  description = "Namespace de Kubernetes para NGX Agents"
}

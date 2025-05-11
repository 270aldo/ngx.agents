/**
 * NGX Agents - Network Configuration
 * 
 * Este módulo configura la infraestructura de red necesaria para el sistema NGX Agents,
 * incluyendo VPC, subredes, reglas de firewall, y conectores de VPC para servicios sin servidor.
 */

# Red VPC principal para el sistema
resource "google_compute_network" "ngx_agents_network" {
  name                    = var.network_name
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL"
  project                 = var.project_id
}

# Subred principal para los servicios
resource "google_compute_subnetwork" "ngx_agents_subnetwork" {
  name          = var.subnetwork_name
  ip_cidr_range = var.subnetwork_cidr
  region        = var.region
  network       = google_compute_network.ngx_agents_network.id
  
  private_ip_google_access = true
  
  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
  
  secondary_ip_range {
    range_name    = "${var.subnetwork_name}-pods"
    ip_cidr_range = "10.1.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "${var.subnetwork_name}-services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

# Reglas de firewall para la red

# Permitir tráfico interno en la VPC 
resource "google_compute_firewall" "allow_internal" {
  name    = "allow-internal"
  network = google_compute_network.ngx_agents_network.name
  
  allow {
    protocol = "icmp"
  }
  
  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  
  source_ranges = [var.subnetwork_cidr, "10.1.0.0/16", "10.2.0.0/16"]
}

# Permitir acceso desde health checks de Google Cloud
resource "google_compute_firewall" "allow_health_checks" {
  name    = "allow-health-checks"
  network = google_compute_network.ngx_agents_network.name
  
  allow {
    protocol = "tcp"
    ports    = ["8000", "8001", "443"]
  }
  
  # Rangos de IP de los health checks de Google Cloud
  source_ranges = ["35.191.0.0/16", "130.211.0.0/22"]
  target_tags   = ["http-server", "https-server", "lb-health-check"]
}

# Permitir tráfico SSH para administración (con restricciones de IP)
resource "google_compute_firewall" "allow_ssh_iap" {
  name    = "allow-ssh-iap"
  network = google_compute_network.ngx_agents_network.name
  
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  
  # Rangos de IP para Identity-Aware Proxy (IAP)
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["ssh"]
}

# Permitir tráfico HTTP/HTTPS desde el balanceador de carga a las instancias
resource "google_compute_firewall" "allow_lb_traffic" {
  name    = "allow-lb-traffic"
  network = google_compute_network.ngx_agents_network.name
  
  allow {
    protocol = "tcp"
    ports    = ["8000", "8001", "443"]
  }
  
  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
  target_tags   = ["http-server", "https-server"]
}

# Conector de VPC para servicios sin servidor
resource "google_vpc_access_connector" "connector" {
  name          = "vpc-connector"
  region        = var.region
  network       = google_compute_network.ngx_agents_network.name
  ip_cidr_range = "10.8.0.0/28"
  
  # Escalar automáticamente de 2 a 10 instancias según la carga
  min_instances = 2
  max_instances = 10
}

# Router Cloud NAT para permitir que las instancias privadas accedan a Internet
resource "google_compute_router" "router" {
  name    = "nat-router"
  region  = var.region
  network = google_compute_network.ngx_agents_network.name
}

resource "google_compute_router_nat" "nat" {
  name                               = "nat-config"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Private Service Connect para Vertex AI
resource "google_compute_global_address" "private_service_connect_address" {
  name          = "vertex-ai-psc-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.ngx_agents_network.id
  
  # Usar un rango de IPs que no se superponga con otras subredes
  address       = "10.100.0.0"
}

resource "google_service_networking_connection" "private_service_connection" {
  network                 = google_compute_network.ngx_agents_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_service_connect_address.name]
}

# Perimetro de seguridad de VPC Service Controls (opcional)
resource "google_access_context_manager_service_perimeter" "service_perimeter" {
  count = var.enable_vpc_service_controls ? 1 : 0
  
  name         = "accessPolicies/${var.access_policy_id}/servicePerimeters/ngx_agents_perimeter"
  title        = "NGX Agents Service Perimeter"
  perimeter_type = "PERIMETER_TYPE_REGULAR"
  
  status {
    restricted_services = [
      "aiplatform.googleapis.com",
      "sqladmin.googleapis.com",
      "storage.googleapis.com"
    ]
    
    vpc_accessible_services {
      enable_restriction = true
      allowed_services   = ["aiplatform.googleapis.com", "sqladmin.googleapis.com"]
    }
    
    resources = [
      "projects/${var.project_number}"
    ]
    
    ingress_policies {
      ingress_from {
        sources {
          access_level = "*"
        }
        identity_type = "ANY_IDENTITY"
      }
      ingress_to {
        resources = ["*"]
        operations {
          service_name = "*"
          method_selectors {
            method = "*"
          }
        }
      }
    }
  }
  
  # Este recurso depende de la existencia de una política de acceso
  # que debe configurarse manualmente o mediante otro recurso de Terraform
  depends_on = []
}

# Outputs para usar en otros módulos
output "network_name" {
  description = "Nombre de la red VPC creada"
  value       = google_compute_network.ngx_agents_network.name
}

output "subnetwork_name" {
  description = "Nombre de la subred creada"
  value       = google_compute_subnetwork.ngx_agents_subnetwork.name
}

output "vpc_connector_id" {
  description = "ID del conector de VPC para servicios sin servidor"
  value       = google_vpc_access_connector.connector.id
}

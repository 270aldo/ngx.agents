# Terraform configuration for NGX Agents Cloud Infrastructure

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Create a GCS bucket for storing agent artifacts
resource "google_storage_bucket" "ngx_agents_artifacts" {
  name          = "${var.project_id}-ngx-agents-artifacts"
  location      = var.region
  storage_class = "STANDARD"
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Create service account for NGX Agents
resource "google_service_account" "ngx_agents_service_account" {
  account_id   = "ngx-agents"
  display_name = "NGX Agents Service Account"
  description  = "Service account for NGX Agents to access Google Cloud resources"
}

# Grant Vertex AI user role
resource "google_project_iam_binding" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"

  members = [
    "serviceAccount:${google_service_account.ngx_agents_service_account.email}",
  ]
}

# Grant GCS admin role for artifacts
resource "google_storage_bucket_iam_binding" "gcs_admin" {
  bucket  = google_storage_bucket.ngx_agents_artifacts.name
  role    = "roles/storage.admin"
  
  members = [
    "serviceAccount:${google_service_account.ngx_agents_service_account.email}",
  ]
}

# Create a Cloud Run service for the NGX Agents API
resource "google_cloud_run_service" "ngx_agents_api" {
  name     = "ngx-agents-api"
  location = var.region

  template {
    spec {
      containers {
        image = var.container_image
        
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
        
        env {
          name  = "SUPABASE_URL"
          value = var.supabase_url
        }
        
        env {
          name  = "GEMINI_API_KEY"
          value = var.gemini_api_key
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }
      }
      
      service_account_name = google_service_account.ngx_agents_service_account.email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Create a Cloud Run service for the A2A server
resource "google_cloud_run_service" "ngx_agents_a2a" {
  name     = "ngx-agents-a2a"
  location = var.region

  template {
    spec {
      containers {
        image = var.a2a_container_image
        
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }
      }
      
      service_account_name = google_service_account.ngx_agents_service_account.email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Allow unauthenticated access to the API
resource "google_cloud_run_service_iam_binding" "api_public" {
  location = google_cloud_run_service.ngx_agents_api.location
  service  = google_cloud_run_service.ngx_agents_api.name
  role     = "roles/run.invoker"
  members  = ["allUsers"]
}

# Allow unauthenticated access to the A2A server for internal communication
resource "google_cloud_run_service_iam_binding" "a2a_public" {
  location = google_cloud_run_service.ngx_agents_a2a.location
  service  = google_cloud_run_service.ngx_agents_a2a.name
  role     = "roles/run.invoker"
  members  = ["allUsers"]
}

# Cloud SQL instance for database
resource "google_sql_database_instance" "ngx_agents_db" {
  name             = "ngx-agents-db"
  region           = var.region
  database_version = "POSTGRES_14"
  
  settings {
    tier = "db-f1-micro"
    
    backup_configuration {
      enabled = true
      start_time = "03:00"
    }
    
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "allow-all-for-development"
        value = "0.0.0.0/0"  # Note: Restrict this to specific IPs in production
      }
    }
  }
}

# Database for NGX Agents
resource "google_sql_database" "ngx_agents" {
  name     = "ngxdb"
  instance = google_sql_database_instance.ngx_agents_db.name
}

# Cloud Build triggers for CI/CD
resource "google_cloudbuild_trigger" "ngx_agents_main" {
  name        = "ngx-agents-main"
  description = "Build and deploy NGX Agents from main branch"
  
  github {
    owner = var.github_owner
    name  = var.github_repo
    
    push {
      branch = "^main$"
    }
  }
  
  filename = "cloudbuild.yaml"
}

# Secret Manager for sensitive credentials
resource "google_secret_manager_secret" "supabase_key" {
  secret_id = "supabase-key"
  
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"
  
  replication {
    automatic = true
  }
}

# Grant access to secrets
resource "google_secret_manager_secret_iam_binding" "supabase_key_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.supabase_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  
  members = [
    "serviceAccount:${google_service_account.ngx_agents_service_account.email}",
  ]
}

resource "google_secret_manager_secret_iam_binding" "gemini_api_key_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  
  members = [
    "serviceAccount:${google_service_account.ngx_agents_service_account.email}",
  ]
}

# Cloud Scheduler for periodic tasks
resource "google_cloud_scheduler_job" "health_check_job" {
  name      = "ngx-agents-health-check"
  schedule  = "*/15 * * * *"
  time_zone = "America/Phoenix"
  
  http_target {
    uri         = "${google_cloud_run_service.ngx_agents_api.status[0].url}/health"
    http_method = "GET"
    oidc_token {
      service_account_email = google_service_account.ngx_agents_service_account.email
    }
  }
}

# Log-based metrics for monitoring
resource "google_logging_metric" "error_count" {
  name        = "ngx_agents_error_count"
  filter      = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"ngx-agents-api\" AND severity>=ERROR"
  description = "Count of error logs in NGX Agents API"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

# Cloud Monitoring alerts
resource "google_monitoring_alert_policy" "error_rate_alert" {
  display_name = "NGX Agents Error Rate Alert"
  combiner     = "OR"
  
  conditions {
    display_name = "Error Rate Threshold"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.error_count.name}\" AND resource.type=\"cloud_run_revision\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [var.notification_channel_id]
}

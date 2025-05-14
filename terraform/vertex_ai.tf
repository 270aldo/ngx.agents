/**
 * NGX Agents - Vertex AI Configuration
 * 
 * Este módulo configura los recursos necesarios para utilizar Vertex AI,
 * incluyendo endpoints, modelos, y configuración de permisos para
 * optimizar el uso de los modelos de LLM con los agentes.
 */

# Configuración de Vertex AI y recursos asociados
resource "google_project_service" "vertex_ai" {
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

# Reserva de endpoints para modelos - mejora la latencia y disponibilidad
resource "google_vertex_ai_endpoint" "ngx_agents_endpoint" {
  display_name = "ngx-agents-endpoint"
  location     = var.vertex_ai_region
  
  depends_on = [google_project_service.vertex_ai]
}

# Bucket para almacenar artefactos de modelos
resource "google_storage_bucket" "model_artifacts" {
  name          = "${var.project_id}-model-artifacts"
  location      = var.region
  storage_class = "STANDARD"
  force_destroy = true

  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 90  # Retener artefactos de modelo por 90 días
    }
    action {
      type = "Delete"
    }
  }
}

# Configuración de IAM para acceso a Vertex AI
resource "google_project_iam_binding" "vertex_ai_user_binding" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  
  members = [
    "serviceAccount:${google_service_account.ngx_agents_service_account.email}",
  ]
}

resource "google_project_iam_binding" "vertex_ai_admin" {
  project = var.project_id
  role    = "roles/aiplatform.admin"
  
  members = [
    "serviceAccount:${google_service_account.ngx_agents_service_account.email}",
  ]
}

# Configuración para monitoreo de uso de Vertex AI
resource "google_monitoring_dashboard" "vertex_ai_usage" {
  dashboard_json = <<EOF
{
  "displayName": "NGX Agents - Vertex AI Usage",
  "gridLayout": {
    "widgets": [
      {
        "title": "Vertex AI API Calls",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"serviceruntime.googleapis.com/api/request_count\" resource.type=\"consumed_api\" resource.label.\"service\"=\"aiplatform.googleapis.com\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_RATE",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Calls/minute"
          }
        }
      },
      {
        "title": "Vertex AI API Latency",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"serviceruntime.googleapis.com/api/request_latencies\" resource.type=\"consumed_api\" resource.label.\"service\"=\"aiplatform.googleapis.com\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_PERCENTILE_99",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE",
              "legendTemplate": "p99"
            },
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"serviceruntime.googleapis.com/api/request_latencies\" resource.type=\"consumed_api\" resource.label.\"service\"=\"aiplatform.googleapis.com\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_PERCENTILE_50",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE",
              "legendTemplate": "p50"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Latency (ms)"
          }
        }
      },
      {
        "title": "Vertex AI Error Rate",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"serviceruntime.googleapis.com/api/error_count\" resource.type=\"consumed_api\" resource.label.\"service\"=\"aiplatform.googleapis.com\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_RATE",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Errors/minute"
          }
        }
      },
      {
        "title": "Gemini Model Token Usage",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents/gemini_token_usage\" resource.type=\"k8s_container\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_SUM",
                    "alignmentPeriod": "3600s"
                  }
                }
              },
              "plotType": "STACKED_BAR"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Tokens"
          }
        }
      },
      {
        "title": "Vertex AI Client Cache Hit Rate",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/vertex_ai.client.cache_hits\" resource.type=\"k8s_container\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_RATE",
                    "alignmentPeriod": "300s"
                  }
                }
              },
              "plotType": "LINE",
              "legendTemplate": "Cache Hits"
            },
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/vertex_ai.client.cache_misses\" resource.type=\"k8s_container\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_RATE",
                    "alignmentPeriod": "300s"
                  }
                }
              },
              "plotType": "LINE",
              "legendTemplate": "Cache Misses"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Requests/minute"
          }
        }
      },
      {
        "title": "Vertex AI Client Latency by Operation",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/vertex_ai.client.latency\" resource.type=\"k8s_container\" metric.label.operation=\"content_generation\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_PERCENTILE_95",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE",
              "legendTemplate": "Content Generation"
            },
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/vertex_ai.client.latency\" resource.type=\"k8s_container\" metric.label.operation=\"embedding\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_PERCENTILE_95",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE",
              "legendTemplate": "Embedding"
            },
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/vertex_ai.client.latency\" resource.type=\"k8s_container\" metric.label.operation=\"multimodal\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_PERCENTILE_95",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE",
              "legendTemplate": "Multimodal"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Latency (ms)"
          }
        }
      },
      {
        "title": "Estimated Cost (Tokens per day)",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/vertex_ai.client.tokens\" resource.type=\"k8s_container\" metric.label.type=\"total\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_SUM",
                    "alignmentPeriod": "86400s"
                  }
                }
              },
              "plotType": "COLUMN"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Tokens/day"
          }
        }
      },
      {
        "title": "Vertex AI Client Errors by Type",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/vertex_ai.client.errors\" resource.type=\"k8s_container\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_RATE",
                    "alignmentPeriod": "300s",
                    "crossSeriesReducer": "REDUCE_NONE",
                    "groupByFields": ["metric.label.error_type"]
                  }
                }
              },
              "plotType": "STACKED_BAR"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Errors/minute"
          }
        }
      }
    ]
  }
}
EOF
}

# Alertas para uso de Vertex AI
resource "google_monitoring_alert_policy" "vertex_ai_error_rate" {
  display_name = "NGX Agents - Vertex AI Error Rate"
  combiner     = "OR"
  conditions {
    display_name = "Vertex AI Error Rate > 5%"
    condition_threshold {
      filter          = "metric.type=\"serviceruntime.googleapis.com/api/error_count\" resource.type=\"consumed_api\" resource.label.\"service\"=\"aiplatform.googleapis.com\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = var.alert_notification_channels

  documentation {
    content   = "Alta tasa de errores en llamadas a Vertex AI. Esto puede afectar el funcionamiento de los agentes que dependen de modelos de IA."
    mime_type = "text/markdown"
  }
}

# Política de cuotas - opcional, puede configurarse si es necesario un límite de uso
resource "google_service_usage_quota_policy" "vertex_ai_quota" {
  count = var.enforce_vertex_ai_quotas ? 1 : 0
  
  name = "projects/${var.project_id}/locations/${var.region}/quotaPolicies/vertex-ai-quota-policy"
  
  service_quotas {
    service = "aiplatform.googleapis.com"
    quota {
      unit      = "COUNT"
      metric    = "aiplatform.googleapis.com/gemini_1_pro_1_generate_tokens"
      dimension = "region"
      value     = var.gemini_token_quota
    }
  }
}

# Outputs que pueden ser útiles para la aplicación
output "vertex_ai_endpoint_id" {
  value = google_vertex_ai_endpoint.ngx_agents_endpoint.id
  description = "ID del endpoint de Vertex AI para los agentes"
}

output "model_artifacts_bucket" {
  value = google_storage_bucket.model_artifacts.name
  description = "Bucket para artefactos de modelos"
}

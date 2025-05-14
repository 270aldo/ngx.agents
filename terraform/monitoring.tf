/**
 * NGX Agents - Monitoring Configuration
 * 
 * Este módulo define los recursos de monitoreo y observabilidad para la aplicación NGX Agents:
 * - Dashboards para visualizar métricas de rendimiento
 * - Políticas de alertas para detectar problemas
 * - Canales de notificación para recibir alertas
 */

resource "google_monitoring_dashboard" "ngx_agents_overview" {
  dashboard_json = <<EOF
{
  "displayName": "NGX Agents - Panel General",
  "gridLayout": {
    "widgets": [
      {
        "title": "Estado de Servicios",
        "scorecard": {
          "timeSeriesQuery": {
            "timeSeriesFilter": {
              "filter": "metric.type=\"custom.googleapis.com/ngx_agents/health_status\"",
              "aggregation": {
                "perSeriesAligner": "ALIGN_MEAN",
                "alignmentPeriod": "60s"
              }
            },
            "unitOverride": "1"
          },
          "sparkChartView": {
            "sparkChartType": "SPARK_LINE"
          },
          "thresholds": [
            {
              "value": 0.5,
              "color": "RED",
              "direction": "BELOW"
            }
          ]
        }
      },
      {
        "title": "Solicitudes por minuto",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents_requests_total\"",
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
            "label": "Solicitudes/minuto"
          }
        }
      },
      {
        "title": "Latencia de API (percentiles)",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents_request_duration_seconds\" AND metric.label.percentile=\"50\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE",
              "legendTemplate": "p50"
            },
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents_request_duration_seconds\" AND metric.label.percentile=\"95\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE",
              "legendTemplate": "p95"
            },
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents_request_duration_seconds\" AND metric.label.percentile=\"99\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE",
              "legendTemplate": "p99"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Segundos"
          }
        }
      },
      {
        "title": "Uso de CPU",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents/cpu_usage\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "% CPU",
            "maxValue": 100
          }
        }
      },
      {
        "title": "Uso de Memoria",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents/memory_usage\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "% Memoria",
            "maxValue": 100
          }
        }
      },
      {
        "title": "Errores por minuto",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents_errors_total\"",
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
            "label": "Errores/minuto"
          }
        }
      }
    ]
  }
}
EOF
}

resource "google_monitoring_dashboard" "a2a_metrics" {
  dashboard_json = <<EOF
{
  "displayName": "NGX Agents - A2A Communication",
  "gridLayout": {
    "widgets": [
      {
        "title": "Mensajes A2A por minuto",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents/a2a_messages_total\"",
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
            "label": "Mensajes/minuto"
          }
        }
      },
      {
        "title": "Latencia de mensajes A2A",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents/a2a_latency_seconds\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN",
                    "alignmentPeriod": "60s"
                  }
                }
              },
              "plotType": "LINE"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Segundos"
          }
        }
      },
      {
        "title": "Errores A2A por minuto",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents/a2a_errors_total\"",
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
            "label": "Errores/minuto"
          }
        }
      }
    ]
  }
}
EOF
}

resource "google_monitoring_dashboard" "agent_metrics" {
  dashboard_json = <<EOF
{
  "displayName": "NGX Agents - Agent Performance",
  "gridLayout": {
    "widgets": [
      {
        "title": "Tiempo de procesamiento por agente",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents/agent_processing_time\" resource.type=\"k8s_container\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_MEAN",
                    "alignmentPeriod": "60s",
                    "crossSeriesReducer": "REDUCE_NONE",
                    "groupByFields": ["metric.label.agent_id"]
                  }
                }
              },
              "plotType": "LINE"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Segundos"
          }
        }
      },
      {
        "title": "Llamadas a skills por agente",
        "xyChart": {
          "dataSets": [
            {
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/ngx_agents/skill_calls_total\" resource.type=\"k8s_container\"",
                  "aggregation": {
                    "perSeriesAligner": "ALIGN_RATE",
                    "alignmentPeriod": "60s",
                    "crossSeriesReducer": "REDUCE_NONE",
                    "groupByFields": ["metric.label.agent_id"]
                  }
                }
              },
              "plotType": "STACKED_BAR"
            }
          ],
          "yAxis": {
            "scale": "LINEAR",
            "label": "Llamadas/minuto"
          }
        }
      }
    ]
  }
}
EOF
}

# Alert policies

resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "NGX Agents - Alta tasa de errores"
  combiner     = "OR"
  conditions {
    display_name = "Error rate > 5%"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/ngx_agents_errors_total\" resource.type=\"k8s_container\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.pagerduty.name]

  documentation {
    content   = "Alta tasa de errores detectada en los servicios NGX Agents. Revisar los logs para más detalles."
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_alert_policy" "high_latency" {
  display_name = "NGX Agents - Alta latencia"
  combiner     = "OR"
  conditions {
    display_name = "p95 latency > 2s"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/ngx_agents_request_duration_seconds\" resource.type=\"k8s_container\" metric.label.percentile=\"95\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 2
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.pagerduty.name]

  documentation {
    content   = "Alta latencia detectada en los servicios NGX Agents. La latencia p95 supera los 2 segundos."
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_alert_policy" "service_unavailable" {
  display_name = "NGX Agents - Servicio no disponible"
  combiner     = "OR"
  conditions {
    display_name = "Health status = 0"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/ngx_agents/health_status\" resource.type=\"k8s_container\""
      duration        = "60s"
      comparison      = "COMPARISON_LT"
      threshold_value = 0.5
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.pagerduty.name]

  documentation {
    content   = "Uno o más servicios de NGX Agents no responden. Verificar el estado de los pods y servicios."
    mime_type = "text/markdown"
  }
}

# Alertas específicas para Vertex AI
resource "google_monitoring_alert_policy" "vertex_ai_high_usage" {
  display_name = "NGX Agents - Vertex AI Alto Uso"
  combiner     = "OR"
  conditions {
    display_name = "Uso de tokens > 100,000/min"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/vertex_ai.client.tokens\" resource.type=\"k8s_container\" metric.label.type=\"total\""
      duration        = "900s"  # 15 minutos
      comparison      = "COMPARISON_GT"
      threshold_value = 100000
      aggregations {
        alignment_period   = "300s"  # 5 minutos
        per_series_aligner = "ALIGN_RATE"
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.pagerduty.name]

  documentation {
    content   = "Alto uso de tokens de Vertex AI detectado. Esto puede generar costos elevados. Revisar el uso y considerar ajustes en la caché o en los parámetros de generación."
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_alert_policy" "vertex_ai_low_cache_hit_rate" {
  display_name = "NGX Agents - Vertex AI Baja Tasa de Aciertos de Caché"
  combiner     = "OR"
  conditions {
    display_name = "Tasa de aciertos de caché < 50%"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/vertex_ai.client.cache_hits\" resource.type=\"k8s_container\""
      duration        = "1800s"  # 30 minutos
      comparison      = "COMPARISON_LT"
      threshold_value = 0.5
      denominator_filter = "metric.type=\"custom.googleapis.com/vertex_ai.client.cache_misses\" resource.type=\"k8s_container\""
      denominator_aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.pagerduty.name]

  documentation {
    content   = "Baja tasa de aciertos de caché en Vertex AI. Esto puede aumentar costos y latencia. Revisar la configuración de TTL y estrategias de caché."
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_notification_channel" "pagerduty" {
  display_name = "PagerDuty - NGX Agents"
  type         = "pagerduty"
  
  labels = {
    service_key = var.pagerduty_service_key
  }
  
  sensitive_labels {
    service_key = var.pagerduty_service_key
  }
}

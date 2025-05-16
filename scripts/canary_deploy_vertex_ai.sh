#!/bin/bash
# Script para despliegue gradual (Canary) del cliente Vertex AI optimizado
# 
# Este script implementa una estrategia de despliegue gradual para minimizar riesgos:
# 1. Despliega la nueva versión al 20% del tráfico
# 2. Monitorea métricas clave durante 30 minutos
# 3. Si no hay problemas, aumenta al 50% del tráfico
# 4. Monitorea durante 1 hora
# 5. Si no hay problemas, completa el despliegue al 100%
#
# Uso: ./canary_deploy_vertex_ai.sh [--version VERSION] [--namespace NAMESPACE] [--dry-run]

set -e

# Configuración por defecto
VERSION=${VERSION:-"latest"}
NAMESPACE=${NAMESPACE:-"ngx-agents"}
DRY_RUN=${DRY_RUN:-false}
MONITORING_ENDPOINT=${MONITORING_ENDPOINT:-"http://prometheus:9090"}
SLACK_WEBHOOK=${SLACK_WEBHOOK:-""}
PAGERDUTY_ROUTING_KEY=${PAGERDUTY_ROUTING_KEY:-""}

# Umbrales de alerta
ERROR_RATE_THRESHOLD=0.05  # 5%
LATENCY_P95_THRESHOLD=2000  # 2 segundos
CACHE_HIT_RATIO_THRESHOLD=0.4  # 40%

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parsear argumentos
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --version)
      VERSION="$2"
      shift
      shift
      ;;
    --namespace)
      NAMESPACE="$2"
      shift
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --help)
      echo "Uso: $0 [--version VERSION] [--namespace NAMESPACE] [--dry-run]"
      echo ""
      echo "Opciones:"
      echo "  --version VERSION    Versión a desplegar (default: latest)"
      echo "  --namespace NAMESPACE    Namespace de Kubernetes (default: ngx-agents)"
      echo "  --dry-run    Ejecutar en modo simulación sin aplicar cambios"
      exit 0
      ;;
    *)
      echo "Opción desconocida: $1"
      echo "Usa --help para ver las opciones disponibles"
      exit 1
      ;;
  esac
done

# Función para imprimir mensajes con timestamp
log() {
  local level=$1
  local message=$2
  local color=$NC
  
  case $level in
    INFO)
      color=$BLUE
      ;;
    SUCCESS)
      color=$GREEN
      ;;
    WARNING)
      color=$YELLOW
      ;;
    ERROR)
      color=$RED
      ;;
  esac
  
  echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message${NC}"
}

# Función para enviar notificaciones
notify() {
  local level=$1
  local message=$2
  
  log $level "$message"
  
  # Enviar a Slack si está configurado
  if [[ -n "$SLACK_WEBHOOK" ]]; then
    curl -s -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"[$level] Canary Deploy: $message\"}" \
      $SLACK_WEBHOOK > /dev/null
  fi
  
  # Enviar a PagerDuty si es un error y está configurado
  if [[ "$level" == "ERROR" && -n "$PAGERDUTY_ROUTING_KEY" ]]; then
    curl -s -X POST -H 'Content-type: application/json' \
      --data "{
        \"routing_key\": \"$PAGERDUTY_ROUTING_KEY\",
        \"event_action\": \"trigger\",
        \"payload\": {
          \"summary\": \"Canary Deploy Error: $message\",
          \"severity\": \"error\",
          \"source\": \"canary-deploy-script\"
        }
      }" \
      "https://events.pagerduty.com/v2/enqueue" > /dev/null
  fi
}

# Función para verificar si kubectl está disponible
check_kubectl() {
  if ! command -v kubectl &> /dev/null; then
    notify "ERROR" "kubectl no está disponible. Por favor, instálalo e inténtalo de nuevo."
    exit 1
  fi
  
  # Verificar acceso al cluster
  if ! kubectl get ns &> /dev/null; then
    notify "ERROR" "No se puede acceder al cluster de Kubernetes. Verifica la configuración."
    exit 1
  fi
  
  # Verificar si el namespace existe
  if ! kubectl get ns $NAMESPACE &> /dev/null; then
    notify "ERROR" "El namespace '$NAMESPACE' no existe."
    exit 1
  }
}

# Función para verificar si curl está disponible
check_curl() {
  if ! command -v curl &> /dev/null; then
    notify "ERROR" "curl no está disponible. Por favor, instálalo e inténtalo de nuevo."
    exit 1
  fi
}

# Función para verificar si jq está disponible
check_jq() {
  if ! command -v jq &> /dev/null; then
    notify "ERROR" "jq no está disponible. Por favor, instálalo e inténtalo de nuevo."
    exit 1
  fi
}

# Función para consultar métricas de Prometheus
query_prometheus() {
  local query=$1
  local result
  
  result=$(curl -s -G "$MONITORING_ENDPOINT/api/v1/query" --data-urlencode "query=$query")
  
  if [[ $(echo "$result" | jq -r '.status') != "success" ]]; then
    notify "ERROR" "Error al consultar Prometheus: $(echo "$result" | jq -r '.error // "Unknown error"')"
    return 1
  fi
  
  echo "$result" | jq -r '.data.result[0].value[1] // "0"'
}

# Función para verificar métricas de salud
check_health_metrics() {
  local traffic_percentage=$1
  local error_rate
  local latency_p95
  local cache_hit_ratio
  
  log "INFO" "Verificando métricas de salud para despliegue al $traffic_percentage%..."
  
  # Consultar tasa de errores
  error_rate=$(query_prometheus "sum(rate(vertex_ai_client_errors{version=\"$VERSION\"}[5m])) / sum(rate(vertex_ai_client_initializations{version=\"$VERSION\"}[5m]))")
  
  # Consultar latencia P95
  latency_p95=$(query_prometheus "histogram_quantile(0.95, sum(rate(vertex_ai_client_latency_bucket{version=\"$VERSION\",operation=\"content_generation\"}[5m])) by (le))")
  
  # Consultar ratio de aciertos de caché
  cache_hits=$(query_prometheus "sum(rate(vertex_ai_client_cache_hits{version=\"$VERSION\"}[5m]))")
  cache_misses=$(query_prometheus "sum(rate(vertex_ai_client_cache_misses{version=\"$VERSION\"}[5m]))")
  cache_hit_ratio=$(echo "scale=2; $cache_hits / ($cache_hits + $cache_misses)" | bc)
  
  # Verificar métricas contra umbrales
  if (( $(echo "$error_rate > $ERROR_RATE_THRESHOLD" | bc -l) )); then
    notify "ERROR" "Tasa de errores ($error_rate) supera el umbral ($ERROR_RATE_THRESHOLD)"
    return 1
  fi
  
  if (( $(echo "$latency_p95 > $LATENCY_P95_THRESHOLD" | bc -l) )); then
    notify "ERROR" "Latencia P95 ($latency_p95 ms) supera el umbral ($LATENCY_P95_THRESHOLD ms)"
    return 1
  fi
  
  if (( $(echo "$cache_hit_ratio < $CACHE_HIT_RATIO_THRESHOLD" | bc -l) )); then
    notify "WARNING" "Ratio de aciertos de caché ($cache_hit_ratio) por debajo del umbral ($CACHE_HIT_RATIO_THRESHOLD)"
    # No fallamos por esto, solo advertimos
  fi
  
  log "SUCCESS" "Métricas de salud OK para despliegue al $traffic_percentage%"
  log "INFO" "- Tasa de errores: $error_rate"
  log "INFO" "- Latencia P95: $latency_p95 ms"
  log "INFO" "- Ratio de aciertos de caché: $cache_hit_ratio"
  
  return 0
}

# Función para actualizar el despliegue
update_deployment() {
  local traffic_percentage=$1
  local deployment_name="vertex-ai-optimizer"
  
  log "INFO" "Actualizando despliegue al $traffic_percentage% de tráfico..."
  
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando actualización de despliegue al $traffic_percentage%"
    return 0
  fi
  
  # Actualizar el deployment con la nueva versión y peso de tráfico
  if [[ $traffic_percentage -eq 100 ]]; then
    # Despliegue completo - eliminar versión anterior
    kubectl -n $NAMESPACE set image deployment/$deployment_name optimizer=gcr.io/PROJECT_ID/ngx-agents-api:$VERSION
    kubectl -n $NAMESPACE patch deployment $deployment_name --type json -p '[{"op": "remove", "path": "/spec/template/metadata/annotations/sidecar.istio.io~1inject"}]'
  else
    # Despliegue canary - configurar peso de tráfico
    kubectl -n $NAMESPACE set image deployment/$deployment_name optimizer=gcr.io/PROJECT_ID/ngx-agents-api:$VERSION
    kubectl -n $NAMESPACE patch deployment $deployment_name --type json -p "[{\"op\": \"add\", \"path\": \"/spec/template/metadata/annotations/sidecar.istio.io~1inject\", \"value\": \"true\"}]"
    
    # Configurar VirtualService para dividir tráfico
    cat <<EOF | kubectl -n $NAMESPACE apply -f -
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: vertex-ai-optimizer-vs
spec:
  hosts:
  - vertex-ai-optimizer
  http:
  - route:
    - destination:
        host: vertex-ai-optimizer
        subset: stable
      weight: $((100 - $traffic_percentage))
    - destination:
        host: vertex-ai-optimizer
        subset: canary
      weight: $traffic_percentage
EOF
    
    # Configurar DestinationRule para definir subsets
    cat <<EOF | kubectl -n $NAMESPACE apply -f -
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: vertex-ai-optimizer-dr
spec:
  host: vertex-ai-optimizer
  subsets:
  - name: stable
    labels:
      version: stable
  - name: canary
    labels:
      version: canary
EOF
  fi
  
  # Verificar que el despliegue se haya actualizado correctamente
  kubectl -n $NAMESPACE rollout status deployment/$deployment_name --timeout=5m
  
  if [[ $? -ne 0 ]]; then
    notify "ERROR" "Error al actualizar el despliegue al $traffic_percentage%"
    return 1
  fi
  
  log "SUCCESS" "Despliegue actualizado al $traffic_percentage% de tráfico"
  return 0
}

# Función para realizar rollback
rollback() {
  local deployment_name="vertex-ai-optimizer"
  
  notify "WARNING" "Iniciando rollback del despliegue..."
  
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando rollback del despliegue"
    return 0
  fi
  
  # Realizar rollback del deployment
  kubectl -n $NAMESPACE rollout undo deployment/$deployment_name
  
  # Verificar que el rollback se haya completado correctamente
  kubectl -n $NAMESPACE rollout status deployment/$deployment_name --timeout=5m
  
  if [[ $? -ne 0 ]]; then
    notify "ERROR" "Error al realizar rollback del despliegue"
    return 1
  fi
  
  # Eliminar VirtualService y DestinationRule si existen
  kubectl -n $NAMESPACE delete virtualservice vertex-ai-optimizer-vs --ignore-not-found
  kubectl -n $NAMESPACE delete destinationrule vertex-ai-optimizer-dr --ignore-not-found
  
  notify "SUCCESS" "Rollback completado exitosamente"
  return 0
}

# Función principal
main() {
  log "INFO" "Iniciando despliegue gradual (Canary) del cliente Vertex AI optimizado"
  log "INFO" "Versión: $VERSION"
  log "INFO" "Namespace: $NAMESPACE"
  
  if [[ "$DRY_RUN" == "true" ]]; then
    log "WARNING" "Ejecutando en modo simulación (--dry-run)"
  fi
  
  # Verificar dependencias
  check_kubectl
  check_curl
  check_jq
  
  # Fase 1: Despliegue al 20%
  log "INFO" "=== FASE 1: Despliegue al 20% ==="
  if ! update_deployment 20; then
    rollback
    notify "ERROR" "Despliegue fallido en Fase 1"
    exit 1
  fi
  
  # Esperar 30 minutos y verificar métricas
  log "INFO" "Esperando 30 minutos para monitorear métricas..."
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando espera de 30 minutos"
    sleep 5
  else
    sleep 1800  # 30 minutos
  fi
  
  if ! check_health_metrics 20; then
    rollback
    notify "ERROR" "Verificación de métricas fallida en Fase 1"
    exit 1
  fi
  
  # Fase 2: Despliegue al 50%
  log "INFO" "=== FASE 2: Despliegue al 50% ==="
  if ! update_deployment 50; then
    rollback
    notify "ERROR" "Despliegue fallido en Fase 2"
    exit 1
  fi
  
  # Esperar 1 hora y verificar métricas
  log "INFO" "Esperando 1 hora para monitorear métricas..."
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando espera de 1 hora"
    sleep 10
  else
    sleep 3600  # 1 hora
  fi
  
  if ! check_health_metrics 50; then
    rollback
    notify "ERROR" "Verificación de métricas fallida en Fase 2"
    exit 1
  fi
  
  # Fase 3: Despliegue al 100%
  log "INFO" "=== FASE 3: Despliegue al 100% ==="
  if ! update_deployment 100; then
    rollback
    notify "ERROR" "Despliegue fallido en Fase 3"
    exit 1
  fi
  
  # Verificación final
  log "INFO" "Esperando 15 minutos para verificación final..."
  if [[ "$DRY_RUN" == "true" ]]; then
    log "INFO" "[DRY RUN] Simulando espera de 15 minutos"
    sleep 5
  else
    sleep 900  # 15 minutos
  fi
  
  if ! check_health_metrics 100; then
    rollback
    notify "ERROR" "Verificación final de métricas fallida"
    exit 1
  fi
  
  notify "SUCCESS" "Despliegue gradual completado exitosamente"
  log "INFO" "El cliente Vertex AI optimizado ha sido desplegado al 100% del tráfico"
}

# Ejecutar función principal
main
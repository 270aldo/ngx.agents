#!/bin/bash
# Script para desplegar NGX Agents en Kubernetes (GKE)

set -e

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para mostrar mensajes
log() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
  echo -e "${RED}[ERROR]${NC} $1"
  exit 1
}

# Verificar dependencias
check_dependencies() {
  log "Verificando dependencias..."
  
  if ! command -v kubectl &> /dev/null; then
    error "kubectl no está instalado. Por favor, instálalo antes de continuar."
  fi
  
  if ! command -v gcloud &> /dev/null; then
    error "gcloud no está instalado. Por favor, instálalo antes de continuar."
  fi
}

# Obtener el ID del proyecto de GCP
get_project_id() {
  log "Obteniendo ID del proyecto de GCP..."
  
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
  if [ -z "$PROJECT_ID" ]; then
    error "No se pudo obtener el ID del proyecto de GCP. Por favor, configura gcloud con 'gcloud config set project PROJECT_ID'."
  fi
  
  log "Usando proyecto: $PROJECT_ID"
  return 0
}

# Reemplazar PROJECT_ID en los archivos de Kubernetes
replace_project_id() {
  log "Reemplazando PROJECT_ID en los archivos de Kubernetes..."
  
  # Crear directorio temporal para los archivos procesados
  mkdir -p kubernetes/tmp
  
  # Procesar cada archivo
  for file in kubernetes/*.yaml; do
    basename=$(basename "$file")
    sed "s/PROJECT_ID/$PROJECT_ID/g" "$file" > "kubernetes/tmp/$basename"
  done
  
  log "Archivos procesados en kubernetes/tmp/"
}

# Aplicar configuraciones de Kubernetes
apply_kubernetes_configs() {
  log "Aplicando configuraciones de Kubernetes..."
  
  # Verificar conexión con el cluster
  if ! kubectl cluster-info &> /dev/null; then
    error "No se pudo conectar al cluster de Kubernetes. Verifica tu configuración de kubectl."
  fi
  
  # Aplicar configuraciones en orden
  log "Creando namespace y configuraciones básicas..."
  kubectl apply -f kubernetes/tmp/namespace-config.yaml || error "Error al aplicar namespace-config.yaml"
  
  log "Aplicando políticas de red..."
  kubectl apply -f kubernetes/tmp/network-policy.yaml || error "Error al aplicar network-policy.yaml"
  
  log "Desplegando servicios y deployments..."
  kubectl apply -f kubernetes/tmp/deployment.yaml || error "Error al aplicar deployment.yaml"
  
  log "Configurando ingress..."
  kubectl apply -f kubernetes/tmp/ingress.yaml || error "Error al aplicar ingress.yaml"
  
  log "Configuraciones aplicadas correctamente."
}

# Verificar estado del despliegue
verify_deployment() {
  log "Verificando estado del despliegue..."
  
  # Esperar a que los deployments estén disponibles
  kubectl rollout status deployment/ngx-agents-api -n ngx-agents
  kubectl rollout status deployment/ngx-agents-a2a -n ngx-agents
  
  # Mostrar información de los servicios
  log "Servicios desplegados:"
  kubectl get services -n ngx-agents
  
  # Mostrar información del ingress
  log "Ingress configurado:"
  kubectl get ingress -n ngx-agents
}

# Limpiar archivos temporales
cleanup() {
  log "Limpiando archivos temporales..."
  rm -rf kubernetes/tmp
}

# Función principal
main() {
  log "Iniciando despliegue de NGX Agents en Kubernetes..."
  
  check_dependencies
  get_project_id
  replace_project_id
  apply_kubernetes_configs
  verify_deployment
  cleanup
  
  log "Despliegue completado exitosamente."
}

# Ejecutar función principal
main

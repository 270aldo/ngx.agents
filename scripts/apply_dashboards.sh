#!/bin/bash
# Script para aplicar dashboards de monitoreo en el entorno de producción
# Este script aplica los dashboards definidos en Terraform

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directorio base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TERRAFORM_DIR="${BASE_DIR}/terraform"

# Verificar que Terraform está instalado
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Error: Terraform no está instalado.${NC}"
    echo "Por favor, instale Terraform: https://learn.hashicorp.com/tutorials/terraform/install-cli"
    exit 1
fi

# Verificar que gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: Google Cloud SDK no está instalado.${NC}"
    echo "Por favor, instale Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Verificar que el usuario está autenticado en gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${YELLOW}No se ha detectado una sesión activa de gcloud.${NC}"
    echo "Iniciando proceso de autenticación..."
    gcloud auth login
fi

# Función para aplicar un dashboard específico
apply_dashboard() {
    local dashboard_name=$1
    local dashboard_file=$2
    
    echo -e "${YELLOW}Aplicando dashboard: ${dashboard_name}${NC}"
    
    # Crear archivo temporal de configuración Terraform
    cat > "${TERRAFORM_DIR}/dashboard_${dashboard_name}.tf" <<EOF
resource "google_monitoring_dashboard" "${dashboard_name}" {
  dashboard_json = file("\${path.module}/dashboards/${dashboard_file}")
}
EOF
    
    # Inicializar Terraform si es necesario
    if [ ! -d "${TERRAFORM_DIR}/.terraform" ]; then
        echo "Inicializando Terraform..."
        (cd "${TERRAFORM_DIR}" && terraform init)
    fi
    
    # Aplicar el dashboard
    echo "Aplicando dashboard con Terraform..."
    (cd "${TERRAFORM_DIR}" && terraform apply -auto-approve -target=google_monitoring_dashboard.${dashboard_name})
    
    echo -e "${GREEN}Dashboard ${dashboard_name} aplicado correctamente.${NC}"
}

# Función principal
main() {
    echo -e "${YELLOW}=== Aplicando Dashboards de NGX Agents ===${NC}"
    
    # Verificar que los archivos de dashboard existen
    if [ ! -f "${TERRAFORM_DIR}/dashboards/operational_kpis.json" ]; then
        echo -e "${RED}Error: No se encontró el archivo de dashboard operational_kpis.json${NC}"
        exit 1
    fi
    
    if [ ! -f "${TERRAFORM_DIR}/dashboards/agent_dashboards.json" ]; then
        echo -e "${RED}Error: No se encontró el archivo de dashboard agent_dashboards.json${NC}"
        exit 1
    fi
    
    # Aplicar dashboards
    apply_dashboard "operational_kpis" "operational_kpis.json"
    apply_dashboard "agent_dashboards" "agent_dashboards.json"
    
    echo -e "${GREEN}=== Todos los dashboards han sido aplicados correctamente ===${NC}"
    echo "Puede acceder a los dashboards en la consola de Google Cloud:"
    echo "https://console.cloud.google.com/monitoring/dashboards"
}

# Ejecutar función principal
main "$@"
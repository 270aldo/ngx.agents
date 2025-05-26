#!/bin/bash
# Blue-Green Deployment Script for NGX Agents

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
CLUSTER_NAME="${CLUSTER_NAME:-ngx-agents-cluster}"
CLUSTER_ZONE="${CLUSTER_ZONE:-us-central1-a}"
NAMESPACE="${NAMESPACE:-ngx-agents}"
REGISTRY="gcr.io/${PROJECT_ID}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    for tool in kubectl gcloud docker helm; do
        if ! command -v $tool &> /dev/null; then
            log_error "$tool is not installed"
            exit 1
        fi
    done
    
    # Check GCP authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        log_error "Not authenticated with GCP. Run 'gcloud auth login'"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Build and push Docker images
build_and_push_images() {
    log_info "Building and pushing Docker images..."
    
    # Build base image
    log_info "Building base image..."
    docker build -f docker/Dockerfile.base -t ${REGISTRY}/ngx-agents-base:latest .
    docker push ${REGISTRY}/ngx-agents-base:latest
    
    # Build service images
    services=("api" "a2a-server")
    for service in "${services[@]}"; do
        log_info "Building $service image..."
        if [ "$service" == "api" ]; then
            docker build -f Dockerfile -t ${REGISTRY}/ngx-agents-${service}:latest .
        else
            docker build -f Dockerfile.a2a -t ${REGISTRY}/ngx-agents-${service}:latest .
        fi
        docker push ${REGISTRY}/ngx-agents-${service}:latest
    done
    
    # Build agent images
    agents=("orchestrator" "elite-training" "nutrition" "progress-tracker")
    for agent in "${agents[@]}"; do
        log_info "Building $agent agent image..."
        docker build -f docker/agents/Dockerfile.${agent//-/_} \
            --build-arg BASE_IMAGE=${REGISTRY}/ngx-agents-base:latest \
            -t ${REGISTRY}/ngx-agent-${agent}:latest .
        docker push ${REGISTRY}/ngx-agent-${agent}:latest
    done
    
    log_success "All images built and pushed successfully"
}

# Connect to GKE cluster
connect_to_cluster() {
    log_info "Connecting to GKE cluster..."
    gcloud container clusters get-credentials ${CLUSTER_NAME} \
        --zone ${CLUSTER_ZONE} \
        --project ${PROJECT_ID}
    log_success "Connected to cluster"
}

# Create namespace and base resources
setup_base_resources() {
    log_info "Setting up base resources..."
    
    # Create namespace
    kubectl apply -f k8s/base/namespace.yaml
    
    # Create ConfigMaps and Secrets
    kubectl apply -f k8s/base/configmap.yaml
    
    # Create secrets (ensure you've updated the values)
    if kubectl get secret ngx-agents-secrets -n ${NAMESPACE} &> /dev/null; then
        log_warning "Secrets already exist, skipping..."
    else
        kubectl apply -f k8s/base/secret.yaml
    fi
    
    # Create service account
    kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ngx-agents-sa
  namespace: ${NAMESPACE}
  annotations:
    iam.gke.io/gcp-service-account: ngx-agents@${PROJECT_ID}.iam.gserviceaccount.com
EOF
    
    log_success "Base resources created"
}

# Deploy infrastructure services
deploy_infrastructure() {
    log_info "Deploying infrastructure services..."
    
    # Deploy Redis
    kubectl apply -f k8s/services/redis.yaml
    
    # Wait for Redis to be ready
    kubectl wait --for=condition=ready pod -l app=redis -n ${NAMESPACE} --timeout=300s
    
    # Deploy A2A Server
    kubectl apply -f k8s/services/a2a-server.yaml
    
    # Wait for A2A Server to be ready
    kubectl wait --for=condition=ready pod -l app=a2a-server -n ${NAMESPACE} --timeout=300s
    
    log_success "Infrastructure services deployed"
}

# Blue-Green deployment for API
blue_green_deploy_api() {
    local SERVICE="ngx-api"
    local NEW_VERSION="${1:-latest}"
    local OLD_VERSION=$(kubectl get deployment ${SERVICE} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null | cut -d: -f2 || echo "none")
    
    log_info "Starting blue-green deployment for API (${OLD_VERSION} -> ${NEW_VERSION})..."
    
    # Create green deployment
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${SERVICE}-green
  namespace: ${NAMESPACE}
  labels:
    app: ${SERVICE}
    version: green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ${SERVICE}
      version: green
  template:
    metadata:
      labels:
        app: ${SERVICE}
        version: green
    spec:
      containers:
      - name: api
        image: ${REGISTRY}/${SERVICE}:${NEW_VERSION}
        ports:
        - containerPort: 8000
        env:
        - name: VERSION
          value: "${NEW_VERSION}"
        # Copy other env vars from k8s/services/api.yaml
EOF
    
    # Wait for green deployment to be ready
    kubectl wait --for=condition=available deployment/${SERVICE}-green -n ${NAMESPACE} --timeout=300s
    
    # Run smoke tests
    log_info "Running smoke tests on green deployment..."
    GREEN_POD=$(kubectl get pod -l app=${SERVICE},version=green -n ${NAMESPACE} -o jsonpath='{.items[0].metadata.name}')
    
    if kubectl exec ${GREEN_POD} -n ${NAMESPACE} -- curl -f http://localhost:8000/health; then
        log_success "Smoke tests passed"
        
        # Switch traffic to green
        log_info "Switching traffic to green deployment..."
        kubectl patch service ${SERVICE} -n ${NAMESPACE} -p '{"spec":{"selector":{"version":"green"}}}'
        
        # Wait for traffic to stabilize
        sleep 30
        
        # Delete old blue deployment
        if kubectl get deployment ${SERVICE}-blue -n ${NAMESPACE} &> /dev/null; then
            log_info "Removing old blue deployment..."
            kubectl delete deployment ${SERVICE}-blue -n ${NAMESPACE}
        fi
        
        # Rename green to blue for next deployment
        kubectl patch deployment ${SERVICE}-green -n ${NAMESPACE} -p '{"metadata":{"name":"'${SERVICE}'-blue"}}'
        
        log_success "Blue-green deployment completed successfully"
    else
        log_error "Smoke tests failed, rolling back..."
        kubectl delete deployment ${SERVICE}-green -n ${NAMESPACE}
        exit 1
    fi
}

# Deploy agents
deploy_agents() {
    log_info "Deploying agents..."
    
    # Deploy orchestrator first
    kubectl apply -f k8s/agents/orchestrator.yaml
    kubectl wait --for=condition=available deployment/orchestrator -n ${NAMESPACE} --timeout=300s
    
    # Deploy other agents
    agents=("elite-training" "nutrition" "progress-tracker")
    for agent in "${agents[@]}"; do
        # Generate from template
        sed -e "s/AGENT_NAME/${agent}/g" \
            -e "s/AGENT_DISPLAY_NAME/${agent//-/ }/g" \
            -e "s/AGENT_PORT/90$(( ${#agent} % 10 + 2 ))/g" \
            -e "s/AGENT_TYPE/specialist/g" \
            -e "s/PROJECT_ID/${PROJECT_ID}/g" \
            k8s/agents/agent-template.yaml | kubectl apply -f -
    done
    
    log_success "All agents deployed"
}

# Setup Istio resources
setup_istio() {
    log_info "Setting up Istio resources..."
    
    # Apply Istio gateway and virtual services
    kubectl apply -f k8s/istio/gateway.yaml
    kubectl apply -f k8s/istio/autoscaling.yaml
    
    log_success "Istio resources configured"
}

# Main deployment flow
main() {
    log_info "Starting NGX Agents deployment..."
    
    check_prerequisites
    
    # Parse command line arguments
    case "${1:-all}" in
        "build")
            build_and_push_images
            ;;
        "deploy")
            connect_to_cluster
            setup_base_resources
            deploy_infrastructure
            deploy_agents
            setup_istio
            ;;
        "blue-green")
            connect_to_cluster
            blue_green_deploy_api "${2:-latest}"
            ;;
        "all")
            build_and_push_images
            connect_to_cluster
            setup_base_resources
            deploy_infrastructure
            deploy_agents
            setup_istio
            ;;
        *)
            echo "Usage: $0 [build|deploy|blue-green|all] [version]"
            exit 1
            ;;
    esac
    
    log_success "Deployment completed successfully!"
    
    # Show status
    log_info "Deployment status:"
    kubectl get deployments -n ${NAMESPACE}
    kubectl get pods -n ${NAMESPACE}
    kubectl get services -n ${NAMESPACE}
}

# Run main function
main "$@"
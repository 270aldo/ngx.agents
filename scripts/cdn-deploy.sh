#!/bin/bash

# CDN Deployment Script for NGX Agents
# Configures and deploys Google Cloud CDN

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="agentes-ngx"
REGION="us-central1"
CDN_BACKEND="ngx-agents-backend"
URL_MAP="ngx-agents-url-map"
HTTPS_PROXY="ngx-agents-https-proxy"
FORWARDING_RULE="ngx-agents-forwarding-rule"
SSL_CERT="ngx-agents-ssl-cert"
SECURITY_POLICY="ngx-agents-security-policy"

echo -e "${GREEN}🚀 Starting CDN deployment for NGX Agents${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK${NC}"
    exit 1
fi

# Set project
echo -e "${YELLOW}📋 Setting project to ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable compute.googleapis.com
gcloud services enable cloudcdn.googleapis.com

# Create health check
echo -e "${YELLOW}🏥 Creating health check...${NC}"
gcloud compute health-checks create http ${CDN_BACKEND}-health-check \
    --port=80 \
    --request-path=/health \
    --check-interval=10s \
    --timeout=5s \
    --healthy-threshold=2 \
    --unhealthy-threshold=3 \
    --global \
    || echo "Health check already exists"

# Create backend service with CDN enabled
echo -e "${YELLOW}🌐 Creating backend service with CDN...${NC}"
gcloud compute backend-services create ${CDN_BACKEND} \
    --protocol=HTTPS \
    --port-name=http \
    --timeout=30s \
    --health-checks=${CDN_BACKEND}-health-check \
    --global \
    --enable-cdn \
    --cache-mode=CACHE_ALL_STATIC \
    --default-ttl=3600 \
    --max-ttl=86400 \
    --client-ttl=3600 \
    --negative-caching \
    --serve-while-stale=86400 \
    || echo "Backend service already exists"

# Update backend service CDN policy
echo -e "${YELLOW}📝 Updating CDN cache policies...${NC}"
gcloud compute backend-services update ${CDN_BACKEND} \
    --global \
    --cache-key-policy-include-host \
    --cache-key-policy-include-protocol \
    --cache-key-policy-include-query-string \
    --cache-key-policy-query-string-whitelist=v,w,h,q,f

# Create URL map
echo -e "${YELLOW}🗺️  Creating URL map...${NC}"
gcloud compute url-maps create ${URL_MAP} \
    --default-service=${CDN_BACKEND} \
    --global \
    || echo "URL map already exists"

# Create managed SSL certificate
echo -e "${YELLOW}🔒 Creating managed SSL certificate...${NC}"
gcloud compute ssl-certificates create ${SSL_CERT} \
    --domains=api.ngx-agents.com,cdn.ngx-agents.com \
    --global \
    || echo "SSL certificate already exists"

# Create HTTPS proxy
echo -e "${YELLOW}🔗 Creating HTTPS proxy...${NC}"
gcloud compute target-https-proxies create ${HTTPS_PROXY} \
    --url-map=${URL_MAP} \
    --ssl-certificates=${SSL_CERT} \
    --global \
    --quic-override=ENABLE \
    || echo "HTTPS proxy already exists"

# Reserve external IP
echo -e "${YELLOW}🌍 Reserving external IP address...${NC}"
gcloud compute addresses create ${FORWARDING_RULE}-ip \
    --ip-version=IPV4 \
    --global \
    || echo "IP address already reserved"

# Get the reserved IP
EXTERNAL_IP=$(gcloud compute addresses describe ${FORWARDING_RULE}-ip --global --format="get(address)")
echo -e "${GREEN}✅ Reserved IP: ${EXTERNAL_IP}${NC}"

# Create forwarding rule
echo -e "${YELLOW}➡️  Creating forwarding rule...${NC}"
gcloud compute forwarding-rules create ${FORWARDING_RULE} \
    --address=${EXTERNAL_IP} \
    --global \
    --target-https-proxy=${HTTPS_PROXY} \
    --ports=443 \
    || echo "Forwarding rule already exists"

# Create security policy
echo -e "${YELLOW}🛡️  Creating security policy...${NC}"
gcloud compute security-policies create ${SECURITY_POLICY} \
    --description="Security policy for NGX Agents CDN" \
    || echo "Security policy already exists"

# Add rate limiting rule
echo -e "${YELLOW}⏱️  Adding rate limiting rule...${NC}"
gcloud compute security-policies rules create 1000 \
    --security-policy=${SECURITY_POLICY} \
    --expression="true" \
    --action="throttle" \
    --rate-limit-threshold-count=100 \
    --rate-limit-threshold-interval-sec=60 \
    --conform-action="allow" \
    --exceed-action="deny-429" \
    --enforce-on-key="IP" \
    || echo "Rate limiting rule already exists"

# Enable Cloud Armor DDoS protection
echo -e "${YELLOW}🔰 Enabling DDoS protection...${NC}"
gcloud compute security-policies update ${SECURITY_POLICY} \
    --enable-layer7-ddos-defense

# Apply security policy to backend
echo -e "${YELLOW}🔐 Applying security policy to backend...${NC}"
gcloud compute backend-services update ${CDN_BACKEND} \
    --security-policy=${SECURITY_POLICY} \
    --global

# Add backend to backend service (you need to specify your actual backend)
echo -e "${YELLOW}🔌 Note: You need to add your actual backend (NEG/IG) to the backend service${NC}"
echo -e "${YELLOW}Example: gcloud compute backend-services add-backend ${CDN_BACKEND} --global --neg=YOUR_NEG --neg-zone=${REGION}-a${NC}"

# Display CDN information
echo -e "\n${GREEN}✅ CDN deployment completed!${NC}"
echo -e "\n${YELLOW}📊 CDN Information:${NC}"
echo -e "External IP: ${EXTERNAL_IP}"
echo -e "Domains: api.ngx-agents.com, cdn.ngx-agents.com"
echo -e "Backend Service: ${CDN_BACKEND}"
echo -e "URL Map: ${URL_MAP}"
echo -e "SSL Certificate: ${SSL_CERT}"

echo -e "\n${YELLOW}⚠️  Next steps:${NC}"
echo -e "1. Update your DNS records to point to: ${EXTERNAL_IP}"
echo -e "2. Add your actual backend (NEG/Instance Group) to the backend service"
echo -e "3. Test CDN functionality with: curl -I https://cdn.ngx-agents.com/test"
echo -e "4. Monitor CDN performance in Cloud Console > Network Services > Cloud CDN"

# Test CDN cache headers
echo -e "\n${YELLOW}🧪 To test CDN cache headers:${NC}"
echo -e "curl -I https://cdn.ngx-agents.com/static/test.jpg"
echo -e "Look for headers: x-goog-cached, age, cache-control"

echo -e "\n${GREEN}🎉 CDN deployment script completed!${NC}"
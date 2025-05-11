#!/bin/bash

# Script para configurar el entorno de desarrollo para NGX Agents
# Este script instala todas las dependencias necesarias y configura el entorno

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Configurando entorno de desarrollo para NGX Agents ===${NC}"

# Verificar si Python está instalado
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}Python detectado: ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}Error: Python 3 no está instalado. Por favor, instala Python 3.8 o superior.${NC}"
    exit 1
fi

# Verificar si pip está instalado
if command -v pip3 &>/dev/null; then
    PIP_VERSION=$(pip3 --version)
    echo -e "${GREEN}Pip detectado: ${PIP_VERSION}${NC}"
else
    echo -e "${RED}Error: pip3 no está instalado. Por favor, instala pip para Python 3.${NC}"
    exit 1
fi

# Crear entorno virtual
echo -e "${YELLOW}Creando entorno virtual...${NC}"
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo -e "${RED}Error al crear el entorno virtual. Asegúrate de tener instalado el paquete venv.${NC}"
    exit 1
fi

# Activar entorno virtual
echo -e "${YELLOW}Activando entorno virtual...${NC}"
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}Error al activar el entorno virtual.${NC}"
    exit 1
fi

# Actualizar pip
echo -e "${YELLOW}Actualizando pip...${NC}"
pip install --upgrade pip

# Instalar dependencias
echo -e "${YELLOW}Instalando dependencias...${NC}"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Error al instalar las dependencias. Revisa el archivo requirements.txt.${NC}"
    exit 1
fi

# Instalar el paquete en modo desarrollo
echo -e "${YELLOW}Instalando el paquete en modo desarrollo...${NC}"
pip install -e .
if [ $? -ne 0 ]; then
    echo -e "${RED}Error al instalar el paquete en modo desarrollo.${NC}"
    exit 1
fi

# Configurar variables de entorno
echo -e "${YELLOW}Configurando variables de entorno...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creando archivo .env a partir de .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}Archivo .env creado. Por favor, edita el archivo con tus credenciales.${NC}"
    else
        echo -e "${YELLOW}No se encontró el archivo .env.example. Creando archivo .env básico...${NC}"
        cat > .env << EOF
# Configuración de NGX Agents
DEBUG=True
LOG_LEVEL=INFO

# Configuración de Google Cloud
GCP_PROJECT_ID=your-project-id
VERTEX_AI_LOCATION=us-central1
VERTEX_MODEL=gemini-1.5-pro

# Configuración de Supabase
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key

# Configuración de Redis (opcional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Configuración de telemetría
ENABLE_TELEMETRY=True
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
EOF
        echo -e "${GREEN}Archivo .env básico creado. Por favor, edita el archivo con tus credenciales.${NC}"
    fi
fi

# Verificar instalación ejecutando pruebas básicas
echo -e "${YELLOW}Verificando instalación...${NC}"
python -c "import vertexai; import google.cloud.aiplatform; import opentelemetry.instrumentation.fastapi; print('Importaciones básicas correctas')"
if [ $? -ne 0 ]; then
    echo -e "${RED}Error al verificar la instalación. Algunas dependencias pueden no estar instaladas correctamente.${NC}"
    echo -e "${YELLOW}Puedes intentar instalar manualmente las dependencias faltantes.${NC}"
else
    echo -e "${GREEN}Verificación básica completada con éxito.${NC}"
fi

echo -e "${GREEN}=== Configuración del entorno de desarrollo completada ===${NC}"
echo -e "${YELLOW}Para activar el entorno virtual en el futuro, ejecuta:${NC}"
echo -e "${GREEN}source venv/bin/activate${NC}"
echo -e "${YELLOW}Para ejecutar las pruebas, ejecuta:${NC}"
echo -e "${GREEN}python -m pytest${NC}"
echo -e "${YELLOW}Para ejecutar la aplicación, ejecuta:${NC}"
echo -e "${GREEN}uvicorn app.main:app --reload${NC}"
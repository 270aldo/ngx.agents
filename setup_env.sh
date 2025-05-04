#!/bin/bash
# Script para configurar un entorno virtual limpio y reproducible

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Configurando entorno virtual para NGX Agents...${NC}"

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 no está instalado. Por favor, instálalo primero.${NC}"
    exit 1
fi

# Eliminar entorno virtual existente si existe
if [ -d "venv" ]; then
    echo -e "${YELLOW}Eliminando entorno virtual existente...${NC}"
    rm -rf venv
fi

# Crear nuevo entorno virtual
echo -e "${YELLOW}Creando nuevo entorno virtual...${NC}"
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo -e "${RED}Error al crear el entorno virtual.${NC}"
    exit 1
fi

# Activar entorno virtual
echo -e "${YELLOW}Activando entorno virtual...${NC}"
source venv/bin/activate

# Actualizar pip
echo -e "${YELLOW}Actualizando pip...${NC}"
pip install --upgrade pip

# Instalar dependencias principales
echo -e "${YELLOW}Instalando dependencias principales...${NC}"
pip install -e .

# Instalar dependencias de desarrollo y pruebas
echo -e "${YELLOW}Instalando dependencias de desarrollo y pruebas...${NC}"
pip install -e ".[dev,test]"

# Verificar instalación
echo -e "${YELLOW}Verificando instalación...${NC}"
python -c "import sys; print(f'Python {sys.version}')"
pip list | grep -E 'fastapi|uvicorn|pydantic|pytest|google-adk|supabase|python-json-logger'

echo -e "${GREEN}¡Entorno virtual configurado correctamente!${NC}"
echo -e "${YELLOW}Para activar el entorno virtual, ejecuta:${NC} source venv/bin/activate"
echo -e "${YELLOW}Para ejecutar pruebas unitarias:${NC} pytest -m unit"
echo -e "${YELLOW}Para ejecutar pruebas de agentes:${NC} pytest -m agents"
echo -e "${YELLOW}Para ejecutar pruebas de integración:${NC} pytest -m integration"

#!/bin/bash
# Script para configurar un entorno virtual limpio y reproducible con Poetry

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Configurando entorno virtual para NGX Agents con Poetry...${NC}"

# Verificar si Poetry está instalado
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}Error: Poetry no está instalado. Por favor, instálalo primero:${NC}"
    echo -e "${YELLOW}curl -sSL https://install.python-poetry.org | python3 -${NC}"
    exit 1
fi

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 no está instalado. Por favor, instálalo primero.${NC}"
    exit 1
fi

# Configurar Poetry para crear el entorno virtual en el directorio del proyecto
echo -e "${YELLOW}Configurando Poetry para crear el entorno virtual en el directorio del proyecto...${NC}"
poetry config virtualenvs.in-project true

# Eliminar entorno virtual existente si existe
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Eliminando entorno virtual existente...${NC}"
    rm -rf .venv
fi

# Crear nuevo entorno virtual e instalar dependencias
echo -e "${YELLOW}Creando nuevo entorno virtual e instalando dependencias...${NC}"
poetry install --no-root --with dev,test,agents,clients,core,tools

# Activar entorno virtual
echo -e "${YELLOW}Activando entorno virtual...${NC}"
source .venv/bin/activate

# Verificar instalación
echo -e "${YELLOW}Verificando instalación...${NC}"
python -c "import sys; print(f'Python {sys.version}')"
poetry show | grep -E 'fastapi|uvicorn|pydantic|pytest|google-adk|supabase|python-json-logger'

echo -e "${GREEN}¡Entorno virtual configurado correctamente con Poetry!${NC}"
echo -e "${YELLOW}Para activar el entorno virtual, ejecuta:${NC} source .venv/bin/activate"
echo -e "${YELLOW}Para ejecutar pruebas unitarias:${NC} pytest -m unit"
echo -e "${YELLOW}Para ejecutar pruebas de agentes:${NC} pytest -m agents"
echo -e "${YELLOW}Para ejecutar pruebas de integración:${NC} pytest -m integration"
echo -e "${YELLOW}Para instalar solo componentes específicos:${NC} poetry install --no-root --with dev,test,agents"

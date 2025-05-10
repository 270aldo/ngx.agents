#!/bin/bash

# Script para ejecutar pruebas de compatibilidad entre componentes
# Este script verifica que los componentes pueden comunicarse correctamente

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Ejecutando pruebas de compatibilidad entre componentes ===${NC}"

# Verificar que los entornos virtuales existen
if [ ! -d ".venvs" ]; then
    echo -e "${YELLOW}No se encontraron entornos virtuales. Ejecutando setup_component_envs.sh...${NC}"
    ./setup_component_envs.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error al configurar entornos virtuales. Abortando.${NC}"
        exit 1
    fi
fi

# Crear entorno virtual para pruebas de compatibilidad
echo -e "${YELLOW}Creando entorno virtual para pruebas de compatibilidad...${NC}"
python -m venv .venvs/compatibility
source .venvs/compatibility/bin/activate

# Instalar pytest y otras dependencias necesarias
echo -e "${YELLOW}Instalando dependencias para pruebas...${NC}"
pip install pytest pytest-asyncio pytest-cov

# Ejecutar pruebas de compatibilidad
echo -e "${YELLOW}Ejecutando pruebas de compatibilidad...${NC}"
python -m pytest tests/compatibility -v -m compatibility

# Guardar el código de salida
EXIT_CODE=$?

# Desactivar entorno virtual
deactivate

# Mostrar resultado
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=== Pruebas de compatibilidad completadas con éxito ===${NC}"
else
    echo -e "${RED}=== Pruebas de compatibilidad fallidas. Revisa los errores. ===${NC}"
fi

exit $EXIT_CODE

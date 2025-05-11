#!/bin/bash
# Script para ejecutar las pruebas de integración con Google ADK

# Colores para la salida
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Ejecutando pruebas de integración con Google ADK...${NC}"
echo

# Verificar que la biblioteca oficial de Google ADK esté instalada
if python -c "import google.adk" 2>/dev/null; then
    echo -e "${GREEN}✓ Biblioteca oficial de Google ADK detectada${NC}"
else
    echo -e "${YELLOW}⚠ Biblioteca oficial de Google ADK no detectada${NC}"
    echo -e "${YELLOW}  Se utilizarán stubs locales como fallback${NC}"
fi
echo

# Ejecutar las pruebas de integración con Google ADK
echo -e "${YELLOW}Ejecutando pruebas...${NC}"
poetry run pytest tests/test_adk_integration.py -v

# Verificar el resultado
if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}✓ Pruebas de integración con Google ADK completadas exitosamente${NC}"
else
    echo
    echo -e "${RED}✗ Pruebas de integración con Google ADK fallaron${NC}"
    echo -e "${YELLOW}  Verifica la instalación de la biblioteca oficial de Google ADK${NC}"
    echo -e "${YELLOW}  o revisa los logs para más detalles${NC}"
fi
echo

# Ejecutar el ejemplo de uso
echo -e "${YELLOW}Ejecutando ejemplo de uso...${NC}"
poetry run python examples/adk_usage_example.py

# Verificar el resultado
if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}✓ Ejemplo de uso ejecutado exitosamente${NC}"
else
    echo
    echo -e "${RED}✗ Ejemplo de uso falló${NC}"
    echo -e "${YELLOW}  Verifica la instalación de la biblioteca oficial de Google ADK${NC}"
    echo -e "${YELLOW}  o revisa los logs para más detalles${NC}"
fi

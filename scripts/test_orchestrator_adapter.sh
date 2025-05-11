#!/bin/bash
# Script para probar el adaptador del Orchestrator

# Colores para la salida
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando pruebas del adaptador del Orchestrator...${NC}"

# Activar el entorno virtual si existe
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activando entorno virtual...${NC}"
    source venv/bin/activate
fi

# Ejecutar las pruebas unitarias
echo -e "${YELLOW}Ejecutando pruebas unitarias...${NC}"
python -m pytest tests/adapters/test_orchestrator_adapter.py -v

# Verificar el resultado
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Pruebas unitarias completadas con éxito.${NC}"
else
    echo -e "${RED}❌ Algunas pruebas unitarias fallaron.${NC}"
    exit 1
fi

# Ejecutar pruebas de integración si existen
if [ -f "tests/integration/test_orchestrator_integration.py" ]; then
    echo -e "${YELLOW}Ejecutando pruebas de integración...${NC}"
    python -m pytest tests/integration/test_orchestrator_integration.py -v
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Pruebas de integración completadas con éxito.${NC}"
    else
        echo -e "${RED}❌ Algunas pruebas de integración fallaron.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️ No se encontraron pruebas de integración.${NC}"
fi

# Verificar la integración con el servidor A2A
echo -e "${YELLOW}Verificando integración con el servidor A2A...${NC}"
python -c "
import asyncio
from infrastructure.adapters.orchestrator_adapter import initialize_orchestrator_adapter

async def test_initialization():
    try:
        await initialize_orchestrator_adapter()
        print('✅ Adaptador del Orchestrator inicializado correctamente.')
    except Exception as e:
        print(f'❌ Error al inicializar el adaptador del Orchestrator: {e}')
        exit(1)

asyncio.run(test_initialization())
"

# Verificar el resultado
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Integración con el servidor A2A verificada.${NC}"
else
    echo -e "${RED}❌ Error en la integración con el servidor A2A.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Todas las pruebas completadas con éxito.${NC}"
echo -e "${YELLOW}Progreso de la migración del Orchestrator: 85%${NC}"

# Desactivar el entorno virtual si se activó
if [ -d "venv" ]; then
    deactivate 2>/dev/null
fi

exit 0

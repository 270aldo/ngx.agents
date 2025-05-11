#!/bin/bash

# Script para probar el adaptador de Recovery Corrective

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Iniciando pruebas del adaptador de Recovery Corrective ===${NC}"

# Verificar entorno virtual
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}No se detectó un entorno virtual activo. Activando entorno...${NC}"
    source .venv/bin/activate || { echo -e "${RED}Error al activar el entorno virtual. Asegúrate de que exista.${NC}"; exit 1; }
fi

# Verificar que el archivo de prueba existe
if [ ! -f "tests/adapters/test_recovery_corrective_adapter.py" ]; then
    echo -e "${RED}Error: No se encontró el archivo de prueba tests/adapters/test_recovery_corrective_adapter.py${NC}"
    exit 1
fi

# Verificar que el adaptador existe
if [ ! -f "infrastructure/adapters/recovery_corrective_adapter.py" ]; then
    echo -e "${RED}Error: No se encontró el adaptador infrastructure/adapters/recovery_corrective_adapter.py${NC}"
    exit 1
fi

echo -e "${YELLOW}Ejecutando pruebas unitarias...${NC}"

# Ejecutar pruebas con pytest
python -m pytest tests/adapters/test_recovery_corrective_adapter.py -v

# Verificar resultado
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Todas las pruebas del adaptador de Recovery Corrective pasaron correctamente.${NC}"
else
    echo -e "${RED}❌ Algunas pruebas fallaron. Revisa los errores anteriores.${NC}"
    exit 1
fi

echo -e "${YELLOW}Ejecutando prueba de integración básica...${NC}"

# Crear un script temporal de Python para probar la integración básica
TMP_SCRIPT=$(mktemp)
cat > $TMP_SCRIPT << 'EOF'
import asyncio
from infrastructure.adapters.recovery_corrective_adapter import RecoveryCorrectiveAdapter

async def test_basic_integration():
    try:
        # Crear instancia del adaptador
        adapter = await RecoveryCorrectiveAdapter.create()
        print("✅ Adaptador creado correctamente")
        
        # Probar método simple
        user_data = {"user_id": "test_user", "age": 30, "weight": 75}
        training_history = [{"date": "2025-10-01", "type": "strength", "intensity": "high"}]
        
        result = await adapter.analyze_recovery_needs(user_data, training_history)
        print(f"✅ Método analyze_recovery_needs ejecutado correctamente")
        print(f"Resultado: {result}")
        
        return True
    except Exception as e:
        print(f"❌ Error en la prueba de integración: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_basic_integration())
    exit(0 if success else 1)
EOF

# Ejecutar el script temporal
python $TMP_SCRIPT

# Verificar resultado
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Prueba de integración básica completada correctamente.${NC}"
else
    echo -e "${RED}❌ La prueba de integración básica falló. Revisa los errores anteriores.${NC}"
    exit 1
fi

# Limpiar
rm $TMP_SCRIPT

echo -e "${BLUE}=== Pruebas del adaptador de Recovery Corrective completadas ===${NC}"
echo -e "${GREEN}El adaptador de Recovery Corrective está funcionando correctamente.${NC}"

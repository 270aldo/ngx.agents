#!/bin/bash
# Script para configurar un entorno virtual simple para pruebas

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Configurando entorno de pruebas para NGX Agents...${NC}"

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 no está instalado. Por favor, instálalo primero.${NC}"
    exit 1
fi

# Eliminar entorno virtual existente si existe
if [ -d "venv_test" ]; then
    echo -e "${YELLOW}Eliminando entorno virtual existente...${NC}"
    rm -rf venv_test
fi

# Crear nuevo entorno virtual
echo -e "${YELLOW}Creando nuevo entorno virtual...${NC}"
python3 -m venv venv_test
if [ $? -ne 0 ]; then
    echo -e "${RED}Error al crear el entorno virtual.${NC}"
    exit 1
fi

# Activar entorno virtual
echo -e "${YELLOW}Activando entorno virtual...${NC}"
source venv_test/bin/activate

# Actualizar pip
echo -e "${YELLOW}Actualizando pip...${NC}"
pip install --upgrade pip

# Instalar dependencias mínimas para pruebas
echo -e "${YELLOW}Instalando dependencias mínimas para pruebas...${NC}"
pip install pytest pytest-asyncio python-dotenv pydantic python-json-logger fastapi httpx starlette python-jose passlib bcrypt websockets

# Crear un mock de adk.toolkit
echo -e "${YELLOW}Creando mock de adk.toolkit...${NC}"
mkdir -p venv_test/lib/python*/site-packages/adk
touch venv_test/lib/python*/site-packages/adk/__init__.py
cat > venv_test/lib/python*/site-packages/adk/toolkit.py << 'EOF'
"""Mock de la clase Toolkit para pruebas."""

class Toolkit:
    """Mock de la clase Toolkit."""
    
    def __init__(self, *args, **kwargs):
        """Inicializa el mock."""
        self.args = args
        self.kwargs = kwargs
        self.tools = []
    
    def add_tool(self, tool):
        """Añade una herramienta al toolkit."""
        self.tools.append(tool)
        return self
    
    def run(self, *args, **kwargs):
        """Simula la ejecución del toolkit."""
        return {"result": "mock_result"}
EOF

echo -e "${GREEN}¡Entorno de pruebas configurado correctamente!${NC}"
echo -e "${YELLOW}Para activar el entorno virtual, ejecuta:${NC} source venv_test/bin/activate"
echo -e "${YELLOW}Para ejecutar pruebas unitarias:${NC} pytest -m unit"
echo -e "${YELLOW}Para ejecutar pruebas de agentes:${NC} pytest -m agents"

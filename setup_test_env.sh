#!/bin/bash
# Script para configurar un entorno virtual simple para pruebas con Poetry

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Configurando entorno de pruebas para NGX Agents con Poetry...${NC}"

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 no está instalado. Por favor, instálalo primero.${NC}"
    exit 1
fi

# Verificar si Poetry está instalado
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}Error: Poetry no está instalado. Por favor, instálalo primero:${NC}"
    echo -e "${YELLOW}curl -sSL https://install.python-poetry.org | python3 -${NC}"
    exit 1
fi

# Configurar Poetry para crear el entorno virtual en el directorio del proyecto
echo -e "${YELLOW}Configurando Poetry para crear el entorno virtual en el directorio del proyecto...${NC}"
poetry config virtualenvs.in-project true

# Eliminar entorno virtual existente si existe
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Eliminando entorno virtual existente .venv...${NC}"
    rm -rf .venv
fi

# Crear nuevo entorno virtual e instalar dependencias mínimas para pruebas
echo -e "${YELLOW}Creando nuevo entorno virtual e instalando dependencias para pruebas...${NC}"
poetry install --no-root --with dev,test,core,agents,clients

# Activar entorno virtual
echo -e "${YELLOW}Activando entorno virtual...${NC}"
source .venv/bin/activate

# Configurar Vertex AI en modo mock para pruebas
echo -e "${YELLOW}Configurando Vertex AI en modo mock para pruebas...${NC}"
export MOCK_VERTEX_AI=true

# Crear un mock de adk.toolkit si es necesario
echo -e "${YELLOW}Verificando si se necesita crear mock de adk.toolkit...${NC}"
if ! python -c "import adk.toolkit" &> /dev/null; then
    echo -e "${YELLOW}Creando mock de adk.toolkit...${NC}"
    SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
    mkdir -p "${SITE_PACKAGES}/adk"
    touch "${SITE_PACKAGES}/adk/__init__.py"
    cat > "${SITE_PACKAGES}/adk/toolkit.py" << 'EOF'
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
fi

echo -e "${GREEN}¡Entorno de pruebas configurado correctamente con Poetry!${NC}"
echo -e "${YELLOW}Para activar el entorno virtual, ejecuta:${NC} source .venv/bin/activate"
echo -e "${YELLOW}Para ejecutar pruebas unitarias:${NC} pytest -m unit"
echo -e "${YELLOW}Para ejecutar pruebas de agentes:${NC} pytest -m agents"
echo -e "${YELLOW}Para ejecutar todas las pruebas:${NC} pytest"

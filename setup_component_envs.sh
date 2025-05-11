#!/bin/bash

# Script para configurar entornos virtuales aislados para cada componente
# Este script crea entornos virtuales separados para los componentes principales

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Configurando entornos virtuales aislados para componentes de NGX Agents ===${NC}"

# Verificar si Poetry está instalado
if command -v poetry &>/dev/null; then
    POETRY_VERSION=$(poetry --version)
    echo -e "${GREEN}Poetry detectado: ${POETRY_VERSION}${NC}"
else
    echo -e "${YELLOW}Poetry no está instalado. Instalando Poetry...${NC}"
    curl -sSL https://install.python-poetry.org | python3 -
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error al instalar Poetry. Por favor, instálalo manualmente: https://python-poetry.org/docs/#installation${NC}"
        exit 1
    fi
    echo -e "${GREEN}Poetry instalado correctamente.${NC}"
fi

# Definir componentes principales
COMPONENTS=("agents" "app" "clients" "core" "tools")

# Directorio base para entornos virtuales
VENV_BASE_DIR=".venvs"

# Crear directorio base para entornos virtuales si no existe
mkdir -p $VENV_BASE_DIR

# Función para crear un entorno virtual para un componente
create_component_env() {
    local component=$1
    local venv_dir="${VENV_BASE_DIR}/${component}"
    
    echo -e "${YELLOW}Configurando entorno virtual para el componente: ${component}${NC}"
    
    # Crear archivo pyproject.toml específico para el componente
    cat > "${component}_pyproject.toml" << EOF
[tool.poetry]
name = "ngx-${component}"
version = "0.1.0"
description = "Componente ${component} del sistema NGX Agents"
authors = ["NGX Team"]
packages = [{include = "${component}"}]

[tool.poetry.dependencies]
python = ">=3.9,<3.13"
EOF

    # Añadir dependencias específicas según el componente
    case $component in
        "agents")
            cat >> "${component}_pyproject.toml" << EOF
# Dependencias específicas para agentes
google-adk = "^0.1.0"
google-generativeai = "^0.8.5"
pydantic = ">=2.6.0,<3.0.0"
httpx = "^0.28.1"
EOF
            ;;
        "app")
            cat >> "${component}_pyproject.toml" << EOF
# Dependencias específicas para la aplicación
fastapi = ">=0.110.0,<0.120.0"
uvicorn = {extras = ["standard"], version = ">=0.34.0,<0.35.0"}
pydantic = ">=2.6.0,<3.0.0"
pydantic-settings = ">=2.2.0,<3.0.0"
python-dotenv = ">=1.0.0,<2.0.0"
sse-starlette = ">=1.6.1,<2.0.0"
EOF
            ;;
        "clients")
            cat >> "${component}_pyproject.toml" << EOF
# Dependencias específicas para clientes
httpx = "^0.28.1"
websockets = "^13.0.0"
EOF
            ;;
        "core")
            cat >> "${component}_pyproject.toml" << EOF
# Dependencias específicas para el núcleo
pydantic = ">=2.6.0,<3.0.0"
python-json-logger = ">=2.0.7,<3.0.0"
EOF
            ;;
        "tools")
            cat >> "${component}_pyproject.toml" << EOF
# Dependencias específicas para herramientas
supabase = ">=2.3.0,<3.0.0"
EOF
            ;;
    esac

    # Añadir dependencias de desarrollo comunes
    cat >> "${component}_pyproject.toml" << EOF

[tool.poetry.group.dev.dependencies]
black = "^24.3.0"
isort = "^5.13.2"
mypy = "^1.10.0"
ruff = "^0.4.7"

[tool.poetry.group.test.dependencies]
pytest = ">=8.2.0,<9.0.0"
pytest-asyncio = ">=0.23.0,<0.24.0"
pytest-cov = ">=4.1.0,<5.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
EOF

    # Crear directorio para el componente
    mkdir -p "${VENV_BASE_DIR}/${component}"
    
    # Copiar el archivo pyproject.toml específico al directorio del componente
    cp "${component}_pyproject.toml" "${VENV_BASE_DIR}/${component}/pyproject.toml"
    
    # Crear entorno virtual usando Poetry
    echo -e "${YELLOW}Creando entorno virtual para ${component}...${NC}"
    cd "${VENV_BASE_DIR}/${component}"
    poetry env use python3
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error al crear el entorno virtual para ${component}.${NC}"
        cd - > /dev/null
        return 1
    fi
    
    # Instalar dependencias
    echo -e "${YELLOW}Instalando dependencias para ${component}...${NC}"
    poetry install --no-root
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error al instalar dependencias para ${component}.${NC}"
        cd - > /dev/null
        return 1
    fi
    
    # Volver al directorio original
    cd - > /dev/null
    
    echo -e "${GREEN}Entorno virtual para ${component} configurado correctamente.${NC}"
    return 0
}

# Crear entornos virtuales para cada componente
for component in "${COMPONENTS[@]}"; do
    create_component_env "$component"
done

# Crear archivo de activación para facilitar el cambio entre entornos
cat > activate_component_env.sh << EOF
#!/bin/bash

# Script para activar el entorno virtual de un componente específico

if [ \$# -ne 1 ]; then
    echo "Uso: source activate_component_env.sh <nombre_componente>"
    echo "Componentes disponibles: ${COMPONENTS[*]}"
    return 1
fi

COMPONENT=\$1
VENV_PATH=".venvs/\${COMPONENT}/bin/activate"

if [ -f "\$VENV_PATH" ]; then
    echo "Activando entorno virtual para el componente: \$COMPONENT"
    source "\$VENV_PATH"
    echo "Entorno activado. Para desactivar, ejecuta 'deactivate'"
else
    echo "Error: No se encontró el entorno virtual para el componente \$COMPONENT"
    echo "Componentes disponibles: ${COMPONENTS[*]}"
    return 1
fi
EOF

chmod +x activate_component_env.sh

echo -e "${GREEN}=== Configuración de entornos virtuales aislados completada ===${NC}"
echo -e "${YELLOW}Para activar un entorno virtual de componente, ejecuta:${NC}"
echo -e "${GREEN}source activate_component_env.sh <nombre_componente>${NC}"
echo -e "${YELLOW}Componentes disponibles: ${COMPONENTS[*]}${NC}"
echo -e "${YELLOW}Para usar el entorno principal con todas las dependencias, usa Poetry:${NC}"
echo -e "${GREEN}poetry shell${NC}"

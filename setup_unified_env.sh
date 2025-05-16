#!/bin/bash
# Script unificado para configurar el entorno de desarrollo de NGX Agents
# Este script reemplaza los múltiples scripts de configuración de entorno

set -e

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}Uso: $0 [opciones]${NC}"
    echo -e "Configura el entorno de desarrollo para NGX Agents."
    echo -e ""
    echo -e "Opciones:"
    echo -e "  ${GREEN}-h, --help${NC}       Muestra esta ayuda"
    echo -e "  ${GREEN}-d, --dev${NC}        Configura el entorno de desarrollo (por defecto)"
    echo -e "  ${GREEN}-t, --test${NC}       Configura el entorno de pruebas"
    echo -e "  ${GREEN}-p, --prod${NC}       Configura el entorno de producción"
    echo -e "  ${GREEN}-c, --component${NC}  Configura un componente específico (agents, app, clients, core, tools)"
    echo -e "  ${GREEN}--clean${NC}          Limpia el entorno virtual antes de configurar"
    echo -e ""
    echo -e "Ejemplos:"
    echo -e "  $0                  # Configura el entorno de desarrollo"
    echo -e "  $0 --test           # Configura el entorno de pruebas"
    echo -e "  $0 --component app  # Configura solo el componente app"
    echo -e "  $0 --clean --dev    # Limpia y configura el entorno de desarrollo"
}

# Función para verificar dependencias
check_dependencies() {
    echo -e "${BLUE}Verificando dependencias...${NC}"
    
    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 no está instalado.${NC}"
        exit 1
    fi
    
    # Verificar Poetry
    if ! command -v poetry &> /dev/null; then
        echo -e "${RED}Error: Poetry no está instalado.${NC}"
        echo -e "${YELLOW}Instala Poetry siguiendo las instrucciones en https://python-poetry.org/docs/#installation${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Todas las dependencias están instaladas.${NC}"
}

# Función para limpiar el entorno virtual
clean_env() {
    echo -e "${BLUE}Limpiando entorno virtual...${NC}"
    
    # Eliminar entorno virtual si existe
    if [ -d ".venv" ]; then
        echo -e "${YELLOW}Eliminando entorno virtual existente...${NC}"
        rm -rf .venv
    fi
    
    # Limpiar caché de Poetry
    echo -e "${YELLOW}Limpiando caché de Poetry...${NC}"
    poetry cache clear --all pypi --no-interaction
    
    echo -e "${GREEN}Entorno virtual limpiado correctamente.${NC}"
}

# Función para configurar el entorno
setup_env() {
    local env_type=$1
    local component=$2
    
    echo -e "${BLUE}Configurando entorno $env_type...${NC}"
    
    # Crear entorno virtual con Poetry
    echo -e "${YELLOW}Creando entorno virtual con Poetry...${NC}"
    
    # Configurar Poetry para usar un entorno virtual en el proyecto
    poetry config virtualenvs.in-project true
    
    # Instalar dependencias según el tipo de entorno y componente
    if [ -n "$component" ]; then
        echo -e "${YELLOW}Instalando dependencias para el componente $component...${NC}"
        poetry install --no-root --only $component
    else
        case $env_type in
            dev)
                echo -e "${YELLOW}Instalando dependencias de desarrollo...${NC}"
                poetry install --no-root
                ;;
            test)
                echo -e "${YELLOW}Instalando dependencias de pruebas...${NC}"
                poetry install --no-root --with test
                ;;
            prod)
                echo -e "${YELLOW}Instalando dependencias de producción...${NC}"
                poetry install --no-root --only main
                ;;
            *)
                echo -e "${RED}Tipo de entorno no válido: $env_type${NC}"
                exit 1
                ;;
        esac
    fi
    
    # Copiar archivo .env correspondiente si no existe
    if [ ! -f ".env" ]; then
        case $env_type in
            dev)
                echo -e "${YELLOW}Copiando .env.example a .env...${NC}"
                cp .env.example .env
                ;;
            test)
                echo -e "${YELLOW}Copiando .env.test a .env...${NC}"
                cp .env.test .env
                ;;
            prod)
                echo -e "${YELLOW}Copiando .env.production a .env...${NC}"
                cp .env.production .env
                ;;
        esac
    else
        echo -e "${YELLOW}El archivo .env ya existe, no se sobrescribirá.${NC}"
    fi
    
    echo -e "${GREEN}Entorno $env_type configurado correctamente.${NC}"
}

# Función para activar el entorno virtual
activate_env() {
    echo -e "${BLUE}Activando entorno virtual...${NC}"
    
    # Verificar si el entorno virtual existe
    if [ ! -d ".venv" ]; then
        echo -e "${RED}Error: No se encontró el entorno virtual.${NC}"
        exit 1
    fi
    
    # Mostrar instrucciones para activar el entorno virtual
    echo -e "${YELLOW}Para activar el entorno virtual, ejecuta:${NC}"
    echo -e "${GREEN}source .venv/bin/activate${NC}"
    
    # Intentar activar el entorno virtual automáticamente si es posible
    if [ -z "$VIRTUAL_ENV" ]; then
        echo -e "${YELLOW}Intentando activar el entorno virtual automáticamente...${NC}"
        if [ -f ".venv/bin/activate" ]; then
            source .venv/bin/activate
            echo -e "${GREEN}Entorno virtual activado correctamente.${NC}"
        else
            echo -e "${RED}No se pudo activar el entorno virtual automáticamente.${NC}"
        fi
    else
        echo -e "${GREEN}Ya estás en un entorno virtual: $VIRTUAL_ENV${NC}"
    fi
}

# Valores por defecto
ENV_TYPE="dev"
COMPONENT=""
CLEAN=false

# Procesar argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--dev)
            ENV_TYPE="dev"
            shift
            ;;
        -t|--test)
            ENV_TYPE="test"
            shift
            ;;
        -p|--prod)
            ENV_TYPE="prod"
            shift
            ;;
        -c|--component)
            COMPONENT="$2"
            shift 2
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        *)
            echo -e "${RED}Opción desconocida: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Verificar que el componente sea válido
if [ -n "$COMPONENT" ]; then
    case $COMPONENT in
        agents|app|clients|core|tools)
            # Componente válido
            ;;
        *)
            echo -e "${RED}Componente no válido: $COMPONENT${NC}"
            echo -e "${YELLOW}Los componentes válidos son: agents, app, clients, core, tools${NC}"
            exit 1
            ;;
    esac
fi

# Mostrar configuración
echo -e "${BLUE}Configuración:${NC}"
echo -e "  Tipo de entorno: ${GREEN}$ENV_TYPE${NC}"
if [ -n "$COMPONENT" ]; then
    echo -e "  Componente: ${GREEN}$COMPONENT${NC}"
fi
echo -e "  Limpiar entorno: ${GREEN}$CLEAN${NC}"
echo ""

# Verificar dependencias
check_dependencies

# Limpiar entorno si se solicitó
if [ "$CLEAN" = true ]; then
    clean_env
fi

# Configurar entorno
setup_env "$ENV_TYPE" "$COMPONENT"

# Activar entorno virtual
activate_env

echo -e "${BLUE}Proceso completado.${NC}"
echo -e "${GREEN}El entorno de $ENV_TYPE está listo para usar.${NC}"

if [ "$ENV_TYPE" = "dev" ]; then
    echo -e "${YELLOW}Para iniciar el servidor de desarrollo, ejecuta:${NC}"
    echo -e "${GREEN}python -m app.main${NC}"
elif [ "$ENV_TYPE" = "test" ]; then
    echo -e "${YELLOW}Para ejecutar las pruebas, ejecuta:${NC}"
    echo -e "${GREEN}pytest${NC}"
fi

exit 0

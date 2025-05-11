#!/bin/bash

# Script para ejecutar las pruebas del sistema NGX Agents
# Este script ejecuta las pruebas de integración, rendimiento y sistema

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar si el entorno virtual está activado
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}Entorno virtual no detectado. Intentando activar...${NC}"
    if [ -d "venv" ]; then
        source venv/bin/activate
        if [[ "$VIRTUAL_ENV" == "" ]]; then
            echo -e "${RED}Error al activar el entorno virtual. Por favor, actívalo manualmente:${NC}"
            echo -e "${GREEN}source venv/bin/activate${NC}"
            exit 1
        else
            echo -e "${GREEN}Entorno virtual activado.${NC}"
        fi
    else
        echo -e "${RED}No se encontró el directorio del entorno virtual (venv).${NC}"
        echo -e "${YELLOW}Por favor, ejecuta primero setup_dev_env.sh para configurar el entorno.${NC}"
        exit 1
    fi
fi

# Función para ejecutar pruebas y mostrar resultados
run_test() {
    TEST_TYPE=$1
    TEST_PATH=$2
    EXTRA_ARGS=$3
    
    echo -e "${YELLOW}Ejecutando pruebas de $TEST_TYPE...${NC}"
    
    if [ "$EXTRA_ARGS" != "" ]; then
        python -m pytest $TEST_PATH $EXTRA_ARGS
    else
        python -m pytest $TEST_PATH
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Pruebas de $TEST_TYPE completadas con éxito.${NC}"
        return 0
    else
        echo -e "${RED}Algunas pruebas de $TEST_TYPE fallaron.${NC}"
        return 1
    fi
}

# Menú principal
show_menu() {
    echo -e "${GREEN}=== Sistema de pruebas NGX Agents ===${NC}"
    echo -e "${YELLOW}Selecciona una opción:${NC}"
    echo "1) Ejecutar todas las pruebas"
    echo "2) Ejecutar pruebas de integración de adaptadores"
    echo "3) Ejecutar pruebas de sistema completo"
    echo "4) Ejecutar pruebas de rendimiento"
    echo "5) Ejecutar pruebas con cobertura"
    echo "6) Salir"
    echo -n "Opción: "
    read OPTION
    
    case $OPTION in
        1)
            echo -e "${GREEN}Ejecutando todas las pruebas...${NC}"
            run_test "adaptadores" "tests/test_*_adapter.py" "-v"
            run_test "sistema" "tests/test_system_integration.py" "-v"
            run_test "rendimiento" "tests/test_performance.py" "-v"
            echo -e "${GREEN}Todas las pruebas completadas.${NC}"
            ;;
        2)
            run_test "adaptadores" "tests/test_*_adapter.py" "-v"
            ;;
        3)
            run_test "sistema" "tests/test_system_integration.py" "-v"
            ;;
        4)
            run_test "rendimiento" "tests/test_performance.py" "-v"
            ;;
        5)
            echo -e "${YELLOW}Ejecutando pruebas con cobertura...${NC}"
            python -m pytest --cov=. --cov-report=html
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Pruebas con cobertura completadas. Informe generado en htmlcov/index.html${NC}"
                # Abrir informe de cobertura si es posible
                if command -v open &>/dev/null; then
                    open htmlcov/index.html
                elif command -v xdg-open &>/dev/null; then
                    xdg-open htmlcov/index.html
                else
                    echo -e "${YELLOW}Puedes abrir el informe de cobertura en htmlcov/index.html${NC}"
                fi
            else
                echo -e "${RED}Algunas pruebas fallaron durante la generación del informe de cobertura.${NC}"
            fi
            ;;
        6)
            echo -e "${GREEN}Saliendo...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Opción inválida.${NC}"
            ;;
    esac
    
    echo ""
    echo -e "${YELLOW}Presiona Enter para continuar...${NC}"
    read
    show_menu
}

# Verificar dependencias
echo -e "${YELLOW}Verificando dependencias...${NC}"
python -c "import pytest; import pytest_asyncio; import pytest_cov" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Faltan algunas dependencias para las pruebas.${NC}"
    echo -e "${YELLOW}Instalando dependencias...${NC}"
    pip install pytest pytest-asyncio pytest-cov
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error al instalar las dependencias. Por favor, instálalas manualmente:${NC}"
        echo -e "${GREEN}pip install pytest pytest-asyncio pytest-cov${NC}"
        exit 1
    fi
fi

# Verificar si se pasó un argumento para ejecutar directamente
if [ "$1" != "" ]; then
    case $1 in
        "all")
            echo -e "${GREEN}Ejecutando todas las pruebas...${NC}"
            run_test "adaptadores" "tests/test_*_adapter.py" "-v"
            run_test "sistema" "tests/test_system_integration.py" "-v"
            run_test "rendimiento" "tests/test_performance.py" "-v"
            echo -e "${GREEN}Todas las pruebas completadas.${NC}"
            exit 0
            ;;
        "adapters")
            run_test "adaptadores" "tests/test_*_adapter.py" "-v"
            exit 0
            ;;
        "system")
            run_test "sistema" "tests/test_system_integration.py" "-v"
            exit 0
            ;;
        "performance")
            run_test "rendimiento" "tests/test_performance.py" "-v"
            exit 0
            ;;
        "coverage")
            echo -e "${YELLOW}Ejecutando pruebas con cobertura...${NC}"
            python -m pytest --cov=. --cov-report=html
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Pruebas con cobertura completadas. Informe generado en htmlcov/index.html${NC}"
            else
                echo -e "${RED}Algunas pruebas fallaron durante la generación del informe de cobertura.${NC}"
            fi
            exit 0
            ;;
        *)
            echo -e "${RED}Argumento inválido: $1${NC}"
            echo -e "${YELLOW}Argumentos válidos: all, adapters, system, performance, coverage${NC}"
            exit 1
            ;;
    esac
fi

# Mostrar menú interactivo
show_menu
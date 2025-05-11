#!/bin/bash

# Script para activar el entorno virtual de un componente específico

if [ $# -ne 1 ]; then
    echo "Uso: source activate_component_env.sh <nombre_componente>"
    echo "Componentes disponibles: agents app clients core tools"
    return 1
fi

COMPONENT=$1
VENV_PATH=".venvs/${COMPONENT}/bin/activate"

if [ -f "$VENV_PATH" ]; then
    echo "Activando entorno virtual para el componente: $COMPONENT"
    source "$VENV_PATH"
    echo "Entorno activado. Para desactivar, ejecuta 'deactivate'"
else
    echo "Error: No se encontró el entorno virtual para el componente $COMPONENT"
    echo "Componentes disponibles: agents app clients core tools"
    return 1
fi

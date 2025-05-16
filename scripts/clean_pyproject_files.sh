#!/bin/bash
# Script para limpiar los archivos *_pyproject.toml y consolidar las dependencias en el pyproject.toml principal

set -e

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Iniciando limpieza de archivos pyproject.toml secundarios...${NC}"

# Verificar que estamos en el directorio raíz del proyecto
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Este script debe ejecutarse desde el directorio raíz del proyecto.${NC}"
    exit 1
fi

# Crear directorio de respaldo
BACKUP_DIR="backup_pyproject_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo -e "${YELLOW}Creando directorio de respaldo: $BACKUP_DIR${NC}"

# Función para extraer dependencias de un archivo pyproject.toml
extract_dependencies() {
    local file=$1
    local component=$(basename "$file" | sed 's/_pyproject.toml//')
    
    echo -e "${YELLOW}Extrayendo dependencias de $file para el componente $component...${NC}"
    
    # Copiar archivo a respaldo
    cp "$file" "$BACKUP_DIR/"
    
    # Extraer dependencias
    local deps=$(grep -A 100 "\[tool.poetry.dependencies\]" "$file" | grep -B 100 -m 1 "^\[" | grep -v "^\[" | grep "=" | sed 's/^/# From '"$component"': /')
    local dev_deps=$(grep -A 100 "\[tool.poetry.group.dev.dependencies\]" "$file" 2>/dev/null | grep -B 100 -m 1 "^\[" | grep -v "^\[" | grep "=" | sed 's/^/# From '"$component"': /')
    
    echo "$deps"
    echo "$dev_deps"
}

# Archivos a procesar
FILES=("agents_pyproject.toml" "app_pyproject.toml" "clients_pyproject.toml" "core_pyproject.toml" "tools_pyproject.toml")

# Crear archivo temporal para las dependencias extraídas
TEMP_DEPS=$(mktemp)
TEMP_DEV_DEPS=$(mktemp)

echo "# Dependencias extraídas de los archivos *_pyproject.toml" > "$TEMP_DEPS"
echo "# Dependencias de desarrollo extraídas de los archivos *_pyproject.toml" > "$TEMP_DEV_DEPS"

# Procesar cada archivo
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        # Extraer dependencias y añadirlas a los archivos temporales
        extract_dependencies "$file" >> "$TEMP_DEPS"
        
        echo -e "${GREEN}Archivo $file procesado y respaldado.${NC}"
    else
        echo -e "${YELLOW}Archivo $file no encontrado, omitiendo...${NC}"
    fi
done

# Crear archivo de consolidación
CONSOLIDATED_FILE="$BACKUP_DIR/consolidated_dependencies.txt"
cat "$TEMP_DEPS" > "$CONSOLIDATED_FILE"
echo -e "\n\n# Dependencias de desarrollo\n" >> "$CONSOLIDATED_FILE"
cat "$TEMP_DEV_DEPS" >> "$CONSOLIDATED_FILE"

echo -e "${GREEN}Dependencias consolidadas en $CONSOLIDATED_FILE${NC}"

# Limpiar archivos temporales
rm "$TEMP_DEPS" "$TEMP_DEV_DEPS"

# Actualizar pyproject.toml principal
echo -e "${YELLOW}Actualizando pyproject.toml principal...${NC}"

# Hacer una copia de seguridad del pyproject.toml principal
cp pyproject.toml "$BACKUP_DIR/pyproject.toml.bak"

# Añadir grupos para cada componente
for component in "agents" "app" "clients" "core" "tools"; do
    if ! grep -q "\[tool.poetry.group.$component\]" pyproject.toml; then
        echo -e "${YELLOW}Añadiendo grupo $component a pyproject.toml...${NC}"
        echo -e "\n[tool.poetry.group.$component]\noptional = true\n\n[tool.poetry.group.$component.dependencies]" >> pyproject.toml
    fi
done

echo -e "${GREEN}pyproject.toml actualizado con grupos para cada componente.${NC}"
echo -e "${YELLOW}Revisa el archivo $CONSOLIDATED_FILE para ver las dependencias extraídas.${NC}"
echo -e "${YELLOW}Ahora debes añadir manualmente las dependencias específicas a cada grupo en pyproject.toml.${NC}"

# Eliminar los archivos *_pyproject.toml si se confirma
read -p "¿Deseas eliminar los archivos *_pyproject.toml originales? (s/n): " confirm
if [[ $confirm == [sS] ]]; then
    for file in "${FILES[@]}"; do
        if [ -f "$file" ]; then
            rm "$file"
            echo -e "${GREEN}Archivo $file eliminado.${NC}"
        fi
    done
    echo -e "${GREEN}Archivos *_pyproject.toml eliminados correctamente.${NC}"
else
    echo -e "${YELLOW}Los archivos *_pyproject.toml no han sido eliminados.${NC}"
fi

echo -e "${GREEN}Proceso completado. Recuerda actualizar el archivo pyproject.toml con las dependencias específicas.${NC}"

#!/bin/bash
# Script para limpiar archivos redundantes en el proyecto NGX Agents

set -e  # Salir si hay errores

echo "Iniciando limpieza del proyecto NGX Agents..."

# 1. Consolidar archivos de documentación redundantes
echo "Consolidando documentación..."

# Crear directorio para archivos obsoletos (por si acaso)
mkdir -p .obsolete/docs

# Mover archivos de progreso redundantes a un solo archivo
cat docs/progress_*.md > .obsolete/docs/all_progress.md

# Eliminar archivos de progreso individuales excepto el principal
find docs -name "progress_*.md" ! -name "progress_summary.md" -exec rm {} \;

# Consolidar planes de migración
cat docs/*_migration_plan.md > .obsolete/docs/all_migration_plans.md
find docs -name "*_migration_plan.md" -exec rm {} \;

# 2. Limpiar clientes Vertex AI redundantes
echo "Limpiando clientes Vertex AI redundantes..."

# Mover cliente antiguo a obsoletos
mv clients/vertex_client.py .obsolete/

# Renombrar cliente optimizado a cliente principal
mv clients/vertex_ai_client.py .obsolete/
mv clients/vertex_ai_client_optimized.py clients/vertex_ai_client.py

# Mover ejemplo de telemetría a carpeta de ejemplos
mkdir -p examples/clients
mv clients/vertex_ai_client_telemetry_example.py examples/clients/

# 3. Limpiar adaptadores redundantes
echo "Limpiando adaptadores redundantes..."

# Consolidar adaptadores en una carpeta
mkdir -p infrastructure/adapters
find infrastructure -name "*_adapter.py" -exec mv {} infrastructure/adapters/ \;
find core -name "*_adapter.py" -exec mv {} infrastructure/adapters/ \;

# 4. Limpiar archivos de prueba redundantes
echo "Limpiando pruebas redundantes..."

# Consolidar pruebas de adaptadores
mkdir -p tests/adapters
find tests -name "test_*_adapter.py" -exec mv {} tests/adapters/ \;

# 5. Actualizar importaciones
echo "Actualizando importaciones..."

# Crear script temporal para actualizar importaciones
cat > update_imports_temp.py << 'EOF'
import os
import re

def update_imports_in_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Actualizar importaciones de vertex_ai_client_optimized a vertex_ai_client
    content = re.sub(
        r'from clients.vertex_ai_client_optimized import', 
        'from clients.vertex_ai_client import', 
        content
    )
    
    # Actualizar importaciones de adaptadores movidos
    content = re.sub(
        r'from (infrastructure|core)\.(\w+)_adapter import', 
        r'from infrastructure.adapters.\2_adapter import', 
        content
    )
    
    with open(file_path, 'w') as file:
        file.write(content)

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                update_imports_in_file(file_path)

# Procesar directorios principales
process_directory('agents')
process_directory('app')
process_directory('clients')
process_directory('core')
process_directory('infrastructure')
process_directory('tests')
process_directory('tools')
EOF

python update_imports_temp.py
rm update_imports_temp.py

echo "Limpieza completada. Los archivos eliminados se han respaldado en .obsolete/"
echo "Revisa que todo funcione correctamente antes de eliminar la carpeta .obsolete/"

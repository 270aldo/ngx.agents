#!/bin/bash

# Script para ejecutar pruebas del cliente Vertex AI optimizado
# Este script ejecuta las pruebas del cliente Vertex AI optimizado y muestra los resultados

echo "Ejecutando pruebas del cliente Vertex AI optimizado..."
echo "======================================================"

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Ejecutar pruebas con pytest
python -m pytest tests/test_vertex_ai_client_optimized.py -v

# Verificar resultado
if [ $? -eq 0 ]; then
    echo "======================================================"
    echo "✅ Todas las pruebas pasaron correctamente"
    echo ""
    echo "El cliente Vertex AI optimizado está listo para ser integrado"
    echo "en el sistema. Para integrarlo, sigue estos pasos:"
    echo ""
    echo "1. Actualiza las importaciones en los archivos que usan el cliente:"
    echo "   from clients.vertex_ai import vertex_ai_client"
    echo "   a"
    echo "   from clients.vertex_ai_client_optimized import vertex_ai_client_optimized as vertex_ai_client"
    echo ""
    echo "2. Ejecuta pruebas de integración para verificar la compatibilidad"
    echo "3. Cuando todo funcione correctamente, reemplaza el archivo original"
    echo "   clients/vertex_ai_client.py con el optimizado"
    echo ""
else
    echo "======================================================"
    echo "❌ Algunas pruebas fallaron"
    echo ""
    echo "Revisa los errores y corrige los problemas antes de integrar"
    echo "el cliente optimizado en el sistema."
    echo ""
fi
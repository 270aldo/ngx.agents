#!/bin/bash
# Script para ejecutar pruebas del adaptador de Vertex AI

set -e  # Salir inmediatamente si algún comando falla

echo "Ejecutando pruebas del adaptador de Vertex AI..."

# Configurar entorno de pruebas
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT_DIR=$( cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd )
source "$PROJECT_ROOT_DIR/setup_test_env.sh"

# Ejecutar pruebas específicas del adaptador
python -m pytest scripts/test_vertex_ai_adapter.py -v

# Si se desea, también se pueden ejecutar pruebas de integración
# para verificar que el adaptador funciona con componentes reales
if [ "$1" == "--with-integration" ]; then
    echo "Ejecutando pruebas de integración con el adaptador..."
    
    # Crear archivo temporal de configuración para pruebas de integración
    cat > tests/integration/test_vertex_adapter_integration.py << EOF
"""
Pruebas de integración para el adaptador de Vertex AI.

Este módulo contiene pruebas que verifican la integración del adaptador
con componentes reales del sistema.
"""

import pytest
import asyncio
from clients.vertex_ai.client import VertexAIClient
vertex_ai_client = VertexAIClient()

@pytest.mark.asyncio
async def test_adapter_with_intent_analyzer():
    """Prueba la integración del adaptador con el analizador de intenciones."""
    from core.intent_analyzer import IntentAnalyzer
    
    # Inicializar cliente

    
    try:
        # Crear analizador de intenciones con el adaptador
        analyzer = IntentAnalyzer()
        
        # Ejecutar análisis simple
        result = await analyzer.analyze("¿Cuál es el mejor ejercicio para fortalecer piernas?")
        
        # Verificar que se obtuvo un resultado válido
        assert result is not None
        assert "intent" in result
        assert "confidence" in result
        assert result["confidence"] > 0.5
    finally:
        # Limpiar
        await vertex_ai_client.close()

@pytest.mark.asyncio
async def test_adapter_direct_usage():
    """Prueba el uso directo del adaptador."""
    # Inicializar cliente

    
    try:
        # Generar contenido simple
        response = await vertex_ai_client.generate_content(
            prompt="Escribe un breve párrafo sobre la importancia del ejercicio",
            temperature=0.7
        )
        
        # Verificar respuesta
        assert response is not None
        assert "text" in response
        assert len(response["text"]) > 0
        
        # Verificar estadísticas
        stats = await vertex_ai_client.get_stats()
        assert stats["content_requests"] >= 1
    finally:
        # Limpiar
        await vertex_ai_client.close()
EOF
    
    # Ejecutar pruebas de integración
    python -m pytest tests/integration/test_vertex_adapter_integration.py -v
    
    # Limpiar
    rm tests/integration/test_vertex_adapter_integration.py
fi

echo "Pruebas completadas exitosamente."

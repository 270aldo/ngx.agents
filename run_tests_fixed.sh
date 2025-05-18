#!/bin/bash
# Script para ejecutar pruebas con configuración adecuada

# Cargar variables de entorno para pruebas
export MOCK_MODE=True
export MOCK_VERTEX_AI=True
export MOCK_A2A=True
export ENV=test
export LOG_LEVEL=INFO

# Ejecutar pruebas
python -m pytest tests/integration/test_full_system_integration.py -v

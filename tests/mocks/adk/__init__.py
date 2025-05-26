"""
Mock del módulo adk para pruebas unitarias.

Este módulo proporciona implementaciones simuladas del Google Agent Development Kit (ADK)
para facilitar las pruebas unitarias sin dependencias externas. Permite
simular las interacciones con el ADK sin necesidad de conectarse a servicios externos.

Características principales:
- Simulación de Toolkit: Implementa una versión simulada del Toolkit de ADK.
- Simulación de Respuestas: Proporciona respuestas predefinidas para las llamadas a la API.
- Registro de Llamadas: Registra las llamadas realizadas para verificación en pruebas.

Clases:
    MockToolkit: Simulación del Toolkit de ADK.
"""

# Importar el módulo toolkit para que los mocks sean compatibles
from .toolkit import Toolkit

__all__ = ["Toolkit"]

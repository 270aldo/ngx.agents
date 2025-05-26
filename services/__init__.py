"""
Módulo de servicios para el sistema NGX.

Contiene servicios centralizados que pueden ser utilizados por múltiples agentes
y componentes del sistema.
"""

from services.program_classification_service import ProgramClassificationService

__all__ = ["ProgramClassificationService"]

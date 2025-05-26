"""
Módulo compartido para agentes NGX.

Contiene definiciones, utilidades y funcionalidades comunes que pueden ser
utilizadas por múltiples agentes en el sistema.
"""

from agents.shared.program_definitions import (
    get_program_definition,
    get_program_keywords,
    get_age_range,
    get_all_program_types,
    get_program_by_age,
    is_keyword_match,
    PROGRAM_DEFINITIONS,
)

__all__ = [
    "get_program_definition",
    "get_program_keywords",
    "get_age_range",
    "get_all_program_types",
    "get_program_by_age",
    "is_keyword_match",
    "PROGRAM_DEFINITIONS",
]

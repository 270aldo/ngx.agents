"""
Mock del módulo google.generativeai para pruebas.
"""

from unittest.mock import MagicMock

# Configuración básica
configure = MagicMock()


class GenerationConfig:
    """Mock de GenerationConfig."""

    def __init__(self, **kwargs):
        """Inicializa el mock con los parámetros proporcionados."""
        self.__dict__.update(kwargs)


class Content:
    """Mock de Content."""

    def __init__(self, text):
        """Inicializa el mock con el texto proporcionado."""
        self.text = text
        self.parts = [{"text": text}]

    def __str__(self):
        return self.text


class Candidate:
    """Mock de Candidate."""

    def __init__(self, text):
        """Inicializa el mock con el texto proporcionado."""
        self.text = text
        self.content = Content(text)

    def __str__(self):
        return self.text


class GenerationResponse:
    """Mock de GenerationResponse."""

    def __init__(self, text):
        """Inicializa el mock con el texto proporcionado."""
        self.text = text
        self.candidates = [Candidate(text)]
        self.result = Candidate(text)

    def __str__(self):
        return self.text


class GenerativeModel:
    """Mock de GenerativeModel."""

    def __init__(self, model_name):
        """Inicializa el mock con el nombre del modelo proporcionado."""
        self.model_name = model_name
        self.generation_config = GenerationConfig()

    def generate_content(self, *args, **kwargs):
        """Simula la generación de contenido."""
        return GenerationResponse("Respuesta simulada de Gemini.")


# Exportar las clases y funciones
__all__ = [
    "configure",
    "GenerationConfig",
    "GenerativeModel",
    "GenerationResponse",
    "Candidate",
    "Content",
]

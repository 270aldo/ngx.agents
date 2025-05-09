"""
Paquete ADK local simulado para pruebas.
"""

class Agent:
    """Stub de Google ADK Agent para pruebas locales."""
    def __init__(self, toolkit=None, **kwargs):
        self.toolkit = toolkit
        # Atributos adicionales pueden inicializarse si es necesario

    async def run(self, *args, **kwargs):
        """Stub del método run."""
        return {}

class Skill:
    """Stub de la clase Skill de Google ADK."""
    def __init__(self, name: str, description: str, input_schema=None, output_schema=None, handler=None):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.handler = handler

    async def __call__(self, *args, **kwargs):
        if self.handler:
            return await self.handler(*args, **kwargs)
        raise NotImplementedError("Skill handler no implementado")

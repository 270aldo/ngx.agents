"""
Adaptador para Google ADK Toolkit.

Este módulo proporciona una implementación que utiliza la biblioteca oficial
de Google ADK en lugar de stubs locales.
"""

try:
    # Intentar importar la biblioteca oficial de Google ADK
    from google.adk.toolkit import Toolkit as GoogleADKToolkit

    class Toolkit(GoogleADKToolkit):
        """
        Implementación de Toolkit que utiliza la biblioteca oficial de Google ADK.

        Esta clase hereda directamente de google.adk.toolkit.Toolkit y proporciona
        compatibilidad con el sistema NGX Agents.
        """

        def __init__(self, **kwargs):
            """
            Inicializa un toolkit ADK.

            Args:
                **kwargs: Argumentos adicionales para pasar a la clase base
            """
            super().__init__(**kwargs)

except ImportError:
    # Fallback a stubs locales si la biblioteca oficial no está disponible
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(
        "No se pudo importar la biblioteca oficial de Google ADK. Usando stubs locales."
    )

    class Toolkit:
        """Stub del ADK Toolkit para permitir la importación local."""

        def __init__(self, **kwargs):
            self.tools = []
            self.skills = {}

        def add_tool(self, tool):
            """
            Añade una herramienta al toolkit.

            Args:
                tool: Herramienta a añadir
            """
            if tool not in self.tools:
                self.tools.append(tool)

        def register_skill(self, skill):
            """
            Registra una skill en el toolkit.

            Args:
                skill: Skill a registrar
            """
            if hasattr(skill, "name"):
                self.skills[skill.name] = skill
            else:
                logger.warning("Intento de registrar una skill sin nombre")

        async def execute_skill(self, skill_name, **kwargs):
            """
            Ejecuta una skill registrada.

            Args:
                skill_name: Nombre de la skill a ejecutar
                **kwargs: Argumentos para la skill

            Returns:
                Resultado de la ejecución de la skill
            """
            if skill_name in self.skills:
                skill = self.skills[skill_name]
                return await skill(**kwargs)
            else:
                raise ValueError(f"Skill '{skill_name}' no encontrada en el toolkit")

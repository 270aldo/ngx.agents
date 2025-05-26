"""
Mock de la clase Toolkit del ADK para pruebas unitarias.

Este módulo proporciona una implementación simulada de la clase Toolkit
del Google Agent Development Kit (ADK) para facilitar las pruebas unitarias
sin dependencias externas.
"""


# Mantener el nombre original para compatibilidad
class Toolkit:
    """Mock de la clase Toolkit del ADK.

    Esta clase simula el comportamiento del Toolkit del ADK, permitiendo
    añadir herramientas y ejecutar operaciones sin necesidad de conectarse
    a servicios externos.

    Atributos:
        tools (list): Lista de herramientas añadidas al toolkit.
        call_history (list): Historial de llamadas realizadas al toolkit.
        default_response (dict): Respuesta predeterminada para el método run.
    """

    def __init__(self, *args, **kwargs):
        """Inicializa el mock del Toolkit.

        Args:
            *args: Argumentos posicionales que se pasan al constructor real.
            **kwargs: Argumentos con nombre que se pasan al constructor real.
        """
        self.args = args
        self.kwargs = kwargs
        self.tools = []
        self.call_history = []
        self.default_response = {"result": "mock_result"}

    def add_tool(self, tool):
        """Añade una herramienta al toolkit.

        Args:
            tool: Herramienta a añadir al toolkit.

        Returns:
            self: Retorna la instancia actual para encadenar métodos.
        """
        self.tools.append(tool)
        return self

    def run(self, *args, **kwargs):
        """Simula la ejecución del toolkit.

        Args:
            *args: Argumentos posicionales para la ejecución.
            **kwargs: Argumentos con nombre para la ejecución.

        Returns:
            dict: Resultado simulado de la ejecución.
        """
        # Registrar la llamada en el historial
        call_info = {"args": args, "kwargs": kwargs}
        self.call_history.append(call_info)

        # Si se ha configurado una respuesta personalizada para esta llamada, usarla
        if hasattr(self, "custom_responses") and self.call_history.index(
            call_info
        ) < len(self.custom_responses):
            return self.custom_responses[self.call_history.index(call_info)]

        # De lo contrario, devolver la respuesta predeterminada
        return self.default_response

    def set_default_response(self, response):
        """Establece la respuesta predeterminada para el método run.

        Args:
            response (dict): Respuesta predeterminada a devolver.

        Returns:
            self: Retorna la instancia actual para encadenar métodos.
        """
        self.default_response = response
        return self

    def set_custom_responses(self, responses):
        """Establece respuestas personalizadas para llamadas específicas al método run.

        Args:
            responses (list): Lista de respuestas a devolver en orden para cada llamada.

        Returns:
            self: Retorna la instancia actual para encadenar métodos.
        """
        self.custom_responses = responses
        return self

    def clear_history(self):
        """Limpia el historial de llamadas.

        Returns:
            self: Retorna la instancia actual para encadenar métodos.
        """
        self.call_history = []
        return self

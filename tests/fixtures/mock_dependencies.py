"""
Fixtures para mockear dependencias externas en pruebas unitarias.

Este módulo proporciona mocks elegantes para dependencias como:
- google.generativeai
- adk.toolkit
- Clientes externos

Utiliza monkeypatch para evitar modificar site-packages directamente.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_adk_toolkit(monkeypatch):
    """
    Mockea el módulo adk.toolkit y la clase Toolkit.

    Esto permite ejecutar pruebas sin tener instalado google-adk.
    """
    # Crear un módulo mock para adk
    adk_mock = types.ModuleType("adk")
    toolkit_mock = types.ModuleType("adk.toolkit")

    # Crear una clase Toolkit mock
    class MockToolkit:
        """Mock de la clase Toolkit."""

        def __init__(self, *args, **kwargs):
            """Inicializa el mock."""
            self.args = args
            self.kwargs = kwargs
            self.tools = []

        def add_tool(self, tool):
            """Añade una herramienta al toolkit."""
            self.tools.append(tool)
            return self

        def run(self, *args, **kwargs):
            """Simula la ejecución del toolkit."""
            return {"result": "mock_result"}

    # Asignar la clase mock al módulo
    toolkit_mock.Toolkit = MockToolkit

    # Registrar los módulos mock en sys.modules
    monkeypatch.setitem(sys.modules, "adk", adk_mock)
    monkeypatch.setitem(sys.modules, "adk.toolkit", toolkit_mock)

    return MockToolkit


@pytest.fixture
def mock_gemini_client(monkeypatch):
    """
    Mockea el módulo google.generativeai y proporciona un cliente Gemini mock.
    """
    # Crear un módulo mock para google.generativeai
    genai_mock = types.ModuleType("google.generativeai")

    # Configurar comportamientos básicos
    genai_mock.configure = MagicMock()

    class MockGenerationConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class MockGenerativeModel:
        def __init__(self, model_name):
            self.model_name = model_name
            self.generation_config = MockGenerationConfig()

        def generate_content(self, *args, **kwargs):
            """Simula la generación de contenido."""
            return MockGenerationResponse("Respuesta simulada de Gemini.")

    class MockGenerationResponse:
        def __init__(self, text):
            self.text = text
            self.candidates = [MockCandidate(text)]
            self.result = MockCandidate(text)

        def __str__(self):
            return self.text

    class MockCandidate:
        def __init__(self, text):
            self.text = text
            self.content = MockContent(text)

        def __str__(self):
            return self.text

    class MockContent:
        def __init__(self, text):
            self.text = text
            self.parts = [{"text": text}]

        def __str__(self):
            return self.text

    # Asignar las clases mock al módulo
    genai_mock.GenerativeModel = MockGenerativeModel
    genai_mock.GenerationConfig = MockGenerationConfig

    # Registrar el módulo mock en sys.modules
    monkeypatch.setitem(sys.modules, "google", types.ModuleType("google"))
    monkeypatch.setitem(sys.modules, "google.generativeai", genai_mock)

    return genai_mock


@pytest.fixture
def mock_supabase_client():
    """
    Proporciona un cliente Supabase mock para pruebas.

    Este mock ya está implementado en conftest.py, pero lo incluimos aquí
    para tener todos los mocks en un solo lugar.
    """

    class MockSupabaseClient:
        def __init__(self):
            self._initialized = True
            self.client = None
            self.calls = {}
            self.data = {"conversation_states": {}}

        async def initialize(self):
            pass

        def _record_call(self, method_name):
            if method_name not in self.calls:
                self.calls[method_name] = 0
            self.calls[method_name] += 1

        async def query(self, table_name, **kwargs):
            self._record_call("query")
            if table_name == "conversation_states":
                filters = kwargs.get("filters", {})
                if "session_id" in filters:
                    session_id = filters["session_id"]
                    if session_id in self.data["conversation_states"]:
                        return [self.data["conversation_states"][session_id]]
            return []

        async def insert(self, table_name, data, **kwargs):
            self._record_call("insert")
            if table_name == "conversation_states":
                session_id = data["session_id"]
                self.data["conversation_states"][session_id] = data
                return [data]
            return []

        async def update(self, table_name, data, filters, **kwargs):
            self._record_call("update")
            if table_name == "conversation_states":
                session_id = filters["session_id"]
                if session_id in self.data["conversation_states"]:
                    self.data["conversation_states"][session_id].update(data)
                    return [self.data["conversation_states"][session_id]]
            return []

        async def delete(self, table_name, filters, **kwargs):
            self._record_call("delete")
            if table_name == "conversation_states":
                session_id = filters["session_id"]
                if session_id in self.data["conversation_states"]:
                    deleted = self.data["conversation_states"].pop(session_id)
                    return [deleted]
            return []

    return MockSupabaseClient()

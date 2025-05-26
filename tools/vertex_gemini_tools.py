"""
Habilidades basadas en Vertex AI Gemini.

Este módulo implementa skills que utilizan los modelos de Gemini a través de Vertex AI
para generar texto, responder preguntas y analizar contenido.
"""

from typing import Any, Dict, List, Optional
import logging

from pydantic import BaseModel, Field

from clients.gemini_client import GeminiClient
from core.skill import Skill, skill_registry

logger = logging.getLogger(__name__)


# --- Inicio: Mock Temporal de get_available_models ---
def get_available_models() -> Dict[str, Dict[str, Any]]:
    """Mock temporal para desbloquear la importación."""
    logger.warning(
        "Usando mock temporal para get_available_models en vertex_gemini_tools.py"
    )
    return {
        "gemini-1.5-pro": {"description": "Mocked Pro", "capabilities": []},
        "gemini-1.5-flash": {"description": "Mocked Flash", "capabilities": []},
    }


# --- Fin: Mock Temporal ---

# Obtener modelos disponibles
AVAILABLE_MODELS = list(get_available_models().keys())
DEFAULT_MODEL = "gemini-1.5-flash"  # Modelo por defecto


class VertexGeminiGenerateInput(BaseModel):
    """Esquema de entrada para la skill de generación con Vertex AI Gemini."""

    prompt: str = Field(..., description="Texto de entrada para generar la respuesta")
    model: str = Field(
        DEFAULT_MODEL,
        description=f"Modelo a utilizar (disponibles: {', '.join(AVAILABLE_MODELS)})",
    )
    temperature: float = Field(0.7, description="Control de aleatoriedad (0.0-1.0)")


class VertexGeminiGenerateOutput(BaseModel):
    """Esquema de salida para la skill de generación con Vertex AI Gemini."""

    text: str = Field(..., description="Texto generado")
    model: str = Field(..., description="Modelo utilizado")
    execution_time: float = Field(..., description="Tiempo de ejecución en segundos")


class VertexGeminiGenerateSkill(Skill):
    """
    Skill para generar texto utilizando Vertex AI Gemini.

    Permite enviar prompts a Gemini a través de Vertex AI y obtener respuestas generadas.
    """

    def __init__(self):
        """Inicializa la skill de generación con Vertex AI Gemini."""
        super().__init__(
            name="vertex_gemini_generate",
            description="Genera texto utilizando los modelos Gemini a través de Vertex AI",
            version="1.0.0",
            input_schema=VertexGeminiGenerateInput,
            output_schema=VertexGeminiGenerateOutput,
            categories=["nlp", "generation", "ai", "vertex"],
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la generación de texto con Vertex AI Gemini.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Texto generado y metadatos
        """
        import time

        # Extraer parámetros
        prompt = input_data["prompt"]
        model_name = input_data.get("model", DEFAULT_MODEL)
        temperature = input_data.get("temperature", 0.7)

        try:
            # Crear cliente Gemini
            client = GeminiClient(model_name=model_name)

            # Medir tiempo de ejecución
            start_time = time.time()

            # Generar respuesta
            response = client.generate_response(prompt=prompt, temperature=temperature)

            # Calcular tiempo de ejecución
            execution_time = time.time() - start_time

            # Construir resultado
            return {
                "text": response,
                "model": model_name,
                "execution_time": execution_time,
            }
        except Exception as e:
            logger.error(f"Error en generación con Vertex AI Gemini: {e}")
            return {
                "text": f"[Error en la generación: {str(e)}]",
                "model": model_name,
                "execution_time": 0.0,
            }


class VertexGeminiChatInput(BaseModel):
    """Esquema de entrada para la skill de chat con Vertex AI Gemini."""

    message: str = Field(..., description="Mensaje del usuario")
    model: str = Field(
        DEFAULT_MODEL,
        description=f"Modelo a utilizar (disponibles: {', '.join(AVAILABLE_MODELS)})",
    )
    temperature: float = Field(0.7, description="Control de aleatoriedad (0.0-1.0)")
    session_id: Optional[str] = Field(
        None, description="ID de sesión para continuar una conversación"
    )


class VertexGeminiChatOutput(BaseModel):
    """Esquema de salida para la skill de chat con Vertex AI Gemini."""

    text: str = Field(..., description="Respuesta generada")
    model: str = Field(..., description="Modelo utilizado")
    execution_time: float = Field(..., description="Tiempo de ejecución en segundos")
    session_id: str = Field(..., description="ID de la sesión de chat")


class VertexGeminiChatSkill(Skill):
    """
    Skill para mantener conversaciones utilizando Vertex AI Gemini.

    Permite enviar mensajes a Gemini a través de Vertex AI y mantener el contexto de la conversación.
    """

    def __init__(self):
        """Inicializa la skill de chat con Vertex AI Gemini."""
        super().__init__(
            name="vertex_gemini_chat",
            description="Mantiene conversaciones utilizando los modelos Gemini a través de Vertex AI",
            version="1.0.0",
            input_schema=VertexGeminiChatInput,
            output_schema=VertexGeminiChatOutput,
            categories=["nlp", "chat", "ai", "vertex"],
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el chat con Vertex AI Gemini.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Respuesta del chat y metadatos
        """
        import time
        import uuid

        # Extraer parámetros
        message = input_data["message"]
        model_name = input_data.get("model", DEFAULT_MODEL)
        temperature = input_data.get("temperature", 0.7)
        session_id = input_data.get("session_id")

        try:
            # Crear cliente Gemini
            client = GeminiClient(model_name=model_name)

            # Medir tiempo de ejecución
            start_time = time.time()

            # Iniciar chat o continuar sesión existente
            if session_id is None:
                # Iniciar nueva conversación
                model, session_id = client.start_chat()

            # Enviar mensaje y obtener respuesta
            response = client.chat_response(
                message=message, temperature=temperature, session_id=session_id
            )

            # Calcular tiempo de ejecución
            execution_time = time.time() - start_time

            # Construir resultado
            return {
                "text": response,
                "model": model_name,
                "execution_time": execution_time,
                "session_id": session_id,
            }
        except Exception as e:
            logger.error(f"Error en chat con Vertex AI Gemini: {e}")
            return {
                "text": f"[Error en la conversación: {str(e)}]",
                "model": model_name,
                "execution_time": 0.0,
                "session_id": session_id or str(uuid.uuid4()),
            }


class VertexGeminiModelsInput(BaseModel):
    """Esquema de entrada para la skill de obtención de modelos disponibles."""


class ModelInfo(BaseModel):
    """Información sobre un modelo de Gemini."""

    name: str = Field(..., description="Nombre del modelo")
    description: str = Field(..., description="Descripción del modelo")
    capabilities: List[str] = Field(..., description="Capacidades del modelo")


class VertexGeminiModelsOutput(BaseModel):
    """Esquema de salida para la skill de obtención de modelos disponibles."""

    models: List[ModelInfo] = Field(..., description="Lista de modelos disponibles")


class VertexGeminiModelsSkill(Skill):
    """
    Skill para obtener información sobre los modelos de Gemini disponibles en Vertex AI.

    Proporciona detalles sobre los modelos que se pueden utilizar en la aplicación.
    """

    def __init__(self):
        """Inicializa la skill de obtención de modelos disponibles."""
        super().__init__(
            name="vertex_gemini_models",
            description="Obtiene información sobre los modelos de Gemini disponibles en Vertex AI",
            version="1.0.0",
            input_schema=VertexGeminiModelsInput,
            output_schema=VertexGeminiModelsOutput,
            categories=["info", "ai", "vertex"],
            is_async=False,
        )

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtiene información sobre los modelos disponibles.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Lista de modelos disponibles y sus metadatos
        """
        try:
            # Obtener modelos disponibles
            available_models = get_available_models()

            # Convertir a formato de salida
            models_info = []
            for name, info in available_models.items():
                models_info.append(
                    ModelInfo(
                        name=name,
                        description=info.get("description", ""),
                        capabilities=info.get("capabilities", []),
                    )
                )

            return {"models": models_info}
        except Exception as e:
            logger.error(f"Error al obtener modelos disponibles: {e}")
            return {"models": []}


# Registrar las skills en el registro global
skill_registry.register_skill(VertexGeminiGenerateSkill())
skill_registry.register_skill(VertexGeminiChatSkill())
skill_registry.register_skill(VertexGeminiModelsSkill())

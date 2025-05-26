"""
Habilidades para interactuar con Vertex AI de Google Cloud.

Este módulo implementa skills que permiten utilizar modelos de IA avanzados
de Google Cloud Platform para tareas de generación de texto, análisis de documentos
y clasificación de contenido.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from clients.vertex_ai import vertex_ai_client
from core.skill import Skill, skill_registry


class VertexGenerateInput(BaseModel):
    """Esquema de entrada para la skill de generación con Vertex AI."""

    prompt: Union[str, List[Dict[str, Any]]] = Field(
        ..., description="Texto o lista de partes"
    )
    temperature: float = Field(0.7, description="Control de aleatoriedad (0.0-1.0)")
    max_output_tokens: int = Field(1024, description="Longitud máxima de la respuesta")
    top_p: float = Field(0.95, description="Parámetro de nucleus sampling")
    top_k: int = Field(40, description="Parámetro de top-k sampling")


class VertexGenerateOutput(BaseModel):
    """Esquema de salida para la skill de generación con Vertex AI."""

    text: str = Field(..., description="Texto generado")
    candidates: List[Dict[str, Any]] = Field(
        default_factory=list, description="Candidatos alternativos"
    )


class VertexGenerateSkill(Skill):
    """
    Skill para generar contenido con Vertex AI.

    Permite generar texto y contenido multimodal utilizando
    modelos avanzados de Google Cloud.
    """

    def __init__(self):
        """Inicializa la skill de generación con Vertex AI."""
        super().__init__(
            name="vertex_generate",
            description="Genera contenido con modelos de Vertex AI",
            version="1.0.0",
            input_schema=VertexGenerateInput,
            output_schema=VertexGenerateOutput,
            categories=["nlp", "generation", "ai"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la generación de contenido con Vertex AI.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Contenido generado y metadatos
        """
        # Extraer parámetros
        prompt = input_data["prompt"]
        temperature = input_data.get("temperature", 0.7)
        max_output_tokens = input_data.get("max_output_tokens", 1024)
        top_p = input_data.get("top_p", 0.95)
        top_k = input_data.get("top_k", 40)

        # Ejecutar generación
        result = await vertex_ai_client.generate_content(
            prompt=prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            top_p=top_p,
            top_k=top_k,
        )

        # Construir resultado
        return {
            "text": result.get("text", ""),
            "candidates": result.get("candidates", []),
        }


class VertexAnalyzeDocumentInput(BaseModel):
    """Esquema de entrada para la skill de análisis de documentos con Vertex AI."""

    document: str = Field(..., description="Contenido del documento a analizar")


class VertexAnalyzeDocumentOutput(BaseModel):
    """Esquema de salida para la skill de análisis de documentos con Vertex AI."""

    title: Optional[str] = Field(None, description="Título del documento")
    author: Optional[str] = Field(None, description="Autor del documento")
    date: Optional[str] = Field(None, description="Fecha del documento")
    topics: List[str] = Field(default_factory=list, description="Temas principales")
    summary: str = Field(..., description="Resumen del documento")
    entities: List[Dict[str, Any]] = Field(
        default_factory=list, description="Entidades detectadas"
    )


class VertexAnalyzeDocumentSkill(Skill):
    """
    Skill para analizar documentos con Vertex AI.

    Permite extraer información estructurada de documentos de texto.
    """

    def __init__(self):
        """Inicializa la skill de análisis de documentos con Vertex AI."""
        super().__init__(
            name="vertex_analyze_document",
            description="Analiza documentos para extraer información estructurada",
            version="1.0.0",
            input_schema=VertexAnalyzeDocumentInput,
            output_schema=VertexAnalyzeDocumentOutput,
            categories=["nlp", "analysis", "ai"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el análisis de documentos con Vertex AI.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Información estructurada extraída del documento
        """
        # Extraer parámetros
        document = input_data["document"]

        # Ejecutar análisis
        result = await vertex_ai_client.analyze_document(
            document_bytes=document.encode("utf-8"),
            prompt="Analiza este documento y extrae información estructurada",
        )

        # Extraer información
        title = result.get("title")
        author = result.get("author")
        date = result.get("date")
        topics = result.get("topics", [])
        summary = result.get("summary", "No se pudo generar un resumen.")
        entities = result.get("entities", [])

        # Construir resultado
        return {
            "title": title,
            "author": author,
            "date": date,
            "topics": topics,
            "summary": summary,
            "entities": entities,
        }


class VertexClassifyInput(BaseModel):
    """Esquema de entrada para la skill de clasificación con Vertex AI."""

    content: str = Field(..., description="Texto a clasificar")
    categories: List[str] = Field(..., description="Categorías posibles")


class VertexClassifyOutput(BaseModel):
    """Esquema de salida para la skill de clasificación con Vertex AI."""

    classifications: Dict[str, float] = Field(
        ..., description="Puntuaciones por categoría"
    )
    top_category: str = Field(..., description="Categoría con mayor puntuación")
    top_score: float = Field(..., description="Puntuación de la categoría principal")


class VertexClassifySkill(Skill):
    """
    Skill para clasificar contenido con Vertex AI.

    Permite clasificar texto en categorías predefinidas.
    """

    def __init__(self):
        """Inicializa la skill de clasificación con Vertex AI."""
        super().__init__(
            name="vertex_classify",
            description="Clasifica contenido en categorías predefinidas",
            version="1.0.0",
            input_schema=VertexClassifyInput,
            output_schema=VertexClassifyOutput,
            categories=["nlp", "classification", "ai"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la clasificación de contenido con Vertex AI.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Clasificaciones y puntuaciones
        """
        # Extraer parámetros
        content = input_data["content"]
        categories = input_data["categories"]

        # Ejecutar clasificación
        # Construir prompt para clasificación
        categories_str = ", ".join(categories)
        prompt = f"Clasifica el siguiente texto en una o más de estas categorías: {categories_str}.\n\nTexto: {content}"

        response = await vertex_ai_client.generate_content(
            prompt=prompt, temperature=0.1, max_output_tokens=512
        )

        # Procesar respuesta para extraer clasificaciones
        classifications = {}
        try:
            # Intentar extraer JSON si está presente
            import re
            import json

            # Buscar estructura JSON en la respuesta
            json_match = re.search(r"\{.*\}", response["text"], re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                classifications = data.get("classifications", {})
            else:
                # Procesamiento simple de texto
                for category in categories:
                    if category.lower() in response["text"].lower():
                        classifications[category] = 0.9
        except Exception as e:
            logger.error(f"Error al procesar clasificaciones: {e}")
            # Fallback: asignar puntuación baja a todas las categorías
            classifications = {category: 0.1 for category in categories}

        # Encontrar la categoría con mayor puntuación
        top_category = max(
            classifications.items(), key=lambda x: x[1], default=("unknown", 0.0)
        )

        # Construir resultado
        return {
            "classifications": classifications,
            "top_category": top_category[0],
            "top_score": top_category[1],
        }


# Registrar las skills
skill_registry.register_skill(VertexGenerateSkill())
skill_registry.register_skill(VertexAnalyzeDocumentSkill())
skill_registry.register_skill(VertexClassifySkill())

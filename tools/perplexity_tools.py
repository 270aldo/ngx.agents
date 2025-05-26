"""
Habilidades para interactuar con Perplexity AI.

Este módulo implementa skills que permiten realizar búsquedas, obtener respuestas
a preguntas y generar contenido con acceso a información actualizada.
"""

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from clients.perplexity_client import perplexity_client
from core.skill import Skill, skill_registry


class PerplexitySearchInput(BaseModel):
    """Esquema de entrada para la skill de búsqueda con Perplexity."""

    query: str = Field(..., description="Consulta de búsqueda")
    search_focus: str = Field("internet", description="Enfoque de la búsqueda")
    max_sources: int = Field(5, description="Número máximo de fuentes a incluir")


class PerplexitySearchOutput(BaseModel):
    """Esquema de salida para la skill de búsqueda con Perplexity."""

    answer: str = Field(..., description="Respuesta generada")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Fuentes utilizadas"
    )


class PerplexitySearchSkill(Skill):
    """
    Skill para realizar búsquedas con Perplexity AI.

    Permite realizar búsquedas en internet y obtener respuestas
    con fuentes verificables.
    """

    def __init__(self):
        """Inicializa la skill de búsqueda con Perplexity."""
        super().__init__(
            name="perplexity_search",
            description="Realiza búsquedas en internet con Perplexity AI",
            version="1.0.0",
            input_schema=PerplexitySearchInput,
            output_schema=PerplexitySearchOutput,
            categories=["search", "research", "ai"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una búsqueda con Perplexity.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Respuesta y fuentes
        """
        # Extraer parámetros
        query = input_data["query"]
        search_focus = input_data.get("search_focus", "internet")
        max_sources = input_data.get("max_sources", 5)

        # Ejecutar búsqueda
        result = await perplexity_client.search(
            query=query, search_focus=search_focus, max_sources=max_sources
        )

        # Extraer respuesta y fuentes
        answer = result.get("answer", "")
        sources = result.get("sources", [])

        # Construir resultado
        return {"answer": answer, "sources": sources}


class PerplexityAskInput(BaseModel):
    """Esquema de entrada para la skill de preguntas con Perplexity."""

    question: str = Field(..., description="Pregunta a responder")
    model: str = Field("llama-3-sonar-small-online", description="Modelo a utilizar")
    temperature: float = Field(0.7, description="Control de aleatoriedad (0.0-1.0)")
    max_tokens: int = Field(1024, description="Longitud máxima de la respuesta")


class PerplexityAskOutput(BaseModel):
    """Esquema de salida para la skill de preguntas con Perplexity."""

    answer: str = Field(..., description="Respuesta generada")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Fuentes utilizadas"
    )
    model: str = Field(..., description="Modelo utilizado")


class PerplexityAskSkill(Skill):
    """
    Skill para hacer preguntas a Perplexity AI.

    Permite realizar preguntas y obtener respuestas con acceso
    a información actualizada de internet.
    """

    def __init__(self):
        """Inicializa la skill de preguntas con Perplexity."""
        super().__init__(
            name="perplexity_ask",
            description="Hace preguntas a Perplexity AI con acceso a internet",
            version="1.0.0",
            input_schema=PerplexityAskInput,
            output_schema=PerplexityAskOutput,
            categories=["qa", "research", "ai"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una pregunta con Perplexity.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Respuesta y fuentes
        """
        # Extraer parámetros
        question = input_data["question"]
        model = input_data.get("model", "llama-3-sonar-small-online")
        temperature = input_data.get("temperature", 0.7)
        max_tokens = input_data.get("max_tokens", 1024)

        # Ejecutar pregunta
        result = await perplexity_client.ask(
            question=question,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Extraer respuesta
        answer = ""
        sources = []

        if "choices" in result and result["choices"]:
            choice = result["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                answer = choice["message"]["content"]

            # Extraer fuentes si están disponibles
            if "context" in choice and "documents" in choice["context"]:
                sources = choice["context"]["documents"]

        # Construir resultado
        return {"answer": answer, "sources": sources, "model": model}


class PerplexityResearchInput(BaseModel):
    """Esquema de entrada para la skill de investigación con Perplexity."""

    topic: str = Field(..., description="Tema a investigar")
    depth: str = Field("medium", description="Profundidad de la investigación")
    focus: Optional[str] = Field(
        None, description="Enfoque específico de la investigación"
    )
    model: str = Field("llama-3-sonar-small-online", description="Modelo a utilizar")


class PerplexityResearchOutput(BaseModel):
    """Esquema de salida para la skill de investigación con Perplexity."""

    research: str = Field(..., description="Investigación generada")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Fuentes utilizadas"
    )
    sections: List[str] = Field(
        default_factory=list, description="Secciones de la investigación"
    )


class PerplexityResearchSkill(Skill):
    """
    Skill para realizar investigaciones con Perplexity AI.

    Permite realizar investigaciones profundas sobre temas específicos
    con acceso a información actualizada.
    """

    def __init__(self):
        """Inicializa la skill de investigación con Perplexity."""
        super().__init__(
            name="perplexity_research",
            description="Realiza investigaciones profundas con Perplexity AI",
            version="1.0.0",
            input_schema=PerplexityResearchInput,
            output_schema=PerplexityResearchOutput,
            categories=["research", "ai"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una investigación con Perplexity.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Investigación y fuentes
        """
        # Extraer parámetros
        topic = input_data["topic"]
        depth = input_data.get("depth", "medium")
        focus = input_data.get("focus")
        model = input_data.get("model", "llama-3-sonar-small-online")

        # Ejecutar investigación
        result = await perplexity_client.research(
            topic=topic, depth=depth, focus=focus, model=model
        )

        # Extraer investigación y fuentes
        research = ""
        sources = []
        sections = []

        if "choices" in result and result["choices"]:
            choice = result["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                research = choice["message"]["content"]

                # Extraer secciones (títulos)
                import re

                section_pattern = r"#+\s+(.*)"
                sections = re.findall(section_pattern, research)

            # Extraer fuentes si están disponibles
            if "context" in choice and "documents" in choice["context"]:
                sources = choice["context"]["documents"]

        # Construir resultado
        return {"research": research, "sources": sources, "sections": sections}


class PerplexityFactCheckInput(BaseModel):
    """Esquema de entrada para la skill de verificación de hechos con Perplexity."""

    statement: str = Field(..., description="Afirmación a verificar")
    model: str = Field("llama-3-sonar-small-online", description="Modelo a utilizar")


class PerplexityFactCheckOutput(BaseModel):
    """Esquema de salida para la skill de verificación de hechos con Perplexity."""

    verdict: str = Field(
        ..., description="Veredicto (verdadero, falso, parcialmente verdadero)"
    )
    confidence: float = Field(..., description="Confianza en el veredicto (0.0-1.0)")
    explanation: str = Field(..., description="Explicación detallada")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Fuentes utilizadas"
    )


class PerplexityFactCheckSkill(Skill):
    """
    Skill para verificar hechos con Perplexity AI.

    Permite verificar la veracidad de afirmaciones con fuentes verificables.
    """

    def __init__(self):
        """Inicializa la skill de verificación de hechos con Perplexity."""
        super().__init__(
            name="perplexity_fact_check",
            description="Verifica la veracidad de afirmaciones con Perplexity AI",
            version="1.0.0",
            input_schema=PerplexityFactCheckInput,
            output_schema=PerplexityFactCheckOutput,
            categories=["fact_check", "research", "ai"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una verificación de hechos con Perplexity.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Resultado de la verificación
        """
        # Extraer parámetros
        statement = input_data["statement"]
        model = input_data.get("model", "llama-3-sonar-small-online")

        # Ejecutar verificación
        result = await perplexity_client.fact_check(statement=statement, model=model)

        # Extraer resultado de la verificación
        fact_check = result.get("fact_check", {})

        # Valores por defecto si no se encuentra información
        verdict = fact_check.get("verdict", "unknown")
        confidence = fact_check.get("confidence", 0.0)
        explanation = fact_check.get(
            "explanation", "No se pudo verificar la afirmación."
        )
        sources = fact_check.get("sources", [])

        # Construir resultado
        return {
            "verdict": verdict,
            "confidence": confidence,
            "explanation": explanation,
            "sources": sources,
        }


class PerplexityCompareInput(BaseModel):
    """Esquema de entrada para la skill de comparación con Perplexity."""

    items: List[str] = Field(..., description="Lista de elementos a comparar")
    criteria: Optional[List[str]] = Field(
        None, description="Criterios específicos para la comparación"
    )
    detailed: bool = Field(
        True, description="Si es True, devuelve una comparación detallada"
    )
    model: str = Field("llama-3-sonar-small-online", description="Modelo a utilizar")


class PerplexityCompareOutput(BaseModel):
    """Esquema de salida para la skill de comparación con Perplexity."""

    comparison: str = Field(..., description="Análisis comparativo")
    summary: str = Field(..., description="Resumen de las diferencias principales")
    recommendations: List[str] = Field(
        default_factory=list, description="Recomendaciones basadas en la comparación"
    )
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Fuentes utilizadas"
    )


class PerplexityCompareSkill(Skill):
    """
    Skill para realizar análisis comparativos con Perplexity AI.

    Permite comparar múltiples elementos, productos, conceptos o enfoques
    con base en criterios específicos y con acceso a información actualizada.
    """

    def __init__(self):
        """Inicializa la skill de comparación con Perplexity."""
        super().__init__(
            name="perplexity_compare",
            description="Realiza análisis comparativos con Perplexity AI",
            version="1.0.0",
            input_schema=PerplexityCompareInput,
            output_schema=PerplexityCompareOutput,
            categories=["compare", "research", "ai"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una comparación con Perplexity.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Análisis comparativo y recomendaciones
        """
        # Extraer parámetros
        items = input_data["items"]
        criteria = input_data.get("criteria", [])
        detailed = input_data.get("detailed", True)
        model = input_data.get("model", "llama-3-sonar-small-online")

        # Construir el prompt para la comparación
        prompt = f"Realiza un análisis comparativo detallado entre los siguientes elementos: {', '.join(items)}."

        if criteria:
            prompt += f" Utiliza los siguientes criterios para la comparación: {', '.join(criteria)}."

        if detailed:
            prompt += " Proporciona una explicación detallada de cada aspecto relevante, incluyendo ventajas y desventajas."

        prompt += " Incluye un resumen de las diferencias principales y recomendaciones basadas en este análisis."

        # Formato de respuesta esperado
        prompt += """ Devuelve la respuesta en el siguiente formato JSON:
        {
          "comparison": "análisis comparativo detallado",
          "summary": "resumen de las diferencias principales",
          "recommendations": ["recomendación 1", "recomendación 2", ...],
          "sources": ["fuente 1", "fuente 2", ...]
        }"""

        # Ejecutar consulta a través del método ask de Perplexity
        result = await perplexity_client.ask(
            question=prompt,
            model=model,
            temperature=0.5,  # Valor bajo para mayor consistencia en comparaciones
            max_tokens=2048,  # Mayor para permitir análisis detallados
        )

        # Extraer resultado
        comparison_result = {}
        try:
            # Extraer el JSON de la respuesta
            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]

                    # Buscar el primer { y el último }
                    import re

                    json_match = re.search(r"\{[\s\S]*\}", content)
                    if json_match:
                        json_str = json_match.group(0)
                        try:
                            comparison_result = json.loads(json_str)
                        except Exception:
                            # Si falla el parsing, intentar limpiar el JSON
                            clean_json = re.sub(r"```json|```", "", json_str)
                            comparison_result = json.loads(clean_json)
        except Exception as e:
            # Si falla el parsing, construir un resultado manualmente
            content = ""
            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]

            comparison_result = {
                "comparison": content,
                "summary": "No se pudo extraer un resumen estructurado.",
                "recommendations": [],
                "sources": [],
            }

        # Extraer fuentes si están disponibles en la respuesta
        sources = []
        if "choices" in result and result["choices"]:
            choice = result["choices"][0]
            if "context" in choice and "documents" in choice["context"]:
                sources = choice["context"]["documents"]

        # Construir resultado final
        return {
            "comparison": comparison_result.get("comparison", ""),
            "summary": comparison_result.get("summary", ""),
            "recommendations": comparison_result.get("recommendations", []),
            "sources": sources,
        }


class PerplexitySummarizeInput(BaseModel):
    """Esquema de entrada para la skill de resumen con Perplexity."""

    texts: List[str] = Field(..., description="Textos o URLs a resumir")
    length: str = Field(
        "medium", description="Longitud del resumen (short, medium, long)"
    )
    focus: Optional[str] = Field(
        None, description="Aspecto específico en el que centrarse"
    )
    model: str = Field("llama-3-sonar-small-online", description="Modelo a utilizar")


class PerplexitySummarizeOutput(BaseModel):
    """Esquema de salida para la skill de resumen con Perplexity."""

    summary: str = Field(..., description="Resumen generado")
    key_points: List[str] = Field(
        default_factory=list, description="Puntos clave extraídos"
    )
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Fuentes utilizadas"
    )


class PerplexitySummarizeSkill(Skill):
    """
    Skill para resumir múltiples fuentes con Perplexity AI.

    Permite generar resúmenes coherentes a partir de múltiples textos
    o URLs, extrayendo los puntos clave con acceso a información actualizada.
    """

    def __init__(self):
        """Inicializa la skill de resumen con Perplexity."""
        super().__init__(
            name="perplexity_summarize",
            description="Resume múltiples fuentes con Perplexity AI",
            version="1.0.0",
            input_schema=PerplexitySummarizeInput,
            output_schema=PerplexitySummarizeOutput,
            categories=["summarize", "research", "ai"],
            requires_auth=True,
            is_async=True,
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta un resumen con Perplexity.

        Args:
            input_data: Datos de entrada validados

        Returns:
            Resumen y puntos clave
        """
        # Extraer parámetros
        texts = input_data["texts"]
        length = input_data.get("length", "medium")
        focus = input_data.get("focus")
        model = input_data.get("model", "llama-3-sonar-small-online")

        # Construir el prompt para el resumen
        prompt = f"Resume los siguientes textos o URLs en un formato {length}:"

        # Añadir cada texto/URL
        for i, text in enumerate(texts, 1):
            prompt += f"\n\nFuente {i}: {text}"

        if focus:
            prompt += (
                f"\n\nCéntrate específicamente en aspectos relacionados con: {focus}"
            )

        prompt += (
            "\n\nExtrae y enumera los puntos clave de todos los textos en tu resumen."
        )

        # Formato de respuesta esperado
        prompt += """ Devuelve la respuesta en el siguiente formato JSON:
        {
          "summary": "resumen completo y coherente",
          "key_points": ["punto clave 1", "punto clave 2", ...]
        }"""

        # Ejecutar consulta a través del método ask de Perplexity
        result = await perplexity_client.ask(
            question=prompt,
            model=model,
            temperature=0.3,  # Valor bajo para mayor fidelidad en resúmenes
            max_tokens=1536,  # Ajustar según la longitud deseada
        )

        # Extraer resultado
        summary_result = {}
        try:
            # Extraer el JSON de la respuesta
            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]

                    # Buscar el primer { y el último }
                    import re

                    json_match = re.search(r"\{[\s\S]*\}", content)
                    if json_match:
                        json_str = json_match.group(0)
                        try:
                            summary_result = json.loads(json_str)
                        except Exception:
                            # Si falla el parsing, intentar limpiar el JSON
                            clean_json = re.sub(r"```json|```", "", json_str)
                            summary_result = json.loads(clean_json)
        except Exception as e:
            # Si falla el parsing, construir un resultado manualmente
            content = ""
            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]

            # Intentar extraer puntos clave
            key_points = []
            import re

            points_match = re.findall(r"\d+\. (.+)", content)
            if points_match:
                key_points = points_match

            summary_result = {"summary": content, "key_points": key_points}

        # Extraer fuentes si están disponibles en la respuesta
        sources = []
        if "choices" in result and result["choices"]:
            choice = result["choices"][0]
            if "context" in choice and "documents" in choice["context"]:
                sources = choice["context"]["documents"]

        # Construir resultado final
        return {
            "summary": summary_result.get("summary", ""),
            "key_points": summary_result.get("key_points", []),
            "sources": sources,
        }


# Registrar las skills
skill_registry.register_skill(PerplexitySearchSkill())
skill_registry.register_skill(PerplexityAskSkill())
skill_registry.register_skill(PerplexityResearchSkill())
skill_registry.register_skill(PerplexityFactCheckSkill())
skill_registry.register_skill(PerplexityCompareSkill())
skill_registry.register_skill(PerplexitySummarizeSkill())

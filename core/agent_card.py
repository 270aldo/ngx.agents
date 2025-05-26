"""
Implementación de Agent Card según las especificaciones oficiales.

Este módulo define la estructura estándar para las Agent Cards,
que describen las capacidades, entradas, salidas y ejemplos de un agente.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class InputSchema(BaseModel):
    """Esquema de entrada para un agente."""

    type: str = "object"
    properties: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class OutputSchema(BaseModel):
    """Esquema de salida para un agente."""

    type: str = "object"
    properties: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class Example(BaseModel):
    """Ejemplo de uso de un agente."""

    input: Dict[str, Any]
    output: Dict[str, Any]


class AgentCard(BaseModel):
    """
    Agent Card según las especificaciones oficiales.

    Una Agent Card describe las capacidades, entradas, salidas y ejemplos de un agente,
    siguiendo las especificaciones del protocolo A2A (Agent-to-Agent).
    """

    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: List[str] = Field(default_factory=list)
    skills: List[Dict[str, str]] = Field(default_factory=list)
    inputs: InputSchema = Field(default_factory=InputSchema)
    outputs: OutputSchema = Field(default_factory=OutputSchema)
    examples: List[Example] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create_standard_card(
        cls,
        agent_id: str,
        name: str,
        description: str,
        capabilities: List[str],
        skills: Optional[List[Dict[str, str]]] = None,
        version: str = "1.0.0",
        examples: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AgentCard":
        """
        Crea una Agent Card estándar con esquemas de entrada/salida predefinidos.

        Args:
            agent_id: Identificador único del agente
            name: Nombre del agente
            description: Descripción del agente
            capabilities: Lista de capacidades del agente
            skills: Lista de habilidades del agente (opcional)
            version: Versión del agente (opcional)
            examples: Lista de ejemplos de uso (opcional)
            metadata: Metadatos adicionales (opcional)

        Returns:
            AgentCard: Una Agent Card estándar
        """
        # Esquema de entrada estándar
        input_schema = InputSchema(
            type="object",
            properties={
                "message": {"type": "string", "description": "Mensaje del usuario"},
                "context": {
                    "type": "object",
                    "description": "Contexto adicional para el procesamiento",
                },
            },
            required=["message"],
        )

        # Esquema de salida estándar
        output_schema = OutputSchema(
            type="object",
            properties={
                "response": {"type": "string", "description": "Respuesta del agente"},
                "confidence": {
                    "type": "number",
                    "description": "Nivel de confianza en la respuesta (0-1)",
                },
                "metadata": {
                    "type": "object",
                    "description": "Metadatos adicionales sobre la respuesta",
                },
            },
            required=["response"],
        )

        # Convertir ejemplos al formato correcto
        formatted_examples = []
        if examples:
            for example in examples:
                formatted_examples.append(
                    Example(
                        input=example.get("input", {}), output=example.get("output", {})
                    )
                )

        return cls(
            agent_id=agent_id,
            name=name,
            description=description,
            version=version,
            capabilities=capabilities,
            skills=skills or [],
            inputs=input_schema,
            outputs=output_schema,
            examples=formatted_examples,
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la Agent Card a un diccionario.

        Returns:
            Dict[str, Any]: Representación en diccionario de la Agent Card
        """
        return self.model_dump()

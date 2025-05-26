"""
Mock del analizador de intenciones para pruebas.

Este módulo proporciona una versión simulada del analizador de intenciones
para usar en pruebas sin depender de servicios externos.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

# Configurar logger
logger = logging.getLogger(__name__)


class IntentEntity:
    """
    Entidad reconocida en una consulta.

    Representa una entidad identificada en la consulta del usuario,
    como un tipo de ejercicio, una métrica de salud, un objetivo, etc.
    """

    def __init__(
        self,
        entity_type: str,
        value: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Inicializa una entidad.

        Args:
            entity_type: Tipo de entidad (ej: 'exercise', 'metric', 'goal')
            value: Valor de la entidad (ej: 'push-up', 'weight', 'muscle gain')
            confidence: Confianza en la detección (0.0-1.0)
            metadata: Metadatos adicionales
        """
        self.entity_type = entity_type
        self.value = value
        self.confidence = confidence
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la entidad a un diccionario.

        Returns:
            Dict[str, Any]: Representación como diccionario
        """
        return {
            "entity_type": self.entity_type,
            "value": self.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntentEntity":
        """
        Crea una entidad a partir de un diccionario.

        Args:
            data: Diccionario con los datos de la entidad

        Returns:
            IntentEntity: Entidad creada
        """
        return cls(
            entity_type=data["entity_type"],
            value=data["value"],
            confidence=data["confidence"],
            metadata=data.get("metadata", {}),
        )


class Intent:
    """
    Intención reconocida en una consulta.

    Representa la intención del usuario y los agentes asociados que
    deberían procesar esa intención.
    """

    def __init__(
        self,
        intent_type: str,
        confidence: float,
        agents: List[str],
        entities: Optional[List[IntentEntity]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Inicializa una intención.

        Args:
            intent_type: Tipo de intención (ej: 'training_request', 'nutrition_query')
            confidence: Confianza en la detección (0.0-1.0)
            agents: Lista de IDs de agentes que deben procesar esta intención
            entities: Entidades reconocidas en la consulta
            metadata: Metadatos adicionales
        """
        self.intent_type = intent_type
        self.confidence = confidence
        self.agents = agents
        self.entities = entities or []
        self.metadata = metadata or {}
        self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la intención a un diccionario.

        Returns:
            Dict[str, Any]: Representación como diccionario
        """
        return {
            "id": self.id,
            "intent_type": self.intent_type,
            "confidence": self.confidence,
            "agents": self.agents,
            "entities": [entity.to_dict() for entity in self.entities],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Intent":
        """
        Crea una intención a partir de un diccionario.

        Args:
            data: Diccionario con los datos de la intención

        Returns:
            Intent: Intención creada
        """
        entities = []
        for entity_data in data.get("entities", []):
            entities.append(IntentEntity.from_dict(entity_data))

        intent = cls(
            intent_type=data["intent_type"],
            confidence=data["confidence"],
            agents=data["agents"],
            entities=entities,
            metadata=data.get("metadata", {}),
        )

        if "id" in data:
            intent.id = data["id"]

        return intent

    def add_entity(self, entity: IntentEntity) -> None:
        """
        Añade una entidad a la intención.

        Args:
            entity: Entidad a añadir
        """
        self.entities.append(entity)

    def get_entities_by_type(self, entity_type: str) -> List[IntentEntity]:
        """
        Obtiene entidades de un tipo específico.

        Args:
            entity_type: Tipo de entidad a buscar

        Returns:
            List[IntentEntity]: Lista de entidades del tipo especificado
        """
        return [entity for entity in self.entities if entity.entity_type == entity_type]


class IntentAnalyzer:
    """
    Analizador de intenciones simulado para pruebas.
    """

    def __init__(self):
        """Inicializa el analizador de intenciones simulado."""
        self.stats = {"total_queries": 0, "cached_embeddings": 0, "api_calls": 0}

    async def initialize(self) -> None:
        """Inicializa recursos necesarios para el analizador simulado."""
        logger.info("Mock: Analizador de intenciones inicializado (simulado)")

    async def analyze_intent(
        self,
        user_query: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        multimodal_data: Optional[Dict[str, Any]] = None,
    ) -> List[Intent]:
        """
        Analiza la intención del usuario simulada para pruebas.

        Args:
            user_query: Consulta del usuario
            conversation_id: ID de la conversación para contextualizar
            user_id: ID del usuario
            context: Contexto adicional
            multimodal_data: Datos multimodales (imágenes, audio, etc.)

        Returns:
            List[Intent]: Lista de intenciones identificadas
        """
        self.stats["total_queries"] += 1

        # Crear una intención genérica para pruebas
        intent = Intent(
            intent_type="training_request",
            confidence=0.9,
            agents=["elite_training_strategist"],
            entities=[
                IntentEntity(entity_type="exercise", value="push-up", confidence=0.95)
            ],
        )

        return [intent]

    async def analyze_intents_with_embeddings(
        self, user_query: str, conversation_id: Optional[str] = None
    ) -> List[Intent]:
        """
        Analiza intenciones utilizando embeddings simulados para pruebas.

        Args:
            user_query: Consulta del usuario
            conversation_id: ID de la conversación para contextualizar

        Returns:
            List[Intent]: Lista de intenciones identificadas
        """
        self.stats["total_queries"] += 1

        # Crear una intención genérica para pruebas
        intent = Intent(
            intent_type="nutrition_query",
            confidence=0.85,
            agents=["precision_nutrition_architect"],
        )

        return [intent]

    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso del analizador simulado.

        Returns:
            Dict[str, Any]: Estadísticas de uso
        """
        return self.stats


# Instancia global para pruebas
intent_analyzer = IntentAnalyzer()

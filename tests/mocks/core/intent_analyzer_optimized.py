"""
Mock del analizador de intenciones optimizado para pruebas.

Este módulo proporciona una versión simulada del analizador de intenciones optimizado
para usar en pruebas sin depender de servicios externos.
"""

import logging
from typing import Any, Dict, List, Optional

# Importar clases de intent_analyzer para mantener compatibilidad
from tests.mocks.core.intent_analyzer import Intent, IntentEntity

# Configurar logger
logger = logging.getLogger(__name__)


class IntentAnalyzerOptimized:
    """
    Analizador de intenciones optimizado simulado para pruebas.
    """

    # Instancia única (patrón Singleton)
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(IntentAnalyzerOptimized, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        embedding_cache_size: int = 1000,
        intent_cache_size: int = 500,
        intent_cache_ttl: int = 3600,
        similarity_threshold: float = 0.75,
    ):
        """
        Inicializa el analizador de intenciones optimizado simulado.

        Args:
            embedding_cache_size: Tamaño máximo de la caché de embeddings
            intent_cache_size: Tamaño máximo de la caché de intenciones
            intent_cache_ttl: TTL para la caché de intenciones en segundos
            similarity_threshold: Umbral de similitud para coincidencia de intenciones
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return

        # Configuración
        self.embedding_cache_size = embedding_cache_size
        self.intent_cache_size = intent_cache_size
        self.intent_cache_ttl = intent_cache_ttl
        self.similarity_threshold = similarity_threshold

        # Estadísticas
        self.stats = {
            "total_queries": 0,
            "embedding_cache_hits": 0,
            "embedding_cache_misses": 0,
            "intent_cache_hits": 0,
            "intent_cache_misses": 0,
            "llm_calls": 0,
            "embedding_calls": 0,
            "processing_time": 0.0,
            "errors": 0,
        }

        self._initialized = True
        logger.info(
            "Mock: Analizador de intenciones optimizado inicializado (simulado)"
        )

    async def initialize(self) -> bool:
        """
        Inicializa el analizador de intenciones optimizado simulado.

        Returns:
            bool: True si la inicialización fue exitosa
        """
        logger.info(
            "Mock: Analizador de intenciones optimizado inicializado (simulado)"
        )
        return True

    async def analyze_query(
        self,
        user_query: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        multimodal_data: Optional[Dict[str, Any]] = None,
    ) -> List[Intent]:
        """
        Analiza una consulta de usuario para identificar intenciones simuladas para pruebas.

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
            metadata={"optimized": True},
        )

        # Si hay datos multimodales, añadir una intención adicional
        if multimodal_data:
            intent2 = Intent(
                intent_type="biometric_analysis",
                confidence=0.85,
                agents=["biometrics_insight_engine"],
                metadata={"multimodal": True, "optimized": True},
            )
            return [intent, intent2]

        return [intent]

    async def _analyze_with_embeddings(self, user_query: str) -> List[Intent]:
        """
        Analiza una consulta utilizando embeddings simulados para pruebas.

        Args:
            user_query: Consulta del usuario

        Returns:
            List[Intent]: Lista de intenciones identificadas
        """
        self.stats["embedding_calls"] += 1

        # Crear una intención genérica para pruebas
        intent = Intent(
            intent_type="nutrition_query",
            confidence=0.85,
            agents=["precision_nutrition_architect"],
            metadata={"embedding_based": True, "optimized": True},
        )

        return [intent]

    async def _analyze_with_llm(
        self,
        user_query: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Intent]:
        """
        Analiza una consulta utilizando un modelo de lenguaje simulado para pruebas.

        Args:
            user_query: Consulta del usuario
            conversation_id: ID de la conversación para contextualizar
            user_id: ID del usuario
            context: Contexto adicional

        Returns:
            List[Intent]: Lista de intenciones identificadas
        """
        self.stats["llm_calls"] += 1

        # Crear una intención genérica para pruebas
        intent = Intent(
            intent_type="recovery_advice",
            confidence=0.9,
            agents=["recovery_corrective"],
            metadata={"llm_based": True, "optimized": True},
        )

        return [intent]

    async def _extract_entities(self, user_query: str) -> List[IntentEntity]:
        """
        Extrae entidades de una consulta simulada para pruebas.

        Args:
            user_query: Consulta del usuario

        Returns:
            List[IntentEntity]: Lista de entidades identificadas
        """
        # Crear entidades genéricas para pruebas
        entities = [
            IntentEntity(entity_type="exercise", value="push-up", confidence=0.95),
            IntentEntity(entity_type="goal", value="muscle gain", confidence=0.9),
        ]

        return entities

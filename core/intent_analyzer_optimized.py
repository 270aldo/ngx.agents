"""
Analizador avanzado de intenciones optimizado para NGX Agents.

Este módulo implementa un sistema de análisis de intenciones basado en embeddings 
y modelos semánticos para mejorar la comprensión de las consultas de los usuarios
y asignar agentes especializados de manera más eficiente.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union, Set
import uuid
import hashlib

from clients.vertex_ai import vertex_ai_client
from core.logging_config import get_logger
from core.state_manager_optimized import state_manager
# Intentar importar telemetry_manager del módulo real, si falla usar el mock
try:
    from core.telemetry import telemetry_manager
except ImportError:
    from tests.mocks.core.telemetry import telemetry_manager

# Configurar logger
logger = get_logger(__name__)


class IntentEntity:
    """
    Entidad reconocida en una consulta.
    
    Representa una entidad identificada en la consulta del usuario,
    como un tipo de ejercicio, una métrica de salud, un objetivo, etc.
    """
    
    def __init__(self, 
                 entity_type: str,
                 value: str,
                 confidence: float,
                 metadata: Optional[Dict[str, Any]] = None):
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
            "metadata": self.metadata
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
            metadata=data.get("metadata", {})
        )


class Intent:
    """
    Intención reconocida en una consulta.
    
    Representa la intención del usuario y los agentes asociados que
    deberían procesar esa intención.
    """
    
    def __init__(self, 
                 intent_type: str,
                 confidence: float,
                 agents: List[str],
                 entities: Optional[List[IntentEntity]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
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
        self.created_at = time.time()
    
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
            "created_at": self.created_at
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
        intent = cls(
            intent_type=data["intent_type"],
            confidence=data["confidence"],
            agents=data["agents"],
            entities=[IntentEntity.from_dict(entity) for entity in data.get("entities", [])],
            metadata=data.get("metadata", {})
        )
        intent.id = data.get("id", str(uuid.uuid4()))
        intent.created_at = data.get("created_at", time.time())
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


class IntentAnalyzerOptimized:
    """
    Analizador avanzado de intenciones optimizado.
    
    Utiliza embeddings y modelos semánticos para analizar consultas,
    identificar intenciones y entidades, y asignar agentes apropiados.
    Implementa caché multinivel, análisis de intenciones múltiples y
    procesamiento asíncrono para mayor eficiencia.
    """
    
    # Instancia única (patrón Singleton)
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(IntentAnalyzerOptimized, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, 
                embedding_cache_size: int = 1000,
                intent_cache_size: int = 500,
                intent_cache_ttl: int = 3600,
                similarity_threshold: float = 0.75):
        """
        Inicializa el analizador de intenciones optimizado.
        
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
        
        # Mapeo de intenciones a agentes
        self.intent_agent_map = {
            "training_request": ["elite_training_strategist"],
            "nutrition_query": ["precision_nutrition_architect"],
            "biometric_analysis": ["biometrics_insight_engine"],
            "motivation_request": ["motivation_behavior_coach"],
            "progress_tracking": ["progress_tracker"],
            "recovery_advice": ["recovery_corrective"],
            "compliance_check": ["security_compliance_guardian"],
            "integration_request": ["systems_integration_ops"],
            "general_query": ["elite_training_strategist", "precision_nutrition_architect"]
        }
        
        # Mapeo de intenciones secundarias
        self.secondary_intent_map = {
            "training_request": ["nutrition_query", "biometric_analysis", "progress_tracking"],
            "nutrition_query": ["training_request", "biometric_analysis", "progress_tracking"],
            "biometric_analysis": ["training_request", "nutrition_query", "progress_tracking"],
            "motivation_request": ["training_request", "nutrition_query"],
            "progress_tracking": ["training_request", "nutrition_query", "biometric_analysis"],
            "recovery_advice": ["training_request", "biometric_analysis"],
            "compliance_check": ["training_request", "nutrition_query"],
            "integration_request": ["biometric_analysis", "progress_tracking"]
        }
        
        # Caché de embeddings (LRU)
        self.embedding_cache: Dict[str, Tuple[List[float], float]] = {}
        self.embedding_cache_order: List[str] = []
        
        # Caché de intenciones (LRU con TTL)
        self.intent_cache: Dict[str, Tuple[List[Intent], float]] = {}
        self.intent_cache_order: List[str] = []
        
        # Semáforos para limitar conexiones concurrentes
        self.vertex_semaphore = asyncio.Semaphore(5)
        self.embedding_semaphore = asyncio.Semaphore(10)
        
        # Lock para operaciones concurrentes
        self._lock = asyncio.Lock()
        
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
            "errors": 0
        }
        
        # Ejemplos de intenciones precomputados
        self.intent_examples = self._get_intent_examples()
        
        # Embeddings de ejemplos (se cargarán bajo demanda)
        self.example_embeddings: Dict[str, List[float]] = {}
        
        self._initialized = True
        logger.info("Analizador de intenciones optimizado inicializado")
    
    async def initialize(self) -> bool:
        """
        Inicializa el analizador de intenciones.
        
        Carga modelos, recursos y precomputa embeddings de ejemplos.
        
        Returns:
            bool: True si la inicialización fue exitosa
        """
        try:
            # Inicializar cliente Vertex AI
            await vertex_ai_client.initialize()
            
            # Precomputar embeddings de ejemplos (en segundo plano)
            asyncio.create_task(self._precompute_example_embeddings())
            
            logger.info("Analizador de intenciones optimizado inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al inicializar analizador de intenciones optimizado: {e}")
            self.stats["errors"] += 1
            return False
    
    async def _precompute_example_embeddings(self) -> None:
        """
        Precomputa embeddings para ejemplos de intenciones.
        
        Esta función se ejecuta en segundo plano para mejorar el rendimiento
        de las primeras consultas.
        """
        try:
            logger.info("Iniciando precomputación de embeddings de ejemplos")
            
            for intent_type, examples in self.intent_examples.items():
                for i, example in enumerate(examples):
                    # Limitar concurrencia
                    async with self.embedding_semaphore:
                        # Generar embedding
                        text = example["text"]
                        key = f"example:{intent_type}:{i}"
                        
                        if key not in self.example_embeddings:
                            embedding = await self._get_embedding(text)
                            self.example_embeddings[key] = embedding
            
            logger.info(f"Precomputación de embeddings completada. Total: {len(self.example_embeddings)}")
            
        except Exception as e:
            logger.error(f"Error en precomputación de embeddings: {e}")
            self.stats["errors"] += 1
    
    async def analyze_query(self, 
                         user_query: str,
                         conversation_id: Optional[str] = None,
                         user_id: Optional[str] = None,
                         context: Optional[Dict[str, Any]] = None,
                         multimodal_data: Optional[Dict[str, Any]] = None) -> List[Intent]:
        """
        Analiza una consulta de usuario para identificar intenciones.
        
        Esta función combina análisis basado en embeddings y LLM para
        obtener resultados más precisos.
        
        Args:
            user_query: Consulta del usuario
            conversation_id: ID de la conversación para contextualizar
            user_id: ID del usuario
            context: Contexto adicional
            multimodal_data: Datos multimodales (imágenes, audio, etc.)
            
        Returns:
            List[Intent]: Lista de intenciones identificadas
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="analyze_query",
            attributes={
                "conversation_id": conversation_id or "unknown",
                "user_id": user_id or "unknown",
                "query_length": len(user_query),
                "has_multimodal": multimodal_data is not None
            }
        )
        
        start_time = time.time()
        self.stats["total_queries"] += 1
        
        try:
            # Verificar caché de intenciones
            cache_key = self._generate_cache_key(user_query, conversation_id, multimodal_data)
            cached_intents = await self._get_from_intent_cache(cache_key)
            
            if cached_intents:
                self.stats["intent_cache_hits"] += 1
                telemetry_manager.set_span_attribute(span_id, "cache", "hit")
                
                # Registrar tiempo de procesamiento
                processing_time = time.time() - start_time
                self.stats["processing_time"] += processing_time
                telemetry_manager.set_span_attribute(span_id, "processing_time", processing_time)
                
                return cached_intents
                
            self.stats["intent_cache_misses"] += 1
            telemetry_manager.set_span_attribute(span_id, "cache", "miss")
            
            # Determinar si la consulta contiene datos multimodales
            has_multimodal = multimodal_data is not None and len(multimodal_data) > 0
            
            # Estrategia híbrida: usar embeddings para consultas simples,
            # LLM para consultas complejas o multimodales
            if has_multimodal or len(user_query.split()) > 15:
                # Consulta compleja o multimodal: usar LLM
                intents = await self._analyze_with_llm(
                    user_query=user_query,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    context=context,
                    multimodal_data=multimodal_data
                )
                telemetry_manager.set_span_attribute(span_id, "method", "llm")
            else:
                # Consulta simple: usar embeddings primero, con fallback a LLM
                intents = await self._analyze_with_embeddings(user_query)
                
                # Si no se encontraron intenciones con alta confianza, usar LLM
                if not intents or intents[0].confidence < 0.7:
                    intents = await self._analyze_with_llm(
                        user_query=user_query,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        context=context,
                        multimodal_data=multimodal_data
                    )
                    telemetry_manager.set_span_attribute(span_id, "method", "embedding_with_llm_fallback")
                else:
                    telemetry_manager.set_span_attribute(span_id, "method", "embedding")
            
            # Extraer entidades si no se han extraído ya
            if intents and not any(intent.entities for intent in intents):
                entities = await self._extract_entities(user_query)
                for entity in entities:
                    intents[0].add_entity(entity)
            
            # Guardar en caché
            await self._add_to_intent_cache(cache_key, intents)
            
            # Agregar análisis al contexto de la conversación
            if conversation_id and intents:
                for intent in intents:
                    await self._add_intent_to_conversation(conversation_id, intent)
            
            # Registrar tiempo de procesamiento
            processing_time = time.time() - start_time
            self.stats["processing_time"] += processing_time
            telemetry_manager.set_span_attribute(span_id, "processing_time", processing_time)
            telemetry_manager.set_span_attribute(span_id, "intent_count", len(intents))
            telemetry_manager.set_span_attribute(span_id, "success", True)
            
            return intents
            
        except Exception as e:
            logger.error(f"Error al analizar consulta: {e}")
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            self.stats["errors"] += 1
            
            # Fallback a intención genérica
            return [Intent(
                intent_type="general_query",
                confidence=0.5,
                agents=["elite_training_strategist", "precision_nutrition_architect"],
                metadata={"error": str(e), "fallback": True}
            )]
            
        finally:
            telemetry_manager.end_span(span_id)
    
    async def _analyze_with_embeddings(self, user_query: str) -> List[Intent]:
        """
        Analiza intenciones utilizando embeddings.
        
        Esta función utiliza embeddings para comparar semánticamente
        la consulta con ejemplos de intenciones conocidas.
        
        Args:
            user_query: Consulta del usuario
            
        Returns:
            List[Intent]: Lista de intenciones identificadas
        """
        # Generar embedding para la consulta del usuario
        query_embedding = await self._get_embedding(user_query)
        
        # Comparar con embeddings de intenciones conocidas
        similarities: List[Dict[str, Any]] = []
        
        # Comparar con ejemplos precomputados
        for intent_type, examples in self.intent_examples.items():
            for i, example in enumerate(examples):
                # Obtener embedding del ejemplo (precomputado o bajo demanda)
                key = f"example:{intent_type}:{i}"
                if key in self.example_embeddings:
                    example_embedding = self.example_embeddings[key]
                else:
                    example_embedding = await self._get_embedding(example["text"])
                    self.example_embeddings[key] = example_embedding
                
                # Calcular similitud
                similarity = self._calculate_similarity(query_embedding, example_embedding)
                
                if similarity > self.similarity_threshold:
                    similarities.append({
                        "intent_type": intent_type,
                        "similarity": similarity,
                        "agents": self.intent_agent_map.get(intent_type, ["elite_training_strategist"]),
                        "example": example["text"]
                    })
        
        # Ordenar por similitud
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Convertir a objetos Intent
        intents = []
        
        # Intención principal (la más similar)
        if similarities:
            primary = similarities[0]
            primary_intent = Intent(
                intent_type=primary["intent_type"],
                confidence=primary["similarity"],
                agents=primary["agents"],
                metadata={"example": primary["example"]}
            )
            intents.append(primary_intent)
            
            # Buscar intenciones secundarias relacionadas
            secondary_types = self.secondary_intent_map.get(primary["intent_type"], [])
            for sim in similarities[1:]:
                if sim["intent_type"] in secondary_types and len(intents) < 3:
                    secondary_intent = Intent(
                        intent_type=sim["intent_type"],
                        confidence=sim["similarity"] * 0.9,  # Reducir confianza para secundarias
                        agents=sim["agents"],
                        metadata={"example": sim["example"], "secondary": True}
                    )
                    intents.append(secondary_intent)
        
        # Si no se encontraron intenciones, usar fallback
        if not intents:
            intents = [Intent(
                intent_type="general_query",
                confidence=0.5,
                agents=["elite_training_strategist", "precision_nutrition_architect"],
                metadata={"fallback": True}
            )]
        
        return intents
    
    async def _analyze_with_llm(self, 
                             user_query: str,
                             conversation_id: Optional[str] = None,
                             user_id: Optional[str] = None,
                             context: Optional[Dict[str, Any]] = None,
                             multimodal_data: Optional[Dict[str, Any]] = None) -> List[Intent]:
        """
        Analiza intenciones utilizando un modelo de lenguaje.
        
        Esta función utiliza Gemini para analizar la consulta y determinar
        las intenciones del usuario.
        
        Args:
            user_query: Consulta del usuario
            conversation_id: ID de la conversación para contextualizar
            user_id: ID del usuario
            context: Contexto adicional
            multimodal_data: Datos multimodales (imágenes, audio, etc.)
            
        Returns:
            List[Intent]: Lista de intenciones identificadas
        """
        # Obtener contexto de la conversación si está disponible
        conversation_messages = []
        if conversation_id:
            conversation_messages = await state_manager.get_conversation_messages(
                conversation_id=conversation_id,
                limit=5  # Últimos 5 mensajes para contexto
            )
        
        # Preparar prompt para análisis de intención
        prompt = await self._prepare_intent_prompt(
            user_query=user_query,
            conversation_messages=conversation_messages,
            context=context,
            multimodal_data=multimodal_data
        )
        
        # Analizar intención con Gemini
        async with self.vertex_semaphore:
            try:
                self.stats["llm_calls"] += 1
                
                # Preparar contenido multimodal si existe
                contents = [{"text": prompt}]
                
                if multimodal_data and "image" in multimodal_data:
                    # Añadir imagen al contenido
                    contents.append({
                        "image": multimodal_data["image"]
                    })
                
                response = await vertex_ai_client.generate_content(
                    contents=contents,
                    temperature=0.2,
                    max_output_tokens=1024
                )
                
                # Extraer intenciones del análisis
                intents = await self._extract_intents_from_response(response["text"])
                
                return intents
                
            except Exception as e:
                logger.error(f"Error al analizar intención con LLM: {e}")
                self.stats["errors"] += 1
                
                # Fallback a intención genérica
                return [Intent(
                    intent_type="general_query",
                    confidence=0.5,
                    agents=["elite_training_strategist", "precision_nutrition_architect"],
                    metadata={"error": str(e), "fallback": True}
                )]
    
    async def _get_embedding(self, text: str) -> List[float]:
        """
        Obtiene el embedding de un texto.
        
        Utiliza caché para evitar recalcular embeddings.
        
        Args:
            text: Texto a convertir en embedding
            
        Returns:
            List[float]: Vector de embedding
        """
        # Normalizar texto para caché
        normalized_text = text.lower().strip()
        
        # Comprobar si ya está en caché
        async with self._lock:
            if normalized_text in self.embedding_cache:
                # Actualizar orden LRU
                self.embedding_cache_order.remove(normalized_text)
                self.embedding_cache_order.append(normalized_text)
                
                self.stats["embedding_cache_hits"] += 1
                return self.embedding_cache[normalized_text][0]
            
            self.stats["embedding_cache_misses"] += 1
        
        # Generar embedding
        async with self.embedding_semaphore:
            try:
                self.stats["embedding_calls"] += 1
                embedding = await vertex_ai_client.generate_embedding(text)
                
                # Guardar en caché
                async with self._lock:
                    # Verificar tamaño de caché
                    if len(self.embedding_cache) >= self.embedding_cache_size:
                        # Eliminar el menos usado recientemente
                        oldest = self.embedding_cache_order.pop(0)
                        del self.embedding_cache[oldest]
                    
                    # Añadir nuevo embedding
                    self.embedding_cache[normalized_text] = (embedding, time.time())
                    self.embedding_cache_order.append(normalized_text)
                
                return embedding
                
            except Exception as e:
                logger.error(f"Error al generar embedding: {e}")
                self.stats["errors"] += 1
                
                # Retornar embedding vacío en caso de error
                return [0.0] * 768  # Dimensión típica de embeddings
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calcula la similitud coseno entre dos embeddings.
        
        Args:
            embedding1: Primer embedding
            embedding2: Segundo embedding
            
        Returns:
            float: Similitud coseno (0.0-1.0)
        """
        # Implementar cálculo de similitud coseno
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        if magnitude1 * magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _get_intent_examples(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Obtiene ejemplos de intenciones para comparación semántica.
        
        Returns:
            Dict[str, List[Dict[str, str]]]: Ejemplos de intenciones por tipo
        """
        return {
            "training_request": [
                {"text": "Necesito un programa de entrenamiento para ganar masa muscular"},
                {"text": "Quiero un plan de entrenamiento para correr una maratón"},
                {"text": "¿Puedes diseñarme una rutina de ejercicios para hacer en casa?"}
            ],
            "nutrition_query": [
                {"text": "¿Cuál es la mejor dieta para perder peso?"},
                {"text": "Necesito un plan de alimentación para atletas"},
                {"text": "¿Qué debería comer antes de entrenar?"}
            ],
            "biometric_analysis": [
                {"text": "Analiza mis métricas de sueño de este mes"},
                {"text": "¿Qué significan mis niveles de glucosa?"},
                {"text": "Revisa mis datos de frecuencia cardíaca durante el ejercicio"}
            ],
            "motivation_request": [
                {"text": "No tengo motivación para ir al gimnasio"},
                {"text": "¿Cómo puedo mantenerme consistente con mi entrenamiento?"},
                {"text": "Necesito ayuda para no abandonar mi dieta"}
            ],
            "progress_tracking": [
                {"text": "¿Estoy progresando adecuadamente?"},
                {"text": "Muéstrame mi evolución de los últimos 3 meses"},
                {"text": "Quiero ver mis mejoras en fuerza"}
            ],
            "recovery_advice": [
                {"text": "Tengo dolor en el hombro después de entrenar"},
                {"text": "¿Cómo puedo recuperarme más rápido entre entrenamientos?"},
                {"text": "Estrategias para reducir el dolor muscular"}
            ],
            "compliance_check": [
                {"text": "¿Este programa cumple con las regulaciones médicas?"},
                {"text": "Necesito verificar si estos suplementos están permitidos"},
                {"text": "¿Hay algún problema legal con mi plan de entrenamiento?"}
            ],
            "integration_request": [
                {"text": "Conecta mi reloj Garmin a la aplicación"},
                {"text": "¿Puedes sincronizar mis datos con Strava?"},
                {"text": "Necesito exportar mis métricas a Excel"}
            ]
        }
    
    def _generate_cache_key(self, 
                          user_query: str, 
                          conversation_id: Optional[str] = None,
                          multimodal_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Genera una clave única para la caché de intenciones.
        
        Args:
            user_query: Consulta del usuario
            conversation_id: ID de la conversación
            multimodal_data: Datos multimodales
            
        Returns:
            str: Clave única para la caché
        """
        # Normalizar consulta
        normalized_query = user_query.lower().strip()
        
        # Crear componentes de la clave
        key_components = [normalized_query]
        
        if conversation_id:
            key_components.append(f"conv:{conversation_id}")

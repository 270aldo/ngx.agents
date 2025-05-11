"""
Adaptador para el Analizador de Intenciones de NGX Agents.

Este módulo implementa un adaptador que permite la migración gradual
del analizador de intenciones original al optimizado, manteniendo
la compatibilidad con el código existente.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union

from core.intent_analyzer import Intent, IntentEntity, intent_analyzer
from core.intent_analyzer_optimized import IntentAnalyzerOptimized
from core.logging_config import get_logger
from core.telemetry import telemetry_manager

# Configurar logger
logger = get_logger(__name__)


class IntentAnalyzerAdapter:
    """
    Adaptador para el analizador de intenciones.
    
    Proporciona una interfaz compatible con el analizador original,
    pero permite utilizar internamente el analizador optimizado.
    """
    
    # Instancia única (patrón Singleton)
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(IntentAnalyzerAdapter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, use_optimized: bool = False):
        """
        Inicializa el adaptador.
        
        Args:
            use_optimized: Si True, utiliza el analizador optimizado.
                          Si False, utiliza el analizador original.
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return
        
        self.use_optimized = use_optimized
        self._original_analyzer = intent_analyzer
        self._optimized_analyzer = IntentAnalyzerOptimized()
        
        # Estadísticas
        self.stats = {
            "total_queries": 0,
            "original_analyzer_calls": 0,
            "optimized_analyzer_calls": 0,
            "errors": 0,
            "processing_time": 0.0
        }
        
        self._initialized = True
        logger.info(f"Adaptador de analizador de intenciones inicializado (use_optimized={use_optimized})")
    
    async def initialize(self) -> bool:
        """
        Inicializa el adaptador y los analizadores subyacentes.
        
        Returns:
            bool: True si la inicialización fue exitosa
        """
        try:
            # Inicializar ambos analizadores
            await self._original_analyzer.initialize()
            
            # Inicializar el optimizado solo si se va a utilizar
            if self.use_optimized:
                await self._optimized_analyzer.initialize()
            
            logger.info("Adaptador de analizador de intenciones inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al inicializar adaptador de analizador de intenciones: {e}")
            self.stats["errors"] += 1
            return False
    
    def set_use_optimized(self, use_optimized: bool) -> None:
        """
        Cambia el analizador a utilizar.
        
        Args:
            use_optimized: Si True, utiliza el analizador optimizado.
                          Si False, utiliza el analizador original.
        """
        self.use_optimized = use_optimized
        logger.info(f"Cambiado analizador a: {'optimizado' if use_optimized else 'original'}")
    
    async def analyze_intent(self, 
                           user_query: str,
                           conversation_id: Optional[str] = None,
                           user_id: Optional[str] = None,
                           context: Optional[Dict[str, Any]] = None,
                           multimodal_data: Optional[Dict[str, Any]] = None) -> List[Intent]:
        """
        Analiza la intención del usuario.
        
        Mantiene la interfaz del analizador original, pero puede utilizar
        internamente el analizador optimizado.
        
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
            name="intent_analyzer_adapter.analyze_intent",
            attributes={
                "conversation_id": conversation_id or "unknown",
                "user_id": user_id or "unknown",
                "query_length": len(user_query),
                "has_multimodal": multimodal_data is not None,
                "use_optimized": self.use_optimized
            }
        )
        
        start_time = time.time()
        self.stats["total_queries"] += 1
        
        try:
            # Utilizar el analizador correspondiente
            if self.use_optimized:
                self.stats["optimized_analyzer_calls"] += 1
                
                # El analizador optimizado tiene un método diferente
                intents = await self._optimized_analyzer.analyze_query(
                    user_query=user_query,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    context=context,
                    multimodal_data=multimodal_data
                )
                
            else:
                self.stats["original_analyzer_calls"] += 1
                
                # Utilizar el analizador original
                intents = await self._original_analyzer.analyze_intent(
                    user_query=user_query,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    context=context,
                    multimodal_data=multimodal_data
                )
            
            # Registrar tiempo de procesamiento
            processing_time = time.time() - start_time
            self.stats["processing_time"] += processing_time
            
            telemetry_manager.set_span_attribute(span_id, "processing_time", processing_time)
            telemetry_manager.set_span_attribute(span_id, "intent_count", len(intents))
            telemetry_manager.set_span_attribute(span_id, "success", True)
            
            return intents
            
        except Exception as e:
            logger.error(f"Error en adaptador de analizador de intenciones: {e}")
            self.stats["errors"] += 1
            
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            
            # Fallback a intención genérica
            return [Intent(
                intent_type="general_query",
                confidence=0.5,
                agents=["elite_training_strategist", "precision_nutrition_architect"],
                metadata={"error": str(e), "fallback": True, "from_adapter": True}
            )]
            
        finally:
            telemetry_manager.end_span(span_id)
    
    async def analyze_intents_with_embeddings(self, 
                                           user_query: str,
                                           conversation_id: Optional[str] = None) -> List[Intent]:
        """
        Analiza intenciones utilizando embeddings.
        
        Mantiene la interfaz del analizador original, pero puede utilizar
        internamente el analizador optimizado.
        
        Args:
            user_query: Consulta del usuario
            conversation_id: ID de la conversación para contextualizar
            
        Returns:
            List[Intent]: Lista de intenciones identificadas
        """
        # Registrar inicio de telemetría
        span_id = telemetry_manager.start_span(
            name="intent_analyzer_adapter.analyze_intents_with_embeddings",
            attributes={
                "conversation_id": conversation_id or "unknown",
                "query_length": len(user_query),
                "use_optimized": self.use_optimized
            }
        )
        
        start_time = time.time()
        
        try:
            # Utilizar el analizador correspondiente
            if self.use_optimized:
                # El analizador optimizado no tiene este método específico,
                # pero podemos usar analyze_query que internamente usa embeddings
                intents = await self._optimized_analyzer.analyze_query(
                    user_query=user_query,
                    conversation_id=conversation_id
                )
                
            else:
                # Utilizar el analizador original
                intents = await self._original_analyzer.analyze_intents_with_embeddings(
                    user_query=user_query,
                    conversation_id=conversation_id
                )
            
            # Registrar tiempo de procesamiento
            processing_time = time.time() - start_time
            
            telemetry_manager.set_span_attribute(span_id, "processing_time", processing_time)
            telemetry_manager.set_span_attribute(span_id, "intent_count", len(intents))
            telemetry_manager.set_span_attribute(span_id, "success", True)
            
            return intents
            
        except Exception as e:
            logger.error(f"Error en adaptador de analizador de intenciones (embeddings): {e}")
            
            telemetry_manager.set_span_attribute(span_id, "error", str(e))
            
            # Fallback a intención genérica
            return [Intent(
                intent_type="general_query",
                confidence=0.5,
                agents=["elite_training_strategist", "precision_nutrition_architect"],
                metadata={"error": str(e), "fallback": True, "from_adapter": True}
            )]
            
        finally:
            telemetry_manager.end_span(span_id)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso del adaptador y analizadores.
        
        Returns:
            Dict[str, Any]: Estadísticas de uso
        """
        # Obtener estadísticas de los analizadores subyacentes
        original_stats = await self._original_analyzer.get_stats()
        
        stats = {
            **self.stats,
            "original_analyzer": original_stats,
        }
        
        # Añadir estadísticas del optimizado si se está utilizando
        if self.use_optimized:
            optimized_stats = self._optimized_analyzer.stats
            stats["optimized_analyzer"] = optimized_stats
        
        # Calcular métricas adicionales
        if self.stats["total_queries"] > 0:
            stats["avg_processing_time"] = self.stats["processing_time"] / self.stats["total_queries"]
        
        return stats


# Crear instancia global del adaptador
intent_analyzer_adapter = IntentAnalyzerAdapter()

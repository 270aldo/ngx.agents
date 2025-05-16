"""
Adaptador para el agente BiometricsInsightEngine que utiliza los componentes optimizados.

Este adaptador extiende el agente BiometricsInsightEngine original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime

from agents.biometrics_insight_engine.agent import BiometricsInsightEngine
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from core.telemetry_adapter import telemetry_adapter
from core.logging_config import get_logger
from clients.vertex_ai_client_adapter import vertex_ai_client

# Configurar logger
logger = get_logger(__name__)

class BiometricsInsightEngineAdapter(BiometricsInsightEngine, BaseAgentAdapter):
    """
    Adaptador para el agente BiometricsInsightEngine que utiliza los componentes optimizados.
    
    Este adaptador extiende el agente BiometricsInsightEngine original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa el adaptador BiometricsInsightEngine.
        
        Args:
            *args: Argumentos posicionales para la clase base
            **kwargs: Argumentos de palabras clave para la clase base
        """
        super().__init__(*args, **kwargs)
        
        # Configuración de clasificación específica para este agente
        self.fallback_keywords = [
            "biométricos", "biometrics", "hrv", "sueño", "sleep", 
            "glucosa", "glucose", "composición corporal", "body composition",
            "datos de salud", "health data", "métricas", "metrics",
            "análisis biométrico", "biometric analysis", "tendencias", "trends"
        ]
        
        self.excluded_keywords = [
            "entrenamiento", "training", "nutrición", "nutrition",
            "receta", "recipe", "meal", "comida"
        ]
        
        # Métricas de telemetría
        self.metrics = {
            "queries_processed": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_processing_time": 0,
            "total_processing_time": 0,
            "query_types": {}
        }
        
        logger.info(f"Adaptador del BiometricsInsightEngine inicializado: {self.agent_id}")
    
    async def initialize(self) -> bool:
        """
        Inicializa el adaptador y registra el agente con el servidor A2A.
        
        Returns:
            bool: True si la inicialización fue exitosa
        """
        try:
            # Registrar el agente con el servidor A2A
            await self._register_with_a2a_server()
            
            # Inicializar componentes
            await intent_analyzer_adapter.initialize()
            await state_manager_adapter.initialize()
            
            logger.info(f"Adaptador del BiometricsInsightEngine inicializado correctamente: {self.agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error al inicializar el adaptador del BiometricsInsightEngine: {e}", exc_info=True)
            return False
    
    async def _register_with_a2a_server(self) -> None:
        """
        Registra el agente con el servidor A2A optimizado.
        """
        try:
            # Crear función de callback para recibir mensajes
            async def message_handler(message: Dict[str, Any]) -> Dict[str, Any]:
                try:
                    # Extraer información del mensaje
                    user_input = message.get("user_input", "")
                    context = message.get("context", {})
                    user_id = context.get("user_id", "anonymous")
                    session_id = context.get("session_id", "")
                    
                    # Procesar la consulta
                    response = await self.run_async_impl(
                        query=user_input,
                        user_id=user_id,
                        session_id=session_id,
                        context=context
                    )
                    
                    return response
                except Exception as e:
                    logger.error(f"Error en message_handler: {e}", exc_info=True)
                    return {
                        "status": "error",
                        "error": str(e),
                        "output": "Lo siento, ha ocurrido un error al procesar tu solicitud."
                    }
            
            # Registrar el agente con el adaptador A2A
            a2a_adapter.register_agent(
                agent_id=self.agent_id,
                agent_info={
                    "name": self.name,
                    "description": self.description,
                    "message_callback": message_handler
                }
            )
            
            logger.info(f"Agente BiometricsInsightEngine registrado con el servidor A2A: {self.agent_id}")
        except Exception as e:
            logger.error(f"Error al registrar el agente BiometricsInsightEngine con el servidor A2A: {e}", exc_info=True)
            raise
    
    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente BiometricsInsightEngine.
        
        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "analyses": [],
            "biometric_data": {},
            "visualizations": [],
            "pattern_analyses": [],
            "trend_analyses": [],
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para BiometricsInsightEngine.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "análisis": "biometric_analysis",
            "analysis": "biometric_analysis",
            "biométricos": "biometric_analysis",
            "biometrics": "biometric_analysis",
            "patrones": "pattern_recognition",
            "patterns": "pattern_recognition",
            "tendencias": "trend_identification",
            "trends": "trend_identification",
            "visualización": "data_visualization",
            "visualization": "data_visualization",
            "gráfico": "data_visualization",
            "chart": "data_visualization"
        }
    
    def _adjust_score_based_on_context(self, score: float, context: Dict[str, Any]) -> float:
        """
        Ajusta la puntuación de clasificación basada en el contexto.
        
        Args:
            score: Puntuación de clasificación original
            context: Contexto adicional para la clasificación
            
        Returns:
            float: Puntuación ajustada
        """
        # Puntuación base
        adjusted_score = score
        
        # Si hay análisis biométricos previos, aumentar la puntuación
        if context.get("analyses") or context.get("biometric_data"):
            adjusted_score += 0.15
        
        # Si hay análisis de patrones o tendencias previos, aumentar la puntuación
        if context.get("pattern_analyses") or context.get("trend_analyses"):
            adjusted_score += 0.1
        
        # Si el contexto menciona datos biométricos, aumentar la puntuación
        if context.get("mentions_biometrics", False) or context.get("mentions_health_data", False):
            adjusted_score += 0.2
        
        # Limitar la puntuación máxima a 1.0
        return min(1.0, adjusted_score)
    
    async def _process_query(self, query: str, user_id: str, session_id: str,
                           program_type: str, state: Dict[str, Any], profile: Dict[str, Any],
                           **kwargs) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario.
        
        Este método implementa la lógica específica del BiometricsInsightEngine utilizando la funcionalidad
        de la clase base BaseAgentAdapter.
        
        Args:
            query: La consulta del usuario
            user_id: ID del usuario
            session_id: ID de la sesión
            program_type: Tipo de programa (general, elite, etc.)
            state: Estado actual del usuario
            profile: Perfil del usuario
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta del agente
        """
        try:
            # Iniciar span de telemetría
            span = telemetry_adapter.start_span("biometrics_insight_engine.process_query")
            
            # Incrementar contador de consultas procesadas
            self.metrics["queries_processed"] += 1
            
            # Registrar inicio de procesamiento
            start_time = time.time()
            
            # Analizar la intención para determinar el tipo de consulta
            intent_result = await intent_analyzer_adapter.analyze_intent(query)
            
            # Determinar el tipo de consulta basado en la intención
            query_type = self._determine_query_type(intent_result, query)
            
            # Registrar distribución de tipos de consulta
            self.metrics["query_types"][query_type] = self.metrics["query_types"].get(query_type, 0) + 1
            
            # Registrar información de telemetría
            telemetry_adapter.set_span_attribute(span, "query_type", query_type)
            telemetry_adapter.set_span_attribute(span, "user_id", user_id)
            telemetry_adapter.set_span_attribute(span, "session_id", session_id)
            
            logger.info(f"BiometricsInsightEngineAdapter procesando consulta de tipo: {query_type}")
            
            # Obtener o crear el contexto
            context = state.get("biometrics_context", self._create_default_context())
            
            # Procesar según el tipo de consulta
            if query_type == "biometric_analysis":
                result = await self._handle_biometric_analysis(query, context, profile, program_type)
            elif query_type == "pattern_recognition":
                result = await self._handle_pattern_recognition(query, context, profile)
            elif query_type == "trend_identification":
                result = await self._handle_trend_identification(query, context, profile)
            elif query_type == "data_visualization":
                result = await self._handle_data_visualization(query, context, profile)
            else:
                # Tipo de consulta no reconocido, usar procesamiento genérico
                result = await self._handle_generic_query(query, context, profile, program_type)
            
            # Actualizar el contexto en el estado
            state["biometrics_context"] = context
            
            # Calcular tiempo de procesamiento
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Actualizar métricas
            self.metrics["successful_queries"] += 1
            self.metrics["total_processing_time"] += processing_time
            self.metrics["average_processing_time"] = (
                self.metrics["total_processing_time"] / self.metrics["successful_queries"]
            )
            
            # Registrar información de telemetría
            telemetry_adapter.set_span_attribute(span, "processing_time", processing_time)
            telemetry_adapter.set_span_attribute(span, "success", True)
            
            # Finalizar span de telemetría
            telemetry_adapter.end_span(span)
            
            # Construir la respuesta
            response = {
                "status": "success",
                "output": result.get("response", "No se pudo generar una respuesta"),
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "query_type": query_type,
                "program_type": program_type,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            return response
            
        except Exception as e:
            # Incrementar contador de consultas fallidas
            self.metrics["failed_queries"] += 1
            
            # Registrar error en telemetría
            if 'span' in locals():
                telemetry_adapter.set_span_attribute(span, "error", str(e))
                telemetry_adapter.set_span_attribute(span, "success", False)
                telemetry_adapter.end_span(span)
            
            logger.error(f"Error al procesar consulta en BiometricsInsightEngineAdapter: {str(e)}", exc_info=True)
            
            # Devolver respuesta de error
            return {
                "status": "error",
                "error": str(e),
                "output": "Lo siento, ha ocurrido un error al procesar tu solicitud.",
                "agent_id": self.agent_id,
                "agent_name": self.name
            }
    
    def _determine_query_type(self, intent_result: List[Any], query: str) -> str:
        """
        Determina el tipo de consulta basado en la intención y el texto.
        
        Args:
            intent_result: Resultado del análisis de intención
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta determinado
        """
        # Obtener el mapeo de intenciones a tipos de consulta
        intent_mapping = self._get_intent_to_query_type_mapping()
        
        # Verificar si hay una intención reconocida
        if intent_result and len(intent_result) > 0:
            intent = intent_result[0]
            intent_type = intent.intent_type.lower()
            
            # Buscar en el mapeo
            for key, query_type in intent_mapping.items():
                if key in intent_type:
                    return query_type
        
        # Si no se encuentra una intención específica, determinar por palabras clave
        query_lower = query.lower()
        
        if "análisis" in query_lower or "analysis" in query_lower or "biométricos" in query_lower or "biometrics" in query_lower:
            return "biometric_analysis"
        elif "patrones" in query_lower or "patterns" in query_lower:
            return "pattern_recognition"
        elif "tendencias" in query_lower or "trends" in query_lower:
            return "trend_identification"
        elif "visualización" in query_lower or "visualization" in query_lower or "gráfico" in query_lower or "chart" in query_lower:
            return "data_visualization"
        
        # Valor por defecto
        return "biometric_analysis"
    
    def _get_sample_biometric_data(self) -> Dict[str, Any]:
        """
        Obtiene datos biométricos de ejemplo para usar cuando no hay datos reales.
        
        Returns:
            Dict[str, Any]: Datos biométricos de ejemplo
        """
        return {
            "heart_rate": {
                "resting": 65,
                "max": 175,
                "average": 72,
                "hrv": 45
            },
            "sleep": {
                "average_duration": 7.2,
                "deep_sleep": 1.8,
                "rem_sleep": 1.5,
                "light_sleep": 3.9,
                "sleep_score": 82
            },
            "glucose": {
                "fasting": 85,
                "post_meal_average": 120,
                "variability": 15
            },
            "body_composition": {
                "weight": 75,
                "muscle_mass": 32,
                "body_fat": 18,
                "water": 55
            },
            "activity": {
                "steps": 8500,
                "active_minutes": 45,
                "calories_burned": 2200
            }
        }
    
    def _build_prompt_with_context(self, prompt: str, context: Dict[str, Any], profile: Dict[str, Any] = None, program_type: str = None) -> str:
        """
        Construye un prompt completo incluyendo el contexto relevante.
        
        Args:
            prompt: Prompt base
            context: Contexto para incluir
            profile: Perfil del usuario (opcional)
            program_type: Tipo de programa (opcional)
            
        Returns:
            str: Prompt completo con contexto
        """
        # Iniciar con el prompt base
        full_prompt = f"Como especialista en análisis de datos biométricos, {prompt}\n\n"
        
        # Añadir información del perfil del usuario si está disponible
        if profile and isinstance(profile, dict):
            full_prompt += "Información del usuario:\n"
            
            if "age" in profile:
                full_prompt += f"- Edad: {profile['age']}\n"
            if "gender" in profile:
                full_prompt += f"- Género: {profile['gender']}\n"
            if "fitness_level" in profile:
                full_prompt += f"- Nivel de condición física: {profile['fitness_level']}\n"
            if "medical_conditions" in profile and isinstance(profile['medical_conditions'], list):
                full_prompt += f"- Condiciones médicas: {', '.join(profile['medical_conditions'])}\n"
            
            full_prompt += "\n"
        
        # Añadir tipo de programa si está disponible
        if program_type:
            full_prompt += f"Tipo de programa: {program_type}\n\n"
        
        # Añadir datos biométricos si están disponibles
        if "biometric_data" in context and context["biometric_data"]:
            full_prompt += f"Datos biométricos:\n{context['biometric_data']}\n\n"
        
        # Añadir análisis previos si están disponibles
        if "analyses" in context and context["analyses"]:
            # Tomar solo el análisis más reciente para no sobrecargar el prompt
            latest_analysis = context["analyses"][-1]
            full_prompt += f"Análisis previo ({latest_analysis['date']}):\n"
            full_prompt += f"{latest_analysis['analysis']}\n\n"
        
        # Añadir análisis de patrones previos si están disponibles
        if "pattern_analyses" in context and context["pattern_analyses"]:
            # Tomar solo el análisis más reciente
            latest_pattern = context["pattern_analyses"][-1]
            full_prompt += f"Análisis de patrones previo ({latest_pattern['date']}):\n"
            full_prompt += f"{latest_pattern['analysis']}\n\n"
        
        # Añadir análisis de tendencias previos si están disponibles
        if "trend_analyses" in context and context["trend_analyses"]:
            # Tomar solo el análisis más reciente
            latest_trend = context["trend_analyses"][-1]
            full_prompt += f"Análisis de tendencias previo ({latest_trend['date']}):\n"
            full_prompt += f"{latest_trend['analysis']}\n\n"
        
        return full_prompt
    
    async def _handle_biometric_analysis(self, query: str, context: Dict[str, Any], 
                                       profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta de análisis biométrico.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado del análisis
        """
        # Obtener datos biométricos del contexto o usar datos de ejemplo
        biometric_data = context.get("biometric_data", {})
        if not biometric_data:
            biometric_data = self._get_sample_biometric_data()
            context["biometric_data"] = biometric_data
        
        # Generar el análisis
        analysis = self._generate_response(
            prompt=self._build_prompt_with_context(
                f"Analiza los siguientes datos biométricos y proporciona insights personalizados y recomendaciones basadas en los patrones observados para la consulta: {query}",
                context,
                profile,
                program_type
            )
        )
        
        # Actualizar el contexto con el nuevo análisis
        if "analyses" not in context:
            context["analyses"] = []
            
        context["analyses"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "analysis": analysis,
            "program_type": program_type
        })
        
        return {
            "response": analysis,
            "context": context
        }
    
    async def _handle_pattern_recognition(self, query: str, context: Dict[str, Any], 
                                        profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja una consulta de reconocimiento de patrones.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Resultado del reconocimiento de patrones
        """
        # Obtener datos biométricos del contexto o usar datos de ejemplo
        biometric_data = context.get("biometric_data", {})
        if not biometric_data:
            biometric_data = self._get_sample_biometric_data()
            context["biometric_data"] = biometric_data
        
        # Generar el análisis de patrones
        patterns_analysis = self._generate_response(
            prompt=self._build_prompt_with_context(
                f"Identifica patrones recurrentes en los datos biométricos para la consulta: {query}. Incluye patrones identificados, correlaciones entre métricas, posibles relaciones causales y recomendaciones.",
                context,
                profile
            )
        )
        
        # Actualizar el contexto con el nuevo análisis de patrones
        if "pattern_analyses" not in context:
            context["pattern_analyses"] = []
            
        context["pattern_analyses"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "analysis": patterns_analysis
        })
        
        return {
            "response": patterns_analysis,
            "context": context
        }
    
    async def _handle_trend_identification(self, query: str, context: Dict[str, Any], 
                                         profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja una consulta de identificación de tendencias.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Resultado de la identificación de tendencias
        """
        # Obtener datos biométricos del contexto o usar datos de ejemplo
        biometric_data = context.get("biometric_data", {})
        if not biometric_data:
            biometric_data = self._get_sample_biometric_data()
            context["biometric_data"] = biometric_data
        
        # Generar el análisis de tendencias
        trends_analysis = self._generate_response(
            prompt=self._build_prompt_with_context(
                f"Analiza las tendencias en los datos biométricos para la consulta: {query}. Incluye tendencias identificadas, cambios significativos, progreso hacia objetivos, proyecciones futuras y recomendaciones.",
                context,
                profile
            )
        )
        
        # Actualizar el contexto con el nuevo análisis de tendencias
        if "trend_analyses" not in context:
            context["trend_analyses"] = []
            
        context["trend_analyses"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "analysis": trends_analysis
        })
        
        return {
            "response": trends_analysis,
            "context": context
        }
    
    async def _handle_data_visualization(self, query: str, context: Dict[str, Any], 
                                       profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja una consulta de visualización de datos.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Resultado de la visualización de datos
        """
        # Obtener datos biométricos del contexto o usar datos de ejemplo
        biometric_data = context.get("biometric_data", {})
        if not biometric_data:
            biometric_data = self._get_sample_biometric_data()
            context["biometric_data"] = biometric_data
        
        # Generar la descripción de la visualización
        visualization_description = self._generate_response(
            prompt=self._build_prompt_with_context(
                f"Describe una visualización para los datos biométricos relacionada con la consulta: {query}. Incluye tipo de gráfico recomendado, métricas a visualizar, ejes y escalas, patrones destacados e interpretación.",
                context,
                profile
            )
        )
        
        # Actualizar el contexto con la nueva visualización
        if "visualizations" not in context:
            context["visualizations"] = []
            
        visualization_id = f"viz_{len(context['visualizations']) + 1}"
        
        context["visualizations"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "description": visualization_description,
            "visualization_id": visualization_id
        })
        
        return {
            "response": visualization_description,
            "context": context
        }
    
    async def _handle_generic_query(self, query: str, context: Dict[str, Any], 
                                  profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta genérica.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado del procesamiento
        """
        # Generar respuesta genérica
        response = self._generate_response(
            prompt=self._build_prompt_with_context(
                f"Responde a la siguiente consulta: {query}",
                context,
                profile,
                program_type
            )
        )
        
        # Actualizar el historial de conversación
        if "conversation_history" not in context:
            context["conversation_history"] = []
            
        context["conversation_history"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "response": response
        })
        
        return {
            "response": response,
            "context": context
        }
    
    def _generate_response(self, prompt: str) -> str:
        """
        Genera una respuesta utilizando el cliente Vertex AI optimizado.
        
        Args:
            prompt: Prompt para generar la respuesta
            
        Returns:
            str: Respuesta generada
        """
        try:
            # Generar respuesta utilizando el cliente Vertex AI optimizado
            response = vertex_ai_client.generate_text(
                prompt=prompt,
                max_tokens=1024,
                temperature=0.7,
                model="gemini-pro"
            )
            
            return response
        except Exception as e:
            logger.error(f"Error al generar respuesta: {e}", exc_info=True)
            return f"Lo siento, ha ocurrido un error al generar la respuesta: {str(e)}"
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas de rendimiento del adaptador.
        
        Returns:
            Dict[str, Any]: Métricas de rendimiento
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "metrics": self.metrics
        }


# Crear instancia del adaptador
biometrics_insight_engine_adapter = BiometricsInsightEngineAdapter()

# Función para inicializar el adaptador
async def initialize_biometrics_insight_engine_adapter():
    """
    Inicializa el adaptador del BiometricsInsightEngine y lo registra con el servidor A2A optimizado.
    """
    try:
        await biometrics_insight_engine_adapter.initialize()
        logger.info("Adaptador del BiometricsInsightEngine inicializado y registrado correctamente.")
    except Exception as e:
        logger.error(f"Error al inicializar el adaptador del BiometricsInsightEngine: {e}", exc_info=True)

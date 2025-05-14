"""
Adaptador para el agente BiometricsInsightEngine que utiliza los componentes optimizados.

Este adaptador extiende el agente BiometricsInsightEngine original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from agents.biometrics_insight_engine.agent import BiometricsInsightEngine
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.telemetry import get_telemetry

# Configurar logger
logger = logging.getLogger(__name__)

class BiometricsInsightEngineAdapter(BiometricsInsightEngine, BaseAgentAdapter):
    """
    Adaptador para el agente BiometricsInsightEngine que utiliza los componentes optimizados.
    
    Este adaptador extiende el agente BiometricsInsightEngine original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """
    
    def __init__(self):
        """
        Inicializa el adaptador BiometricsInsightEngine.
        """
        super().__init__()
        self.telemetry = get_telemetry()
        self.agent_name = "biometrics_insight_engine"
        
        # Configuración de clasificación
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
    
    def get_agent_name(self) -> str:
        """Devuelve el nombre del agente."""
        return self.agent_name
    
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
    
    async def _process_query(self, query: str, user_id: str, session_id: str,
                           program_type: str, state: Dict[str, Any], profile: Dict[str, Any],
                           **kwargs) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario.
        
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
            # Registrar telemetría para el inicio del procesamiento
            if self.telemetry:
                with self.telemetry.start_as_current_span(f"{self.__class__.__name__}._process_query") as span:
                    span.set_attribute("user_id", user_id)
                    span.set_attribute("session_id", session_id)
                    span.set_attribute("program_type", program_type)
            
            # Determinar el tipo de consulta basado en el mapeo de intenciones
            query_type = self._determine_query_type(query)
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
            
            # Construir la respuesta
            response = {
                "success": True,
                "output": result.get("response", "No se pudo generar una respuesta"),
                "query_type": query_type,
                "program_type": program_type,
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat(),
                "context": context
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error al procesar consulta en BiometricsInsightEngineAdapter: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    def _determine_query_type(self, query: str) -> str:
        """
        Determina el tipo de consulta basado en el texto.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta identificado
        """
        query_lower = query.lower()
        intent_mapping = self._get_intent_to_query_type_mapping()
        
        for intent, query_type in intent_mapping.items():
            if intent.lower() in query_lower:
                return query_type
        
        # Si no se encuentra un tipo específico, devolver análisis biométrico por defecto
        return "biometric_analysis"
    
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
        analysis = await self._generate_response(
            prompt=f"""
            Como especialista en análisis de datos biométricos, analiza los siguientes datos y proporciona insights 
            personalizados y recomendaciones basadas en los patrones observados.
            
            CONSULTA DEL USUARIO:
            {query}
            
            DATOS BIOMÉTRICOS:
            {biometric_data}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            Proporciona un análisis detallado que incluya:
            1. Interpretación de los datos y patrones observados
            2. Insights clave sobre el estado de salud y bienestar
            3. Recomendaciones personalizadas basadas en los datos y el tipo de programa del usuario
            4. Áreas de mejora y posibles intervenciones específicas
            
            Tu análisis debe ser claro, preciso y basado en evidencia científica.
            """,
            context=context
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
        patterns_analysis = await self._generate_response(
            prompt=f"""
            Como especialista en análisis de datos biométricos, identifica patrones recurrentes en los siguientes datos.
            
            CONSULTA DEL USUARIO:
            {query}
            
            DATOS BIOMÉTRICOS:
            {biometric_data}
            
            PERFIL DEL USUARIO:
            {profile}
            
            Proporciona un análisis detallado que incluya:
            1. Patrones identificados con descripción detallada
            2. Correlaciones entre diferentes métricas
            3. Posibles relaciones causales (si aplica)
            4. Recomendaciones basadas en los patrones identificados
            
            Tu análisis debe ser claro, preciso y basado en evidencia científica.
            """,
            context=context
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
        trends_analysis = await self._generate_response(
            prompt=f"""
            Como especialista en análisis de datos biométricos, analiza las tendencias en los siguientes datos.
            
            CONSULTA DEL USUARIO:
            {query}
            
            DATOS BIOMÉTRICOS:
            {biometric_data}
            
            PERFIL DEL USUARIO:
            {profile}
            
            Proporciona un análisis detallado que incluya:
            1. Tendencias identificadas a lo largo del tiempo
            2. Cambios significativos en métricas clave
            3. Progreso hacia objetivos
            4. Proyecciones futuras
            5. Recomendaciones basadas en tendencias
            
            Tu análisis debe ser claro, preciso y basado en evidencia científica.
            """,
            context=context
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
        visualization_description = await self._generate_response(
            prompt=f"""
            Como especialista en análisis de datos biométricos, describe una visualización para los siguientes datos.
            
            CONSULTA DEL USUARIO:
            {query}
            
            DATOS BIOMÉTRICOS:
            {biometric_data}
            
            PERFIL DEL USUARIO:
            {profile}
            
            Proporciona una descripción detallada que incluya:
            1. Tipo de gráfico recomendado
            2. Métricas a visualizar
            3. Ejes y escalas
            4. Patrones destacados
            5. Interpretación de la visualización
            
            Tu descripción debe ser clara, precisa y útil para entender los datos.
            """,
            context=context
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
            "response": f"Descripción de la visualización: {visualization_description}",
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
        response = await self._generate_response(
            prompt=f"""
            Como especialista en análisis de datos biométricos, responde a la siguiente consulta:
            
            CONSULTA DEL USUARIO:
            {query}
            
            PERFIL DEL USUARIO:
            {profile}
            
            TIPO DE PROGRAMA:
            {program_type}
            
            CONTEXTO PREVIO:
            {context}
            
            Proporciona una respuesta clara, precisa y útil basada en tu experiencia en análisis biométrico.
            """,
            context=context
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
    
    async def _generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Genera una respuesta utilizando el modelo de lenguaje.
        
        Args:
            prompt: Prompt para el modelo
            context: Contexto actual
            
        Returns:
            str: Respuesta generada
        """
        try:
            # En una implementación real, aquí se llamaría al cliente de Vertex AI optimizado
            # Por ahora, simulamos una respuesta
            return f"Respuesta simulada para: {prompt[:50]}..."
        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}", exc_info=True)
            return f"Error al generar respuesta: {str(e)}"

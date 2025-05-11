"""
Adaptador para el agente Biometrics Insight Engine.

Este adaptador permite que el agente Biometrics Insight Engine sea utilizado a través del sistema A2A optimizado,
manteniendo la compatibilidad con la implementación original pero aprovechando las mejoras
de rendimiento y capacidades del nuevo sistema.
"""

import logging
import asyncio
import json
import uuid
import time
from typing import Dict, Any, Optional, List, Union

from core.logging_config import get_logger
from agents.biometrics_insight_engine.agent import BiometricsInsightEngine
from infrastructure.adapters.a2a_adapter import a2a_adapter
from clients.vertex_ai import vertex_ai_client, VertexAIClient
from core.state_manager_adapter import state_manager_adapter
from core.telemetry import telemetry
from app.schemas.a2a import A2ATaskContext

logger = get_logger(__name__)

class BiometricsInsightEngineAdapter:
    """
    Adaptador para el agente Biometrics Insight Engine.
    
    Este adaptador proporciona funcionalidades para:
    - Análisis e interpretación de datos biométricos
    - Reconocimiento de patrones en datos biométricos
    - Identificación de tendencias a largo plazo
    - Visualización de datos biométricos
    """
    
    def __init__(self, a2a_client, state_manager):
        """
        Inicializa el adaptador del Biometrics Insight Engine.
        
        Args:
            a2a_client: Cliente A2A para comunicación con otros agentes
            state_manager: Gestor de estado para persistencia
        """
        self.a2a_client = a2a_client
        self.state_manager = state_manager
        self.logger = get_logger("biometrics_insight_engine_adapter")
        
    @classmethod
    async def create(cls):
        """
        Método de fábrica para crear una instancia del adaptador.
        
        Returns:
            BiometricsInsightEngineAdapter: Una nueva instancia del adaptador
        """
        a2a_client = a2a_adapter
        state_manager = state_manager_adapter
        
        # Inicializar el cliente Vertex AI si no está inicializado
        if not vertex_ai_client.is_initialized:
            await vertex_ai_client.initialize()
            
        return cls(a2a_client, state_manager)
        
    async def analyze_biometric_data(self, user_id: str, biometric_data: Dict[str, Any], query: Optional[str] = None) -> Dict[str, Any]:
        """
        Analiza e interpreta datos biométricos.
        
        Args:
            user_id: ID del usuario
            biometric_data: Datos biométricos a analizar
            query: Consulta específica sobre los datos (opcional)
            
        Returns:
            Dict[str, Any]: Análisis de los datos biométricos
        """
        try:
            with telemetry.start_span("biometrics_insight_engine.analyze_biometric_data"):
                # Construir el prompt para el análisis
                prompt = self._build_biometric_analysis_prompt(biometric_data, query)
                
                # Generar análisis
                response = await vertex_ai_client.generate_content(prompt=prompt)
                
                # Procesar y estructurar la respuesta
                analysis = self._parse_biometric_analysis(response["text"])
                
                # Guardar el análisis en el estado del usuario
                await self._save_analysis_to_state(user_id, analysis)
                
                # Telemetría
                telemetry.record_event("biometrics_insight_engine", "analysis_completed", {
                    "user_id": user_id,
                    "metrics_analyzed": len(biometric_data.keys()),
                    "response_time_ms": telemetry.get_current_span().duration_ms
                })
                
                return analysis
        except Exception as e:
            self.logger.error(f"Error analyzing biometric data: {str(e)}")
            telemetry.record_error("biometrics_insight_engine", "analysis_failed", {
                "error": str(e),
                "user_id": user_id
            })
            raise
            
    async def identify_patterns(self, user_id: str, biometric_data: Dict[str, Any], time_range: Optional[str] = None) -> Dict[str, Any]:
        """
        Identifica patrones en datos biométricos.
        
        Args:
            user_id: ID del usuario
            biometric_data: Datos biométricos a analizar
            time_range: Rango de tiempo para el análisis (opcional)
            
        Returns:
            Dict[str, Any]: Patrones identificados
        """
        try:
            with telemetry.start_span("biometrics_insight_engine.identify_patterns"):
                # Construir el prompt para la identificación de patrones
                prompt = self._build_pattern_recognition_prompt(biometric_data, time_range)
                
                # Generar identificación de patrones
                response = await vertex_ai_client.generate_content(prompt=prompt)
                
                # Procesar y estructurar la respuesta
                patterns = self._parse_pattern_recognition(response["text"])
                
                # Guardar los patrones en el estado del usuario
                await self._save_patterns_to_state(user_id, patterns)
                
                # Telemetría
                telemetry.record_event("biometrics_insight_engine", "patterns_identified", {
                    "user_id": user_id,
                    "patterns_count": len(patterns.get("identified_patterns", [])),
                    "response_time_ms": telemetry.get_current_span().duration_ms
                })
                
                return patterns
        except Exception as e:
            self.logger.error(f"Error identifying patterns: {str(e)}")
            telemetry.record_error("biometrics_insight_engine", "pattern_identification_failed", {
                "error": str(e),
                "user_id": user_id
            })
            raise
            
    async def analyze_trends(self, user_id: str, biometric_data: Dict[str, Any], metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analiza tendencias a largo plazo en datos biométricos.
        
        Args:
            user_id: ID del usuario
            biometric_data: Datos biométricos a analizar
            metrics: Lista de métricas específicas a analizar (opcional)
            
        Returns:
            Dict[str, Any]: Tendencias identificadas
        """
        try:
            with telemetry.start_span("biometrics_insight_engine.analyze_trends"):
                # Construir el prompt para el análisis de tendencias
                prompt = self._build_trend_analysis_prompt(biometric_data, metrics)
                
                # Generar análisis de tendencias
                response = await vertex_ai_client.generate_content(prompt=prompt)
                
                # Procesar y estructurar la respuesta
                trends = self._parse_trend_analysis(response["text"])
                
                # Guardar las tendencias en el estado del usuario
                await self._save_trends_to_state(user_id, trends)
                
                # Telemetría
                telemetry.record_event("biometrics_insight_engine", "trends_analyzed", {
                    "user_id": user_id,
                    "metrics_analyzed": len(metrics) if metrics else len(biometric_data.keys()),
                    "response_time_ms": telemetry.get_current_span().duration_ms
                })
                
                return trends
        except Exception as e:
            self.logger.error(f"Error analyzing trends: {str(e)}")
            telemetry.record_error("biometrics_insight_engine", "trend_analysis_failed", {
                "error": str(e),
                "user_id": user_id
            })
            raise
            
    async def generate_visualization(self, user_id: str, biometric_data: Dict[str, Any], visualization_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Genera una visualización de datos biométricos.
        
        Args:
            user_id: ID del usuario
            biometric_data: Datos biométricos a visualizar
            visualization_type: Tipo de visualización (opcional)
            
        Returns:
            Dict[str, Any]: Descripción de la visualización
        """
        try:
            with telemetry.start_span("biometrics_insight_engine.generate_visualization"):
                # Construir el prompt para la visualización
                prompt = self._build_visualization_prompt(biometric_data, visualization_type)
                
                # Generar visualización
                response = await vertex_ai_client.generate_content(prompt=prompt)
                
                # Procesar y estructurar la respuesta
                visualization = self._parse_visualization(response["text"])
                
                # Guardar la visualización en el estado del usuario
                await self._save_visualization_to_state(user_id, visualization)
                
                # Telemetría
                telemetry.record_event("biometrics_insight_engine", "visualization_generated", {
                    "user_id": user_id,
                    "visualization_type": visualization.get("chart_type", "unknown"),
                    "response_time_ms": telemetry.get_current_span().duration_ms
                })
                
                return visualization
        except Exception as e:
            self.logger.error(f"Error generating visualization: {str(e)}")
            telemetry.record_error("biometrics_insight_engine", "visualization_failed", {
                "error": str(e),
                "user_id": user_id
            })
            raise
            
    async def _consult_other_agent(self, agent_name: str, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta a otro agente para obtener información adicional.
        
        Args:
            agent_name: Nombre del agente a consultar
            query: Consulta para el agente
            context: Contexto adicional
            
        Returns:
            Dict[str, Any]: Respuesta del agente consultado
        """
        try:
            with telemetry.start_span(f"biometrics_insight_engine.consult_{agent_name}"):
                # Crear el contexto de la tarea
                task_context_data = A2ATaskContext(
                    session_id=context.get("session_id") if context else None, 
                    user_id=context.get("user_id") if context else None, 
                    additional_context=context if context else {}
                )
                
                # Llamar al agente utilizando el adaptador A2A
                response = await self.a2a_client.call_agent(
                    agent_id=agent_name,
                    user_input=query,
                    context=task_context_data
                )
                
                return response
        except Exception as e:
            self.logger.error(f"Error consulting agent {agent_name}: {str(e)}")
            telemetry.record_error("biometrics_insight_engine", "agent_consultation_failed", {
                "agent": agent_name,
                "error": str(e)
            })
            # Implementar fallback
            return {"status": "error", "message": f"Failed to consult {agent_name}"}
    
    async def _save_analysis_to_state(self, user_id: str, analysis: Dict[str, Any]) -> None:
        """
        Guarda el análisis en el estado del usuario.
        
        Args:
            user_id: ID del usuario
            analysis: Análisis a guardar
        """
        try:
            # Crear clave para el estado
            state_key = f"biometrics_analysis_{user_id}"
            
            # Cargar estado actual
            current_state = await self.state_manager.load_state(state_key) or {"analyses": []}
            
            # Añadir el nuevo análisis
            analysis["timestamp"] = time.time()
            analysis["id"] = str(uuid.uuid4())
            current_state["analyses"].append(analysis)
            
            # Limitar a los 10 análisis más recientes
            if len(current_state["analyses"]) > 10:
                current_state["analyses"] = current_state["analyses"][-10:]
            
            # Guardar estado actualizado
            await self.state_manager.save_state(state_key, current_state)
        except Exception as e:
            self.logger.error(f"Error saving analysis to state: {str(e)}")
    
    async def _save_patterns_to_state(self, user_id: str, patterns: Dict[str, Any]) -> None:
        """
        Guarda los patrones en el estado del usuario.
        
        Args:
            user_id: ID del usuario
            patterns: Patrones a guardar
        """
        try:
            # Crear clave para el estado
            state_key = f"biometrics_patterns_{user_id}"
            
            # Cargar estado actual
            current_state = await self.state_manager.load_state(state_key) or {"patterns": []}
            
            # Añadir los nuevos patrones
            patterns["timestamp"] = time.time()
            patterns["id"] = str(uuid.uuid4())
            current_state["patterns"].append(patterns)
            
            # Limitar a los 10 patrones más recientes
            if len(current_state["patterns"]) > 10:
                current_state["patterns"] = current_state["patterns"][-10:]
            
            # Guardar estado actualizado
            await self.state_manager.save_state(state_key, current_state)
        except Exception as e:
            self.logger.error(f"Error saving patterns to state: {str(e)}")
    
    async def _save_trends_to_state(self, user_id: str, trends: Dict[str, Any]) -> None:
        """
        Guarda las tendencias en el estado del usuario.
        
        Args:
            user_id: ID del usuario
            trends: Tendencias a guardar
        """
        try:
            # Crear clave para el estado
            state_key = f"biometrics_trends_{user_id}"
            
            # Cargar estado actual
            current_state = await self.state_manager.load_state(state_key) or {"trends": []}
            
            # Añadir las nuevas tendencias
            trends["timestamp"] = time.time()
            trends["id"] = str(uuid.uuid4())
            current_state["trends"].append(trends)
            
            # Limitar a los 10 tendencias más recientes
            if len(current_state["trends"]) > 10:
                current_state["trends"] = current_state["trends"][-10:]
            
            # Guardar estado actualizado
            await self.state_manager.save_state(state_key, current_state)
        except Exception as e:
            self.logger.error(f"Error saving trends to state: {str(e)}")
    
    async def _save_visualization_to_state(self, user_id: str, visualization: Dict[str, Any]) -> None:
        """
        Guarda la visualización en el estado del usuario.
        
        Args:
            user_id: ID del usuario
            visualization: Visualización a guardar
        """
        try:
            # Crear clave para el estado
            state_key = f"biometrics_visualizations_{user_id}"
            
            # Cargar estado actual
            current_state = await self.state_manager.load_state(state_key) or {"visualizations": []}
            
            # Añadir la nueva visualización
            visualization["timestamp"] = time.time()
            visualization["id"] = str(uuid.uuid4())
            current_state["visualizations"].append(visualization)
            
            # Limitar a las 10 visualizaciones más recientes
            if len(current_state["visualizations"]) > 10:
                current_state["visualizations"] = current_state["visualizations"][-10:]
            
            # Guardar estado actualizado
            await self.state_manager.save_state(state_key, current_state)
        except Exception as e:
            self.logger.error(f"Error saving visualization to state: {str(e)}")
    
    def _build_biometric_analysis_prompt(self, biometric_data: Dict[str, Any], query: Optional[str] = None) -> str:
        """
        Construye el prompt para el análisis biométrico.
        
        Args:
            biometric_data: Datos biométricos a analizar
            query: Consulta específica sobre los datos (opcional)
            
        Returns:
            str: Prompt para el análisis
        """
        prompt = f"""
        Eres un especialista en análisis e interpretación de datos biométricos.
        
        Analiza los siguientes datos biométricos:
        
        {json.dumps(biometric_data, indent=2)}
        
        """
        
        if query:
            prompt += f"""
            Consulta específica: "{query}"
            
            """
        
        prompt += """
        El análisis debe incluir:
        1. Interpretación de los datos principales
        2. Insights clave identificados
        3. Patrones relevantes
        4. Recomendaciones personalizadas
        5. Áreas de mejora
        
        Devuelve el análisis en formato JSON estructurado con las siguientes claves:
        - interpretation: interpretación general de los datos
        - main_insights: lista de insights clave
        - patterns: lista de patrones identificados
        - recommendations: lista de recomendaciones
        - areas_for_improvement: lista de áreas de mejora
        """
        
        return prompt
        
    def _parse_biometric_analysis(self, response: str) -> Dict[str, Any]:
        """
        Procesa y estructura la respuesta del análisis biométrico.
        
        Args:
            response: Respuesta del modelo
            
        Returns:
            Dict[str, Any]: Análisis estructurado
        """
        try:
            # Intentar parsear la respuesta como JSON
            if isinstance(response, dict):
                return response
            
            # Buscar el bloque JSON en la respuesta
            import re
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Intentar parsear toda la respuesta como JSON
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error parsing biometric analysis: {str(e)}")
            # En caso de error, devolver un diccionario básico
            return {
                "interpretation": "No se pudo generar una interpretación completa debido a un error",
                "main_insights": ["Error en el procesamiento de datos biométricos"],
                "patterns": ["No se pudieron identificar patrones"],
                "recommendations": ["Consulta a un profesional de la salud"],
                "areas_for_improvement": ["No se pudieron identificar áreas de mejora"]
            }
    
    def _build_pattern_recognition_prompt(self, biometric_data: Dict[str, Any], time_range: Optional[str] = None) -> str:
        """
        Construye el prompt para la identificación de patrones.
        
        Args:
            biometric_data: Datos biométricos a analizar
            time_range: Rango de tiempo para el análisis (opcional)
            
        Returns:
            str: Prompt para la identificación de patrones
        """
        prompt = f"""
        Eres un especialista en análisis e interpretación de datos biométricos.
        
        Identifica patrones recurrentes en los siguientes datos biométricos:
        
        {json.dumps(biometric_data, indent=2)}
        
        """
        
        if time_range:
            prompt += f"""
            Rango de tiempo a considerar: {time_range}
            
            """
        
        prompt += """
        El análisis debe incluir:
        1. Patrones identificados con descripción detallada
        2. Correlaciones entre diferentes métricas
        3. Posibles relaciones causales (si aplica)
        4. Recomendaciones basadas en los patrones identificados
        
        Devuelve el análisis en formato JSON estructurado con las siguientes claves:
        - identified_patterns: lista de patrones identificados (cada uno con name y description)
        - correlations: lista de correlaciones (cada una con metrics, correlation_type y strength)
        - causality_analysis: análisis de causalidad (con possible_causes)
        - recommendations: lista de recomendaciones
        """
        
        return prompt
        
    def _parse_pattern_recognition(self, response: str) -> Dict[str, Any]:
        """
        Procesa y estructura la respuesta de la identificación de patrones.
        
        Args:
            response: Respuesta del modelo
            
        Returns:
            Dict[str, Any]: Patrones estructurados
        """
        try:
            # Intentar parsear la respuesta como JSON
            if isinstance(response, dict):
                return response
            
            # Buscar el bloque JSON en la respuesta
            import re
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Intentar parsear toda la respuesta como JSON
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error parsing pattern recognition: {str(e)}")
            # En caso de error, devolver un diccionario básico
            return {
                "identified_patterns": [
                    {"name": "Error en el análisis", "description": "No se pudieron identificar patrones"}
                ],
                "correlations": [
                    {"metrics": ["N/A", "N/A"], "correlation_type": "N/A", "strength": "N/A"}
                ],
                "causality_analysis": {"possible_causes": ["Error en el análisis"]},
                "recommendations": ["Consulta a un profesional de la salud"]
            }
    
    def _build_trend_analysis_prompt(self, biometric_data: Dict[str, Any], metrics: Optional[List[str]] = None) -> str:
        """
        Construye el prompt para el análisis de tendencias.
        
        Args:
            biometric_data: Datos biométricos a analizar
            metrics: Lista de métricas específicas a analizar (opcional)
            
        Returns:
            str: Prompt para el análisis de tendencias
        """
        prompt = f"""
        Eres un especialista en análisis e interpretación de datos biométricos.
        
        Analiza las tendencias en los siguientes datos biométricos:
        
        {json.dumps(biometric_data, indent=2)}
        
        """
        
        if metrics:
            prompt += f"""
            Métricas específicas a analizar: {', '.join(metrics)}
            
            """
        
        prompt += """
        El análisis debe incluir:
        1. Tendencias identificadas a lo largo del tiempo
        2. Cambios significativos en métricas clave
        3. Progreso hacia objetivos
        4. Proyecciones futuras
        5. Recomendaciones basadas en tendencias
        
        Devuelve el análisis en formato JSON estructurado con las siguientes claves:
        - trends: lista de tendencias identificadas
        - significant_changes: lista de cambios significativos
        - progress: descripción del progreso
        - projections: lista de proyecciones futuras
        - recommendations: lista de recomendaciones
        """
        
        return prompt
        
    def _parse_trend_analysis(self, response: str) -> Dict[str, Any]:
        """
        Procesa y estructura la respuesta del análisis de tendencias.
        
        Args:
            response: Respuesta del modelo
            
        Returns:
            Dict[str, Any]: Tendencias estructuradas
        """
        try:
            # Intentar parsear la respuesta como JSON
            if isinstance(response, dict):
                return response
            
            # Buscar el bloque JSON en la respuesta
            import re
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Intentar parsear toda la respuesta como JSON
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error parsing trend analysis: {str(e)}")
            # En caso de error, devolver un diccionario básico
            return {
                "trends": ["Error en el análisis de tendencias"],
                "significant_changes": [f"Error: {str(e)}"],
                "progress": "No disponible debido a un error",
                "projections": ["No disponible debido a un error"],
                "recommendations": ["Consulta a un profesional de la salud"]
            }
    
    def _build_visualization_prompt(self, biometric_data: Dict[str, Any], visualization_type: Optional[str] = None) -> str:
        """
        Construye el prompt para la visualización.
        
        Args:
            biometric_data: Datos biométricos a visualizar
            visualization_type: Tipo de visualización (opcional)
            
        Returns:
            str: Prompt para la visualización
        """
        prompt = f"""
        Eres un especialista en análisis e interpretación de datos biométricos.
        
        Genera una descripción para una visualización de los siguientes datos biométricos:
        
        {json.dumps(biometric_data, indent=2)}
        
        """
        
        if visualization_type:
            prompt += f"""
            Tipo de visualización solicitada: {visualization_type}
            
            """
        
        prompt += """
        La visualización debe incluir:
        1. Tipo de gráfico recomendado
        2. Métricas a visualizar
        3. Ejes y escalas
        4. Patrones destacados
        5. Interpretación de la visualización
        
        Devuelve la descripción en formato JSON estructurado con las siguientes claves:
        - chart_type: tipo de gráfico recomendado
        - metrics: lista de métricas a visualizar
        - axes: objeto con ejes x e y
        - highlighted_patterns: lista de patrones destacados
        - interpretation: interpretación de la visualización
        """
        
        return prompt
        
    def _parse_visualization(self, response: str) -> Dict[str, Any]:
        """
        Procesa y estructura la respuesta de la visualización.
        
        Args:
            response: Respuesta del modelo
            
        Returns:
            Dict[str, Any]: Visualización estructurada
        """
        try:
            # Intentar parsear la respuesta como JSON
            if isinstance(response, dict):
                return response
            
            # Buscar el bloque JSON en la respuesta
            import re
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Intentar parsear toda la respuesta como JSON
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error parsing visualization: {str(e)}")
            # En caso de error, devolver un diccionario básico
            return {
                "chart_type": "Error",
                "metrics": ["No disponible debido a un error"],
                "axes": {"x": "No disponible", "y": "No disponible"},
                "highlighted_patterns": [f"Error: {str(e)}"],
                "interpretation": "No se pudo generar una visualización debido a un error"
            }

# Crear una instancia del adaptador
biometrics_insight_engine_adapter = None

# Función para inicializar el adaptador
async def initialize_biometrics_insight_engine_adapter():
    """
    Inicializa el adaptador del Biometrics Insight Engine.
    
    Returns:
        BiometricsInsightEngineAdapter: Instancia del adaptador
    """
    global biometrics_insight_engine_adapter
    
    try:
        biometrics_insight_engine_adapter = await BiometricsInsightEngineAdapter.create()
        logger.info("Adaptador del Biometrics Insight Engine inicializado correctamente.")
        return biometrics_insight_engine_adapter
    except Exception as e:
        logger.error(f"Error al inicializar el adaptador del Biometrics Insight Engine: {e}", exc_info=True)
        raise

"""
Adaptador para el agente Recovery Corrective.
Este adaptador integra el agente con el sistema A2A optimizado.
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Union

from infrastructure.adapters.a2a_adapter import A2AAdapter
from clients.vertex_ai import vertex_ai_client, VertexAIClient
from core.telemetry import telemetry

logger = logging.getLogger("recovery_corrective_adapter")

class RecoveryCorrectiveAdapter:
    """
    Adaptador para el agente Recovery Corrective que integra con el sistema A2A optimizado.
    
    Este adaptador proporciona funcionalidades para:
    - Analizar necesidades de recuperación
    - Generar planes de recuperación personalizados
    - Ajustar programas de entrenamiento
    - Proporcionar orientación de recuperación en tiempo real
    """
    
    def __init__(self, a2a_client: A2AAdapter):
        """
        Inicializa el adaptador de Recovery Corrective.
        
        Args:
            a2a_client: Cliente A2A para comunicación con otros agentes
        """
        self.a2a_client = a2a_client
        self.logger = logging.getLogger("recovery_corrective_adapter")
        
    @classmethod
    async def create(cls):
        """
        Método de fábrica para crear una instancia del adaptador.
        
        Returns:
            RecoveryCorrectiveAdapter: Una nueva instancia del adaptador
        """
        a2a_client = await A2AAdapter.create()
        
        # Inicializar el cliente Vertex AI si no está inicializado
        if not vertex_ai_client.is_initialized:
            await vertex_ai_client.initialize()
            
        return cls(a2a_client)
        
    async def analyze_recovery_needs(self, user_data: Dict[str, Any], training_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analiza las necesidades de recuperación basadas en datos del usuario y su historial de entrenamiento.
        
        Args:
            user_data: Datos del usuario incluyendo métricas biométricas
            training_history: Historial de entrenamientos recientes
            
        Returns:
            Dict[str, Any]: Análisis de necesidades de recuperación
        """
        try:
            with telemetry.start_span("recovery_corrective.analyze_recovery_needs"):
                # Implementación optimizada
                prompt = self._build_recovery_analysis_prompt(user_data, training_history)
                response = await vertex_ai_client.generate_content(prompt=prompt)
                
                # Procesamiento y estructuración de la respuesta
                analysis = self._parse_recovery_analysis(response["text"])
                
                # Telemetría
                telemetry.record_event("recovery_corrective", "analysis_completed", {
                    "user_id": user_data.get("user_id"),
                    "analysis_factors": len(analysis.get("factors", [])),
                    "response_time_ms": telemetry.get_current_span().duration_ms
                })
                
                return analysis
        except Exception as e:
            self.logger.error(f"Error analyzing recovery needs: {str(e)}")
            telemetry.record_error("recovery_corrective", "analysis_failed", {
                "error": str(e)
            })
            raise
            
    async def generate_recovery_plan(self, recovery_needs: Dict[str, Any], user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un plan de recuperación personalizado.
        
        Args:
            recovery_needs: Análisis de necesidades de recuperación
            user_preferences: Preferencias del usuario
            
        Returns:
            Dict[str, Any]: Plan de recuperación estructurado
        """
        try:
            with telemetry.start_span("recovery_corrective.generate_recovery_plan"):
                # Consultar al agente de nutrición para recomendaciones
                nutrition_recommendations = await self._consult_other_agent(
                    "precision_nutrition_architect",
                    f"Necesito recomendaciones nutricionales para recuperación basadas en: {recovery_needs}"
                )
                
                # Consultar al agente de entrenamiento para recomendaciones
                training_recommendations = await self._consult_other_agent(
                    "elite_training_strategist",
                    f"Necesito recomendaciones de entrenamiento para recuperación basadas en: {recovery_needs}"
                )
                
                # Construir prompt para el plan de recuperación
                prompt = self._build_recovery_plan_prompt(
                    recovery_needs, 
                    user_preferences,
                    nutrition_recommendations,
                    training_recommendations
                )
                
                # Generar plan de recuperación
                response = await vertex_ai_client.generate_content(prompt=prompt)
                
                # Procesar y estructurar la respuesta
                plan = self._parse_recovery_plan(response["text"])
                
                # Telemetría
                telemetry.record_event("recovery_corrective", "plan_generated", {
                    "user_id": recovery_needs.get("user_id"),
                    "plan_components": len(plan.get("components", [])),
                    "response_time_ms": telemetry.get_current_span().duration_ms
                })
                
                return plan
        except Exception as e:
            self.logger.error(f"Error generating recovery plan: {str(e)}")
            telemetry.record_error("recovery_corrective", "plan_generation_failed", {
                "error": str(e)
            })
            raise
        
    async def adjust_training_program(self, current_program: Dict[str, Any], recovery_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ajusta el programa de entrenamiento actual basado en el plan de recuperación.
        
        Args:
            current_program: Programa de entrenamiento actual
            recovery_plan: Plan de recuperación
            
        Returns:
            Dict[str, Any]: Programa de entrenamiento ajustado
        """
        try:
            with telemetry.start_span("recovery_corrective.adjust_training_program"):
                # Consultar al agente de entrenamiento para ajustes
                training_adjustments = await self._consult_other_agent(
                    "elite_training_strategist",
                    f"Necesito ajustar este programa de entrenamiento basado en este plan de recuperación: {recovery_plan}"
                )
                
                # Construir prompt para ajustar el programa
                prompt = self._build_training_adjustment_prompt(
                    current_program,
                    recovery_plan,
                    training_adjustments
                )
                
                # Generar programa ajustado
                response = await vertex_ai_client.generate_content(prompt=prompt)
                
                # Procesar y estructurar la respuesta
                adjusted_program = self._parse_adjusted_program(response["text"])
                
                # Telemetría
                telemetry.record_event("recovery_corrective", "program_adjusted", {
                    "user_id": current_program.get("user_id"),
                    "adjustment_level": adjusted_program.get("adjustment_level"),
                    "response_time_ms": telemetry.get_current_span().duration_ms
                })
                
                return adjusted_program
        except Exception as e:
            self.logger.error(f"Error adjusting training program: {str(e)}")
            telemetry.record_error("recovery_corrective", "program_adjustment_failed", {
                "error": str(e)
            })
            raise
        
    async def provide_recovery_guidance(self, user_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Proporciona orientación de recuperación en tiempo real.
        
        Args:
            user_id: ID del usuario
            context: Contexto adicional
            
        Returns:
            Dict[str, Any]: Orientación de recuperación
        """
        try:
            with telemetry.start_span("recovery_corrective.provide_recovery_guidance"):
                # Obtener datos del usuario y su historial reciente
                user_data = await self._get_user_data(user_id)
                training_history = await self._get_training_history(user_id)
                
                # Analizar necesidades de recuperación
                recovery_needs = await self.analyze_recovery_needs(user_data, training_history)
                
                # Construir prompt para orientación
                prompt = self._build_guidance_prompt(user_id, recovery_needs, context)
                
                # Generar orientación
                response = await vertex_ai_client.generate_content(prompt=prompt)
                
                # Procesar y estructurar la respuesta
                guidance = self._parse_guidance(response["text"])
                
                # Telemetría
                telemetry.record_event("recovery_corrective", "guidance_provided", {
                    "user_id": user_id,
                    "guidance_type": guidance.get("type"),
                    "response_time_ms": telemetry.get_current_span().duration_ms
                })
                
                return guidance
        except Exception as e:
            self.logger.error(f"Error providing recovery guidance: {str(e)}")
            telemetry.record_error("recovery_corrective", "guidance_failed", {
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
            with telemetry.start_span(f"recovery_corrective.consult_{agent_name}"):
                response = await self.a2a_client.call_agent(agent_name, query, context)
                return response
        except Exception as e:
            self.logger.error(f"Error consulting agent {agent_name}: {str(e)}")
            telemetry.record_error("recovery_corrective", "agent_consultation_failed", {
                "agent": agent_name,
                "error": str(e)
            })
            # Implementar fallback
            return {"status": "error", "message": f"Failed to consult {agent_name}"}
    
    async def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Obtiene los datos del usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict[str, Any]: Datos del usuario
        """
        # Implementación simulada - en producción, esto obtendría datos de una base de datos
        return {
            "user_id": user_id,
            "age": 30,
            "weight": 75,
            "height": 180,
            "fitness_level": "intermediate",
            "recovery_profile": "normal"
        }
    
    async def _get_training_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de entrenamiento del usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            List[Dict[str, Any]]: Historial de entrenamiento
        """
        # Implementación simulada - en producción, esto obtendría datos de una base de datos
        return [
            {"date": "2025-10-01", "type": "strength", "intensity": "high", "duration": 60},
            {"date": "2025-10-03", "type": "cardio", "intensity": "medium", "duration": 45},
            {"date": "2025-10-05", "type": "flexibility", "intensity": "low", "duration": 30}
        ]
            
    def _build_recovery_analysis_prompt(self, user_data: Dict[str, Any], training_history: List[Dict[str, Any]]) -> str:
        """
        Construye el prompt para el análisis de recuperación.
        
        Args:
            user_data: Datos del usuario
            training_history: Historial de entrenamiento
            
        Returns:
            str: Prompt para el análisis
        """
        prompt = f"""
        Analiza las necesidades de recuperación para este usuario basado en sus datos y su historial de entrenamiento reciente.
        
        Datos del usuario:
        {user_data}
        
        Historial de entrenamiento reciente:
        {training_history}
        
        Proporciona un análisis detallado que incluya:
        1. Factores de riesgo de sobreentrenamiento
        2. Áreas que necesitan recuperación prioritaria
        3. Recomendaciones generales de recuperación
        4. Nivel de fatiga estimado
        5. Tiempo de recuperación recomendado
        
        Estructura tu respuesta en formato JSON con las siguientes claves:
        - factors: lista de factores de riesgo
        - priority_areas: lista de áreas prioritarias
        - recommendations: lista de recomendaciones
        - fatigue_level: nivel de fatiga (bajo, medio, alto)
        - recovery_time: tiempo de recuperación en días
        """
        return prompt
        
    def _parse_recovery_analysis(self, response: str) -> Dict[str, Any]:
        """
        Procesa y estructura la respuesta del modelo.
        
        Args:
            response: Respuesta del modelo
            
        Returns:
            Dict[str, Any]: Análisis estructurado
        """
        # En una implementación real, esto analizaría el JSON de la respuesta
        # Para esta implementación básica, devolvemos un diccionario simulado
        return {
            "factors": ["alta intensidad reciente", "volumen acumulado", "descanso insuficiente"],
            "priority_areas": ["sistema nervioso central", "músculos de la espalda baja"],
            "recommendations": ["hidratación aumentada", "sueño de calidad", "nutrición antiinflamatoria"],
            "fatigue_level": "medio",
            "recovery_time": 2
        }
        
    def _build_recovery_plan_prompt(self, recovery_needs: Dict[str, Any], user_preferences: Dict[str, Any], 
                                   nutrition_recommendations: Dict[str, Any], training_recommendations: Dict[str, Any]) -> str:
        """
        Construye el prompt para el plan de recuperación.
        
        Args:
            recovery_needs: Necesidades de recuperación
            user_preferences: Preferencias del usuario
            nutrition_recommendations: Recomendaciones nutricionales
            training_recommendations: Recomendaciones de entrenamiento
            
        Returns:
            str: Prompt para el plan
        """
        prompt = f"""
        Eres un especialista en recuperación y corrección para atletas y personas activas.
        
        Necesito que generes un plan de recuperación personalizado basado en la siguiente información:
        
        NECESIDADES DE RECUPERACIÓN:
        {json.dumps(recovery_needs, indent=2)}
        
        PREFERENCIAS DEL USUARIO:
        {json.dumps(user_preferences, indent=2)}
        
        RECOMENDACIONES NUTRICIONALES:
        {json.dumps(nutrition_recommendations, indent=2)}
        
        RECOMENDACIONES DE ENTRENAMIENTO:
        {json.dumps(training_recommendations, indent=2)}
        
        El plan debe incluir:
        1. Componentes principales (nutrición, descanso, movilidad, etc.)
        2. Duración recomendada en días
        3. Intensidad general del plan
        4. Actividades específicas día por día
        5. Métricas para seguimiento del progreso
        
        Devuelve el plan en formato JSON estructurado con las siguientes claves:
        - components: lista de componentes principales
        - duration_days: duración en días
        - intensity: intensidad general (baja, moderada, alta)
        - daily_activities: objeto con actividades por día
        - progress_metrics: métricas para seguimiento
        """
        
        return prompt
        
    def _parse_recovery_plan(self, response: str) -> Dict[str, Any]:
        """
        Procesa y estructura la respuesta del plan de recuperación.
        
        Args:
            response: Respuesta del modelo
            
        Returns:
            Dict[str, Any]: Plan estructurado
        """
        # Implementación simulada
        return {
            "components": ["nutrición", "descanso", "movilidad", "recuperación activa"],
            "duration_days": 3,
            "intensity": "moderada"
        }
        
    def _build_training_adjustment_prompt(self, current_program: Dict[str, Any], recovery_plan: Dict[str, Any], 
                                         training_adjustments: Dict[str, Any]) -> str:
        """
        Construye el prompt para ajustar el programa de entrenamiento.
        
        Args:
            current_program: Programa actual
            recovery_plan: Plan de recuperación
            training_adjustments: Ajustes recomendados
            
        Returns:
            str: Prompt para ajustes
        """
        prompt = f"""
        Eres un especialista en recuperación y corrección para atletas y personas activas.
        
        Necesito que ajustes el siguiente programa de entrenamiento basado en un plan de recuperación:
        
        PROGRAMA ACTUAL:
        {json.dumps(current_program, indent=2)}
        
        PLAN DE RECUPERACIÓN:
        {json.dumps(recovery_plan, indent=2)}
        
        AJUSTES RECOMENDADOS:
        {json.dumps(training_adjustments, indent=2)}
        
        El programa ajustado debe:
        1. Mantener los objetivos principales del programa original
        2. Incorporar períodos de recuperación adecuados
        3. Ajustar la intensidad y volumen según sea necesario
        4. Incluir ejercicios específicos para áreas que necesitan recuperación
        5. Proporcionar alternativas para ejercicios de alto impacto
        
        Devuelve el programa ajustado en formato JSON estructurado con las siguientes claves:
        - adjustment_level: nivel de ajuste (mínimo, moderado, significativo)
        - modified_sessions: número de sesiones modificadas
        - intensity_reduction: porcentaje de reducción de intensidad
        - volume_reduction: porcentaje de reducción de volumen
        - recovery_additions: elementos de recuperación añadidos
        - exercise_substitutions: ejercicios sustituidos
        """
        
        return prompt
        
    def _parse_adjusted_program(self, response: str) -> Dict[str, Any]:
        """
        Procesa y estructura la respuesta del programa ajustado.
        
        Args:
            response: Respuesta del modelo
            
        Returns:
            Dict[str, Any]: Programa ajustado
        """
        # Implementación simulada
        return {
            "adjustment_level": "moderado",
            "modified_sessions": 3,
            "intensity_reduction": "20%"
        }
        
    def _build_guidance_prompt(self, user_id: str, recovery_needs: Dict[str, Any], context: Optional[Dict[str, Any]]) -> str:
        """
        Construye el prompt para orientación de recuperación.
        
        Args:
            user_id: ID del usuario
            recovery_needs: Necesidades de recuperación
            context: Contexto adicional
            
        Returns:
            str: Prompt para orientación
        """
        prompt = f"""
        Eres un especialista en recuperación y corrección para atletas y personas activas.
        
        Proporciona orientación de recuperación en tiempo real para el usuario con ID: {user_id}
        
        NECESIDADES DE RECUPERACIÓN:
        {json.dumps(recovery_needs, indent=2)}
        """
        
        if context:
            prompt += f"""
            
            CONTEXTO ADICIONAL:
            {json.dumps(context, indent=2)}
            """
        
        prompt += """
        
        La orientación debe incluir:
        1. Acciones inmediatas que el usuario puede tomar
        2. Nivel de urgencia de la recuperación
        3. Técnicas específicas para aliviar la fatiga o dolor
        4. Recomendaciones sobre cuándo reanudar la actividad normal
        5. Señales de advertencia que indiquen la necesidad de atención profesional
        
        Devuelve la orientación en formato JSON estructurado con las siguientes claves:
        - type: tipo de orientación (inmediata, a corto plazo, a largo plazo)
        - actions: lista de acciones recomendadas
        - urgency: nivel de urgencia (baja, media, alta)
        - relief_techniques: técnicas para alivio
        - resume_activity_timeline: cuándo reanudar actividad
        - warning_signs: señales de advertencia
        """
        
        return prompt
        
    def _parse_guidance(self, response: str) -> Dict[str, Any]:
        """
        Procesa y estructura la respuesta de orientación.
        
        Args:
            response: Respuesta del modelo
            
        Returns:
            Dict[str, Any]: Orientación estructurada
        """
        # Implementación simulada
        return {
            "type": "inmediata",
            "actions": ["hidratación", "estiramiento", "descanso"],
            "urgency": "media"
        }

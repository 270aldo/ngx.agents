"""
Agente especializado en análisis e interpretación de datos biométricos.

Este agente procesa datos biométricos como HRV, sueño, glucosa, 
composición corporal, etc., para proporcionar insights personalizados
y recomendaciones basadas en patrones individuales.
"""
import logging
import uuid
import time
from typing import Dict, Any, Optional, List
import json

from adk.toolkit import Toolkit
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from agents.base.a2a_agent import A2AAgent
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager

# Configurar logging
logger = logging.getLogger(__name__)

class BiometricsInsightEngine(A2AAgent):
    """
    Agente especializado en análisis e interpretación de datos biométricos.
    
    Este agente procesa datos biométricos como HRV, sueño, glucosa, 
    composición corporal, etc., para proporcionar insights personalizados
    y recomendaciones basadas en patrones individuales.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None):
        """
        Inicializa el agente BiometricsInsightEngine.
        
        Args:
            toolkit: Toolkit con herramientas disponibles para el agente
            a2a_server_url: URL del servidor A2A (opcional)
        """
        # Definir capacidades y habilidades
        capabilities = [
            "biometric_analysis", 
            "pattern_recognition", 
            "trend_identification", 
            "personalized_insights",
            "data_visualization"
        ]
        
        skills = [
            {
                "name": "biometric_analysis",
                "description": "Análisis detallado de datos biométricos como HRV, sueño, glucosa, etc."
            },
            {
                "name": "pattern_recognition",
                "description": "Identificación de patrones en datos biométricos a lo largo del tiempo"
            },
            {
                "name": "trend_identification",
                "description": "Reconocimiento de tendencias y cambios significativos en métricas"
            },
            {
                "name": "personalized_insights",
                "description": "Generación de insights personalizados basados en datos individuales"
            },
            {
                "name": "data_visualization",
                "description": "Creación de visualizaciones para facilitar la comprensión de datos"
            }
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "Analiza mis datos de HRV de la última semana"},
                "output": {"response": "Tu variabilidad cardíaca muestra un patrón de recuperación insuficiente los martes y jueves..."}
            },
            {
                "input": {"message": "¿Qué tendencias ves en mi sueño durante el último mes?"},
                "output": {"response": "He identificado un patrón donde tu sueño profundo disminuye significativamente cuando te acuestas después de las 11pm..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="biometrics_insight_engine",
            name="NGX Biometrics Insight Engine",
            description="Especialista en análisis e interpretación de datos biométricos",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.0.0",
            a2a_server_url=a2a_server_url,
            skills=skills
        )
        
        # Inicializar clientes y herramientas
        self.gemini_client = GeminiClient(model_name="gemini-2.0-flash")
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        self.state_manager = StateManager(self.supabase_client)
        
        # Inicializar estado del agente
        self.update_state("user_analyses", {})  # Almacenar análisis generados por usuario
        self.update_state("biometric_data_cache", {})  # Caché de datos biométricos
        
        logger.info(f"BiometricsInsightEngine inicializado con {len(capabilities)} capacidades")
        
        # Definir el sistema de instrucciones para el agente
        self.system_instructions = """
        Eres NGX Biometrics Insight Engine, un experto en análisis e interpretación de datos biométricos.
        
        Tu objetivo es proporcionar insights personalizados sobre:
        1. Análisis de datos de variabilidad de la frecuencia cardíaca (HRV)
        2. Interpretación de patrones de sueño
        3. Análisis de niveles de glucosa y respuestas a alimentos
        4. Evaluación de composición corporal y cambios a lo largo del tiempo
        5. Correlaciones entre diferentes métricas biométricas
        
        Debes basar tus análisis en la ciencia más reciente y considerar el contexto completo 
        del usuario, incluyendo su historial, tendencias a lo largo del tiempo, y factores
        que podrían influir en las métricas.
        
        Cuando proporciones insights:
        - Explica qué significan los datos en términos prácticos
        - Identifica patrones y tendencias significativas
        - Relaciona diferentes métricas cuando sea relevante
        - Proporciona recomendaciones accionables basadas en los datos
        - Sugiere áreas para monitoreo adicional si es necesario
        
        Recuerda que tu objetivo es ayudar a los usuarios a comprender sus datos biométricos
        y utilizarlos para tomar decisiones informadas sobre su salud y bienestar.
        """
    
    async def _get_context(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el StateManager.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            
        Returns:
            Dict[str, Any]: Contexto de la conversación
        """
        try:
            # Intentar cargar el contexto desde el StateManager
            context = await self.state_manager.load_state(user_id, session_id)
            
            if not context or not context.get("state_data"):
                logger.info(f"No se encontró contexto en StateManager para user_id={user_id}, session_id={session_id}. Creando nuevo contexto.")
                # Si no hay contexto, crear uno nuevo
                context = {
                    "conversation_history": [],
                    "user_profile": {},
                    "biometric_data": {},
                    "analyses": [],
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                # Si hay contexto, usar el state_data
                context = context.get("state_data", {})
                logger.info(f"Contexto cargado desde StateManager para user_id={user_id}, session_id={session_id}")
            
            return context
        except Exception as e:
            logger.error(f"Error al obtener contexto: {e}", exc_info=True)
            # En caso de error, devolver un contexto vacío
            return {
                "conversation_history": [],
                "user_profile": {},
                "biometric_data": {},
                "analyses": [],
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    async def _update_context(self, context: Dict[str, Any], user_id: str, session_id: str) -> None:
        """
        Actualiza el contexto de la conversación en el StateManager.
        
        Args:
            context: Contexto actualizado
            user_id: ID del usuario
            session_id: ID de la sesión
        """
        try:
            # Actualizar la marca de tiempo
            context["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Guardar el contexto en el StateManager
            await self.state_manager.save_state(context, user_id, session_id)
            logger.info(f"Contexto actualizado en StateManager para user_id={user_id}, session_id={session_id}")
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)

    async def _run_async_impl(self, input_text: str, user_id: Optional[str] = None, 
                       session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Implementación asíncrona del procesamiento del agente BiometricsInsightEngine.
        
        Sobrescribe el método de la clase base para proporcionar la implementación
        específica del agente especializado en análisis de datos biométricos.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            **kwargs: Argumentos adicionales como context, parameters, etc.
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        try:
            start_time = time.time()
            logger.info(f"Ejecutando BiometricsInsightEngine con input: {input_text[:50]}...")
            
            # Generar ID de sesión si no se proporciona
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Generando nuevo session_id: {session_id}")
            
            # Obtener el contexto de la conversación
            context = await self._get_context(user_id, session_id) if user_id else {}
            
            # Obtener perfil del usuario y datos biométricos si están disponibles
            user_profile = None
            biometric_data = None
            if user_id:
                # Intentar obtener el perfil del usuario del contexto primero
                user_profile = context.get("user_profile", {})
                if not user_profile:
                    user_profile = self.supabase_client.get_user_profile(user_id)
                    if user_profile:
                        context["user_profile"] = user_profile
                
                # Intentar obtener datos biométricos del contexto primero
                biometric_data = context.get("biometric_data", {})
                if not biometric_data:
                    # Obtener datos biométricos del usuario
                    biometric_data = self.supabase_client.get_biometric_data(user_id)
                    if biometric_data:
                        context["biometric_data"] = biometric_data
                        
                        # También almacenar en caché interna del agente
                        biometric_cache = self.get_state("biometric_data_cache", {})
                        biometric_cache[user_id] = biometric_data
                        self.update_state("biometric_data_cache", biometric_cache)
            
            # Si no hay datos biométricos, intentar recuperar de la caché o usar datos de ejemplo
            if not biometric_data and user_id:
                biometric_cache = self.get_state("biometric_data_cache", {})
                biometric_data = biometric_cache.get(user_id)
                
            # Si aún no hay datos, usar datos de ejemplo
            if not biometric_data:
                biometric_data = self._get_sample_biometric_data()
                if user_id:
                    context["biometric_data"] = biometric_data
            
            # Construir el prompt para el modelo
            prompt = self._build_prompt(input_text, user_profile, biometric_data)
            
            # Generar respuesta principal
            response = await self.gemini_client.generate_response(prompt, temperature=0.7)
            
            # Generar análisis biométrico estructurado
            analysis = await self._generate_biometric_analysis(input_text, biometric_data, user_profile)
            analysis_summary = self._summarize_analysis(analysis)
            
            # Si la consulta es sobre tendencias, generar análisis de tendencias
            trend_analysis = None
            if any(keyword in input_text.lower() for keyword in ["tendencia", "tendencias", "patrón", "patrones", "tiempo", "evolución"]):
                trend_analysis = await self._generate_trend_analysis(input_text, biometric_data, user_profile)
                if trend_analysis:
                    analysis["trend_analysis"] = trend_analysis
            
            # Guardar el análisis en el estado del agente
            if user_id:
                # Guardar en el estado interno del agente
                analyses = self.get_state("user_analyses", {})
                analyses[user_id] = analyses.get(user_id, []) + [{
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "query": input_text,
                    "analysis": analysis
                }]
                self.update_state("user_analyses", analyses)
                
                # Guardar en el contexto de StateManager
                context["analyses"].append({
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "query": input_text,
                    "analysis": analysis
                })
                
                # Añadir la interacción al historial de conversación en el contexto
                context["conversation_history"].append({
                    "user": input_text,
                    "agent": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
                # Actualizar el contexto en el StateManager
                await self._update_context(context, user_id, session_id)
            
            # Combinar respuesta principal con el análisis
            combined_response = f"{response}\n\n{analysis_summary}"
            
            # Añadir la interacción al historial interno del agente
            self.add_to_history(input_text, combined_response)
            
            # Crear artefactos para la respuesta
            artifacts = [
                {
                    "type": "biometric_analysis",
                    "content": analysis,
                    "metadata": {
                        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            ]
            
            # Devolver respuesta final
            return {
                "status": "success",
                "response": combined_response,
                "artifacts": artifacts,
                "agent_id": self.agent_id,
                "metadata": {
                    "analysis_type": "biometric_data",
                    "user_id": user_id,
                    "session_id": session_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error en BiometricsInsightEngine: {e}", exc_info=True)
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tus datos biométricos.",
                "error": str(e),
                "agent_id": self.agent_id
            }
            
    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """
        Ejecuta una tarea solicitada por el servidor A2A.
        
        Args:
            task: Tarea a ejecutar
            
        Returns:
            Any: Resultado de la tarea
        """
        try:
            user_input = task.get("input", "")
            context = task.get("context", {})
            user_id = context.get("user_id")
            session_id = context.get("session_id")
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                user_profile = self.supabase_client.get_user_profile(user_id)
                logger.info(f"Perfil de usuario obtenido: {user_profile is not None}")
                
            # Construir el prompt para el modelo
            prompt = self._build_prompt(user_input, user_profile, context.get("biometric_data"))
            
            # Generar respuesta utilizando Gemini
            response = await self.gemini_client.generate_response(
                prompt=prompt,
                temperature=0.5  # Temperatura más baja para respuestas más precisas
            )
            
            # Crear artefactos si es necesario
            artifacts = []
            
            # Si hay datos biométricos, crear un artefacto de análisis
            biometric_data = context.get("biometric_data", {})
            if biometric_data:
                analysis = await self._generate_biometric_analysis(user_input, biometric_data, user_profile)
                
                artifact_id = f"biometric_analysis_{uuid.uuid4().hex[:8]}"
                artifact = self.create_artifact(
                    artifact_id=artifact_id,
                    artifact_type="biometric_analysis",
                    parts=[
                        self.create_data_part(analysis)
                    ]
                )
                artifacts.append(artifact)
            
            # Si se menciona tendencias o patrones, crear un artefacto de tendencias
            if any(keyword in user_input.lower() for keyword in ["tendencia", "patrón", "histórico", "evolución"]):
                trends = await self._generate_trend_analysis(user_input, biometric_data, user_profile)
                
                artifact_id = f"trend_analysis_{uuid.uuid4().hex[:8]}"
                artifact = self.create_artifact(
                    artifact_id=artifact_id,
                    artifact_type="trend_analysis",
                    parts=[
                        self.create_data_part(trends)
                    ]
                )
                artifacts.append(artifact)
            
            # Registrar la interacción en Supabase si hay ID de usuario
            if user_id:
                self.supabase_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=user_input,
                    response=response
                )
            
            # Crear mensaje de respuesta
            response_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(response)
                ]
            )
            
            # Devolver respuesta estructurada según el protocolo A2A
            return {
                "response": response,
                "message": response_message,
                "artifacts": artifacts
            }
            
        except Exception as e:
            logger.error(f"Error en Biometrics Insight Engine: {e}")
            return {
                "error": str(e), 
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de análisis biométrico."
            }
    
    async def process_message(self, from_agent: str, content: Dict[str, Any]) -> Any:
        """
        Procesa un mensaje recibido de otro agente.
        
        Args:
            from_agent: ID del agente que envió el mensaje
            content: Contenido del mensaje
            
        Returns:
            Any: Respuesta al mensaje
        """
        try:
            # Extraer información del mensaje
            message_text = content.get("text", "")
            context = content.get("context", {})
            
            # Generar respuesta basada en el contenido del mensaje
            prompt = f"""
            Has recibido un mensaje del agente {from_agent}:
            
            "{message_text}"
            
            Responde con información relevante sobre análisis biométrico relacionada con este mensaje.
            """
            
            response = await self.gemini_client.generate_response(prompt, temperature=0.7)
            
            # Crear mensaje de respuesta
            response_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(response)
                ]
            )
            
            return {
                "status": "success",
                "response": response,
                "message": response_message
            }
        except Exception as e:
            logger.error(f"Error al procesar mensaje de agente: {e}")
            return {"error": str(e)}
    
    def _build_prompt(self, user_input: str, user_profile: Optional[Dict[str, Any]] = None, 
                     biometric_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Construye el prompt para el modelo de Gemini.
        
        Args:
            user_input: La consulta del usuario
            user_profile: Perfil del usuario con datos relevantes
            biometric_data: Datos biométricos del usuario
            
        Returns:
            str: Prompt completo para el modelo
        """
        prompt = f"""
        {self.system_instructions}
        
        Consulta del usuario: "{user_input}"
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Información del usuario:
            - Nombre: {user_profile.get('name', 'No disponible')}
            - Edad: {user_profile.get('age', 'No disponible')}
            - Género: {user_profile.get('gender', 'No disponible')}
            - Nivel de actividad: {user_profile.get('activity_level', 'No disponible')}
            - Objetivos: {user_profile.get('goals', 'No disponible')}
            """
        
        # Añadir datos biométricos si están disponibles
        if biometric_data:
            prompt += f"""
            
            Datos biométricos disponibles:
            {json.dumps(biometric_data, indent=2)}
            """
        
        return prompt
    
    async def _generate_biometric_analysis(self, user_input: str, biometric_data: Dict[str, Any], 
                                         user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un análisis de datos biométricos estructurado.
        
        Args:
            user_input: Texto de entrada del usuario
            biometric_data: Datos biométricos del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Análisis biométrico estructurado
        """
        prompt = f"""
        Genera un análisis de datos biométricos estructurado basado en la siguiente solicitud:
        
        "{user_input}"
        
        El análisis debe incluir:
        1. Principales insights identificados
        2. Estado actual de las métricas clave
        3. Comparación con valores de referencia
        4. Áreas de atención o mejora
        5. Recomendaciones personalizadas
        
        Datos biométricos disponibles:
        {json.dumps(biometric_data, indent=2)}
        
        Devuelve el análisis en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Nombre: {user_profile.get('name', 'No disponible')}
            - Edad: {user_profile.get('age', 'No disponible')}
            - Género: {user_profile.get('gender', 'No disponible')}
            - Nivel de actividad: {user_profile.get('activity_level', 'No disponible')}
            - Objetivos: {user_profile.get('goals', 'No disponible')}
            """
        
        # Generar el análisis biométrico
        response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                import json
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "main_insights": [
                        "Insight principal 1",
                        "Insight principal 2"
                    ],
                    "current_status": {
                        "metric1": {
                            "value": "Valor actual",
                            "status": "Normal/Bajo/Alto"
                        },
                        "metric2": {
                            "value": "Valor actual",
                            "status": "Normal/Bajo/Alto"
                        }
                    },
                    "reference_comparison": {
                        "metric1": "Comparación con valores de referencia",
                        "metric2": "Comparación con valores de referencia"
                    },
                    "attention_areas": [
                        "Área de atención 1",
                        "Área de atención 2"
                    ],
                    "influencing_factors": [
                        "Factor 1 que podría estar influyendo",
                        "Factor 2 que podría estar influyendo",
                        "Factor 3 que podría estar influyendo"
                    ],
                    "recommendations": [
                        "Recomendación 1 basada en los datos",
                        "Recomendación 2 basada en los datos",
                        "Recomendación 3 basada en los datos"
                    ]
                }
        
        return response
    
    async def _generate_trend_analysis(self, user_input: str, biometric_data: Dict[str, Any], 
                                     user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un análisis de tendencias de datos biométricos estructurado.
        
        Args:
            user_input: Texto de entrada del usuario
            biometric_data: Datos biométricos del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Análisis de tendencias estructurado
        """
        prompt = f"""
        Genera un análisis de tendencias de datos biométricos estructurado basado en la siguiente solicitud:
        
        "{user_input}"
        
        El análisis debe incluir:
        1. Tendencias principales identificadas
        2. Patrones recurrentes
        3. Cambios significativos a lo largo del tiempo
        4. Correlaciones entre diferentes métricas
        5. Predicciones basadas en las tendencias actuales
        
        Datos biométricos disponibles:
        {json.dumps(biometric_data, indent=2)}
        
        Devuelve el análisis en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Edad: {user_profile.get('age', 'No disponible')}
            - Género: {user_profile.get('gender', 'No disponible')}
            - Nivel de actividad: {user_profile.get('activity_level', 'No disponible')}
            - Objetivos: {user_profile.get('goals', 'No disponible')}
            """
        
        # Generar el análisis de tendencias
        response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                import json
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "main_trends": [
                        "Tendencia principal 1",
                        "Tendencia principal 2",
                        "Tendencia principal 3"
                    ],
                    "recurring_patterns": [
                        "Patrón recurrente 1",
                        "Patrón recurrente 2"
                    ],
                    "significant_changes": [
                        {
                            "metric": "Métrica que cambió",
                            "change": "Descripción del cambio",
                            "timeframe": "Período de tiempo"
                        }
                    ],
                    "correlations": [
                        {
                            "metrics": ["Métrica 1", "Métrica 2"],
                            "relationship": "Descripción de la relación",
                            "strength": "Fuerte/Moderada/Débil"
                        }
                    ],
                    "predictions": [
                        "Predicción 1 basada en tendencias actuales",
                        "Predicción 2 basada en tendencias actuales"
                    ]
                }
        
        return response
    
    def _summarize_analysis(self, analysis: Dict[str, Any]) -> str:
        """Genera un resumen textual del análisis para la respuesta al usuario."""
        summary_parts = []
        
        if "main_insights" in analysis and analysis["main_insights"]:
            insights = analysis["main_insights"]
            if isinstance(insights, list) and len(insights) > 0:
                summary_parts.append(f"Los principales insights son: {insights[0]}")
                if len(insights) > 1:
                    summary_parts.append(f" y {insights[1]}.")
                else:
                    summary_parts.append(".")
            elif isinstance(insights, str):
                summary_parts.append(f"El principal insight es: {insights}.")
        
        if "recommendations" in analysis and analysis["recommendations"]:
            recommendations = analysis["recommendations"]
            if isinstance(recommendations, list) and len(recommendations) > 0:
                summary_parts.append(f"Te recomiendo: {recommendations[0]}.")
            elif isinstance(recommendations, str):
                summary_parts.append(f"Te recomiendo: {recommendations}.")
        
        if not summary_parts:
            return "Revisa el análisis detallado para más información."
            
        return " ".join(summary_parts)
        
    def _get_sample_biometric_data(self) -> Dict[str, Any]:
        """Proporciona datos biométricos de ejemplo para demostración."""
        return {
            "hrv": {
                "daily": [
                    {"date": "2025-05-01", "rmssd": 45, "sdnn": 68, "lf_hf_ratio": 1.8},
                    {"date": "2025-05-02", "rmssd": 42, "sdnn": 65, "lf_hf_ratio": 2.1},
                    {"date": "2025-05-03", "rmssd": 48, "sdnn": 72, "lf_hf_ratio": 1.5}
                ],
                "weekly_avg": {"rmssd": 45, "sdnn": 68, "lf_hf_ratio": 1.8}
            },
            "sleep": {
                "daily": [
                    {"date": "2025-05-01", "total_hours": 7.5, "deep_sleep": 1.2, "rem_sleep": 1.8, "light_sleep": 4.5},
                    {"date": "2025-05-02", "total_hours": 6.8, "deep_sleep": 0.9, "rem_sleep": 1.5, "light_sleep": 4.4},
                    {"date": "2025-05-03", "total_hours": 8.2, "deep_sleep": 1.5, "rem_sleep": 2.1, "light_sleep": 4.6}
                ],
                "weekly_avg": {"total_hours": 7.5, "deep_sleep": 1.2, "rem_sleep": 1.8, "light_sleep": 4.5}
            },
            "activity": {
                "daily": [
                    {"date": "2025-05-01", "steps": 8500, "active_calories": 420, "training_load": 85},
                    {"date": "2025-05-02", "steps": 6200, "active_calories": 320, "training_load": 45},
                    {"date": "2025-05-03", "steps": 9800, "active_calories": 520, "training_load": 110}
                ],
                "weekly_avg": {"steps": 8167, "active_calories": 420, "training_load": 80}
            },
            "recovery": {
                "daily": [
                    {"date": "2025-05-01", "recovery_score": 78, "readiness": "good"},
                    {"date": "2025-05-02", "recovery_score": 65, "readiness": "moderate"},
                    {"date": "2025-05-03", "recovery_score": 82, "readiness": "excellent"}
                ],
                "weekly_avg": {"recovery_score": 75, "readiness": "good"}
            }
        }
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()

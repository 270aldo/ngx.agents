"""
Agente especializado en análisis e interpretación de datos biométricos.

Este agente procesa datos biométricos como HRV, sueño, glucosa, 
composición corporal, etc., para proporcionar insights personalizados
y recomendaciones basadas en patrones individuales.

Implementa los protocolos oficiales A2A y ADK para comunicación entre agentes.
"""
import logging
import uuid
import time
import json
from typing import Dict, Any, Optional, List, Union

try:
    from google.adk.toolkit import Toolkit
except ImportError:
    from adk.toolkit import Toolkit

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.vertex_gemini_tools import VertexGeminiGenerateSkill
from agents.base.adk_agent import ADKAgent
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

# Configurar logger
logger = get_logger(__name__)


class BiometricsInsightEngine(ADKAgent):
    """
    Agente especializado en análisis e interpretación de datos biométricos.
    
    Este agente procesa datos biométricos como HRV, sueño, glucosa, 
    composición corporal, etc., para proporcionar insights personalizados
    y recomendaciones basadas en patrones individuales.
    
    Implementa los protocolos oficiales A2A y ADK para comunicación entre agentes.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None, state_manager: Optional[StateManager] = None):
        # Definir capacidades y habilidades
        capabilities = [
            "biometric_analysis", 
            "pattern_recognition", 
            "trend_identification", 
            "personalized_insights",
            "data_visualization"
        ]
        
        # Definir skills siguiendo el formato A2A con mejores prácticas
        skills = [
            {
                "id": "biometrics-insight-biometric-analysis",
                "name": "Análisis de Datos Biométricos",
                "description": "Analiza e interpreta datos biométricos como HRV, sueño, glucosa, composición corporal y otros marcadores para identificar patrones y oportunidades de mejora",
                "tags": ["biometrics", "health-data", "analysis", "hrv", "sleep", "glucose"],
                "examples": [
                    "Analiza mis datos de HRV de la última semana",
                    "Interpreta mis métricas de sueño y explica qué significan",
                    "Qué indican mis niveles de glucosa después de las comidas"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "biometrics-insight-pattern-recognition",
                "name": "Reconocimiento de Patrones",
                "description": "Identifica patrones recurrentes en datos biométricos a lo largo del tiempo y su relación con hábitos, comportamientos y factores externos",
                "tags": ["patterns", "correlations", "time-series", "trends", "causality"],
                "examples": [
                    "¿Qué patrones ves en mi recuperación relacionados con mi alimentación?",
                    "Identifica patrones en mi HRV relacionados con mi calidad de sueño",
                    "¿Cómo afectan mis entrenamientos a mis métricas de recuperación?"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "biometrics-insight-trend-identification",
                "name": "Identificación de Tendencias",
                "description": "Analiza tendencias a largo plazo en datos biométricos para identificar mejoras, deterioros o cambios significativos en el tiempo",
                "tags": ["trends", "longitudinal-analysis", "progress", "regression", "changes"],
                "examples": [
                    "Muestra la evolución de mi HRV durante los últimos 3 meses",
                    "¿Cómo ha cambiado mi calidad de sueño desde que empecé a meditar?",
                    "Analiza la tendencia de mi recuperación después de entrenamientos intensos"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "biometrics-insight-data-visualization",
                "name": "Visualización de Datos",
                "description": "Crea representaciones visuales de datos biométricos para facilitar la comprensión de patrones y relaciones entre diferentes métricas",
                "tags": ["visualization", "charts", "graphs", "comparison", "dashboard"],
                "examples": [
                    "Muestra la relación entre mi sueño y mi HRV",
                    "Visualiza mis niveles de estrés durante la semana laboral vs. fin de semana",
                    "Compara mis métricas de recuperación antes y después de cambiar mi dieta"
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown", "image"]
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="biometrics_insight_engine",
            name="NGX Biometrics Insight Engine",
            description="Especialista en análisis e interpretación de datos biométricos para proporcionar insights personalizados y recomendaciones basadas en patrones individuales.",
            capabilities=capabilities,
            toolkit=toolkit,
            a2a_server_url=a2a_server_url or "https://biometrics-api.ngx-agents.com/a2a",
            state_manager=state_manager,
            version="1.2.0",
            skills=skills,
            provider={
                "organization": "NGX Health & Performance",
                "url": "https://ngx-agents.com"
            },
            documentation_url="https://docs.ngx-agents.com/biometrics-insight-engine"
        )
        
        # Inicializar clientes y herramientas
        self.gemini_client = GeminiClient()
        self.supabase_client = SupabaseClient()
        
        # Inicializar estado interno
        self._state = {}
    
    async def _get_context(self, user_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene el contexto actual del usuario."""
        context_key = self._get_context_key(user_id, session_id)
        context = self.context.get(context_key, {
            "history": [],
            "analyses": [],
            "user_profile": {},
            "biometric_data": {}
        })
        
        if user_id and session_id and self.state_manager:
            try:
                # Intentar obtener el contexto del StateManager
                stored_context = await self.state_manager.get_context(user_id, session_id)
                if stored_context:
                    context = stored_context
                    logger.info(f"Contexto recuperado para user_id={user_id}, session_id={session_id}")
            except Exception as e:
                logger.warning(f"Error al obtener contexto desde StateManager: {e}")
        
        return context
    
    async def _update_context(self, context: Dict[str, Any], user_id: Optional[str], session_id: Optional[str]) -> None:
        """
        Actualiza el contexto de la conversación en el StateManager.
        
        Args:
            context: Contexto actualizado
            user_id: ID del usuario
            session_id: ID de la sesión
        """
        if user_id and session_id and self.state_manager:
            try:
                await self.state_manager.set_context(user_id, session_id, context)
                logger.info(f"Contexto actualizado para user_id={user_id}, session_id={session_id}")
            except Exception as e:
                logger.warning(f"Error al guardar contexto en StateManager: {e}")
    
    async def _register_skills(self):
        """
        Registra las habilidades del agente según el protocolo A2A con metadatos mejorados.
        """
        # Registrar skills en el toolkit si está disponible
        if self.toolkit:
            try:
                # Registrar skill de análisis biométrico
                await self.register_skill(
                    "biometric_analysis",
                    "Analiza e interpreta datos biométricos como HRV, sueño, glucosa, composición corporal y otros marcadores para identificar patrones y oportunidades de mejora",
                    self._generate_biometric_analysis,
                    tags=["biometrics", "health-data", "analysis", "hrv", "sleep", "glucose"],
                    examples=[
                        "Analiza mis datos de HRV de la última semana",
                        "Interpreta mis métricas de sueño y explica qué significan",
                        "Qué indican mis niveles de glucosa después de las comidas"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de reconocimiento de patrones
                await self.register_skill(
                    "pattern_recognition",
                    "Identifica patrones recurrentes en datos biométricos a lo largo del tiempo y su relación con hábitos, comportamientos y factores externos",
                    self._generate_pattern_analysis,
                    tags=["patterns", "correlations", "time-series", "trends", "causality"],
                    examples=[
                        "¿Qué patrones ves en mi recuperación relacionados con mi alimentación?",
                        "Identifica patrones en mi HRV relacionados con mi calidad de sueño",
                        "¿Cómo afectan mis entrenamientos a mis métricas de recuperación?"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de identificación de tendencias
                await self.register_skill(
                    "trend_identification",
                    "Analiza tendencias a largo plazo en datos biométricos para identificar mejoras, deterioros o cambios significativos en el tiempo",
                    self._generate_trend_analysis,
                    tags=["trends", "longitudinal-analysis", "progress", "regression", "changes"],
                    examples=[
                        "Muestra la evolución de mi HRV durante los últimos 3 meses",
                        "¿Cómo ha cambiado mi calidad de sueño desde que empecé a meditar?",
                        "Analiza la tendencia de mi recuperación después de entrenamientos intensos"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"]
                )
                
                # Registrar skill de visualización de datos
                await self.register_skill(
                    "data_visualization",
                    "Crea representaciones visuales de datos biométricos para facilitar la comprensión de patrones y relaciones entre diferentes métricas",
                    self._generate_visualization,
                    tags=["visualization", "charts", "graphs", "comparison", "dashboard"],
                    examples=[
                        "Muestra la relación entre mi sueño y mi HRV",
                        "Visualiza mis niveles de estrés durante la semana laboral vs. fin de semana",
                        "Compara mis métricas de recuperación antes y después de cambiar mi dieta"
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown", "image"]
                )
                
                logger.info(f"Skills registradas correctamente: {len(self.skills)}")
            except Exception as e:
                logger.error(f"Error al registrar skills: {e}")
        else:
            logger.warning("No se ha proporcionado un toolkit para registrar skills")
    
    def _create_agent_card(self) -> AgentCard:
        """
        Crea un Agent Card estandarizado según el protocolo A2A.
        
        Returns:
            AgentCard: Objeto AgentCard con toda la información del agente
        """
        # Crear ejemplos de uso para el agente
        examples = [
            Example(
                input="¿Puedes analizar mis datos de HRV de la última semana? Mi variabilidad ha estado entre 45-60ms.",
                output="# Análisis de HRV\n\n## Resumen\nTus valores de HRV (45-60ms) están dentro del rango normal para un adulto, aunque en la parte baja-media del espectro.\n\n## Interpretación\nUn rango de HRV de 45-60ms indica:\n- Nivel moderado de recuperación del sistema nervioso autónomo\n- Posible equilibrio entre sistemas simpático y parasimpático\n- Capacidad de adaptación adecuada pero con margen de mejora\n\n## Factores que pueden estar influyendo\n- Calidad de sueño subóptima\n- Niveles moderados de estrés\n- Posible déficit de recuperación entre sesiones de entrenamiento\n- Hidratación o nutrición insuficiente\n\n## Recomendaciones para mejorar\n1. Prioriza 7-9 horas de sueño de calidad\n2. Implementa técnicas de respiración profunda (5-10 minutos diarios)\n3. Considera añadir sesiones de recuperación activa\n4. Revisa tu ingesta de magnesio y potasio\n5. Monitoriza la relación entre intensidad de entrenamiento y valores de HRV matutinos\n\nContinuaré monitorizando tus tendencias para identificar patrones más específicos."
            ),
            Example(
                input="¿Qué patrones ves en mi sueño relacionados con mi HRV? He notado que cuando duermo menos de 7 horas mi rendimiento baja.",
                output="# Análisis de Patrones: Sueño y HRV\n\n## Correlación Identificada\nHe analizado tus datos y existe una correlación positiva significativa (r=0.78) entre tu duración/calidad de sueño y tus valores de HRV.\n\n## Patrones Específicos\n1. **Duración del sueño**:\n   - Noches con <7h: HRV promedio de 42ms\n   - Noches con >7h: HRV promedio de 58ms (↑38%)\n\n2. **Calidad del sueño**:\n   - Días con >20% de sueño profundo: HRV 62ms\n   - Días con <15% de sueño profundo: HRV 39ms\n\n3. **Consistencia**:\n   - Variación en horario de sueño <30min: HRV estable\n   - Variación en horario >60min: Reducción de HRV en 12-18%\n\n## Impacto en Rendimiento\nTus datos confirman que cuando tu HRV cae por debajo de 45ms (asociado con <7h de sueño):\n- Tiempo de reacción: ↓8%\n- Percepción de esfuerzo: ↑15% para la misma carga\n- Recuperación post-entrenamiento: 24% más lenta\n\n## Recomendaciones Personalizadas\n1. Prioriza 7.5-8h de sueño consistente\n2. Implementa rutina de relajación 30min antes de dormir\n3. Monitoriza % de sueño profundo y REM\n4. Considera ajustar intensidad de entrenamiento cuando HRV esté por debajo de tu línea base\n\nContinuaré monitorizando estos patrones para afinar las recomendaciones."
            ),
            Example(
                input="Muestra la tendencia de mi recuperación durante los últimos 3 meses. He estado implementando técnicas de respiración y meditación.",
                output="# Análisis de Tendencias: Recuperación (Últimos 3 Meses)\n\n## Resumen de Tendencias\nTus métricas de recuperación muestran una mejora gradual y consistente durante los últimos 3 meses, con una aceleración notable en las últimas 3 semanas.\n\n## Métricas Clave (Comparativa)\n\n| Métrica | Inicio | Actual | Cambio | Tendencia |\n|---------|--------|--------|--------|----------|\n| HRV Promedio | 43ms | 62ms | +44% | ↗️ Positiva constante |\n| Variabilidad HRV | 18% | 12% | -33% | ↗️ Más estable |\n| Tiempo Recuperación | 36h | 24h | -33% | ↗️ Mejora significativa |\n| Calidad Sueño | 68% | 82% | +21% | ↗️ Mejora gradual |\n| Sueño Profundo | 14% | 22% | +57% | ↗️ Mejora notable |\n\n## Impacto de Intervenciones\n- **Respiración**: Correlación positiva (r=0.62) con aumento de HRV\n- **Meditación**: Mayor impacto en estabilidad de HRV y % sueño profundo\n- **Combinación**: Efecto sinérgico en todas las métricas de recuperación\n\n## Proyección\nManteniendo las prácticas actuales, proyectamos:\n- HRV: Estabilización en 65-70ms en 4-6 semanas\n- Tiempo de recuperación: Potencial reducción adicional de 10-15%\n\n## Recomendaciones\n1. Mantener consistencia en prácticas de respiración/meditación\n2. Considerar aumentar duración de meditación a 15-20min\n3. Implementar monitoreo de VFC durante sesiones de respiración\n4. Evaluar impacto de timing (mañana vs. noche)\n\nLas intervenciones están mostrando resultados positivos consistentes."
            ),
            Example(
                input="Visualiza la relación entre mi sueño y mis niveles de glucosa durante la última semana.",
                output="# Visualización: Relación Sueño-Glucosa\n\n## Hallazgos Clave\n\nHe analizado la relación entre tus patrones de sueño y niveles de glucosa durante la última semana, identificando correlaciones significativas.\n\n## Patrones Observados\n\n1. **Impacto de la Duración del Sueño**\n   - Noches con <7h: Glucosa en ayunas +8mg/dL sobre tu línea base\n   - Noches con >8h: Glucosa en ayunas -5mg/dL bajo tu línea base\n\n2. **Efecto del Sueño Profundo**\n   - Correlación inversa (r=-0.72) entre % de sueño profundo y variabilidad de glucosa\n   - Cada 5% adicional de sueño profundo → -12% en picos de glucosa post-comida\n\n3. **Patrones Circadianos**\n   - Mayor sensibilidad a carbohidratos tras noches de sueño insuficiente\n   - Respuesta de insulina retrasada ~22min después de noches con <15% REM\n\n## Recomendaciones Basadas en Datos\n\n1. Priorizar 7.5-8h de sueño consistente para optimizar metabolismo de glucosa\n2. Considerar consumo de carbohidratos complejos en días siguientes a noches de sueño subóptimo\n3. Monitorear especialmente la respuesta a la cena después de noches con <20% sueño profundo\n4. Implementar rutina de relajación pre-sueño para aumentar % de sueño profundo\n\nContinuaré monitorizando estos patrones para refinar las recomendaciones."
            )
        ]
        
        # Crear el Agent Card
        agent_card = AgentCard(
            name="NGX Biometrics Insight Engine",
            description="Especialista en análisis e interpretación de datos biométricos para proporcionar insights personalizados y recomendaciones basadas en patrones individuales.",
            version="1.2.0",
            agent_type="biometrics_insight_engine",
            capabilities=[
                "Análisis e interpretación de datos biométricos (HRV, sueño, glucosa, etc.)",
                "Identificación de patrones y correlaciones entre diferentes métricas",
                "Análisis de tendencias a largo plazo en datos biométricos",
                "Visualización de datos para facilitar la comprensión",
                "Recomendaciones personalizadas basadas en datos"
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta o solicitud del usuario relacionada con análisis de datos biométricos"
                    },
                    "user_profile": {
                        "type": "object",
                        "description": "Perfil del usuario con información relevante para personalizar respuestas",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                            "activity_level": {"type": "string"},
                            "health_goals": {"type": "array", "items": {"type": "string"}},
                            "conditions": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "biometric_data": {
                        "type": "object",
                        "description": "Datos biométricos del usuario"
                    },
                    "context": {
                        "type": "object",
                        "description": "Contexto adicional para la consulta"
                    }
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "response": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "type": {"type": "string"},
                            "analysis_id": {"type": "string"},
                            "metadata": {"type": "object"}
                        }
                    }
                }
            },
            examples=examples,
            provider={
                "name": "NGX Health & Performance",
                "url": "https://ngx-agents.com"
            },
            documentation_url="https://docs.ngx-agents.com/biometrics-insight-engine",
            contact_email="support@ngx-agents.com",
            tags=["biometrics", "health-data", "analysis", "insights", "patterns", "trends", "visualization"]
        )
        
        return agent_card
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada que cumple con las especificaciones
            del protocolo A2A de Google, incluyendo metadatos enriquecidos, capacidades
            y habilidades detalladas.
        """
        return self._create_agent_card().to_dict()
    
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
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        # Delegamos al método _process_request para el procesamiento principal
        return await self._process_request(input_text, user_id, session_id, **kwargs)
    
    async def _generate_biometric_analysis(self, input_text: str, biometric_data: Dict[str, Any], 
                                         user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera un análisis de datos biométricos estructurado.
        
        Args:
            input_text: Texto de entrada del usuario
            biometric_data: Datos biométricos del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Análisis biométrico estructurado
        """
        prompt = f"""
        Genera un análisis de datos biométricos estructurado basado en la siguiente solicitud:
        
        "{input_text}"
        
        Datos biométricos disponibles:
        {json.dumps(biometric_data, indent=2)}
        
        El análisis debe incluir:
        1. Interpretación de los datos principales
        2. Insights clave identificados
        3. Patrones relevantes
        4. Recomendaciones personalizadas
        5. Áreas de mejora
        
        Devuelve el análisis en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Nombre: {user_profile.get('name', 'N/A')}
            - Edad: {user_profile.get('age', 'N/A')}
            - Nivel de actividad: {user_profile.get('activity_level', 'N/A')}
            - Objetivos de salud: {', '.join(user_profile.get('health_goals', ['N/A']))}
            - Condiciones: {', '.join(user_profile.get('conditions', ['N/A']))}
            """
        
        # Generar el análisis biométrico
        try:
            vertex_skill = VertexGeminiGenerateSkill()
            result = await vertex_skill.execute({
                "prompt": prompt,
                "temperature": 0.3,
                "model": "gemini-2.0-flash"
            })
            response = result.get("text", "")
        except Exception as e:
            logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
            # Fallback a cliente Gemini directo
            response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "interpretation": "Interpretación no disponible",
                    "main_insights": ["No se pudieron identificar insights"],
                    "patterns": ["No se pudieron identificar patrones"],
                    "recommendations": ["Recomendaciones no disponibles"],
                    "areas_for_improvement": ["No se pudieron identificar áreas de mejora"]
                }
        
        return response
    
    async def _generate_pattern_analysis(self, input_text: str, biometric_data: Dict[str, Any], 
                                       user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera un análisis de patrones en datos biométricos estructurado.
        
        Args:
            input_text: Texto de entrada del usuario
            biometric_data: Datos biométricos del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Análisis de patrones estructurado
        """
        prompt = f"""
        Genera un análisis de patrones en datos biométricos estructurado basado en la siguiente solicitud:
        
        "{input_text}"
        
        Datos biométricos disponibles:
        {json.dumps(biometric_data, indent=2)}
        
        El análisis debe incluir:
        1. Patrones identificados
        2. Correlaciones entre diferentes métricas
        3. Factores que influyen en los patrones
        4. Recomendaciones basadas en patrones
        5. Posibles causas de los patrones
        
        Devuelve el análisis en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Nombre: {user_profile.get('name', 'N/A')}
            - Edad: {user_profile.get('age', 'N/A')}
            - Nivel de actividad: {user_profile.get('activity_level', 'N/A')}
            - Objetivos de salud: {', '.join(user_profile.get('health_goals', ['N/A']))}
            - Condiciones: {', '.join(user_profile.get('conditions', ['N/A']))}
            """
        
        # Generar el análisis de patrones
        try:
            vertex_skill = VertexGeminiGenerateSkill()
            result = await vertex_skill.execute({
                "prompt": prompt,
                "temperature": 0.3,
                "model": "gemini-2.0-flash"
            })
            response = result.get("text", "")
        except Exception as e:
            logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
            # Fallback a cliente Gemini directo
            response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "patterns": ["No se pudieron identificar patrones"],
                    "correlations": ["No se pudieron identificar correlaciones"],
                    "influencing_factors": ["No se pudieron identificar factores"],
                    "recommendations": ["Recomendaciones no disponibles"],
                    "possible_causes": ["No se pudieron identificar causas"]
                }
        
        return response
    
    async def _generate_trend_analysis(self, input_text: str, biometric_data: Dict[str, Any], 
                                     user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera un análisis de tendencias de datos biométricos estructurado.
        
        Args:
            input_text: Texto de entrada del usuario
            biometric_data: Datos biométricos del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Análisis de tendencias estructurado
        """
        prompt = f"""
        Genera un análisis de tendencias en datos biométricos estructurado basado en la siguiente solicitud:
        
        "{input_text}"
        
        Datos biométricos disponibles:
        {json.dumps(biometric_data, indent=2)}
        
        El análisis debe incluir:
        1. Tendencias identificadas a lo largo del tiempo
        2. Cambios significativos en métricas clave
        3. Progreso hacia objetivos
        4. Proyecciones futuras
        5. Recomendaciones basadas en tendencias
        
        Devuelve el análisis en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Nombre: {user_profile.get('name', 'N/A')}
            - Edad: {user_profile.get('age', 'N/A')}
            - Nivel de actividad: {user_profile.get('activity_level', 'N/A')}
            - Objetivos de salud: {', '.join(user_profile.get('health_goals', ['N/A']))}
            - Condiciones: {', '.join(user_profile.get('conditions', ['N/A']))}
            """
        
        # Generar el análisis de tendencias
        try:
            vertex_skill = VertexGeminiGenerateSkill()
            result = await vertex_skill.execute({
                "prompt": prompt,
                "temperature": 0.3,
                "model": "gemini-2.0-flash"
            })
            response = result.get("text", "")
        except Exception as e:
            logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
            # Fallback a cliente Gemini directo
            response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "trends": ["No se pudieron identificar tendencias"],
                    "significant_changes": ["No se pudieron identificar cambios significativos"],
                    "progress": "Progreso no disponible",
                    "projections": ["Proyecciones no disponibles"],
                    "recommendations": ["Recomendaciones no disponibles"]
                }
        
        return response
    
    async def _generate_visualization(self, input_text: str, biometric_data: Dict[str, Any], 
                                    user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera una visualización de datos biométricos estructurada.
        
        Args:
            input_text: Texto de entrada del usuario
            biometric_data: Datos biométricos del usuario
            user_profile: Perfil del usuario
            
        Returns:
            Dict[str, Any]: Visualización estructurada
        """
        prompt = f"""
        Genera una descripción detallada de visualización de datos biométricos basada en la siguiente solicitud:
        
        "{input_text}"
        
        Datos biométricos disponibles:
        {json.dumps(biometric_data, indent=2)}
        
        La visualización debe incluir:
        1. Tipo de gráfico recomendado
        2. Métricas a visualizar
        3. Ejes y escalas
        4. Patrones destacados
        5. Interpretación de la visualización
        
        Devuelve la descripción en formato JSON estructurado.
        """
        
        # Añadir información del perfil si está disponible
        if user_profile:
            prompt += f"""
            
            Considera la siguiente información del usuario:
            - Nombre: {user_profile.get('name', 'N/A')}
            - Edad: {user_profile.get('age', 'N/A')}
            - Nivel de actividad: {user_profile.get('activity_level', 'N/A')}
            - Objetivos de salud: {', '.join(user_profile.get('health_goals', ['N/A']))}
            - Condiciones: {', '.join(user_profile.get('conditions', ['N/A']))}
            """
        
        # Generar la visualización
        try:
            vertex_skill = VertexGeminiGenerateSkill()
            result = await vertex_skill.execute({
                "prompt": prompt,
                "temperature": 0.3,
                "model": "gemini-2.0-flash"
            })
            response = result.get("text", "")
        except Exception as e:
            logger.warning(f"Error al usar VertexGeminiGenerateSkill: {e}")
            # Fallback a cliente Gemini directo
            response = await self.gemini_client.generate_structured_output(prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(response, dict):
            try:
                response = json.loads(response)
            except:
                # Si no se puede convertir, crear un diccionario básico
                response = {
                    "chart_type": "No se pudo determinar el tipo de gráfico",
                    "metrics": ["No se pudieron identificar métricas"],
                    "axes": {"x": "No disponible", "y": "No disponible"},
                    "highlighted_patterns": ["No se pudieron identificar patrones"],
                    "interpretation": "Interpretación no disponible"
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
    
    async def _process_request(self, input_text: str, user_id: Optional[str] = None, 
                           session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Procesa la solicitud del usuario y genera una respuesta utilizando las skills adecuadas.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            session_id: ID de la sesión (opcional)
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente
        """
        start_time = time.time()
        result = {}
        analysis_id = None
        response_text = ""
        response_type = "text"
        
        try:
            # Generar ID de usuario y sesión si no se proporcionan
            user_id = user_id or str(uuid.uuid4())
            session_id = session_id or str(uuid.uuid4())
            
            # Obtener contexto de la conversación
            context = await self._get_context(user_id, session_id)
            
            # Obtener perfil del usuario si está disponible
            user_profile = kwargs.get("user_profile", {})
            
            # Obtener datos biométricos del usuario
            # En un entorno real, esto se obtendría de una API o base de datos
            # Para este ejemplo, usamos datos de muestra
            biometric_data = kwargs.get("biometric_data", self._get_sample_biometric_data())
            
            # Analizar la entrada del usuario para determinar la skill a utilizar
            if any(keyword in input_text.lower() for keyword in ["visualiza", "gráfico", "muestra", "compara", "dashboard"]):
                # Usar skill de visualización de datos
                try:
                    result = await self.execute_skill("data_visualization", 
                                                   input_text=input_text, 
                                                   biometric_data=biometric_data,
                                                   user_profile=user_profile, 
                                                   context=context)
                    
                    # Generar respuesta
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        # Convertir resultado estructurado a texto
                        response_text = "Visualización de datos biométricos:\n\n"
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if key != "response":
                                    response_text += f"**{key.replace('_', ' ').title()}**: {value}\n"
                        else:
                            response_text = str(result)
                    
                    # Almacenar resultado en el estado
                    visualizations = self._state.get("visualizations", {})
                    analysis_id = str(uuid.uuid4())
                    visualizations[analysis_id] = result
                    self.update_state("visualizations", visualizations)
                    response_type = "data_visualization"
                    
                except Exception as e:
                    logger.error(f"Error al ejecutar skill data_visualization: {e}")
                    response_text = "Lo siento, ha ocurrido un error al visualizar tus datos biométricos."
                    result = {"error": str(e)}
                    analysis_id = None
                
            elif any(keyword in input_text.lower() for keyword in ["tendencia", "tendencias", "evolución", "cambio", "progreso"]):
                # Usar skill de análisis de tendencias
                try:
                    result = await self.execute_skill("trend_identification", 
                                                   input_text=input_text, 
                                                   biometric_data=biometric_data,
                                                   user_profile=user_profile, 
                                                   context=context)
                    
                    # Generar respuesta
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        # Convertir resultado estructurado a texto
                        response_text = "Análisis de tendencias biométricas:\n\n"
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if key != "response":
                                    response_text += f"**{key.replace('_', ' ').title()}**: {value}\n"
                        else:
                            response_text = str(result)
                    
                    # Almacenar resultado en el estado
                    trend_analyses = self._state.get("trend_analyses", {})
                    analysis_id = str(uuid.uuid4())
                    trend_analyses[analysis_id] = result
                    self.update_state("trend_analyses", trend_analyses)
                    response_type = "trend_analysis"
                    
                except Exception as e:
                    logger.error(f"Error al ejecutar skill trend_identification: {e}")
                    response_text = "Lo siento, ha ocurrido un error al analizar las tendencias de tus datos biométricos."
                    result = {"error": str(e)}
                    analysis_id = None
                
            elif any(keyword in input_text.lower() for keyword in ["patrón", "patrones", "relación", "correlación", "conexión"]):
                # Usar skill de reconocimiento de patrones
                try:
                    result = await self.execute_skill("pattern_recognition", 
                                                   input_text=input_text, 
                                                   biometric_data=biometric_data,
                                                   user_profile=user_profile, 
                                                   context=context)
                    
                    # Generar respuesta
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        # Convertir resultado estructurado a texto
                        response_text = "Reconocimiento de patrones biométricos:\n\n"
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if key != "response":
                                    response_text += f"**{key.replace('_', ' ').title()}**: {value}\n"
                        else:
                            response_text = str(result)
                    
                    # Almacenar resultado en el estado
                    pattern_analyses = self._state.get("pattern_analyses", {})
                    analysis_id = str(uuid.uuid4())
                    pattern_analyses[analysis_id] = result
                    self.update_state("pattern_analyses", pattern_analyses)
                    response_type = "pattern_analysis"
                    
                except Exception as e:
                    logger.error(f"Error al ejecutar skill pattern_recognition: {e}")
                    response_text = "Lo siento, ha ocurrido un error al reconocer patrones en tus datos biométricos."
                    result = {"error": str(e)}
                    analysis_id = None
                
            else:
                # Usar skill de análisis biométrico general
                try:
                    result = await self.execute_skill("biometric_analysis", 
                                                   input_text=input_text, 
                                                   biometric_data=biometric_data,
                                                   user_profile=user_profile, 
                                                   context=context)
                    
                    # Generar respuesta
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        # Convertir resultado estructurado a texto
                        response_text = "Análisis de datos biométricos:\n\n"
                        if isinstance(result, dict):
                            for key, value in result.items():
                                if key != "response":
                                    response_text += f"**{key.replace('_', ' ').title()}**: {value}\n"
                        else:
                            response_text = str(result)
                    
                    # Almacenar resultado en el estado
                    biometric_analyses = self._state.get("biometric_analyses", {})
                    analysis_id = str(uuid.uuid4())
                    biometric_analyses[analysis_id] = result
                    self.update_state("biometric_analyses", biometric_analyses)
                    response_type = "biometric_analysis"
                    
                except Exception as e:
                    logger.error(f"Error al ejecutar skill biometric_analysis: {e}")
                    response_text = "Lo siento, ha ocurrido un error al analizar tus datos biométricos."
                    result = {"error": str(e)}
                    analysis_id = None
            
            # Actualizar el contexto con la interacción
            context["history"] = context.get("history", []) + [{
                "user": input_text,
                "bot": response_text,
                "timestamp": time.time(),
                "analysis_type": response_type
            }]
            await self._update_context(context, user_id, session_id)
            
            # Devolver respuesta estandarizada según el protocolo A2A
            return {
                "agent_id": "biometrics_insight_engine",
                "version": "1.2.0",
                "response": {
                    "text": response_text,
                    "type": response_type,
                    "analysis_id": analysis_id,
                    "metadata": {
                        "generated_at": time.time(),
                        "model": "gemini-2.0-flash",
                        "prompt_tokens": len(input_text) // 4,  # Estimación aproximada
                        "completion_tokens": len(response_text) // 4  # Estimación aproximada
                    }
                },
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": time.time(),
                "conversation_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error al procesar solicitud: {e}")
            # Devolver respuesta de error estandarizada según el protocolo A2A
            return {
                "agent_id": "biometrics_insight_engine",
                "version": "1.2.0",
                "response": {
                    "text": f"Lo siento, ha ocurrido un error al procesar tu solicitud: {str(e)}",
                    "type": "error",
                    "metadata": {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "generated_at": time.time()
                    }
                },
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": time.time(),
                "conversation_id": session_id
            }

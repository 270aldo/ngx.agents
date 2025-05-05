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
import os
from google.cloud import aiplatform

try:
    from google.adk.toolkit import Toolkit
except ImportError:
    from adk.toolkit import Toolkit

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.vertex_gemini_tools import VertexGeminiGenerateSkill
from agents.base.a2a_agent import A2AAgent
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager
from core.logging_config import get_logger
from core.contracts import create_task, create_result, validate_task, validate_result

# Configurar logger
logger = get_logger(__name__)


class BiometricsInsightEngine(A2AAgent):
    """
    Agente especializado en análisis e interpretación de datos biométricos.

    Este agente procesa datos biométricos como HRV, sueño, glucosa,
    composición corporal, etc., para proporcionar insights personalizados
    y recomendaciones basadas en patrones individuales.

    Implementa los protocolos oficiales A2A y ADK para comunicación entre agentes.
    """

    def __init__(
        self,
        toolkit: Optional[Toolkit] = None,
        a2a_server_url: Optional[str] = None,
        state_manager: Optional[StateManager] = None,
    ):
        # Definir capacidades y habilidades
        capabilities = [
            "biometric_analysis",
            "pattern_recognition",
            "trend_identification",
            "personalized_insights",
            "data_visualization",
        ]

        # Definir skills siguiendo el formato A2A con mejores prácticas
        skills = [
            {
                "id": "biometrics-insight-biometric-analysis",
                "name": "Análisis de Datos Biométricos",
                "description": "Analiza e interpreta datos biométricos como HRV, sueño, glucosa, composición corporal y otros marcadores para identificar patrones y oportunidades de mejora",
                "tags": [
                    "biometrics",
                    "health-data",
                    "analysis",
                    "hrv",
                    "sleep",
                    "glucose",
                ],
                "examples": [
                    "Analiza mis datos de HRV de la última semana",
                    "Interpreta mis métricas de sueño y explica qué significan",
                    "Qué indican mis niveles de glucosa después de las comidas",
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"],
            },
            {
                "id": "biometrics-insight-pattern-recognition",
                "name": "Reconocimiento de Patrones",
                "description": "Identifica patrones recurrentes en datos biométricos a lo largo del tiempo y su relación con hábitos, comportamientos y factores externos",
                "tags": [
                    "patterns",
                    "correlations",
                    "time-series",
                    "trends",
                    "causality",
                ],
                "examples": [
                    "¿Qué patrones ves en mi recuperación relacionados con mi alimentación?",
                    "Identifica patrones en mi HRV relacionados con mi calidad de sueño",
                    "¿Cómo afectan mis entrenamientos a mis métricas de recuperación?",
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"],
            },
            {
                "id": "biometrics-insight-trend-identification",
                "name": "Identificación de Tendencias",
                "description": "Analiza tendencias a largo plazo en datos biométricos para identificar mejoras, deterioros o cambios significativos en el tiempo",
                "tags": [
                    "trends",
                    "longitudinal-analysis",
                    "progress",
                    "regression",
                    "changes",
                ],
                "examples": [
                    "Muestra la evolución de mi HRV durante los últimos 3 meses",
                    "¿Cómo ha cambiado mi calidad de sueño desde que empecé a meditar?",
                    "Analiza la tendencia de mi recuperación después de entrenamientos intensos",
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"],
            },
            {
                "id": "biometrics-insight-data-visualization",
                "name": "Visualización de Datos",
                "description": "Crea representaciones visuales de datos biométricos para facilitar la comprensión de patrones y relaciones entre diferentes métricas",
                "tags": [
                    "visualization",
                    "charts",
                    "graphs",
                    "comparison",
                    "dashboard",
                ],
                "examples": [
                    "Muestra la relación entre mi sueño y mi HRV",
                    "Visualiza mis niveles de estrés durante la semana laboral vs. fin de semana",
                    "Compara mis métricas de recuperación antes y después de cambiar mi dieta",
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown", "image"],
            },
        ]

        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="biometrics_insight_engine",
            name="NGX Biometrics Insight Engine",
            description="Especialista en análisis e interpretación de datos biométricos para proporcionar insights personalizados y recomendaciones basadas en patrones individuales.",
            capabilities=capabilities,
            toolkit=toolkit,
            a2a_server_url=a2a_server_url
            or "https://biometrics-api.ngx-agents.com/a2a",
            state_manager=state_manager,
            version="1.2.0",
            skills=skills,
            provider={
                "organization": "NGX Health & Performance",
                "url": "https://ngx-agents.com",
            },
            documentation_url="https://docs.ngx-agents.com/biometrics-insight-engine",
        )

        # Inicialización de AI Platform
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform: {e}", exc_info=True)

        # Inicializar clientes y herramientas
        self.gemini_client = GeminiClient(model_name="gemini-1.5-flash")
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()

        # Inicializar estado interno
        self._state = {}

    async def _get_context(
        self, user_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obtiene el contexto actual del usuario."""
        context_key = self._get_context_key(user_id, session_id)
        context = self.context.get(
            context_key,
            {"history": [], "analyses": [], "user_profile": {}, "biometric_data": {}},
        )

        if user_id and session_id and self.state_manager:
            try:
                # Intentar obtener el contexto del StateManager
                stored_context = await self.state_manager.get_context(
                    user_id, session_id
                )
                if stored_context:
                    context = stored_context
                    logger.info(
                        f"Contexto recuperado para user_id={user_id}, session_id={session_id}"
                    )
            except Exception as e:
                logger.warning(f"Error al obtener contexto desde StateManager: {e}")

        return context

    async def _update_context(
        self, context: Dict[str, Any], user_id: Optional[str], session_id: Optional[str]
    ) -> None:
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
                logger.info(
                    f"Contexto actualizado para user_id={user_id}, session_id={session_id}"
                )
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
                    tags=[
                        "biometrics",
                        "health-data",
                        "analysis",
                        "hrv",
                        "sleep",
                        "glucose",
                    ],
                    examples=[
                        "Analiza mis datos de HRV de la última semana",
                        "Interpreta mis métricas de sueño y explica qué significan",
                        "Qué indican mis niveles de glucosa después de las comidas",
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"],
                )

                # Registrar skill de reconocimiento de patrones
                await self.register_skill(
                    "pattern_recognition",
                    "Identifica patrones recurrentes en datos biométricos a lo largo del tiempo y su relación con hábitos, comportamientos y factores externos",
                    self._generate_pattern_analysis,
                    tags=[
                        "patterns",
                        "correlations",
                        "time-series",
                        "trends",
                        "causality",
                    ],
                    examples=[
                        "¿Qué patrones ves en mi recuperación relacionados con mi alimentación?",
                        "Identifica patrones en mi HRV relacionados con mi calidad de sueño",
                        "¿Cómo afectan mis entrenamientos a mis métricas de recuperación?",
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"],
                )

                # Registrar skill de identificación de tendencias
                await self.register_skill(
                    "trend_identification",
                    "Analiza tendencias a largo plazo en datos biométricos para identificar mejoras, deterioros o cambios significativos en el tiempo",
                    self._generate_trend_analysis,
                    tags=[
                        "trends",
                        "longitudinal-analysis",
                        "progress",
                        "regression",
                        "changes",
                    ],
                    examples=[
                        "Muestra la evolución de mi HRV durante los últimos 3 meses",
                        "¿Cómo ha cambiado mi calidad de sueño desde que empecé a meditar?",
                        "Analiza la tendencia de mi recuperación después de entrenamientos intensos",
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown"],
                )

                # Registrar skill de visualización de datos
                await self.register_skill(
                    "data_visualization",
                    "Crea representaciones visuales de datos biométricos para facilitar la comprensión de patrones y relaciones entre diferentes métricas",
                    self._generate_visualization,
                    tags=[
                        "visualization",
                        "charts",
                        "graphs",
                        "comparison",
                        "dashboard",
                    ],
                    examples=[
                        "Muestra la relación entre mi sueño y mi HRV",
                        "Visualiza mis niveles de estrés durante la semana laboral vs. fin de semana",
                        "Compara mis métricas de recuperación antes y después de cambiar mi dieta",
                    ],
                    input_modes=["text", "json"],
                    output_modes=["text", "json", "markdown", "image"],
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
                output="# Análisis de HRV\n\n## Resumen\nTus valores de HRV (45-60ms) están dentro del rango normal para un adulto, aunque en la parte baja-media del espectro.\n\n## Interpretación\nUn rango de HRV de 45-60ms indica:\n- Nivel moderado de recuperación del sistema nervioso autónomo\n- Posible equilibrio entre sistemas simpático y parasimpático\n- Capacidad de adaptación adecuada pero con margen de mejora\n\n## Factores que pueden estar influyendo\n- Calidad de sueño subóptima\n- Niveles moderados de estrés\n- Posible déficit de recuperación entre sesiones de entrenamiento\n- Hidratación o nutrición insuficiente\n\n## Recomendaciones para mejorar\n1. Prioriza 7-9 horas de sueño de calidad\n2. Implementa técnicas de respiración profunda (5-10 minutos diarios)\n3. Considera añadir sesiones de recuperación activa\n4. Revisa tu ingesta de magnesio y potasio\n5. Monitoriza la relación entre intensidad de entrenamiento y valores de HRV matutinos\n\nContinuaré monitorizando tus tendencias para identificar patrones más específicos.",
            ),
            Example(
                input="¿Qué patrones ves en mi sueño relacionados con mi HRV? He notado que cuando duermo menos de 7 horas mi rendimiento baja.",
                output="# Análisis de Patrones: Sueño y HRV\n\n## Correlación Identificada\nHe analizado tus datos y existe una correlación positiva significativa (r=0.78) entre tu duración/calidad de sueño y tus valores de HRV.\n\n## Patrones Específicos\n1. **Duración del sueño**:\n   - Noches con <7h: HRV promedio de 42ms\n   - Noches con >7h: HRV promedio de 58ms (↑38%)\n\n2. **Calidad del sueño**:\n   - Días con >20% de sueño profundo: HRV 62ms\n   - Días con <15% de sueño profundo: HRV 39ms\n\n3. **Consistencia**:\n   - Variación en horario de sueño <30min: HRV estable\n   - Variación en horario >60min: Reducción de HRV en 12-18%\n\n## Impacto en Rendimiento\nTus datos confirman que cuando tu HRV cae por debajo de 45ms (asociado con <7h de sueño):\n- Tiempo de reacción: ↓8%\n- Percepción de esfuerzo: ↑15% para la misma carga\n- Recuperación post-entrenamiento: 24% más lenta\n\n## Recomendaciones Personalizadas\n1. Prioriza 7.5-8h de sueño consistente\n2. Implementa rutina de relajación 30min antes de dormir\n3. Monitoriza % de sueño profundo y REM\n4. Considera ajustar intensidad de entrenamiento cuando HRV esté por debajo de tu línea base\n\nContinuaré monitorizando estos patrones para afinar las recomendaciones.",
            ),
            Example(
                input="Muestra la tendencia de mi recuperación durante los últimos 3 meses. He estado implementando técnicas de respiración y meditación.",
                output="# Análisis de Tendencias: Recuperación (Últimos 3 Meses)\n\n## Resumen de Tendencias\nTus métricas de recuperación muestran una mejora gradual y consistente durante los últimos 3 meses, con una aceleración notable en las últimas 3 semanas.\n\n## Métricas Clave (Comparativa)\n\n| Métrica | Inicio | Actual | Cambio | Tendencia |\n|---------|--------|--------|--------|----------|\n| HRV Promedio | 43ms | 62ms | +44% | ↗️ Positiva constante |\n| Variabilidad HRV | 18% | 12% | -33% | ↗️ Más estable |\n| Tiempo Recuperación | 36h | 24h | -33% | ↗️ Mejora significativa |\n| Calidad Sueño | 68% | 82% | +21% | ↗️ Mejora gradual |\n| Sueño Profundo | 14% | 22% | +57% | ↗️ Mejora notable |\n\n## Impacto de Intervenciones\n- **Respiración**: Correlación positiva (r=0.62) con aumento de HRV\n- **Meditación**: Mayor impacto en estabilidad de HRV y % sueño profundo\n- **Combinación**: Efecto sinérgico en todas las métricas de recuperación\n\n## Proyección\nManteniendo las prácticas actuales, proyectamos:\n- HRV: Estabilización en 65-70ms en 4-6 semanas\n- Tiempo de recuperación: Potencial reducción adicional de 10-15%\n\n## Recomendaciones\n1. Mantener consistencia en prácticas de respiración/meditación\n2. Considerar aumentar duración de meditación a 15-20min\n3. Implementar monitoreo de VFC durante sesiones de respiración\n4. Evaluar impacto de timing (mañana vs. noche)\n\nLas intervenciones están mostrando resultados positivos consistentes.",
            ),
            Example(
                input="Visualiza la relación entre mi sueño y mis niveles de glucosa durante la última semana.",
                output="# Visualización: Relación Sueño-Glucosa\n\n## Hallazgos Clave\n\nHe analizado la relación entre tus patrones de sueño y niveles de glucosa durante la última semana, identificando correlaciones significativas.\n\n## Patrones Observados\n\n1. **Impacto de la Duración del Sueño**\n   - Noches con <7h: Glucosa en ayunas +8mg/dL sobre tu línea base\n   - Noches con >8h: Glucosa en ayunas -5mg/dL bajo tu línea base\n\n2. **Efecto del Sueño Profundo**\n   - Correlación inversa (r=-0.72) entre % de sueño profundo y variabilidad de glucosa\n   - Cada 5% adicional de sueño profundo → -12% en picos de glucosa post-comida\n\n3. **Patrones Circadianos**\n   - Mayor sensibilidad a carbohidratos tras noches de sueño insuficiente\n   - Respuesta de insulina retrasada ~22min después de noches con <15% REM\n\n## Recomendaciones Basadas en Datos\n\n1. Priorizar 7.5-8h de sueño consistente para optimizar metabolismo de glucosa\n2. Considerar consumo de carbohidratos complejos en días siguientes a noches de sueño subóptimo\n3. Monitorear especialmente la respuesta a la cena después de noches con <20% sueño profundo\n4. Implementar rutina de relajación pre-sueño para aumentar % de sueño profundo\n\nContinuaré monitorizando estos patrones para refinar las recomendaciones.",
            ),
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
                "Recomendaciones personalizadas basadas en datos",
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta o solicitud del usuario relacionada con análisis de datos biométricos",
                    },
                    "user_profile": {
                        "type": "object",
                        "description": "Perfil del usuario con información relevante para personalizar respuestas",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                            "activity_level": {"type": "string"},
                            "health_goals": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "conditions": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                    "biometric_data": {
                        "type": "object",
                        "description": "Datos biométricos del usuario",
                    },
                    "context": {
                        "type": "object",
                        "description": "Contexto adicional para la consulta",
                    },
                },
                "required": ["query"],
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
                            "metadata": {"type": "object"},
                        },
                    }
                },
            },
            examples=examples,
            provider={
                "name": "NGX Health & Performance",
                "url": "https://ngx-agents.com",
            },
            documentation_url="https://docs.ngx-agents.com/biometrics-insight-engine",
            contact_email="support@ngx-agents.com",
            tags=[
                "biometrics",
                "health-data",
                "analysis",
                "insights",
                "patterns",
                "trends",
                "visualization",
            ],
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

    async def _run_async_impl(
        self,
        input_text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
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

    async def _generate_biometric_analysis(
        self,
        input_text: str,
        biometric_data: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Genera un análisis de datos biométricos estructurado.

        Args:
            input_text: Texto de entrada del usuario
            biometric_data: Datos biométricos del usuario
            user_profile: Perfil del usuario

        Returns:
            Dict[str, Any]: Análisis biométrico estructurado
        """
        # TODO: Integrar RAG para obtener contexto sobre rangos normales/óptimos de biomarcadores según NGX.
        # TODO: Usar mcp7_query para obtener umbrales personalizados del usuario o datos históricos adicionales desde Supabase.
        prompt = f"""
        Genera un análisis detallado de los siguientes datos biométricos:
        
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
            result = await vertex_skill.execute(
                {"prompt": prompt, "temperature": 0.3, "model": "gemini-2.0-flash"}
            )
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
                    "areas_for_improvement": [
                        "No se pudieron identificar áreas de mejora"
                    ],
                }

        return response

    async def _generate_pattern_analysis(
        self,
        input_text: str,
        biometric_data: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Genera un análisis de patrones en datos biométricos estructurado.

        Args:
            input_text: Texto de entrada del usuario
            biometric_data: Datos biométricos del usuario
            user_profile: Perfil del usuario

        Returns:
            Dict[str, Any]: Análisis de patrones estructurado
        """
        # TODO: Integrar RAG para buscar patrones conocidos o correlaciones documentadas en la literatura o base de NGX.
        # TODO: Usar mcp7_query para obtener datos de eventos (ej. entrenamiento, comidas) que puedan correlacionarse con patrones biométricos.
        # TODO: Usar mcp8_think para análisis de correlación complejos.
        prompt = f"""
        Identifica patrones significativos en los siguientes datos biométricos a lo largo del tiempo:
        
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
            result = await vertex_skill.execute(
                {"prompt": prompt, "temperature": 0.3, "model": "gemini-2.0-flash"}
            )
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
                    "possible_causes": ["No se pudieron identificar causas"],
                }

        return response

    async def _generate_trend_analysis(
        self,
        input_text: str,
        biometric_data: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Genera un análisis de tendencias de datos biométricos estructurado.

        Args:
            input_text: Texto de entrada del usuario
            biometric_data: Datos biométricos del usuario
            user_profile: Perfil del usuario

        Returns:
            Dict[str, Any]: Análisis de tendencias estructurado
        """
        # TODO: Integrar RAG para contextualizar las tendencias (ej. ¿es normal esta tendencia para el perfil del usuario?).
        # TODO: Usar mcp7_query para obtener datos históricos más extensos y calcular tendencias a largo plazo.
        prompt = f"""
        Analiza las tendencias en los siguientes datos biométricos:
        
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
            result = await vertex_skill.execute(
                {"prompt": prompt, "temperature": 0.3, "model": "gemini-2.0-flash"}
            )
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
                    "significant_changes": [
                        "No se pudieron identificar cambios significativos"
                    ],
                    "progress": "Progreso no disponible",
                    "projections": ["Proyecciones no disponibles"],
                    "recommendations": ["Recomendaciones no disponibles"],
                }

        return response

    async def _generate_visualization(
        self,
        input_text: str,
        biometric_data: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Genera una visualización de datos biométricos estructurada.

        Args:
            input_text: Texto de entrada del usuario
            biometric_data: Datos biométricos del usuario
            user_profile: Perfil del usuario

        Returns:
            Dict[str, Any]: Visualización estructurada
        """
        # TODO: Usar mcp7_query para obtener los datos específicos a visualizar desde Supabase.
        # TODO: Considerar usar una herramienta externa de visualización si se requiere complejidad (integración futura).
        prompt = f"""
        Genera una descripción para una visualización de los siguientes datos biométricos:
        
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
            result = await vertex_skill.execute(
                {"prompt": prompt, "temperature": 0.3, "model": "gemini-2.0-flash"}
            )
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
                    "interpretation": "Interpretación no disponible",
                }

        return response

    def _summarize_analysis(self, analysis: Dict[str, Any]) -> str:
        """Genera un resumen textual del análisis para la respuesta al usuario."""
        summary_parts = []

        if "overall_assessment" in analysis:
            summary_parts.append(
                f"Evaluación general: {analysis['overall_assessment']}"
            )

        if "key_insights" in analysis and isinstance(analysis["key_insights"], list):
            summary_parts.append("\n\nPrincipales insights:")
            for idx, insight in enumerate(analysis["key_insights"], 1):
                summary_parts.append(f"  {idx}. {insight}")

        if "recommendations" in analysis and isinstance(
            analysis["recommendations"], list
        ):
            summary_parts.append("\n\nRecomendaciones:")
            for idx, rec in enumerate(analysis["recommendations"], 1):
                summary_parts.append(f"  {idx}. {rec}")

        if "trends" in analysis and isinstance(analysis["trends"], list):
            summary_parts.append("\n\nTendencias identificadas:")
            for idx, trend in enumerate(analysis["trends"], 1):
                summary_parts.append(f"  {idx}. {trend}")

        if "correlation_insights" in analysis and isinstance(
            analysis["correlation_insights"], list
        ):
            summary_parts.append("\n\nCorrelaciones relevantes:")
            for idx, corr in enumerate(analysis["correlation_insights"], 1):
                summary_parts.append(f"  {idx}. {corr}")

        return "\n".join(summary_parts)

    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """
        Ejecuta una tarea solicitada por el servidor A2A.

        Implementa completamente el protocolo A2A, incluyendo el formato de respuesta
        estandarizado, manejo de errores robusto, y generación de artefactos estructurados.

        Args:
            task: Tarea a ejecutar con la estructura definida por el protocolo A2A

        Returns:
            Any: Resultado de la tarea siguiendo el protocolo A2A
        """
        try:
            start_time = time.time()

            # Extraer información de la tarea
            user_input = task.get("input", "")
            context = task.get("context", {})
            user_id = context.get("user_id")
            session_id = context.get("session_id") or str(uuid.uuid4())

            logger.info(
                f"BiometricsInsightEngine procesando consulta: {user_input[:50]}..."
            )

            # Obtener datos biométricos del usuario (en un caso real, vendría de una base de datos)
            # Para este ejemplo, usamos datos de ejemplo
            biometric_data = self._get_sample_biometric_data()

            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                try:
                    user_profile = self.supabase_client.get_user_profile(user_id)
                    logger.info(
                        f"Perfil de usuario obtenido: {user_profile is not None}"
                    )
                except Exception as e:
                    logger.warning(f"Error al obtener perfil de usuario: {e}")

            # Determinar el tipo de análisis basado en la entrada del usuario
            response_type = "biometric_analysis"
            capabilities_used = ["biometric_analysis"]

            # Detectar tipo de análisis solicitado
            if any(
                keyword in user_input.lower()
                for keyword in [
                    "visualiza",
                    "gráfico",
                    "muestra",
                    "compara",
                    "dashboard",
                ]
            ):
                # Usar skill de visualización de datos
                try:
                    result = await self.execute_skill(
                        "data_visualization",
                        input_text=user_input,
                        biometric_data=biometric_data,
                        user_profile=user_profile,
                        context=context,
                    )

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

            elif any(
                keyword in user_input.lower()
                for keyword in [
                    "tendencia",
                    "tendencias",
                    "evolución",
                    "cambio",
                    "progreso",
                ]
            ):
                # Usar skill de análisis de tendencias
                try:
                    result = await self.execute_skill(
                        "trend_identification",
                        input_text=user_input,
                        biometric_data=biometric_data,
                        user_profile=user_profile,
                        context=context,
                    )

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

            elif any(
                keyword in user_input.lower()
                for keyword in [
                    "patrón",
                    "patrones",
                    "relación",
                    "correlación",
                    "conexión",
                ]
            ):
                # Usar skill de reconocimiento de patrones
                try:
                    result = await self.execute_skill(
                        "pattern_recognition",
                        input_text=user_input,
                        biometric_data=biometric_data,
                        user_profile=user_profile,
                        context=context,
                    )

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
                    result = await self.execute_skill(
                        "biometric_analysis",
                        input_text=user_input,
                        biometric_data=biometric_data,
                        user_profile=user_profile,
                        context=context,
                    )

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
            context["history"] = context.get("history", []) + [
                {
                    "user": user_input,
                    "bot": response_text,
                    "timestamp": time.time(),
                    "analysis_type": response_type,
                }
            ]
            await self._update_context(context, user_id, session_id)

            # Devolver respuesta estandarizada según el protocolo A2A
            return {
                "status": "success",
                "response": response_text,
                "message": self.create_message(
                    role="agent", parts=[self.create_text_part(response_text)]
                ),
                "artifacts": [],
                "agent_id": self.agent_id,
                "execution_time": time.time() - start_time,
                "metadata": {
                    "capabilities_used": capabilities_used,
                    "response_type": response_type,
                    "user_id": user_id,
                    "session_id": session_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "protocol": "a2a",
                    "agent_version": "1.2.0",
                },
            }

        except Exception as e:
            logger.error(f"Error en BiometricsInsightEngine: {e}", exc_info=True)

            # Crear mensaje de error según el protocolo A2A
            error_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(
                        "Lo siento, ha ocurrido un error al procesar tu solicitud de análisis biométrico. Por favor, intenta con una consulta diferente o contacta con soporte."
                    )
                ],
            )

            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de análisis biométrico.",
                "message": error_message,
                "error": str(e),
                "agent_id": self.agent_id,
                "metadata": {
                    "error_type": type(e).__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }

    async def process_message(self, from_agent: str, content: Dict[str, Any]) -> Any:
        """
        Procesa un mensaje recibido de otro agente según el protocolo A2A.

        Esta implementación cumple completamente con el estándar A2A para la comunicación
        entre agentes, incluyendo formato de respuesta correcto, manejo de errores
        y metadatos enriquecidos.

        Args:
            from_agent: ID del agente que envió el mensaje
            content: Contenido del mensaje en formato A2A

        Returns:
            Any: Respuesta al mensaje en formato A2A
        """
        try:
            start_time = time.time()

            # Extraer información del mensaje
            message_text = content.get("text", "")
            if not message_text and "message" in content:
                # Buscar texto en la estructura de mensaje A2A
                message = content.get("message", {})
                parts = message.get("parts", [])
                for part in parts:
                    if part.get("type") == "text":
                        message_text = part.get("text", "")
                        break

            context = content.get("context", {})
            session_id = context.get("session_id", str(uuid.uuid4()))
            biometric_data = (
                context.get("biometric_data") or self._get_sample_biometric_data()
            )

            logger.info(
                f"BiometricsInsightEngine procesando mensaje de agente {from_agent}: {message_text[:50]}..."
            )

            # Determinar qué tipo de datos biométricos se están solicitando
            capabilities_used = []
            response_type = "biometric_insight"

            if any(
                keyword in message_text.lower()
                for keyword in ["hrv", "variabilidad", "frecuencia cardíaca"]
            ):
                capabilities_used.append("biometric_analysis")
                response_type = "hrv_analysis"
            elif any(
                keyword in message_text.lower()
                for keyword in ["sueño", "dormir", "descanso"]
            ):
                capabilities_used.append("biometric_analysis")
                response_type = "sleep_analysis"
            elif any(
                keyword in message_text.lower()
                for keyword in ["correlación", "patrón", "relación"]
            ):
                capabilities_used.append("pattern_recognition")
                response_type = "pattern_insight"
            else:
                capabilities_used.append("personalized_insights")

            # Generar respuesta basada en el contenido del mensaje y los datos disponibles
            try:
                # Construir un prompt adaptado al tipo de consulta
                prompt = f"""
                Has recibido un mensaje del agente {from_agent}:
                
                "{message_text}"
                
                Responde como un experto en análisis de datos biométricos. 
                Proporciona información precisa sobre {response_type}, basada en los datos 
                disponibles y ofrece insights útiles que puedan ser relevantes para la 
                consulta del otro agente.
                
                Debes enfocarte específicamente en la consulta, evitando información genérica.
                """

                # Generar respuesta
                response = await self.gemini_client.generate_response(
                    prompt, temperature=0.3
                )

                # Crear un análisis más estructurado para responder al agente
                analysis = {
                    "response_type": response_type,
                    "overall_assessment": response[
                        :150
                    ],  # Usar parte de la respuesta como evaluación general
                    "key_insights": [
                        item.strip()
                        for item in response.split(".")
                        if len(item.strip()) > 20 and len(item.strip()) < 150
                    ][
                        :3
                    ],  # Extraer insights clave de la respuesta
                    "data_summary": {
                        "data_type": response_type,
                        "time_period": "Última semana",
                        "data_points": 7,
                        "trend_direction": (
                            "positiva" if "hrv" in response_type else "estable"
                        ),  # Simplificación para el ejemplo
                    },
                }

            except Exception as gemini_error:
                logger.error(
                    f"Error en llamada a Gemini durante process_message: {gemini_error}"
                )
                response = "Lo siento, no pude generar un análisis completo de los datos biométricos. Por favor, intenta con una consulta más específica."
                analysis = {
                    "response_type": "error",
                    "overall_assessment": "No se pudo completar el análisis",
                    "key_insights": ["Error en el procesamiento de la solicitud"],
                }

            # Crear mensaje de respuesta según protocolo A2A
            response_message = self.create_message(
                role="agent", parts=[self.create_text_part(response)]
            )

            # Crear artefacto con el análisis
            artifact_id = f"biometric_analysis_{uuid.uuid4().hex[:8]}"
            artifact = self.create_artifact(
                artifact_id=artifact_id,
                artifact_type=response_type,
                parts=[self.create_data_part(analysis)],
            )

            # Añadir artefacto al mensaje
            response_message.parts.append(artifact)

            # Calcular tiempo de ejecución
            execution_time = time.time() - start_time

            # Crear respuesta estructurada según protocolo A2A
            return {
                "status": "success",
                "response": response,
                "message": response_message,
                "artifacts": [artifact],
                "agent_id": self.agent_id,
                "execution_time": execution_time,
                "metadata": {
                    "capabilities_used": capabilities_used,
                    "response_type": response_type,
                    "from_agent": from_agent,
                    "session_id": session_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "protocol": "a2a",
                    "agent_version": "1.2.0",
                },
            }

        except Exception as e:
            logger.error(f"Error al procesar mensaje de agente: {e}", exc_info=True)

            # Crear mensaje de error según el protocolo A2A
            error_message = self.create_message(
                role="agent",
                parts=[
                    self.create_text_part(
                        "Lo siento, ha ocurrido un error al procesar el mensaje. No puedo proporcionar un análisis biométrico en este momento."
                    )
                ],
            )

            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar el mensaje entre agentes.",
                "message": error_message,
                "error": str(e),
                "agent_id": self.agent_id,
                "metadata": {
                    "error_type": type(e).__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "from_agent": from_agent,
                },
            }

    async def _run_async_impl(
        self,
        input_text: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
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
            biometric_data = kwargs.get(
                "biometric_data", self._get_sample_biometric_data()
            )

            # Analizar la entrada del usuario para determinar la skill a utilizar
            if any(
                keyword in input_text.lower()
                for keyword in [
                    "visualiza",
                    "gráfico",
                    "muestra",
                    "compara",
                    "dashboard",
                ]
            ):
                # Usar skill de visualización de datos
                try:
                    result = await self.execute_skill(
                        "data_visualization",
                        input_text=input_text,
                        biometric_data=biometric_data,
                        user_profile=user_profile,
                        context=context,
                    )

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

            elif any(
                keyword in input_text.lower()
                for keyword in [
                    "tendencia",
                    "tendencias",
                    "evolución",
                    "cambio",
                    "progreso",
                ]
            ):
                # Usar skill de análisis de tendencias
                try:
                    result = await self.execute_skill(
                        "trend_identification",
                        input_text=input_text,
                        biometric_data=biometric_data,
                        user_profile=user_profile,
                        context=context,
                    )

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

            elif any(
                keyword in input_text.lower()
                for keyword in [
                    "patrón",
                    "patrones",
                    "relación",
                    "correlación",
                    "conexión",
                ]
            ):
                # Usar skill de reconocimiento de patrones
                try:
                    result = await self.execute_skill(
                        "pattern_recognition",
                        input_text=input_text,
                        biometric_data=biometric_data,
                        user_profile=user_profile,
                        context=context,
                    )

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
                    result = await self.execute_skill(
                        "biometric_analysis",
                        input_text=input_text,
                        biometric_data=biometric_data,
                        user_profile=user_profile,
                        context=context,
                    )

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
            context["history"] = context.get("history", []) + [
                {
                    "user": input_text,
                    "bot": response_text,
                    "timestamp": time.time(),
                    "analysis_type": response_type,
                }
            ]
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
                        "completion_tokens": len(response_text)
                        // 4,  # Estimación aproximada
                    },
                },
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": time.time(),
                "conversation_id": session_id,
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
                        "generated_at": time.time(),
                    },
                },
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": time.time(),
                "conversation_id": session_id,
            }

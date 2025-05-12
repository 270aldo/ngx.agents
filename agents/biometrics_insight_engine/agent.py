"""
Agente especializado en análisis e interpretación de datos biométricos.

Este agente procesa datos biométricos como HRV, sueño, glucosa,
composición corporal, etc., para proporcionar insights personalizados
y recomendaciones basadas en patrones individuales.

Implementa los protocolos oficiales ADK y A2A para comunicación entre agentes.
"""

import logging
import uuid
import time
import json
import os
from typing import Dict, Any, Optional, List, Union
from google.cloud import aiplatform

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from agents.base.adk_agent import ADKAgent
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from core.logging_config import get_logger

# Importar Skill y Toolkit desde adk.agent
from adk.agent import Skill
from adk.toolkit import Toolkit

# Importar esquemas para las skills
from agents.biometrics_insight_engine.schemas import (
    BiometricAnalysisInput, BiometricAnalysisOutput,
    PatternRecognitionInput, PatternRecognitionOutput,
    TrendIdentificationInput, TrendIdentificationOutput,
    DataVisualizationInput, DataVisualizationOutput,
    BiometricAnalysisArtifact, BiometricVisualizationArtifact
)

# Configurar logger
logger = get_logger(__name__)


class BiometricsInsightEngine(ADKAgent):
    """
    Agente especializado en análisis e interpretación de datos biométricos.

    Este agente procesa datos biométricos como HRV, sueño, glucosa,
    composición corporal, etc., para proporcionar insights personalizados
    y recomendaciones basadas en patrones individuales.

    Implementa los protocolos oficiales ADK y A2A para comunicación entre agentes.
    """
    
    AGENT_ID = "biometrics_insight_engine"
    AGENT_NAME = "NGX Biometrics Insight Engine"
    AGENT_DESCRIPTION = "Especialista en análisis e interpretación de datos biométricos para proporcionar insights personalizados y recomendaciones basadas en patrones individuales."
    DEFAULT_INSTRUCTION = """
    Eres un especialista en análisis e interpretación de datos biométricos.
    Tu objetivo es proporcionar insights personalizados y recomendaciones basadas en patrones individuales.
    Analiza datos biométricos como HRV, sueño, glucosa, composición corporal, etc., para identificar patrones y tendencias.
    Tus análisis deben ser precisos, basados en evidencia y personalizados para cada usuario.
    """
    DEFAULT_MODEL = "gemini-1.5-flash"
    
    def __init__(
        self,
        state_manager: StateManager,
        mcp_toolkit: Optional[MCPToolkit] = None,
        a2a_server_url: Optional[str] = None,
        model: Optional[str] = None,
        instruction: Optional[str] = None,
        agent_id: str = AGENT_ID,
        name: str = AGENT_NAME,
        description: str = AGENT_DESCRIPTION,
        **kwargs
    ):
        """
        Inicializa el agente BiometricsInsightEngine.
        
        Args:
            state_manager: Gestor de estado para persistencia
            mcp_toolkit: Toolkit de MCP para herramientas adicionales
            a2a_server_url: URL del servidor A2A
            model: Modelo de Gemini a utilizar
            instruction: Instrucciones del sistema
            agent_id: ID del agente
            name: Nombre del agente
            description: Descripción del agente
            **kwargs: Argumentos adicionales para la clase base
        """
        _model = model or self.DEFAULT_MODEL
        _instruction = instruction or self.DEFAULT_INSTRUCTION
        _mcp_toolkit = mcp_toolkit if mcp_toolkit is not None else MCPToolkit()
        
        # Crear directorio temporal para visualizaciones si es necesario
        self.tmp_dir = os.path.join(os.getcwd(), "tmp", "biometrics_viz")
        os.makedirs(self.tmp_dir, exist_ok=True)
        
        # Definir las skills antes de llamar al constructor de ADKAgent
        self.skills = [
            Skill(
                name="biometric_analysis",
                description="Analiza e interpreta datos biométricos como HRV, sueño, glucosa, composición corporal y otros marcadores",
                handler=self._skill_biometric_analysis,
                input_schema=BiometricAnalysisInput,
                output_schema=BiometricAnalysisOutput
            ),
            Skill(
                name="pattern_recognition",
                description="Identifica patrones recurrentes en datos biométricos y su relación con hábitos y comportamientos",
                handler=self._skill_pattern_recognition,
                input_schema=PatternRecognitionInput,
                output_schema=PatternRecognitionOutput
            ),
            Skill(
                name="trend_identification",
                description="Analiza tendencias a largo plazo en datos biométricos para identificar mejoras o cambios significativos",
                handler=self._skill_trend_identification,
                input_schema=TrendIdentificationInput,
                output_schema=TrendIdentificationOutput
            ),
            Skill(
                name="data_visualization",
                description="Crea representaciones visuales de datos biométricos para facilitar la comprensión de patrones",
                handler=self._skill_data_visualization,
                input_schema=DataVisualizationInput,
                output_schema=DataVisualizationOutput
            )
        ]
        
        # Definir las capacidades del agente
        _capabilities = [
            "biometric_analysis",
            "pattern_recognition",
            "trend_identification",
            "personalized_insights",
            "data_visualization",
        ]
        
        # Crear un toolkit de ADK
        adk_toolkit = Toolkit()
        
        # Inicializar el agente ADK
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            model=_model,
            instruction=_instruction,
            state_manager=state_manager,
            adk_toolkit=adk_toolkit,
            capabilities=_capabilities,
            a2a_server_url=a2a_server_url,
            **kwargs
        )
        
        # Configurar clientes adicionales
        self.gemini_client = GeminiClient(model_name=self.model)
        self.supabase_client = SupabaseClient()
        
        # Inicializar Vertex AI
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform (Vertex AI SDK) inicializado correctamente para BiometricsInsightEngine.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform para BiometricsInsightEngine: {e}", exc_info=True)
            
        logger.info(f"{self.name} ({self.agent_id}) inicializado con integración oficial de Google ADK.")
    
    async def _get_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el StateManager.

        Args:
            user_id (Optional[str]): ID del usuario.
            session_id (Optional[str]): ID de la sesión.

        Returns:
            Dict[str, Any]: Contexto de la conversación.
        """
        context_key = f"context_{user_id}_{session_id}" if user_id and session_id else f"context_default_{uuid.uuid4().hex[:6]}"
        
        try:
            # Intentar cargar desde StateManager (si está disponible)
            if self.state_manager and user_id and session_id:
                try:
                    state_data = await self.state_manager.load_state(context_key)
                    if state_data and isinstance(state_data, dict):
                        logger.debug(f"Contexto cargado desde StateManager para key={context_key}")
                        return state_data
                except Exception as e:
                    logger.warning(f"Error al cargar contexto desde StateManager: {e}")
            
            # Si no hay contexto o hay error, crear uno nuevo
            return {
                "conversation_history": [],
                "user_profile": {},
                "analyses": [],
                "biometric_data": {},
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.error(f"Error al obtener contexto: {e}", exc_info=True)
            # En caso de error, devolver un contexto vacío
            return {
                "conversation_history": [],
                "user_profile": {},
                "analyses": [],
                "biometric_data": {},
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }

    async def _update_context(self, context: Dict[str, Any], user_id: str, session_id: str) -> None:
        """
        Actualiza el contexto de la conversación en el StateManager.

        Args:
            context (Dict[str, Any]): Contexto actualizado.
            user_id (str): ID del usuario.
            session_id (str): ID de la sesión.
        """
        context_key = f"context_{user_id}_{session_id}"
        
        try:
            # Actualizar la marca de tiempo
            context["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Guardar el contexto en el StateManager
            if self.state_manager:
                await self.state_manager.save_state(context_key, context)
                logger.info(f"Contexto actualizado en StateManager para key={context_key}")
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)
    
    # --- Métodos de Habilidades (Skills) ---
    
    async def _skill_biometric_analysis(self, input_data: BiometricAnalysisInput) -> BiometricAnalysisOutput:
        """
        Skill para analizar e interpretar datos biométricos.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            BiometricAnalysisOutput: Análisis biométrico generado
        """
        logger.info(f"Ejecutando habilidad: _skill_biometric_analysis con input: {input_data.user_input[:30]}...")
        
        try:
            # Obtener datos biométricos
            biometric_data = input_data.biometric_data
            if not biometric_data:
                # Si no hay datos biométricos, usar datos de ejemplo
                biometric_data = self._get_sample_biometric_data()
            
            # Preparar prompt para el modelo
            prompt = f"""
            Eres un especialista en análisis e interpretación de datos biométricos.
            
            Analiza los siguientes datos biométricos:
            
            "{input_data.user_input}"
            
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
            if input_data.user_profile:
                prompt += f"""
                
                Considera la siguiente información del usuario:
                - Edad: {input_data.user_profile.get('age', 'No disponible')}
                - Género: {input_data.user_profile.get('gender', 'No disponible')}
                - Nivel de actividad: {input_data.user_profile.get('activity_level', 'No disponible')}
                - Objetivos de salud: {', '.join(input_data.user_profile.get('health_goals', ['No disponible']))}
                - Condiciones: {', '.join(input_data.user_profile.get('conditions', ['No disponible']))}
                """
            
            # Generar el análisis biométrico
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
            
            # Crear el artefacto de análisis biométrico
            artifact = BiometricAnalysisArtifact(
                analysis_id=str(uuid.uuid4()),
                analysis_type="biometric_analysis",
                metrics_analyzed=list(biometric_data.keys()),
                timestamp=time.time(),
                summary=response.get("interpretation", "Análisis completado")
            )
            
            # Crear la salida de la skill
            return BiometricAnalysisOutput(
                interpretation=response.get("interpretation", "Interpretación no disponible"),
                main_insights=response.get("main_insights", ["No se pudieron identificar insights"]),
                patterns=response.get("patterns", ["No se pudieron identificar patrones"]),
                recommendations=response.get("recommendations", ["Recomendaciones no disponibles"]),
                areas_for_improvement=response.get("areas_for_improvement", ["No se pudieron identificar áreas de mejora"]),
                artifact=artifact
            )
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_biometric_analysis': {e}", exc_info=True)
            # En caso de error, devolver un análisis básico
            return BiometricAnalysisOutput(
                interpretation="No se pudo generar un análisis completo debido a un error",
                main_insights=["Error en el procesamiento de datos biométricos"],
                patterns=["No se pudieron identificar patrones"],
                recommendations=["Consulta a un profesional de la salud"],
                areas_for_improvement=["No se pudieron identificar áreas de mejora"],
                artifact=BiometricAnalysisArtifact(
                    analysis_id=str(uuid.uuid4()),
                    analysis_type="error",
                    metrics_analyzed=[],
                    timestamp=time.time(),
                    summary=f"Error: {str(e)}"
                )
            )
    
    async def _skill_pattern_recognition(self, input_data: PatternRecognitionInput) -> PatternRecognitionOutput:
        """
        Skill para identificar patrones en datos biométricos.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            PatternRecognitionOutput: Patrones identificados
        """
        logger.info(f"Ejecutando habilidad: _skill_pattern_recognition con input: {input_data.user_input[:30]}...")
        
        try:
            # Obtener datos biométricos
            biometric_data = input_data.biometric_data
            if not biometric_data:
                # Si no hay datos biométricos, usar datos de ejemplo
                biometric_data = self._get_sample_biometric_data()
            
            # Preparar prompt para el modelo
            prompt = f"""
            Eres un especialista en análisis e interpretación de datos biométricos.
            
            Identifica patrones recurrentes en los siguientes datos biométricos:
            
            "{input_data.user_input}"
            
            Datos biométricos disponibles:
            {json.dumps(biometric_data, indent=2)}
            
            El análisis debe incluir:
            1. Patrones identificados con descripción detallada
            2. Correlaciones entre diferentes métricas
            3. Posibles relaciones causales (si aplica)
            4. Recomendaciones basadas en los patrones identificados
            
            Devuelve el análisis en formato JSON estructurado.
            """
            
            # Añadir información del perfil si está disponible
            if input_data.user_profile:
                prompt += f"""
                
                Considera la siguiente información del usuario:
                - Edad: {input_data.user_profile.get('age', 'No disponible')}
                - Género: {input_data.user_profile.get('gender', 'No disponible')}
                - Nivel de actividad: {input_data.user_profile.get('activity_level', 'No disponible')}
                - Objetivos de salud: {', '.join(input_data.user_profile.get('health_goals', ['No disponible']))}
                - Condiciones: {', '.join(input_data.user_profile.get('conditions', ['No disponible']))}
                """
            
            # Generar el análisis de patrones
            response = await self.gemini_client.generate_structured_output(prompt)
            
            # Si la respuesta no es un diccionario, intentar convertirla
            if not isinstance(response, dict):
                try:
                    response = json.loads(response)
                except:
                    # Si no se puede convertir, crear un diccionario básico
                    response = {
                        "identified_patterns": [
                            {"name": "No se pudieron identificar patrones", "description": ""}
                        ],
                        "correlations": [
                            {
                                "metrics": ["N/A", "N/A"],
                                "correlation_type": "N/A",
                                "strength": "N/A",
                            }
                        ],
                        "causality_analysis": {"possible_causes": ["No se pudo determinar"]},
                        "recommendations": ["No hay recomendaciones disponibles"],
                    }
            
            # Crear la salida de la skill
            return PatternRecognitionOutput(
                identified_patterns=response.get("identified_patterns", [{"name": "No se pudieron identificar patrones", "description": ""}]),
                correlations=response.get("correlations", [{"metrics": ["N/A", "N/A"], "correlation_type": "N/A", "strength": "N/A"}]),
                causality_analysis=response.get("causality_analysis", {"possible_causes": ["No se pudo determinar"]}),
                recommendations=response.get("recommendations", ["No hay recomendaciones disponibles"])
            )
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_pattern_recognition': {e}", exc_info=True)
            # En caso de error, devolver un análisis básico
            return PatternRecognitionOutput(
                identified_patterns=[{"name": "Error en el análisis", "description": f"No se pudieron identificar patrones: {str(e)}"}],
                correlations=[{"metrics": ["N/A", "N/A"], "correlation_type": "N/A", "strength": "N/A"}],
                causality_analysis={"possible_causes": ["Error en el análisis"]},
                recommendations=["Consulta a un profesional de la salud"]
            )
    
    async def _skill_trend_identification(self, input_data: TrendIdentificationInput) -> TrendIdentificationOutput:
        """
        Skill para identificar tendencias en datos biométricos.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            TrendIdentificationOutput: Tendencias identificadas
        """
        logger.info(f"Ejecutando habilidad: _skill_trend_identification con input: {input_data.user_input[:30]}...")
        
        try:
            # Obtener datos biométricos
            biometric_data = input_data.biometric_data
            if not biometric_data:
                # Si no hay datos biométricos, usar datos de ejemplo
                biometric_data = self._get_sample_biometric_data()
            
            # Preparar prompt para el modelo
            prompt = f"""
            Eres un especialista en análisis e interpretación de datos biométricos.
            
            Analiza las tendencias en los siguientes datos biométricos:
            
            "{input_data.user_input}"
            
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
            if input_data.user_profile:
                prompt += f"""
                
                Considera la siguiente información del usuario:
                - Edad: {input_data.user_profile.get('age', 'No disponible')}
                - Género: {input_data.user_profile.get('gender', 'No disponible')}
                - Nivel de actividad: {input_data.user_profile.get('activity_level', 'No disponible')}
                - Objetivos de salud: {', '.join(input_data.user_profile.get('health_goals', ['No disponible']))}
                - Condiciones: {', '.join(input_data.user_profile.get('conditions', ['No disponible']))}
                """
            
            # Generar el análisis de tendencias
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
                        "recommendations": ["Recomendaciones no disponibles"],
                    }
            
            # Crear la salida de la skill
            return TrendIdentificationOutput(
                trends=response.get("trends", ["No se pudieron identificar tendencias"]),
                significant_changes=response.get("significant_changes", ["No se pudieron identificar cambios significativos"]),
                progress=response.get("progress", "Progreso no disponible"),
                projections=response.get("projections", ["Proyecciones no disponibles"]),
                recommendations=response.get("recommendations", ["Recomendaciones no disponibles"])
            )
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_trend_identification': {e}", exc_info=True)
            # En caso de error, devolver un análisis básico
            return TrendIdentificationOutput(
                trends=["Error en el análisis de tendencias"],
                significant_changes=[f"Error: {str(e)}"],
                progress="No disponible debido a un error",
                projections=["No disponible debido a un error"],
                recommendations=["Consulta a un profesional de la salud"]
            )
    
    async def _skill_data_visualization(self, input_data: DataVisualizationInput) -> DataVisualizationOutput:
        """
        Skill para generar visualizaciones de datos biométricos.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            DataVisualizationOutput: Visualización generada
        """
        logger.info(f"Ejecutando habilidad: _skill_data_visualization con input: {input_data.user_input[:30]}...")
        
        try:
            # Obtener datos biométricos
            biometric_data = input_data.biometric_data
            if not biometric_data:
                # Si no hay datos biométricos, usar datos de ejemplo
                biometric_data = self._get_sample_biometric_data()
            
            # Preparar prompt para el modelo
            prompt = f"""
            Eres un especialista en análisis e interpretación de datos biométricos.
            
            Genera una descripción para una visualización de los siguientes datos biométricos:
            
            "{input_data.user_input}"
            
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
            if input_data.user_profile:
                prompt += f"""
                
                Considera la siguiente información del usuario:
                - Edad: {input_data.user_profile.get('age', 'No disponible')}
                - Género: {input_data.user_profile.get('gender', 'No disponible')}
                - Nivel de actividad: {input_data.user_profile.get('activity_level', 'No disponible')}
                - Objetivos de salud: {', '.join(input_data.user_profile.get('health_goals', ['No disponible']))}
                - Condiciones: {', '.join(input_data.user_profile.get('conditions', ['No disponible']))}
                """
            
            # Generar la visualización
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
            
            # Crear el artefacto de visualización
            artifact = BiometricVisualizationArtifact(
                visualization_id=str(uuid.uuid4()),
                visualization_type=response.get("chart_type", "line"),
                metrics_included=response.get("metrics", list(biometric_data.keys())),
                timestamp=time.time(),
                url=f"visualization_{time.time()}.png"  # URL simulada
            )
            
            # Crear la salida de la skill
            return DataVisualizationOutput(
                chart_type=response.get("chart_type", "No se pudo determinar el tipo de gráfico"),
                metrics=response.get("metrics", ["No se pudieron identificar métricas"]),
                axes=response.get("axes", {"x": "No disponible", "y": "No disponible"}),
                highlighted_patterns=response.get("highlighted_patterns", ["No se pudieron identificar patrones"]),
                interpretation=response.get("interpretation", "Interpretación no disponible"),
                artifact=artifact
            )
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_data_visualization': {e}", exc_info=True)
            # En caso de error, devolver una visualización básica
            return DataVisualizationOutput(
                chart_type="Error",
                metrics=["No disponible debido a un error"],
                axes={"x": "No disponible", "y": "No disponible"},
                highlighted_patterns=[f"Error: {str(e)}"],
                interpretation="No se pudo generar una visualización debido a un error",
                artifact=BiometricVisualizationArtifact(
                    visualization_id=str(uuid.uuid4()),
                    visualization_type="error",
                    metrics_included=[],
                    timestamp=time.time(),
                    url=""
                )
            )
    
    def _get_sample_biometric_data(self) -> Dict[str, Any]:
        """
        Genera datos biométricos de ejemplo para pruebas.
        
        Returns:
            Dict[str, Any]: Datos biométricos de ejemplo
        """
        # Datos de ejemplo para HRV (Variabilidad de la Frecuencia Cardíaca)
        hrv_data = {
            "daily_average": [
                {"date": "2025-08-01", "value": 52, "unit": "ms"},
                {"date": "2025-08-02", "value": 48, "unit": "ms"},
                {"date": "2025-08-03", "value": 55, "unit": "ms"},
                {"date": "2025-08-04", "value": 51, "unit": "ms"},
                {"date": "2025-08-05", "value": 57, "unit": "ms"}
            ],
            "rmssd": [
                {"date": "2025-08-01", "value": 45, "unit": "ms"},
                {"date": "2025-08-02", "value": 42, "unit": "ms"},
                {"date": "2025-08-03", "value": 48, "unit": "ms"},
                {"date": "2025-08-04", "value": 44, "unit": "ms"},
                {"date": "2025-08-05", "value": 50, "unit": "ms"}
            ],
            "sdnn": [
                {"date": "2025-08-01", "value": 62, "unit": "ms"},
                {"date": "2025-08-02", "value": 58, "unit": "ms"},
                {"date": "2025-08-03", "value": 65, "unit": "ms"},
                {"date": "2025-08-04", "value": 60, "unit": "ms"},
                {"date": "2025-08-05", "value": 68, "unit": "ms"}
            ]
        }
        
        # Datos de ejemplo para sueño
        sleep_data = {
            "daily": [
                {"date": "2025-08-01", "total_duration": 7.5, "deep_sleep": 1.8, "rem_sleep": 2.2, "light_sleep": 3.5, "unit": "hours"},
                {"date": "2025-08-02", "total_duration": 6.8, "deep_sleep": 1.5, "rem_sleep": 1.9, "light_sleep": 3.4, "unit": "hours"},
                {"date": "2025-08-03", "total_duration": 8.2, "deep_sleep": 2.0, "rem_sleep": 2.5, "light_sleep": 3.7, "unit": "hours"},
                {"date": "2025-08-04", "total_duration": 7.0, "deep_sleep": 1.6, "rem_sleep": 2.0, "light_sleep": 3.4, "unit": "hours"},
                {"date": "2025-08-05", "total_duration": 7.8, "deep_sleep": 1.9, "rem_sleep": 2.3, "light_sleep": 3.6, "unit": "hours"}
            ],
            "sleep_score": [
                {"date": "2025-08-01", "value": 78, "unit": "score"},
                {"date": "2025-08-02", "value": 72, "unit": "score"},
                {"date": "2025-08-03", "value": 85, "unit": "score"},
                {"date": "2025-08-04", "value": 75, "unit": "score"},
                {"date": "2025-08-05", "value": 82, "unit": "score"}
            ],
            "sleep_efficiency": [
                {"date": "2025-08-01", "value": 92, "unit": "%"},
                {"date": "2025-08-02", "value": 88, "unit": "%"},
                {"date": "2025-08-03", "value": 95, "unit": "%"},
                {"date": "2025-08-04", "value": 90, "unit": "%"},
                {"date": "2025-08-05", "value": 93, "unit": "%"}
            ]
        }
        
        # Datos de ejemplo para glucosa
        glucose_data = {
            "daily_average": [
                {"date": "2025-08-01", "value": 105, "unit": "mg/dL"},
                {"date": "2025-08-02", "value": 110, "unit": "mg/dL"},
                {"date": "2025-08-03", "value": 102, "unit": "mg/dL"},
                {"date": "2025-08-04", "value": 108, "unit": "mg/dL"},
                {"date": "2025-08-05", "value": 104, "unit": "mg/dL"}
            ],
            "variability": [
                {"date": "2025-08-01", "value": 15, "unit": "mg/dL"},
                {"date": "2025-08-02", "value": 18, "unit": "mg/dL"},
                {"date": "2025-08-03", "value": 12, "unit": "mg/dL"},
                {"date": "2025-08-04", "value": 16, "unit": "mg/dL"},
                {"date": "2025-08-05", "value": 14, "unit": "mg/dL"}
            ],
            "time_in_range": [
                {"date": "2025-08-01", "value": 85, "unit": "%"},
                {"date": "2025-08-02", "value": 80, "unit": "%"},
                {"date": "2025-08-03", "value": 88, "unit": "%"},
                {"date": "2025-08-04", "value": 82, "unit": "%"},
                {"date": "2025-08-05", "value": 86, "unit": "%"}
            ]
        }
        
        # Datos de ejemplo para composición corporal
        body_composition_data = {
            "weight": [
                {"date": "2025-08-01", "value": 75.5, "unit": "kg"},
                {"date": "2025-08-02", "value": 75.3, "unit": "kg"},
                {"date": "2025-08-03", "value": 75.2, "unit": "kg"},
                {"date": "2025-08-04", "value": 75.0, "unit": "kg"},
                {"date": "2025-08-05", "value": 74.8, "unit": "kg"}
            ],
            "body_fat": [
                {"date": "2025-08-01", "value": 18.5, "unit": "%"},
                {"date": "2025-08-02", "value": 18.4, "unit": "%"},
                {"date": "2025-08-03", "value": 18.3, "unit": "%"},
                {"date": "2025-08-04", "value": 18.2, "unit": "%"},
                {"date": "2025-08-05", "value": 18.0, "unit": "%"}
            ],
            "muscle_mass": [
                {"date": "2025-08-01", "value": 32.5, "unit": "kg"},
                {"date": "2025-08-02", "value": 32.6, "unit": "kg"},
                {"date": "2025-08-03", "value": 32.7, "unit": "kg"},
                {"date": "2025-08-04", "value": 32.8, "unit": "kg"},
                {"date": "2025-08-05", "value": 32.9, "unit": "kg"}
            ]
        }
        
        # Combinar todos los datos
        return {
            "hrv": hrv_data,
            "sleep": sleep_data,
            "glucose": glucose_data,
            "body_composition": body_composition_data
        }

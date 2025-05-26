"""
Agente especializado en análisis e interpretación de datos biométricos.

Este agente procesa datos biométricos como HRV, sueño, glucosa,
composición corporal, etc., para proporcionar insights personalizados
y recomendaciones basadas en patrones individuales.

Implementa los protocolos oficiales ADK y A2A para comunicación entre agentes.
"""

import uuid
import time
import json
import os
from typing import Dict, Any, Optional
from google.cloud import aiplatform

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from agents.base.adk_agent import ADKAgent
from core.logging_config import get_logger
from services.program_classification_service import ProgramClassificationService
from agents.shared.program_definitions import get_program_definition

# Importar Skill y Toolkit desde adk.agent
from adk.agent import Skill
from adk.toolkit import Toolkit

# Importar esquemas para las skills
from agents.biometrics_insight_engine.schemas import (
    BiometricAnalysisInput,
    BiometricAnalysisOutput,
    PatternRecognitionInput,
    PatternRecognitionOutput,
    TrendIdentificationInput,
    TrendIdentificationOutput,
    DataVisualizationInput,
    DataVisualizationOutput,
    BiometricAnalysisArtifact,
    BiometricVisualizationArtifact,
    BiometricImageAnalysisInput,
    BiometricImageAnalysisOutput,
    BiometricImageArtifact,
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
        **kwargs,
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

        # Inicializar el servicio de clasificación de programas
        self.gemini_client = GeminiClient()
        self.program_classification_service = ProgramClassificationService(
            self.gemini_client
        )

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
                output_schema=BiometricAnalysisOutput,
            ),
            Skill(
                name="pattern_recognition",
                description="Identifica patrones recurrentes en datos biométricos y su relación con hábitos y comportamientos",
                handler=self._skill_pattern_recognition,
                input_schema=PatternRecognitionInput,
                output_schema=PatternRecognitionOutput,
            ),
            Skill(
                name="trend_identification",
                description="Analiza tendencias a largo plazo en datos biométricos para identificar mejoras o cambios significativos",
                handler=self._skill_trend_identification,
                input_schema=TrendIdentificationInput,
                output_schema=TrendIdentificationOutput,
            ),
            Skill(
                name="data_visualization",
                description="Crea representaciones visuales de datos biométricos para facilitar la comprensión de patrones",
                handler=self._skill_data_visualization,
                input_schema=DataVisualizationInput,
                output_schema=DataVisualizationOutput,
            ),
            Skill(
                name="biometric_image_analysis",
                description="Analiza imágenes biométricas para extraer métricas, identificar indicadores visuales y proporcionar insights de salud",
                handler=self._skill_biometric_image_analysis,
                input_schema=BiometricImageAnalysisInput,
                output_schema=BiometricImageAnalysisOutput,
            ),
        ]

        # Definir las capacidades del agente
        _capabilities = [
            "biometric_analysis",
            "pattern_recognition",
            "trend_identification",
            "personalized_insights",
            "data_visualization",
            "biometric_image_analysis",
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
            **kwargs,
        )

        # Configurar clientes adicionales
        self.gemini_client = GeminiClient(model_name=self.model)
        self.supabase_client = SupabaseClient()

        # Inicializar Vertex AI
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(
                f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}"
            )
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info(
                "AI Platform (Vertex AI SDK) inicializado correctamente para BiometricsInsightEngine."
            )
        except Exception as e:
            logger.error(
                f"Error al inicializar AI Platform para BiometricsInsightEngine: {e}",
                exc_info=True,
            )

        logger.info(
            f"{self.name} ({self.agent_id}) inicializado con integración oficial de Google ADK."
        )

    async def _get_context(
        self, user_id: Optional[str], session_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el StateManager.

        Args:
            user_id (Optional[str]): ID del usuario.
            session_id (Optional[str]): ID de la sesión.

        Returns:
            Dict[str, Any]: Contexto de la conversación.
        """
        context_key = (
            f"context_{user_id}_{session_id}"
            if user_id and session_id
            else f"context_default_{uuid.uuid4().hex[:6]}"
        )

        try:
            # Intentar cargar desde StateManager (si está disponible)
            if self.state_manager and user_id and session_id:
                try:
                    state_data = await self.state_manager.load_state(context_key)
                    if state_data and isinstance(state_data, dict):
                        logger.debug(
                            f"Contexto cargado desde StateManager para key={context_key}"
                        )
                        return state_data
                except Exception as e:
                    logger.warning(f"Error al cargar contexto desde StateManager: {e}")

            # Si no hay contexto o hay error, crear uno nuevo
            return {
                "conversation_history": [],
                "user_profile": {},
                "analyses": [],
                "biometric_data": {},
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            logger.error(f"Error al obtener contexto: {e}", exc_info=True)
            # En caso de error, devolver un contexto vacío
            return {
                "conversation_history": [],
                "user_profile": {},
                "analyses": [],
                "biometric_data": {},
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

    async def _update_context(
        self, context: Dict[str, Any], user_id: str, session_id: str
    ) -> None:
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
                logger.info(
                    f"Contexto actualizado en StateManager para key={context_key}"
                )
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)

    # --- Métodos de Habilidades (Skills) ---

    async def _skill_biometric_analysis(
        self, input_data: BiometricAnalysisInput
    ) -> BiometricAnalysisOutput:
        """
        Skill para analizar e interpretar datos biométricos.

        Args:
            input_data: Datos de entrada para la skill

        Returns:
            BiometricAnalysisOutput: Análisis biométrico generado
        """
        logger.info(f"Ejecutando skill de análisis biométrico con datos: {input_data}")

        # Obtener datos biométricos (en un caso real, se obtendrían de una API o base de datos)
        biometric_data = input_data.biometric_data or self._get_sample_biometric_data()
        user_profile = input_data.user_profile or {}

        # Determinar el tipo de programa del usuario para análisis personalizado
        context = {"user_profile": user_profile, "goals": user_profile.get("goals", [])}

        try:
            # Clasificar el tipo de programa del usuario
            program_type = (
                await self.program_classification_service.classify_program_type(context)
            )
            logger.info(
                f"Tipo de programa determinado para análisis biométrico: {program_type}"
            )

            # Obtener definición del programa para personalizar el análisis
            program_def = get_program_definition(program_type)
            program_context = f"""\nCONTEXTO DEL PROGRAMA {program_type}:\n"""

            if program_def:
                program_context += f"- {program_def.get('description', '')}\n"
                program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                program_context += (
                    f"- Pilares: {', '.join(program_def.get('pillars', []))}\n"
                )
                program_context += (
                    f"- Necesidades: {', '.join(program_def.get('user_needs', []))}\n"
                )

        except Exception as e:
            logger.warning(
                f"No se pudo determinar el tipo de programa: {e}. Usando análisis general."
            )
            program_type = "GENERAL"
            program_context = ""

        # Construir prompt para el análisis
        prompt = f"""
        Eres un experto en análisis de datos biométricos. Analiza los siguientes datos y proporciona insights 
        personalizados y recomendaciones basadas en los patrones observados.
        
        DATOS BIOMÉTRICOS:
        {json.dumps(biometric_data, indent=2)}
        
        PERFIL DEL USUARIO:
        {json.dumps(user_profile, indent=2)}
        {program_context}
        
        Proporciona un análisis detallado que incluya:
        1. Interpretación de los datos y patrones observados
        2. Insights clave sobre el estado de salud y bienestar
        3. Recomendaciones personalizadas basadas en los datos y el tipo de programa del usuario ({program_type})
        4. Áreas de mejora y posibles intervenciones específicas para el programa {program_type}
        
        Tu análisis debe ser claro, preciso y basado en evidencia científica.
        """

        try:
            # Generar análisis usando Gemini
            analysis_text = await self.gemini_client.generate_text(prompt)

            # Crear artefacto con el análisis
            artifact = BiometricAnalysisArtifact(
                id=str(uuid.uuid4()),
                label=f"Análisis Biométrico - Programa {program_type}",
                content=analysis_text,
                metadata={
                    "timestamp": time.time(),
                    "data_types": list(biometric_data.keys()),
                    "analysis_type": "comprehensive",
                    "program_type": program_type,
                },
            )

            return BiometricAnalysisOutput(
                analysis=analysis_text,
                artifacts=[artifact],
                metadata={
                    "timestamp": time.time(),
                    "data_points": sum(
                        len(data_type) for data_type in biometric_data.values()
                    ),
                    "program_type": program_type,
                },
            )

        except Exception as e:
            logger.error(f"Error al generar análisis biométrico: {e}", exc_info=True)
            # Crear un artefacto de error
            error_artifact = BiometricAnalysisArtifact(
                id=str(uuid.uuid4()),
                label="Error en Análisis Biométrico",
                content=f"Error: {str(e)}",
                metadata={
                    "timestamp": time.time(),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            return BiometricAnalysisOutput(
                analysis="No se pudo generar el análisis debido a un error.",
                artifacts=[error_artifact],
                metadata={"error": str(e)},
            )

    async def _skill_pattern_recognition(
        self, input_data: PatternRecognitionInput
    ) -> PatternRecognitionOutput:
        """
        Skill para identificar patrones en datos biométricos.

        Args:
            input_data: Datos de entrada para la skill

        Returns:
            PatternRecognitionOutput: Patrones identificados
        """
        logger.info(
            f"Ejecutando habilidad: _skill_pattern_recognition con input: {input_data.user_input[:30]}..."
        )

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
                except Exception:
                    # Si no se puede convertir, crear un diccionario básico
                    response = {
                        "identified_patterns": [
                            {
                                "name": "No se pudieron identificar patrones",
                                "description": "",
                            }
                        ],
                        "correlations": [
                            {
                                "metrics": ["N/A", "N/A"],
                                "correlation_type": "N/A",
                                "strength": "N/A",
                            }
                        ],
                        "causality_analysis": {
                            "possible_causes": ["No se pudo determinar"]
                        },
                        "recommendations": ["No hay recomendaciones disponibles"],
                    }

            # Crear la salida de la skill
            return PatternRecognitionOutput(
                identified_patterns=response.get(
                    "identified_patterns",
                    [
                        {
                            "name": "No se pudieron identificar patrones",
                            "description": "",
                        }
                    ],
                ),
                correlations=response.get(
                    "correlations",
                    [
                        {
                            "metrics": ["N/A", "N/A"],
                            "correlation_type": "N/A",
                            "strength": "N/A",
                        }
                    ],
                ),
                causality_analysis=response.get(
                    "causality_analysis", {"possible_causes": ["No se pudo determinar"]}
                ),
                recommendations=response.get(
                    "recommendations", ["No hay recomendaciones disponibles"]
                ),
            )

        except Exception as e:
            logger.error(
                f"Error en skill '_skill_pattern_recognition': {e}", exc_info=True
            )
            # En caso de error, devolver un análisis básico
            return PatternRecognitionOutput(
                identified_patterns=[
                    {
                        "name": "Error en el análisis",
                        "description": f"No se pudieron identificar patrones: {str(e)}",
                    }
                ],
                correlations=[
                    {
                        "metrics": ["N/A", "N/A"],
                        "correlation_type": "N/A",
                        "strength": "N/A",
                    }
                ],
                causality_analysis={"possible_causes": ["Error en el análisis"]},
                recommendations=["Consulta a un profesional de la salud"],
            )

    async def _skill_trend_identification(
        self, input_data: TrendIdentificationInput
    ) -> TrendIdentificationOutput:
        """
        Skill para identificar tendencias en datos biométricos.

        Args:
            input_data: Datos de entrada para la skill

        Returns:
            TrendIdentificationOutput: Tendencias identificadas
        """
        logger.info(
            f"Ejecutando habilidad: _skill_trend_identification con input: {input_data.user_input[:30]}..."
        )

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
                except Exception:
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

            # Crear la salida de la skill
            return TrendIdentificationOutput(
                trends=response.get(
                    "trends", ["No se pudieron identificar tendencias"]
                ),
                significant_changes=response.get(
                    "significant_changes",
                    ["No se pudieron identificar cambios significativos"],
                ),
                progress=response.get("progress", "Progreso no disponible"),
                projections=response.get(
                    "projections", ["Proyecciones no disponibles"]
                ),
                recommendations=response.get(
                    "recommendations", ["Recomendaciones no disponibles"]
                ),
            )

        except Exception as e:
            logger.error(
                f"Error en skill '_skill_trend_identification': {e}", exc_info=True
            )
            # En caso de error, devolver un análisis básico
            return TrendIdentificationOutput(
                trends=["Error en el análisis de tendencias"],
                significant_changes=[f"Error: {str(e)}"],
                progress="No disponible debido a un error",
                projections=["No disponible debido a un error"],
                recommendations=["Consulta a un profesional de la salud"],
            )

    async def _skill_data_visualization(
        self, input_data: DataVisualizationInput
    ) -> DataVisualizationOutput:
        """
        Skill para generar visualizaciones de datos biométricos.

        Args:
            input_data: Datos de entrada para la skill

        Returns:
            DataVisualizationOutput: Visualización generada
        """
        logger.info(
            f"Ejecutando habilidad: _skill_data_visualization con input: {input_data.user_input[:30]}..."
        )

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
                except Exception:
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
                url=f"visualization_{time.time()}.png",  # URL simulada
            )

            # Crear la salida de la skill
            return DataVisualizationOutput(
                chart_type=response.get(
                    "chart_type", "No se pudo determinar el tipo de gráfico"
                ),
                metrics=response.get(
                    "metrics", ["No se pudieron identificar métricas"]
                ),
                axes=response.get("axes", {"x": "No disponible", "y": "No disponible"}),
                highlighted_patterns=response.get(
                    "highlighted_patterns", ["No se pudieron identificar patrones"]
                ),
                interpretation=response.get(
                    "interpretation", "Interpretación no disponible"
                ),
                artifact=artifact,
            )

        except Exception as e:
            logger.error(
                f"Error en skill '_skill_data_visualization': {e}", exc_info=True
            )
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
                    url="",
                ),
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
                {"date": "2025-08-05", "value": 57, "unit": "ms"},
            ],
            "rmssd": [
                {"date": "2025-08-01", "value": 45, "unit": "ms"},
                {"date": "2025-08-02", "value": 42, "unit": "ms"},
                {"date": "2025-08-03", "value": 48, "unit": "ms"},
                {"date": "2025-08-04", "value": 44, "unit": "ms"},
                {"date": "2025-08-05", "value": 50, "unit": "ms"},
            ],
            "sdnn": [
                {"date": "2025-08-01", "value": 62, "unit": "ms"},
                {"date": "2025-08-02", "value": 58, "unit": "ms"},
                {"date": "2025-08-03", "value": 65, "unit": "ms"},
                {"date": "2025-08-04", "value": 60, "unit": "ms"},
                {"date": "2025-08-05", "value": 68, "unit": "ms"},
            ],
        }

        # Datos de ejemplo para sueño
        sleep_data = {
            "daily": [
                {
                    "date": "2025-08-01",
                    "total_duration": 7.5,
                    "deep_sleep": 1.8,
                    "rem_sleep": 2.2,
                    "light_sleep": 3.5,
                    "unit": "hours",
                },
                {
                    "date": "2025-08-02",
                    "total_duration": 6.8,
                    "deep_sleep": 1.5,
                    "rem_sleep": 1.9,
                    "light_sleep": 3.4,
                    "unit": "hours",
                },
                {
                    "date": "2025-08-03",
                    "total_duration": 8.2,
                    "deep_sleep": 2.0,
                    "rem_sleep": 2.5,
                    "light_sleep": 3.7,
                    "unit": "hours",
                },
                {
                    "date": "2025-08-04",
                    "total_duration": 7.0,
                    "deep_sleep": 1.6,
                    "rem_sleep": 2.0,
                    "light_sleep": 3.4,
                    "unit": "hours",
                },
                {
                    "date": "2025-08-05",
                    "total_duration": 7.8,
                    "deep_sleep": 1.9,
                    "rem_sleep": 2.3,
                    "light_sleep": 3.6,
                    "unit": "hours",
                },
            ],
            "sleep_score": [
                {"date": "2025-08-01", "value": 78, "unit": "score"},
                {"date": "2025-08-02", "value": 72, "unit": "score"},
                {"date": "2025-08-03", "value": 85, "unit": "score"},
                {"date": "2025-08-04", "value": 75, "unit": "score"},
                {"date": "2025-08-05", "value": 82, "unit": "score"},
            ],
            "sleep_efficiency": [
                {"date": "2025-08-01", "value": 92, "unit": "%"},
                {"date": "2025-08-02", "value": 88, "unit": "%"},
                {"date": "2025-08-03", "value": 95, "unit": "%"},
                {"date": "2025-08-04", "value": 90, "unit": "%"},
                {"date": "2025-08-05", "value": 93, "unit": "%"},
            ],
        }

        # Datos de ejemplo para glucosa
        glucose_data = {
            "daily_average": [
                {"date": "2025-08-01", "value": 105, "unit": "mg/dL"},
                {"date": "2025-08-02", "value": 110, "unit": "mg/dL"},
                {"date": "2025-08-03", "value": 102, "unit": "mg/dL"},
                {"date": "2025-08-04", "value": 108, "unit": "mg/dL"},
                {"date": "2025-08-05", "value": 104, "unit": "mg/dL"},
            ],
            "variability": [
                {"date": "2025-08-01", "value": 15, "unit": "mg/dL"},
                {"date": "2025-08-02", "value": 18, "unit": "mg/dL"},
                {"date": "2025-08-03", "value": 12, "unit": "mg/dL"},
                {"date": "2025-08-04", "value": 16, "unit": "mg/dL"},
                {"date": "2025-08-05", "value": 14, "unit": "mg/dL"},
            ],
            "time_in_range": [
                {"date": "2025-08-01", "value": 85, "unit": "%"},
                {"date": "2025-08-02", "value": 80, "unit": "%"},
                {"date": "2025-08-03", "value": 88, "unit": "%"},
                {"date": "2025-08-04", "value": 82, "unit": "%"},
                {"date": "2025-08-05", "value": 86, "unit": "%"},
            ],
        }

        # Datos de ejemplo para composición corporal
        body_composition_data = {
            "weight": [
                {"date": "2025-08-01", "value": 75.5, "unit": "kg"},
                {"date": "2025-08-02", "value": 75.3, "unit": "kg"},
                {"date": "2025-08-03", "value": 75.2, "unit": "kg"},
                {"date": "2025-08-04", "value": 75.0, "unit": "kg"},
                {"date": "2025-08-05", "value": 74.8, "unit": "kg"},
            ],
            "body_fat": [
                {"date": "2025-08-01", "value": 18.5, "unit": "%"},
                {"date": "2025-08-02", "value": 18.4, "unit": "%"},
                {"date": "2025-08-03", "value": 18.3, "unit": "%"},
                {"date": "2025-08-04", "value": 18.2, "unit": "%"},
                {"date": "2025-08-05", "value": 18.0, "unit": "%"},
            ],
            "muscle_mass": [
                {"date": "2025-08-01", "value": 32.5, "unit": "kg"},
                {"date": "2025-08-02", "value": 32.6, "unit": "kg"},
                {"date": "2025-08-03", "value": 32.7, "unit": "kg"},
                {"date": "2025-08-04", "value": 32.8, "unit": "kg"},
                {"date": "2025-08-05", "value": 32.9, "unit": "kg"},
            ],
        }

        # Combinar todos los datos
        return {
            "hrv": hrv_data,
            "sleep": sleep_data,
            "glucose": glucose_data,
            "body_composition": body_composition_data,
        }

    async def _skill_biometric_image_analysis(
        self, input_data: BiometricImageAnalysisInput
    ) -> BiometricImageAnalysisOutput:
        """
        Skill para analizar imágenes biométricas.

        Args:
            input_data: Datos de entrada para la skill

        Returns:
            BiometricImageAnalysisOutput: Análisis de la imagen biométrica
        """
        logger.info(
            f"Ejecutando skill de análisis de imágenes biométricas con tipo de análisis: {input_data.analysis_type}"
        )

        try:
            # Obtener datos de la imagen
            image_data = input_data.image_data
            analysis_type = input_data.analysis_type or "full"
            user_profile = input_data.user_profile or {}

            # Determinar el tipo de programa del usuario para análisis personalizado
            context = {
                "user_profile": user_profile,
                "goals": user_profile.get("goals", []),
            }

            try:
                # Clasificar el tipo de programa del usuario
                program_type = (
                    await self.program_classification_service.classify_program_type(
                        context
                    )
                )
                logger.info(
                    f"Tipo de programa determinado para análisis de imagen biométrica: {program_type}"
                )
            except Exception as e:
                logger.warning(
                    f"No se pudo determinar el tipo de programa: {e}. Usando análisis general."
                )
                program_type = "GENERAL"

            # Utilizar las capacidades de visión del agente base
            with self.tracer.start_as_current_span("biometric_image_analysis"):
                # Analizar la imagen utilizando el procesador de visión
                if analysis_type == "full":
                    # Análisis completo de la imagen
                    vision_result = await self.vision_processor.analyze_image(
                        image_data
                    )
                elif analysis_type == "body":
                    # Análisis específico de cuerpo/postura
                    vision_result = await self.vision_processor.analyze_image(
                        image_data, "objects"
                    )
                elif analysis_type == "face":
                    # Análisis específico de rostro
                    vision_result = await self.vision_processor.analyze_faces(
                        image_data
                    )
                else:
                    # Análisis por defecto
                    vision_result = await self.vision_processor.analyze_image(
                        image_data
                    )

                # Generar una descripción detallada de la imagen
                description_result = await self.vision_processor.describe_image(
                    image_data, detail_level="detailed", focus_aspect="people"
                )

                # Extraer métricas biométricas de la imagen usando el modelo multimodal
                prompt = f"""
                Eres un experto en análisis biométrico visual. Analiza esta imagen y extrae métricas biométricas
                visibles. Considera aspectos como:
                
                1. Composición corporal aproximada
                2. Postura y alineación
                3. Indicadores visuales de salud
                4. Simetría corporal
                5. Otros indicadores biométricos relevantes
                
                Proporciona un análisis detallado y objetivo basado únicamente en lo que es visible en la imagen.
                Considera que este análisis es para un usuario con programa tipo {program_type}.
                """

                multimodal_result = await self.multimodal_adapter.process_multimodal(
                    prompt=prompt,
                    image_data=image_data,
                    temperature=0.2,
                    max_output_tokens=1024,
                )

                # Combinar los resultados para crear un análisis completo
                analysis_summary = multimodal_result.get("text", "")

                # Extraer métricas detectadas (simuladas para este ejemplo)
                detected_metrics = {
                    "posture_score": 0.85,
                    "symmetry_score": 0.78,
                    "estimated_body_composition": {
                        "body_fat_percentage": "No determinable con precisión desde la imagen",
                        "muscle_definition": "Moderada",
                        "body_proportions": "Dentro de rangos normales",
                    },
                }

                # Extraer indicadores visuales
                visual_indicators = []
                if "objects" in vision_result:
                    for obj in vision_result.get("objects", []):
                        if obj.get("name") in ["person", "face", "body", "arm", "leg"]:
                            visual_indicators.append(
                                {
                                    "type": obj.get("name"),
                                    "confidence": obj.get("score", 0),
                                    "location": obj.get("bounding_poly", []),
                                }
                            )

                # Generar insights de salud basados en el análisis
                health_insights_prompt = f"""
                Basándote en el siguiente análisis de una imagen biométrica, genera 3-5 insights de salud
                concretos y accionables. El análisis es:
                
                {analysis_summary}
                
                Proporciona insights específicos, basados en evidencia y relevantes para un programa {program_type}.
                """

                health_insights_response = await self.gemini_client.generate_text(
                    health_insights_prompt
                )
                health_insights = [
                    insight.strip()
                    for insight in health_insights_response.split("\n")
                    if insight.strip()
                ]

                # Generar recomendaciones personalizadas
                recommendations_prompt = f"""
                Basándote en el siguiente análisis de una imagen biométrica, genera 3-5 recomendaciones
                personalizadas y accionables. El análisis es:
                
                {analysis_summary}
                
                Proporciona recomendaciones específicas, basadas en evidencia y relevantes para un programa {program_type}.
                """

                recommendations_response = await self.gemini_client.generate_text(
                    recommendations_prompt
                )
                recommendations = [
                    rec.strip()
                    for rec in recommendations_response.split("\n")
                    if rec.strip()
                ]

                # Crear artefacto con el análisis
                artifact = BiometricImageArtifact(
                    analysis_id=str(uuid.uuid4()),
                    image_type="biometric",
                    analysis_type=analysis_type,
                    timestamp=time.time(),
                    annotations={
                        "indicators": visual_indicators,
                        "metrics": detected_metrics,
                    },
                    processed_image_url="",  # En un caso real, aquí iría la URL de la imagen procesada
                )

                # Calcular puntuación de confianza
                confidence_scores = [
                    indicator.get("confidence", 0) for indicator in visual_indicators
                ]
                confidence_score = (
                    sum(confidence_scores) / len(confidence_scores)
                    if confidence_scores
                    else 0.7
                )

                return BiometricImageAnalysisOutput(
                    analysis_summary=analysis_summary,
                    detected_metrics=detected_metrics,
                    visual_indicators=visual_indicators,
                    health_insights=health_insights,
                    recommendations=recommendations,
                    confidence_score=confidence_score,
                )

        except Exception as e:
            logger.error(f"Error al analizar imagen biométrica: {e}", exc_info=True)

            # En caso de error, devolver un análisis básico
            return BiometricImageAnalysisOutput(
                analysis_summary=f"Error al analizar la imagen biométrica: {str(e)}",
                detected_metrics={},
                visual_indicators=[],
                health_insights=[
                    "No se pudieron generar insights debido a un error en el análisis"
                ],
                recommendations=[
                    "Consulta a un profesional de la salud para un análisis preciso"
                ],
                confidence_score=0.0,
            )

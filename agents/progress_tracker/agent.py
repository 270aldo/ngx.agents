"""
Agente especializado en seguimiento y análisis de progreso del usuario.

Este agente utiliza el modelo Gemini para analizar datos de progreso, generar visualizaciones
y comparar métricas a lo largo del tiempo. Implementa los protocolos oficiales A2A y ADK
para comunicación entre agentes.
"""
import logging
import uuid
import time
from typing import Dict, Any, Optional, List, Union
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import datetime
from google.cloud import aiplatform

from pydantic import BaseModel, Field

from agents.base.adk_agent import ADKAgent
from adk.agent import Skill
from adk.toolkit import Toolkit
from core.contracts import create_result

from agents.progress_tracker.schemas import (
    AnalyzeProgressInput,
    AnalyzeProgressOutput,
    VisualizeProgressInput,
    VisualizeProgressOutput,
    CompareProgressInput,
    CompareProgressOutput,
    ProgressAnalysisArtifact,
    ProgressVisualizationArtifact,
    AnalyzeBodyProgressInput,
    AnalyzeBodyProgressOutput,
    BodyChangeMetric,
    BodyAreaChange,
    GenerateProgressVisualizationInput,
    GenerateProgressVisualizationOutput,
    BodyProgressAnalysisArtifact
)

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from core.logging_config import get_logger
from services.program_classification_service import ProgramClassificationService
from agents.shared.program_definitions import get_program_definition

# Configurar logger
logger = get_logger(__name__)

class ProgressTracker(ADKAgent):
    """
    Agente especializado en seguimiento y análisis de progreso del usuario.
    
    Esta implementación utiliza la integración oficial con Google ADK.
    """

    AGENT_ID = "progress_tracker"
    AGENT_NAME = "NGX Progress Tracker"
    AGENT_DESCRIPTION = "Especialista en seguimiento, análisis y visualización de progreso"
    DEFAULT_INSTRUCTION = "Eres un analista de datos especializado en seguimiento de progreso y visualización."
    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(
        self,
        state_manager = None,
        mcp_toolkit: Optional[MCPToolkit] = None,
        a2a_server_url: Optional[str] = None,
        model: Optional[str] = None,
        instruction: Optional[str] = None,
        agent_id: str = AGENT_ID,
        name: str = AGENT_NAME,
        description: str = AGENT_DESCRIPTION,
        **kwargs
    ):
        _model = model or self.DEFAULT_MODEL
        _instruction = instruction or self.DEFAULT_INSTRUCTION
        _mcp_toolkit = mcp_toolkit if mcp_toolkit is not None else MCPToolkit()

        # Definir las skills antes de llamar al constructor de ADKAgent
        self.skills = [
            Skill(
                name="analyze_progress",
                description="Analiza los datos de progreso del usuario e identifica tendencias.",
                handler=self._skill_analyze_progress,
                input_schema=AnalyzeProgressInput,
                output_schema=AnalyzeProgressOutput
            ),
            Skill(
                name="visualize_progress",
                description="Genera una visualización (gráfico) del progreso del usuario.",
                handler=self._skill_visualize_progress,
                input_schema=VisualizeProgressInput,
                output_schema=VisualizeProgressOutput
            ),
            Skill(
                name="compare_progress",
                description="Compara el progreso entre dos periodos de tiempo.",
                handler=self._skill_compare_progress,
                input_schema=CompareProgressInput,
                output_schema=CompareProgressOutput
            ),
            Skill(
                name="analyze_body_progress",
                description="Analiza el progreso corporal mediante imágenes antes/después.",
                handler=self._skill_analyze_body_progress,
                input_schema=AnalyzeBodyProgressInput,
                output_schema=AnalyzeBodyProgressOutput
            ),
            Skill(
                name="generate_progress_visualization",
                description="Genera visualizaciones de progreso a partir de múltiples imágenes.",
                handler=self._skill_generate_progress_visualization,
                input_schema=GenerateProgressVisualizationInput,
                output_schema=GenerateProgressVisualizationOutput
            )
        ]

        # Definir las capacidades del agente
        _capabilities = [
            "analyze_progress",
            "visualize_progress",
            "compare_progress",
            "data_analysis",
            "trend_identification",
            "body_progress_analysis",
            "visual_comparison"
        ]

        # Crear un toolkit de ADK
        adk_toolkit = Toolkit()

        # Inicializar el servicio de clasificación de programas
        self.gemini_client = GeminiClient()
        self.program_classification_service = ProgramClassificationService(self.gemini_client)
        
        # Inicializar componentes para capacidades de visión y multimodales
        try:
            from infrastructure.adapters.vision_adapter import VisionProcessor
            from infrastructure.adapters.multimodal_adapter import MultimodalAdapter
            from opentelemetry import trace
            
            # Inicializar procesador de visión
            self.vision_processor = VisionProcessor()
            
            # Inicializar adaptador multimodal
            self.multimodal_adapter = MultimodalAdapter()
            
            # Inicializar tracer para telemetría
            self.tracer = trace.get_tracer(__name__)
            
            # Bandera para verificar disponibilidad de capacidades de visión
            self._vision_capabilities_available = True
            
            logger.info("Capacidades de visión y multimodales inicializadas correctamente")
        except Exception as e:
            logger.warning(f"No se pudieron inicializar las capacidades de visión y multimodales: {e}")
            
            # Crear implementaciones simuladas para mantener la funcionalidad básica
            class MockVisionProcessor:
                async def analyze_image(self, image_data):
                    return {"description": "Análisis de imagen simulado"}
            
            class MockMultimodalAdapter:
                async def compare_images(self, image_data1, image_data2, comparison_prompt, **kwargs):
                    return {"text": "Comparación de imágenes simulada"}
            
            class MockTracer:
                def start_as_current_span(self, name):
                    class MockSpan:
                        def __enter__(self): return self
                        def __exit__(self, exc_type, exc_val, exc_tb): pass
                    return MockSpan()
            
            self.vision_processor = MockVisionProcessor()
            self.multimodal_adapter = MockMultimodalAdapter()
            self.tracer = MockTracer()
            self._vision_capabilities_available = False
            
            logger.warning("Usando implementaciones simuladas para capacidades de visión y multimodales")
        
        # Inicializar el agente ADK
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            model=_model,
            instruction=_instruction,
            state_manager=None,  # Ya no usamos el state_manager original
            adk_toolkit=adk_toolkit,
            capabilities=_capabilities,
            a2a_server_url=a2a_server_url,
            **kwargs
        )
        
        # Configurar clientes adicionales
        self.gemini_client = GeminiClient(model_name=self.model)
        self.supabase_client = SupabaseClient()
        
        # Directorio para guardar gráficos temporales
        self.tmp_dir = os.path.join(os.getcwd(), "tmp_progress")
        # Crear directorio si no existe
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir, exist_ok=True)
        
        # Configurar sistema de instrucciones para Gemini
        self.system_instructions = """Eres un analista de datos especializado en seguimiento de progreso y visualización. 
        Tu objetivo es proporcionar análisis claros, concisos y útiles sobre el progreso del usuario en diversas métricas.
        Identifica tendencias, patrones y proporciona recomendaciones accionables basadas en datos."""
        
        # Inicializar Vertex AI
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform (Vertex AI SDK) inicializado correctamente para ProgressTracker.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform para ProgressTracker: {e}", exc_info=True)
            
        logger.info(f"{self.name} ({self.agent_id}) inicializado con integración oficial de Google ADK.")

    # --- Métodos de Habilidades (Skills) ---
    
    async def _skill_analyze_progress(self, input_data: AnalyzeProgressInput) -> AnalyzeProgressOutput:
        """Skill para analizar el progreso del usuario."""
        logger.info(f"Ejecutando habilidad: _skill_analyze_progress con input: {input_data}")
        user_id = input_data.user_id
        time_period = input_data.time_period
        metrics = input_data.metrics
        user_profile = input_data.user_profile if hasattr(input_data, 'user_profile') else {}
        
        try:
            # Determinar el tipo de programa del usuario para personalizar el análisis
            context = {
                "user_profile": user_profile,
                "goals": user_profile.get("goals", []) if user_profile else []
            }
            
            try:
                # Clasificar el tipo de programa del usuario
                program_type = await self.program_classification_service.classify_program_type(context)
                logger.info(f"Tipo de programa determinado para análisis de progreso: {program_type}")
                
                # Obtener definición del programa para personalizar el análisis
                program_def = get_program_definition(program_type)
                
                # Preparar contexto específico del programa
                program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
                
                if program_def:
                    program_context += f"- {program_def.get('description', '')}\n"
                    program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                    
                    # Añadir métricas clave específicas del programa si están disponibles
                    if program_def.get("key_metrics"):
                        program_context += "- Métricas clave para este programa:\n"
                        for metric in program_def.get("key_metrics", []):
                            program_context += f"  * {metric}\n"
                    
                    # Añadir consideraciones especiales para el análisis según el programa
                    if program_type == "PRIME":
                        program_context += "\nConsideraciones especiales para PRIME:\n"
                        program_context += "- Enfoque en métricas de rendimiento y progresión\n"
                        program_context += "- Análisis de tendencias de capacidad de trabajo\n"
                        program_context += "- Identificación de patrones de recuperación\n"
                    elif program_type == "LONGEVITY":
                        program_context += "\nConsideraciones especiales para LONGEVITY:\n"
                        program_context += "- Enfoque en métricas de salud a largo plazo\n"
                        program_context += "- Análisis de tendencias de biomarcadores\n"
                        program_context += "- Identificación de patrones de bienestar general\n"
            except Exception as e:
                logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando análisis general.")
                program_type = "GENERAL"
                program_context = ""
                program_def = None
            
            # 1. Obtener datos (simulado por ahora, idealmente de Supabase o StateManager)
            user_data = await self._get_user_data(user_id, time_period, metrics)
            if not user_data:
                raise ValueError("No se encontraron datos para el análisis.")

            # 2. Preparar prompt para Gemini
            metrics_str = ", ".join(metrics) if metrics else "todas las métricas disponibles"
            data_summary = json.dumps(user_data, indent=2, default=str)[:1000] # Resumen de datos
            
            prompt = f"{self.system_instructions}\n"
            prompt += f"Eres un analista especializado en seguimiento de progreso para programas {program_type}.\n"
            prompt += f"Analiza los siguientes datos de progreso para el usuario {user_id} durante el periodo '{time_period}' para las métricas: {metrics_str}.\n"
            prompt += f"Datos:\n{data_summary}\n"
            prompt += f"{program_context}\n"
            prompt += f"Identifica tendencias clave, insights y proporciona un análisis personalizado para el programa {program_type} en formato JSON.\n"
            prompt += f"Incluye recomendaciones específicas basadas en los objetivos del programa {program_type}."

            # 3. Llamar a Gemini para análisis
            analysis_result = await self.gemini_client.generate_structured_output(prompt)
            
            if not isinstance(analysis_result, dict):
                # Si no es JSON, intentar envolverlo
                analysis_result = {"analysis_summary": str(analysis_result)}
            
            # Añadir información del programa al resultado
            analysis_result["program_type"] = program_type
            if program_def:
                analysis_result["program_objective"] = program_def.get("objective", "")

            # 4. (Opcional) Guardar análisis en estado
            analysis_id = f"analysis_{user_id}_{time.time():.0f}"

            logger.info(f"Análisis completado para user {user_id} con programa {program_type}")
            return AnalyzeProgressOutput(
                analysis_id=analysis_id,
                result=analysis_result,
                status="success"
            )

        except Exception as e:
            logger.error(f"Error en skill '_skill_analyze_progress': {e}", exc_info=True)
            raise

    async def _skill_visualize_progress(self, input_data: VisualizeProgressInput) -> VisualizeProgressOutput:
        """Skill para visualizar el progreso del usuario."""
        logger.info(f"Ejecutando habilidad: _skill_visualize_progress con input: {input_data}")
        user_id = input_data.user_id
        metric = input_data.metric
        time_period = input_data.time_period
        chart_type = input_data.chart_type
        user_profile = input_data.user_profile if hasattr(input_data, 'user_profile') else {}
        
        try:
            # Determinar el tipo de programa del usuario para personalizar la visualización
            context = {
                "user_profile": user_profile,
                "goals": user_profile.get("goals", []) if user_profile else []
            }
            
            try:
                # Clasificar el tipo de programa del usuario
                program_type = await self.program_classification_service.classify_program_type(context)
                logger.info(f"Tipo de programa determinado para visualización de progreso: {program_type}")
                
                # Obtener definición del programa para personalizar la visualización
                program_def = get_program_definition(program_type)
                
                # Verificar si la métrica es clave para el programa
                is_key_metric = False
                if program_def and program_def.get("key_metrics"):
                    is_key_metric = metric in program_def.get("key_metrics", [])
                    if is_key_metric:
                        logger.info(f"La métrica {metric} es una métrica clave para el programa {program_type}")
            except Exception as e:
                logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando visualización general.")
                program_type = "GENERAL"
                program_def = None
                is_key_metric = False
            
            # 1. Obtener datos (simulado)
            user_data = await self._get_user_data(user_id, time_period, [metric])
            if not user_data or metric not in user_data or not user_data[metric]:
                raise ValueError(f"No se encontraron datos para la métrica '{metric}'.")  # Extraer fechas y valores
            dates = [item['date'] for item in user_data[metric]]
            values = [item['value'] for item in user_data[metric]]
            
            # Convertir fechas si son strings
            try:
                dates = [datetime.datetime.fromisoformat(d.replace('Z', '+00:00')) if isinstance(d, str) else d for d in dates]
            except ValueError:
                logger.warning(f"No se pudieron parsear algunas fechas para visualización: {dates}")
                # Intentar continuar o devolver error

            # 2. Generar gráfico personalizado según el tipo de programa
            plt.figure(figsize=(10, 5))
            
            # Personalizar colores y estilos según el programa
            if program_type == "PRIME":
                color = '#1E88E5'  # Azul para PRIME
                linestyle = '-'
                linewidth = 2
                marker_size = 8
                title_prefix = "PRIME - "
            elif program_type == "LONGEVITY":
                color = '#43A047'  # Verde para LONGEVITY
                linestyle = '-'
                linewidth = 2
                marker_size = 8
                title_prefix = "LONGEVITY - "
            else:
                color = '#757575'  # Gris para GENERAL
                linestyle = '-'
                linewidth = 1.5
                marker_size = 6
                title_prefix = ""
            
            # Destacar métricas clave con colores más intensos
            if is_key_metric:
                if program_type == "PRIME":
                    color = '#0D47A1'  # Azul más intenso
                    linewidth = 3
                elif program_type == "LONGEVITY":
                    color = '#2E7D32'  # Verde más intenso
                    linewidth = 3
                else:
                    color = '#424242'  # Gris más intenso
                    linewidth = 2
            
            # Generar el gráfico según el tipo especificado
            if chart_type == 'line':
                plt.plot(dates, values, marker='o', color=color, linestyle=linestyle, 
                         linewidth=linewidth, markersize=marker_size)
                
                # Añadir línea de tendencia para métricas clave
                if is_key_metric and len(values) > 2:
                    try:
                        # Crear índices para las fechas
                        x = np.arange(len(dates))
                        # Calcular línea de tendencia
                        z = np.polyfit(x, values, 1)
                        p = np.poly1d(z)
                        # Dibujar línea de tendencia
                        plt.plot(dates, p(x), "--", color=color, alpha=0.7, 
                                 linewidth=linewidth-0.5)
                    except Exception as e:
                        logger.warning(f"No se pudo generar línea de tendencia: {e}")
            elif chart_type == 'bar':
                plt.bar(dates, values, color=color, alpha=0.8, width=0.7)
            else:
                plt.plot(dates, values, marker='o', color=color, linestyle=linestyle, 
                         linewidth=linewidth, markersize=marker_size)
            
            # Añadir zonas objetivo si están definidas para el programa y la métrica
            if program_def and program_def.get("metric_targets") and metric in program_def.get("metric_targets", {}):
                try:
                    target_range = program_def["metric_targets"][metric]
                    if isinstance(target_range, dict) and "min" in target_range and "max" in target_range:
                        min_val = target_range["min"]
                        max_val = target_range["max"]
                        plt.axhspan(min_val, max_val, alpha=0.2, color='green', label="Rango objetivo")
                        plt.legend()
                except Exception as e:
                    logger.warning(f"No se pudo añadir zona objetivo: {e}")
                 
            plt.xlabel("Fecha")
            plt.ylabel(metric.capitalize())
            plt.title(f"{title_prefix}Progreso de {metric.capitalize()} para Usuario {user_id} ({time_period})")
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Añadir anotaciones para valores destacados
            if is_key_metric:
                try:
                    # Encontrar valor máximo
                    max_idx = values.index(max(values))
                    plt.annotate(f"Máx: {values[max_idx]}", 
                                xy=(dates[max_idx], values[max_idx]),
                                xytext=(10, 10),
                                textcoords="offset points",
                                arrowprops=dict(arrowstyle="->", color=color))
                    
                    # Encontrar valor mínimo
                    min_idx = values.index(min(values))
                    plt.annotate(f"Mín: {values[min_idx]}", 
                                xy=(dates[min_idx], values[min_idx]),
                                xytext=(10, -15),
                                textcoords="offset points",
                                arrowprops=dict(arrowstyle="->", color=color))
                except Exception as e:
                    logger.warning(f"No se pudieron añadir anotaciones: {e}")
            
            # 3. Guardar gráfico
            viz_filename = f"viz_{user_id}_{metric}_{time.time():.0f}.png"
            viz_filepath = os.path.join(self.tmp_dir, viz_filename)
            plt.savefig(viz_filepath)
            plt.close() # Cerrar figura para liberar memoria
            
            # 4. (Opcional) Subir a almacenamiento o devolver path/URL
            # Por ahora devolvemos path local (esto necesitaría más lógica para ser útil en ADK)
            # En un escenario real, subiríamos a GCS/S3 y devolveríamos la URL firmada.
            viz_url = f"file://{viz_filepath}" # Placeholder

            logger.info(f"Visualización generada: {viz_filepath}")
            return VisualizeProgressOutput(
                visualization_url=viz_url,
                filepath=viz_filepath,
                status="success"
            )

        except Exception as e:
            logger.error(f"Error en skill '_skill_visualize_progress': {e}", exc_info=True)
            # Limpiar figura si hubo error
            plt.close()
            raise

    async def _skill_compare_progress(self, input_data: CompareProgressInput) -> CompareProgressOutput:
        """Skill para comparar el progreso entre dos periodos."""
        logger.info(f"Ejecutando habilidad: _skill_compare_progress con input: {input_data}")
        user_id = input_data.user_id
        period1 = input_data.period1
        period2 = input_data.period2
        metrics = input_data.metrics
        user_profile = input_data.user_profile if hasattr(input_data, 'user_profile') else {}
        
        try:
            # Determinar el tipo de programa del usuario para personalizar la comparación
            context = {
                "user_profile": user_profile,
                "goals": user_profile.get("goals", []) if user_profile else []
            }
            
            try:
                # Clasificar el tipo de programa del usuario
                program_type = await self.program_classification_service.classify_program_type(context)
                logger.info(f"Tipo de programa determinado para comparación de progreso: {program_type}")
                
                # Obtener definición del programa para personalizar la comparación
                program_def = get_program_definition(program_type)
                
                # Preparar contexto específico del programa
                program_context = f"\n\nCONTEXTO DEL PROGRAMA {program_type}:\n"
                
                if program_def:
                    program_context += f"- {program_def.get('description', '')}\n"
                    program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                    
                    # Añadir métricas clave específicas del programa si están disponibles
                    key_metrics_in_request = []
                    if program_def.get("key_metrics"):
                        program_context += "- Métricas clave para este programa:\n"
                        for metric in program_def.get("key_metrics", []):
                            program_context += f"  * {metric}\n"
                            if metric in metrics:
                                key_metrics_in_request.append(metric)
                    
                    # Añadir consideraciones especiales para la comparación según el programa
                    if program_type == "PRIME":
                        program_context += "\nConsideraciones especiales para comparación en PRIME:\n"
                        program_context += "- Enfoque en progresión de rendimiento y capacidad de trabajo\n"
                        program_context += "- Análisis de consistencia en patrones de entrenamiento\n"
                        program_context += "- Evaluación de adaptación a cargas de trabajo\n"
                    elif program_type == "LONGEVITY":
                        program_context += "\nConsideraciones especiales para comparación en LONGEVITY:\n"
                        program_context += "- Enfoque en tendencias de biomarcadores y salud a largo plazo\n"
                        program_context += "- Análisis de estabilidad en métricas de salud\n"
                        program_context += "- Evaluación de mejoras sostenibles en bienestar general\n"
            except Exception as e:
                logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando comparación general.")
                program_type = "GENERAL"
                program_context = ""
                program_def = None
                key_metrics_in_request = []
            
            # 1. Obtener datos para ambos periodos (simulado)
            data_p1 = await self._get_user_data(user_id, period1, metrics)
            data_p2 = await self._get_user_data(user_id, period2, metrics)

            if not data_p1 or not data_p2:
                raise ValueError("Datos insuficientes para comparación.")

            # 2. Preparar prompt para Gemini
            metrics_str = ", ".join(metrics)
            summary_p1 = json.dumps(data_p1, indent=2, default=str)[:500]
            summary_p2 = json.dumps(data_p2, indent=2, default=str)[:500]
            
            # Destacar métricas clave si existen
            key_metrics_str = ", ".join(key_metrics_in_request) if key_metrics_in_request else ""
            key_metrics_context = f"\nPresta especial atención a las siguientes métricas clave para el programa {program_type}: {key_metrics_str}" if key_metrics_in_request else ""
            
            prompt = f"{self.system_instructions}\n"
            prompt += f"Eres un analista especializado en comparación de progreso para programas {program_type}.\n"
            prompt += f"Compara los datos de progreso del usuario {user_id} para las métricas '{metrics_str}' entre el periodo '{period1}' y el periodo '{period2}'.\n"
            prompt += f"Datos Periodo 1 ({period1}):\n{summary_p1}\n\n"
            prompt += f"Datos Periodo 2 ({period2}):\n{summary_p2}\n\n"
            prompt += f"{program_context}\n"
            prompt += f"{key_metrics_context}\n"
            prompt += f"Identifica las diferencias clave, calcula los cambios porcentuales si aplica, y proporciona un análisis personalizado para el programa {program_type} en formato JSON.\n"
            prompt += f"Incluye recomendaciones específicas basadas en los objetivos del programa {program_type}."

            # 3. Llamar a Gemini para comparación
            comparison_result = await self.gemini_client.generate_structured_output(prompt)

            if not isinstance(comparison_result, dict):
                comparison_result = {"comparison_summary": str(comparison_result)}
            
            # Añadir información del programa al resultado
            comparison_result["program_type"] = program_type
            if program_def:
                comparison_result["program_objective"] = program_def.get("objective", "")
                if key_metrics_in_request:
                    comparison_result["key_metrics_analyzed"] = key_metrics_in_request

            logger.info(f"Comparación completada para user {user_id} con programa {program_type}")
            return CompareProgressOutput(
                result=comparison_result,
                status="success"
            )
            
        except Exception as e:
            logger.error(f"Error en skill '_skill_compare_progress': {e}", exc_info=True)
            raise

    # Método auxiliar para obtener datos (simulación)
    async def _get_user_data(self, user_id: str, time_period: str, metrics: Optional[List[str]]) -> Optional[Dict[str, Any]]:
         """Obtiene datos del usuario (simulado). Debería interactuar con Supabase/StateManager."""
         logger.debug(f"Simulando obtención de datos para user {user_id}, periodo {time_period}, métricas: {metrics}")
         # Simulación: Devolver datos de ejemplo
         # En una implementación real, consultaría Supabase o el StateManager
         if time_period == 'last_month':
             start_date = datetime.date.today() - datetime.timedelta(days=30)
         elif time_period == 'last_3_months':
             start_date = datetime.date.today() - datetime.timedelta(days=90)
         else:
             start_date = datetime.date.today() - datetime.timedelta(days=7)
         
         mock_data = {}
         requested_metrics = metrics or ['weight', 'performance'] # Default metrics

         for metric in requested_metrics:
             mock_data[metric] = []
             current_date = start_date
             base_value = 70 if metric == 'weight' else 80 # Valores base simulados
             trend = -0.1 if metric == 'weight' else 0.2 # Tendencia simulada
             while current_date <= datetime.date.today():
                 value = base_value + (current_date - start_date).days * trend + np.random.randn() * (1 if metric == 'weight' else 2)
                 mock_data[metric].append({"date": current_date.isoformat(), "value": round(value, 2)})
                 current_date += datetime.timedelta(days=np.random.randint(1, 4)) # Días variables
                 
         # logger.debug(f"Datos simulados generados: {json.dumps(mock_data, indent=2, default=str)}")
         return mock_data

    # --- Métodos de Contexto ---

    async def _get_context(
        self, user_id: Optional[str], session_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación para un usuario y sesión específicos.
        
        Este método intenta primero obtener el contexto del adaptador del StateManager para persistencia.
        Si no está disponible, usa el almacenamiento en memoria como fallback.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            
        Returns:
            Dict[str, Any]: Contexto de la conversación
        """
        # Intentar cargar desde el adaptador del StateManager
        if user_id and session_id:
            try:
                state_data = await state_manager_adapter.load_state(user_id, session_id)
                if state_data and isinstance(state_data, dict):
                    logger.debug(f"Contexto cargado desde adaptador del StateManager para user_id={user_id}, session_id={session_id}")
                    return state_data
            except Exception as e:
                logger.warning(f"Error al cargar contexto desde adaptador del StateManager: {e}")

        # Fallback: devolver contexto vacío
        return {"history": []}
    
    async def _update_context(self, context: Dict[str, Any], user_id: str, session_id: str) -> None:
        """
        Actualiza el contexto de la conversación en el adaptador del StateManager.

        Args:
            context (Dict[str, Any]): Contexto actualizado.
            user_id (str): ID del usuario.
            session_id (str): ID de la sesión.
        """
        try:
            # Actualizar la marca de tiempo
            context["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Guardar el contexto en el adaptador del StateManager
            await state_manager_adapter.save_state(user_id, session_id, context)
            logger.info(f"Contexto actualizado en adaptador del StateManager para user_id={user_id}, session_id={session_id}")
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)
    
    # --- Métodos para análisis de intenciones ---
    async def _classify_query(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario utilizando el adaptador del Intent Analyzer.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta clasificada
        """
        try:
            # Utilizar el adaptador del Intent Analyzer para analizar la intención
            intent_analysis = await intent_analyzer_adapter.analyze_intent(query)
            
            # Mapear la intención primaria a los tipos de consulta del agente
            primary_intent = intent_analysis.get("primary_intent", "").lower()
            
            # Mapeo de intenciones a tipos de consulta
            intent_to_query_type = {
                "analyze": "analyze_progress",
                "visualize": "visualize_progress",
                "compare": "compare_progress"
            }
            
            # Buscar coincidencias exactas
            if primary_intent in intent_to_query_type:
                return intent_to_query_type[primary_intent]
            
            # Buscar coincidencias parciales
            for intent, query_type in intent_to_query_type.items():
                if intent in primary_intent:
                    return query_type
            
            # Si no hay coincidencias, usar el método de palabras clave como fallback
            return self._classify_query_by_keywords(query)
        except Exception as e:
            logger.error(f"Error al clasificar consulta con Intent Analyzer: {e}", exc_info=True)
            # En caso de error, usar el método de palabras clave como fallback
            return self._classify_query_by_keywords(query)
    
    def _classify_query_by_keywords(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario utilizando palabras clave.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta clasificada
        """
        query_lower = query.lower()
        
        # Palabras clave para análisis de progreso
        analyze_keywords = [
            "analiza", "análisis", "tendencia", "progreso", "evalúa", 
            "evaluación", "resumen", "resumir", "interpretar", "interpretación"
        ]
        
        # Palabras clave para visualización
        visualize_keywords = [
            "visualiza", "gráfico", "gráfica", "mostrar", "ver", 
            "imagen", "visual", "visualización", "dibujar", "representar"
        ]
        
        # Palabras clave para comparación
        compare_keywords = [
            "compara", "comparación", "diferencia", "contrastar", "versus", 
            "vs", "entre", "cambio", "evolución", "antes y después"
        ]
        
        # Verificar coincidencias con palabras clave
        for keyword in compare_keywords:
            if keyword in query_lower:
                return "compare_progress"
                
        for keyword in visualize_keywords:
            if keyword in query_lower:
                return "visualize_progress"
                
        for keyword in analyze_keywords:
            if keyword in query_lower:
                return "analyze_progress"
                
        # Si no hay coincidencias, devolver tipo general
        return "analyze_progress"
    
    # --- Métodos para comunicación entre agentes ---
    async def _consult_other_agent(self, agent_id: str, query: str, user_id: Optional[str] = None, session_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta a otro agente utilizando el adaptador de A2A.
        
        Args:
            agent_id: ID del agente a consultar
            query: Consulta a enviar al agente
            user_id: ID del usuario
            session_id: ID de la sesión
            context: Contexto adicional para la consulta
            
        Returns:
            Dict[str, Any]: Respuesta del agente consultado
        """
        try:
            # Crear contexto para la consulta
            task_context = {
                "user_id": user_id,
                "session_id": session_id,
                "additional_context": context or {}
            }
            
            # Llamar al agente utilizando el adaptador de A2A
            response = await a2a_adapter.call_agent(
                agent_id=agent_id,
                user_input=query,
                context=task_context
            )
            
            logger.info(f"Respuesta recibida del agente {agent_id}")
            return response
        except Exception as e:
            logger.error(f"Error al consultar al agente {agent_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "output": f"Error al consultar al agente {agent_id}",
                "agent_id": agent_id,
                "agent_name": agent_id
            }
    
    async def _skill_analyze_body_progress(self, input_data: AnalyzeBodyProgressInput) -> AnalyzeBodyProgressOutput:
        """
        Skill para analizar el progreso corporal mediante imágenes antes/después.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            AnalyzeBodyProgressOutput: Análisis del progreso corporal
        """
        logger.info(f"Ejecutando habilidad: _skill_analyze_body_progress para usuario: {input_data.user_id}")
        
        # Verificar si las capacidades de visión están disponibles
        if not hasattr(self, '_vision_capabilities_available') or not self._vision_capabilities_available:
            logger.warning("Las capacidades de visión no están disponibles. Usando análisis simulado.")
            return self._generate_mock_body_progress_analysis(input_data)
        
        try:
            # Obtener datos de las imágenes
            before_image = input_data.before_image
            after_image = input_data.after_image
            user_id = input_data.user_id or "usuario_anónimo"
            time_between_images = input_data.time_between_images or "No especificado"
            focus_areas = input_data.focus_areas or ["composición corporal", "postura", "masa muscular", "definición"]
            user_profile = input_data.user_profile or {}
            
            # Determinar el tipo de programa del usuario para personalizar el análisis
            context = {
                "user_profile": user_profile,
                "goals": user_profile.get("goals", []) if user_profile else []
            }
            
            try:
                # Clasificar el tipo de programa del usuario
                program_type = await self.program_classification_service.classify_program_type(context)
                logger.info(f"Tipo de programa determinado para análisis de progreso corporal: {program_type}")
                
                # Obtener definición del programa para personalizar el análisis
                program_def = get_program_definition(program_type)
                program_context = f"""\nCONTEXTO DEL PROGRAMA {program_type}:\n"""
                
                if program_def:
                    program_context += f"- {program_def.get('description', '')}\n"
                    program_context += f"- Objetivo: {program_def.get('objective', '')}\n"
                    
                    # Añadir consideraciones específicas del programa
                    if program_type == "PRIME":
                        program_context += "- Enfoque en desarrollo muscular y rendimiento físico\n"
                    elif program_type == "LONGEVITY":
                        program_context += "- Enfoque en composición corporal saludable y postura\n"
            except Exception as e:
                logger.warning(f"No se pudo determinar el tipo de programa: {e}. Usando análisis general.")
                program_type = "GENERAL"
                program_context = ""
            
            # Utilizar las capacidades de visión del agente base
            with self.tracer.start_as_current_span("body_progress_analysis"):
                # Analizar ambas imágenes utilizando el procesador de visión
                before_analysis = await self.vision_processor.analyze_image(before_image)
                after_analysis = await self.vision_processor.analyze_image(after_image)
                
                # Extraer análisis de progreso corporal usando el modelo multimodal
                prompt = f"""
                Eres un experto en análisis de progreso físico y composición corporal. Analiza estas dos imágenes
                de antes y después de un usuario con programa tipo {program_type} y proporciona un análisis detallado
                del progreso corporal.
                
                Tiempo transcurrido entre imágenes: {time_between_images}
                
                Enfócate específicamente en las siguientes áreas:
                {', '.join(focus_areas)}
                
                {program_context}
                
                Proporciona:
                1. Un resumen general del progreso observado
                2. Métricas específicas de cambio corporal (con valores estimados si es posible)
                3. Análisis por áreas corporales
                4. Una puntuación general de progreso (0-10)
                5. Recomendaciones basadas en los cambios observados
                
                Sé objetivo, detallado y proporciona feedback constructivo basado en los cambios visibles.
                """
                
                multimodal_result = await self.multimodal_adapter.compare_images(
                    image_data1=before_image,
                    image_data2=after_image,
                    comparison_prompt=prompt,
                    temperature=0.2,
                    max_output_tokens=1024
                )
                
                # Extraer métricas de cambio corporal estructuradas
                metrics_prompt = f"""
                Basándote en el siguiente análisis de progreso corporal, extrae métricas específicas de cambio
                en formato estructurado. Para cada métrica, incluye:
                1. Nombre de la métrica
                2. Valor antes (si es posible)
                3. Valor después (si es posible)
                4. Cambio (absoluto o porcentual)
                5. Confianza en la medición (0.0-1.0)
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """
                
                metrics_response = await self.gemini_client.generate_structured_output(metrics_prompt)
                
                # Procesar métricas de cambio
                metrics = []
                if isinstance(metrics_response, list):
                    for metric in metrics_response:
                        if isinstance(metric, dict) and "metric_name" in metric:
                            metrics.append(BodyChangeMetric(
                                metric_name=metric.get("metric_name", "No especificado"),
                                before_value=metric.get("before_value"),
                                after_value=metric.get("after_value"),
                                change=metric.get("change"),
                                confidence=metric.get("confidence", 0.7)
                            ))
                elif isinstance(metrics_response, dict) and "metrics" in metrics_response:
                    for metric in metrics_response["metrics"]:
                        if isinstance(metric, dict) and "metric_name" in metric:
                            metrics.append(BodyChangeMetric(
                                metric_name=metric.get("metric_name", "No especificado"),
                                before_value=metric.get("before_value"),
                                after_value=metric.get("after_value"),
                                change=metric.get("change"),
                                confidence=metric.get("confidence", 0.7)
                            ))
                
                # Si no hay métricas, crear algunas genéricas
                if not metrics:
                    metrics.append(BodyChangeMetric(
                        metric_name="Composición corporal general",
                        before_value="No disponible",
                        after_value="No disponible",
                        change="Cambio visible pero no cuantificable",
                        confidence=0.6
                    ))
                
                # Extraer cambios por áreas corporales
                body_areas_prompt = f"""
                Basándote en el siguiente análisis de progreso corporal, extrae cambios específicos por áreas corporales
                en formato estructurado. Para cada área corporal, incluye:
                1. Nombre del área corporal
                2. Cambios observados (lista de strings)
                3. Nivel de mejora (ninguno, leve, moderado, significativo)
                4. Notas adicionales (opcional)
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve la información en formato JSON estructurado.
                """
                
                body_areas_response = await self.gemini_client.generate_structured_output(body_areas_prompt)
                
                # Procesar cambios por áreas corporales
                body_areas = []
                if isinstance(body_areas_response, list):
                    for area in body_areas_response:
                        if isinstance(area, dict) and "body_area" in area:
                            body_areas.append(BodyAreaChange(
                                body_area=area.get("body_area", "No especificado"),
                                changes_observed=area.get("changes_observed", ["No especificado"]),
                                improvement_level=area.get("improvement_level", "leve"),
                                notes=area.get("notes")
                            ))
                elif isinstance(body_areas_response, dict) and "body_areas" in body_areas_response:
                    for area in body_areas_response["body_areas"]:
                        if isinstance(area, dict) and "body_area" in area:
                            body_areas.append(BodyAreaChange(
                                body_area=area.get("body_area", "No especificado"),
                                changes_observed=area.get("changes_observed", ["No especificado"]),
                                improvement_level=area.get("improvement_level", "leve"),
                                notes=area.get("notes")
                            ))
                
                # Si no hay áreas corporales, crear algunas genéricas
                if not body_areas:
                    for area in ["Torso", "Brazos", "Piernas"]:
                        body_areas.append(BodyAreaChange(
                            body_area=area,
                            changes_observed=["Cambios no especificados"],
                            improvement_level="leve",
                            notes=None
                        ))
                
                # Extraer recomendaciones
                recommendations_prompt = f"""
                Basándote en el siguiente análisis de progreso corporal, genera 3-5 recomendaciones específicas
                y accionables para continuar o mejorar el progreso. Considera el contexto del programa {program_type}.
                
                Análisis:
                {multimodal_result.get("text", "")}
                
                Devuelve las recomendaciones como una lista de strings.
                """
                
                recommendations_response = await self.gemini_client.generate_structured_output(recommendations_prompt)
                
                # Procesar recomendaciones
                recommendations = []
                if isinstance(recommendations_response, list):
                    recommendations = [rec for rec in recommendations_response if isinstance(rec, str)]
                elif isinstance(recommendations_response, dict) and "recommendations" in recommendations_response:
                    recommendations = [rec for rec in recommendations_response["recommendations"] if isinstance(rec, str)]
                
                # Si no hay recomendaciones, crear algunas genéricas
                if not recommendations:
                    recommendations = [
                        "Mantener consistencia en el programa actual",
                        "Considerar ajustes en la nutrición para optimizar resultados",
                        "Documentar el progreso regularmente con fotos en las mismas condiciones"
                    ]
                
                # Calcular puntuación general de progreso (simulada)
                overall_progress_score = 7.5  # Valor simulado entre 0-10
                
                # Crear artefacto con el análisis
                analysis_id = str(uuid.uuid4())
                artifact = BodyProgressAnalysisArtifact(
                    analysis_id=analysis_id,
                    created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                    user_id=user_id,
                    progress_score=overall_progress_score,
                    comparison_image_url="",  # En un caso real, aquí iría la URL de la imagen comparativa
                    time_period=time_between_images
                )
                
                # Extraer resumen del progreso
                progress_summary = multimodal_result.get("text", "").split("\n\n")[0] if multimodal_result.get("text") else "No se pudo generar un resumen del progreso."
                
                # Crear la salida de la skill
                return AnalyzeBodyProgressOutput(
                    analysis_id=analysis_id,
                    progress_summary=progress_summary,
                    metrics=metrics,
                    body_areas=body_areas,
                    overall_progress_score=overall_progress_score,
                    recommendations=recommendations,
                    comparison_image_url=""  # En un caso real, aquí iría la URL de la imagen comparativa
                )
                
        except Exception as e:
            logger.error(f"Error al analizar progreso corporal: {e}", exc_info=True)
            
            # En caso de error, devolver un análisis básico
            return AnalyzeBodyProgressOutput(
                analysis_id=str(uuid.uuid4()),
                progress_summary="No se pudo realizar el análisis debido a un error en el procesamiento.",
                metrics=[
                    BodyChangeMetric(
                        metric_name="Error en análisis",
                        before_value=None,
                        after_value=None,
                        change=None,
                        confidence=0.0
                    )
                ],
                body_areas=[
                    BodyAreaChange(
                        body_area="General",
                        changes_observed=["No se pudieron determinar cambios debido a un error"],
                        improvement_level="ninguno",
                        notes="Error en el procesamiento de imágenes"
                    )
                ],
                overall_progress_score=0.0,
                recommendations=["Intente nuevamente con imágenes de mejor calidad o en mejor iluminación."],
                comparison_image_url=None
            )
    
    async def _skill_generate_progress_visualization(self, input_data: GenerateProgressVisualizationInput) -> GenerateProgressVisualizationOutput:
        """
        Skill para generar visualizaciones de progreso a partir de múltiples imágenes.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            GenerateProgressVisualizationOutput: Visualización del progreso generada
        """
        logger.info(f"Ejecutando habilidad: _skill_generate_progress_visualization para usuario: {input_data.user_id}")
        
        # Verificar si las capacidades de visión están disponibles
        if not hasattr(self, '_vision_capabilities_available') or not self._vision_capabilities_available:
            logger.warning("Las capacidades de visión no están disponibles. Usando visualización simulada.")
            return self._generate_mock_progress_visualization(input_data)
        
        try:
            # Obtener datos de las imágenes
            images = input_data.images
            user_id = input_data.user_id or "usuario_anónimo"
            visualization_type = input_data.visualization_type
            metrics_to_highlight = input_data.metrics_to_highlight or []
            include_measurements = input_data.include_measurements
            
            if not images or len(images) < 2:
                raise ValueError("Se requieren al menos dos imágenes para generar una visualización de progreso.")
            
            # Ordenar imágenes por fecha si es posible
            # Ordenar imágenes por fecha si es posible
            try:
                images = sorted(images, key=lambda x: x.get("date", ""))
            except Exception as e:
                logger.warning(f"No se pudieron ordenar las imágenes por fecha: {e}")
            
            # Utilizar las capacidades de visión del agente base
            with self.tracer.start_as_current_span("progress_visualization_generation"):
                # Procesar cada imagen para preparar la visualización
                processed_images = []
                for idx, img_data in enumerate(images):
                    image_data = img_data.get("image_data")
                    if not image_data:
                        continue
                    
                    # Analizar la imagen para extraer información relevante
                    analysis = await self.vision_processor.analyze_image(image_data)
                    
                    # Añadir a la lista de imágenes procesadas
                    processed_images.append({
                        "image_data": image_data,
                        "date": img_data.get("date", f"Imagen {idx+1}"),
                        "analysis": analysis
                    })
                
                # Generar la visualización según el tipo especificado
                visualization_id = str(uuid.uuid4())
                visualization_filename = f"progress_viz_{user_id}_{visualization_id}.png"
                visualization_filepath = os.path.join(self.tmp_dir, visualization_filename)
                
                # Crear una figura para la visualización
                if visualization_type == "side_by_side":
                    # Visualización lado a lado
                    fig, axes = plt.subplots(1, len(processed_images), figsize=(5*len(processed_images), 5))
                    
                    # Si solo hay una imagen, axes no será un array
                    if len(processed_images) == 1:
                        axes = [axes]
                    
                    for i, img_data in enumerate(processed_images):
                        # Aquí iría el código para cargar y mostrar la imagen
                        # Como no podemos procesar imágenes reales en este ejemplo, simulamos
                        axes[i].text(0.5, 0.5, f"Imagen {i+1}\n{img_data['date']}",
                                    horizontalalignment='center', verticalalignment='center')
                        axes[i].set_title(img_data['date'])
                        axes[i].axis('off')
                    
                    plt.tight_layout()
                    
                elif visualization_type == "grid":
                    # Visualización en cuadrícula
                    rows = (len(processed_images) + 2) // 3  # Calcular filas necesarias
                    cols = min(3, len(processed_images))  # Máximo 3 columnas
                    
                    fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 5*rows))
                    axes = axes.flatten() if rows > 1 or cols > 1 else [axes]
                    
                    for i, img_data in enumerate(processed_images):
                        if i < len(axes):
                            # Aquí iría el código para cargar y mostrar la imagen
                            axes[i].text(0.5, 0.5, f"Imagen {i+1}\n{img_data['date']}",
                                        horizontalalignment='center', verticalalignment='center')
                            axes[i].set_title(img_data['date'])
                            axes[i].axis('off')
                    
                    # Ocultar ejes vacíos
                    for i in range(len(processed_images), len(axes)):
                        axes[i].axis('off')
                    
                    plt.tight_layout()
                    
                elif visualization_type == "timeline":
                    # Visualización en línea de tiempo
                    fig, ax = plt.subplots(figsize=(12, 6))
                    
                    # Crear una línea de tiempo con marcadores para cada imagen
                    ax.plot([i for i in range(len(processed_images))],
                           [0 for _ in range(len(processed_images))],
                           'o-', markersize=15, linewidth=2)
                    
                    # Añadir etiquetas con fechas
                    for i, img_data in enumerate(processed_images):
                        ax.annotate(img_data['date'],
                                   xy=(i, 0),
                                   xytext=(0, 10),
                                   textcoords="offset points",
                                   ha='center')
                    
                    ax.set_title("Línea de tiempo de progreso")
                    ax.axis('off')
                    
                    plt.tight_layout()
                    
                else:  # Default: side_by_side
                    fig, axes = plt.subplots(1, len(processed_images), figsize=(5*len(processed_images), 5))
                    
                    # Si solo hay una imagen, axes no será un array
                    if len(processed_images) == 1:
                        axes = [axes]
                    
                    for i, img_data in enumerate(processed_images):
                        # Aquí iría el código para cargar y mostrar la imagen
                        axes[i].text(0.5, 0.5, f"Imagen {i+1}\n{img_data['date']}",
                                    horizontalalignment='center', verticalalignment='center')
                        axes[i].set_title(img_data['date'])
                        axes[i].axis('off')
                    
                    plt.tight_layout()
                
                # Añadir título general
                fig.suptitle(f"Visualización de Progreso - {user_id}", fontsize=16)
                
                # Guardar la visualización
                plt.savefig(visualization_filepath)
                plt.close()
                
                # Calcular el período de tiempo cubierto
                time_span = "No disponible"
                if len(processed_images) >= 2:
                    try:
                        first_date = processed_images[0].get("date", "")
                        last_date = processed_images[-1].get("date", "")
                        if first_date and last_date and first_date != last_date:
                            time_span = f"{first_date} a {last_date}"
                    except Exception as e:
                        logger.warning(f"No se pudo calcular el período de tiempo: {e}")
                
                # Crear la salida de la skill
                return GenerateProgressVisualizationOutput(
                    visualization_id=visualization_id,
                    visualization_url=f"file://{visualization_filepath}",  # En un caso real, aquí iría la URL de la visualización
                    visualization_type=visualization_type,
                    image_count=len(processed_images),
                    time_span=time_span,
                    notes=f"Visualización generada con {len(processed_images)} imágenes en formato {visualization_type}"
                )
                
        except Exception as e:
            logger.error(f"Error al generar visualización de progreso: {e}", exc_info=True)
            
            # Limpiar figura si hubo error
            plt.close()
            
            # En caso de error, devolver una respuesta básica
            return GenerateProgressVisualizationOutput(
                visualization_id=str(uuid.uuid4()),
                visualization_url="",
                visualization_type=input_data.visualization_type,
                image_count=len(input_data.images) if input_data.images else 0,
                time_span=None,
                notes="No se pudo generar la visualización debido a un error en el procesamiento."
            )
    
    async def _generate_mock_body_progress_analysis(self, input_data: AnalyzeBodyProgressInput) -> AnalyzeBodyProgressOutput:
            """
            Genera un análisis simulado del progreso corporal cuando las capacidades de visión no están disponibles.
            
            Args:
                input_data: Datos de entrada para la skill
                
            Returns:
                AnalyzeBodyProgressOutput: Análisis simulado del progreso corporal
            """
            logger.info("Generando análisis simulado de progreso corporal")
            
            user_id = input_data.user_id or "usuario_anónimo"
            time_between_images = input_data.time_between_images or "No especificado"
            focus_areas = input_data.focus_areas or ["composición corporal", "postura", "masa muscular", "definición"]
            
            # Generar un ID de análisis
            analysis_id = str(uuid.uuid4())
            
            # Generar métricas simuladas
            metrics = [
                BodyChangeMetric(
                    metric_name="Composición corporal",
                    before_value="Inicial",
                    after_value="Mejorado",
                    change="Cambio positivo visible",
                    confidence=0.7
                ),
                BodyChangeMetric(
                    metric_name="Masa muscular",
                    before_value="Moderada",
                    after_value="Incrementada",
                    change="Aumento aproximado del 5-10%",
                    confidence=0.6
                ),
                BodyChangeMetric(
                    metric_name="Definición muscular",
                    before_value="Baja",
                    after_value="Media",
                    change="Mejora notable",
                    confidence=0.65
                )
            ]
            
            # Generar cambios por áreas corporales simulados
            body_areas = []
            for area in ["Torso", "Brazos", "Piernas"]:
                body_areas.append(BodyAreaChange(
                    body_area=area,
                    changes_observed=["Mejora en tono muscular", "Mayor definición"],
                    improvement_level="moderado",
                    notes="Análisis simulado - sin capacidades de visión"
                ))
            
            # Generar recomendaciones simuladas
            recommendations = [
                "Continuar con el programa actual de entrenamiento",
                "Mantener consistencia en la nutrición",
                "Documentar el progreso con fotos regulares en las mismas condiciones",
                "Considerar ajustes en la intensidad del entrenamiento para seguir progresando"
            ]
            
            # Generar puntuación simulada
            overall_progress_score = 7.0
            
            # Generar resumen simulado
            progress_summary = (
                f"Análisis simulado de progreso corporal para el usuario {user_id} durante el período {time_between_images}. "
                f"Se observa una mejora general en las áreas de enfoque: {', '.join(focus_areas)}. "
                f"La puntuación general de progreso es {overall_progress_score}/10, indicando un avance positivo. "
                "Este es un análisis simulado debido a que las capacidades de visión no están disponibles."
            )
            
            return AnalyzeBodyProgressOutput(
                analysis_id=analysis_id,
                progress_summary=progress_summary,
                metrics=metrics,
                body_areas=body_areas,
                overall_progress_score=overall_progress_score,
                recommendations=recommendations,
                comparison_image_url=None
            )
        
    async def _generate_mock_progress_visualization(self, input_data: GenerateProgressVisualizationInput) -> GenerateProgressVisualizationOutput:
        """
        Genera una visualización simulada del progreso cuando las capacidades de visión no están disponibles.
        
        Args:
            input_data: Datos de entrada para la skill
            
        Returns:
            GenerateProgressVisualizationOutput: Visualización simulada del progreso
        """
        logger.info("Generando visualización simulada de progreso")
        
        user_id = input_data.user_id or "usuario_anónimo"
        visualization_type = input_data.visualization_type or "side_by_side"
        images = input_data.images or []
        
        # Generar un ID de visualización
        visualization_id = str(uuid.uuid4())
        
        # Crear una visualización básica
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Añadir texto explicativo
        ax.text(0.5, 0.5,
                "Visualización simulada de progreso\n(Capacidades de visión no disponibles)",
                horizontalalignment='center',
                verticalalignment='center',
                fontsize=14)
        
        # Añadir información sobre las imágenes
        image_count = len(images)
        image_info = f"Número de imágenes: {image_count}"
        ax.text(0.5, 0.4, image_info, horizontalalignment='center', fontsize=12)
        
        # Añadir información sobre el tipo de visualización
        viz_info = f"Tipo de visualización solicitada: {visualization_type}"
        ax.text(0.5, 0.3, viz_info, horizontalalignment='center', fontsize=12)
        
        # Añadir nota sobre la simulación
        note = "Esta es una visualización simulada debido a que las capacidades de visión no están disponibles."
        ax.text(0.5, 0.2, note, horizontalalignment='center', fontsize=10, style='italic')
        
        # Configurar el gráfico
        ax.set_title(f"Progreso simulado - {user_id}")
        ax.axis('off')
        
        # Guardar la visualización
        visualization_filename = f"mock_viz_{user_id}_{visualization_id}.png"
        visualization_filepath = os.path.join(self.tmp_dir, visualization_filename)
        plt.savefig(visualization_filepath)
        plt.close()
        
        # Calcular el período de tiempo simulado
        time_span = "No disponible"
        if len(images) >= 2:
            try:
                dates = [img.get("date", "") for img in images if img.get("date")]
                if dates and len(dates) >= 2:
                    time_span = f"{dates[0]} a {dates[-1]}"
            except Exception as e:
                logger.warning(f"No se pudo calcular el período de tiempo simulado: {e}")
        
        return GenerateProgressVisualizationOutput(
            visualization_id=visualization_id,
            visualization_url=f"file://{visualization_filepath}",
            visualization_type=visualization_type,
            image_count=image_count,
            time_span=time_span,
            notes="Visualización simulada generada sin capacidades de visión"
        )
                

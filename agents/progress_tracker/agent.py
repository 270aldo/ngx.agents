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
    ProgressVisualizationArtifact
)

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from infrastructure.adapters.intent_analyzer_adapter import intent_analyzer_adapter
from infrastructure.adapters.a2a_adapter import a2a_adapter
from core.logging_config import get_logger

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
            )
        ]

        # Definir las capacidades del agente
        _capabilities = [
            "analyze_progress",
            "visualize_progress",
            "compare_progress",
            "data_analysis",
            "trend_identification"
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
        
        try:
            # 1. Obtener datos (simulado por ahora, idealmente de Supabase o StateManager)
            user_data = await self._get_user_data(user_id, time_period, metrics)
            if not user_data:
                raise ValueError("No se encontraron datos para el análisis.")

            # 2. Preparar prompt para Gemini
            metrics_str = ", ".join(metrics) if metrics else "todas las métricas disponibles"
            data_summary = json.dumps(user_data, indent=2, default=str)[:1000] # Resumen de datos
            prompt = f"{self.system_instructions}\nAnaliza los siguientes datos de progreso para el usuario {user_id} durante el periodo '{time_period}' para las métricas: {metrics_str}.\nDatos:\n{data_summary}\n\nIdentifica tendencias clave, insights y proporciona un resumen conciso del análisis en formato JSON." 

            # 3. Llamar a Gemini para análisis
            analysis_result = await self.gemini_client.generate_structured_output(prompt)
            
            if not isinstance(analysis_result, dict):
                # Si no es JSON, intentar envolverlo
                analysis_result = {"analysis_summary": str(analysis_result)}

            # 4. (Opcional) Guardar análisis en estado
            analysis_id = f"analysis_{user_id}_{time.time():.0f}"

            logger.info(f"Análisis completado para user {user_id}")
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
        
        try:
            # 1. Obtener datos (simulado)
            user_data = await self._get_user_data(user_id, time_period, [metric])
            if not user_data or metric not in user_data or not user_data[metric]:
                raise ValueError(f"No se encontraron datos para la métrica '{metric}'.")

            # Extraer fechas y valores
            dates = [item['date'] for item in user_data[metric]]
            values = [item['value'] for item in user_data[metric]]
            
            # Convertir fechas si son strings
            try:
                dates = [datetime.datetime.fromisoformat(d.replace('Z', '+00:00')) if isinstance(d, str) else d for d in dates]
            except ValueError:
                logger.warning(f"No se pudieron parsear algunas fechas para visualización: {dates}")
                # Intentar continuar o devolver error

            # 2. Generar gráfico
            plt.figure(figsize=(10, 5))
            if chart_type == 'line':
                plt.plot(dates, values, marker='o')
            elif chart_type == 'bar':
                plt.bar(dates, values)
            else:
                plt.plot(dates, values, marker='o') # Default a línea
                 
            plt.xlabel("Fecha")
            plt.ylabel(metric.capitalize())
            plt.title(f"Progreso de {metric.capitalize()} para Usuario {user_id} ({time_period})")
            plt.xticks(rotation=45)
            plt.tight_layout()
            
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
        
        try:
            # 1. Obtener datos para ambos periodos (simulado)
            data_p1 = await self._get_user_data(user_id, period1, metrics)
            data_p2 = await self._get_user_data(user_id, period2, metrics)

            if not data_p1 or not data_p2:
                raise ValueError("Datos insuficientes para comparación.")

            # 2. Preparar prompt para Gemini
            metrics_str = ", ".join(metrics)
            summary_p1 = json.dumps(data_p1, indent=2, default=str)[:500]
            summary_p2 = json.dumps(data_p2, indent=2, default=str)[:500]
            prompt = f"""{self.system_instructions}\nCompara los datos de progreso del usuario {user_id} para las métricas '{metrics_str}' entre el periodo '{period1}' y el periodo '{period2}'.
            Datos Periodo 1 ({period1}):\n{summary_p1}\n
            Datos Periodo 2 ({period2}):\n{summary_p2}\n
            Identifica las diferencias clave, calcula los cambios porcentuales si aplica, y proporciona un resumen de la comparación en formato JSON."""

            # 3. Llamar a Gemini para comparación
            comparison_result = await self.gemini_client.generate_structured_output(prompt)

            if not isinstance(comparison_result, dict):
                comparison_result = {"comparison_summary": str(comparison_result)}

            logger.info(f"Comparación completada para user {user_id}")
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

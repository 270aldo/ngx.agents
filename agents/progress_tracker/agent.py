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

from agents.base.adk_agent import ADKAgent, Skill, create_result
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
from core.state_manager import StateManager
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)

class ProgressTracker(ADKAgent):
    """
    Agente especializado en seguimiento y análisis de progreso del usuario.
    """

    def __init__(
        self,
        agent_id: str = "progress_tracker",
        name: str = "NGX Progress Tracker",
        description: str = "Especialista en seguimiento, análisis y visualización de progreso",
        mcp_toolkit: Optional[Any] = None,
        a2a_server_url: Optional[str] = None,
        state_manager: Optional[Any] = None,
        model: str = "gemini-1.5-flash",
        instruction: str = "Eres un analista de datos especializado en seguimiento de progreso y visualización.",
        **kwargs
    ):
        agent_id_val = agent_id
        name_val = name
        description_val = description
        
        # Capacidades para BaseAgent y A2A
        capabilities_val = [
            "analyze_progress",
            "visualize_progress",
            "compare_progress",
            "data_analysis",
            "trend_identification"
        ]
        
        # Herramientas para Google ADK
        google_adk_tools_val = [
            # Aquí irían las herramientas específicas de Google ADK si se necesitan
        ]
        
        # Skills para A2A
        a2a_skills_val = [
            {
                "name": "analyze_progress",
                "description": "Analiza los datos de progreso del usuario e identifica tendencias.",
                "input_schema": { "type": "object", "properties": { "input_text": {"type": "string"}, "user_id": {"type": "string"}, "time_period": {"type": "string"}, "metrics": {"type": "array"} }, "required": ["user_id", "time_period"] },
                "output_schema": { "type": "object", "properties": { "analysis": {"type": "object"} } }
            },
            {
                "name": "visualize_progress",
                "description": "Genera una visualización (gráfico) del progreso del usuario.",
                "input_schema": { "type": "object", "properties": { "input_text": {"type": "string"}, "user_id": {"type": "string"}, "metric": {"type": "string"}, "time_period": {"type": "string"}, "chart_type": {"type": "string"} }, "required": ["user_id", "metric", "time_period"] },
                "output_schema": { "type": "object", "properties": { "visualization": {"type": "object"} } }
            },
            {
                "name": "compare_progress",
                "description": "Compara el progreso entre dos periodos de tiempo.",
                "input_schema": { "type": "object", "properties": { "input_text": {"type": "string"}, "user_id": {"type": "string"}, "period1": {"type": "string"}, "period2": {"type": "string"}, "metrics": {"type": "array"} }, "required": ["user_id", "period1", "period2"] },
                "output_schema": { "type": "object", "properties": { "comparison": {"type": "object"} } }
            }
        ]
        
        # Instanciar MCPToolkit si no se provee
        actual_adk_toolkit = mcp_toolkit if mcp_toolkit is not None else MCPToolkit()
        
        # Asegurar que state_manager se pasa a través de kwargs si está presente
        if state_manager:
            kwargs['state_manager'] = state_manager
            
        super().__init__(
            agent_id=agent_id_val,
            name=name_val,
            description=description_val,
            capabilities=capabilities_val,
            model=model,
            instruction=instruction,
            google_adk_tools=google_adk_tools_val,
            a2a_skills=a2a_skills_val,
            adk_toolkit=actual_adk_toolkit,
            a2a_server_url=a2a_server_url,
            endpoint=f"/agents/{agent_id_val}",
            **kwargs
        )
        
        # Inicializar clientes específicos del agente
        self.gemini_client = GeminiClient(model_name=self.model)
        self.supabase_client = SupabaseClient()
        
        # Directorio para guardar gráficos temporales
        self.tmp_dir = os.path.join(os.getcwd(), "tmp_progress")
        # Crear directorio si no existe
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir, exist_ok=True)
        
        # Definir skills
        self.skills = {
            "analyze_progress": Skill(
                name="analyze_progress",
                description="Analiza los datos de progreso del usuario e identifica tendencias.",
                method=self._skill_analyze_progress,
                input_schema=AnalyzeProgressInput,
                output_schema=AnalyzeProgressOutput,
            ),
            "visualize_progress": Skill(
                name="visualize_progress",
                description="Genera una visualización (gráfico) del progreso del usuario.",
                method=self._skill_visualize_progress,
                input_schema=VisualizeProgressInput,
                output_schema=VisualizeProgressOutput,
            ),
            "compare_progress": Skill(
                name="compare_progress",
                description="Compara el progreso entre dos periodos de tiempo.",
                method=self._skill_compare_progress,
                input_schema=CompareProgressInput,
                output_schema=CompareProgressOutput,
            ),
        }
        
        logger.info(f"Agente {self.name} inicializado con {len(self.skills)} skills: {list(self.skills.keys())}")
        
        # Configurar sistema de instrucciones para Gemini
        self.system_instructions = """Eres un analista de datos especializado en seguimiento de progreso y visualización. 
        Tu objetivo es proporcionar análisis claros, concisos y útiles sobre el progreso del usuario en diversas métricas.
        Identifica tendencias, patrones y proporciona recomendaciones accionables basadas en datos."""
        
        # Inicializar AI Platform si es necesario
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform (Vertex AI SDK) inicializado correctamente para ProgressTracker.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform para ProgressTracker: {e}", exc_info=True)
        os.makedirs(self.tmp_dir, exist_ok=True)

        # Instrucciones del sistema para el agente (se pueden pasar a super() si se quiere)
        self.system_instructions = """
        Eres NGX Progress Tracker, experto en seguimiento, análisis y visualización de progreso.
        Tu objetivo es ayudar a los usuarios a entender sus datos, identificar tendencias y ajustar estrategias.
        Proporciona análisis basados en datos y visualizaciones claras para facilitar la comprensión.
        Identifica patrones y sugiere ajustes para optimizar resultados.
        """
        
        logger.info(f"ProgressTracker inicializado con {len(capabilities)} capacidades según protocolo ADK/A2A")

    # --- Métodos de Skill --- 
    # Estos métodos contienen la lógica que antes estaba en execute_task
    
    async def _skill_analyze_progress(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """Skill para analizar el progreso del usuario."""
        logger.info(f"Skill '{self._skill_analyze_progress.__name__}' llamada con entrada: '{input_text[:50]}...'")
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id")
        time_period = kwargs.get("time_period", "last_month")
        metrics = kwargs.get("metrics")
        
        try:
            # Obtener client_profile del contexto si es necesario
            full_context = await self._get_context(user_id, session_id)
            client_profile_from_context = full_context.get("client_profile", {})
            
            # 1. Obtener datos (simulado por ahora, idealmente de Supabase o StateManager)
            user_data = await self._get_user_data(user_id, time_period, metrics)
            if not user_data:
                return create_result(
                    status="error", 
                    error_message="No se encontraron datos para el análisis."
                )

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
            if hasattr(self, 'update_state'):
                self.update_state(f"analysis_{analysis_id}", analysis_result)

            # 5. Crear artefacto
            artifact = self.create_artifact(
                label="ProgressAnalysis", 
                content_type="application/json",
                data=analysis_result
            )

            logger.info(f"Análisis completado para user {user_id}")
            return create_result(
                status="success", 
                response_data={"analysis_id": analysis_id, "result": analysis_result},
                artifacts=[artifact]
            )

        except Exception as e:
            logger.error(f"Error en skill '{self._skill_analyze_progress.__name__}': {e}", exc_info=True)
            return create_result(status="error", error_message=str(e))

    async def _skill_visualize_progress(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """Skill para visualizar el progreso del usuario."""
        logger.info(f"Skill '{self._skill_visualize_progress.__name__}' llamada con entrada: '{input_text[:50]}...'")
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id")
        metric = kwargs.get("metric", "weight")
        time_period = kwargs.get("time_period", "last_month")
        chart_type = kwargs.get("chart_type", "line")
        
        try:
            # Obtener client_profile del contexto si es necesario
            full_context = await self._get_context(user_id, session_id)
            client_profile_from_context = full_context.get("client_profile", {})
            
            # 1. Obtener datos (simulado)
            user_data = await self._get_user_data(user_id, time_period, [metric])
            if not user_data or metric not in user_data or not user_data[metric]:
                return create_result(
                    status="error", 
                    error_message=f"No se encontraron datos para la métrica '{metric}'."
                )

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

            # 5. Crear artefacto
            artifact = self.create_artifact(
                label="ProgressVisualization", 
                content_type="image/png",
                data={"url": viz_url, "metric": metric, "time_period": time_period}
            )

            logger.info(f"Visualización generada: {viz_filepath}")
            return create_result(
                status="success", 
                response_data={"visualization_url": viz_url, "filepath": viz_filepath},
                artifacts=[artifact]
            )

        except Exception as e:
            logger.error(f"Error en skill '{self._skill_visualize_progress.__name__}': {e}", exc_info=True)
            # Limpiar figura si hubo error
            plt.close()
            return create_result(status="error", error_message=str(e))

    async def _skill_compare_progress(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """Skill para comparar el progreso entre dos periodos."""
        logger.info(f"Skill '{self._skill_compare_progress.__name__}' llamada con entrada: '{input_text[:50]}...'")
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id")
        period1 = kwargs.get("period1", "last_month")
        period2 = kwargs.get("period2", "previous_month")
        metrics = kwargs.get("metrics", ["weight", "performance"])
        
        try:
            # Obtener client_profile del contexto si es necesario
            full_context = await self._get_context(user_id, session_id)
            client_profile_from_context = full_context.get("client_profile", {})
            
            # 1. Obtener datos para ambos periodos (simulado)
            data_p1 = await self._get_user_data(user_id, period1, metrics)
            data_p2 = await self._get_user_data(user_id, period2, metrics)

            if not data_p1 or not data_p2:
                return create_result(
                    status="error", 
                    error_message="Datos insuficientes para comparación."
                )

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

            # 4. Crear artefacto
            artifact = self.create_artifact(
                label="ProgressComparison", 
                content_type="application/json",
                data=comparison_result
            )

            logger.info(f"Comparación completada para user {user_id}")
            return create_result(
                status="success", 
                response_data={"result": comparison_result},
                artifacts=[artifact]
            )
            
        except Exception as e:
            logger.error(f"Error en skill '{self._skill_compare_progress.__name__}': {e}", exc_info=True)
            return create_result(status="error", error_message=str(e))

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


    # Método auxiliar para manejar errores
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Maneja errores y devuelve un resultado formateado.
        """
        # Registrar el error
        logger.error(f"Error en ProgressTracker: {error}", exc_info=True)
        
        # Crear un mensaje de error amigable
        error_message = str(error)
        if isinstance(error, ValueError):
            friendly_message = f"Error de valor: {error_message}"
        elif isinstance(error, TypeError):
            friendly_message = f"Error de tipo: {error_message}"
        elif isinstance(error, KeyError):
            friendly_message = f"Error de clave: {error_message}"
        else:
            friendly_message = f"Error inesperado: {error_message}"
            
        # Devolver un resultado formateado con el error
        return create_result(status="error", error_message=friendly_message)
        
    def _get_completion_message(self, skill_name: str, response_data: Dict[str, Any]) -> Optional[str]:
        """
        Genera un mensaje de finalización personalizado para la skill, si es necesario.
        """
        # Implementación específica si se necesita un mensaje de finalización personalizado
        # Por ahora, devolvemos None para usar el mensaje por defecto
        return None

    # --- Métodos de Contexto (Revisar si son necesarios o usar StateManager directamente) ---

    async def _get_context(
        self, user_id: Optional[str], session_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación para un usuario y sesión específicos.
        
        Este método intenta primero obtener el contexto del StateManager para persistencia.
        Si no está disponible, usa el almacenamiento en memoria como fallback.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            
        Returns:
            Dict[str, Any]: Contexto de la conversación
        """
        context_key = f"context_{user_id}_{session_id}" if user_id and session_id else f"context_default_{uuid.uuid4().hex[:6]}"
        
        # Intentar cargar desde StateManager (si está disponible)
        if self.state_manager and user_id and session_id:
            try:
                state_data = await self.state_manager.load_state(context_key)
                if state_data and isinstance(state_data, dict):
                    logger.debug(f"Contexto cargado desde StateManager para key={context_key}")
                    return state_data
            except Exception as e:
                logger.warning(f"Error al cargar contexto desde StateManager: {e}")

        # Fallback o si no se usa StateManager: usar estado interno del agente
        context = self.get_state(context_key, None) 
        if context is None:
            context = {"history": []}
            self.update_state(context_key, context)
            logger.debug(f"Nuevo contexto inicializado en memoria para key={context_key}")

        return context

    async def _update_context(self, user_id: Optional[str], session_id: Optional[str], msg: str, resp: str):
        """
        Actualiza el contexto de la conversación con un nuevo mensaje y respuesta.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            msg: Mensaje del usuario
            resp: Respuesta del bot
        """
        context_key = f"context_{user_id}_{session_id}" if user_id and session_id else f"context_default_{uuid.uuid4().hex[:6]}"
        context = await self._get_context(user_id, session_id) # Obtener contexto (cargará o inicializará)
        
        if "history" not in context or not isinstance(context["history"], list):
            context["history"] = []
            
        context["history"].append({"user": msg, "bot": resp, "timestamp": time.time()})
        
        # Limitar historial
        context["history"] = context["history"][-10:] # Mantener últimas 10

        # Guardar en StateManager o estado interno
        if self.state_manager and user_id and session_id:
            try:
                await self.state_manager.save_state(context, context_key)
                logger.debug(f"Contexto actualizado en StateManager para key={context_key}")
            except Exception as e:
                logger.warning(f"Error al guardar contexto en StateManager: {e}")
        else:
             self.update_state(context_key, context)
             logger.debug(f"Contexto actualizado en memoria para key={context_key}")

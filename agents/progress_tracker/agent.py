import logging
import uuid
import time
from typing import Dict, Any, Optional, List
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import datetime
from google.cloud import aiplatform

from adk.toolkit import Toolkit
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from tools.mcp_client import MCPClient  # Importar MCPClient
from agents.base.adk_agent import ADKAgent
from core.state_manager import StateManager
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)

class ProgressTracker(ADKAgent):
    """
    Agente especializado en seguimiento y análisis de progreso del usuario.
    """

    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None, state_manager: Optional[StateManager] = None, **kwargs):
        # Definir atributos del agente
        agent_id="progress_tracker"
        name="NGX Progress Tracker"
        description="Especialista en seguimiento, análisis y visualización de progreso"
        capabilities = [
            "progress_monitoring",
            "data_analysis",
            "trend_identification",
            "visualization",
            "goal_tracking"
        ]
        version="1.1.0"
        # Definir estructura de skills para Agent Card
        agent_skills_definition = [
            {
                "name": "analyze_progress",
                "description": "Analiza los datos de progreso del usuario e identifica tendencias.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "ID del usuario."},
                        "metrics": {"type": "array", "items": {"type": "string"}, "description": "Métricas a analizar (opcional)."},
                        "time_period": {"type": "string", "description": "Periodo de tiempo (ej. 'last_month', 'last_3_months')."}
                    },
                    "required": ["user_id", "time_period"]
                },
                "output_schema": {"type": "object", "description": "Análisis del progreso con insights."}
            },
            {
                "name": "visualize_progress",
                "description": "Genera una visualización (gráfico) del progreso del usuario.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "ID del usuario."},
                        "metric": {"type": "string", "description": "Métrica a visualizar (ej. 'weight', 'performance')."},
                        "time_period": {"type": "string", "description": "Periodo de tiempo."},
                        "chart_type": {"type": "string", "description": "Tipo de gráfico (ej. 'line', 'bar')."}
                    },
                    "required": ["user_id", "metric", "time_period", "chart_type"]
                },
                "output_schema": {"type": "object", "description": "URL o datos de la imagen de visualización."}
            },
            {
                "name": "compare_progress",
                "description": "Compara el progreso entre dos periodos de tiempo.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "ID del usuario."},
                        "period1": {"type": "string", "description": "Primer periodo (ej. 'last_month')."},
                        "period2": {"type": "string", "description": "Segundo periodo (ej. 'previous_month')."},
                        "metrics": {"type": "array", "items": {"type": "string"}, "description": "Métricas a comparar."}
                    },
                    "required": ["user_id", "period1", "period2", "metrics"]
                },
                "output_schema": {"type": "object", "description": "Comparación del progreso con diferencias clave."}
            }
        ]
        
        # Llamar al constructor de ADKAgent
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities,
            toolkit=toolkit,
            version=version,
            a2a_server_url=a2a_server_url,
            state_manager=state_manager, # Pasar state_manager a la clase base
            skills=agent_skills_definition, # Pasar definición de skills
            **kwargs
        )
        
        # Inicialización de Clientes y Herramientas (si es necesario específicamente aquí)
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform: {e}", exc_info=True)
            # Considerar comportamiento si Vertex AI no está disponible
        
        self.gemini_client = GeminiClient(model_name="gemini-1.5-flash") # Asegurarse que el modelo es el correcto
        # self.supabase_client = SupabaseClient() # Descomentar si se usa activamente
        # self.mcp_toolkit = MCPToolkit() # Descomentar si se usa activamente
        # self.mcp_client = MCPClient() # Descomentar si se usa activamente
        
        # Directorio para guardar gráficos temporales
        self.tmp_dir = os.path.join(os.getcwd(), "tmp_progress")
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
    
    async def _skill_analyze_progress(self, user_id: str, time_period: str, metrics: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Skill para analizar el progreso del usuario."""
        logger.info(f"Executing skill: analyze_progress for user {user_id} over {time_period}")
        try:
            # 1. Obtener datos (simulado por ahora, idealmente de Supabase o StateManager)
            user_data = await self._get_user_data(user_id, time_period, metrics)
            if not user_data:
                return {"status": "error", "message": "No se encontraron datos para el análisis."}

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
            self.update_state(f"analysis_{analysis_id}", analysis_result) 

            logger.info(f"Análisis completado para user {user_id}")
            return {"status": "success", "analysis_id": analysis_id, "result": analysis_result}

        except Exception as e:
            logger.error(f"Error en skill analyze_progress: {e}", exc_info=True)
            return {"status": "error", "message": f"Error al analizar progreso: {e}"} 

    async def _skill_visualize_progress(self, user_id: str, metric: str, time_period: str, chart_type: str, **kwargs) -> Dict[str, Any]:
        """Skill para visualizar el progreso del usuario."""
        logger.info(f"Executing skill: visualize_progress for user {user_id}, metric {metric}, period {time_period}, type {chart_type}")
        try:
            # 1. Obtener datos (simulado)
            user_data = await self._get_user_data(user_id, time_period, [metric])
            if not user_data or metric not in user_data or not user_data[metric]:
                 return {"status": "error", "message": f"No se encontraron datos para la métrica '{metric}'."}

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
            return {"status": "success", "visualization_url": viz_url, "filepath": viz_filepath}

        except Exception as e:
            logger.error(f"Error en skill visualize_progress: {e}", exc_info=True)
            # Limpiar figura si hubo error
            plt.close()
            return {"status": "error", "message": f"Error al visualizar progreso: {e}"}

    async def _skill_compare_progress(self, user_id: str, period1: str, period2: str, metrics: List[str], **kwargs) -> Dict[str, Any]:
        """Skill para comparar el progreso entre dos periodos."""
        logger.info(f"Executing skill: compare_progress for user {user_id} between {period1} and {period2}")
        try:
            # 1. Obtener datos para ambos periodos (simulado)
            data_p1 = await self._get_user_data(user_id, period1, metrics)
            data_p2 = await self._get_user_data(user_id, period2, metrics)

            if not data_p1 or not data_p2:
                 return {"status": "error", "message": "Datos insuficientes para comparación."}

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
            return {"status": "success", "result": comparison_result}
            
        except Exception as e:
            logger.error(f"Error en skill compare_progress: {e}", exc_info=True)
            return {"status": "error", "message": f"Error al comparar progreso: {e}"}

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


    # --- Métodos de Ciclo de Vida y Registro --- 

    # Añadir método start
    async def start(self) -> None:
        """Inicia el agente, conectando y registrando skills."""
        await super().start() # Llama al start de ADKAgent
        if self._running:
            await self._register_skills()
            logger.info(f"Skills de {self.agent_id} registradas.")
        else:
             logger.warning(f"No se registraron skills para {self.agent_id} porque el inicio base falló.")

    # Añadir método _register_skills
    async def _register_skills(self) -> None:
        """Registra las skills específicas de este agente."""
        if not self.toolkit:
            logger.error(f"No se puede registrar skills para {self.agent_id}: Toolkit no inicializado.")
            return
            
        self.register_skill("analyze_progress", self._skill_analyze_progress)
        self.register_skill("visualize_progress", self._skill_visualize_progress)
        self.register_skill("compare_progress", self._skill_compare_progress)
        logger.info(f"Skills analyze, visualize, compare registradas para {self.agent_id}")

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

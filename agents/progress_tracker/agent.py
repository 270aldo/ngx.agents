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
from agents.base.a2a_agent import A2AAgent
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)

class ProgressTracker(A2AAgent):
    """
    Agente especializado en seguimiento y análisis de progreso del usuario.
    """

    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None, state_manager: Optional[StateManager] = None):
        # Definir capacidades según el protocolo A2A
        capabilities = [
            "progress_monitoring",
            "data_analysis",
            "trend_identification",
            "visualization",
            "goal_tracking"
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="progress_tracker",
            name="NGX Progress Tracker",
            description="Especialista en seguimiento, análisis y visualización de progreso",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.1.0",
            a2a_server_url=a2a_server_url
        )
        
        # Inicialización de Clientes y Herramientas
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
        
        # Inicializar el StateManager para persistencia
        self.state_manager = state_manager or StateManager()
        
        # Inicializar estado del agente
        self.update_state("visualizations", {})  # Almacenar visualizaciones generadas
        self.update_state("analyses", {})  # Almacenar análisis realizados
        self.update_state("conversation_contexts", {})  # Almacenar contextos de conversación
        
        # Directorio para guardar gráficos temporales
        self.tmp_dir = os.path.join(os.getcwd(), "tmp_progress")
        os.makedirs(self.tmp_dir, exist_ok=True)

        # Instrucciones del sistema para el agente
        self.system_instructions = """
        Eres NGX Progress Tracker, experto en seguimiento, análisis y visualización de progreso.
        Tu objetivo es ayudar a los usuarios a entender sus datos, identificar tendencias y ajustar estrategias.
        Proporciona análisis basados en datos y visualizaciones claras para facilitar la comprensión.
        Identifica patrones y sugiere ajustes para optimizar resultados.
        """
        
        # Crear y configurar la tarjeta del agente
        self.agent_card = self._create_agent_card()
        
        logger.info(f"ProgressTracker inicializado con {len(capabilities)} capacidades según protocolo A2A")

    async def run(self, input_text: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta el agente con un texto de entrada siguiendo el protocolo A2A oficial.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            **kwargs: Argumentos adicionales como context, parameters, etc.
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente según el protocolo A2A
        """
        try:
            start_time = time.time()
            logger.info(f"Ejecutando ProgressTracker con input: {input_text[:50]}...")
            
            # Obtener session_id de los kwargs o generar uno nuevo
            session_id = kwargs.get("session_id") or str(uuid.uuid4())
            logger.debug(f"ProgressTracker usando session_id: {session_id}")
            
            # Cargar el contexto de la conversación utilizando el método _get_context
            # Este método ya maneja la carga desde StateManager o memoria según corresponda
            context = await self._get_context(user_id, session_id)
            
            # Obtener datos de progreso
            progress_data = context.get("progress_data")
            if not progress_data and user_id:
                progress_data = self.supabase_client.get_user_progress_data(user_id)
            
            # Determinar tipo de consulta y capacidades a utilizar
            query_type = self._classify_query(input_text)
            capabilities_used = []
            
            if query_type == "visualization_request":
                result = await self._handle_visual_request(input_text, progress_data)
                capabilities_used.append("visualization")
                capabilities_used.append("progress_monitoring")
            elif query_type == "analysis_request":
                result = await self._handle_analysis_request(input_text, progress_data)
                capabilities_used.append("data_analysis")
                capabilities_used.append("trend_identification")
            else:
                result = await self._handle_general_request(input_text, progress_data)
                capabilities_used.append("goal_tracking")
            
            response = result.get("response", "")
            artifacts = result.get("artifacts", [])
            message = result.get("message")
            
            # Si no hay mensaje en el resultado, crear uno según el protocolo A2A
            if not message:
                message = self.create_message(
                    role="agent",
                    parts=[self.create_text_part(response)]
                )
                
                # Si hay artefactos, añadirlos al mensaje
                for artifact in artifacts:
                    message.parts.append(artifact)
            
            # Registrar la interacción si hay un usuario identificado
            if user_id:
                self.supabase_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=input_text,
                    response=response
                )
                
                # Interactuar con MCPClient
                await self.mcp_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=input_text,
                    response=response
                )
                logger.info("Interacción con MCPClient registrada")
                
                # Actualizar contexto y persistir en StateManager
                await self._update_context(user_id, session_id, input_text, response)
            
            # Calcular tiempo de ejecución
            execution_time = time.time() - start_time
            
            # Formatear respuesta según el protocolo A2A
            return {
                "status": "success",
                "response": response,
                "message": message,
                "confidence": 0.9,
                "execution_time": execution_time,
                "agent_id": self.agent_id,
                "artifacts": artifacts,
                "metadata": {
                    "capabilities_used": capabilities_used,
                    "user_id": user_id,
                    "session_id": session_id,
                    "query_type": query_type,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "protocol": "a2a",
                    "agent_version": "1.1.0"
                }
            }
            
        except Exception as e:
            logger.error(f"Error en ProgressTracker: {e}", exc_info=True)
            
            # Crear mensaje de error según el protocolo A2A
            error_message = self.create_message(
                role="agent",
                parts=[self.create_text_part("Lo siento, ha ocurrido un error al procesar tu solicitud de seguimiento de progreso.")]
            )
            
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de seguimiento de progreso.",
                "message": error_message,
                "error": str(e),
                "agent_id": self.agent_id,
                "metadata": {
                    "error_type": type(e).__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }

    async def process_message(self, from_agent: str, content: Dict[str, Any]) -> Any:
        msg = content.get("text", "")
        logger.info("ProgressTracker procesando mensaje de %s: %s", from_agent, msg)
        
        try:
            start_time = time.time()
            response_text = await self.gemini_client.generate_response(
                f"Mensaje de {from_agent}: {msg}\nResponde de forma concisa y relevante con información de progreso si es posible."
            )
            message = self.create_message(role="agent", parts=[self.create_text_part(response_text)])
            execution_time = time.time() - start_time
            
            return {
                "status": "success", 
                "response": response_text, 
                "message": message,
                "agent_id": self.agent_id,
                "execution_time": execution_time,
                "metadata": {
                    "from_agent": from_agent,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "protocol": "a2a",
                    "agent_version": "1.1.0"
                }
            }
            
        except Exception as e:
            logger.error(f"Error en process_message desde {from_agent}: {e}", exc_info=True)
            error_message = self.create_message(
                role="agent",
                parts=[self.create_text_part(f"Error procesando mensaje de {from_agent}.")]
            )
            return {
                "status": "error",
                "response": f"Error procesando mensaje de {from_agent}: {str(e)}",
                "message": error_message,
                "error": str(e),
                "agent_id": self.agent_id,
                "metadata": {
                    "from_agent": from_agent,
                    "error_type": type(e).__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }

    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """
        Ejecuta una tarea solicitada por el servidor A2A.
        
        Args:
            task: Tarea a ejecutar
            
        Returns:
            Any: Resultado de la tarea según el protocolo A2A
        """
        try:
            # Extraer información de la tarea
            user_input = task.get("input", "")
            context = task.get("context", {})
            user_id = context.get("user_id")
            session_id = context.get("session_id") or str(uuid.uuid4())
            
            # Cargar el contexto de la conversación
            conversation_context = await self._get_context(user_id, session_id)

            logger.info("ProgressTracker recibió consulta: %s", user_input)

            # Obtener datos de progreso
            progress_data = context.get("progress_data")
            if not progress_data and user_id:
                progress_data = self.supabase_client.get_user_progress_data(user_id)
            
            # Determinar tipo de consulta
            query_type = self._classify_query(user_input)
            capabilities_used = []
            
            # Procesar la consulta según su tipo
            if query_type == "visualization_request":
                result = await self._handle_visual_request(user_input, progress_data)
                capabilities_used.extend(["visualization", "progress_monitoring"])
            elif query_type == "analysis_request":
                result = await self._handle_analysis_request(user_input, progress_data)
                capabilities_used.extend(["data_analysis", "trend_identification"])
            else:
                result = await self._handle_general_request(user_input, progress_data)
                capabilities_used.append("goal_tracking")

            # Asegurar que el resultado tenga un mensaje A2A
            if "message" not in result:
                result["message"] = self.create_message(
                    role="agent",
                    parts=[self.create_text_part(result.get("response", ""))]
                )
                
                # Si hay artefactos, añadirlos al mensaje
                for artifact in result.get("artifacts", []):
                    if isinstance(artifact, dict) and "parts" in artifact:
                        result["message"].parts.extend(artifact["parts"])
                    else:
                        result["message"].parts.append(artifact)

            # Registrar interacción
            if user_id:
                self.supabase_client.log_interaction(user_id, self.agent_id, user_input, result["response"])
                
                # Interactuar con MCPClient
                await self.mcp_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=user_input,
                    response=result["response"]
                )
                logger.info("Interacción con MCPClient registrada")
                
                # Actualizar contexto y persistir en StateManager
                await self._update_context(user_id, session_id, user_input, result["response"])

            # Añadir metadatos A2A al resultado
            result["agent_id"] = self.agent_id
            result["metadata"] = {
                "capabilities_used": capabilities_used,
                "query_type": query_type,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "protocol": "a2a",
                "agent_version": "1.1.0"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error en execute_task: {e}", exc_info=True)
            
            # Crear mensaje de error según el protocolo A2A
            error_message = self.create_message(
                role="agent",
                parts=[self.create_text_part("Lo siento, ha ocurrido un error al procesar tu solicitud de seguimiento de progreso.")]
            )
            
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de seguimiento de progreso.",
                "message": error_message,
                "error": str(e),
                "agent_id": self.agent_id,
                "metadata": {
                    "error_type": type(e).__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }

    # ------------- Internal helpers -------------
    async def _get_context(self, user_id: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
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
        # Intentar cargar desde StateManager si hay user_id y session_id
        if user_id and session_id:
            try:
                state_data = await self.state_manager.load_state(user_id, session_id)
                if state_data and "context" in state_data:
                    logger.debug(f"Contexto cargado desde StateManager para session_id={session_id}")
                    return state_data["context"]
            except Exception as e:
                logger.warning(f"Error al cargar contexto desde StateManager: {e}")
        
        # Fallback: Obtener contextos almacenados en memoria
        contexts = self.get_state("conversation_contexts") or {}
        
        # Generar clave de contexto
        context_key = f"{user_id}_{session_id}" if user_id and session_id else "default"
        
        # Obtener o inicializar contexto
        if context_key not in contexts:
            contexts[context_key] = {"history": []}
            self.update_state("conversation_contexts", contexts)
        
        return contexts[context_key]
        
    async def _update_context(self, user_id: Optional[str], session_id: Optional[str], msg: str, resp: str) -> None:
        """
        Actualiza el contexto de la conversación con un nuevo mensaje y respuesta.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            msg: Mensaje del usuario
            resp: Respuesta del bot
        """
        # Obtener contexto actual
        context = await self._get_context(user_id, session_id)
        
        # Añadir nueva interacción al historial
        if "history" not in context:
            context["history"] = []
            
        context["history"].append({"user": msg, "bot": resp, "timestamp": time.time()})
        
        # Limitar el tamaño del historial (mantener últimas 10 interacciones)
        if len(context["history"]) > 10:
            context["history"] = context["history"][-10:]
            
        # Actualizar contexto en memoria
        contexts = self.get_state("conversation_contexts") or {}
        key = f"{user_id}_{session_id}" if user_id and session_id else "default"
        contexts[key] = context
        self.update_state("conversation_contexts", contexts)
        
        # Persistir en StateManager si hay user_id y session_id
        if user_id and session_id:
            try:
                # Guardar contexto en StateManager
                state_data = {"context": context}
                await self.state_manager.save_state(state_data, user_id, session_id)
                logger.debug(f"Contexto actualizado en StateManager para session_id={session_id}")
            except Exception as e:
                logger.warning(f"Error al guardar contexto en StateManager: {e}")
    
    def _classify_query(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["gráfico", "visual", "ver", "plot"]):
            return "visualization_request"
        if any(w in q for w in ["tendencia", "análisis", "patrón"]):
            return "analysis_request"
        return "general_request"

    async def _handle_visual_request(self, query: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Maneja solicitudes de visualización."""
        logger.info(f"Manejando solicitud de visualización: {query[:50]}...")
        # TODO: Usar mcp7_query para obtener datos específicos de Supabase para visualizar.
        # TODO: Integrar RAG para obtener guías sobre mejores prácticas de visualización según la filosofía NGX.
        try:
            # Lógica para generar visualización (simplificada)
            if not data:
                return {"response": "Lo siento, no tengo datos suficientes para generar una visualización.", "artifacts": []}
            # Por simplicidad, graficar peso si existe body_composition
            if "body_composition" not in data:
                return {"response": "No se encontraron datos de composición corporal para graficar.", "artifacts": []}
            dates = [datetime.datetime.strptime(d["date"], "%Y-%m-%d") for d in data["body_composition"]]
            weights = [d["weight"] for d in data["body_composition"]]
            fig_path = os.path.join(self.tmp_dir, f"weight_{uuid.uuid4().hex[:6]}.png")
            plt.figure()
            plt.plot(dates, weights, marker="o")
            plt.title("Evolución del peso")
            plt.xlabel("Fecha")
            plt.ylabel("Peso (kg)")
            plt.tight_layout()
            plt.savefig(fig_path)
            plt.close()
            artifact = self.create_artifact(artifact_id=f"plot_{uuid.uuid4().hex[:8]}", artifact_type="image/png", parts=[self.create_file_part(fig_path)])
            message = self.create_message(role="agent", parts=[self.create_text_part("Aquí tienes la visualización solicitada."), artifact])
            return {"response": "Visualización generada.", "artifacts": [artifact], "message": message}
        except Exception as e:
            logger.error(f"Error en _handle_visual_request: {e}", exc_info=True)
            return {"response": "Lo siento, ocurrió un error al generar la visualización.", "artifacts": [], "message": self.create_message(role="agent", parts=[self.create_text_part("Lo siento, ocurrió un error al generar la visualización.")])}

    async def _handle_analysis_request(self, query: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Maneja solicitudes de análisis."""
        logger.info(f"Manejando solicitud de análisis: {query[:50]}...")
        # TODO: Usar mcp7_query para obtener datos históricos/métricas desde Supabase.
        # TODO: Integrar RAG para obtener principios de análisis de NGX o benchmarks relevantes.
        # TODO: Usar mcp8_think para análisis complejos o multi-paso.
        try:
            # Lógica para realizar análisis con Gemini (simplificada)
            prompt = self.system_instructions + "\n\nDatos:" + json.dumps(data or {}, indent=2) + f"\n\nPregunta: {query}\nProporciona un análisis detallado basado en los datos."
            response = await self.gemini_client.generate_response(prompt, temperature=0.4)
            msg = self.create_message(role="agent", parts=[self.create_text_part(response)])
            return {"response": response, "artifacts": [], "message": msg}
        except Exception as e:
            logger.error(f"Error en _handle_analysis_request: {e}", exc_info=True)
            return {"response": "Lo siento, ocurrió un error al realizar el análisis.", "artifacts": [], "message": self.create_message(role="agent", parts=[self.create_text_part("Lo siento, ocurrió un error al realizar el análisis.")])}

    async def _handle_general_request(self, query: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Maneja solicitudes generales o no clasificadas."""
        logger.info(f"Manejando solicitud general: {query[:50]}...")
        # TODO: Integrar RAG para proporcionar contexto general relevante a la consulta.
        try:
            # Lógica para respuesta general con Gemini (simplificada)
            prompt = self.system_instructions + f"\n\nConsulta: {query}\nResponde de forma motivadora y basada en datos si están disponibles." + ("\n\nResumen de datos:\n" + json.dumps(data, indent=2) if data else "")
            response = await self.gemini_client.generate_response(prompt)
            msg = self.create_message(role="agent", parts=[self.create_text_part(response)])
            return {"response": response, "artifacts": [], "message": msg}
        except Exception as e:
            logger.error(f"Error en _handle_general_request: {e}", exc_info=True)
            return {"response": "Lo siento, ocurrió un error al procesar tu solicitud.", "artifacts": [], "message": self.create_message(role="agent", parts=[self.create_text_part("Lo siento, ocurrió un error al procesar tu solicitud.")])}

    def _create_agent_card(self) -> AgentCard:
        """
        Crea una tarjeta de agente estandarizada según el protocolo A2A.
        
        Returns:
            AgentCard: Tarjeta del agente estandarizada
        """
        # Crear ejemplos para la tarjeta del agente
        examples = [
            Example(
                input={"message": "Muéstrame un gráfico de mi progreso de peso"},
                output={"response": "Aquí tienes la visualización de tu progreso de peso a lo largo del tiempo. Puedes observar una tendencia descendente constante de 0.5kg por semana, lo que se alinea con tus objetivos de pérdida de peso saludable."}
            ),
            Example(
                input={"message": "¿Qué tendencias ves en mis datos de entrenamiento?"},
                output={"response": "Analizando tus datos de entrenamiento de los últimos 3 meses, he identificado las siguientes tendencias: 1) Aumento del 15% en tu capacidad de levantamiento de peso en ejercicios compuestos, 2) Mejora del 8% en resistencia cardiovascular, 3) Mayor consistencia en los entrenamientos de la mañana vs. los de la tarde. Recomiendo mantener la frecuencia actual y considerar aumentar la intensidad en tus sesiones de fuerza."}
            ),
            Example(
                input={"message": "¿Cómo va mi progreso hacia mi meta de reducción de grasa corporal?"},
                output={"response": "Tu progreso hacia la reducción de grasa corporal está en camino. Has reducido tu porcentaje de grasa corporal del 22% al 18% en 8 semanas, lo que representa un ritmo saludable de pérdida. Estás al 67% del camino hacia tu objetivo del 15%. Si mantienes este ritmo, alcanzarás tu objetivo en aproximadamente 4 semanas más."}
            ),
            Example(
                input={"message": "Compara mi rendimiento actual con el del mes pasado"},
                output={"response": "Comparando tu rendimiento actual con el del mes pasado: Fuerza: +7% en ejercicios principales. Resistencia: +12% en tiempo hasta el agotamiento. Recuperación: -15% en tiempo necesario entre series. Consistencia: +3 sesiones más que el mes anterior. En general, muestras una mejora significativa, especialmente en aspectos de resistencia y recuperación."}
            )
        ]
        
        # Crear la tarjeta del agente
        return AgentCard(
            title="NGX Progress Tracker",
            description="Especialista en seguimiento, análisis y visualización de progreso para optimizar resultados y ajustar estrategias.",
            instructions="Proporciona detalles sobre qué métricas quieres analizar, el período de tiempo que te interesa o solicita visualizaciones específicas de tu progreso.",
            examples=examples,
            capabilities=[
                "Monitoreo continuo de métricas clave de progreso",
                "Análisis cuantitativo de datos para extraer insights accionables",
                "Identificación de tendencias y patrones en tu rendimiento",
                "Generación de visualizaciones comprensibles de tu progreso",
                "Seguimiento de metas SMART y evaluación de hitos"
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "user_data": {"type": "object"},
                    "time_period": {"type": "string"}
                },
                "required": ["message"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                    "visualization": {"type": "object"},
                    "analysis": {"type": "object"},
                    "recommendations": {"type": "array"}
                },
                "required": ["response"]
            }
        )
        
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self._create_agent_card().to_dict()

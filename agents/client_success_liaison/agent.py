import logging
import uuid
import time
from typing import Dict, Any, Optional, List
import json
import os
import datetime

from adk.toolkit import Toolkit
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from agents.base.a2a_agent import A2AAgent
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager

logger = logging.getLogger(__name__)

class ClientSuccessLiaison(A2AAgent):
    """
    Agente especializado en comunidad y éxito del cliente.
    
    Este agente se encarga de facilitar la construcción de comunidad, mejorar la experiencia del usuario,
    proporcionar soporte personalizado, diseñar programas de fidelización, y gestionar la comunicación
    para maximizar la satisfacción y retención de los clientes.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None):
        # Definir capacidades y habilidades
        capabilities = [
            "community_building", 
            "user_experience", 
            "customer_support", 
            "retention_strategies", 
            "communication_management"
        ]
        
        skills = [
            {"name": "community_building", "description": "Construcción y gestión de comunidades de usuarios"},
            {"name": "user_experience", "description": "Optimización de la experiencia del usuario"},
            {"name": "customer_support", "description": "Soporte y resolución de problemas del cliente"},
            {"name": "retention_strategies", "description": "Estrategias para fidelización y retención"},
            {"name": "communication_management", "description": "Gestión de comunicaciones con usuarios"}
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "Necesito ideas para mejorar la retención de usuarios en mi aplicación"},
                "output": {"response": "He analizado estrategias efectivas de retención para aplicaciones similares..."}
            },
            {
                "input": {"message": "¿Cómo puedo construir una comunidad más activa alrededor de mi producto?"},
                "output": {"response": "Para construir una comunidad más activa, te recomiendo implementar estas estrategias..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="client_success_liaison",
            name="NGX Community & Client-Success Liaison",
            description="Especialista en comunidad, experiencia del usuario y éxito del cliente",
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
        self.update_state("community_calendars", {})  # Almacenar calendarios de comunidad generados
        self.update_state("customer_journey_maps", {})  # Almacenar mapas de customer journey
        self.update_state("support_requests", {})  # Almacenar solicitudes de soporte
        
        logger.info(f"ClientSuccessLiaison inicializado con {len(capabilities)} capacidades")
        
        # Definir el sistema de instrucciones para el agente
        self.system_instructions = """
        Eres NGX Community & Client-Success Liaison, un experto en comunidad, experiencia del usuario y éxito del cliente.
        
        Tu objetivo es facilitar la construcción de comunidad, mejorar la experiencia del usuario,
        proporcionar soporte personalizado, diseñar programas de fidelización, y gestionar la comunicación
        para maximizar la satisfacción y retención de los clientes en las siguientes áreas:
        
        1. Construcción de comunidad
           - Estrategias para crear sentido de pertenencia
           - Diseño de programas de embajadores
           - Facilitación de interacciones entre usuarios
           - Organización de eventos y desafíos comunitarios
           - Creación de contenido generado por la comunidad
        
        2. Experiencia del usuario
           - Análisis de journey maps de usuarios
           - Identificación de puntos de fricción
           - Diseño de experiencias personalizadas
           - Estrategias de onboarding efectivas
           - Optimización de interfaces y flujos
        
        3. Soporte al cliente
           - Resolución efectiva de problemas
           - Identificación de necesidades no expresadas
           - Anticipación a posibles dificultades
           - Seguimiento personalizado
           - Conversión de problemas en oportunidades
        
        4. Estrategias de retención
           - Programas de fidelización
           - Prevención de abandono (churn)
           - Reactivación de usuarios inactivos
           - Diseño de hitos y celebraciones
           - Incentivos y gamificación efectiva
        
        5. Gestión de comunicación
           - Diseño de estrategias multicanal
           - Personalización de mensajes
           - Timing y frecuencia óptimos
           - Tono y estilo adaptados al contexto
           - Medición de efectividad comunicativa
        
        Debes adaptar tu enfoque según el perfil del usuario, considerando:
        - Su nivel de experiencia con el producto/servicio
        - Sus objetivos y motivaciones
        - Sus patrones de uso previos
        - Sus preferencias de comunicación
        - Su contexto cultural y personal
        
        Cuando proporciones análisis y recomendaciones:
        - Utiliza un lenguaje empático y orientado al usuario
        - Ofrece ejemplos concretos y accionables
        - Balancea lo técnico con lo emocional
        - Prioriza la creación de valor a largo plazo
        - Considera tanto la experiencia individual como colectiva
        - Mantén el foco en resultados medibles
        
        Tu objetivo es ayudar a crear una comunidad vibrante, comprometida y en crecimiento,
        donde los usuarios se sientan valorados, apoyados y motivados a lo largo de su journey.
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
                    "calendars": [],
                    "journey_maps": [],
                    "support_requests": [],
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
                "calendars": [],
                "journey_maps": [],
                "support_requests": [],
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
        Implementación asíncrona del procesamiento del agente ClientSuccessLiaison.
        
        Sobrescribe el método de la clase base para proporcionar la implementación
        específica del agente especializado en comunidad y éxito del cliente.
        
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
            logger.info(f"Ejecutando ClientSuccessLiaison con input: {input_text[:50]}...")
            
            # Generar ID de sesión si no se proporciona
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Generando nuevo session_id: {session_id}")
            
            # Obtener el contexto de la conversación
            context = await self._get_context(user_id, session_id) if user_id else {}
            
            # Obtener perfil del usuario si está disponible
            user_profile = None
            if user_id:
                # Intentar obtener el perfil del usuario del contexto primero
                user_profile = context.get("user_profile", {})
                if not user_profile:
                    user_profile = self.supabase_client.get_user_profile(user_id)
                    if user_profile:
                        context["user_profile"] = user_profile
            
            # Clasificar el tipo de consulta
            query_type = self._classify_query(input_text)
            
            # Manejar la consulta según su tipo
            if query_type == "community_building":
                result = await self._handle_community_request(input_text, context)
                
                # Guardar en el estado si es un calendario de comunidad
                if "calendar" in result.get("artifacts", []) and user_id:
                    # Guardar en el estado interno del agente
                    calendars = self.get_state("community_calendars", {})
                    calendars[user_id] = calendars.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "calendar": result.get("calendar", {})
                    }]
                    self.update_state("community_calendars", calendars)
                    
                    # Guardar en el contexto de StateManager
                    context["calendars"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "calendar": result.get("calendar", {})
                    })
                    
            elif query_type == "user_experience":
                result = await self._handle_experience_request(input_text, context)
                
                # Guardar en el estado si es un mapa de customer journey
                if "journey_map" in result.get("artifacts", []) and user_id:
                    # Guardar en el estado interno del agente
                    journey_maps = self.get_state("customer_journey_maps", {})
                    journey_maps[user_id] = journey_maps.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "journey_map": result.get("journey_map", {})
                    }]
                    self.update_state("customer_journey_maps", journey_maps)
                    
                    # Guardar en el contexto de StateManager
                    context["journey_maps"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "journey_map": result.get("journey_map", {})
                    })
                    
            elif query_type == "customer_support":
                result = await self._handle_support_request(input_text, context)
                
                # Guardar en el estado si es una solicitud de soporte
                if user_id:
                    # Guardar en el estado interno del agente
                    support_requests = self.get_state("support_requests", {})
                    support_requests[user_id] = support_requests.get(user_id, []) + [{
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "response": result.get("response", "")
                    }]
                    self.update_state("support_requests", support_requests)
                    
                    # Guardar en el contexto de StateManager
                    context["support_requests"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "response": result.get("response", "")
                    })
                    
            elif query_type == "retention_strategies":
                result = await self._handle_retention_request(input_text, context)
            elif query_type == "communication_management":
                result = await self._handle_communication_request(input_text, context)
            else:
                result = await self._handle_general_request(input_text, context)
            
            # Extraer la respuesta y metadatos del resultado
            response = result.get("response", "")
            artifacts = result.get("artifacts", [])
            query_type = result.get("query_type", "general_request")
            confidence = result.get("confidence", 0.8)
            
            # Añadir la interacción al historial interno del agente
            self.add_to_history(input_text, response)
            
            # Añadir la interacción al historial de conversación en el contexto
            if user_id:
                context["conversation_history"].append({
                    "user": input_text,
                    "agent": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "query_type": query_type
                })
                
                # Actualizar el contexto en el StateManager
                await self._update_context(context, user_id, session_id)
            
            # Devolver respuesta final
            return {
                "status": "success",
                "response": response,
                "artifacts": artifacts,
                "agent_id": self.agent_id,
                "metadata": {
                    "query_type": query_type,
                    "user_id": user_id,
                    "session_id": session_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error en ClientSuccessLiaison: {e}", exc_info=True)
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud de éxito del cliente.",
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo A2A oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()
    
    async def execute_task(self, task: Dict[str, Any]) -> Any:
        """
        Ejecuta una tarea solicitada por el servidor A2A.
        
        Args:
            task: Tarea a ejecutar
            
        Returns:
            Any: Resultado de la tarea
        """
        user_input = task.get("input", "")
        context = task.get("context", {})
        user_id = context.get("user_id")
        
        logger.info(f"ClientSuccessLiaison procesando consulta: {user_input}")
        
        # Determinar el tipo de consulta
        query_type = self._classify_query(user_input)
        
        # Procesar según el tipo de consulta
        if query_type == "community_request":
            result = await self._handle_community_request(user_input, context)
        elif query_type == "experience_request":
            result = await self._handle_experience_request(user_input, context)
        elif query_type == "support_request":
            result = await self._handle_support_request(user_input, context)
        elif query_type == "retention_request":
            result = await self._handle_retention_request(user_input, context)
        elif query_type == "communication_request":
            result = await self._handle_communication_request(user_input, context)
        else:
            result = await self._handle_general_request(user_input, context)
        
        # Registrar la interacción en Supabase si hay ID de usuario
        if user_id:
            self.supabase_client.log_interaction(
                user_id=user_id,
                agent_id=self.agent_id,
                message=user_input,
                response=result.get("response", "")
            )
        
        return result
    
    async def process_message(self, from_agent: str, content: Dict[str, Any]) -> Any:
        """
        Procesa un mensaje recibido de otro agente.
        
        Args:
            from_agent: ID del agente que envió el mensaje
            content: Contenido del mensaje
            
        Returns:
            Any: Respuesta al mensaje
        """
        msg = content.get("text", "")
        logger.info(f"ClientSuccessLiaison procesando mensaje de {from_agent}: {msg}")
        
        # Generar respuesta utilizando Gemini
        prompt = f"""
        {self.system_instructions}
        
        Has recibido un mensaje del agente {from_agent}:
        "{msg}"
        
        Responde con información relevante sobre comunidad, experiencia del usuario,
        o estrategias de éxito del cliente relacionadas con este mensaje.
        """
        
        response = await self.gemini_client.generate_response(prompt, temperature=0.3)
        
        # Crear mensaje de respuesta
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "status": "success",
            "response": response,
            "message": message
        }
    
    def _classify_query(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta
        """
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["comunidad", "grupo", "miembros", "pertenencia", "embajador"]):
            return "community_request"
        elif any(word in query_lower for word in ["experiencia", "usabilidad", "interfaz", "onboarding", "journey"]):
            return "experience_request"
        elif any(word in query_lower for word in ["soporte", "ayuda", "problema", "dificultad", "resolver"]):
            return "support_request"
        elif any(word in query_lower for word in ["retención", "fidelización", "abandono", "reactivar", "gamificación"]):
            return "retention_request"
        elif any(word in query_lower for word in ["comunicación", "mensaje", "email", "notificación", "contacto"]):
            return "communication_request"
        else:
            return "general_request"
    
    async def _handle_community_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con construcción de comunidad.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Obtener información del usuario si está disponible
        user_data = context.get("user_data", {})
        user_type = user_data.get("type", "regular")
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita información sobre comunidad con la siguiente consulta:
        "{query}"
        
        Tipo de usuario: {user_type}
        
        Proporciona una respuesta detallada sobre estrategias de construcción de comunidad,
        incluyendo recomendaciones específicas, mejores prácticas, ejemplos de éxito,
        y pasos concretos para implementación.
        
        Estructura tu respuesta en secciones:
        1. Análisis de la necesidad de comunidad
        2. Estrategias recomendadas
        3. Pasos de implementación
        4. Métricas de éxito
        5. Recursos adicionales
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear plan de comunidad como artefacto
        community_plan = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "community_request",
            "query": query,
            "user_type": user_type,
            "plan_summary": "Plan de comunidad generado",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"community_plan_{uuid.uuid4().hex[:8]}",
            artifact_type="community_plan",
            parts=[self.create_data_part(community_plan)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "community_request",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_experience_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con experiencia del usuario.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita información sobre experiencia del usuario con la siguiente consulta:
        "{query}"
        
        Proporciona una respuesta detallada sobre optimización de la experiencia del usuario,
        incluyendo análisis de journeys, identificación de puntos de fricción, estrategias de onboarding,
        personalización de experiencias y mejores prácticas de UX/UI.
        
        Estructura tu respuesta en secciones:
        1. Análisis de la experiencia actual
        2. Puntos de mejora identificados
        3. Recomendaciones específicas
        4. Casos de éxito relevantes
        5. Métricas para evaluar mejoras
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear análisis de experiencia como artefacto
        experience_analysis = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "experience_request",
            "query": query,
            "analysis_summary": "Análisis de experiencia del usuario generado",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"experience_analysis_{uuid.uuid4().hex[:8]}",
            artifact_type="experience_analysis",
            parts=[self.create_data_part(experience_analysis)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "experience_request",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_support_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con soporte al cliente.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Obtener información del problema si está disponible
        problem_info = None
        if "problem_details" in context:
            problem_info = context["problem_details"]
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita soporte con la siguiente consulta:
        "{query}"
        
        {"Detalles del problema:\n" + json.dumps(problem_info, indent=2) if problem_info else "No se proporcionaron detalles específicos del problema."}
        
        Proporciona una respuesta de soporte detallada, empática y orientada a soluciones,
        abordando la consulta específica del usuario y ofreciendo pasos claros para resolver el problema.
        
        Estructura tu respuesta en secciones:
        1. Reconocimiento del problema
        2. Análisis de posibles causas
        3. Soluciones paso a paso
        4. Prevención de problemas similares
        5. Seguimiento recomendado
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear ticket de soporte como artefacto
        support_ticket = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "support_request",
            "query": query,
            "problem_info": problem_info,
            "ticket_summary": "Ticket de soporte generado",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"support_ticket_{uuid.uuid4().hex[:8]}",
            artifact_type="support_ticket",
            parts=[self.create_data_part(support_ticket)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "support_request",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_retention_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con estrategias de retención.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Obtener datos de retención si están disponibles
        retention_data = context.get("retention_data", {})
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita información sobre retención con la siguiente consulta:
        "{query}"
        
        {"Datos de retención:\n" + json.dumps(retention_data, indent=2) if retention_data else "No se proporcionaron datos específicos de retención."}
        
        Proporciona una respuesta detallada sobre estrategias de retención y fidelización,
        incluyendo programas de lealtad, prevención de abandono, reactivación de usuarios,
        gamificación efectiva y creación de hábitos positivos.
        
        Estructura tu respuesta en secciones:
        1. Análisis de la situación actual
        2. Estrategias recomendadas
        3. Plan de implementación
        4. Métricas de seguimiento
        5. Casos de éxito relevantes
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear plan de retención como artefacto
        retention_plan = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "retention_request",
            "query": query,
            "plan_summary": "Plan de retención generado",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"retention_plan_{uuid.uuid4().hex[:8]}",
            artifact_type="retention_plan",
            parts=[self.create_data_part(retention_plan)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "retention_request",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_communication_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con gestión de comunicación.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Obtener preferencias de comunicación si están disponibles
        communication_prefs = context.get("communication_preferences", {})
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita información sobre comunicación con la siguiente consulta:
        "{query}"
        
        {"Preferencias de comunicación:\n" + json.dumps(communication_prefs, indent=2) if communication_prefs else "No se proporcionaron preferencias específicas de comunicación."}
        
        Proporciona una respuesta detallada sobre estrategias de comunicación efectivas,
        incluyendo diseño multicanal, personalización de mensajes, timing óptimo,
        tono y estilo adaptados, y medición de efectividad.
        
        Estructura tu respuesta en secciones:
        1. Análisis de las necesidades de comunicación
        2. Estrategia de comunicación recomendada
        3. Plantillas y ejemplos de mensajes
        4. Calendario de comunicación sugerido
        5. Métricas para evaluar efectividad
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear plan de comunicación como artefacto
        communication_plan = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "communication_request",
            "query": query,
            "plan_summary": "Plan de comunicación generado",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"communication_plan_{uuid.uuid4().hex[:8]}",
            artifact_type="communication_plan",
            parts=[self.create_data_part(communication_plan)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "communication_request",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_general_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas generales relacionadas con éxito del cliente.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario ha realizado la siguiente consulta sobre comunidad o éxito del cliente:
        "{query}"
        
        Proporciona una respuesta detallada y útil, adaptada específicamente a esta consulta.
        Incluye información relevante, mejores prácticas, y recomendaciones concretas.
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.5)
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "general_request",
            "artifacts": [],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.8
        }
    
    async def _generate_community_calendar(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un calendario de eventos comunitarios.
        
        Args:
            context: Contexto para la generación del calendario
            
        Returns:
            Dict[str, Any]: Calendario de eventos
        """
        # Determinar el tipo de comunidad
        community_type = context.get("community_type", "fitness")
        time_frame = context.get("time_frame", "mensual")
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        Genera un calendario de eventos comunitarios para una comunidad de tipo: {community_type}.
        Período: {time_frame}
        
        El calendario debe incluir:
        1. Eventos educativos
        2. Desafíos grupales
        3. Sesiones de Q&A
        4. Celebraciones de hitos
        5. Actividades de networking
        
        Para cada evento, incluye:
        - Nombre del evento
        - Descripción breve
        - Duración recomendada
        - Objetivo principal
        - Recursos necesarios
        
        Formatea el calendario de manera estructurada y fácil de seguir.
        """
        
        # Generar calendario utilizando Gemini
        calendar_content = await self.gemini_client.generate_response(prompt, temperature=0.3)
        
        # Crear estructura del calendario
        community_calendar = {
            "timestamp": datetime.datetime.now().isoformat(),
            "community_type": community_type,
            "time_frame": time_frame,
            "calendar_type": "community_events",
            "content": calendar_content
        }
        
        return community_calendar
    
    async def _generate_customer_journey_map(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un mapa de customer journey personalizado.
        
        Args:
            context: Contexto para la generación del mapa
            
        Returns:
            Dict[str, Any]: Mapa de customer journey
        """
        # Determinar el tipo de usuario
        user_type = context.get("user_type", "principiante")
        journey_focus = context.get("journey_focus", "onboarding")
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        Genera un mapa detallado de customer journey para un usuario de tipo: {user_type}.
        Enfoque del journey: {journey_focus}
        
        El mapa debe incluir:
        1. Etapas principales del journey
        2. Touchpoints clave en cada etapa
        3. Emociones y necesidades del usuario
        4. Puntos de fricción potenciales
        5. Oportunidades de mejora
        6. Métricas relevantes para cada etapa
        
        Para cada etapa, proporciona detalles específicos y recomendaciones accionables.
        Formatea el mapa de manera estructurada y fácil de seguir.
        """
        
        # Generar mapa utilizando Gemini
        journey_map_content = await self.gemini_client.generate_response(prompt, temperature=0.3)
        
        # Crear estructura del mapa
        customer_journey_map = {
            "timestamp": datetime.datetime.now().isoformat(),
            "user_type": user_type,
            "journey_focus": journey_focus,
            "map_type": "customer_journey",
            "content": journey_map_content
        }
        
        return customer_journey_map

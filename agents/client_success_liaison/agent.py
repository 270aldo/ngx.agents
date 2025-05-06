import logging
import uuid
import time
from typing import Dict, Any, Optional, List
import json
import os
import datetime
from google.cloud import aiplatform

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
    
    def __init__(self, toolkit: Optional[Toolkit] = None, a2a_server_url: Optional[str] = None, state_manager: Optional[StateManager] = None):
        # Definir capacidades y habilidades
        capabilities = [
            "community_building", 
            "user_experience", 
            "customer_support", 
            "retention_strategies", 
            "communication_management",
            "information_retrieval", # Added capability for search
            "database_query" # Added capability for DB interaction
        ]
        
        # Definir skills siguiendo el formato A2A con mejores prácticas
        skills = [
            {
                "id": "client-success-community-building",
                "name": "Construcción de Comunidad",
                "description": "Diseña estrategias y programas para crear, desarrollar y mantener comunidades activas y comprometidas alrededor de productos y servicios",
                "tags": ["community", "engagement", "events", "forums", "user-groups"],
                "examples": [
                    {"input": "¿Cómo puedo construir una comunidad más activa alrededor de mi producto?", "output": "Podríamos implementar un programa de embajadores, organizar Q&A regulares con el equipo, y crear un foro dedicado..."},
                    {"input": "Estrategias para aumentar la participación en foros de usuarios", "output": "Gamificación (puntos/insignias), moderadores activos, contenido exclusivo, y destacar contribuciones valiosas son buenas estrategias."},
                    {"input": "Ideas para eventos comunitarios que generen engagement", "output": "Hackathons virtuales, webinars con expertos, concursos temáticos, sesiones de 'ask me anything' (AMA)."}
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "client-success-user-experience",
                "name": "Experiencia de Usuario",
                "description": "Analiza y optimiza la experiencia del usuario en diferentes puntos de contacto para maximizar la satisfacción y minimizar la fricción",
                "tags": ["ux", "customer-journey", "touchpoints", "onboarding", "user-flow"],
                "examples": [
                    {"input": "Cómo mejorar el proceso de onboarding para nuevos usuarios", "output": "Implementar un tutorial interactivo, ofrecer checklists de primeros pasos, y personalizar la bienvenida basado en el rol o caso de uso."},
                    {"input": "Identificar y resolver puntos de fricción en el customer journey", "output": "Mediante análisis de datos de uso, encuestas de satisfacción post-interacción, y mapas de experiencia del cliente."},
                    {"input": "Estrategias para optimizar la experiencia de usuario en una aplicación móvil", "output": "Simplificar navegación, mejorar tiempos de carga, asegurar consistencia visual, y optimizar para diferentes tamaños de pantalla."}
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "client-success-customer-support",
                "name": "Soporte al Cliente",
                "description": "Desarrolla sistemas y procesos para proporcionar soporte efectivo, resolver problemas y maximizar la satisfacción del cliente",
                "tags": ["support", "troubleshooting", "tickets", "resolution", "satisfaction"],
                "examples": [
                    {"input": "Cómo estructurar un sistema de tickets para soporte al cliente", "output": "Definir prioridades (urgente, normal, bajo), categorías (técnico, facturación, consulta), SLAs claros, y rutas de escalación."},
                    {"input": "Mejores prácticas para reducir el tiempo de respuesta en soporte", "output": "Usar respuestas predefinidas para consultas comunes, implementar un chatbot para triaje inicial, y asegurar suficiente personal en horas pico."},
                    {"input": "Estrategias para convertir interacciones de soporte en oportunidades de fidelización", "output": "Ofrecer soluciones proactivas, seguimiento post-resolución, y identificar oportunidades de up-selling/cross-selling relevantes."}
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "client-success-retention-strategies",
                "name": "Estrategias de Retención",
                "description": "Diseña e implementa programas y tácticas para maximizar la retención de clientes, reducir el churn y aumentar el lifetime value",
                "tags": ["retention", "churn", "loyalty", "ltv", "win-back"],
                "examples": [
                    {"input": "Necesito ideas para mejorar la retención de usuarios en mi aplicación", "output": "Programas de lealtad, contenido exclusivo para suscriptores, encuestas de salida para entender motivos de churn, y mejoras basadas en feedback."},
                    {"input": "Estrategias para reducir el churn en una suscripción mensual", "output": "Recordatorios de valor antes de la renovación, ofertas personalizadas, facilidad para pausar suscripción, y excelente soporte."},
                    {"input": "Cómo diseñar un programa de fidelización efectivo", "output": "Recompensas escalonadas, beneficios exclusivos, acceso anticipado a nuevas funciones, y reconocimiento público (si aplica)."}
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "client-success-communication-management",
                "name": "Gestión de Comunicaciones",
                "description": "Planifica y optimiza estrategias de comunicación con usuarios y clientes para maximizar el engagement y fortalecer relaciones",
                "tags": ["communication", "emails", "messaging", "notifications", "campaigns"],
                "examples": [
                    {"input": "Cómo estructurar una campaña de email para reactivar usuarios inactivos", "output": "Segmentar por nivel de inactividad, ofrecer incentivos para volver, destacar novedades, y usar un asunto atractivo."},
                    {"input": "Mejores prácticas para comunicaciones in-app", "output": "Ser contextuales, relevantes, breves, permitir al usuario controlar notificaciones, y evitar ser intrusivo."},
                    {"input": "Estrategias para personalizar comunicaciones masivas", "output": "Usar datos demográficos, historial de compras/uso, preferencias declaradas, y segmentación conductual."}
                ],
                "inputModes": ["text", "json"],
                "outputModes": ["text", "json", "markdown"]
            },
            {
                "id": "web_search",
                "name": "Web Search",
                "description": "Realiza una búsqueda en la web para encontrar información relevante sobre un tema específico.",
                "tags": ["search", "web", "information", "research"],
                "examples": [
                    {"input": "Busca las últimas tendencias en marketing de comunidades online", "output": "Resumen de artículos y estudios recientes sobre tendencias como..."},
                    {"input": "¿Cuáles son las mejores plataformas para foros de soporte?", "output": "Comparativa de plataformas populares como Discourse, Zendesk Community, Khoros, etc., con sus pros y contras."}
                ],
                "inputModes": ["text"],
                "outputModes": ["text", "markdown"]
            },
            { # New skill for fetching user profile via Supabase
                "id": "get_user_profile",
                "name": "Get User Profile",
                "description": "Recupera el perfil de un usuario específico desde la base de datos.",
                "tags": ["database", "user", "profile", "supabase", "query"],
                "examples": [
                    # This skill is typically invoked internally, not directly by user text
                    {"input": {"user_id": "user-123"}, "output": {"user_id": "user-123", "name": "Jane Doe", "email": "jane@example.com", "preferences": {...}}}
                ],
                "inputModes": ["json"], # Expects user_id
                "outputModes": ["json"] # Returns profile data
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="client_success_liaison",
            name="NGX Community & Client-Success Liaison",
            description="Especialista en construcción de comunidad, optimización de experiencia de usuario, soporte al cliente, estrategias de retención y gestión de comunicaciones. Diseña e implementa programas para maximizar la satisfacción, engagement y retención de clientes.",
            capabilities=capabilities,
            toolkit=toolkit,
            a2a_server_url=a2a_server_url or "https://client-success-api.ngx-agents.com/a2a", # Default URL example
            state_manager=state_manager,
            version="1.4.0", # Incremented version due to added skill
            skills=skills 
        )

        # Inicializar clientes después de llamar a super()
        self.gemini_client = GeminiClient(model_name="gemini-1.5-flash") # Modelo eficiente para estas tareas
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()

        # Instrucción del sistema para Gemini
        self.system_instructions = (
            "Eres un experto en éxito del cliente y construcción de comunidades. "
            "Tu objetivo es entender las necesidades del usuario y proporcionar estrategias, "
            "ideas y soluciones prácticas para mejorar la experiencia, el engagement y la retención de clientes."
        )
        logger.info(f"Agente {self.agent_id} v{self.version} inicializado.")
        
        # Inicialización de AI Platform
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}")
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform: {e}", exc_info=True)
        
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
                user_profile = context.get("user_profile")
                if not user_profile:
                    logger.info(f"Perfil no encontrado en contexto para {user_id}. Consultando Supabase vía MCP.")
                    try:
                        # Construir la consulta SQL (¡Asegúrate de sanitizar user_id si no confías en él!)
                        # Asumiendo tabla 'user_profiles' y columna 'user_id'
                        sql_query = f"SELECT * FROM user_profiles WHERE user_id = '{user_id}' LIMIT 1;"
                        # Invocar la herramienta MCP de Supabase
                        # Asumiendo que el ID de la herramienta es 'supabase/query'
                        query_result = await self.mcp_toolkit.invoke("supabase/query", sql=sql_query)
                        
                        # Procesar el resultado (esperamos una lista, tomamos el primer elemento si existe)
                        if query_result and isinstance(query_result, list) and len(query_result) > 0:
                            user_profile = query_result[0] 
                            logger.info(f"Perfil obtenido de Supabase para {user_id}.")
                            context["user_profile"] = user_profile # Guardar en contexto para futuro
                        else:
                             logger.warning(f"No se encontró perfil en Supabase para {user_id} o resultado inesperado: {query_result}")
                             user_profile = {} # Dejar como diccionario vacío si no se encuentra
                             context["user_profile"] = {} # Guardar vacío en contexto
                             
                    except Exception as e:
                         logger.error(f"Error al consultar perfil de usuario {user_id} vía MCP: {e}", exc_info=True)
                         user_profile = {} # Fallback a perfil vacío en caso de error
                         context["user_profile"] = {} # Guardar vacío en contexto
                         
                # else: perfil ya estaba en el contexto

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
            elif query_type == "web_search": # Added block for web search
                result = await self._handle_web_search(input_text, context)
                # Web search results are typically not saved to state unless specifically requested
            else: # Handles "general_request"
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
            Dict[str, Any]: Agent Card estandarizada que cumple con las especificaciones
            del protocolo A2A de Google, incluyendo metadatos enriquecidos, capacidades
            y habilidades detalladas.
        """
        return self._create_agent_card()
    
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
        elif query_type == "web_search": # Added block for web search
            result = await self._handle_web_search(user_input, context)
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
        search_keywords = ["busca", "search", "find", "investiga", "research", "encuentra", "lookup"]
        
        if any(query_lower.startswith(keyword + " ") for keyword in search_keywords):
             return "web_search"
        # Prioritize search detection before other keywords that might overlap

        elif any(word in query_lower for word in ["comunidad", "grupo", "miembros", "pertenencia", "embajador", "foro"]):
            return "community_building" # Aligned with _run_async_impl
        elif any(word in query_lower for word in ["experiencia", "usabilidad", "interfaz", "onboarding", "journey", "ux"]):
            return "user_experience" # Aligned
        elif any(word in query_lower for word in ["soporte", "ayuda", "problema", "dificultad", "resolver", "ticket"]):
            return "customer_support" # Aligned
        elif any(word in query_lower for word in ["retención", "fidelización", "abandono", "reactivar", "churn", "loyalty"]):
            return "retention_strategies" # Aligned
        elif any(word in query_lower for word in ["comunicación", "mensaje", "email", "notificación", "contacto", "campaña"]):
            return "communication_management" # Aligned
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
        # TODO: Integrar RAG para buscar estudios de caso o mejores prácticas de construcción de comunidades NGX.
        # TODO: Usar mcp7_query para obtener datos sobre la comunidad actual (miembros, actividad) desde Supabase.
        logger.info(f"Manejando solicitud de comunidad: {query}")
        
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
        # TODO: Integrar RAG para obtener heurísticas de UX o guías de diseño NGX.
        # TODO: Usar mcp7_query para obtener feedback de usuarios o datos de uso desde Supabase.
        logger.info(f"Manejando solicitud de experiencia: {query}")
        
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
        # TODO: Integrar RAG para buscar en la base de conocimientos de soporte NGX.
        # TODO: Usar mcp7_query para obtener historial de soporte del usuario desde Supabase.
        # TODO: Usar mcp4_create_issue (GitHub) si se necesita escalar a un ticket de desarrollo.
        logger.info(f"Manejando solicitud de soporte: {query}")
        
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
        # TODO: Integrar RAG para buscar estrategias de retención efectivas documentadas por NGX.
        # TODO: Usar mcp7_query para obtener datos de cohortes de usuarios o métricas de retención desde Supabase.
        logger.info(f"Manejando solicitud de retención: {query}")
        
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
        # TODO: Integrar RAG para obtener plantillas de comunicación o guías de tono de voz NGX.
        # TODO: Usar mcp7_query para obtener preferencias de comunicación del usuario desde Supabase.
        logger.info(f"Manejando solicitud de comunicación: {query}")
        
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
        # TODO: Integrar RAG para búsqueda general en documentación de NGX sobre éxito del cliente.
        # TODO: Usar mcp8_think para razonar sobre la mejor manera de abordar una consulta general.
        logger.info(f"Manejando solicitud general de éxito del cliente: {query}")
        
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
    
    async def _handle_web_search(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja las solicitudes de búsqueda web utilizando la herramienta MCP.
        """
        logger.info(f"Manejando solicitud de búsqueda web: {query[:50]}...")
        
        # Extraer la consulta real (eliminar la palabra clave inicial)
        search_keywords = ["busca", "search", "find", "investiga", "research", "encuentra", "lookup"]
        actual_query = query
        for keyword in search_keywords:
            if query.lower().startswith(keyword + " "):
                actual_query = query[len(keyword) + 1:].strip()
                break
                
        if not actual_query or actual_query == query: # Fallback si no se pudo extraer
            actual_query = query
            logger.warning("No se pudo extraer la consulta de búsqueda específica, usando el texto completo.")

        try:
            logger.info(f"Invocando herramienta 'search_web' con query: '{actual_query}'")
            # Asumiendo que 'search_web' es el ID correcto de la herramienta en MCPToolkit
            # y que devuelve una estructura como {'results': [{'title': ..., 'snippet': ..., 'url': ...}, ...]}
            search_results = await self.mcp_toolkit.invoke("search_web", query=actual_query)
            
            if search_results and search_results.get("results"): 
                formatted_response = f"Aquí tienes algunos resultados de la búsqueda web para '{actual_query}':\n\n"
                for i, result in enumerate(search_results["results"][:5]): # Limitar a 5 resultados
                    title = result.get('title', 'Sin título')
                    snippet = result.get('snippet', 'Sin descripción')
                    url = result.get('url', '')
                    formatted_response += f"{i+1}. **{title}**\n   {snippet}\n   [Fuente]({url})\n\n"
                if len(search_results["results"]) > 5:
                    formatted_response += "(Se encontraron más resultados)"
                response_content = formatted_response
            else:
                logger.warning(f"La herramienta 'search_web' no devolvió resultados para '{actual_query}'")
                response_content = f"No pude encontrar resultados en la web para '{actual_query}'."
                
        except Exception as e:
            logger.error(f"Error invocando la herramienta 'search_web': {e}", exc_info=True)
            response_content = f"Hubo un error al intentar buscar en la web: {e}"

        return {"response": response_content, "artifacts": []} # No hay artefactos específicos de la búsqueda generalmente

# Bloque de ejecución para pruebas locales
if __name__ == '__main__':
    # Ejemplo de ejecución local
    agent = ClientSuccessLiaison()
    user_input = "¿Cómo puedo mejorar la experiencia del usuario en mi aplicación móvil?"
    result = agent._run_async_impl(user_input)
    print(result)

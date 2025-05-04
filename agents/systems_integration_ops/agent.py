import logging
import uuid
import time
from typing import Dict, Any, Optional, List
import json
import os
import datetime
import asyncio

from adk.toolkit import Toolkit
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from agents.base.a2a_agent import A2AAgent
from core.agent_card import AgentCard, Example
from core.state_manager import StateManager

logger = logging.getLogger(__name__)

class SystemsIntegrationOps(A2AAgent):
    """
    Agente especializado en integración de sistemas y automatización.
    
    Este agente se encarga de facilitar la integración de diferentes sistemas,
    automatizar flujos de trabajo, gestionar conexiones con APIs externas,
    y optimizar la infraestructura tecnológica para mejorar la eficiencia operativa.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None):
        # Definir capacidades y habilidades
        capabilities = [
            "systems_integration", 
            "workflow_automation", 
            "api_management", 
            "infrastructure_optimization", 
            "data_pipeline_design"
        ]
        
        skills = [
            {"name": "systems_integration", "description": "Integración de sistemas heterogéneos y servicios digitales"},
            {"name": "workflow_automation", "description": "Automatización de procesos y flujos de trabajo"},
            {"name": "api_management", "description": "Gestión y optimización de conexiones con APIs"},
            {"name": "infrastructure_optimization", "description": "Optimización de infraestructura técnica"},
            {"name": "data_pipeline_design", "description": "Diseño de pipelines de datos eficientes"}
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "Necesito integrar mi aplicación de fitness con Apple Health"},
                "output": {"response": "He creado un plan de integración detallado para conectar tu aplicación con Apple Health..."}
            },
            {
                "input": {"message": "¿Cómo puedo automatizar el envío de notificaciones a mis usuarios?"},
                "output": {"response": "Para automatizar notificaciones, te recomiendo implementar este flujo de trabajo..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="systems_integration_ops",
            name="NGX Systems Integration & Ops",
            description="Especialista en integración de sistemas y automatización operativa",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.0.0",
            skills=skills
        )
        
        # Inicializar clientes y herramientas
        self.gemini_client = GeminiClient(model_name="gemini-2.0-flash")
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        self.state_manager = StateManager(self.supabase_client)
        
        # Crear Agent Card estandarizada
        self.agent_card = AgentCard.create_standard_card(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            skills=self.skills,
            version="1.0.0",
            examples=examples,
            metadata={
                "model": "gemini-pro",
                "creator": "NGX Team",
                "last_updated": time.strftime("%Y-%m-%d")
            }
        )
        
        # Definir el sistema de instrucciones para el agente
        self.system_instructions = """
        Eres NGX Systems Integration & Ops, un experto en integración de sistemas y automatización operativa.
        
        Tu objetivo es facilitar la integración fluida de diferentes sistemas, automatizar procesos,
        gestionar conexiones con APIs externas, y optimizar la infraestructura tecnológica
        para mejorar la eficiencia operativa en las siguientes áreas:
        
        1. Integración de sistemas
           - Integración de plataformas de fitness y salud
           - Conexión con dispositivos wearables y sensores
           - Integración con aplicaciones de terceros
           - Estrategias para la interoperabilidad de datos
           - Soluciones para la sincronización entre sistemas
        
        2. Automatización de flujos de trabajo
           - Automatización de procesos repetitivos
           - Creación de flujos de trabajo inteligentes
           - Diseño de reglas de negocio automatizadas
           - Implementación de gatillos y acciones condicionadas
           - Estrategias para reducir intervención manual
        
        3. Gestión de APIs
           - Recomendaciones de APIs relevantes para salud y fitness
           - Optimización de uso de APIs
           - Estrategias para manejo de cuotas y límites
           - Soluciones para la autenticación y autorización
           - Manejo de actualizaciones y cambios en APIs
        
        4. Optimización de infraestructura
           - Recomendaciones para arquitectura tecnológica
           - Estrategias de escalabilidad
           - Optimización de rendimiento
           - Gestión de recursos técnicos
           - Monitoreo y alertas
        
        5. Diseño de pipelines de datos
           - Arquitectura para procesamiento de datos de fitness
           - Estrategias ETL para datos de salud y biométricos
           - Optimización de flujos de datos
           - Soluciones para procesamiento en tiempo real
           - Estrategias para manejo de grandes volúmenes de datos
        
        Debes adaptar tu enfoque según el contexto específico, considerando:
        - El ecosistema tecnológico existente
        - Las necesidades específicas del usuario o negocio
        - Las restricciones técnicas y de recursos
        - El nivel de complejidad apropiado
        - Las mejores prácticas de la industria
        
        Cuando proporciones análisis y recomendaciones:
        - Utiliza un lenguaje claro y comprensible
        - Proporciona explicaciones técnicas precisas
        - Ofrece soluciones prácticas y viables
        - Considera el balance entre complejidad y beneficio
        - Prioriza la escalabilidad y el mantenimiento a largo plazo
        - Destaca tanto ventajas como posibles desafíos
        
        Tu objetivo es ayudar a crear un ecosistema tecnológico integrado, eficiente y escalable
        que permita una experiencia fluida para los usuarios y operaciones optimizadas para el negocio.
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
                    "integration_requests": [],
                    "automation_requests": [],
                    "api_requests": [],
                    "infrastructure_requests": [],
                    "data_pipeline_requests": [],
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
                "integration_requests": [],
                "automation_requests": [],
                "api_requests": [],
                "infrastructure_requests": [],
                "data_pipeline_requests": [],
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

    async def run(self, input_text: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta el agente con un texto de entrada siguiendo el protocolo ADK oficial.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            **kwargs: Argumentos adicionales como context, parameters, etc.
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente según el protocolo ADK
        """
        try:
            start_time = time.time()
            logger.info(f"Ejecutando SystemsIntegrationOps con input: {input_text[:50]}...")
            
            # Obtener session_id de los kwargs o generar uno nuevo
            session_id = kwargs.get("session_id", str(uuid.uuid4()))
            
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
            capabilities_used = []
            
            # Procesar la consulta según su tipo
            if query_type == "integration_request":
                result = await self._handle_integration_request(input_text, context)
                capabilities_used.append("systems_integration")
                
                # Guardar en el contexto
                if user_id:
                    context["integration_requests"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "response": result.get("response", "")[:100] + "..."
                    })
                
            elif query_type == "automation_request":
                result = await self._handle_automation_request(input_text, context)
                capabilities_used.append("workflow_automation")
                
                # Guardar en el contexto
                if user_id:
                    context["automation_requests"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "response": result.get("response", "")[:100] + "..."
                    })
                
            elif query_type == "api_request":
                result = await self._handle_api_request(input_text, context)
                capabilities_used.append("api_management")
                
                # Guardar en el contexto
                if user_id:
                    context["api_requests"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "response": result.get("response", "")[:100] + "..."
                    })
                
            elif query_type == "infrastructure_request":
                result = await self._handle_infrastructure_request(input_text, context)
                capabilities_used.append("infrastructure_optimization")
                
                # Guardar en el contexto
                if user_id:
                    context["infrastructure_requests"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "response": result.get("response", "")[:100] + "..."
                    })
                
            elif query_type == "data_pipeline_request":
                result = await self._handle_data_pipeline_request(input_text, context)
                capabilities_used.append("data_pipeline_design")
                
                # Guardar en el contexto
                if user_id:
                    context["data_pipeline_requests"].append({
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "query": input_text,
                        "response": result.get("response", "")[:100] + "..."
                    })
                
            else:
                result = await self._handle_general_request(input_text, context)
                capabilities_used.append("systems_integration")
                capabilities_used.append("workflow_automation")
            
            response = result.get("response", "")
            artifacts = result.get("artifacts", [])
            
            # Añadir la interacción al historial de conversación
            if user_id:
                context["conversation_history"].append({
                    "user": input_text,
                    "agent": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "query_type": query_type
                })
                
                # Actualizar el contexto en el StateManager
                await self._update_context(context, user_id, session_id)
            
            # Registrar la interacción si hay un usuario identificado
            if user_id:
                self.supabase_client.log_interaction(
                    user_id=user_id,
                    agent_id=self.agent_id,
                    message=input_text,
                    response=response
                )
            
            # Calcular tiempo de ejecución
            execution_time = time.time() - start_time
            
            # Formatear respuesta según el protocolo ADK
            return {
                "status": "success",
                "response": response,
                "confidence": 0.9,
                "execution_time": execution_time,
                "agent_id": self.agent_id,
                "artifacts": artifacts,
                "metadata": {
                    "capabilities_used": capabilities_used,
                    "user_id": user_id,
                    "query_type": query_type,
                    "session_id": session_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error en SystemsIntegrationOps: {e}")
            execution_time = time.time() - start_time if 'start_time' in locals() else 0.0
            
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud sobre integración de sistemas.",
                "error": str(e),
                "execution_time": execution_time,
                "confidence": 0.0,
                "agent_id": self.agent_id,
                "metadata": {
                    "error_type": type(e).__name__,
                    "user_id": user_id
                }
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
        
        logger.info(f"SystemsIntegrationOps procesando consulta: {user_input}")
        
        # Determinar el tipo de consulta
        query_type = self._classify_query(user_input)
        
        # Procesar según el tipo de consulta
        if query_type == "integration_request":
            result = await self._handle_integration_request(user_input, context)
        elif query_type == "automation_request":
            result = await self._handle_automation_request(user_input, context)
        elif query_type == "api_request":
            result = await self._handle_api_request(user_input, context)
        elif query_type == "infrastructure_request":
            result = await self._handle_infrastructure_request(user_input, context)
        elif query_type == "data_pipeline_request":
            result = await self._handle_data_pipeline_request(user_input, context)
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
        logger.info(f"SystemsIntegrationOps procesando mensaje de {from_agent}: {msg}")
        
        # Generar respuesta utilizando Gemini
        prompt = f"""
        {self.system_instructions}
        
        Has recibido un mensaje del agente {from_agent}:
        "{msg}"
        
        Responde con información relevante sobre integración de sistemas, automatización
        u optimización de infraestructura relacionada con este mensaje.
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
        
        if any(word in query_lower for word in ["integrar", "integración", "conectar", "sincronizar", "interoperabilidad"]):
            return "integration_request"
        elif any(word in query_lower for word in ["automatizar", "automatización", "workflow", "flujo de trabajo", "proceso"]):
            return "automation_request"
        elif any(word in query_lower for word in ["api", "endpoint", "webhook", "interfaz", "servicio web"]):
            return "api_request"
        elif any(word in query_lower for word in ["infraestructura", "arquitectura", "rendimiento", "escalabilidad", "servidor"]):
            return "infrastructure_request"
        elif any(word in query_lower for word in ["pipeline", "datos", "etl", "procesamiento", "flujo de datos"]):
            return "data_pipeline_request"
        else:
            return "general_request"
    
    async def _handle_integration_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con integración de sistemas.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Identificar qué sistemas se desean integrar
        systems = []
        query_lower = query.lower()
        
        # Sistemas comunes de fitness y salud
        if any(s in query_lower for s in ["garmin", "connect"]):
            systems.append("Garmin Connect")
        if any(s in query_lower for s in ["fitbit"]):
            systems.append("Fitbit")
        if any(s in query_lower for s in ["apple", "health", "healthkit"]):
            systems.append("Apple HealthKit")
        if any(s in query_lower for s in ["google", "fit", "googlefit"]):
            systems.append("Google Fit")
        if any(s in query_lower for s in ["strava"]):
            systems.append("Strava")
        if any(s in query_lower for s in ["oura", "ring"]):
            systems.append("Oura Ring")
        if any(s in query_lower for s in ["whoop"]):
            systems.append("WHOOP")
        if any(s in query_lower for s in ["myfitnesspal", "fitness pal"]):
            systems.append("MyFitnessPal")
        
        # Si no se identificaron sistemas específicos
        if not systems:
            systems = ["Sistema genérico de fitness/salud"]
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita información sobre integración de sistemas con la siguiente consulta:
        "{query}"
        
        Sistemas identificados: {', '.join(systems)}
        
        Proporciona una respuesta detallada sobre cómo integrar estos sistemas,
        incluyendo consideraciones técnicas, mejores prácticas, estrategias de implementación,
        posibles desafíos y soluciones recomendadas. 
        
        Estructura tu respuesta en secciones:
        1. Visión general de la integración
        2. Arquitectura recomendada
        3. APIs y protocolos relevantes
        4. Desafíos de implementación
        5. Próximos pasos recomendados
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear informe de integración como artefacto
        integration_report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "integration_request",
            "query": query,
            "systems": systems,
            "integration_summary": "Análisis de integración de sistemas completado",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"integration_report_{uuid.uuid4().hex[:8]}",
            artifact_type="integration_report",
            parts=[self.create_data_part(integration_report)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "integration_request",
            "systems": systems,
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_automation_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con automatización de flujos de trabajo.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita información sobre automatización con la siguiente consulta:
        "{query}"
        
        Proporciona una respuesta detallada sobre automatización de procesos relacionados,
        incluyendo herramientas recomendadas, estrategias de implementación, mejores prácticas,
        y consideraciones importantes.
        
        Estructura tu respuesta en secciones:
        1. Análisis del proceso a automatizar
        2. Estrategia de automatización recomendada
        3. Herramientas y tecnologías sugeridas
        4. Pasos de implementación
        5. Métricas de éxito y monitoreo
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear plan de automatización como artefacto
        automation_plan = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "automation_request",
            "query": query,
            "automation_summary": "Plan de automatización generado",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"automation_plan_{uuid.uuid4().hex[:8]}",
            artifact_type="automation_plan",
            parts=[self.create_data_part(automation_plan)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "automation_request",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_api_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con gestión de APIs.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Identificar posibles APIs mencionadas
        apis = []
        query_lower = query.lower()
        
        # APIs comunes de fitness y salud
        if any(a in query_lower for a in ["garmin", "connect"]):
            apis.append("Garmin Connect API")
        if any(a in query_lower for a in ["fitbit"]):
            apis.append("Fitbit API")
        if any(a in query_lower for a in ["apple", "health", "healthkit"]):
            apis.append("Apple HealthKit API")
        if any(a in query_lower for a in ["google", "fit", "googlefit"]):
            apis.append("Google Fit API")
        if any(a in query_lower for a in ["strava"]):
            apis.append("Strava API")
        if any(a in query_lower for a in ["oura", "ring"]):
            apis.append("Oura Ring API")
        if any(a in query_lower for a in ["whoop"]):
            apis.append("WHOOP API")
        
        # Si no se identificaron APIs específicas
        if not apis:
            apis = ["APIs genéricas de fitness/salud"]
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita información sobre APIs con la siguiente consulta:
        "{query}"
        
        APIs identificadas: {', '.join(apis)}
        
        Proporciona una respuesta detallada sobre estas APIs, incluyendo endpoints principales,
        requisitos de autenticación, límites de uso, mejores prácticas de implementación,
        y ejemplos de casos de uso comunes.
        
        Estructura tu respuesta en secciones:
        1. Visión general de las APIs
        2. Autenticación y autorización
        3. Endpoints y funcionalidades clave
        4. Consideraciones de implementación
        5. Recursos adicionales
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear guía de API como artefacto
        api_guide = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "api_request",
            "query": query,
            "apis": apis,
            "guide_summary": "Guía de APIs generada",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"api_guide_{uuid.uuid4().hex[:8]}",
            artifact_type="api_guide",
            parts=[self.create_data_part(api_guide)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "api_request",
            "apis": apis,
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_infrastructure_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con optimización de infraestructura.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita información sobre infraestructura con la siguiente consulta:
        "{query}"
        
        Proporciona una respuesta detallada sobre arquitectura e infraestructura tecnológica
        para aplicaciones de fitness y salud, incluyendo recomendaciones de arquitectura,
        estrategias de escalabilidad, balanceo de carga, almacenamiento de datos,
        seguridad y monitoreo.
        
        Estructura tu respuesta en secciones:
        1. Análisis de requisitos de infraestructura
        2. Arquitectura recomendada
        3. Componentes clave y tecnologías
        4. Estrategias de escalabilidad y rendimiento
        5. Consideraciones de seguridad
        6. Monitoreo y mantenimiento
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear informe de infraestructura como artefacto
        infrastructure_report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "infrastructure_request",
            "query": query,
            "report_summary": "Informe de infraestructura generado",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"infrastructure_report_{uuid.uuid4().hex[:8]}",
            artifact_type="infrastructure_report",
            parts=[self.create_data_part(infrastructure_report)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "infrastructure_request",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_data_pipeline_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con diseño de pipelines de datos.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita información sobre pipelines de datos con la siguiente consulta:
        "{query}"
        
        Proporciona una respuesta detallada sobre diseño de pipelines de datos para aplicaciones
        de fitness y salud, incluyendo arquitectura de procesamiento, estrategias ETL,
        opciones de almacenamiento, consideraciones de latencia, integración de fuentes de datos,
        y análisis de datos.
        
        Estructura tu respuesta en secciones:
        1. Análisis de requisitos del pipeline
        2. Arquitectura recomendada
        3. Estrategias de procesamiento (batch vs. streaming)
        4. Almacenamiento y acceso a datos
        5. Calidad y gobierno de datos
        6. Monitoreo y mantenimiento
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear diseño de pipeline como artefacto
        pipeline_design = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "data_pipeline_request",
            "query": query,
            "design_summary": "Diseño de pipeline de datos generado",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"pipeline_design_{uuid.uuid4().hex[:8]}",
            artifact_type="pipeline_design",
            parts=[self.create_data_part(pipeline_design)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "data_pipeline_request",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_general_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas generales relacionadas con integración de sistemas y automatización.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario ha realizado la siguiente consulta sobre integración de sistemas o automatización:
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
    
    async def _generate_integration_diagram(self, systems: List[str]) -> Dict[str, Any]:
        """
        Genera un diagrama conceptual de integración de sistemas.
        
        Args:
            systems: Lista de sistemas a integrar
            
        Returns:
            Dict[str, Any]: Descripción del diagrama
        """
        # En una implementación real, esto podría generar un diagrama visual
        # Por ahora, generamos una descripción textual
        
        prompt = f"""
        {self.system_instructions}
        
        Genera una descripción detallada de un diagrama de arquitectura para la integración de los siguientes sistemas:
        {', '.join(systems)}
        
        La descripción debe incluir:
        1. Componentes principales
        2. Flujo de datos entre sistemas
        3. Interfaces de integración
        4. Protocolos de comunicación
        5. Consideraciones de seguridad
        
        Formato la descripción como si estuvieras explicando un diagrama visual.
        """
        
        # Generar descripción utilizando Gemini
        diagram_description = await self.gemini_client.generate_response(prompt, temperature=0.3)
        
        # Crear estructura del diagrama
        integration_diagram = {
            "timestamp": datetime.datetime.now().isoformat(),
            "systems": systems,
            "diagram_type": "integration_architecture",
            "description": diagram_description
        }
        
        return integration_diagram

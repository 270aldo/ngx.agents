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

class SecurityComplianceGuardian(A2AAgent):
    """
    Agente especializado en seguridad y cumplimiento normativo.
    
    Este agente se encarga de garantizar la seguridad de la aplicación, proteger
    los datos de los usuarios, verificar el cumplimiento de normativas y estándares,
    detectar posibles vulnerabilidades y proporcionar recomendaciones de seguridad.
    """
    
    def __init__(self, toolkit: Optional[Toolkit] = None):
        # Definir capacidades y habilidades
        capabilities = [
            "security_assessment", 
            "compliance_verification", 
            "vulnerability_detection", 
            "data_protection", 
            "security_recommendations"
        ]
        
        skills = [
            {"name": "security_assessment", "description": "Evaluación de la seguridad de sistemas y aplicaciones"},
            {"name": "compliance_verification", "description": "Verificación del cumplimiento de normativas y estándares"},
            {"name": "vulnerability_detection", "description": "Detección de vulnerabilidades y riesgos de seguridad"},
            {"name": "data_protection", "description": "Protección de datos sensibles y personales"},
            {"name": "security_recommendations", "description": "Recomendaciones para mejorar la seguridad"}
        ]
        
        # Ejemplos para la Agent Card
        examples = [
            {
                "input": {"message": "¿Puedes realizar una evaluación de seguridad de mi aplicación web?"},
                "output": {"response": "He realizado una evaluación de seguridad de tu aplicación web y he encontrado las siguientes vulnerabilidades..."}
            },
            {
                "input": {"message": "¿Cómo puedo asegurarme de que mi aplicación cumple con GDPR?"},
                "output": {"response": "Para cumplir con GDPR, debes implementar las siguientes medidas..."}
            }
        ]
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="security_compliance_guardian",
            name="NGX Security & Compliance Guardian",
            description="Especialista en seguridad, protección de datos y cumplimiento normativo",
            capabilities=capabilities,
            toolkit=toolkit,
            version="1.0.0",
            skills=skills
        )
        
        # Inicializar clientes y herramientas
        self.gemini_client = GeminiClient(model_name="gemini-2.0-flash")
        self.supabase_client = SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        
        # Inicializar gestor de estado
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
        Eres NGX Security & Compliance Guardian, un experto en seguridad, protección de datos y cumplimiento normativo.
        
        Tu objetivo es garantizar la seguridad de la aplicación, proteger los datos de los usuarios,
        verificar el cumplimiento de normativas y estándares, detectar posibles vulnerabilidades
        y proporcionar recomendaciones de seguridad en las siguientes áreas:
        
        1. Seguridad de la aplicación
           - Evaluación de la arquitectura de seguridad
           - Análisis de configuraciones de seguridad
           - Detección de vulnerabilidades en el código
           - Revisión de prácticas de desarrollo seguro
           - Monitoreo de actividades sospechosas
        
        2. Protección de datos
           - Verificación de cifrado de datos sensibles
           - Evaluación de políticas de acceso y permisos
           - Revisión de prácticas de almacenamiento de datos
           - Análisis de flujos de datos y transferencias
           - Recomendaciones para minimizar la exposición de datos
        
        3. Cumplimiento normativo
           - Verificación de cumplimiento con GDPR, HIPAA, CCPA, etc.
           - Evaluación de políticas de privacidad
           - Revisión de términos de servicio
           - Análisis de procedimientos de consentimiento
           - Recomendaciones para mejorar el cumplimiento
        
        4. Gestión de identidad y acceso
           - Evaluación de mecanismos de autenticación
           - Revisión de políticas de contraseñas
           - Análisis de control de acceso
           - Recomendaciones para implementar MFA
           - Detección de accesos no autorizados
        
        5. Respuesta a incidentes
           - Guía para la gestión de brechas de seguridad
           - Procedimientos de notificación de incidentes
           - Análisis forense básico
           - Recomendaciones para mitigar daños
           - Planes de recuperación y continuidad
        
        Debes adaptar tu enfoque según el contexto específico, considerando:
        - El tipo de aplicación y su arquitectura
        - La sensibilidad de los datos manejados
        - Las normativas aplicables según la región
        - Los recursos disponibles para implementar medidas
        - El nivel de conocimiento técnico del interlocutor
        
        Cuando proporciones análisis y recomendaciones:
        - Utiliza un lenguaje claro y preciso
        - Prioriza las vulnerabilidades según su gravedad
        - Proporciona pasos concretos y accionables
        - Balancea seguridad con usabilidad
        - Cita estándares y mejores prácticas relevantes
        - Adapta las recomendaciones al contexto específico
        
        Tu objetivo es ayudar a mantener un alto nivel de seguridad y cumplimiento
        sin comprometer la experiencia del usuario ni la funcionalidad de la aplicación.
        """
    
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
            # Delegamos la implementación al método _run_async_impl
            return await self._run_async_impl(input_text, user_id, **kwargs)
        except Exception as e:
            logger.error(f"Error en SecurityComplianceGuardian.run: {e}")
            return {
                "status": "error",
                "response": "Lo siento, ha ocurrido un error al procesar tu solicitud sobre seguridad y cumplimiento.",
                "error": str(e),
                "confidence": 0.0,
                "agent_id": self.agent_id,
                "metadata": {
                    "error_type": type(e).__name__,
                    "user_id": user_id
                }
            }
            
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
                    "security_queries": [],
                    "security_assessments": [],
                    "compliance_checks": [],
                    "vulnerability_scans": [],
                    "data_protections": [],
                    "general_recommendations": [],
                    "query_types": {},
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
                "security_queries": [],
                "security_assessments": [],
                "compliance_checks": [],
                "vulnerability_scans": [],
                "data_protections": [],
                "general_recommendations": [],
                "query_types": {},
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

    async def _run_async_impl(self, input_text: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Implementación asíncrona del método run. Procesa la entrada del usuario y genera una respuesta.
        
        Args:
            input_text: Texto de entrada del usuario
            user_id: ID del usuario (opcional)
            **kwargs: Argumentos adicionales como context, parameters, etc.
            
        Returns:
            Dict[str, Any]: Respuesta estandarizada del agente según el protocolo ADK
        """
        start_time = time.time()
        logger.info(f"Ejecutando SecurityComplianceGuardian con input: {input_text[:50]}...")
        
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
                
        # Añadir la consulta actual al historial
        context["security_queries"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "query": input_text
        })
        
        # Clasificar el tipo de consulta
        query_type = self._classify_query(input_text)
        capabilities_used = []
        
        # Actualizar el contexto con el tipo de consulta
        if query_type in context["query_types"]:
            context["query_types"][query_type] += 1
        else:
            context["query_types"][query_type] = 1
        
        # Procesar la consulta según su tipo
        if query_type == "security_assessment":
            result = await self._handle_security_assessment(input_text, context)
            capabilities_used.append("security_assessment")
            
            # Actualizar contexto con evaluaciones de seguridad
            context["security_assessments"].append({
                "timestamp": datetime.datetime.now().isoformat(),
                "assessment_summary": result.get("response", "")[:100] + "..."
            })
            
        elif query_type == "compliance_check":
            result = await self._handle_compliance_check(input_text, context)
            capabilities_used.append("compliance_verification")
            
            # Actualizar contexto con verificaciones de cumplimiento
            context["compliance_checks"].append({
                "timestamp": datetime.datetime.now().isoformat(),
                "compliance_summary": result.get("response", "")[:100] + "..."
            })
            
        elif query_type == "vulnerability_scan":
            result = await self._handle_vulnerability_scan(input_text, context)
            capabilities_used.append("vulnerability_detection")
            
            # Actualizar contexto con escaneos de vulnerabilidades
            context["vulnerability_scans"].append({
                "timestamp": datetime.datetime.now().isoformat(),
                "scan_summary": result.get("response", "")[:100] + "..."
            })
            
        elif query_type == "data_protection":
            result = await self._handle_data_protection(input_text, context)
            capabilities_used.append("data_protection")
            
            # Actualizar contexto con protecciones de datos
            context["data_protections"].append({
                "timestamp": datetime.datetime.now().isoformat(),
                "protection_summary": result.get("response", "")[:100] + "..."
            })
            
        else:
            result = await self._handle_general_request(input_text, context)
            capabilities_used.append("security_recommendations")
            
            # Actualizar contexto con recomendaciones generales
            context["general_recommendations"].append({
                "timestamp": datetime.datetime.now().isoformat(),
                "recommendation_summary": result.get("response", "")[:100] + "..."
            })
        
        response = result.get("response", "")
        artifacts = result.get("artifacts", [])
        
        # Añadir la interacción al historial de conversación
        context["conversation_history"].append({
            "user": input_text,
            "agent": response,
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": query_type
        })
        
        # Actualizar el contexto con la última respuesta
        context["last_response"] = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query": input_text,
            "response": response,
            "query_type": query_type
        }
        
        # Guardar el contexto actualizado
        if user_id:
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
                "query_type": query_type
            }
        }
        
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
        
        logger.info(f"SecurityComplianceGuardian procesando consulta: {user_input}")
        
        # Determinar el tipo de consulta
        query_type = self._classify_query(user_input)
        
        # Procesar según el tipo de consulta
        if query_type == "security_assessment":
            result = await self._handle_security_assessment(user_input, context)
        elif query_type == "compliance_check":
            result = await self._handle_compliance_check(user_input, context)
        elif query_type == "vulnerability_scan":
            result = await self._handle_vulnerability_scan(user_input, context)
        elif query_type == "data_protection":
            result = await self._handle_data_protection(user_input, context)
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
        logger.info(f"SecurityComplianceGuardian procesando mensaje de {from_agent}: {msg}")
        
        # Generar respuesta utilizando Gemini
        prompt = f"""
        {self.system_instructions}
        
        Has recibido un mensaje del agente {from_agent}:
        "{msg}"
        
        Responde con información relevante sobre seguridad y cumplimiento normativo relacionada con este mensaje.
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
            "query_type": "agent_message",
            "artifacts": [],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.8
        }
    
    def _classify_query(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta clasificada
        """
        query_lower = query.lower()
        
        # Palabras clave para evaluación de seguridad
        security_assessment_keywords = [
            "evaluación de seguridad", "auditoría de seguridad", "revisar seguridad",
            "analizar seguridad", "evaluar seguridad", "test de seguridad", "pentesting"
        ]
        
        # Palabras clave para verificación de cumplimiento
        compliance_check_keywords = [
            "cumplimiento", "normativa", "regulación", "gdpr", "hipaa", "pci",
            "iso 27001", "cumplir con", "estándar", "conformidad"
        ]
        
        # Palabras clave para detección de vulnerabilidades
        vulnerability_scan_keywords = [
            "vulnerabilidad", "escaneo", "exploits", "fallos", "debilidades",
            "amenazas", "riesgos", "hackear", "penetración"
        ]
        
        # Palabras clave para protección de datos
        data_protection_keywords = [
            "protección de datos", "cifrado", "encriptación", "privacidad",
            "datos personales", "anonimización", "fuga de datos", "proteger datos"
        ]
        
        # Verificar coincidencias con palabras clave
        for keyword in security_assessment_keywords:
            if keyword in query_lower:
                return "security_assessment"
                
        for keyword in compliance_check_keywords:
            if keyword in query_lower:
                return "compliance_check"
                
        for keyword in vulnerability_scan_keywords:
            if keyword in query_lower:
                return "vulnerability_scan"
                
        for keyword in data_protection_keywords:
            if keyword in query_lower:
                return "data_protection"
                
        # Si no hay coincidencias, devolver tipo general
        return "general_request"
    
    async def _handle_security_assessment(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con evaluación de seguridad.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Obtener información del sistema si está disponible
        system_info = context.get("system_info", {})
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita una evaluación de seguridad con la siguiente consulta:
        "{query}"
        
        Información del sistema:
        {json.dumps(system_info, indent=2) if system_info else "No disponible"}
        
        Proporciona una evaluación de seguridad detallada, identificando posibles riesgos
        y recomendando medidas para mejorar la seguridad. Estructura tu respuesta en secciones:
        1. Resumen de la evaluación
        2. Riesgos identificados (priorizados)
        3. Recomendaciones específicas
        4. Próximos pasos sugeridos
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear informe de seguridad como artefacto
        security_report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "security_assessment",
            "query": query,
            "assessment_summary": "Evaluación de seguridad completada",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"security_assessment_{uuid.uuid4().hex[:8]}",
            artifact_type="security_report",
            parts=[self.create_data_part(security_report)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "security_assessment",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_compliance_check(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con verificación de cumplimiento normativo.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Determinar qué normativa se está consultando
        regulations = []
        query_lower = query.lower()
        
        if "gdpr" in query_lower:
            regulations.append("GDPR")
        if "hipaa" in query_lower:
            regulations.append("HIPAA")
        if "ccpa" in query_lower:
            regulations.append("CCPA")
        if "pci" in query_lower or "pci dss" in query_lower:
            regulations.append("PCI DSS")
        
        if not regulations:
            regulations = ["GDPR", "HIPAA", "CCPA"]  # Por defecto, verificar las principales
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita una verificación de cumplimiento normativo con la siguiente consulta:
        "{query}"
        
        Normativas a verificar: {', '.join(regulations)}
        
        Proporciona una evaluación detallada del cumplimiento de estas normativas,
        identificando posibles áreas de incumplimiento y recomendando medidas para
        mejorar el cumplimiento. Estructura tu respuesta en secciones:
        1. Resumen del análisis de cumplimiento
        2. Estado de cumplimiento por normativa
        3. Áreas de mejora (priorizadas)
        4. Recomendaciones específicas
        5. Recursos adicionales
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear informe de cumplimiento como artefacto
        compliance_report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "compliance_check",
            "query": query,
            "regulations": regulations,
            "compliance_summary": "Verificación de cumplimiento completada",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"compliance_check_{uuid.uuid4().hex[:8]}",
            artifact_type="compliance_report",
            parts=[self.create_data_part(compliance_report)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "compliance_check",
            "regulations": regulations,
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_vulnerability_scan(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con detección de vulnerabilidades.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Obtener información del sistema si está disponible
        system_info = context.get("system_info", {})
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita un análisis de vulnerabilidades con la siguiente consulta:
        "{query}"
        
        Información del sistema:
        {json.dumps(system_info, indent=2) if system_info else "No disponible"}
        
        Proporciona un análisis detallado de posibles vulnerabilidades,
        clasificándolas según su gravedad y recomendando medidas para mitigarlas.
        Estructura tu respuesta en secciones:
        1. Resumen del análisis
        2. Vulnerabilidades identificadas (clasificadas por gravedad)
        3. Vectores de ataque potenciales
        4. Recomendaciones de mitigación
        5. Recursos y herramientas recomendados
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear informe de vulnerabilidades como artefacto
        vulnerability_report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "vulnerability_scan",
            "query": query,
            "scan_summary": "Análisis de vulnerabilidades completado",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"vulnerability_scan_{uuid.uuid4().hex[:8]}",
            artifact_type="vulnerability_report",
            parts=[self.create_data_part(vulnerability_report)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "vulnerability_scan",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_data_protection(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas relacionadas con protección de datos.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario solicita información sobre protección de datos con la siguiente consulta:
        "{query}"
        
        Proporciona una respuesta detallada sobre protección de datos,
        incluyendo mejores prácticas, técnicas de cifrado, políticas de acceso,
        y recomendaciones para garantizar la privacidad y seguridad de los datos.
        Estructura tu respuesta en secciones:
        1. Resumen de la consulta
        2. Principios clave de protección de datos
        3. Técnicas y herramientas recomendadas
        4. Políticas y procedimientos sugeridos
        5. Recursos adicionales
        """
        
        # Generar respuesta utilizando Gemini
        response = await self.gemini_client.generate_response(prompt, temperature=0.4)
        
        # Crear guía de protección de datos como artefacto
        data_protection_guide = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "data_protection",
            "query": query,
            "guide_summary": "Guía de protección de datos generada",
            "response": response
        }
        
        # Crear artefacto
        artifact = self.create_artifact(
            artifact_id=f"data_protection_{uuid.uuid4().hex[:8]}",
            artifact_type="data_protection_guide",
            parts=[self.create_data_part(data_protection_guide)]
        )
        
        # Crear mensaje
        message = self.create_message(
            role="agent",
            parts=[self.create_text_part(response)]
        )
        
        return {
            "response": response,
            "query_type": "data_protection",
            "artifacts": [artifact],
            "message": message,
            "agent_id": self.agent_id,
            "confidence": 0.9
        }
    
    async def _handle_general_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja consultas generales relacionadas con seguridad y cumplimiento.
        
        Args:
            query: Consulta del usuario
            context: Contexto de la consulta
            
        Returns:
            Dict[str, Any]: Resultado de la consulta
        """
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        El usuario ha realizado la siguiente consulta sobre seguridad o cumplimiento:
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
    
    async def _generate_security_checklist(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera una lista de verificación de seguridad personalizada.
        
        Args:
            context: Contexto para la generación de la lista
            
        Returns:
            Dict[str, Any]: Lista de verificación de seguridad
        """
        # Determinar el tipo de aplicación
        app_type = context.get("app_type", "general")
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        Genera una lista de verificación de seguridad completa para una aplicación de tipo: {app_type}.
        
        La lista debe incluir:
        1. Verificaciones de seguridad de la aplicación
        2. Verificaciones de protección de datos
        3. Verificaciones de cumplimiento normativo
        4. Verificaciones de gestión de identidad y acceso
        5. Verificaciones de respuesta a incidentes
        
        Para cada elemento, incluye:
        - Descripción clara del elemento a verificar
        - Nivel de prioridad (Alto, Medio, Bajo)
        - Método de verificación
        - Referencia a estándares relevantes (si aplica)
        
        Formatea la lista de manera estructurada y fácil de seguir.
        """
        
        # Generar lista de verificación utilizando Gemini
        checklist_content = await self.gemini_client.generate_response(prompt, temperature=0.3)
        
        # Crear estructura de la lista de verificación
        security_checklist = {
            "timestamp": datetime.datetime.now().isoformat(),
            "app_type": app_type,
            "checklist_type": "security",
            "content": checklist_content
        }
        
        return security_checklist
    
    async def _generate_incident_response_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un plan de respuesta a incidentes personalizado.
        
        Args:
            context: Contexto para la generación del plan
            
        Returns:
            Dict[str, Any]: Plan de respuesta a incidentes
        """
        # Determinar el tipo de organización
        org_type = context.get("org_type", "general")
        
        # Construir el prompt para el modelo
        prompt = f"""
        {self.system_instructions}
        
        Genera un plan de respuesta a incidentes de seguridad completo para una organización de tipo: {org_type}.
        
        El plan debe incluir:
        1. Roles y responsabilidades
        2. Procedimientos de detección de incidentes
        3. Procedimientos de contención
        4. Procedimientos de erradicación
        5. Procedimientos de recuperación
        6. Procedimientos de comunicación
        7. Lecciones aprendidas y mejora continua
        
        Para cada sección, proporciona detalles específicos y accionables.
        Formatea el plan de manera estructurada y fácil de seguir.
        """
        
        # Generar plan utilizando Gemini
        plan_content = await self.gemini_client.generate_response(prompt, temperature=0.3)
        
        # Crear estructura del plan
        incident_response_plan = {
            "timestamp": datetime.datetime.now().isoformat(),
            "org_type": org_type,
            "plan_type": "incident_response",
            "content": plan_content
        }
        
        return incident_response_plan

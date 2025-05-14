"""
Adaptador para el agente SystemsIntegrationOps que utiliza los componentes optimizados.

Este adaptador extiende el agente SystemsIntegrationOps original y sobrescribe los métodos
necesarios para utilizar el sistema A2A optimizado y el cliente Vertex AI optimizado.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from agents.systems_integration_ops.agent import SystemsIntegrationOps
from infrastructure.adapters.base_agent_adapter import BaseAgentAdapter
from core.telemetry import get_telemetry

# Configurar logger
logger = logging.getLogger(__name__)

class SystemsIntegrationOpsAdapter(SystemsIntegrationOps, BaseAgentAdapter):
    """
    Adaptador para el agente SystemsIntegrationOps que utiliza los componentes optimizados.
    
    Este adaptador extiende el agente SystemsIntegrationOps original y utiliza la clase
    BaseAgentAdapter para implementar métodos comunes.
    """
    
    def __init__(self):
        """
        Inicializa el adaptador SystemsIntegrationOps.
        """
        super().__init__()
        self.telemetry = get_telemetry()
        self.agent_name = "systems_integration_ops"
        
        # Configuración de clasificación
        self.fallback_keywords = [
            "integración", "integration", "automatización", "automation", 
            "api", "infraestructura", "infrastructure", "pipeline",
            "conectar", "connect", "sincronizar", "synchronize",
            "flujo de trabajo", "workflow", "datos", "data"
        ]
        
        self.excluded_keywords = [
            "nutrición", "nutrition", "entrenamiento", "training",
            "médico", "medical", "doctor", "lesión", "injury"
        ]
    
    def get_agent_name(self) -> str:
        """Devuelve el nombre del agente."""
        return self.agent_name
    
    def _create_default_context(self) -> Dict[str, Any]:
        """
        Crea un contexto predeterminado para el agente SystemsIntegrationOps.
        
        Returns:
            Dict[str, Any]: Contexto predeterminado
        """
        return {
            "conversation_history": [],
            "user_profile": {},
            "integration_requests": [],
            "automation_requests": [],
            "api_requests": [],
            "infrastructure_requests": [],
            "data_pipeline_requests": [],
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_intent_to_query_type_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de intenciones a tipos de consulta específico para SystemsIntegrationOps.
        
        Returns:
            Dict[str, str]: Mapeo de intenciones a tipos de consulta
        """
        return {
            "integrar": "integration_request",
            "integración": "integration_request",
            "integration": "integration_request",
            "conectar": "integration_request",
            "connect": "integration_request",
            "sincronizar": "integration_request",
            "synchronize": "integration_request",
            "interoperabilidad": "integration_request",
            "interoperability": "integration_request",
            
            "automatizar": "automation_request",
            "automatización": "automation_request",
            "automation": "automation_request",
            "workflow": "automation_request",
            "flujo de trabajo": "automation_request",
            "proceso": "automation_request",
            "process": "automation_request",
            
            "api": "api_request",
            "endpoint": "api_request",
            "webhook": "api_request",
            "interfaz": "api_request",
            "interface": "api_request",
            "servicio web": "api_request",
            "web service": "api_request",
            
            "infraestructura": "infrastructure_request",
            "infrastructure": "infrastructure_request",
            "arquitectura": "infrastructure_request",
            "architecture": "infrastructure_request",
            "rendimiento": "infrastructure_request",
            "performance": "infrastructure_request",
            "escalabilidad": "infrastructure_request",
            "scalability": "infrastructure_request",
            "servidor": "infrastructure_request",
            "server": "infrastructure_request",
            
            "pipeline": "data_pipeline_request",
            "datos": "data_pipeline_request",
            "data": "data_pipeline_request",
            "etl": "data_pipeline_request",
            "procesamiento": "data_pipeline_request",
            "processing": "data_pipeline_request",
            "flujo de datos": "data_pipeline_request",
            "data flow": "data_pipeline_request"
        }
    
    async def _process_query(self, query: str, user_id: str, session_id: str,
                           program_type: str, state: Dict[str, Any], profile: Dict[str, Any],
                           **kwargs) -> Dict[str, Any]:
        """
        Procesa la consulta del usuario.
        
        Args:
            query: La consulta del usuario
            user_id: ID del usuario
            session_id: ID de la sesión
            program_type: Tipo de programa (general, elite, etc.)
            state: Estado actual del usuario
            profile: Perfil del usuario
            **kwargs: Argumentos adicionales
            
        Returns:
            Dict[str, Any]: Respuesta del agente
        """
        try:
            # Registrar telemetría para el inicio del procesamiento
            if self.telemetry:
                with self.telemetry.start_as_current_span(f"{self.__class__.__name__}._process_query") as span:
                    span.set_attribute("user_id", user_id)
                    span.set_attribute("session_id", session_id)
                    span.set_attribute("program_type", program_type)
            
            # Determinar el tipo de consulta basado en el mapeo de intenciones
            query_type = self._determine_query_type(query)
            logger.info(f"SystemsIntegrationOpsAdapter procesando consulta de tipo: {query_type}")
            
            # Obtener o crear el contexto
            context = state.get("integration_context", self._create_default_context())
            
            # Procesar según el tipo de consulta
            if query_type == "integration_request":
                result = await self._handle_integration_request(query, context, profile, program_type)
            elif query_type == "automation_request":
                result = await self._handle_automation_request(query, context, profile, program_type)
            elif query_type == "api_request":
                result = await self._handle_api_request(query, context, profile, program_type)
            elif query_type == "infrastructure_request":
                result = await self._handle_infrastructure_request(query, context, profile, program_type)
            elif query_type == "data_pipeline_request":
                result = await self._handle_data_pipeline_request(query, context, profile, program_type)
            else:
                # Tipo de consulta no reconocido, usar procesamiento genérico
                result = await self._handle_general_request(query, context, profile, program_type)
            
            # Actualizar el contexto en el estado
            state["integration_context"] = context
            
            # Construir la respuesta
            response = {
                "success": True,
                "output": result.get("response", "No se pudo generar una respuesta"),
                "query_type": query_type,
                "program_type": program_type,
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat(),
                "context": context
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error al procesar consulta en SystemsIntegrationOpsAdapter: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent": self.__class__.__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    def _determine_query_type(self, query: str) -> str:
        """
        Determina el tipo de consulta basado en el texto.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta identificado
        """
        query_lower = query.lower()
        intent_mapping = self._get_intent_to_query_type_mapping()
        
        for intent, query_type in intent_mapping.items():
            if intent.lower() in query_lower:
                return query_type
        
        # Si no se encuentra un tipo específico, verificar palabras clave adicionales
        if any(word in query_lower for word in ["sistema", "system", "integrar", "conectar"]):
            return "integration_request"
        elif any(word in query_lower for word in ["automatizar", "proceso", "workflow"]):
            return "automation_request"
        elif any(word in query_lower for word in ["api", "endpoint", "servicio"]):
            return "api_request"
        elif any(word in query_lower for word in ["infraestructura", "servidor", "arquitectura"]):
            return "infrastructure_request"
        elif any(word in query_lower for word in ["datos", "pipeline", "etl"]):
            return "data_pipeline_request"
        
        # Si no se encuentra un tipo específico, devolver solicitud general
        return "general_request"
    
    async def _handle_integration_request(self, query: str, context: Dict[str, Any], 
                                        profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta de integración de sistemas.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado de la integración de sistemas
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
        
        # Generar la respuesta de integración
        integration_response = await self._generate_response(
            prompt=f"""
            Eres un experto en integración de sistemas y automatización operativa.
            
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
            """,
            context=context
        )
        
        # Crear informe de integración como artefacto
        integration_report = {
            "timestamp": datetime.now().isoformat(),
            "query_type": "integration_request",
            "query": query,
            "systems": systems,
            "integration_summary": "Análisis de integración de sistemas completado",
            "response": integration_response
        }
        
        # Actualizar el contexto con la nueva solicitud de integración
        if "integration_requests" not in context:
            context["integration_requests"] = []
            
        context["integration_requests"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "systems": systems,
            "integration_report": integration_report
        })
        
        return {
            "response": integration_response,
            "systems": systems,
            "integration_report": integration_report,
            "context": context
        }
    
    async def _handle_automation_request(self, query: str, context: Dict[str, Any], 
                                       profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta de automatización de flujos de trabajo.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado de la automatización de flujos de trabajo
        """
        # Generar la respuesta de automatización
        automation_response = await self._generate_response(
            prompt=f"""
            Eres un experto en automatización de flujos de trabajo y procesos.
            
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
            """,
            context=context
        )
        
        # Crear plan de automatización como artefacto
        automation_plan = {
            "timestamp": datetime.now().isoformat(),
            "query_type": "automation_request",
            "query": query,
            "automation_summary": "Plan de automatización generado",
            "response": automation_response
        }
        
        # Actualizar el contexto con la nueva solicitud de automatización
        if "automation_requests" not in context:
            context["automation_requests"] = []
            
        context["automation_requests"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "automation_plan": automation_plan
        })
        
        return {
            "response": automation_response,
            "automation_plan": automation_plan,
            "context": context
        }
    
    async def _handle_api_request(self, query: str, context: Dict[str, Any], 
                                profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta de gestión de APIs.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado de la gestión de APIs
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
        
        # Generar la respuesta de API
        api_response = await self._generate_response(
            prompt=f"""
            Eres un experto en gestión de APIs y integración de sistemas.
            
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
            """,
            context=context
        )
        
        # Crear guía de API como artefacto
        api_guide = {
            "timestamp": datetime.now().isoformat(),
            "query_type": "api_request",
            "query": query,
            "apis": apis,
            "guide_summary": "Guía de APIs generada",
            "response": api_response
        }
        
        # Actualizar el contexto con la nueva solicitud de API
        if "api_requests" not in context:
            context["api_requests"] = []
            
        context["api_requests"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "apis": apis,
            "api_guide": api_guide
        })
        
        return {
            "response": api_response,
            "apis": apis,
            "api_guide": api_guide,
            "context": context
        }
    
    async def _handle_infrastructure_request(self, query: str, context: Dict[str, Any], 
                                           profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta de optimización de infraestructura.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado de la optimización de infraestructura
        """
        # Generar la respuesta de infraestructura
        infrastructure_response = await self._generate_response(
            prompt=f"""
            Eres un experto en arquitectura e infraestructura tecnológica.
            
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
            """,
            context=context
        )
        
        # Crear informe de infraestructura como artefacto
        infrastructure_report = {
            "timestamp": datetime.now().isoformat(),
            "query_type": "infrastructure_request",
            "query": query,
            "report_summary": "Informe de infraestructura generado",
            "response": infrastructure_response
        }
        
        # Actualizar el contexto con la nueva solicitud de infraestructura
        if "infrastructure_requests" not in context:
            context["infrastructure_requests"] = []
            
        context["infrastructure_requests"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "infrastructure_report": infrastructure_report
        })
        
        return {
            "response": infrastructure_response,
            "infrastructure_report": infrastructure_report,
            "context": context
        }
    
    async def _handle_data_pipeline_request(self, query: str, context: Dict[str, Any], 
                                          profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta de diseño de pipelines de datos.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado del diseño de pipelines de datos
        """
        # Generar la respuesta de pipeline de datos
        pipeline_response = await self._generate_response(
            prompt=f"""
            Eres un experto en diseño de pipelines de datos y arquitectura de datos.
            
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
            """,
            context=context
        )
        
        # Crear diseño de pipeline como artefacto
        pipeline_design = {
            "timestamp": datetime.now().isoformat(),
            "query_type": "data_pipeline_request",
            "query": query,
            "design_summary": "Diseño de pipeline de datos generado",
            "response": pipeline_response
        }
        
        # Actualizar el contexto con la nueva solicitud de pipeline de datos
        if "data_pipeline_requests" not in context:
            context["data_pipeline_requests"] = []
            
        context["data_pipeline_requests"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "pipeline_design": pipeline_design
        })
        
        return {
            "response": pipeline_response,
            "pipeline_design": pipeline_design,
            "context": context
        }
    
    async def _handle_general_request(self, query: str, context: Dict[str, Any], 
                                    profile: Dict[str, Any], program_type: str) -> Dict[str, Any]:
        """
        Maneja una consulta general.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            profile: Perfil del usuario
            program_type: Tipo de programa
            
        Returns:
            Dict[str, Any]: Resultado de la respuesta general
        """
        # Generar respuesta general
        general_response = await self._generate_response(
            prompt=f"""
            Eres un experto en integración de sistemas y automatización operativa.
            
            El usuario ha realizado la siguiente consulta sobre integración de sistemas o automatización:
            "{query}"
            
            Proporciona una respuesta detallada y útil, adaptada específicamente a esta consulta.
            Incluye información relevante, mejores prácticas, y recomendaciones concretas.
            """,
            context=context
        )
        
        # Actualizar el historial de conversación
        if "conversation_history" not in context:
            context["conversation_history"] = []
            
        context["conversation_history"].append({
            "date": datetime.now().isoformat(),
            "query": query,
            "response": general_response
        })
        
        return {
            "response": general_response,
            "context": context
        }
    
    async def _generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Genera una respuesta utilizando el modelo de lenguaje.
        
        Args:
            prompt: Prompt para el modelo
            context: Contexto actual
            
        Returns:
            str: Respuesta generada
        """
        try:
            # En una implementación real, aquí se llamaría al cliente de Vertex AI optimizado
            # Por ahora, simulamos una respuesta
            return f"Respuesta simulada para: {prompt[:50]}..."
        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}", exc_info=True)
            return f"Error al generar respuesta: {str(e)}"

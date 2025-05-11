import logging
import uuid
import time
from typing import Dict, Any, Optional, List, Union
import json
import os
from google.cloud import aiplatform
import datetime
import asyncio
from pydantic import BaseModel, Field

# Importar componentes de Google ADK
from adk.toolkit import Toolkit
from adk.agent import Skill as GoogleADKSkill

from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from agents.base.adk_agent import ADKAgent
from core.agent_card import AgentCard, Example
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from core.logging_config import get_logger

# Configurar logger
logger = get_logger(__name__)

# Definir esquemas de entrada y salida para las skills
class CommunityBuildingInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre construcción de comunidad")
    community_data: Optional[Dict[str, Any]] = Field(None, description="Datos de la comunidad actual")

class CommunityBuildingOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre construcción de comunidad")
    community_plan: Dict[str, Any] = Field(..., description="Plan de comunidad estructurado")

class UserExperienceInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre experiencia de usuario")
    experience_data: Optional[Dict[str, Any]] = Field(None, description="Datos de experiencia del usuario")

class UserExperienceOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre experiencia de usuario")
    journey_map: Optional[Dict[str, Any]] = Field(None, description="Mapa de customer journey")

class CustomerSupportInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre soporte al cliente")
    problem_details: Optional[Dict[str, Any]] = Field(None, description="Detalles del problema reportado")

class CustomerSupportOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre soporte al cliente")
    ticket: Optional[Dict[str, Any]] = Field(None, description="Ticket de soporte generado")

class RetentionStrategyInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre estrategias de retención")
    retention_data: Optional[Dict[str, Any]] = Field(None, description="Datos de retención del usuario")

class RetentionStrategyOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre estrategias de retención")
    retention_plan: Optional[Dict[str, Any]] = Field(None, description="Plan de retención estructurado")

class CommunicationManagementInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre gestión de comunicación")
    communication_details: Optional[Dict[str, Any]] = Field(None, description="Detalles de comunicación")

class CommunicationManagementOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre gestión de comunicación")
    communication_plan: Optional[Dict[str, Any]] = Field(None, description="Plan de comunicación estructurado")

class WebSearchInput(BaseModel):
    query: str = Field(..., description="Consulta de búsqueda web")

class WebSearchOutput(BaseModel):
    response: str = Field(..., description="Resultados de la búsqueda web")
    search_results: Optional[List[Dict[str, Any]]] = Field(None, description="Resultados estructurados de la búsqueda")

class GeneralRequestInput(BaseModel):
    query: str = Field(..., description="Consulta general del usuario")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para la consulta")

class GeneralRequestOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada a la consulta general")

# Definir las skills como clases que heredan de GoogleADKSkill
class CommunityBuildingSkill(GoogleADKSkill):
    name = "community_building"
    description = "Diseña estrategias y programas para crear, desarrollar y mantener comunidades activas"
    input_schema = CommunityBuildingInput
    output_schema = CommunityBuildingOutput
    
    async def handler(self, input_data: CommunityBuildingInput) -> CommunityBuildingOutput:
        """Implementación de la skill de construcción de comunidad"""
        query = input_data.query
        community_data = input_data.community_data or {}
        
        # Construir el prompt para el modelo
        community_data_str = f"Más detalles del contexto:\n{json.dumps(community_data, indent=2)}" \
            if community_data else "No se proporcionaron detalles adicionales."
        
        prompt = f"""
        Eres un experto en construcción de comunidades y éxito del cliente.
        
        El usuario solicita ayuda con la construcción de comunidad:
        "{query}"
        
        {community_data_str}
        
        Proporciona una respuesta detallada sobre cómo construir y gestionar una comunidad online,
        incluyendo estrategias de engagement, moderación, creación de contenido y eventos.
        
        Estructura tu respuesta en secciones:
        1. Análisis de la necesidad de comunidad
        2. Estrategias recomendadas
        3. Pasos de implementación
        4. Métricas de éxito
        5. Recursos adicionales
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Generar plan de comunidad estructurado
        plan_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un plan de comunidad estructurado en formato JSON con los siguientes campos:
        - objective: objetivo principal del plan
        - target_audience: audiencia objetivo
        - engagement_strategies: estrategias de engagement
        - content_plan: plan de contenido
        - events: eventos recomendados
        - moderation: estrategia de moderación
        - metrics: métricas para seguimiento
        - timeline: cronograma de implementación
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        plan_json = await gemini_client.generate_structured_output(plan_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(plan_json, dict):
            try:
                plan_json = json.loads(plan_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                plan_json = {
                    "objective": "Construir una comunidad activa y comprometida",
                    "target_audience": "Usuarios del producto/servicio",
                    "engagement_strategies": [
                        "Programa de embajadores",
                        "Contenido generado por usuarios",
                        "Gamificación (puntos, insignias)",
                        "Eventos regulares"
                    ],
                    "content_plan": {
                        "types": ["Tutoriales", "Casos de éxito", "Preguntas frecuentes", "Novedades"],
                        "frequency": "Semanal"
                    },
                    "events": [
                        "Webinars mensuales",
                        "AMAs trimestrales",
                        "Hackathons anuales"
                    ],
                    "moderation": {
                        "approach": "Combinación de moderación por equipo y comunidad",
                        "guidelines": "Crear y publicar directrices claras"
                    },
                    "metrics": [
                        "Usuarios activos mensuales",
                        "Tasa de participación",
                        "Tiempo en plataforma",
                        "Retención de miembros"
                    ],
                    "timeline": {
                        "phase1": "Configuración (1-2 meses)",
                        "phase2": "Lanzamiento y crecimiento inicial (3-6 meses)",
                        "phase3": "Expansión y optimización (6-12 meses)"
                    }
                }
        
        return CommunityBuildingOutput(
            response=response_text,
            community_plan=plan_json
        )

class UserExperienceSkill(GoogleADKSkill):
    name = "user_experience"
    description = "Analiza y optimiza la experiencia del usuario en diferentes puntos de contacto"
    input_schema = UserExperienceInput
    output_schema = UserExperienceOutput
    
    async def handler(self, input_data: UserExperienceInput) -> UserExperienceOutput:
        """Implementación de la skill de experiencia de usuario"""
        query = input_data.query
        experience_data = input_data.experience_data or {}
        
        # Construir el prompt para el modelo
        experience_data_str = f"Detalles sobre la experiencia del usuario:\n{json.dumps(experience_data, indent=2)}" \
            if experience_data else "No se proporcionaron datos específicos de la experiencia."
        
        prompt = f"""
        Eres un experto en experiencia de usuario y éxito del cliente.
        
        El usuario consulta sobre la experiencia del usuario:
        "{query}"
        
        {experience_data_str}
        
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
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Generar journey map estructurado
        journey_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un mapa de customer journey estructurado en formato JSON con los siguientes campos:
        - stages: etapas del journey (array)
        - touchpoints: puntos de contacto por etapa (objeto)
        - pain_points: puntos de dolor por etapa (objeto)
        - opportunities: oportunidades de mejora por etapa (objeto)
        - emotions: emociones del usuario por etapa (objeto)
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        journey_json = await gemini_client.generate_structured_output(journey_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(journey_json, dict):
            try:
                journey_json = json.loads(journey_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                journey_json = {
                    "stages": ["Descubrimiento", "Consideración", "Onboarding", "Uso", "Retención"],
                    "touchpoints": {
                        "Descubrimiento": ["Redes sociales", "Búsqueda web", "Recomendaciones"],
                        "Consideración": ["Sitio web", "Demos", "Comparativas"],
                        "Onboarding": ["Registro", "Tutorial", "Primera experiencia"],
                        "Uso": ["Interfaz principal", "Soporte", "Actualizaciones"],
                        "Retención": ["Comunicaciones", "Renovación", "Programa de lealtad"]
                    },
                    "pain_points": {
                        "Descubrimiento": ["Dificultad para encontrar información relevante"],
                        "Consideración": ["Proceso de comparación complejo"],
                        "Onboarding": ["Tutorial demasiado largo", "Muchos pasos de configuración"],
                        "Uso": ["Interfaz no intuitiva", "Tiempos de carga lentos"],
                        "Retención": ["Falta de incentivos para continuar", "Comunicación excesiva"]
                    },
                    "opportunities": {
                        "Descubrimiento": ["Mejorar SEO", "Optimizar presencia en redes"],
                        "Consideración": ["Simplificar comparativas", "Añadir testimonios"],
                        "Onboarding": ["Personalizar onboarding", "Reducir pasos"],
                        "Uso": ["Rediseñar interfaz", "Mejorar rendimiento"],
                        "Retención": ["Programa de lealtad", "Comunicación personalizada"]
                    },
                    "emotions": {
                        "Descubrimiento": "Curiosidad",
                        "Consideración": "Interés/Duda",
                        "Onboarding": "Expectativa/Frustración",
                        "Uso": "Satisfacción/Confusión",
                        "Retención": "Lealtad/Indiferencia"
                    }
                }
        
        return UserExperienceOutput(
            response=response_text,
            journey_map=journey_json
        )

class CustomerSupportSkill(GoogleADKSkill):
    name = "customer_support"
    description = "Desarrolla sistemas y procesos para proporcionar soporte efectivo y resolver problemas"
    input_schema = CustomerSupportInput
    output_schema = CustomerSupportOutput
    
    async def handler(self, input_data: CustomerSupportInput) -> CustomerSupportOutput:
        """Implementación de la skill de soporte al cliente"""
        query = input_data.query
        problem_details = input_data.problem_details or {}
        
        # Construir el prompt para el modelo
        problem_details_str = "\n".join([f"- {k}: {v}" for k, v in problem_details.items()]) if problem_details else "No se proporcionaron detalles adicionales del problema."
        
        prompt = f"""
        Eres un experto en soporte al cliente y éxito del cliente.
        
        El usuario necesita soporte técnico. Su consulta es:
        "{query}"
        
        Detalles adicionales del problema:
        {problem_details_str}
        
        Por favor, proporciona una solución paso a paso, o solicita más información si es necesario.
        Genera un ticket de soporte con un resumen del problema y la solución propuesta (o los siguientes pasos).
        Intenta ser conciso y directo en tu respuesta al usuario, y detallado en el ticket.
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.5)
        
        # Crear ticket de soporte
        ticket_id = str(uuid.uuid4())
        ticket = {
            "ticket_id": ticket_id,
            "query": query,
            "problem_details": problem_details,
            "response_provided": response_text,
            "internal_summary": f"Ticket {ticket_id}: Usuario reportó '{query}'. Detalles: {problem_details_str}. Respuesta: {response_text[:100]}...",
            "status": "open",
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        return CustomerSupportOutput(
            response=response_text,
            ticket=ticket
        )

class RetentionStrategySkill(GoogleADKSkill):
    name = "retention_strategies"
    description = "Diseña e implementa programas y tácticas para maximizar la retención de clientes"
    input_schema = RetentionStrategyInput
    output_schema = RetentionStrategyOutput
    
    async def handler(self, input_data: RetentionStrategyInput) -> RetentionStrategyOutput:
        """Implementación de la skill de estrategias de retención"""
        query = input_data.query
        retention_data = input_data.retention_data or {}
        
        # Construir el prompt para el modelo
        retention_info_str = "\n".join([f"- {k}: {v}" for k, v in retention_data.items()]) if retention_data else "No se proporcionaron datos específicos para la retención."
        
        prompt = f"""
        Eres un experto en retención de clientes y éxito del cliente.
        
        El usuario busca estrategias de retención. La consulta es:
        "{query}"
        
        Información relevante para la estrategia de retención:
        {retention_info_str}
        
        Por favor, diseña un plan de retención o sugiere tácticas específicas y accionables.
        Considera la personalización y el valor para el cliente. Sé creativo y práctico.
        Devuelve el plan o las tácticas como parte de tu respuesta.
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.7)
        
        # Generar plan de retención estructurado
        plan_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un plan de retención estructurado en formato JSON con los siguientes campos:
        - objective: objetivo principal del plan
        - target_segments: segmentos objetivo
        - strategies: estrategias de retención
        - loyalty_program: detalles del programa de lealtad
        - win_back: estrategias para recuperar clientes
        - metrics: métricas para seguimiento
        - timeline: cronograma de implementación
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        plan_json = await gemini_client.generate_structured_output(plan_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(plan_json, dict):
            try:
                plan_json = json.loads(plan_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                plan_json = {
                    "objective": "Aumentar la retención de clientes y reducir el churn",
                    "target_segments": [
                        "Clientes nuevos (0-3 meses)",
                        "Clientes establecidos (3-12 meses)",
                        "Clientes de largo plazo (>12 meses)",
                        "Clientes en riesgo de abandono"
                    ],
                    "strategies": [
                        "Programa de onboarding personalizado",
                        "Comunicación proactiva en momentos clave",
                        "Programa de lealtad escalonado",
                        "Educación continua y recursos de valor",
                        "Feedback regular y mejoras basadas en él"
                    ],
                    "loyalty_program": {
                        "tiers": ["Básico", "Plata", "Oro", "Platino"],
                        "benefits": ["Contenido exclusivo", "Soporte prioritario", "Acceso anticipado", "Descuentos"],
                        "progression": "Basada en tiempo de permanencia y nivel de uso"
                    },
                    "win_back": [
                        "Campaña de reactivación con incentivos",
                        "Encuesta de salida para entender motivos",
                        "Oferta personalizada basada en historial"
                    ],
                    "metrics": [
                        "Tasa de retención mensual/anual",
                        "Churn rate por segmento",
                        "Customer Lifetime Value (CLV)",
                        "Net Promoter Score (NPS)",
                        "Engagement con programa de lealtad"
                    ],
                    "timeline": {
                        "phase1": "Implementación de programa de lealtad (1-2 meses)",
                        "phase2": "Optimización de comunicaciones (2-3 meses)",
                        "phase3": "Lanzamiento de estrategias de win-back (3-4 meses)"
                    }
                }
        
        return RetentionStrategyOutput(
            response=response_text,
            retention_plan=plan_json
        )

class CommunicationManagementSkill(GoogleADKSkill):
    name = "communication_management"
    description = "Planifica y optimiza estrategias de comunicación con usuarios y clientes"
    input_schema = CommunicationManagementInput
    output_schema = CommunicationManagementOutput
    
    async def handler(self, input_data: CommunicationManagementInput) -> CommunicationManagementOutput:
        """Implementación de la skill de gestión de comunicación"""
        query = input_data.query
        communication_details = input_data.communication_details or {}
        
        # Construir el prompt para el modelo
        communication_details_str = f"Detalles de la comunicación:\n{json.dumps(communication_details, indent=2)}" \
            if communication_details else "No se proporcionaron detalles específicos de la comunicación."
        
        prompt = f"""
        Eres un experto en comunicación con clientes y éxito del cliente.
        
        El usuario solicita ayuda con la gestión de comunicación:
        "{query}"
        
        {communication_details_str}
        
        Proporciona una respuesta detallada sobre estrategias de comunicación efectivas,
        gestión de crisis, comunicación interna, relaciones públicas, y uso de canales.
        
        Estructura tu respuesta en secciones:
        1. Análisis de las necesidades de comunicación
        2. Estrategia de comunicación recomendada
        3. Plantillas y ejemplos de mensajes
        4. Calendario de comunicación sugerido
        5. Métricas para evaluar efectividad
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)
        
        # Generar plan de comunicación estructurado
        plan_prompt = f"""
        Basándote en la consulta del usuario:
        "{query}"
        
        Genera un plan de comunicación estructurado en formato JSON con los siguientes campos:
        - objective: objetivo principal del plan
        - target_audience: audiencia objetivo
        - channels: canales de comunicación
        - message_types: tipos de mensajes
        - frequency: frecuencia recomendada
        - templates: plantillas de mensajes
        - metrics: métricas para seguimiento
        - calendar: calendario de comunicación
        
        Devuelve SOLO el JSON, sin explicaciones adicionales.
        """
        
        plan_json = await gemini_client.generate_structured_output(plan_prompt)
        
        # Si la respuesta no es un diccionario, intentar convertirla
        if not isinstance(plan_json, dict):
            try:
                plan_json = json.loads(plan_json)
            except:
                # Si no se puede convertir, crear un diccionario básico
                plan_json = {
                    "objective": "Establecer una comunicación efectiva y personalizada con los clientes",
                    "target_audience": [
                        "Clientes nuevos",
                        "Clientes activos",
                        "Clientes inactivos",
                        "Clientes potenciales"
                    ],
                    "channels": [
                        "Email",
                        "In-app",
                        "SMS",
                        "Redes sociales",
                        "Blog",
                        "Webinars"
                    ],
                    "message_types": {
                        "onboarding": "Bienvenida y primeros pasos",
                        "educational": "Tutoriales y mejores prácticas",
                        "promotional": "Nuevas funciones y ofertas",
                        "engagement": "Recordatorios y reactivación",
                        "feedback": "Solicitudes de opinión y encuestas"
                    },
                    "frequency": {
                        "email": "1-2 veces por semana",
                        "in-app": "Contextual, no más de 1 por día",
                        "sms": "Solo para información crítica",
                        "social": "3-5 veces por semana"
                    },
                    "templates": {
                        "welcome": "Plantilla de bienvenida",
                        "feature_update": "Plantilla de actualización",
                        "re-engagement": "Plantilla de reactivación"
                    },
                    "metrics": [
                        "Tasa de apertura",
                        "Tasa de clics",
                        "Tasa de conversión",
                        "Engagement post-comunicación",
                        "Opt-out rate"
                    ],
                    "calendar": {
                        "monday": "Email educativo",
                        "wednesday": "Actualización de producto",
                        "friday": "Contenido de comunidad"
                    }
                }
        
        return CommunicationManagementOutput(
            response=response_text,
            communication_plan=plan_json
        )

class WebSearchSkill(GoogleADKSkill):
    name = "web_search"
    description = "Realiza búsquedas en la web para encontrar información relevante"
    input_schema = WebSearchInput
    output_schema = WebSearchOutput
    
    async def handler(self, input_data: WebSearchInput) -> WebSearchOutput:
        """Implementación de la skill de búsqueda web"""
        query = input_data.query
        
        # Extraer la consulta real (eliminar la palabra clave inicial)
        search_keywords = ["busca", "search", "find", "investiga", "research", "encuentra", "lookup"]
        actual_query = query
        for keyword in search_keywords:
            if query.lower().startswith(keyword + " "):
                actual_query = query[len(keyword) + 1:].strip()
                break
                
        if not actual_query or actual_query == query:
            actual_query = query
            logger.warning("No se pudo extraer la consulta de búsqueda específica, usando el texto completo.")
        
        try:
            logger.info(f"Invocando herramienta 'search_web' con query: '{actual_query}'")
            
            # Obtener MCP toolkit del agente
            mcp_toolkit = self.agent.mcp_toolkit
            
            # Invocar la herramienta de búsqueda web
            search_results = await mcp_toolkit.invoke("search_web", query=actual_query)
            
            if search_results and search_results.get("results"): 
                formatted_response = f"Aquí tienes algunos resultados de la búsqueda web para '{actual_query}':\n\n"
                for i, result in enumerate(search_results["results"][:5]):
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
            search_results = None
        
        return WebSearchOutput(
            response=response_content,
            search_results=search_results.get("results") if search_results else None
        )

class GeneralRequestSkill(GoogleADKSkill):
    name = "general_request"
    description = "Maneja consultas generales relacionadas con éxito del cliente"
    input_schema = GeneralRequestInput
    output_schema = GeneralRequestOutput
    
    async def handler(self, input_data: GeneralRequestInput) -> GeneralRequestOutput:
        """Implementación de la skill de consultas generales"""
        query = input_data.query
        context = input_data.context or {}
        
        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en éxito del cliente y construcción de comunidades.
        
        El usuario ha realizado la siguiente consulta sobre comunidad o éxito del cliente:
        "{query}"
        
        Proporciona una respuesta detallada y útil, adaptada específicamente a esta consulta.
        Incluye información relevante, mejores prácticas, y recomendaciones concretas.
        """
        
        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client
        
        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.5)
        
        return GeneralRequestOutput(
            response=response_text
        )

class ClientSuccessLiaison(ADKAgent):
    """
    Agente especializado en comunidad y éxito del cliente.
    
    Este agente se encarga de facilitar la construcción de comunidad, mejorar la experiencia del usuario,
    proporcionar soporte personalizado, diseñar programas de fidelización, y gestionar la comunicación
    para maximizar la satisfacción y retención de los clientes.
    """
    
    def __init__(self, 
                 gemini_client: Optional[GeminiClient] = None,
                 supabase_client: Optional[SupabaseClient] = None,
                 state_manager = None,
                 adk_toolkit: Optional[Toolkit] = None,
                 a2a_server_url: Optional[str] = None):
        
        # Definir las skills del agente
        skills = [
            CommunityBuildingSkill(),
            UserExperienceSkill(),
            CustomerSupportSkill(),
            RetentionStrategySkill(),
            CommunicationManagementSkill(),
            WebSearchSkill(),
            GeneralRequestSkill()
        ]
        
        # Definir capacidades según el protocolo ADK
        capabilities = [
            "community_building", 
            "user_experience", 
            "customer_support", 
            "retention_strategies", 
            "communication_management",
            "information_retrieval",
            "database_query"
        ]
        
        # Inicializar clientes si no se proporcionan
        self.gemini_client = gemini_client if gemini_client else GeminiClient(model_name="gemini-1.5-flash")
        self.supabase_client = supabase_client if supabase_client else SupabaseClient()
        self.mcp_toolkit = MCPToolkit()
        
        # Definir instrucciones del sistema
        system_instructions = """
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
        
        # Ejemplos para la Agent Card
        examples = [
            Example(
                input={"message": "¿Cómo puedo construir una comunidad activa alrededor de mi app de fitness?"},
                output={"response": "Para construir una comunidad activa alrededor de tu app de fitness, te recomiendo implementar estas estrategias..."}
            ),
            Example(
                input={"message": "Estamos teniendo problemas con la retención de usuarios después del primer mes"},
                output={"response": "Para mejorar la retención de usuarios después del primer mes, considera implementar estas estrategias..."}
            ),
            Example(
                input={"message": "¿Qué métricas debo seguir para evaluar la salud de mi comunidad?"},
                output={"response": "Las métricas clave para evaluar la salud de tu comunidad incluyen..."}
            )
        ]
        
        # Crear Agent Card
        agent_card = AgentCard.create_standard_card(
            agent_id="client_success_liaison",
            name="NGX Community & Client-Success Liaison",
            description="Especialista en construcción de comunidad, optimización de experiencia de usuario, soporte al cliente, estrategias de retención y gestión de comunicaciones. Diseña e implementa programas para maximizar la satisfacción, engagement y retención de clientes.",
            capabilities=capabilities,
            skills=[skill.name for skill in skills],
            version="1.5.0",
            examples=examples,
            metadata={
                "model": "gemini-1.5-flash",
                "creator": "NGX Team",
                "last_updated": time.strftime("%Y-%m-%d")
            }
        )
        
        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="client_success_liaison",
            name="NGX Community & Client-Success Liaison",
            description="Especialista en construcción de comunidad, optimización de experiencia de usuario, soporte al cliente, estrategias de retención y gestión de comunicaciones. Diseña e implementa programas para maximizar la satisfacción, engagement y retención de clientes.",
            model="gemini-1.5-flash",
            instruction=system_instructions,
            capabilities=capabilities,
            gemini_client=self.gemini_client,
            supabase_client=self.supabase_client,
            state_manager=state_manager,
            adk_toolkit=adk_toolkit,
            a2a_server_url=a2a_server_url,
            version="1.5.0",
            agent_card=agent_card,
            skills=skills
        )
        
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
        
        logger.info(f"ClientSuccessLiaison inicializado con {len(capabilities)} capacidades y {len(skills)} skills")
    
    async def _get_context(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el adaptador del StateManager.
        
        Args:
            user_id: ID del usuario
            session_id: ID de la sesión
            
        Returns:
            Dict[str, Any]: Contexto de la conversación
        """
        try:
            # Intentar cargar el contexto desde el adaptador del StateManager
            context = await state_manager_adapter.load_state(user_id, session_id)
            
            if not context:
                logger.info(f"No se encontró contexto en adaptador del StateManager para user_id={user_id}, session_id={session_id}. Creando nuevo contexto.")
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
                logger.info(f"Contexto cargado desde adaptador del StateManager para user_id={user_id}, session_id={session_id}")
            
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
        Actualiza el contexto de la conversación en el adaptador del StateManager.
        
        Args:
            context: Contexto actualizado
            user_id: ID del usuario
            session_id: ID de la sesión
        """
        try:
            # Actualizar la marca de tiempo
            context["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Guardar el contexto en el adaptador del StateManager
            await state_manager_adapter.save_state(user_id, session_id, context)
            logger.info(f"Contexto actualizado en adaptador del StateManager para user_id={user_id}, session_id={session_id}")
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)
    
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
    
    def _classify_query(self, query: str) -> str:
        """
        Clasifica el tipo de consulta del usuario.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            str: Tipo de consulta clasificada
        """
        query_lower = query.lower()
        search_keywords = ["busca", "search", "find", "investiga", "research", "encuentra", "lookup"]
        
        if any(query_lower.startswith(keyword + " ") for keyword in search_keywords):
             return "web_search"
        # Prioritize search detection before other keywords that might overlap

        elif any(word in query_lower for word in ["comunidad", "grupo", "miembros", "pertenencia", "embajador", "foro"]):
            return "community_building"
        elif any(word in query_lower for word in ["experiencia", "usabilidad", "interfaz", "onboarding", "journey", "ux"]):
            return "user_experience"
        elif any(word in query_lower for word in ["soporte", "ayuda", "problema", "dificultad", "resolver", "ticket"]):
            return "customer_support"
        elif any(word in query_lower for word in ["retención", "fidelización", "abandono", "reactivar", "churn", "loyalty"]):
            return "retention_strategies"
        elif any(word in query_lower for word in ["comunicación", "mensaje", "email", "notificación", "contacto", "campaña"]):
            return "communication_management"
        else:
            return "general_request"
    
    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo ADK oficial.
        
        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()
    
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
        logger.info(f"Ejecutando ClientSuccessLiaison con input: {input_text[:50]}...")
        
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
                logger.info(f"Perfil no encontrado en contexto para {user_id}. Consultando Supabase vía MCP.")
                try:
                    # Construir la consulta SQL
                    sql_query = f"SELECT * FROM user_profiles WHERE user_id = '{user_id}' LIMIT 1;"
                    # Invocar la herramienta MCP de Supabase
                    query_result = await self.mcp_toolkit.invoke("supabase/query", sql=sql_query)
                    
                    # Procesar el resultado
                    if query_result and isinstance(query_result, list) and len(query_result) > 0:
                        user_profile = query_result[0] 
                        logger.info(f"Perfil obtenido de Supabase para {user_id}.")
                        context["user_profile"] = user_profile
                    else:
                         logger.warning(f"No se encontró perfil en Supabase para {user_id} o resultado inesperado: {query_result}")
                         user_profile = {}
                         context["user_profile"] = {}
                         
                except Exception as e:
                     logger.error(f"Error al consultar perfil de usuario {user_id} vía MCP: {e}", exc_info=True)
                     user_profile = {}
                     context["user_profile"] = {}
        
        # Clasificar el tipo de consulta
        query_type = self._classify_query(input_text)
        capabilities_used = []
        
        # Procesar la consulta según su tipo utilizando las skills ADK
        if query_type == "community_building":
            # Usar la skill de construcción de comunidad
            community_skill = next((skill for skill in self.skills if skill.name == "community_building"), None)
            if community_skill:
                input_data = CommunityBuildingInput(
                    query=input_text,
                    community_data=context.get("community_data", {})
                )
                result = await community_skill.handler(input_data)
                response = result.response
                capabilities_used.append("community_building")
                
                # Actualizar contexto con el plan de comunidad
                context["calendars"].append({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "query": input_text,
                    "community_plan": result.community_plan
                })
                
        elif query_type == "user_experience":
            # Usar la skill de experiencia de usuario
            experience_skill = next((skill for skill in self.skills if skill.name == "user_experience"), None)
            if experience_skill:
                input_data = UserExperienceInput(
                    query=input_text,
                    experience_data=context.get("experience_data", {})
                )
                result = await experience_skill.handler(input_data)
                response = result.response
                capabilities_used.append("user_experience")
                
                # Actualizar contexto con el journey map
                if result.journey_map:
                    context["journey_maps"].append({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "journey_map": result.journey_map
                    })
                
        elif query_type == "customer_support":
            # Usar la skill de soporte al cliente
            support_skill = next((skill for skill in self.skills if skill.name == "customer_support"), None)
            if support_skill:
                input_data = CustomerSupportInput(
                    query=input_text,
                    problem_details=context.get("problem_details", {})
                )
                result = await support_skill.handler(input_data)
                response = result.response
                capabilities_used.append("customer_support")
                
                # Actualizar contexto con el ticket de soporte
                if result.ticket:
                    context["support_requests"].append({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "ticket": result.ticket
                    })
                
        elif query_type == "retention_strategies":
            # Usar la skill de estrategias de retención
            retention_skill = next((skill for skill in self.skills if skill.name == "retention_strategies"), None)
            if retention_skill:
                input_data = RetentionStrategyInput(
                    query=input_text,
                    retention_data=context.get("retention_data", {})
                )
                result = await retention_skill.handler(input_data)
                response = result.response
                capabilities_used.append("retention_strategies")
                
        elif query_type == "communication_management":
            # Usar la skill de gestión de comunicación
            communication_skill = next((skill for skill in self.skills if skill.name == "communication_management"), None)
            if communication_skill:
                input_data = CommunicationManagementInput(
                    query=input_text,
                    communication_details=context.get("communication_details", {})
                )
                result = await communication_skill.handler(input_data)
                response = result.response
                capabilities_used.append("communication_management")
                
        elif query_type == "web_search":
            # Usar la skill de búsqueda web
            web_search_skill = next((skill for skill in self.skills if skill.name == "web_search"), None)
            if web_search_skill:
                input_data = WebSearchInput(
                    query=input_text
                )
                result = await web_search_skill.handler(input_data)
                response = result.response
                capabilities_used.append("information_retrieval")
                
        else:  # general_request
            # Usar la skill de consultas generales
            general_skill = next((skill for skill in self.skills if skill.name == "general_request"), None)
            if general_skill:
                input_data = GeneralRequestInput(
                    query=input_text,
                    context=context
                )
                result = await general_skill.handler(input_data)
                response = result.response
                capabilities_used.append("customer_support")
        
        # Actualizar el historial de conversación
        context["conversation_history"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "role": "user",
            "content": input_text
        })
        context["conversation_history"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "role": "assistant",
            "content": response
        })
        
        # Actualizar el contexto en el StateManager
        if user_id:
            await self._update_context(context, user_id, session_id)
        
        # Calcular tiempo de ejecución
        execution_time = time.time() - start_time
        logger.info(f"ClientSuccessLiaison completó la ejecución en {execution_time:.2f} segundos")
        
        # Preparar respuesta según el protocolo ADK
        return {
            "response": response,
            "capabilities_used": capabilities_used,
            "metadata": {
                "query_type": query_type,
                "execution_time": execution_time,
                "session_id": session_id
            }
        }

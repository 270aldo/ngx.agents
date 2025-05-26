import uuid
import time
from typing import Dict, Any, Optional, List
import os
import datetime
from google.cloud import aiplatform
from pydantic import BaseModel, Field

from adk.toolkit import Toolkit
from adk.agent import Skill as GoogleADKSkill
from clients.gemini_client import GeminiClient
from clients.supabase_client import SupabaseClient
from tools.mcp_toolkit import MCPToolkit
from agents.base.adk_agent import ADKAgent
from core.agent_card import AgentCard, Example
from infrastructure.adapters.state_manager_adapter import state_manager_adapter
from core.logging_config import get_logger
from core.vision_processor import VisionProcessor
from infrastructure.adapters.vision_adapter import VisionAdapter
from infrastructure.adapters.multimodal_adapter import MultimodalAdapter

# Configurar logger
logger = get_logger(__name__)


# Definir esquemas de entrada y salida para las skills
class IntegrationRequestInput(BaseModel):
    query: str = Field(
        ..., description="Consulta del usuario sobre integración de sistemas"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class IntegrationRequestOutput(BaseModel):
    response: str = Field(
        ..., description="Respuesta detallada sobre integración de sistemas"
    )
    systems: List[str] = Field(
        ..., description="Sistemas identificados para integración"
    )
    integration_report: Optional[Dict[str, Any]] = Field(
        None, description="Informe de integración estructurado"
    )


class AutomationRequestInput(BaseModel):
    query: str = Field(
        ...,
        description="Consulta del usuario sobre automatización de flujos de trabajo",
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class AutomationRequestOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre automatización")
    automation_plan: Optional[Dict[str, Any]] = Field(
        None, description="Plan de automatización estructurado"
    )


class ApiRequestInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre gestión de APIs")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class ApiRequestOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre gestión de APIs")
    apis: List[str] = Field(..., description="APIs identificadas")
    api_guide: Optional[Dict[str, Any]] = Field(
        None, description="Guía de API estructurada"
    )


class InfrastructureRequestInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre infraestructura")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class InfrastructureRequestOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre infraestructura")
    infrastructure_report: Optional[Dict[str, Any]] = Field(
        None, description="Informe de infraestructura estructurado"
    )


class DataPipelineRequestInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre pipelines de datos")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class DataPipelineRequestOutput(BaseModel):
    response: str = Field(
        ..., description="Respuesta detallada sobre pipelines de datos"
    )
    pipeline_design: Optional[Dict[str, Any]] = Field(
        None, description="Diseño de pipeline estructurado"
    )


class GeneralRequestInput(BaseModel):
    query: str = Field(..., description="Consulta general del usuario")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class GeneralRequestOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada a la consulta general")


# Esquemas para capacidades de visión
class VisualSystemAnalysisInput(BaseModel):
    query: str = Field(
        ..., description="Consulta del usuario sobre análisis visual de sistemas"
    )
    image_data: str = Field(..., description="Datos de la imagen en formato base64")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class VisualSystemAnalysisOutput(BaseModel):
    analysis_id: str = Field(..., description="ID único del análisis")
    response: str = Field(
        ..., description="Respuesta detallada del análisis visual de sistemas"
    )
    analysis_summary: str = Field(..., description="Resumen del análisis")
    system_components: List[Dict[str, Any]] = Field(
        ..., description="Componentes del sistema identificados"
    )
    integration_points: List[Dict[str, Any]] = Field(
        ..., description="Puntos de integración identificados"
    )
    recommendations: List[str] = Field(
        ..., description="Recomendaciones basadas en el análisis visual"
    )
    confidence_score: float = Field(
        ..., description="Puntuación de confianza del análisis"
    )


class VisualIntegrationVerificationInput(BaseModel):
    query: str = Field(
        ..., description="Consulta del usuario sobre verificación visual de integración"
    )
    image_data: str = Field(..., description="Datos de la imagen en formato base64")
    integration_type: Optional[str] = Field(
        None, description="Tipo de integración a verificar"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class VisualIntegrationVerificationOutput(BaseModel):
    verification_id: str = Field(..., description="ID único de la verificación")
    response: str = Field(
        ..., description="Respuesta detallada de la verificación visual de integración"
    )
    verification_summary: str = Field(..., description="Resumen de la verificación")
    integration_status: Dict[str, Any] = Field(
        ..., description="Estado de la integración verificada"
    )
    issues_detected: List[Dict[str, Any]] = Field(
        ..., description="Problemas detectados en la integración"
    )
    recommendations: List[str] = Field(
        ..., description="Recomendaciones para mejorar la integración"
    )
    confidence_score: float = Field(
        ..., description="Puntuación de confianza de la verificación"
    )


class VisualDataFlowAnalysisInput(BaseModel):
    query: str = Field(
        ..., description="Consulta del usuario sobre análisis visual de flujo de datos"
    )
    image_data: str = Field(..., description="Datos de la imagen en formato base64")
    flow_type: Optional[str] = Field(
        None, description="Tipo de flujo de datos a analizar"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class VisualDataFlowAnalysisOutput(BaseModel):
    analysis_id: str = Field(..., description="ID único del análisis")
    response: str = Field(
        ..., description="Respuesta detallada del análisis visual de flujo de datos"
    )
    analysis_summary: str = Field(..., description="Resumen del análisis")
    data_flow_components: List[Dict[str, Any]] = Field(
        ..., description="Componentes del flujo de datos identificados"
    )
    bottlenecks: List[Dict[str, Any]] = Field(
        ..., description="Cuellos de botella identificados"
    )
    optimization_suggestions: List[str] = Field(
        ..., description="Sugerencias de optimización"
    )
    confidence_score: float = Field(
        ..., description="Puntuación de confianza del análisis"
    )


# Definir las skills como clases que heredan de GoogleADKSkill
class IntegrationRequestSkill(GoogleADKSkill):
    name = "integration_request"
    description = "Maneja consultas relacionadas con integración de sistemas"
    input_schema = IntegrationRequestInput
    output_schema = IntegrationRequestOutput

    async def handler(
        self, input_data: IntegrationRequestInput
    ) -> IntegrationRequestOutput:
        """Implementación de la skill de integración de sistemas"""
        query = input_data.query
        context = input_data.context or {}

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
        """

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)

        # Crear informe de integración como artefacto
        integration_report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "integration_request",
            "query": query,
            "systems": systems,
            "integration_summary": "Análisis de integración de sistemas completado",
            "response": response_text,
        }

        return IntegrationRequestOutput(
            response=response_text,
            systems=systems,
            integration_report=integration_report,
        )


class AutomationRequestSkill(GoogleADKSkill):
    name = "automation_request"
    description = (
        "Maneja consultas relacionadas con automatización de flujos de trabajo"
    )
    input_schema = AutomationRequestInput
    output_schema = AutomationRequestOutput

    async def handler(
        self, input_data: AutomationRequestInput
    ) -> AutomationRequestOutput:
        """Implementación de la skill de automatización de flujos de trabajo"""
        query = input_data.query
        context = input_data.context or {}

        # Construir el prompt para el modelo
        prompt = f"""
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
        """

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)

        # Crear plan de automatización como artefacto
        automation_plan = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "automation_request",
            "query": query,
            "automation_summary": "Plan de automatización generado",
            "response": response_text,
        }

        return AutomationRequestOutput(
            response=response_text, automation_plan=automation_plan
        )


class ApiRequestSkill(GoogleADKSkill):
    name = "api_request"
    description = "Maneja consultas relacionadas con gestión de APIs"
    input_schema = ApiRequestInput
    output_schema = ApiRequestOutput

    async def handler(self, input_data: ApiRequestInput) -> ApiRequestOutput:
        """Implementación de la skill de gestión de APIs"""
        query = input_data.query
        context = input_data.context or {}

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
        """

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)

        # Crear guía de API como artefacto
        api_guide = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "api_request",
            "query": query,
            "apis": apis,
            "guide_summary": "Guía de APIs generada",
            "response": response_text,
        }

        return ApiRequestOutput(response=response_text, apis=apis, api_guide=api_guide)


class InfrastructureRequestSkill(GoogleADKSkill):
    name = "infrastructure_request"
    description = "Maneja consultas relacionadas con optimización de infraestructura"
    input_schema = InfrastructureRequestInput
    output_schema = InfrastructureRequestOutput

    async def handler(
        self, input_data: InfrastructureRequestInput
    ) -> InfrastructureRequestOutput:
        """Implementación de la skill de optimización de infraestructura"""
        query = input_data.query
        context = input_data.context or {}

        # Construir el prompt para el modelo
        prompt = f"""
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
        """

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)

        # Crear informe de infraestructura como artefacto
        infrastructure_report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "infrastructure_request",
            "query": query,
            "report_summary": "Informe de infraestructura generado",
            "response": response_text,
        }

        return InfrastructureRequestOutput(
            response=response_text, infrastructure_report=infrastructure_report
        )


class DataPipelineRequestSkill(GoogleADKSkill):
    name = "data_pipeline_request"
    description = "Maneja consultas relacionadas con diseño de pipelines de datos"
    input_schema = DataPipelineRequestInput
    output_schema = DataPipelineRequestOutput

    async def handler(
        self, input_data: DataPipelineRequestInput
    ) -> DataPipelineRequestOutput:
        """Implementación de la skill de diseño de pipelines de datos"""
        query = input_data.query
        context = input_data.context or {}

        # Construir el prompt para el modelo
        prompt = f"""
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
        """

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)

        # Crear diseño de pipeline como artefacto
        pipeline_design = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_type": "data_pipeline_request",
            "query": query,
            "design_summary": "Diseño de pipeline de datos generado",
            "response": response_text,
        }

        return DataPipelineRequestOutput(
            response=response_text, pipeline_design=pipeline_design
        )


class GeneralRequestSkill(GoogleADKSkill):
    name = "general_request"
    description = "Maneja consultas generales relacionadas con integración de sistemas y automatización"
    input_schema = GeneralRequestInput
    output_schema = GeneralRequestOutput

    async def handler(self, input_data: GeneralRequestInput) -> GeneralRequestOutput:
        """Implementación de la skill de consultas generales"""
        query = input_data.query
        context = input_data.context or {}

        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en integración de sistemas y automatización operativa.
        
        El usuario ha realizado la siguiente consulta sobre integración de sistemas o automatización:
        "{query}"
        
        Proporciona una respuesta detallada y útil, adaptada específicamente a esta consulta.
        Incluye información relevante, mejores prácticas, y recomendaciones concretas.
        """

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.5)

        return GeneralRequestOutput(response=response_text)


# Skills para capacidades de visión
class VisualSystemAnalysisSkill(GoogleADKSkill):
    name = "visual_system_analysis"
    description = "Analiza visualmente diagramas y capturas de sistemas para identificar componentes y puntos de integración"
    input_schema = VisualSystemAnalysisInput
    output_schema = VisualSystemAnalysisOutput

    async def handler(
        self, input_data: VisualSystemAnalysisInput
    ) -> VisualSystemAnalysisOutput:
        """Implementación de la skill de análisis visual de sistemas"""
        query = input_data.query
        image_data = input_data.image_data
        context = input_data.context or {}

        # Verificar si las capacidades de visión están disponibles
        if (
            not hasattr(self.agent, "_vision_capabilities_available")
            or not self.agent._vision_capabilities_available
        ):
            logger.warning(
                "Capacidades de visión no disponibles. Usando análisis simulado."
            )
            return self._generate_mock_system_analysis(input_data)

        try:
            # Utilizar el procesador de visión para analizar la imagen
            vision_result = await self.agent.vision_processor.analyze_image(image_data)

            # Construir el prompt para el análisis detallado
            prompt = f"""
            Eres un experto en integración de sistemas y arquitectura tecnológica.
            
            Analiza esta imagen con la siguiente consulta:
            "{query}"
            
            Descripción de la imagen según el análisis inicial:
            {vision_result.get('text', 'No disponible')}
            
            Proporciona un análisis detallado del sistema mostrado en la imagen que incluya:
            1. Resumen del sistema visualizado
            2. Componentes principales identificados
            3. Puntos de integración entre componentes
            4. Posibles cuellos de botella o áreas de mejora
            5. Recomendaciones para optimizar la integración
            
            Estructura tu análisis de forma clara y accionable.
            """

            # Obtener cliente Gemini del agente
            gemini_client = self.agent.gemini_client

            # Generar análisis utilizando Gemini
            analysis_text = await gemini_client.generate_response(
                prompt, temperature=0.4
            )

            # Extraer elementos estructurados del análisis
            extraction_prompt = f"""
            Basándote en el siguiente análisis de un sistema visualizado en una imagen:
            
            {analysis_text}
            
            Extrae y estructura la siguiente información en formato JSON:
            1. analysis_summary: resumen conciso del análisis del sistema
            2. system_components: lista de componentes del sistema identificados (array de objetos con "name", "type" y "description")
            3. integration_points: lista de puntos de integración identificados (array de objetos con "source", "target" y "integration_type")
            4. recommendations: lista de recomendaciones para mejorar la integración (array de strings)
            5. confidence_score: puntuación de confianza del análisis (0-1)
            
            Devuelve SOLO el JSON, sin explicaciones adicionales.
            """

            structured_data = await gemini_client.generate_structured_output(
                extraction_prompt
            )

            # Generar ID único para el análisis
            analysis_id = str(uuid.uuid4())

            # Crear respuesta estructurada
            return VisualSystemAnalysisOutput(
                analysis_id=analysis_id,
                response=analysis_text,
                analysis_summary=structured_data.get(
                    "analysis_summary", "Análisis visual de sistema"
                ),
                system_components=structured_data.get(
                    "system_components",
                    [
                        {
                            "name": "Componente genérico",
                            "type": "desconocido",
                            "description": "No se identificaron componentes específicos",
                        }
                    ],
                ),
                integration_points=structured_data.get(
                    "integration_points",
                    [
                        {
                            "source": "Componente A",
                            "target": "Componente B",
                            "integration_type": "desconocido",
                        }
                    ],
                ),
                recommendations=structured_data.get(
                    "recommendations", ["Realizar un análisis más detallado"]
                ),
                confidence_score=structured_data.get("confidence_score", 0.7),
            )

        except Exception as e:
            logger.error(f"Error en análisis visual de sistema: {e}", exc_info=True)
            return self._generate_mock_system_analysis(input_data)

    def _generate_mock_system_analysis(
        self, input_data: VisualSystemAnalysisInput
    ) -> VisualSystemAnalysisOutput:
        """Genera un análisis simulado cuando las capacidades de visión no están disponibles"""
        analysis_id = str(uuid.uuid4())

        return VisualSystemAnalysisOutput(
            analysis_id=analysis_id,
            response="No se pudo realizar un análisis detallado del sistema en la imagen. Por favor, proporciona una descripción textual de lo que muestra la imagen para poder ayudarte mejor.",
            analysis_summary="Análisis simulado de sistema en imagen",
            system_components=[
                {
                    "name": "Componente desconocido",
                    "type": "no identificado",
                    "description": "No se pudo analizar el contenido específico",
                }
            ],
            integration_points=[
                {
                    "source": "Componente A",
                    "target": "Componente B",
                    "integration_type": "no identificado",
                }
            ],
            recommendations=[
                "Proporcionar una descripción textual del sistema",
                "Intentar nuevamente cuando las capacidades de visión estén disponibles",
                "Realizar un análisis manual del sistema",
            ],
            confidence_score=0.1,
        )


class VisualIntegrationVerificationSkill(GoogleADKSkill):
    name = "visual_integration_verification"
    description = "Verifica visualmente la integración entre sistemas mediante el análisis de capturas de pantalla o diagramas"
    input_schema = VisualIntegrationVerificationInput
    output_schema = VisualIntegrationVerificationOutput

    async def handler(
        self, input_data: VisualIntegrationVerificationInput
    ) -> VisualIntegrationVerificationOutput:
        """Implementación de la skill de verificación visual de integración"""
        query = input_data.query
        image_data = input_data.image_data
        integration_type = input_data.integration_type or "No especificado"
        context = input_data.context or {}

        # Verificar si las capacidades de visión están disponibles
        if (
            not hasattr(self.agent, "_vision_capabilities_available")
            or not self.agent._vision_capabilities_available
        ):
            logger.warning(
                "Capacidades de visión no disponibles. Usando verificación simulada."
            )
            return self._generate_mock_integration_verification(input_data)

        try:
            # Utilizar el procesador de visión para analizar la imagen
            vision_result = await self.agent.vision_processor.analyze_image(image_data)

            # Construir el prompt para el análisis detallado
            prompt = f"""
            Eres un experto en integración de sistemas y verificación de conexiones entre aplicaciones.
            
            Analiza esta imagen con la siguiente consulta:
            "{query}"
            
            Tipo de integración a verificar: {integration_type}
            
            Descripción de la imagen según el análisis inicial:
            {vision_result.get('text', 'No disponible')}
            
            Proporciona una verificación detallada de la integración mostrada en la imagen que incluya:
            1. Resumen del estado de la integración
            2. Estado de la conexión (exitosa, fallida, parcial)
            3. Problemas detectados (si los hay)
            4. Recomendaciones para mejorar o solucionar problemas
            5. Nivel de confianza en la verificación
            
            Estructura tu verificación de forma clara y accionable.
            """

            # Obtener cliente Gemini del agente
            gemini_client = self.agent.gemini_client

            # Generar análisis utilizando Gemini
            verification_text = await gemini_client.generate_response(
                prompt, temperature=0.4
            )

            # Extraer elementos estructurados del análisis
            extraction_prompt = f"""
            Basándote en la siguiente verificación de integración:
            
            {verification_text}
            
            Extrae y estructura la siguiente información en formato JSON:
            1. verification_summary: resumen conciso de la verificación
            2. integration_status: objeto con "status" (exitosa/fallida/parcial), "connection_type", "timestamp"
            3. issues_detected: lista de problemas detectados (array de objetos con "issue_type", "description", "severity")
            4. recommendations: lista de recomendaciones para mejorar la integración (array de strings)
            5. confidence_score: puntuación de confianza de la verificación (0-1)
            
            Devuelve SOLO el JSON, sin explicaciones adicionales.
            """

            structured_data = await gemini_client.generate_structured_output(
                extraction_prompt
            )

            # Generar ID único para la verificación
            verification_id = str(uuid.uuid4())

            # Crear respuesta estructurada
            return VisualIntegrationVerificationOutput(
                verification_id=verification_id,
                response=verification_text,
                verification_summary=structured_data.get(
                    "verification_summary", "Verificación visual de integración"
                ),
                integration_status=structured_data.get(
                    "integration_status",
                    {
                        "status": "desconocido",
                        "connection_type": integration_type,
                        "timestamp": datetime.datetime.now().isoformat(),
                    },
                ),
                issues_detected=structured_data.get(
                    "issues_detected",
                    [
                        {
                            "issue_type": "desconocido",
                            "description": "No se identificaron problemas específicos",
                            "severity": "baja",
                        }
                    ],
                ),
                recommendations=structured_data.get(
                    "recommendations", ["Realizar una verificación más detallada"]
                ),
                confidence_score=structured_data.get("confidence_score", 0.7),
            )

        except Exception as e:
            logger.error(
                f"Error en verificación visual de integración: {e}", exc_info=True
            )
            return self._generate_mock_integration_verification(input_data)

    def _generate_mock_integration_verification(
        self, input_data: VisualIntegrationVerificationInput
    ) -> VisualIntegrationVerificationOutput:
        """Genera una verificación simulada cuando las capacidades de visión no están disponibles"""
        verification_id = str(uuid.uuid4())
        integration_type = input_data.integration_type or "No especificado"

        return VisualIntegrationVerificationOutput(
            verification_id=verification_id,
            response="No se pudo realizar una verificación detallada de la integración en la imagen. Por favor, proporciona una descripción textual de lo que muestra la imagen para poder ayudarte mejor.",
            verification_summary="Verificación simulada de integración en imagen",
            integration_status={
                "status": "desconocido",
                "connection_type": integration_type,
                "timestamp": datetime.datetime.now().isoformat(),
            },
            issues_detected=[
                {
                    "issue_type": "verificación_limitada",
                    "description": "No se pudo analizar el contenido específico",
                    "severity": "media",
                }
            ],
            recommendations=[
                "Proporcionar una descripción textual de la integración",
                "Intentar nuevamente cuando las capacidades de visión estén disponibles",
                "Realizar una verificación manual de la integración",
            ],
            confidence_score=0.1,
        )


class VisualDataFlowAnalysisSkill(GoogleADKSkill):
    name = "visual_data_flow_analysis"
    description = "Analiza visualmente diagramas de flujo de datos para identificar componentes, relaciones y posibles optimizaciones"
    input_schema = VisualDataFlowAnalysisInput
    output_schema = VisualDataFlowAnalysisOutput

    async def handler(
        self, input_data: VisualDataFlowAnalysisInput
    ) -> VisualDataFlowAnalysisOutput:
        """Implementación de la skill de análisis visual de flujo de datos"""
        query = input_data.query
        image_data = input_data.image_data
        flow_type = input_data.flow_type or "No especificado"
        context = input_data.context or {}

        # Verificar si las capacidades de visión están disponibles
        if (
            not hasattr(self.agent, "_vision_capabilities_available")
            or not self.agent._vision_capabilities_available
        ):
            logger.warning(
                "Capacidades de visión no disponibles. Usando análisis simulado."
            )
            return self._generate_mock_data_flow_analysis(input_data)

        try:
            # Utilizar el procesador de visión para analizar la imagen
            vision_result = await self.agent.vision_processor.analyze_image(image_data)

            # Construir el prompt para el análisis detallado
            prompt = f"""
            Eres un experto en arquitectura de datos y análisis de flujos de datos.
            
            Analiza esta imagen con la siguiente consulta:
            "{query}"
            
            Tipo de flujo de datos a analizar: {flow_type}
            
            Descripción de la imagen según el análisis inicial:
            {vision_result.get('text', 'No disponible')}
            
            Proporciona un análisis detallado del flujo de datos mostrado en la imagen que incluya:
            1. Resumen del flujo de datos
            2. Componentes principales identificados
            3. Relaciones y dependencias entre componentes
            4. Cuellos de botella o áreas de ineficiencia
            5. Sugerencias de optimización
            
            Estructura tu análisis de forma clara y accionable.
            """

            # Obtener cliente Gemini del agente
            gemini_client = self.agent.gemini_client

            # Generar análisis utilizando Gemini
            analysis_text = await gemini_client.generate_response(
                prompt, temperature=0.4
            )

            # Extraer elementos estructurados del análisis
            extraction_prompt = f"""
            Basándote en el siguiente análisis de flujo de datos:
            
            {analysis_text}
            
            Extrae y estructura la siguiente información en formato JSON:
            1. analysis_summary: resumen conciso del análisis del flujo de datos
            2. data_flow_components: lista de componentes del flujo de datos (array de objetos con "name", "type", "description", "role")
            3. bottlenecks: lista de cuellos de botella identificados (array de objetos con "component", "issue", "impact")
            4. optimization_suggestions: lista de sugerencias de optimización (array de strings)
            5. confidence_score: puntuación de confianza del análisis (0-1)
            
            Devuelve SOLO el JSON, sin explicaciones adicionales.
            """

            structured_data = await gemini_client.generate_structured_output(
                extraction_prompt
            )

            # Generar ID único para el análisis
            analysis_id = str(uuid.uuid4())

            # Crear respuesta estructurada
            return VisualDataFlowAnalysisOutput(
                analysis_id=analysis_id,
                response=analysis_text,
                analysis_summary=structured_data.get(
                    "analysis_summary", "Análisis visual de flujo de datos"
                ),
                data_flow_components=structured_data.get(
                    "data_flow_components",
                    [
                        {
                            "name": "Componente genérico",
                            "type": "desconocido",
                            "description": "No se identificaron componentes específicos",
                            "role": "desconocido",
                        }
                    ],
                ),
                bottlenecks=structured_data.get(
                    "bottlenecks",
                    [
                        {
                            "component": "No identificado",
                            "issue": "No se identificaron cuellos de botella específicos",
                            "impact": "desconocido",
                        }
                    ],
                ),
                optimization_suggestions=structured_data.get(
                    "optimization_suggestions", ["Realizar un análisis más detallado"]
                ),
                confidence_score=structured_data.get("confidence_score", 0.7),
            )

        except Exception as e:
            logger.error(
                f"Error en análisis visual de flujo de datos: {e}", exc_info=True
            )
            return self._generate_mock_data_flow_analysis(input_data)

    def _generate_mock_data_flow_analysis(
        self, input_data: VisualDataFlowAnalysisInput
    ) -> VisualDataFlowAnalysisOutput:
        """Genera un análisis simulado cuando las capacidades de visión no están disponibles"""
        analysis_id = str(uuid.uuid4())
        flow_type = input_data.flow_type or "No especificado"

        return VisualDataFlowAnalysisOutput(
            analysis_id=analysis_id,
            response="No se pudo realizar un análisis detallado del flujo de datos en la imagen. Por favor, proporciona una descripción textual de lo que muestra la imagen para poder ayudarte mejor.",
            analysis_summary="Análisis simulado de flujo de datos en imagen",
            data_flow_components=[
                {
                    "name": "Componente desconocido",
                    "type": "no identificado",
                    "description": "No se pudo analizar el contenido específico",
                    "role": "desconocido",
                }
            ],
            bottlenecks=[
                {
                    "component": "No identificado",
                    "issue": "No se pudieron identificar cuellos de botella",
                    "impact": "desconocido",
                }
            ],
            optimization_suggestions=[
                "Proporcionar una descripción textual del flujo de datos",
                "Intentar nuevamente cuando las capacidades de visión estén disponibles",
                "Realizar un análisis manual del flujo de datos",
            ],
            confidence_score=0.1,
        )


class SystemsIntegrationOps(ADKAgent):
    """
    Agente especializado en integración de sistemas y automatización.

    Este agente se encarga de facilitar la integración de diferentes sistemas,
    automatizar flujos de trabajo, gestionar conexiones con APIs externas,
    y optimizar la infraestructura tecnológica para mejorar la eficiencia operativa.
    """

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        supabase_client: Optional[SupabaseClient] = None,
        state_manager=None,
        adk_toolkit: Optional[Toolkit] = None,
        a2a_server_url: Optional[str] = None,
    ):

        # Definir las skills del agente
        skills = [
            IntegrationRequestSkill(),
            AutomationRequestSkill(),
            ApiRequestSkill(),
            InfrastructureRequestSkill(),
            DataPipelineRequestSkill(),
            GeneralRequestSkill(),
            # Añadir skills de visión
            VisualSystemAnalysisSkill(),
            VisualIntegrationVerificationSkill(),
            VisualDataFlowAnalysisSkill(),
        ]

        # Definir capacidades según el protocolo ADK
        capabilities = [
            "systems_integration",
            "workflow_automation",
            "api_management",
            "infrastructure_optimization",
            "data_pipeline_design",
        ]

        # Inicializar clientes si no se proporcionan
        self.gemini_client = (
            gemini_client
            if gemini_client
            else GeminiClient(model_name="gemini-2.0-flash")
        )
        self.supabase_client = supabase_client if supabase_client else SupabaseClient()
        self.mcp_toolkit = MCPToolkit()

        # Definir instrucciones del sistema
        system_instructions = """
        Eres NGX Systems Integration & Ops, un experto en integración de sistemas y automatización operativa.
        
        Tu objetivo es facilitar la integración fluida de diferentes sistemas,
        automatizar procesos, gestionar conexiones con APIs externas,
        y optimizar la infraestructura tecnológica para mejorar la eficiencia operativa en las siguientes áreas:
        
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

        # Ejemplos para la Agent Card
        examples = [
            Example(
                input={
                    "message": "Necesito integrar mi aplicación de fitness con Apple Health"
                },
                output={
                    "response": "Para integrar tu aplicación con Apple Health, necesitarás implementar HealthKit API..."
                },
            ),
            Example(
                input={
                    "message": "¿Cómo puedo automatizar el envío de notificaciones a mis usuarios?"
                },
                output={
                    "response": "Para automatizar notificaciones, te recomiendo implementar un sistema de eventos..."
                },
            ),
            Example(
                input={
                    "message": "¿Qué arquitectura recomendarías para una app de fitness con millones de usuarios?"
                },
                output={
                    "response": "Para una app de fitness a gran escala, recomendaría una arquitectura de microservicios..."
                },
            ),
        ]

        # Crear Agent Card
        agent_card = AgentCard.create_standard_card(
            agent_id="systems_integration_ops",
            name="NGX Systems Integration & Ops",
            description="Especialista en integración de sistemas y automatización operativa. Facilita la integración de diferentes sistemas, automatiza flujos de trabajo, gestiona conexiones con APIs externas, y optimiza la infraestructura tecnológica.",
            capabilities=capabilities,
            skills=[skill.name for skill in skills],
            version="1.5.0",
            examples=examples,
            metadata={
                "model": "gemini-2.0-flash",
                "creator": "NGX Team",
                "last_updated": time.strftime("%Y-%m-%d"),
            },
        )

        # Inicializar agente base con los parámetros definidos
        super().__init__(
            agent_id="systems_integration_ops",
            name="NGX Systems Integration & Ops",
            description="Especialista en integración de sistemas y automatización operativa",
            model="gemini-2.0-flash",
            instruction=system_instructions,
            capabilities=capabilities,
            gemini_client=self.gemini_client,
            supabase_client=self.supabase_client,
            state_manager=state_manager,
            adk_toolkit=adk_toolkit,
            a2a_server_url=a2a_server_url,
            version="1.5.0",
            agent_card=agent_card,
            skills=skills,
        )

        # Inicialización de AI Platform
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        try:
            logger.info(
                f"Inicializando AI Platform con Proyecto: {gcp_project_id}, Región: {gcp_region}"
            )
            aiplatform.init(project=gcp_project_id, location=gcp_region)
            logger.info("AI Platform inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al inicializar AI Platform: {e}", exc_info=True)

        # Inicializar estado del agente
        self.update_state(
            "integration_requests", {}
        )  # Almacenar solicitudes de integración
        self.update_state(
            "automation_requests", {}
        )  # Almacenar solicitudes de automatización
        self.update_state("api_requests", {})  # Almacenar solicitudes de API
        self.update_state(
            "infrastructure_requests", {}
        )  # Almacenar solicitudes de infraestructura
        self.update_state(
            "data_pipeline_requests", {}
        )  # Almacenar solicitudes de pipeline de datos

        # Inicializar componentes de visión y multimodales
        try:
            # Inicializar adaptador de visión
            vision_adapter = VisionAdapter()

            # Inicializar procesador de visión
            self.vision_processor = VisionProcessor(vision_adapter)

            # Inicializar adaptador multimodal
            self.multimodal_adapter = MultimodalAdapter()

            # Establecer bandera de capacidades de visión disponibles
            self._vision_capabilities_available = True

            logger.info(
                f"Capacidades de visión inicializadas correctamente para el agente {self.agent_id}"
            )
        except Exception as e:
            logger.error(
                f"Error al inicializar capacidades de visión: {e}", exc_info=True
            )
            self._vision_capabilities_available = False
            logger.warning(
                f"El agente {self.agent_id} funcionará sin capacidades de visión"
            )

        logger.info(
            f"SystemsIntegrationOps inicializado con {len(capabilities)} capacidades y {len(skills)} skills"
        )

    async def _get_context(
        self, user_id: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene el contexto de la conversación desde el StateManager.

        Args:
            user_id: ID del usuario
            session_id: ID de la sesión

        Returns:
            Dict[str, Any]: Contexto de la conversación
        """
        try:
            # Intentar cargar el contexto desde el adaptador del StateManager
            context = await state_manager_adapter.load_state(user_id, session_id)

            if not context or not context.get("state_data"):
                logger.info(
                    f"No se encontró contexto en el adaptador del StateManager para user_id={user_id}, session_id={session_id}. Creando nuevo contexto."
                )
                # Si no hay contexto, crear uno nuevo
                context = {
                    "conversation_history": [],
                    "user_profile": {},
                    "integration_requests": [],
                    "automation_requests": [],
                    "api_requests": [],
                    "infrastructure_requests": [],
                    "data_pipeline_requests": [],
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            else:
                # Si hay contexto, usar el state_data
                context = context.get("state_data", {})
                logger.info(
                    f"Contexto cargado desde el adaptador del StateManager para user_id={user_id}, session_id={session_id}"
                )

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
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

    async def _update_context(
        self, context: Dict[str, Any], user_id: str, session_id: str
    ) -> None:
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

            # Guardar el contexto en el adaptador del StateManager
            await state_manager_adapter.save_state(user_id, session_id, context)
            logger.info(
                f"Contexto actualizado en el adaptador del StateManager para user_id={user_id}, session_id={session_id}"
            )
        except Exception as e:
            logger.error(f"Error al actualizar contexto: {e}", exc_info=True)

    async def _consult_other_agent(
        self,
        agent_id: str,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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
                "additional_context": context or {},
            }

            # Llamar al agente utilizando el adaptador de A2A
            response = await a2a_adapter.call_agent(
                agent_id=agent_id, user_input=query, context=task_context
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
                "agent_name": agent_id,
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

        if any(
            word in query_lower
            for word in [
                "integrar",
                "integración",
                "conectar",
                "sincronizar",
                "interoperabilidad",
            ]
        ):
            return "integration_request"
        elif any(
            word in query_lower
            for word in [
                "automatizar",
                "automatización",
                "workflow",
                "flujo de trabajo",
                "proceso",
            ]
        ):
            return "automation_request"
        elif any(
            word in query_lower
            for word in ["api", "endpoint", "webhook", "interfaz", "servicio web"]
        ):
            return "api_request"
        elif any(
            word in query_lower
            for word in [
                "infraestructura",
                "arquitectura",
                "rendimiento",
                "escalabilidad",
                "servidor",
            ]
        ):
            return "infrastructure_request"
        elif any(
            word in query_lower
            for word in ["pipeline", "datos", "etl", "procesamiento", "flujo de datos"]
        ):
            return "data_pipeline_request"
        else:
            return "general_request"

    def get_agent_card(self) -> Dict[str, Any]:
        """
        Obtiene el Agent Card del agente según el protocolo ADK oficial.

        Returns:
            Dict[str, Any]: Agent Card estandarizada
        """
        return self.agent_card.to_dict()

    async def _run_async_impl(
        self, input_text: str, user_id: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
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
        logger.info(f"Ejecutando SystemsIntegrationOps con input: {input_text[:50]}...")

        # Obtener session_id de los kwargs o generar uno nuevo
        session_id = kwargs.get("session_id", str(uuid.uuid4()))

        # Obtener el contexto de la conversación
        context = await self._get_context(user_id, session_id) if user_id else {}

        # Clasificar el tipo de consulta
        query_type = self._classify_query(input_text)
        capabilities_used = []

        # Procesar la consulta según su tipo utilizando las skills ADK
        if query_type == "integration_request":
            # Usar la skill de integración de sistemas
            integration_skill = next(
                (skill for skill in self.skills if skill.name == "integration_request"),
                None,
            )
            if integration_skill:
                input_data = IntegrationRequestInput(query=input_text, context=context)
                result = await integration_skill.handler(input_data)
                response = result.response
                capabilities_used.append("systems_integration")

                # Actualizar contexto con el informe de integración
                if result.integration_report:
                    context["integration_requests"].append(
                        {
                            "timestamp": datetime.datetime.now().isoformat(),
                            "query": input_text,
                            "systems": result.systems,
                            "integration_report": result.integration_report,
                        }
                    )

        elif query_type == "automation_request":
            # Usar la skill de automatización de flujos de trabajo
            automation_skill = next(
                (skill for skill in self.skills if skill.name == "automation_request"),
                None,
            )
            if automation_skill:
                input_data = AutomationRequestInput(query=input_text, context=context)
                result = await automation_skill.handler(input_data)
                response = result.response
                capabilities_used.append("workflow_automation")

                # Actualizar contexto con el plan de automatización
                if result.automation_plan:
                    context["automation_requests"].append(
                        {
                            "timestamp": datetime.datetime.now().isoformat(),
                            "query": input_text,
                            "automation_plan": result.automation_plan,
                        }
                    )

        elif query_type == "api_request":
            # Usar la skill de gestión de APIs
            api_skill = next(
                (skill for skill in self.skills if skill.name == "api_request"), None
            )
            if api_skill:
                input_data = ApiRequestInput(query=input_text, context=context)
                result = await api_skill.handler(input_data)
                response = result.response
                capabilities_used.append("api_management")

                # Actualizar contexto con la guía de API
                if result.api_guide:
                    context["api_requests"].append(
                        {
                            "timestamp": datetime.datetime.now().isoformat(),
                            "query": input_text,
                            "apis": result.apis,
                            "api_guide": result.api_guide,
                        }
                    )

        elif query_type == "infrastructure_request":
            # Usar la skill de optimización de infraestructura
            infrastructure_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "infrastructure_request"
                ),
                None,
            )
            if infrastructure_skill:
                input_data = InfrastructureRequestInput(
                    query=input_text, context=context
                )
                result = await infrastructure_skill.handler(input_data)
                response = result.response
                capabilities_used.append("infrastructure_optimization")

                # Actualizar contexto con el informe de infraestructura
                if result.infrastructure_report:
                    context["infrastructure_requests"].append(
                        {
                            "timestamp": datetime.datetime.now().isoformat(),
                            "query": input_text,
                            "infrastructure_report": result.infrastructure_report,
                        }
                    )

        elif query_type == "data_pipeline_request":
            # Usar la skill de diseño de pipelines de datos
            pipeline_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "data_pipeline_request"
                ),
                None,
            )
            if pipeline_skill:
                input_data = DataPipelineRequestInput(query=input_text, context=context)
                result = await pipeline_skill.handler(input_data)
                response = result.response
                capabilities_used.append("data_pipeline_design")

                # Actualizar contexto con el diseño de pipeline
                if result.pipeline_design:
                    context["data_pipeline_requests"].append(
                        {
                            "timestamp": datetime.datetime.now().isoformat(),
                            "query": input_text,
                            "pipeline_design": result.pipeline_design,
                        }
                    )

        else:  # general_request
            # Usar la skill de consultas generales
            general_skill = next(
                (skill for skill in self.skills if skill.name == "general_request"),
                None,
            )
            if general_skill:
                input_data = GeneralRequestInput(query=input_text, context=context)
                result = await general_skill.handler(input_data)
                response = result.response
                capabilities_used.append("systems_integration")

        # Actualizar el historial de conversación
        context["conversation_history"].append(
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "role": "user",
                "content": input_text,
            }
        )
        context["conversation_history"].append(
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "role": "assistant",
                "content": response,
            }
        )

        # Actualizar el contexto en el StateManager
        if user_id:
            await self._update_context(context, user_id, session_id)

        # Calcular tiempo de ejecución
        execution_time = time.time() - start_time
        logger.info(
            f"SystemsIntegrationOps completó la ejecución en {execution_time:.2f} segundos"
        )

        # Preparar respuesta según el protocolo ADK
        return {
            "response": response,
            "capabilities_used": capabilities_used,
            "metadata": {
                "query_type": query_type,
                "execution_time": execution_time,
                "session_id": session_id,
            },
        }

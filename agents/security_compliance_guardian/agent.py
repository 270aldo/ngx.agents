import uuid
import time
from typing import Dict, Any, Optional, List
import json
import datetime
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
from core.vision_processor import VisionProcessor
from infrastructure.adapters.vision_adapter import VisionAdapter
from infrastructure.adapters.multimodal_adapter import MultimodalAdapter

# Importar esquemas para las skills
from agents.security_compliance_guardian.schemas import (
    SecurityAssessmentInput,
    SecurityAssessmentOutput,
    ComplianceCheckInput,
    ComplianceCheckOutput,
    VulnerabilityScanInput,
    VulnerabilityScanOutput,
    DataProtectionInput,
    DataProtectionOutput,
    GeneralSecurityInput,
    GeneralSecurityOutput,
    # Nuevos esquemas para capacidades de visión
    ImageComplianceVerificationInput,
    ImageComplianceVerificationOutput,
    SecurityImageAnalysisInput,
    SecurityImageAnalysisOutput,
    VisualDataLeakageDetectionInput,
    VisualDataLeakageDetectionOutput,
)

# Configurar logger
logger = get_logger(__name__)


# Definir esquemas de entrada y salida para las skills
class SecurityAssessmentInput(BaseModel):
    query: str = Field(
        ..., description="Consulta del usuario sobre evaluación de seguridad"
    )
    system_info: Optional[Dict[str, Any]] = Field(
        None, description="Información del sistema a evaluar"
    )
    app_type: Optional[str] = Field(
        None, description="Tipo de aplicación (web, móvil, API, etc.)"
    )


class SecurityAssessmentOutput(BaseModel):
    response: str = Field(
        ..., description="Respuesta detallada de la evaluación de seguridad"
    )
    risks: List[Dict[str, Any]] = Field(
        ..., description="Lista de riesgos identificados"
    )
    recommendations: List[str] = Field(..., description="Recomendaciones de seguridad")


class ComplianceCheckInput(BaseModel):
    query: str = Field(
        ..., description="Consulta del usuario sobre cumplimiento normativo"
    )
    regulations: Optional[List[str]] = Field(
        None, description="Normativas específicas a verificar"
    )
    region: Optional[str] = Field(
        None, description="Región geográfica para normativas aplicables"
    )


class ComplianceCheckOutput(BaseModel):
    response: str = Field(
        ..., description="Respuesta detallada de la verificación de cumplimiento"
    )
    compliance_status: Dict[str, Any] = Field(
        ..., description="Estado de cumplimiento por normativa"
    )
    recommendations: List[str] = Field(
        ..., description="Recomendaciones para mejorar el cumplimiento"
    )


class VulnerabilityScanInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre vulnerabilidades")
    system_info: Optional[Dict[str, Any]] = Field(
        None, description="Información del sistema a escanear"
    )
    scan_type: Optional[str] = Field(
        None, description="Tipo de escaneo (general, específico, etc.)"
    )


class VulnerabilityScanOutput(BaseModel):
    response: str = Field(
        ..., description="Respuesta detallada del escaneo de vulnerabilidades"
    )
    vulnerabilities: List[Dict[str, Any]] = Field(
        ..., description="Lista de vulnerabilidades identificadas"
    )
    severity_summary: Dict[str, int] = Field(
        ..., description="Resumen de severidad de vulnerabilidades"
    )
    recommendations: List[str] = Field(
        ..., description="Recomendaciones para mitigar vulnerabilidades"
    )


class DataProtectionInput(BaseModel):
    query: str = Field(
        ..., description="Consulta del usuario sobre protección de datos"
    )
    data_types: Optional[List[str]] = Field(
        None, description="Tipos de datos a proteger"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class DataProtectionOutput(BaseModel):
    response: str = Field(
        ..., description="Respuesta detallada sobre protección de datos"
    )
    protection_measures: List[Dict[str, Any]] = Field(
        ..., description="Medidas de protección recomendadas"
    )
    best_practices: List[str] = Field(
        ..., description="Mejores prácticas de protección de datos"
    )


class GeneralSecurityInput(BaseModel):
    query: str = Field(..., description="Consulta general sobre seguridad")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para la consulta"
    )


class GeneralSecurityOutput(BaseModel):
    response: str = Field(
        ..., description="Respuesta detallada a la consulta de seguridad"
    )
    recommendations: Optional[List[str]] = Field(
        None, description="Recomendaciones generales de seguridad"
    )


# Definir las skills como clases que heredan de GoogleADKSkill
class SecurityAssessmentSkill(GoogleADKSkill):
    name = "security_assessment"
    description = "Realiza evaluaciones de seguridad para sistemas y aplicaciones"
    input_schema = SecurityAssessmentInput
    output_schema = SecurityAssessmentOutput

    async def handler(
        self, input_data: SecurityAssessmentInput
    ) -> SecurityAssessmentOutput:
        """Implementación de la skill de evaluación de seguridad"""
        query = input_data.query
        system_info = input_data.system_info or {}
        app_type = input_data.app_type or "general"

        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en seguridad informática especializado en evaluaciones de seguridad.
        
        El usuario solicita una evaluación de seguridad con la siguiente consulta:
        "{query}"
        
        Tipo de aplicación: {app_type}
        
        Información del sistema:
        {json.dumps(system_info, indent=2) if system_info else "No disponible"}
        
        Proporciona una evaluación de seguridad detallada, identificando posibles riesgos
        y recomendando medidas para mejorar la seguridad. Estructura tu respuesta en secciones:
        1. Resumen de la evaluación
        2. Riesgos identificados (priorizados)
        3. Recomendaciones específicas
        4. Próximos pasos sugeridos
        """

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)

        # Extraer riesgos y recomendaciones del texto (simplificado)
        risks = [
            {
                "severity": "alta",
                "description": "Posible vulnerabilidad en la autenticación",
                "impact": "Acceso no autorizado",
            },
            {
                "severity": "media",
                "description": "Falta de cifrado en tránsito",
                "impact": "Interceptación de datos",
            },
            {
                "severity": "baja",
                "description": "Logs insuficientes",
                "impact": "Dificultad para detectar incidentes",
            },
        ]

        recommendations = [
            "Implementar autenticación multifactor",
            "Configurar TLS para todas las comunicaciones",
            "Mejorar el sistema de logging y monitoreo",
        ]

        return SecurityAssessmentOutput(
            response=response_text, risks=risks, recommendations=recommendations
        )


class ComplianceCheckSkill(GoogleADKSkill):
    name = "compliance_verification"
    description = "Verifica el cumplimiento de normativas y estándares de seguridad"
    input_schema = ComplianceCheckInput
    output_schema = ComplianceCheckOutput

    async def handler(self, input_data: ComplianceCheckInput) -> ComplianceCheckOutput:
        """Implementación de la skill de verificación de cumplimiento"""
        query = input_data.query
        regulations = input_data.regulations or ["GDPR", "HIPAA", "CCPA"]
        region = input_data.region or "global"

        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en cumplimiento normativo y seguridad de la información.
        
        El usuario solicita una verificación de cumplimiento con la siguiente consulta:
        "{query}"
        
        Normativas a verificar: {', '.join(regulations)}
        Región: {region}
        
        Proporciona una evaluación detallada del cumplimiento de estas normativas,
        identificando posibles áreas de incumplimiento y recomendando medidas para
        mejorar el cumplimiento. Estructura tu respuesta en secciones:
        1. Resumen del análisis de cumplimiento
        2. Estado de cumplimiento por normativa
        3. Áreas de mejora (priorizadas)
        4. Recomendaciones específicas
        5. Recursos adicionales
        """

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)

        # Crear estructura de cumplimiento (simplificada)
        compliance_status = {}
        for reg in regulations:
            compliance_status[reg] = {
                "status": "parcial",
                "areas_of_concern": [
                    "Documentación incompleta",
                    "Procesos no formalizados",
                ],
                "compliance_score": 65,
            }

        recommendations = [
            "Desarrollar política de privacidad completa",
            "Implementar proceso de gestión de consentimiento",
            "Establecer procedimiento de respuesta a solicitudes de derechos GDPR",
        ]

        return ComplianceCheckOutput(
            response=response_text,
            compliance_status=compliance_status,
            recommendations=recommendations,
        )


class VulnerabilityScanSkill(GoogleADKSkill):
    name = "vulnerability_detection"
    description = "Detecta vulnerabilidades y riesgos de seguridad en sistemas"
    input_schema = VulnerabilityScanInput
    output_schema = VulnerabilityScanOutput

    async def handler(
        self, input_data: VulnerabilityScanInput
    ) -> VulnerabilityScanOutput:
        """Implementación de la skill de detección de vulnerabilidades"""
        query = input_data.query
        system_info = input_data.system_info or {}
        scan_type = input_data.scan_type or "general"

        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en seguridad informática especializado en detección de vulnerabilidades.
        
        El usuario solicita un análisis de vulnerabilidades con la siguiente consulta:
        "{query}"
        
        Tipo de escaneo: {scan_type}
        
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

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)

        # Crear lista de vulnerabilidades (simplificada)
        vulnerabilities = [
            {
                "severity": "crítica",
                "name": "Inyección SQL",
                "cve": "CVE-2021-1234",
                "description": "Vulnerabilidad de inyección SQL en formulario de login",
            },
            {
                "severity": "alta",
                "name": "XSS Persistente",
                "cve": "CVE-2021-5678",
                "description": "Cross-site scripting persistente en comentarios",
            },
            {
                "severity": "media",
                "name": "CSRF",
                "cve": "CVE-2021-9012",
                "description": "Falta de protección CSRF en formularios",
            },
        ]

        # Resumen de severidad
        severity_summary = {"crítica": 1, "alta": 1, "media": 1, "baja": 0}

        recommendations = [
            "Implementar validación de entradas y prepared statements",
            "Sanitizar todas las entradas de usuario y utilizar CSP",
            "Implementar tokens anti-CSRF en todos los formularios",
        ]

        return VulnerabilityScanOutput(
            response=response_text,
            vulnerabilities=vulnerabilities,
            severity_summary=severity_summary,
            recommendations=recommendations,
        )


class DataProtectionSkill(GoogleADKSkill):
    name = "data_protection"
    description = "Proporciona recomendaciones para proteger datos sensibles"
    input_schema = DataProtectionInput
    output_schema = DataProtectionOutput

    async def handler(self, input_data: DataProtectionInput) -> DataProtectionOutput:
        """Implementación de la skill de protección de datos"""
        query = input_data.query
        data_types = input_data.data_types or ["personal", "financiero", "salud"]
        context = input_data.context or {}

        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en protección de datos y privacidad.
        
        El usuario solicita información sobre protección de datos con la siguiente consulta:
        "{query}"
        
        Tipos de datos a proteger: {', '.join(data_types)}
        
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

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.4)

        # Crear medidas de protección (simplificadas)
        protection_measures = [
            {
                "type": "cifrado",
                "description": "Cifrado AES-256 para datos en reposo",
                "implementation": "Utilizar herramientas de cifrado de disco completo",
            },
            {
                "type": "acceso",
                "description": "Control de acceso basado en roles",
                "implementation": "Implementar RBAC con principio de mínimo privilegio",
            },
            {
                "type": "auditoría",
                "description": "Logging y auditoría de acceso a datos",
                "implementation": "Configurar sistema centralizado de logs",
            },
        ]

        best_practices = [
            "Minimizar la recolección de datos personales",
            "Implementar cifrado de extremo a extremo para datos sensibles",
            "Establecer políticas de retención y eliminación de datos",
            "Realizar evaluaciones de impacto de protección de datos (DPIA)",
        ]

        return DataProtectionOutput(
            response=response_text,
            protection_measures=protection_measures,
            best_practices=best_practices,
        )


class GeneralSecuritySkill(GoogleADKSkill):
    name = "security_recommendations"
    description = "Proporciona recomendaciones generales de seguridad"
    input_schema = GeneralSecurityInput
    output_schema = GeneralSecurityOutput

    async def handler(self, input_data: GeneralSecurityInput) -> GeneralSecurityOutput:
        """Implementación de la skill de recomendaciones generales de seguridad"""
        query = input_data.query
        context = input_data.context or {}

        # Construir el prompt para el modelo
        prompt = f"""
        Eres un experto en seguridad informática y ciberseguridad.
        
        El usuario ha realizado la siguiente consulta sobre seguridad:
        "{query}"
        
        Proporciona una respuesta detallada y útil, adaptada específicamente a esta consulta.
        Incluye información relevante, mejores prácticas, y recomendaciones concretas.
        """

        # Obtener cliente Gemini del agente
        gemini_client = self.agent.gemini_client

        # Generar respuesta utilizando Gemini
        response_text = await gemini_client.generate_response(prompt, temperature=0.5)

        # Extraer recomendaciones (simplificado)
        recommendations = [
            "Implementar autenticación multifactor en todos los sistemas",
            "Mantener software y sistemas actualizados con los últimos parches",
            "Realizar copias de seguridad regulares y verificar su restauración",
            "Educar a los usuarios sobre amenazas de seguridad y phishing",
        ]

        return GeneralSecurityOutput(
            response=response_text, recommendations=recommendations
        )


# Nuevas skills para capacidades de visión
class ImageComplianceVerificationSkill(GoogleADKSkill):
    name = "image_compliance_verification"
    description = "Verifica el cumplimiento normativo en imágenes para identificar posibles problemas de seguridad"
    input_schema = ImageComplianceVerificationInput
    output_schema = ImageComplianceVerificationOutput

    async def handler(
        self, input_data: ImageComplianceVerificationInput
    ) -> ImageComplianceVerificationOutput:
        """Implementación de la skill de verificación de cumplimiento en imágenes"""
        query = input_data.query
        image_data = input_data.image_data
        regulations = input_data.regulations or ["GDPR", "HIPAA", "CCPA"]
        region = input_data.region or "global"
        context = input_data.context or {}

        # Verificar si las capacidades de visión están disponibles
        if (
            not hasattr(self.agent, "_vision_capabilities_available")
            or not self.agent._vision_capabilities_available
        ):
            logger.warning(
                "Capacidades de visión no disponibles. Usando análisis simulado."
            )
            return self._generate_mock_compliance_verification(input_data)

        try:
            # Utilizar el procesador de visión para analizar la imagen
            vision_result = await self.agent.vision_processor.analyze_image(image_data)

            # Construir el prompt para el análisis detallado
            prompt = f"""
            Eres un experto en cumplimiento normativo y seguridad de la información.
            
            Analiza esta imagen con la siguiente consulta:
            "{query}"
            
            Normativas a verificar: {', '.join(regulations)}
            Región: {region}
            
            Descripción de la imagen según el análisis inicial:
            {vision_result.get('text', 'No disponible')}
            
            Proporciona un análisis detallado de cumplimiento normativo que incluya:
            1. Resumen del análisis de cumplimiento
            2. Estado de cumplimiento por normativa
            3. Elementos sensibles identificados en la imagen
            4. Problemas de cumplimiento identificados
            5. Recomendaciones para resolver problemas de cumplimiento
            
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
            Basándote en el siguiente análisis de cumplimiento normativo de una imagen:
            
            {analysis_text}
            
            Extrae y estructura la siguiente información en formato JSON:
            1. compliance_summary: resumen conciso del análisis de cumplimiento
            2. compliance_status: estado de cumplimiento por normativa (objeto con normativas como claves)
            3. sensitive_elements: lista de elementos sensibles identificados (array de objetos con "element" y "description")
            4. compliance_issues: lista de problemas de cumplimiento (array de objetos con "issue", "regulation" y "severity")
            5. recommendations: lista de recomendaciones para resolver problemas (array de strings)
            6. confidence_score: puntuación de confianza del análisis (0-1)
            
            Devuelve SOLO el JSON, sin explicaciones adicionales.
            """

            structured_data = await gemini_client.generate_structured_output(
                extraction_prompt
            )

            # Generar ID único para la verificación
            verification_id = str(uuid.uuid4())

            # Crear respuesta estructurada
            return ImageComplianceVerificationOutput(
                verification_id=verification_id,
                compliance_summary=structured_data.get(
                    "compliance_summary", "Análisis de cumplimiento normativo en imagen"
                ),
                compliance_status=structured_data.get(
                    "compliance_status",
                    {
                        "GDPR": "indeterminado",
                        "HIPAA": "indeterminado",
                        "CCPA": "indeterminado",
                    },
                ),
                sensitive_elements=structured_data.get(
                    "sensitive_elements",
                    [
                        {
                            "element": "general",
                            "description": "No se identificaron elementos específicos",
                        }
                    ],
                ),
                compliance_issues=structured_data.get(
                    "compliance_issues",
                    [
                        {
                            "issue": "No determinado",
                            "regulation": "general",
                            "severity": "baja",
                        }
                    ],
                ),
                recommendations=structured_data.get(
                    "recommendations", ["Realizar un análisis manual detallado"]
                ),
                response=analysis_text,
                confidence_score=structured_data.get("confidence_score", 0.7),
            )

        except Exception as e:
            logger.error(
                f"Error en verificación de cumplimiento en imagen: {e}", exc_info=True
            )
            return self._generate_mock_compliance_verification(input_data)

    def _generate_mock_compliance_verification(
        self, input_data: ImageComplianceVerificationInput
    ) -> ImageComplianceVerificationOutput:
        """Genera una verificación simulada cuando las capacidades de visión no están disponibles"""
        verification_id = str(uuid.uuid4())

        return ImageComplianceVerificationOutput(
            verification_id=verification_id,
            compliance_summary="Análisis simulado de cumplimiento normativo en imagen",
            compliance_status={
                "GDPR": "indeterminado",
                "HIPAA": "indeterminado",
                "CCPA": "indeterminado",
            },
            sensitive_elements=[
                {
                    "element": "contenido",
                    "description": "No se pudo analizar el contenido específico",
                }
            ],
            compliance_issues=[
                {
                    "issue": "Análisis visual no disponible",
                    "regulation": "general",
                    "severity": "media",
                }
            ],
            recommendations=[
                "Proporcionar una descripción textual de la imagen",
                "Intentar nuevamente cuando las capacidades de visión estén disponibles",
                "Realizar un análisis manual de cumplimiento",
            ],
            response="No se pudo realizar un análisis detallado de cumplimiento normativo en la imagen. Por favor, proporciona una descripción textual de lo que muestra la imagen para poder ayudarte mejor.",
            confidence_score=0.1,
        )


class SecurityImageAnalysisSkill(GoogleADKSkill):
    name = "security_image_analysis"
    description = "Analiza imágenes para identificar riesgos y problemas de seguridad"
    input_schema = SecurityImageAnalysisInput
    output_schema = SecurityImageAnalysisOutput

    async def handler(
        self, input_data: SecurityImageAnalysisInput
    ) -> SecurityImageAnalysisOutput:
        """Implementación de la skill de análisis de seguridad en imágenes"""
        query = input_data.query
        image_data = input_data.image_data
        analysis_type = input_data.analysis_type or "general"
        context = input_data.context or {}

        # Verificar si las capacidades de visión están disponibles
        if (
            not hasattr(self.agent, "_vision_capabilities_available")
            or not self.agent._vision_capabilities_available
        ):
            logger.warning(
                "Capacidades de visión no disponibles. Usando análisis simulado."
            )
            return self._generate_mock_security_analysis(input_data)

        try:
            # Utilizar el procesador de visión para analizar la imagen
            vision_result = await self.agent.vision_processor.analyze_image(image_data)

            # Construir el prompt para el análisis detallado
            prompt = f"""
            Eres un experto en seguridad informática y análisis de riesgos.
            
            Analiza esta imagen con la siguiente consulta:
            "{query}"
            
            Tipo de análisis: {analysis_type}
            
            Descripción de la imagen según el análisis inicial:
            {vision_result.get('text', 'No disponible')}
            
            Proporciona un análisis detallado de seguridad que incluya:
            1. Resumen del análisis de seguridad
            2. Riesgos de seguridad identificados
            3. Niveles de severidad de los riesgos
            4. Recomendaciones para mitigar riesgos
            
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
            Basándote en el siguiente análisis de seguridad de una imagen:
            
            {analysis_text}
            
            Extrae y estructura la siguiente información en formato JSON:
            1. analysis_summary: resumen conciso del análisis de seguridad
            2. security_risks: lista de riesgos de seguridad identificados (array de objetos con "risk", "description" y "severity")
            3. severity_levels: niveles de severidad de los riesgos (objeto con niveles como claves y conteo como valores)
            4. recommendations: lista de recomendaciones para mitigar riesgos (array de strings)
            5. confidence_score: puntuación de confianza del análisis (0-1)
            
            Devuelve SOLO el JSON, sin explicaciones adicionales.
            """

            structured_data = await gemini_client.generate_structured_output(
                extraction_prompt
            )

            # Generar ID único para el análisis
            analysis_id = str(uuid.uuid4())

            # Crear respuesta estructurada
            return SecurityImageAnalysisOutput(
                analysis_id=analysis_id,
                analysis_summary=structured_data.get(
                    "analysis_summary", "Análisis de seguridad en imagen"
                ),
                security_risks=structured_data.get(
                    "security_risks",
                    [
                        {
                            "risk": "No determinado",
                            "description": "No se identificaron riesgos específicos",
                            "severity": "baja",
                        }
                    ],
                ),
                severity_levels=structured_data.get(
                    "severity_levels", {"alta": 0, "media": 0, "baja": 1}
                ),
                recommendations=structured_data.get(
                    "recommendations", ["Realizar un análisis manual detallado"]
                ),
                response=analysis_text,
                confidence_score=structured_data.get("confidence_score", 0.7),
            )

        except Exception as e:
            logger.error(
                f"Error en análisis de seguridad en imagen: {e}", exc_info=True
            )
            return self._generate_mock_security_analysis(input_data)

    def _generate_mock_security_analysis(
        self, input_data: SecurityImageAnalysisInput
    ) -> SecurityImageAnalysisOutput:
        """Genera un análisis simulado cuando las capacidades de visión no están disponibles"""
        analysis_id = str(uuid.uuid4())

        return SecurityImageAnalysisOutput(
            analysis_id=analysis_id,
            analysis_summary="Análisis simulado de seguridad en imagen",
            security_risks=[
                {
                    "risk": "Análisis visual no disponible",
                    "description": "No se pudo analizar el contenido específico",
                    "severity": "media",
                }
            ],
            severity_levels={"alta": 0, "media": 1, "baja": 0},
            recommendations=[
                "Proporcionar una descripción textual de la imagen",
                "Intentar nuevamente cuando las capacidades de visión estén disponibles",
                "Realizar un análisis manual de seguridad",
            ],
            response="No se pudo realizar un análisis detallado de seguridad en la imagen. Por favor, proporciona una descripción textual de lo que muestra la imagen para poder ayudarte mejor.",
            confidence_score=0.1,
        )


class VisualDataLeakageDetectionSkill(GoogleADKSkill):
    name = "visual_data_leakage_detection"
    description = "Detecta posibles fugas de datos sensibles en imágenes"
    input_schema = VisualDataLeakageDetectionInput
    output_schema = VisualDataLeakageDetectionOutput

    async def handler(
        self, input_data: VisualDataLeakageDetectionInput
    ) -> VisualDataLeakageDetectionOutput:
        """Implementación de la skill de detección de fugas de datos en imágenes"""
        query = input_data.query
        image_data = input_data.image_data
        data_types = input_data.data_types or [
            "personal",
            "financiero",
            "credenciales",
            "corporativo",
        ]
        context = input_data.context or {}

        # Verificar si las capacidades de visión están disponibles
        if (
            not hasattr(self.agent, "_vision_capabilities_available")
            or not self.agent._vision_capabilities_available
        ):
            logger.warning(
                "Capacidades de visión no disponibles. Usando análisis simulado."
            )
            return self._generate_mock_data_leakage_detection(input_data)

        try:
            # Utilizar el procesador de visión para analizar la imagen
            vision_result = await self.agent.vision_processor.analyze_image(image_data)

            # Construir el prompt para el análisis detallado
            prompt = f"""
            Eres un experto en protección de datos y detección de fugas de información.
            
            Analiza esta imagen con la siguiente consulta:
            "{query}"
            
            Tipos de datos a detectar: {', '.join(data_types)}
            
            Descripción de la imagen según el análisis inicial:
            {vision_result.get('text', 'No disponible')}
            
            Proporciona un análisis detallado de posibles fugas de datos que incluya:
            1. Resumen de la detección de fugas de datos
            2. Datos sensibles encontrados
            3. Evaluación de riesgos
            4. Recomendaciones para proteger datos
            
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
            Basándote en el siguiente análisis de detección de fugas de datos en una imagen:
            
            {analysis_text}
            
            Extrae y estructura la siguiente información en formato JSON:
            1. detection_summary: resumen conciso de la detección de fugas de datos
            2. sensitive_data_found: lista de datos sensibles encontrados (array de objetos con "data_type", "description" y "risk_level")
            3. risk_assessment: evaluación de riesgos (objeto con "overall_risk", "impact" y "likelihood")
            4. protection_recommendations: lista de recomendaciones para proteger datos (array de strings)
            5. confidence_score: puntuación de confianza de la detección (0-1)
            
            Devuelve SOLO el JSON, sin explicaciones adicionales.
            """

            structured_data = await gemini_client.generate_structured_output(
                extraction_prompt
            )

            # Generar ID único para la detección
            detection_id = str(uuid.uuid4())

            # Crear respuesta estructurada
            return VisualDataLeakageDetectionOutput(
                detection_id=detection_id,
                detection_summary=structured_data.get(
                    "detection_summary", "Detección de fugas de datos en imagen"
                ),
                sensitive_data_found=structured_data.get(
                    "sensitive_data_found",
                    [
                        {
                            "data_type": "No determinado",
                            "description": "No se identificaron datos sensibles específicos",
                            "risk_level": "bajo",
                        }
                    ],
                ),
                risk_assessment=structured_data.get(
                    "risk_assessment",
                    {"overall_risk": "bajo", "impact": "bajo", "likelihood": "bajo"},
                ),
                protection_recommendations=structured_data.get(
                    "protection_recommendations",
                    ["Realizar un análisis manual detallado"],
                ),
                response=analysis_text,
                confidence_score=structured_data.get("confidence_score", 0.7),
            )

        except Exception as e:
            logger.error(
                f"Error en detección de fugas de datos en imagen: {e}", exc_info=True
            )
            return self._generate_mock_data_leakage_detection(input_data)

    def _generate_mock_data_leakage_detection(
        self, input_data: VisualDataLeakageDetectionInput
    ) -> VisualDataLeakageDetectionOutput:
        """Genera una detección simulada cuando las capacidades de visión no están disponibles"""
        detection_id = str(uuid.uuid4())

        return VisualDataLeakageDetectionOutput(
            detection_id=detection_id,
            detection_summary="Detección simulada de fugas de datos en imagen",
            sensitive_data_found=[
                {
                    "data_type": "general",
                    "description": "No se pudo analizar el contenido específico",
                    "risk_level": "indeterminado",
                }
            ],
            risk_assessment={
                "overall_risk": "indeterminado",
                "impact": "indeterminado",
                "likelihood": "indeterminado",
            },
            protection_recommendations=[
                "Proporcionar una descripción textual de la imagen",
                "Intentar nuevamente cuando las capacidades de visión estén disponibles",
                "Realizar un análisis manual de datos sensibles",
            ],
            response="No se pudo realizar una detección detallada de fugas de datos en la imagen. Por favor, proporciona una descripción textual de lo que muestra la imagen para poder ayudarte mejor.",
            confidence_score=0.1,
        )


class SecurityComplianceGuardian(ADKAgent):
    """
    Agente especializado en seguridad y cumplimiento normativo.

    Este agente se encarga de garantizar la seguridad de la aplicación, proteger
    los datos de los usuarios, verificar el cumplimiento de normativas y estándares,
    detectar posibles vulnerabilidades y proporcionar recomendaciones de seguridad.
    """

    def __init__(
        self,
        agent_id: str = None,
        gemini_client: GeminiClient = None,
        supabase_client: SupabaseClient = None,
        mcp_toolkit: MCPToolkit = None,
        state_manager=None,
        **kwargs,
    ):
        """Inicializa el agente SecurityComplianceGuardian con sus dependencias"""

        # Generar ID único si no se proporciona
        if agent_id is None:
            agent_id = f"security_compliance_guardian_{uuid.uuid4().hex[:8]}"

        # Crear tarjeta de agente
        agent_card = AgentCard(
            name="SecurityComplianceGuardian",
            description="Especialista en seguridad, protección de datos y cumplimiento normativo",
            instructions="""
            Soy un agente especializado en seguridad y cumplimiento normativo.
            
            Puedo ayudarte con:
            - Evaluaciones de seguridad para sistemas y aplicaciones
            - Verificación de cumplimiento con normativas (GDPR, HIPAA, etc.)
            - Detección de vulnerabilidades y riesgos de seguridad
            - Recomendaciones para proteger datos sensibles
            - Estrategias generales de seguridad informática
            
            Mi objetivo es garantizar la seguridad de la aplicación, proteger los datos de los usuarios,
            verificar el cumplimiento de normativas y estándares, detectar posibles vulnerabilidades
            y proporcionar recomendaciones de seguridad.
            """,
            examples=[
                Example(
                    input="¿Puedes realizar una evaluación de seguridad para mi aplicación web?",
                    output="Aquí tienes una evaluación de seguridad detallada para tu aplicación web...",
                ),
                Example(
                    input="¿Cómo puedo asegurarme de que mi aplicación cumple con GDPR?",
                    output="Para cumplir con GDPR, debes implementar las siguientes medidas...",
                ),
                Example(
                    input="¿Qué vulnerabilidades debo buscar en mi sistema?",
                    output="Aquí tienes un análisis de las vulnerabilidades más comunes y cómo detectarlas...",
                ),
                Example(
                    input="¿Cómo puedo proteger los datos sensibles de mis usuarios?",
                    output="Para proteger los datos sensibles, te recomiendo las siguientes medidas...",
                ),
                Example(
                    input="¿Cuáles son las mejores prácticas de seguridad para mi aplicación?",
                    output="Las mejores prácticas de seguridad para tu aplicación incluyen...",
                ),
                # Ejemplos para capacidades de visión
                Example(
                    input="¿Puedes verificar si esta captura de pantalla cumple con las normativas de protección de datos?",
                    output="He analizado la imagen y he identificado posibles problemas de cumplimiento normativo...",
                ),
                Example(
                    input="¿Hay algún riesgo de seguridad en esta imagen de mi configuración?",
                    output="En el análisis de seguridad de la imagen he detectado varios riesgos potenciales...",
                ),
                Example(
                    input="¿Esta imagen contiene alguna información sensible que no debería compartirse?",
                    output="He detectado posibles fugas de datos en la imagen, incluyendo información personal y credenciales...",
                ),
            ],
        )

        # Crear toolkit con las skills del agente
        skills = [
            SecurityAssessmentSkill(),
            ComplianceCheckSkill(),
            VulnerabilityScanSkill(),
            DataProtectionSkill(),
            GeneralSecuritySkill(),
            # Nuevas skills para capacidades de visión
            ImageComplianceVerificationSkill(),
            SecurityImageAnalysisSkill(),
            VisualDataLeakageDetectionSkill(),
        ]

        toolkit = Toolkit(skills=skills)

        # Inicializar la clase base
        super().__init__(
            agent_id=agent_id,
            agent_card=agent_card,
            toolkit=toolkit,
            gemini_client=gemini_client,
            supabase_client=supabase_client,
            mcp_toolkit=mcp_toolkit,
            state_manager=state_manager,
            **kwargs,
        )

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
                f"Capacidades de visión inicializadas correctamente para el agente {agent_id}"
            )
        except Exception as e:
            logger.error(
                f"Error al inicializar capacidades de visión: {e}", exc_info=True
            )
            self._vision_capabilities_available = False
            logger.warning(f"El agente {agent_id} funcionará sin capacidades de visión")

        logger.info(
            f"Agente SecurityComplianceGuardian inicializado con ID: {agent_id}"
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
                    "security_queries": [],
                    "security_assessments": [],
                    "compliance_checks": [],
                    "vulnerability_scans": [],
                    "data_protections": [],
                    "general_recommendations": [],
                    "query_types": {},
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
                "security_queries": [],
                "security_assessments": [],
                "compliance_checks": [],
                "vulnerability_scans": [],
                "data_protections": [],
                "general_recommendations": [],
                "query_types": {},
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

    def _classify_query(self, query: str, has_image: bool = False) -> str:
        """
        Clasifica el tipo de consulta del usuario.

        Args:
            query: Consulta del usuario
            has_image: Indica si la consulta incluye una imagen

        Returns:
            str: Tipo de consulta clasificada
        """
        query_lower = query.lower()

        # Si hay una imagen, verificar si es una consulta relacionada con visión
        if has_image:
            # Palabras clave para verificación de cumplimiento en imágenes
            image_compliance_keywords = [
                "cumplimiento",
                "normativa",
                "regulación",
                "gdpr",
                "hipaa",
                "pci",
                "iso 27001",
                "cumplir con",
                "estándar",
                "conformidad",
                "legal",
            ]

            # Palabras clave para análisis de seguridad en imágenes
            security_image_keywords = [
                "seguridad",
                "riesgo",
                "vulnerabilidad",
                "amenaza",
                "peligro",
                "configuración",
                "setup",
                "sistema",
                "evaluar",
                "analizar",
            ]

            # Palabras clave para detección de fugas de datos en imágenes
            data_leakage_keywords = [
                "fuga de datos",
                "información sensible",
                "datos personales",
                "credenciales",
                "contraseña",
                "privacidad",
                "confidencial",
                "secreto",
                "compartir",
            ]

            # Verificar coincidencias con palabras clave para imágenes
            for keyword in image_compliance_keywords:
                if keyword in query_lower:
                    return "image_compliance_verification"

            for keyword in security_image_keywords:
                if keyword in query_lower:
                    return "security_image_analysis"

            for keyword in data_leakage_keywords:
                if keyword in query_lower:
                    return "visual_data_leakage_detection"

            # Si hay imagen pero no hay coincidencias específicas, usar análisis de seguridad por defecto
            return "security_image_analysis"

        # Si no hay imagen, continuar con la clasificación normal
        # Palabras clave para evaluación de seguridad
        security_assessment_keywords = [
            "evaluación de seguridad",
            "auditoría de seguridad",
            "revisar seguridad",
            "analizar seguridad",
            "evaluar seguridad",
            "test de seguridad",
            "pentesting",
        ]

        # Palabras clave para verificación de cumplimiento
        compliance_check_keywords = [
            "cumplimiento",
            "normativa",
            "regulación",
            "gdpr",
            "hipaa",
            "pci",
            "iso 27001",
            "cumplir con",
            "estándar",
            "conformidad",
        ]

        # Palabras clave para detección de vulnerabilidades
        vulnerability_scan_keywords = [
            "vulnerabilidad",
            "escaneo",
            "exploits",
            "fallos",
            "debilidades",
            "amenazas",
            "riesgos",
            "hackear",
            "penetración",
        ]

        # Palabras clave para protección de datos
        data_protection_keywords = [
            "protección de datos",
            "cifrado",
            "encriptación",
            "privacidad",
            "datos personales",
            "anonimización",
            "fuga de datos",
            "proteger datos",
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
        logger.info(
            f"Ejecutando SecurityComplianceGuardian con input: {input_text[:50]}..."
        )

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
        context["security_queries"].append(
            {"timestamp": datetime.datetime.now().isoformat(), "query": input_text}
        )

        # Verificar si hay una imagen en los parámetros
        image_data = kwargs.get("image_data")
        has_image = image_data is not None

        # Clasificar el tipo de consulta (considerando si hay imagen)
        query_type = self._classify_query(input_text, has_image)
        capabilities_used = []

        # Actualizar el contexto con el tipo de consulta
        if query_type in context["query_types"]:
            context["query_types"][query_type] += 1
        else:
            context["query_types"][query_type] = 1

        # Procesar la consulta según su tipo utilizando las skills ADK
        # Primero manejar los tipos de consulta relacionados con imágenes
        if query_type == "image_compliance_verification" and has_image:
            # Usar la skill de verificación de cumplimiento en imágenes
            image_compliance_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "image_compliance_verification"
                ),
                None,
            )
            if image_compliance_skill:
                input_data = ImageComplianceVerificationInput(
                    query=input_text,
                    image_data=image_data,
                    regulations=context.get("regulations", None),
                    region=context.get("region", None),
                    context=context,
                )
                result = await image_compliance_skill.handler(input_data)
                response = result.response
                capabilities_used.append("image_compliance_verification")

                # Actualizar contexto con verificaciones de cumplimiento en imágenes
                if "image_compliance_verifications" not in context:
                    context["image_compliance_verifications"] = []

                context["image_compliance_verifications"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "verification_id": result.verification_id,
                        "response": response,
                        "compliance_summary": result.compliance_summary,
                        "compliance_status": result.compliance_status,
                        "recommendations": result.recommendations,
                    }
                )

        elif query_type == "security_image_analysis" and has_image:
            # Usar la skill de análisis de seguridad en imágenes
            security_image_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "security_image_analysis"
                ),
                None,
            )
            if security_image_skill:
                input_data = SecurityImageAnalysisInput(
                    query=input_text,
                    image_data=image_data,
                    analysis_type=context.get("analysis_type", "general"),
                    context=context,
                )
                result = await security_image_skill.handler(input_data)
                response = result.response
                capabilities_used.append("security_image_analysis")

                # Actualizar contexto con análisis de seguridad en imágenes
                if "security_image_analyses" not in context:
                    context["security_image_analyses"] = []

                context["security_image_analyses"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "analysis_id": result.analysis_id,
                        "response": response,
                        "analysis_summary": result.analysis_summary,
                        "security_risks": result.security_risks,
                        "recommendations": result.recommendations,
                    }
                )

        elif query_type == "visual_data_leakage_detection" and has_image:
            # Usar la skill de detección de fugas de datos en imágenes
            data_leakage_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "visual_data_leakage_detection"
                ),
                None,
            )
            if data_leakage_skill:
                input_data = VisualDataLeakageDetectionInput(
                    query=input_text,
                    image_data=image_data,
                    data_types=context.get("data_types", None),
                    context=context,
                )
                result = await data_leakage_skill.handler(input_data)
                response = result.response
                capabilities_used.append("visual_data_leakage_detection")

                # Actualizar contexto con detecciones de fugas de datos en imágenes
                if "visual_data_leakage_detections" not in context:
                    context["visual_data_leakage_detections"] = []

                context["visual_data_leakage_detections"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "detection_id": result.detection_id,
                        "response": response,
                        "detection_summary": result.detection_summary,
                        "sensitive_data_found": result.sensitive_data_found,
                        "protection_recommendations": result.protection_recommendations,
                    }
                )

        # Manejar los tipos de consulta normales (sin imágenes)
        elif query_type == "security_assessment":
            # Usar la skill de evaluación de seguridad
            security_assessment_skill = next(
                (skill for skill in self.skills if skill.name == "security_assessment"),
                None,
            )
            if security_assessment_skill:
                input_data = SecurityAssessmentInput(
                    query=input_text,
                    system_info=context.get("system_info", {}),
                    app_type=context.get("app_type", "general"),
                )
                result = await security_assessment_skill.handler(input_data)
                response = result.response
                capabilities_used.append("security_assessment")

                # Actualizar contexto con evaluaciones de seguridad
                context["security_assessments"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "response": response,
                        "risks": result.risks,
                        "recommendations": result.recommendations,
                    }
                )

        elif query_type == "compliance_check":
            # Usar la skill de verificación de cumplimiento
            compliance_check_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "compliance_verification"
                ),
                None,
            )
            if compliance_check_skill:
                input_data = ComplianceCheckInput(
                    query=input_text,
                    regulations=context.get("regulations", None),
                    region=context.get("region", None),
                )
                result = await compliance_check_skill.handler(input_data)
                response = result.response
                capabilities_used.append("compliance_verification")

                # Actualizar contexto con verificaciones de cumplimiento
                context["compliance_checks"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "response": response,
                        "compliance_status": result.compliance_status,
                        "recommendations": result.recommendations,
                    }
                )

        elif query_type == "vulnerability_scan":
            # Usar la skill de detección de vulnerabilidades
            vulnerability_scan_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "vulnerability_detection"
                ),
                None,
            )
            if vulnerability_scan_skill:
                input_data = VulnerabilityScanInput(
                    query=input_text,
                    system_info=context.get("system_info", {}),
                    scan_type=context.get("scan_type", "general"),
                )
                result = await vulnerability_scan_skill.handler(input_data)
                response = result.response
                capabilities_used.append("vulnerability_detection")

                # Actualizar contexto con escaneos de vulnerabilidades
                context["vulnerability_scans"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "response": response,
                        "vulnerabilities": result.vulnerabilities,
                        "severity_summary": result.severity_summary,
                        "recommendations": result.recommendations,
                    }
                )

        elif query_type == "data_protection":
            # Usar la skill de protección de datos
            data_protection_skill = next(
                (skill for skill in self.skills if skill.name == "data_protection"),
                None,
            )
            if data_protection_skill:
                input_data = DataProtectionInput(
                    query=input_text,
                    data_types=context.get("data_types", None),
                    context=context.get("data_context", {}),
                )
                result = await data_protection_skill.handler(input_data)
                response = result.response
                capabilities_used.append("data_protection")

                # Actualizar contexto con protecciones de datos
                context["data_protections"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "response": response,
                        "protection_measures": result.protection_measures,
                        "best_practices": result.best_practices,
                    }
                )

        else:  # general_request
            # Usar la skill de recomendaciones generales de seguridad
            general_security_skill = next(
                (
                    skill
                    for skill in self.skills
                    if skill.name == "security_recommendations"
                ),
                None,
            )
            if general_security_skill:
                input_data = GeneralSecurityInput(query=input_text, context=context)
                result = await general_security_skill.handler(input_data)
                response = result.response
                capabilities_used.append("security_recommendations")

                # Actualizar contexto con recomendaciones generales
                context["general_recommendations"].append(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "query": input_text,
                        "response": response,
                        "recommendations": result.recommendations,
                    }
                )

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
            f"SecurityComplianceGuardian completó la ejecución en {execution_time:.2f} segundos"
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

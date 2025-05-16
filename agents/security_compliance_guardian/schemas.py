"""
Esquemas para el agente Security Compliance Guardian.

Define los esquemas de entrada y salida para las skills del agente,
incluyendo las nuevas capacidades de visión y multimodales.
"""
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
from datetime import datetime

# Esquemas existentes
class SecurityAssessmentInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre evaluación de seguridad")
    system_info: Optional[Dict[str, Any]] = Field(None, description="Información del sistema a evaluar")
    app_type: Optional[str] = Field(None, description="Tipo de aplicación (web, móvil, API, etc.)")

class SecurityAssessmentOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada de la evaluación de seguridad")
    risks: List[Dict[str, Any]] = Field(..., description="Lista de riesgos identificados")
    recommendations: List[str] = Field(..., description="Recomendaciones de seguridad")

class ComplianceCheckInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre cumplimiento normativo")
    regulations: Optional[List[str]] = Field(None, description="Normativas específicas a verificar")
    region: Optional[str] = Field(None, description="Región geográfica para normativas aplicables")

class ComplianceCheckOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada de la verificación de cumplimiento")
    compliance_status: Dict[str, Any] = Field(..., description="Estado de cumplimiento por normativa")
    recommendations: List[str] = Field(..., description="Recomendaciones para mejorar el cumplimiento")

class VulnerabilityScanInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre vulnerabilidades")
    system_info: Optional[Dict[str, Any]] = Field(None, description="Información del sistema a escanear")
    scan_type: Optional[str] = Field(None, description="Tipo de escaneo (general, específico, etc.)")

class VulnerabilityScanOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada del escaneo de vulnerabilidades")
    vulnerabilities: List[Dict[str, Any]] = Field(..., description="Lista de vulnerabilidades identificadas")
    severity_summary: Dict[str, int] = Field(..., description="Resumen de severidad de vulnerabilidades")
    recommendations: List[str] = Field(..., description="Recomendaciones para mitigar vulnerabilidades")

class DataProtectionInput(BaseModel):
    query: str = Field(..., description="Consulta del usuario sobre protección de datos")
    data_types: Optional[List[str]] = Field(None, description="Tipos de datos a proteger")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para la consulta")

class DataProtectionOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada sobre protección de datos")
    protection_measures: List[Dict[str, Any]] = Field(..., description="Medidas de protección recomendadas")
    best_practices: List[str] = Field(..., description="Mejores prácticas de protección de datos")

class GeneralSecurityInput(BaseModel):
    query: str = Field(..., description="Consulta general sobre seguridad")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para la consulta")

class GeneralSecurityOutput(BaseModel):
    response: str = Field(..., description="Respuesta detallada a la consulta de seguridad")
    recommendations: Optional[List[str]] = Field(None, description="Recomendaciones generales de seguridad")

# Nuevos esquemas para capacidades de visión

class ImageComplianceVerificationInput(BaseModel):
    """Esquema de entrada para verificación de cumplimiento normativo en imágenes."""
    image_data: Union[str, Dict[str, Any]] = Field(..., description="Datos de la imagen (base64, URL o ruta)")
    query: str = Field(..., description="Consulta o contexto del usuario sobre la imagen")
    regulations: Optional[List[str]] = Field(None, description="Normativas específicas a verificar")
    region: Optional[str] = Field(None, description="Región geográfica para normativas aplicables")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para la verificación")

class ImageComplianceVerificationOutput(BaseModel):
    """Esquema de salida para verificación de cumplimiento normativo en imágenes."""
    verification_id: str = Field(..., description="ID único de la verificación")
    compliance_summary: str = Field(..., description="Resumen del análisis de cumplimiento")
    compliance_status: Dict[str, Any] = Field(..., description="Estado de cumplimiento por normativa")
    sensitive_elements: List[Dict[str, Any]] = Field(..., description="Elementos sensibles identificados en la imagen")
    compliance_issues: List[Dict[str, Any]] = Field(..., description="Problemas de cumplimiento identificados")
    recommendations: List[str] = Field(..., description="Recomendaciones para resolver problemas de cumplimiento")
    response: str = Field(..., description="Respuesta detallada para el usuario")
    confidence_score: float = Field(..., description="Puntuación de confianza del análisis (0-1)")

class SecurityImageAnalysisInput(BaseModel):
    """Esquema de entrada para análisis de seguridad en imágenes."""
    image_data: Union[str, Dict[str, Any]] = Field(..., description="Datos de la imagen (base64, URL o ruta)")
    query: str = Field(..., description="Consulta o contexto del usuario sobre la imagen")
    analysis_type: Optional[str] = Field(None, description="Tipo de análisis (general, específico, etc.)")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para el análisis")

class SecurityImageAnalysisOutput(BaseModel):
    """Esquema de salida para análisis de seguridad en imágenes."""
    analysis_id: str = Field(..., description="ID único del análisis")
    analysis_summary: str = Field(..., description="Resumen del análisis de seguridad")
    security_risks: List[Dict[str, Any]] = Field(..., description="Riesgos de seguridad identificados")
    severity_levels: Dict[str, int] = Field(..., description="Niveles de severidad de los riesgos")
    recommendations: List[str] = Field(..., description="Recomendaciones para mitigar riesgos")
    response: str = Field(..., description="Respuesta detallada para el usuario")
    confidence_score: float = Field(..., description="Puntuación de confianza del análisis (0-1)")

class VisualDataLeakageDetectionInput(BaseModel):
    """Esquema de entrada para detección de fugas de datos en imágenes."""
    image_data: Union[str, Dict[str, Any]] = Field(..., description="Datos de la imagen (base64, URL o ruta)")
    query: str = Field(..., description="Consulta o contexto del usuario sobre la imagen")
    data_types: Optional[List[str]] = Field(None, description="Tipos de datos a detectar")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para la detección")

class VisualDataLeakageDetectionOutput(BaseModel):
    """Esquema de salida para detección de fugas de datos en imágenes."""
    detection_id: str = Field(..., description="ID único de la detección")
    detection_summary: str = Field(..., description="Resumen de la detección de fugas de datos")
    sensitive_data_found: List[Dict[str, Any]] = Field(..., description="Datos sensibles encontrados")
    risk_assessment: Dict[str, Any] = Field(..., description="Evaluación de riesgos")
    protection_recommendations: List[str] = Field(..., description="Recomendaciones para proteger datos")
    response: str = Field(..., description="Respuesta detallada para el usuario")
    confidence_score: float = Field(..., description="Puntuación de confianza de la detección (0-1)")

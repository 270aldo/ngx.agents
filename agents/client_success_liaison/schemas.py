"""
Esquemas para el agente Client Success Liaison.

Define los esquemas de entrada y salida para las skills del agente,
incluyendo las nuevas capacidades de visión y multimodales.
"""
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
from datetime import datetime

# Esquemas existentes
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

# Nuevos esquemas para capacidades de visión

class FeedbackImageAnalysisInput(BaseModel):
    """Esquema de entrada para análisis de imágenes de feedback de clientes."""
    image_data: Union[str, Dict[str, Any]] = Field(..., description="Datos de la imagen (base64, URL o ruta)")
    query: str = Field(..., description="Consulta o contexto del usuario sobre la imagen")
    feedback_type: Optional[str] = Field(None, description="Tipo de feedback (sugerencia, problema, pregunta)")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario que envía el feedback")

class FeedbackImageAnalysisOutput(BaseModel):
    """Esquema de salida para análisis de imágenes de feedback de clientes."""
    analysis_id: str = Field(..., description="ID único del análisis")
    analysis_summary: str = Field(..., description="Resumen del análisis de la imagen")
    feedback_category: str = Field(..., description="Categoría del feedback identificada")
    content_type: str = Field(..., description="Tipo de contenido identificado en la imagen")
    key_elements: List[Dict[str, Any]] = Field(..., description="Elementos clave identificados en la imagen")
    recommendations: List[str] = Field(..., description="Recomendaciones basadas en el análisis")
    response: str = Field(..., description="Respuesta detallada para el usuario")
    confidence_score: float = Field(..., description="Puntuación de confianza del análisis (0-1)")

class CommunityContentAnalysisInput(BaseModel):
    """Esquema de entrada para análisis de contenido de comunidad."""
    image_data: Union[str, Dict[str, Any]] = Field(..., description="Datos de la imagen (base64, URL o ruta)")
    query: str = Field(..., description="Consulta o contexto del usuario sobre la imagen")
    community_context: Optional[Dict[str, Any]] = Field(None, description="Contexto de la comunidad")
    content_purpose: Optional[str] = Field(None, description="Propósito del contenido (educativo, motivacional, etc.)")

class CommunityContentAnalysisOutput(BaseModel):
    """Esquema de salida para análisis de contenido de comunidad."""
    analysis_id: str = Field(..., description="ID único del análisis")
    content_summary: str = Field(..., description="Resumen del contenido de la imagen")
    engagement_potential: str = Field(..., description="Potencial de engagement estimado (alto, medio, bajo)")
    target_audience: List[str] = Field(..., description="Audiencia objetivo identificada")
    content_recommendations: List[Dict[str, Any]] = Field(..., description="Recomendaciones para mejorar el contenido")
    distribution_channels: List[str] = Field(..., description="Canales de distribución recomendados")
    response: str = Field(..., description="Respuesta detallada para el usuario")
    
class UserJourneyVisualizationInput(BaseModel):
    """Esquema de entrada para visualización de journey de usuario."""
    journey_data: Dict[str, Any] = Field(..., description="Datos del journey del usuario")
    visualization_type: str = Field(..., description="Tipo de visualización (timeline, flowchart, etc.)")
    focus_points: Optional[List[str]] = Field(None, description="Puntos de enfoque específicos")
    
class UserJourneyVisualizationOutput(BaseModel):
    """Esquema de salida para visualización de journey de usuario."""
    visualization_id: str = Field(..., description="ID único de la visualización")
    visualization_url: str = Field(..., description="URL de la visualización generada")
    journey_summary: str = Field(..., description="Resumen del journey visualizado")
    key_touchpoints: List[Dict[str, Any]] = Field(..., description="Puntos de contacto clave identificados")
    improvement_areas: List[Dict[str, Any]] = Field(..., description="Áreas de mejora identificadas")
    response: str = Field(..., description="Respuesta detallada para el usuario")

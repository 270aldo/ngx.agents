"""
Esquemas para el agente BiometricsInsightEngine.

Este módulo define los esquemas de entrada y salida para las skills del agente
BiometricsInsightEngine utilizando modelos Pydantic.
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field


# Modelos para la skill de análisis biométrico
class BiometricAnalysisInput(BaseModel):
    """Esquema de entrada para la skill de análisis biométrico."""

    input_text: str = Field(..., description="Texto de entrada del usuario")
    biometric_data: Dict[str, Any] = Field(
        ..., description="Datos biométricos del usuario a analizar"
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )


class BiometricAnalysisOutput(BaseModel):
    """Esquema de salida para la skill de análisis biométrico."""

    interpretation: str = Field(
        ..., description="Interpretación general de los datos biométricos"
    )
    main_insights: List[str] = Field(
        ..., description="Principales insights identificados"
    )
    patterns: List[str] = Field(..., description="Patrones relevantes identificados")
    recommendations: List[str] = Field(
        ..., description="Recomendaciones personalizadas"
    )
    areas_for_improvement: List[str] = Field(
        ..., description="Áreas de mejora identificadas"
    )


# Modelos para la skill de reconocimiento de patrones
class PatternRecognitionInput(BaseModel):
    """Esquema de entrada para la skill de reconocimiento de patrones."""

    input_text: str = Field(..., description="Texto de entrada del usuario")
    biometric_data: Dict[str, Any] = Field(
        ..., description="Datos biométricos del usuario a analizar"
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )


class PatternRecognitionOutput(BaseModel):
    """Esquema de salida para la skill de reconocimiento de patrones."""

    identified_patterns: List[Dict[str, Any]] = Field(
        ..., description="Patrones identificados en los datos biométricos"
    )
    correlations: List[Dict[str, Any]] = Field(
        ..., description="Correlaciones entre diferentes métricas"
    )
    causality_analysis: Optional[Dict[str, Any]] = Field(
        None, description="Análisis de posibles relaciones causales"
    )
    recommendations: List[str] = Field(
        ..., description="Recomendaciones basadas en los patrones identificados"
    )


# Modelos para la skill de identificación de tendencias
class TrendIdentificationInput(BaseModel):
    """Esquema de entrada para la skill de identificación de tendencias."""

    input_text: str = Field(..., description="Texto de entrada del usuario")
    biometric_data: Dict[str, Any] = Field(
        ..., description="Datos biométricos del usuario a analizar"
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )


class TrendIdentificationOutput(BaseModel):
    """Esquema de salida para la skill de identificación de tendencias."""

    trends: List[Dict[str, Any]] = Field(
        ..., description="Tendencias identificadas en los datos biométricos"
    )
    significant_changes: List[Dict[str, Any]] = Field(
        ..., description="Cambios significativos detectados"
    )
    progress_evaluation: Dict[str, Any] = Field(
        ..., description="Evaluación del progreso en el tiempo"
    )
    future_projections: Optional[Dict[str, Any]] = Field(
        None, description="Proyecciones futuras basadas en tendencias actuales"
    )
    recommendations: List[str] = Field(
        ..., description="Recomendaciones basadas en las tendencias identificadas"
    )


# Modelos para la skill de visualización de datos
class DataVisualizationInput(BaseModel):
    """Esquema de entrada para la skill de visualización de datos."""

    input_text: str = Field(..., description="Texto de entrada del usuario")
    biometric_data: Dict[str, Any] = Field(
        ..., description="Datos biométricos del usuario a visualizar"
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )
    visualization_type: Optional[str] = Field(
        "line", description="Tipo de visualización (line, bar, scatter, etc.)"
    )
    metrics: Optional[List[str]] = Field(
        None, description="Métricas específicas a visualizar"
    )


class DataVisualizationOutput(BaseModel):
    """Esquema de salida para la skill de visualización de datos."""

    visualization_url: str = Field(
        ..., description="URL o ruta a la visualización generada"
    )
    visualization_type: str = Field(..., description="Tipo de visualización generada")
    metrics_included: List[str] = Field(
        ..., description="Métricas incluidas en la visualización"
    )
    interpretation: Optional[str] = Field(
        None, description="Interpretación de la visualización"
    )
    recommendations: Optional[List[str]] = Field(
        None, description="Recomendaciones basadas en la visualización"
    )


# Artefactos
class BiometricAnalysisArtifact(BaseModel):
    """Artefacto para el análisis biométrico."""

    analysis_id: str = Field(..., description="ID único del análisis")
    analysis_type: str = Field(..., description="Tipo de análisis realizado")
    metrics_analyzed: List[str] = Field(..., description="Métricas analizadas")
    timestamp: str = Field(..., description="Timestamp del análisis")
    summary: str = Field(..., description="Resumen del análisis")


class BiometricVisualizationArtifact(BaseModel):
    """Artefacto para la visualización de datos biométricos."""

    visualization_id: str = Field(..., description="ID único de la visualización")
    visualization_type: str = Field(..., description="Tipo de visualización")
    metrics_included: List[str] = Field(..., description="Métricas incluidas")
    timestamp: str = Field(..., description="Timestamp de la visualización")
    url: str = Field(..., description="URL o ruta a la visualización")


# Modelos para la skill de análisis de imágenes biométricas
class BiometricImageAnalysisInput(BaseModel):
    """Esquema de entrada para la skill de análisis de imágenes biométricas."""

    image_data: Union[str, Dict[str, Any]] = Field(
        ..., description="Datos de la imagen (base64, URL o ruta de archivo)"
    )
    analysis_type: Optional[str] = Field(
        "full",
        description="Tipo de análisis a realizar (full, body, face, posture, etc.)",
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )


class BiometricImageAnalysisOutput(BaseModel):
    """Esquema de salida para la skill de análisis de imágenes biométricas."""

    analysis_summary: str = Field(
        ..., description="Resumen del análisis de la imagen biométrica"
    )
    detected_metrics: Dict[str, Any] = Field(
        ..., description="Métricas biométricas detectadas en la imagen"
    )
    visual_indicators: List[Dict[str, Any]] = Field(
        ..., description="Indicadores visuales identificados"
    )
    health_insights: List[str] = Field(
        ..., description="Insights de salud basados en el análisis visual"
    )
    recommendations: List[str] = Field(
        ..., description="Recomendaciones basadas en el análisis visual"
    )
    confidence_score: float = Field(
        ..., description="Puntuación de confianza del análisis (0.0-1.0)"
    )


class BiometricImageArtifact(BaseModel):
    """Artefacto para el análisis de imágenes biométricas."""

    analysis_id: str = Field(..., description="ID único del análisis")
    image_type: str = Field(..., description="Tipo de imagen analizada")
    analysis_type: str = Field(..., description="Tipo de análisis realizado")
    timestamp: float = Field(..., description="Timestamp del análisis")
    annotations: Optional[Dict[str, Any]] = Field(
        None, description="Anotaciones en la imagen"
    )
    processed_image_url: Optional[str] = Field(
        None, description="URL de la imagen procesada con anotaciones"
    )

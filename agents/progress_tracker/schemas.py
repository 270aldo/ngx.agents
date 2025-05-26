from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field


class AnalyzeProgressInput(BaseModel):
    """Entrada para analizar el progreso del usuario."""

    user_id: str = Field(..., description="ID del usuario")
    time_period: str = Field(
        ..., description="Periodo de tiempo (ej. 'last_month', 'last_3_months')"
    )
    metrics: Optional[List[str]] = Field(
        None, description="Métricas específicas a analizar (opcional)"
    )


class AnalyzeProgressOutput(BaseModel):
    """Salida del análisis de progreso."""

    analysis_id: str = Field(..., description="ID único del análisis generado")
    result: Dict[str, Any] = Field(
        ..., description="Resultado del análisis con insights y tendencias"
    )
    status: str = Field("success", description="Estado de la operación")


class VisualizeProgressInput(BaseModel):
    """Entrada para visualizar el progreso del usuario."""

    user_id: str = Field(..., description="ID del usuario")
    metric: str = Field(
        ..., description="Métrica a visualizar (ej. 'weight', 'performance')"
    )
    time_period: str = Field(
        ..., description="Periodo de tiempo (ej. 'last_month', 'last_3_months')"
    )
    chart_type: str = Field(..., description="Tipo de gráfico ('line', 'bar')")


class VisualizeProgressOutput(BaseModel):
    """Salida de la visualización de progreso."""

    visualization_url: str = Field(
        ..., description="URL o ruta al archivo de visualización generado"
    )
    filepath: Optional[str] = Field(
        None, description="Ruta local al archivo (solo para desarrollo)"
    )
    status: str = Field("success", description="Estado de la operación")


class CompareProgressInput(BaseModel):
    """Entrada para comparar el progreso entre dos periodos."""

    user_id: str = Field(..., description="ID del usuario")
    period1: str = Field(..., description="Primer periodo (ej. 'last_month')")
    period2: str = Field(..., description="Segundo periodo (ej. 'previous_month')")
    metrics: List[str] = Field(..., description="Métricas a comparar")


class CompareProgressOutput(BaseModel):
    """Salida de la comparación de progreso."""

    result: Dict[str, Any] = Field(
        ...,
        description="Resultado de la comparación con diferencias y cambios porcentuales",
    )
    status: str = Field("success", description="Estado de la operación")


class ProgressAnalysisArtifact(BaseModel):
    """Artefacto para análisis de progreso."""

    label: str = Field(..., description="Etiqueta del artefacto")
    content_type: str = Field("application/json", description="Tipo de contenido")
    data: Dict[str, Any] = Field(..., description="Datos del análisis de progreso")


class ProgressVisualizationArtifact(BaseModel):
    """Artefacto para visualización de progreso."""

    label: str = Field(..., description="Etiqueta del artefacto")
    content_type: str = Field("image/png", description="Tipo de contenido")
    url: str = Field(..., description="URL a la imagen de visualización")
    data: Optional[Dict[str, Any]] = Field(
        None, description="Metadatos adicionales de la visualización"
    )


class AnalyzeBodyProgressInput(BaseModel):
    """Entrada para analizar el progreso corporal mediante imágenes."""

    before_image: Union[str, Dict[str, Any]] = Field(
        ..., description="Imagen 'antes' (base64, URL o ruta de archivo)"
    )
    after_image: Union[str, Dict[str, Any]] = Field(
        ..., description="Imagen 'después' (base64, URL o ruta de archivo)"
    )
    user_id: Optional[str] = Field(None, description="ID del usuario")
    time_between_images: Optional[str] = Field(
        None, description="Tiempo transcurrido entre las imágenes"
    )
    focus_areas: Optional[List[str]] = Field(
        None,
        description="Áreas específicas a analizar (composición corporal, postura, etc.)",
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )


class BodyChangeMetric(BaseModel):
    """Modelo para una métrica de cambio corporal."""

    metric_name: str = Field(..., description="Nombre de la métrica")
    before_value: Optional[str] = Field(None, description="Valor antes")
    after_value: Optional[str] = Field(None, description="Valor después")
    change: Optional[str] = Field(None, description="Cambio (absoluto o porcentual)")
    confidence: float = Field(..., description="Confianza en la medición (0.0-1.0)")


class BodyAreaChange(BaseModel):
    """Modelo para un cambio en un área corporal específica."""

    body_area: str = Field(..., description="Área corporal")
    changes_observed: List[str] = Field(..., description="Cambios observados")
    improvement_level: str = Field(
        ..., description="Nivel de mejora (ninguno, leve, moderado, significativo)"
    )
    notes: Optional[str] = Field(None, description="Notas adicionales")


class AnalyzeBodyProgressOutput(BaseModel):
    """Salida del análisis de progreso corporal mediante imágenes."""

    analysis_id: str = Field(..., description="ID único del análisis")
    progress_summary: str = Field(..., description="Resumen del progreso observado")
    metrics: List[BodyChangeMetric] = Field(
        ..., description="Métricas de cambio corporal"
    )
    body_areas: List[BodyAreaChange] = Field(
        ..., description="Cambios por áreas corporales"
    )
    overall_progress_score: float = Field(
        ..., description="Puntuación general de progreso (0-10)"
    )
    recommendations: List[str] = Field(
        ..., description="Recomendaciones basadas en el progreso"
    )
    comparison_image_url: Optional[str] = Field(
        None, description="URL de la imagen comparativa generada"
    )


class GenerateProgressVisualizationInput(BaseModel):
    """Entrada para generar visualizaciones de progreso a partir de imágenes."""

    images: List[Dict[str, Any]] = Field(
        ...,
        description="Lista de imágenes con fechas (cada elemento debe tener 'image_data' y 'date')",
    )
    user_id: Optional[str] = Field(None, description="ID del usuario")
    visualization_type: str = Field(
        "side_by_side",
        description="Tipo de visualización (side_by_side, overlay, grid, timeline)",
    )
    metrics_to_highlight: Optional[List[str]] = Field(
        None, description="Métricas específicas a resaltar en la visualización"
    )
    include_measurements: Optional[bool] = Field(
        False, description="Si se deben incluir mediciones en la visualización"
    )


class GenerateProgressVisualizationOutput(BaseModel):
    """Salida de la generación de visualizaciones de progreso."""

    visualization_id: str = Field(..., description="ID único de la visualización")
    visualization_url: str = Field(..., description="URL de la visualización generada")
    visualization_type: str = Field(..., description="Tipo de visualización generada")
    image_count: int = Field(..., description="Número de imágenes incluidas")
    time_span: Optional[str] = Field(None, description="Período de tiempo cubierto")
    notes: Optional[str] = Field(
        None, description="Notas adicionales sobre la visualización"
    )


class BodyProgressAnalysisArtifact(BaseModel):
    """Artefacto para análisis de progreso corporal."""

    analysis_id: str = Field(..., description="ID único del análisis")
    created_at: str = Field(..., description="Timestamp de creación")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    progress_score: float = Field(..., description="Puntuación de progreso")
    comparison_image_url: Optional[str] = Field(
        None, description="URL de la imagen comparativa"
    )
    time_period: Optional[str] = Field(None, description="Período de tiempo analizado")

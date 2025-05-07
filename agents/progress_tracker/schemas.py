from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class AnalyzeProgressInput(BaseModel):
    """Entrada para analizar el progreso del usuario."""
    user_id: str = Field(..., description="ID del usuario")
    time_period: str = Field(..., description="Periodo de tiempo (ej. 'last_month', 'last_3_months')")
    metrics: Optional[List[str]] = Field(None, description="Métricas específicas a analizar (opcional)")

class AnalyzeProgressOutput(BaseModel):
    """Salida del análisis de progreso."""
    analysis_id: str = Field(..., description="ID único del análisis generado")
    result: Dict[str, Any] = Field(..., description="Resultado del análisis con insights y tendencias")
    status: str = Field("success", description="Estado de la operación")

class VisualizeProgressInput(BaseModel):
    """Entrada para visualizar el progreso del usuario."""
    user_id: str = Field(..., description="ID del usuario")
    metric: str = Field(..., description="Métrica a visualizar (ej. 'weight', 'performance')")
    time_period: str = Field(..., description="Periodo de tiempo (ej. 'last_month', 'last_3_months')")
    chart_type: str = Field(..., description="Tipo de gráfico ('line', 'bar')")

class VisualizeProgressOutput(BaseModel):
    """Salida de la visualización de progreso."""
    visualization_url: str = Field(..., description="URL o ruta al archivo de visualización generado")
    filepath: Optional[str] = Field(None, description="Ruta local al archivo (solo para desarrollo)")
    status: str = Field("success", description="Estado de la operación")

class CompareProgressInput(BaseModel):
    """Entrada para comparar el progreso entre dos periodos."""
    user_id: str = Field(..., description="ID del usuario")
    period1: str = Field(..., description="Primer periodo (ej. 'last_month')")
    period2: str = Field(..., description="Segundo periodo (ej. 'previous_month')")
    metrics: List[str] = Field(..., description="Métricas a comparar")

class CompareProgressOutput(BaseModel):
    """Salida de la comparación de progreso."""
    result: Dict[str, Any] = Field(..., description="Resultado de la comparación con diferencias y cambios porcentuales")
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
    data: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales de la visualización")

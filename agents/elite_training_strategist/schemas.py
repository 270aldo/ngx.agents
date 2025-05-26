from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field


class GenerateTrainingPlanInput(BaseModel):
    """Entrada para generar un plan de entrenamiento."""

    goals: List[str] = Field(..., description="Objetivos del entrenamiento")
    preferences: Optional[Dict[str, Any]] = Field(
        None, description="Preferencias del usuario"
    )
    training_history: Optional[Dict[str, Any]] = Field(
        None, description="Historial de entrenamiento"
    )
    duration_weeks: Optional[int] = Field(8, description="Duración del plan en semanas")


class GenerateTrainingPlanOutput(BaseModel):
    """Salida de la generación de un plan de entrenamiento."""

    plan_name: str = Field(..., description="Nombre del plan de entrenamiento")
    program_type: str = Field(..., description="Tipo de programa, ej: PRIME, STRENGTH")
    duration_weeks: int = Field(..., description="Duración del plan en semanas")
    description: str = Field(..., description="Descripción general del plan")
    phases: List[Dict[str, Any]] = Field(
        ..., description="Fases del plan de entrenamiento"
    )
    artifacts: Optional[List[Dict[str, Any]]] = Field(
        None, description="Artefactos generados, como archivos markdown"
    )
    response: Optional[str] = Field(
        None, description="Respuesta textual principal del plan"
    )


class AdaptTrainingProgramInput(BaseModel):
    """Entrada para adaptar un programa de entrenamiento existente."""

    existing_plan_id: str = Field(..., description="ID o referencia al plan existente")
    adaptation_reason: str = Field(..., description="Razón para la adaptación")
    feedback: Optional[Dict[str, Any]] = Field(
        None, description="Feedback sobre el plan actual"
    )
    new_goals: Optional[List[str]] = Field(
        None, description="Nuevos objetivos o ajustes"
    )


class AdaptTrainingProgramOutput(BaseModel):
    """Salida de la adaptación de un programa de entrenamiento."""

    adapted_plan_name: str = Field(..., description="Nombre del plan adaptado")
    program_type: str = Field(
        ..., description="Tipo de programa (PRIME, LONGEVITY, GENERAL)"
    )
    adaptation_summary: str = Field(
        ..., description="Resumen de los cambios realizados"
    )
    duration_weeks: int = Field(
        ..., description="Duración del plan adaptado en semanas"
    )
    description: str = Field(..., description="Descripción general del plan adaptado")
    phases: List[Dict[str, Any]] = Field(..., description="Fases del plan adaptado")


class AnalyzePerformanceDataInput(BaseModel):
    """Entrada para analizar datos de rendimiento."""

    performance_data: Dict[str, Any] = Field(
        ..., description="Datos de rendimiento a analizar"
    )
    metrics_to_focus: Optional[List[str]] = Field(
        None, description="Métricas específicas para enfocar el análisis"
    )
    comparison_period: Optional[Dict[str, Any]] = Field(
        None, description="Período de comparación"
    )


class AnalyzePerformanceDataOutput(BaseModel):
    """Salida del análisis de datos de rendimiento."""

    analysis_summary: str = Field(..., description="Resumen del análisis")
    key_observations: List[Dict[str, Any]] = Field(
        ..., description="Observaciones clave identificadas"
    )
    recommendations: List[Dict[str, Any]] = Field(
        ..., description="Recomendaciones basadas en el análisis"
    )


class SetTrainingIntensityVolumeInput(BaseModel):
    """Entrada para establecer intensidad y volumen de entrenamiento."""

    current_phase: str = Field(..., description="Fase actual del entrenamiento")
    athlete_feedback: Dict[str, Any] = Field(
        ..., description="Feedback del atleta sobre fatiga, RPE, etc."
    )
    performance_metrics: Dict[str, Any] = Field(
        ..., description="Métricas de rendimiento recientes"
    )
    goal_adjustment_reason: Optional[str] = Field(
        None, description="Razón para ajustar objetivos"
    )


class SetTrainingIntensityVolumeOutput(BaseModel):
    """Salida para establecer intensidad y volumen de entrenamiento."""

    adjustment_summary: str = Field(
        ..., description="Resumen de los ajustes recomendados"
    )
    recommended_intensity: Dict[str, Any] = Field(
        ..., description="Recomendaciones de intensidad"
    )
    recommended_volume: Dict[str, Any] = Field(
        ..., description="Recomendaciones de volumen"
    )
    notes: Optional[str] = Field(
        None, description="Notas adicionales sobre los ajustes"
    )


class PrescribeExerciseRoutinesInput(BaseModel):
    """Entrada para prescribir rutinas de ejercicios."""

    focus_area: str = Field(..., description="Área de enfoque para la rutina")
    exercise_type: str = Field(
        ..., description="Tipo de ejercicio (compound, isolation, etc.)"
    )
    equipment_available: List[str] = Field(..., description="Equipamiento disponible")
    experience_level: str = Field(..., description="Nivel de experiencia del atleta")


class PrescribeExerciseRoutinesOutput(BaseModel):
    """Salida para prescribir rutinas de ejercicios."""

    routine_name: str = Field(..., description="Nombre de la rutina")
    focus_area: str = Field(..., description="Área de enfoque")
    exercise_type: str = Field(..., description="Tipo de ejercicio")
    estimated_duration_minutes: int = Field(
        ..., description="Duración estimada en minutos"
    )
    exercises: List[Dict[str, Any]] = Field(..., description="Lista de ejercicios")
    warm_up: Optional[List[str]] = Field(
        None, description="Ejercicios de calentamiento"
    )
    cool_down: Optional[List[str]] = Field(
        None, description="Ejercicios de enfriamiento"
    )


class TrainingPlanArtifact(BaseModel):
    """Artefacto para planes de entrenamiento."""

    label: str = Field(..., description="Etiqueta del artefacto")
    content_type: str = Field("application/json", description="Tipo de contenido")
    data: Dict[str, Any] = Field(..., description="Datos del plan de entrenamiento")


class AnalyzeExerciseFormInput(BaseModel):
    """Entrada para analizar la forma y técnica de ejercicios mediante imágenes."""

    image_data: Union[str, Dict[str, Any]] = Field(
        ..., description="Datos de la imagen (base64, URL o ruta de archivo)"
    )
    exercise_name: Optional[str] = Field(
        None, description="Nombre del ejercicio que se está realizando"
    )
    exercise_type: Optional[str] = Field(
        None, description="Tipo de ejercicio (fuerza, cardio, flexibilidad, etc.)"
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )
    analysis_focus: Optional[List[str]] = Field(
        None,
        description="Aspectos específicos a analizar (postura, alineación, rango de movimiento, etc.)",
    )


class FormCorrectionPoint(BaseModel):
    """Modelo para un punto de corrección de forma en un ejercicio."""

    body_part: str = Field(
        ..., description="Parte del cuerpo relacionada con la corrección"
    )
    issue: str = Field(..., description="Problema identificado")
    correction: str = Field(..., description="Corrección recomendada")
    severity: str = Field(
        ..., description="Severidad del problema (leve, moderada, grave)"
    )
    confidence: float = Field(..., description="Confianza en la detección (0.0-1.0)")


class AnalyzeExerciseFormOutput(BaseModel):
    """Salida del análisis de forma y técnica de ejercicios."""

    exercise_name: str = Field(
        ..., description="Nombre del ejercicio identificado o proporcionado"
    )
    form_quality_score: float = Field(
        ..., description="Puntuación general de calidad de forma (0-10)"
    )
    form_analysis: str = Field(
        ..., description="Análisis detallado de la forma del ejercicio"
    )
    correction_points: List[FormCorrectionPoint] = Field(
        ..., description="Puntos específicos de corrección"
    )
    strengths: List[str] = Field(..., description="Aspectos positivos de la forma")
    recommendations: List[str] = Field(..., description="Recomendaciones para mejorar")
    risk_assessment: Optional[Dict[str, Any]] = Field(
        None, description="Evaluación de riesgos potenciales de lesión"
    )


class CompareExerciseProgressInput(BaseModel):
    """Entrada para comparar el progreso en ejercicios a través de imágenes."""

    before_image: Union[str, Dict[str, Any]] = Field(
        ..., description="Imagen 'antes' (base64, URL o ruta de archivo)"
    )
    after_image: Union[str, Dict[str, Any]] = Field(
        ..., description="Imagen 'después' (base64, URL o ruta de archivo)"
    )
    exercise_name: Optional[str] = Field(
        None, description="Nombre del ejercicio que se está comparando"
    )
    time_between_images: Optional[str] = Field(
        None, description="Tiempo transcurrido entre las imágenes"
    )
    metrics_to_compare: Optional[List[str]] = Field(
        None, description="Métricas específicas a comparar"
    )


class CompareExerciseProgressOutput(BaseModel):
    """Salida de la comparación de progreso en ejercicios."""

    exercise_name: str = Field(..., description="Nombre del ejercicio comparado")
    progress_summary: str = Field(..., description="Resumen del progreso observado")
    key_improvements: List[Dict[str, Any]] = Field(
        ..., description="Mejoras clave identificadas"
    )
    form_changes: List[Dict[str, Any]] = Field(
        ..., description="Cambios en la forma del ejercicio"
    )
    recommendations: List[str] = Field(
        ..., description="Recomendaciones basadas en el progreso"
    )
    progress_score: Optional[float] = Field(
        None, description="Puntuación cuantitativa del progreso (0-10)"
    )


class ExerciseFormAnalysisArtifact(BaseModel):
    """Artefacto para análisis de forma de ejercicios."""

    analysis_id: str = Field(..., description="ID único del análisis")
    exercise_name: str = Field(..., description="Nombre del ejercicio analizado")
    timestamp: str = Field(..., description="Timestamp del análisis")
    form_quality_score: float = Field(..., description="Puntuación de calidad de forma")
    processed_image_url: Optional[str] = Field(
        None, description="URL de la imagen procesada con anotaciones"
    )

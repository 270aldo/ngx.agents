"""
Esquemas para el agente PrecisionNutritionArchitect.

Este módulo define los esquemas de entrada y salida para las skills del agente
PrecisionNutritionArchitect utilizando modelos Pydantic.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


# Modelos para la skill de creación de plan de comidas
class CreateMealPlanInput(BaseModel):
    """Esquema de entrada para la skill de creación de plan de comidas."""
    input_text: str = Field(..., description="Texto de entrada del usuario")
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )
    dietary_restrictions: Optional[List[str]] = Field(
        None, description="Restricciones alimenticias del usuario"
    )
    allergies: Optional[List[str]] = Field(
        None, description="Alergias alimentarias del usuario"
    )
    goals: Optional[List[str]] = Field(
        None, description="Objetivos nutricionales del usuario"
    )


class MealItem(BaseModel):
    """Modelo para un elemento de comida en un plan de alimentación."""
    name: str = Field(..., description="Nombre del alimento")
    portion: str = Field(..., description="Porción o cantidad")
    calories: Optional[int] = Field(None, description="Calorías aproximadas")
    macros: Optional[Dict[str, Any]] = Field(None, description="Macronutrientes")


class Meal(BaseModel):
    """Modelo para una comida en un plan de alimentación."""
    name: str = Field(..., description="Nombre de la comida (desayuno, almuerzo, etc.)")
    time: str = Field(..., description="Hora recomendada")
    items: List[MealItem] = Field(..., description="Elementos de la comida")
    notes: Optional[str] = Field(None, description="Notas adicionales")


class CreateMealPlanOutput(BaseModel):
    """Esquema de salida para la skill de creación de plan de comidas."""
    daily_plan: List[Meal] = Field(..., description="Plan diario de comidas")
    total_calories: Optional[int] = Field(
        None, description="Total de calorías diarias"
    )
    macronutrient_distribution: Optional[Dict[str, Any]] = Field(
        None, description="Distribución de macronutrientes"
    )
    recommendations: Optional[List[str]] = Field(
        None, description="Recomendaciones generales"
    )
    notes: Optional[str] = Field(None, description="Notas adicionales")


# Modelos para la skill de recomendación de suplementos
class RecommendSupplementsInput(BaseModel):
    """Esquema de entrada para la skill de recomendación de suplementos."""
    input_text: str = Field(..., description="Texto de entrada del usuario")
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )
    biomarkers: Optional[Dict[str, Any]] = Field(
        None, description="Biomarcadores del usuario"
    )
    current_supplements: Optional[List[str]] = Field(
        None, description="Suplementos actuales del usuario"
    )
    goals: Optional[List[str]] = Field(
        None, description="Objetivos del usuario"
    )


class Supplement(BaseModel):
    """Modelo para un suplemento recomendado."""
    name: str = Field(..., description="Nombre del suplemento")
    dosage: str = Field(..., description="Dosis recomendada")
    timing: str = Field(..., description="Momento óptimo de consumo")
    benefits: List[str] = Field(..., description="Beneficios esperados")
    precautions: Optional[List[str]] = Field(
        None, description="Precauciones a considerar"
    )
    natural_alternatives: Optional[List[str]] = Field(
        None, description="Alternativas naturales"
    )


class RecommendSupplementsOutput(BaseModel):
    """Esquema de salida para la skill de recomendación de suplementos."""
    supplements: List[Supplement] = Field(..., description="Suplementos recomendados")
    general_recommendations: str = Field(
        ..., description="Recomendaciones generales sobre suplementación"
    )
    notes: Optional[str] = Field(None, description="Notas adicionales")


# Modelos para la skill de análisis de biomarcadores
class AnalyzeBiomarkersInput(BaseModel):
    """Esquema de entrada para la skill de análisis de biomarcadores."""
    input_text: str = Field(..., description="Texto de entrada del usuario")
    biomarkers: Dict[str, Any] = Field(
        ..., description="Biomarcadores del usuario a analizar"
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )
    reference_ranges: Optional[Dict[str, Any]] = Field(
        None, description="Rangos de referencia para los biomarcadores"
    )


class BiomarkerAnalysis(BaseModel):
    """Modelo para el análisis de un biomarcador."""
    name: str = Field(..., description="Nombre del biomarcador")
    value: Any = Field(..., description="Valor del biomarcador")
    reference_range: Optional[str] = Field(
        None, description="Rango de referencia"
    )
    status: str = Field(..., description="Estado (normal, bajo, alto)")
    interpretation: str = Field(..., description="Interpretación del valor")
    nutritional_implications: List[str] = Field(
        ..., description="Implicaciones nutricionales"
    )
    recommendations: List[str] = Field(
        ..., description="Recomendaciones basadas en el valor"
    )


class AnalyzeBiomarkersOutput(BaseModel):
    """Esquema de salida para la skill de análisis de biomarcadores."""
    analyses: List[BiomarkerAnalysis] = Field(
        ..., description="Análisis de biomarcadores"
    )
    overall_assessment: str = Field(
        ..., description="Evaluación general de los biomarcadores"
    )
    nutritional_priorities: List[str] = Field(
        ..., description="Prioridades nutricionales basadas en biomarcadores"
    )
    supplement_considerations: Optional[List[str]] = Field(
        None, description="Consideraciones sobre suplementación"
    )


# Modelos para la skill de planificación de crononutrición
class PlanChrononutritionInput(BaseModel):
    """Esquema de entrada para la skill de planificación de crononutrición."""
    input_text: str = Field(..., description="Texto de entrada del usuario")
    user_profile: Optional[Dict[str, Any]] = Field(
        None, description="Perfil del usuario con información relevante"
    )
    daily_schedule: Optional[Dict[str, Any]] = Field(
        None, description="Horario diario del usuario"
    )
    training_schedule: Optional[Dict[str, Any]] = Field(
        None, description="Horario de entrenamiento del usuario"
    )
    sleep_pattern: Optional[Dict[str, Any]] = Field(
        None, description="Patrón de sueño del usuario"
    )


class NutritionTimeWindow(BaseModel):
    """Modelo para una ventana de tiempo nutricional."""
    name: str = Field(..., description="Nombre de la ventana (ej. 'Alimentación', 'Ayuno')")
    start_time: str = Field(..., description="Hora de inicio")
    end_time: str = Field(..., description="Hora de fin")
    description: str = Field(..., description="Descripción de la ventana")
    nutritional_focus: List[str] = Field(
        ..., description="Enfoque nutricional para esta ventana"
    )
    recommended_foods: Optional[List[str]] = Field(
        None, description="Alimentos recomendados"
    )
    foods_to_avoid: Optional[List[str]] = Field(
        None, description="Alimentos a evitar"
    )


class PlanChrononutritionOutput(BaseModel):
    """Esquema de salida para la skill de planificación de crononutrición."""
    time_windows: List[NutritionTimeWindow] = Field(
        ..., description="Ventanas de tiempo nutricionales"
    )
    fasting_period: Optional[str] = Field(
        None, description="Período de ayuno recomendado"
    )
    eating_period: Optional[str] = Field(
        None, description="Período de alimentación recomendado"
    )
    pre_workout_nutrition: Optional[Dict[str, Any]] = Field(
        None, description="Nutrición pre-entrenamiento"
    )
    post_workout_nutrition: Optional[Dict[str, Any]] = Field(
        None, description="Nutrición post-entrenamiento"
    )
    general_recommendations: str = Field(
        ..., description="Recomendaciones generales de crononutrición"
    )


# Artefactos
class MealPlanArtifact(BaseModel):
    """Artefacto para un plan de comidas."""
    plan_id: str = Field(..., description="ID único del plan de comidas")
    created_at: str = Field(..., description="Timestamp de creación")
    total_meals: int = Field(..., description="Número total de comidas")
    calories: Optional[int] = Field(None, description="Calorías totales")
    user_goals: Optional[List[str]] = Field(None, description="Objetivos del usuario")


class SupplementRecommendationArtifact(BaseModel):
    """Artefacto para recomendaciones de suplementos."""
    recommendation_id: str = Field(..., description="ID único de la recomendación")
    created_at: str = Field(..., description="Timestamp de creación")
    supplement_count: int = Field(..., description="Número de suplementos recomendados")
    based_on_biomarkers: bool = Field(
        ..., description="Si se basó en biomarcadores"
    )


class BiomarkerAnalysisArtifact(BaseModel):
    """Artefacto para análisis de biomarcadores."""
    analysis_id: str = Field(..., description="ID único del análisis")
    created_at: str = Field(..., description="Timestamp de creación")
    biomarker_count: int = Field(..., description="Número de biomarcadores analizados")
    critical_findings: bool = Field(
        ..., description="Si se encontraron hallazgos críticos"
    )


class ChrononutritionPlanArtifact(BaseModel):
    """Artefacto para un plan de crononutrición."""
    plan_id: str = Field(..., description="ID único del plan")
    created_at: str = Field(..., description="Timestamp de creación")
    window_count: int = Field(..., description="Número de ventanas nutricionales")
    fasting_hours: Optional[int] = Field(
        None, description="Horas de ayuno recomendadas"
    )

"""
Esquemas para el agente MotivationBehaviorCoach.

Este módulo define los modelos Pydantic para las entradas y salidas
de las skills del agente MotivationBehaviorCoach.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# Modelos para Formación de Hábitos
class HabitFormationInput(BaseModel):
    """Modelo para la entrada de la skill de formación de hábitos."""
    user_input: str = Field(..., description="Texto de entrada del usuario")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    session_id: Optional[str] = Field(None, description="ID de la sesión")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")


class HabitStep(BaseModel):
    """Modelo para un paso en el plan de hábitos."""
    description: str = Field(..., description="Descripción del paso")
    timeframe: str = Field(..., description="Marco temporal para completar el paso")
    difficulty: Optional[str] = Field(None, description="Nivel de dificultad del paso")


class HabitPlan(BaseModel):
    """Modelo para un plan de hábitos."""
    habit_name: str = Field(..., description="Nombre del hábito a formar")
    cue: str = Field(..., description="Señal o disparador para el hábito")
    routine: str = Field(..., description="Rutina o acción a realizar")
    reward: str = Field(..., description="Recompensa por completar el hábito")
    implementation_intention: str = Field(..., description="Intención de implementación (Cuando X, haré Y)")
    steps: List[HabitStep] = Field(..., description="Pasos para formar el hábito")
    tracking_method: str = Field(..., description="Método para hacer seguimiento del hábito")


class HabitFormationOutput(BaseModel):
    """Modelo para la salida de la skill de formación de hábitos."""
    habit_plan: HabitPlan = Field(..., description="Plan de hábitos generado")
    tips: List[str] = Field(..., description="Consejos para la formación de hábitos")
    obstacles: List[Dict[str, str]] = Field(..., description="Posibles obstáculos y estrategias para superarlos")
    consistency_strategies: List[str] = Field(..., description="Estrategias para mantener la consistencia")


# Modelos para Establecimiento de Metas
class GoalSettingInput(BaseModel):
    """Modelo para la entrada de la skill de establecimiento de metas."""
    user_input: str = Field(..., description="Texto de entrada del usuario")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    session_id: Optional[str] = Field(None, description="ID de la sesión")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")


class SmartGoal(BaseModel):
    """Modelo para una meta SMART."""
    specific: str = Field(..., description="Específico - Qué quieres lograr exactamente")
    measurable: str = Field(..., description="Medible - Cómo sabrás que has alcanzado la meta")
    achievable: str = Field(..., description="Alcanzable - Por qué es realista")
    relevant: str = Field(..., description="Relevante - Por qué es importante para ti")
    time_bound: str = Field(..., description="Limitado en tiempo - Cuándo quieres lograrlo")


class Milestone(BaseModel):
    """Modelo para un hito en el plan de metas."""
    description: str = Field(..., description="Descripción del hito")
    target_date: str = Field(..., description="Fecha objetivo para alcanzar el hito")
    metrics: str = Field(..., description="Métricas para medir el éxito")


class Timeline(BaseModel):
    """Modelo para la línea de tiempo del plan de metas."""
    start_date: str = Field(..., description="Fecha de inicio")
    end_date: str = Field(..., description="Fecha de finalización")
    key_dates: List[str] = Field(..., description="Fechas clave en el proceso")


class Obstacle(BaseModel):
    """Modelo para un obstáculo en el plan de metas."""
    description: str = Field(..., description="Descripción del obstáculo")
    strategy: str = Field(..., description="Estrategia para superar el obstáculo")


class TrackingSystem(BaseModel):
    """Modelo para el sistema de seguimiento del plan de metas."""
    frequency: str = Field(..., description="Frecuencia de seguimiento")
    method: str = Field(..., description="Método de seguimiento")
    review_points: List[str] = Field(..., description="Puntos de revisión")


class GoalPlan(BaseModel):
    """Modelo para un plan de metas."""
    main_goal: SmartGoal = Field(..., description="Meta principal en formato SMART")
    purpose: str = Field(..., description="Propósito o razón profunda para alcanzar la meta")
    milestones: List[Milestone] = Field(..., description="Hitos o submetas")
    timeline: Timeline = Field(..., description="Línea de tiempo")
    resources: List[str] = Field(..., description="Recursos necesarios")
    obstacles: List[Obstacle] = Field(..., description="Posibles obstáculos y estrategias")
    tracking: TrackingSystem = Field(..., description="Sistema de seguimiento")


class GoalSettingOutput(BaseModel):
    """Modelo para la salida de la skill de establecimiento de metas."""
    goal_plan: GoalPlan = Field(..., description="Plan de metas generado")


# Modelos para Estrategias de Motivación
class MotivationStrategiesInput(BaseModel):
    """Modelo para la entrada de la skill de estrategias de motivación."""
    user_input: str = Field(..., description="Texto de entrada del usuario")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    session_id: Optional[str] = Field(None, description="ID de la sesión")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")


class MotivationStrategy(BaseModel):
    """Modelo para una estrategia de motivación."""
    name: str = Field(..., description="Nombre de la estrategia")
    description: str = Field(..., description="Descripción detallada")
    implementation: str = Field(..., description="Cómo implementar la estrategia")
    science_behind: str = Field(..., description="Ciencia detrás de la estrategia")
    example: str = Field(..., description="Ejemplo de aplicación")


class MotivationStrategiesOutput(BaseModel):
    """Modelo para la salida de la skill de estrategias de motivación."""
    analysis: str = Field(..., description="Análisis de la situación motivacional")
    strategies: List[MotivationStrategy] = Field(..., description="Estrategias de motivación recomendadas")
    daily_practices: List[str] = Field(..., description="Prácticas diarias recomendadas")
    long_term_approach: str = Field(..., description="Enfoque a largo plazo")


# Modelos para Cambio de Comportamiento
class BehaviorChangeInput(BaseModel):
    """Modelo para la entrada de la skill de cambio de comportamiento."""
    user_input: str = Field(..., description="Texto de entrada del usuario")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    session_id: Optional[str] = Field(None, description="ID de la sesión")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")


class BehaviorChangeStage(BaseModel):
    """Modelo para una etapa en el plan de cambio de comportamiento."""
    stage_name: str = Field(..., description="Nombre de la etapa")
    description: str = Field(..., description="Descripción de la etapa")
    strategies: List[str] = Field(..., description="Estrategias para esta etapa")
    duration: str = Field(..., description="Duración estimada")
    success_indicators: List[str] = Field(..., description="Indicadores de éxito")


class BehaviorChangePlan(BaseModel):
    """Modelo para un plan de cambio de comportamiento."""
    target_behavior: str = Field(..., description="Comportamiento objetivo a cambiar")
    current_state: str = Field(..., description="Estado actual del comportamiento")
    desired_state: str = Field(..., description="Estado deseado del comportamiento")
    stages: List[BehaviorChangeStage] = Field(..., description="Etapas del cambio")
    psychological_techniques: List[str] = Field(..., description="Técnicas psicológicas recomendadas")
    environmental_adjustments: List[str] = Field(..., description="Ajustes ambientales recomendados")
    support_systems: List[str] = Field(..., description="Sistemas de apoyo recomendados")


class BehaviorChangeOutput(BaseModel):
    """Modelo para la salida de la skill de cambio de comportamiento."""
    behavior_plan: BehaviorChangePlan = Field(..., description="Plan de cambio de comportamiento")
    estimated_timeline: str = Field(..., description="Línea de tiempo estimada")
    success_probability_factors: List[str] = Field(..., description="Factores que afectan la probabilidad de éxito")


# Modelos para Gestión de Obstáculos
class ObstacleManagementInput(BaseModel):
    """Modelo para la entrada de la skill de gestión de obstáculos."""
    user_input: str = Field(..., description="Texto de entrada del usuario")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    session_id: Optional[str] = Field(None, description="ID de la sesión")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Perfil del usuario")


class ObstacleAnalysis(BaseModel):
    """Modelo para el análisis de un obstáculo."""
    nature: str = Field(..., description="Naturaleza del obstáculo")
    impact: str = Field(..., description="Impacto del obstáculo")
    frequency: str = Field(..., description="Frecuencia con la que aparece")
    triggers: List[str] = Field(..., description="Desencadenantes del obstáculo")
    past_attempts: Optional[str] = Field(None, description="Intentos pasados para superarlo")


class ObstacleSolution(BaseModel):
    """Modelo para una solución a un obstáculo."""
    strategy: str = Field(..., description="Estrategia para superar el obstáculo")
    implementation: str = Field(..., description="Cómo implementar la estrategia")
    expected_outcome: str = Field(..., description="Resultado esperado")
    alternative_approaches: List[str] = Field(..., description="Enfoques alternativos")
    resources_needed: List[str] = Field(..., description="Recursos necesarios")


class ObstacleManagementOutput(BaseModel):
    """Modelo para la salida de la skill de gestión de obstáculos."""
    obstacle_analysis: ObstacleAnalysis = Field(..., description="Análisis del obstáculo")
    primary_solution: ObstacleSolution = Field(..., description="Solución principal")
    alternative_solutions: List[ObstacleSolution] = Field(..., description="Soluciones alternativas")
    prevention_strategies: List[str] = Field(..., description="Estrategias de prevención")
    mindset_adjustments: List[str] = Field(..., description="Ajustes de mentalidad recomendados")


# Artefactos para las skills
class HabitPlanArtifact(BaseModel):
    """Artefacto para el plan de hábitos."""
    habit_plan: HabitPlan = Field(..., description="Plan de hábitos")
    tips: List[str] = Field(..., description="Consejos para la formación de hábitos")
    obstacles: List[Dict[str, str]] = Field(..., description="Obstáculos y estrategias")


class GoalPlanArtifact(BaseModel):
    """Artefacto para el plan de metas."""
    goal_plan: GoalPlan = Field(..., description="Plan de metas")


class MotivationStrategiesArtifact(BaseModel):
    """Artefacto para las estrategias de motivación."""
    strategies: List[MotivationStrategy] = Field(..., description="Estrategias de motivación")
    analysis: str = Field(..., description="Análisis motivacional")


class BehaviorChangePlanArtifact(BaseModel):
    """Artefacto para el plan de cambio de comportamiento."""
    behavior_plan: BehaviorChangePlan = Field(..., description="Plan de cambio de comportamiento")


class ObstacleManagementArtifact(BaseModel):
    """Artefacto para la gestión de obstáculos."""
    obstacle_analysis: ObstacleAnalysis = Field(..., description="Análisis del obstáculo")
    solutions: List[ObstacleSolution] = Field(..., description="Soluciones propuestas")

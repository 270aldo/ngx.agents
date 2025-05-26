"""
Skills avanzadas de visión para agentes especializados.

Este módulo contiene skills reutilizables de visión que pueden ser
utilizadas por diferentes agentes para realizar análisis avanzados
de imágenes relacionadas con fitness y bienestar.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json

from core.skill import Skill
from core.logging_config import get_logger
from clients.vertex_ai.advanced_vision_client import AdvancedVisionClient
from infrastructure.adapters.vision_adapter import vision_adapter

logger = get_logger(__name__)


class PhysicalFormAnalysisSkill(Skill):
    """
    Skill para análisis avanzado de forma física desde imágenes.
    Utilizada principalmente por Progress Tracker y Elite Training Strategist.
    """

    def __init__(self, vision_client: Optional[AdvancedVisionClient] = None):
        super().__init__(
            name="physical_form_analysis",
            description="Analiza la forma física y composición corporal desde imágenes",
            parameters={
                "image": {"type": "string", "description": "Imagen en base64 o URL"},
                "user_profile": {
                    "type": "object",
                    "description": "Perfil del usuario",
                    "optional": True,
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Tipo de análisis: comprehensive, body_composition, symmetry",
                    "default": "comprehensive",
                },
            },
        )
        self.vision_client = vision_client or AdvancedVisionClient()

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Ejecuta el análisis de forma física."""
        try:
            image = kwargs.get("image")
            user_profile = kwargs.get("user_profile")
            analysis_type = kwargs.get("analysis_type", "comprehensive")

            if not image:
                return {
                    "status": "error",
                    "error": "No se proporcionó imagen para analizar",
                }

            # Realizar análisis
            result = await self.vision_client.analyze_physical_form(
                image_data=image, user_profile=user_profile, analysis_type=analysis_type
            )

            # Enriquecer con recomendaciones específicas
            if result.get("status") == "success":
                result["skill_metadata"] = {
                    "skill_name": self.name,
                    "execution_time": datetime.utcnow().isoformat(),
                    "confidence": result["analysis"]
                    .get("metadata", {})
                    .get("confidence_score", 0),
                }

            return result

        except Exception as e:
            logger.error(f"Error en PhysicalFormAnalysisSkill: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}


class ExercisePostureDetectionSkill(Skill):
    """
    Skill para detección y análisis de postura en ejercicios.
    Utilizada por Elite Training Strategist y Recovery Corrective.
    """

    def __init__(self, vision_client: Optional[AdvancedVisionClient] = None):
        super().__init__(
            name="exercise_posture_detection",
            description="Detecta y analiza la postura durante ejercicios",
            parameters={
                "image": {"type": "string", "description": "Imagen del ejercicio"},
                "exercise_name": {
                    "type": "string",
                    "description": "Nombre del ejercicio",
                },
                "expected_form": {
                    "type": "object",
                    "description": "Forma esperada del ejercicio",
                    "optional": True,
                },
            },
        )
        self.vision_client = vision_client or AdvancedVisionClient()

        # Base de datos de ejercicios comunes y su forma correcta
        self.exercise_database = self._load_exercise_database()

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Ejecuta la detección de postura en ejercicio."""
        try:
            image = kwargs.get("image")
            exercise_name = kwargs.get("exercise_name")
            expected_form = kwargs.get("expected_form")

            if not image or not exercise_name:
                return {
                    "status": "error",
                    "error": "Se requiere imagen y nombre del ejercicio",
                }

            # Si no se proporciona forma esperada, buscar en base de datos
            if not expected_form and exercise_name in self.exercise_database:
                expected_form = self.exercise_database[exercise_name]

            # Realizar análisis
            result = await self.vision_client.detect_exercise_posture(
                image_data=image,
                exercise_name=exercise_name,
                expected_form=expected_form,
            )

            # Añadir contexto adicional para el agente
            if result.get("status") == "success":
                result["exercise_context"] = {
                    "muscle_groups": self._get_muscle_groups(exercise_name),
                    "common_mistakes": self._get_common_mistakes(exercise_name),
                    "progression_options": self._get_progression_options(exercise_name),
                    "safety_priority": self._get_safety_priority(exercise_name),
                }

            return result

        except Exception as e:
            logger.error(f"Error en ExercisePostureDetectionSkill: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def _load_exercise_database(self) -> Dict[str, Dict[str, Any]]:
        """Carga la base de datos de ejercicios."""
        # En producción, esto vendría de una base de datos real
        return {
            "sentadilla": {
                "key_points": [
                    "Pies al ancho de hombros",
                    "Rodillas alineadas con pies",
                    "Espalda recta",
                    "Peso en talones",
                ],
                "joint_angles": {"hip": 90, "knee": 90, "ankle": 70},
            },
            "press_banca": {
                "key_points": [
                    "Escápulas retraídas",
                    "Arco natural en espalda",
                    "Pies firmes en suelo",
                    "Barra sobre pecho",
                ],
                "joint_angles": {"shoulder": 90, "elbow": 90},
            },
            # Más ejercicios...
        }

    def _get_muscle_groups(self, exercise_name: str) -> List[str]:
        """Obtiene los grupos musculares trabajados."""
        muscle_map = {
            "sentadilla": ["cuádriceps", "glúteos", "isquiotibiales", "core"],
            "press_banca": ["pectoral", "tríceps", "deltoides anterior"],
            # Más mapeos...
        }
        return muscle_map.get(exercise_name.lower(), ["múltiples grupos musculares"])

    def _get_common_mistakes(self, exercise_name: str) -> List[str]:
        """Obtiene errores comunes del ejercicio."""
        mistakes_map = {
            "sentadilla": [
                "Rodillas hacia adentro",
                "Talones levantados",
                "Espalda redondeada",
                "Descenso insuficiente",
            ],
            "press_banca": [
                "Codos muy abiertos",
                "Barra rebotando en pecho",
                "Pérdida de retracción escapular",
                "Pies en el aire",
            ],
            # Más errores...
        }
        return mistakes_map.get(exercise_name.lower(), [])

    def _get_progression_options(self, exercise_name: str) -> Dict[str, List[str]]:
        """Obtiene opciones de progresión y regresión."""
        progressions = {
            "sentadilla": {
                "easier": [
                    "sentadilla en caja",
                    "sentadilla asistida",
                    "media sentadilla",
                ],
                "harder": [
                    "sentadilla con pausa",
                    "sentadilla frontal",
                    "sentadilla búlgara",
                ],
            },
            "press_banca": {
                "easier": ["flexiones", "press con mancuernas", "press en máquina"],
                "harder": ["press con pausa", "press con cadenas", "press con déficit"],
            },
            # Más progresiones...
        }
        return progressions.get(exercise_name.lower(), {"easier": [], "harder": []})

    def _get_safety_priority(self, exercise_name: str) -> str:
        """Determina la prioridad de seguridad del ejercicio."""
        high_risk = ["sentadilla", "peso_muerto", "press_banca", "press_militar"]
        medium_risk = ["remo", "dominadas", "fondos", "prensa"]

        exercise_lower = exercise_name.lower()
        if any(ex in exercise_lower for ex in high_risk):
            return "high"
        elif any(ex in exercise_lower for ex in medium_risk):
            return "medium"
        else:
            return "low"


class ProgressTrackingSkill(Skill):
    """
    Skill para seguimiento visual de progreso a lo largo del tiempo.
    Utilizada principalmente por Progress Tracker.
    """

    def __init__(self, vision_client: Optional[AdvancedVisionClient] = None):
        super().__init__(
            name="visual_progress_tracking",
            description="Realiza seguimiento visual del progreso físico",
            parameters={
                "current_image": {"type": "string", "description": "Imagen actual"},
                "previous_images": {
                    "type": "array",
                    "description": "Lista de imágenes anteriores con metadatos",
                },
                "user_goals": {
                    "type": "object",
                    "description": "Objetivos del usuario",
                    "optional": True,
                },
            },
        )
        self.vision_client = vision_client or AdvancedVisionClient()

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Ejecuta el seguimiento de progreso visual."""
        try:
            current_image = kwargs.get("current_image")
            previous_images = kwargs.get("previous_images", [])
            user_goals = kwargs.get("user_goals")

            if not current_image:
                return {"status": "error", "error": "Se requiere imagen actual"}

            if not previous_images:
                return {
                    "status": "warning",
                    "message": "No hay imágenes previas para comparar",
                    "recommendation": "Toma fotos de progreso regularmente para mejor seguimiento",
                }

            # Realizar análisis de progreso
            result = await self.vision_client.track_visual_progress(
                current_image=current_image,
                previous_images=previous_images,
                user_goals=user_goals,
            )

            # Enriquecer con insights adicionales
            if result.get("status") == "success":
                result["insights"] = self._generate_progress_insights(
                    result["analysis"], user_goals
                )
                result["motivational_message"] = self._generate_motivation(
                    result["analysis"]
                )

            return result

        except Exception as e:
            logger.error(f"Error en ProgressTrackingSkill: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def _generate_progress_insights(
        self, analysis: Dict[str, Any], user_goals: Optional[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Genera insights del progreso."""
        insights = []

        # Analizar tendencias
        if analysis.get("progress_rate"):
            rate = analysis["progress_rate"]
            if rate > 0.8:
                insights.append(
                    {
                        "type": "positive",
                        "message": "¡Excelente progreso! Estás avanzando más rápido que el promedio.",
                    }
                )
            elif rate > 0.5:
                insights.append(
                    {
                        "type": "positive",
                        "message": "Buen progreso constante. Mantén la consistencia.",
                    }
                )
            else:
                insights.append(
                    {
                        "type": "neutral",
                        "message": "El progreso es gradual. Considera ajustar tu plan.",
                    }
                )

        # Comparar con objetivos
        if user_goals:
            goal_alignment = self._check_goal_alignment(analysis, user_goals)
            insights.extend(goal_alignment)

        return insights

    def _check_goal_alignment(
        self, analysis: Dict[str, Any], user_goals: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Verifica alineación con objetivos."""
        insights = []

        # Lógica de verificación de objetivos
        if user_goals.get("target_weight") and analysis.get("estimated_weight_change"):
            progress_percentage = (
                analysis["estimated_weight_change"] / user_goals["target_weight"]
            ) * 100

            insights.append(
                {
                    "type": "info",
                    "message": f"Has alcanzado aproximadamente el {progress_percentage:.1f}% de tu objetivo de peso",
                }
            )

        return insights

    def _generate_motivation(self, analysis: Dict[str, Any]) -> str:
        """Genera mensaje motivacional basado en el progreso."""
        messages = {
            "excellent": "¡Increíble trabajo! Tu dedicación está dando resultados visibles. 💪",
            "good": "¡Sigue así! Cada día te acercas más a tus objetivos. 🎯",
            "moderate": "El progreso toma tiempo. ¡No te rindas, estás en el camino correcto! 🌟",
            "slow": "Recuerda: el progreso no siempre es lineal. ¡Mantén la consistencia! 💫",
        }

        # Determinar categoría basada en análisis
        progress_category = "moderate"  # Por defecto
        if analysis.get("overall_progress_score", 0) > 80:
            progress_category = "excellent"
        elif analysis.get("overall_progress_score", 0) > 60:
            progress_category = "good"
        elif analysis.get("overall_progress_score", 0) < 30:
            progress_category = "slow"

        return messages.get(progress_category, messages["moderate"])


class NutritionalLabelExtractionSkill(Skill):
    """
    Skill para extracción de información nutricional de etiquetas.
    Utilizada por Precision Nutrition Architect.
    """

    def __init__(self, vision_client: Optional[AdvancedVisionClient] = None):
        super().__init__(
            name="nutritional_label_extraction",
            description="Extrae información nutricional de etiquetas de alimentos",
            parameters={
                "image": {"type": "string", "description": "Imagen de la etiqueta"},
                "language": {
                    "type": "string",
                    "description": "Idioma de la etiqueta",
                    "default": "es",
                },
                "extract_ingredients": {
                    "type": "boolean",
                    "description": "Extraer lista de ingredientes",
                    "default": True,
                },
            },
        )
        self.vision_client = vision_client or AdvancedVisionClient()

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Ejecuta la extracción de información nutricional."""
        try:
            image = kwargs.get("image")
            language = kwargs.get("language", "es")
            extract_ingredients = kwargs.get("extract_ingredients", True)

            if not image:
                return {"status": "error", "error": "Se requiere imagen de la etiqueta"}

            # Realizar extracción
            result = await self.vision_client.extract_nutritional_info(
                image_data=image,
                language=language,
                extract_ingredients=extract_ingredients,
            )

            # Enriquecer con análisis nutricional
            if result.get("status") == "success":
                nutritional_info = result["nutritional_info"]
                result["nutritional_analysis"] = self._analyze_nutritional_quality(
                    nutritional_info
                )
                result["meal_suggestions"] = self._generate_meal_suggestions(
                    nutritional_info
                )
                result["portion_recommendations"] = (
                    self._calculate_portion_recommendations(nutritional_info)
                )

            return result

        except Exception as e:
            logger.error(
                f"Error en NutritionalLabelExtractionSkill: {e}", exc_info=True
            )
            return {"status": "error", "error": str(e)}

    def _analyze_nutritional_quality(
        self, nutritional_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analiza la calidad nutricional del producto."""
        quality_score = 0
        factors = []

        # Evaluar proteína
        protein_percentage = nutritional_info.get("calculated_metrics", {}).get(
            "protein_percentage", 0
        )
        if protein_percentage > 20:
            quality_score += 25
            factors.append({"factor": "high_protein", "positive": True})
        elif protein_percentage > 15:
            quality_score += 15
            factors.append({"factor": "moderate_protein", "positive": True})

        # Evaluar fibra
        fiber_adequacy = nutritional_info.get("calculated_metrics", {}).get(
            "fiber_adequacy", "low"
        )
        if fiber_adequacy in ["excellent", "good"]:
            quality_score += 20
            factors.append({"factor": "good_fiber", "positive": True})

        # Evaluar azúcar
        sugar_ratio = nutritional_info.get("calculated_metrics", {}).get(
            "sugar_to_carb_ratio", 1
        )
        if sugar_ratio < 0.3:
            quality_score += 20
            factors.append({"factor": "low_sugar", "positive": True})
        elif sugar_ratio > 0.5:
            quality_score -= 10
            factors.append({"factor": "high_sugar", "positive": False})

        # Evaluar sodio
        sodium_level = nutritional_info.get("calculated_metrics", {}).get(
            "sodium_level", "high"
        )
        if sodium_level in ["low", "moderate"]:
            quality_score += 15
            factors.append({"factor": "controlled_sodium", "positive": True})
        elif sodium_level == "very_high":
            quality_score -= 10
            factors.append({"factor": "excessive_sodium", "positive": False})

        # Evaluar grasas trans
        trans_fat = nutritional_info.get("trans_fat_g", 0)
        if trans_fat == 0:
            quality_score += 20
            factors.append({"factor": "no_trans_fat", "positive": True})
        else:
            quality_score -= 20
            factors.append({"factor": "contains_trans_fat", "positive": False})

        return {
            "quality_score": max(0, min(100, quality_score)),
            "quality_grade": self._calculate_grade(quality_score),
            "factors": factors,
            "summary": self._generate_quality_summary(quality_score, factors),
        }

    def _calculate_grade(self, score: int) -> str:
        """Calcula la calificación basada en el puntaje."""
        if score >= 80:
            return "A"
        elif score >= 60:
            return "B"
        elif score >= 40:
            return "C"
        elif score >= 20:
            return "D"
        else:
            return "F"

    def _generate_quality_summary(self, score: int, factors: List[Dict]) -> str:
        """Genera un resumen de la calidad nutricional."""
        if score >= 80:
            return "Excelente opción nutricional con buen balance de macronutrientes"
        elif score >= 60:
            return "Buena opción con algunos aspectos a considerar"
        elif score >= 40:
            return "Opción moderada, consumir con moderación"
        else:
            return "Opción de baja calidad nutricional, limitar consumo"

    def _generate_meal_suggestions(
        self, nutritional_info: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Genera sugerencias de comidas basadas en la información nutricional."""
        suggestions = []

        # Basado en el perfil de macros
        protein_percentage = nutritional_info.get("calculated_metrics", {}).get(
            "protein_percentage", 0
        )

        if protein_percentage < 15:
            suggestions.append(
                {
                    "type": "complement",
                    "suggestion": "Combinar con fuente de proteína magra (pollo, pescado, legumbres)",
                }
            )

        fiber_adequacy = nutritional_info.get("calculated_metrics", {}).get(
            "fiber_adequacy", "low"
        )
        if fiber_adequacy == "low":
            suggestions.append(
                {
                    "type": "complement",
                    "suggestion": "Añadir vegetales frescos o ensalada para aumentar fibra",
                }
            )

        return suggestions

    def _calculate_portion_recommendations(
        self, nutritional_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula recomendaciones de porciones para diferentes objetivos."""
        calories_per_serving = nutritional_info.get("calories", 0)

        return {
            "weight_loss": {
                "portions": (
                    max(0.5, min(1.0, 200 / calories_per_serving))
                    if calories_per_serving > 0
                    else 1
                ),
                "calories": min(200, calories_per_serving),
                "frequency": (
                    "1-2 veces por semana"
                    if calories_per_serving > 300
                    else "3-4 veces por semana"
                ),
            },
            "maintenance": {
                "portions": 1.0,
                "calories": calories_per_serving,
                "frequency": "según plan nutricional",
            },
            "muscle_gain": {
                "portions": (
                    max(1.0, min(2.0, 400 / calories_per_serving))
                    if calories_per_serving > 0
                    else 1
                ),
                "calories": min(400, calories_per_serving * 1.5),
                "frequency": "diariamente si encaja en macros",
            },
        }


class BodyMeasurementExtractionSkill(Skill):
    """
    Skill para extraer medidas corporales estimadas de imágenes.
    Utilizada por Progress Tracker y Biometrics Insight Engine.
    """

    def __init__(self, vision_client: Optional[AdvancedVisionClient] = None):
        super().__init__(
            name="body_measurement_extraction",
            description="Extrae medidas corporales estimadas de imágenes",
            parameters={
                "image": {"type": "string", "description": "Imagen corporal"},
                "reference_height": {
                    "type": "number",
                    "description": "Altura de referencia en cm",
                    "optional": True,
                },
                "previous_measurements": {
                    "type": "object",
                    "description": "Medidas anteriores para calibración",
                    "optional": True,
                },
            },
        )
        self.vision_client = vision_client or AdvancedVisionClient()

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Ejecuta la extracción de medidas corporales."""
        try:
            image = kwargs.get("image")
            reference_height = kwargs.get("reference_height")
            previous_measurements = kwargs.get("previous_measurements")

            if not image:
                return {"status": "error", "error": "Se requiere imagen para análisis"}

            # Prompt especializado para estimación de medidas
            prompt = f"""
            Analiza esta imagen corporal y proporciona estimaciones de medidas.
            
            {"Altura de referencia: " + str(reference_height) + " cm" if reference_height else ""}
            {"Medidas previas para calibración: " + json.dumps(previous_measurements) if previous_measurements else ""}
            
            Estima las siguientes medidas (en cm):
            
            1. **Circunferencias**:
               - Cuello
               - Hombros
               - Pecho/Busto
               - Brazo (bíceps)
               - Antebrazo
               - Cintura
               - Cadera
               - Muslo
               - Pantorrilla
            
            2. **Proporciones Corporales**:
               - Ratio cintura/cadera
               - Ratio hombros/cintura
               - Índice de simetría (izq/der)
            
            3. **Estimación de Composición**:
               - Porcentaje de grasa corporal visual
               - Masa muscular relativa (bajo/medio/alto)
               - Tipo de distribución de grasa
            
            Proporciona las estimaciones en formato JSON con rangos de confianza.
            Indica claramente que son estimaciones visuales, no medidas exactas.
            """

            # Realizar análisis
            result = await self.vision_client.analyze_image(
                image_data=image, prompt=prompt, temperature=0.3
            )

            # Parsear y validar medidas
            measurements = self._parse_measurements(result)

            # Calcular cambios si hay medidas previas
            if previous_measurements:
                measurements["changes"] = self._calculate_measurement_changes(
                    measurements, previous_measurements
                )

            return {
                "status": "success",
                "measurements": measurements,
                "disclaimer": "Estas son estimaciones visuales. Para medidas precisas, use cinta métrica.",
                "recommendations": self._generate_measurement_recommendations(
                    measurements
                ),
            }

        except Exception as e:
            logger.error(f"Error en BodyMeasurementExtractionSkill: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def _parse_measurements(self, result: Union[str, Dict]) -> Dict[str, Any]:
        """Parsea las medidas del resultado de visión."""
        # Implementación básica de parsing
        try:
            if isinstance(result, str):
                # Intentar extraer JSON del string
                import re

                json_match = re.search(r"\{.*\}", result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            elif isinstance(result, dict):
                return result.get("measurements", {})
        except:
            pass

        # Retornar estructura vacía si falla
        return {"circumferences": {}, "proportions": {}, "composition": {}}

    def _calculate_measurement_changes(
        self, current: Dict[str, Any], previous: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula cambios en las medidas."""
        changes = {}

        # Comparar circunferencias
        current_circ = current.get("circumferences", {})
        previous_circ = previous.get("circumferences", {})

        for measure, value in current_circ.items():
            if measure in previous_circ and isinstance(value, (int, float)):
                prev_value = previous_circ[measure]
                if isinstance(prev_value, (int, float)):
                    change = value - prev_value
                    change_percent = (
                        (change / prev_value * 100) if prev_value != 0 else 0
                    )
                    changes[measure] = {
                        "absolute": round(change, 1),
                        "percentage": round(change_percent, 1),
                    }

        return changes

    def _generate_measurement_recommendations(
        self, measurements: Dict[str, Any]
    ) -> List[str]:
        """Genera recomendaciones basadas en las medidas."""
        recommendations = []

        # Analizar proporciones
        proportions = measurements.get("proportions", {})

        # Ratio cintura/cadera
        waist_hip_ratio = proportions.get("waist_hip_ratio")
        if waist_hip_ratio:
            if waist_hip_ratio > 0.95:  # Hombres
                recommendations.append(
                    "Ratio cintura/cadera elevado. Considera enfocarte en reducción de grasa abdominal."
                )
            elif waist_hip_ratio > 0.85:  # Mujeres
                recommendations.append(
                    "Ratio cintura/cadera en límite superior. Mantén hábitos saludables."
                )

        # Simetría
        symmetry_index = proportions.get("symmetry_index")
        if symmetry_index and symmetry_index < 0.95:
            recommendations.append(
                "Se detecta asimetría. Considera ejercicios unilaterales para balance."
            )

        return recommendations


# Funciones de utilidad para los skills


def create_vision_skill_suite() -> Dict[str, Skill]:
    """
    Crea un conjunto completo de skills de visión para usar en agentes.
    """
    vision_client = AdvancedVisionClient()

    return {
        "physical_form_analysis": PhysicalFormAnalysisSkill(vision_client),
        "exercise_posture_detection": ExercisePostureDetectionSkill(vision_client),
        "progress_tracking": ProgressTrackingSkill(vision_client),
        "nutritional_label_extraction": NutritionalLabelExtractionSkill(vision_client),
        "body_measurement_extraction": BodyMeasurementExtractionSkill(vision_client),
    }


def get_vision_skill_for_agent(agent_type: str) -> List[Skill]:
    """
    Obtiene las skills de visión apropiadas para un tipo de agente específico.
    """
    skill_mapping = {
        "progress_tracker": [
            "physical_form_analysis",
            "progress_tracking",
            "body_measurement_extraction",
        ],
        "elite_training_strategist": [
            "exercise_posture_detection",
            "physical_form_analysis",
        ],
        "precision_nutrition_architect": ["nutritional_label_extraction"],
        "recovery_corrective": ["exercise_posture_detection", "physical_form_analysis"],
        "biometrics_insight_engine": [
            "body_measurement_extraction",
            "physical_form_analysis",
        ],
    }

    skills = create_vision_skill_suite()
    agent_skills = skill_mapping.get(agent_type, [])

    return [skills[skill_name] for skill_name in agent_skills if skill_name in skills]

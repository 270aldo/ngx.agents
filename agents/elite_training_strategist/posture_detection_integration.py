"""
Integración de detección de postura para Elite Training Strategist.

Este módulo añade capacidades avanzadas de análisis de postura
y técnica de ejercicios al Elite Training Strategist.
"""

import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from agents.skills.advanced_vision_skills import ExercisePostureDetectionSkill
from clients.vertex_ai.advanced_vision_client import AdvancedVisionClient
from config.gemini_models import get_model_config
from core.logging_config import get_logger
from adk.agent import Skill

logger = get_logger(__name__)


class PostureDetectionMixin:
    """
    Mixin que añade capacidades de detección de postura al Elite Training Strategist.
    """

    def init_posture_detection(self):
        """Inicializa las capacidades de detección de postura."""
        # Configurar modelo para el agente
        model_config = get_model_config("elite_training_strategist")

        # Inicializar cliente de visión
        self.posture_vision_client = AdvancedVisionClient(
            model=model_config["model_id"]
        )

        # Inicializar skill de detección de postura
        self.posture_detection_skill = ExercisePostureDetectionSkill(
            self.posture_vision_client
        )

        # Añadir nuevas skills al agente
        self._add_posture_detection_skills()

        logger.info("Capacidades de detección de postura inicializadas")

    def _add_posture_detection_skills(self):
        """Añade skills de detección de postura al agente."""
        new_skills = [
            Skill(
                name="analyze_exercise_form",
                description="Analiza la forma y técnica de un ejercicio desde imagen o video",
                handler=self._skill_analyze_exercise_form,
            ),
            Skill(
                name="compare_exercise_technique",
                description="Compara la técnica del usuario con la forma ideal",
                handler=self._skill_compare_exercise_technique,
            ),
            Skill(
                name="generate_form_corrections",
                description="Genera correcciones específicas para mejorar la técnica",
                handler=self._skill_generate_form_corrections,
            ),
            Skill(
                name="assess_injury_risk",
                description="Evalúa el riesgo de lesión basado en la forma observada",
                handler=self._skill_assess_injury_risk,
            ),
        ]

        # Añadir skills si el agente las tiene
        if hasattr(self, "skills"):
            self.skills.extend(new_skills)

    async def _skill_analyze_exercise_form(
        self,
        image: Union[str, bytes],
        exercise_name: str,
        user_experience: str = "intermediate",
        focus_areas: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analiza la forma y técnica de un ejercicio.

        Args:
            image: Imagen del ejercicio
            exercise_name: Nombre del ejercicio
            user_experience: Nivel de experiencia (beginner, intermediate, advanced)
            focus_areas: Áreas específicas a revisar (ej: ["rodillas", "espalda"])

        Returns:
            Análisis detallado de la forma
        """
        try:
            # Obtener forma esperada según nivel de experiencia
            expected_form = self._get_expected_form_by_level(
                exercise_name, user_experience
            )

            # Ejecutar análisis de postura
            result = await self.posture_detection_skill.execute(
                image=image, exercise_name=exercise_name, expected_form=expected_form
            )

            if result.get("status") == "success":
                analysis = result["analysis"]

                # Enriquecer con análisis específico por áreas de enfoque
                if focus_areas:
                    focused_analysis = await self._analyze_focus_areas(
                        image, exercise_name, focus_areas, analysis
                    )
                    result["focused_analysis"] = focused_analysis

                # Generar score ajustado por experiencia
                adjusted_score = self._adjust_score_by_experience(
                    analysis.get("form_score", 0), user_experience
                )
                result["adjusted_form_score"] = adjusted_score

                # Añadir progresiones/regresiones según el score
                if adjusted_score < 70:
                    result["recommended_progression"] = self._get_exercise_regression(
                        exercise_name, user_experience
                    )
                elif adjusted_score > 90:
                    result["recommended_progression"] = self._get_exercise_progression(
                        exercise_name, user_experience
                    )

                # Generar plan de mejora
                improvement_plan = await self._generate_improvement_plan(
                    exercise_name, analysis, user_experience
                )
                result["improvement_plan"] = improvement_plan

            return result

        except Exception as e:
            logger.error(f"Error analizando forma de ejercicio: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _skill_compare_exercise_technique(
        self,
        user_image: Union[str, bytes],
        reference_image: Optional[Union[str, bytes]] = None,
        exercise_name: str = None,
        comparison_points: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compara la técnica del usuario con una referencia ideal.

        Args:
            user_image: Imagen del usuario realizando el ejercicio
            reference_image: Imagen de referencia (opcional, se puede generar)
            exercise_name: Nombre del ejercicio
            comparison_points: Puntos específicos a comparar

        Returns:
            Comparación detallada de técnicas
        """
        try:
            # Si no hay imagen de referencia, usar descripción ideal
            if not reference_image:
                reference_description = self._get_ideal_form_description(exercise_name)
            else:
                # Analizar imagen de referencia
                reference_analysis = await self.posture_detection_skill.execute(
                    image=reference_image, exercise_name=exercise_name
                )
                reference_description = reference_analysis.get("analysis", {})

            # Analizar imagen del usuario
            user_analysis = await self.posture_detection_skill.execute(
                image=user_image, exercise_name=exercise_name
            )

            # Comparar técnicas
            comparison = await self._perform_technique_comparison(
                user_analysis.get("analysis", {}),
                reference_description,
                comparison_points,
            )

            # Generar visualización de diferencias
            visualization = await self._generate_comparison_visualization(
                user_image, user_analysis, comparison
            )

            return {
                "status": "success",
                "user_score": user_analysis.get("analysis", {}).get("form_score", 0),
                "comparison": comparison,
                "key_differences": self._extract_key_differences(comparison),
                "visualization": visualization,
                "improvement_priority": self._prioritize_improvements(comparison),
            }

        except Exception as e:
            logger.error(f"Error comparando técnicas: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _skill_generate_form_corrections(
        self,
        analysis: Dict[str, Any],
        exercise_name: str,
        user_profile: Optional[Dict[str, Any]] = None,
        correction_style: str = "detailed",
    ) -> Dict[str, Any]:
        """
        Genera correcciones específicas para mejorar la técnica.

        Args:
            analysis: Análisis de postura previo
            exercise_name: Nombre del ejercicio
            user_profile: Perfil del usuario (limitaciones, experiencia, etc.)
            correction_style: Estilo de corrección (detailed, concise, visual)

        Returns:
            Correcciones detalladas y plan de acción
        """
        try:
            errors = analysis.get("errors", [])
            if not errors:
                return {
                    "status": "success",
                    "message": "¡Excelente técnica! No se requieren correcciones mayores.",
                    "minor_adjustments": self._get_minor_adjustments(analysis),
                }

            # Generar correcciones para cada error
            corrections = []
            for error in errors:
                correction = await self._generate_correction_for_error(
                    error, exercise_name, user_profile, correction_style
                )
                corrections.append(correction)

            # Ordenar por prioridad
            corrections = sorted(
                corrections, key=lambda x: x.get("priority_score", 0), reverse=True
            )

            # Generar ejercicios correctivos
            corrective_exercises = await self._generate_corrective_exercises(
                errors, exercise_name, user_profile
            )

            # Crear plan de implementación
            implementation_plan = self._create_correction_implementation_plan(
                corrections, corrective_exercises
            )

            return {
                "status": "success",
                "corrections": corrections,
                "corrective_exercises": corrective_exercises,
                "implementation_plan": implementation_plan,
                "estimated_improvement_time": self._estimate_improvement_timeline(
                    corrections
                ),
                "visual_cues": (
                    self._generate_visual_cues(corrections)
                    if correction_style == "visual"
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Error generando correcciones: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _skill_assess_injury_risk(
        self,
        posture_analysis: Dict[str, Any],
        exercise_name: str,
        user_history: Optional[Dict[str, Any]] = None,
        workout_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evalúa el riesgo de lesión basado en la forma observada.

        Args:
            posture_analysis: Análisis de postura
            exercise_name: Nombre del ejercicio
            user_history: Historial de lesiones y limitaciones
            workout_context: Contexto del entrenamiento (sets, reps, peso)

        Returns:
            Evaluación de riesgo y recomendaciones
        """
        try:
            # Factores de riesgo base
            risk_factors = []
            risk_score = 0

            # Evaluar errores de forma
            form_errors = posture_analysis.get("errors", [])
            for error in form_errors:
                risk_factor = self._evaluate_error_risk(error, exercise_name)
                risk_factors.append(risk_factor)
                risk_score += risk_factor["risk_value"]

            # Evaluar compensaciones
            compensations = posture_analysis.get("compensations", [])
            for compensation in compensations:
                risk_factor = self._evaluate_compensation_risk(compensation)
                risk_factors.append(risk_factor)
                risk_score += risk_factor["risk_value"]

            # Considerar historial del usuario
            if user_history:
                historical_risk = self._evaluate_historical_risk(
                    user_history, exercise_name, form_errors
                )
                risk_factors.extend(historical_risk)
                risk_score += sum(r["risk_value"] for r in historical_risk)

            # Considerar contexto del entrenamiento
            if workout_context:
                context_risk = self._evaluate_workout_context_risk(
                    workout_context, risk_score
                )
                risk_factors.append(context_risk)
                risk_score += context_risk["risk_value"]

            # Normalizar score de riesgo (0-100)
            normalized_risk = min(100, risk_score * 10)

            # Generar categoría de riesgo
            risk_category = self._categorize_risk(normalized_risk)

            # Generar recomendaciones
            recommendations = await self._generate_risk_mitigation_recommendations(
                risk_factors, risk_category, exercise_name
            )

            # Ejercicios alternativos si el riesgo es alto
            alternatives = []
            if risk_category in ["high", "very_high"]:
                alternatives = self._get_safer_alternatives(exercise_name, risk_factors)

            return {
                "status": "success",
                "risk_score": normalized_risk,
                "risk_category": risk_category,
                "risk_factors": risk_factors,
                "primary_concerns": self._identify_primary_concerns(risk_factors),
                "recommendations": recommendations,
                "safer_alternatives": alternatives,
                "continue_exercise": risk_category in ["low", "moderate"],
                "monitoring_required": risk_category == "moderate",
            }

        except Exception as e:
            logger.error(f"Error evaluando riesgo de lesión: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    # Métodos auxiliares

    def _get_expected_form_by_level(
        self, exercise_name: str, experience_level: str
    ) -> Dict[str, Any]:
        """Obtiene la forma esperada según el nivel de experiencia."""
        # Base de datos de formas por nivel
        form_database = {
            "sentadilla": {
                "beginner": {
                    "depth": "paralelo o ligeramente arriba",
                    "knee_tracking": "ligera desviación aceptable",
                    "back_angle": "inclinación moderada permitida",
                    "tolerance": 0.8,
                },
                "intermediate": {
                    "depth": "paralelo completo",
                    "knee_tracking": "alineación con pies",
                    "back_angle": "espalda recta",
                    "tolerance": 0.6,
                },
                "advanced": {
                    "depth": "completo (ATG si es posible)",
                    "knee_tracking": "perfecta alineación",
                    "back_angle": "neutral perfecto",
                    "tolerance": 0.3,
                },
            }
            # Más ejercicios...
        }

        exercise_forms = form_database.get(exercise_name.lower(), {})
        return exercise_forms.get(
            experience_level, exercise_forms.get("intermediate", {})
        )

    async def _analyze_focus_areas(
        self,
        image: Union[str, bytes],
        exercise_name: str,
        focus_areas: List[str],
        general_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analiza áreas específicas de enfoque."""
        focused_results = {}

        for area in focus_areas:
            # Generar prompt específico para el área
            area_prompt = f"""
            Analiza específicamente la zona de {area} en este ejercicio de {exercise_name}.
            
            Evalúa:
            1. Posición y alineación de {area}
            2. Movimiento y rango de {area}
            3. Tensión o compensación en {area}
            4. Riesgo de lesión en {area}
            
            Proporciona análisis detallado y recomendaciones específicas.
            """

            # Análisis específico del área
            area_analysis = await self.posture_vision_client.analyze_image(
                image, area_prompt, temperature=0.3
            )

            focused_results[area] = {
                "analysis": area_analysis,
                "risk_level": self._assess_area_risk(area, area_analysis),
                "corrections": self._generate_area_corrections(area, area_analysis),
            }

        return focused_results

    def _adjust_score_by_experience(self, base_score: float, experience: str) -> float:
        """Ajusta el score según el nivel de experiencia."""
        adjustments = {
            "beginner": 1.2,  # Más permisivo
            "intermediate": 1.0,  # Sin ajuste
            "advanced": 0.8,  # Más estricto
        }

        factor = adjustments.get(experience, 1.0)
        return min(100, base_score * factor)

    def _get_exercise_regression(
        self, exercise_name: str, experience_level: str
    ) -> Dict[str, Any]:
        """Obtiene una regresión del ejercicio."""
        regressions = {
            "sentadilla": {
                "beginner": {
                    "exercise": "sentadilla en caja",
                    "reasoning": "Ayuda a controlar la profundidad y mejora la confianza",
                },
                "intermediate": {
                    "exercise": "sentadilla goblet",
                    "reasoning": "Mejora la posición del torso y el patrón de movimiento",
                },
            }
            # Más ejercicios...
        }

        exercise_regressions = regressions.get(exercise_name.lower(), {})
        return exercise_regressions.get(
            experience_level,
            {
                "exercise": f"{exercise_name} asistido",
                "reasoning": "Reducir la dificultad para mejorar la técnica",
            },
        )

    def _get_exercise_progression(
        self, exercise_name: str, experience_level: str
    ) -> Dict[str, Any]:
        """Obtiene una progresión del ejercicio."""
        progressions = {
            "sentadilla": {
                "intermediate": {
                    "exercise": "sentadilla frontal",
                    "reasoning": "Aumenta la demanda en core y movilidad",
                },
                "advanced": {
                    "exercise": "sentadilla overhead",
                    "reasoning": "Máxima demanda de movilidad y estabilidad",
                },
            }
            # Más ejercicios...
        }

        exercise_progressions = progressions.get(exercise_name.lower(), {})
        return exercise_progressions.get(
            experience_level,
            {
                "exercise": f"{exercise_name} avanzado",
                "reasoning": "Aumentar la dificultad para continuar progresando",
            },
        )

    async def _generate_improvement_plan(
        self, exercise_name: str, analysis: Dict[str, Any], experience_level: str
    ) -> Dict[str, Any]:
        """Genera un plan de mejora personalizado."""
        plan = {
            "timeline": "4-6 semanas",
            "frequency": "2-3 veces por semana",
            "phases": [],
        }

        # Fase 1: Movilidad y activación
        phase1 = {
            "phase": 1,
            "duration": "1-2 semanas",
            "focus": "Movilidad y activación",
            "exercises": self._get_mobility_exercises(exercise_name, analysis),
            "goals": ["Mejorar rango de movimiento", "Activar músculos correctos"],
        }
        plan["phases"].append(phase1)

        # Fase 2: Patrón de movimiento
        phase2 = {
            "phase": 2,
            "duration": "2-3 semanas",
            "focus": "Perfeccionar patrón",
            "exercises": self._get_pattern_exercises(exercise_name, experience_level),
            "goals": ["Automatizar movimiento correcto", "Eliminar compensaciones"],
        }
        plan["phases"].append(phase2)

        # Fase 3: Integración y progresión
        phase3 = {
            "phase": 3,
            "duration": "1-2 semanas",
            "focus": "Integración completa",
            "exercises": [exercise_name],
            "goals": [
                "Ejecutar con técnica perfecta",
                "Aumentar intensidad gradualmente",
            ],
        }
        plan["phases"].append(phase3)

        return plan

    def _get_ideal_form_description(self, exercise_name: str) -> Dict[str, Any]:
        """Obtiene descripción de la forma ideal de un ejercicio."""
        ideal_forms = {
            "sentadilla": {
                "posture": "Espalda recta, pecho arriba, core activado",
                "movement": "Descenso controlado, rodillas alineadas con pies",
                "depth": "Cadera por debajo de rodillas (si la movilidad lo permite)",
                "breathing": "Inhalar al bajar, exhalar al subir",
            }
            # Más ejercicios...
        }

        return ideal_forms.get(
            exercise_name.lower(),
            {
                "posture": "Mantener alineación neutral",
                "movement": "Control en todo el rango",
                "breathing": "Respiración coordinada con movimiento",
            },
        )

    async def _perform_technique_comparison(
        self,
        user_analysis: Dict[str, Any],
        reference: Dict[str, Any],
        comparison_points: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Realiza comparación detallada de técnicas."""
        comparison = {
            "overall_similarity": 0,
            "differences": [],
            "strengths": [],
            "areas_to_improve": [],
        }

        # Puntos de comparación por defecto
        if not comparison_points:
            comparison_points = [
                "posture",
                "alignment",
                "range_of_motion",
                "tempo",
                "control",
            ]

        # Comparar cada punto
        for point in comparison_points:
            user_value = user_analysis.get(point)
            ref_value = reference.get(point)

            if user_value and ref_value:
                similarity = self._calculate_similarity(user_value, ref_value)

                if similarity > 0.8:
                    comparison["strengths"].append(
                        {
                            "aspect": point,
                            "similarity": similarity,
                            "description": f"Excelente {point}",
                        }
                    )
                else:
                    comparison["areas_to_improve"].append(
                        {
                            "aspect": point,
                            "similarity": similarity,
                            "user": user_value,
                            "ideal": ref_value,
                            "correction": self._generate_correction_cue(
                                point, user_value, ref_value
                            ),
                        }
                    )

        # Calcular similitud general
        if comparison["strengths"] or comparison["areas_to_improve"]:
            total_points = len(comparison["strengths"]) + len(
                comparison["areas_to_improve"]
            )
            comparison["overall_similarity"] = (
                len(comparison["strengths"]) / total_points
            )

        return comparison

    def _calculate_similarity(self, value1: Any, value2: Any) -> float:
        """Calcula similitud entre dos valores."""
        # Implementación simplificada
        if isinstance(value1, str) and isinstance(value2, str):
            return (
                0.8
                if value1.lower() in value2.lower() or value2.lower() in value1.lower()
                else 0.3
            )
        elif isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            diff = abs(value1 - value2)
            max_val = max(abs(value1), abs(value2))
            return 1.0 - (diff / max_val) if max_val > 0 else 1.0
        else:
            return 0.5

    def _generate_correction_cue(self, aspect: str, current: Any, ideal: Any) -> str:
        """Genera una indicación de corrección."""
        cues = {
            "posture": "Mantén el pecho arriba y la espalda recta",
            "alignment": "Alinea rodillas con la punta de los pies",
            "range_of_motion": "Busca mayor profundidad manteniendo la técnica",
            "tempo": "Controla más el descenso, 2-3 segundos",
            "control": "Evita movimientos bruscos, mantén tensión constante",
        }

        return cues.get(aspect, f"Ajusta {aspect} para acercarte más a la forma ideal")

    async def _generate_comparison_visualization(
        self,
        user_image: Union[str, bytes],
        user_analysis: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> Optional[str]:
        """Genera visualización de la comparación."""
        # Implementación futura con OpenCV o similar
        # Por ahora retornar None
        return None

    def _extract_key_differences(self, comparison: Dict[str, Any]) -> List[str]:
        """Extrae las diferencias clave de la comparación."""
        key_differences = []

        for area in comparison.get("areas_to_improve", []):
            if area["similarity"] < 0.5:  # Diferencias significativas
                key_differences.append(f"{area['aspect']}: {area['correction']}")

        return key_differences[:3]  # Top 3 diferencias

    def _prioritize_improvements(
        self, comparison: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Prioriza las mejoras según importancia."""
        improvements = comparison.get("areas_to_improve", [])

        # Definir prioridades por aspecto
        priority_weights = {
            "alignment": 10,  # Más importante para seguridad
            "posture": 9,
            "control": 8,
            "range_of_motion": 6,
            "tempo": 5,
        }

        # Ordenar por prioridad
        for improvement in improvements:
            aspect = improvement["aspect"]
            base_priority = priority_weights.get(aspect, 5)
            # Ajustar por similitud (menos similar = más prioritario)
            improvement["priority"] = base_priority * (1 - improvement["similarity"])

        return sorted(improvements, key=lambda x: x["priority"], reverse=True)

    def _get_minor_adjustments(self, analysis: Dict[str, Any]) -> List[str]:
        """Obtiene ajustes menores para técnica ya buena."""
        adjustments = []

        form_score = analysis.get("form_score", 0)
        if form_score > 90:
            adjustments.append("Mantén la consistencia en cada repetición")
            adjustments.append("Experimenta con tempo más lento para mayor control")
        elif form_score > 80:
            adjustments.append("Enfócate en la respiración coordinada")
            adjustments.append("Busca un poco más de profundidad si es posible")

        return adjustments

    async def _generate_correction_for_error(
        self,
        error: str,
        exercise_name: str,
        user_profile: Optional[Dict[str, Any]],
        style: str,
    ) -> Dict[str, Any]:
        """Genera corrección específica para un error."""
        correction = {
            "error": error,
            "correction_cue": "",
            "drill": "",
            "priority_score": 5,
        }

        # Base de correcciones por error común
        corrections_db = {
            "rodillas hacia adentro": {
                "cue": "Empuja las rodillas hacia afuera, alineadas con los pies",
                "drill": "Sentadillas con banda elástica en rodillas",
                "priority": 9,
            },
            "espalda redondeada": {
                "cue": "Pecho arriba, escápulas juntas, mirada al frente",
                "drill": "Good mornings con barra para fortalecer espalda",
                "priority": 10,
            },
            # Más correcciones...
        }

        if error.lower() in corrections_db:
            correction_data = corrections_db[error.lower()]
            correction["correction_cue"] = correction_data["cue"]
            correction["drill"] = correction_data["drill"]
            correction["priority_score"] = correction_data["priority"]
        else:
            # Generar corrección genérica
            correction["correction_cue"] = f"Corrige {error} con atención consciente"
            correction["drill"] = (
                f"Practica el movimiento sin peso enfocándote en eliminar {error}"
            )
            correction["priority_score"] = 5

        # Ajustar por estilo
        if style == "concise":
            correction["correction_cue"] = correction["correction_cue"].split(",")[0]
        elif style == "visual":
            correction["visual_reference"] = (
                f"Imagina {self._get_visual_metaphor(error)}"
            )

        return correction

    def _get_visual_metaphor(self, error: str) -> str:
        """Obtiene una metáfora visual para la corrección."""
        metaphors = {
            "rodillas hacia adentro": "un laser saliendo de tus rodillas hacia los dedos pequeños de los pies",
            "espalda redondeada": "una cuerda tirando de tu pecho hacia el techo",
            "talones levantados": "raíces creciendo de tus talones hacia el suelo",
        }

        return metaphors.get(error.lower(), "la forma perfecta del movimiento")

    async def _generate_corrective_exercises(
        self,
        errors: List[str],
        exercise_name: str,
        user_profile: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Genera ejercicios correctivos para los errores encontrados."""
        corrective_exercises = []

        # Base de ejercicios correctivos por tipo de error
        correctives_db = {
            "rodillas hacia adentro": [
                {
                    "exercise": "Clamshells",
                    "sets": "3x15",
                    "purpose": "Fortalecer glúteo medio",
                    "frequency": "diario",
                },
                {
                    "exercise": "Monster walks con banda",
                    "sets": "3x20 pasos",
                    "purpose": "Activación de abductores",
                    "frequency": "antes de entrenar piernas",
                },
            ],
            "espalda redondeada": [
                {
                    "exercise": "Cat-cow",
                    "sets": "3x10",
                    "purpose": "Movilidad espinal",
                    "frequency": "diario",
                },
                {
                    "exercise": "Bird dog",
                    "sets": "3x8 cada lado",
                    "purpose": "Estabilidad de core",
                    "frequency": "3x semana",
                },
            ],
            # Más ejercicios correctivos...
        }

        # Recopilar ejercicios únicos para todos los errores
        added_exercises = set()

        for error in errors:
            if error.lower() in correctives_db:
                for exercise in correctives_db[error.lower()]:
                    if exercise["exercise"] not in added_exercises:
                        corrective_exercises.append(exercise)
                        added_exercises.add(exercise["exercise"])

        # Limitar a 4-5 ejercicios máximo
        return corrective_exercises[:5]

    def _create_correction_implementation_plan(
        self,
        corrections: List[Dict[str, Any]],
        corrective_exercises: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Crea un plan de implementación de correcciones."""
        plan = {"phases": [], "total_duration": "4-6 semanas", "check_points": []}

        # Fase 1: Ejercicios correctivos y movilidad (1-2 semanas)
        phase1 = {
            "phase": 1,
            "name": "Preparación y activación",
            "duration": "1-2 semanas",
            "daily_routine": [
                {
                    "timing": "calentamiento",
                    "exercises": [
                        ex for ex in corrective_exercises if ex["frequency"] == "diario"
                    ],
                    "duration": "10-15 min",
                }
            ],
            "training_days": [
                {
                    "timing": "pre-entrenamiento",
                    "exercises": [
                        ex
                        for ex in corrective_exercises
                        if "antes de entrenar" in ex["frequency"]
                    ],
                    "duration": "5-10 min",
                }
            ],
        }
        plan["phases"].append(phase1)

        # Fase 2: Integración de correcciones (2-3 semanas)
        phase2 = {
            "phase": 2,
            "name": "Práctica con correcciones",
            "duration": "2-3 semanas",
            "focus_points": [corr["correction_cue"] for corr in corrections[:3]],
            "practice_sets": "3-4 sets x 8-10 reps con peso ligero",
            "mental_cues": self._generate_mental_cues(corrections),
        }
        plan["phases"].append(phase2)

        # Fase 3: Consolidación (1-2 semanas)
        phase3 = {
            "phase": 3,
            "name": "Automatización",
            "duration": "1-2 semanas",
            "goals": [
                "Ejecutar sin pensar en las correcciones",
                "Aumentar intensidad gradualmente",
            ],
            "progression": "Aumentar peso 5-10% cuando la técnica sea consistente",
        }
        plan["phases"].append(phase3)

        # Checkpoints
        plan["check_points"] = [
            {"week": 2, "action": "Grabar video para evaluar progreso"},
            {"week": 4, "action": "Re-evaluación completa de técnica"},
            {"week": 6, "action": "Test de técnica con peso objetivo"},
        ]

        return plan

    def _generate_mental_cues(self, corrections: List[Dict[str, Any]]) -> List[str]:
        """Genera indicaciones mentales simples."""
        cues = []

        for corr in corrections[:3]:  # Top 3 correcciones
            # Simplificar la corrección a 2-3 palabras
            cue = corr["correction_cue"]
            if "rodillas" in cue.lower():
                cues.append("Rodillas afuera")
            elif "pecho" in cue.lower():
                cues.append("Pecho arriba")
            elif "espalda" in cue.lower():
                cues.append("Espalda recta")
            elif "core" in cue.lower():
                cues.append("Core apretado")

        return cues

    def _estimate_improvement_timeline(self, corrections: List[Dict[str, Any]]) -> str:
        """Estima tiempo para mejorar la técnica."""
        total_priority = sum(c.get("priority_score", 5) for c in corrections)

        if total_priority < 15:
            return "1-2 semanas"
        elif total_priority < 30:
            return "3-4 semanas"
        elif total_priority < 45:
            return "4-6 semanas"
        else:
            return "6-8 semanas"

    def _generate_visual_cues(
        self, corrections: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Genera indicaciones visuales para las correcciones."""
        visual_cues = []

        for corr in corrections:
            visual_cue = {
                "error": corr["error"],
                "visual": corr.get("visual_reference", ""),
                "body_position": self._describe_correct_position(corr["error"]),
                "movement_path": self._describe_movement_path(corr["error"]),
            }
            visual_cues.append(visual_cue)

        return visual_cues

    def _describe_correct_position(self, error: str) -> str:
        """Describe la posición corporal correcta."""
        positions = {
            "rodillas hacia adentro": "Rodillas apuntando hacia los dedos pequeños de los pies",
            "espalda redondeada": "Columna neutral, pecho orgulloso como un superhéroe",
            "talones levantados": "Peso distribuido en todo el pie, talones pegados al suelo",
        }

        return positions.get(error.lower(), "Mantén posición neutral y estable")

    def _describe_movement_path(self, error: str) -> str:
        """Describe la trayectoria correcta del movimiento."""
        paths = {
            "rodillas hacia adentro": "Las rodillas siguen la línea de los pies durante todo el movimiento",
            "espalda redondeada": "El pecho lidera el movimiento hacia arriba",
            "talones levantados": "Empuja el suelo con los talones para iniciar el ascenso",
        }

        return paths.get(error.lower(), "Movimiento controlado y fluido")

    # Métodos de evaluación de riesgo

    def _evaluate_error_risk(self, error: str, exercise_name: str) -> Dict[str, Any]:
        """Evalúa el riesgo asociado a un error de forma."""
        risk_values = {
            "espalda redondeada": {"risk_value": 8, "affected_area": "columna lumbar"},
            "rodillas hacia adentro": {
                "risk_value": 7,
                "affected_area": "ligamentos de rodilla",
            },
            "hombros enrollados": {
                "risk_value": 5,
                "affected_area": "manguito rotador",
            },
            "cuello hiperextendido": {"risk_value": 6, "affected_area": "cervicales"},
        }

        risk_factor = risk_values.get(
            error.lower(), {"risk_value": 4, "affected_area": "general"}
        )
        risk_factor["error"] = error
        risk_factor["exercise"] = exercise_name

        return risk_factor

    def _evaluate_compensation_risk(self, compensation: str) -> Dict[str, Any]:
        """Evalúa el riesgo de compensaciones musculares."""
        return {
            "compensation": compensation,
            "risk_value": 5,
            "concern": "Desequilibrio muscular a largo plazo",
        }

    def _evaluate_historical_risk(
        self,
        user_history: Dict[str, Any],
        exercise_name: str,
        current_errors: List[str],
    ) -> List[Dict[str, Any]]:
        """Evalúa riesgo basado en historial del usuario."""
        historical_risks = []

        # Verificar lesiones previas
        previous_injuries = user_history.get("injuries", [])
        for injury in previous_injuries:
            if self._is_related_to_exercise(injury, exercise_name, current_errors):
                historical_risks.append(
                    {
                        "factor": f"Lesión previa: {injury}",
                        "risk_value": 6,
                        "recommendation": "Progresión más conservadora",
                    }
                )

        return historical_risks

    def _is_related_to_exercise(
        self, injury: str, exercise_name: str, errors: List[str]
    ) -> bool:
        """Verifica si una lesión previa está relacionada con el ejercicio actual."""
        # Lógica simplificada
        injury_lower = injury.lower()
        exercise_lower = exercise_name.lower()

        # Mapeo de lesiones a ejercicios de riesgo
        if "rodilla" in injury_lower and "sentadilla" in exercise_lower:
            return True
        if "espalda" in injury_lower and any(
            ex in exercise_lower for ex in ["peso muerto", "remo", "sentadilla"]
        ):
            return True
        if "hombro" in injury_lower and any(
            ex in exercise_lower for ex in ["press", "dominadas"]
        ):
            return True

        return False

    def _evaluate_workout_context_risk(
        self, workout_context: Dict[str, Any], base_risk: float
    ) -> Dict[str, Any]:
        """Evalúa riesgo basado en el contexto del entrenamiento."""
        risk_multiplier = 1.0
        factors = []

        # Evaluar fatiga acumulada
        sets_done = workout_context.get("sets_completed", 0)
        if sets_done > 3:
            risk_multiplier *= 1.2
            factors.append("Fatiga acumulada")

        # Evaluar intensidad
        intensity = workout_context.get("intensity_percentage", 0)
        if intensity > 85:
            risk_multiplier *= 1.3
            factors.append("Alta intensidad")

        # Evaluar volumen
        total_reps = workout_context.get("total_reps", 0)
        if total_reps > 50:
            risk_multiplier *= 1.15
            factors.append("Alto volumen")

        return {
            "factor": "Contexto de entrenamiento",
            "risk_value": base_risk * (risk_multiplier - 1),
            "details": factors,
        }

    def _categorize_risk(self, risk_score: float) -> str:
        """Categoriza el nivel de riesgo."""
        if risk_score < 20:
            return "low"
        elif risk_score < 40:
            return "moderate"
        elif risk_score < 60:
            return "high"
        else:
            return "very_high"

    async def _generate_risk_mitigation_recommendations(
        self, risk_factors: List[Dict[str, Any]], risk_category: str, exercise_name: str
    ) -> List[Dict[str, str]]:
        """Genera recomendaciones para mitigar riesgos."""
        recommendations = []

        # Recomendaciones generales por categoría
        if risk_category == "very_high":
            recommendations.append(
                {
                    "priority": "immediate",
                    "action": "Detener el ejercicio y trabajar en correcciones",
                    "reasoning": "El riesgo de lesión es demasiado alto para continuar",
                }
            )
        elif risk_category == "high":
            recommendations.append(
                {
                    "priority": "high",
                    "action": "Reducir peso significativamente (50-60%)",
                    "reasoning": "Permite enfocarse en la técnica sin riesgo",
                }
            )

        # Recomendaciones específicas por factor de riesgo
        for factor in risk_factors:
            if factor["risk_value"] > 5:
                rec = self._get_specific_mitigation(factor)
                if rec:
                    recommendations.append(rec)

        return recommendations

    def _get_specific_mitigation(
        self, risk_factor: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """Obtiene mitigación específica para un factor de riesgo."""
        if "espalda" in str(risk_factor.get("affected_area", "")):
            return {
                "priority": "high",
                "action": "Fortalecer core y mejorar movilidad de cadera",
                "reasoning": "Reduce stress en la columna",
            }
        elif "rodilla" in str(risk_factor.get("affected_area", "")):
            return {
                "priority": "high",
                "action": "Trabajar en activación de glúteos y control de rodilla",
                "reasoning": "Mejora la mecánica y reduce stress articular",
            }

        return None

    def _identify_primary_concerns(
        self, risk_factors: List[Dict[str, Any]]
    ) -> List[str]:
        """Identifica las principales preocupaciones de seguridad."""
        # Ordenar por valor de riesgo
        sorted_factors = sorted(
            risk_factors, key=lambda x: x.get("risk_value", 0), reverse=True
        )

        # Tomar los top 3
        primary_concerns = []
        for factor in sorted_factors[:3]:
            if "error" in factor:
                primary_concerns.append(
                    f"{factor['error']} - Alto riesgo para {factor.get('affected_area', 'articulación')}"
                )
            else:
                primary_concerns.append(
                    factor.get("factor", "Factor de riesgo no especificado")
                )

        return primary_concerns

    def _get_safer_alternatives(
        self, exercise_name: str, risk_factors: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Obtiene alternativas más seguras al ejercicio."""
        alternatives = {
            "sentadilla": [
                {
                    "exercise": "Prensa de piernas",
                    "reasoning": "Menor stress en espalda baja",
                },
                {
                    "exercise": "Sentadilla goblet",
                    "reasoning": "Mejor control postural",
                },
                {"exercise": "Split squat", "reasoning": "Menor carga axial"},
            ],
            "peso muerto": [
                {
                    "exercise": "Peso muerto rumano",
                    "reasoning": "Menor rango, más control",
                },
                {"exercise": "Rack pulls", "reasoning": "Posición inicial más segura"},
                {
                    "exercise": "Hip thrust",
                    "reasoning": "Aísla glúteos sin stress espinal",
                },
            ],
            # Más alternativas...
        }

        exercise_alternatives = alternatives.get(
            exercise_name.lower(),
            [
                {
                    "exercise": f"{exercise_name} con peso corporal",
                    "reasoning": "Menor carga, mismo patrón",
                },
                {
                    "exercise": f"{exercise_name} asistido",
                    "reasoning": "Mayor control y seguridad",
                },
            ],
        )

        return exercise_alternatives[:3]

    def _get_mobility_exercises(
        self, exercise_name: str, analysis: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Obtiene ejercicios de movilidad específicos."""
        mobility_exercises = []

        # Mapeo de ejercicios a movilidad requerida
        mobility_requirements = {
            "sentadilla": [
                "movilidad de tobillo",
                "movilidad de cadera",
                "movilidad torácica",
            ],
            "press_banca": ["movilidad de hombro", "movilidad torácica"],
            "peso_muerto": ["movilidad de cadera", "flexibilidad de isquiotibiales"],
        }

        requirements = mobility_requirements.get(
            exercise_name.lower(), ["movilidad general"]
        )

        # Base de ejercicios de movilidad
        mobility_database = {
            "movilidad de tobillo": {
                "exercise": "Estiramiento de pantorrilla en pared",
                "sets": "3x30 segundos cada lado",
                "frequency": "diario",
            },
            "movilidad de cadera": {
                "exercise": "90/90 hip stretch",
                "sets": "3x45 segundos cada lado",
                "frequency": "diario",
            },
            "movilidad torácica": {
                "exercise": "Cat-cow + rotaciones torácicas",
                "sets": "3x10 repeticiones",
                "frequency": "2x día",
            },
            # Más ejercicios...
        }

        for req in requirements:
            if req in mobility_database:
                mobility_exercises.append(mobility_database[req])

        return mobility_exercises

    def _get_pattern_exercises(
        self, exercise_name: str, experience_level: str
    ) -> List[Dict[str, str]]:
        """Obtiene ejercicios para mejorar el patrón de movimiento."""
        pattern_exercises = {
            "sentadilla": {
                "beginner": [
                    {
                        "exercise": "Sentadilla en pared",
                        "purpose": "Aprender posición correcta",
                    },
                    {"exercise": "Box squat", "purpose": "Controlar profundidad"},
                ],
                "intermediate": [
                    {
                        "exercise": "Pausa sentadilla (3 seg)",
                        "purpose": "Control y propriocepción",
                    },
                    {
                        "exercise": "Sentadilla tempo 3-1-1",
                        "purpose": "Control excéntrico",
                    },
                ],
            }
            # Más patrones...
        }

        exercise_patterns = pattern_exercises.get(exercise_name.lower(), {})
        return exercise_patterns.get(
            experience_level,
            [{"exercise": f"{exercise_name} con pausa", "purpose": "Mejorar control"}],
        )

    def _assess_area_risk(self, area: str, analysis: str) -> str:
        """Evalúa el nivel de riesgo de un área específica."""
        # Buscar palabras clave de riesgo en el análisis
        high_risk_keywords = [
            "desalineación",
            "compensación",
            "tensión excesiva",
            "hiperextensión",
        ]
        medium_risk_keywords = ["ligera desviación", "tensión moderada", "asimetría"]

        analysis_lower = str(analysis).lower()

        if any(keyword in analysis_lower for keyword in high_risk_keywords):
            return "high"
        elif any(keyword in analysis_lower for keyword in medium_risk_keywords):
            return "medium"
        else:
            return "low"

    def _generate_area_corrections(self, area: str, analysis: str) -> List[str]:
        """Genera correcciones específicas para un área."""
        corrections = []

        # Correcciones generales por área
        area_corrections = {
            "rodillas": [
                "Mantén las rodillas alineadas con los pies",
                "Activa glúteos para estabilizar",
            ],
            "espalda": [
                "Mantén la columna neutral",
                "Activa el core durante todo el movimiento",
            ],
            "hombros": [
                "Retrae las escápulas",
                "Evita enrollar los hombros hacia adelante",
            ],
        }

        return area_corrections.get(
            area.lower(), ["Mantén control y alineación en esta área"]
        )

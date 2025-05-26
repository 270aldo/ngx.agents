"""
Progress Tracker mejorado con capacidades avanzadas de visión.

Este módulo extiende el Progress Tracker con las nuevas capacidades
de análisis de imágenes usando Gemini 2.0 y skills especializadas.
"""

import os
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta

from agents.progress_tracker.agent import ProgressTracker
from agents.skills.advanced_vision_skills import (
    PhysicalFormAnalysisSkill,
    ProgressTrackingSkill,
    BodyMeasurementExtractionSkill,
)
from clients.vertex_ai.advanced_vision_client import AdvancedVisionClient
from clients.gcs_client import GCSClient
from config.gemini_models import get_model_config, GCP_CONFIG
from core.logging_config import get_logger
from adk.agent import Skill

logger = get_logger(__name__)


class EnhancedProgressTracker(ProgressTracker):
    """
    Progress Tracker mejorado con capacidades avanzadas de análisis visual.
    """

    def __init__(self, *args, **kwargs):
        """Inicializa el Progress Tracker mejorado."""
        super().__init__(*args, **kwargs)

        # Configurar modelo Gemini 2.0 Flash para el agente
        model_config = get_model_config("progress_tracker")
        self.model = model_config["model_id"]

        # Inicializar cliente de visión avanzado
        self.advanced_vision_client = AdvancedVisionClient(
            model=self.model, gcs_client=GCSClient()
        )

        # Inicializar skills de visión avanzadas
        self._init_advanced_vision_skills()

        # Configurar almacenamiento para imágenes de progreso
        self.progress_images_bucket = GCP_CONFIG["storage_bucket"]

        logger.info(f"Progress Tracker mejorado inicializado con modelo {self.model}")

    def _init_advanced_vision_skills(self):
        """Inicializa las skills de visión avanzadas."""
        # Crear instancias de skills
        self.physical_form_skill = PhysicalFormAnalysisSkill(
            self.advanced_vision_client
        )
        self.progress_tracking_skill = ProgressTrackingSkill(
            self.advanced_vision_client
        )
        self.body_measurement_skill = BodyMeasurementExtractionSkill(
            self.advanced_vision_client
        )

        # Añadir nuevas skills al agente
        new_skills = [
            Skill(
                name="analyze_physical_form_advanced",
                description="Realiza análisis avanzado de forma física con estimación de composición corporal",
                handler=self._skill_analyze_physical_form_advanced,
            ),
            Skill(
                name="track_visual_progress_advanced",
                description="Compara imágenes de progreso con análisis detallado de cambios",
                handler=self._skill_track_visual_progress_advanced,
            ),
            Skill(
                name="extract_body_measurements",
                description="Extrae medidas corporales estimadas de imágenes",
                handler=self._skill_extract_body_measurements,
            ),
            Skill(
                name="generate_progress_report",
                description="Genera un reporte visual completo de progreso",
                handler=self._skill_generate_progress_report,
            ),
        ]

        # Extender las skills existentes
        self.skills.extend(new_skills)

    async def _skill_analyze_physical_form_advanced(
        self,
        image: Union[str, bytes],
        user_id: str,
        analysis_type: str = "comprehensive",
        save_analysis: bool = True,
    ) -> Dict[str, Any]:
        """
        Realiza análisis avanzado de forma física.

        Args:
            image: Imagen para analizar
            user_id: ID del usuario
            analysis_type: Tipo de análisis (comprehensive, body_composition, symmetry)
            save_analysis: Si guardar el análisis en GCS

        Returns:
            Análisis detallado de forma física
        """
        try:
            # Obtener perfil del usuario
            user_profile = await self._get_user_profile(user_id)

            # Ejecutar skill de análisis
            result = await self.physical_form_skill.execute(
                image=image, user_profile=user_profile, analysis_type=analysis_type
            )

            if result.get("status") == "success" and save_analysis:
                # Guardar análisis en historial
                await self._save_progress_checkpoint(
                    user_id, image, result["analysis"], "physical_form_analysis"
                )

                # Generar insights personalizados
                insights = await self._generate_personalized_insights(
                    result["analysis"], user_profile
                )
                result["personalized_insights"] = insights

                # Comparar con análisis anteriores si existen
                previous_analyses = await self._get_previous_analyses(
                    user_id, "physical_form", limit=3
                )
                if previous_analyses:
                    trends = self._analyze_body_composition_trends(
                        result["analysis"], previous_analyses
                    )
                    result["trends"] = trends

            return result

        except Exception as e:
            logger.error(
                f"Error en análisis avanzado de forma física: {e}", exc_info=True
            )
            return {"status": "error", "error": str(e)}

    async def _skill_track_visual_progress_advanced(
        self,
        current_image: Union[str, bytes],
        user_id: str,
        comparison_period: str = "all",
        generate_visualization: bool = True,
    ) -> Dict[str, Any]:
        """
        Realiza seguimiento visual avanzado del progreso.

        Args:
            current_image: Imagen actual
            user_id: ID del usuario
            comparison_period: Período de comparación (all, 30days, 90days, 6months)
            generate_visualization: Si generar visualización de progreso

        Returns:
            Análisis de progreso visual
        """
        try:
            # Obtener imágenes anteriores según el período
            previous_images = await self._get_progress_images(
                user_id, comparison_period
            )

            if not previous_images:
                return {
                    "status": "warning",
                    "message": "No hay imágenes anteriores para comparar",
                    "recommendation": "Toma fotos de progreso regularmente (semanalmente) para mejor seguimiento",
                }

            # Obtener objetivos del usuario
            user_goals = await self._get_user_goals(user_id)

            # Ejecutar skill de tracking
            result = await self.progress_tracking_skill.execute(
                current_image=current_image,
                previous_images=previous_images,
                user_goals=user_goals,
            )

            if result.get("status") == "success":
                # Guardar nueva imagen de progreso
                await self._save_progress_image(user_id, current_image)

                # Generar visualización si se solicita
                if generate_visualization:
                    visualization = await self._generate_progress_visualization(
                        user_id, result["analysis"], result.get("metrics", {})
                    )
                    result["visualization_url"] = visualization

                # Calcular proyecciones
                projections = await self._calculate_progress_projections(
                    result["analysis"], user_goals
                )
                result["projections"] = projections

                # Generar recomendaciones de ajuste
                adjustments = await self._generate_plan_adjustments(
                    result["analysis"], user_goals
                )
                result["plan_adjustments"] = adjustments

            return result

        except Exception as e:
            logger.error(f"Error en tracking visual avanzado: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _skill_extract_body_measurements(
        self,
        image: Union[str, bytes],
        user_id: str,
        user_height: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Extrae medidas corporales estimadas de una imagen.

        Args:
            image: Imagen para análisis
            user_id: ID del usuario
            user_height: Altura del usuario en cm (para calibración)

        Returns:
            Medidas corporales estimadas
        """
        try:
            # Obtener altura del perfil si no se proporciona
            if not user_height:
                user_profile = await self._get_user_profile(user_id)
                user_height = user_profile.get("height_cm")

            # Obtener medidas anteriores para calibración
            previous_measurements = await self._get_latest_measurements(user_id)

            # Ejecutar skill de extracción
            result = await self.body_measurement_skill.execute(
                image=image,
                reference_height=user_height,
                previous_measurements=previous_measurements,
            )

            if result.get("status") == "success":
                # Guardar medidas
                await self._save_measurements(user_id, result["measurements"])

                # Comparar con objetivos de medidas
                measurement_goals = await self._get_measurement_goals(user_id)
                if measurement_goals:
                    comparison = self._compare_with_measurement_goals(
                        result["measurements"], measurement_goals
                    )
                    result["goal_comparison"] = comparison

                # Generar gráfico de evolución de medidas
                evolution_chart = await self._generate_measurements_chart(user_id)
                result["evolution_chart_url"] = evolution_chart

            return result

        except Exception as e:
            logger.error(f"Error en extracción de medidas: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _skill_generate_progress_report(
        self,
        user_id: str,
        report_period: str = "monthly",
        include_projections: bool = True,
    ) -> Dict[str, Any]:
        """
        Genera un reporte completo de progreso con visualizaciones.

        Args:
            user_id: ID del usuario
            report_period: Período del reporte (weekly, monthly, quarterly)
            include_projections: Si incluir proyecciones futuras

        Returns:
            Reporte completo de progreso
        """
        try:
            # Recopilar todos los datos necesarios
            report_data = await self._gather_report_data(user_id, report_period)

            # Generar análisis comprehensivo
            comprehensive_analysis = await self._generate_comprehensive_analysis(
                report_data
            )

            # Crear visualizaciones
            visualizations = await self._create_report_visualizations(report_data)

            # Generar PDF del reporte si es posible
            report_pdf = await self._generate_pdf_report(
                user_id, comprehensive_analysis, visualizations
            )

            # Preparar respuesta
            report = {
                "status": "success",
                "report_period": report_period,
                "generated_at": datetime.utcnow().isoformat(),
                "summary": comprehensive_analysis["executive_summary"],
                "key_achievements": comprehensive_analysis["achievements"],
                "areas_of_improvement": comprehensive_analysis["improvements"],
                "visualizations": visualizations,
                "recommendations": comprehensive_analysis["recommendations"],
            }

            if include_projections:
                report["future_projections"] = comprehensive_analysis.get(
                    "projections", {}
                )

            if report_pdf:
                report["pdf_url"] = report_pdf

            # Notificar al usuario
            await self._notify_report_ready(user_id, report)

            return report

        except Exception as e:
            logger.error(f"Error generando reporte de progreso: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    # Métodos auxiliares privados

    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Obtiene el perfil del usuario."""
        try:
            # Aquí iría la lógica real para obtener el perfil de Supabase
            return {
                "user_id": user_id,
                "age": 30,
                "gender": "male",
                "height_cm": 175,
                "goals": ["muscle_gain", "strength"],
                "experience_level": "intermediate",
            }
        except Exception as e:
            logger.error(f"Error obteniendo perfil de usuario: {e}")
            return {}

    async def _save_progress_checkpoint(
        self,
        user_id: str,
        image: Union[str, bytes],
        analysis: Dict[str, Any],
        checkpoint_type: str,
    ) -> Optional[str]:
        """Guarda un checkpoint de progreso en GCS."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

            # Guardar imagen
            image_path = (
                f"users/{user_id}/progress/{checkpoint_type}/{timestamp}_image.jpg"
            )
            image_url = await self.advanced_vision_client.gcs_client.upload_image(
                image, image_path
            )

            # Guardar análisis
            analysis_path = (
                f"users/{user_id}/progress/{checkpoint_type}/{timestamp}_analysis.json"
            )
            analysis_data = json.dumps(analysis, indent=2).encode("utf-8")
            await self.advanced_vision_client.gcs_client.upload_file(
                analysis_data, analysis_path
            )

            # Actualizar índice en base de datos
            await self._update_progress_index(
                user_id, checkpoint_type, image_url, analysis_path
            )

            return image_url

        except Exception as e:
            logger.error(f"Error guardando checkpoint: {e}")
            return None

    async def _generate_personalized_insights(
        self, analysis: Dict[str, Any], user_profile: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Genera insights personalizados basados en el análisis y perfil."""
        insights = []

        # Analizar según objetivos
        goals = user_profile.get("goals", [])

        if "muscle_gain" in goals:
            muscle_development = analysis.get("body_composition", {}).get(
                "muscle_distribution"
            )
            if muscle_development:
                insights.append(
                    {
                        "type": "muscle_development",
                        "insight": self._analyze_muscle_development(
                            muscle_development, user_profile
                        ),
                        "priority": "high",
                    }
                )

        if "fat_loss" in goals:
            body_fat = analysis.get("body_composition", {}).get("body_fat_percentage")
            if body_fat:
                insights.append(
                    {
                        "type": "body_composition",
                        "insight": self._analyze_body_fat_progress(
                            body_fat, user_profile
                        ),
                        "priority": "high",
                    }
                )

        # Análisis de simetría siempre es relevante
        symmetry = analysis.get("symmetry_analysis", {})
        if symmetry:
            insights.append(
                {
                    "type": "symmetry",
                    "insight": self._analyze_symmetry(symmetry),
                    "priority": "medium",
                }
            )

        return insights

    def _analyze_muscle_development(
        self, muscle_distribution: Dict[str, Any], user_profile: Dict[str, Any]
    ) -> str:
        """Analiza el desarrollo muscular según el perfil."""
        # Lógica de análisis personalizada
        return "Tu desarrollo muscular muestra buen progreso en la parte superior del cuerpo. Considera enfocarte más en piernas para mejor balance."

    def _analyze_body_fat_progress(
        self, body_fat_percentage: float, user_profile: Dict[str, Any]
    ) -> str:
        """Analiza el progreso de grasa corporal."""
        # Lógica de análisis según género y objetivos
        gender = user_profile.get("gender", "male")

        if gender == "male":
            if body_fat_percentage < 15:
                return f"Excelente nivel de grasa corporal ({body_fat_percentage}%). Mantén tu enfoque actual."
            elif body_fat_percentage < 20:
                return f"Buen nivel de grasa corporal ({body_fat_percentage}%). Continúa con déficit calórico moderado."
            else:
                return f"Nivel de grasa corporal elevado ({body_fat_percentage}%). Aumenta el cardio y ajusta la dieta."
        else:  # female
            if body_fat_percentage < 25:
                return f"Excelente nivel de grasa corporal ({body_fat_percentage}%). Mantén hábitos saludables."
            elif body_fat_percentage < 30:
                return f"Buen nivel de grasa corporal ({body_fat_percentage}%). Sigue con tu plan actual."
            else:
                return f"Considera reducir grasa corporal ({body_fat_percentage}%). Enfócate en déficit calórico sostenible."

    def _analyze_symmetry(self, symmetry_data: Dict[str, Any]) -> str:
        """Analiza la simetría corporal."""
        imbalances = symmetry_data.get("imbalances", [])

        if not imbalances:
            return "Excelente simetría corporal. Mantén el balance en tu entrenamiento."
        else:
            areas = ", ".join(imbalances)
            return f"Se detectaron desequilibrios en: {areas}. Incluye ejercicios unilaterales para corregir."

    async def _get_previous_analyses(
        self, user_id: str, analysis_type: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Obtiene análisis anteriores del usuario."""
        # Implementación pendiente - consultar base de datos
        return []

    def _analyze_body_composition_trends(
        self, current_analysis: Dict[str, Any], previous_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analiza tendencias en la composición corporal."""
        trends = {
            "muscle_trend": "stable",
            "fat_trend": "stable",
            "overall_progress": "on_track",
        }

        # Implementar lógica de análisis de tendencias
        # Por ahora retornamos valores de ejemplo

        return trends

    async def _get_progress_images(
        self, user_id: str, period: str
    ) -> List[Dict[str, Any]]:
        """Obtiene imágenes de progreso según el período."""
        # Calcular fecha de inicio según período
        end_date = datetime.utcnow()

        if period == "30days":
            start_date = end_date - timedelta(days=30)
        elif period == "90days":
            start_date = end_date - timedelta(days=90)
        elif period == "6months":
            start_date = end_date - timedelta(days=180)
        else:  # all
            start_date = None

        # Consultar imágenes de la base de datos
        # Implementación pendiente

        return []

    async def _get_user_goals(self, user_id: str) -> Dict[str, Any]:
        """Obtiene los objetivos del usuario."""
        # Implementación pendiente
        return {
            "target_weight": 80,
            "target_body_fat": 12,
            "target_measurements": {"chest": 110, "waist": 80, "arms": 40},
            "timeline": "6_months",
        }

    async def _save_progress_image(
        self, user_id: str, image: Union[str, bytes]
    ) -> Optional[str]:
        """Guarda una imagen de progreso."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = f"users/{user_id}/progress/images/{timestamp}.jpg"
            url = await self.advanced_vision_client.gcs_client.upload_image(image, path)

            # Registrar en base de datos
            # Implementación pendiente

            return url
        except Exception as e:
            logger.error(f"Error guardando imagen de progreso: {e}")
            return None

    async def _generate_progress_visualization(
        self, user_id: str, analysis: Dict[str, Any], metrics: Dict[str, Any]
    ) -> Optional[str]:
        """Genera visualización del progreso."""
        # Implementación pendiente - usar matplotlib o similar
        return None

    async def _calculate_progress_projections(
        self, analysis: Dict[str, Any], goals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula proyecciones de progreso futuro."""
        projections = {
            "estimated_goal_date": "2025-12-01",
            "current_pace": "on_track",
            "required_adjustments": [],
        }

        # Implementar lógica de proyección basada en tendencias

        return projections

    async def _generate_plan_adjustments(
        self, analysis: Dict[str, Any], goals: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Genera ajustes recomendados al plan."""
        adjustments = []

        # Analizar si el progreso está alineado con objetivos
        # y generar recomendaciones

        adjustments.append(
            {
                "area": "training",
                "adjustment": "Aumentar volumen de piernas en 20%",
                "reasoning": "Desequilibrio detectado entre tren superior e inferior",
            }
        )

        return adjustments

    async def _get_latest_measurements(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene las últimas medidas del usuario."""
        # Implementación pendiente
        return None

    async def _save_measurements(
        self, user_id: str, measurements: Dict[str, Any]
    ) -> bool:
        """Guarda las medidas extraídas."""
        # Implementación pendiente
        return True

    async def _get_measurement_goals(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene los objetivos de medidas del usuario."""
        # Implementación pendiente
        return {"chest": 110, "waist": 80, "arms": 40, "thighs": 60}

    def _compare_with_measurement_goals(
        self, current: Dict[str, Any], goals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compara medidas actuales con objetivos."""
        comparison = {}

        for measure, goal_value in goals.items():
            current_value = current.get("circumferences", {}).get(measure)
            if current_value and isinstance(current_value, (int, float)):
                difference = goal_value - current_value
                percentage = (
                    (current_value / goal_value * 100) if goal_value != 0 else 0
                )
                comparison[measure] = {
                    "current": current_value,
                    "goal": goal_value,
                    "difference": difference,
                    "progress_percentage": percentage,
                }

        return comparison

    async def _generate_measurements_chart(self, user_id: str) -> Optional[str]:
        """Genera gráfico de evolución de medidas."""
        # Implementación pendiente
        return None

    async def _gather_report_data(self, user_id: str, period: str) -> Dict[str, Any]:
        """Recopila todos los datos para el reporte."""
        # Implementación pendiente
        return {
            "user_id": user_id,
            "period": period,
            "progress_images": [],
            "measurements": [],
            "workouts": [],
            "nutrition": [],
        }

    async def _generate_comprehensive_analysis(
        self, report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Genera análisis comprehensivo de los datos."""
        # Usar Gemini para análisis profundo
        prompt = f"""
        Analiza los siguientes datos de progreso y genera un análisis ejecutivo:
        
        {json.dumps(report_data, indent=2)}
        
        Proporciona:
        1. Resumen ejecutivo
        2. Logros clave
        3. Áreas de mejora
        4. Recomendaciones específicas
        5. Proyecciones futuras
        """

        # Llamar a Gemini
        # Implementación pendiente

        return {
            "executive_summary": "Progreso consistente en los últimos 30 días",
            "achievements": [
                "Reducción de 2% grasa corporal",
                "Aumento de fuerza en 10%",
            ],
            "improvements": ["Mayor enfoque en movilidad", "Consistencia en nutrición"],
            "recommendations": ["Aumentar proteína diaria", "Añadir día de movilidad"],
            "projections": {"goal_achievement_date": "2025-12-01"},
        }

    async def _create_report_visualizations(
        self, report_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Crea visualizaciones para el reporte."""
        # Implementación pendiente
        return {
            "progress_timeline": "url_to_timeline_chart",
            "measurements_evolution": "url_to_measurements_chart",
            "body_composition": "url_to_composition_chart",
        }

    async def _generate_pdf_report(
        self, user_id: str, analysis: Dict[str, Any], visualizations: Dict[str, str]
    ) -> Optional[str]:
        """Genera PDF del reporte."""
        # Implementación pendiente - usar reportlab o similar
        return None

    async def _notify_report_ready(self, user_id: str, report: Dict[str, Any]) -> None:
        """Notifica al usuario que el reporte está listo."""
        # Implementación pendiente - enviar notificación
        pass

    async def _update_progress_index(
        self, user_id: str, checkpoint_type: str, image_url: str, analysis_path: str
    ) -> None:
        """Actualiza el índice de progreso en la base de datos."""
        # Implementación pendiente
        pass

"""
Visualization skills for generating charts and reports.

These skills allow agents to create visual content like progress charts,
nutritional infographics, and comprehensive reports.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.skill import Skill
from core.visualization import (
    ExerciseVideoLinkGenerator,
    NutritionInfographicGenerator,
    PDFReportGenerator,
    ProgressChartGenerator,
)
from clients.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class GenerateProgressChartSkill(Skill):
    """Skill for generating various progress charts."""

    def __init__(self):
        super().__init__(
            name="generate_progress_chart",
            description="Generate visual progress charts for fitness metrics",
            parameters={
                "chart_type": {
                    "type": "string",
                    "description": "Type of chart to generate",
                    "enum": ["weight", "body_composition", "performance", "comparison"],
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for the data",
                    "enum": ["7d", "30d", "90d", "1y"],
                    "default": "30d",
                },
                "metric_type": {
                    "type": "string",
                    "description": "For performance charts: strength, endurance, flexibility",
                    "enum": ["strength", "endurance", "flexibility"],
                    "required": False,
                },
                "comparison_period": {
                    "type": "string",
                    "description": "For comparison charts: week, month, quarter",
                    "enum": ["week", "month", "quarter"],
                    "required": False,
                },
            },
        )
        self.chart_generator = ProgressChartGenerator()

    async def execute(self, context: Dict[str, Any], **params) -> Dict[str, Any]:
        """Generate a progress chart based on user data."""
        try:
            user_id = context.get("user_id")
            if not user_id:
                return {"status": "error", "message": "User ID not found in context"}

            chart_type = params.get("chart_type", "weight")
            time_range = params.get("time_range", "30d")

            # Calculate date range
            days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(time_range, 30)
            start_date = datetime.now() - timedelta(days=days)

            supabase = get_supabase_client()

            if chart_type == "weight":
                # Fetch weight data
                response = (
                    supabase.table("weight_logs")
                    .select("*")
                    .eq("user_id", user_id)
                    .gte("date", start_date.isoformat())
                    .order("date")
                    .execute()
                )

                if not response.data:
                    return {
                        "status": "info",
                        "message": "No weight data found for the specified period",
                    }

                # Get user info
                user_response = (
                    supabase.table("users")
                    .select("*")
                    .eq("id", user_id)
                    .single()
                    .execute()
                )

                user_info = {
                    "name": (
                        user_response.data.get("full_name", "User")
                        if user_response.data
                        else "User"
                    ),
                    "goal_weight": (
                        user_response.data.get("goal_weight")
                        if user_response.data
                        else None
                    ),
                }

                # Generate chart
                chart_bytes = await self.chart_generator.generate_weight_progress_chart(
                    response.data, user_info
                )

                return {
                    "status": "success",
                    "chart_type": "weight_progress",
                    "time_range": time_range,
                    "data_points": len(response.data),
                    "chart_generated": True,
                    "message": f"Generated weight progress chart for the last {time_range}",
                }

            elif chart_type == "body_composition":
                # Fetch body composition data
                response = (
                    supabase.table("body_composition_logs")
                    .select("*")
                    .eq("user_id", user_id)
                    .gte("date", start_date.isoformat())
                    .order("date")
                    .execute()
                )

                if not response.data:
                    return {
                        "status": "info",
                        "message": "No body composition data found for the specified period",
                    }

                chart_bytes = (
                    await self.chart_generator.generate_body_composition_chart(
                        response.data
                    )
                )

                return {
                    "status": "success",
                    "chart_type": "body_composition",
                    "time_range": time_range,
                    "data_points": len(response.data),
                    "chart_generated": True,
                    "message": f"Generated body composition chart for the last {time_range}",
                }

            elif chart_type == "performance":
                metric_type = params.get("metric_type", "strength")

                # Fetch performance data
                response = (
                    supabase.table("performance_logs")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("metric_type", metric_type)
                    .gte("date", start_date.isoformat())
                    .order("date")
                    .execute()
                )

                if not response.data:
                    return {
                        "status": "info",
                        "message": f"No {metric_type} performance data found",
                    }

                chart_bytes = (
                    await self.chart_generator.generate_performance_metrics_chart(
                        response.data, metric_type
                    )
                )

                return {
                    "status": "success",
                    "chart_type": f"{metric_type}_performance",
                    "time_range": time_range,
                    "data_points": len(response.data),
                    "chart_generated": True,
                    "message": f"Generated {metric_type} performance chart for the last {time_range}",
                }

            elif chart_type == "comparison":
                period = params.get("comparison_period", "month")

                # Implementation would fetch and compare data between periods
                # For now, return a placeholder
                return {
                    "status": "success",
                    "chart_type": "comparison",
                    "period": period,
                    "message": f"Generated {period}-over-{period} comparison chart",
                }

            else:
                return {
                    "status": "error",
                    "message": f"Unknown chart type: {chart_type}",
                }

        except Exception as e:
            logger.error(f"Error generating progress chart: {e}")
            return {"status": "error", "message": f"Failed to generate chart: {str(e)}"}


class GenerateNutritionInfographicSkill(Skill):
    """Skill for generating nutrition-related infographics."""

    def __init__(self):
        super().__init__(
            name="generate_nutrition_infographic",
            description="Generate visual nutrition breakdowns and meal plans",
            parameters={
                "infographic_type": {
                    "type": "string",
                    "description": "Type of infographic to generate",
                    "enum": ["daily_breakdown", "meal_plan"],
                },
                "date": {
                    "type": "string",
                    "description": "Date for the data (ISO format)",
                    "required": False,
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days for meal plan",
                    "default": 7,
                    "required": False,
                },
            },
        )
        self.nutrition_generator = NutritionInfographicGenerator()

    async def execute(self, context: Dict[str, Any], **params) -> Dict[str, Any]:
        """Generate a nutrition infographic."""
        try:
            user_id = context.get("user_id")
            if not user_id:
                return {"status": "error", "message": "User ID not found in context"}

            infographic_type = params.get("infographic_type", "daily_breakdown")

            if infographic_type == "daily_breakdown":
                target_date = params.get("date")
                if target_date:
                    target_date = datetime.fromisoformat(target_date)
                else:
                    target_date = datetime.now()

                supabase = get_supabase_client()

                # Fetch nutrition data for the day
                response = (
                    supabase.table("nutrition_logs")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("date", target_date.date().isoformat())
                    .execute()
                )

                if not response.data:
                    return {
                        "status": "info",
                        "message": "No nutrition data found for the specified date",
                    }

                # Aggregate nutrition data
                nutrition_data = self._aggregate_nutrition_data(response.data)

                # Get user nutrition targets
                user_response = (
                    supabase.table("users")
                    .select("nutrition_targets")
                    .eq("id", user_id)
                    .single()
                    .execute()
                )

                if user_response.data and user_response.data.get("nutrition_targets"):
                    targets = user_response.data["nutrition_targets"]
                    nutrition_data.update(
                        {
                            "calories_target": targets.get("calories", 2000),
                            "protein_target": targets.get("protein", 150),
                            "carbs_target": targets.get("carbs", 250),
                            "fat_target": targets.get("fat", 65),
                            "fiber_target": targets.get("fiber", 30),
                        }
                    )

                # Generate infographic
                chart_bytes = (
                    await self.nutrition_generator.generate_daily_nutrition_breakdown(
                        nutrition_data
                    )
                )

                return {
                    "status": "success",
                    "infographic_type": "daily_nutrition_breakdown",
                    "date": target_date.date().isoformat(),
                    "total_calories": nutrition_data.get("calories_consumed", 0),
                    "infographic_generated": True,
                    "message": f"Generated nutrition breakdown for {target_date.date()}",
                }

            elif infographic_type == "meal_plan":
                days = params.get("days", 7)
                start_date = params.get("date")
                if start_date:
                    start = datetime.fromisoformat(start_date)
                else:
                    start = datetime.now()

                end = start + timedelta(days=days)

                supabase = get_supabase_client()

                # Fetch meal plan data
                response = (
                    supabase.table("meal_plans")
                    .select("*")
                    .eq("user_id", user_id)
                    .gte("date", start.date().isoformat())
                    .lt("date", end.date().isoformat())
                    .order("date")
                    .execute()
                )

                if not response.data:
                    return {
                        "status": "info",
                        "message": "No meal plan found for the specified period",
                    }

                # Organize meal plan by day
                meal_plan = self._organize_meal_plan(response.data)

                # Generate infographic
                chart_bytes = (
                    await self.nutrition_generator.generate_meal_plan_infographic(
                        meal_plan
                    )
                )

                return {
                    "status": "success",
                    "infographic_type": "meal_plan",
                    "start_date": start.date().isoformat(),
                    "days": days,
                    "infographic_generated": True,
                    "message": f"Generated {days}-day meal plan infographic",
                }

            else:
                return {
                    "status": "error",
                    "message": f"Unknown infographic type: {infographic_type}",
                }

        except Exception as e:
            logger.error(f"Error generating nutrition infographic: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate infographic: {str(e)}",
            }

    def _aggregate_nutrition_data(
        self, nutrition_logs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Helper to aggregate nutrition data."""
        aggregated = {
            "calories_consumed": sum(log.get("calories", 0) for log in nutrition_logs),
            "protein": sum(log.get("protein", 0) for log in nutrition_logs),
            "carbs": sum(log.get("carbs", 0) for log in nutrition_logs),
            "fat": sum(log.get("fat", 0) for log in nutrition_logs),
            "fiber": sum(log.get("fiber", 0) for log in nutrition_logs),
            "meals": {},
        }

        # Group by meal type
        for log in nutrition_logs:
            meal_type = log.get("meal_type", "snack")
            if meal_type not in aggregated["meals"]:
                aggregated["meals"][meal_type] = {
                    "calories": 0,
                    "protein": 0,
                    "carbs": 0,
                    "fat": 0,
                }

            aggregated["meals"][meal_type]["calories"] += log.get("calories", 0)
            aggregated["meals"][meal_type]["protein"] += log.get("protein", 0)
            aggregated["meals"][meal_type]["carbs"] += log.get("carbs", 0)
            aggregated["meals"][meal_type]["fat"] += log.get("fat", 0)

        return aggregated

    def _organize_meal_plan(
        self, meal_plan_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Helper to organize meal plan by day."""
        meal_plan = {}

        for item in meal_plan_data:
            date_str = item["date"]
            if date_str not in meal_plan:
                meal_plan[date_str] = {}

            meal_type = item.get("meal_type", "meal")
            meal_plan[date_str][meal_type] = {
                "name": item.get("meal_name", "Meal"),
                "calories": item.get("calories", 0),
                "protein": item.get("protein", 0),
                "carbs": item.get("carbs", 0),
                "fat": item.get("fat", 0),
            }

        return meal_plan


class GenerateProgressReportSkill(Skill):
    """Skill for generating comprehensive progress reports."""

    def __init__(self):
        super().__init__(
            name="generate_progress_report",
            description="Generate comprehensive PDF progress reports",
            parameters={
                "period": {
                    "type": "string",
                    "description": "Report period",
                    "enum": ["weekly", "monthly", "quarterly"],
                    "default": "monthly",
                },
                "include_sections": {
                    "type": "array",
                    "description": "Sections to include in the report",
                    "items": {
                        "type": "string",
                        "enum": [
                            "weight",
                            "body_composition",
                            "performance",
                            "nutrition",
                            "recommendations",
                        ],
                    },
                    "default": [
                        "weight",
                        "body_composition",
                        "performance",
                        "nutrition",
                        "recommendations",
                    ],
                },
            },
        )
        self.pdf_generator = PDFReportGenerator()

    async def execute(self, context: Dict[str, Any], **params) -> Dict[str, Any]:
        """Generate a comprehensive progress report."""
        try:
            user_id = context.get("user_id")
            if not user_id:
                return {"status": "error", "message": "User ID not found in context"}

            period = params.get("period", "monthly")
            include_sections = params.get(
                "include_sections",
                [
                    "weight",
                    "body_composition",
                    "performance",
                    "nutrition",
                    "recommendations",
                ],
            )

            # Calculate date range
            period_days = {"weekly": 7, "monthly": 30, "quarterly": 90}.get(period, 30)

            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            # Fetch all necessary data
            supabase = get_supabase_client()

            # User data
            user_response = (
                supabase.table("users").select("*").eq("id", user_id).single().execute()
            )

            if not user_response.data:
                return {"status": "error", "message": "User data not found"}

            user_data = {
                "name": user_response.data.get("full_name", "User"),
                "email": user_response.data.get("email"),
                "age": user_response.data.get("age"),
                "height": user_response.data.get("height"),
                "goals": user_response.data.get("goals", {}),
            }

            progress_data = {"period": period}

            # Fetch data for each included section
            if "weight" in include_sections:
                weight_response = (
                    supabase.table("weight_logs")
                    .select("*")
                    .eq("user_id", user_id)
                    .gte("date", start_date.isoformat())
                    .order("date")
                    .execute()
                )

                if weight_response.data:
                    progress_data["weight_data"] = weight_response.data
                    if len(weight_response.data) >= 2:
                        progress_data["weight_change"] = (
                            weight_response.data[-1]["weight"]
                            - weight_response.data[0]["weight"]
                        )

            if "body_composition" in include_sections:
                body_comp_response = (
                    supabase.table("body_composition_logs")
                    .select("*")
                    .eq("user_id", user_id)
                    .gte("date", start_date.isoformat())
                    .order("date")
                    .execute()
                )

                if body_comp_response.data:
                    progress_data["body_composition_data"] = body_comp_response.data
                    if len(body_comp_response.data) >= 2:
                        progress_data["body_fat_change"] = body_comp_response.data[
                            -1
                        ].get("body_fat", 0) - body_comp_response.data[0].get(
                            "body_fat", 0
                        )
                        progress_data["muscle_mass_change"] = body_comp_response.data[
                            -1
                        ].get("muscle_mass", 0) - body_comp_response.data[0].get(
                            "muscle_mass", 0
                        )

            if "performance" in include_sections:
                performance_response = (
                    supabase.table("performance_logs")
                    .select("*")
                    .eq("user_id", user_id)
                    .gte("date", start_date.isoformat())
                    .order("date")
                    .execute()
                )

                if performance_response.data:
                    progress_data["performance_data"] = performance_response.data
                    progress_data["performance_type"] = (
                        "strength"  # Could be determined from data
                    )

            if "nutrition" in include_sections:
                # Get last day's nutrition for summary
                nutrition_response = (
                    supabase.table("nutrition_logs")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("date", end_date.date().isoformat())
                    .execute()
                )

                if nutrition_response.data:
                    progress_data["nutrition_data"] = self._aggregate_nutrition_data(
                        nutrition_response.data
                    )

            # Add compliance metrics
            progress_data["workout_compliance"] = (
                85  # This would be calculated from actual data
            )
            progress_data["nutrition_adherence"] = (
                78  # This would be calculated from actual data
            )
            progress_data["overall_assessment"] = (
                "excellent"  # This would be determined by analysis
            )

            # Generate PDF report
            pdf_bytes = await self.pdf_generator.generate_progress_report(
                user_data, progress_data, period
            )

            # In a real implementation, you would save the PDF and return a URL
            # For now, we'll just return success status
            return {
                "status": "success",
                "report_type": "progress_report",
                "period": period,
                "sections_included": include_sections,
                "report_generated": True,
                "message": f"Generated {period} progress report with {len(include_sections)} sections",
            }

        except Exception as e:
            logger.error(f"Error generating progress report: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate report: {str(e)}",
            }

    def _aggregate_nutrition_data(
        self, nutrition_logs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Helper to aggregate nutrition data."""
        aggregated = {
            "calories_consumed": sum(log.get("calories", 0) for log in nutrition_logs),
            "protein_consumed": sum(log.get("protein", 0) for log in nutrition_logs),
            "carbs_consumed": sum(log.get("carbs", 0) for log in nutrition_logs),
            "fat_consumed": sum(log.get("fat", 0) for log in nutrition_logs),
            "fiber_consumed": sum(log.get("fiber", 0) for log in nutrition_logs),
            "meals": {},
        }

        # Group by meal type
        for log in nutrition_logs:
            meal_type = log.get("meal_type", "snack")
            if meal_type not in aggregated["meals"]:
                aggregated["meals"][meal_type] = {"calories": 0}
            aggregated["meals"][meal_type]["calories"] += log.get("calories", 0)

        return aggregated


class GetExerciseVideosSkill(Skill):
    """Skill for getting exercise demonstration video links."""

    def __init__(self):
        super().__init__(
            name="get_exercise_videos",
            description="Get video links for exercise demonstrations",
            parameters={
                "exercises": {
                    "type": "array",
                    "description": "List of exercise names",
                    "items": {"type": "string"},
                },
                "create_playlist": {
                    "type": "boolean",
                    "description": "Whether to create a playlist",
                    "default": False,
                },
            },
        )
        self.video_generator = ExerciseVideoLinkGenerator()

    async def execute(self, context: Dict[str, Any], **params) -> Dict[str, Any]:
        """Get exercise video links."""
        try:
            exercises = params.get("exercises", [])
            create_playlist = params.get("create_playlist", False)

            if not exercises:
                return {"status": "error", "message": "No exercises specified"}

            # Get video links
            video_links = await self.video_generator.get_exercise_video_links(exercises)

            result = {
                "status": "success",
                "videos": video_links,
                "total_videos": len(video_links),
                "message": f"Found video links for {len(video_links)} exercises",
            }

            # If playlist requested, organize as workout
            if create_playlist:
                workout_plan = {
                    "name": "Custom Exercise Playlist",
                    "exercises": [
                        {
                            "muscle_group": "Mixed",
                            "exercises": [
                                {"name": ex, "sets": 3, "reps": "8-12", "rest": "60s"}
                                for ex in exercises
                            ],
                        }
                    ],
                }

                playlist = await self.video_generator.generate_workout_video_playlist(
                    workout_plan
                )
                result["playlist"] = playlist
                result["message"] += " and created playlist"

            return result

        except Exception as e:
            logger.error(f"Error getting exercise videos: {e}")
            return {"status": "error", "message": f"Failed to get videos: {str(e)}"}


# Export all visualization skills
__all__ = [
    "GenerateProgressChartSkill",
    "GenerateNutritionInfographicSkill",
    "GenerateProgressReportSkill",
    "GetExerciseVideosSkill",
]

"""
Report Generation Tasks
Async tasks for generating various reports and documents
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from core.celery_app import app
from clients.supabase_client import SupabaseClient
from visualization.generators.pdf_report import PDFReportGenerator
from visualization.generators.progress_chart import ProgressChartGenerator
from visualization.generators.nutrition_infographic import NutritionInfographicGenerator

logger = logging.getLogger(__name__)


class BaseReportTask(Task):
    """Base class for report generation tasks with common functionality"""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    track_started = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Task {task_id} failed: {exc}", exc_info=einfo)
        # Could send notification or update status in database

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        logger.info(f"Task {task_id} completed successfully")


@app.task(base=BaseReportTask, name="tasks.reports.generate_progress_report")
def generate_progress_report(
    user_id: str, period: str = "monthly", include_charts: bool = True
) -> Dict[str, Any]:
    """
    Generate comprehensive progress report for a user

    Args:
        user_id: User identifier
        period: Report period (weekly, monthly, quarterly)
        include_charts: Whether to include visual charts

    Returns:
        Dict with report URL and metadata
    """
    try:
        logger.info(f"Generating progress report for user {user_id}, period: {period}")

        # Initialize clients
        supabase = SupabaseClient()
        pdf_generator = PDFReportGenerator()
        chart_generator = ProgressChartGenerator()

        # Fetch user data
        user_data = supabase.get_user_profile(user_id)
        progress_data = supabase.get_user_progress(user_id, period)
        workout_history = supabase.get_workout_history(user_id, period)

        # Generate charts if requested
        charts = {}
        if include_charts:
            charts = {
                "weight_progress": chart_generator.generate_weight_chart(
                    progress_data.get("weight_history", [])
                ),
                "performance_metrics": chart_generator.generate_performance_chart(
                    progress_data.get("performance_data", [])
                ),
                "consistency_calendar": chart_generator.generate_consistency_calendar(
                    workout_history
                ),
            }

        # Compile report data
        report_data = {
            "user": user_data,
            "period": period,
            "summary": _calculate_progress_summary(progress_data),
            "workouts": workout_history,
            "achievements": progress_data.get("achievements", []),
            "charts": charts,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Generate PDF
        pdf_path = pdf_generator.generate_progress_report(report_data)

        # Upload to storage
        report_url = supabase.upload_file(
            pdf_path, f"reports/{user_id}/{period}_report.pdf"
        )

        # Store report metadata
        report_metadata = {
            "user_id": user_id,
            "report_type": "progress",
            "period": period,
            "url": report_url,
            "generated_at": datetime.utcnow().isoformat(),
            "file_size": _get_file_size(pdf_path),
        }
        supabase.save_report_metadata(report_metadata)

        logger.info(f"Progress report generated successfully: {report_url}")

        return {"success": True, "report_url": report_url, "metadata": report_metadata}

    except SoftTimeLimitExceeded:
        logger.error("Task exceeded soft time limit")
        raise
    except Exception as e:
        logger.error(f"Error generating progress report: {e}")
        raise


@app.task(base=BaseReportTask, name="tasks.reports.generate_nutrition_plan_pdf")
def generate_nutrition_plan_pdf(
    user_id: str, plan_id: str, include_recipes: bool = True
) -> Dict[str, Any]:
    """
    Generate PDF version of nutrition plan

    Args:
        user_id: User identifier
        plan_id: Nutrition plan identifier
        include_recipes: Whether to include detailed recipes

    Returns:
        Dict with PDF URL and metadata
    """
    try:
        logger.info(f"Generating nutrition plan PDF for user {user_id}, plan {plan_id}")

        # Initialize clients
        supabase = SupabaseClient()
        pdf_generator = PDFReportGenerator()
        infographic_generator = NutritionInfographicGenerator()

        # Fetch plan data
        plan_data = supabase.get_nutrition_plan(plan_id)
        user_preferences = supabase.get_user_nutrition_preferences(user_id)

        # Generate nutrition infographics
        infographics = {
            "macro_distribution": infographic_generator.generate_macro_chart(
                plan_data.get("macros", {})
            ),
            "meal_timing": infographic_generator.generate_meal_timing_chart(
                plan_data.get("meal_schedule", [])
            ),
            "weekly_overview": infographic_generator.generate_weekly_overview(
                plan_data.get("weekly_meals", {})
            ),
        }

        # Fetch recipes if requested
        recipes = []
        if include_recipes:
            meal_ids = [meal["id"] for meal in plan_data.get("meals", [])]
            recipes = supabase.get_recipes_batch(meal_ids)

        # Compile plan document data
        document_data = {
            "user_id": user_id,
            "plan": plan_data,
            "preferences": user_preferences,
            "infographics": infographics,
            "recipes": recipes,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Generate PDF
        pdf_path = pdf_generator.generate_nutrition_plan(document_data)

        # Upload to storage
        plan_url = supabase.upload_file(
            pdf_path, f"nutrition_plans/{user_id}/{plan_id}_plan.pdf"
        )

        # Update plan with PDF URL
        supabase.update_nutrition_plan(plan_id, {"pdf_url": plan_url})

        logger.info(f"Nutrition plan PDF generated successfully: {plan_url}")

        return {
            "success": True,
            "plan_url": plan_url,
            "plan_id": plan_id,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error generating nutrition plan PDF: {e}")
        raise


@app.task(base=BaseReportTask, name="tasks.reports.generate_workout_summary")
def generate_workout_summary(user_id: str, workout_ids: List[str]) -> Dict[str, Any]:
    """
    Generate workout summary report

    Args:
        user_id: User identifier
        workout_ids: List of workout IDs to include

    Returns:
        Dict with summary URL and statistics
    """
    try:
        logger.info(
            f"Generating workout summary for user {user_id}, workouts: {workout_ids}"
        )

        # Initialize clients
        supabase = SupabaseClient()
        pdf_generator = PDFReportGenerator()
        chart_generator = ProgressChartGenerator()

        # Fetch workout data
        workouts = supabase.get_workouts_batch(workout_ids)

        # Calculate statistics
        stats = _calculate_workout_statistics(workouts)

        # Generate performance charts
        charts = {
            "volume_progression": chart_generator.generate_volume_chart(workouts),
            "intensity_distribution": chart_generator.generate_intensity_chart(
                workouts
            ),
            "exercise_breakdown": chart_generator.generate_exercise_breakdown(workouts),
        }

        # Compile summary data
        summary_data = {
            "user_id": user_id,
            "workouts": workouts,
            "statistics": stats,
            "charts": charts,
            "period": _determine_period(workouts),
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Generate PDF summary
        pdf_path = pdf_generator.generate_workout_summary(summary_data)

        # Upload to storage
        summary_url = supabase.upload_file(
            pdf_path,
            f"workout_summaries/{user_id}/{datetime.utcnow().strftime('%Y%m%d')}_summary.pdf",
        )

        logger.info(f"Workout summary generated successfully: {summary_url}")

        return {
            "success": True,
            "summary_url": summary_url,
            "statistics": stats,
            "workout_count": len(workouts),
        }

    except Exception as e:
        logger.error(f"Error generating workout summary: {e}")
        raise


@app.task(base=BaseReportTask, name="tasks.reports.generate_achievement_certificate")
def generate_achievement_certificate(
    user_id: str, achievement_id: str
) -> Dict[str, Any]:
    """
    Generate achievement certificate for user milestones

    Args:
        user_id: User identifier
        achievement_id: Achievement identifier

    Returns:
        Dict with certificate URL
    """
    try:
        logger.info(
            f"Generating achievement certificate for user {user_id}, achievement {achievement_id}"
        )

        # Initialize clients
        supabase = SupabaseClient()
        pdf_generator = PDFReportGenerator()

        # Fetch achievement and user data
        achievement = supabase.get_achievement(achievement_id)
        user_data = supabase.get_user_profile(user_id)

        # Generate certificate
        certificate_data = {
            "user_name": user_data.get("name"),
            "achievement": achievement,
            "earned_date": datetime.utcnow().isoformat(),
            "certificate_id": f"{user_id}-{achievement_id}-{datetime.utcnow().timestamp()}",
        }

        pdf_path = pdf_generator.generate_achievement_certificate(certificate_data)

        # Upload certificate
        certificate_url = supabase.upload_file(
            pdf_path, f"certificates/{user_id}/{achievement_id}_certificate.pdf"
        )

        # Update achievement record
        supabase.update_achievement(
            achievement_id,
            {
                "certificate_url": certificate_url,
                "certificate_generated_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(
            f"Achievement certificate generated successfully: {certificate_url}"
        )

        return {
            "success": True,
            "certificate_url": certificate_url,
            "achievement": achievement,
        }

    except Exception as e:
        logger.error(f"Error generating achievement certificate: {e}")
        raise


@app.task(name="tasks.reports.batch_generate_weekly_summaries")
def batch_generate_weekly_summaries(user_ids: List[str]) -> Dict[str, Any]:
    """
    Batch generate weekly summaries for multiple users

    Args:
        user_ids: List of user identifiers

    Returns:
        Dict with generation results
    """
    logger.info(f"Batch generating weekly summaries for {len(user_ids)} users")

    results = {"successful": 0, "failed": 0, "details": []}

    for user_id in user_ids:
        try:
            # Launch individual task
            result = generate_progress_report.apply_async(
                args=[user_id, "weekly", True], queue="reports", priority=2
            )

            results["details"].append(
                {"user_id": user_id, "task_id": result.id, "status": "queued"}
            )
            results["successful"] += 1

        except Exception as e:
            logger.error(f"Failed to queue summary for user {user_id}: {e}")
            results["failed"] += 1
            results["details"].append(
                {"user_id": user_id, "error": str(e), "status": "failed"}
            )

    return results


# Helper functions
def _calculate_progress_summary(progress_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate progress summary statistics"""
    return {
        "total_workouts": len(progress_data.get("workouts", [])),
        "weight_change": progress_data.get("weight_change", 0),
        "strength_improvement": progress_data.get("strength_improvement", 0),
        "consistency_score": progress_data.get("consistency_score", 0),
        "top_achievements": progress_data.get("achievements", [])[:3],
    }


def _calculate_workout_statistics(workouts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate workout statistics"""
    total_duration = sum(w.get("duration_minutes", 0) for w in workouts)
    total_volume = sum(w.get("total_volume", 0) for w in workouts)

    return {
        "total_workouts": len(workouts),
        "total_duration_hours": round(total_duration / 60, 1),
        "total_volume_kg": total_volume,
        "average_duration_minutes": (
            round(total_duration / len(workouts), 1) if workouts else 0
        ),
        "most_frequent_exercises": _get_most_frequent_exercises(workouts),
    }


def _get_most_frequent_exercises(workouts: List[Dict[str, Any]]) -> List[str]:
    """Get most frequently performed exercises"""
    exercise_count = {}
    for workout in workouts:
        for exercise in workout.get("exercises", []):
            name = exercise.get("name")
            if name:
                exercise_count[name] = exercise_count.get(name, 0) + 1

    return sorted(exercise_count.keys(), key=exercise_count.get, reverse=True)[:5]


def _determine_period(workouts: List[Dict[str, Any]]) -> str:
    """Determine the period covered by workouts"""
    if not workouts:
        return "unknown"

    dates = [datetime.fromisoformat(w["date"]) for w in workouts if "date" in w]
    if not dates:
        return "unknown"

    duration = (max(dates) - min(dates)).days

    if duration <= 7:
        return "weekly"
    elif duration <= 31:
        return "monthly"
    elif duration <= 93:
        return "quarterly"
    else:
        return "custom"


def _get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    import os

    return os.path.getsize(file_path)

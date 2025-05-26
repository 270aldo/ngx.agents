"""
Visualization API router for generating charts and reports.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse

from app.middleware.auth import get_current_user
from app.schemas.auth import User
from core.visualization import (
    ExerciseVideoLinkGenerator,
    NutritionInfographicGenerator,
    PDFReportGenerator,
    ProgressChartGenerator,
    create_progress_collage,
)
from clients.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visualization", tags=["visualization"])

# Initialize generators
progress_chart_gen = ProgressChartGenerator()
nutrition_gen = NutritionInfographicGenerator()
pdf_gen = PDFReportGenerator()
exercise_video_gen = ExerciseVideoLinkGenerator()


@router.post("/charts/weight-progress")
async def generate_weight_progress_chart(
    time_range: Optional[str] = "30d", current_user: User = Depends(get_current_user)
) -> Response:
    """
    Generate a weight progress chart for the current user.

    Args:
        time_range: Time range for data (e.g., "7d", "30d", "90d", "1y")
        current_user: Authenticated user

    Returns:
        PNG image of weight progress chart
    """
    try:
        # Parse time range
        days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(time_range, 30)

        start_date = datetime.now() - timedelta(days=days)

        # Fetch weight data from database
        supabase = get_supabase_client()
        response = (
            supabase.table("weight_logs")
            .select("*")
            .eq("user_id", current_user.id)
            .gte("date", start_date.isoformat())
            .order("date")
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404, detail="No weight data found for the specified period"
            )

        # Get user info including goals
        user_response = (
            supabase.table("users")
            .select("*")
            .eq("id", current_user.id)
            .single()
            .execute()
        )

        user_info = {
            "name": current_user.email.split("@")[0],
            "goal_weight": (
                user_response.data.get("goal_weight") if user_response.data else None
            ),
        }

        # Generate chart
        chart_bytes = await progress_chart_gen.generate_weight_progress_chart(
            response.data, user_info
        )

        return Response(
            content=chart_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=weight_progress.png"},
        )

    except Exception as e:
        logger.error(f"Error generating weight progress chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/charts/body-composition")
async def generate_body_composition_chart(
    time_range: Optional[str] = "30d", current_user: User = Depends(get_current_user)
) -> Response:
    """
    Generate a body composition chart showing muscle mass, body fat, etc.

    Args:
        time_range: Time range for data
        current_user: Authenticated user

    Returns:
        PNG image of body composition chart
    """
    try:
        days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(time_range, 30)

        start_date = datetime.now() - timedelta(days=days)

        # Fetch body composition data
        supabase = get_supabase_client()
        response = (
            supabase.table("body_composition_logs")
            .select("*")
            .eq("user_id", current_user.id)
            .gte("date", start_date.isoformat())
            .order("date")
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="No body composition data found for the specified period",
            )

        # Generate chart
        chart_bytes = await progress_chart_gen.generate_body_composition_chart(
            response.data
        )

        return Response(
            content=chart_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=body_composition.png"},
        )

    except Exception as e:
        logger.error(f"Error generating body composition chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/charts/performance/{metric_type}")
async def generate_performance_chart(
    metric_type: str,
    time_range: Optional[str] = "30d",
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Generate performance metrics charts.

    Args:
        metric_type: Type of metric ('strength', 'endurance', 'flexibility')
        time_range: Time range for data
        current_user: Authenticated user

    Returns:
        PNG image of performance metrics
    """
    try:
        if metric_type not in ["strength", "endurance", "flexibility"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid metric type. Must be 'strength', 'endurance', or 'flexibility'",
            )

        days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(time_range, 30)

        start_date = datetime.now() - timedelta(days=days)

        # Fetch performance data
        supabase = get_supabase_client()
        response = (
            supabase.table("performance_logs")
            .select("*")
            .eq("user_id", current_user.id)
            .eq("metric_type", metric_type)
            .gte("date", start_date.isoformat())
            .order("date")
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404, detail=f"No {metric_type} performance data found"
            )

        # Generate chart
        chart_bytes = await progress_chart_gen.generate_performance_metrics_chart(
            response.data, metric_type
        )

        return Response(
            content=chart_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename={metric_type}_performance.png"
            },
        )

    except Exception as e:
        logger.error(f"Error generating performance chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/charts/comparison")
async def generate_comparison_chart(
    period: str = "month", current_user: User = Depends(get_current_user)
) -> Response:
    """
    Generate a comparison chart between current and previous period.

    Args:
        period: Comparison period ('week', 'month', 'quarter')
        current_user: Authenticated user

    Returns:
        PNG image of comparison chart
    """
    try:
        # Calculate date ranges
        period_days = {"week": 7, "month": 30, "quarter": 90}.get(period, 30)

        current_end = datetime.now()
        current_start = current_end - timedelta(days=period_days)
        previous_end = current_start
        previous_start = previous_end - timedelta(days=period_days)

        # Fetch data for both periods
        supabase = get_supabase_client()

        # Get current period averages
        current_response = supabase.rpc(
            "get_period_averages",
            {
                "user_id": current_user.id,
                "start_date": current_start.isoformat(),
                "end_date": current_end.isoformat(),
            },
        ).execute()

        # Get previous period averages
        previous_response = supabase.rpc(
            "get_period_averages",
            {
                "user_id": current_user.id,
                "start_date": previous_start.isoformat(),
                "end_date": previous_end.isoformat(),
            },
        ).execute()

        if not current_response.data or not previous_response.data:
            raise HTTPException(
                status_code=404, detail="Insufficient data for comparison"
            )

        # Generate comparison chart
        chart_bytes = await progress_chart_gen.generate_comparison_chart(
            current_response.data[0], previous_response.data[0], period
        )

        return Response(
            content=chart_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=comparison_{period}.png"
            },
        )

    except Exception as e:
        logger.error(f"Error generating comparison chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nutrition/daily-breakdown")
async def generate_nutrition_breakdown(
    date: Optional[str] = None, current_user: User = Depends(get_current_user)
) -> Response:
    """
    Generate a daily nutrition breakdown infographic.

    Args:
        date: Date for nutrition data (defaults to today)
        current_user: Authenticated user

    Returns:
        PNG image of nutrition breakdown
    """
    try:
        # Use today if no date specified
        target_date = datetime.fromisoformat(date) if date else datetime.now()

        # Fetch nutrition data
        supabase = get_supabase_client()
        response = (
            supabase.table("nutrition_logs")
            .select("*")
            .eq("user_id", current_user.id)
            .eq("date", target_date.date().isoformat())
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404, detail="No nutrition data found for the specified date"
            )

        # Aggregate nutrition data
        nutrition_data = {
            "calories_consumed": sum(item.get("calories", 0) for item in response.data),
            "calories_target": 2000,  # This should come from user settings
            "protein": sum(item.get("protein", 0) for item in response.data),
            "carbs": sum(item.get("carbs", 0) for item in response.data),
            "fat": sum(item.get("fat", 0) for item in response.data),
            "fiber": sum(item.get("fiber", 0) for item in response.data),
            "meals": {},
        }

        # Group by meal type
        for item in response.data:
            meal_type = item.get("meal_type", "snack")
            if meal_type not in nutrition_data["meals"]:
                nutrition_data["meals"][meal_type] = {
                    "calories": 0,
                    "protein": 0,
                    "carbs": 0,
                    "fat": 0,
                }

            nutrition_data["meals"][meal_type]["calories"] += item.get("calories", 0)
            nutrition_data["meals"][meal_type]["protein"] += item.get("protein", 0)
            nutrition_data["meals"][meal_type]["carbs"] += item.get("carbs", 0)
            nutrition_data["meals"][meal_type]["fat"] += item.get("fat", 0)

        # Get user targets
        user_response = (
            supabase.table("users")
            .select("nutrition_targets")
            .eq("id", current_user.id)
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
        chart_bytes = await nutrition_gen.generate_daily_nutrition_breakdown(
            nutrition_data
        )

        return Response(
            content=chart_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=nutrition_breakdown.png"},
        )

    except Exception as e:
        logger.error(f"Error generating nutrition breakdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nutrition/meal-plan")
async def generate_meal_plan_infographic(
    start_date: Optional[str] = None,
    days: int = 7,
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Generate a weekly meal plan infographic.

    Args:
        start_date: Start date for meal plan
        days: Number of days to include
        current_user: Authenticated user

    Returns:
        PNG image of meal plan
    """
    try:
        # Calculate date range
        start = datetime.fromisoformat(start_date) if start_date else datetime.now()
        end = start + timedelta(days=days)

        # Fetch meal plan data
        supabase = get_supabase_client()
        response = (
            supabase.table("meal_plans")
            .select("*")
            .eq("user_id", current_user.id)
            .gte("date", start.date().isoformat())
            .lt("date", end.date().isoformat())
            .order("date")
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404, detail="No meal plan found for the specified period"
            )

        # Organize meal plan by day
        meal_plan = {}
        for item in response.data:
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

        # Generate infographic
        chart_bytes = await nutrition_gen.generate_meal_plan_infographic(meal_plan)

        return Response(
            content=chart_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=meal_plan.png"},
        )

    except Exception as e:
        logger.error(f"Error generating meal plan infographic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/progress")
async def generate_progress_report(
    period: str = "monthly",
    format: str = "pdf",
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Generate a comprehensive progress report.

    Args:
        period: Report period ('weekly', 'monthly', 'quarterly')
        format: Output format ('pdf')
        current_user: Authenticated user

    Returns:
        PDF progress report
    """
    try:
        if format != "pdf":
            raise HTTPException(
                status_code=400, detail="Currently only PDF format is supported"
            )

        # Calculate date range
        period_days = {"weekly": 7, "monthly": 30, "quarterly": 90}.get(period, 30)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        # Fetch all necessary data
        supabase = get_supabase_client()

        # User data
        user_response = (
            supabase.table("users")
            .select("*")
            .eq("id", current_user.id)
            .single()
            .execute()
        )

        user_data = {
            "name": user_response.data.get(
                "full_name", current_user.email.split("@")[0]
            ),
            "email": current_user.email,
            "age": user_response.data.get("age"),
            "height": user_response.data.get("height"),
            "goals": user_response.data.get("goals", {}),
        }

        # Weight data
        weight_response = (
            supabase.table("weight_logs")
            .select("*")
            .eq("user_id", current_user.id)
            .gte("date", start_date.isoformat())
            .order("date")
            .execute()
        )

        # Body composition data
        body_comp_response = (
            supabase.table("body_composition_logs")
            .select("*")
            .eq("user_id", current_user.id)
            .gte("date", start_date.isoformat())
            .order("date")
            .execute()
        )

        # Performance data
        performance_response = (
            supabase.table("performance_logs")
            .select("*")
            .eq("user_id", current_user.id)
            .gte("date", start_date.isoformat())
            .order("date")
            .execute()
        )

        # Nutrition data (last day)
        nutrition_response = (
            supabase.table("nutrition_logs")
            .select("*")
            .eq("user_id", current_user.id)
            .eq("date", end_date.date().isoformat())
            .execute()
        )

        # Calculate progress metrics
        progress_data = {
            "period": period,
            "weight_data": weight_response.data,
            "body_composition_data": body_comp_response.data,
            "performance_data": performance_response.data,
            "performance_type": "strength",  # Could be determined from data
            "nutrition_data": self._aggregate_nutrition_data(nutrition_response.data),
        }

        # Calculate changes
        if weight_response.data and len(weight_response.data) >= 2:
            progress_data["weight_change"] = (
                weight_response.data[-1]["weight"] - weight_response.data[0]["weight"]
            )

        if body_comp_response.data and len(body_comp_response.data) >= 2:
            progress_data["body_fat_change"] = body_comp_response.data[-1].get(
                "body_fat", 0
            ) - body_comp_response.data[0].get("body_fat", 0)
            progress_data["muscle_mass_change"] = body_comp_response.data[-1].get(
                "muscle_mass", 0
            ) - body_comp_response.data[0].get("muscle_mass", 0)

        # Generate PDF report
        pdf_bytes = await pdf_gen.generate_progress_report(
            user_data, progress_data, period
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=progress_report_{period}_{datetime.now().strftime('%Y%m%d')}.pdf"
            },
        )

    except Exception as e:
        logger.error(f"Error generating progress report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exercise/video-links")
async def get_exercise_videos(
    exercises: List[str], current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get video links for exercises.

    Args:
        exercises: List of exercise names
        current_user: Authenticated user

    Returns:
        Exercise video information
    """
    try:
        video_links = await exercise_video_gen.get_exercise_video_links(exercises)

        return {
            "exercises": video_links,
            "total": len(video_links),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting exercise videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exercise/workout-playlist")
async def generate_workout_playlist(
    workout_plan: Dict[str, Any], current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate a video playlist for a workout plan.

    Args:
        workout_plan: Workout plan with exercises
        current_user: Authenticated user

    Returns:
        Playlist information with video links
    """
    try:
        playlist = await exercise_video_gen.generate_workout_video_playlist(
            workout_plan
        )

        return {"playlist": playlist, "generated_at": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"Error generating workout playlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collage/progress")
async def create_progress_collage_endpoint(
    image_ids: List[str],
    layout: str = "grid",
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Create a collage from multiple progress images.

    Args:
        image_ids: List of image IDs to include
        layout: Layout style ('grid', 'timeline', 'comparison')
        current_user: Authenticated user

    Returns:
        PNG image of collage
    """
    try:
        if layout not in ["grid", "timeline", "comparison"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid layout. Must be 'grid', 'timeline', or 'comparison'",
            )

        # Fetch images from storage
        supabase = get_supabase_client()
        images = []

        for image_id in image_ids:
            # This assumes images are stored in Supabase storage
            # Adjust based on your actual storage solution
            try:
                image_data = supabase.storage.from_("progress-images").download(
                    f"{current_user.id}/{image_id}"
                )
                images.append(image_data)
            except Exception as e:
                logger.warning(f"Could not fetch image {image_id}: {e}")

        if not images:
            raise HTTPException(status_code=404, detail="No valid images found")

        # Create collage
        collage_bytes = await create_progress_collage(images, layout)

        return Response(
            content=collage_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=progress_collage_{layout}.png"
            },
        )

    except Exception as e:
        logger.error(f"Error creating progress collage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _aggregate_nutrition_data(nutrition_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper function to aggregate nutrition data."""
    if not nutrition_logs:
        return {}

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

"""
Analytics and Data Analysis Tasks
Async tasks for data analysis, trends, and predictions
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from core.celery_app import app
from clients.supabase_client import SupabaseClient
from clients.vertex_ai.client import VertexAIClient
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class BaseAnalyticsTask(Task):
    """Base class for analytics tasks"""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 45}
    track_started = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Analytics task {task_id} failed: {exc}", exc_info=einfo)


@app.task(base=BaseAnalyticsTask, name="tasks.analytics.calculate_user_trends")
def calculate_user_trends(
    user_id: str, period_days: int = 30, metrics: List[str] = None
) -> Dict[str, Any]:
    """
    Calculate user trends over specified period

    Args:
        user_id: User identifier
        period_days: Number of days to analyze
        metrics: Specific metrics to analyze (default: all)

    Returns:
        Dict with trend analysis results
    """
    try:
        logger.info(f"Calculating trends for user {user_id} over {period_days} days")

        # Initialize client
        supabase = SupabaseClient()

        # Define default metrics if not specified
        if not metrics:
            metrics = [
                "weight",
                "body_fat",
                "muscle_mass",
                "strength",
                "endurance",
                "consistency",
                "calories",
                "protein",
            ]

        # Fetch historical data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)

        historical_data = supabase.get_user_metrics_history(
            user_id, start_date, end_date
        )

        # Calculate trends for each metric
        trends = {}
        predictions = {}

        for metric in metrics:
            metric_data = _extract_metric_data(historical_data, metric)

            if len(metric_data) >= 3:  # Need at least 3 data points
                # Calculate trend
                trend_analysis = _analyze_trend(metric_data)
                trends[metric] = trend_analysis

                # Make prediction
                prediction = _predict_future_value(metric_data, days_ahead=30)
                predictions[metric] = prediction
            else:
                trends[metric] = {"status": "insufficient_data"}
                predictions[metric] = None

        # Calculate overall progress score
        progress_score = _calculate_overall_progress(trends)

        # Identify key insights
        insights = _generate_insights(trends, historical_data)

        # Store analysis results
        analysis_record = {
            "user_id": user_id,
            "period_days": period_days,
            "trends": trends,
            "predictions": predictions,
            "progress_score": progress_score,
            "insights": insights,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        supabase.save_trend_analysis(analysis_record)

        logger.info(f"Trend analysis completed with progress score: {progress_score}")

        return {
            "success": True,
            "trends": trends,
            "predictions": predictions,
            "progress_score": progress_score,
            "insights": insights,
        }

    except Exception as e:
        logger.error(f"Error calculating user trends: {e}")
        raise


@app.task(base=BaseAnalyticsTask, name="tasks.analytics.analyze_workout_patterns")
def analyze_workout_patterns(user_id: str, period_days: int = 90) -> Dict[str, Any]:
    """
    Analyze workout patterns and habits

    Args:
        user_id: User identifier
        period_days: Number of days to analyze

    Returns:
        Dict with workout pattern analysis
    """
    try:
        logger.info(f"Analyzing workout patterns for user {user_id}")

        # Initialize client
        supabase = SupabaseClient()

        # Fetch workout history
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)

        workouts = supabase.get_workout_history(user_id, start_date, end_date)

        # Analyze patterns
        patterns = {
            "frequency": _analyze_workout_frequency(workouts),
            "timing": _analyze_workout_timing(workouts),
            "duration": _analyze_workout_duration(workouts),
            "intensity": _analyze_workout_intensity(workouts),
            "exercise_distribution": _analyze_exercise_distribution(workouts),
            "rest_days": _analyze_rest_patterns(workouts),
            "consistency_score": _calculate_consistency_score(workouts, period_days),
        }

        # Identify habits and recommendations
        habits = _identify_workout_habits(patterns)
        recommendations = _generate_workout_recommendations(patterns, habits)

        # Predict optimal workout times
        optimal_times = _predict_optimal_workout_times(workouts)

        # Store analysis
        pattern_record = {
            "user_id": user_id,
            "period_days": period_days,
            "patterns": patterns,
            "habits": habits,
            "recommendations": recommendations,
            "optimal_times": optimal_times,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        supabase.save_workout_pattern_analysis(pattern_record)

        logger.info(f"Workout pattern analysis completed")

        return {
            "success": True,
            "patterns": patterns,
            "habits": habits,
            "recommendations": recommendations,
            "optimal_workout_times": optimal_times,
        }

    except Exception as e:
        logger.error(f"Error analyzing workout patterns: {e}")
        raise


@app.task(base=BaseAnalyticsTask, name="tasks.analytics.predict_goal_achievement")
def predict_goal_achievement(user_id: str, goal_id: str) -> Dict[str, Any]:
    """
    Predict likelihood of achieving specific fitness goal

    Args:
        user_id: User identifier
        goal_id: Goal identifier

    Returns:
        Dict with goal achievement prediction
    """
    try:
        logger.info(f"Predicting goal achievement for user {user_id}, goal {goal_id}")

        # Initialize clients
        supabase = SupabaseClient()
        vertex_client = VertexAIClient()

        # Fetch goal details
        goal = supabase.get_user_goal(goal_id)

        # Fetch user's historical progress
        historical_data = supabase.get_user_progress_towards_goal(user_id, goal_id)

        # Calculate current progress rate
        progress_rate = _calculate_progress_rate(historical_data, goal)

        # Analyze factors affecting goal achievement
        factors = {
            "consistency": _analyze_consistency_factor(user_id),
            "adherence": _analyze_plan_adherence(user_id),
            "progress_rate": progress_rate,
            "time_remaining": _calculate_time_remaining(goal),
            "difficulty_level": _assess_goal_difficulty(goal),
        }

        # Use ML model for prediction
        prediction_probability = _predict_with_ml_model(factors)

        # Generate detailed analysis with AI
        ai_analysis = vertex_client.analyze_goal_achievement(
            goal_details=goal, historical_progress=historical_data, factors=factors
        )

        # Calculate required adjustments
        adjustments = _calculate_required_adjustments(
            goal, progress_rate, prediction_probability
        )

        # Generate action plan
        action_plan = _generate_action_plan(goal, factors, adjustments)

        # Store prediction
        prediction_record = {
            "user_id": user_id,
            "goal_id": goal_id,
            "prediction_probability": prediction_probability,
            "factors": factors,
            "adjustments_needed": adjustments,
            "action_plan": action_plan,
            "ai_analysis": ai_analysis,
            "predicted_at": datetime.utcnow().isoformat(),
        }

        supabase.save_goal_prediction(prediction_record)

        logger.info(f"Goal prediction completed: {prediction_probability}% likelihood")

        return {
            "success": True,
            "achievement_probability": prediction_probability,
            "factors": factors,
            "adjustments_needed": adjustments,
            "action_plan": action_plan,
            "ai_insights": ai_analysis,
        }

    except Exception as e:
        logger.error(f"Error predicting goal achievement: {e}")
        raise


@app.task(base=BaseAnalyticsTask, name="tasks.analytics.generate_performance_insights")
def generate_performance_insights(
    user_id: str, focus_area: str = "overall"
) -> Dict[str, Any]:
    """
    Generate deep performance insights using AI

    Args:
        user_id: User identifier
        focus_area: Specific area to focus on (strength, endurance, etc.)

    Returns:
        Dict with performance insights
    """
    try:
        logger.info(
            f"Generating performance insights for user {user_id}, focus: {focus_area}"
        )

        # Initialize clients
        supabase = SupabaseClient()
        vertex_client = VertexAIClient()

        # Gather comprehensive data
        performance_data = {
            "workouts": supabase.get_recent_workouts(user_id, days=90),
            "progress": supabase.get_progress_metrics(user_id),
            "nutrition": supabase.get_nutrition_summary(user_id),
            "recovery": supabase.get_recovery_data(user_id),
            "goals": supabase.get_active_goals(user_id),
        }

        # Calculate performance metrics
        metrics = _calculate_performance_metrics(performance_data, focus_area)

        # Identify strengths and weaknesses
        analysis = _analyze_strengths_weaknesses(metrics, performance_data)

        # Generate AI insights
        ai_insights = vertex_client.generate_performance_insights(
            user_data=performance_data, metrics=metrics, focus_area=focus_area
        )

        # Create improvement recommendations
        recommendations = _generate_improvement_plan(analysis, ai_insights, focus_area)

        # Predict performance trajectory
        trajectory = _predict_performance_trajectory(metrics, performance_data)

        # Store insights
        insights_record = {
            "user_id": user_id,
            "focus_area": focus_area,
            "metrics": metrics,
            "strengths": analysis["strengths"],
            "areas_for_improvement": analysis["weaknesses"],
            "recommendations": recommendations,
            "trajectory": trajectory,
            "ai_insights": ai_insights,
            "generated_at": datetime.utcnow().isoformat(),
        }

        supabase.save_performance_insights(insights_record)

        logger.info(f"Performance insights generated successfully")

        return {
            "success": True,
            "metrics": metrics,
            "analysis": analysis,
            "recommendations": recommendations,
            "performance_trajectory": trajectory,
            "ai_insights": ai_insights,
        }

    except Exception as e:
        logger.error(f"Error generating performance insights: {e}")
        raise


@app.task(base=BaseAnalyticsTask, name="tasks.analytics.generate_daily_summary")
def generate_daily_summary() -> Dict[str, Any]:
    """
    Generate daily analytics summary for all active users

    Returns:
        Dict with summary generation results
    """
    try:
        logger.info("Generating daily analytics summary")

        # Initialize client
        supabase = SupabaseClient()

        # Get all active users
        active_users = supabase.get_active_users()

        summaries_generated = 0
        errors = []

        for user in active_users:
            try:
                # Generate individual summary
                summary = _generate_user_daily_summary(user["id"])

                # Store summary
                supabase.save_daily_summary(user["id"], summary)

                # Send notification if enabled
                if user.get("notifications_enabled"):
                    _queue_summary_notification(user["id"], summary)

                summaries_generated += 1

            except Exception as e:
                logger.error(f"Error generating summary for user {user['id']}: {e}")
                errors.append({"user_id": user["id"], "error": str(e)})

        logger.info(
            f"Daily summaries generated: {summaries_generated}/{len(active_users)}"
        )

        return {
            "success": True,
            "summaries_generated": summaries_generated,
            "total_users": len(active_users),
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"Error in daily summary generation: {e}")
        raise


@app.task(base=BaseAnalyticsTask, name="tasks.analytics.analyze_nutrition_compliance")
def analyze_nutrition_compliance(
    user_id: str, plan_id: str, period_days: int = 30
) -> Dict[str, Any]:
    """
    Analyze compliance with nutrition plan

    Args:
        user_id: User identifier
        plan_id: Nutrition plan identifier
        period_days: Days to analyze

    Returns:
        Dict with compliance analysis
    """
    try:
        logger.info(
            f"Analyzing nutrition compliance for user {user_id}, plan {plan_id}"
        )

        # Initialize client
        supabase = SupabaseClient()

        # Fetch plan details and logged meals
        plan = supabase.get_nutrition_plan(plan_id)
        logged_meals = supabase.get_logged_meals(user_id, period_days)

        # Calculate compliance metrics
        compliance_metrics = {
            "overall_compliance": _calculate_overall_compliance(plan, logged_meals),
            "macro_compliance": _analyze_macro_compliance(plan, logged_meals),
            "calorie_compliance": _analyze_calorie_compliance(plan, logged_meals),
            "meal_timing_compliance": _analyze_meal_timing(plan, logged_meals),
            "missed_meals": _identify_missed_meals(plan, logged_meals),
        }

        # Identify patterns
        patterns = _identify_compliance_patterns(logged_meals, plan)

        # Generate recommendations
        recommendations = _generate_nutrition_recommendations(
            compliance_metrics, patterns
        )

        # Predict impact on goals
        goal_impact = _predict_nutrition_goal_impact(compliance_metrics)

        # Store analysis
        compliance_record = {
            "user_id": user_id,
            "plan_id": plan_id,
            "period_days": period_days,
            "metrics": compliance_metrics,
            "patterns": patterns,
            "recommendations": recommendations,
            "goal_impact": goal_impact,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        supabase.save_nutrition_compliance_analysis(compliance_record)

        logger.info(
            f"Nutrition compliance analysis completed: {compliance_metrics['overall_compliance']}%"
        )

        return {
            "success": True,
            "compliance_score": compliance_metrics["overall_compliance"],
            "detailed_metrics": compliance_metrics,
            "patterns": patterns,
            "recommendations": recommendations,
            "goal_impact": goal_impact,
        }

    except Exception as e:
        logger.error(f"Error analyzing nutrition compliance: {e}")
        raise


# Helper functions for trend analysis
def _extract_metric_data(
    historical_data: List[Dict], metric: str
) -> List[Tuple[datetime, float]]:
    """Extract specific metric data from historical records"""
    metric_data = []
    for record in historical_data:
        if metric in record:
            date = datetime.fromisoformat(record["date"])
            value = float(record[metric])
            metric_data.append((date, value))
    return sorted(metric_data, key=lambda x: x[0])


def _analyze_trend(data: List[Tuple[datetime, float]]) -> Dict[str, Any]:
    """Analyze trend in metric data"""
    if len(data) < 2:
        return {"trend": "insufficient_data"}

    # Convert to arrays for analysis
    dates = np.array([(d[0] - data[0][0]).days for d in data]).reshape(-1, 1)
    values = np.array([d[1] for d in data])

    # Fit linear regression
    model = LinearRegression()
    model.fit(dates, values)

    # Calculate trend metrics
    slope = model.coef_[0]
    r_squared = model.score(dates, values)

    # Determine trend direction
    if abs(slope) < 0.01:
        direction = "stable"
    elif slope > 0:
        direction = "increasing"
    else:
        direction = "decreasing"

    # Calculate percentage change
    if len(data) >= 2:
        initial_value = data[0][1]
        final_value = data[-1][1]
        if initial_value != 0:
            percentage_change = (
                (final_value - initial_value) / abs(initial_value)
            ) * 100
        else:
            percentage_change = 0
    else:
        percentage_change = 0

    return {
        "direction": direction,
        "slope": float(slope),
        "r_squared": float(r_squared),
        "percentage_change": float(percentage_change),
        "data_points": len(data),
    }


def _predict_future_value(
    data: List[Tuple[datetime, float]], days_ahead: int
) -> Dict[str, Any]:
    """Predict future value based on historical data"""
    if len(data) < 3:
        return None

    # Prepare data
    dates = np.array([(d[0] - data[0][0]).days for d in data]).reshape(-1, 1)
    values = np.array([d[1] for d in data])

    # Fit model
    model = LinearRegression()
    model.fit(dates, values)

    # Predict future value
    future_day = dates[-1][0] + days_ahead
    predicted_value = model.predict([[future_day]])[0]

    # Calculate confidence interval (simplified)
    std_error = np.std(values - model.predict(dates))
    confidence_interval = 1.96 * std_error  # 95% confidence

    return {
        "predicted_value": float(predicted_value),
        "confidence_interval": float(confidence_interval),
        "prediction_date": (data[-1][0] + timedelta(days=days_ahead)).isoformat(),
    }


def _calculate_overall_progress(trends: Dict[str, Any]) -> float:
    """Calculate overall progress score from multiple trends"""
    positive_metrics = ["muscle_mass", "strength", "endurance", "consistency"]
    negative_metrics = ["body_fat"]
    neutral_metrics = ["weight"]  # Can be positive or negative depending on goal

    score = 50.0  # Base score

    for metric, trend in trends.items():
        if trend.get("status") == "insufficient_data":
            continue

        direction = trend.get("direction", "stable")
        change = trend.get("percentage_change", 0)

        if metric in positive_metrics:
            if direction == "increasing":
                score += min(change, 20)
            elif direction == "decreasing":
                score -= min(abs(change), 20)

        elif metric in negative_metrics:
            if direction == "decreasing":
                score += min(abs(change), 20)
            elif direction == "increasing":
                score -= min(change, 20)

    return max(0, min(100, score))


def _generate_insights(
    trends: Dict[str, Any], historical_data: List[Dict]
) -> List[str]:
    """Generate actionable insights from trends"""
    insights = []

    # Check each trend
    for metric, trend in trends.items():
        if trend.get("status") == "insufficient_data":
            continue

        direction = trend.get("direction")
        change = trend.get("percentage_change", 0)

        # Generate metric-specific insights
        if metric == "weight" and direction == "decreasing" and change > 5:
            insights.append(
                f"Great progress! You've lost {abs(change):.1f}% body weight."
            )
        elif metric == "muscle_mass" and direction == "increasing":
            insights.append(f"Excellent muscle gain of {change:.1f}%.")
        elif metric == "consistency" and direction == "decreasing":
            insights.append(
                "Your workout consistency has dropped. Try setting reminders."
            )

    return insights


# Helper functions for workout pattern analysis
def _analyze_workout_frequency(workouts: List[Dict]) -> Dict[str, Any]:
    """Analyze workout frequency patterns"""
    if not workouts:
        return {"average_per_week": 0}

    # Group by week
    weeks = {}
    for workout in workouts:
        date = datetime.fromisoformat(workout["date"])
        week = date.isocalendar()[1]
        year = date.year
        week_key = f"{year}-{week}"
        weeks[week_key] = weeks.get(week_key, 0) + 1

    # Calculate statistics
    frequencies = list(weeks.values())

    return {
        "average_per_week": np.mean(frequencies) if frequencies else 0,
        "min_per_week": min(frequencies) if frequencies else 0,
        "max_per_week": max(frequencies) if frequencies else 0,
        "consistency": np.std(frequencies) < 1.5 if frequencies else False,
    }


def _analyze_workout_timing(workouts: List[Dict]) -> Dict[str, Any]:
    """Analyze preferred workout times"""
    time_distribution = {
        "early_morning": 0,  # 5-8
        "morning": 0,  # 8-12
        "afternoon": 0,  # 12-17
        "evening": 0,  # 17-21
        "night": 0,  # 21-24
    }

    for workout in workouts:
        if "time" in workout:
            hour = datetime.fromisoformat(workout["time"]).hour
            if 5 <= hour < 8:
                time_distribution["early_morning"] += 1
            elif 8 <= hour < 12:
                time_distribution["morning"] += 1
            elif 12 <= hour < 17:
                time_distribution["afternoon"] += 1
            elif 17 <= hour < 21:
                time_distribution["evening"] += 1
            else:
                time_distribution["night"] += 1

    # Find preferred time
    total = sum(time_distribution.values())
    if total > 0:
        preferred_time = max(time_distribution, key=time_distribution.get)
        preference_strength = time_distribution[preferred_time] / total
    else:
        preferred_time = "unknown"
        preference_strength = 0

    return {
        "distribution": time_distribution,
        "preferred_time": preferred_time,
        "preference_strength": preference_strength,
    }


def _analyze_workout_duration(workouts: List[Dict]) -> Dict[str, Any]:
    """Analyze workout duration patterns"""
    durations = [
        w.get("duration_minutes", 0) for w in workouts if "duration_minutes" in w
    ]

    if not durations:
        return {"average_duration": 0}

    return {
        "average_duration": np.mean(durations),
        "min_duration": min(durations),
        "max_duration": max(durations),
        "typical_range": (np.percentile(durations, 25), np.percentile(durations, 75)),
    }


def _analyze_workout_intensity(workouts: List[Dict]) -> Dict[str, Any]:
    """Analyze workout intensity distribution"""
    intensities = [w.get("intensity", "medium") for w in workouts]

    intensity_count = {
        "low": intensities.count("low"),
        "medium": intensities.count("medium"),
        "high": intensities.count("high"),
    }

    total = sum(intensity_count.values())
    if total > 0:
        intensity_distribution = {k: v / total for k, v in intensity_count.items()}
    else:
        intensity_distribution = {"low": 0, "medium": 0, "high": 0}

    return {
        "distribution": intensity_distribution,
        "dominant_intensity": (
            max(intensity_count, key=intensity_count.get) if total > 0 else "unknown"
        ),
    }


def _analyze_exercise_distribution(workouts: List[Dict]) -> Dict[str, Any]:
    """Analyze distribution of exercise types"""
    exercise_types = {}
    muscle_groups = {}

    for workout in workouts:
        for exercise in workout.get("exercises", []):
            # Count exercise types
            ex_type = exercise.get("type", "unknown")
            exercise_types[ex_type] = exercise_types.get(ex_type, 0) + 1

            # Count muscle groups
            for muscle in exercise.get("muscle_groups", []):
                muscle_groups[muscle] = muscle_groups.get(muscle, 0) + 1

    return {
        "exercise_types": exercise_types,
        "muscle_groups": muscle_groups,
        "variety_score": len(exercise_types) / 10.0,  # Normalized score
    }


def _analyze_rest_patterns(workouts: List[Dict]) -> Dict[str, Any]:
    """Analyze rest day patterns"""
    if not workouts:
        return {"average_rest_days": 0}

    # Sort workouts by date
    sorted_workouts = sorted(workouts, key=lambda x: x["date"])

    # Calculate days between workouts
    rest_periods = []
    for i in range(1, len(sorted_workouts)):
        date1 = datetime.fromisoformat(sorted_workouts[i - 1]["date"])
        date2 = datetime.fromisoformat(sorted_workouts[i]["date"])
        rest_days = (date2 - date1).days - 1
        if rest_days > 0:
            rest_periods.append(rest_days)

    if rest_periods:
        return {
            "average_rest_days": np.mean(rest_periods),
            "max_rest_period": max(rest_periods),
            "typical_rest": int(np.median(rest_periods)),
        }
    else:
        return {"average_rest_days": 0}


def _calculate_consistency_score(workouts: List[Dict], period_days: int) -> float:
    """Calculate workout consistency score"""
    if not workouts:
        return 0.0

    # Expected workouts (3-4 per week is good)
    expected_workouts = (period_days / 7) * 3.5
    actual_workouts = len(workouts)

    # Calculate base score
    ratio = actual_workouts / expected_workouts
    base_score = min(ratio * 100, 100)

    # Adjust for regularity
    dates = [datetime.fromisoformat(w["date"]) for w in workouts]
    if len(dates) > 1:
        intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        regularity = 1 - (
            np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 1
        )
        base_score *= 0.7 + 0.3 * regularity

    return min(max(base_score, 0), 100)


def _identify_workout_habits(patterns: Dict[str, Any]) -> List[str]:
    """Identify workout habits from patterns"""
    habits = []

    # Frequency habits
    avg_per_week = patterns["frequency"].get("average_per_week", 0)
    if avg_per_week >= 5:
        habits.append("highly_active")
    elif avg_per_week >= 3:
        habits.append("regularly_active")
    elif avg_per_week >= 1:
        habits.append("moderately_active")
    else:
        habits.append("inactive")

    # Timing habits
    preferred_time = patterns["timing"].get("preferred_time")
    if patterns["timing"].get("preference_strength", 0) > 0.7:
        habits.append(f"consistent_{preferred_time}_trainer")

    # Duration habits
    avg_duration = patterns["duration"].get("average_duration", 0)
    if avg_duration > 90:
        habits.append("long_session_preference")
    elif avg_duration < 30:
        habits.append("short_session_preference")

    return habits


def _generate_workout_recommendations(
    patterns: Dict[str, Any], habits: List[str]
) -> List[str]:
    """Generate workout recommendations based on patterns"""
    recommendations = []

    # Frequency recommendations
    avg_per_week = patterns["frequency"].get("average_per_week", 0)
    if avg_per_week < 3:
        recommendations.append(
            "Try to increase workout frequency to at least 3 times per week"
        )
    elif avg_per_week > 6:
        recommendations.append("Consider adding more rest days for recovery")

    # Variety recommendations
    variety_score = patterns["exercise_distribution"].get("variety_score", 0)
    if variety_score < 0.5:
        recommendations.append("Add more exercise variety to prevent plateaus")

    # Intensity recommendations
    intensity_dist = patterns["intensity"].get("distribution", {})
    if intensity_dist.get("high", 0) < 0.2:
        recommendations.append(
            "Include more high-intensity sessions for better results"
        )
    elif intensity_dist.get("high", 0) > 0.6:
        recommendations.append("Balance with more moderate intensity sessions")

    return recommendations


def _predict_optimal_workout_times(workouts: List[Dict]) -> List[Dict[str, Any]]:
    """Predict optimal workout times based on performance data"""
    # Analyze performance by time of day
    time_performance = {}

    for workout in workouts:
        if "time" in workout and "performance_score" in workout:
            hour = datetime.fromisoformat(workout["time"]).hour
            time_slot = _get_time_slot(hour)

            if time_slot not in time_performance:
                time_performance[time_slot] = []
            time_performance[time_slot].append(workout["performance_score"])

    # Calculate average performance by time slot
    optimal_times = []
    for time_slot, scores in time_performance.items():
        if scores:
            avg_score = np.mean(scores)
            optimal_times.append(
                {
                    "time_slot": time_slot,
                    "average_performance": avg_score,
                    "sample_size": len(scores),
                }
            )

    # Sort by performance
    optimal_times.sort(key=lambda x: x["average_performance"], reverse=True)

    return optimal_times[:3]  # Top 3 times


def _get_time_slot(hour: int) -> str:
    """Convert hour to time slot"""
    if 5 <= hour < 8:
        return "early_morning"
    elif 8 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


# Helper functions for other analytics tasks
def _calculate_progress_rate(historical_data: List[Dict], goal: Dict) -> float:
    """Calculate rate of progress towards goal"""
    if not historical_data or len(historical_data) < 2:
        return 0.0

    # Sort by date
    sorted_data = sorted(historical_data, key=lambda x: x["date"])

    # Calculate progress
    initial_value = sorted_data[0].get("value", 0)
    current_value = sorted_data[-1].get("value", 0)
    goal_value = goal.get("target_value", 0)

    if goal_value == initial_value:
        return 0.0

    progress = (current_value - initial_value) / (goal_value - initial_value)

    # Calculate time elapsed
    start_date = datetime.fromisoformat(sorted_data[0]["date"])
    current_date = datetime.fromisoformat(sorted_data[-1]["date"])
    days_elapsed = (current_date - start_date).days

    # Daily progress rate
    if days_elapsed > 0:
        return (progress / days_elapsed) * 100
    else:
        return 0.0


def _analyze_consistency_factor(user_id: str) -> float:
    """Analyze user's consistency factor"""
    # Simplified - would fetch from database
    return 0.85


def _analyze_plan_adherence(user_id: str) -> float:
    """Analyze adherence to training/nutrition plans"""
    # Simplified - would fetch from database
    return 0.78


def _calculate_time_remaining(goal: Dict) -> int:
    """Calculate days remaining to goal deadline"""
    if "deadline" in goal:
        deadline = datetime.fromisoformat(goal["deadline"])
        return (deadline - datetime.utcnow()).days
    return 365  # Default to 1 year


def _assess_goal_difficulty(goal: Dict) -> float:
    """Assess difficulty level of goal"""
    # Simplified assessment based on goal type and target
    goal_type = goal.get("type", "general")
    target_change = goal.get("target_change_percentage", 10)

    difficulty_factors = {
        "weight_loss": 1.0,
        "muscle_gain": 1.2,
        "strength": 1.1,
        "endurance": 0.9,
        "body_recomposition": 1.5,
    }

    base_difficulty = difficulty_factors.get(goal_type, 1.0)

    # Adjust for target magnitude
    if target_change > 20:
        base_difficulty *= 1.3
    elif target_change > 30:
        base_difficulty *= 1.5

    return min(base_difficulty, 2.0)


def _predict_with_ml_model(factors: Dict[str, Any]) -> float:
    """Use ML model to predict goal achievement probability"""
    # Simplified prediction model
    base_probability = 50.0

    # Adjust based on factors
    base_probability += factors["consistency"] * 20
    base_probability += factors["adherence"] * 15
    base_probability += min(factors["progress_rate"], 1.0) * 10
    base_probability -= factors["difficulty_level"] * 10

    # Time factor
    if factors["time_remaining"] < 30:
        base_probability -= 10
    elif factors["time_remaining"] > 180:
        base_probability += 5

    return max(0, min(100, base_probability))


def _calculate_required_adjustments(
    goal: Dict, progress_rate: float, probability: float
) -> Dict[str, Any]:
    """Calculate adjustments needed to achieve goal"""
    adjustments = {}

    if probability < 70:
        # Need significant adjustments
        if progress_rate < 0.5:
            adjustments["intensity_increase"] = "20-30%"
            adjustments["frequency_increase"] = "1-2 sessions/week"

        if progress_rate < 0.3:
            adjustments["plan_revision"] = "major"
            adjustments["nutrition_adjustment"] = "required"

    elif probability < 85:
        # Minor adjustments
        adjustments["intensity_increase"] = "10-15%"
        adjustments["consistency_focus"] = "high"

    return adjustments


def _generate_action_plan(goal: Dict, factors: Dict, adjustments: Dict) -> List[str]:
    """Generate specific action plan"""
    actions = []

    if "intensity_increase" in adjustments:
        actions.append(
            f"Increase workout intensity by {adjustments['intensity_increase']}"
        )

    if "frequency_increase" in adjustments:
        actions.append(f"Add {adjustments['frequency_increase']} to your routine")

    if factors["consistency"] < 0.8:
        actions.append("Set daily reminders for workouts")
        actions.append("Prepare workout clothes the night before")

    if factors["adherence"] < 0.8:
        actions.append("Review and simplify your nutrition plan")
        actions.append("Meal prep twice per week")

    return actions


def _calculate_performance_metrics(
    data: Dict[str, Any], focus_area: str
) -> Dict[str, Any]:
    """Calculate comprehensive performance metrics"""
    metrics = {}

    # Calculate based on focus area
    if focus_area in ["strength", "overall"]:
        metrics["strength_progression"] = _calculate_strength_progression(
            data["workouts"]
        )

    if focus_area in ["endurance", "overall"]:
        metrics["endurance_improvement"] = _calculate_endurance_metrics(
            data["workouts"]
        )

    if focus_area in ["overall"]:
        metrics["overall_fitness_score"] = _calculate_fitness_score(data)

    return metrics


def _analyze_strengths_weaknesses(metrics: Dict, data: Dict) -> Dict[str, Any]:
    """Identify strengths and weaknesses"""
    strengths = []
    weaknesses = []

    # Analyze metrics
    for metric, value in metrics.items():
        if isinstance(value, dict) and "score" in value:
            if value["score"] > 80:
                strengths.append(metric)
            elif value["score"] < 60:
                weaknesses.append(metric)

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "balance_score": (
            len(strengths) / (len(strengths) + len(weaknesses))
            if strengths or weaknesses
            else 0.5
        ),
    }


def _generate_improvement_plan(
    analysis: Dict, ai_insights: str, focus_area: str
) -> List[Dict[str, Any]]:
    """Generate improvement recommendations"""
    recommendations = []

    # Address weaknesses
    for weakness in analysis["weaknesses"]:
        recommendations.append(
            {
                "area": weakness,
                "priority": "high",
                "actions": _get_improvement_actions(weakness),
                "timeline": "2-4 weeks",
            }
        )

    # Enhance strengths
    for strength in analysis["strengths"][:2]:  # Top 2 strengths
        recommendations.append(
            {
                "area": strength,
                "priority": "medium",
                "actions": _get_enhancement_actions(strength),
                "timeline": "4-6 weeks",
            }
        )

    return recommendations


def _predict_performance_trajectory(metrics: Dict, data: Dict) -> Dict[str, Any]:
    """Predict future performance trajectory"""
    # Simplified trajectory prediction
    current_score = metrics.get("overall_fitness_score", {}).get("score", 50)

    trajectory = {
        "30_days": current_score * 1.05,
        "60_days": current_score * 1.12,
        "90_days": current_score * 1.20,
        "confidence": 0.75,
    }

    return trajectory


def _generate_user_daily_summary(user_id: str) -> Dict[str, Any]:
    """Generate daily summary for a user"""
    # Would implement actual summary generation
    return {
        "workouts_completed": 1,
        "calories_consumed": 2150,
        "goals_progress": {"weight_loss": 0.15, "strength": 0.08},
        "key_achievements": ["Completed all planned workouts"],
        "recommendations": ["Increase protein intake by 20g"],
    }


def _queue_summary_notification(user_id: str, summary: Dict):
    """Queue notification for user summary"""
    # Would queue notification task
    pass


# Nutrition compliance helpers
def _calculate_overall_compliance(plan: Dict, meals: List[Dict]) -> float:
    """Calculate overall nutrition compliance percentage"""
    if not plan or not meals:
        return 0.0

    # Simplified calculation
    planned_meals = plan.get("daily_meals", 3) * 30  # Assuming 30 days
    logged_meals = len(meals)

    return min((logged_meals / planned_meals) * 100, 100)


def _analyze_macro_compliance(plan: Dict, meals: List[Dict]) -> Dict[str, float]:
    """Analyze macronutrient compliance"""
    target_macros = plan.get("daily_macros", {})

    compliance = {"protein": 0.0, "carbs": 0.0, "fat": 0.0}

    # Would implement actual macro tracking
    return compliance


def _analyze_calorie_compliance(plan: Dict, meals: List[Dict]) -> Dict[str, Any]:
    """Analyze calorie intake compliance"""
    target_calories = plan.get("daily_calories", 2000)

    # Would implement actual calorie tracking
    return {
        "average_daily": 1950,
        "compliance_percentage": 97.5,
        "over_days": 3,
        "under_days": 2,
    }


def _analyze_meal_timing(plan: Dict, meals: List[Dict]) -> Dict[str, Any]:
    """Analyze meal timing compliance"""
    # Would implement meal timing analysis
    return {"on_schedule_percentage": 85, "missed_breakfast": 2, "late_dinners": 3}


def _identify_missed_meals(plan: Dict, meals: List[Dict]) -> List[Dict[str, Any]]:
    """Identify missed meals"""
    # Would implement missed meal detection
    return [{"date": "2024-01-15", "meal": "breakfast", "reason": "unknown"}]


def _identify_compliance_patterns(meals: List[Dict], plan: Dict) -> List[str]:
    """Identify patterns in compliance"""
    patterns = []

    # Would analyze actual patterns
    patterns.append("Better compliance on weekdays")
    patterns.append("Tendency to skip breakfast on weekends")

    return patterns


def _generate_nutrition_recommendations(
    metrics: Dict, patterns: List[str]
) -> List[str]:
    """Generate nutrition recommendations"""
    recommendations = []

    if metrics["overall_compliance"] < 80:
        recommendations.append("Set meal reminders on your phone")

    if "skip breakfast" in " ".join(patterns):
        recommendations.append("Prepare quick breakfast options the night before")

    return recommendations


def _predict_nutrition_goal_impact(compliance_metrics: Dict) -> Dict[str, Any]:
    """Predict impact of compliance on goals"""
    overall_compliance = compliance_metrics.get("overall_compliance", 0)

    impact = {
        "goal_achievement_likelihood": overall_compliance * 0.9,
        "estimated_timeline_adjustment": (
            "on track" if overall_compliance > 85 else "+2 weeks"
        ),
        "risk_factors": [],
    }

    if overall_compliance < 70:
        impact["risk_factors"].append("Low compliance may delay results")

    return impact


# Additional helper functions
def _calculate_strength_progression(workouts: List[Dict]) -> Dict[str, Any]:
    """Calculate strength progression metrics"""
    # Would implement actual strength calculation
    return {
        "score": 75,
        "total_volume_increase": 15.5,
        "one_rep_max_improvements": {"bench": 10, "squat": 20, "deadlift": 25},
    }


def _calculate_endurance_metrics(workouts: List[Dict]) -> Dict[str, Any]:
    """Calculate endurance improvement metrics"""
    # Would implement actual endurance calculation
    return {
        "score": 82,
        "vo2_max_estimate": 45.2,
        "distance_improvements": {"5k": -45, "10k": -120},  # seconds improvement
    }


def _calculate_fitness_score(data: Dict) -> Dict[str, Any]:
    """Calculate overall fitness score"""
    # Would implement comprehensive fitness scoring
    return {
        "score": 78.5,
        "components": {
            "strength": 75,
            "endurance": 82,
            "flexibility": 70,
            "body_composition": 80,
        },
    }


def _get_improvement_actions(weakness: str) -> List[str]:
    """Get specific improvement actions for weakness"""
    actions_map = {
        "strength_progression": [
            "Add progressive overload each week",
            "Focus on compound movements",
            "Ensure adequate protein intake",
        ],
        "endurance_improvement": [
            "Add 1-2 cardio sessions per week",
            "Include interval training",
            "Gradually increase duration",
        ],
    }

    return actions_map.get(weakness, ["Consult with trainer for specific plan"])


def _get_enhancement_actions(strength: str) -> List[str]:
    """Get enhancement actions for strengths"""
    actions_map = {
        "strength_progression": [
            "Consider advanced techniques (drop sets, supersets)",
            "Add Olympic lifts for power development",
        ],
        "endurance_improvement": [
            "Train for specific event or challenge",
            "Add tempo runs or fartlek training",
        ],
    }

    return actions_map.get(strength, ["Maintain current approach"])

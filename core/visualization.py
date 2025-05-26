"""
Visualization module for generating dynamic charts and reports.

This module provides utilities for creating visual content like progress charts,
nutritional infographics, and PDF reports for the NGX Agents fitness system.
"""

import asyncio
import io
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image, ImageDraw, ImageFont

# Use non-interactive backend to avoid GUI dependencies
matplotlib.use("Agg")

# Set style for professional-looking charts
plt.style.use("seaborn-v0_8-darkgrid")
sns.set_palette("husl")


class ProgressChartGenerator:
    """Generates dynamic progress charts for fitness metrics."""

    def __init__(self):
        """Initialize the chart generator with default settings."""
        self.default_colors = {
            "weight": "#FF6B6B",
            "muscle_mass": "#4ECDC4",
            "body_fat": "#FFE66D",
            "performance": "#95E1D3",
            "calories": "#F38181",
            "protein": "#AA96DA",
            "carbs": "#FCBAD3",
            "fat": "#FFFFD2",
        }

    async def generate_weight_progress_chart(
        self, data: List[Dict[str, Any]], user_info: Dict[str, Any]
    ) -> bytes:
        """
        Generate a weight progress chart.

        Args:
            data: List of weight measurements with timestamps
            user_info: User information including goals

        Returns:
            PNG image as bytes
        """
        # Convert data to DataFrame for easier manipulation
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(12, 10), gridspec_kw={"height_ratios": [3, 1]}
        )

        # Main weight progress plot
        ax1.plot(
            df["date"],
            df["weight"],
            color=self.default_colors["weight"],
            linewidth=3,
            marker="o",
            markersize=8,
        )

        # Add goal line if exists
        if "goal_weight" in user_info:
            ax1.axhline(
                y=user_info["goal_weight"],
                color="green",
                linestyle="--",
                alpha=0.7,
                label=f"Goal: {user_info['goal_weight']} kg",
            )

        # Calculate and plot trend line
        z = np.polyfit(df.index, df["weight"], 1)
        p = np.poly1d(z)
        ax1.plot(
            df["date"],
            p(df.index),
            color="blue",
            linestyle=":",
            alpha=0.7,
            label="Trend",
        )

        # Formatting
        ax1.set_title(
            f"Weight Progress for {user_info.get('name', 'User')}",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )
        ax1.set_ylabel("Weight (kg)", fontsize=12)
        ax1.legend(loc="best")
        ax1.grid(True, alpha=0.3)

        # Weekly change subplot
        df["weekly_change"] = df["weight"].diff()
        weekly_colors = [
            "green" if x < 0 else "red" for x in df["weekly_change"].fillna(0)
        ]
        ax2.bar(df["date"], df["weekly_change"], color=weekly_colors, alpha=0.7)
        ax2.set_ylabel("Weekly Change (kg)", fontsize=12)
        ax2.set_xlabel("Date", fontsize=12)
        ax2.grid(True, alpha=0.3)

        # Rotate x-axis labels
        for ax in [ax1, ax2]:
            ax.tick_params(axis="x", rotation=45)

        plt.tight_layout()

        # Save to bytes
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
        plt.close()

        img_buffer.seek(0)
        return img_buffer.getvalue()

    async def generate_body_composition_chart(
        self, data: List[Dict[str, Any]]
    ) -> bytes:
        """
        Generate a body composition chart showing muscle mass, body fat, etc.

        Args:
            data: List of body composition measurements

        Returns:
            PNG image as bytes
        """
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        fig, ax = plt.subplots(figsize=(12, 8))

        # Plot multiple metrics
        metrics = {
            "muscle_mass": ("Muscle Mass (%)", self.default_colors["muscle_mass"]),
            "body_fat": ("Body Fat (%)", self.default_colors["body_fat"]),
            "water": ("Water (%)", "#74C0FC"),
        }

        for metric, (label, color) in metrics.items():
            if metric in df.columns:
                ax.plot(
                    df["date"],
                    df[metric],
                    color=color,
                    linewidth=2.5,
                    marker="o",
                    markersize=6,
                    label=label,
                )

        # Formatting
        ax.set_title(
            "Body Composition Progress", fontsize=16, fontweight="bold", pad=20
        )
        ax.set_ylabel("Percentage (%)", fontsize=12)
        ax.set_xlabel("Date", fontsize=12)
        ax.legend(loc="best", frameon=True, fancybox=True, shadow=True)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", rotation=45)

        # Add healthy ranges as background
        ax.axhspan(18, 25, alpha=0.1, color="green", label="Healthy Body Fat Range")

        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
        plt.close()

        img_buffer.seek(0)
        return img_buffer.getvalue()

    async def generate_performance_metrics_chart(
        self, data: List[Dict[str, Any]], metric_type: str = "strength"
    ) -> bytes:
        """
        Generate performance metrics charts (strength, endurance, etc.).

        Args:
            data: Performance data
            metric_type: Type of metric ('strength', 'endurance', 'flexibility')

        Returns:
            PNG image as bytes
        """
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()

        # Different visualizations based on metric type
        if metric_type == "strength":
            exercises = ["bench_press", "squat", "deadlift", "overhead_press"]
            for idx, exercise in enumerate(exercises):
                if exercise in df.columns and idx < len(axes):
                    ax = axes[idx]
                    ax.plot(
                        df["date"],
                        df[exercise],
                        color=list(self.default_colors.values())[idx],
                        linewidth=2.5,
                        marker="o",
                    )
                    ax.set_title(exercise.replace("_", " ").title(), fontsize=12)
                    ax.set_ylabel("Weight (kg)", fontsize=10)
                    ax.grid(True, alpha=0.3)
                    ax.tick_params(axis="x", rotation=45)

        elif metric_type == "endurance":
            metrics = [
                "running_distance",
                "running_pace",
                "vo2_max",
                "heart_rate_recovery",
            ]
            for idx, metric in enumerate(metrics):
                if metric in df.columns and idx < len(axes):
                    ax = axes[idx]
                    ax.plot(
                        df["date"],
                        df[metric],
                        color=list(self.default_colors.values())[idx],
                        linewidth=2.5,
                        marker="o",
                    )
                    ax.set_title(metric.replace("_", " ").title(), fontsize=12)
                    ax.grid(True, alpha=0.3)
                    ax.tick_params(axis="x", rotation=45)

        plt.suptitle(
            f"{metric_type.title()} Performance Metrics", fontsize=16, fontweight="bold"
        )
        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
        plt.close()

        img_buffer.seek(0)
        return img_buffer.getvalue()

    async def generate_comparison_chart(
        self,
        current_data: Dict[str, float],
        previous_data: Dict[str, float],
        period: str = "month",
    ) -> bytes:
        """
        Generate a comparison chart between two periods.

        Args:
            current_data: Current period metrics
            previous_data: Previous period metrics
            period: Time period for comparison

        Returns:
            PNG image as bytes
        """
        metrics = list(current_data.keys())
        current_values = list(current_data.values())
        previous_values = list(previous_data.values())

        x = np.arange(len(metrics))
        width = 0.35

        fig, ax = plt.subplots(figsize=(12, 8))

        bars1 = ax.bar(
            x - width / 2,
            previous_values,
            width,
            label=f"Previous {period}",
            color="#FF6B6B",
            alpha=0.8,
        )
        bars2 = ax.bar(
            x + width / 2,
            current_values,
            width,
            label=f"Current {period}",
            color="#4ECDC4",
            alpha=0.8,
        )

        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.annotate(
                    f"{height:.1f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                )

        # Calculate and display percentage changes
        for i, (curr, prev) in enumerate(zip(current_values, previous_values)):
            if prev != 0:
                change = ((curr - prev) / prev) * 100
                color = "green" if change > 0 else "red"
                ax.text(
                    i,
                    max(curr, prev) + 2,
                    f"{change:+.1f}%",
                    ha="center",
                    color=color,
                    fontweight="bold",
                )

        ax.set_ylabel("Values", fontsize=12)
        ax.set_title(
            f"Progress Comparison: {period.title()} over {period.title()}",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )
        ax.set_xticks(x)
        ax.set_xticklabels([m.replace("_", " ").title() for m in metrics])
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
        plt.close()

        img_buffer.seek(0)
        return img_buffer.getvalue()


class NutritionInfographicGenerator:
    """Generates nutritional plan infographics."""

    def __init__(self):
        """Initialize the infographic generator."""
        self.colors = {
            "protein": "#E74C3C",
            "carbs": "#3498DB",
            "fat": "#F39C12",
            "fiber": "#27AE60",
            "calories": "#9B59B6",
        }

    async def generate_daily_nutrition_breakdown(
        self, nutrition_data: Dict[str, Any]
    ) -> bytes:
        """
        Generate a daily nutrition breakdown infographic.

        Args:
            nutrition_data: Daily nutritional information

        Returns:
            PNG image as bytes
        """
        fig = plt.figure(figsize=(14, 10))

        # Create grid for subplots
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # 1. Macronutrient pie chart
        ax1 = fig.add_subplot(gs[0, :2])
        macros = ["protein", "carbs", "fat"]
        macro_values = [nutrition_data.get(m, 0) for m in macros]
        colors = [self.colors[m] for m in macros]

        wedges, texts, autotexts = ax1.pie(
            macro_values,
            labels=macros,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            pctdistance=0.85,
        )

        # Beautify the pie chart
        for w in wedges:
            w.set_linewidth(2)
            w.set_edgecolor("white")

        ax1.set_title("Macronutrient Distribution", fontsize=14, fontweight="bold")

        # 2. Calorie gauge
        ax2 = fig.add_subplot(gs[0, 2])
        self._create_gauge_chart(
            ax2,
            nutrition_data.get("calories_consumed", 0),
            nutrition_data.get("calories_target", 2000),
            "Calories",
        )

        # 3. Meal breakdown
        ax3 = fig.add_subplot(gs[1, :])
        meals = nutrition_data.get("meals", {})
        meal_names = list(meals.keys())
        meal_calories = [m.get("calories", 0) for m in meals.values()]

        bars = ax3.bar(
            meal_names, meal_calories, color=self.colors["calories"], alpha=0.7
        )
        ax3.set_title("Calories by Meal", fontsize=14, fontweight="bold")
        ax3.set_ylabel("Calories")

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax3.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{int(height)}",
                ha="center",
                va="bottom",
            )

        # 4. Nutrient goals progress
        ax4 = fig.add_subplot(gs[2, :])
        nutrients = ["protein", "carbs", "fat", "fiber"]
        consumed = [nutrition_data.get(f"{n}_consumed", 0) for n in nutrients]
        targets = [nutrition_data.get(f"{n}_target", 100) for n in nutrients]

        x = np.arange(len(nutrients))
        width = 0.35

        bars1 = ax4.bar(x - width / 2, consumed, width, label="Consumed", alpha=0.8)
        bars2 = ax4.bar(x + width / 2, targets, width, label="Target", alpha=0.5)

        # Color bars based on nutrient
        for i, (bar1, bar2, nutrient) in enumerate(zip(bars1, bars2, nutrients)):
            bar1.set_color(self.colors[nutrient])
            bar2.set_color(self.colors[nutrient])

        ax4.set_ylabel("Grams")
        ax4.set_title("Daily Nutrient Goals", fontsize=14, fontweight="bold")
        ax4.set_xticks(x)
        ax4.set_xticklabels([n.title() for n in nutrients])
        ax4.legend()
        ax4.grid(True, alpha=0.3, axis="y")

        plt.suptitle(
            f"Daily Nutrition Summary - {datetime.now().strftime('%Y-%m-%d')}",
            fontsize=16,
            fontweight="bold",
        )

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
        plt.close()

        img_buffer.seek(0)
        return img_buffer.getvalue()

    def _create_gauge_chart(self, ax, value, target, label):
        """Create a gauge chart for a single metric."""
        # Create arc
        theta = np.linspace(0, np.pi, 1000)
        radius_inner = 0.7
        radius_outer = 1.0

        # Calculate percentage
        percentage = min(value / target * 100, 100) if target > 0 else 0
        fill_angle = np.pi * percentage / 100

        # Draw outer arc
        ax.plot(np.cos(theta), np.sin(theta), "k-", linewidth=2)
        ax.plot(
            radius_inner * np.cos(theta),
            radius_inner * np.sin(theta),
            "k-",
            linewidth=2,
        )

        # Fill based on percentage
        theta_fill = np.linspace(0, fill_angle, 100)
        color = "green" if percentage >= 90 else "orange" if percentage >= 70 else "red"

        ax.fill_between(
            np.cos(theta_fill),
            radius_inner * np.sin(theta_fill),
            radius_outer * np.sin(theta_fill),
            color=color,
            alpha=0.7,
        )

        # Add text
        ax.text(
            0, -0.2, f"{value}/{target}", ha="center", fontsize=12, fontweight="bold"
        )
        ax.text(0, -0.4, label, ha="center", fontsize=10)
        ax.text(
            0, 0.3, f"{percentage:.0f}%", ha="center", fontsize=14, fontweight="bold"
        )

        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-0.5, 1.2)
        ax.axis("off")

    async def generate_meal_plan_infographic(self, meal_plan: Dict[str, Any]) -> bytes:
        """
        Generate a weekly meal plan infographic.

        Args:
            meal_plan: Weekly meal plan data

        Returns:
            PNG image as bytes
        """
        # This would create a more complex infographic with meal images,
        # nutritional info, and preparation times
        # For now, we'll create a simplified version

        days = list(meal_plan.keys())
        fig, axes = plt.subplots(len(days), 1, figsize=(12, 2 * len(days)))

        if len(days) == 1:
            axes = [axes]

        for idx, (day, ax) in enumerate(zip(days, axes)):
            meals = meal_plan[day]
            meal_types = list(meals.keys())
            calories = [m.get("calories", 0) for m in meals.values()]

            bars = ax.barh(
                meal_types, calories, color=self.colors["calories"], alpha=0.7
            )
            ax.set_title(f"{day.title()} Meal Plan", fontsize=12, fontweight="bold")
            ax.set_xlabel("Calories")

            # Add meal names and macros
            for bar, meal_type in zip(bars, meal_types):
                meal = meals[meal_type]
                width = bar.get_width()
                ax.text(
                    width + 10,
                    bar.get_y() + bar.get_height() / 2,
                    f"{meal.get('name', 'Meal')} - P:{meal.get('protein', 0)}g C:{meal.get('carbs', 0)}g F:{meal.get('fat', 0)}g",
                    va="center",
                    fontsize=9,
                )

        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
        plt.close()

        img_buffer.seek(0)
        return img_buffer.getvalue()


class PDFReportGenerator:
    """Generates personalized PDF reports."""

    def __init__(self):
        """Initialize the PDF report generator."""
        self.chart_generator = ProgressChartGenerator()
        self.nutrition_generator = NutritionInfographicGenerator()

    async def generate_progress_report(
        self,
        user_data: Dict[str, Any],
        progress_data: Dict[str, Any],
        period: str = "monthly",
    ) -> bytes:
        """
        Generate a comprehensive progress report PDF.

        Args:
            user_data: User information
            progress_data: Progress metrics and data
            period: Report period

        Returns:
            PDF file as bytes
        """
        # Create a temporary PDF file
        pdf_buffer = io.BytesIO()

        with PdfPages(pdf_buffer) as pdf:
            # Page 1: Cover page
            fig = plt.figure(figsize=(8.5, 11))
            fig.text(
                0.5,
                0.7,
                f"{user_data['name']}'s Progress Report",
                ha="center",
                fontsize=24,
                fontweight="bold",
            )
            fig.text(0.5, 0.6, f"{period.title()} Summary", ha="center", fontsize=18)
            fig.text(
                0.5,
                0.5,
                f"Generated on {datetime.now().strftime('%B %d, %Y')}",
                ha="center",
                fontsize=14,
            )

            # Add logo or branding here if available
            plt.axis("off")
            pdf.savefig(fig, bbox_inches="tight")
            plt.close()

            # Page 2: Executive Summary
            fig = plt.figure(figsize=(8.5, 11))
            ax = fig.add_subplot(111)
            ax.axis("off")

            summary_text = self._generate_summary_text(user_data, progress_data)
            ax.text(0.1, 0.9, "Executive Summary", fontsize=18, fontweight="bold")
            ax.text(
                0.1,
                0.8,
                summary_text,
                fontsize=11,
                wrap=True,
                verticalalignment="top",
                horizontalalignment="left",
            )

            pdf.savefig(fig, bbox_inches="tight")
            plt.close()

            # Page 3: Weight Progress
            if "weight_data" in progress_data:
                weight_chart = (
                    await self.chart_generator.generate_weight_progress_chart(
                        progress_data["weight_data"], user_data
                    )
                )
                fig = plt.figure(figsize=(8.5, 11))
                img = Image.open(io.BytesIO(weight_chart))
                plt.imshow(img)
                plt.axis("off")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close()

            # Page 4: Body Composition
            if "body_composition_data" in progress_data:
                comp_chart = await self.chart_generator.generate_body_composition_chart(
                    progress_data["body_composition_data"]
                )
                fig = plt.figure(figsize=(8.5, 11))
                img = Image.open(io.BytesIO(comp_chart))
                plt.imshow(img)
                plt.axis("off")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close()

            # Page 5: Performance Metrics
            if "performance_data" in progress_data:
                perf_chart = (
                    await self.chart_generator.generate_performance_metrics_chart(
                        progress_data["performance_data"],
                        progress_data.get("performance_type", "strength"),
                    )
                )
                fig = plt.figure(figsize=(8.5, 11))
                img = Image.open(io.BytesIO(perf_chart))
                plt.imshow(img)
                plt.axis("off")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close()

            # Page 6: Nutrition Summary
            if "nutrition_data" in progress_data:
                nutrition_chart = (
                    await self.nutrition_generator.generate_daily_nutrition_breakdown(
                        progress_data["nutrition_data"]
                    )
                )
                fig = plt.figure(figsize=(8.5, 11))
                img = Image.open(io.BytesIO(nutrition_chart))
                plt.imshow(img)
                plt.axis("off")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close()

            # Page 7: Recommendations
            fig = plt.figure(figsize=(8.5, 11))
            ax = fig.add_subplot(111)
            ax.axis("off")

            recommendations = self._generate_recommendations(progress_data)
            ax.text(0.1, 0.9, "Recommendations", fontsize=18, fontweight="bold")

            y_position = 0.8
            for i, rec in enumerate(recommendations, 1):
                ax.text(0.1, y_position, f"{i}. {rec}", fontsize=11, wrap=True)
                y_position -= 0.1

            pdf.savefig(fig, bbox_inches="tight")
            plt.close()

            # Add metadata
            d = pdf.infodict()
            d["Title"] = f"{user_data['name']}'s Progress Report"
            d["Author"] = "NGX Agents Fitness System"
            d["Subject"] = f"{period.title()} Progress Report"
            d["Keywords"] = "Fitness, Progress, Health"
            d["CreationDate"] = datetime.now()

        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    def _generate_summary_text(
        self, user_data: Dict[str, Any], progress_data: Dict[str, Any]
    ) -> str:
        """Generate executive summary text."""
        summary = f"""
Dear {user_data['name']},

This report summarizes your fitness progress over the past {progress_data.get('period', 'month')}. 

Key Achievements:
• Weight Change: {progress_data.get('weight_change', 'N/A')} kg
• Body Fat Change: {progress_data.get('body_fat_change', 'N/A')}%
• Muscle Mass Change: {progress_data.get('muscle_mass_change', 'N/A')}%
• Workout Compliance: {progress_data.get('workout_compliance', 'N/A')}%
• Nutrition Adherence: {progress_data.get('nutrition_adherence', 'N/A')}%

Overall, your progress has been {progress_data.get('overall_assessment', 'good')}. 
Continue following your personalized plan for optimal results.

Best regards,
Your NGX Fitness Team
        """
        return summary.strip()

    def _generate_recommendations(self, progress_data: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations based on progress."""
        recommendations = []

        # Weight-based recommendations
        if progress_data.get("weight_change", 0) < progress_data.get(
            "weight_goal_change", -1
        ):
            recommendations.append(
                "Consider increasing your caloric deficit by 200-300 calories per day"
            )

        # Body composition recommendations
        if progress_data.get("muscle_mass_change", 0) < 0:
            recommendations.append(
                "Increase protein intake to 1.6-2.2g per kg of body weight to preserve muscle mass"
            )

        # Performance recommendations
        if progress_data.get("performance_plateau", False):
            recommendations.append(
                "Implement progressive overload by increasing weights by 2.5-5% weekly"
            )

        # Compliance recommendations
        if progress_data.get("workout_compliance", 100) < 80:
            recommendations.append(
                "Try scheduling workouts at the same time each day to build consistency"
            )

        # Nutrition recommendations
        if progress_data.get("nutrition_adherence", 100) < 70:
            recommendations.append(
                "Consider meal prepping on weekends to improve nutritional compliance"
            )

        # Always add some positive reinforcement
        recommendations.append(
            "Keep up the great work! Consistency is key to achieving your fitness goals"
        )

        return recommendations


class ExerciseVideoLinkGenerator:
    """Generates links to exercise demonstration videos."""

    def __init__(self):
        """Initialize with exercise video database."""
        # This would normally connect to a database or API
        # For now, we'll use a mock database
        self.exercise_database = {
            "squat": {
                "name": "Barbell Back Squat",
                "video_url": "https://www.youtube.com/watch?v=example1",
                "thumbnail": "squat_thumb.jpg",
                "difficulty": "intermediate",
                "muscle_groups": ["quadriceps", "glutes", "hamstrings"],
            },
            "bench_press": {
                "name": "Barbell Bench Press",
                "video_url": "https://www.youtube.com/watch?v=example2",
                "thumbnail": "bench_thumb.jpg",
                "difficulty": "intermediate",
                "muscle_groups": ["chest", "triceps", "shoulders"],
            },
            "deadlift": {
                "name": "Conventional Deadlift",
                "video_url": "https://www.youtube.com/watch?v=example3",
                "thumbnail": "deadlift_thumb.jpg",
                "difficulty": "advanced",
                "muscle_groups": ["back", "glutes", "hamstrings"],
            },
        }

    async def get_exercise_video_links(
        self, exercises: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get video links for a list of exercises.

        Args:
            exercises: List of exercise names

        Returns:
            List of exercise video information
        """
        video_links = []

        for exercise in exercises:
            exercise_key = exercise.lower().replace(" ", "_")
            if exercise_key in self.exercise_database:
                video_info = self.exercise_database[exercise_key].copy()
                video_info["requested_exercise"] = exercise
                video_links.append(video_info)
            else:
                # Search for similar exercises or use a default
                video_links.append(
                    {
                        "requested_exercise": exercise,
                        "name": exercise,
                        "video_url": f"https://www.youtube.com/results?search_query={exercise.replace(' ', '+')}+proper+form",
                        "thumbnail": None,
                        "difficulty": "unknown",
                        "muscle_groups": [],
                    }
                )

        return video_links

    async def generate_workout_video_playlist(
        self, workout_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a video playlist for a workout plan.

        Args:
            workout_plan: Workout plan with exercises

        Returns:
            Playlist information with video links
        """
        playlist = {
            "workout_name": workout_plan.get("name", "Custom Workout"),
            "duration": workout_plan.get("duration", "45-60 minutes"),
            "difficulty": workout_plan.get("difficulty", "intermediate"),
            "exercises": [],
        }

        for exercise_group in workout_plan.get("exercises", []):
            group_videos = {
                "group_name": exercise_group.get("muscle_group", "General"),
                "videos": [],
            }

            exercises = exercise_group.get("exercises", [])
            videos = await self.get_exercise_video_links([e["name"] for e in exercises])

            for exercise, video in zip(exercises, videos):
                video["sets"] = exercise.get("sets", 3)
                video["reps"] = exercise.get("reps", "8-12")
                video["rest"] = exercise.get("rest", "60s")
                group_videos["videos"].append(video)

            playlist["exercises"].append(group_videos)

        return playlist


# Utility functions for visualization
async def create_progress_collage(images: List[bytes], layout: str = "grid") -> bytes:
    """
    Create a collage from multiple progress images.

    Args:
        images: List of image bytes
        layout: Layout style ('grid', 'timeline', 'comparison')

    Returns:
        Collage image as bytes
    """
    # Convert bytes to PIL images
    pil_images = [Image.open(io.BytesIO(img)) for img in images]

    if layout == "grid":
        # Calculate grid dimensions
        n = len(pil_images)
        cols = int(np.ceil(np.sqrt(n)))
        rows = int(np.ceil(n / cols))

        # Determine size of collage
        max_width = max(img.width for img in pil_images)
        max_height = max(img.height for img in pil_images)

        collage = Image.new("RGB", (cols * max_width, rows * max_height), "white")

        for idx, img in enumerate(pil_images):
            row = idx // cols
            col = idx % cols
            collage.paste(img, (col * max_width, row * max_height))

    elif layout == "timeline":
        # Horizontal timeline layout
        total_width = sum(img.width for img in pil_images)
        max_height = max(img.height for img in pil_images)

        collage = Image.new("RGB", (total_width, max_height), "white")

        x_offset = 0
        for img in pil_images:
            collage.paste(img, (x_offset, 0))
            x_offset += img.width

    elif layout == "comparison":
        # Side-by-side comparison (works best with 2 images)
        if len(pil_images) >= 2:
            img1, img2 = pil_images[0], pil_images[1]
            width = img1.width + img2.width + 50  # 50px spacing
            height = max(img1.height, img2.height)

            collage = Image.new("RGB", (width, height), "white")
            collage.paste(img1, (0, 0))
            collage.paste(img2, (img1.width + 50, 0))

            # Add labels
            draw = ImageDraw.Draw(collage)
            try:
                font = ImageFont.truetype("Arial.ttf", 24)
            except:
                font = ImageFont.load_default()

            draw.text(
                (img1.width // 2, height - 30),
                "Before",
                fill="black",
                font=font,
                anchor="mm",
            )
            draw.text(
                (img1.width + 50 + img2.width // 2, height - 30),
                "After",
                fill="black",
                font=font,
                anchor="mm",
            )
        else:
            collage = (
                pil_images[0] if pil_images else Image.new("RGB", (100, 100), "white")
            )

    # Convert back to bytes
    output = io.BytesIO()
    collage.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()


# Export main classes
__all__ = [
    "ProgressChartGenerator",
    "NutritionInfographicGenerator",
    "PDFReportGenerator",
    "ExerciseVideoLinkGenerator",
    "create_progress_collage",
]

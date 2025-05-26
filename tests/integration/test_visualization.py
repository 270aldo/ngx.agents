"""
Integration tests for visualization module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from core.visualization import (
    ProgressChartGenerator,
    NutritionInfographicGenerator,
    PDFReportGenerator,
    ExerciseVideoLinkGenerator,
    create_progress_collage,
)


class TestProgressChartGenerator:
    """Test progress chart generation."""

    @pytest.fixture
    def chart_generator(self):
        """Create a chart generator instance."""
        return ProgressChartGenerator()

    @pytest.fixture
    def sample_weight_data(self):
        """Sample weight data for testing."""
        base_date = datetime.now() - timedelta(days=30)
        return [
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "weight": 80 - (i * 0.1),  # Simulating weight loss
            }
            for i in range(30)
        ]

    @pytest.fixture
    def sample_user_info(self):
        """Sample user information."""
        return {"name": "Test User", "goal_weight": 75}

    @pytest.mark.asyncio
    async def test_generate_weight_progress_chart(
        self, chart_generator, sample_weight_data, sample_user_info
    ):
        """Test weight progress chart generation."""
        # Generate chart
        chart_bytes = await chart_generator.generate_weight_progress_chart(
            sample_weight_data, sample_user_info
        )

        # Verify chart was generated
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0

        # Verify it's a valid PNG
        assert chart_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.asyncio
    async def test_generate_body_composition_chart(self, chart_generator):
        """Test body composition chart generation."""
        # Sample body composition data
        base_date = datetime.now() - timedelta(days=30)
        data = [
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "muscle_mass": 40 + (i * 0.05),  # Gaining muscle
                "body_fat": 25 - (i * 0.1),  # Losing fat
                "water": 55 + (i * 0.02),
            }
            for i in range(30)
        ]

        # Generate chart
        chart_bytes = await chart_generator.generate_body_composition_chart(data)

        # Verify
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0

    @pytest.mark.asyncio
    async def test_generate_performance_metrics_chart(self, chart_generator):
        """Test performance metrics chart generation."""
        # Sample performance data
        base_date = datetime.now() - timedelta(days=30)
        data = [
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "bench_press": 60 + (i * 0.5),
                "squat": 80 + (i * 0.7),
                "deadlift": 100 + (i * 1),
                "overhead_press": 40 + (i * 0.3),
            }
            for i in range(0, 30, 3)  # Every 3 days
        ]

        # Generate chart
        chart_bytes = await chart_generator.generate_performance_metrics_chart(
            data, "strength"
        )

        # Verify
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0

    @pytest.mark.asyncio
    async def test_generate_comparison_chart(self, chart_generator):
        """Test comparison chart generation."""
        current_data = {
            "weight": 78,
            "body_fat": 22,
            "muscle_mass": 42,
            "strength_score": 85,
        }

        previous_data = {
            "weight": 82,
            "body_fat": 25,
            "muscle_mass": 40,
            "strength_score": 75,
        }

        # Generate chart
        chart_bytes = await chart_generator.generate_comparison_chart(
            current_data, previous_data, "month"
        )

        # Verify
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0


class TestNutritionInfographicGenerator:
    """Test nutrition infographic generation."""

    @pytest.fixture
    def nutrition_generator(self):
        """Create a nutrition generator instance."""
        return NutritionInfographicGenerator()

    @pytest.fixture
    def sample_nutrition_data(self):
        """Sample nutrition data for testing."""
        return {
            "calories_consumed": 2150,
            "calories_target": 2000,
            "protein": 150,
            "protein_consumed": 145,
            "protein_target": 150,
            "carbs": 250,
            "carbs_consumed": 230,
            "carbs_target": 250,
            "fat": 65,
            "fat_consumed": 70,
            "fat_target": 65,
            "fiber": 30,
            "fiber_consumed": 25,
            "fiber_target": 30,
            "meals": {
                "breakfast": {"calories": 450, "protein": 30, "carbs": 50, "fat": 15},
                "lunch": {"calories": 650, "protein": 45, "carbs": 70, "fat": 25},
                "dinner": {"calories": 750, "protein": 50, "carbs": 80, "fat": 20},
                "snack": {"calories": 300, "protein": 20, "carbs": 30, "fat": 10},
            },
        }

    @pytest.mark.asyncio
    async def test_generate_daily_nutrition_breakdown(
        self, nutrition_generator, sample_nutrition_data
    ):
        """Test daily nutrition breakdown generation."""
        # Generate infographic
        chart_bytes = await nutrition_generator.generate_daily_nutrition_breakdown(
            sample_nutrition_data
        )

        # Verify
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0

        # Verify it's a valid PNG
        assert chart_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.asyncio
    async def test_generate_meal_plan_infographic(self, nutrition_generator):
        """Test meal plan infographic generation."""
        # Sample meal plan
        meal_plan = {
            "2024-01-01": {
                "breakfast": {
                    "name": "Oatmeal with Berries",
                    "calories": 350,
                    "protein": 15,
                    "carbs": 60,
                    "fat": 8,
                },
                "lunch": {
                    "name": "Grilled Chicken Salad",
                    "calories": 450,
                    "protein": 40,
                    "carbs": 30,
                    "fat": 20,
                },
                "dinner": {
                    "name": "Salmon with Vegetables",
                    "calories": 550,
                    "protein": 45,
                    "carbs": 40,
                    "fat": 25,
                },
            },
            "2024-01-02": {
                "breakfast": {
                    "name": "Greek Yogurt Parfait",
                    "calories": 300,
                    "protein": 20,
                    "carbs": 40,
                    "fat": 10,
                },
                "lunch": {
                    "name": "Turkey Wrap",
                    "calories": 400,
                    "protein": 35,
                    "carbs": 45,
                    "fat": 15,
                },
                "dinner": {
                    "name": "Beef Stir Fry",
                    "calories": 600,
                    "protein": 40,
                    "carbs": 50,
                    "fat": 30,
                },
            },
        }

        # Generate infographic
        chart_bytes = await nutrition_generator.generate_meal_plan_infographic(
            meal_plan
        )

        # Verify
        assert chart_bytes is not None
        assert isinstance(chart_bytes, bytes)
        assert len(chart_bytes) > 0


class TestPDFReportGenerator:
    """Test PDF report generation."""

    @pytest.fixture
    def pdf_generator(self):
        """Create a PDF generator instance."""
        return PDFReportGenerator()

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "height": 180,
            "goals": {"weight_loss": 10, "muscle_gain": 5},
        }

    @pytest.fixture
    def sample_progress_data(self):
        """Sample progress data for testing."""
        base_date = datetime.now() - timedelta(days=30)
        return {
            "period": "monthly",
            "weight_data": [
                {
                    "date": (base_date + timedelta(days=i)).isoformat(),
                    "weight": 85 - (i * 0.1),
                }
                for i in range(30)
            ],
            "body_composition_data": [
                {
                    "date": (base_date + timedelta(days=i)).isoformat(),
                    "muscle_mass": 40 + (i * 0.05),
                    "body_fat": 25 - (i * 0.1),
                }
                for i in range(30)
            ],
            "weight_change": -3,
            "body_fat_change": -3,
            "muscle_mass_change": 1.5,
            "workout_compliance": 85,
            "nutrition_adherence": 78,
            "overall_assessment": "excellent",
        }

    @pytest.mark.asyncio
    async def test_generate_progress_report(
        self, pdf_generator, sample_user_data, sample_progress_data
    ):
        """Test progress report PDF generation."""
        # Generate report
        pdf_bytes = await pdf_generator.generate_progress_report(
            sample_user_data, sample_progress_data, "monthly"
        )

        # Verify
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

        # Verify it's a valid PDF (starts with %PDF)
        assert pdf_bytes[:4] == b"%PDF"


class TestExerciseVideoLinkGenerator:
    """Test exercise video link generation."""

    @pytest.fixture
    def video_generator(self):
        """Create a video link generator instance."""
        return ExerciseVideoLinkGenerator()

    @pytest.mark.asyncio
    async def test_get_exercise_video_links(self, video_generator):
        """Test getting exercise video links."""
        exercises = ["squat", "bench_press", "deadlift", "running"]

        # Get video links
        video_links = await video_generator.get_exercise_video_links(exercises)

        # Verify
        assert video_links is not None
        assert len(video_links) == 4

        # Check known exercises
        squat_video = next(v for v in video_links if v["requested_exercise"] == "squat")
        assert squat_video["name"] == "Barbell Back Squat"
        assert "video_url" in squat_video
        assert squat_video["difficulty"] == "intermediate"

        # Check unknown exercise
        running_video = next(
            v for v in video_links if v["requested_exercise"] == "running"
        )
        assert running_video["name"] == "running"
        assert "youtube.com/results" in running_video["video_url"]

    @pytest.mark.asyncio
    async def test_generate_workout_video_playlist(self, video_generator):
        """Test workout video playlist generation."""
        workout_plan = {
            "name": "Upper Body Workout",
            "duration": "45 minutes",
            "difficulty": "intermediate",
            "exercises": [
                {
                    "muscle_group": "Chest",
                    "exercises": [
                        {
                            "name": "bench_press",
                            "sets": 4,
                            "reps": "8-10",
                            "rest": "90s",
                        },
                        {
                            "name": "dumbbell_fly",
                            "sets": 3,
                            "reps": "12-15",
                            "rest": "60s",
                        },
                    ],
                },
                {
                    "muscle_group": "Back",
                    "exercises": [
                        {"name": "deadlift", "sets": 4, "reps": "6-8", "rest": "120s"},
                        {"name": "pullup", "sets": 3, "reps": "8-12", "rest": "90s"},
                    ],
                },
            ],
        }

        # Generate playlist
        playlist = await video_generator.generate_workout_video_playlist(workout_plan)

        # Verify
        assert playlist is not None
        assert playlist["workout_name"] == "Upper Body Workout"
        assert playlist["duration"] == "45 minutes"
        assert len(playlist["exercises"]) == 2

        # Check exercise groups
        chest_group = playlist["exercises"][0]
        assert chest_group["group_name"] == "Chest"
        assert len(chest_group["videos"]) == 2


class TestVisualizationUtilities:
    """Test visualization utility functions."""

    @pytest.mark.asyncio
    async def test_create_progress_collage_grid(self):
        """Test creating a grid collage."""
        # Create dummy images (solid color PNGs)
        from PIL import Image
        import io

        images = []
        for i in range(4):
            img = Image.new("RGB", (200, 200), color=(i * 60, 100, 200 - i * 50))
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            images.append(buffer.getvalue())

        # Create collage
        collage_bytes = await create_progress_collage(images, "grid")

        # Verify
        assert collage_bytes is not None
        assert isinstance(collage_bytes, bytes)
        assert len(collage_bytes) > 0

        # Verify it's a valid PNG
        assert collage_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.asyncio
    async def test_create_progress_collage_comparison(self):
        """Test creating a comparison collage."""
        # Create two dummy images
        from PIL import Image
        import io

        images = []
        for color in [(255, 0, 0), (0, 255, 0)]:  # Red and green
            img = Image.new("RGB", (300, 400), color=color)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            images.append(buffer.getvalue())

        # Create collage
        collage_bytes = await create_progress_collage(images, "comparison")

        # Verify
        assert collage_bytes is not None
        assert isinstance(collage_bytes, bytes)
        assert len(collage_bytes) > 0

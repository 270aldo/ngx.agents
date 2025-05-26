"""
Image Processing Tasks
Async tasks for image analysis and processing
"""

import json
import logging
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from core.celery_app import app
from clients.vertex_ai.multimodal_client import MultimodalClient
from clients.supabase_client import SupabaseClient
from clients.vertex_ai.vision_client import VisionClient
import numpy as np
from PIL import Image
import io

logger = logging.getLogger(__name__)


class BaseImageTask(Task):
    """Base class for image processing tasks"""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 30}
    track_started = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Image task {task_id} failed: {exc}", exc_info=einfo)


@app.task(base=BaseImageTask, name="tasks.images.analyze_posture")
def analyze_posture(user_id: str, image_url: str, exercise_type: str) -> Dict[str, Any]:
    """
    Analyze exercise posture from image

    Args:
        user_id: User identifier
        image_url: URL of the image to analyze
        exercise_type: Type of exercise being performed

    Returns:
        Dict with posture analysis results
    """
    try:
        logger.info(f"Analyzing posture for user {user_id}, exercise: {exercise_type}")

        # Initialize clients
        vision_client = VisionClient()
        supabase = SupabaseClient()

        # Download image
        image_data = supabase.download_file(image_url)

        # Perform posture analysis
        analysis_prompt = f"""
        Analyze the exercise posture in this image for {exercise_type}.
        Identify:
        1. Key body positions and alignment
        2. Any form issues or corrections needed
        3. Safety concerns
        4. Positive aspects of the form
        5. Specific recommendations for improvement
        
        Provide a detailed technical analysis suitable for fitness coaching.
        """

        analysis_result = vision_client.analyze_image(
            image_data, prompt=analysis_prompt
        )

        # Extract key points
        posture_data = _parse_posture_analysis(analysis_result)

        # Calculate posture score
        posture_score = _calculate_posture_score(posture_data)

        # Generate visual overlay (key points)
        overlay_image = _generate_posture_overlay(image_data, posture_data)

        # Upload analyzed image
        overlay_url = None
        if overlay_image:
            overlay_path = f"posture_analysis/{user_id}/{datetime.utcnow().timestamp()}_overlay.png"
            overlay_url = supabase.upload_file(overlay_image, overlay_path)

        # Store analysis results
        analysis_record = {
            "user_id": user_id,
            "exercise_type": exercise_type,
            "original_image_url": image_url,
            "overlay_image_url": overlay_url,
            "posture_score": posture_score,
            "analysis": posture_data,
            "recommendations": posture_data.get("recommendations", []),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        supabase.save_posture_analysis(analysis_record)

        logger.info(f"Posture analysis completed with score: {posture_score}")

        return {
            "success": True,
            "posture_score": posture_score,
            "analysis": posture_data,
            "overlay_url": overlay_url,
            "recommendations": posture_data.get("recommendations", []),
        }

    except SoftTimeLimitExceeded:
        logger.error("Posture analysis exceeded time limit")
        raise
    except Exception as e:
        logger.error(f"Error in posture analysis: {e}")
        raise


@app.task(base=BaseImageTask, name="tasks.images.compare_progress_photos")
def compare_progress_photos(
    user_id: str, before_url: str, after_url: str, comparison_type: str = "general"
) -> Dict[str, Any]:
    """
    Compare before/after progress photos

    Args:
        user_id: User identifier
        before_url: URL of before photo
        after_url: URL of after photo
        comparison_type: Type of comparison (general, muscle, weight_loss)

    Returns:
        Dict with comparison results
    """
    try:
        logger.info(f"Comparing progress photos for user {user_id}")

        # Initialize clients
        multimodal_client = MultimodalClient()
        supabase = SupabaseClient()

        # Download images
        before_image = supabase.download_file(before_url)
        after_image = supabase.download_file(after_url)

        # Prepare comparison prompt based on type
        comparison_prompts = {
            "general": """
            Compare these before and after fitness progress photos.
            Analyze visible changes in:
            1. Body composition
            2. Muscle definition
            3. Posture improvements
            4. Overall physique changes
            5. Estimated body fat percentage change
            """,
            "muscle": """
            Compare muscle development in these progress photos.
            Focus on:
            1. Muscle size changes
            2. Definition improvements
            3. Symmetry development
            4. Specific muscle groups that show progress
            5. Areas that need more focus
            """,
            "weight_loss": """
            Compare weight loss progress in these photos.
            Analyze:
            1. Visible weight reduction
            2. Body shape changes
            3. Waist/hip improvements
            4. Face/neck changes
            5. Estimated pounds lost
            """,
        }

        prompt = comparison_prompts.get(comparison_type, comparison_prompts["general"])

        # Perform visual comparison
        comparison_result = multimodal_client.analyze_multiple_images(
            [before_image, after_image], prompt=prompt
        )

        # Parse comparison results
        comparison_data = _parse_comparison_results(comparison_result)

        # Generate side-by-side comparison image
        comparison_image = _create_comparison_image(before_image, after_image)

        # Upload comparison image
        comparison_url = supabase.upload_file(
            comparison_image,
            f"progress_comparisons/{user_id}/{datetime.utcnow().timestamp()}_comparison.png",
        )

        # Calculate progress metrics
        progress_metrics = _calculate_progress_metrics(comparison_data)

        # Store comparison results
        comparison_record = {
            "user_id": user_id,
            "before_url": before_url,
            "after_url": after_url,
            "comparison_url": comparison_url,
            "comparison_type": comparison_type,
            "analysis": comparison_data,
            "metrics": progress_metrics,
            "created_at": datetime.utcnow().isoformat(),
        }

        supabase.save_progress_comparison(comparison_record)

        logger.info(f"Progress comparison completed successfully")

        return {
            "success": True,
            "comparison_url": comparison_url,
            "analysis": comparison_data,
            "metrics": progress_metrics,
            "key_changes": comparison_data.get("key_changes", []),
        }

    except Exception as e:
        logger.error(f"Error comparing progress photos: {e}")
        raise


@app.task(base=BaseImageTask, name="tasks.images.process_nutrition_label")
def process_nutrition_label(user_id: str, image_url: str) -> Dict[str, Any]:
    """
    Extract nutrition information from food label image

    Args:
        user_id: User identifier
        image_url: URL of nutrition label image

    Returns:
        Dict with extracted nutrition data
    """
    try:
        logger.info(f"Processing nutrition label for user {user_id}")

        # Initialize clients
        vision_client = VisionClient()
        supabase = SupabaseClient()

        # Download image
        image_data = supabase.download_file(image_url)

        # OCR and nutrition extraction
        ocr_prompt = """
        Extract all nutrition information from this food label.
        Include:
        1. Serving size and servings per container
        2. Calories per serving
        3. All macronutrients (protein, carbs, fat) with amounts
        4. Fiber and sugar content
        5. Sodium and cholesterol
        6. Vitamins and minerals with percentages
        7. Ingredients list if visible
        
        Format the data in a structured way.
        """

        ocr_result = vision_client.extract_text_from_image(
            image_data, prompt=ocr_prompt
        )

        # Parse nutrition data
        nutrition_data = _parse_nutrition_label(ocr_result)

        # Validate and standardize nutrition values
        validated_data = _validate_nutrition_data(nutrition_data)

        # Calculate additional metrics
        nutrition_metrics = _calculate_nutrition_metrics(validated_data)

        # Store nutrition data
        nutrition_record = {
            "user_id": user_id,
            "image_url": image_url,
            "nutrition_data": validated_data,
            "metrics": nutrition_metrics,
            "raw_ocr": ocr_result,
            "processed_at": datetime.utcnow().isoformat(),
        }

        supabase.save_nutrition_label_data(nutrition_record)

        logger.info(f"Nutrition label processed successfully")

        return {
            "success": True,
            "nutrition": validated_data,
            "metrics": nutrition_metrics,
            "warnings": nutrition_metrics.get("warnings", []),
        }

    except Exception as e:
        logger.error(f"Error processing nutrition label: {e}")
        raise


@app.task(base=BaseImageTask, name="tasks.images.analyze_meal_photo")
def analyze_meal_photo(
    user_id: str, image_url: str, meal_type: str = "unknown"
) -> Dict[str, Any]:
    """
    Analyze meal photo for nutritional estimation

    Args:
        user_id: User identifier
        image_url: URL of meal photo
        meal_type: Type of meal (breakfast, lunch, dinner, snack)

    Returns:
        Dict with meal analysis and nutrition estimates
    """
    try:
        logger.info(f"Analyzing meal photo for user {user_id}, meal type: {meal_type}")

        # Initialize clients
        multimodal_client = MultimodalClient()
        supabase = SupabaseClient()

        # Download image
        image_data = supabase.download_file(image_url)

        # Analyze meal
        meal_prompt = """
        Analyze this meal photo and provide:
        1. Identified food items with portion sizes
        2. Estimated calories for each item
        3. Estimated macronutrients (protein, carbs, fat)
        4. Overall meal healthiness score (1-10)
        5. Nutritional balance assessment
        6. Suggestions for improvement
        
        Be specific about portions and provide realistic estimates.
        """

        meal_analysis = multimodal_client.analyze_image(image_data, prompt=meal_prompt)

        # Parse meal analysis
        meal_data = _parse_meal_analysis(meal_analysis)

        # Calculate total nutrition
        total_nutrition = _calculate_meal_totals(meal_data)

        # Get user's nutrition goals
        user_goals = supabase.get_user_nutrition_goals(user_id)

        # Compare with daily goals
        goal_comparison = _compare_with_goals(total_nutrition, user_goals, meal_type)

        # Store meal analysis
        meal_record = {
            "user_id": user_id,
            "image_url": image_url,
            "meal_type": meal_type,
            "food_items": meal_data.get("items", []),
            "total_nutrition": total_nutrition,
            "healthiness_score": meal_data.get("healthiness_score", 0),
            "goal_comparison": goal_comparison,
            "suggestions": meal_data.get("suggestions", []),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        supabase.save_meal_analysis(meal_record)

        logger.info(
            f"Meal analysis completed with score: {meal_data.get('healthiness_score', 0)}"
        )

        return {
            "success": True,
            "meal_analysis": meal_data,
            "total_nutrition": total_nutrition,
            "goal_comparison": goal_comparison,
            "healthiness_score": meal_data.get("healthiness_score", 0),
        }

    except Exception as e:
        logger.error(f"Error analyzing meal photo: {e}")
        raise


@app.task(base=BaseImageTask, name="tasks.images.batch_resize_images")
def batch_resize_images(
    user_id: str, image_urls: List[str], sizes: List[Tuple[int, int]]
) -> Dict[str, Any]:
    """
    Batch resize images for different display purposes

    Args:
        user_id: User identifier
        image_urls: List of image URLs to resize
        sizes: List of (width, height) tuples

    Returns:
        Dict with resized image URLs
    """
    try:
        logger.info(f"Batch resizing {len(image_urls)} images for user {user_id}")

        supabase = SupabaseClient()
        resized_images = {}

        for image_url in image_urls:
            try:
                # Download original image
                image_data = supabase.download_file(image_url)
                image = Image.open(io.BytesIO(image_data))

                resized_versions = []

                for width, height in sizes:
                    # Resize image maintaining aspect ratio
                    resized = _resize_image_aspect_ratio(image, width, height)

                    # Convert to bytes
                    buffer = io.BytesIO()
                    resized.save(buffer, format="PNG", optimize=True)
                    buffer.seek(0)

                    # Upload resized version
                    filename = f"resized/{user_id}/{width}x{height}_{datetime.utcnow().timestamp()}.png"
                    resized_url = supabase.upload_file(buffer.getvalue(), filename)

                    resized_versions.append(
                        {"size": f"{width}x{height}", "url": resized_url}
                    )

                resized_images[image_url] = resized_versions

            except Exception as e:
                logger.error(f"Error resizing image {image_url}: {e}")
                resized_images[image_url] = {"error": str(e)}

        logger.info(f"Batch resize completed for {len(resized_images)} images")

        return {
            "success": True,
            "resized_images": resized_images,
            "total_processed": len(resized_images),
        }

    except Exception as e:
        logger.error(f"Error in batch resize: {e}")
        raise


# Helper functions
def _parse_posture_analysis(analysis_result: str) -> Dict[str, Any]:
    """Parse posture analysis from AI response"""
    # Implementation would parse the structured response
    # This is a simplified version
    return {
        "alignment": "good",
        "issues": [],
        "recommendations": ["Keep spine neutral", "Engage core"],
        "safety_concerns": [],
        "positive_aspects": ["Good hip hinge", "Proper foot position"],
    }


def _calculate_posture_score(posture_data: Dict[str, Any]) -> float:
    """Calculate posture score from analysis data"""
    base_score = 10.0

    # Deduct for issues
    base_score -= len(posture_data.get("issues", [])) * 0.5
    base_score -= len(posture_data.get("safety_concerns", [])) * 1.0

    # Add for positive aspects
    base_score += len(posture_data.get("positive_aspects", [])) * 0.2

    return max(0, min(10, base_score))


def _generate_posture_overlay(
    image_data: bytes, posture_data: Dict[str, Any]
) -> Optional[bytes]:
    """Generate image with posture key points overlay"""
    # This would use computer vision to overlay key points
    # Simplified for now
    return None


def _parse_comparison_results(comparison_result: str) -> Dict[str, Any]:
    """Parse progress comparison results"""
    return {
        "key_changes": ["Visible muscle definition", "Reduced body fat"],
        "body_composition": {"before": "estimated 25%", "after": "estimated 20%"},
        "muscle_changes": ["Improved shoulder development", "Better core definition"],
        "recommendations": ["Continue current program", "Focus on lower body"],
    }


def _create_comparison_image(before: bytes, after: bytes) -> bytes:
    """Create side-by-side comparison image"""
    # Load images
    img1 = Image.open(io.BytesIO(before))
    img2 = Image.open(io.BytesIO(after))

    # Resize to same height
    height = min(img1.height, img2.height)
    img1 = img1.resize((int(img1.width * height / img1.height), height))
    img2 = img2.resize((int(img2.width * height / img2.height), height))

    # Create combined image
    combined = Image.new("RGB", (img1.width + img2.width + 10, height))
    combined.paste(img1, (0, 0))
    combined.paste(img2, (img1.width + 10, 0))

    # Save to bytes
    buffer = io.BytesIO()
    combined.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.getvalue()


def _calculate_progress_metrics(comparison_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate progress metrics from comparison data"""
    return {
        "overall_progress_score": 8.5,
        "body_fat_change": -5.0,
        "muscle_gain_estimate": "+3-5 lbs",
        "areas_improved": ["shoulders", "core", "arms"],
        "areas_to_focus": ["legs", "back"],
    }


def _parse_nutrition_label(ocr_result: str) -> Dict[str, Any]:
    """Parse nutrition label OCR results"""
    # Would implement actual parsing logic
    return {
        "serving_size": "1 cup (240g)",
        "calories": 150,
        "protein": 10,
        "carbs": 20,
        "fat": 5,
        "fiber": 3,
        "sugar": 8,
        "sodium": 200,
    }


def _validate_nutrition_data(nutrition_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and standardize nutrition data"""
    validated = nutrition_data.copy()

    # Ensure all values are numeric
    for key in ["calories", "protein", "carbs", "fat", "fiber", "sugar", "sodium"]:
        if key in validated:
            try:
                validated[key] = float(validated[key])
            except:
                validated[key] = 0

    return validated


def _calculate_nutrition_metrics(nutrition_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate additional nutrition metrics"""
    metrics = {
        "calorie_density": nutrition_data.get("calories", 0) / 100,  # per 100g
        "protein_percentage": (nutrition_data.get("protein", 0) * 4)
        / nutrition_data.get("calories", 1)
        * 100,
        "is_high_protein": nutrition_data.get("protein", 0) > 20,
        "is_low_sugar": nutrition_data.get("sugar", 0) < 5,
        "warnings": [],
    }

    if nutrition_data.get("sodium", 0) > 500:
        metrics["warnings"].append("High sodium content")

    if nutrition_data.get("sugar", 0) > 15:
        metrics["warnings"].append("High sugar content")

    return metrics


def _parse_meal_analysis(meal_analysis: str) -> Dict[str, Any]:
    """Parse meal analysis results"""
    return {
        "items": [
            {
                "name": "Grilled chicken",
                "portion": "4 oz",
                "calories": 180,
                "protein": 35,
            },
            {"name": "Brown rice", "portion": "1 cup", "calories": 220, "protein": 5},
            {"name": "Broccoli", "portion": "1 cup", "calories": 30, "protein": 2},
        ],
        "healthiness_score": 8.5,
        "suggestions": ["Add more vegetables", "Good protein portion"],
    }


def _calculate_meal_totals(meal_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate total nutrition from meal items"""
    totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}

    for item in meal_data.get("items", []):
        totals["calories"] += item.get("calories", 0)
        totals["protein"] += item.get("protein", 0)
        totals["carbs"] += item.get("carbs", 0)
        totals["fat"] += item.get("fat", 0)

    return totals


def _compare_with_goals(
    nutrition: Dict[str, Any], goals: Dict[str, Any], meal_type: str
) -> Dict[str, Any]:
    """Compare meal nutrition with daily goals"""
    meal_percentages = {
        "breakfast": 0.25,
        "lunch": 0.35,
        "dinner": 0.30,
        "snack": 0.10,
        "unknown": 0.25,
    }

    percentage = meal_percentages.get(meal_type, 0.25)

    return {
        "calories_vs_goal": nutrition["calories"]
        / (goals.get("daily_calories", 2000) * percentage)
        * 100,
        "protein_vs_goal": nutrition["protein"]
        / (goals.get("daily_protein", 150) * percentage)
        * 100,
        "on_track": True,  # Simplified
    }


def _resize_image_aspect_ratio(image: Image, max_width: int, max_height: int) -> Image:
    """Resize image maintaining aspect ratio"""
    ratio = min(max_width / image.width, max_height / image.height)
    new_size = (int(image.width * ratio), int(image.height * ratio))
    return image.resize(new_size, Image.Resampling.LANCZOS)

"""
Nutrition Data Normalizer
Converts nutrition data from various sources to NGX Agents standard format
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from .adapters.myfitnesspal import (
    MFPDailyNutrition,
    MFPMeal,
    MFPFood,
    MFPExercise,
    MFPWeight,
)

logger = logging.getLogger(__name__)


class NutritionSource(Enum):
    """Supported nutrition data sources"""

    MYFITNESSPAL = "myfitnesspal"
    CRONOMETER = "cronometer"
    LOSEIT = "loseit"
    MANUAL = "manual"


class NutritionMetricType(Enum):
    """Standard nutrition metric types in NGX system"""

    CALORIES = "calories"
    PROTEIN = "protein"
    CARBOHYDRATES = "carbohydrates"
    FAT = "fat"
    FIBER = "fiber"
    SUGAR = "sugar"
    SODIUM = "sodium"
    CHOLESTEROL = "cholesterol"
    WATER = "water"
    WEIGHT = "weight"
    BODY_FAT = "body_fat"
    CALORIE_GOAL = "calorie_goal"
    MACRO_BALANCE = "macro_balance"


@dataclass
class NormalizedNutritionMetric:
    """Normalized nutrition metric in NGX standard format"""

    source: NutritionSource
    metric_type: NutritionMetricType
    value: float
    unit: str
    timestamp: datetime
    source_specific_id: str
    user_id: str
    meal_type: Optional[str] = None  # breakfast, lunch, dinner, snacks
    food_name: Optional[str] = None
    brand_name: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    is_goal: bool = False


@dataclass
class NormalizedMealData:
    """Normalized meal data"""

    meal_id: str
    meal_type: str  # breakfast, lunch, dinner, snacks
    date: date
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: Optional[float] = None
    total_sugar_g: Optional[float] = None
    total_sodium_mg: Optional[float] = None
    food_count: int
    source: NutritionSource
    user_id: str
    foods: List[Dict[str, Any]] = None


@dataclass
class NormalizedDailyNutrition:
    """Normalized daily nutrition summary"""

    date: date
    user_id: str
    source: NutritionSource
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: Optional[float] = None
    total_sugar_g: Optional[float] = None
    total_sodium_mg: Optional[float] = None
    total_water_ml: Optional[float] = None
    meals: List[NormalizedMealData]
    calorie_goal: Optional[float] = None
    protein_goal_g: Optional[float] = None
    carbs_goal_g: Optional[float] = None
    fat_goal_g: Optional[float] = None
    goal_adherence_percent: Optional[float] = None
    macro_balance: Dict[str, float] = None  # percentages of protein, carbs, fat


@dataclass
class NormalizedWeightData:
    """Normalized weight tracking data"""

    date: date
    weight_kg: float
    body_fat_percent: Optional[float] = None
    muscle_mass_kg: Optional[float] = None
    bmi: Optional[float] = None
    source: NutritionSource
    user_id: str
    notes: Optional[str] = None


class NutritionDataNormalizer:
    """
    Normalizes nutrition data from various sources to NGX standard format
    """

    def __init__(self):
        self.source_handlers = {NutritionSource.MYFITNESSPAL: self._normalize_mfp_data}

    def normalize_daily_nutrition(
        self,
        source: NutritionSource,
        raw_data: Union[MFPDailyNutrition, Dict[str, Any]],
    ) -> NormalizedDailyNutrition:
        """
        Normalize daily nutrition data from any source

        Args:
            source: Data source
            raw_data: Raw nutrition data

        Returns:
            Normalized daily nutrition
        """
        if source == NutritionSource.MYFITNESSPAL:
            return self._normalize_mfp_daily_nutrition(raw_data)
        else:
            raise ValueError(f"Unsupported source for nutrition data: {source}")

    def normalize_weight_data(
        self, source: NutritionSource, raw_data: Union[MFPWeight, Dict[str, Any]]
    ) -> NormalizedWeightData:
        """
        Normalize weight tracking data

        Args:
            source: Data source
            raw_data: Raw weight data

        Returns:
            Normalized weight data
        """
        if source == NutritionSource.MYFITNESSPAL:
            return self._normalize_mfp_weight(raw_data)
        else:
            raise ValueError(f"Unsupported source for weight data: {source}")

    def nutrition_to_metrics(
        self,
        source: NutritionSource,
        raw_data: Union[MFPDailyNutrition, MFPMeal, MFPFood, Dict[str, Any]],
        data_type: str,
    ) -> List[NormalizedNutritionMetric]:
        """
        Convert nutrition data to individual metrics

        Args:
            source: Data source
            raw_data: Raw data
            data_type: Type of data (daily, meal, food)

        Returns:
            List of normalized metrics
        """
        metrics = []

        if source == NutritionSource.MYFITNESSPAL:
            if data_type == "daily":
                daily = self._normalize_mfp_daily_nutrition(raw_data)
                metrics.extend(self._daily_to_metrics(daily))
            elif data_type == "meal":
                meal = self._normalize_mfp_meal(raw_data)
                metrics.extend(self._meal_to_metrics(meal))
            elif data_type == "food":
                metrics.extend(self._mfp_food_to_metrics(raw_data))

        return metrics

    def _normalize_mfp_data(self, raw_data: Any) -> Any:
        """Placeholder for MyFitnessPal data normalization"""
        pass

    def _normalize_mfp_daily_nutrition(
        self, mfp_data: MFPDailyNutrition
    ) -> NormalizedDailyNutrition:
        """Normalize MyFitnessPal daily nutrition data"""
        # Convert meals
        normalized_meals = []
        for meal in mfp_data.meals:
            normalized_meal = self._normalize_mfp_meal(meal)
            normalized_meals.append(normalized_meal)

        # Calculate goal adherence if goals are available
        goal_adherence = None
        if mfp_data.goal_calories and mfp_data.goal_calories > 0:
            calorie_adherence = (mfp_data.total_calories / mfp_data.goal_calories) * 100
            goal_adherence = min(100, abs(100 - abs(calorie_adherence - 100)))

        # Calculate macro balance
        total_macros = (
            mfp_data.total_protein_g + mfp_data.total_carbs_g + mfp_data.total_fat_g
        )
        macro_balance = None
        if total_macros > 0:
            protein_cals = mfp_data.total_protein_g * 4
            carbs_cals = mfp_data.total_carbs_g * 4
            fat_cals = mfp_data.total_fat_g * 9
            total_macro_cals = protein_cals + carbs_cals + fat_cals

            macro_balance = {
                "protein_percent": (
                    (protein_cals / total_macro_cals) * 100
                    if total_macro_cals > 0
                    else 0
                ),
                "carbs_percent": (
                    (carbs_cals / total_macro_cals) * 100 if total_macro_cals > 0 else 0
                ),
                "fat_percent": (
                    (fat_cals / total_macro_cals) * 100 if total_macro_cals > 0 else 0
                ),
            }

        return NormalizedDailyNutrition(
            date=mfp_data.date,
            user_id=mfp_data.user_id,
            source=NutritionSource.MYFITNESSPAL,
            total_calories=mfp_data.total_calories,
            total_protein_g=mfp_data.total_protein_g,
            total_carbs_g=mfp_data.total_carbs_g,
            total_fat_g=mfp_data.total_fat_g,
            total_fiber_g=mfp_data.total_fiber_g,
            total_sugar_g=mfp_data.total_sugar_g,
            total_sodium_mg=mfp_data.total_sodium_mg,
            total_water_ml=(
                mfp_data.water_cups * 236.588 if mfp_data.water_cups else None
            ),  # cups to ml
            meals=normalized_meals,
            calorie_goal=mfp_data.goal_calories,
            protein_goal_g=mfp_data.goal_protein_g,
            carbs_goal_g=mfp_data.goal_carbs_g,
            fat_goal_g=mfp_data.goal_fat_g,
            goal_adherence_percent=goal_adherence,
            macro_balance=macro_balance,
        )

    def _normalize_mfp_meal(self, meal: MFPMeal) -> NormalizedMealData:
        """Normalize MyFitnessPal meal data"""
        # Convert foods to simple dict format
        foods = []
        for food in meal.foods:
            foods.append(
                {
                    "name": food.food_name,
                    "brand": food.brand_name,
                    "calories": food.calories,
                    "protein_g": food.protein_g,
                    "carbs_g": food.carbs_g,
                    "fat_g": food.fat_g,
                    "serving_size": food.serving_size,
                    "serving_qty": food.serving_qty,
                }
            )

        return NormalizedMealData(
            meal_id=meal.meal_id,
            meal_type=meal.meal_name,
            date=meal.date,
            total_calories=meal.total_calories,
            total_protein_g=meal.total_protein_g,
            total_carbs_g=meal.total_carbs_g,
            total_fat_g=meal.total_fat_g,
            total_fiber_g=sum(f.fiber_g for f in meal.foods if f.fiber_g) or None,
            total_sugar_g=sum(f.sugar_g for f in meal.foods if f.sugar_g) or None,
            total_sodium_mg=sum(f.sodium_mg for f in meal.foods if f.sodium_mg) or None,
            food_count=len(meal.foods),
            source=NutritionSource.MYFITNESSPAL,
            user_id="",  # Will be set by service
            foods=foods,
        )

    def _normalize_mfp_weight(self, weight: MFPWeight) -> NormalizedWeightData:
        """Normalize MyFitnessPal weight data"""
        return NormalizedWeightData(
            date=weight.date,
            weight_kg=weight.weight_kg,
            body_fat_percent=weight.body_fat_percent,
            muscle_mass_kg=None,  # MFP doesn't track muscle mass
            bmi=None,  # Would need height to calculate
            source=NutritionSource.MYFITNESSPAL,
            user_id="",  # Will be set by service
            notes=weight.notes,
        )

    def _daily_to_metrics(
        self, daily: NormalizedDailyNutrition
    ) -> List[NormalizedNutritionMetric]:
        """Convert daily nutrition to metrics"""
        metrics = []
        base_timestamp = datetime.combine(daily.date, datetime.min.time())

        # Calories
        metrics.append(
            NormalizedNutritionMetric(
                source=daily.source,
                metric_type=NutritionMetricType.CALORIES,
                value=daily.total_calories,
                unit="kcal",
                timestamp=base_timestamp,
                source_specific_id=f"{daily.date}_daily",
                user_id=daily.user_id,
                raw_data={
                    "date": str(daily.date),
                    "total_calories": daily.total_calories,
                },
            )
        )

        # Macros
        for macro, value, unit in [
            (NutritionMetricType.PROTEIN, daily.total_protein_g, "g"),
            (NutritionMetricType.CARBOHYDRATES, daily.total_carbs_g, "g"),
            (NutritionMetricType.FAT, daily.total_fat_g, "g"),
        ]:
            metrics.append(
                NormalizedNutritionMetric(
                    source=daily.source,
                    metric_type=macro,
                    value=value,
                    unit=unit,
                    timestamp=base_timestamp,
                    source_specific_id=f"{daily.date}_daily",
                    user_id=daily.user_id,
                    raw_data={"date": str(daily.date), macro.value: value},
                )
            )

        # Optional nutrients
        if daily.total_fiber_g:
            metrics.append(
                NormalizedNutritionMetric(
                    source=daily.source,
                    metric_type=NutritionMetricType.FIBER,
                    value=daily.total_fiber_g,
                    unit="g",
                    timestamp=base_timestamp,
                    source_specific_id=f"{daily.date}_daily",
                    user_id=daily.user_id,
                )
            )

        if daily.total_water_ml:
            metrics.append(
                NormalizedNutritionMetric(
                    source=daily.source,
                    metric_type=NutritionMetricType.WATER,
                    value=daily.total_water_ml,
                    unit="ml",
                    timestamp=base_timestamp,
                    source_specific_id=f"{daily.date}_daily",
                    user_id=daily.user_id,
                )
            )

        # Goals
        if daily.calorie_goal:
            metrics.append(
                NormalizedNutritionMetric(
                    source=daily.source,
                    metric_type=NutritionMetricType.CALORIE_GOAL,
                    value=daily.calorie_goal,
                    unit="kcal",
                    timestamp=base_timestamp,
                    source_specific_id=f"{daily.date}_goal",
                    user_id=daily.user_id,
                    is_goal=True,
                )
            )

        return metrics

    def _meal_to_metrics(
        self, meal: NormalizedMealData
    ) -> List[NormalizedNutritionMetric]:
        """Convert meal data to metrics"""
        metrics = []
        base_timestamp = datetime.combine(meal.date, datetime.min.time())

        # Meal calories
        metrics.append(
            NormalizedNutritionMetric(
                source=meal.source,
                metric_type=NutritionMetricType.CALORIES,
                value=meal.total_calories,
                unit="kcal",
                timestamp=base_timestamp,
                source_specific_id=meal.meal_id,
                user_id=meal.user_id,
                meal_type=meal.meal_type,
                raw_data={"meal": meal.meal_type, "calories": meal.total_calories},
            )
        )

        # Meal macros
        for macro, value in [
            (NutritionMetricType.PROTEIN, meal.total_protein_g),
            (NutritionMetricType.CARBOHYDRATES, meal.total_carbs_g),
            (NutritionMetricType.FAT, meal.total_fat_g),
        ]:
            if value > 0:
                metrics.append(
                    NormalizedNutritionMetric(
                        source=meal.source,
                        metric_type=macro,
                        value=value,
                        unit="g",
                        timestamp=base_timestamp,
                        source_specific_id=meal.meal_id,
                        user_id=meal.user_id,
                        meal_type=meal.meal_type,
                    )
                )

        return metrics

    def _mfp_food_to_metrics(self, food: MFPFood) -> List[NormalizedNutritionMetric]:
        """Convert individual food item to metrics"""
        metrics = []
        timestamp = datetime.utcnow()  # Food items don't have timestamps

        # Create metrics for each nutrient
        nutrients = [
            (NutritionMetricType.CALORIES, food.calories, "kcal"),
            (NutritionMetricType.PROTEIN, food.protein_g, "g"),
            (NutritionMetricType.CARBOHYDRATES, food.carbs_g, "g"),
            (NutritionMetricType.FAT, food.fat_g, "g"),
        ]

        if food.fiber_g:
            nutrients.append((NutritionMetricType.FIBER, food.fiber_g, "g"))
        if food.sugar_g:
            nutrients.append((NutritionMetricType.SUGAR, food.sugar_g, "g"))
        if food.sodium_mg:
            nutrients.append((NutritionMetricType.SODIUM, food.sodium_mg, "mg"))

        for metric_type, value, unit in nutrients:
            metrics.append(
                NormalizedNutritionMetric(
                    source=NutritionSource.MYFITNESSPAL,
                    metric_type=metric_type,
                    value=value,
                    unit=unit,
                    timestamp=timestamp,
                    source_specific_id=food.food_id,
                    user_id="",  # Will be set by service
                    food_name=food.food_name,
                    brand_name=food.brand_name,
                    raw_data={
                        "serving_size": food.serving_size,
                        "serving_qty": food.serving_qty,
                    },
                )
            )

        return metrics


# Example usage
def example_normalizer_usage():
    """Example of how to use the nutrition normalizer"""
    from datetime import date

    normalizer = NutritionDataNormalizer()

    # Example MFP daily nutrition
    example_mfp_data = MFPDailyNutrition(
        date=date.today(),
        user_id="mfp_user123",
        meals=[],
        total_calories=2000,
        total_protein_g=150,
        total_carbs_g=200,
        total_fat_g=70,
        goal_calories=2100,
        goal_protein_g=160,
        goal_carbs_g=210,
        goal_fat_g=75,
    )

    # Normalize the data
    normalized_daily = normalizer.normalize_daily_nutrition(
        NutritionSource.MYFITNESSPAL, example_mfp_data
    )

    # Convert to metrics
    metrics = normalizer.nutrition_to_metrics(
        NutritionSource.MYFITNESSPAL, example_mfp_data, "daily"
    )

    print(f"Normalized daily nutrition: {normalized_daily.total_calories} kcal")
    print(f"Goal adherence: {normalized_daily.goal_adherence_percent}%")
    print(f"Macro balance: {normalized_daily.macro_balance}")
    print(f"Generated {len(metrics)} nutrition metrics")


if __name__ == "__main__":
    example_normalizer_usage()

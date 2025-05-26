"""
MyFitnessPal API Integration
Provides access to MyFitnessPal nutrition tracking data
Note: MyFitnessPal doesn't have an official public API, this uses their private API
Use responsibly and consider rate limiting
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
import aiohttp
import hashlib
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


@dataclass
class MFPConfig:
    """MyFitnessPal API configuration"""

    username: str
    password: str
    api_key: Optional[str] = None
    base_url: str = "https://api.myfitnesspal.com"
    web_url: str = "https://www.myfitnesspal.com"
    user_agent: str = "NGX-Agents/1.0"


@dataclass
class MFPFood:
    """MyFitnessPal food item"""

    food_id: str
    brand_name: Optional[str]
    food_name: str
    serving_size: str
    serving_qty: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    cholesterol_mg: Optional[float] = None


@dataclass
class MFPMeal:
    """MyFitnessPal meal entry"""

    meal_id: str
    meal_name: str  # breakfast, lunch, dinner, snacks
    date: date
    foods: List[MFPFood]
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float


@dataclass
class MFPDailyNutrition:
    """Daily nutrition summary from MyFitnessPal"""

    date: date
    user_id: str
    meals: List[MFPMeal]
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: Optional[float] = None
    total_sugar_g: Optional[float] = None
    total_sodium_mg: Optional[float] = None
    water_cups: Optional[float] = None
    goal_calories: Optional[float] = None
    goal_protein_g: Optional[float] = None
    goal_carbs_g: Optional[float] = None
    goal_fat_g: Optional[float] = None


@dataclass
class MFPExercise:
    """MyFitnessPal exercise entry"""

    exercise_id: str
    exercise_name: str
    duration_minutes: float
    calories_burned: float
    date: date
    notes: Optional[str] = None


@dataclass
class MFPWeight:
    """MyFitnessPal weight entry"""

    date: date
    weight_kg: float
    body_fat_percent: Optional[float] = None
    notes: Optional[str] = None


class MyFitnessPalAdapter:
    """
    MyFitnessPal API adapter for NGX Agents
    Handles authentication and data retrieval
    """

    def __init__(self, config: MFPConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self._auth_cookies: Optional[Dict[str, str]] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def authenticate(self) -> bool:
        """
        Authenticate with MyFitnessPal using username/password

        Returns:
            True if authentication successful
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use as async context manager.")

        # Login endpoint
        login_url = f"{self.config.web_url}/account/login"

        # Get CSRF token first
        async with self.session.get(login_url) as response:
            if response.status != 200:
                raise Exception(f"Failed to get login page: {response.status}")

            # Extract CSRF token from response
            # This is a simplified version - real implementation would parse HTML
            csrf_token = "dummy_csrf_token"

        # Login data
        login_data = {
            "username": self.config.username,
            "password": self.config.password,
            "csrf_token": csrf_token,
            "remember_me": "true",
        }

        # Perform login
        async with self.session.post(
            f"{self.config.web_url}/account/login",
            data=login_data,
            allow_redirects=False,
        ) as response:
            if response.status not in [200, 302]:
                raise Exception(f"Login failed: {response.status}")

            # Store cookies
            self._auth_cookies = {
                cookie.key: cookie.value for cookie in response.cookies.values()
            }

            # Extract user ID from cookies or response
            self.user_id = self._extract_user_id(response)

            logger.info(
                f"Successfully authenticated with MyFitnessPal for user {self.config.username}"
            )
            return True

    def _extract_user_id(self, response) -> str:
        """Extract user ID from login response"""
        # This would parse the actual response to get user ID
        # For now, return a placeholder
        return f"mfp_{self.config.username}"

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Dict[str, Any] = None,
        data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated API request

        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data: Request body data

        Returns:
            API response data
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use as async context manager.")

        if not self._auth_cookies:
            await self.authenticate()

        url = f"{self.config.base_url}{endpoint}"

        # Add auth cookies to headers
        headers = {
            "Cookie": "; ".join([f"{k}={v}" for k, v in self._auth_cookies.items()])
        }

        async with self.session.request(
            method, url, headers=headers, params=params, json=data
        ) as response:
            if response.status == 401:
                # Try to re-authenticate
                logger.info("Session expired, re-authenticating...")
                await self.authenticate()

                # Retry request
                headers["Cookie"] = "; ".join(
                    [f"{k}={v}" for k, v in self._auth_cookies.items()]
                )
                async with self.session.request(
                    method, url, headers=headers, params=params, json=data
                ) as retry_response:
                    if retry_response.status != 200:
                        error_text = await retry_response.text()
                        raise Exception(
                            f"API request failed after re-auth: {retry_response.status} - {error_text}"
                        )
                    return await retry_response.json()

            elif response.status != 200:
                error_text = await response.text()
                raise Exception(f"API request failed: {response.status} - {error_text}")

            return await response.json()

    async def get_daily_nutrition(self, target_date: date = None) -> MFPDailyNutrition:
        """
        Get daily nutrition data for a specific date

        Args:
            target_date: Date to retrieve (defaults to today)

        Returns:
            Daily nutrition summary
        """
        if target_date is None:
            target_date = date.today()

        # Format date for API
        date_str = target_date.strftime("%Y-%m-%d")

        # Get food diary for the date
        diary_data = await self._make_request(
            f"/v2/diary/{self.user_id}", params={"date": date_str}
        )

        meals = []
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        total_fiber = 0
        total_sugar = 0
        total_sodium = 0

        # Parse each meal
        for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
            if meal_type in diary_data:
                meal_foods = []
                meal_calories = 0
                meal_protein = 0
                meal_carbs = 0
                meal_fat = 0

                for food_entry in diary_data[meal_type]:
                    food = MFPFood(
                        food_id=str(food_entry.get("id", "")),
                        brand_name=food_entry.get("brand_name"),
                        food_name=food_entry.get("food_name", ""),
                        serving_size=food_entry.get("serving_size", ""),
                        serving_qty=float(food_entry.get("serving_qty", 1)),
                        calories=float(food_entry.get("calories", 0)),
                        protein_g=float(food_entry.get("protein", 0)),
                        carbs_g=float(food_entry.get("carbohydrates", 0)),
                        fat_g=float(food_entry.get("fat", 0)),
                        fiber_g=(
                            float(food_entry.get("fiber", 0))
                            if food_entry.get("fiber")
                            else None
                        ),
                        sugar_g=(
                            float(food_entry.get("sugar", 0))
                            if food_entry.get("sugar")
                            else None
                        ),
                        sodium_mg=(
                            float(food_entry.get("sodium", 0))
                            if food_entry.get("sodium")
                            else None
                        ),
                        cholesterol_mg=(
                            float(food_entry.get("cholesterol", 0))
                            if food_entry.get("cholesterol")
                            else None
                        ),
                    )
                    meal_foods.append(food)

                    # Add to meal totals
                    meal_calories += food.calories
                    meal_protein += food.protein_g
                    meal_carbs += food.carbs_g
                    meal_fat += food.fat_g

                    # Add to daily totals
                    total_calories += food.calories
                    total_protein += food.protein_g
                    total_carbs += food.carbs_g
                    total_fat += food.fat_g
                    if food.fiber_g:
                        total_fiber += food.fiber_g
                    if food.sugar_g:
                        total_sugar += food.sugar_g
                    if food.sodium_mg:
                        total_sodium += food.sodium_mg

                meal = MFPMeal(
                    meal_id=f"{date_str}_{meal_type}",
                    meal_name=meal_type,
                    date=target_date,
                    foods=meal_foods,
                    total_calories=meal_calories,
                    total_protein_g=meal_protein,
                    total_carbs_g=meal_carbs,
                    total_fat_g=meal_fat,
                )
                meals.append(meal)

        # Get goals if available
        goals = diary_data.get("goals", {})

        return MFPDailyNutrition(
            date=target_date,
            user_id=self.user_id,
            meals=meals,
            total_calories=total_calories,
            total_protein_g=total_protein,
            total_carbs_g=total_carbs,
            total_fat_g=total_fat,
            total_fiber_g=total_fiber if total_fiber > 0 else None,
            total_sugar_g=total_sugar if total_sugar > 0 else None,
            total_sodium_mg=total_sodium if total_sodium > 0 else None,
            water_cups=diary_data.get("water_cups"),
            goal_calories=goals.get("calories"),
            goal_protein_g=goals.get("protein"),
            goal_carbs_g=goals.get("carbohydrates"),
            goal_fat_g=goals.get("fat"),
        )

    async def get_nutrition_history(
        self, start_date: date, end_date: date = None
    ) -> List[MFPDailyNutrition]:
        """
        Get nutrition history for a date range

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            List of daily nutrition summaries
        """
        if end_date is None:
            end_date = date.today()

        nutrition_history = []
        current_date = start_date

        while current_date <= end_date:
            try:
                daily_nutrition = await self.get_daily_nutrition(current_date)
                nutrition_history.append(daily_nutrition)
            except Exception as e:
                logger.error(f"Failed to get nutrition for {current_date}: {str(e)}")

            current_date += timedelta(days=1)

            # Add small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        return nutrition_history

    async def log_food(
        self,
        food_name: str,
        meal_type: str,
        servings: float = 1.0,
        target_date: date = None,
    ) -> bool:
        """
        Log a food item to diary

        Args:
            food_name: Name of food to log
            meal_type: Meal type (breakfast, lunch, dinner, snacks)
            servings: Number of servings
            target_date: Date to log (defaults to today)

        Returns:
            True if successful
        """
        if target_date is None:
            target_date = date.today()

        # Search for food
        search_results = await self._make_request(
            "/v2/foods/search", params={"q": food_name, "limit": 1}
        )

        if not search_results or not search_results.get("items"):
            raise ValueError(f"Food '{food_name}' not found")

        food_item = search_results["items"][0]

        # Log the food
        log_data = {
            "food_id": food_item["id"],
            "meal_type": meal_type,
            "servings": servings,
            "date": target_date.strftime("%Y-%m-%d"),
        }

        await self._make_request(
            f"/v2/diary/{self.user_id}/log", method="POST", data=log_data
        )

        logger.info(
            f"Successfully logged {servings} servings of {food_name} to {meal_type}"
        )
        return True

    async def get_weight_history(
        self, start_date: date = None, end_date: date = None
    ) -> List[MFPWeight]:
        """
        Get weight tracking history

        Args:
            start_date: Start date (defaults to 30 days ago)
            end_date: End date (defaults to today)

        Returns:
            List of weight entries
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        params = {
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
        }

        weight_data = await self._make_request(
            f"/v2/measurements/{self.user_id}/weight", params=params
        )

        weights = []
        for entry in weight_data.get("measurements", []):
            weight = MFPWeight(
                date=datetime.fromisoformat(entry["date"]).date(),
                weight_kg=(
                    float(entry["weight"]) * 0.453592
                    if entry.get("unit") == "lbs"
                    else float(entry["weight"])
                ),
                body_fat_percent=(
                    float(entry["body_fat"]) if entry.get("body_fat") else None
                ),
                notes=entry.get("notes"),
            )
            weights.append(weight)

        return weights

    async def get_exercise_log(self, target_date: date = None) -> List[MFPExercise]:
        """
        Get exercise log for a specific date

        Args:
            target_date: Date to retrieve (defaults to today)

        Returns:
            List of exercise entries
        """
        if target_date is None:
            target_date = date.today()

        date_str = target_date.strftime("%Y-%m-%d")

        exercise_data = await self._make_request(
            f"/v2/exercise/{self.user_id}", params={"date": date_str}
        )

        exercises = []
        for entry in exercise_data.get("exercises", []):
            exercise = MFPExercise(
                exercise_id=str(entry.get("id", "")),
                exercise_name=entry.get("name", ""),
                duration_minutes=float(entry.get("duration", 0)),
                calories_burned=float(entry.get("calories", 0)),
                date=target_date,
                notes=entry.get("notes"),
            )
            exercises.append(exercise)

        return exercises

    async def search_foods(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for foods in MyFitnessPal database

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of food items
        """
        search_results = await self._make_request(
            "/v2/foods/search", params={"q": query, "limit": limit}
        )

        return search_results.get("items", [])


# Example usage
async def example_usage():
    """Example of how to use the MyFitnessPal adapter"""
    config = MFPConfig(username="your_username", password="your_password")

    async with MyFitnessPalAdapter(config) as mfp:
        # Authenticate
        await mfp.authenticate()

        # Get today's nutrition
        today_nutrition = await mfp.get_daily_nutrition()
        print(f"Today's calories: {today_nutrition.total_calories}")
        print(f"Protein: {today_nutrition.total_protein_g}g")
        print(f"Carbs: {today_nutrition.total_carbs_g}g")
        print(f"Fat: {today_nutrition.total_fat_g}g")

        # Get nutrition history
        start_date = date.today() - timedelta(days=7)
        history = await mfp.get_nutrition_history(start_date)
        print(f"Retrieved {len(history)} days of nutrition data")

        # Search for food
        # search_results = await mfp.search_foods("apple")
        # print(f"Found {len(search_results)} results for 'apple'")


if __name__ == "__main__":
    asyncio.run(example_usage())

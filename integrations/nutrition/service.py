"""
Nutrition Integration Service
Central service for managing nutrition tracking integrations in NGX Agents
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import json

from .adapters.myfitnesspal import (
    MyFitnessPalAdapter,
    MFPConfig,
    MFPDailyNutrition,
    MFPWeight,
    MFPExercise,
    MFPFood,
)
from .normalizer import (
    NutritionDataNormalizer,
    NutritionSource,
    NormalizedDailyNutrition,
    NormalizedWeightData,
    NormalizedNutritionMetric,
)

logger = logging.getLogger(__name__)


@dataclass
class NutritionConnection:
    """Represents a user's connection to a nutrition tracking platform"""

    user_id: str
    source: NutritionSource
    platform_user_id: str
    username: str
    password: Optional[str] = None  # Encrypted
    api_key: Optional[str] = None
    is_active: bool = True
    last_sync: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class NutritionSyncResult:
    """Result of a nutrition data synchronization"""

    success: bool
    source: NutritionSource
    user_id: str
    days_synced: int
    meals_synced: int = 0
    foods_synced: int = 0
    weights_synced: int = 0
    exercises_synced: int = 0
    error_message: Optional[str] = None
    sync_timestamp: datetime = None

    def __post_init__(self):
        if self.sync_timestamp is None:
            self.sync_timestamp = datetime.utcnow()


class NutritionIntegrationService:
    """
    Central service for managing nutrition tracking integrations
    Handles authentication, data synchronization, and normalization
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the nutrition integration service

        Args:
            config: Configuration dict containing platform credentials
        """
        self.config = config
        self.normalizer = NutritionDataNormalizer()
        self.active_connections: Dict[str, NutritionConnection] = {}
        self.platform_adapters: Dict[NutritionSource, Any] = {}

        # Initialize platform adapters
        self._initialize_adapters()

    def _initialize_adapters(self):
        """Initialize adapters for supported platforms"""
        # Initialize MyFitnessPal adapter if configured
        if "myfitnesspal" in self.config:
            # Store config for creating user-specific adapters
            self.platform_adapters[NutritionSource.MYFITNESSPAL] = self.config[
                "myfitnesspal"
            ]
            logger.info("MyFitnessPal adapter configuration loaded")

        # TODO: Initialize other platform adapters (Cronometer, LoseIt, etc.)

    async def connect_platform(
        self, user_id: str, source: NutritionSource, credentials: Dict[str, str]
    ) -> NutritionConnection:
        """
        Connect a user to a nutrition tracking platform

        Args:
            user_id: NGX user ID
            source: Nutrition platform
            credentials: Platform-specific credentials (username, password, api_key, etc.)

        Returns:
            Nutrition connection information
        """
        if source == NutritionSource.MYFITNESSPAL:
            # Create user-specific MFP config
            mfp_config = MFPConfig(
                username=credentials["username"],
                password=credentials["password"],  # Should be encrypted in production
            )

            # Test authentication
            async with MyFitnessPalAdapter(mfp_config) as mfp:
                success = await mfp.authenticate()
                if not success:
                    raise ValueError("Failed to authenticate with MyFitnessPal")

                platform_user_id = mfp.user_id

            # Create connection
            connection = NutritionConnection(
                user_id=user_id,
                source=source,
                platform_user_id=platform_user_id,
                username=credentials["username"],
                password=credentials["password"],  # Should be encrypted
            )

            # Store connection
            connection_key = f"{user_id}:{source.value}"
            self.active_connections[connection_key] = connection

            logger.info(f"Successfully connected {source.value} for user {user_id}")
            return connection
        else:
            raise ValueError(f"Unsupported nutrition platform: {source}")

    async def sync_nutrition_data(
        self,
        user_id: str,
        source: NutritionSource,
        days_back: int = 7,
        force_refresh: bool = False,
    ) -> NutritionSyncResult:
        """
        Synchronize nutrition data for a user from a specific platform

        Args:
            user_id: NGX user ID
            source: Nutrition platform to sync from
            days_back: Number of days of historical data to sync
            force_refresh: Force refresh even if recently synced

        Returns:
            Synchronization result
        """
        connection_key = f"{user_id}:{source.value}"
        connection = self.active_connections.get(connection_key)

        if not connection or not connection.is_active:
            return NutritionSyncResult(
                success=False,
                source=source,
                user_id=user_id,
                days_synced=0,
                error_message="No active connection found for platform",
            )

        try:
            if source == NutritionSource.MYFITNESSPAL:
                return await self._sync_mfp_data(connection, days_back, force_refresh)
            else:
                return NutritionSyncResult(
                    success=False,
                    source=source,
                    user_id=user_id,
                    days_synced=0,
                    error_message=f"Sync not implemented for {source.value}",
                )
        except Exception as e:
            logger.error(
                f"Error syncing {source.value} data for user {user_id}: {str(e)}"
            )
            return NutritionSyncResult(
                success=False,
                source=source,
                user_id=user_id,
                days_synced=0,
                error_message=str(e),
            )

    async def _sync_mfp_data(
        self, connection: NutritionConnection, days_back: int, force_refresh: bool
    ) -> NutritionSyncResult:
        """Sync data specifically from MyFitnessPal"""
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # If not forcing refresh, only sync since last sync
        if not force_refresh and connection.last_sync:
            sync_date = connection.last_sync.date()
            start_date = max(start_date, sync_date)

        days_synced = 0
        meals_synced = 0
        foods_synced = 0
        weights_synced = 0

        # Create MFP adapter
        mfp_config = MFPConfig(
            username=connection.username,
            password=connection.password,  # Should be decrypted
        )

        async with MyFitnessPalAdapter(mfp_config) as mfp:
            # Authenticate
            await mfp.authenticate()

            # Sync nutrition history
            nutrition_history = await mfp.get_nutrition_history(start_date, end_date)

            for daily_nutrition in nutrition_history:
                # Normalize the data
                normalized_daily = self.normalizer.normalize_daily_nutrition(
                    NutritionSource.MYFITNESSPAL, daily_nutrition
                )

                # Convert to metrics
                metrics = self.normalizer.nutrition_to_metrics(
                    NutritionSource.MYFITNESSPAL, daily_nutrition, "daily"
                )

                # Store normalized data
                await self._store_daily_nutrition(connection.user_id, normalized_daily)
                await self._store_nutrition_metrics(connection.user_id, metrics)

                days_synced += 1
                meals_synced += len(daily_nutrition.meals)
                foods_synced += sum(len(meal.foods) for meal in daily_nutrition.meals)

            # Sync weight history
            try:
                weight_history = await mfp.get_weight_history(start_date, end_date)
                for weight in weight_history:
                    normalized_weight = self.normalizer.normalize_weight_data(
                        NutritionSource.MYFITNESSPAL, weight
                    )
                    await self._store_weight_data(connection.user_id, normalized_weight)
                    weights_synced += 1
            except Exception as e:
                logger.warning(f"Failed to sync weight data: {str(e)}")

            # Update last sync time
            connection.last_sync = datetime.utcnow()
            connection.updated_at = datetime.utcnow()

            logger.info(
                f"Successfully synced MyFitnessPal data for user {connection.user_id}: "
                f"{days_synced} days, {meals_synced} meals, {foods_synced} foods"
            )

            return NutritionSyncResult(
                success=True,
                source=NutritionSource.MYFITNESSPAL,
                user_id=connection.user_id,
                days_synced=days_synced,
                meals_synced=meals_synced,
                foods_synced=foods_synced,
                weights_synced=weights_synced,
            )

    async def get_daily_nutrition(
        self, user_id: str, target_date: date = None
    ) -> Optional[NormalizedDailyNutrition]:
        """
        Get daily nutrition data for a user

        Args:
            user_id: NGX user ID
            target_date: Date to retrieve (defaults to today)

        Returns:
            Normalized daily nutrition data
        """
        if target_date is None:
            target_date = date.today()

        # Try to get from cache/database first
        cached_data = await self._get_cached_daily_nutrition(user_id, target_date)
        if cached_data:
            return cached_data

        # If not cached, try to sync from connected platforms
        for connection_key, connection in self.active_connections.items():
            if connection.user_id == user_id and connection.is_active:
                try:
                    # Sync just this day
                    await self.sync_nutrition_data(
                        user_id, connection.source, days_back=1, force_refresh=True
                    )

                    # Try to get from cache again
                    return await self._get_cached_daily_nutrition(user_id, target_date)
                except Exception as e:
                    logger.error(f"Failed to sync {connection.source.value}: {str(e)}")

        return None

    async def log_food(
        self,
        user_id: str,
        food_name: str,
        meal_type: str,
        servings: float = 1.0,
        source: NutritionSource = None,
    ) -> bool:
        """
        Log a food item to the user's diary

        Args:
            user_id: NGX user ID
            food_name: Name of food to log
            meal_type: Meal type (breakfast, lunch, dinner, snacks)
            servings: Number of servings
            source: Specific platform to log to (or log to all)

        Returns:
            True if successfully logged
        """
        success = False

        # Get user's connections
        user_connections = [
            conn
            for conn in self.active_connections.values()
            if conn.user_id == user_id and conn.is_active
        ]

        # Filter by source if specified
        if source:
            user_connections = [
                conn for conn in user_connections if conn.source == source
            ]

        # Log to each connected platform
        for connection in user_connections:
            try:
                if connection.source == NutritionSource.MYFITNESSPAL:
                    mfp_config = MFPConfig(
                        username=connection.username, password=connection.password
                    )

                    async with MyFitnessPalAdapter(mfp_config) as mfp:
                        await mfp.authenticate()
                        await mfp.log_food(food_name, meal_type, servings)
                        success = True
                        logger.info(
                            f"Logged {food_name} to MyFitnessPal for user {user_id}"
                        )
            except Exception as e:
                logger.error(
                    f"Failed to log food to {connection.source.value}: {str(e)}"
                )

        return success

    async def search_foods(
        self,
        query: str,
        source: NutritionSource = NutritionSource.MYFITNESSPAL,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for foods across nutrition databases

        Args:
            query: Search query
            source: Platform to search (defaults to MyFitnessPal)
            limit: Maximum results

        Returns:
            List of food items
        """
        if source == NutritionSource.MYFITNESSPAL:
            # Use a generic connection for searching
            if NutritionSource.MYFITNESSPAL in self.platform_adapters:
                # Get any active MFP connection for searching
                mfp_connection = next(
                    (
                        conn
                        for conn in self.active_connections.values()
                        if conn.source == NutritionSource.MYFITNESSPAL
                        and conn.is_active
                    ),
                    None,
                )

                if mfp_connection:
                    mfp_config = MFPConfig(
                        username=mfp_connection.username,
                        password=mfp_connection.password,
                    )

                    async with MyFitnessPalAdapter(mfp_config) as mfp:
                        await mfp.authenticate()
                        return await mfp.search_foods(query, limit)

        return []

    async def get_nutrition_trends(
        self, user_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get nutrition trends and analytics for a user

        Args:
            user_id: NGX user ID
            days: Number of days to analyze

        Returns:
            Nutrition trends and insights
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get nutrition history from cache/database
        daily_data = await self._get_nutrition_history(user_id, start_date, end_date)

        if not daily_data:
            return {
                "error": "No nutrition data available for analysis",
                "days_analyzed": 0,
            }

        # Calculate trends
        total_days = len(daily_data)
        avg_calories = sum(d.total_calories for d in daily_data) / total_days
        avg_protein = sum(d.total_protein_g for d in daily_data) / total_days
        avg_carbs = sum(d.total_carbs_g for d in daily_data) / total_days
        avg_fat = sum(d.total_fat_g for d in daily_data) / total_days

        # Goal adherence
        days_with_goals = [d for d in daily_data if d.calorie_goal]
        avg_adherence = None
        if days_with_goals:
            avg_adherence = sum(
                d.goal_adherence_percent or 0 for d in days_with_goals
            ) / len(days_with_goals)

        # Macro balance trends
        macro_balances = [d.macro_balance for d in daily_data if d.macro_balance]
        avg_macro_balance = None
        if macro_balances:
            avg_macro_balance = {
                "protein_percent": sum(m["protein_percent"] for m in macro_balances)
                / len(macro_balances),
                "carbs_percent": sum(m["carbs_percent"] for m in macro_balances)
                / len(macro_balances),
                "fat_percent": sum(m["fat_percent"] for m in macro_balances)
                / len(macro_balances),
            }

        return {
            "days_analyzed": total_days,
            "average_daily_calories": round(avg_calories, 1),
            "average_daily_protein_g": round(avg_protein, 1),
            "average_daily_carbs_g": round(avg_carbs, 1),
            "average_daily_fat_g": round(avg_fat, 1),
            "average_goal_adherence_percent": (
                round(avg_adherence, 1) if avg_adherence else None
            ),
            "average_macro_balance": avg_macro_balance,
            "calorie_trend": self._calculate_trend(
                [d.total_calories for d in daily_data]
            ),
            "protein_trend": self._calculate_trend(
                [d.total_protein_g for d in daily_data]
            ),
            "insights": self._generate_nutrition_insights(daily_data),
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values"""
        if len(values) < 2:
            return "stable"

        # Simple linear regression
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Determine trend based on slope
        if slope > 0.5:
            return "increasing"
        elif slope < -0.5:
            return "decreasing"
        else:
            return "stable"

    def _generate_nutrition_insights(
        self, daily_data: List[NormalizedDailyNutrition]
    ) -> List[str]:
        """Generate insights from nutrition data"""
        insights = []

        if not daily_data:
            return insights

        # Calorie consistency
        calories = [d.total_calories for d in daily_data]
        calorie_std = self._calculate_std_dev(calories)
        if calorie_std > 500:
            insights.append(
                "Your daily calorie intake varies significantly. Consider more consistent eating patterns."
            )

        # Protein intake
        avg_protein = sum(d.total_protein_g for d in daily_data) / len(daily_data)
        if avg_protein < 50:
            insights.append(
                "Your protein intake is below recommended levels. Consider adding more protein sources."
            )
        elif avg_protein > 150:
            insights.append(
                "You're consuming high amounts of protein. Ensure adequate hydration."
            )

        # Macro balance
        recent_balances = [d.macro_balance for d in daily_data[-7:] if d.macro_balance]
        if recent_balances:
            avg_carb_percent = sum(b["carbs_percent"] for b in recent_balances) / len(
                recent_balances
            )
            if avg_carb_percent > 60:
                insights.append(
                    "Your diet is very high in carbohydrates. Consider balancing with more protein and healthy fats."
                )
            elif avg_carb_percent < 30:
                insights.append(
                    "You're following a low-carb diet. Ensure you're getting enough fiber and micronutrients."
                )

        return insights

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation of a list of values"""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance**0.5

    async def _store_daily_nutrition(
        self, user_id: str, daily_nutrition: NormalizedDailyNutrition
    ):
        """Store normalized daily nutrition data"""
        # TODO: Integrate with NGX storage system (Supabase)
        logger.debug(
            f"Storing daily nutrition for user {user_id} on {daily_nutrition.date}"
        )

    async def _store_nutrition_metrics(
        self, user_id: str, metrics: List[NormalizedNutritionMetric]
    ):
        """Store normalized nutrition metrics"""
        # TODO: Integrate with NGX storage system (Supabase)
        logger.debug(f"Storing {len(metrics)} nutrition metrics for user {user_id}")

    async def _store_weight_data(self, user_id: str, weight: NormalizedWeightData):
        """Store normalized weight data"""
        # TODO: Integrate with NGX storage system (Supabase)
        logger.debug(
            f"Storing weight data for user {user_id}: {weight.weight_kg}kg on {weight.date}"
        )

    async def _get_cached_daily_nutrition(
        self, user_id: str, target_date: date
    ) -> Optional[NormalizedDailyNutrition]:
        """Get cached daily nutrition data"""
        # TODO: Retrieve from NGX storage system (Supabase)
        return None

    async def _get_nutrition_history(
        self, user_id: str, start_date: date, end_date: date
    ) -> List[NormalizedDailyNutrition]:
        """Get nutrition history from cache/database"""
        # TODO: Retrieve from NGX storage system (Supabase)
        return []

    async def disconnect_platform(self, user_id: str, source: NutritionSource) -> bool:
        """
        Disconnect a nutrition platform for a user

        Args:
            user_id: NGX user ID
            source: Platform to disconnect

        Returns:
            True if successfully disconnected
        """
        connection_key = f"{user_id}:{source.value}"
        connection = self.active_connections.get(connection_key)

        if connection:
            connection.is_active = False
            connection.updated_at = datetime.utcnow()
            logger.info(f"Disconnected {source.value} for user {user_id}")
            return True

        return False

    async def get_user_connections(self, user_id: str) -> List[NutritionConnection]:
        """
        Get all nutrition platform connections for a user

        Args:
            user_id: NGX user ID

        Returns:
            List of active connections
        """
        return [
            conn
            for conn in self.active_connections.values()
            if conn.user_id == user_id and conn.is_active
        ]

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the nutrition integration service

        Returns:
            Health check status
        """
        health_status = {
            "service": "nutrition_integration",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "active_connections": len(
                [c for c in self.active_connections.values() if c.is_active]
            ),
            "supported_platforms": [source.value for source in NutritionSource],
            "platform_status": {},
        }

        # Check each platform
        for source in NutritionSource:
            if source in self.platform_adapters:
                health_status["platform_status"][source.value] = "configured"
            else:
                health_status["platform_status"][source.value] = "not configured"

        return health_status


# Example usage
async def example_service_usage():
    """Example of how to use the nutrition integration service"""

    # Configuration for the service
    config = {"myfitnesspal": {"api_endpoint": "https://api.myfitnesspal.com"}}

    # Initialize service
    service = NutritionIntegrationService(config)

    # Check health
    health = await service.health_check()
    print(f"Service health: {health}")

    # Connect a user to MyFitnessPal
    user_id = "ngx_user_123"
    credentials = {"username": "test_user", "password": "test_password"}

    try:
        # connection = await service.connect_platform(
        #     user_id,
        #     NutritionSource.MYFITNESSPAL,
        #     credentials
        # )
        # print(f"Connected to MyFitnessPal: {connection}")

        # Sync nutrition data
        # sync_result = await service.sync_nutrition_data(
        #     user_id,
        #     NutritionSource.MYFITNESSPAL,
        #     days_back=7
        # )
        # print(f"Sync result: {sync_result}")

        # Get nutrition trends
        # trends = await service.get_nutrition_trends(user_id, days=30)
        # print(f"Nutrition trends: {trends}")

        print("Nutrition integration service ready!")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(example_service_usage())

"""
Apple HealthKit Integration Adapter
Provides a bridge to receive and process Apple Health data
Since HealthKit is iOS-only, this adapter implements a REST endpoint approach
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
import hashlib
import hmac
import json

logger = logging.getLogger(__name__)


class HealthKitDataType(Enum):
    """Apple HealthKit data types we support"""

    STEPS = "HKQuantityTypeIdentifierStepCount"
    HEART_RATE = "HKQuantityTypeIdentifierHeartRate"
    HEART_RATE_VARIABILITY = "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
    RESTING_HEART_RATE = "HKQuantityTypeIdentifierRestingHeartRate"
    WALKING_HEART_RATE_AVERAGE = "HKQuantityTypeIdentifierWalkingHeartRateAverage"
    ACTIVE_ENERGY = "HKQuantityTypeIdentifierActiveEnergyBurned"
    BASAL_ENERGY = "HKQuantityTypeIdentifierBasalEnergyBurned"
    DISTANCE = "HKQuantityTypeIdentifierDistanceWalkingRunning"
    FLIGHTS_CLIMBED = "HKQuantityTypeIdentifierFlightsClimbed"
    EXERCISE_TIME = "HKQuantityTypeIdentifierAppleExerciseTime"
    STAND_TIME = "HKQuantityTypeIdentifierAppleStandTime"
    WORKOUT = "HKWorkoutType"
    SLEEP = "HKCategoryTypeIdentifierSleepAnalysis"
    MINDFUL_MINUTES = "HKCategoryTypeIdentifierMindfulSession"
    BODY_MASS = "HKQuantityTypeIdentifierBodyMass"
    BODY_FAT_PERCENTAGE = "HKQuantityTypeIdentifierBodyFatPercentage"
    HEIGHT = "HKQuantityTypeIdentifierHeight"
    BLOOD_OXYGEN = "HKQuantityTypeIdentifierOxygenSaturation"
    BODY_TEMPERATURE = "HKQuantityTypeIdentifierBodyTemperature"
    RESPIRATORY_RATE = "HKQuantityTypeIdentifierRespiratoryRate"
    VO2_MAX = "HKQuantityTypeIdentifierVO2Max"


@dataclass
class AppleHealthConfig:
    """Configuration for Apple Health integration"""

    webhook_secret: str  # For verifying webhook authenticity
    api_key: Optional[str] = None  # Optional API key for direct calls
    enable_shortcuts: bool = True  # Enable iOS Shortcuts integration
    enable_webhooks: bool = True  # Enable webhook reception


@dataclass
class HealthKitSample:
    """Generic HealthKit data sample"""

    type: HealthKitDataType
    value: float
    unit: str
    start_date: datetime
    end_date: datetime
    source_name: str = "Apple Health"
    source_version: Optional[str] = None
    device: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HealthKitWorkout:
    """HealthKit workout data"""

    activity_type: str  # Running, Cycling, etc.
    duration_minutes: float
    total_energy_burned: Optional[float] = None  # kcal
    total_distance: Optional[float] = None  # meters
    average_heart_rate: Optional[float] = None
    start_date: datetime = None
    end_date: datetime = None
    source_name: str = "Apple Health"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HealthKitSleep:
    """HealthKit sleep analysis data"""

    sleep_state: str  # InBed, Asleep, Awake
    start_date: datetime
    end_date: datetime
    duration_minutes: float
    source_name: str = "Apple Health"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HealthKitActivity:
    """Daily activity summary from HealthKit"""

    date: datetime
    active_energy_burned: Optional[float] = None  # kcal
    basal_energy_burned: Optional[float] = None  # kcal
    steps: Optional[int] = None
    distance: Optional[float] = None  # meters
    flights_climbed: Optional[int] = None
    exercise_minutes: Optional[float] = None
    stand_hours: Optional[float] = None
    move_goal: Optional[float] = None
    exercise_goal: Optional[float] = None
    stand_goal: Optional[float] = None


class AppleHealthAdapter:
    """
    Apple HealthKit adapter for NGX Agents

    Since HealthKit is iOS-only, this adapter provides:
    1. REST endpoints to receive data from iOS Shortcuts
    2. Webhook support for third-party HealthKit sync services
    3. Data validation and normalization
    """

    def __init__(self, config: AppleHealthConfig):
        self.config = config
        self.supported_types = list(HealthKitDataType)

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature for security

        Args:
            payload: Raw webhook payload
            signature: Signature from webhook header

        Returns:
            True if signature is valid
        """
        expected_sig = hmac.new(
            self.config.webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_sig, signature)

    def parse_healthkit_data(
        self, data: Dict[str, Any]
    ) -> List[Union[HealthKitSample, HealthKitWorkout, HealthKitSleep]]:
        """
        Parse incoming HealthKit data from various sources

        Args:
            data: Raw data dictionary from iOS Shortcuts or webhooks

        Returns:
            List of parsed HealthKit objects
        """
        parsed_items = []

        # Handle different data formats
        if "samples" in data:
            # Format from iOS Shortcuts
            for sample in data["samples"]:
                parsed_item = self._parse_sample(sample)
                if parsed_item:
                    parsed_items.append(parsed_item)

        elif "workouts" in data:
            # Workout data
            for workout in data["workouts"]:
                parsed_item = self._parse_workout(workout)
                if parsed_item:
                    parsed_items.append(parsed_item)

        elif "sleep" in data:
            # Sleep data
            for sleep in data["sleep"]:
                parsed_item = self._parse_sleep(sleep)
                if parsed_item:
                    parsed_items.append(parsed_item)

        elif "type" in data:
            # Single sample format
            parsed_item = self._parse_sample(data)
            if parsed_item:
                parsed_items.append(parsed_item)

        return parsed_items

    def _parse_sample(self, sample: Dict[str, Any]) -> Optional[HealthKitSample]:
        """Parse a single HealthKit sample"""
        try:
            # Map string type to enum
            type_str = sample.get("type", "")
            data_type = None

            for hk_type in HealthKitDataType:
                if (
                    hk_type.value == type_str
                    or hk_type.name.lower() == type_str.lower()
                ):
                    data_type = hk_type
                    break

            if not data_type:
                logger.warning(f"Unknown HealthKit type: {type_str}")
                return None

            # Parse dates
            start_date = self._parse_date(sample.get("startDate"))
            end_date = self._parse_date(sample.get("endDate", sample.get("startDate")))

            return HealthKitSample(
                type=data_type,
                value=float(sample.get("value", 0)),
                unit=sample.get("unit", "count"),
                start_date=start_date,
                end_date=end_date,
                source_name=sample.get("sourceName", "Apple Health"),
                source_version=sample.get("sourceVersion"),
                device=sample.get("device"),
                metadata=sample.get("metadata"),
            )

        except Exception as e:
            logger.error(f"Error parsing HealthKit sample: {e}")
            return None

    def _parse_workout(self, workout: Dict[str, Any]) -> Optional[HealthKitWorkout]:
        """Parse workout data"""
        try:
            start_date = self._parse_date(workout.get("startDate"))
            end_date = self._parse_date(workout.get("endDate"))

            # Calculate duration
            if start_date and end_date:
                duration_minutes = (end_date - start_date).total_seconds() / 60
            else:
                duration_minutes = float(workout.get("duration", 0))

            return HealthKitWorkout(
                activity_type=workout.get("activityType", "Unknown"),
                duration_minutes=duration_minutes,
                total_energy_burned=workout.get("totalEnergyBurned"),
                total_distance=workout.get("totalDistance"),
                average_heart_rate=workout.get("averageHeartRate"),
                start_date=start_date,
                end_date=end_date,
                source_name=workout.get("sourceName", "Apple Health"),
                metadata=workout.get("metadata"),
            )

        except Exception as e:
            logger.error(f"Error parsing workout: {e}")
            return None

    def _parse_sleep(self, sleep: Dict[str, Any]) -> Optional[HealthKitSleep]:
        """Parse sleep data"""
        try:
            start_date = self._parse_date(sleep.get("startDate"))
            end_date = self._parse_date(sleep.get("endDate"))

            # Calculate duration
            if start_date and end_date:
                duration_minutes = (end_date - start_date).total_seconds() / 60
            else:
                duration_minutes = float(sleep.get("duration", 0))

            return HealthKitSleep(
                sleep_state=sleep.get("value", "InBed"),
                start_date=start_date,
                end_date=end_date,
                duration_minutes=duration_minutes,
                source_name=sleep.get("sourceName", "Apple Health"),
                metadata=sleep.get("metadata"),
            )

        except Exception as e:
            logger.error(f"Error parsing sleep data: {e}")
            return None

    def _parse_date(self, date_str: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse date from various formats"""
        if isinstance(date_str, datetime):
            return date_str

        if not date_str:
            return None

        # Try different date formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def aggregate_daily_activity(
        self, samples: List[HealthKitSample], date: datetime
    ) -> HealthKitActivity:
        """
        Aggregate samples into daily activity summary

        Args:
            samples: List of HealthKit samples for a day
            date: The date to aggregate for

        Returns:
            Daily activity summary
        """
        activity = HealthKitActivity(date=date.date())

        for sample in samples:
            if sample.start_date.date() != date.date():
                continue

            if sample.type == HealthKitDataType.STEPS:
                activity.steps = (activity.steps or 0) + int(sample.value)
            elif sample.type == HealthKitDataType.ACTIVE_ENERGY:
                activity.active_energy_burned = (
                    activity.active_energy_burned or 0
                ) + sample.value
            elif sample.type == HealthKitDataType.BASAL_ENERGY:
                activity.basal_energy_burned = (
                    activity.basal_energy_burned or 0
                ) + sample.value
            elif sample.type == HealthKitDataType.DISTANCE:
                activity.distance = (activity.distance or 0) + sample.value
            elif sample.type == HealthKitDataType.FLIGHTS_CLIMBED:
                activity.flights_climbed = (activity.flights_climbed or 0) + int(
                    sample.value
                )
            elif sample.type == HealthKitDataType.EXERCISE_TIME:
                activity.exercise_minutes = (
                    activity.exercise_minutes or 0
                ) + sample.value
            elif sample.type == HealthKitDataType.STAND_TIME:
                activity.stand_hours = (activity.stand_hours or 0) + sample.value

        return activity

    def get_latest_metrics(self, samples: List[HealthKitSample]) -> Dict[str, Any]:
        """
        Get latest value for each metric type

        Args:
            samples: List of HealthKit samples

        Returns:
            Dictionary of latest metrics by type
        """
        latest_metrics = {}

        # Sort samples by date
        sorted_samples = sorted(samples, key=lambda x: x.start_date, reverse=True)

        for sample in sorted_samples:
            metric_key = sample.type.name.lower()
            if metric_key not in latest_metrics:
                latest_metrics[metric_key] = {
                    "value": sample.value,
                    "unit": sample.unit,
                    "timestamp": sample.start_date,
                    "source": sample.source_name,
                }

        return latest_metrics

    def create_shortcut_webhook_url(self, user_id: str, base_url: str) -> str:
        """
        Create a webhook URL for iOS Shortcuts

        Args:
            user_id: NGX user ID
            base_url: Base URL of the API

        Returns:
            Webhook URL for iOS Shortcuts configuration
        """
        # Generate a simple token for the user
        token = hashlib.sha256(
            f"{user_id}:{self.config.webhook_secret}".encode()
        ).hexdigest()[:16]

        return f"{base_url}/wearables/webhooks/apple-health/{user_id}/{token}"

    def generate_shortcut_instructions(self, webhook_url: str) -> Dict[str, Any]:
        """
        Generate instructions for setting up iOS Shortcuts

        Args:
            webhook_url: The webhook URL for this user

        Returns:
            Instructions and shortcut configuration
        """
        return {
            "instructions": [
                "Open the Shortcuts app on your iPhone",
                "Create a new Automation (not Shortcut)",
                "Choose 'Time of Day' trigger",
                "Set it to run daily at your preferred time",
                "Add these actions:",
                "1. Find Health Samples Where (Type is Steps, Start Date is Today)",
                "2. Get Contents of URL (POST to webhook URL)",
                "3. Set the body to the health samples as JSON",
                "Enable 'Run Without Asking'",
                "Repeat for other health metrics you want to sync",
            ],
            "webhook_url": webhook_url,
            "example_shortcut": {
                "name": "Sync Health to NGX",
                "trigger": "Daily at 11:00 PM",
                "actions": [
                    {
                        "action": "Find Health Samples",
                        "parameters": {
                            "Type": "Steps",
                            "Start Date": "Beginning of Today",
                            "End Date": "End of Today",
                        },
                    },
                    {
                        "action": "Get Contents of URL",
                        "parameters": {
                            "URL": webhook_url,
                            "Method": "POST",
                            "Headers": {"Content-Type": "application/json"},
                            "Body": "Health Samples (as JSON)",
                        },
                    },
                ],
            },
            "supported_metrics": [
                {"type": "Steps", "description": "Daily step count"},
                {"type": "Heart Rate", "description": "Heart rate measurements"},
                {"type": "Active Energy", "description": "Calories burned"},
                {"type": "Exercise Time", "description": "Workout minutes"},
                {"type": "Sleep Analysis", "description": "Sleep tracking"},
                {"type": "Heart Rate Variability", "description": "HRV measurements"},
            ],
        }

    def validate_data_freshness(
        self, samples: List[HealthKitSample], max_age_hours: int = 48
    ) -> List[HealthKitSample]:
        """
        Filter samples to only include recent data

        Args:
            samples: List of HealthKit samples
            max_age_hours: Maximum age of data in hours

        Returns:
            Filtered list of recent samples
        """
        cutoff_date = datetime.utcnow() - timedelta(hours=max_age_hours)

        fresh_samples = [
            sample for sample in samples if sample.start_date >= cutoff_date
        ]

        if len(fresh_samples) < len(samples):
            logger.info(f"Filtered out {len(samples) - len(fresh_samples)} old samples")

        return fresh_samples


# Activity type mapping from HealthKit to standard names
ACTIVITY_TYPE_MAPPING = {
    "HKWorkoutActivityTypeRunning": "Running",
    "HKWorkoutActivityTypeWalking": "Walking",
    "HKWorkoutActivityTypeCycling": "Cycling",
    "HKWorkoutActivityTypeSwimming": "Swimming",
    "HKWorkoutActivityTypeYoga": "Yoga",
    "HKWorkoutActivityTypeStrengthTraining": "Strength Training",
    "HKWorkoutActivityTypeFunctionalStrengthTraining": "Functional Training",
    "HKWorkoutActivityTypeCoreTraining": "Core Training",
    "HKWorkoutActivityTypeElliptical": "Elliptical",
    "HKWorkoutActivityTypeRowing": "Rowing",
    "HKWorkoutActivityTypeStairClimbing": "Stair Climbing",
    "HKWorkoutActivityTypeHighIntensityIntervalTraining": "HIIT",
    "HKWorkoutActivityTypePilates": "Pilates",
    "HKWorkoutActivityTypeDance": "Dance",
    "HKWorkoutActivityTypeMartialArts": "Martial Arts",
    "HKWorkoutActivityTypeMindAndBody": "Mind & Body",
    "HKWorkoutActivityTypeSports": "Sports",
    "HKWorkoutActivityTypeOther": "Other",
}


def map_activity_type(hk_activity_type: str) -> str:
    """Map HealthKit activity type to standard name"""
    return ACTIVITY_TYPE_MAPPING.get(hk_activity_type, hk_activity_type)


# Example usage
def example_usage():
    """Example of how to use the Apple Health adapter"""

    config = AppleHealthConfig(webhook_secret="your_webhook_secret")

    adapter = AppleHealthAdapter(config)

    # Example data from iOS Shortcuts
    sample_data = {
        "samples": [
            {
                "type": "HKQuantityTypeIdentifierStepCount",
                "value": 8500,
                "unit": "count",
                "startDate": "2025-05-26T00:00:00Z",
                "endDate": "2025-05-26T23:59:59Z",
                "sourceName": "iPhone",
            },
            {
                "type": "HKQuantityTypeIdentifierHeartRate",
                "value": 72,
                "unit": "count/min",
                "startDate": "2025-05-26T08:00:00Z",
                "endDate": "2025-05-26T08:00:00Z",
                "sourceName": "Apple Watch",
            },
        ]
    }

    # Parse the data
    parsed_items = adapter.parse_healthkit_data(sample_data)

    for item in parsed_items:
        print(f"Type: {item.type.name}, Value: {item.value} {item.unit}")

    # Generate webhook URL for a user
    webhook_url = adapter.create_shortcut_webhook_url(
        "user_123", "https://api.ngxagents.com"
    )
    print(f"Webhook URL: {webhook_url}")

    # Get shortcut instructions
    instructions = adapter.generate_shortcut_instructions(webhook_url)
    print(f"Setup instructions: {instructions['instructions'][0]}")


if __name__ == "__main__":
    example_usage()

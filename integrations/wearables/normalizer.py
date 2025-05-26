"""
Wearable Data Normalizer
Converts data from different wearable devices to NGX Agents standard format
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from .adapters.whoop import WHOOPRecovery, WHOOPStrain, WHOOPSleep, WHOOPWorkout
from .adapters.apple_health import (
    HealthKitSample,
    HealthKitWorkout,
    HealthKitSleep,
    HealthKitActivity,
    HealthKitDataType,
)
from .adapters.oura import (
    OuraSleep,
    OuraActivity,
    OuraReadiness,
    OuraHeartRate,
    OuraWorkout,
)

logger = logging.getLogger(__name__)


class WearableDevice(Enum):
    """Supported wearable devices"""

    WHOOP = "whoop"
    APPLE_WATCH = "apple_watch"
    OURA_RING = "oura_ring"
    GARMIN = "garmin"
    CGM = "cgm"


class MetricType(Enum):
    """Standard metric types in NGX system"""

    RECOVERY_SCORE = "recovery_score"
    STRAIN_SCORE = "strain_score"
    SLEEP_SCORE = "sleep_score"
    HEART_RATE_VARIABILITY = "hrv"
    RESTING_HEART_RATE = "rhr"
    SLEEP_DURATION = "sleep_duration"
    SLEEP_EFFICIENCY = "sleep_efficiency"
    DEEP_SLEEP = "deep_sleep"
    REM_SLEEP = "rem_sleep"
    LIGHT_SLEEP = "light_sleep"
    AWAKE_TIME = "awake_time"
    WORKOUT_STRAIN = "workout_strain"
    WORKOUT_DURATION = "workout_duration"
    CALORIES_BURNED = "calories_burned"
    STEPS = "steps"
    DISTANCE = "distance"
    VO2_MAX = "vo2_max"


@dataclass
class NormalizedMetric:
    """Normalized metric in NGX standard format"""

    device: WearableDevice
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    device_specific_id: str
    user_id: str
    raw_data: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    additional_metadata: Optional[Dict[str, Any]] = None


@dataclass
class NormalizedRecoveryData:
    """Normalized recovery data"""

    recovery_score: Optional[float]
    hrv_score: Optional[float]
    resting_heart_rate: Optional[float]
    sleep_need_hours: Optional[float]
    timestamp: datetime
    device: WearableDevice
    device_specific_id: str
    user_id: str
    raw_data: Dict[str, Any]


@dataclass
class NormalizedSleepData:
    """Normalized sleep data"""

    sleep_score: Optional[float]
    total_duration_minutes: Optional[float]
    sleep_efficiency_percent: Optional[float]
    deep_sleep_minutes: Optional[float]
    rem_sleep_minutes: Optional[float]
    light_sleep_minutes: Optional[float]
    awake_minutes: Optional[float]
    sleep_start: datetime
    sleep_end: datetime
    device: WearableDevice
    device_specific_id: str
    user_id: str
    raw_data: Dict[str, Any]


@dataclass
class NormalizedWorkoutData:
    """Normalized workout data"""

    workout_strain: Optional[float]
    duration_minutes: Optional[float]
    calories_burned: Optional[float]
    average_heart_rate: Optional[float]
    max_heart_rate: Optional[float]
    sport_type: Optional[str]
    start_time: datetime
    end_time: datetime
    device: WearableDevice
    device_specific_id: str
    user_id: str
    raw_data: Dict[str, Any]


class WearableDataNormalizer:
    """
    Normalizes data from various wearable devices to NGX standard format
    """

    def __init__(self):
        self.device_handlers = {
            WearableDevice.WHOOP: self._normalize_whoop_data,
            WearableDevice.OURA_RING: self._normalize_oura_data,
        }

    def normalize_recovery_data(
        self,
        device: WearableDevice,
        raw_data: Union[
            WHOOPRecovery, HealthKitActivity, OuraReadiness, Dict[str, Any]
        ],
    ) -> NormalizedRecoveryData:
        """
        Normalize recovery data from any device

        Args:
            device: Source device type
            raw_data: Raw data from device

        Returns:
            Normalized recovery data
        """
        if device == WearableDevice.WHOOP:
            return self._normalize_whoop_recovery(raw_data)
        elif device == WearableDevice.APPLE_WATCH:
            return self._normalize_apple_recovery(raw_data)
        elif device == WearableDevice.OURA_RING:
            return self._normalize_oura_recovery(raw_data)
        else:
            raise ValueError(f"Unsupported device for recovery data: {device}")

    def normalize_sleep_data(
        self,
        device: WearableDevice,
        raw_data: Union[
            WHOOPSleep, HealthKitSleep, List[HealthKitSleep], OuraSleep, Dict[str, Any]
        ],
    ) -> NormalizedSleepData:
        """
        Normalize sleep data from any device

        Args:
            device: Source device type
            raw_data: Raw data from device

        Returns:
            Normalized sleep data
        """
        if device == WearableDevice.WHOOP:
            return self._normalize_whoop_sleep(raw_data)
        elif device == WearableDevice.APPLE_WATCH:
            return self._normalize_apple_sleep(raw_data)
        elif device == WearableDevice.OURA_RING:
            return self._normalize_oura_sleep(raw_data)
        else:
            raise ValueError(f"Unsupported device for sleep data: {device}")

    def normalize_workout_data(
        self,
        device: WearableDevice,
        raw_data: Union[WHOOPWorkout, HealthKitWorkout, OuraWorkout, Dict[str, Any]],
    ) -> NormalizedWorkoutData:
        """
        Normalize workout data from any device

        Args:
            device: Source device type
            raw_data: Raw data from device

        Returns:
            Normalized workout data
        """
        if device == WearableDevice.WHOOP:
            return self._normalize_whoop_workout(raw_data)
        elif device == WearableDevice.APPLE_WATCH:
            return self._normalize_apple_workout(raw_data)
        elif device == WearableDevice.OURA_RING:
            return self._normalize_oura_workout(raw_data)
        else:
            raise ValueError(f"Unsupported device for workout data: {device}")

    def normalize_to_metrics(
        self,
        device: WearableDevice,
        raw_data: Union[
            WHOOPRecovery,
            WHOOPSleep,
            WHOOPWorkout,
            HealthKitActivity,
            HealthKitSleep,
            HealthKitWorkout,
            List[HealthKitSample],
            OuraReadiness,
            OuraSleep,
            OuraActivity,
            OuraWorkout,
            Dict[str, Any],
        ],
        data_type: str,
    ) -> List[NormalizedMetric]:
        """
        Convert any device data to list of normalized metrics

        Args:
            device: Source device type
            raw_data: Raw data from device
            data_type: Type of data (recovery, sleep, workout)

        Returns:
            List of normalized metrics
        """
        metrics = []

        if device == WearableDevice.WHOOP:
            if data_type == "recovery":
                recovery = self._normalize_whoop_recovery(raw_data)
                metrics.extend(self._recovery_to_metrics(recovery))
            elif data_type == "sleep":
                sleep = self._normalize_whoop_sleep(raw_data)
                metrics.extend(self._sleep_to_metrics(sleep))
            elif data_type == "workout":
                workout = self._normalize_whoop_workout(raw_data)
                metrics.extend(self._workout_to_metrics(workout))

        elif device == WearableDevice.APPLE_WATCH:
            if data_type == "recovery":
                recovery = self._normalize_apple_recovery(raw_data)
                metrics.extend(self._recovery_to_metrics(recovery))
            elif data_type == "sleep":
                sleep = self._normalize_apple_sleep(raw_data)
                metrics.extend(self._sleep_to_metrics(sleep))
            elif data_type == "workout":
                workout = self._normalize_apple_workout(raw_data)
                metrics.extend(self._workout_to_metrics(workout))
            elif data_type == "samples" and isinstance(raw_data, list):
                # Direct samples from HealthKit
                metrics.extend(self._healthkit_samples_to_metrics(raw_data))

        elif device == WearableDevice.OURA_RING:
            if data_type == "recovery":
                recovery = self._normalize_oura_recovery(raw_data)
                metrics.extend(self._recovery_to_metrics(recovery))
            elif data_type == "sleep":
                sleep = self._normalize_oura_sleep(raw_data)
                metrics.extend(self._sleep_to_metrics(sleep))
            elif data_type == "workout":
                workout = self._normalize_oura_workout(raw_data)
                metrics.extend(self._workout_to_metrics(workout))
            elif data_type == "activity":
                # Oura activity data is different, convert directly to metrics
                metrics.extend(self._oura_activity_to_metrics(raw_data))

        return metrics

    def _normalize_whoop_recovery(
        self, recovery: WHOOPRecovery
    ) -> NormalizedRecoveryData:
        """Normalize WHOOP recovery data"""
        recovery_score = None
        hrv_score = None
        resting_heart_rate = None
        sleep_need_hours = None

        # Extract recovery score
        if recovery.score and "recovery_score" in recovery.score:
            recovery_score = float(recovery.score["recovery_score"])

        # Extract HRV data
        if recovery.heart_rate_variability:
            if isinstance(recovery.heart_rate_variability, dict):
                hrv_score = recovery.heart_rate_variability.get("rmssd_milli")
            else:
                hrv_score = float(recovery.heart_rate_variability)

        # Extract resting heart rate
        if recovery.resting_heart_rate:
            if isinstance(recovery.resting_heart_rate, dict):
                resting_heart_rate = recovery.resting_heart_rate.get("bpm")
            else:
                resting_heart_rate = float(recovery.resting_heart_rate)

        # Extract sleep need
        if recovery.sleep_need:
            if isinstance(recovery.sleep_need, dict):
                sleep_need_baseline = recovery.sleep_need.get("baseline_milli", 0)
                sleep_need_debt = recovery.sleep_need.get(
                    "need_from_sleep_debt_milli", 0
                )
                sleep_need_strain = recovery.sleep_need.get(
                    "need_from_recent_strain_milli", 0
                )
                sleep_need_nap = recovery.sleep_need.get(
                    "need_from_recent_nap_milli", 0
                )

                total_need_milli = (
                    sleep_need_baseline
                    + sleep_need_debt
                    + sleep_need_strain
                    - sleep_need_nap
                )
                sleep_need_hours = total_need_milli / (
                    1000 * 60 * 60
                )  # Convert to hours

        return NormalizedRecoveryData(
            recovery_score=recovery_score,
            hrv_score=hrv_score,
            resting_heart_rate=resting_heart_rate,
            sleep_need_hours=sleep_need_hours,
            timestamp=recovery.created_at,
            device=WearableDevice.WHOOP,
            device_specific_id=recovery.recovery_id,
            user_id=recovery.user_id,
            raw_data=recovery.__dict__,
        )

    def _normalize_whoop_sleep(self, sleep: WHOOPSleep) -> NormalizedSleepData:
        """Normalize WHOOP sleep data"""
        sleep_score = None
        total_duration_minutes = None
        sleep_efficiency_percent = None
        deep_sleep_minutes = None
        rem_sleep_minutes = None
        light_sleep_minutes = None
        awake_minutes = None

        # Extract sleep score
        if sleep.score and "stage_summary" in sleep.score:
            sleep_score = float(sleep.score.get("sleep_performance_percentage", 0))

        # Calculate total duration
        duration_delta = sleep.end - sleep.start
        total_duration_minutes = duration_delta.total_seconds() / 60

        # Extract stage summary
        if sleep.stage_summary:
            total_in_bed_milli = sleep.stage_summary.get("total_in_bed_time_milli", 0)
            total_awake_milli = sleep.stage_summary.get("total_awake_time_milli", 0)
            total_no_data_milli = sleep.stage_summary.get("total_no_data_time_milli", 0)

            sleep_time_milli = (
                total_in_bed_milli - total_awake_milli - total_no_data_milli
            )

            if total_in_bed_milli > 0:
                sleep_efficiency_percent = (sleep_time_milli / total_in_bed_milli) * 100

            # Convert stage times to minutes
            deep_sleep_minutes = sleep.stage_summary.get(
                "total_slow_wave_sleep_time_milli", 0
            ) / (1000 * 60)
            rem_sleep_minutes = sleep.stage_summary.get(
                "total_rem_sleep_time_milli", 0
            ) / (1000 * 60)
            light_sleep_minutes = sleep.stage_summary.get(
                "total_light_sleep_time_milli", 0
            ) / (1000 * 60)
            awake_minutes = total_awake_milli / (1000 * 60)

        return NormalizedSleepData(
            sleep_score=sleep_score,
            total_duration_minutes=total_duration_minutes,
            sleep_efficiency_percent=sleep_efficiency_percent,
            deep_sleep_minutes=deep_sleep_minutes,
            rem_sleep_minutes=rem_sleep_minutes,
            light_sleep_minutes=light_sleep_minutes,
            awake_minutes=awake_minutes,
            sleep_start=sleep.start,
            sleep_end=sleep.end,
            device=WearableDevice.WHOOP,
            device_specific_id=sleep.sleep_id,
            user_id=sleep.user_id,
            raw_data=sleep.__dict__,
        )

    def _normalize_whoop_workout(self, workout: WHOOPWorkout) -> NormalizedWorkoutData:
        """Normalize WHOOP workout data"""
        workout_strain = None
        duration_minutes = None
        calories_burned = None
        average_heart_rate = None
        max_heart_rate = None
        sport_type = None

        # Extract strain score
        if workout.score and "strain" in workout.score:
            workout_strain = float(workout.score["strain"])

        # Calculate duration
        duration_delta = workout.end - workout.start
        duration_minutes = duration_delta.total_seconds() / 60

        # Extract additional metrics from score
        if workout.score:
            calories_burned = (
                workout.score.get("kilojoule", 0) * 0.239006
            )  # Convert kJ to calories
            average_heart_rate = workout.score.get("average_heart_rate")
            max_heart_rate = workout.score.get("max_heart_rate")

        # Map sport ID to sport name (simplified mapping)
        sport_mapping = {
            -1: "Activity",
            0: "Running",
            1: "Cycling",
            16: "Baseball",
            17: "Basketball",
            18: "Rowing",
            19: "Fencing",
            20: "Field Hockey",
            21: "Football",
            22: "Golf",
            23: "Ice Hockey",
            24: "Lacrosse",
            25: "Rugby",
            26: "Sailing",
            27: "Skiing",
            28: "Soccer",
            29: "Softball",
            30: "Squash",
            31: "Swimming",
            32: "Tennis",
            33: "Track and Field",
            34: "Volleyball",
            35: "Water Polo",
            36: "Wrestling",
            42: "Boxing",
            43: "Dance",
            44: "Pilates",
            45: "Yoga",
            46: "Weightlifting",
            47: "Cross Country Skiing",
            48: "Functional Fitness",
            49: "Duathlon",
            51: "Triathlon",
            52: "Dartsport",
            53: "MMA",
            55: "Surfing",
            56: "Elliptical",
            57: "Stairmaster",
            59: "Ultra Running",
            60: "Hiking",
            61: "Martial Arts",
            62: "Gymnastics",
            63: "Snowboard",
            64: "Motocross",
            65: "Calisthenics",
            66: "Rock Climbing",
            67: "Kayaking",
            68: "Circuit Training",
            70: "Track Cycling",
            71: "Powerlifting",
            72: "Wheelchair Racing",
            73: "Paddle Tennis",
            74: "Barre",
            75: "Meditation",
        }

        sport_type = sport_mapping.get(workout.sport_id, f"Sport_{workout.sport_id}")

        return NormalizedWorkoutData(
            workout_strain=workout_strain,
            duration_minutes=duration_minutes,
            calories_burned=calories_burned,
            average_heart_rate=average_heart_rate,
            max_heart_rate=max_heart_rate,
            sport_type=sport_type,
            start_time=workout.start,
            end_time=workout.end,
            device=WearableDevice.WHOOP,
            device_specific_id=workout.workout_id,
            user_id=workout.user_id,
            raw_data=workout.__dict__,
        )

    def _recovery_to_metrics(
        self, recovery: NormalizedRecoveryData
    ) -> List[NormalizedMetric]:
        """Convert normalized recovery data to individual metrics"""
        metrics = []

        if recovery.recovery_score is not None:
            metrics.append(
                NormalizedMetric(
                    device=recovery.device,
                    metric_type=MetricType.RECOVERY_SCORE,
                    value=recovery.recovery_score,
                    unit="percentage",
                    timestamp=recovery.timestamp,
                    device_specific_id=recovery.device_specific_id,
                    user_id=recovery.user_id,
                    raw_data=recovery.raw_data,
                )
            )

        if recovery.hrv_score is not None:
            metrics.append(
                NormalizedMetric(
                    device=recovery.device,
                    metric_type=MetricType.HEART_RATE_VARIABILITY,
                    value=recovery.hrv_score,
                    unit="milliseconds",
                    timestamp=recovery.timestamp,
                    device_specific_id=recovery.device_specific_id,
                    user_id=recovery.user_id,
                    raw_data=recovery.raw_data,
                )
            )

        if recovery.resting_heart_rate is not None:
            metrics.append(
                NormalizedMetric(
                    device=recovery.device,
                    metric_type=MetricType.RESTING_HEART_RATE,
                    value=recovery.resting_heart_rate,
                    unit="bpm",
                    timestamp=recovery.timestamp,
                    device_specific_id=recovery.device_specific_id,
                    user_id=recovery.user_id,
                    raw_data=recovery.raw_data,
                )
            )

        return metrics

    def _sleep_to_metrics(self, sleep: NormalizedSleepData) -> List[NormalizedMetric]:
        """Convert normalized sleep data to individual metrics"""
        metrics = []

        if sleep.sleep_score is not None:
            metrics.append(
                NormalizedMetric(
                    device=sleep.device,
                    metric_type=MetricType.SLEEP_SCORE,
                    value=sleep.sleep_score,
                    unit="percentage",
                    timestamp=sleep.sleep_start,
                    device_specific_id=sleep.device_specific_id,
                    user_id=sleep.user_id,
                    raw_data=sleep.raw_data,
                )
            )

        if sleep.total_duration_minutes is not None:
            metrics.append(
                NormalizedMetric(
                    device=sleep.device,
                    metric_type=MetricType.SLEEP_DURATION,
                    value=sleep.total_duration_minutes,
                    unit="minutes",
                    timestamp=sleep.sleep_start,
                    device_specific_id=sleep.device_specific_id,
                    user_id=sleep.user_id,
                    raw_data=sleep.raw_data,
                )
            )

        if sleep.sleep_efficiency_percent is not None:
            metrics.append(
                NormalizedMetric(
                    device=sleep.device,
                    metric_type=MetricType.SLEEP_EFFICIENCY,
                    value=sleep.sleep_efficiency_percent,
                    unit="percentage",
                    timestamp=sleep.sleep_start,
                    device_specific_id=sleep.device_specific_id,
                    user_id=sleep.user_id,
                    raw_data=sleep.raw_data,
                )
            )

        if sleep.deep_sleep_minutes is not None:
            metrics.append(
                NormalizedMetric(
                    device=sleep.device,
                    metric_type=MetricType.DEEP_SLEEP,
                    value=sleep.deep_sleep_minutes,
                    unit="minutes",
                    timestamp=sleep.sleep_start,
                    device_specific_id=sleep.device_specific_id,
                    user_id=sleep.user_id,
                    raw_data=sleep.raw_data,
                )
            )

        if sleep.rem_sleep_minutes is not None:
            metrics.append(
                NormalizedMetric(
                    device=sleep.device,
                    metric_type=MetricType.REM_SLEEP,
                    value=sleep.rem_sleep_minutes,
                    unit="minutes",
                    timestamp=sleep.sleep_start,
                    device_specific_id=sleep.device_specific_id,
                    user_id=sleep.user_id,
                    raw_data=sleep.raw_data,
                )
            )

        if sleep.light_sleep_minutes is not None:
            metrics.append(
                NormalizedMetric(
                    device=sleep.device,
                    metric_type=MetricType.LIGHT_SLEEP,
                    value=sleep.light_sleep_minutes,
                    unit="minutes",
                    timestamp=sleep.sleep_start,
                    device_specific_id=sleep.device_specific_id,
                    user_id=sleep.user_id,
                    raw_data=sleep.raw_data,
                )
            )

        return metrics

    def _workout_to_metrics(
        self, workout: NormalizedWorkoutData
    ) -> List[NormalizedMetric]:
        """Convert normalized workout data to individual metrics"""
        metrics = []

        if workout.workout_strain is not None:
            metrics.append(
                NormalizedMetric(
                    device=workout.device,
                    metric_type=MetricType.WORKOUT_STRAIN,
                    value=workout.workout_strain,
                    unit="strain_score",
                    timestamp=workout.start_time,
                    device_specific_id=workout.device_specific_id,
                    user_id=workout.user_id,
                    raw_data=workout.raw_data,
                )
            )

        if workout.duration_minutes is not None:
            metrics.append(
                NormalizedMetric(
                    device=workout.device,
                    metric_type=MetricType.WORKOUT_DURATION,
                    value=workout.duration_minutes,
                    unit="minutes",
                    timestamp=workout.start_time,
                    device_specific_id=workout.device_specific_id,
                    user_id=workout.user_id,
                    raw_data=workout.raw_data,
                )
            )

        if workout.calories_burned is not None:
            metrics.append(
                NormalizedMetric(
                    device=workout.device,
                    metric_type=MetricType.CALORIES_BURNED,
                    value=workout.calories_burned,
                    unit="calories",
                    timestamp=workout.start_time,
                    device_specific_id=workout.device_specific_id,
                    user_id=workout.user_id,
                    raw_data=workout.raw_data,
                )
            )

        return metrics

    def _normalize_apple_recovery(
        self, data: Union[HealthKitActivity, List[HealthKitSample], Dict[str, Any]]
    ) -> NormalizedRecoveryData:
        """Normalize Apple HealthKit recovery/activity data"""
        # Apple doesn't have a direct "recovery score" like WHOOP
        # We'll use activity data and HRV to estimate recovery status

        recovery_score = None
        hrv_score = None
        resting_heart_rate = None
        timestamp = datetime.utcnow()

        if isinstance(data, HealthKitActivity):
            # Activity data can give us a general wellness indicator
            # This is a simplified approach - you might want to enhance this
            if data.active_energy_burned and data.exercise_minutes:
                # Simple recovery estimation based on activity level
                # Lower activity might indicate recovery day
                recovery_score = min(100, (data.exercise_minutes / 30) * 100)
            timestamp = data.date or timestamp
            device_id = f"activity_{data.date.strftime('%Y%m%d')}"

        elif isinstance(data, list):
            # Process list of samples
            for sample in data:
                if sample.type == HealthKitDataType.HEART_RATE_VARIABILITY:
                    hrv_score = sample.value
                elif sample.type == HealthKitDataType.RESTING_HEART_RATE:
                    resting_heart_rate = sample.value

            device_id = f"samples_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        else:
            device_id = f"data_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        return NormalizedRecoveryData(
            recovery_score=recovery_score,
            hrv_score=hrv_score,
            resting_heart_rate=resting_heart_rate,
            sleep_need_hours=None,  # Apple doesn't provide this
            timestamp=timestamp,
            device=WearableDevice.APPLE_WATCH,
            device_specific_id=device_id,
            user_id="apple_user",  # This should be passed in
            raw_data=data.__dict__ if hasattr(data, "__dict__") else data,
        )

    def _normalize_apple_sleep(
        self, data: Union[HealthKitSleep, List[HealthKitSleep], Dict[str, Any]]
    ) -> NormalizedSleepData:
        """Normalize Apple HealthKit sleep data"""
        if isinstance(data, list) and data:
            # Apple often provides multiple sleep samples
            # We need to aggregate them
            sleep_start = min(s.start_date for s in data)
            sleep_end = max(s.end_date for s in data)

            # Calculate time in different states
            asleep_minutes = 0
            in_bed_minutes = 0
            awake_minutes = 0

            for sample in data:
                duration = sample.duration_minutes
                if sample.sleep_state == "Asleep":
                    asleep_minutes += duration
                elif sample.sleep_state == "InBed":
                    in_bed_minutes += duration
                elif sample.sleep_state == "Awake":
                    awake_minutes += duration

            total_duration_minutes = (sleep_end - sleep_start).total_seconds() / 60
            sleep_efficiency_percent = (
                (asleep_minutes / total_duration_minutes * 100)
                if total_duration_minutes > 0
                else 0
            )

            # Apple doesn't differentiate sleep stages like WHOOP
            # We'll estimate based on total sleep
            deep_sleep_minutes = asleep_minutes * 0.15  # Estimate 15% deep sleep
            rem_sleep_minutes = asleep_minutes * 0.25  # Estimate 25% REM
            light_sleep_minutes = asleep_minutes * 0.60  # Estimate 60% light sleep

            device_id = f"sleep_{sleep_start.strftime('%Y%m%d%H%M%S')}"

        elif isinstance(data, HealthKitSleep):
            # Single sleep sample
            sleep_start = data.start_date
            sleep_end = data.end_date
            total_duration_minutes = data.duration_minutes

            # Simple efficiency calculation
            if data.sleep_state == "Asleep":
                sleep_efficiency_percent = 90  # Assume good efficiency if asleep
                asleep_minutes = total_duration_minutes
                awake_minutes = 0
            else:
                sleep_efficiency_percent = 50  # Lower efficiency if just in bed
                asleep_minutes = total_duration_minutes * 0.85
                awake_minutes = total_duration_minutes * 0.15

            deep_sleep_minutes = asleep_minutes * 0.15
            rem_sleep_minutes = asleep_minutes * 0.25
            light_sleep_minutes = asleep_minutes * 0.60

            device_id = f"sleep_{data.start_date.strftime('%Y%m%d%H%M%S')}"
        else:
            # Dict format
            return self._normalize_apple_sleep_from_dict(data)

        return NormalizedSleepData(
            sleep_score=sleep_efficiency_percent,  # Use efficiency as score
            total_duration_minutes=total_duration_minutes,
            sleep_efficiency_percent=sleep_efficiency_percent,
            deep_sleep_minutes=deep_sleep_minutes,
            rem_sleep_minutes=rem_sleep_minutes,
            light_sleep_minutes=light_sleep_minutes,
            awake_minutes=awake_minutes,
            sleep_start=sleep_start,
            sleep_end=sleep_end,
            device=WearableDevice.APPLE_WATCH,
            device_specific_id=device_id,
            user_id="apple_user",
            raw_data=(
                data
                if isinstance(data, dict)
                else (
                    [d.__dict__ for d in data]
                    if isinstance(data, list)
                    else data.__dict__
                )
            ),
        )

    def _normalize_apple_workout(
        self, workout: Union[HealthKitWorkout, Dict[str, Any]]
    ) -> NormalizedWorkoutData:
        """Normalize Apple HealthKit workout data"""
        if isinstance(workout, HealthKitWorkout):
            # Calculate strain (Apple doesn't provide this, so estimate)
            # Simple strain calculation based on duration and calories
            strain_estimate = None
            if workout.duration_minutes and workout.total_energy_burned:
                # Rough estimate: higher calories/minute = higher strain
                calories_per_minute = (
                    workout.total_energy_burned / workout.duration_minutes
                )
                strain_estimate = min(20, calories_per_minute * 2)  # Cap at 20

            return NormalizedWorkoutData(
                workout_strain=strain_estimate,
                duration_minutes=workout.duration_minutes,
                calories_burned=workout.total_energy_burned,
                average_heart_rate=workout.average_heart_rate,
                max_heart_rate=None,  # Apple doesn't always provide this
                sport_type=workout.activity_type,
                start_time=workout.start_date,
                end_time=workout.end_date,
                device=WearableDevice.APPLE_WATCH,
                device_specific_id=f"workout_{workout.start_date.strftime('%Y%m%d%H%M%S')}",
                user_id="apple_user",
                raw_data=workout.__dict__,
            )
        else:
            # Handle dict format
            return self._normalize_apple_workout_from_dict(workout)

    def _normalize_apple_sleep_from_dict(
        self, data: Dict[str, Any]
    ) -> NormalizedSleepData:
        """Helper to normalize sleep from dict format"""
        # Implementation for dict format
        return NormalizedSleepData(
            sleep_score=data.get("sleep_efficiency", 0),
            total_duration_minutes=data.get("duration_minutes", 0),
            sleep_efficiency_percent=data.get("sleep_efficiency", 0),
            deep_sleep_minutes=data.get("deep_sleep", 0),
            rem_sleep_minutes=data.get("rem_sleep", 0),
            light_sleep_minutes=data.get("light_sleep", 0),
            awake_minutes=data.get("awake", 0),
            sleep_start=datetime.fromisoformat(
                data.get("start_date", datetime.utcnow().isoformat())
            ),
            sleep_end=datetime.fromisoformat(
                data.get("end_date", datetime.utcnow().isoformat())
            ),
            device=WearableDevice.APPLE_WATCH,
            device_specific_id=data.get("id", "unknown"),
            user_id=data.get("user_id", "apple_user"),
            raw_data=data,
        )

    def _normalize_apple_workout_from_dict(
        self, data: Dict[str, Any]
    ) -> NormalizedWorkoutData:
        """Helper to normalize workout from dict format"""
        return NormalizedWorkoutData(
            workout_strain=data.get("strain"),
            duration_minutes=data.get("duration_minutes"),
            calories_burned=data.get("calories"),
            average_heart_rate=data.get("avg_hr"),
            max_heart_rate=data.get("max_hr"),
            sport_type=data.get("activity_type", "Unknown"),
            start_time=datetime.fromisoformat(
                data.get("start_date", datetime.utcnow().isoformat())
            ),
            end_time=datetime.fromisoformat(
                data.get("end_date", datetime.utcnow().isoformat())
            ),
            device=WearableDevice.APPLE_WATCH,
            device_specific_id=data.get("id", "unknown"),
            user_id=data.get("user_id", "apple_user"),
            raw_data=data,
        )

    def _healthkit_samples_to_metrics(
        self, samples: List[HealthKitSample]
    ) -> List[NormalizedMetric]:
        """Convert HealthKit samples directly to metrics"""
        metrics = []

        # Map HealthKit types to MetricType
        type_mapping = {
            HealthKitDataType.STEPS: MetricType.STEPS,
            HealthKitDataType.HEART_RATE: MetricType.RESTING_HEART_RATE,
            HealthKitDataType.HEART_RATE_VARIABILITY: MetricType.HEART_RATE_VARIABILITY,
            HealthKitDataType.RESTING_HEART_RATE: MetricType.RESTING_HEART_RATE,
            HealthKitDataType.ACTIVE_ENERGY: MetricType.CALORIES_BURNED,
            HealthKitDataType.DISTANCE: MetricType.DISTANCE,
            HealthKitDataType.VO2_MAX: MetricType.VO2_MAX,
        }

        for sample in samples:
            metric_type = type_mapping.get(sample.type)
            if metric_type:
                metric = NormalizedMetric(
                    device=WearableDevice.APPLE_WATCH,
                    metric_type=metric_type,
                    value=sample.value,
                    unit=sample.unit,
                    timestamp=sample.start_date,
                    device_specific_id=f"{sample.type.name}_{sample.start_date.strftime('%Y%m%d%H%M%S')}",
                    user_id="apple_user",  # Should be passed in context
                    raw_data=sample.__dict__ if hasattr(sample, "__dict__") else {},
                )
                metrics.append(metric)

        return metrics

    def _normalize_oura_data(self, raw_data: Any) -> Any:
        """Placeholder for Oura data normalization - delegates to specific methods"""
        # This method is referenced in device_handlers but not actually used
        # The specific normalize_* methods handle the actual normalization
        pass

    def _normalize_oura_recovery(
        self, readiness: OuraReadiness
    ) -> NormalizedRecoveryData:
        """Normalize Oura readiness data to recovery format"""
        return NormalizedRecoveryData(
            recovery_score=float(readiness.score) if readiness.score else None,
            hrv_score=readiness.heart_rate_variability,
            resting_heart_rate=(
                float(readiness.resting_heart_rate)
                if readiness.resting_heart_rate
                else None
            ),
            sleep_need_hours=None,  # Oura doesn't provide explicit sleep need
            timestamp=datetime.fromisoformat(readiness.day),
            device=WearableDevice.OURA_RING,
            device_specific_id=readiness.id,
            user_id="",  # Will be set by the service
            raw_data={
                "score": readiness.score,
                "temperature_deviation": readiness.temperature_deviation,
                "contributors": readiness.contributors,
                "temperature": readiness.temperature,
                "resting_heart_rate": readiness.resting_heart_rate,
                "hrv": readiness.heart_rate_variability,
            },
        )

    def _normalize_oura_sleep(self, sleep: OuraSleep) -> NormalizedSleepData:
        """Normalize Oura sleep data"""
        total_minutes = (
            sleep.total_sleep_duration / 60 if sleep.total_sleep_duration else None
        )

        return NormalizedSleepData(
            sleep_score=float(sleep.score) if sleep.score else None,
            total_duration_minutes=total_minutes,
            sleep_efficiency_percent=(
                float(sleep.efficiency) if sleep.efficiency else None
            ),
            deep_sleep_minutes=(
                sleep.deep_sleep_duration / 60 if sleep.deep_sleep_duration else None
            ),
            rem_sleep_minutes=(
                sleep.rem_sleep_duration / 60 if sleep.rem_sleep_duration else None
            ),
            light_sleep_minutes=(
                sleep.light_sleep_duration / 60 if sleep.light_sleep_duration else None
            ),
            awake_minutes=sleep.awake_time / 60 if sleep.awake_time else None,
            sleep_start=sleep.bedtime_start,
            sleep_end=sleep.bedtime_end,
            device=WearableDevice.OURA_RING,
            device_specific_id=sleep.id,
            user_id="",  # Will be set by the service
            raw_data={
                "day": sleep.day,
                "score": sleep.score,
                "efficiency": sleep.efficiency,
                "latency": sleep.latency,
                "hr_lowest": sleep.hr_lowest,
                "hr_average": sleep.hr_average,
                "hrv_average": sleep.hrv_average,
                "respiratory_rate": sleep.respiratory_rate,
                "temperature_deviation": sleep.temperature_deviation,
            },
        )

    def _normalize_oura_workout(self, workout: OuraWorkout) -> NormalizedWorkoutData:
        """Normalize Oura workout data"""
        duration_minutes = (
            workout.end_datetime - workout.start_datetime
        ).total_seconds() / 60

        return NormalizedWorkoutData(
            workout_strain=None,  # Oura doesn't provide strain scores
            duration_minutes=duration_minutes,
            calories_burned=(
                float(workout.active_calories) if workout.active_calories else None
            ),
            average_heart_rate=(
                float(workout.average_heart_rate)
                if workout.average_heart_rate
                else None
            ),
            max_heart_rate=(
                float(workout.max_heart_rate) if workout.max_heart_rate else None
            ),
            sport_type=workout.activity,
            start_time=workout.start_datetime,
            end_time=workout.end_datetime,
            device=WearableDevice.OURA_RING,
            device_specific_id=workout.id,
            user_id="",  # Will be set by the service
            raw_data={
                "day": workout.day,
                "activity": workout.activity,
                "active_calories": workout.active_calories,
                "average_heart_rate": workout.average_heart_rate,
                "max_heart_rate": workout.max_heart_rate,
                "average_met_minutes": workout.average_met_minutes,
                "intensity": workout.intensity,
            },
        )

    def _oura_activity_to_metrics(
        self, activity: OuraActivity
    ) -> List[NormalizedMetric]:
        """Convert Oura activity data directly to metrics"""
        metrics = []
        base_date = datetime.fromisoformat(activity.day)

        # Steps metric
        if activity.steps:
            metrics.append(
                NormalizedMetric(
                    device=WearableDevice.OURA_RING,
                    metric_type=MetricType.STEPS,
                    value=float(activity.steps),
                    unit="steps",
                    timestamp=base_date,
                    device_specific_id=activity.id,
                    user_id="",
                    raw_data={"day": activity.day, "steps": activity.steps},
                )
            )

        # Calories metric
        if activity.total_calories:
            metrics.append(
                NormalizedMetric(
                    device=WearableDevice.OURA_RING,
                    metric_type=MetricType.CALORIES_BURNED,
                    value=float(activity.total_calories),
                    unit="kcal",
                    timestamp=base_date,
                    device_specific_id=activity.id,
                    user_id="",
                    raw_data={
                        "day": activity.day,
                        "total_calories": activity.total_calories,
                    },
                )
            )

        return metrics


# Example usage
def example_normalizer_usage():
    """Example of how to use the normalizer"""
    normalizer = WearableDataNormalizer()

    # Example WHOOP recovery data
    whoop_recovery = WHOOPRecovery(
        recovery_id="rec_123",
        user_id="user_456",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        score={"recovery_score": 85},
        heart_rate_variability={"rmssd_milli": 45.2},
        resting_heart_rate={"bpm": 52},
        sleep_need={"baseline_milli": 28800000, "need_from_sleep_debt_milli": 1800000},
    )

    # Normalize the data
    normalized_recovery = normalizer.normalize_recovery_data(
        WearableDevice.WHOOP, whoop_recovery
    )

    # Convert to individual metrics
    metrics = normalizer.normalize_to_metrics(
        WearableDevice.WHOOP, whoop_recovery, "recovery"
    )

    print(f"Normalized recovery: {normalized_recovery}")
    print(f"Individual metrics: {len(metrics)} metrics extracted")


if __name__ == "__main__":
    example_normalizer_usage()

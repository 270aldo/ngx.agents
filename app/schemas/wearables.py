"""
Wearable Integration API Schemas
Pydantic models for wearable device integration endpoints
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class WearableDeviceType(str, Enum):
    """Supported wearable device types"""

    WHOOP = "whoop"
    APPLE_WATCH = "apple_watch"
    OURA_RING = "oura_ring"
    GARMIN = "garmin"
    CGM = "cgm"


class MetricTypeEnum(str, Enum):
    """Standard metric types"""

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


# Request Models
class AuthorizeDeviceRequest(BaseModel):
    """Request to get device authorization URL"""

    device: WearableDeviceType
    redirect_url: Optional[str] = None
    state: Optional[str] = None


class CompleteAuthorizationRequest(BaseModel):
    """Request to complete device authorization"""

    device: WearableDeviceType
    authorization_code: str
    state: Optional[str] = None


class SyncDataRequest(BaseModel):
    """Request to sync user data from device"""

    device: WearableDeviceType
    days_back: int = Field(
        default=7, ge=1, le=30, description="Number of days to sync (1-30)"
    )
    force_refresh: bool = Field(
        default=False, description="Force refresh even if recently synced"
    )


class DisconnectDeviceRequest(BaseModel):
    """Request to disconnect a device"""

    device: WearableDeviceType


# Response Models
class AuthorizeDeviceResponse(BaseModel):
    """Response with device authorization URL"""

    success: bool
    authorization_url: str
    device: WearableDeviceType
    expires_in: Optional[int] = Field(
        default=600, description="URL expiration in seconds"
    )


class DeviceConnectionInfo(BaseModel):
    """Device connection information"""

    device: WearableDeviceType
    device_user_id: str
    is_active: bool
    last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CompleteAuthorizationResponse(BaseModel):
    """Response after completing authorization"""

    success: bool
    message: str
    connection: Optional[DeviceConnectionInfo] = None
    error: Optional[str] = None


class MetricData(BaseModel):
    """Individual metric data point"""

    metric_type: MetricTypeEnum
    value: float
    unit: str
    timestamp: datetime
    device: WearableDeviceType
    device_specific_id: str
    confidence_score: Optional[float] = None


class RecoveryData(BaseModel):
    """Recovery data summary"""

    recovery_score: Optional[float] = None
    hrv_score: Optional[float] = None
    resting_heart_rate: Optional[float] = None
    sleep_need_hours: Optional[float] = None
    timestamp: datetime
    device: WearableDeviceType
    device_specific_id: str


class SleepData(BaseModel):
    """Sleep data summary"""

    sleep_score: Optional[float] = None
    total_duration_minutes: Optional[float] = None
    sleep_efficiency_percent: Optional[float] = None
    deep_sleep_minutes: Optional[float] = None
    rem_sleep_minutes: Optional[float] = None
    light_sleep_minutes: Optional[float] = None
    awake_minutes: Optional[float] = None
    sleep_start: datetime
    sleep_end: datetime
    device: WearableDeviceType
    device_specific_id: str


class WorkoutData(BaseModel):
    """Workout data summary"""

    workout_strain: Optional[float] = None
    duration_minutes: Optional[float] = None
    calories_burned: Optional[float] = None
    average_heart_rate: Optional[float] = None
    max_heart_rate: Optional[float] = None
    sport_type: Optional[str] = None
    start_time: datetime
    end_time: datetime
    device: WearableDeviceType
    device_specific_id: str


class SyncResult(BaseModel):
    """Data synchronization result"""

    success: bool
    device: WearableDeviceType
    metrics_synced: int
    recovery_records: int = 0
    sleep_records: int = 0
    workout_records: int = 0
    error_message: Optional[str] = None
    sync_timestamp: datetime


class SyncDataResponse(BaseModel):
    """Response from data sync operation"""

    success: bool
    result: Optional[SyncResult] = None
    error: Optional[str] = None


class UserConnectionsResponse(BaseModel):
    """Response with user's device connections"""

    success: bool
    connections: List[DeviceConnectionInfo]
    total_connections: int


class DisconnectDeviceResponse(BaseModel):
    """Response from device disconnection"""

    success: bool
    message: str
    device: WearableDeviceType


class UserMetricsRequest(BaseModel):
    """Request for user metrics"""

    device: Optional[WearableDeviceType] = None
    metric_types: Optional[List[MetricTypeEnum]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)


class UserMetricsResponse(BaseModel):
    """Response with user metrics"""

    success: bool
    metrics: List[MetricData]
    total_metrics: int
    filters_applied: Dict[str, Any]


class RecoveryDataResponse(BaseModel):
    """Response with recovery data"""

    success: bool
    recovery_data: List[RecoveryData]
    total_records: int


class SleepDataResponse(BaseModel):
    """Response with sleep data"""

    success: bool
    sleep_data: List[SleepData]
    total_records: int


class WorkoutDataResponse(BaseModel):
    """Response with workout data"""

    success: bool
    workout_data: List[WorkoutData]
    total_records: int


class DeviceHealthStatus(BaseModel):
    """Health status for a specific device"""

    device: WearableDeviceType
    status: str  # "available", "configured", "error"
    message: Optional[str] = None


class WearableServiceHealthResponse(BaseModel):
    """Wearable service health check response"""

    success: bool
    service: str = "wearable_integration"
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    active_connections: int
    supported_devices: List[WearableDeviceType]
    device_status: List[DeviceHealthStatus]


class SupportedDevicesResponse(BaseModel):
    """Response with supported devices"""

    success: bool
    devices: List[WearableDeviceType]
    total_devices: int


class BulkSyncRequest(BaseModel):
    """Request to sync all users"""

    days_back: int = Field(
        default=1, ge=1, le=7, description="Number of days to sync for all users"
    )
    device_filter: Optional[List[WearableDeviceType]] = None


class BulkSyncResponse(BaseModel):
    """Response from bulk sync operation"""

    success: bool
    total_users_processed: int
    successful_syncs: int
    failed_syncs: int
    sync_results: List[SyncResult]
    processing_time_seconds: float


# Webhook Models (for real-time updates)
class WHOOPWebhookData(BaseModel):
    """WHOOP webhook notification data"""

    user_id: str
    type: str  # "recovery", "sleep", "workout", "cycle"
    id: str
    timestamp: datetime


class WebhookNotification(BaseModel):
    """Generic webhook notification"""

    device: WearableDeviceType
    event_type: str
    user_id: str
    data: Dict[str, Any]
    timestamp: datetime
    signature: Optional[str] = None  # For webhook verification


class WebhookResponse(BaseModel):
    """Webhook processing response"""

    success: bool
    message: str
    processed_at: datetime


# Error Models
class WearableAPIError(BaseModel):
    """Wearable API error response"""

    success: bool = False
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Validation
class UserMetricsRequest(UserMetricsRequest):
    """Enhanced user metrics request with validation"""

    @validator("end_date")
    def validate_end_date(cls, v, values):
        if v and "start_date" in values and values["start_date"]:
            if v <= values["start_date"]:
                raise ValueError("end_date must be after start_date")
        return v

    @validator("start_date")
    def validate_start_date(cls, v):
        if v and v > datetime.utcnow():
            raise ValueError("start_date cannot be in the future")
        return v


# Configuration Models
class DeviceConfig(BaseModel):
    """Configuration for a wearable device integration"""

    client_id: str
    client_secret: str
    redirect_uri: str
    sandbox: bool = True
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None


class WearableServiceConfig(BaseModel):
    """Configuration for the entire wearable service"""

    whoop: Optional[DeviceConfig] = None
    apple_health: Optional[DeviceConfig] = None
    oura: Optional[DeviceConfig] = None
    garmin: Optional[DeviceConfig] = None

    # Global settings
    default_sync_interval_hours: int = Field(default=6, ge=1, le=24)
    max_historical_days: int = Field(default=30, ge=1, le=365)
    enable_webhooks: bool = True
    webhook_timeout_seconds: int = Field(default=30, ge=5, le=300)


# Statistics and Analytics
class DeviceUsageStats(BaseModel):
    """Usage statistics for a device"""

    device: WearableDeviceType
    total_users: int
    active_users: int
    total_syncs_today: int
    total_metrics_synced: int
    average_sync_time_seconds: float
    last_successful_sync: Optional[datetime] = None


class WearableAnalytics(BaseModel):
    """Analytics for wearable integrations"""

    total_connected_devices: int
    total_active_users: int
    total_metrics_today: int
    device_stats: List[DeviceUsageStats]
    uptime_percentage: float
    average_response_time_ms: float
    error_rate_percentage: float


class WearableAnalyticsResponse(BaseModel):
    """Response with wearable analytics"""

    success: bool
    analytics: WearableAnalytics
    generated_at: datetime


# Export all models
__all__ = [
    # Enums
    "WearableDeviceType",
    "MetricTypeEnum",
    # Request Models
    "AuthorizeDeviceRequest",
    "CompleteAuthorizationRequest",
    "SyncDataRequest",
    "DisconnectDeviceRequest",
    "UserMetricsRequest",
    "BulkSyncRequest",
    # Response Models
    "AuthorizeDeviceResponse",
    "DeviceConnectionInfo",
    "CompleteAuthorizationResponse",
    "MetricData",
    "RecoveryData",
    "SleepData",
    "WorkoutData",
    "SyncResult",
    "SyncDataResponse",
    "UserConnectionsResponse",
    "DisconnectDeviceResponse",
    "UserMetricsResponse",
    "RecoveryDataResponse",
    "SleepDataResponse",
    "WorkoutDataResponse",
    "WearableServiceHealthResponse",
    "SupportedDevicesResponse",
    "BulkSyncResponse",
    # Webhook Models
    "WHOOPWebhookData",
    "WebhookNotification",
    "WebhookResponse",
    # Error Models
    "WearableAPIError",
    # Configuration Models
    "DeviceConfig",
    "WearableServiceConfig",
    # Analytics Models
    "DeviceUsageStats",
    "WearableAnalytics",
    "WearableAnalyticsResponse",
]

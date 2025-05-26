"""
Wearable Integration Service
Central service for managing all wearable device integrations in NGX Agents
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import json

from .adapters.whoop import WHOOPAdapter, WHOOPConfig
from .adapters.apple_health import AppleHealthAdapter, AppleHealthConfig
from .adapters.oura import OuraAdapter, OuraConfig
from .normalizer import (
    WearableDataNormalizer,
    WearableDevice,
    NormalizedMetric,
    NormalizedRecoveryData,
    NormalizedSleepData,
    NormalizedWorkoutData,
)

logger = logging.getLogger(__name__)


@dataclass
class DeviceConnection:
    """Represents a user's connection to a wearable device"""

    user_id: str
    device: WearableDevice
    device_user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
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
class SyncResult:
    """Result of a data synchronization operation"""

    success: bool
    device: WearableDevice
    user_id: str
    metrics_synced: int
    recovery_records: int = 0
    sleep_records: int = 0
    workout_records: int = 0
    error_message: Optional[str] = None
    sync_timestamp: datetime = None

    def __post_init__(self):
        if self.sync_timestamp is None:
            self.sync_timestamp = datetime.utcnow()


class WearableIntegrationService:
    """
    Central service for managing wearable device integrations
    Handles authentication, data synchronization, and normalization
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the wearable integration service

        Args:
            config: Configuration dict containing API credentials for different devices
        """
        self.config = config
        self.normalizer = WearableDataNormalizer()
        self.active_connections: Dict[str, DeviceConnection] = {}
        self.device_adapters: Dict[WearableDevice, Any] = {}

        # Initialize device adapters
        self._initialize_adapters()

    def _initialize_adapters(self):
        """Initialize adapters for supported devices"""
        # Initialize WHOOP adapter if configured
        if "whoop" in self.config:
            whoop_config = WHOOPConfig(
                client_id=self.config["whoop"]["client_id"],
                client_secret=self.config["whoop"]["client_secret"],
                redirect_uri=self.config["whoop"]["redirect_uri"],
                sandbox=self.config["whoop"].get("sandbox", True),
            )
            self.device_adapters[WearableDevice.WHOOP] = whoop_config
            logger.info("WHOOP adapter initialized")

        # Initialize Apple Health adapter if configured
        if "apple_health" in self.config:
            apple_config = AppleHealthConfig(
                webhook_secret=self.config["apple_health"]["webhook_secret"],
                api_key=self.config["apple_health"].get("api_key"),
                enable_shortcuts=self.config["apple_health"].get(
                    "enable_shortcuts", True
                ),
                enable_webhooks=self.config["apple_health"].get(
                    "enable_webhooks", True
                ),
            )
            self.device_adapters[WearableDevice.APPLE_WATCH] = apple_config
            logger.info("Apple Health adapter initialized")

        # Initialize Oura Ring adapter if configured
        if "oura" in self.config:
            oura_config = OuraConfig(
                client_id=self.config["oura"]["client_id"],
                client_secret=self.config["oura"]["client_secret"],
                redirect_uri=self.config["oura"]["redirect_uri"],
            )
            self.device_adapters[WearableDevice.OURA_RING] = oura_config
            logger.info("Oura Ring adapter initialized")

        # TODO: Initialize other device adapters (Garmin, etc.)

    async def get_authorization_url(
        self, device: WearableDevice, user_id: str, state: str = None
    ) -> str:
        """
        Get authorization URL for a device

        Args:
            device: Wearable device type
            user_id: NGX user ID
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for the device
        """
        if device == WearableDevice.WHOOP:
            config = self.device_adapters[device]
            async with WHOOPAdapter(config) as whoop:
                auth_state = f"{user_id}:{state}" if state else user_id
                return whoop.get_auth_url(auth_state)
        elif device == WearableDevice.OURA_RING:
            config = self.device_adapters[device]
            async with OuraAdapter(config) as oura:
                auth_state = f"{user_id}:{state}" if state else user_id
                return oura.get_auth_url(auth_state)
        elif device == WearableDevice.APPLE_WATCH:
            # Apple Health uses webhooks/shortcuts, not OAuth
            config = self.device_adapters[device]
            adapter = AppleHealthAdapter(config)
            webhook_url = adapter.create_shortcut_webhook_url(
                user_id, self.config.get("base_url", "https://api.ngxagents.com")
            )
            # Return a special URL that indicates iOS Shortcuts setup
            return f"shortcuts://setup?webhook={webhook_url}"
        else:
            raise ValueError(f"Unsupported device: {device}")

    async def complete_authorization(
        self, device: WearableDevice, authorization_code: str, state: str = None
    ) -> DeviceConnection:
        """
        Complete OAuth authorization flow and store connection

        Args:
            device: Wearable device type
            authorization_code: Authorization code from callback
            state: State parameter (contains user_id)

        Returns:
            Device connection information
        """
        # Extract user_id from state
        user_id = state.split(":")[0] if state and ":" in state else state

        if device == WearableDevice.WHOOP:
            config = self.device_adapters[device]
            async with WHOOPAdapter(config) as whoop:
                # Exchange code for tokens
                token_data = await whoop.exchange_code_for_tokens(authorization_code)

                # Get user profile to get device user ID
                profile = await whoop.get_user_profile()
                device_user_id = profile["user_id"]

                # Create connection
                connection = DeviceConnection(
                    user_id=user_id,
                    device=device,
                    device_user_id=device_user_id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                    token_expires_at=datetime.utcnow()
                    + timedelta(seconds=token_data["expires_in"]),
                )

                # Store connection
                connection_key = f"{user_id}:{device.value}"
                self.active_connections[connection_key] = connection

                logger.info(f"Successfully connected {device.value} for user {user_id}")
                return connection
        elif device == WearableDevice.OURA_RING:
            config = self.device_adapters[device]
            async with OuraAdapter(config) as oura:
                # Exchange code for tokens
                token_data = await oura.exchange_code_for_tokens(authorization_code)

                # Get user profile to get device user ID
                profile = await oura.get_personal_info()
                device_user_id = profile.get("id", f"oura_{user_id}")

                # Create connection
                connection = DeviceConnection(
                    user_id=user_id,
                    device=device,
                    device_user_id=device_user_id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_expires_at=datetime.utcnow()
                    + timedelta(seconds=token_data.get("expires_in", 86400)),
                )

                # Store connection
                connection_key = f"{user_id}:{device.value}"
                self.active_connections[connection_key] = connection

                logger.info(f"Successfully connected {device.value} for user {user_id}")
                return connection
        else:
            raise ValueError(f"Unsupported device: {device}")

    async def sync_user_data(
        self,
        user_id: str,
        device: WearableDevice,
        days_back: int = 7,
        force_refresh: bool = False,
    ) -> SyncResult:
        """
        Synchronize data for a user from a specific device

        Args:
            user_id: NGX user ID
            device: Wearable device to sync from
            days_back: Number of days of historical data to sync
            force_refresh: Force refresh even if recently synced

        Returns:
            Synchronization result
        """
        connection_key = f"{user_id}:{device.value}"
        connection = self.active_connections.get(connection_key)

        if not connection or not connection.is_active:
            return SyncResult(
                success=False,
                device=device,
                user_id=user_id,
                metrics_synced=0,
                error_message="No active connection found for device",
            )

        try:
            if device == WearableDevice.WHOOP:
                return await self._sync_whoop_data(connection, days_back, force_refresh)
            elif device == WearableDevice.OURA_RING:
                return await self._sync_oura_data(connection, days_back, force_refresh)
            else:
                return SyncResult(
                    success=False,
                    device=device,
                    user_id=user_id,
                    metrics_synced=0,
                    error_message=f"Sync not implemented for {device.value}",
                )
        except Exception as e:
            logger.error(
                f"Error syncing {device.value} data for user {user_id}: {str(e)}"
            )
            return SyncResult(
                success=False,
                device=device,
                user_id=user_id,
                metrics_synced=0,
                error_message=str(e),
            )

    async def _sync_whoop_data(
        self, connection: DeviceConnection, days_back: int, force_refresh: bool
    ) -> SyncResult:
        """Sync data specifically from WHOOP device"""
        config = self.device_adapters[WearableDevice.WHOOP]

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        # If not forcing refresh, only sync since last sync
        if not force_refresh and connection.last_sync:
            start_date = max(start_date, connection.last_sync)

        metrics_synced = 0
        recovery_records = 0
        sleep_records = 0
        workout_records = 0

        async with WHOOPAdapter(config) as whoop:
            # Set tokens from stored connection
            whoop.access_token = connection.access_token
            whoop.refresh_token = connection.refresh_token
            whoop.token_expires_at = connection.token_expires_at

            try:
                # Sync recovery data
                recovery_data = await whoop.get_recovery_data(
                    start_date, end_date, limit=50
                )
                for recovery in recovery_data:
                    normalized_recovery = self.normalizer.normalize_recovery_data(
                        WearableDevice.WHOOP, recovery
                    )
                    metrics = self.normalizer.normalize_to_metrics(
                        WearableDevice.WHOOP, recovery, "recovery"
                    )

                    # Store metrics (integrate with NGX storage system)
                    await self._store_metrics(connection.user_id, metrics)
                    await self._store_recovery_data(
                        connection.user_id, normalized_recovery
                    )

                    metrics_synced += len(metrics)
                    recovery_records += 1

                # Sync sleep data
                sleep_data = await whoop.get_sleep_data(start_date, end_date, limit=50)
                for sleep in sleep_data:
                    normalized_sleep = self.normalizer.normalize_sleep_data(
                        WearableDevice.WHOOP, sleep
                    )
                    metrics = self.normalizer.normalize_to_metrics(
                        WearableDevice.WHOOP, sleep, "sleep"
                    )

                    # Store metrics
                    await self._store_metrics(connection.user_id, metrics)
                    await self._store_sleep_data(connection.user_id, normalized_sleep)

                    metrics_synced += len(metrics)
                    sleep_records += 1

                # Sync workout data
                workout_data = await whoop.get_workout_data(
                    start_date, end_date, limit=50
                )
                for workout in workout_data:
                    normalized_workout = self.normalizer.normalize_workout_data(
                        WearableDevice.WHOOP, workout
                    )
                    metrics = self.normalizer.normalize_to_metrics(
                        WearableDevice.WHOOP, workout, "workout"
                    )

                    # Store metrics
                    await self._store_metrics(connection.user_id, metrics)
                    await self._store_workout_data(
                        connection.user_id, normalized_workout
                    )

                    metrics_synced += len(metrics)
                    workout_records += 1

                # Update connection with new tokens if refreshed
                if whoop.access_token != connection.access_token:
                    connection.access_token = whoop.access_token
                    connection.refresh_token = whoop.refresh_token
                    connection.token_expires_at = whoop.token_expires_at

                # Update last sync time
                connection.last_sync = datetime.utcnow()
                connection.updated_at = datetime.utcnow()

                logger.info(
                    f"Successfully synced WHOOP data for user {connection.user_id}: "
                    f"{metrics_synced} metrics, {recovery_records} recovery, "
                    f"{sleep_records} sleep, {workout_records} workouts"
                )

                return SyncResult(
                    success=True,
                    device=WearableDevice.WHOOP,
                    user_id=connection.user_id,
                    metrics_synced=metrics_synced,
                    recovery_records=recovery_records,
                    sleep_records=sleep_records,
                    workout_records=workout_records,
                )

            except Exception as e:
                logger.error(f"Error during WHOOP sync: {str(e)}")
                raise

    async def _sync_oura_data(
        self, connection: DeviceConnection, days_back: int, force_refresh: bool
    ) -> SyncResult:
        """Sync data specifically from Oura Ring device"""
        config = self.device_adapters[WearableDevice.OURA_RING]

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        # If not forcing refresh, only sync since last sync
        if not force_refresh and connection.last_sync:
            start_date = max(start_date, connection.last_sync)

        metrics_synced = 0
        recovery_records = 0
        sleep_records = 0
        workout_records = 0

        async with OuraAdapter(config) as oura:
            # Set tokens from stored connection
            oura.access_token = connection.access_token
            oura.refresh_token = connection.refresh_token
            oura.token_expires_at = connection.token_expires_at

            try:
                # Sync readiness data (similar to recovery)
                readiness_data = await oura.get_readiness_data(start_date, end_date)
                for readiness in readiness_data:
                    normalized_recovery = self.normalizer.normalize_recovery_data(
                        WearableDevice.OURA_RING, readiness
                    )
                    metrics = self.normalizer.normalize_to_metrics(
                        WearableDevice.OURA_RING, readiness, "recovery"
                    )

                    # Store metrics
                    await self._store_metrics(connection.user_id, metrics)
                    await self._store_recovery_data(
                        connection.user_id, normalized_recovery
                    )

                    metrics_synced += len(metrics)
                    recovery_records += 1

                # Sync sleep data
                sleep_data = await oura.get_sleep_data(start_date, end_date)
                for sleep in sleep_data:
                    normalized_sleep = self.normalizer.normalize_sleep_data(
                        WearableDevice.OURA_RING, sleep
                    )
                    metrics = self.normalizer.normalize_to_metrics(
                        WearableDevice.OURA_RING, sleep, "sleep"
                    )

                    # Store metrics
                    await self._store_metrics(connection.user_id, metrics)
                    await self._store_sleep_data(connection.user_id, normalized_sleep)

                    metrics_synced += len(metrics)
                    sleep_records += 1

                # Sync activity data
                activity_data = await oura.get_activity_data(start_date, end_date)
                for activity in activity_data:
                    # Convert activity to metrics
                    metrics = self.normalizer.normalize_to_metrics(
                        WearableDevice.OURA_RING, activity, "activity"
                    )

                    # Store metrics
                    await self._store_metrics(connection.user_id, metrics)
                    metrics_synced += len(metrics)

                # Sync workout data
                workout_data = await oura.get_workout_data(start_date, end_date)
                for workout in workout_data:
                    normalized_workout = self.normalizer.normalize_workout_data(
                        WearableDevice.OURA_RING, workout
                    )
                    metrics = self.normalizer.normalize_to_metrics(
                        WearableDevice.OURA_RING, workout, "workout"
                    )

                    # Store metrics
                    await self._store_metrics(connection.user_id, metrics)
                    await self._store_workout_data(
                        connection.user_id, normalized_workout
                    )

                    metrics_synced += len(metrics)
                    workout_records += 1

                # Update connection with new tokens if refreshed
                if oura.access_token != connection.access_token:
                    connection.access_token = oura.access_token
                    connection.refresh_token = oura.refresh_token
                    connection.token_expires_at = oura.token_expires_at

                # Update last sync time
                connection.last_sync = datetime.utcnow()
                connection.updated_at = datetime.utcnow()

                logger.info(
                    f"Successfully synced Oura data for user {connection.user_id}: "
                    f"{metrics_synced} metrics, {recovery_records} readiness, "
                    f"{sleep_records} sleep, {workout_records} workouts"
                )

                return SyncResult(
                    success=True,
                    device=WearableDevice.OURA_RING,
                    user_id=connection.user_id,
                    metrics_synced=metrics_synced,
                    recovery_records=recovery_records,
                    sleep_records=sleep_records,
                    workout_records=workout_records,
                )

            except Exception as e:
                logger.error(f"Error during Oura sync: {str(e)}")
                raise

    async def sync_all_users(self, days_back: int = 1) -> List[SyncResult]:
        """
        Sync data for all connected users

        Args:
            days_back: Number of days to sync (default 1 for daily sync)

        Returns:
            List of sync results for all users
        """
        results = []

        # Group connections by user
        user_connections = {}
        for connection_key, connection in self.active_connections.items():
            if connection.is_active:
                if connection.user_id not in user_connections:
                    user_connections[connection.user_id] = []
                user_connections[connection.user_id].append(connection)

        # Sync each user's devices
        for user_id, connections in user_connections.items():
            for connection in connections:
                try:
                    result = await self.sync_user_data(
                        user_id, connection.device, days_back
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(
                        f"Failed to sync {connection.device.value} for user {user_id}: {str(e)}"
                    )
                    results.append(
                        SyncResult(
                            success=False,
                            device=connection.device,
                            user_id=user_id,
                            metrics_synced=0,
                            error_message=str(e),
                        )
                    )

        return results

    async def get_user_connections(self, user_id: str) -> List[DeviceConnection]:
        """
        Get all device connections for a user

        Args:
            user_id: NGX user ID

        Returns:
            List of active device connections
        """
        connections = []
        for connection_key, connection in self.active_connections.items():
            if connection.user_id == user_id and connection.is_active:
                connections.append(connection)
        return connections

    async def disconnect_device(self, user_id: str, device: WearableDevice) -> bool:
        """
        Disconnect a device for a user

        Args:
            user_id: NGX user ID
            device: Device to disconnect

        Returns:
            True if successfully disconnected
        """
        connection_key = f"{user_id}:{device.value}"
        connection = self.active_connections.get(connection_key)

        if connection:
            connection.is_active = False
            connection.updated_at = datetime.utcnow()
            logger.info(f"Disconnected {device.value} for user {user_id}")
            return True

        return False

    async def _store_metrics(self, user_id: str, metrics: List[NormalizedMetric]):
        """
        Store normalized metrics in NGX system

        Args:
            user_id: NGX user ID
            metrics: List of normalized metrics to store
        """
        # TODO: Integrate with NGX storage system (Supabase)
        # This would typically save to the database
        logger.debug(f"Storing {len(metrics)} metrics for user {user_id}")

        # For now, just log the metrics
        for metric in metrics:
            logger.debug(
                f"Metric: {metric.metric_type.value} = {metric.value} {metric.unit} "
                f"from {metric.device.value} at {metric.timestamp}"
            )

    async def _store_recovery_data(
        self, user_id: str, recovery: NormalizedRecoveryData
    ):
        """Store normalized recovery data"""
        logger.debug(
            f"Storing recovery data for user {user_id}: score={recovery.recovery_score}"
        )

    async def _store_sleep_data(self, user_id: str, sleep: NormalizedSleepData):
        """Store normalized sleep data"""
        logger.debug(
            f"Storing sleep data for user {user_id}: duration={sleep.total_duration_minutes}min"
        )

    async def _store_workout_data(self, user_id: str, workout: NormalizedWorkoutData):
        """Store normalized workout data"""
        logger.debug(
            f"Storing workout data for user {user_id}: {workout.sport_type}, "
            f"duration={workout.duration_minutes}min"
        )

    def get_supported_devices(self) -> List[WearableDevice]:
        """Get list of supported wearable devices"""
        return list(self.device_adapters.keys())

    async def process_apple_health_webhook(
        self,
        user_id: str,
        webhook_data: Dict[str, Any],
        signature: Optional[str] = None,
    ) -> SyncResult:
        """
        Process incoming Apple Health data from webhook/shortcuts

        Args:
            user_id: NGX user ID
            webhook_data: Data from iOS Shortcuts or webhook
            signature: Optional webhook signature for verification

        Returns:
            Sync result with processed metrics
        """
        if WearableDevice.APPLE_WATCH not in self.device_adapters:
            raise ValueError("Apple Health not configured")

        config = self.device_adapters[WearableDevice.APPLE_WATCH]
        adapter = AppleHealthAdapter(config)

        # Verify signature if provided
        if signature and config.webhook_secret:
            payload = json.dumps(webhook_data).encode()
            if not adapter.verify_webhook_signature(payload, signature):
                raise ValueError("Invalid webhook signature")

        # Parse the data
        parsed_items = adapter.parse_healthkit_data(webhook_data)

        metrics_synced = 0
        recovery_records = 0
        sleep_records = 0
        workout_records = 0

        # Group items by type
        samples = []
        workouts = []
        sleep_data = []

        for item in parsed_items:
            if hasattr(item, "type"):  # HealthKitSample
                samples.append(item)
            elif hasattr(item, "activity_type"):  # HealthKitWorkout
                workouts.append(item)
            elif hasattr(item, "sleep_state"):  # HealthKitSleep
                sleep_data.append(item)

        # Process samples
        if samples:
            # Get latest activity data
            activity = adapter.aggregate_daily_activity(samples, datetime.utcnow())

            # Normalize and store
            normalized_recovery = self.normalizer.normalize_recovery_data(
                WearableDevice.APPLE_WATCH, activity
            )
            recovery_metrics = self.normalizer.normalize_to_metrics(
                WearableDevice.APPLE_WATCH, activity, "recovery"
            )

            await self._store_metrics(user_id, recovery_metrics)
            await self._store_recovery_data(user_id, normalized_recovery)

            metrics_synced += len(recovery_metrics)
            recovery_records += 1

            # Also process individual samples
            sample_metrics = self.normalizer.normalize_to_metrics(
                WearableDevice.APPLE_WATCH, samples, "samples"
            )
            await self._store_metrics(user_id, sample_metrics)
            metrics_synced += len(sample_metrics)

        # Process sleep data
        for sleep in sleep_data:
            normalized_sleep = self.normalizer.normalize_sleep_data(
                WearableDevice.APPLE_WATCH, sleep
            )
            sleep_metrics = self.normalizer.normalize_to_metrics(
                WearableDevice.APPLE_WATCH, sleep, "sleep"
            )

            await self._store_metrics(user_id, sleep_metrics)
            await self._store_sleep_data(user_id, normalized_sleep)

            metrics_synced += len(sleep_metrics)
            sleep_records += 1

        # Process workouts
        for workout in workouts:
            normalized_workout = self.normalizer.normalize_workout_data(
                WearableDevice.APPLE_WATCH, workout
            )
            workout_metrics = self.normalizer.normalize_to_metrics(
                WearableDevice.APPLE_WATCH, workout, "workout"
            )

            await self._store_metrics(user_id, workout_metrics)
            await self._store_workout_data(user_id, normalized_workout)

            metrics_synced += len(workout_metrics)
            workout_records += 1

        # Create/update connection
        connection_key = f"{user_id}:{WearableDevice.APPLE_WATCH.value}"
        if connection_key not in self.active_connections:
            self.active_connections[connection_key] = DeviceConnection(
                user_id=user_id,
                device=WearableDevice.APPLE_WATCH,
                device_user_id=f"apple_{user_id}",
                access_token="webhook",  # No OAuth token for Apple
                refresh_token=None,
                is_active=True,
            )

        connection = self.active_connections[connection_key]
        connection.last_sync = datetime.utcnow()
        connection.updated_at = datetime.utcnow()

        logger.info(
            f"Processed Apple Health webhook for user {user_id}: "
            f"{metrics_synced} metrics, {recovery_records} recovery, "
            f"{sleep_records} sleep, {workout_records} workouts"
        )

        return SyncResult(
            success=True,
            device=WearableDevice.APPLE_WATCH,
            user_id=user_id,
            metrics_synced=metrics_synced,
            recovery_records=recovery_records,
            sleep_records=sleep_records,
            workout_records=workout_records,
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the wearable integration service

        Returns:
            Health check status
        """
        health_status = {
            "service": "wearable_integration",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "active_connections": len(
                [c for c in self.active_connections.values() if c.is_active]
            ),
            "supported_devices": [
                device.value for device in self.get_supported_devices()
            ],
            "device_status": {},
        }

        # Check each device adapter
        for device in self.get_supported_devices():
            try:
                if device == WearableDevice.WHOOP:
                    # Test WHOOP connection
                    config = self.device_adapters[device]
                    async with WHOOPAdapter(config) as whoop:
                        # Just test if we can create the adapter
                        health_status["device_status"][device.value] = "available"
                else:
                    health_status["device_status"][device.value] = "configured"
            except Exception as e:
                health_status["device_status"][device.value] = f"error: {str(e)}"
                health_status["status"] = "degraded"

        return health_status


# Example usage and testing
async def example_service_usage():
    """Example of how to use the wearable integration service"""

    # Configuration for the service
    config = {
        "whoop": {
            "client_id": "your_whoop_client_id",
            "client_secret": "your_whoop_client_secret",
            "redirect_uri": "http://localhost:8000/auth/whoop/callback",
            "sandbox": True,
        }
    }

    # Initialize service
    service = WearableIntegrationService(config)

    # Check health
    health = await service.health_check()
    print(f"Service health: {health}")

    # Get authorization URL for a user
    user_id = "ngx_user_123"
    auth_url = await service.get_authorization_url(WearableDevice.WHOOP, user_id)
    print(f"Authorization URL: {auth_url}")

    # After user authorizes and you get the callback...
    # authorization_code = "code_from_callback"
    # connection = await service.complete_authorization(
    #     WearableDevice.WHOOP, authorization_code, user_id
    # )
    # print(f"Connected: {connection}")

    # Sync user data
    # sync_result = await service.sync_user_data(user_id, WearableDevice.WHOOP, days_back=7)
    # print(f"Sync result: {sync_result}")


if __name__ == "__main__":
    asyncio.run(example_service_usage())

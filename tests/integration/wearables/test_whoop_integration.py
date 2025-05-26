"""
Integration tests for WHOOP wearable device integration
Tests the complete flow from OAuth to data synchronization
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from integrations.wearables.adapters.whoop import (
    WHOOPAdapter,
    WHOOPConfig,
    WHOOPRecovery,
    WHOOPSleep,
    WHOOPWorkout,
)
from integrations.wearables.service import WearableIntegrationService
from integrations.wearables.normalizer import WearableDataNormalizer, WearableDevice
from app.main import app


class TestWHOOPIntegration:
    """Test WHOOP integration functionality"""

    @pytest.fixture
    def whoop_config(self):
        """Test WHOOP configuration"""
        return WHOOPConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/auth/whoop/callback",
            sandbox=True,
        )

    @pytest.fixture
    def mock_whoop_recovery(self):
        """Mock WHOOP recovery data"""
        return WHOOPRecovery(
            recovery_id="rec_123",
            user_id="whoop_user_456",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            score={"recovery_score": 85.5},
            heart_rate_variability={"rmssd_milli": 45.2},
            resting_heart_rate={"bpm": 52},
            sleep_need={
                "baseline_milli": 28800000,  # 8 hours
                "need_from_sleep_debt_milli": 1800000,  # 30 min
                "need_from_recent_strain_milli": 900000,  # 15 min
                "need_from_recent_nap_milli": 0,
            },
        )

    @pytest.fixture
    def mock_whoop_sleep(self):
        """Mock WHOOP sleep data"""
        return WHOOPSleep(
            sleep_id="sleep_123",
            user_id="whoop_user_456",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            start=datetime.utcnow() - timedelta(hours=8),
            end=datetime.utcnow(),
            timezone_offset="-08:00",
            score={"sleep_performance_percentage": 88.0},
            stage_summary={
                "total_in_bed_time_milli": 28800000,  # 8 hours
                "total_awake_time_milli": 1800000,  # 30 min
                "total_no_data_time_milli": 0,
                "total_slow_wave_sleep_time_milli": 7200000,  # 2 hours
                "total_rem_sleep_time_milli": 5400000,  # 1.5 hours
                "total_light_sleep_time_milli": 14400000,  # 4 hours
            },
            sleep_need={"baseline_milli": 28800000},
        )

    @pytest.fixture
    def mock_whoop_workout(self):
        """Mock WHOOP workout data"""
        return WHOOPWorkout(
            workout_id="workout_123",
            user_id="whoop_user_456",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            start=datetime.utcnow() - timedelta(hours=1),
            end=datetime.utcnow(),
            timezone_offset="-08:00",
            sport_id=0,  # Running
            score={
                "strain": 15.2,
                "average_heart_rate": 155,
                "max_heart_rate": 175,
                "kilojoule": 2500,  # ~600 calories
            },
            zone_duration={
                "zone_zero_milli": 0,
                "zone_one_milli": 600000,  # 10 min
                "zone_two_milli": 1800000,  # 30 min
                "zone_three_milli": 1200000,  # 20 min
                "zone_four_milli": 0,
                "zone_five_milli": 0,
            },
        )


class TestWHOOPAdapter:
    """Test WHOOP API adapter functionality"""

    @pytest.mark.asyncio
    async def test_auth_url_generation(self, whoop_config):
        """Test OAuth URL generation"""
        async with WHOOPAdapter(whoop_config) as whoop:
            auth_url = whoop.get_auth_url(state="test_state")

            assert "api-7.whoop.com/oauth/authorize" in auth_url
            assert "client_id=test_client_id" in auth_url
            assert "response_type=code" in auth_url
            assert "state=test_state" in auth_url
            assert "scope=" in auth_url

    @pytest.mark.asyncio
    async def test_token_exchange_success(self, whoop_config):
        """Test successful token exchange"""
        mock_token_response = {
            "access_token": "access_123",
            "refresh_token": "refresh_123",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        async with WHOOPAdapter(whoop_config) as whoop:
            with patch.object(whoop.session, "post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value=mock_token_response)
                mock_post.return_value.__aenter__.return_value = mock_response

                result = await whoop.exchange_code_for_tokens("test_code")

                assert result["access_token"] == "access_123"
                assert whoop.access_token == "access_123"
                assert whoop.refresh_token == "refresh_123"
                assert whoop.token_expires_at is not None

    @pytest.mark.asyncio
    async def test_token_exchange_failure(self, whoop_config):
        """Test failed token exchange"""
        async with WHOOPAdapter(whoop_config) as whoop:
            with patch.object(whoop.session, "post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 400
                mock_response.text = AsyncMock(return_value="Invalid code")
                mock_post.return_value.__aenter__.return_value = mock_response

                with pytest.raises(Exception, match="Token exchange failed"):
                    await whoop.exchange_code_for_tokens("invalid_code")

    @pytest.mark.asyncio
    async def test_get_recovery_data(self, whoop_config, mock_whoop_recovery):
        """Test recovery data retrieval"""
        mock_api_response = {
            "records": [
                {
                    "id": mock_whoop_recovery.recovery_id,
                    "user_id": mock_whoop_recovery.user_id,
                    "created_at": mock_whoop_recovery.created_at.isoformat() + "Z",
                    "updated_at": mock_whoop_recovery.updated_at.isoformat() + "Z",
                    "score": mock_whoop_recovery.score,
                    "heart_rate_variability_rmssd_milli": mock_whoop_recovery.heart_rate_variability,
                    "resting_heart_rate": mock_whoop_recovery.resting_heart_rate,
                    "sleep_need": mock_whoop_recovery.sleep_need,
                }
            ]
        }

        async with WHOOPAdapter(whoop_config) as whoop:
            whoop.access_token = "test_token"
            whoop.token_expires_at = datetime.utcnow() + timedelta(hours=1)

            with patch.object(whoop, "_make_request", return_value=mock_api_response):
                recoveries = await whoop.get_recovery_data(limit=1)

                assert len(recoveries) == 1
                assert recoveries[0].recovery_id == mock_whoop_recovery.recovery_id
                assert recoveries[0].score == mock_whoop_recovery.score


class TestWearableDataNormalizer:
    """Test data normalization functionality"""

    def test_normalize_whoop_recovery(self, mock_whoop_recovery):
        """Test WHOOP recovery data normalization"""
        normalizer = WearableDataNormalizer()

        normalized = normalizer.normalize_recovery_data(
            WearableDevice.WHOOP, mock_whoop_recovery
        )

        assert normalized.recovery_score == 85.5
        assert normalized.hrv_score == 45.2
        assert normalized.resting_heart_rate == 52
        assert normalized.sleep_need_hours == 8.75  # 8h + 30min + 15min
        assert normalized.device == WearableDevice.WHOOP

    def test_normalize_whoop_sleep(self, mock_whoop_sleep):
        """Test WHOOP sleep data normalization"""
        normalizer = WearableDataNormalizer()

        normalized = normalizer.normalize_sleep_data(
            WearableDevice.WHOOP, mock_whoop_sleep
        )

        assert normalized.sleep_score == 88.0
        assert normalized.total_duration_minutes == 480  # 8 hours
        assert normalized.sleep_efficiency_percent > 0
        assert normalized.deep_sleep_minutes == 120  # 2 hours
        assert normalized.rem_sleep_minutes == 90  # 1.5 hours
        assert normalized.light_sleep_minutes == 240  # 4 hours
        assert normalized.device == WearableDevice.WHOOP

    def test_normalize_whoop_workout(self, mock_whoop_workout):
        """Test WHOOP workout data normalization"""
        normalizer = WearableDataNormalizer()

        normalized = normalizer.normalize_workout_data(
            WearableDevice.WHOOP, mock_whoop_workout
        )

        assert normalized.workout_strain == 15.2
        assert normalized.duration_minutes == 60  # 1 hour
        assert normalized.average_heart_rate == 155
        assert normalized.max_heart_rate == 175
        assert normalized.sport_type == "Running"
        assert normalized.calories_burned > 0  # Converted from kilojoules
        assert normalized.device == WearableDevice.WHOOP

    def test_recovery_to_metrics(self, mock_whoop_recovery):
        """Test conversion of recovery data to individual metrics"""
        normalizer = WearableDataNormalizer()

        normalized = normalizer.normalize_recovery_data(
            WearableDevice.WHOOP, mock_whoop_recovery
        )

        metrics = normalizer._recovery_to_metrics(normalized)

        # Should have 3 metrics: recovery_score, hrv, rhr
        assert len(metrics) == 3

        metric_types = {m.metric_type.value for m in metrics}
        assert "recovery_score" in metric_types
        assert "hrv" in metric_types
        assert "rhr" in metric_types

        # Check units
        for metric in metrics:
            if metric.metric_type.value == "recovery_score":
                assert metric.unit == "percentage"
                assert metric.value == 85.5
            elif metric.metric_type.value == "hrv":
                assert metric.unit == "milliseconds"
                assert metric.value == 45.2
            elif metric.metric_type.value == "rhr":
                assert metric.unit == "bpm"
                assert metric.value == 52


class TestWearableIntegrationService:
    """Test wearable integration service"""

    @pytest.fixture
    def service_config(self):
        """Test service configuration"""
        return {
            "whoop": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uri": "http://localhost:8000/auth/whoop/callback",
                "sandbox": True,
            }
        }

    @pytest.fixture
    def integration_service(self, service_config):
        """Test integration service instance"""
        return WearableIntegrationService(service_config)

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, integration_service):
        """Test authorization URL generation via service"""
        auth_url = await integration_service.get_authorization_url(
            WearableDevice.WHOOP, "test_user_123", "test_state"
        )

        assert "oauth/authorize" in auth_url
        assert "test_user_123:test_state" in auth_url or "test_state" in auth_url

    @pytest.mark.asyncio
    async def test_complete_authorization(self, integration_service):
        """Test completing authorization flow"""
        mock_token_data = {
            "access_token": "access_123",
            "refresh_token": "refresh_123",
            "expires_in": 3600,
        }

        mock_profile = {"user_id": "whoop_user_456"}

        with patch("integrations.wearables.adapters.whoop.WHOOPAdapter") as MockAdapter:
            mock_adapter = AsyncMock()
            mock_adapter.exchange_code_for_tokens.return_value = mock_token_data
            mock_adapter.get_user_profile.return_value = mock_profile
            MockAdapter.return_value.__aenter__.return_value = mock_adapter

            connection = await integration_service.complete_authorization(
                WearableDevice.WHOOP, "test_code", "test_user_123"
            )

            assert connection.user_id == "test_user_123"
            assert connection.device == WearableDevice.WHOOP
            assert connection.device_user_id == "whoop_user_456"
            assert connection.is_active is True

    @pytest.mark.asyncio
    async def test_health_check(self, integration_service):
        """Test service health check"""
        health = await integration_service.health_check()

        assert health["service"] == "wearable_integration"
        assert "status" in health
        assert "supported_devices" in health
        assert "whoop" in health["supported_devices"]
        assert "device_status" in health

    def test_get_supported_devices(self, integration_service):
        """Test getting supported devices"""
        devices = integration_service.get_supported_devices()

        assert len(devices) > 0
        assert WearableDevice.WHOOP in devices


class TestWearableAPI:
    """Test wearable API endpoints"""

    @pytest.fixture
    def client(self):
        """Test client for API endpoints"""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_user(self):
        """Mock authenticated user"""
        return "test_user_123"

    def test_get_supported_devices(self, client):
        """Test supported devices endpoint"""
        with patch("app.routers.wearables.get_current_user", return_value="test_user"):
            with patch("app.routers.wearables.get_wearable_service") as mock_service:
                mock_service_instance = MagicMock()
                mock_service_instance.get_supported_devices.return_value = [
                    WearableDevice.WHOOP
                ]
                mock_service.return_value = mock_service_instance

                response = client.get("/wearables/devices")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "whoop" in [d for d in data["devices"]]

    def test_authorize_device(self, client):
        """Test device authorization endpoint"""
        with patch("app.routers.wearables.get_current_user", return_value="test_user"):
            with patch("app.routers.wearables.get_wearable_service") as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_authorization_url.return_value = (
                    "https://test-auth-url.com"
                )
                mock_service.return_value = mock_service_instance

                response = client.post(
                    "/wearables/auth/authorize",
                    json={"device": "whoop", "state": "test_state"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "authorization_url" in data

    def test_get_service_health(self, client):
        """Test service health endpoint"""
        mock_health = {
            "service": "wearable_integration",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "active_connections": 0,
            "supported_devices": ["whoop"],
            "device_status": {"whoop": "available"},
        }

        with patch("app.routers.wearables.get_wearable_service") as mock_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.health_check.return_value = mock_health
            mock_service.return_value = mock_service_instance

            response = client.get("/wearables/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "healthy"


class TestEndToEndFlow:
    """Test complete end-to-end wearable integration flow"""

    @pytest.mark.asyncio
    async def test_complete_whoop_flow(self):
        """Test complete WHOOP integration flow"""
        # This test would require actual WHOOP API access or sophisticated mocking
        # For now, we'll test the flow components separately

        config = {
            "whoop": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uri": "http://localhost:8000/auth/whoop/callback",
                "sandbox": True,
            }
        }

        service = WearableIntegrationService(config)
        normalizer = WearableDataNormalizer()

        # Test 1: Service initialization
        assert service is not None
        assert WearableDevice.WHOOP in service.get_supported_devices()

        # Test 2: Authorization URL generation
        auth_url = await service.get_authorization_url(
            WearableDevice.WHOOP, "test_user_123"
        )
        assert "oauth/authorize" in auth_url

        # Test 3: Data normalization
        mock_recovery = WHOOPRecovery(
            recovery_id="rec_123",
            user_id="whoop_user_456",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            score={"recovery_score": 85},
            heart_rate_variability={"rmssd_milli": 45.2},
            resting_heart_rate={"bpm": 52},
            sleep_need={"baseline_milli": 28800000},
        )

        normalized = normalizer.normalize_recovery_data(
            WearableDevice.WHOOP, mock_recovery
        )

        assert normalized.recovery_score == 85
        assert normalized.device == WearableDevice.WHOOP

        # Test 4: Metric conversion
        metrics = normalizer.normalize_to_metrics(
            WearableDevice.WHOOP, mock_recovery, "recovery"
        )

        assert len(metrics) > 0
        assert all(m.device == WearableDevice.WHOOP for m in metrics)


# Performance Tests
class TestWearablePerformance:
    """Test performance aspects of wearable integration"""

    @pytest.mark.asyncio
    async def test_large_data_sync_performance(self):
        """Test performance with large amounts of data"""
        normalizer = WearableDataNormalizer()

        # Generate mock data for 30 days
        mock_data = []
        for i in range(30):
            mock_recovery = WHOOPRecovery(
                recovery_id=f"rec_{i}",
                user_id="test_user",
                created_at=datetime.utcnow() - timedelta(days=i),
                updated_at=datetime.utcnow() - timedelta(days=i),
                score={"recovery_score": 85 + (i % 20)},
                heart_rate_variability={"rmssd_milli": 45.2},
                resting_heart_rate={"bpm": 52},
                sleep_need={"baseline_milli": 28800000},
            )
            mock_data.append(mock_recovery)

        # Time the normalization process
        start_time = datetime.utcnow()

        all_metrics = []
        for recovery in mock_data:
            metrics = normalizer.normalize_to_metrics(
                WearableDevice.WHOOP, recovery, "recovery"
            )
            all_metrics.extend(metrics)

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        # Should process 30 days of data quickly
        assert processing_time < 1.0  # Less than 1 second
        assert len(all_metrics) == 90  # 3 metrics per recovery × 30 days

        print(f"Processed {len(all_metrics)} metrics in {processing_time:.3f} seconds")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

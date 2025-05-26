"""
NGX Agents Wearable Integration Demo
Demonstrates how to integrate and use wearable device data in NGX Agents
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from integrations.wearables.service import WearableIntegrationService
from integrations.wearables.adapters.whoop import WHOOPConfig
from integrations.wearables.normalizer import WearableDevice, WearableDataNormalizer


async def demo_whoop_integration():
    """Demonstrate WHOOP integration workflow"""

    print("🚀 NGX Agents - WHOOP Integration Demo")
    print("=" * 50)

    # 1. Setup configuration
    config = {
        "whoop": {
            "client_id": os.getenv("WHOOP_CLIENT_ID", "your_whoop_client_id"),
            "client_secret": os.getenv(
                "WHOOP_CLIENT_SECRET", "your_whoop_client_secret"
            ),
            "redirect_uri": os.getenv(
                "WHOOP_REDIRECT_URI",
                "http://localhost:8000/wearables/auth/whoop/callback",
            ),
            "sandbox": True,  # Use sandbox for testing
        }
    }

    # 2. Initialize service
    print("\n📱 Initializing Wearable Integration Service...")
    service = WearableIntegrationService(config)

    # 3. Check service health
    print("\n🔍 Checking service health...")
    health = await service.health_check()
    print(f"Service Status: {health['status']}")
    print(f"Supported Devices: {health['supported_devices']}")
    print(f"Active Connections: {health['active_connections']}")

    # 4. Generate authorization URL
    print("\n🔐 Generating authorization URL...")
    user_id = "demo_user_123"

    try:
        auth_url = await service.get_authorization_url(
            WearableDevice.WHOOP, user_id, "demo_state"
        )
        print(f"Authorization URL: {auth_url}")
        print("\n📝 In a real application:")
        print("1. User would visit this URL")
        print("2. Grant permissions to NGX Agents")
        print("3. Get redirected back with authorization code")

    except Exception as e:
        print(f"❌ Error generating auth URL: {e}")
        return

    # 5. Simulate OAuth completion (normally done via callback)
    print("\n🔄 Simulating OAuth completion...")
    print("(In real usage, this happens automatically via webhook)")

    # For demo purposes, we'll show what would happen after OAuth
    print("\n✅ After successful OAuth, the service would:")
    print("- Store access and refresh tokens")
    print("- Create device connection")
    print("- Enable automatic data synchronization")

    # 6. Demonstrate data normalization
    print("\n🔄 Demonstrating data normalization...")
    await demo_data_normalization()

    # 7. Show supported operations
    print("\n🛠️ Available Operations:")
    print("- Get user connections: service.get_user_connections(user_id)")
    print("- Sync device data: service.sync_user_data(user_id, device, days_back=7)")
    print("- Disconnect device: service.disconnect_device(user_id, device)")
    print("- Bulk sync all users: service.sync_all_users()")


async def demo_data_normalization():
    """Demonstrate data normalization functionality"""

    print("\n📊 Data Normalization Demo")
    print("-" * 30)

    normalizer = WearableDataNormalizer()

    # Create mock WHOOP data for demonstration
    from integrations.wearables.adapters.whoop import (
        WHOOPRecovery,
        WHOOPSleep,
        WHOOPWorkout,
    )

    # 1. Recovery data example
    print("\n💪 Recovery Data Normalization:")
    mock_recovery = WHOOPRecovery(
        recovery_id="rec_demo_123",
        user_id="whoop_user_456",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        score={"recovery_score": 87.5},
        heart_rate_variability={"rmssd_milli": 42.8},
        resting_heart_rate={"bpm": 48},
        sleep_need={
            "baseline_milli": 28800000,  # 8 hours
            "need_from_sleep_debt_milli": 1800000,  # 30 minutes
            "need_from_recent_strain_milli": 900000,  # 15 minutes
            "need_from_recent_nap_milli": 0,
        },
    )

    normalized_recovery = normalizer.normalize_recovery_data(
        WearableDevice.WHOOP, mock_recovery
    )

    print(f"  Recovery Score: {normalized_recovery.recovery_score}%")
    print(f"  HRV Score: {normalized_recovery.hrv_score}ms")
    print(f"  Resting HR: {normalized_recovery.resting_heart_rate} bpm")
    print(f"  Sleep Need: {normalized_recovery.sleep_need_hours:.1f} hours")

    # 2. Sleep data example
    print("\n😴 Sleep Data Normalization:")
    mock_sleep = WHOOPSleep(
        sleep_id="sleep_demo_123",
        user_id="whoop_user_456",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        start=datetime.utcnow() - timedelta(hours=8),
        end=datetime.utcnow(),
        timezone_offset="-08:00",
        score={"sleep_performance_percentage": 89.2},
        stage_summary={
            "total_in_bed_time_milli": 28800000,  # 8 hours
            "total_awake_time_milli": 1200000,  # 20 minutes
            "total_no_data_time_milli": 0,
            "total_slow_wave_sleep_time_milli": 5400000,  # 1.5 hours deep
            "total_rem_sleep_time_milli": 7200000,  # 2 hours REM
            "total_light_sleep_time_milli": 14400000,  # 4 hours light
        },
        sleep_need={"baseline_milli": 28800000},
    )

    normalized_sleep = normalizer.normalize_sleep_data(WearableDevice.WHOOP, mock_sleep)

    print(f"  Sleep Score: {normalized_sleep.sleep_score}%")
    print(f"  Total Duration: {normalized_sleep.total_duration_minutes:.0f} minutes")
    print(f"  Sleep Efficiency: {normalized_sleep.sleep_efficiency_percent:.1f}%")
    print(f"  Deep Sleep: {normalized_sleep.deep_sleep_minutes:.0f} minutes")
    print(f"  REM Sleep: {normalized_sleep.rem_sleep_minutes:.0f} minutes")
    print(f"  Light Sleep: {normalized_sleep.light_sleep_minutes:.0f} minutes")

    # 3. Workout data example
    print("\n🏃 Workout Data Normalization:")
    mock_workout = WHOOPWorkout(
        workout_id="workout_demo_123",
        user_id="whoop_user_456",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        start=datetime.utcnow() - timedelta(minutes=45),
        end=datetime.utcnow(),
        timezone_offset="-08:00",
        sport_id=0,  # Running
        score={
            "strain": 16.8,
            "average_heart_rate": 162,
            "max_heart_rate": 185,
            "kilojoule": 2800,  # ~670 calories
        },
        zone_duration={
            "zone_zero_milli": 0,
            "zone_one_milli": 300000,  # 5 min
            "zone_two_milli": 1200000,  # 20 min
            "zone_three_milli": 1200000,  # 20 min
            "zone_four_milli": 0,
            "zone_five_milli": 0,
        },
    )

    normalized_workout = normalizer.normalize_workout_data(
        WearableDevice.WHOOP, mock_workout
    )

    print(f"  Sport: {normalized_workout.sport_type}")
    print(f"  Strain Score: {normalized_workout.workout_strain}")
    print(f"  Duration: {normalized_workout.duration_minutes:.0f} minutes")
    print(f"  Calories: {normalized_workout.calories_burned:.0f}")
    print(f"  Avg HR: {normalized_workout.average_heart_rate} bpm")
    print(f"  Max HR: {normalized_workout.max_heart_rate} bpm")

    # 4. Individual metrics conversion
    print("\n📈 Individual Metrics Conversion:")
    recovery_metrics = normalizer.normalize_to_metrics(
        WearableDevice.WHOOP, mock_recovery, "recovery"
    )

    print(f"  Extracted {len(recovery_metrics)} metrics from recovery data:")
    for metric in recovery_metrics:
        print(f"    - {metric.metric_type.value}: {metric.value} {metric.unit}")


def demo_api_usage():
    """Demonstrate API usage examples"""

    print("\n🌐 API Usage Examples")
    print("=" * 30)

    print("\n1. 🔐 Device Authorization:")
    print(
        """
    POST /wearables/auth/authorize
    {
        "device": "whoop",
        "state": "user_123"
    }
    
    Response:
    {
        "success": true,
        "authorization_url": "https://api-7.whoop.com/oauth/authorize?...",
        "device": "whoop",
        "expires_in": 600
    }
    """
    )

    print("\n2. ✅ Complete Authorization:")
    print(
        """
    POST /wearables/auth/complete
    {
        "device": "whoop", 
        "authorization_code": "code_from_callback",
        "state": "user_123"
    }
    
    Response:
    {
        "success": true,
        "message": "Successfully connected whoop",
        "connection": {
            "device": "whoop",
            "device_user_id": "whoop_user_456",
            "is_active": true,
            "created_at": "2025-05-26T...",
            "updated_at": "2025-05-26T..."
        }
    }
    """
    )

    print("\n3. 🔄 Sync Device Data:")
    print(
        """
    POST /wearables/sync
    {
        "device": "whoop",
        "days_back": 7,
        "force_refresh": false
    }
    
    Response:
    {
        "success": true,
        "result": {
            "success": true,
            "device": "whoop",
            "metrics_synced": 45,
            "recovery_records": 7,
            "sleep_records": 6,
            "workout_records": 3,
            "sync_timestamp": "2025-05-26T..."
        }
    }
    """
    )

    print("\n4. 📱 Get User Connections:")
    print(
        """
    GET /wearables/connections
    
    Response:
    {
        "success": true,
        "connections": [
            {
                "device": "whoop",
                "device_user_id": "whoop_user_456",
                "is_active": true,
                "last_sync": "2025-05-26T...",
                "created_at": "2025-05-26T..."
            }
        ],
        "total_connections": 1
    }
    """
    )

    print("\n5. 🔍 Service Health Check:")
    print(
        """
    GET /wearables/health
    
    Response:
    {
        "success": true,
        "service": "wearable_integration",
        "status": "healthy",
        "active_connections": 15,
        "supported_devices": ["whoop"],
        "device_status": [
            {
                "device": "whoop",
                "status": "available",
                "message": null
            }
        ]
    }
    """
    )


def demo_integration_benefits():
    """Show the benefits of wearable integration for NGX users"""

    print("\n🎯 Integration Benefits for NGX Users")
    print("=" * 40)

    print("\n💡 Enhanced Personalization:")
    print("  ✅ Real-time recovery scores influence workout recommendations")
    print("  ✅ Sleep quality affects nutrition and supplement timing")
    print("  ✅ HRV trends guide training periodization")
    print("  ✅ Strain tracking prevents overtraining")

    print("\n📊 Automatic Data Collection:")
    print("  ✅ No manual logging required")
    print("  ✅ Continuous 24/7 monitoring")
    print("  ✅ Objective biometric data")
    print("  ✅ Historical trend analysis")

    print("\n🤖 AI-Powered Insights:")
    print("  ✅ Recovery-based training adjustments")
    print("  ✅ Sleep optimization recommendations")
    print("  ✅ Nutrition timing based on circadian rhythms")
    print("  ✅ Predictive health risk assessment")

    print("\n🔄 Real-time Adaptations:")
    print("  ✅ Workout intensity adjustments")
    print("  ✅ Rest day recommendations")
    print("  ✅ Meal timing optimization")
    print("  ✅ Supplement dosage adjustments")

    print("\n📈 Long-term Optimization:")
    print("  ✅ Training load progression")
    print("  ✅ Recovery pattern analysis")
    print("  ✅ Performance trend tracking")
    print("  ✅ Health biomarker monitoring")


async def main():
    """Main demo function"""

    try:
        await demo_whoop_integration()
        demo_api_usage()
        demo_integration_benefits()

        print("\n" + "=" * 50)
        print("🎉 Demo completed successfully!")
        print("\n📚 Next Steps:")
        print("1. Set up your WHOOP developer account")
        print("2. Configure environment variables")
        print("3. Start the NGX Agents API server")
        print("4. Test the integration with real data")
        print("\n🔗 Useful Links:")
        print("- WHOOP Developer Docs: https://developer.whoop.com/")
        print("- NGX Agents Documentation: ./docs/")
        print("- Integration Tests: ./tests/integration/wearables/")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

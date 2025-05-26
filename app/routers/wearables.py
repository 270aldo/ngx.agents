"""
Wearable Integration API Router
FastAPI endpoints for managing wearable device integrations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Request
from fastapi.responses import RedirectResponse
import time
import hashlib

from app.schemas.wearables import (
    # Request/Response models
    AuthorizeDeviceRequest,
    AuthorizeDeviceResponse,
    CompleteAuthorizationRequest,
    CompleteAuthorizationResponse,
    SyncDataRequest,
    SyncDataResponse,
    DisconnectDeviceRequest,
    DisconnectDeviceResponse,
    UserConnectionsResponse,
    UserMetricsRequest,
    UserMetricsResponse,
    RecoveryDataResponse,
    SleepDataResponse,
    WorkoutDataResponse,
    WearableServiceHealthResponse,
    SupportedDevicesResponse,
    BulkSyncRequest,
    BulkSyncResponse,
    WearableAnalyticsResponse,
    # Webhook models
    WebhookNotification,
    WebhookResponse,
    WHOOPWebhookData,
    # Error models
    WearableAPIError,
    # Enums
    WearableDeviceType,
    MetricTypeEnum,
)

from integrations.wearables.service import WearableIntegrationService
from integrations.wearables.normalizer import WearableDevice
from integrations.wearables.adapters.apple_health import AppleHealthAdapter
from app.middleware.auth import get_current_user
from core.telemetry import get_tracer, create_span

# Initialize router
router = APIRouter(prefix="/wearables", tags=["Wearable Integrations"])
logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

# Global service instance (would be initialized from config in real implementation)
wearable_service: Optional[WearableIntegrationService] = None


def get_wearable_service() -> WearableIntegrationService:
    """Dependency to get wearable service instance"""
    global wearable_service
    if wearable_service is None:
        # Initialize with configuration
        # In production, this would come from environment/config
        config = {
            "whoop": {
                "client_id": "dummy_client_id",
                "client_secret": "dummy_client_secret",
                "redirect_uri": "http://localhost:8000/wearables/auth/whoop/callback",
                "sandbox": True,
            }
        }
        wearable_service = WearableIntegrationService(config)

    return wearable_service


# Authentication and Authorization Endpoints
@router.post("/auth/authorize", response_model=AuthorizeDeviceResponse)
async def authorize_device(
    request: AuthorizeDeviceRequest,
    user_id: str = Depends(get_current_user),
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Get authorization URL for connecting a wearable device

    This endpoint generates an OAuth authorization URL that users can visit
    to grant permission for NGX Agents to access their wearable device data.
    """
    with create_span(tracer, "authorize_device") as span:
        span.set_attribute("device", request.device.value)
        span.set_attribute("user_id", user_id)

        try:
            # Convert enum to internal type
            device_type = WearableDevice(request.device.value)

            auth_url = await service.get_authorization_url(
                device_type, user_id, request.state
            )

            logger.info(
                f"Generated authorization URL for {request.device.value} - user {user_id}"
            )

            return AuthorizeDeviceResponse(
                success=True,
                authorization_url=auth_url,
                device=request.device,
                expires_in=600,  # 10 minutes
            )

        except ValueError as e:
            logger.error(f"Unsupported device {request.device.value}: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Unsupported device: {request.device.value}"
            )
        except Exception as e:
            logger.error(f"Error generating auth URL: {str(e)}")
            span.record_exception(e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate authorization URL: {str(e)}",
            )


@router.post("/auth/complete", response_model=CompleteAuthorizationResponse)
async def complete_authorization(
    request: CompleteAuthorizationRequest,
    user_id: str = Depends(get_current_user),
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Complete OAuth authorization flow for a wearable device

    This endpoint is called after the user grants permission and is redirected
    back with an authorization code. It exchanges the code for access tokens.
    """
    with create_span(tracer, "complete_authorization") as span:
        span.set_attribute("device", request.device.value)
        span.set_attribute("user_id", user_id)

        try:
            device_type = WearableDevice(request.device.value)

            connection = await service.complete_authorization(
                device_type, request.authorization_code, request.state or user_id
            )

            logger.info(
                f"Successfully connected {request.device.value} for user {user_id}"
            )

            return CompleteAuthorizationResponse(
                success=True,
                message=f"Successfully connected {request.device.value}",
                connection={
                    "device": request.device,
                    "device_user_id": connection.device_user_id,
                    "is_active": connection.is_active,
                    "last_sync": connection.last_sync,
                    "created_at": connection.created_at,
                    "updated_at": connection.updated_at,
                },
            )

        except Exception as e:
            logger.error(f"Error completing authorization: {str(e)}")
            span.record_exception(e)
            return CompleteAuthorizationResponse(
                success=False, message="Failed to complete authorization", error=str(e)
            )


# OAuth callback endpoint (GET endpoint for redirects)
@router.get("/auth/{device}/callback")
async def oauth_callback(
    device: WearableDeviceType,
    code: str = Query(..., description="Authorization code"),
    state: Optional[str] = Query(None, description="State parameter"),
    error: Optional[str] = Query(None, description="OAuth error"),
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    OAuth callback endpoint for wearable devices

    This is where the wearable device provider redirects after user authorization.
    It automatically completes the authorization flow.
    """
    if error:
        logger.error(f"OAuth error for {device.value}: {error}")
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    try:
        # Extract user_id from state
        user_id = state.split(":")[0] if state and ":" in state else state

        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        device_type = WearableDevice(device.value)
        connection = await service.complete_authorization(device_type, code, state)

        # In a real app, you might redirect to a success page
        return {
            "success": True,
            "message": f"Successfully connected {device.value}",
            "device": device.value,
            "user_id": user_id,
        }

    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Data Synchronization Endpoints
@router.post("/sync", response_model=SyncDataResponse)
async def sync_device_data(
    request: SyncDataRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Synchronize data from a wearable device

    Pulls the latest data from the specified device and stores it in NGX format.
    Can be run in the background for large sync operations.
    """
    with create_span(tracer, "sync_device_data") as span:
        span.set_attribute("device", request.device.value)
        span.set_attribute("user_id", user_id)
        span.set_attribute("days_back", request.days_back)

        try:
            device_type = WearableDevice(request.device.value)

            if request.days_back > 7:
                # For large syncs, run in background
                background_tasks.add_task(
                    _background_sync,
                    service,
                    user_id,
                    device_type,
                    request.days_back,
                    request.force_refresh,
                )

                return SyncDataResponse(
                    success=True,
                    result=None,
                    error="Large sync operation started in background. Check status via /sync/status endpoint.",
                )
            else:
                # For small syncs, run synchronously
                sync_result = await service.sync_user_data(
                    user_id, device_type, request.days_back, request.force_refresh
                )

                return SyncDataResponse(
                    success=sync_result.success,
                    result={
                        "success": sync_result.success,
                        "device": request.device,
                        "metrics_synced": sync_result.metrics_synced,
                        "recovery_records": sync_result.recovery_records,
                        "sleep_records": sync_result.sleep_records,
                        "workout_records": sync_result.workout_records,
                        "error_message": sync_result.error_message,
                        "sync_timestamp": sync_result.sync_timestamp,
                    },
                    error=(
                        sync_result.error_message if not sync_result.success else None
                    ),
                )

        except Exception as e:
            logger.error(f"Error syncing device data: {str(e)}")
            span.record_exception(e)
            return SyncDataResponse(success=False, error=str(e))


async def _background_sync(
    service: WearableIntegrationService,
    user_id: str,
    device: WearableDevice,
    days_back: int,
    force_refresh: bool,
):
    """Background task for large sync operations"""
    try:
        result = await service.sync_user_data(user_id, device, days_back, force_refresh)
        logger.info(
            f"Background sync completed for {device.value} user {user_id}: "
            f"{result.metrics_synced} metrics synced"
        )
    except Exception as e:
        logger.error(
            f"Background sync failed for {device.value} user {user_id}: {str(e)}"
        )


# Connection Management Endpoints
@router.get("/connections", response_model=UserConnectionsResponse)
async def get_user_connections(
    user_id: str = Depends(get_current_user),
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Get all connected wearable devices for the current user
    """
    with create_span(tracer, "get_user_connections") as span:
        span.set_attribute("user_id", user_id)

        try:
            connections = await service.get_user_connections(user_id)

            connection_info = []
            for conn in connections:
                connection_info.append(
                    {
                        "device": WearableDeviceType(conn.device.value),
                        "device_user_id": conn.device_user_id,
                        "is_active": conn.is_active,
                        "last_sync": conn.last_sync,
                        "created_at": conn.created_at,
                        "updated_at": conn.updated_at,
                    }
                )

            return UserConnectionsResponse(
                success=True,
                connections=connection_info,
                total_connections=len(connection_info),
            )

        except Exception as e:
            logger.error(f"Error getting user connections: {str(e)}")
            span.record_exception(e)
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect", response_model=DisconnectDeviceResponse)
async def disconnect_device(
    request: DisconnectDeviceRequest,
    user_id: str = Depends(get_current_user),
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Disconnect a wearable device for the current user
    """
    with create_span(tracer, "disconnect_device") as span:
        span.set_attribute("device", request.device.value)
        span.set_attribute("user_id", user_id)

        try:
            device_type = WearableDevice(request.device.value)
            success = await service.disconnect_device(user_id, device_type)

            if success:
                return DisconnectDeviceResponse(
                    success=True,
                    message=f"Successfully disconnected {request.device.value}",
                    device=request.device,
                )
            else:
                return DisconnectDeviceResponse(
                    success=False,
                    message=f"No active connection found for {request.device.value}",
                    device=request.device,
                )

        except Exception as e:
            logger.error(f"Error disconnecting device: {str(e)}")
            span.record_exception(e)
            raise HTTPException(status_code=500, detail=str(e))


# Data Retrieval Endpoints
@router.post("/metrics", response_model=UserMetricsResponse)
async def get_user_metrics(
    request: UserMetricsRequest,
    user_id: str = Depends(get_current_user),
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Get normalized metrics for the current user

    Retrieves metrics from all connected devices in a standardized format.
    """
    with create_span(tracer, "get_user_metrics") as span:
        span.set_attribute("user_id", user_id)
        span.set_attribute("limit", request.limit)

        try:
            # TODO: Implement actual metric retrieval from storage
            # This would query the database for stored normalized metrics

            # For now, return mock data
            metrics = []

            return UserMetricsResponse(
                success=True,
                metrics=metrics,
                total_metrics=len(metrics),
                filters_applied={
                    "device": request.device.value if request.device else None,
                    "metric_types": (
                        [mt.value for mt in request.metric_types]
                        if request.metric_types
                        else None
                    ),
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                    "limit": request.limit,
                },
            )

        except Exception as e:
            logger.error(f"Error getting user metrics: {str(e)}")
            span.record_exception(e)
            raise HTTPException(status_code=500, detail=str(e))


# Administrative Endpoints
@router.get("/health", response_model=WearableServiceHealthResponse)
async def get_service_health(
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Get health status of the wearable integration service
    """
    try:
        health = await service.health_check()

        device_status = []
        for device, status in health["device_status"].items():
            device_status.append(
                {
                    "device": WearableDeviceType(device),
                    "status": status.split(":")[0] if ":" in status else status,
                    "message": (
                        status.split(":", 1)[1].strip() if ":" in status else None
                    ),
                }
            )

        return WearableServiceHealthResponse(
            success=True,
            service=health["service"],
            status=health["status"],
            timestamp=datetime.fromisoformat(health["timestamp"]),
            active_connections=health["active_connections"],
            supported_devices=[
                WearableDeviceType(d) for d in health["supported_devices"]
            ],
            device_status=device_status,
        )

    except Exception as e:
        logger.error(f"Error getting service health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices", response_model=SupportedDevicesResponse)
async def get_supported_devices(
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Get list of supported wearable devices
    """
    try:
        devices = service.get_supported_devices()
        device_types = [WearableDeviceType(d.value) for d in devices]

        return SupportedDevicesResponse(
            success=True, devices=device_types, total_devices=len(device_types)
        )

    except Exception as e:
        logger.error(f"Error getting supported devices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Bulk Operations (Admin only)
@router.post("/admin/bulk-sync", response_model=BulkSyncResponse)
async def bulk_sync_all_users(
    request: BulkSyncRequest,
    background_tasks: BackgroundTasks,
    # TODO: Add admin authentication
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Bulk synchronize data for all connected users (Admin only)

    This endpoint is typically used for scheduled/automated sync operations.
    """
    start_time = time.time()

    try:
        results = await service.sync_all_users(request.days_back)

        successful_syncs = sum(1 for r in results if r.success)
        failed_syncs = len(results) - successful_syncs

        processing_time = time.time() - start_time

        # Convert internal results to API format
        sync_results = []
        for result in results:
            sync_results.append(
                {
                    "success": result.success,
                    "device": WearableDeviceType(result.device.value),
                    "metrics_synced": result.metrics_synced,
                    "recovery_records": result.recovery_records,
                    "sleep_records": result.sleep_records,
                    "workout_records": result.workout_records,
                    "error_message": result.error_message,
                    "sync_timestamp": result.sync_timestamp,
                }
            )

        return BulkSyncResponse(
            success=True,
            total_users_processed=len(set(r.user_id for r in results)),
            successful_syncs=successful_syncs,
            failed_syncs=failed_syncs,
            sync_results=sync_results,
            processing_time_seconds=processing_time,
        )

    except Exception as e:
        logger.error(f"Error in bulk sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Webhook Endpoints
@router.post("/webhooks/whoop")
async def whoop_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Webhook endpoint for WHOOP real-time notifications

    Receives notifications when new data is available from WHOOP devices.
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # TODO: Verify webhook signature
        # signature = request.headers.get("X-WHOOP-Signature")

        # Parse webhook data
        webhook_data = await request.json()

        # Process webhook in background
        background_tasks.add_task(_process_whoop_webhook, service, webhook_data)

        return WebhookResponse(
            success=True,
            message="Webhook received and queued for processing",
            processed_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error processing WHOOP webhook: {str(e)}")
        return WebhookResponse(
            success=False,
            message=f"Error processing webhook: {str(e)}",
            processed_at=datetime.utcnow(),
        )


async def _process_whoop_webhook(
    service: WearableIntegrationService, webhook_data: Dict[str, Any]
):
    """Background task to process WHOOP webhook"""
    try:
        # Extract user and data type from webhook
        user_id = webhook_data.get("user_id")
        data_type = webhook_data.get("type")

        if user_id and data_type:
            # Trigger sync for this specific user
            await service.sync_user_data(
                user_id,
                WearableDevice.WHOOP,
                days_back=1,  # Just get recent data
                force_refresh=True,
            )

            logger.info(f"Processed WHOOP webhook for user {user_id}, type {data_type}")

    except Exception as e:
        logger.error(f"Error processing WHOOP webhook background task: {str(e)}")


@router.post("/webhooks/apple-health/{user_id}/{token}")
async def apple_health_webhook(
    user_id: str,
    token: str,
    request: Request,
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Webhook endpoint for Apple Health data from iOS Shortcuts

    This endpoint receives data from iOS Shortcuts automation.
    The URL contains user_id and a simple token for basic validation.
    """
    try:
        # Verify token (simple validation)
        # In production, use more secure token validation
        expected_token = hashlib.sha256(
            f"{user_id}:webhook_secret".encode()
        ).hexdigest()[:16]

        if token != expected_token:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get webhook data
        webhook_data = await request.json()

        # Process the data
        sync_result = await service.process_apple_health_webhook(user_id, webhook_data)

        return WebhookResponse(
            success=sync_result.success,
            message=f"Processed {sync_result.metrics_synced} metrics",
            processed_at=sync_result.sync_timestamp,
        )

    except Exception as e:
        logger.error(f"Error processing Apple Health webhook: {str(e)}")
        return WebhookResponse(
            success=False,
            message=f"Error processing webhook: {str(e)}",
            processed_at=datetime.utcnow(),
        )


@router.get("/apple-health/setup/{user_id}")
async def get_apple_health_setup(
    user_id: str = Depends(get_current_user),
    service: WearableIntegrationService = Depends(get_wearable_service),
):
    """
    Get iOS Shortcuts setup instructions for Apple Health

    Returns detailed instructions on how to set up iOS Shortcuts
    to automatically sync health data to NGX Agents.
    """
    try:
        if WearableDevice.APPLE_WATCH not in service.device_adapters:
            raise HTTPException(
                status_code=400, detail="Apple Health integration not configured"
            )

        config = service.device_adapters[WearableDevice.APPLE_WATCH]
        adapter = AppleHealthAdapter(config)

        # Generate webhook URL
        base_url = service.config.get("base_url", "https://api.ngxagents.com")
        webhook_url = adapter.create_shortcut_webhook_url(user_id, base_url)

        # Get setup instructions
        instructions = adapter.generate_shortcut_instructions(webhook_url)

        return {
            "success": True,
            "device": "apple_watch",
            "user_id": user_id,
            "setup_instructions": instructions,
        }

    except Exception as e:
        logger.error(f"Error getting Apple Health setup: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Error Handlers
@router.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions"""
    return WearableAPIError(
        error_code="INVALID_INPUT",
        error_message=str(exc),
        details={"request_path": str(request.url)},
    )


@router.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception in wearables API: {str(exc)}")
    return WearableAPIError(
        error_code="INTERNAL_ERROR",
        error_message="An internal error occurred",
        details={"request_path": str(request.url)},
    )

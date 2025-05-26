"""
WHOOP 4.0 API Integration
Provides access to WHOOP recovery, strain, sleep, and heart rate data
Documentation: https://developer.whoop.com/
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import aiohttp
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


@dataclass
class WHOOPConfig:
    """WHOOP API configuration"""

    client_id: str
    client_secret: str
    redirect_uri: str
    sandbox: bool = True
    base_url: str = None

    def __post_init__(self):
        if self.base_url is None:
            self.base_url = (
                "https://api-7.whoop.com"
                if not self.sandbox
                else "https://api-7.whoop.com"
            )


@dataclass
class WHOOPRecovery:
    """WHOOP recovery data model"""

    recovery_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    score: Optional[Dict[str, Any]]
    heart_rate_variability: Optional[Dict[str, Any]]
    resting_heart_rate: Optional[Dict[str, Any]]
    sleep_need: Optional[Dict[str, Any]]


@dataclass
class WHOOPStrain:
    """WHOOP strain data model"""

    strain_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    score: Optional[Dict[str, Any]]
    raw_data: Optional[Dict[str, Any]]


@dataclass
class WHOOPSleep:
    """WHOOP sleep data model"""

    sleep_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    start: datetime
    end: datetime
    timezone_offset: str
    score: Optional[Dict[str, Any]]
    stage_summary: Optional[Dict[str, Any]]
    sleep_need: Optional[Dict[str, Any]]


@dataclass
class WHOOPWorkout:
    """WHOOP workout data model"""

    workout_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    start: datetime
    end: datetime
    timezone_offset: str
    sport_id: int
    score: Optional[Dict[str, Any]]
    zone_duration: Optional[Dict[str, Any]]


class WHOOPAdapter:
    """
    WHOOP 4.0 API adapter for NGX Agents
    Handles OAuth authentication and data retrieval
    """

    def __init__(self, config: WHOOPConfig):
        self.config = config
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def get_auth_url(self, state: str = None) -> str:
        """
        Generate OAuth authorization URL

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for user to grant permissions
        """
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": "read:recovery read:cycles read:workout read:sleep read:profile read:body_measurement",
        }

        if state:
            params["state"] = state

        return f"{self.config.base_url}/oauth/authorize?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token response with access_token, refresh_token, expires_in
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use as async context manager.")

        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": self.config.redirect_uri,
            "code": code,
        }

        async with self.session.post(
            f"{self.config.base_url}/oauth/token", data=data
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(
                    f"Token exchange failed: {response.status} - {error_text}"
                )

            token_data = await response.json()

            # Store tokens
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data["refresh_token"]
            expires_in = token_data["expires_in"]
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("Successfully exchanged code for WHOOP tokens")
            return token_data

    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh access token using refresh token

        Returns:
            New token response
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        if not self.session:
            raise RuntimeError("Session not initialized. Use as async context manager.")

        data = {
            "grant_type": "refresh_token",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": self.refresh_token,
        }

        async with self.session.post(
            f"{self.config.base_url}/oauth/token", data=data
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(
                    f"Token refresh failed: {response.status} - {error_text}"
                )

            token_data = await response.json()

            # Update tokens
            self.access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]
            expires_in = token_data["expires_in"]
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("Successfully refreshed WHOOP access token")
            return token_data

    async def _ensure_valid_token(self):
        """Ensure we have a valid access token, refresh if needed"""
        if not self.access_token:
            raise ValueError("No access token available. Complete OAuth flow first.")

        if self.token_expires_at and datetime.utcnow() >= self.token_expires_at:
            logger.info("Access token expired, refreshing...")
            await self.refresh_access_token()

    async def _make_request(
        self, endpoint: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters

        Returns:
            API response data
        """
        await self._ensure_valid_token()

        if not self.session:
            raise RuntimeError("Session not initialized. Use as async context manager.")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        url = f"{self.config.base_url}{endpoint}"

        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status == 401:
                # Token might be expired, try to refresh
                logger.info("Received 401, attempting token refresh...")
                await self.refresh_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"

                # Retry request
                async with self.session.get(
                    url, headers=headers, params=params
                ) as retry_response:
                    if retry_response.status != 200:
                        error_text = await retry_response.text()
                        raise Exception(
                            f"API request failed after token refresh: {retry_response.status} - {error_text}"
                        )
                    return await retry_response.json()

            elif response.status != 200:
                error_text = await response.text()
                raise Exception(f"API request failed: {response.status} - {error_text}")

            return await response.json()

    async def get_user_profile(self) -> Dict[str, Any]:
        """Get user profile information"""
        return await self._make_request("/developer/v1/user/profile/basic")

    async def get_recovery_data(
        self, start_date: datetime = None, end_date: datetime = None, limit: int = 25
    ) -> List[WHOOPRecovery]:
        """
        Get recovery data for date range

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            limit: Maximum number of records (default 25, max 50)

        Returns:
            List of recovery records
        """
        params = {"limit": min(limit, 50)}

        if start_date:
            params["start"] = start_date.isoformat()
        if end_date:
            params["end"] = end_date.isoformat()

        response = await self._make_request("/developer/v1/recovery", params)

        recoveries = []
        for item in response.get("records", []):
            recovery = WHOOPRecovery(
                recovery_id=item["id"],
                user_id=item["user_id"],
                created_at=datetime.fromisoformat(
                    item["created_at"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    item["updated_at"].replace("Z", "+00:00")
                ),
                score=item.get("score"),
                heart_rate_variability=item.get("heart_rate_variability_rmssd_milli"),
                resting_heart_rate=item.get("resting_heart_rate"),
                sleep_need=item.get("sleep_need"),
            )
            recoveries.append(recovery)

        return recoveries

    async def get_strain_data(
        self, start_date: datetime = None, end_date: datetime = None, limit: int = 25
    ) -> List[WHOOPStrain]:
        """
        Get strain data for date range

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            limit: Maximum number of records

        Returns:
            List of strain records
        """
        params = {"limit": min(limit, 50)}

        if start_date:
            params["start"] = start_date.isoformat()
        if end_date:
            params["end"] = end_date.isoformat()

        response = await self._make_request("/developer/v1/cycle", params)

        strains = []
        for item in response.get("records", []):
            strain = WHOOPStrain(
                strain_id=item["id"],
                user_id=item["user_id"],
                created_at=datetime.fromisoformat(
                    item["created_at"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    item["updated_at"].replace("Z", "+00:00")
                ),
                score=item.get("score"),
                raw_data=item,
            )
            strains.append(strain)

        return strains

    async def get_sleep_data(
        self, start_date: datetime = None, end_date: datetime = None, limit: int = 25
    ) -> List[WHOOPSleep]:
        """
        Get sleep data for date range

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            limit: Maximum number of records

        Returns:
            List of sleep records
        """
        params = {"limit": min(limit, 50)}

        if start_date:
            params["start"] = start_date.isoformat()
        if end_date:
            params["end"] = end_date.isoformat()

        response = await self._make_request("/developer/v1/activity/sleep", params)

        sleeps = []
        for item in response.get("records", []):
            sleep = WHOOPSleep(
                sleep_id=item["id"],
                user_id=item["user_id"],
                created_at=datetime.fromisoformat(
                    item["created_at"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    item["updated_at"].replace("Z", "+00:00")
                ),
                start=datetime.fromisoformat(item["start"].replace("Z", "+00:00")),
                end=datetime.fromisoformat(item["end"].replace("Z", "+00:00")),
                timezone_offset=item["timezone_offset"],
                score=item.get("score"),
                stage_summary=item.get("stage_summary"),
                sleep_need=item.get("sleep_need"),
            )
            sleeps.append(sleep)

        return sleeps

    async def get_workout_data(
        self, start_date: datetime = None, end_date: datetime = None, limit: int = 25
    ) -> List[WHOOPWorkout]:
        """
        Get workout data for date range

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            limit: Maximum number of records

        Returns:
            List of workout records
        """
        params = {"limit": min(limit, 50)}

        if start_date:
            params["start"] = start_date.isoformat()
        if end_date:
            params["end"] = end_date.isoformat()

        response = await self._make_request("/developer/v1/activity/workout", params)

        workouts = []
        for item in response.get("records", []):
            workout = WHOOPWorkout(
                workout_id=item["id"],
                user_id=item["user_id"],
                created_at=datetime.fromisoformat(
                    item["created_at"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    item["updated_at"].replace("Z", "+00:00")
                ),
                start=datetime.fromisoformat(item["start"].replace("Z", "+00:00")),
                end=datetime.fromisoformat(item["end"].replace("Z", "+00:00")),
                timezone_offset=item["timezone_offset"],
                sport_id=item["sport_id"],
                score=item.get("score"),
                zone_duration=item.get("zone_duration"),
            )
            workouts.append(workout)

        return workouts


# Example usage
async def example_usage():
    """Example of how to use the WHOOP adapter"""
    config = WHOOPConfig(
        client_id="your_client_id",
        client_secret="your_client_secret",
        redirect_uri="http://localhost:8000/auth/whoop/callback",
        sandbox=True,
    )

    async with WHOOPAdapter(config) as whoop:
        # Step 1: Get authorization URL
        auth_url = whoop.get_auth_url(state="random_state_string")
        print(f"Visit this URL to authorize: {auth_url}")

        # Step 2: After user authorizes, exchange code for tokens
        # authorization_code = "code_from_callback"
        # await whoop.exchange_code_for_tokens(authorization_code)

        # Step 3: Get user data
        # profile = await whoop.get_user_profile()
        # recovery_data = await whoop.get_recovery_data(limit=10)
        # sleep_data = await whoop.get_sleep_data(limit=10)

        print("WHOOP integration ready!")


if __name__ == "__main__":
    asyncio.run(example_usage())

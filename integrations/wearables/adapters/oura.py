"""
Oura Ring API Integration
Provides access to Oura sleep, activity, readiness, and heart rate data
Documentation: https://cloud.ouraring.com/docs/
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
class OuraConfig:
    """Oura API configuration"""

    client_id: str
    client_secret: str
    redirect_uri: str
    base_url: str = "https://api.ouraring.com"
    auth_url: str = "https://cloud.ouraring.com/oauth/authorize"
    token_url: str = "https://api.ouraring.com/oauth/token"


@dataclass
class OuraSleep:
    """Oura sleep data model"""

    id: str
    day: str
    bedtime_start: datetime
    bedtime_end: datetime
    total_sleep_duration: int  # seconds
    rem_sleep_duration: int
    deep_sleep_duration: int
    light_sleep_duration: int
    awake_time: int
    score: Optional[int]
    efficiency: Optional[int]
    latency: Optional[int]
    hr_lowest: Optional[int]
    hr_average: Optional[float]
    hrv_average: Optional[float]
    respiratory_rate: Optional[float]
    temperature_deviation: Optional[float]


@dataclass
class OuraActivity:
    """Oura activity data model"""

    id: str
    day: str
    score: Optional[int]
    active_calories: int
    total_calories: int
    steps: int
    activity_time: int  # seconds
    met_minutes: Dict[str, int]
    non_wear_time: int
    resting_time: int
    sedentary_time: int
    low_activity_time: int
    medium_activity_time: int
    high_activity_time: int


@dataclass
class OuraReadiness:
    """Oura readiness data model"""

    id: str
    day: str
    score: Optional[int]
    temperature_deviation: Optional[float]
    contributors: Dict[str, int]
    temperature: Optional[float]
    resting_heart_rate: Optional[int]
    heart_rate_variability: Optional[float]


@dataclass
class OuraHeartRate:
    """Oura heart rate data model"""

    timestamp: datetime
    bpm: int
    source: str


@dataclass
class OuraWorkout:
    """Oura workout data model"""

    id: str
    activity: str
    day: str
    start_datetime: datetime
    end_datetime: datetime
    active_calories: int
    average_heart_rate: Optional[int]
    max_heart_rate: Optional[int]
    average_met_minutes: Optional[float]
    intensity: str


class OuraAdapter:
    """
    Oura Ring API adapter for NGX Agents
    Handles OAuth authentication and data retrieval
    """

    def __init__(self, config: OuraConfig):
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
            "scope": "daily personal heartrate workout session spo2",
        }

        if state:
            params["state"] = state

        return f"{self.config.auth_url}?{urlencode(params)}"

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

        async with self.session.post(self.config.token_url, data=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(
                    f"Token exchange failed: {response.status} - {error_text}"
                )

            token_data = await response.json()

            # Store tokens
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 86400)  # Default to 24 hours
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("Successfully exchanged code for Oura tokens")
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

        async with self.session.post(self.config.token_url, data=data) as response:
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
            expires_in = token_data.get("expires_in", 86400)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("Successfully refreshed Oura access token")
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

    async def get_personal_info(self) -> Dict[str, Any]:
        """Get user personal information"""
        return await self._make_request("/v2/usercollection/personal_info")

    async def get_sleep_data(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> List[OuraSleep]:
        """
        Get sleep data for date range

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval

        Returns:
            List of sleep records
        """
        params = {}

        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%d")

        response = await self._make_request("/v2/usercollection/daily_sleep", params)

        sleep_sessions = []
        for item in response.get("data", []):
            sleep = OuraSleep(
                id=item["id"],
                day=item["day"],
                bedtime_start=datetime.fromisoformat(
                    item["bedtime_start"].replace("Z", "+00:00")
                ),
                bedtime_end=datetime.fromisoformat(
                    item["bedtime_end"].replace("Z", "+00:00")
                ),
                total_sleep_duration=item.get("total_sleep_duration", 0),
                rem_sleep_duration=item.get("rem_sleep_duration", 0),
                deep_sleep_duration=item.get("deep_sleep_duration", 0),
                light_sleep_duration=item.get("light_sleep_duration", 0),
                awake_time=item.get("awake_time", 0),
                score=item.get("score"),
                efficiency=item.get("efficiency"),
                latency=item.get("latency"),
                hr_lowest=item.get("hr_lowest"),
                hr_average=item.get("hr_average"),
                hrv_average=item.get("hrv_average"),
                respiratory_rate=item.get("respiratory_rate"),
                temperature_deviation=item.get("temperature_deviation"),
            )
            sleep_sessions.append(sleep)

        return sleep_sessions

    async def get_activity_data(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> List[OuraActivity]:
        """
        Get activity data for date range

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval

        Returns:
            List of activity records
        """
        params = {}

        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%d")

        response = await self._make_request("/v2/usercollection/daily_activity", params)

        activities = []
        for item in response.get("data", []):
            activity = OuraActivity(
                id=item["id"],
                day=item["day"],
                score=item.get("score"),
                active_calories=item.get("active_calories", 0),
                total_calories=item.get("total_calories", 0),
                steps=item.get("steps", 0),
                activity_time=item.get("activity_time", 0),
                met_minutes=item.get("met", {}),
                non_wear_time=item.get("non_wear_time", 0),
                resting_time=item.get("resting_time", 0),
                sedentary_time=item.get("sedentary_time", 0),
                low_activity_time=item.get("low_activity_time", 0),
                medium_activity_time=item.get("medium_activity_time", 0),
                high_activity_time=item.get("high_activity_time", 0),
            )
            activities.append(activity)

        return activities

    async def get_readiness_data(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> List[OuraReadiness]:
        """
        Get readiness data for date range

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval

        Returns:
            List of readiness records
        """
        params = {}

        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%d")

        response = await self._make_request(
            "/v2/usercollection/daily_readiness", params
        )

        readiness_data = []
        for item in response.get("data", []):
            readiness = OuraReadiness(
                id=item["id"],
                day=item["day"],
                score=item.get("score"),
                temperature_deviation=item.get("temperature_deviation"),
                contributors=item.get("contributors", {}),
                temperature=item.get("temperature"),
                resting_heart_rate=item.get("resting_heart_rate"),
                heart_rate_variability=item.get("hrv_balance"),
            )
            readiness_data.append(readiness)

        return readiness_data

    async def get_heart_rate_data(
        self, start_datetime: datetime = None, end_datetime: datetime = None
    ) -> List[OuraHeartRate]:
        """
        Get heart rate data for datetime range

        Args:
            start_datetime: Start datetime for data retrieval
            end_datetime: End datetime for data retrieval

        Returns:
            List of heart rate records
        """
        params = {}

        if start_datetime:
            params["start_datetime"] = start_datetime.isoformat()
        if end_datetime:
            params["end_datetime"] = end_datetime.isoformat()

        response = await self._make_request("/v2/usercollection/heartrate", params)

        heart_rates = []
        for item in response.get("data", []):
            hr = OuraHeartRate(
                timestamp=datetime.fromisoformat(
                    item["timestamp"].replace("Z", "+00:00")
                ),
                bpm=item["bpm"],
                source=item.get("source", "unknown"),
            )
            heart_rates.append(hr)

        return heart_rates

    async def get_workout_data(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> List[OuraWorkout]:
        """
        Get workout data for date range

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval

        Returns:
            List of workout records
        """
        params = {}

        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%d")

        response = await self._make_request("/v2/usercollection/workout", params)

        workouts = []
        for item in response.get("data", []):
            workout = OuraWorkout(
                id=item["id"],
                activity=item.get("activity", "Unknown"),
                day=item["day"],
                start_datetime=datetime.fromisoformat(
                    item["start_datetime"].replace("Z", "+00:00")
                ),
                end_datetime=datetime.fromisoformat(
                    item["end_datetime"].replace("Z", "+00:00")
                ),
                active_calories=item.get("active_calories", 0),
                average_heart_rate=item.get("average_heart_rate"),
                max_heart_rate=item.get("max_heart_rate"),
                average_met_minutes=item.get("average_met_minutes"),
                intensity=item.get("intensity", "moderate"),
            )
            workouts.append(workout)

        return workouts


# Example usage
async def example_usage():
    """Example of how to use the Oura adapter"""
    config = OuraConfig(
        client_id="your_client_id",
        client_secret="your_client_secret",
        redirect_uri="http://localhost:8000/auth/oura/callback",
    )

    async with OuraAdapter(config) as oura:
        # Step 1: Get authorization URL
        auth_url = oura.get_auth_url(state="random_state_string")
        print(f"Visit this URL to authorize: {auth_url}")

        # Step 2: After user authorizes, exchange code for tokens
        # authorization_code = "code_from_callback"
        # await oura.exchange_code_for_tokens(authorization_code)

        # Step 3: Get user data
        # personal_info = await oura.get_personal_info()
        # sleep_data = await oura.get_sleep_data()
        # activity_data = await oura.get_activity_data()
        # readiness_data = await oura.get_readiness_data()

        print("Oura integration ready!")


if __name__ == "__main__":
    asyncio.run(example_usage())

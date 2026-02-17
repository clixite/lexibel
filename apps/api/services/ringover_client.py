"""Ringover API v2 HTTP Client.

Production-ready HTTP client for Ringover REST API v2.
Handles authentication, retries, caching, and error handling.

API Documentation: https://public-api.ringover.com/v2
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Optional

import httpx
from pydantic import BaseModel


class RingoverAPIError(Exception):
    """Base exception for Ringover API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[dict] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class RingoverCall(BaseModel):
    """Ringover call record from API v2."""

    id: str
    direction: str  # inbound | outbound
    caller_number: str
    callee_number: str
    duration_seconds: int
    call_type: str  # answered | missed | voicemail
    started_at: str  # ISO 8601
    ended_at: Optional[str] = None
    recording_available: bool = False
    user_id: Optional[str] = None
    tags: list[str] = []
    metadata: dict[str, Any] = {}


class RingoverCallsResponse(BaseModel):
    """Paginated response for calls list."""

    calls: list[RingoverCall]
    total: int
    page: int
    per_page: int
    has_more: bool


class RingoverRecording(BaseModel):
    """Call recording information."""

    call_id: str
    url: str
    duration_seconds: int
    format: str = "mp3"
    expires_at: Optional[str] = None


class RingoverClient:
    """Async HTTP client for Ringover API v2.

    Features:
    - Bearer token authentication
    - Automatic retry with exponential backoff
    - Request timeout management
    - Optional Redis caching
    - Comprehensive error handling

    Example:
        async with RingoverClient() as client:
            calls = await client.list_calls(page=1, per_page=50)
            recording = await client.get_recording(call_id="abc123")
    """

    BASE_URL = "https://public-api.ringover.com/v2"
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    CACHE_TTL = 300  # 5 minutes

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        enable_cache: bool = True,
    ):
        """Initialize Ringover API client.

        Args:
            api_key: Ringover API key (defaults to RINGOVER_API_KEY env var)
            base_url: API base URL (defaults to production v2 endpoint)
            timeout: Request timeout in seconds
            enable_cache: Enable Redis caching for list calls
        """
        self.api_key = api_key or os.getenv("RINGOVER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Ringover API key required. Set RINGOVER_API_KEY env var or pass api_key parameter."
            )

        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self.enable_cache = enable_cache and bool(os.getenv("REDIS_URL"))

        self._client: Optional[httpx.AsyncClient] = None
        self._redis_client: Optional[Any] = None

    async def __aenter__(self) -> "RingoverClient":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self):
        """Lazily initialize HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "LexiBel/1.0",
                },
            )

        # Initialize Redis client if caching enabled
        if self.enable_cache and self._redis_client is None:
            try:
                import redis.asyncio as aioredis

                redis_url = os.getenv("REDIS_URL")
                self._redis_client = await aioredis.from_url(
                    redis_url,
                    decode_responses=True,
                )
            except Exception as e:
                # Gracefully degrade if Redis unavailable
                self.enable_cache = False
                print(f"Redis cache disabled: {e}")

    async def close(self):
        """Close HTTP and Redis connections."""
        if self._client:
            await self._client.aclose()
            self._client = None

        if self._redis_client:
            await self._redis_client.aclose()
            self._redis_client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        retry_count: int = 0,
    ) -> dict:
        """Execute HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            retry_count: Current retry attempt

        Returns:
            Parsed JSON response

        Raises:
            RingoverAPIError: On API errors or network failures
        """
        await self._ensure_client()

        try:
            response = await self._client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
            )

            # Handle error responses
            if response.status_code >= 400:
                error_data = None
                try:
                    error_data = response.json()
                except Exception:
                    pass

                error_msg = f"Ringover API error: {response.status_code}"
                if error_data and "message" in error_data:
                    error_msg += f" - {error_data['message']}"

                raise RingoverAPIError(
                    message=error_msg,
                    status_code=response.status_code,
                    response_data=error_data,
                )

            return response.json()

        except httpx.TimeoutException as e:
            # Retry on timeout
            if retry_count < self.MAX_RETRIES:
                backoff_delay = 2**retry_count  # Exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(backoff_delay)
                return await self._request(
                    method, endpoint, params, json_data, retry_count + 1
                )
            raise RingoverAPIError(
                f"Request timeout after {self.MAX_RETRIES} retries: {e}"
            )

        except httpx.NetworkError as e:
            # Retry on network errors
            if retry_count < self.MAX_RETRIES:
                backoff_delay = 2**retry_count
                await asyncio.sleep(backoff_delay)
                return await self._request(
                    method, endpoint, params, json_data, retry_count + 1
                )
            raise RingoverAPIError(
                f"Network error after {self.MAX_RETRIES} retries: {e}"
            )

        except RingoverAPIError:
            # Don't retry on API errors (4xx, 5xx)
            raise

        except Exception as e:
            raise RingoverAPIError(f"Unexpected error: {e}")

    async def list_calls(
        self,
        page: int = 1,
        per_page: int = 20,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        direction: Optional[str] = None,
        call_type: Optional[str] = None,
    ) -> RingoverCallsResponse:
        """List calls with pagination and filters.

        Args:
            page: Page number (1-indexed)
            per_page: Results per page (max 100)
            date_from: Filter calls after this date
            date_to: Filter calls before this date
            direction: Filter by direction (inbound/outbound)
            call_type: Filter by type (answered/missed/voicemail)

        Returns:
            Paginated calls response

        Example:
            calls = await client.list_calls(
                page=1,
                per_page=50,
                date_from=datetime(2024, 1, 1),
                direction="inbound",
            )
        """
        # Build query parameters
        params: dict[str, Any] = {
            "page": page,
            "per_page": min(per_page, 100),  # API max limit
        }

        if date_from:
            params["date_from"] = date_from.isoformat()

        if date_to:
            params["date_to"] = date_to.isoformat()

        if direction:
            params["direction"] = direction

        if call_type:
            params["call_type"] = call_type

        # Check cache if enabled
        cache_key = None
        if self.enable_cache and self._redis_client:
            cache_key = f"ringover:calls:{hash(frozenset(params.items()))}"
            try:
                cached = await self._redis_client.get(cache_key)
                if cached:
                    import json

                    return RingoverCallsResponse(**json.loads(cached))
            except Exception:
                pass  # Cache miss or error, continue to API

        # Fetch from API
        data = await self._request("GET", "/calls", params=params)

        # Parse response
        response = RingoverCallsResponse(
            calls=[RingoverCall(**call_data) for call_data in data.get("calls", [])],
            total=data.get("total", 0),
            page=page,
            per_page=per_page,
            has_more=data.get("has_more", False),
        )

        # Cache result
        if cache_key and self._redis_client:
            try:
                import json

                await self._redis_client.setex(
                    cache_key,
                    self.CACHE_TTL,
                    json.dumps(response.model_dump()),
                )
            except Exception:
                pass  # Cache write failure, non-critical

        return response

    async def get_call(self, call_id: str) -> RingoverCall:
        """Get detailed call information.

        Args:
            call_id: Ringover call ID

        Returns:
            Detailed call record

        Raises:
            RingoverAPIError: If call not found or API error
        """
        data = await self._request("GET", f"/calls/{call_id}")
        return RingoverCall(**data)

    async def get_recording(self, call_id: str) -> RingoverRecording:
        """Get call recording URL.

        Args:
            call_id: Ringover call ID

        Returns:
            Recording information with download URL

        Raises:
            RingoverAPIError: If recording not available

        Note:
            Recording URLs are typically time-limited signed URLs.
            Download and store the recording if long-term access needed.
        """
        data = await self._request("GET", f"/calls/{call_id}/recording")
        return RingoverRecording(
            call_id=call_id,
            url=data["url"],
            duration_seconds=data.get("duration_seconds", 0),
            format=data.get("format", "mp3"),
            expires_at=data.get("expires_at"),
        )

    async def invalidate_cache(self):
        """Clear all cached call data.

        Useful after webhook events to force fresh data fetch.
        """
        if self._redis_client:
            try:
                keys = await self._redis_client.keys("ringover:calls:*")
                if keys:
                    await self._redis_client.delete(*keys)
            except Exception:
                pass  # Non-critical


async def get_ringover_client() -> RingoverClient:
    """Dependency injection helper for FastAPI routes.

    Example:
        @router.get("/calls")
        async def list_calls(
            client: RingoverClient = Depends(get_ringover_client),
        ):
            return await client.list_calls()
    """
    client = RingoverClient()
    try:
        yield client
    finally:
        await client.close()

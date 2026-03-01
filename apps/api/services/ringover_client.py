"""Ringover API v2 HTTP Client.

Production-ready HTTP client for Ringover REST API v2.
Handles authentication, retries, caching, and error handling.

API Documentation: https://developer.ringover.com
Base URL: https://public-api.ringover.com/v2
Auth: Authorization: <api_key>  (no Bearer prefix)
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
    """Ringover call record from API v2.

    Field names match the real Ringover API v2 response:
    - cdr_id: integer CDR identifier (used for cursor pagination)
    - call_id: string call UUID
    - from_number: caller phone number
    - to_number: called phone number
    - call_type: ANSWERED | MISSED | OUT | VOICEMAIL
    - duration: call duration in seconds
    - start_date: ISO 8601 start timestamp
    - end_date: ISO 8601 end timestamp (may be null)
    - user: dict with user info (id, name, etc.)
    """

    cdr_id: int
    call_id: str = ""
    from_number: str = ""
    to_number: str = ""
    call_type: str = "ANSWERED"  # ANSWERED | MISSED | OUT | VOICEMAIL
    duration: int = 0
    start_date: str = ""
    end_date: Optional[str] = None
    user: Optional[dict] = None

    @property
    def direction(self) -> str:
        """Infer direction from call_type. OUT = outbound, others = inbound."""
        return "outbound" if self.call_type == "OUT" else "inbound"

    @property
    def internal_call_type(self) -> str:
        """Map Ringover call_type to our internal format (lowercase)."""
        mapping = {
            "ANSWERED": "answered",
            "MISSED": "missed",
            "OUT": "answered",
            "VOICEMAIL": "voicemail",
        }
        return mapping.get(self.call_type, "answered")

    @property
    def recording_available(self) -> bool:
        return False  # Ringover API v2 list doesn't expose this directly

    @property
    def user_id(self) -> Optional[str]:
        if self.user:
            uid = self.user.get("id") or self.user.get("user_id")
            return str(uid) if uid else None
        return None


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

    Authentication: API key sent directly as Authorization header value.
    Pagination: uses limit_count + limit_offset (page-based) or last_id_returned (cursor).
    Date filters: start_date / end_date (ISO 8601, max 15-day range).

    Example:
        async with RingoverClient() as client:
            calls = await client.list_calls(page=1, per_page=50)
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
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensure_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    # Ringover API v2: key directly in Authorization (no "Bearer" prefix)
                    "Authorization": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "LexiBel/1.0",
                },
            )

        if self.enable_cache and self._redis_client is None:
            try:
                import redis.asyncio as aioredis

                redis_url = os.getenv("REDIS_URL")
                self._redis_client = await aioredis.from_url(
                    redis_url,
                    decode_responses=True,
                )
            except Exception as e:
                self.enable_cache = False
                print(f"Redis cache disabled: {e}")

    async def close(self):
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
        await self._ensure_client()

        try:
            response = await self._client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
            )

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
            if retry_count < self.MAX_RETRIES:
                await asyncio.sleep(2**retry_count)
                return await self._request(method, endpoint, params, json_data, retry_count + 1)
            raise RingoverAPIError(f"Request timeout after {self.MAX_RETRIES} retries: {e}")

        except httpx.NetworkError as e:
            if retry_count < self.MAX_RETRIES:
                await asyncio.sleep(2**retry_count)
                return await self._request(method, endpoint, params, json_data, retry_count + 1)
            raise RingoverAPIError(f"Network error after {self.MAX_RETRIES} retries: {e}")

        except RingoverAPIError:
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

        Ringover API v2 parameters:
        - limit_count: number of results (max 1000)
        - limit_offset: offset for page-based pagination (max 9000)
        - start_date / end_date: ISO 8601, max 15-day range
        - call_type: ANSWERED | MISSED | OUT | VOICEMAIL

        Returns:
            RingoverCallsResponse with calls mapped to internal model
        """
        # Build filter body for POST /calls
        body: dict[str, Any] = {
            "limit_count": min(per_page, 100),
            "limit_offset": (page - 1) * per_page,
        }

        if date_from:
            body["start_date"] = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")

        if date_to:
            body["end_date"] = date_to.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Map internal call_type to Ringover API format
        if call_type:
            type_map = {
                "answered": "ANSWERED",
                "missed": "MISSED",
                "voicemail": "VOICEMAIL",
                "outbound": "OUT",
            }
            api_type = type_map.get(call_type)
            if api_type:
                body["call_type"] = api_type

        # Direction filter: if outbound only, override call_type
        if direction == "outbound":
            body["call_type"] = "OUT"

        # Check cache
        cache_key = None
        if self.enable_cache and self._redis_client:
            cache_key = f"ringover:calls:{hash(str(sorted(body.items())))}"
            try:
                cached = await self._redis_client.get(cache_key)
                if cached:
                    import json
                    return RingoverCallsResponse(**json.loads(cached))
            except Exception:
                pass

        # Ringover v2 uses POST for filtered calls
        data = await self._request("POST", "/calls", json_data=body)

        # Parse response: field is "call_list", total is "total_call_count"
        raw_calls = data.get("call_list", [])
        total = data.get("total_call_count", len(raw_calls))

        calls = []
        for raw in raw_calls:
            try:
                calls.append(RingoverCall(
                    cdr_id=raw.get("cdr_id", 0),
                    call_id=str(raw.get("call_id", raw.get("cdr_id", ""))),
                    from_number=raw.get("from_number", ""),
                    to_number=raw.get("to_number", ""),
                    call_type=str(raw.get("call_type", "ANSWERED")).upper(),
                    duration=int(raw.get("duration", 0)),
                    start_date=raw.get("start_date", ""),
                    end_date=raw.get("end_date"),
                    user=raw.get("user"),
                ))
            except Exception:
                continue

        response = RingoverCallsResponse(
            calls=calls,
            total=total,
            page=page,
            per_page=per_page,
            has_more=(page * per_page) < total,
        )

        if cache_key and self._redis_client:
            try:
                import json
                await self._redis_client.setex(
                    cache_key,
                    self.CACHE_TTL,
                    json.dumps(response.model_dump()),
                )
            except Exception:
                pass

        return response

    async def get_call(self, call_id: str) -> RingoverCall:
        """Get detailed call information by CDR ID or call UUID."""
        data = await self._request("GET", f"/calls/{call_id}")
        raw = data if isinstance(data, dict) else data
        return RingoverCall(
            cdr_id=raw.get("cdr_id", 0),
            call_id=str(raw.get("call_id", call_id)),
            from_number=raw.get("from_number", ""),
            to_number=raw.get("to_number", ""),
            call_type=str(raw.get("call_type", "ANSWERED")).upper(),
            duration=int(raw.get("duration", 0)),
            start_date=raw.get("start_date", ""),
            end_date=raw.get("end_date"),
            user=raw.get("user"),
        )

    async def get_recording(self, call_id: str) -> RingoverRecording:
        """Get call recording URL."""
        data = await self._request("GET", f"/calls/{call_id}/recording")
        return RingoverRecording(
            call_id=call_id,
            url=data["url"],
            duration_seconds=data.get("duration_seconds", 0),
            format=data.get("format", "mp3"),
            expires_at=data.get("expires_at"),
        )

    async def invalidate_cache(self):
        """Clear all cached call data."""
        if self._redis_client:
            try:
                keys = await self._redis_client.keys("ringover:calls:*")
                if keys:
                    await self._redis_client.delete(*keys)
            except Exception:
                pass


async def get_ringover_client() -> RingoverClient:
    """Dependency injection helper for FastAPI routes."""
    client = RingoverClient()
    try:
        yield client
    finally:
        await client.close()

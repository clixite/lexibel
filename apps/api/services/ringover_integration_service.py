"""Ringover API integration service for call management.

Fetches call records from Ringover API and stores them in database.
"""

import logging
import os
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.call_record import CallRecord
from packages.db.models.contact import Contact

logger = logging.getLogger(__name__)


class RingoverIntegrationService:
    """Ringover VoIP integration service."""

    def __init__(self):
        """Initialize Ringover integration."""
        self.api_key = os.getenv("RINGOVER_API_KEY")
        self.base_url = os.getenv(
            "RINGOVER_API_BASE_URL", "https://public-api.ringover.com/v2"
        )

        if not self.api_key:
            raise ValueError("RINGOVER_API_KEY must be set")

    async def fetch_calls(
        self,
        tenant_id: UUID,
        session: AsyncSession,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[CallRecord]:
        """Fetch calls from Ringover API and store in database.

        Args:
            tenant_id: Tenant ID
            session: Database session
            date_from: Start date filter
            date_to: End date filter
            limit: Max calls to fetch

        Returns:
            List of CallRecord objects
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        params = {
            "limit": limit,
        }

        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/calls",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError as e:
                # Log error but don't crash - return empty list
                logger.error("Ringover API error: %s", e)
                return []

        calls = data.get("calls", [])
        call_records = []

        for call_data in calls:
            # Check if call already exists
            external_id = call_data.get("id")
            stmt = select(CallRecord).where(
                CallRecord.tenant_id == tenant_id,
                CallRecord.external_id == external_id,
            )
            result = await session.execute(stmt)
            existing_call = result.scalar_one_or_none()

            if existing_call:
                # Skip duplicate
                continue

            # Try to match contact by phone number
            caller_number = call_data.get("caller_number")
            contact_id = None

            if caller_number:
                contact_stmt = select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.phone_e164 == caller_number,
                )
                contact_result = await session.execute(contact_stmt)
                contact = contact_result.scalar_one_or_none()
                if contact:
                    contact_id = contact.id

            # Create call record
            call_record = CallRecord(
                tenant_id=tenant_id,
                external_id=external_id,
                contact_id=contact_id,
                direction=call_data.get("direction", "inbound"),
                caller_number=caller_number,
                callee_number=call_data.get("callee_number"),
                duration_seconds=call_data.get("duration"),
                call_type=call_data.get("type", "answered"),
                recording_url=call_data.get("recording_url"),
                started_at=datetime.fromisoformat(call_data["started_at"])
                if call_data.get("started_at")
                else None,
                ended_at=datetime.fromisoformat(call_data["ended_at"])
                if call_data.get("ended_at")
                else None,
                metadata_=call_data.get("metadata", {}),
            )

            session.add(call_record)
            call_records.append(call_record)

        if call_records:
            await session.commit()

        return call_records

    async def get_call_recording(self, recording_url: str) -> bytes:
        """Download call recording audio file.

        Args:
            recording_url: URL to recording file

        Returns:
            Audio file bytes
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(recording_url, headers=headers)
            response.raise_for_status()
            return response.content


# Singleton instance
_ringover_integration_service: RingoverIntegrationService | None = None


def get_ringover_integration_service() -> RingoverIntegrationService:
    """Get singleton Ringover integration service."""
    global _ringover_integration_service
    if _ringover_integration_service is None:
        _ringover_integration_service = RingoverIntegrationService()
    return _ringover_integration_service

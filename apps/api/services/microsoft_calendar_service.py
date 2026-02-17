"""Microsoft Calendar synchronization service via Graph API.

Syncs calendar events from Outlook Calendar to CalendarEvent model.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.calendar_event import CalendarEvent
from apps.api.services.microsoft_oauth_service import get_microsoft_oauth_service


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_TIMEOUT = 30.0


class MicrosoftCalendarService:
    """Microsoft Calendar synchronization via Graph API."""

    async def list_events(
        self,
        access_token: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: int = 100,
    ) -> list[dict]:
        """List calendar events via Graph API.

        Args:
            access_token: Valid Microsoft Graph access token
            start_time: Filter events starting after this time
            end_time: Filter events ending before this time
            max_results: Maximum number of events to fetch

        Returns:
            List of calendar event dictionaries
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        params = {
            "$top": max_results,
            "$orderby": "start/dateTime",
        }

        # Build filter
        filters = []
        if start_time:
            start_iso = start_time.isoformat()
            filters.append(f"start/dateTime ge '{start_iso}Z'")

        if end_time:
            end_iso = end_time.isoformat()
            filters.append(f"end/dateTime le '{end_iso}Z'")

        if filters:
            params["$filter"] = " and ".join(filters)

        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            response = await client.get(
                f"{GRAPH_BASE_URL}/me/events",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        return data.get("value", [])

    async def sync_to_db(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: int = 100,
    ) -> dict:
        """Sync calendar events to database.

        Args:
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID
            start_time: Filter events starting after this time
            end_time: Filter events ending before this time
            max_results: Maximum events to sync

        Returns:
            Sync statistics (events_created, events_updated, etc.)
        """
        # Get valid access token
        microsoft_oauth = get_microsoft_oauth_service()
        access_token = await microsoft_oauth.get_valid_access_token(
            session, tenant_id, user_id
        )

        if not access_token:
            raise ValueError("No Microsoft OAuth token found")

        # Default to future events if no time range specified
        if not start_time:
            start_time = datetime.now(timezone.utc)

        # Fetch events from Graph API
        events = await self.list_events(
            access_token,
            start_time,
            end_time,
            max_results,
        )

        events_created = 0
        events_updated = 0

        for event in events:
            external_id = event["id"]

            # Check if event already exists
            stmt = select(CalendarEvent).where(
                CalendarEvent.tenant_id == tenant_id,
                CalendarEvent.external_id == external_id,
                CalendarEvent.provider == "outlook",
            )
            result = await session.execute(stmt)
            existing_event = result.scalar_one_or_none()

            # Parse times
            start = event["start"]["dateTime"]
            end = event["end"]["dateTime"]
            is_all_day = event.get("isAllDay", False)

            # Parse attendees
            attendees = []
            for attendee in event.get("attendees", []):
                email_address = attendee.get("emailAddress", {})
                attendees.append({
                    "email": email_address.get("address"),
                    "name": email_address.get("name"),
                    "status": attendee.get("status", {}).get("response", "none"),
                })

            # Parse location
            location = None
            if event.get("location"):
                location = event["location"].get("displayName")

            # Additional metadata
            metadata = {
                "webLink": event.get("webLink"),
                "organizer": event.get("organizer", {}).get("emailAddress"),
                "responseStatus": event.get("responseStatus", {}).get("response"),
                "onlineMeetingUrl": event.get("onlineMeetingUrl"),
            }

            if existing_event:
                # Update existing event
                existing_event.title = event.get("subject", "(No title)")[:500]
                existing_event.description = event.get("bodyPreview")
                existing_event.start_time = datetime.fromisoformat(start)
                existing_event.end_time = datetime.fromisoformat(end)
                existing_event.location = location
                existing_event.attendees = attendees
                existing_event.is_all_day = is_all_day
                existing_event.metadata = metadata
                existing_event.synced_at = datetime.now(timezone.utc)
                events_updated += 1
            else:
                # Create new event
                calendar_event = CalendarEvent(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    external_id=external_id,
                    provider="outlook",
                    title=event.get("subject", "(No title)")[:500],
                    description=event.get("bodyPreview"),
                    start_time=datetime.fromisoformat(start),
                    end_time=datetime.fromisoformat(end),
                    location=location,
                    attendees=attendees,
                    is_all_day=is_all_day,
                    metadata=metadata,
                    synced_at=datetime.now(timezone.utc),
                )
                session.add(calendar_event)
                events_created += 1

        await session.commit()

        return {
            "events_created": events_created,
            "events_updated": events_updated,
            "total_processed": len(events),
        }


# Singleton instance
_microsoft_calendar_service: MicrosoftCalendarService | None = None


def get_microsoft_calendar_service() -> MicrosoftCalendarService:
    """Get singleton Microsoft Calendar service."""
    global _microsoft_calendar_service
    if _microsoft_calendar_service is None:
        _microsoft_calendar_service = MicrosoftCalendarService()
    return _microsoft_calendar_service

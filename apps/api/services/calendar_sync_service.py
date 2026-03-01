"""Calendar synchronization service for Google and Microsoft calendars.

Syncs calendar events to calendar_events table.
"""

from datetime import datetime
from uuid import UUID, uuid4

import httpx
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.calendar_event import CalendarEvent
from apps.api.services.google_oauth_service import get_google_oauth_service
from apps.api.services.microsoft_oauth_service import get_microsoft_oauth_service


class CalendarSyncService:
    """Calendar synchronization service for Google and Microsoft."""

    async def sync_google_calendar(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        max_results: int = 100,
    ) -> dict:
        """Sync Google Calendar events.

        Args:
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID
            max_results: Max events to fetch

        Returns:
            Sync statistics
        """
        # Get valid credentials
        google_oauth = get_google_oauth_service()
        credentials = await google_oauth.get_valid_credentials(
            session, tenant_id, user_id
        )

        if not credentials:
            raise ValueError("No Google OAuth token found")

        # Build Calendar API service
        service = build("calendar", "v3", credentials=credentials)

        # Fetch events
        now = datetime.utcnow().isoformat() + "Z"
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        events_created = 0

        for event in events:
            external_id = event["id"]

            # Check if event already exists
            stmt = select(CalendarEvent).where(
                CalendarEvent.tenant_id == tenant_id,
                CalendarEvent.external_id == external_id,
                CalendarEvent.provider == "google",
            )
            result = await session.execute(stmt)
            existing_event = result.scalar_one_or_none()

            if existing_event:
                continue  # Skip duplicate

            # Parse start/end times
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            is_all_day = "date" in event["start"]

            calendar_event = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                external_id=external_id,
                provider="google",
                title=event.get("summary", "(No title)"),
                description=event.get("description"),
                start_time=datetime.fromisoformat(start.replace("Z", "+00:00")),
                end_time=datetime.fromisoformat(end.replace("Z", "+00:00")),
                location=event.get("location"),
                attendees=event.get("attendees", []),
                is_all_day=is_all_day,
            )
            session.add(calendar_event)
            events_created += 1

        await session.commit()

        return {
            "events_created": events_created,
            "total_processed": len(events),
        }

    async def sync_outlook_calendar(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        max_results: int = 100,
    ) -> dict:
        """Sync Outlook Calendar events via Microsoft Graph API.

        Args:
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID
            max_results: Max events to fetch

        Returns:
            Sync statistics
        """
        # Get valid access token
        microsoft_oauth = get_microsoft_oauth_service()
        access_token = await microsoft_oauth.get_valid_access_token(
            session, tenant_id, user_id
        )

        if not access_token:
            raise ValueError("No Microsoft OAuth token found")

        # Fetch events from Microsoft Graph API
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        params = {
            "$top": max_results,
            "$orderby": "start/dateTime",
            "$filter": f"start/dateTime ge '{datetime.utcnow().isoformat()}Z'",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/events",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        events = data.get("value", [])
        events_created = 0

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

            if existing_event:
                continue  # Skip duplicate

            # Parse times
            start = event["start"]["dateTime"]
            end = event["end"]["dateTime"]
            is_all_day = event.get("isAllDay", False)

            calendar_event = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                external_id=external_id,
                provider="outlook",
                title=event.get("subject", "(No title)"),
                description=event.get("bodyPreview"),
                start_time=datetime.fromisoformat(start),
                end_time=datetime.fromisoformat(end),
                location=event.get("location", {}).get("displayName"),
                attendees=event.get("attendees", []),
                is_all_day=is_all_day,
            )
            session.add(calendar_event)
            events_created += 1

        await session.commit()

        return {
            "events_created": events_created,
            "total_processed": len(events),
        }

    async def sync_google_calendar_with_token(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        access_token: str,
        max_results: int = 100,
    ) -> dict:
        """Sync Google Calendar using a pre-obtained access token (from oauth_engine)."""
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=access_token)
        return await self._sync_google_with_credentials(
            session, tenant_id, user_id, credentials, max_results
        )

    async def _sync_google_with_credentials(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        credentials,
        max_results: int,
    ) -> dict:
        """Core Google Calendar sync logic."""
        service = build("calendar", "v3", credentials=credentials)
        now = datetime.utcnow().isoformat() + "Z"
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        events_created = 0

        for event in events:
            external_id = event["id"]
            stmt = select(CalendarEvent).where(
                CalendarEvent.tenant_id == tenant_id,
                CalendarEvent.external_id == external_id,
                CalendarEvent.provider == "google",
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                continue

            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            is_all_day = "date" in event["start"]

            calendar_event = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                external_id=external_id,
                provider="google",
                title=event.get("summary", "(No title)"),
                description=event.get("description"),
                start_time=datetime.fromisoformat(start.replace("Z", "+00:00")),
                end_time=datetime.fromisoformat(end.replace("Z", "+00:00")),
                location=event.get("location"),
                attendees=event.get("attendees", []),
                is_all_day=is_all_day,
            )
            session.add(calendar_event)
            events_created += 1

        await session.commit()
        return {"events_created": events_created, "total_processed": len(events)}

    async def sync_outlook_calendar_with_token(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        access_token: str,
        max_results: int = 100,
    ) -> dict:
        """Sync Outlook Calendar using a pre-obtained access token (from oauth_engine)."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        params = {
            "$top": max_results,
            "$orderby": "start/dateTime",
            "$filter": f"start/dateTime ge '{datetime.utcnow().isoformat()}Z'",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/events",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        events = data.get("value", [])
        events_created = 0

        for event in events:
            external_id = event["id"]
            stmt = select(CalendarEvent).where(
                CalendarEvent.tenant_id == tenant_id,
                CalendarEvent.external_id == external_id,
                CalendarEvent.provider == "outlook",
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                continue

            start = event["start"]["dateTime"]
            end = event["end"]["dateTime"]
            calendar_event = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                external_id=external_id,
                provider="outlook",
                title=event.get("subject", "(No title)"),
                description=event.get("bodyPreview"),
                start_time=datetime.fromisoformat(start),
                end_time=datetime.fromisoformat(end),
                location=event.get("location", {}).get("displayName"),
                attendees=event.get("attendees", []),
                is_all_day=event.get("isAllDay", False),
            )
            session.add(calendar_event)
            events_created += 1

        await session.commit()
        return {"events_created": events_created, "total_processed": len(events)}

    async def sync_all(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict:
        """Sync both Google and Outlook calendars using oauth_engine for token retrieval."""
        from sqlalchemy import select as sa_select
        from packages.db.models.oauth_token import OAuthToken
        from apps.api.services.oauth_engine import get_oauth_engine

        results: dict = {"google": None, "outlook": None}
        oauth_engine = get_oauth_engine()

        # Google Calendar
        try:
            g_result = await session.execute(
                sa_select(OAuthToken).where(
                    OAuthToken.tenant_id == tenant_id,
                    OAuthToken.user_id == user_id,
                    OAuthToken.provider == "google",
                )
            )
            g_token = g_result.scalar_one_or_none()
            if g_token:
                access_token = await oauth_engine.get_valid_token(session, g_token.id)
                results["google"] = await self.sync_google_calendar_with_token(
                    session, tenant_id, user_id, access_token
                )
            else:
                results["google"] = {"error": "No Google account connected."}
        except Exception as e:
            results["google"] = {"error": str(e)}

        # Outlook Calendar
        try:
            ms_result = await session.execute(
                sa_select(OAuthToken).where(
                    OAuthToken.tenant_id == tenant_id,
                    OAuthToken.user_id == user_id,
                    OAuthToken.provider == "microsoft",
                )
            )
            ms_token = ms_result.scalar_one_or_none()
            if ms_token:
                access_token = await oauth_engine.get_valid_token(session, ms_token.id)
                results["outlook"] = await self.sync_outlook_calendar_with_token(
                    session, tenant_id, user_id, access_token
                )
            else:
                results["outlook"] = {"error": "No Microsoft account connected."}
        except Exception as e:
            results["outlook"] = {"error": str(e)}

        return results


# Singleton instance
_calendar_sync_service: CalendarSyncService | None = None


def get_calendar_sync_service() -> CalendarSyncService:
    """Get singleton calendar sync service."""
    global _calendar_sync_service
    if _calendar_sync_service is None:
        _calendar_sync_service = CalendarSyncService()
    return _calendar_sync_service

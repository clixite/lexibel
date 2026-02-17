"""Microsoft Outlook email synchronization service via Graph API.

Syncs emails from Outlook to EmailThread and EmailMessage models.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.email_message import EmailMessage
from packages.db.models.email_thread import EmailThread
from apps.api.services.microsoft_oauth_service import get_microsoft_oauth_service


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_TIMEOUT = 30.0


class MicrosoftOutlookSyncService:
    """Outlook email synchronization via Microsoft Graph API."""

    async def list_messages(
        self,
        access_token: str,
        since_date: Optional[datetime] = None,
        max_results: int = 50,
    ) -> list[dict]:
        """List messages from Outlook via Graph API.

        Args:
            access_token: Valid Microsoft Graph access token
            since_date: Only fetch messages after this date
            max_results: Maximum number of messages to fetch

        Returns:
            List of message dictionaries from Graph API
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        params = {
            "$top": max_results,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,toRecipients,ccRecipients,bccRecipients,bodyPreview,body,receivedDateTime,hasAttachments,isRead,importance,conversationId",
        }

        if since_date:
            since_iso = since_date.isoformat()
            params["$filter"] = f"receivedDateTime ge {since_iso}Z"

        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            response = await client.get(
                f"{GRAPH_BASE_URL}/me/messages",
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
        since_date: Optional[datetime] = None,
        max_results: int = 50,
    ) -> dict:
        """Sync Outlook messages to database.

        Args:
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID
            since_date: Only sync messages after this date
            max_results: Maximum messages to sync

        Returns:
            Sync statistics (threads_created, messages_created, etc.)
        """
        # Get valid access token
        microsoft_oauth = get_microsoft_oauth_service()
        access_token = await microsoft_oauth.get_valid_access_token(
            session, tenant_id, user_id
        )

        if not access_token:
            raise ValueError("No Microsoft OAuth token found")

        # Fetch messages from Graph API
        messages = await self.list_messages(access_token, since_date, max_results)

        threads_created = 0
        messages_created = 0
        messages_updated = 0

        for msg in messages:
            external_id = msg["id"]
            conversation_id = msg.get("conversationId", external_id)

            # Get or create thread
            thread = await self._get_or_create_thread(
                session,
                tenant_id,
                conversation_id,
                msg.get("subject", "(No subject)"),
                msg,
            )

            if thread.created_at == thread.updated_at:
                threads_created += 1

            # Get or create message
            message_created = await self._create_or_update_message(
                session,
                tenant_id,
                thread.id,
                msg,
            )

            if message_created:
                messages_created += 1
            else:
                messages_updated += 1

            # Update thread metadata
            thread.message_count = len(thread.messages)
            thread.last_message_at = datetime.fromisoformat(
                msg["receivedDateTime"].replace("Z", "+00:00")
            )
            thread.synced_at = datetime.now(timezone.utc)

        await session.commit()

        return {
            "threads_created": threads_created,
            "messages_created": messages_created,
            "messages_updated": messages_updated,
            "total_processed": len(messages),
        }

    async def _get_or_create_thread(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        external_id: str,
        subject: str,
        first_message: dict,
    ) -> EmailThread:
        """Get existing thread or create new one.

        Args:
            session: Database session
            tenant_id: Tenant ID
            external_id: Thread external ID (conversationId)
            subject: Thread subject
            first_message: First message in thread (for metadata)

        Returns:
            EmailThread instance
        """
        stmt = select(EmailThread).where(
            EmailThread.tenant_id == tenant_id,
            EmailThread.external_id == external_id,
            EmailThread.provider == "outlook",
        )
        result = await session.execute(stmt)
        thread = result.scalar_one_or_none()

        if thread:
            return thread

        # Extract participants from first message
        from_info = first_message.get("from", {}).get("emailAddress", {})
        to_recipients = first_message.get("toRecipients", [])
        cc_recipients = first_message.get("ccRecipients", [])
        bcc_recipients = first_message.get("bccRecipients", [])

        participants = {
            "from": {
                "email": from_info.get("address"),
                "name": from_info.get("name"),
            },
            "to": [
                {
                    "email": r.get("emailAddress", {}).get("address"),
                    "name": r.get("emailAddress", {}).get("name"),
                }
                for r in to_recipients
            ],
            "cc": [
                {
                    "email": r.get("emailAddress", {}).get("address"),
                    "name": r.get("emailAddress", {}).get("name"),
                }
                for r in cc_recipients
            ],
            "bcc": [
                {
                    "email": r.get("emailAddress", {}).get("address"),
                    "name": r.get("emailAddress", {}).get("name"),
                }
                for r in bcc_recipients
            ],
        }

        thread = EmailThread(
            id=uuid4(),
            tenant_id=tenant_id,
            external_id=external_id,
            provider="outlook",
            subject=subject[:500] if subject else None,
            participants=participants,
            message_count=0,
            has_attachments=first_message.get("hasAttachments", False),
            is_important=first_message.get("importance") == "high",
        )

        session.add(thread)
        await session.flush()

        return thread

    async def _create_or_update_message(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        thread_id: UUID,
        msg: dict,
    ) -> bool:
        """Create or update email message.

        Args:
            session: Database session
            tenant_id: Tenant ID
            thread_id: Thread ID
            msg: Message dict from Graph API

        Returns:
            True if created, False if updated
        """
        external_id = msg["id"]

        stmt = select(EmailMessage).where(
            EmailMessage.tenant_id == tenant_id,
            EmailMessage.external_id == external_id,
            EmailMessage.provider == "outlook",
        )
        result = await session.execute(stmt)
        existing_message = result.scalar_one_or_none()

        # Parse recipients
        from_info = msg.get("from", {}).get("emailAddress", {})
        to_recipients = [
            r.get("emailAddress", {}).get("address")
            for r in msg.get("toRecipients", [])
            if r.get("emailAddress", {}).get("address")
        ]
        cc_recipients = [
            r.get("emailAddress", {}).get("address")
            for r in msg.get("ccRecipients", [])
            if r.get("emailAddress", {}).get("address")
        ]
        bcc_recipients = [
            r.get("emailAddress", {}).get("address")
            for r in msg.get("bccRecipients", [])
            if r.get("emailAddress", {}).get("address")
        ]

        # Parse body
        body = msg.get("body", {})
        body_text = body.get("content") if body.get("contentType") == "text" else None
        body_html = body.get("content") if body.get("contentType") == "html" else None

        # Parse attachments (would need separate API call for full details)
        attachments = []
        if msg.get("hasAttachments"):
            # In production, fetch attachments via separate endpoint
            # GET /me/messages/{id}/attachments
            attachments = [{"filename": "attachment", "size": 0}]

        if existing_message:
            # Update existing message
            existing_message.subject = msg.get("subject", "")[:500]
            existing_message.body_text = body_text
            existing_message.body_html = body_html
            existing_message.is_read = msg.get("isRead", False)
            existing_message.is_important = msg.get("importance") == "high"
            existing_message.synced_at = datetime.now(timezone.utc)
            return False

        # Create new message
        email_message = EmailMessage(
            id=uuid4(),
            tenant_id=tenant_id,
            thread_id=thread_id,
            external_id=external_id,
            provider="outlook",
            subject=msg.get("subject", "")[:500],
            from_address=from_info.get("address", "unknown"),
            to_addresses=to_recipients,
            cc_addresses=cc_recipients,
            bcc_addresses=bcc_recipients,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            is_read=msg.get("isRead", False),
            is_important=msg.get("importance") == "high",
            received_at=datetime.fromisoformat(
                msg["receivedDateTime"].replace("Z", "+00:00")
            ),
            synced_at=datetime.now(timezone.utc),
        )

        session.add(email_message)
        return True


# Singleton instance
_microsoft_outlook_sync_service: MicrosoftOutlookSyncService | None = None


def get_microsoft_outlook_sync_service() -> MicrosoftOutlookSyncService:
    """Get singleton Microsoft Outlook sync service."""
    global _microsoft_outlook_sync_service
    if _microsoft_outlook_sync_service is None:
        _microsoft_outlook_sync_service = MicrosoftOutlookSyncService()
    return _microsoft_outlook_sync_service

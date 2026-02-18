"""Email synchronization service for Gmail and Outlook.

Syncs emails from Gmail API (Google) and Graph API (Microsoft) into
the email_threads and email_messages tables.
"""

import base64
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.services.oauth_engine import get_oauth_engine
from packages.db.models.email_message import EmailMessage
from packages.db.models.email_thread import EmailThread


class EmailSyncService:
    """Synchronizes emails from Gmail and Outlook."""

    def __init__(self):
        """Initialize email sync service."""
        self.oauth_engine = get_oauth_engine()

    async def sync_emails(
        self,
        session: AsyncSession,
        token_id: uuid.UUID,
        since: datetime | None = None,
        max_results: int = 50,
    ) -> dict:
        """Sync emails from Gmail or Outlook.

        Args:
            session: Database session
            token_id: OAuth token ID
            since: Only fetch emails after this datetime (optional)
            max_results: Maximum number of emails to fetch

        Returns:
            {
                "threads_created": 5,
                "messages_created": 12,
                "provider": "google"
            }
        """
        # Get valid access token
        access_token = await self.oauth_engine.get_valid_token(session, token_id)

        # Get token to determine provider
        from packages.db.models.oauth_token import OAuthToken

        result = await session.execute(
            select(OAuthToken).where(OAuthToken.id == token_id)
        )
        oauth_token = result.scalar_one()

        if oauth_token.provider == "google":
            return await self._sync_gmail(
                session, oauth_token, access_token, since, max_results
            )
        else:  # microsoft
            return await self._sync_outlook(
                session, oauth_token, access_token, since, max_results
            )

    async def _sync_gmail(
        self,
        session: AsyncSession,
        oauth_token,
        access_token: str,
        since: datetime | None,
        max_results: int,
    ) -> dict:
        """Sync emails from Gmail API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build query
            query_params = {"maxResults": max_results}
            if since:
                # Gmail query format: after:YYYY/MM/DD
                date_str = since.strftime("%Y/%m/%d")
                query_params["q"] = f"after:{date_str}"

            # List messages
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params=query_params,
            )

            if response.status_code != 200:
                raise ValueError(f"Gmail API error: {response.status_code} {response.text}")

            data = response.json()
            messages = data.get("messages", [])

            threads_created = 0
            messages_created = 0

            # Fetch full details for each message
            for msg_ref in messages:
                msg_id = msg_ref["id"]

                # Get full message
                msg_response = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if msg_response.status_code != 200:
                    continue

                msg_data = msg_response.json()

                # Parse message
                thread_id = msg_data.get("threadId")
                headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}

                subject = headers.get("Subject", "(No subject)")
                from_email = headers.get("From", "")
                to_email = headers.get("To", "")
                date_str = headers.get("Date", "")

                # Parse date
                try:
                    from email.utils import parsedate_to_datetime
                    received_at = parsedate_to_datetime(date_str)
                except Exception:
                    received_at = datetime.now(timezone.utc)

                # Get body (simplified - Gmail has complex MIME structure)
                body_text = self._extract_gmail_body(msg_data.get("payload", {}))

                # Check if thread exists
                thread_result = await session.execute(
                    select(EmailThread).where(
                        EmailThread.tenant_id == oauth_token.tenant_id,
                        EmailThread.external_id == thread_id,
                        EmailThread.provider == "gmail",
                    )
                )
                email_thread = thread_result.scalar_one_or_none()

                if not email_thread:
                    # Create thread
                    email_thread = EmailThread(
                        tenant_id=oauth_token.tenant_id,
                        external_id=thread_id,
                        provider="gmail",
                        subject=subject,
                        message_count=0,
                        has_attachments=False,
                    )
                    session.add(email_thread)
                    await session.flush()
                    threads_created += 1

                # Check if message already exists
                msg_result = await session.execute(
                    select(EmailMessage).where(
                        EmailMessage.thread_id == email_thread.id,
                        EmailMessage.external_id == msg_id,
                    )
                )
                existing_msg = msg_result.scalar_one_or_none()

                if not existing_msg:
                    # Create message
                    email_message = EmailMessage(
                        tenant_id=oauth_token.tenant_id,
                        thread_id=email_thread.id,
                        external_id=msg_id,
                        from_email=from_email,
                        to_email=to_email,
                        subject=subject,
                        body_text=body_text,
                        body_html=None,  # TODO: extract HTML
                        received_at=received_at,
                        is_read=False,
                        is_starred=False,
                    )
                    session.add(email_message)
                    messages_created += 1

                    # Update thread message count
                    email_thread.message_count += 1

            await session.commit()

            return {
                "threads_created": threads_created,
                "messages_created": messages_created,
                "provider": "gmail",
            }

    def _extract_gmail_body(self, payload: dict) -> str:
        """Extract plain text body from Gmail message payload."""
        if "body" in payload and payload["body"].get("data"):
            # Single part message
            body_data = payload["body"]["data"]
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")

        if "parts" in payload:
            # Multi-part message - find text/plain part
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body_data = part["body"]["data"]
                    return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")

        return ""

    async def _sync_outlook(
        self,
        session: AsyncSession,
        oauth_token,
        access_token: str,
        since: datetime | None,
        max_results: int,
    ) -> dict:
        """Sync emails from Microsoft Graph API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build query
            params = {"$top": max_results, "$orderby": "receivedDateTime desc"}
            if since:
                # Graph API filter format
                since_iso = since.isoformat()
                params["$filter"] = f"receivedDateTime ge {since_iso}"

            # List messages
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )

            if response.status_code != 200:
                raise ValueError(f"Graph API error: {response.status_code} {response.text}")

            data = response.json()
            messages = data.get("value", [])

            threads_created = 0
            messages_created = 0

            for msg in messages:
                # Get conversation ID (thread ID)
                conversation_id = msg.get("conversationId")
                msg_id = msg.get("id")

                subject = msg.get("subject", "(No subject)")
                from_email = msg.get("from", {}).get("emailAddress", {}).get("address", "")
                to_recipients = msg.get("toRecipients", [])
                to_email = (
                    to_recipients[0].get("emailAddress", {}).get("address", "")
                    if to_recipients
                    else ""
                )

                # Parse date
                received_str = msg.get("receivedDateTime")
                try:
                    received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00"))
                except Exception:
                    received_at = datetime.now(timezone.utc)

                # Get body
                body_text = msg.get("body", {}).get("content", "") if msg.get("body", {}).get("contentType") == "text" else ""
                body_html = msg.get("body", {}).get("content", "") if msg.get("body", {}).get("contentType") == "html" else None

                # Check if thread exists
                thread_result = await session.execute(
                    select(EmailThread).where(
                        EmailThread.tenant_id == oauth_token.tenant_id,
                        EmailThread.external_id == conversation_id,
                        EmailThread.provider == "outlook",
                    )
                )
                email_thread = thread_result.scalar_one_or_none()

                if not email_thread:
                    # Create thread
                    email_thread = EmailThread(
                        tenant_id=oauth_token.tenant_id,
                        external_id=conversation_id,
                        provider="outlook",
                        subject=subject,
                        message_count=0,
                        has_attachments=msg.get("hasAttachments", False),
                    )
                    session.add(email_thread)
                    await session.flush()
                    threads_created += 1

                # Check if message already exists
                msg_result = await session.execute(
                    select(EmailMessage).where(
                        EmailMessage.thread_id == email_thread.id,
                        EmailMessage.external_id == msg_id,
                    )
                )
                existing_msg = msg_result.scalar_one_or_none()

                if not existing_msg:
                    # Create message
                    email_message = EmailMessage(
                        tenant_id=oauth_token.tenant_id,
                        thread_id=email_thread.id,
                        external_id=msg_id,
                        from_email=from_email,
                        to_email=to_email,
                        subject=subject,
                        body_text=body_text,
                        body_html=body_html,
                        received_at=received_at,
                        is_read=msg.get("isRead", False),
                        is_starred=False,
                    )
                    session.add(email_message)
                    messages_created += 1

                    # Update thread message count
                    email_thread.message_count += 1

            await session.commit()

            return {
                "threads_created": threads_created,
                "messages_created": messages_created,
                "provider": "outlook",
            }

    async def send_email(
        self,
        session: AsyncSession,
        token_id: uuid.UUID,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
        body_html: str | None = None,
    ) -> dict:
        """Send an email via Gmail or Outlook.

        Args:
            session: Database session
            token_id: OAuth token ID
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            cc: CC recipients (optional)
            body_html: HTML body (optional)

        Returns:
            {
                "message_id": "...",
                "provider": "google"
            }
        """
        # Get valid access token
        access_token = await self.oauth_engine.get_valid_token(session, token_id)

        # Get token to determine provider
        from packages.db.models.oauth_token import OAuthToken

        result = await session.execute(
            select(OAuthToken).where(OAuthToken.id == token_id)
        )
        oauth_token = result.scalar_one()

        if oauth_token.provider == "google":
            return await self._send_gmail(
                access_token, to, subject, body, cc, body_html
            )
        else:  # microsoft
            return await self._send_outlook(
                access_token, to, subject, body, cc, body_html
            )

    async def _send_gmail(
        self,
        access_token: str,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None,
        body_html: str | None,
    ) -> dict:
        """Send email via Gmail API."""
        # Create MIME message
        if body_html:
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(body, "plain"))
            message.attach(MIMEText(body_html, "html"))
        else:
            message = MIMEText(body, "plain")

        message["To"] = to
        message["Subject"] = subject
        if cc:
            message["Cc"] = ", ".join(cc)

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": raw_message},
            )

            if response.status_code != 200:
                raise ValueError(f"Gmail send failed: {response.status_code} {response.text}")

            data = response.json()
            return {"message_id": data["id"], "provider": "gmail"}

    async def _send_outlook(
        self,
        access_token: str,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None,
        body_html: str | None,
    ) -> dict:
        """Send email via Microsoft Graph API."""
        message_payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML" if body_html else "Text",
                    "content": body_html or body,
                },
                "toRecipients": [{"emailAddress": {"address": to}}],
            },
            "saveToSentItems": "true",
        }

        if cc:
            message_payload["message"]["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc
            ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://graph.microsoft.com/v1.0/me/sendMail",
                headers={"Authorization": f"Bearer {access_token}"},
                json=message_payload,
            )

            if response.status_code != 202:  # Graph API returns 202 Accepted
                raise ValueError(f"Graph send failed: {response.status_code} {response.text}")

            return {"message_id": "sent", "provider": "outlook"}

    async def get_email_profile(
        self, session: AsyncSession, token_id: uuid.UUID
    ) -> dict:
        """Get email profile information.

        Returns:
            {
                "email": "user@example.com",
                "name": "User Name",
                "provider": "google"
            }
        """
        # Get valid access token
        access_token = await self.oauth_engine.get_valid_token(session, token_id)

        # Get token to determine provider
        from packages.db.models.oauth_token import OAuthToken

        result = await session.execute(
            select(OAuthToken).where(OAuthToken.id == token_id)
        )
        oauth_token = result.scalar_one()

        async with httpx.AsyncClient() as client:
            if oauth_token.provider == "google":
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            else:  # microsoft
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

            if response.status_code != 200:
                raise ValueError(f"Profile fetch failed: {response.status_code}")

            data = response.json()

            return {
                "email": data.get("email") or data.get("userPrincipalName"),
                "name": data.get("name") or data.get("displayName"),
                "provider": oauth_token.provider,
            }


# Global instance
_email_sync_service: EmailSyncService | None = None


def get_email_sync_service() -> EmailSyncService:
    """Get or create the global email sync service instance."""
    global _email_sync_service
    if _email_sync_service is None:
        _email_sync_service = EmailSyncService()
    return _email_sync_service

"""Gmail synchronization service using Google Gmail API.

Syncs emails from Gmail to email_threads and email_messages tables.
"""

from datetime import datetime
from uuid import UUID, uuid4

from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.email_thread import EmailThread
from packages.db.models.email_message import EmailMessage
from apps.api.services.google_oauth_service import get_google_oauth_service


class GmailSyncService:
    """Gmail email synchronization service."""

    async def sync_emails(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        max_results: int = 100,
    ) -> dict:
        """Sync emails from Gmail.

        Args:
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID
            max_results: Max emails to fetch

        Returns:
            Sync statistics
        """
        # Get valid credentials
        google_oauth = get_google_oauth_service()
        credentials = await google_oauth.get_valid_credentials(
            session, tenant_id, user_id
        )

        if not credentials:
            raise ValueError(
                "No Google OAuth token found. Please connect Google account first."
            )

        # Build Gmail API service
        service = build("gmail", "v1", credentials=credentials)

        # Fetch messages
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                maxResults=max_results,
                labelIds=["INBOX"],
            )
            .execute()
        )

        messages = results.get("messages", [])

        threads_created = 0
        messages_created = 0

        for message_ref in messages:
            message_id = message_ref["id"]
            thread_id = message_ref["threadId"]

            # Fetch full message details
            message = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="full",
                )
                .execute()
            )

            # Check if thread exists
            stmt = select(EmailThread).where(
                EmailThread.tenant_id == tenant_id,
                EmailThread.external_id == thread_id,
                EmailThread.provider == "google",
            )
            result = await session.execute(stmt)
            email_thread = result.scalar_one_or_none()

            # Extract headers
            headers = {
                h["name"]: h["value"] for h in message["payload"].get("headers", [])
            }
            subject = headers.get("Subject", "(No Subject)")
            from_addr = headers.get("From", "unknown@example.com")

            # Create thread if doesn't exist
            if not email_thread:
                email_thread = EmailThread(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    external_id=thread_id,
                    provider="google",
                    subject=subject,
                    participants={"from": from_addr},
                    message_count=0,
                    last_message_at=datetime.fromtimestamp(
                        int(message["internalDate"]) / 1000
                    ),
                )
                session.add(email_thread)
                threads_created += 1

            # Check if message already exists
            msg_stmt = select(EmailMessage).where(
                EmailMessage.tenant_id == tenant_id,
                EmailMessage.external_id == message_id,
                EmailMessage.provider == "google",
            )
            msg_result = await session.execute(msg_stmt)
            existing_message = msg_result.scalar_one_or_none()

            if existing_message:
                # Skip duplicate
                continue

            # Extract body
            body_text = ""
            if "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        body_text = part.get("body", {}).get("data", "")
                        break
            else:
                body_text = message["payload"].get("body", {}).get("data", "")

            # Create email message
            email_message = EmailMessage(
                id=uuid4(),
                tenant_id=tenant_id,
                thread_id=email_thread.id,
                external_id=message_id,
                provider="google",
                subject=subject,
                from_address=from_addr,
                to_addresses=[headers.get("To", "")],
                body_text=body_text,
                is_read="UNREAD" not in message.get("labelIds", []),
                received_at=datetime.fromtimestamp(int(message["internalDate"]) / 1000),
            )
            session.add(email_message)
            messages_created += 1

            # Update thread message count
            email_thread.message_count += 1
            email_thread.last_message_at = email_message.received_at

        await session.commit()

        return {
            "threads_created": threads_created,
            "messages_created": messages_created,
            "total_processed": len(messages),
        }


# Singleton instance
_gmail_sync_service: GmailSyncService | None = None


def get_gmail_sync_service() -> GmailSyncService:
    """Get singleton Gmail sync service."""
    global _gmail_sync_service
    if _gmail_sync_service is None:
        _gmail_sync_service = GmailSyncService()
    return _gmail_sync_service

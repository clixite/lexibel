"""Outlook/Exchange integration service — email sync stub.

Microsoft Graph API client stub for email ingestion.
Real implementation requires OAuth tenant configuration and
Graph API permissions (Mail.Read, Mail.ReadBasic).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional


class OutlookEmail:
    """Parsed email from Microsoft Graph API."""

    def __init__(
        self,
        message_id: str,
        subject: str,
        sender: str,
        recipients: list[str],
        body_preview: str,
        received_at: datetime,
        has_attachments: bool = False,
    ):
        self.message_id = message_id
        self.subject = subject
        self.sender = sender
        self.recipients = recipients
        self.body_preview = body_preview
        self.received_at = received_at
        self.has_attachments = has_attachments


async def sync_emails(
    tenant_id: uuid.UUID,
    mailbox: str,
    since: Optional[datetime] = None,
) -> list[dict]:
    """Sync emails from Outlook/Exchange via Microsoft Graph API.

    Stub: In production, this would:
    1. Get OAuth token for the tenant's Azure AD app
    2. Call GET /users/{mailbox}/messages?$filter=receivedDateTime ge {since}
    3. Parse each email into InboxItems with source=OUTLOOK
    4. Use idempotency_key from message.internetMessageId

    Returns list of dicts representing inbox items to create.
    """
    # TODO: Implement Microsoft Graph API integration
    # async with httpx.AsyncClient() as client:
    #     token = await get_tenant_oauth_token(tenant_id)
    #     resp = await client.get(
    #         f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages",
    #         headers={"Authorization": f"Bearer {token}"},
    #         params={"$top": 50, "$orderby": "receivedDateTime desc"},
    #     )
    #     messages = resp.json()["value"]
    return []


def parse_email_for_case_matching(email: OutlookEmail) -> dict:
    """Parse an email to extract case-matching signals.

    Extracts:
    - Subject line patterns (case reference, dossier number)
    - Sender email → contact match
    - Keywords for AI case suggestion
    """
    signals = {
        "subject": email.subject,
        "sender": email.sender,
        "recipients": email.recipients,
        "body_preview": email.body_preview,
        "has_attachments": email.has_attachments,
        "received_at": email.received_at.isoformat(),
    }

    # Extract case reference patterns (e.g., "2026/001", "Dossier 42")
    import re
    ref_patterns = [
        r"\b\d{4}/\d{3,4}\b",        # 2026/001
        r"\b[Dd]ossier\s+\d+\b",     # Dossier 42
        r"\bRG\s+\d+/\d+\b",         # RG 2026/123 (court roll)
    ]
    references = []
    text = f"{email.subject} {email.body_preview}"
    for pattern in ref_patterns:
        matches = re.findall(pattern, text)
        references.extend(matches)

    signals["extracted_references"] = references
    return signals


async def create_inbox_items_from_emails(
    tenant_id: uuid.UUID,
    emails: list[OutlookEmail],
) -> list[dict]:
    """Create inbox items from parsed emails.

    Stub: Returns the items that would be created.
    """
    items = []
    for email in emails:
        signals = parse_email_for_case_matching(email)
        items.append({
            "tenant_id": str(tenant_id),
            "source": "OUTLOOK",
            "status": "DRAFT",
            "raw_payload": {
                "message_id": email.message_id,
                "subject": email.subject,
                "sender": email.sender,
                "recipients": email.recipients,
                "body_preview": email.body_preview,
                "received_at": email.received_at.isoformat(),
                "has_attachments": email.has_attachments,
            },
            "signals": signals,
        })
    return items

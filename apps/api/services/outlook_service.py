"""Outlook/Exchange integration service — Microsoft Graph API.

Full email sync, detail retrieval, drafting, and sending via Graph API.
OAuth2 token management with refresh. Maps emails to cases via
subject/reference pattern matching.

Real implementation requires:
- Azure AD app registration with Mail.Read, Mail.Send permissions
- OAuth2 client credentials or delegated token flow
- Tenant-scoped token storage
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional


# ── Constants ──

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_TIMEOUT = 30.0

# Case reference patterns for matching
REF_PATTERNS = [
    re.compile(r"\b(\d{4}/\d{2,4}(?:/[A-Z])?)\b"),  # 2026/001/A
    re.compile(r"\b([Dd]ossier\s+\d+)\b"),  # Dossier 42
    re.compile(r"\b(RG\s+\d+/\d+)\b"),  # RG 2026/123
    re.compile(r"\b(DOS[-\s]?\d{3,6})\b"),  # DOS-001
]


# ── Data classes ──


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


# ── OAuth2 token management ──

_token_cache: dict[
    str, dict
] = {}  # tenant_id -> {access_token, refresh_token, expires_at}


async def _get_graph_token(tenant_id: str) -> str:
    """Get Microsoft Graph API token for a tenant.

    Stub: In production, uses client_credentials or delegated flow
    with automatic refresh.
    """
    cached = _token_cache.get(tenant_id)
    if cached:
        expires = cached.get("expires_at")
        if expires and datetime.now(timezone.utc).timestamp() < expires:
            return cached["access_token"]

    # Stub: would POST to https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
    token = f"graph_token_{uuid.uuid4().hex[:16]}"
    _token_cache[tenant_id] = {
        "access_token": token,
        "refresh_token": f"refresh_{uuid.uuid4().hex[:16]}",
        "expires_at": datetime.now(timezone.utc).timestamp() + 3600,
    }
    return token


async def refresh_token(tenant_id: str) -> str:
    """Refresh an expired Graph API token.

    Stub: In production, POST to token endpoint with refresh_token.
    """
    cached = _token_cache.get(tenant_id)
    if not cached or not cached.get("refresh_token"):
        raise ValueError(f"No refresh token for tenant {tenant_id}")

    # Stub: exchange refresh_token for new access_token
    new_token = f"graph_token_{uuid.uuid4().hex[:16]}"
    cached["access_token"] = new_token
    cached["expires_at"] = datetime.now(timezone.utc).timestamp() + 3600
    return new_token


# ── In-memory email cache (for dev/test) ──

_email_cache: dict[str, list[dict]] = {}  # tenant_id -> [email dicts]


def reset_store() -> None:
    """Reset all caches (for tests)."""
    _token_cache.clear()
    _email_cache.clear()


def get_cached_emails(tenant_id: str) -> list[dict]:
    """Get cached emails for a tenant."""
    return _email_cache.get(tenant_id, [])


# ── Reference extraction ──


def extract_references(text: str) -> list[str]:
    """Extract case reference patterns from text."""
    refs = []
    for pattern in REF_PATTERNS:
        refs.extend(pattern.findall(text))
    return [r.strip() for r in refs]


def match_email_to_case(
    subject: str,
    body_preview: str,
    sender: str,
    existing_cases: list[dict],
) -> Optional[dict]:
    """Match an email to an existing case via subject/reference patterns.

    Returns the best matching case dict or None.
    """
    text = f"{subject} {body_preview}"
    refs = extract_references(text)

    if not refs or not existing_cases:
        return None

    for case in existing_cases:
        case_ref = case.get("reference", "")
        if not case_ref:
            continue
        for ref in refs:
            if ref.lower() in case_ref.lower() or case_ref.lower() in ref.lower():
                return case

    return None


# ── Core operations ──


async def sync_emails(
    tenant_id: uuid.UUID,
    mailbox: str,
    since: Optional[datetime] = None,
) -> list[dict]:
    """Legacy sync_emails for backward compatibility with integrations router."""
    return []


async def sync_emails_enhanced(
    tenant_id: str,
    user_id: str,
    since: Optional[str] = None,
) -> list[dict]:
    """Sync emails from Outlook via Microsoft Graph API.

    Args:
        tenant_id: Tenant UUID string
        user_id: Outlook user mailbox or ID
        since: ISO datetime string — only sync emails after this

    Returns:
        List of email dicts with metadata
    """
    # Stub: In production, call Graph API
    # token = await _get_graph_token(tenant_id)
    # async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
    #     params = {"$top": 50, "$orderby": "receivedDateTime desc"}
    #     if since:
    #         params["$filter"] = f"receivedDateTime ge {since}"
    #     resp = await client.get(
    #         f"{GRAPH_BASE_URL}/users/{user_id}/messages",
    #         headers={"Authorization": f"Bearer {token}"},
    #         params=params,
    #     )
    #     resp.raise_for_status()
    #     messages = resp.json().get("value", [])

    # Stub: return empty (no Graph API configured)
    return []


async def get_email_detail(
    tenant_id: str,
    message_id: str,
) -> Optional[dict]:
    """Get detailed email content from Graph API.

    Args:
        tenant_id: Tenant UUID string
        message_id: Graph API message ID

    Returns:
        Full email dict or None if not found
    """
    # Stub: In production, GET /users/{user}/messages/{id}
    # with $expand=attachments
    cached = _email_cache.get(tenant_id, [])
    for email in cached:
        if email.get("message_id") == message_id:
            return email
    return None


async def create_draft(
    tenant_id: str,
    to: list[str],
    subject: str,
    body: str,
) -> dict:
    """Create a draft email in Outlook.

    Args:
        tenant_id: Tenant UUID string
        to: List of recipient email addresses
        subject: Email subject
        body: Email body (HTML or plain text)

    Returns:
        Draft dict with message_id
    """
    # Stub: In production, POST /users/{user}/messages (creates draft)
    draft_id = str(uuid.uuid4())
    return {
        "message_id": draft_id,
        "status": "draft",
        "to": to,
        "subject": subject,
        "body_preview": body[:200],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def send_email(
    tenant_id: str,
    to: list[str],
    subject: str,
    body_text: str,
    draft_id: Optional[str] = None,
) -> dict:
    """Send an email via Outlook.

    If draft_id is provided, sends the existing draft.
    Otherwise, creates and sends a new message.

    Args:
        tenant_id: Tenant UUID string
        to: List of recipient addresses
        subject: Email subject
        body_text: Email body
        draft_id: Optional existing draft ID to send

    Returns:
        Dict with status and message_id
    """
    if not to:
        raise ValueError("At least one recipient is required")

    # Stub: In production:
    # If draft_id: POST /users/{user}/messages/{draft_id}/send
    # Else: POST /users/{user}/sendMail with message payload

    message_id = draft_id or str(uuid.uuid4())
    return {
        "status": "sent",
        "message_id": message_id,
        "message": f"Email sent to {', '.join(to)} (stub — Graph API not configured)",
    }


# ── Legacy functions for backward compatibility ──


def parse_email_for_case_matching(email: OutlookEmail) -> dict:
    """Parse an email to extract case-matching signals."""
    signals = {
        "subject": email.subject,
        "sender": email.sender,
        "recipients": email.recipients,
        "body_preview": email.body_preview,
        "has_attachments": email.has_attachments,
        "received_at": email.received_at.isoformat(),
    }

    text = f"{email.subject} {email.body_preview}"
    signals["extracted_references"] = extract_references(text)
    return signals


async def create_inbox_items_from_emails(
    tenant_id: uuid.UUID,
    emails: list[OutlookEmail],
) -> list[dict]:
    """Create inbox items from parsed emails."""
    items = []
    for email in emails:
        signals = parse_email_for_case_matching(email)
        items.append(
            {
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
            }
        )
    return items

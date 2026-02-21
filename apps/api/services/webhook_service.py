"""Webhook service — HMAC verification, E.164 parsing, contact matching, idempotency."""

import hashlib
import hmac
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.contact import Contact

# In-memory idempotency store (production: Redis SETNX with 24h TTL)
_idempotency_store: dict[str, bool] = {}


def verify_hmac_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """Verify HMAC signature of a webhook payload.

    Args:
        payload: Raw request body bytes.
        signature: Hex-encoded HMAC signature from the webhook header.
        secret: Shared secret for HMAC computation.
        algorithm: Hash algorithm (sha256, sha1, etc.).

    Returns:
        True if the signature is valid.
    """
    mac = hmac.new(
        secret.encode("utf-8"),
        payload,
        getattr(hashlib, algorithm),
    )
    expected = mac.hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_e164(phone: str) -> str | None:
    """Parse and normalize a phone number to E.164 format.

    Accepts formats like +32470123456, 0032470123456, 0470123456 (Belgian).
    Returns E.164 string or None if unparseable.
    """
    # Strip whitespace, dashes, dots, parens
    cleaned = re.sub(r"[\s\-\.\(\)]+", "", phone)

    # Already E.164
    if re.match(r"^\+\d{8,15}$", cleaned):
        return cleaned

    # International prefix 00
    if cleaned.startswith("00") and len(cleaned) >= 10:
        return "+" + cleaned[2:]

    # Belgian local (0 prefix → +32)
    if cleaned.startswith("0") and len(cleaned) >= 9:
        return "+32" + cleaned[1:]

    return None


async def match_contact_by_phone(
    session: AsyncSession,
    phone: str,
) -> Contact | None:
    """Match a contact by phone number (E.164 exact match).

    Multi-signal matching: exact E.164 match is highest confidence.
    RLS ensures tenant isolation.
    """
    normalized = parse_e164(phone)
    if normalized is None:
        return None

    result = await session.execute(
        select(Contact).where(Contact.phone_e164 == normalized)
    )
    return result.scalar_one_or_none()


async def check_idempotency(key: str) -> bool:
    """Check if a webhook has already been processed.

    Returns True if this is a duplicate (already processed).
    In production, this uses Redis SETNX with 24h TTL.
    """
    # TODO: Replace with Redis SETNX in production
    if key in _idempotency_store:
        return True  # Duplicate
    _idempotency_store[key] = True
    return False  # First time


def reset_idempotency_store() -> None:
    """Reset the in-memory idempotency store (for testing)."""
    _idempotency_store.clear()

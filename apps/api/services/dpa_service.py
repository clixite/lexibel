"""DPA integration service — e-Deposit + JBox polling.

Belgian court e-filing (e-Deposit) and judicial communication (JBox)
via the DPA (Digitaal Platform voor Advocaten) API.

Certificate-based auth stub — real implementation requires:
- Client certificate (.p12) per lawyer/firm
- DPA API endpoint (production: https://dpa.just.fgov.be)
- OAuth2 token exchange with certificate
"""
import re
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

import httpx


# ── Constants ──

DPA_BASE_URL = "https://dpa.just.fgov.be/api/v1"  # production stub
DPA_TIMEOUT = 30.0
MAX_RETRIES = 3

VALID_COURT_CODES = {
    "BXL": "Tribunal de première instance de Bruxelles",
    "ANT": "Rechtbank van eerste aanleg Antwerpen",
    "LIE": "Tribunal de première instance de Liège",
    "GEN": "Rechtbank van eerste aanleg Gent",
    "NAM": "Tribunal de première instance de Namur",
    "CHA": "Tribunal de première instance de Charleroi",
    "MON": "Tribunal de première instance de Mons",
    "BRU": "Rechtbank van eerste aanleg Brugge",
    "LEU": "Rechtbank van eerste aanleg Leuven",
    "CC_FR": "Cour de cassation (FR)",
    "CC_NL": "Hof van Cassatie (NL)",
    "CA_BXL": "Cour d'appel de Bruxelles",
    "CA_LIE": "Cour d'appel de Liège",
    "CA_MON": "Cour d'appel de Mons",
}


# ── Data classes ──


@dataclass
class DepositDocument:
    """A document to upload via e-Deposit."""
    file_name: str
    content_type: str = "application/pdf"
    file_size: int = 0
    sha256_hash: str = ""
    document_type: str = "conclusions"  # conclusions, requete, pieces


@dataclass
class DepositResult:
    """Result of an e-Deposit submission."""
    deposit_id: str
    status: str  # submitted, accepted, rejected, processing
    court_code: str
    case_reference: str
    submitted_at: str
    documents_count: int
    message: str = ""


@dataclass
class DepositStatus:
    """Status of an e-Deposit."""
    deposit_id: str
    status: str
    court_code: str
    updated_at: str
    message: str = ""
    receipt_url: Optional[str] = None


@dataclass
class JBoxMessage:
    """A judicial communication from JBox."""
    message_id: str
    sender: str  # court name
    subject: str
    body_preview: str
    received_at: str
    case_reference: str = ""
    court_code: str = ""
    has_attachments: bool = False
    attachment_names: list[str] = field(default_factory=list)
    acknowledged: bool = False


# ── In-memory store for dev/test ──

_deposits: dict[str, DepositResult] = {}
_jbox_messages: dict[str, JBoxMessage] = {}
_acknowledged: set[str] = set()


def reset_store() -> None:
    """Reset in-memory stores (for tests)."""
    _deposits.clear()
    _jbox_messages.clear()
    _acknowledged.clear()


# ── DPA HTTP client with retry logic ──


class DPAClient:
    """HTTP client for DPA API with certificate-based auth stub."""

    def __init__(
        self,
        base_url: str = DPA_BASE_URL,
        cert_path: Optional[str] = None,
        cert_password: Optional[str] = None,
    ):
        self.base_url = base_url
        self.cert_path = cert_path
        self.cert_password = cert_password
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def _get_token(self) -> str:
        """Get OAuth2 token via certificate exchange.

        Stub: Returns a dummy token. Real implementation would:
        1. Load client certificate (.p12)
        2. POST to DPA token endpoint with certificate
        3. Cache token until expiry
        """
        if self._token and self._token_expires and datetime.now(timezone.utc) < self._token_expires:
            return self._token

        # Stub: in production, exchange certificate for token
        self._token = f"dpa_token_{uuid.uuid4().hex[:16]}"
        self._token_expires = datetime.now(timezone.utc)
        return self._token

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[dict] = None,
        retries: int = MAX_RETRIES,
    ) -> dict:
        """Make HTTP request with retry logic.

        Stub: Returns simulated responses. Real implementation would
        use httpx with client certificates.
        """
        token = await self._get_token()
        last_error: Optional[Exception] = None

        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=DPA_TIMEOUT) as client:
                    resp = await client.request(
                        method,
                        f"{self.base_url}{path}",
                        json=json_data,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                    )
                    resp.raise_for_status()
                    return resp.json()
            except httpx.HTTPError as e:
                last_error = e
                if attempt < retries - 1:
                    continue
                raise

        raise last_error or RuntimeError("Request failed after retries")


# ── Singleton client ──

_client = DPAClient()


# ── e-Deposit operations ──


async def submit_deposit(
    tenant_id: str,
    case_id: str,
    documents: list[dict],
    court_code: str,
    case_reference: str = "",
) -> DepositResult:
    """Submit documents to a Belgian court via e-Deposit.

    Args:
        tenant_id: Tenant UUID
        case_id: Internal case ID
        documents: List of dicts with file_name, content_type, file_size, sha256_hash
        court_code: Belgian court code (e.g. 'BXL', 'ANT')
        case_reference: Court case reference (e.g. '2026/001/A')

    Returns:
        DepositResult with deposit_id and status
    """
    if court_code not in VALID_COURT_CODES:
        raise ValueError(f"Invalid court_code: {court_code}. Valid: {list(VALID_COURT_CODES.keys())}")

    if not documents:
        raise ValueError("At least one document is required")

    # Validate documents
    parsed_docs = []
    for doc in documents:
        parsed_docs.append(DepositDocument(
            file_name=doc.get("file_name", "document.pdf"),
            content_type=doc.get("content_type", "application/pdf"),
            file_size=doc.get("file_size", 0),
            sha256_hash=doc.get("sha256_hash", ""),
            document_type=doc.get("document_type", "conclusions"),
        ))

    deposit_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Stub: In production, POST to DPA e-Deposit API
    # response = await _client._request("POST", "/deposits", json_data={...})

    result = DepositResult(
        deposit_id=deposit_id,
        status="submitted",
        court_code=court_code,
        case_reference=case_reference or f"{court_code}/{datetime.now().year}/{uuid.uuid4().hex[:6]}",
        submitted_at=now,
        documents_count=len(parsed_docs),
        message=f"Deposit submitted to {VALID_COURT_CODES[court_code]}",
    )

    _deposits[deposit_id] = result
    return result


async def check_deposit_status(deposit_id: str) -> DepositStatus:
    """Check the status of a previously submitted e-Deposit.

    Args:
        deposit_id: The deposit UUID returned from submit_deposit

    Returns:
        DepositStatus with current status and optional receipt URL
    """
    # Check local store first
    deposit = _deposits.get(deposit_id)
    if not deposit:
        raise ValueError(f"Deposit {deposit_id} not found")

    # Stub: In production, GET /deposits/{id}/status
    # response = await _client._request("GET", f"/deposits/{deposit_id}/status")

    return DepositStatus(
        deposit_id=deposit_id,
        status=deposit.status,
        court_code=deposit.court_code,
        updated_at=datetime.now(timezone.utc).isoformat(),
        message=f"Deposit {deposit.status}",
        receipt_url=f"https://dpa.just.fgov.be/receipts/{deposit_id}" if deposit.status == "accepted" else None,
    )


# ── JBox operations ──


def _seed_jbox_messages() -> None:
    """Seed sample JBox messages for dev/test."""
    if _jbox_messages:
        return

    samples = [
        JBoxMessage(
            message_id=str(uuid.uuid4()),
            sender="Tribunal de première instance de Bruxelles",
            subject="Notification de fixation — 2026/001/A",
            body_preview="L'affaire est fixée à l'audience du 15 mars 2026 à 9h00.",
            received_at="2026-02-15T10:30:00Z",
            case_reference="2026/001/A",
            court_code="BXL",
            has_attachments=True,
            attachment_names=["ordonnance_fixation.pdf"],
        ),
        JBoxMessage(
            message_id=str(uuid.uuid4()),
            sender="Cour d'appel de Bruxelles",
            subject="Communication de pièces — 2025/789/B",
            body_preview="Veuillez trouver ci-joint les pièces communiquées par la partie adverse.",
            received_at="2026-02-14T14:15:00Z",
            case_reference="2025/789/B",
            court_code="CA_BXL",
            has_attachments=True,
            attachment_names=["pieces_adverses.pdf", "inventaire.pdf"],
        ),
    ]
    for msg in samples:
        _jbox_messages[msg.message_id] = msg


async def poll_jbox(
    tenant_id: str,
    since: Optional[str] = None,
) -> list[JBoxMessage]:
    """Poll JBox for new judicial communications.

    Args:
        tenant_id: Tenant UUID
        since: ISO datetime string — only return messages after this time

    Returns:
        List of new JBoxMessage objects
    """
    # Stub: In production, GET /jbox/messages?since={since}
    # response = await _client._request("GET", "/jbox/messages", ...)

    _seed_jbox_messages()

    messages = list(_jbox_messages.values())

    # Filter by since datetime
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            messages = [
                m for m in messages
                if datetime.fromisoformat(m.received_at.replace("Z", "+00:00")) > since_dt
            ]
        except (ValueError, TypeError):
            pass

    # Exclude already acknowledged
    messages = [m for m in messages if m.message_id not in _acknowledged]

    return messages


async def get_jbox_messages(tenant_id: str) -> list[JBoxMessage]:
    """Get all JBox messages (including acknowledged).

    Args:
        tenant_id: Tenant UUID

    Returns:
        All JBox messages for the tenant
    """
    _seed_jbox_messages()
    return list(_jbox_messages.values())


async def acknowledge_jbox(message_id: str, tenant_id: str) -> JBoxMessage:
    """Acknowledge a JBox message.

    Args:
        message_id: The JBox message UUID
        tenant_id: Tenant UUID

    Returns:
        The acknowledged JBoxMessage
    """
    _seed_jbox_messages()

    msg = _jbox_messages.get(message_id)
    if not msg:
        raise ValueError(f"JBox message {message_id} not found")

    if message_id in _acknowledged:
        raise ValueError(f"JBox message {message_id} already acknowledged")

    # Stub: In production, POST /jbox/messages/{id}/acknowledge
    # await _client._request("POST", f"/jbox/messages/{message_id}/acknowledge")

    _acknowledged.add(message_id)
    msg.acknowledged = True
    return msg

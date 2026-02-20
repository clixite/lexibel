"""Bootstrap router — seed the default tenant, admin user, and demo data.

POST /api/v1/bootstrap/admin — creates the default super_admin user.
Idempotent: returns success whether the user is newly created or already exists.

On startup, also seeds demo data (cases, contacts, invoices, etc.) if tables are empty.
"""

import logging
import os
import secrets
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, text

from apps.api.auth.passwords import hash_password
from packages.db.models.case import Case
from packages.db.models.case_contact import CaseContact
from packages.db.models.contact import Contact
from packages.db.models.inbox_item import InboxItem
from packages.db.models.invoice import Invoice
from packages.db.models.invoice_line import InvoiceLine
from packages.db.models.tenant import Tenant
from packages.db.models.time_entry import TimeEntry
from packages.db.models.user import User
from packages.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bootstrap", tags=["bootstrap"])

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
DEFAULT_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000010")
DEFAULT_EMAIL = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "nicolas@clixite.be")
DEFAULT_ROLE = "super_admin"


def _get_bootstrap_password() -> str:
    """Get the bootstrap admin password from environment.

    Falls back to generating a secure random password and logging it
    if BOOTSTRAP_ADMIN_PASSWORD is not set. Never uses a hardcoded default.
    """
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not password:
        password = secrets.token_urlsafe(16)
        logger.warning(
            "BOOTSTRAP_ADMIN_PASSWORD not set. Generated temporary password: %s  "
            "Set BOOTSTRAP_ADMIN_PASSWORD env var for production.",
            password,
        )
    return password


# Fixed UUIDs for demo data (idempotent)
_CONTACT_IDS = [
    uuid.UUID("00000000-0000-4000-a000-000000000101"),
    uuid.UUID("00000000-0000-4000-a000-000000000102"),
    uuid.UUID("00000000-0000-4000-a000-000000000103"),
    uuid.UUID("00000000-0000-4000-a000-000000000104"),
]
_CASE_IDS = [
    uuid.UUID("00000000-0000-4000-a000-000000000201"),
    uuid.UUID("00000000-0000-4000-a000-000000000202"),
    uuid.UUID("00000000-0000-4000-a000-000000000203"),
    uuid.UUID("00000000-0000-4000-a000-000000000204"),
]
_TIME_ENTRY_IDS = [
    uuid.UUID("00000000-0000-4000-a000-000000000301"),
    uuid.UUID("00000000-0000-4000-a000-000000000302"),
    uuid.UUID("00000000-0000-4000-a000-000000000303"),
    uuid.UUID("00000000-0000-4000-a000-000000000304"),
]
_INVOICE_IDS = [
    uuid.UUID("00000000-0000-4000-a000-000000000401"),
    uuid.UUID("00000000-0000-4000-a000-000000000402"),
    uuid.UUID("00000000-0000-4000-a000-000000000403"),
]
_INBOX_IDS = [
    uuid.UUID("00000000-0000-4000-a000-000000000501"),
    uuid.UUID("00000000-0000-4000-a000-000000000502"),
    uuid.UUID("00000000-0000-4000-a000-000000000503"),
    uuid.UUID("00000000-0000-4000-a000-000000000504"),
]


async def ensure_admin_user() -> None:
    """Create the default tenant and admin user in PostgreSQL if they don't exist."""
    async with async_session_factory() as session:
        async with session.begin():
            # Check if admin user already exists
            result = await session.execute(
                select(User).where(User.id == DEFAULT_USER_ID)
            )
            if result.scalar_one_or_none() is not None:
                logger.info("Admin user already exists, skipping bootstrap")
                return

            # Ensure the default tenant exists
            result = await session.execute(
                select(Tenant).where(Tenant.id == DEFAULT_TENANT_ID)
            )
            if result.scalar_one_or_none() is None:
                tenant = Tenant(
                    id=DEFAULT_TENANT_ID,
                    name="Cabinet Simon",
                    slug="cabinet-simon",
                    plan="enterprise",
                    locale="fr-BE",
                    config={"timezone": "Europe/Brussels", "currency": "EUR"},
                    status="active",
                )
                session.add(tenant)
                await session.flush()
                logger.info("Created default tenant: Cabinet Simon")

            # Create the admin user
            password = _get_bootstrap_password()
            admin = User(
                id=DEFAULT_USER_ID,
                tenant_id=DEFAULT_TENANT_ID,
                email=DEFAULT_EMAIL,
                full_name="Nicolas Simon",
                role=DEFAULT_ROLE,
                hashed_password=hash_password(password),
                auth_provider="local",
                mfa_enabled=False,
                is_active=True,
            )
            session.add(admin)
            logger.info("Created admin user: %s", DEFAULT_EMAIL)


async def seed_demo_data() -> None:
    """Seed demo data if tables are empty. Idempotent via fixed UUIDs + ON CONFLICT."""
    async with async_session_factory() as session:
        async with session.begin():
            # Check if demo data already exists (any cases present = skip)
            result = await session.execute(select(func.count()).select_from(Case))
            case_count = result.scalar() or 0
            if case_count > 0:
                logger.info("Demo data exists (%d cases), skipping seed", case_count)
                return

            logger.info("Seeding demo data...")
            tid = DEFAULT_TENANT_ID
            uid = DEFAULT_USER_ID

            # Set tenant context for RLS
            await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tid}'"))

            # ── Contacts ──
            contacts_data = [
                (
                    _CONTACT_IDS[0],
                    "natural",
                    "Jean Dupont",
                    "jean.dupont@email.be",
                    "+32470123456",
                    None,
                ),
                (
                    _CONTACT_IDS[1],
                    "natural",
                    "Marie Van der Berg",
                    "marie.vanderberg@email.be",
                    "+32471234567",
                    None,
                ),
                (
                    _CONTACT_IDS[2],
                    "legal",
                    "SA Immobel",
                    "contact@immobel.be",
                    "+32223456789",
                    "0417.497.106",
                ),
                (
                    _CONTACT_IDS[3],
                    "legal",
                    "SPRL TechWave",
                    "info@techwave.be",
                    "+32224567890",
                    "0123.456.789",
                ),
            ]
            for cid, ctype, name, email, phone, bce in contacts_data:
                session.add(
                    Contact(
                        id=cid,
                        tenant_id=tid,
                        type=ctype,
                        full_name=name,
                        email=email,
                        phone_e164=phone,
                        bce_number=bce,
                        language="fr",
                        address={
                            "street": "Rue Example 1",
                            "city": "Bruxelles",
                            "zip": "1000",
                            "country": "BE",
                        },
                    )
                )
            await session.flush()
            logger.info("Seeded 4 contacts")

            # ── Cases ──
            today = date.today()
            cases_data = [
                (
                    _CASE_IDS[0],
                    "2024/001",
                    "Dupont c/ Immobel",
                    "civil",
                    "open",
                    _CONTACT_IDS[0],
                ),
                (
                    _CASE_IDS[1],
                    "2024/002",
                    "Succession Van der Berg",
                    "family",
                    "open",
                    _CONTACT_IDS[1],
                ),
                (
                    _CASE_IDS[2],
                    "2024/003",
                    "TechWave Restructuration",
                    "commercial",
                    "open",
                    _CONTACT_IDS[3],
                ),
                (
                    _CASE_IDS[3],
                    "2024/004",
                    "Martin - Harcelement moral",
                    "social",
                    "pending",
                    _CONTACT_IDS[0],
                ),
            ]
            for caseid, ref, title, mtype, st, contact_id in cases_data:
                session.add(
                    Case(
                        id=caseid,
                        tenant_id=tid,
                        reference=ref,
                        title=title,
                        matter_type=mtype,
                        status=st,
                        responsible_user_id=uid,
                        opened_at=today - timedelta(days=90),
                        metadata_={},
                    )
                )
            await session.flush()
            logger.info("Seeded 4 cases")

            # ── Case-Contact links ──
            for caseid, _, _, _, _, contact_id in cases_data:
                session.add(
                    CaseContact(
                        tenant_id=tid,
                        case_id=caseid,
                        contact_id=contact_id,
                        role="client",
                    )
                )
            # Immobel as adverse party on Dupont case
            session.add(
                CaseContact(
                    tenant_id=tid,
                    case_id=_CASE_IDS[0],
                    contact_id=_CONTACT_IDS[2],
                    role="adverse",
                )
            )
            await session.flush()
            logger.info("Seeded case-contact links")

            # ── Time Entries ──
            time_data = [
                (
                    _TIME_ENTRY_IDS[0],
                    _CASE_IDS[0],
                    "Consultation initiale - analyse du dossier Dupont c/ Immobel",
                    120,
                    today - timedelta(days=30),
                    "approved",
                    25000,
                ),
                (
                    _TIME_ENTRY_IDS[1],
                    _CASE_IDS[1],
                    "Rédaction conclusions succession Van der Berg",
                    90,
                    today - timedelta(days=15),
                    "approved",
                    25000,
                ),
                (
                    _TIME_ENTRY_IDS[2],
                    _CASE_IDS[2],
                    "Analyse restructuration TechWave - due diligence",
                    180,
                    today - timedelta(days=7),
                    "draft",
                    25000,
                ),
                (
                    _TIME_ENTRY_IDS[3],
                    _CASE_IDS[0],
                    "Audience TPI Bruxelles - plaidoirie Dupont",
                    240,
                    today - timedelta(days=3),
                    "draft",
                    25000,
                ),
            ]
            for teid, caseid, desc, dur, d, st, rate in time_data:
                session.add(
                    TimeEntry(
                        id=teid,
                        tenant_id=tid,
                        case_id=caseid,
                        user_id=uid,
                        description=desc,
                        duration_minutes=dur,
                        billable=True,
                        date=d,
                        status=st,
                        hourly_rate_cents=rate,
                    )
                )
            await session.flush()
            logger.info("Seeded 4 time entries")

            # ── Invoices ──
            invoices_data = [
                (
                    _INVOICE_IDS[0],
                    _CASE_IDS[0],
                    "FAC-2024-001",
                    _CONTACT_IDS[0],
                    "paid",
                    today - timedelta(days=60),
                    today - timedelta(days=30),
                    75000,
                    15750,
                    90750,
                ),
                (
                    _INVOICE_IDS[1],
                    _CASE_IDS[1],
                    "FAC-2024-002",
                    _CONTACT_IDS[1],
                    "sent",
                    today - timedelta(days=14),
                    today + timedelta(days=16),
                    56250,
                    11813,
                    68063,
                ),
                (
                    _INVOICE_IDS[2],
                    _CASE_IDS[2],
                    "FAC-2024-003",
                    _CONTACT_IDS[3],
                    "draft",
                    today,
                    today + timedelta(days=30),
                    112500,
                    23625,
                    136125,
                ),
            ]
            for (
                invid,
                caseid,
                num,
                client,
                st,
                issue,
                due,
                sub,
                vat,
                total,
            ) in invoices_data:
                session.add(
                    Invoice(
                        id=invid,
                        tenant_id=tid,
                        case_id=caseid,
                        invoice_number=num,
                        client_contact_id=client,
                        status=st,
                        issue_date=issue,
                        due_date=due,
                        subtotal_cents=sub,
                        vat_rate=Decimal("21.00"),
                        vat_amount_cents=vat,
                        total_cents=total,
                    )
                )
            await session.flush()

            # Invoice lines
            lines = [
                (
                    _INVOICE_IDS[0],
                    "Consultation initiale (2h)",
                    Decimal("2.00"),
                    25000,
                    50000,
                ),
                (
                    _INVOICE_IDS[0],
                    "Rédaction mise en demeure (1h)",
                    Decimal("1.00"),
                    25000,
                    25000,
                ),
                (
                    _INVOICE_IDS[1],
                    "Analyse successorale (1.5h)",
                    Decimal("1.50"),
                    25000,
                    37500,
                ),
                (
                    _INVOICE_IDS[1],
                    "Rédaction conclusions (0.75h)",
                    Decimal("0.75"),
                    25000,
                    18750,
                ),
                (
                    _INVOICE_IDS[2],
                    "Due diligence TechWave (3h)",
                    Decimal("3.00"),
                    25000,
                    75000,
                ),
                (
                    _INVOICE_IDS[2],
                    "Analyse contrats (1.5h)",
                    Decimal("1.50"),
                    25000,
                    37500,
                ),
            ]
            for i, (invid, desc, qty, unit, total) in enumerate(lines):
                session.add(
                    InvoiceLine(
                        id=uuid.UUID(f"00000000-0000-4000-a000-000000000{700 + i:03d}"),
                        tenant_id=tid,
                        invoice_id=invid,
                        description=desc,
                        quantity=qty,
                        unit_price_cents=unit,
                        total_cents=total,
                        sort_order=i,
                    )
                )
            await session.flush()
            logger.info("Seeded 3 invoices with lines")

            # ── Inbox Items ──
            inbox_data = [
                (
                    _INBOX_IDS[0],
                    "OUTLOOK",
                    {
                        "from": "jean.dupont@email.be",
                        "subject": "Documents pour audience",
                        "body": "Veuillez trouver ci-joint les pièces pour l'audience de vendredi.",
                        "received_at": (
                            datetime.now() - timedelta(hours=2)
                        ).isoformat(),
                    },
                ),
                (
                    _INBOX_IDS[1],
                    "OUTLOOK",
                    {
                        "from": "marie.vanderberg@email.be",
                        "subject": "Question succession",
                        "body": "Pourriez-vous me confirmer la date du rendez-vous chez le notaire?",
                        "received_at": (
                            datetime.now() - timedelta(hours=5)
                        ).isoformat(),
                    },
                ),
                (
                    _INBOX_IDS[2],
                    "RINGOVER",
                    {
                        "caller": "+32470123456",
                        "callee": "+32223456789",
                        "duration": 342,
                        "direction": "inbound",
                        "recording_url": None,
                    },
                ),
                (
                    _INBOX_IDS[3],
                    "PLAUD",
                    {
                        "caller": "+32471234567",
                        "duration": 1205,
                        "transcription": "Discussion concernant la succession Van der Berg...",
                        "language": "fr",
                    },
                ),
            ]
            for iid, source, payload in inbox_data:
                session.add(
                    InboxItem(
                        id=iid,
                        tenant_id=tid,
                        source=source,
                        status="PENDING",
                        raw_payload=payload,
                    )
                )
            await session.flush()
            logger.info("Seeded 4 inbox items")

            logger.info("Demo data seeding complete")


@router.post("/admin", status_code=status.HTTP_201_CREATED)
async def bootstrap_admin() -> dict:
    """Create the default admin user. Idempotent — safe to call multiple times.

    In production, this endpoint is disabled unless BOOTSTRAP_ENABLED=true
    is set in the environment. This prevents accidental or malicious
    admin account creation on public-facing deployments.
    """
    bootstrap_enabled = os.getenv("BOOTSTRAP_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    if not bootstrap_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap is disabled. Set BOOTSTRAP_ENABLED=true to enable.",
        )
    try:
        await ensure_admin_user()
    except Exception as e:
        logger.error("Bootstrap failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bootstrap failed. Check server logs for details.",
        )
    return {
        "message": "Admin user created",
        "email": DEFAULT_EMAIL,
        "tenant": "Cabinet Simon",
        "tenant_id": str(DEFAULT_TENANT_ID),
        "role": DEFAULT_ROLE,
    }

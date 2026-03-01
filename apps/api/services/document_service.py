"""Document service — file upload/download via MinIO/S3 with SHA-256 hashing."""

import hashlib
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.services.storage_client import download_object, upload_object
from packages.db.models.evidence_link import EvidenceLink

logger = logging.getLogger(__name__)


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest of file contents."""
    return hashlib.sha256(data).hexdigest()


async def upload_file(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    interaction_event_id: uuid.UUID,
    *,
    file_name: str,
    file_data: bytes,
    mime_type: str,
) -> EvidenceLink:
    """Upload a file to MinIO/S3 and create an EvidenceLink record."""
    sha256 = compute_sha256(file_data)
    file_size = len(file_data)

    # Build the storage path: {tenant_id}/{event_id}/{filename}
    file_path = f"{tenant_id}/{interaction_event_id}/{file_name}"

    # Upload to MinIO/S3
    uploaded = upload_object(file_path, file_data, content_type=mime_type)
    if not uploaded:
        logger.warning("S3 upload unavailable, storing metadata only: %s", file_path)

    link = EvidenceLink(
        tenant_id=tenant_id,
        interaction_event_id=interaction_event_id,
        file_path=file_path,
        file_name=file_name,
        mime_type=mime_type,
        file_size_bytes=file_size,
        sha256_hash=sha256,
    )
    session.add(link)
    await session.flush()
    await session.refresh(link)
    return link


async def get_evidence_link(
    session: AsyncSession,
    link_id: uuid.UUID,
) -> EvidenceLink | None:
    """Get a single evidence link by ID (RLS filters by tenant)."""
    result = await session.execute(
        select(EvidenceLink).where(EvidenceLink.id == link_id)
    )
    return result.scalar_one_or_none()


async def download_file(
    session: AsyncSession,
    link_id: uuid.UUID,
) -> tuple[EvidenceLink | None, bytes | None]:
    """Download a file by evidence link ID from MinIO/S3."""
    link = await get_evidence_link(session, link_id)
    if link is None:
        return None, None

    # Fetch from MinIO/S3
    data = download_object(link.file_path)
    if data is None:
        logger.warning("S3 download unavailable for: %s", link.file_path)
        return link, b""

    return link, data


async def list_files_for_event(
    session: AsyncSession,
    interaction_event_id: uuid.UUID,
) -> list[EvidenceLink]:
    """List all evidence links for an interaction event."""
    result = await session.execute(
        select(EvidenceLink)
        .where(EvidenceLink.interaction_event_id == interaction_event_id)
        .order_by(EvidenceLink.created_at.asc())
    )
    return list(result.scalars().all())

"""Microsoft OneDrive and SharePoint synchronization service.

Syncs file metadata from OneDrive/SharePoint into cloud_documents table.
Files are NOT copied (GDPR compliance).

Uses Microsoft Graph API v1.0 via raw HTTP with Bearer token.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.cloud_document import CloudDocument
from packages.db.models.cloud_sync_job import CloudSyncJob
from apps.api.services.oauth_engine import get_oauth_engine

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_TIMEOUT = 30.0

OFFICE_EXTENSIONS = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def _get_edit_url(item: dict) -> Optional[str]:
    """Return the Office Online edit URL for a file."""
    # The webUrl from Graph API opens in the browser with Office Online automatically
    return item.get("webUrl")


class OneDriveSync:
    """Synchronizes OneDrive/SharePoint files into cloud_documents."""

    async def list_files(
        self,
        session: AsyncSession,
        token_id: UUID,
        tenant_id: UUID,
        item_id: Optional[str] = None,
        site_id: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> dict:
        """List files from OneDrive or SharePoint folder.
        
        Returns: {"value": [...], "@odata.nextLink": str | None}
        """
        oauth_engine = get_oauth_engine()
        access_token = await oauth_engine.get_valid_token(session, token_id)

        # Build endpoint
        if site_id:
            base = f"{GRAPH_BASE_URL}/sites/{site_id}"
            if drive_id:
                base += f"/drives/{drive_id}"
            else:
                base += "/drive"
        else:
            base = f"{GRAPH_BASE_URL}/me/drive"

        if item_id:
            endpoint = f"{base}/items/{item_id}/children"
        else:
            endpoint = f"{base}/root/children"

        params = {
            "": "id,name,file,folder,size,webUrl,lastModifiedDateTime,lastModifiedBy,parentReference,@microsoft.graph.downloadUrl",
            "": 100,
        }

        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            response.raise_for_status()
            return response.json()
    async def sync_folder(
        self,
        session: AsyncSession,
        token_id: UUID,
        tenant_id: UUID,
        item_id: Optional[str] = None,
        recursive: bool = True,
        job_id: Optional[UUID] = None,
        parent_path: str = "",
        site_id: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> dict:
        """Recursively sync a OneDrive/SharePoint folder."""
        synced = 0
        errors = 0
        provider = "sharepoint" if site_id else "onedrive"

        result = await self.list_files(
            session, token_id, tenant_id, item_id, site_id, drive_id
        )

        for item in result.get("value", []):
            try:
                is_folder = "folder" in item
                file_path = f"{parent_path}/{item['name']}".lstrip("/")

                await self._upsert_document(
                    session, token_id, tenant_id, item, file_path, provider
                )
                synced += 1

                if job_id:
                    await self._update_job_progress(session, job_id, synced)

                if recursive and is_folder:
                    sub = await self.sync_folder(
                        session, token_id, tenant_id,
                        item["id"], recursive, job_id, file_path,
                        site_id, drive_id
                    )
                    synced += sub["synced"]
                    errors += sub["errors"]

            except Exception as e:
                logger.error(f"Failed to sync OneDrive item {item.get('id')}: {e}")
                errors += 1

        # Handle pagination
        next_link = result.get("@odata.nextLink")
        if next_link:
            oauth_engine = get_oauth_engine()
            access_token = await oauth_engine.get_valid_token(session, token_id)
            async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
                resp = await client.get(
                    next_link,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code == 200:
                    for item in resp.json().get("value", []):
                        try:
                            await self._upsert_document(
                                session, token_id, tenant_id, item,
                                f"{parent_path}/{item['name']}".lstrip("/"), provider
                            )
                            synced += 1
                        except Exception as e:
                            logger.error(f"Pagination sync error: {e}")
                            errors += 1

        return {"synced": synced, "errors": errors}

    async def incremental_sync(
        self,
        session: AsyncSession,
        token_id: UUID,
        tenant_id: UUID,
        since: Optional[datetime] = None,
    ) -> dict:
        """Use Graph delta API for efficient incremental sync."""
        oauth_engine = get_oauth_engine()
        access_token = await oauth_engine.get_valid_token(session, token_id)

        # Use delta query for efficient change detection
        endpoint = f"{GRAPH_BASE_URL}/me/drive/root/delta"
        synced = 0
        errors = 0

        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            response = await client.get(
                endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"": "id,name,file,folder,size,webUrl,lastModifiedDateTime,parentReference"},
            )
            response.raise_for_status()
            data = response.json()

        for item in data.get("value", []):
            try:
                if not item.get("deleted"):
                    await self._upsert_document(
                        session, token_id, tenant_id, item, "", "onedrive"
                    )
                    synced += 1
            except Exception as e:
                logger.error(f"Delta sync error for {item.get('id')}: {e}")
                errors += 1

        return {"synced": synced, "errors": errors}
    async def list_sharepoint_sites(
        self, session: AsyncSession, token_id: UUID
    ) -> list[dict]:
        """List accessible SharePoint sites."""
        oauth_engine = get_oauth_engine()
        access_token = await oauth_engine.get_valid_token(session, token_id)

        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            response = await client.get(
                f"{GRAPH_BASE_URL}/sites",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"search": "*", "": "id,displayName,webUrl,description"},
            )
            response.raise_for_status()
            return response.json().get("value", [])
    async def get_file_content(
        self,
        session: AsyncSession,
        token_id: UUID,
        item_id: str,
    ) -> bytes:
        """Download file content from OneDrive."""
        oauth_engine = get_oauth_engine()
        access_token = await oauth_engine.get_valid_token(session, token_id)

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(
                f"{GRAPH_BASE_URL}/me/drive/items/{item_id}/content",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.content
    async def search_files(
        self, session: AsyncSession, token_id: UUID, tenant_id: UUID, query: str
    ) -> list[dict]:
        """Search OneDrive files."""
        oauth_engine = get_oauth_engine()
        access_token = await oauth_engine.get_valid_token(session, token_id)

        safe_query = query.replace("'", "''")
        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            response = await client.get(
                f"{GRAPH_BASE_URL}/me/drive/root/search(q='{safe_query}')",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"": "id,name,file,folder,size,webUrl,lastModifiedDateTime"},
            )
            response.raise_for_status()
            return response.json().get("value", [])
    async def _upsert_document(
        self,
        session: AsyncSession,
        token_id: UUID,
        tenant_id: UUID,
        item: dict,
        path: str,
        provider: str,
    ) -> CloudDocument:
        """Insert or update a cloud_document record."""
        item_id = item["id"]
        is_folder = "folder" in item
        mime_type = None
        if "file" in item:
            mime_type = item["file"].get("mimeType")
        
        # Modified time
        modified_time = None
        if item.get("lastModifiedDateTime"):
            try:
                modified_time = datetime.fromisoformat(
                    item["lastModifiedDateTime"].replace("Z", "+00:00")
                )
            except Exception:
                pass

        last_modifier = None
        if item.get("lastModifiedBy", {}).get("user"):
            last_modifier = item["lastModifiedBy"]["user"].get("displayName")

        web_url = item.get("webUrl")
        edit_url = web_url  # Office Online opens automatically

        parent_id = item.get("parentReference", {}).get("id")
        size = item.get("size")

        # Check existing
        stmt = select(CloudDocument).where(
            CloudDocument.tenant_id == tenant_id,
            CloudDocument.provider == provider,
            CloudDocument.external_id == item_id,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = item["name"]
            existing.mime_type = mime_type
            existing.size_bytes = size
            existing.web_url = web_url
            existing.edit_url = edit_url
            existing.last_modified_at = modified_time
            existing.last_modified_by = last_modifier
            existing.path = path
            existing.external_parent_id = parent_id
            await session.flush()
            return existing
        else:
            doc = CloudDocument(
                tenant_id=tenant_id,
                oauth_token_id=token_id,
                provider=provider,
                external_id=item_id,
                external_parent_id=parent_id,
                name=item["name"],
                mime_type=mime_type,
                size_bytes=size,
                web_url=web_url,
                edit_url=edit_url,
                is_folder=is_folder,
                path=path,
                last_modified_at=modified_time,
                last_modified_by=last_modifier,
                is_indexed=False,
                index_status="pending",
            )
            session.add(doc)
            await session.flush()
            return doc
    async def _update_job_progress(
        self, session: AsyncSession, job_id: UUID, processed: int
    ) -> None:
        result = await session.execute(
            select(CloudSyncJob).where(CloudSyncJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job:
            job.processed_items = processed
            await session.flush()


# Singleton
_onedrive_sync: OneDriveSync | None = None


def get_onedrive_sync() -> OneDriveSync:
    global _onedrive_sync
    if _onedrive_sync is None:
        _onedrive_sync = OneDriveSync()
    return _onedrive_sync

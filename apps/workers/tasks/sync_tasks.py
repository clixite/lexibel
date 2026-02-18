"""Celery tasks for document and email synchronization.

These tasks run asynchronously in the Celery worker process.
They sync documents from Google Drive / OneDrive into the cloud_documents table.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from celery import shared_task
from sqlalchemy import select

logger = logging.getLogger(__name__)


@shared_task(
    name='sync_documents',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='indexing',
)
def sync_documents(
    self,
    connection_id: str,
    job_id: str,
    job_type: str = 'full_sync',
    folder_id: Optional[str] = None,
):
    '''Sync documents from Google Drive or OneDrive.
    
    Args:
        connection_id: UUID string of the OAuth token (connection)
        job_id: UUID string of the CloudSyncJob record
        job_type: 'full_sync' | 'incremental_sync' | 'folder_sync'
        folder_id: Optional folder ID to sync (for folder_sync)
    '''
    import asyncio
    
    async def _run():
        from packages.db.session import async_session_factory
        from packages.db.models.oauth_token import OAuthToken
        from packages.db.models.cloud_sync_job import CloudSyncJob

        token_uuid = uuid.UUID(connection_id)
        job_uuid = uuid.UUID(job_id)

        async with async_session_factory() as session:
            async with session.begin():
                # Load connection
                token_result = await session.execute(
                    select(OAuthToken).where(OAuthToken.id == token_uuid)
                )
                token = token_result.scalar_one_or_none()
                if not token:
                    logger.error(f'OAuth token {connection_id} not found')
                    return

                # Load job
                job_result = await session.execute(
                    select(CloudSyncJob).where(CloudSyncJob.id == job_uuid)
                )
                job = job_result.scalar_one_or_none()
                if not job:
                    logger.error(f'Sync job {job_id} not found')
                    return

                # Mark job as running
                job.status = 'running'
                job.started_at = datetime.now(timezone.utc)
                await session.flush()
                try:
                    if token.provider == 'google':
                        from apps.api.services.google_drive_sync import get_google_drive_sync
                        sync_service = get_google_drive_sync()

                        if job_type == 'incremental_sync':
                            result = await sync_service.incremental_sync(
                                session, token.id, token.tenant_id,
                                since=token.last_sync_at if hasattr(token, 'last_sync_at') else None,
                            )
                        else:
                            result = await sync_service.sync_folder(
                                session, token.id, token.tenant_id,
                                folder_id=folder_id or 'root',
                                recursive=True,
                                job_id=job_uuid,
                            )

                    else:  # microsoft
                        from apps.api.services.microsoft_onedrive_sync import get_onedrive_sync
                        sync_service = get_onedrive_sync()

                        if job_type == 'incremental_sync':
                            result = await sync_service.incremental_sync(
                                session, token.id, token.tenant_id,
                                )
                        else:
                            result = await sync_service.sync_folder(
                                session, token.id, token.tenant_id,
                                item_id=folder_id,
                                recursive=True,
                                job_id=job_uuid,
                            )

                    # Mark job as completed
                    job.status = 'completed'
                    job.completed_at = datetime.now(timezone.utc)
                    job.processed_items = result.get('synced', 0)
                    job.error_count = result.get('errors', 0)
                    
                    # Update last_sync_at on token
                    if hasattr(token, 'sync_status'):
                        token.sync_status = 'idle'
                    if hasattr(token, 'last_sync_at'):
                        token.last_sync_at = datetime.now(timezone.utc)

                    logger.info(
                        f'Sync completed for {connection_id}: '
                        f'{result.get(\'synced\', 0)} synced, {result.get(\'errors\', 0)} errors'
                        )

                except Exception as e:
                    logger.error(f'Sync failed for {connection_id}: {e}', exc_info=True)
                    job.status = 'failed'
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_message = str(e)
                    if hasattr(token, 'sync_status'):
                        token.sync_status = 'error'
                    if hasattr(token, 'sync_error'):
                        token.sync_error = str(e)
                    raise

    asyncio.run(_run())


@shared_task(
    name='sync_emails',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='default',
)
def sync_emails(
    self,
    connection_id: str,
    since_iso: Optional[str] = None,
):
    '''Sync emails from Gmail or Outlook.
    
    Args:
        connection_id: UUID string of the OAuth token
        since_iso: ISO datetime string for incremental sync
    '''
    import asyncio

    async def _run():
        from packages.db.session import async_session_factory
        from packages.db.models.oauth_token import OAuthToken

        token_uuid = uuid.UUID(connection_id)
        since = datetime.fromisoformat(since_iso) if since_iso else None

        async with async_session_factory() as session:
            async with session.begin():
                token_result = await session.execute(
                    select(OAuthToken).where(OAuthToken.id == token_uuid)
                )
                token = token_result.scalar_one_or_none()
                if not token:
                    logger.error(f'OAuth token {connection_id} not found')
                    return

                try:
                    if token.provider == 'google':
                        from apps.api.services.gmail_sync_service import get_gmail_sync_service
                        gmail_sync = get_gmail_sync_service()
                        result = await gmail_sync.sync_emails(
                            session, token.tenant_id, token.user_id, max_results=100
                        )
                    else:
                        from apps.api.services.microsoft_outlook_sync_service import (
                            get_microsoft_outlook_sync_service,
                        )
                        outlook_sync = get_microsoft_outlook_sync_service()
                        result = await outlook_sync.sync_to_db(
                            session, token.tenant_id, token.user_id,
                            since_date=since, max_results=100
                        )

                    logger.info(f'Email sync completed for {connection_id}: {result}')

                except Exception as e:
                    logger.error(f'Email sync failed for {connection_id}: {e}', exc_info=True)
                    raise

    asyncio.run(_run())


@shared_task(name="scheduled_incremental_sync", queue="indexing")
def scheduled_incremental_sync():
    """Run incremental sync for all active connections.

    Called by Celery Beat every 15 minutes.
    Dispatches individual sync_documents tasks for each active connection.
    """
    import asyncio

    from apps.db.database import async_session_factory
    from apps.db.models import CloudConnection

    async def _run():
        async with async_session_factory() as session:
            result = await session.execute(
                select(CloudConnection).where(CloudConnection.is_active == True)  # noqa: E712
            )
            connections = result.scalars().all()
            for conn in connections:
                sync_documents.delay(
                    connection_id=str(conn.id),
                    job_id=str(uuid.uuid4()),
                    job_type="incremental",
                )
            logger.info(f"Dispatched incremental sync for {len(connections)} connections")

    asyncio.run(_run())


@shared_task(name="refresh_expiring_tokens", queue="default")
def refresh_expiring_tokens():
    """Refresh OAuth tokens expiring within 15 minutes.

    Called by Celery Beat every 45 minutes.
    """
    import asyncio
    from datetime import timedelta

    from apps.db.database import async_session_factory
    from apps.db.models import CloudConnection
    from apps.services.oauth_engine import oauth_engine

    async def _run():
        threshold = datetime.now(timezone.utc) + timedelta(minutes=15)
        async with async_session_factory() as session:
            result = await session.execute(
                select(CloudConnection).where(
                    CloudConnection.is_active == True,  # noqa: E712
                    CloudConnection.token_expiry < threshold,
                )
            )
            connections = result.scalars().all()
            refreshed = 0
            for conn in connections:
                try:
                    await oauth_engine.refresh_token(conn)
                    refreshed += 1
                except Exception as e:
                    logger.warning(f"Token refresh failed for {conn.id}: {e}")
            logger.info(f"Refreshed {refreshed}/{len(connections)} expiring tokens")

    asyncio.run(_run())

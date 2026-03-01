"""S3/MinIO storage client — async-compatible wrapper around boto3.

Provides upload, download, and delete operations for file storage.
Uses MinIO in development, any S3-compatible service in production.
Gracefully returns None if storage is not configured (dev fallback).
"""

import io
import logging
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

_s3_client = None
_initialized = False

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "lexibel")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"


def _get_s3_client():
    """Get or create the boto3 S3 client singleton."""
    global _s3_client, _initialized
    if _initialized:
        return _s3_client
    _initialized = True

    if not MINIO_ENDPOINT or not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
        logger.info("MinIO/S3 not configured — file storage disabled")
        return None

    try:
        scheme = "https" if MINIO_USE_SSL else "http"
        endpoint_url = f"{scheme}://{MINIO_ENDPOINT}"
        _s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name="us-east-1",
        )
        # Ensure bucket exists
        _ensure_bucket(_s3_client, MINIO_BUCKET)
        logger.info("MinIO/S3 client initialized: %s", endpoint_url)
        return _s3_client
    except Exception as e:
        logger.warning("Failed to initialize MinIO/S3 client: %s", e)
        _s3_client = None
        return None


def _ensure_bucket(client, bucket: str) -> None:
    """Create the bucket if it doesn't exist."""
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=bucket)
            logger.info("Created bucket: %s", bucket)
        else:
            raise


def upload_object(
    key: str, data: bytes, content_type: str = "application/octet-stream"
) -> bool:
    """Upload bytes to S3/MinIO. Returns True on success, False if storage unavailable."""
    client = _get_s3_client()
    if client is None:
        return False
    try:
        client.put_object(
            Bucket=MINIO_BUCKET,
            Key=key.lstrip("/"),
            Body=io.BytesIO(data),
            ContentLength=len(data),
            ContentType=content_type,
        )
        return True
    except (BotoCoreError, ClientError) as e:
        logger.error("S3 upload failed for %s: %s", key, e)
        return False


def download_object(key: str) -> bytes | None:
    """Download bytes from S3/MinIO. Returns None if unavailable or not found."""
    client = _get_s3_client()
    if client is None:
        return None
    try:
        response = client.get_object(
            Bucket=MINIO_BUCKET,
            Key=key.lstrip("/"),
        )
        return response["Body"].read()
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "NoSuchKey":
            logger.warning("S3 object not found: %s", key)
        else:
            logger.error("S3 download failed for %s: %s", key, e)
        return None
    except BotoCoreError as e:
        logger.error("S3 download failed for %s: %s", key, e)
        return None


def delete_object(key: str) -> bool:
    """Delete an object from S3/MinIO. Returns True on success."""
    client = _get_s3_client()
    if client is None:
        return False
    try:
        client.delete_object(
            Bucket=MINIO_BUCKET,
            Key=key.lstrip("/"),
        )
        return True
    except (BotoCoreError, ClientError) as e:
        logger.error("S3 delete failed for %s: %s", key, e)
        return False


def reset_client() -> None:
    """Reset the client (for testing)."""
    global _s3_client, _initialized
    _s3_client = None
    _initialized = False

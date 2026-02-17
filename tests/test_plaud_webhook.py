"""Test script for Plaud.ai webhook integration.

This script demonstrates how to test the Plaud webhook endpoint
with proper HMAC signature verification.
"""

import hashlib
import hmac
import json
from pathlib import Path

import httpx

# Configuration
WEBHOOK_URL = "http://localhost:8000/api/v1/webhooks/plaud"
WEBHOOK_SECRET = "plaud-dev-secret"  # Should match PLAUD_WEBHOOK_SECRET in .env


def generate_hmac_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload: Raw JSON payload as bytes
        secret: Shared webhook secret

    Returns:
        Hex-encoded HMAC signature
    """
    mac = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256)
    return mac.hexdigest()


async def test_plaud_webhook():
    """Test Plaud webhook with example payload."""
    # Load example payload
    example_path = Path(__file__).parent.parent / "docs" / "plaud_webhook_example.json"

    with open(example_path, "r", encoding="utf-8") as f:
        payload_dict = json.load(f)

    # Convert to bytes
    payload_bytes = json.dumps(payload_dict).encode("utf-8")

    # Generate signature
    signature = generate_hmac_signature(payload_bytes, WEBHOOK_SECRET)

    # Send request
    headers = {
        "Content-Type": "application/json",
        "X-Plaud-Signature": signature,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            WEBHOOK_URL,
            content=payload_bytes,
            headers=headers,
            timeout=30.0,
        )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    return response


def test_signature_verification():
    """Test HMAC signature verification logic."""
    test_payload = b'{"test": "data"}'
    signature = generate_hmac_signature(test_payload, WEBHOOK_SECRET)

    print(f"Test payload: {test_payload.decode()}")
    print(f"Generated signature: {signature}")
    print(f"Signature length: {len(signature)}")


if __name__ == "__main__":
    import asyncio

    print("=== Testing HMAC Signature Generation ===")
    test_signature_verification()

    print("\n=== Testing Plaud Webhook ===")
    print("Note: Make sure the API is running on http://localhost:8000")
    print("Press Ctrl+C to skip the live test\n")

    try:
        asyncio.run(test_plaud_webhook())
    except KeyboardInterrupt:
        print("\nLive test skipped")
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure the API is running and the database is accessible")

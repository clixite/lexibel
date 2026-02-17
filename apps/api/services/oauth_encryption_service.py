"""OAuth token encryption service using Fernet symmetric encryption.

Tokens are encrypted before storage and decrypted when retrieved.
"""

import os
from cryptography.fernet import Fernet


class OAuthEncryptionService:
    """Encrypt and decrypt OAuth tokens using Fernet."""

    def __init__(self):
        """Initialize with encryption key from environment."""
        key = os.getenv("OAUTH_ENCRYPTION_KEY")

        if not key:
            raise ValueError(
                "OAUTH_ENCRYPTION_KEY not set. Generate with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

        try:
            self.fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise ValueError(f"Invalid OAUTH_ENCRYPTION_KEY: {e}")

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext token.

        Args:
            plaintext: The token to encrypt

        Returns:
            Base64-encoded encrypted token
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")

        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt encrypted token.

        Args:
            encrypted: The base64-encoded encrypted token

        Returns:
            Decrypted plaintext token
        """
        if not encrypted:
            raise ValueError("Cannot decrypt empty string")

        try:
            decrypted_bytes = self.fernet.decrypt(encrypted.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")


# Singleton instance
_oauth_encryption_service: OAuthEncryptionService | None = None


def get_oauth_encryption_service() -> OAuthEncryptionService:
    """Get singleton OAuth encryption service."""
    global _oauth_encryption_service
    if _oauth_encryption_service is None:
        _oauth_encryption_service = OAuthEncryptionService()
    return _oauth_encryption_service

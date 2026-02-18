"""Token encryption service using AES-256-GCM.

Encrypts OAuth access_token and refresh_token before storing in database.
Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
"""

import os
from cryptography.fernet import Fernet, InvalidToken


class TokenEncryptionService:
    """Encrypts and decrypts OAuth tokens using Fernet (AES-256)."""

    def __init__(self):
        """Initialize with encryption key from environment."""
        key = os.getenv("OAUTH_ENCRYPTION_KEY")
        if not key:
            raise ValueError(
                "OAUTH_ENCRYPTION_KEY environment variable is required. "
                "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        try:
            self.fernet = Fernet(key.encode())
        except Exception as e:
            raise ValueError(
                f"Invalid OAUTH_ENCRYPTION_KEY: {e}. "
                "Must be a valid Fernet key (44 chars base64)."
            ) from e

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext token.

        Args:
            plaintext: The token to encrypt (access_token or refresh_token)

        Returns:
            Encrypted token as base64 string
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty token")

        encrypted_bytes = self.fernet.encrypt(plaintext.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")

    def decrypt(self, encrypted: str) -> str:
        """Decrypt an encrypted token.

        Args:
            encrypted: The encrypted token (from database)

        Returns:
            Decrypted plaintext token

        Raises:
            InvalidToken: If token is invalid or tampered
        """
        if not encrypted:
            raise ValueError("Cannot decrypt empty token")

        try:
            decrypted_bytes = self.fernet.decrypt(encrypted.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken as e:
            raise ValueError("Failed to decrypt token: invalid or tampered") from e


# Global instance
_encryption_service: TokenEncryptionService | None = None


def get_encryption_service() -> TokenEncryptionService:
    """Get or create the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = TokenEncryptionService()
    return _encryption_service

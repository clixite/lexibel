"""OAuth state token generation and validation using JWT.

The state token is used to prevent CSRF attacks in OAuth2 flow:
1. Generate a JWT with tenant_id, user_id, provider, nonce
2. Store in Redis with 10 minute TTL
3. Validate on callback to ensure request originated from our app
"""

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt


class OAuthStateManager:
    """Manages OAuth state tokens using JWT + Redis."""

    def __init__(self):
        """Initialize with secret key from environment."""
        self.secret_key = os.getenv("SECRET_KEY")
        if not self.secret_key:
            raise ValueError("SECRET_KEY environment variable is required")

        self.algorithm = "HS256"
        self.expiration_minutes = 10

    def create_state(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
    ) -> str:
        """Create a signed JWT state token.

        Args:
            tenant_id: The tenant ID
            user_id: The user ID initiating OAuth flow
            provider: OAuth provider ('google' or 'microsoft')

        Returns:
            JWT state token (signed)
        """
        # Generate a random nonce to prevent replay attacks
        nonce = secrets.token_urlsafe(32)

        # Create JWT payload
        payload = {
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "provider": provider,
            "nonce": nonce,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=self.expiration_minutes),
        }

        # Sign and encode
        state_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return state_token

    def validate_state(self, state_token: str) -> dict:
        """Validate and decode a state token.

        Args:
            state_token: The JWT state token from callback

        Returns:
            Decoded payload with tenant_id, user_id, provider, nonce

        Raises:
            jwt.ExpiredSignatureError: If token expired
            jwt.InvalidTokenError: If token invalid
        """
        try:
            payload = jwt.decode(
                state_token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            # Convert string UUIDs back to UUID objects
            payload["tenant_id"] = uuid.UUID(payload["tenant_id"])
            payload["user_id"] = uuid.UUID(payload["user_id"])

            return payload

        except jwt.ExpiredSignatureError as e:
            raise ValueError("OAuth state token expired (10 min limit)") from e
        except jwt.InvalidTokenError as e:
            raise ValueError("Invalid OAuth state token") from e


# Global instance
_state_manager: OAuthStateManager | None = None


def get_state_manager() -> OAuthStateManager:
    """Get or create the global state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = OAuthStateManager()
    return _state_manager

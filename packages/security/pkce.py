"""PKCE (Proof Key for Code Exchange) implementation for OAuth2.

PKCE provides additional security for OAuth2 authorization code flow by:
1. Generating a random code_verifier
2. Creating a SHA-256 hash (code_challenge) of the verifier
3. Sending code_challenge with authorization request
4. Sending code_verifier with token exchange

This prevents authorization code interception attacks.
"""

import base64
import hashlib
import secrets


def generate_code_verifier() -> str:
    """Generate a cryptographically random code verifier.

    Per RFC 7636, code_verifier must be:
    - 43-128 characters long
    - Contains [A-Z], [a-z], [0-9], "-", ".", "_", "~"

    Returns:
        Base64url-encoded random string (64 bytes → 86 chars)
    """
    # Generate 64 random bytes
    random_bytes = secrets.token_bytes(64)

    # Base64url encode (removes padding)
    code_verifier = base64.urlsafe_b64encode(random_bytes).decode("utf-8").rstrip("=")

    return code_verifier


def generate_code_challenge(code_verifier: str) -> str:
    """Generate a code challenge from a code verifier.

    Uses SHA-256 hash + base64url encoding (code_challenge_method=S256).

    Args:
        code_verifier: The randomly generated code verifier

    Returns:
        Base64url-encoded SHA-256 hash of the verifier
    """
    # SHA-256 hash of code_verifier
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()

    # Base64url encode (removes padding)
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    return code_challenge


def create_pkce_pair() -> tuple[str, str]:
    """Generate both code_verifier and code_challenge.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    return code_verifier, code_challenge

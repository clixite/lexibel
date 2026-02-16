"""TOTP multi-factor authentication using pyotp.

Generates TOTP secrets, provisioning URIs for QR codes, and
verifies 6-digit codes. Issuer is always "LexiBel".
"""

import pyotp

ISSUER_NAME: str = "LexiBel"


def generate_secret() -> str:
    """Generate a random base32 TOTP secret."""
    return pyotp.random_base32()


def generate_provisioning_uri(email: str, secret: str) -> str:
    """Generate an otpauth:// URI for QR code scanning.

    Compatible with Google Authenticator, Authy, 1Password, etc.
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=ISSUER_NAME)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code against the secret.

    Allows a 1-step window (±30s) to account for clock drift.
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)

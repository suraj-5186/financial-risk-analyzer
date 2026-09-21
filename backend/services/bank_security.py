"""
Bank Sync Security & Token Encryption (Task 19)
Provides authenticated encryption at rest (AES-128-CBC + HMAC-SHA256 via Fernet)
for banking provider access and refresh tokens, as well as CSRF state token generation.
"""

import base64
import hashlib
import secrets
import time
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import settings

_FERNET_INSTANCE: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Initializes and returns a cached Fernet instance using configured or derived key."""
    global _FERNET_INSTANCE
    if _FERNET_INSTANCE is not None:
        return _FERNET_INSTANCE

    configured_key = settings.BANK_TOKEN_ENCRYPTION_KEY.strip()
    if configured_key:
        try:
            # Validate if it's already a valid 32-byte urlsafe base64 key
            _FERNET_INSTANCE = Fernet(configured_key.encode("utf-8"))
            return _FERNET_INSTANCE
        except Exception:
            pass

    # Deterministically derive 32-byte Fernet key from SECRET_KEY using PBKDF2HMAC
    salt = b"FinRisk_BankSync_Token_Salt_v1"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    derived_bytes = kdf.derive(settings.SECRET_KEY.encode("utf-8"))
    b64_key = base64.urlsafe_b64encode(derived_bytes)
    _FERNET_INSTANCE = Fernet(b64_key)
    return _FERNET_INSTANCE


def encrypt_token(raw_token: Optional[str]) -> str:
    """Encrypts a provider access token or refresh token for secure database storage."""
    if not raw_token:
        return ""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(raw_token.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_token(encrypted_token: Optional[str]) -> str:
    """Decrypts an encrypted provider token from storage. Never expose to frontend."""
    if not encrypted_token:
        return ""
    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(encrypted_token.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception:
        return ""


def generate_state_token(user_id: str) -> str:
    """
    Generates a secure, time-bound anti-CSRF state token for OAuth / consent initiation.
    Format: <user_id>:<timestamp>:<random_hex>:<hmac_signature>
    """
    timestamp = int(time.time())
    nonce = secrets.token_hex(8)
    payload = f"{user_id}:{timestamp}:{nonce}"
    sig = hashlib.sha256(f"{payload}:{settings.SECRET_KEY}".encode("utf-8")).hexdigest()[:16]
    state_str = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(state_str.encode("utf-8")).decode("utf-8")


def verify_state_token(state_token: str, expected_user_id: str, max_age_seconds: int = 600) -> bool:
    """
    Verifies state token integrity, expiration (10 min), and user identity to prevent CSRF.
    """
    try:
        decoded = base64.urlsafe_b64decode(state_token.encode("utf-8")).decode("utf-8")
        parts = decoded.split(":")
        if len(parts) != 4:
            return False
        user_id, ts_str, nonce, sig = parts
        if user_id != expected_user_id:
            return False

        ts = int(ts_str)
        if time.time() - ts > max_age_seconds:
            return False

        payload = f"{user_id}:{ts_str}:{nonce}"
        expected_sig = hashlib.sha256(f"{payload}:{settings.SECRET_KEY}".encode("utf-8")).hexdigest()[:16]
        return secrets.compare_digest(sig, expected_sig)
    except Exception:
        return False

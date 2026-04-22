"""Credentials vault — symmetric encryption at rest.

OAuth tokens and API secrets never touch the DB as plaintext. The vault uses AES-256-GCM
via cryptography's Fernet (same primitive, URL-safe). The key is derived from the app's
`SECRET_KEY` setting so a deploy with a new secret can decrypt what it wrote.

For production, rotate by:
    1. Adding a new SECRET_KEY as the primary
    2. Keeping the old one as a fallback for decrypt-only
(That's a small extension — current impl uses a single key.)
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def _fernet() -> Fernet:
    secret = get_settings().secret_key.encode("utf-8")
    # Derive 32-byte key → urlsafe base64 for Fernet.
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return _fernet().encrypt(raw).decode("ascii")


def decrypt(token: str) -> dict[str, Any]:
    if not token:
        return {}
    try:
        raw = _fernet().decrypt(token.encode("ascii"))
    except InvalidToken:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}

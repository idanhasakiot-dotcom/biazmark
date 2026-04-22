"""OAuth base class + registry.

Each platform subclass defines:
    - auth_url: where we redirect the user to authorise
    - token_url: where we exchange the code for a token
    - scopes: what permissions we request
    - parse_token(data): normalise the token response
    - fetch_account(token): pull account metadata (id, name, page list, etc.)

The standard flow (implemented by `start` / `finish`):
    1. Generate random state + PKCE code_verifier → persist in oauth_states table
    2. Redirect user to `auth_url` with client_id, redirect_uri, scope, state
    3. User approves, platform redirects back to /api/oauth/callback/{platform}?code=...&state=...
    4. Exchange code for access_token + refresh_token
    5. Fetch account metadata
    6. Persist encrypted credentials + public metadata in ConnectorAccount
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar
from urllib.parse import urlencode

import httpx


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str = ""
    expires_in: int = 0
    token_type: str = "Bearer"
    scope: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountInfo:
    account_id: str
    display_name: str
    meta: dict[str, Any] = field(default_factory=dict)


class BaseOAuth(ABC):
    platform: ClassVar[str] = ""
    auth_url: ClassVar[str] = ""
    token_url: ClassVar[str] = ""
    default_scopes: ClassVar[list[str]] = []
    use_pkce: ClassVar[bool] = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.platform and not cls.__name__.startswith("_"):
            oauth_registry.register(cls)

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    # ---- flow helpers ----

    @staticmethod
    def new_state() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def new_pkce() -> tuple[str, str]:
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return verifier, challenge

    def authorise_url(self, state: str, scopes: list[str] | None = None,
                      pkce_challenge: str | None = None) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or self.default_scopes),
            "state": state,
        }
        if self.use_pkce and pkce_challenge:
            params["code_challenge"] = pkce_challenge
            params["code_challenge_method"] = "S256"
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str = "") -> TokenSet:
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        if self.use_pkce and code_verifier:
            data["code_verifier"] = code_verifier
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(self.token_url, data=data,
                             headers={"Accept": "application/json"})
            r.raise_for_status()
            payload = r.json()
        return self.parse_token(payload)

    async def refresh(self, refresh_token: str) -> TokenSet:
        data = {
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(self.token_url, data=data,
                             headers={"Accept": "application/json"})
            r.raise_for_status()
        return self.parse_token(r.json())

    def parse_token(self, data: dict[str, Any]) -> TokenSet:
        return TokenSet(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            expires_in=int(data.get("expires_in") or 0),
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope", ""),
            raw=data,
        )

    @abstractmethod
    async def fetch_account(self, tokens: TokenSet) -> AccountInfo:
        ...


class _OAuthRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, type[BaseOAuth]] = {}

    def register(self, cls: type[BaseOAuth]) -> None:
        self._providers[cls.platform] = cls

    def get(self, platform: str) -> type[BaseOAuth] | None:
        return self._providers.get(platform)

    def platforms(self) -> list[str]:
        return list(self._providers.keys())


oauth_registry = _OAuthRegistry()

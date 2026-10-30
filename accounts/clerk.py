"""Clerk authentication: verify the session JWT a signed-in browser sends as a Bearer token.

Clerk owns sign-in (Google is a social connection in the Clerk dashboard) and sessions. The backend
only checks signature, issuer, expiry and the authorized party, then looks up the profile once.
"""

import os
from dataclasses import dataclass

import httpx
import jwt
from jwt import PyJWKClient

API_URL = "https://api.clerk.com/v1"
LEEWAY_SECONDS = 10


class AuthError(Exception):
    """The token is missing, malformed, expired or from the wrong place."""


@dataclass(frozen=True)
class Identity:
    clerk_user_id: str
    email: str
    display_name: str


@dataclass(frozen=True)
class ClerkSettings:
    jwks_url: str
    issuer: str
    secret_key: str
    allowed_origins: tuple[str, ...]
    dev_login: bool

    @staticmethod
    def from_env(chain_endpoint: str) -> "ClerkSettings":
        dev = os.environ.get("AUTH_DEV_LOGIN", "0") == "1"
        if dev and chain_endpoint in ("test", "finney", "main"):
            raise RuntimeError("AUTH_DEV_LOGIN must never be enabled against a public network")
        issuer = os.environ.get("CLERK_ISSUER", "").rstrip("/")
        return ClerkSettings(
            jwks_url=os.environ.get("CLERK_JWKS_URL", f"{issuer}/.well-known/jwks.json" if issuer else ""),
            issuer=issuer,
            secret_key=os.environ.get("CLERK_SECRET_KEY", ""),
            allowed_origins=tuple(o.strip() for o in os.environ.get("CLERK_ALLOWED_ORIGINS", "").split(",") if o.strip()),
            dev_login=dev,
        )


class ClerkAuth:
    def __init__(self, settings: ClerkSettings) -> None:
        self._settings = settings
        self._jwks = PyJWKClient(settings.jwks_url, cache_keys=True) if settings.jwks_url else None

    def verify(self, token: str) -> str:
        """Return the Clerk user id (`sub`) for a valid session token."""
        cfg = self._settings
        if cfg.dev_login and token.startswith("dev:"):
            return token
        if self._jwks is None:
            raise AuthError("server is not configured for Clerk")
        try:
            key = self._jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=["RS256"], issuer=cfg.issuer or None,
                                leeway=LEEWAY_SECONDS, options={"require": ["exp", "sub", "iss"]})
        except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
            raise AuthError(f"invalid session: {exc}") from exc
        origin = claims.get("azp")
        if cfg.allowed_origins and origin not in cfg.allowed_origins:
            raise AuthError("session was issued for another site")
        return str(claims["sub"])

    def identity(self, clerk_user_id: str) -> Identity:
        """Profile for a new account. Dev ids carry their own name; real ids ask the Clerk API."""
        if clerk_user_id.startswith("dev:"):
            name = clerk_user_id.removeprefix("dev:")[:32] or "dev"
            return Identity(clerk_user_id, f"{name}@dev.local", name)
        try:
            response = httpx.get(f"{API_URL}/users/{clerk_user_id}", timeout=10,
                                 headers={"Authorization": f"Bearer {self._settings.secret_key}"})
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthError(f"could not load the Clerk profile: {exc}") from exc
        emails = data.get("email_addresses") or []
        email = emails[0].get("email_address", "") if emails else ""
        name = " ".join(p for p in (data.get("first_name"), data.get("last_name")) if p) or email.split("@")[0] or "player"
        return Identity(clerk_user_id, email, name)

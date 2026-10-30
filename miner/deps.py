"""Shared state and request helpers for the hosted miner routes."""

import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy.exc import IntegrityError

from accounts.clerk import AuthError, ClerkAuth
from accounts.keys import KeyVault
from accounts.store import AccountStore, User
from common.chain import Chain, NeuronView
from miner.config import MinerConfig
from miner.db import MinerDb
from miner.ratelimit import RateLimiter

VALIDATOR_CACHE_SECONDS = 30
NEURON_CACHE_SECONDS = 10


@dataclass
class AppState:
    config: MinerConfig
    db: MinerDb
    chain: Chain
    accounts: AccountStore
    vault: KeyVault
    auth: ClerkAuth
    limits: dict[str, RateLimiter] = field(default_factory=lambda: {
        "ticket": RateLimiter(30, 60), "submit": RateLimiter(20, 60), "read": RateLimiter(240, 60),
        "user": RateLimiter(60, 60),
    })
    _validators: dict[str, Any] = field(default_factory=lambda: {"at": 0.0, "keys": frozenset()})
    _neurons: dict[str, Any] = field(default_factory=lambda: {"at": 0.0, "items": []})

    def neurons(self) -> list[NeuronView]:
        if time.monotonic() - self._neurons["at"] > NEURON_CACHE_SECONDS:
            self._neurons["items"] = self.chain.neurons()
            self._neurons["at"] = time.monotonic()
        return self._neurons["items"]

    def validator_keys(self) -> frozenset[str]:
        if time.monotonic() - self._validators["at"] > VALIDATOR_CACHE_SECONDS:
            permitted = {n.hotkey for n in self.chain.neurons() if n.validator_permit}
            self._validators["keys"] = frozenset(permitted | set(self.config.validator_allowlist))
            self._validators["at"] = time.monotonic()
        return self._validators["keys"]


def client_ip(request: Request, trust_proxy: bool) -> str:
    """Rate-limit key. Behind a proxy every request comes from it, so read its header."""
    if trust_proxy:
        forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def limit(state: AppState, kind: str, request: Request, user: User | None = None) -> None:
    if not state.limits[kind].allow(client_ip(request, state.config.trust_proxy)):
        raise HTTPException(429, "too many requests, slow down")
    if user is not None and not state.limits["user"].allow(str(user.id)):
        raise HTTPException(429, "too many requests, slow down")


def current_user(state: AppState, request: Request) -> User:
    """The signed-in player, created with a fresh custodial wallet on first sight."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(401, "sign in first")
    try:
        clerk_id = state.auth.verify(header[7:].strip())
        user = state.accounts.by_clerk_id(clerk_id)
        if user is not None:
            return user
        who = state.auth.identity(clerk_id)
        try:
            return state.accounts.create(who.clerk_user_id, who.email, who.display_name, state.vault.create())
        except IntegrityError:  # two first requests raced; the other one created the account
            existing = state.accounts.by_clerk_id(clerk_id)
            if existing is None:
                raise
            return existing
    except AuthError as exc:
        raise HTTPException(401, str(exc)) from exc

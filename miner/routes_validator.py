"""Routes validators call, one namespace per player hotkey: /m/{hotkey}/..."""

import json
from typing import Any

from bittensor import http_auth
from fastapi import APIRouter, HTTPException, Request

from miner.deps import AppState

PULL_LIMIT = 20
MAX_VERDICTS_PER_POST = 200


def build_router(state: AppState) -> APIRouter:
    router = APIRouter(prefix="/m/{hotkey}")
    nonces = http_auth.InMemoryNonceStore()

    def authenticate(request: Request, body: bytes, hotkey: str) -> str:
        if state.accounts.by_hotkey(hotkey) is None:
            raise HTTPException(404, "unknown miner")
        path = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        try:
            caller = http_auth.verify(
                dict(request.headers), body, method=request.method, path=path,
                self_hotkey_ss58=hotkey, nonce_store=nonces,
            )
        except http_auth.AuthError as exc:
            raise HTTPException(401, f"auth failed: {exc}") from exc
        if caller.hotkey_ss58 not in state.validator_keys():
            raise HTTPException(403, "not a validator on this subnet")
        return caller.hotkey_ss58

    @router.get("/trajectories")
    async def trajectories(hotkey: str, request: Request, since: int = 0) -> dict[str, Any]:
        authenticate(request, await request.body(), hotkey)
        return {"bundles": state.db.bundles_since(hotkey, since, PULL_LIMIT)}

    @router.post("/verdicts")
    async def verdicts(hotkey: str, request: Request) -> dict[str, Any]:
        body = await request.body()
        validator = authenticate(request, body, hotkey)
        try:
            items = json.loads(body).get("verdicts", [])[:MAX_VERDICTS_PER_POST]
            stored = sum(state.db.add_verdict(hotkey, item["bundle_id"], validator, item["verdict"])
                         for item in items)
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
            raise HTTPException(400, f"malformed verdicts: {exc}") from exc
        return {"stored": stored}

    return router

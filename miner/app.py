"""Open-pool miner HTTP app: issues tickets, receives recordings, serves them to validators."""

import json
import time
from typing import Any

from bittensor import http_auth
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from common.bundle import BundleError, parse_bundle
from common.chain import Chain
from common.mjcf import model_hash
from common.scene import pick_task
from common.ticket import TICKET_TTL_BLOCKS, build_ticket
from miner.config import MinerConfig
from miner.db import MinerDb
from miner.ratelimit import RateLimiter

MAX_BODY_BYTES = 4_000_000
PULL_LIMIT = 20
VALIDATOR_CACHE_SECONDS = 30
MAX_VERDICTS_PER_POST = 200


def _client(request: Request, trust_proxy: bool) -> str:
    """Rate-limit key. Behind a tunnel every request comes from the proxy, so read its header."""
    if trust_proxy:
        forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_app(config: MinerConfig, hotkey: str, chain: Chain) -> FastAPI:
    app = FastAPI(title="bittesnor open pool")
    app.add_middleware(
        CORSMiddleware, allow_origins=list(config.allowed_origins), allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    db = MinerDb(config.data_dir)
    nonces = http_auth.InMemoryNonceStore()
    limits = {"ticket": RateLimiter(30, 60), "submit": RateLimiter(20, 60), "read": RateLimiter(240, 60)}
    validators: dict[str, Any] = {"at": 0.0, "keys": set()}

    def limit(kind: str, request: Request) -> None:
        if not limits[kind].allow(_client(request, config.trust_proxy)):
            raise HTTPException(429, "too many requests, slow down")

    def validator_keys() -> set[str]:
        if time.monotonic() - validators["at"] > VALIDATOR_CACHE_SECONDS:
            permitted = {n.hotkey for n in chain.neurons() if n.validator_permit}
            validators["keys"] = permitted | set(config.validator_allowlist)
            validators["at"] = time.monotonic()
        return validators["keys"]

    def authenticate_validator(request: Request, body: bytes) -> str:
        path = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        try:
            caller = http_auth.verify(
                dict(request.headers), body, method=request.method, path=path,
                self_hotkey_ss58=hotkey, nonce_store=nonces,
            )
        except http_auth.AuthError as exc:
            raise HTTPException(401, f"auth failed: {exc}") from exc
        if caller.hotkey_ss58 not in validator_keys():
            raise HTTPException(403, "not a validator on this subnet")
        return caller.hotkey_ss58

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "hotkey": hotkey, "block": chain.current_block()}

    @app.get("/tasks")
    def tasks(request: Request) -> dict[str, Any]:
        limit("read", request)
        return {"tasks": list(config.task_ids)}

    @app.get("/ticket")
    def ticket(request: Request, task: str | None = None) -> dict[str, Any]:
        limit("ticket", request)
        try:
            task_id = pick_task(task, config.task_ids)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        block = chain.current_block()
        block_hash = chain.block_hash(block)
        if block_hash is None:
            raise HTTPException(503, "chain not ready")
        counter = db.issue_ticket_slot(block, block_hash)
        issued = build_ticket(block, block_hash, hotkey, task_id, counter)
        db.set_seed(counter, issued.seed)
        return {**issued.to_dict(), "model_hash": model_hash(issued.scene_xml)}

    @app.post("/submit")
    async def submit(request: Request) -> dict[str, Any]:
        limit("submit", request)
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
            raise HTTPException(413, "recording too large")
        body = await request.body()
        if len(body) > MAX_BODY_BYTES:
            raise HTTPException(413, "recording too large")
        try:
            bundle = parse_bundle(json.loads(body))
        except (json.JSONDecodeError, BundleError) as exc:
            raise HTTPException(400, f"malformed upload: {exc}") from exc
        ticket_in = bundle.ticket
        if ticket_in.hotkey != hotkey:
            raise HTTPException(400, "ticket was issued by another pool")
        issued = db.claim_submission(ticket_in.counter)
        if issued is None:
            raise HTTPException(409, "ticket unknown or already used")
        if (str(ticket_in.seed) != issued["seed"] or ticket_in.block_hash != issued["block_hash"]
                or ticket_in.block != issued["block"]):
            db.release_submission(ticket_in.counter)
            raise HTTPException(400, "ticket does not match what was issued")
        if chain.current_block() > ticket_in.block + TICKET_TTL_BLOCKS:
            raise HTTPException(410, "ticket expired")
        bundle_id = bundle.bundle_id()
        db.add_bundle(bundle_id, ticket_in.counter, bundle.contributor or "anonymous", body.decode())
        return {"bundle_id": bundle_id, "status": "pending"}

    @app.get("/status/{bundle_id}")
    def status(bundle_id: str, request: Request) -> dict[str, Any]:
        limit("read", request)
        result = db.status(bundle_id)
        if result is None:
            raise HTTPException(404, "unknown recording")
        return result

    @app.get("/leaderboard")
    def leaderboard(request: Request) -> dict[str, Any]:
        limit("read", request)
        return {"pool": hotkey, "contributors": db.leaderboard()}

    @app.get("/trajectories")
    async def trajectories(request: Request, since: int = 0) -> dict[str, Any]:
        authenticate_validator(request, await request.body())
        return {"bundles": db.bundles_since(since, PULL_LIMIT)}

    @app.post("/verdicts")
    async def verdicts(request: Request) -> dict[str, Any]:
        body = await request.body()
        validator = authenticate_validator(request, body)
        items = json.loads(body).get("verdicts", [])[:MAX_VERDICTS_PER_POST]
        stored = sum(db.add_verdict(item["bundle_id"], validator, item["verdict"]) for item in items)
        return {"stored": stored}

    return app

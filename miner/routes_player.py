"""Routes a signed-in player uses: profile, ticket, submit, run status."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from common.bundle import BundleError, parse_bundle
from common.mjcf import model_hash
from common.scene import pick_task
from common.ticket import TICKET_TTL_BLOCKS, build_ticket
from miner.deps import AppState, current_user, limit

MAX_BODY_BYTES = 4_000_000


def build_router(state: AppState) -> APIRouter:
    router = APIRouter()
    cfg, db, chain = state.config, state.db, state.chain

    @router.get("/me")
    def me(request: Request) -> dict[str, Any]:
        user = current_user(state, request)
        limit(state, "read", request, user)
        hotkey = user.wallet.hotkey_ss58
        neuron = next((n for n in state.neurons() if n.hotkey == hotkey), None)
        totals = db.player_totals().get(hotkey, {"submitted": 0, "accepted": 0, "value": 0.0})
        return {
            "name": user.display_name, "coldkey": user.wallet.coldkey_ss58, "hotkey": hotkey,
            "uid": user.uid, "registration": user.reg_status, "registration_note": user.reg_error,
            "submitted": totals["submitted"], "accepted": totals["accepted"], "score": totals["value"],
            "incentive": neuron.incentive if neuron else 0.0, "emission": neuron.emission if neuron else 0,
            "netuid": cfg.netuid,
        }

    @router.get("/ticket")
    def ticket(request: Request, task: str | None = None) -> dict[str, Any]:
        user = current_user(state, request)
        limit(state, "ticket", request, user)
        try:
            task_id = pick_task(task, cfg.task_ids)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        block = chain.current_block()
        block_hash = chain.block_hash(block)
        if block_hash is None:
            raise HTTPException(503, "chain not ready")
        hotkey = user.wallet.hotkey_ss58
        counter = db.issue_ticket_slot(hotkey, block, block_hash)
        issued = build_ticket(block, block_hash, hotkey, task_id, counter)
        db.set_seed(counter, issued.seed)
        return {**issued.to_dict(), "model_hash": model_hash(issued.scene_xml)}

    @router.post("/submit")
    async def submit(request: Request) -> dict[str, Any]:
        user = current_user(state, request)
        limit(state, "submit", request, user)
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
            raise HTTPException(413, "recording too large")
        body = await request.body()
        if len(body) > MAX_BODY_BYTES:
            raise HTTPException(413, "recording too large")
        try:
            raw = json.loads(body)
            raw["contributor"] = user.display_name  # the account name, never what the browser claims
            bundle = parse_bundle(raw)
        except (json.JSONDecodeError, TypeError, BundleError) as exc:
            raise HTTPException(400, f"malformed upload: {exc}") from exc
        hotkey, ticket_in = user.wallet.hotkey_ss58, bundle.ticket
        if ticket_in.hotkey != hotkey:
            raise HTTPException(400, "ticket was issued to another player")
        issued = db.claim_submission(hotkey, ticket_in.counter)
        if issued is None:
            raise HTTPException(409, "ticket unknown or already used")
        if (str(ticket_in.seed) != issued["seed"] or ticket_in.block_hash != issued["block_hash"]
                or ticket_in.block != issued["block"]):
            db.release_submission(ticket_in.counter)
            raise HTTPException(400, "ticket does not match what was issued")
        if chain.current_block() > ticket_in.block + TICKET_TTL_BLOCKS:
            raise HTTPException(410, "ticket expired")
        bundle_id = bundle.bundle_id()
        signature = state.vault.open(user.wallet).hotkey.sign(bundle_id.encode()).hex()
        db.add_bundle(bundle_id, ticket_in.counter, hotkey, user.display_name, signature, json.dumps(raw))
        return {"bundle_id": bundle_id, "status": "pending", "registration": user.reg_status}

    @router.get("/status/{bundle_id}")
    def status(bundle_id: str, request: Request) -> dict[str, Any]:
        limit(state, "read", request)
        result = db.status(bundle_id)
        if result is None:
            raise HTTPException(404, "unknown recording")
        return result

    return router

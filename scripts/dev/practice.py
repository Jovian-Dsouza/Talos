"""Practice server: play the teleop demo on one machine with no chain, miner or validator.

It serves the same HTTP API as the miner (ticket, submit, status, leaderboard) and judges each run
with the real validator pipeline (native MuJoCo replay, success check, quality, novelty). Block
numbers and hashes are fixed stand-ins, so nothing here touches Bittensor and nothing is scored
for real.

Usage: python scripts/dev/practice.py [PORT]
"""

import sys
import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from common.mjcf import model_hash
from common.scene import DEFAULT_TASKS, pick_task
from common.ticket import build_ticket
from validator.pipeline import Context, PipelineConfig, process
from validator.store import Store

HOTKEY = "practice"
FAKE_BLOCK = 1000
FAKE_HASH = "ab" * 32
MAX_BODY_BYTES = 4_000_000


class PracticeChain:
    def current_block(self) -> int:
        return FAKE_BLOCK

    def block_hash(self, block: int) -> str | None:
        return FAKE_HASH


def create_app() -> FastAPI:
    app = FastAPI(title="bittesnor practice server")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
    ctx = Context(PipelineConfig(), Store(":memory:"), PracticeChain(), {})
    state: dict[str, Any] = {"counter": 0, "verdicts": {}, "runs": []}

    @app.get("/tasks")
    def tasks() -> dict[str, Any]:
        return {"tasks": list(DEFAULT_TASKS)}

    @app.get("/ticket")
    def ticket(task: str | None = None) -> dict[str, Any]:
        try:
            task_id = pick_task(task, DEFAULT_TASKS)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        state["counter"] += 1
        issued = build_ticket(FAKE_BLOCK, FAKE_HASH, HOTKEY, task_id, state["counter"])
        return {**issued.to_dict(), "model_hash": model_hash(issued.scene_xml)}

    @app.post("/submit")
    async def submit(request: Request) -> dict[str, Any]:
        body = await request.body()
        if len(body) > MAX_BODY_BYTES:
            raise HTTPException(413, "recording too large")
        try:
            import json

            raw = json.loads(body)
        except ValueError as exc:
            raise HTTPException(400, f"malformed upload: {exc}") from exc
        _, verdict = process(raw, HOTKEY, ctx)
        bundle_id = uuid.uuid4().hex[:16]
        state["verdicts"][bundle_id] = verdict.to_dict()
        state["runs"].append({"contributor": str(raw.get("contributor", "anonymous"))[:64], "verdict": verdict})
        return {"bundle_id": bundle_id, "status": "judged"}

    @app.get("/status/{bundle_id}")
    def status(bundle_id: str) -> dict[str, Any]:
        verdict = state["verdicts"].get(bundle_id)
        if verdict is None:
            raise HTTPException(404, "unknown recording")
        return {"bundle_id": bundle_id, "contributor": "", "verdicts": {HOTKEY: verdict}}

    @app.get("/leaderboard")
    def leaderboard() -> dict[str, Any]:
        totals: dict[str, dict[str, Any]] = {}
        for run in state["runs"]:
            entry = totals.setdefault(run["contributor"], {"contributor": run["contributor"],
                                                           "submitted": 0, "accepted": 0, "value": 0.0})
            entry["submitted"] += 1
            if run["verdict"].accepted:
                entry["accepted"] += 1
                entry["value"] += run["verdict"].score
        ranked = sorted(totals.values(), key=lambda e: e["value"], reverse=True)[:20]
        return {"pool": HOTKEY, "contributors": ranked}

    return app


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8091
    uvicorn.run(create_app(), host="127.0.0.1", port=port)

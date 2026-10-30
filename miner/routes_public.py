"""Read-only routes for the landing page, leaderboard, live network view, datasets and episodes."""

import time
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query, Request

from miner import activity as views
from miner.deps import AppState, limit

FEED_LIMIT = 25
LEADERBOARD_LIMIT = 20
EPISODE_PAGE = 25
CACHE_SECONDS = 2.0  # many dashboards poll every few seconds; compute each view once per window


def build_router(state: AppState) -> APIRouter:
    router = APIRouter()
    cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def cached(key: str, build: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        hit = cache.get(key)
        if hit is not None and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]
        value = build()
        cache[key] = (time.monotonic(), value)
        return value

    @router.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "block": state.chain.current_block(), "netuid": state.config.netuid}

    @router.get("/tasks")
    def tasks(request: Request) -> dict[str, Any]:
        limit(state, "read", request)
        return {"tasks": list(state.config.task_ids)}

    def _miners() -> list[dict[str, Any]]:
        names = state.accounts.display_names()
        totals = state.db.player_totals()
        rows = []
        for n in state.neurons():
            if n.hotkey not in names:
                continue
            played = totals.get(n.hotkey, {})
            rows.append({
                "uid": n.uid, "hotkey": n.hotkey, "contributor": names[n.hotkey],
                "submitted": played.get("submitted", 0), "accepted": played.get("accepted", 0),
                "value": played.get("value", 0.0), "incentive": n.incentive, "emission": n.emission,
            })
        return sorted(rows, key=lambda r: r["value"], reverse=True)

    def _validators() -> list[Any]:
        # A local chain gives every neuron a permit, so a validator is one that has set weights
        # or one this service is configured to trust (it may not have had miners to weigh yet).
        trusted = set(state.config.validator_allowlist)
        return [n for n in state.neurons() if n.validator_permit and (n.sets_weights or n.hotkey in trusted)]

    @router.get("/leaderboard")
    def leaderboard(request: Request) -> dict[str, Any]:
        limit(state, "read", request)
        return {"contributors": _miners()[:LEADERBOARD_LIMIT]}

    @router.get("/network")
    def network(request: Request) -> dict[str, Any]:
        limit(state, "read", request)
        names = state.accounts.display_names()
        validators = [
            {"uid": n.uid, "hotkey": n.hotkey, "stake": n.stake, "root": state.chain.latest_commitment(n.hotkey)}
            for n in _validators()
        ]
        feed = [{**item, "contributor": names.get(item["hotkey"], item["contributor"])}
                for item in state.db.recent_verdicts(FEED_LIMIT)]
        return {
            "netuid": state.config.netuid, "subnet_name": state.subnet_name(), "chain": state.config.chain_endpoint,
            "block": state.chain.current_block(), "miners": _miners(), "validators": validators, "feed": feed,
        }

    def _activity(window: str) -> dict[str, Any]:
        names = state.accounts.display_names()
        now = time.time()
        return {
            **views.activity(
                state.db.jobs(), names,
                miners_registered=sum(1 for n in state.neurons() if n.hotkey in names),
                validators_on_chain=len(_validators()),
                playing_now=state.db.playing_since(now - views.PLAYING_SECONDS),
                validating_now=state.db.validators_since(now - views.VALIDATING_SECONDS),
                window=window, now=now,
            ),
            "netuid": state.config.netuid, "subnet_name": state.subnet_name(), "block": state.chain.current_block(),
        }

    @router.get("/activity")
    def live_activity(request: Request, window: str = "1h") -> dict[str, Any]:
        limit(state, "read", request)
        if window not in views.WINDOWS:
            raise HTTPException(400, f"window must be one of {', '.join(views.WINDOWS)}")
        return cached(f"activity:{window}", lambda: _activity(window))

    @router.get("/datasets")
    def datasets(request: Request) -> dict[str, Any]:
        limit(state, "read", request)
        return cached("datasets", lambda: views.datasets(
            state.db.jobs(), state.config.task_ids, state.config.dataset_links))

    @router.get("/episodes")
    def episodes(request: Request, task: str | None = None, before: int | None = Query(None, ge=1),
                 count: int = Query(EPISODE_PAGE, ge=1, le=100)) -> dict[str, Any]:
        limit(state, "read", request)
        if task is not None and task not in state.config.task_ids:
            raise HTTPException(400, "unknown task")
        names = state.accounts.display_names()
        rows = state.db.jobs(task_id=task, before_seq=before, limit=count + 1)
        page = [views.job_view(job, names) for job in rows[:count]]
        return {"episodes": page, "next": page[-1]["id"] if len(rows) > count else None}

    return router

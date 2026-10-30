"""Read-only routes for the landing page, leaderboard and live network view."""

from typing import Any

from fastapi import APIRouter, Request

from miner.deps import AppState, limit

FEED_LIMIT = 25
LEADERBOARD_LIMIT = 20


def build_router(state: AppState) -> APIRouter:
    router = APIRouter()

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

    @router.get("/leaderboard")
    def leaderboard(request: Request) -> dict[str, Any]:
        limit(state, "read", request)
        return {"contributors": _miners()[:LEADERBOARD_LIMIT]}

    @router.get("/network")
    def network(request: Request) -> dict[str, Any]:
        limit(state, "read", request)
        names = state.accounts.display_names()
        permitted = [n for n in state.neurons() if n.validator_permit]
        top_stake = max((n.stake for n in permitted), default=0.0)
        # A local chain gives every neuron a permit, so keep only those with a meaningful stake.
        validators = [
            {"uid": n.uid, "hotkey": n.hotkey, "stake": n.stake, "root": state.chain.latest_commitment(n.hotkey)}
            for n in sorted(permitted, key=lambda n: n.stake, reverse=True) if n.stake >= 0.1 * top_stake
        ]
        feed = [{**item, "contributor": names.get(item["hotkey"], item["contributor"])}
                for item in state.db.recent_verdicts(FEED_LIMIT)]
        return {
            "netuid": state.config.netuid, "block": state.chain.current_block(),
            "miners": _miners(), "validators": validators, "feed": feed,
        }

    return router

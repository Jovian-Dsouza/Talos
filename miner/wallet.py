"""The signed-in player's wallet view: addresses, free TAO and what their miner has earned.

A miner's emissions accrue as alpha staked on its own hotkey, owned by the player's coldkey, so the
earned amount is that stake, valued in TAO at the subnet's spot alpha price. The daily rate is
measured from the stake samples the miner service records, not estimated from block times.
"""

from typing import Any

RAO_PER_UNIT = 1e9
DAY = 86400
RATE_WINDOW_SECONDS = 6 * 3600  # measure the earning rate over recent samples only


def _daily_rate(history: list[dict[str, Any]]) -> float | None:
    if not history:
        return None
    latest = history[-1]
    recent = [s for s in history if s["at"] >= latest["at"] - RATE_WINDOW_SECONDS]
    first = recent[0]
    span = latest["at"] - first["at"]
    if span <= 0:
        return None
    return max(0.0, latest["alpha"] - first["alpha"]) / span * DAY


def wallet_view(*, coldkey: str, hotkey: str, uid: int | None, registration: str, netuid: int,
                subnet_name: str | None, free_rao: int, staked_alpha: float, alpha_price: float,
                emission_rao: int, history: list[dict[str, Any]]) -> dict[str, Any]:
    per_day = _daily_rate(history)
    return {
        "coldkey": coldkey, "hotkey": hotkey, "uid": uid, "registration": registration,
        "netuid": netuid, "subnet_name": subnet_name,
        "free_tao": free_rao / RAO_PER_UNIT,
        "staked_alpha": staked_alpha,
        "alpha_price": alpha_price,
        "earned_tao": staked_alpha * alpha_price,
        "emission_alpha_per_tempo": emission_rao / RAO_PER_UNIT,
        "alpha_per_day": per_day,
        "tao_per_day": None if per_day is None else per_day * alpha_price,
        "history": [{**sample, "tao": sample["alpha"] * alpha_price} for sample in history],
    }

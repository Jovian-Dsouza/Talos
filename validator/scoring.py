"""Value of an accepted episode and pool scores across epochs.

V(t) = Demand(task) * Quality^alpha * (1 + beta * Novelty), reduced for each extra accepted episode
a pool already landed on the same task this epoch. Pool score is an EMA of per-epoch value sums.
"""

import json
from pathlib import Path
from typing import Mapping

ALPHA = 1.5
BETA = 0.5
DIMINISH_AFTER = 20  # accepted episodes per pool, task and epoch before value halves
EMA_KEEP = 0.7
MAX_DEMAND = 5.0


def load_demand(path: str | Path | None) -> dict[str, float]:
    if path is None or not Path(path).exists():
        return {}
    raw = json.loads(Path(path).read_text())
    return {task: min(max(float(value), 1.0), MAX_DEMAND) for task, value in raw.items()}


def episode_value(
    demand: Mapping[str, float], task_id: str, quality: float, novelty: float, prior_count: int
) -> float:
    base = demand.get(task_id, 1.0) * quality**ALPHA * (1.0 + BETA * novelty)
    return base / (1.0 + prior_count / DIMINISH_AFTER)


def pool_scores(epoch_values: Mapping[int, Mapping[str, float]]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for epoch in sorted(epoch_values):
        values = epoch_values[epoch]
        hotkeys = set(scores) | set(values)
        scores = {
            hotkey: EMA_KEEP * scores.get(hotkey, 0.0) + (1.0 - EMA_KEEP) * values.get(hotkey, 0.0)
            for hotkey in hotkeys
        }
    return scores


def normalize(scores: Mapping[str, float]) -> dict[str, float]:
    total = sum(scores.values())
    if total <= 0:
        return {}
    return {hotkey: value / total for hotkey, value in scores.items()}

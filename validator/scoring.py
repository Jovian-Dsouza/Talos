"""Value of an accepted episode and miner scores across epochs.

score = 0.5 * time_score + 0.5 * smooth_score
  time_score   = min(1, ref_seconds / duration_s)   faster than the task reference scores 1
  smooth_score = exp(-jerk_rms / JERK_SCALE)         jerk of the end effector, lower is smoother

Only accepted episodes (ticket, replay match, task success, not a duplicate) earn a score. A miner's
score is an EMA of its per-epoch score sums.
"""

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from common.schema import CONTROL_DT

TIME_WEIGHT = 0.5
SMOOTH_WEIGHT = 0.5
JERK_SCALE = 150.0  # m/s^3 RMS at which smoothness falls to 1/e
EMA_KEEP = 0.7


@dataclass(frozen=True)
class EpisodeScore:
    time_score: float
    smooth_score: float
    duration_s: float
    score: float


def smooth_score(ee_path: np.ndarray) -> float:
    if len(ee_path) < 5:
        return 0.0
    jerk = np.diff(ee_path, n=3, axis=0) / CONTROL_DT**3
    rms = float(np.sqrt((jerk**2).sum(axis=1).mean()))
    return float(np.exp(-rms / JERK_SCALE))


def time_score(duration_s: float, ref_seconds: float) -> float:
    return float(min(1.0, ref_seconds / max(duration_s, 1e-6)))


def score_episode(ee_path: np.ndarray, steps: int, ref_seconds: float) -> EpisodeScore:
    duration = steps * CONTROL_DT
    time_part, smooth_part = time_score(duration, ref_seconds), smooth_score(ee_path)
    return EpisodeScore(
        time_part, smooth_part, duration, TIME_WEIGHT * time_part + SMOOTH_WEIGHT * smooth_part
    )


def miner_scores(epoch_values: Mapping[int, Mapping[str, float]]) -> dict[str, float]:
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

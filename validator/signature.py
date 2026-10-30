"""Path signatures for duplicate detection.

Absolute end-effector paths differ between seeds, so each path is expressed in a frame built from
the scene: origin at the picked object, first axis toward the place point, lengths divided by the
pick to place distance. Two recordings of the same motion then give nearly equal vectors.
"""

from typing import Any, Mapping

import numpy as np

POINTS = 32
MIN_SCALE = 0.05
DUPLICATE_DISTANCE = 0.05


def path_signature(ee_path: np.ndarray, spec: Mapping[str, Any]) -> np.ndarray:
    objects = {o["id"]: o for o in spec["objects"]}
    pick, place = objects[spec["pick"]], spec["place"]
    cube = np.array([pick["x"], pick["y"], 0.0])
    offset = np.array([place["x"] - pick["x"], place["y"] - pick["y"]])
    scale = max(float(np.linalg.norm(offset)), MIN_SCALE)
    u = offset / scale if scale > MIN_SCALE else np.array([1.0, 0.0])
    v = np.array([-u[1], u[0]])
    rel = ee_path - cube
    local = np.stack([rel[:, :2] @ u, rel[:, :2] @ v, rel[:, 2]], axis=1) / scale
    source = np.linspace(0.0, 1.0, len(local))
    target = np.linspace(0.0, 1.0, POINTS)
    resampled = np.stack([np.interp(target, source, local[:, k]) for k in range(3)], axis=1)
    return resampled.reshape(-1)


def distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def nearest_distance(signature: np.ndarray, others: list[np.ndarray]) -> float | None:
    if not others:
        return None
    return min(distance(signature, other) for other in others)

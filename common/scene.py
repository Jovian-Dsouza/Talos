"""Seeded scene generation for the put_cube_in_bowl task.

make_scene(seed) is the only place a scene is randomized. The miner calls it to build a ticket
and every validator calls it again to confirm the ticket, so the output must depend on the seed
alone. Python's random.Random (Mersenne Twister) is stable across versions, and every number is
rounded so JSON round trips compare equal.
"""

import json
import math
import random
from functools import lru_cache
from importlib import resources
from typing import Any

TASK_ID = "put_cube_in_bowl"

PALETTE: dict[str, tuple[float, float, float]] = {
    "red": (0.85, 0.12, 0.12),
    "green": (0.15, 0.65, 0.2),
    "blue": (0.12, 0.25, 0.85),
    "yellow": (0.95, 0.8, 0.1),
    "orange": (0.95, 0.5, 0.1),
    "purple": (0.5, 0.2, 0.7),
}

RADIUS_RANGE = (0.16, 0.26)
ANGLE_RANGE = (-0.8, 0.8)
MIN_SEPARATION = 0.085
RELAXED_SEPARATION = 0.07
MAX_PLACEMENT_TRIES = 2000


@lru_cache(maxsize=None)
def task_config(task_id: str) -> dict[str, Any]:
    text = resources.files("common.tasks").joinpath(f"{task_id}.json").read_text()
    return json.loads(text)


def _place(rng: random.Random, count: int) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    separation = MIN_SEPARATION
    tries = 0
    while len(points) < count:
        tries += 1
        if tries > MAX_PLACEMENT_TRIES:
            separation = RELAXED_SEPARATION
        radius = rng.uniform(*RADIUS_RANGE)
        angle = rng.uniform(*ANGLE_RANGE)
        x, y = radius * math.cos(angle), radius * math.sin(angle)
        if all(math.hypot(x - px, y - py) >= separation for px, py in points):
            points.append((x, y))
    return points


def make_scene(seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    colors = rng.sample(sorted(PALETTE), 4)
    spots = _place(rng, 4)
    roles = (
        ("cube_target", "cube", colors[0]),
        ("bowl_target", "bowl", colors[1]),
        ("cube_distractor", "cube", colors[2]),
        ("bowl_distractor", "bowl", colors[3]),
    )
    objects = [
        {
            "id": object_id,
            "kind": kind,
            "color": color,
            "x": round(x, 4),
            "y": round(y, 4),
            "yaw": round(rng.uniform(-math.pi, math.pi), 4),
        }
        for (object_id, kind, color), (x, y) in zip(roles, spots)
    ]
    template = task_config(TASK_ID)["instruction_template"]
    return {
        "task_id": TASK_ID,
        "instruction": template.format(cube_color=colors[0], bowl_color=colors[1]),
        "objects": objects,
    }

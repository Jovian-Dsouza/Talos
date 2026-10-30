"""Seeded scene generation for the put_cube_in_bowl task.

make_scene(task_id, seed) is the only place a scene is randomized. The miner calls it to build a ticket
and every validator calls it again to confirm the ticket, so the output must depend on the seed
alone. Python's random.Random (Mersenne Twister) is stable across versions, and every number is
rounded so JSON round trips compare equal.
"""

import json
import math
import random
from functools import lru_cache
from importlib import resources
from typing import Any, Callable, Sequence

TASK_ID = "put_cube_in_bowl"

PALETTE: dict[str, tuple[float, float, float]] = {
    "red": (0.85, 0.12, 0.12),
    "green": (0.15, 0.65, 0.2),
    "blue": (0.12, 0.25, 0.85),
    "teal": (0.1, 0.6, 0.62),
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


def _cube_scene(rng: random.Random) -> dict[str, Any]:
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
    bowl = objects[1]
    return {
        "task_id": TASK_ID,
        "instruction": template.format(cube_color=colors[0], bowl_color=colors[1]),
        "pick": "cube_target",
        "place": {"x": bowl["x"], "y": bowl["y"], "z": 0.05},
        "objects": objects,
    }


VIAL_TASK_ID = "rack_vial"
VIAL_COLORS = ("red", "green", "blue", "orange", "purple", "teal")
RACK_ROWS = "AB"
RACK_COLS = 4
RACK_PITCH = 0.042  # metres between slot centres
RACK_RADIUS_RANGE = (0.20, 0.235)
RACK_ANGLE_RANGE = (-0.35, 0.35)
VIAL_RADIUS_RANGE = (0.17, 0.24)
VIAL_ANGLE_RANGE = (-0.9, 0.9)
RACK_CLEARANCE = 0.115  # keep loose vials away from the rack footprint
VIAL_SEPARATION = 0.06


def slot_ids() -> list[str]:
    return [f"{row}{col + 1}" for row in RACK_ROWS for col in range(RACK_COLS)]


def slot_offset(slot: str) -> tuple[float, float]:
    """Slot centre in the rack frame: columns run along x, rows along y, centred on the rack."""
    col = int(slot[1:]) - 1
    row = RACK_ROWS.index(slot[0])
    return (
        (col - (RACK_COLS - 1) / 2) * RACK_PITCH,
        (row - (len(RACK_ROWS) - 1) / 2) * RACK_PITCH,
    )


def slot_world(rack: dict[str, Any], slot: str) -> tuple[float, float]:
    ox, oy = slot_offset(slot)
    c, s = math.cos(rack["yaw"]), math.sin(rack["yaw"])
    return rack["x"] + c * ox - s * oy, rack["y"] + s * ox + c * oy


def _vial_scene(rng: random.Random) -> dict[str, Any]:
    angle = rng.uniform(*RACK_ANGLE_RANGE)
    radius = rng.uniform(*RACK_RADIUS_RANGE)
    rack = {
        "id": "rack",
        "kind": "rack",
        "color": "gray",
        "x": round(radius * math.cos(angle), 4),
        "y": round(radius * math.sin(angle), 4),
        # Long side tangent to the arm's reach so every slot is reachable from above.
        "yaw": round(angle + math.pi / 2 + rng.uniform(-0.1, 0.1), 4),
    }
    colors = rng.sample(VIAL_COLORS, 3)
    spots: list[tuple[float, float]] = []
    tries = 0
    while len(spots) < 3:
        tries += 1
        r = rng.uniform(*VIAL_RADIUS_RANGE)
        a = rng.uniform(*VIAL_ANGLE_RANGE)
        x, y = r * math.cos(a), r * math.sin(a)
        if math.hypot(x - rack["x"], y - rack["y"]) < RACK_CLEARANCE + (0 if tries < 2000 else -0.02):
            continue
        if all(math.hypot(x - px, y - py) >= VIAL_SEPARATION for px, py in spots):
            spots.append((x, y))
    slots = slot_ids()
    target_slot = rng.choice(slots)
    filled = rng.sample([s for s in slots if s != target_slot], rng.randint(1, 2))
    vials = [
        {"id": vial_id, "kind": "vial", "color": color, "x": round(x, 4), "y": round(y, 4),
         "yaw": round(rng.uniform(-math.pi, math.pi), 4)}
        for vial_id, color, (x, y) in zip(("vial_target", "vial_a", "vial_b"), colors, spots)
    ]
    # Pre-filled slots hold seated vials, so the player threads around real obstacles.
    seated = []
    for index, slot in enumerate(filled):
        x, y = slot_world(rack, slot)
        seated.append({"id": f"vial_seated_{index}", "kind": "vial", "color": rng.choice(VIAL_COLORS),
                       "x": round(x, 4), "y": round(y, 4), "yaw": 0.0, "seated": True})
    tx, ty = slot_world(rack, target_slot)
    template = task_config(VIAL_TASK_ID)["instruction_template"]
    return {
        "task_id": VIAL_TASK_ID,
        "instruction": template.format(cap_color=colors[0], slot=target_slot),
        "pick": "vial_target",
        "place": {"x": round(tx, 4), "y": round(ty, 4), "z": 0.06},
        "target_slot": target_slot,
        "objects": [rack, *vials, *seated],
    }


SCENE_BUILDERS: dict[str, Callable[[random.Random], dict[str, Any]]] = {
    TASK_ID: _cube_scene,
    VIAL_TASK_ID: _vial_scene,
}


DEFAULT_TASKS = (VIAL_TASK_ID, TASK_ID)  # the headline task is the default and listed first


def pick_task(requested: str | None, allowed: Sequence[str]) -> str:
    """Task for a new ticket: the first allowed one, or the requested one when it is allowed."""
    if requested is None:
        return allowed[0]
    if requested not in allowed:
        raise ValueError(f"unknown task: {requested}")
    return requested


def make_scene(task_id: str, seed: int) -> dict[str, Any]:
    return SCENE_BUILDERS[task_id](random.Random(seed))

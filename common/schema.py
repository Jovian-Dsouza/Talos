"""Wire and storage contracts shared by miner, validator and export.

All types are frozen: build a new object to change a field.
"""

from dataclasses import dataclass
from typing import Any, Mapping

JOINT_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)

PHYSICS_DT = 0.002
CONTROL_DT = 0.020
SUBSTEPS = round(CONTROL_DT / PHYSICS_DT)
CHECKPOINT_EVERY = 25


@dataclass(frozen=True)
class Ticket:
    block: int
    block_hash: str
    hotkey: str
    task_id: str
    counter: int
    seed: int
    scene_spec: Mapping[str, Any]
    instruction: str
    expires_block: int


@dataclass(frozen=True)
class BundleHeader:
    ticket: Ticket
    mujoco_version: str
    model_hash: str
    control_dt: float
    contributor: str
    reported_success: bool


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    reason: str
    replay_drift: float
    success: bool
    quality: float
    novelty: float
    score: float

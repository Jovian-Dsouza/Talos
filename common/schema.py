"""Wire and storage contracts shared by miner, validator and export.

All types are frozen: build a new object to change a field.
"""

from dataclasses import asdict, dataclass
from typing import Any, Mapping

JOINT_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)
NUM_JOINTS = len(JOINT_NAMES)

# Arm pose at the start of every episode (radians). Browser and validator both start here.
HOME_POSE = (0.0, -1.2, 1.2, 0.8, 0.0, 0.5)

PHYSICS_DT = 0.002
CONTROL_DT = 0.020
SUBSTEPS = round(CONTROL_DT / PHYSICS_DT)
CHECKPOINT_EVERY = 25
MIN_STEPS = 10


@dataclass(frozen=True)
class Ticket:
    block: int
    block_hash: str
    hotkey: str
    task_id: str
    counter: int
    seed: int
    scene_spec: Mapping[str, Any]
    scene_xml: str
    instruction: str
    expires_block: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(raw: Mapping[str, Any]) -> "Ticket":
        return Ticket(
            block=int(raw["block"]),
            block_hash=str(raw["block_hash"]),
            hotkey=str(raw["hotkey"]),
            task_id=str(raw["task_id"]),
            counter=int(raw["counter"]),
            seed=int(raw["seed"]),
            scene_spec=dict(raw["scene_spec"]),
            scene_xml=str(raw["scene_xml"]),
            instruction=str(raw["instruction"]),
            expires_block=int(raw["expires_block"]),
        )


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    reason: str
    replay_drift: float
    success: bool
    quality: float
    novelty: float
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def rejected(reason: str, drift: float = 0.0, success: bool = False) -> Verdict:
    return Verdict(False, reason, drift, success, 0.0, 0.0, 0.0)

"""Convert between simulator joint radians and real SO-101 LeRobot units.

LeRobot's SO-101 in degrees mode reports five joints in degrees and the gripper in 0..100. The
simulator zero pose does not equal the real arm's calibrated zero, so each joint has a sign and an
offset that must be measured once on the physical arm (see docs/real-arm.md). Defaults are the
identity until that calibration exists.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from common.schema import GRIPPER_CLOSED, GRIPPER_OPEN, JOINT_NAMES, NUM_JOINTS

DEFAULT_PATH = Path(__file__).with_name("mapping.json")


@dataclass(frozen=True)
class JointMap:
    sign: float = 1.0
    offset_deg: float = 0.0


@dataclass(frozen=True)
class Mapping:
    joints: tuple[JointMap, ...]

    @staticmethod
    def identity() -> "Mapping":
        return Mapping(tuple(JointMap() for _ in range(NUM_JOINTS - 1)))


def load_mapping(path: str | Path | None = None) -> Mapping:
    target = Path(path) if path else DEFAULT_PATH
    if not target.exists():
        return Mapping.identity()
    raw = json.loads(target.read_text())
    joints = tuple(JointMap(float(raw[name]["sign"]), float(raw[name]["offset_deg"]))
                   for name in JOINT_NAMES[:-1])
    return Mapping(joints)


def sim_to_real(sim_rad: np.ndarray, mapping: Mapping) -> np.ndarray:
    """Rows of six simulator values to LeRobot values (five degrees plus a 0..100 gripper)."""
    out = np.empty_like(sim_rad, dtype=np.float64)
    for index, joint in enumerate(mapping.joints):
        out[..., index] = joint.sign * np.degrees(sim_rad[..., index]) + joint.offset_deg
    opening = (sim_rad[..., NUM_JOINTS - 1] - GRIPPER_CLOSED) / (GRIPPER_OPEN - GRIPPER_CLOSED)
    out[..., NUM_JOINTS - 1] = np.clip(opening, 0.0, 1.0) * 100.0
    return out


def action_dict(row: np.ndarray) -> dict[str, float]:
    return {f"{name}.pos": float(value) for name, value in zip(JOINT_NAMES, row)}

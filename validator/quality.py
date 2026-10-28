"""Quality metrics for a replayed episode, each mapped to 0..1 (higher is better).

Smoothness comes from the end-effector jerk, path efficiency compares the traveled length with the
shortest start to cube to bowl route, idle time and gripper chatter penalize dithering, and arm
contact with the floor penalizes crashing.
"""

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from common.schema import CONTROL_DT, HOME_POSE, NUM_JOINTS

JERK_SCALE = 150.0  # m/s^3 RMS at which smoothness falls to 1/e
IDLE_SPEED = 0.01  # m/s below which the end effector counts as idle
IDLE_LIMIT = 0.5  # idle fraction at which the idle score reaches 0
CHATTER_DEADBAND = 0.02  # rad per step; smaller gripper moves are ignored
CHATTER_SCALE = 8.0  # gripper reversals at which the chatter score falls to 1/e
CONTACT_SCALE = 15.0  # arm floor contact steps at which the score falls to 1/e
WEIGHTS = {"smooth": 0.35, "efficiency": 0.25, "idle": 0.15, "chatter": 0.1, "contact": 0.15}


@dataclass(frozen=True)
class Quality:
    score: float
    parts: dict[str, float]


def _smoothness(ee: np.ndarray) -> float:
    if len(ee) < 5:
        return 0.0
    jerk = np.diff(ee, n=3, axis=0) / CONTROL_DT**3
    rms = float(np.sqrt((jerk**2).sum(axis=1).mean()))
    return float(np.exp(-rms / JERK_SCALE))


def _efficiency(ee: np.ndarray, spec: Mapping[str, Any], home_ee: np.ndarray) -> float:
    objects = {o["id"]: o for o in spec["objects"]}
    cube, bowl = objects["cube_target"], objects["bowl_target"]
    waypoints = np.array([home_ee, [cube["x"], cube["y"], 0.02], [bowl["x"], bowl["y"], 0.05]])
    shortest = float(np.linalg.norm(np.diff(waypoints, axis=0), axis=1).sum())
    traveled = float(np.linalg.norm(np.diff(ee, axis=0), axis=1).sum())
    return float(np.clip(shortest / max(traveled, 1e-6), 0.0, 1.0))


def _idle(ee: np.ndarray) -> float:
    speed = np.linalg.norm(np.diff(ee, axis=0), axis=1) / CONTROL_DT
    fraction = float((speed < IDLE_SPEED).mean())
    return float(np.clip(1.0 - fraction / IDLE_LIMIT, 0.0, 1.0))


def _chatter(ctrl: np.ndarray) -> float:
    delta = np.diff(ctrl[:, NUM_JOINTS - 1])
    moving = delta[np.abs(delta) > CHATTER_DEADBAND]
    reversals = int((np.diff(np.sign(moving)) != 0).sum()) if len(moving) > 1 else 0
    return float(np.exp(-reversals / CHATTER_SCALE))


def _contact(steps: int) -> float:
    return float(np.exp(-steps / CONTACT_SCALE))


def score_quality(
    ee_path: np.ndarray,
    ctrl: np.ndarray,
    spec: Mapping[str, Any],
    arm_contact_steps: int,
    home_ee: np.ndarray,
) -> Quality:
    parts = {
        "smooth": _smoothness(ee_path),
        "efficiency": _efficiency(ee_path, spec, home_ee),
        "idle": _idle(ee_path),
        "chatter": _chatter(ctrl),
        "contact": _contact(arm_contact_steps),
    }
    total = sum(WEIGHTS[name] * value for name, value in parts.items())
    return Quality(float(total), parts)


def home_end_effector() -> np.ndarray:
    import mujoco

    from common.mjcf import robot_assets

    model = mujoco.MjModel.from_xml_string('<mujoco><include file="so101.xml"/></mujoco>', robot_assets())
    data = mujoco.MjData(model)
    data.qpos[:NUM_JOINTS] = HOME_POSE
    mujoco.mj_forward(model, data)
    return data.site("gripperframe").xpos.copy()

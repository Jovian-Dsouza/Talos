"""Deterministic replay of a recording in native MuJoCo.

Strict mode replays every control row from the seeded start and compares each recorded checkpoint
with the replayed state. Windowed mode resets to each recorded checkpoint, simulates one window and
compares with the next, so the chain of checkpoints is verified without long-range chaos.
In both modes the success check runs on state the validator simulated itself.
"""

from dataclasses import dataclass
from typing import Any

import mujoco
import numpy as np

from common.bundle import Bundle
from common.checker import check_success
from common.mjcf import load_model
from common.schema import CHECKPOINT_EVERY, HOME_POSE, NUM_JOINTS, SUBSTEPS

OBJECT_BODIES = ("cube_target", "cube_distractor")
GRIPPER_BODIES = {"gripper", "moving_jaw_so101_v1", "camera_mount"}
ARM_BODIES = {"base", "shoulder", "upper_arm", "lower_arm", "wrist"} | GRIPPER_BODIES


@dataclass(frozen=True)
class ReplayResult:
    drift_arm: float
    drift_object: float
    success: bool
    success_details: dict[str, Any]
    ee_path: np.ndarray
    arm_contact_steps: int


def _home(model: mujoco.MjModel, data: mujoco.MjData) -> None:
    data.qpos[:NUM_JOINTS] = HOME_POSE
    data.ctrl[:NUM_JOINTS] = HOME_POSE
    mujoco.mj_forward(model, data)


def _object_slices(model: mujoco.MjModel) -> list[slice]:
    return [
        slice(adr, adr + 3)
        for adr in (model.joint(f"{name}_free").qposadr[0] for name in OBJECT_BODIES)
    ]


def _state(data: mujoco.MjData) -> np.ndarray:
    return np.concatenate([data.qpos, data.qvel])


def _load_state(model: mujoco.MjModel, data: mujoco.MjData, state: np.ndarray) -> None:
    data.qpos[:] = state[: model.nq]
    data.qvel[:] = state[model.nq :]
    mujoco.mj_forward(model, data)


def _drift(model: mujoco.MjModel, expected: np.ndarray, actual: np.ndarray) -> tuple[float, float]:
    arm = float(np.abs(expected[:NUM_JOINTS] - actual[:NUM_JOINTS]).max())
    obj = max(float(np.abs(expected[s] - actual[s]).max()) for s in _object_slices(model))
    return arm, obj


class _Stepper:
    """Advances the simulation one control row and records the end-effector and contacts."""

    def __init__(self, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        self.model, self.data = model, data
        self.floor = model.geom("floor").id
        self.arm_body_ids = {model.body(n).id for n in ARM_BODIES - GRIPPER_BODIES}
        self.ee: list[np.ndarray] = []
        self.contact_steps = 0

    def step(self, row: np.ndarray) -> None:
        self.data.ctrl[:NUM_JOINTS] = row
        for _ in range(SUBSTEPS):
            mujoco.mj_step(self.model, self.data)
        self.ee.append(self.data.site("gripperframe").xpos.copy())
        if self._arm_hits_floor():
            self.contact_steps += 1

    def _arm_hits_floor(self) -> bool:
        for contact in self.data.contact[: self.data.ncon]:
            pair = (contact.geom1, contact.geom2)
            if self.floor in pair:
                other = pair[0] if pair[1] == self.floor else pair[1]
                if self.model.geom_bodyid[other] in self.arm_body_ids:
                    return True
        return False


def _finish(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    stepper: _Stepper,
    task_id: str,
    drift_arm: float,
    drift_obj: float,
) -> ReplayResult:
    success, details = check_success(model, data, task_id)
    return ReplayResult(
        drift_arm, drift_obj, success, details, np.array(stepper.ee), stepper.contact_steps
    )


def replay_strict(bundle: Bundle) -> ReplayResult:
    model = load_model(bundle.ticket.scene_xml)
    data = mujoco.MjData(model)
    _home(model, data)
    stepper = _Stepper(model, data)
    drift_arm = drift_obj = 0.0
    for index, row in enumerate(bundle.ctrl):
        stepper.step(row)
        if (index + 1) % CHECKPOINT_EVERY == 0:
            recorded = bundle.checkpoints[(index + 1) // CHECKPOINT_EVERY - 1]
            arm, obj = _drift(model, recorded, _state(data))
            drift_arm, drift_obj = max(drift_arm, arm), max(drift_obj, obj)
    return _finish(model, data, stepper, bundle.ticket.task_id, drift_arm, drift_obj)


def replay_windowed(bundle: Bundle) -> ReplayResult:
    model = load_model(bundle.ticket.scene_xml)
    data = mujoco.MjData(model)
    _home(model, data)
    stepper = _Stepper(model, data)
    drift_arm = drift_obj = 0.0
    start = 0
    while start < bundle.steps:
        end = min(start + CHECKPOINT_EVERY, bundle.steps)
        for row in bundle.ctrl[start:end]:
            stepper.step(row)
        if end - start == CHECKPOINT_EVERY:
            recorded = bundle.checkpoints[end // CHECKPOINT_EVERY - 1]
            arm, obj = _drift(model, recorded, _state(data))
            drift_arm, drift_obj = max(drift_arm, arm), max(drift_obj, obj)
            _load_state(model, data, recorded)
        start = end
    return _finish(model, data, stepper, bundle.ticket.task_id, drift_arm, drift_obj)


def replay(bundle: Bundle, mode: str = "strict") -> ReplayResult:
    if mode == "strict":
        return replay_strict(bundle)
    if mode == "windowed":
        return replay_windowed(bundle)
    raise ValueError(f"unknown replay mode: {mode}")

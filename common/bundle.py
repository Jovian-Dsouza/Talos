"""Recording bundle: what the browser uploads and the validator replays.

Wire format is one JSON object. Parsing validates shape and finiteness so nothing malformed
reaches the replay stage.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from common.schema import CHECKPOINT_EVERY, MIN_STEPS, NUM_JOINTS, Ticket
from common.scene import task_config

ARM_STATE_WIDTH = 12  # qpos (6) + qvel (6) for the arm
FREE_BODY_STATE_WIDTH = 13  # qpos (7) + qvel (6) per free body
FREE_KINDS = ("vial",)
MAX_ABS_CTRL = 10.0
MAX_INPUT_EVENTS = 20000
MAX_CONTRIBUTOR_LEN = 64


class BundleError(ValueError):
    """The upload is malformed; the message is safe to show to the contributor."""


@dataclass(frozen=True)
class Bundle:
    ticket: Ticket
    mujoco_version: str
    model_hash: str
    contributor: str
    reported_success: bool
    ctrl: np.ndarray
    checkpoints: np.ndarray
    input_events: tuple[Mapping[str, Any], ...]

    @property
    def steps(self) -> int:
        return int(self.ctrl.shape[0])

    def bundle_id(self) -> str:
        digest = hashlib.sha256()
        digest.update(json.dumps(self.ticket.to_dict(), sort_keys=True).encode())
        digest.update(self.ctrl.astype("<f4").tobytes())
        return digest.hexdigest()[:32]


def _frozen(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


def _matrix(raw: Any, width: int, name: str) -> np.ndarray:
    try:
        array = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise BundleError(f"{name} is not numeric") from exc
    if array.ndim != 2 or array.shape[1] != width:
        raise BundleError(f"{name} must have shape [n, {width}]")
    if not np.isfinite(array).all():
        raise BundleError(f"{name} contains non-finite values")
    return array


def state_width(scene_spec: Mapping[str, Any]) -> int:
    """Checkpoint row width: the arm plus every free body the scene spec lists."""
    free = sum(1 for obj in scene_spec["objects"] if obj["kind"] in FREE_KINDS)
    return ARM_STATE_WIDTH + FREE_BODY_STATE_WIDTH * free


def parse_bundle(raw: Mapping[str, Any]) -> Bundle:
    try:
        ticket = Ticket.from_dict(raw["ticket"])
        mujoco_version = str(raw["mujoco_version"])
        model_hash = str(raw["model_hash"])
        reported_success = bool(raw.get("reported_success", False))
        contributor = str(raw.get("contributor", ""))[:MAX_CONTRIBUTOR_LEN]
        ctrl = _matrix(raw["ctrl"], NUM_JOINTS, "ctrl")
        checkpoints = _matrix(raw["checkpoints"], state_width(ticket.scene_spec), "checkpoints")
        events = tuple(raw.get("input_events", ()))
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, BundleError):
            raise
        raise BundleError(f"missing or invalid field: {exc}") from exc

    max_steps = task_config(ticket.task_id)["max_steps"] if ticket.task_id else 0
    if not MIN_STEPS <= ctrl.shape[0] <= max_steps:
        raise BundleError(f"episode length must be between {MIN_STEPS} and {max_steps} steps")
    if np.abs(ctrl).max() > MAX_ABS_CTRL:
        raise BundleError("ctrl values out of range")
    if checkpoints.shape[0] != ctrl.shape[0] // CHECKPOINT_EVERY:
        raise BundleError("wrong number of checkpoints for episode length")
    if len(events) > MAX_INPUT_EVENTS:
        raise BundleError("too many input events")
    return Bundle(
        ticket=ticket,
        mujoco_version=mujoco_version,
        model_hash=model_hash,
        contributor=contributor,
        reported_success=reported_success,
        ctrl=_frozen(ctrl),
        checkpoints=_frozen(checkpoints),
        input_events=events,
    )

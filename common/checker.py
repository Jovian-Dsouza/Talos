"""Authoritative success check, run on replayed state.

The browser ships a TypeScript copy of the same rules for instant feedback, but only this
function decides whether an episode succeeded.
"""

from typing import Any, Mapping

import mujoco
import numpy as np

from common.scene import task_config

ARM_DOFS = 6


def check_success(
    model: mujoco.MjModel, data: mujoco.MjData, spec: Mapping[str, Any]
) -> tuple[bool, dict[str, Any]]:
    rule = task_config(spec["task_id"])["checker"]
    return CHECKERS[rule["type"]](model, data, rule, spec)


def _object_in_container(
    model: mujoco.MjModel, data: mujoco.MjData, rule: Mapping[str, Any], spec: Mapping[str, Any]
) -> tuple[bool, dict[str, Any]]:
    obj = data.body(rule["object"])
    container = data.body(rule["container"])
    dxy = float(np.linalg.norm(obj.xpos[:2] - container.xpos[:2]))
    z = float(obj.xpos[2])
    obj_speed = float(np.linalg.norm(data.qvel[model.body(rule["object"]).dofadr[0] :][:6]))
    arm_speed = float(np.linalg.norm(data.qvel[:ARM_DOFS]))
    details = {"dxy": dxy, "z": z, "object_speed": obj_speed, "arm_speed": arm_speed}
    ok = (
        dxy <= rule["xy_radius"]
        and rule["z_min"] <= z <= rule["z_max"]
        and obj_speed <= rule["max_speed"]
        and arm_speed <= rule["max_arm_speed"]
    )
    return ok, details


def _object_in_slot(
    model: mujoco.MjModel, data: mujoco.MjData, rule: Mapping[str, Any], spec: Mapping[str, Any]
) -> tuple[bool, dict[str, Any]]:
    obj = data.body(spec["pick"])
    slot = data.site(f"slot_{spec['target_slot']}")
    dxy = float(np.linalg.norm(obj.xpos[:2] - slot.xpos[:2]))
    z = float(obj.xpos[2])
    upright = float(obj.xmat.reshape(3, 3)[2, 2])
    obj_speed = float(np.linalg.norm(data.qvel[model.body(spec["pick"]).dofadr[0] :][:6]))
    arm_speed = float(np.linalg.norm(data.qvel[:ARM_DOFS]))
    details = {"dxy": dxy, "z": z, "upright": upright, "object_speed": obj_speed, "arm_speed": arm_speed}
    ok = (
        dxy <= rule["xy_radius"]
        and rule["z_min"] <= z <= rule["z_max"]
        and upright >= rule["min_upright"]
        and obj_speed <= rule["max_speed"]
        and arm_speed <= rule["max_arm_speed"]
    )
    return ok, details


CHECKERS = {"object_in_container": _object_in_container, "object_in_slot": _object_in_slot}

"""Dev tool: solve a ticket's scene with a scripted IK policy and produce an upload payload.

Stands in for a phone while the web app is built, and drives the load script. It records the same
payload shape the browser records (ctrl rows plus state checkpoints). The validator rejects nothing
here for being scripted, because human-likeness checks are a phase 2 feature.
"""

import json
import sys
from typing import Any, Mapping

import mujoco
import numpy as np

from common.mjcf import load_model, model_hash
from common.schema import CHECKPOINT_EVERY, CONTROL_DT, HOME_POSE, NUM_JOINTS, SUBSTEPS, Ticket

HOVER = 0.09
GRASP_Z = 0.016
CARRY_Z = 0.10
DROP_Z = 0.075
OPEN, CLOSED = 1.3, 0.05
IK_JOINTS = 4  # pan, lift, elbow, wrist_flex; roll is set from the cube yaw


def solve_ik(model: mujoco.MjModel, q0: np.ndarray, target: np.ndarray) -> np.ndarray:
    data = mujoco.MjData(model)
    q = q0.copy()
    site = model.site("gripperframe").id
    lows, highs = model.jnt_range[:IK_JOINTS].T
    for _ in range(300):
        data.qpos[:NUM_JOINTS] = q
        mujoco.mj_forward(model, data)
        pos_err = target - data.site_xpos[site]
        axis = data.site_xmat[site].reshape(3, 3)[:, 0]
        down_err = np.array([0.0, 0.0, -1.0]) - axis
        jacp = np.zeros((3, model.nv))
        jacr = np.zeros((3, model.nv))
        mujoco.mj_jacSite(model, data, jacp, jacr, site)
        skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
        jac_axis = -skew @ jacr  # d(axis)/dq = w x axis
        jac = np.vstack([jacp[:, :IK_JOINTS], 0.3 * jac_axis[:, :IK_JOINTS]])
        err = np.concatenate([pos_err, 0.3 * down_err])
        step = jac.T @ np.linalg.solve(jac @ jac.T + 1e-4 * np.eye(6), err)
        q[:IK_JOINTS] = np.clip(q[:IK_JOINTS] + step, lows, highs)
        if np.linalg.norm(pos_err) < 1e-4 and np.linalg.norm(down_err) < 0.05:
            break
    return q


def _segment(a: np.ndarray, b: np.ndarray, steps: int) -> np.ndarray:
    t = np.linspace(0.0, 1.0, steps, endpoint=False)[:, None]
    return a + (b - a) * (t * t * (3 - 2 * t))


def plan(model: mujoco.MjModel, spec: Mapping[str, Any]) -> np.ndarray:
    objects = {o["id"]: o for o in spec["objects"]}
    cube, bowl = objects["cube_target"], objects["bowl_target"]
    home = np.array(HOME_POSE, dtype=float)

    def pose(x: float, y: float, z: float, gripper: float, roll: float, seed: np.ndarray):
        q = solve_ik(model, seed, np.array([x, y, z]))
        q[4], q[5] = roll, gripper
        return q

    roll = ((cube["yaw"] - np.arctan2(cube["y"], cube["x"]) + np.pi / 4) % (np.pi / 2)) - np.pi / 4
    above = pose(cube["x"], cube["y"], HOVER, OPEN, roll, home)
    grasp = pose(cube["x"], cube["y"], GRASP_Z, OPEN, roll, above)
    closed = grasp.copy()
    closed[5] = CLOSED
    lift = pose(cube["x"], cube["y"], CARRY_Z, CLOSED, roll, grasp)
    over = pose(bowl["x"], bowl["y"], CARRY_Z, CLOSED, roll, lift)
    drop = pose(bowl["x"], bowl["y"], DROP_Z, CLOSED, roll, over)
    released = drop.copy()
    released[5] = OPEN
    retreat = pose(bowl["x"], bowl["y"], CARRY_Z, OPEN, roll, drop)
    waypoints = [(home, 5), (above, 45), (grasp, 35), (closed, 25), (lift, 40), (over, 50),
                 (drop, 25), (released, 25), (retreat, 25), (retreat, 30)]
    rows = [np.tile(home, (10, 1))]
    for (a, _), (b, steps) in zip(waypoints, waypoints[1:]):
        rows.append(_segment(a, b, steps))
    return np.vstack(rows).astype(np.float32)


def record(xml: str, ctrl: np.ndarray) -> tuple[np.ndarray, bool]:
    """Simulate like the browser: return state checkpoints and the final cube position check."""
    model = load_model(xml)
    data = mujoco.MjData(model)
    data.qpos[:NUM_JOINTS] = HOME_POSE
    data.ctrl[:NUM_JOINTS] = HOME_POSE
    mujoco.mj_forward(model, data)
    checkpoints = []
    for index, row in enumerate(ctrl):
        data.ctrl[:NUM_JOINTS] = row
        for _ in range(SUBSTEPS):
            mujoco.mj_step(model, data)
        if (index + 1) % CHECKPOINT_EVERY == 0:
            checkpoints.append(np.concatenate([data.qpos, data.qvel]))
    return np.array(checkpoints), data


def build_payload(ticket: Ticket, contributor: str = "scripted") -> dict[str, Any]:
    model = load_model(ticket.scene_xml)
    ctrl = plan(model, ticket.scene_spec)
    checkpoints, data = record(ticket.scene_xml, ctrl)
    return {
        "ticket": ticket.to_dict(),
        "mujoco_version": mujoco.mj_versionString(),
        "model_hash": model_hash(ticket.scene_xml),
        "control_dt": CONTROL_DT,
        "contributor": contributor,
        "reported_success": True,
        "ctrl": ctrl.tolist(),
        "checkpoints": checkpoints.tolist(),
        "input_events": [],
    }


def main(seed: int, out: str) -> None:
    from common.mjcf import scene_xml
    from common.scene import TASK_ID, make_scene

    spec = make_scene(seed)
    ticket = Ticket(0, "00" * 32, "dev", TASK_ID, 0, seed, spec, scene_xml(spec), spec["instruction"], 10**9)
    payload = build_payload(ticket)
    from common.bundle import parse_bundle
    from validator.replay import replay_strict

    result = replay_strict(parse_bundle(payload))
    print(spec["instruction"], "success", result.success, result.success_details, "drift", result.drift_arm, result.drift_object)
    with open(out, "w") as handle:
        json.dump(payload, handle)


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2])

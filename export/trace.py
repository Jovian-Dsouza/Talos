"""Replay a bundle natively and keep per-step observations, actions and camera frames."""

from dataclasses import dataclass

import mujoco
import numpy as np

from common.bundle import Bundle
from common.mjcf import load_model
from common.schema import HOME_POSE, NUM_JOINTS, SUBSTEPS

CAMERAS = {"front": "front", "wrist": "wrist_cam"}  # dataset name -> MuJoCo camera


@dataclass(frozen=True)
class Trace:
    state: np.ndarray  # (T, 6) arm joint positions after each step, radians
    action: np.ndarray  # (T, 6) ctrl rows applied at each step, radians
    frames: dict[str, np.ndarray]  # camera name -> (T, H, W, 3) uint8; empty when size is None


def trace(bundle: Bundle, size: tuple[int, int] | None = (240, 320)) -> Trace:
    model = load_model(bundle.ticket.scene_xml)
    data = mujoco.MjData(model)
    data.qpos[:NUM_JOINTS] = HOME_POSE
    data.ctrl[:NUM_JOINTS] = HOME_POSE
    mujoco.mj_forward(model, data)
    renderer = mujoco.Renderer(model, size[0], size[1]) if size else None
    states = []
    frames: dict[str, list[np.ndarray]] = {name: [] for name in CAMERAS} if renderer else {}
    try:
        for row in bundle.ctrl:
            data.ctrl[:NUM_JOINTS] = row
            for _ in range(SUBSTEPS):
                mujoco.mj_step(model, data)
            states.append(data.qpos[:NUM_JOINTS].copy())
            for name, camera in (CAMERAS.items() if renderer is not None else ()):
                renderer.update_scene(data, camera=camera)
                frames[name].append(renderer.render().copy())
    finally:
        if renderer is not None:
            renderer.close()
    return Trace(
        np.array(states, dtype=np.float32),
        np.array(bundle.ctrl, dtype=np.float32),
        {name: np.array(rows, dtype=np.uint8) for name, rows in frames.items()},
    )

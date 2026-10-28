"""M0: build a contact-heavy scripted trajectory and the scene with the cube at the gripper target.

Writes assets/so101/m0_scene_built.xml and scripts/m0/ctrl.json.
"""

import json
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "so101"
HOME = np.array([0.0, -1.2, 1.2, 0.8, 0.0, 0.5])
TARGET = np.array([0.0, -0.5, 1.0, 0.8, 0.0, 0.1])
PUSH = np.array([-0.5, -0.5, 1.0, 0.8, 0.0, 0.1])
LIFT = np.array([-0.5, -1.2, 1.2, 0.8, 0.0, 0.6])
CONTROL_STEPS = 40  # per segment at 20 ms


def tip_position(model: mujoco.MjModel, q: np.ndarray) -> np.ndarray:
    data = mujoco.MjData(model)
    data.qpos[:6] = q
    mujoco.mj_forward(model, data)
    return data.site("gripperframe").xpos.copy()


def segment(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    t = np.linspace(0.0, 1.0, CONTROL_STEPS, endpoint=False)[:, None]
    smooth = t * t * (3 - 2 * t)
    return a + (b - a) * smooth


def main() -> None:
    plain = mujoco.MjModel.from_xml_path(str(ASSETS / "so101.xml"))
    tip = tip_position(plain, TARGET)
    cube_pos = f"{tip[0]:.5f} {tip[1]:.5f} 0.0125"
    print("tip at target", tip, "cube at", cube_pos)
    xml = (ASSETS / "m0_scene.xml").read_text().replace("CUBE_POS", cube_pos)
    (ASSETS / "m0_scene_built.xml").write_text(xml)
    ctrl = np.vstack(
        [
            np.tile(HOME, (10, 1)),
            segment(HOME, TARGET),
            segment(TARGET, PUSH),
            segment(PUSH, LIFT),
            np.tile(LIFT, (10, 1)),
        ]
    ).astype(np.float32)
    (Path(__file__).parent / "ctrl.json").write_text(json.dumps(ctrl.tolist()))
    print("ctrl steps", len(ctrl))


main()

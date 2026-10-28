"""M0: replay ctrl.json in native MuJoCo and dump qpos/qvel after every control step."""

import json
import sys
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SUBSTEPS = 10


def main(out: Path) -> None:
    model = mujoco.MjModel.from_xml_path(str(ROOT / "assets/so101/m0_scene_built.xml"))
    data = mujoco.MjData(model)
    ctrl = np.array(json.loads((Path(__file__).parent / "ctrl.json").read_text()), dtype=np.float64)
    data.qpos[:6] = ctrl[0]
    data.ctrl[:6] = ctrl[0]
    mujoco.mj_forward(model, data)
    states = []
    for row in ctrl:
        data.ctrl[:6] = row
        for _ in range(SUBSTEPS):
            mujoco.mj_step(model, data)
        states.append(np.concatenate([data.qpos, data.qvel]).tolist())
    out.write_text(json.dumps({"version": mujoco.mj_versionString(), "states": states}))
    print("native", mujoco.mj_versionString(), "cube final", data.qpos[6:9])


main(Path(sys.argv[1]))

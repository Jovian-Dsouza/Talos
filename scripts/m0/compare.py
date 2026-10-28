"""M0: report per-step drift between two state dumps."""

import json
import sys

import numpy as np


def main(a_path: str, b_path: str) -> None:
    a = np.array(json.loads(open(a_path).read())["states"])
    b = np.array(json.loads(open(b_path).read())["states"])
    qpos_err = np.abs(a[:, :13] - b[:, :13])
    arm = qpos_err[:, :6].max(axis=1)
    cube = qpos_err[:, 6:9].max(axis=1)
    for i in (0, 30, 60, 90, 120, len(a) - 1):
        print(f"step {i:3d}  arm max {arm[i]:.3e}  cube pos {cube[i]:.3e}")
    print("max arm", arm.max(), "max cube", cube.max())


main(sys.argv[1], sys.argv[2])

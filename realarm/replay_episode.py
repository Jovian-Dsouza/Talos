"""Replay a validator-accepted episode on a physical SO-101 follower arm.

Usage: python -m realarm.replay_episode BUNDLE_JSON SERIAL_PORT [MAPPING_JSON]
Environment: DRY_RUN=1 prints the mapped motion without touching hardware.
             SPEED=0.5 time scale (1.0 is the recorded speed), default 0.5.
             MAX_STEP_DEG=8 largest joint change per command sent, default 8.

The arm first glides from its current pose to the episode's first pose, then plays the recorded
actions at the recorded control rate. Keep a hand near the power switch for the first runs.
"""

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

from common.bundle import parse_bundle
from common.schema import CONTROL_DT, JOINT_NAMES
from realarm.mapping import action_dict, load_mapping, sim_to_real

GLIDE_SECONDS = 3.0
DEFAULT_SPEED = 0.5
DEFAULT_MAX_STEP_DEG = 8.0


def mapped_actions(bundle_path: Path, mapping_path: str | None) -> np.ndarray:
    bundle = parse_bundle(json.loads(bundle_path.read_text()))
    return sim_to_real(np.asarray(bundle.ctrl, dtype=np.float64), load_mapping(mapping_path))


def limit_step(previous: np.ndarray, target: np.ndarray, max_step: float) -> np.ndarray:
    return previous + np.clip(target - previous, -max_step, max_step)


def current_pose(robot) -> np.ndarray:
    observation = robot.get_observation()
    return np.array([observation[f"{name}.pos"] for name in JOINT_NAMES], dtype=np.float64)


def main() -> None:
    bundle_path = Path(sys.argv[1])
    port = sys.argv[2]
    mapping_path = sys.argv[3] if len(sys.argv) > 3 else None
    speed = float(os.environ.get("SPEED", DEFAULT_SPEED))
    max_step = float(os.environ.get("MAX_STEP_DEG", DEFAULT_MAX_STEP_DEG))
    actions = mapped_actions(bundle_path, mapping_path)
    print(f"{len(actions)} steps, joint ranges (deg, gripper 0-100):")
    for index, name in enumerate(JOINT_NAMES):
        print(f"  {name}: {actions[:, index].min():.1f} to {actions[:, index].max():.1f}")
    if os.environ.get("DRY_RUN") == "1":
        return

    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

    config = SO101FollowerConfig(port=port, id="bittesnor_follower", use_degrees=True,
                                 max_relative_target=max_step)
    robot = SO101Follower(config)
    robot.connect()
    try:
        input("Clear the workspace and press Enter to start (Ctrl+C aborts)... ")
        pose = current_pose(robot)
        glide_steps = max(1, round(GLIDE_SECONDS / CONTROL_DT))
        for step in range(1, glide_steps + 1):
            blend = pose + (actions[0] - pose) * (step / glide_steps)
            robot.send_action(action_dict(limit_step(current_pose(robot), blend, max_step)))
            time.sleep(CONTROL_DT)
        period = CONTROL_DT / speed
        for row in actions:
            started = time.monotonic()
            robot.send_action(action_dict(limit_step(current_pose(robot), row, max_step)))
            time.sleep(max(0.0, period - (time.monotonic() - started)))
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main()

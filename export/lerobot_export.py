"""Export accepted recordings as a LeRobotDataset (SO-101 feature names).

Usage: python -m export.lerobot_export ACCEPTED_DIR OUT_DIR [REPO_ID] [MAPPING_JSON]

Frames are rendered during native replay, so the browser never has to produce video. Joint values
are converted with realarm/mapping.py. Per-episode provenance (seed, pool, contributor, scores) is
written to meta/teleop_provenance.jsonl next to the standard LeRobot metadata.
"""

import json
import sys
from pathlib import Path

import numpy as np
from lerobot.datasets.lerobot_dataset import LeRobotDataset

from common.bundle import parse_bundle
from common.schema import JOINT_NAMES
from export.trace import trace
from realarm.mapping import load_mapping, sim_to_real

FPS = 50  # the control rate, kept as is so no resampling error enters the data
IMAGE_SIZE = (240, 320)
ROBOT_TYPE = "so101_follower"


def _features() -> dict:
    names = [f"{name}.pos" for name in JOINT_NAMES]
    height, width = IMAGE_SIZE
    return {
        "observation.state": {"dtype": "float32", "shape": (len(names),), "names": names},
        "action": {"dtype": "float32", "shape": (len(names),), "names": names},
        "observation.images.front": {
            "dtype": "video",
            "shape": (height, width, 3),
            "names": ["height", "width", "channels"],
        },
    }


def export(accepted_dir: Path, out_dir: Path, repo_id: str, mapping_path: str | None = None) -> int:
    mapping = load_mapping(mapping_path)
    files = sorted(accepted_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"no accepted recordings in {accepted_dir}")
    dataset = LeRobotDataset.create(
        repo_id=repo_id, fps=FPS, features=_features(), root=out_dir, robot_type=ROBOT_TYPE, use_videos=True
    )
    provenance = []
    for index, path in enumerate(files):
        bundle = parse_bundle(json.loads(path.read_text()))
        result = trace(bundle, IMAGE_SIZE)
        state = sim_to_real(result.state.astype(np.float64), mapping).astype(np.float32)
        action = sim_to_real(result.action.astype(np.float64), mapping).astype(np.float32)
        for step in range(len(state)):
            dataset.add_frame(
                {
                    "observation.state": state[step],
                    "action": action[step],
                    "observation.images.front": result.frames[step],
                    "task": bundle.ticket.instruction,
                }
            )
        dataset.save_episode()
        provenance.append(
            {
                "episode_index": index,
                "bundle_id": path.stem,
                "seed": str(bundle.ticket.seed),
                "pool_hotkey": bundle.ticket.hotkey,
                "task_id": bundle.ticket.task_id,
                "contributor": bundle.contributor,
                "block": bundle.ticket.block,
                "scene": bundle.ticket.scene_spec,
            }
        )
        print(f"episode {index}: {bundle.ticket.instruction} ({len(state)} frames)")
    dataset.finalize()
    meta = out_dir / "meta" / "teleop_provenance.jsonl"
    meta.write_text("\n".join(json.dumps(row) for row in provenance) + "\n")
    return len(files)


if __name__ == "__main__":
    accepted = Path(sys.argv[1])
    out = Path(sys.argv[2])
    repo = sys.argv[3] if len(sys.argv) > 3 else "bittesnor/teleop-so101-sim-sample"
    export(accepted, out, repo, sys.argv[4] if len(sys.argv) > 4 else None)

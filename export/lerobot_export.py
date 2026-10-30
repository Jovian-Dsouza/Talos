"""Export accepted recordings as a LeRobotDataset (SO-101 feature names).

Usage: python -m export.lerobot_export ACCEPTED_DIR OUT_DIR [REPO_ID] [--db VALIDATOR_DB] [--mapping JSON] [--push]

Frames are rendered during native replay, so the browser never has to produce video. Joint values
are converted with realarm/mapping.py. Per-episode provenance (seed, miner, contributor, scores) is
written to meta/teleop_provenance.jsonl next to the standard LeRobot metadata.
"""

import argparse
import json
import os
import sqlite3
from pathlib import Path

import numpy as np
from lerobot.datasets.lerobot_dataset import LeRobotDataset

from common.bundle import parse_bundle
from common.schema import JOINT_NAMES
from export.trace import CAMERAS, trace
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
        **{
            f"observation.images.{name}": {
                "dtype": "video",
                "shape": (height, width, 3),
                "names": ["height", "width", "channels"],
            }
            for name in CAMERAS
        },
    }


def _scores(db_path: Path | None) -> dict[str, dict]:
    """Validator scores per bundle id, so each episode carries why it was worth what it was."""
    if db_path is None or not db_path.exists():
        return {}
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = db.execute("SELECT bundle_id, time_score, smooth_score, duration_s, value, epoch FROM accepted")
    return {r[0]: {"time_score": r[1], "smooth_score": r[2], "duration_s": r[3], "score": r[4], "epoch": r[5]}
            for r in rows}


def export(accepted_dir: Path, out_dir: Path, repo_id: str, mapping_path: str | None = None,
           db_path: Path | None = None, push: bool = False) -> int:
    mapping = load_mapping(mapping_path)
    files = sorted(accepted_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"no accepted recordings in {accepted_dir}")
    dataset = LeRobotDataset.create(
        repo_id=repo_id, fps=FPS, features=_features(), root=out_dir, robot_type=ROBOT_TYPE, use_videos=True
    )
    provenance = []
    scores = _scores(db_path)
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
                    "task": bundle.ticket.instruction,
                    **{f"observation.images.{name}": result.frames[name][step] for name in CAMERAS},
                }
            )
        dataset.save_episode()
        provenance.append(
            {
                "episode_index": index,
                "bundle_id": path.stem,
                "seed": str(bundle.ticket.seed),
                "miner_hotkey": bundle.ticket.hotkey,
                "task_id": bundle.ticket.task_id,
                "contributor": bundle.contributor,
                "block": bundle.ticket.block,
                "scene": bundle.ticket.scene_spec,
                **scores.get(path.stem, {}),
            }
        )
        print(f"episode {index}: {bundle.ticket.instruction} ({len(state)} frames)")
    dataset.finalize()
    meta = out_dir / "meta" / "teleop_provenance.jsonl"
    meta.write_text("\n".join(json.dumps(row) for row in provenance) + "\n")
    if push:
        if not os.environ.get("HF_TOKEN"):
            raise SystemExit("set HF_TOKEN to push to the Hugging Face Hub")
        dataset.push_to_hub()
    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export accepted recordings as a LeRobotDataset")
    parser.add_argument("accepted_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("repo_id", nargs="?", default="taunet/teleop-so101-sim-sample")
    parser.add_argument("--db", type=Path, help="validator database, adds scores to the provenance file")
    parser.add_argument("--mapping", help="sim to real joint mapping JSON")
    parser.add_argument("--push", action="store_true", help="upload to the Hugging Face Hub (needs HF_TOKEN)")
    args = parser.parse_args()
    export(args.accepted_dir, args.out_dir, args.repo_id, args.mapping, args.db, args.push)


if __name__ == "__main__":
    main()

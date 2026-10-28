"""Shrink the SO-101 visual meshes for phones, leaving physics-relevant meshes untouched.

Collision hulls and the camera mount (its mass geom derives inertia from the mesh) must stay
exact so that browser and validator simulate identical bodies. Everything else is visual only.
"""

import json
import shutil
import sys
from pathlib import Path

import fast_simplification
import trimesh

SOURCE = Path(__file__).resolve().parents[2] / "assets" / "so101"
KEEP_EXACT = {
    "wrist_roll_follower_so101_gripper_part0_v1.stl",
    "moving_jaw_so101_gripper_part0_v1.stl",
    "moving_jaw_so101_gripper_part1_v1.stl",
    "wrist_roll_follower_so101_camera_mount.stl",
}
TARGET_FACES = 2500


def decimate(src: Path, dst: Path) -> tuple[int, int]:
    mesh = trimesh.load_mesh(src, process=True)
    before = len(mesh.faces)
    if before > TARGET_FACES:
        points, faces = fast_simplification.simplify(
            mesh.vertices, mesh.faces, target_reduction=1.0 - TARGET_FACES / before
        )
        mesh = trimesh.Trimesh(points, faces, process=False)
    mesh.export(dst)
    return before, len(mesh.faces)


def main(out: Path) -> None:
    (out / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy(SOURCE / "so101.xml", out / "so101.xml")
    for stl in sorted((SOURCE / "assets").glob("*.stl")):
        dst = out / "assets" / stl.name
        if stl.name in KEEP_EXACT:
            shutil.copy(stl, dst)
            continue
        before, after = decimate(stl, dst)
        print(f"{stl.name}: {before} -> {after} faces")
    files = ["so101.xml", *(f"assets/{p.name}" for p in sorted((out / "assets").iterdir()))]
    (out / "manifest.json").write_text(json.dumps(files, indent=1))
    total = sum(f.stat().st_size for f in (out / "assets").iterdir())
    print(f"total mesh bytes {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

"""Build the MuJoCo scene for a SceneSpec and load it natively.

The scene XML is plain text that includes the SO-101 model. The miner ships it in the ticket,
the browser loads it with the same assets, and the validator rebuilds and compares it, so all
three simulate the same physics. Collision geoms are boxes only; the SO-101 meshes are visual.
"""

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import mujoco

from common.scene import PALETTE

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "so101"
ROBOT_FILE = "so101.xml"

CUBE_HALF = 0.0125
CUBE_MASS = 0.02
BOWL_BASE_HALF = 0.04
BOWL_WALL_HALF_HEIGHT = 0.015
BOWL_WALL_THICKNESS_HALF = 0.003
BOWL_BASE_THICKNESS_HALF = 0.003
FRICTION = "1 5e-3 5e-4"


def _rgba(color: str) -> str:
    r, g, b = PALETTE[color]
    return f"{r} {g} {b} 1"


def _cube_xml(obj: Mapping[str, Any]) -> str:
    return f"""    <body name="{obj['id']}" pos="{obj['x']} {obj['y']} {CUBE_HALF}" euler="0 0 {obj['yaw']}">
      <freejoint name="{obj['id']}_free"/>
      <geom name="{obj['id']}_geom" type="box" size="{CUBE_HALF} {CUBE_HALF} {CUBE_HALF}"
        mass="{CUBE_MASS}" rgba="{_rgba(obj['color'])}" friction="{FRICTION}" condim="4"/>
    </body>"""


def _bowl_xml(obj: Mapping[str, Any]) -> str:
    base, wall, tb, th = BOWL_BASE_HALF, BOWL_BASE_THICKNESS_HALF, BOWL_BASE_THICKNESS_HALF, BOWL_WALL_HALF_HEIGHT
    wall_z = 2 * tb + th
    rgba = _rgba(obj["color"])
    walls = (
        (0, base - wall, base, wall, wall_z),
        (0, -(base - wall), base, wall, wall_z),
        (base - wall, 0, wall, base, wall_z),
        (-(base - wall), 0, wall, base, wall_z),
    )
    wall_geoms = "\n".join(
        f'      <geom type="box" pos="{px} {py} {pz}" size="{sx} {sy} {th}" rgba="{rgba}" friction="{FRICTION}"/>'
        for px, py, sx, sy, pz in walls
    )
    return f"""    <body name="{obj['id']}" pos="{obj['x']} {obj['y']} 0" euler="0 0 {obj['yaw']}">
      <geom type="box" pos="0 0 {tb}" size="{base} {base} {tb}" rgba="{rgba}" friction="{FRICTION}"/>
{wall_geoms}
    </body>"""


def scene_xml(spec: Mapping[str, Any]) -> str:
    builders = {"cube": _cube_xml, "bowl": _bowl_xml}
    bodies = "\n".join(builders[o["kind"]](o) for o in spec["objects"])
    return f"""<mujoco model="teleop_scene">
  <include file="{ROBOT_FILE}"/>
  <visual><global offwidth="640" offheight="480"/></visual>
  <worldbody>
    <light pos="0 0 1.5" dir="0 0 -1"/>
    <geom name="floor" type="plane" size="1 1 0.05" friction="{FRICTION}" rgba="0.8 0.8 0.78 1"/>
    <camera name="front" pos="0.2 -0.5 0.3" xyaxes="1 0 0 0 0.5 0.866" fovy="55"/>
{bodies}
  </worldbody>
</mujoco>
"""


@lru_cache(maxsize=1)
def robot_assets() -> dict[str, bytes]:
    files = {ROBOT_FILE: (ASSET_DIR / ROBOT_FILE).read_bytes()}
    for mesh in sorted((ASSET_DIR / "assets").iterdir()):
        files[f"assets/{mesh.name}"] = mesh.read_bytes()
    return files


def model_hash(xml: str) -> str:
    digest = hashlib.sha256()
    digest.update(xml.encode())
    digest.update(robot_assets()[ROBOT_FILE])
    return digest.hexdigest()


def load_model(xml: str) -> mujoco.MjModel:
    return mujoco.MjModel.from_xml_string(xml, robot_assets())

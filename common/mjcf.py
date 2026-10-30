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

from common.scene import PALETTE, RACK_COLS, RACK_PITCH, RACK_ROWS, slot_ids, slot_offset

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "so101"
ROBOT_FILE = "so101.xml"

FRICTION = "1 5e-3 5e-4"
BENCH_RGBA = "0.62 0.66 0.68 1"

# Sample vial: box collision (stable grip width), cylinders for draw only. Sized for teleop on phone.
VIAL_HALF = (0.0175, 0.0175, 0.030)
VIAL_MASS = 0.028
VIAL_CAP_HALF = 0.0065
VIAL_BODY_RADIUS = 0.0185
VIAL_CAP_RADIUS = 0.0195
VIAL_GLASS_RGBA = "0.82 0.9 0.95 0.5"

# Rack: base plate, then a top plate with square holes. Seated vial centre sits on the base.
RACK_BASE_HALF_Z = 0.003
RACK_TOP = 0.025
RACK_HOLE_HALF = 0.0255
RACK_RIM = 0.008
RACK_RGBA = "0.28 0.31 0.34 1"
SEATED_Z = 2 * RACK_BASE_HALF_Z + VIAL_HALF[2] + 0.0005


def _rgba(color: str) -> str:
    r, g, b = PALETTE[color]
    return f"{r} {g} {b} 1"


def _vial_xml(obj: Mapping[str, Any]) -> str:
    z = SEATED_Z if obj.get("seated") else VIAL_HALF[2]
    hx, hy, hz = VIAL_HALF
    cap_z = hz - VIAL_CAP_HALF
    glass_half = hz - 2 * VIAL_CAP_HALF
    return f"""    <body name="{obj['id']}" pos="{obj['x']} {obj['y']} {z}" euler="0 0 {obj['yaw']}">
      <freejoint name="{obj['id']}_free"/>
      <geom name="{obj['id']}_geom" type="box" size="{hx} {hy} {hz}" mass="{VIAL_MASS}"
        group="3" friction="{FRICTION}" condim="4"/>
      <geom name="{obj['id']}_glass" type="cylinder" pos="0 0 {-VIAL_CAP_HALF}" size="{VIAL_BODY_RADIUS} {glass_half + VIAL_CAP_HALF - 0.0005}"
        rgba="{VIAL_GLASS_RGBA}" contype="0" conaffinity="0" group="2" mass="0"/>
      <geom name="{obj['id']}_cap" type="cylinder" pos="0 0 {cap_z}" size="{VIAL_CAP_RADIUS} {VIAL_CAP_HALF}"
        rgba="{_rgba(obj['color'])}" contype="0" conaffinity="0" group="2" mass="0"/>
    </body>"""


def _rack_strips() -> list[tuple[float, float, float, float]]:
    """Solid regions of the top plate as (x_centre, y_centre, half_x, half_y)."""
    half_x = RACK_COLS * RACK_PITCH / 2 + RACK_RIM / 2
    half_y = len(RACK_ROWS) * RACK_PITCH / 2 + RACK_RIM / 2
    h = RACK_HOLE_HALF
    row_centres = sorted({slot_offset(s)[1] for s in slot_ids()})
    col_centres = sorted({slot_offset(s)[0] for s in slot_ids()})
    strips = []
    # Full-length bars between and outside the hole rows.
    edges = [-half_y] + [e for c in row_centres for e in (c - h, c + h)] + [half_y]
    for lo, hi in zip(edges[0::2], edges[1::2]):
        strips.append((0.0, (lo + hi) / 2, half_x, (hi - lo) / 2))
    # Short bars between the holes inside each row.
    x_edges = [-half_x] + [e for c in col_centres for e in (c - h, c + h)] + [half_x]
    for c in row_centres:
        for lo, hi in zip(x_edges[0::2], x_edges[1::2]):
            strips.append(((lo + hi) / 2, c, (hi - lo) / 2, h))
    return strips


def _rack_xml(obj: Mapping[str, Any]) -> str:
    half_x = RACK_COLS * RACK_PITCH / 2 + RACK_RIM / 2
    half_y = len(RACK_ROWS) * RACK_PITCH / 2 + RACK_RIM / 2
    plate_half = (RACK_TOP - 2 * RACK_BASE_HALF_Z) / 2
    plate_z = 2 * RACK_BASE_HALF_Z + plate_half
    geoms = [
        f'      <geom type="box" pos="0 0 {RACK_BASE_HALF_Z}" size="{half_x} {half_y} {RACK_BASE_HALF_Z}" rgba="{RACK_RGBA}" friction="{FRICTION}"/>'
    ]
    for cx, cy, sx, sy in _rack_strips():
        if sx < 1e-4 or sy < 1e-4:
            continue
        geoms.append(
            f'      <geom type="box" pos="{cx:.5f} {cy:.5f} {plate_z}" size="{sx:.5f} {sy:.5f} {plate_half}" rgba="{RACK_RGBA}" friction="{FRICTION}"/>'
        )
    for slot in slot_ids():
        ox, oy = slot_offset(slot)
        geoms.append(f'      <site name="slot_{slot}" pos="{ox} {oy} {SEATED_Z}" size="0.002" group="4"/>')
    body = "\n".join(geoms)
    return f"""    <body name="{obj['id']}" pos="{obj['x']} {obj['y']} 0" euler="0 0 {obj['yaw']}">
{body}
    </body>"""


def scene_xml(spec: Mapping[str, Any]) -> str:
    builders = {"vial": _vial_xml, "rack": _rack_xml}
    bodies = "\n".join(builders[o["kind"]](o) for o in spec["objects"])
    return f"""<mujoco model="teleop_scene">
  <include file="{ROBOT_FILE}"/>
  <visual><global offwidth="640" offheight="480"/></visual>
  <worldbody>
    <light pos="0 0 1.5" dir="0 0 -1"/>
    <geom name="floor" type="plane" size="1 1 0.05" friction="{FRICTION}" rgba="{BENCH_RGBA}"/>
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

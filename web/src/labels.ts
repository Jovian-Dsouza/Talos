import * as THREE from "three";
import { RACK_COLS, RACK_ROWS } from "./constants";
import type { Sim } from "./sim";
import type { SceneSpec } from "./types";

const LABEL_SIZE = 0.03; // metres, so each glyph is readable on a phone
const LABEL_HEIGHT = 0.0007; // just above the bench
// Text baseline along "screen right" of the default camera, so labels read upright from there.
const READING_YAW = -0.69;

function glyph(text: string): THREE.Mesh {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 96;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.font = "700 72px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineWidth = 10;
    ctx.strokeStyle = "#ffffff";
    ctx.strokeText(text, 48, 52);
    ctx.fillStyle = "#14324d";
    ctx.fillText(text, 48, 52);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(LABEL_SIZE, LABEL_SIZE),
    new THREE.MeshBasicMaterial({ map: texture, transparent: true, depthWrite: false }),
  );
  mesh.rotation.z = READING_YAW;
  return mesh;
}

/** Row letters beside the left end of the rack and column numbers along its near side. */
export function buildSlotLabels(sim: Sim, spec: SceneSpec): THREE.Group {
  const group = new THREE.Group();
  if (!spec.objects.some((o) => o.kind === "rack")) return group;
  const { model, data } = sim;
  const slot = (name: string): [number, number] => {
    const id = model.site(`slot_${name}`).id;
    return [data.site_xpos[3 * id], data.site_xpos[3 * id + 1]];
  };
  const rack = model.body("rack").id;
  const xAxis: [number, number] = [data.xmat[9 * rack], data.xmat[9 * rack + 3]];
  const yAxis: [number, number] = [data.xmat[9 * rack + 1], data.xmat[9 * rack + 4]];
  const [a1x, a1y] = slot(`${RACK_ROWS[0]}1`);
  const [a2x, a2y] = slot(`${RACK_ROWS[0]}2`);
  const pitch = Math.hypot(a2x - a1x, a2y - a1y);
  const place = (text: string, x: number, y: number) => {
    const label = glyph(text);
    label.position.set(x, y, LABEL_HEIGHT);
    group.add(label);
  };
  for (const row of RACK_ROWS) {
    const [x, y] = slot(`${row}1`);
    place(row, x - xAxis[0] * pitch, y - xAxis[1] * pitch);
  }
  const near = RACK_ROWS[RACK_ROWS.length - 1];
  for (let col = 1; col <= RACK_COLS; col++) {
    const [x, y] = slot(`${near}${col}`);
    place(String(col), x + yAxis[0] * pitch, y + yAxis[1] * pitch);
  }
  return group;
}

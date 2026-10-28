// M0: replay ctrl.json in WASM MuJoCo (Node) and dump qpos/qvel after every control step.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import loadMujoco from "@mujoco/mujoco";

const here = path.dirname(fileURLToPath(import.meta.url));
const assets = path.join(here, "../../assets/so101");
const SUBSTEPS = 10;

const mujoco = await loadMujoco();
mujoco.FS.mkdir("/work");
mujoco.FS.mkdir("/work/assets");
for (const f of ["so101.xml", "m0_scene_built.xml"]) {
  mujoco.FS.writeFile(`/work/${f}`, fs.readFileSync(path.join(assets, f)));
}
for (const f of fs.readdirSync(path.join(assets, "assets"))) {
  mujoco.FS.writeFile(`/work/assets/${f}`, fs.readFileSync(path.join(assets, "assets", f)));
}

const model = mujoco.MjModel.from_xml_path("/work/m0_scene_built.xml");
const data = new mujoco.MjData(model);
const ctrl = JSON.parse(fs.readFileSync(path.join(here, "ctrl.json"), "utf8"));
for (let j = 0; j < 6; j++) {
  data.qpos[j] = ctrl[0][j];
  data.ctrl[j] = ctrl[0][j];
}
mujoco.mj_forward(model, data);
const states = [];
for (const row of ctrl) {
  for (let j = 0; j < 6; j++) data.ctrl[j] = row[j];
  for (let i = 0; i < SUBSTEPS; i++) mujoco.mj_step(model, data);
  states.push([...data.qpos, ...data.qvel]);
}
fs.writeFileSync(process.argv[2], JSON.stringify({ version: mujoco.mj_versionString?.() ?? "wasm", states }));
console.log("wasm cube final", [...data.qpos].slice(6, 9));
data.delete();
model.delete();

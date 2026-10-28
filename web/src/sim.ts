import loadMujoco from "@mujoco/mujoco";
import { HOME_POSE, NUM_JOINTS, SUBSTEPS } from "./constants";

// The bindings type most members as `any`; keep the looseness inside this module.
/* eslint-disable @typescript-eslint/no-explicit-any */
export type Mujoco = any;
export type Model = any;
export type Data = any;

let mujocoPromise: Promise<Mujoco> | null = null;
const mounted = new Set<string>();

async function mountAssets(mujoco: Mujoco): Promise<void> {
  const base = `${import.meta.env.BASE_URL}assets/so101`;
  const files: string[] = await (await fetch(`${base}/manifest.json`)).json();
  mujoco.FS.mkdir("/work");
  mujoco.FS.mkdir("/work/assets");
  await Promise.all(
    files.map(async (file) => {
      const bytes = new Uint8Array(await (await fetch(`${base}/${file}`)).arrayBuffer());
      mujoco.FS.writeFile(`/work/${file}`, bytes);
      mounted.add(file);
    }),
  );
}

export function getMujoco(): Promise<Mujoco> {
  if (!mujocoPromise) {
    mujocoPromise = (async () => {
      const mujoco = await loadMujoco();
      await mountAssets(mujoco);
      return mujoco;
    })();
  }
  return mujocoPromise;
}

export class Sim {
  readonly model: Model;
  data: Data;
  readonly siteId: number;
  readonly armDofs = NUM_JOINTS;

  constructor(private readonly mujoco: Mujoco, sceneXml: string) {
    mujoco.FS.writeFile("/work/scene.xml", sceneXml);
    this.model = mujoco.MjModel.from_xml_path("/work/scene.xml");
    this.data = new mujoco.MjData(this.model);
    this.siteId = this.model.site("gripperframe").id;
    this.reset();
  }

  /** Back to the exact start state the validator replays from. */
  reset(): void {
    this.data.delete();
    this.data = new this.mujoco.MjData(this.model);
    for (let j = 0; j < NUM_JOINTS; j++) {
      this.data.qpos[j] = HOME_POSE[j];
      this.data.ctrl[j] = HOME_POSE[j];
    }
    this.mujoco.mj_forward(this.model, this.data);
  }

  /** One control step: apply a float32-exact ctrl row, advance SUBSTEPS physics steps. */
  step(row: Float32Array): void {
    for (let j = 0; j < NUM_JOINTS; j++) this.data.ctrl[j] = row[j];
    for (let i = 0; i < SUBSTEPS; i++) this.mujoco.mj_step(this.model, this.data);
  }

  state(): number[] {
    return [...this.data.qpos, ...this.data.qvel];
  }

  arm(): number[] {
    return Array.from(this.data.qpos.slice(0, NUM_JOINTS));
  }

  tip(): [number, number, number] {
    const p = this.data.site_xpos;
    const i = 3 * this.siteId;
    return [p[i], p[i + 1], p[i + 2]];
  }

  bodyPos(name: string): [number, number, number] {
    const id = this.model.body(name).id;
    const p = this.data.xpos;
    return [p[3 * id], p[3 * id + 1], p[3 * id + 2]];
  }

  dispose(): void {
    this.data.delete();
    this.model.delete();
  }

  get raw(): Mujoco {
    return this.mujoco;
  }
}

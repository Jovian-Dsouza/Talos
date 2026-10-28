import { NUM_JOINTS } from "./constants";
import type { Sim } from "./sim";

// Damped least squares on pan, lift, elbow and wrist flex: the tool tip follows a 3D target while
// the jaw axis stays pointed down. Wrist roll and the gripper are set directly by the player.
const IK_JOINTS = 4;
const DAMPING = 1e-3;
const ORIENTATION_WEIGHT = 0.3;
const ITERATIONS = 4;
const DOWN = [0, 0, -1];

export class IkSolver {
  private readonly scratch: any;
  // The bindings write Jacobians into WASM-side buffers, not into plain typed arrays.
  private readonly jacpBuffer: any;
  private readonly jacrBuffer: any;
  private readonly lows: number[] = [];
  private readonly highs: number[] = [];

  constructor(private readonly sim: Sim) {
    this.scratch = new sim.raw.MjData(sim.model);
    this.jacpBuffer = new sim.raw.DoubleBuffer(3 * sim.model.nv);
    this.jacrBuffer = new sim.raw.DoubleBuffer(3 * sim.model.nv);
    for (let j = 0; j < IK_JOINTS; j++) {
      this.lows.push(sim.model.jnt_range[2 * j]);
      this.highs.push(sim.model.jnt_range[2 * j + 1]);
    }
  }

  /** Improve `q` (length 6) toward the target tip position; returns a new array. */
  solve(q: readonly number[], target: readonly [number, number, number]): number[] {
    const { raw, model } = this.sim;
    const next = [...q];
    const nv = model.nv;
    for (let iter = 0; iter < ITERATIONS; iter++) {
      for (let j = 0; j < NUM_JOINTS; j++) this.scratch.qpos[j] = next[j];
      raw.mj_forward(model, this.scratch);
      const s = 3 * this.sim.siteId;
      const err = [0, 0, 0].map((_, k) => target[k] - this.scratch.site_xpos[s + k]);
      const m = 9 * this.sim.siteId;
      const axis = [this.scratch.site_xmat[m], this.scratch.site_xmat[m + 3], this.scratch.site_xmat[m + 6]];
      const tilt = DOWN.map((d, k) => ORIENTATION_WEIGHT * (d - axis[k]));
      raw.mj_jacSite(model, this.scratch, this.jacpBuffer, this.jacrBuffer, this.sim.siteId);
      const jacp = this.jacpBuffer.GetView();
      const jacr = this.jacrBuffer.GetView();
      const jac: number[][] = [];
      for (let r = 0; r < 3; r++) jac.push(Array.from({ length: IK_JOINTS }, (_, c) => jacp[r * nv + c]));
      for (let r = 0; r < 3; r++) {
        // d(axis)/dq = omega x axis, so row r of the orientation Jacobian is -[axis]x * jacr
        jac.push(
          Array.from({ length: IK_JOINTS }, (_, c) => {
            const w = [jacr[c], jacr[nv + c], jacr[2 * nv + c]];
            const cross = [
              w[1] * axis[2] - w[2] * axis[1],
              w[2] * axis[0] - w[0] * axis[2],
              w[0] * axis[1] - w[1] * axis[0],
            ];
            return ORIENTATION_WEIGHT * cross[r];
          }),
        );
      }
      const delta = dampedStep(jac, [...err, ...tilt]);
      for (let j = 0; j < IK_JOINTS; j++) {
        next[j] = Math.min(this.highs[j], Math.max(this.lows[j], next[j] + delta[j]));
      }
    }
    return next;
  }

  dispose(): void {
    this.jacpBuffer.delete();
    this.jacrBuffer.delete();
    this.scratch.delete();
  }
}

/** dq = J^T (J J^T + damping I)^-1 e for a 6 x n Jacobian, solved by Gaussian elimination. */
function dampedStep(jac: number[][], err: number[]): number[] {
  const rows = jac.length;
  const cols = jac[0].length;
  const a: number[][] = jac.map((ri, i) =>
    jac.map((rj, j) => ri.reduce((sum, v, k) => sum + v * rj[k], 0) + (i === j ? DAMPING : 0)),
  );
  const b = [...err];
  for (let i = 0; i < rows; i++) {
    let pivot = i;
    for (let r = i + 1; r < rows; r++) if (Math.abs(a[r][i]) > Math.abs(a[pivot][i])) pivot = r;
    [a[i], a[pivot]] = [a[pivot], a[i]];
    [b[i], b[pivot]] = [b[pivot], b[i]];
    for (let r = i + 1; r < rows; r++) {
      const f = a[r][i] / a[i][i];
      for (let c = i; c < rows; c++) a[r][c] -= f * a[i][c];
      b[r] -= f * b[i];
    }
  }
  const y = new Array<number>(rows).fill(0);
  for (let i = rows - 1; i >= 0; i--) {
    let sum = b[i];
    for (let c = i + 1; c < rows; c++) sum -= a[i][c] * y[c];
    y[i] = sum / a[i][i];
  }
  return Array.from({ length: cols }, (_, c) => jac.reduce((sum, row, r) => sum + row[c] * y[r], 0));
}

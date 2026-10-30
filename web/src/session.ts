import { checkProgress, type Progress } from "./checker";
import {
  CHECKPOINT_EVERY,
  CONTROL_DT,
  GRIPPER_CLOSED,
  GRIPPER_OPEN,
  HOME_POSE,
  MAX_STEPS,
  MIN_STEPS,
} from "./constants";
import type { Controls } from "./controls";
import type { IkSolver } from "./ik";
import type { Sim } from "./sim";
import type { PracticeScene, Ticket } from "./types";

const MAX_TARGET_SPEED = 0.4; // m/s for the tip target
const MAX_JOINT_SPEED = 4.0; // rad/s per arm joint
const MAX_ROLL_SPEED = 4.0;
const MAX_GRIP_SPEED = 5.0;
const SETTLE_STEPS = 50; // one second of success before the page highlights Submit
const IK_WARMUP = 25;

const approach = (from: number, to: number, maxStep: number) =>
  from + Math.max(-maxStep, Math.min(maxStep, to - from));

export type Phase = "waiting" | "recording" | "full";

export class Session {
  readonly ctrl: Float32Array[] = [];
  readonly checkpoints: number[][] = [];
  q: number[] = [...HOME_POSE];
  private target: [number, number, number];
  private roll = 0;
  private grip: number = HOME_POSE[5];
  private accumulator = 0;
  private settled = 0;
  progress: Progress = { success: false, distance: Infinity };

  constructor(
    readonly sim: Sim,
    private readonly controls: Controls,
    private readonly ik: IkSolver,
    readonly ticket: Ticket | PracticeScene,
  ) {
    this.target = sim.tip();
    for (let i = 0; i < IK_WARMUP; i++) this.q = this.ik.solve(this.q, this.target);
    this.progress = checkProgress(sim, ticket.scene_spec);
  }

  get phase(): Phase {
    if (this.ctrl.length >= MAX_STEPS) return "full";
    return this.ctrl.length > 0 ? "recording" : "waiting";
  }

  get steps(): number {
    return this.ctrl.length;
  }

  get readyToSubmit(): boolean {
    return this.settled >= SETTLE_STEPS;
  }

  get canSubmit(): boolean {
    return this.ctrl.length >= MIN_STEPS;
  }

  currentTarget(): [number, number, number] {
    return this.target;
  }

  /** Advance by real elapsed seconds; the sim only moves once the player has acted. */
  tick(elapsedSeconds: number): void {
    this.accumulator = Math.min(this.accumulator + elapsedSeconds, 0.2);
    while (this.accumulator >= CONTROL_DT) {
      this.accumulator -= CONTROL_DT;
      if (this.ctrl.length >= MAX_STEPS) return;
      this.controls.advance(CONTROL_DT);
      const command = this.controls.snapshot();
      if (!command.active && this.ctrl.length === 0) continue;
      this.controlStep(command);
    }
  }

  private controlStep(command: ReturnType<Controls["snapshot"]>): void {
    const maxTarget = MAX_TARGET_SPEED * CONTROL_DT;
    this.target = [
      approach(this.target[0], command.x, maxTarget),
      approach(this.target[1], command.y, maxTarget),
      approach(this.target[2], command.z, maxTarget),
    ];
    const solved = this.ik.solve(this.q, this.target);
    const maxJoint = MAX_JOINT_SPEED * CONTROL_DT;
    this.q = this.q.map((value, j) => (j < 4 ? approach(value, solved[j], maxJoint) : value));
    this.roll = approach(this.roll, command.roll, MAX_ROLL_SPEED * CONTROL_DT);
    this.grip = approach(this.grip, command.gripClosed ? GRIPPER_CLOSED : GRIPPER_OPEN, MAX_GRIP_SPEED * CONTROL_DT);
    // Float32Array rounds each value once; the same rounded numbers are applied and recorded.
    const row = new Float32Array([this.q[0], this.q[1], this.q[2], this.q[3], this.roll, this.grip]);
    this.sim.step(row);
    this.ctrl.push(row);
    if (this.ctrl.length % CHECKPOINT_EVERY === 0) this.checkpoints.push(this.sim.state());
    this.progress = checkProgress(this.sim, this.ticket.scene_spec);
    this.settled = this.progress.success ? this.settled + 1 : 0;
  }

  bundle(contributor: string): Record<string, unknown> {
    if ("kind" in this.ticket) throw new Error("Practice runs stay in this browser.");
    return {
      ticket: this.ticket,
      mujoco_version: "3.17.0",
      model_hash: this.ticket.model_hash ?? "",
      control_dt: CONTROL_DT,
      contributor,
      reported_success: this.progress.success,
      ctrl: this.ctrl.map((row) => Array.from(row)),
      checkpoints: this.checkpoints,
      input_events: this.controls.events,
    };
  }
}

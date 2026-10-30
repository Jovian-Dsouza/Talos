import { HEIGHT_MAX, HEIGHT_MIN, REACH_MAX, REACH_MIN } from "./constants";
import type { InputEvent } from "./types";
import type { SceneView, ViewName } from "./view";

export interface Command {
  x: number;
  y: number;
  z: number;
  roll: number;
  gripClosed: boolean;
  /** True once the player has touched any control. */
  active: boolean;
}

const KEY_STEP = 0.0035;
const ROLL_LIMIT = 2.6;
const TILT_GAIN = 0.035; // rad of wrist roll per degree of phone tilt
const PLANAR_SPEED = 0.18; // m/s at full stick deflection
const VERTICAL_SPEED = 0.12; // m/s
const ROLL_SPEED = 2.5; // rad/s
const CONTROL_KEYS = new Set(["w", "a", "s", "d", "q", "e", "arrowleft", "arrowright", " "]);
const EVENT_INTERVAL_MS = 33;
const MAX_EVENTS = 20_000;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** Pull a target back inside the reachable workspace. */
export function clampWorkspace(x: number, y: number, z: number): { x: number; y: number; z: number } {
  const radius = Math.hypot(x, y);
  const scale = radius > 0 ? clamp(radius, REACH_MIN, REACH_MAX) / radius : 1;
  return { x: x * scale, y: y * scale, z: clamp(z, HEIGHT_MIN, HEIGHT_MAX) };
}

export type StickName = "move" | "lift";
interface StickValue {
  x: number;
  y: number;
}

export class Controls {
  private cmd: Command;
  private sticks: Record<StickName, StickValue> = { move: { x: 0, y: 0 }, lift: { x: 0, y: 0 } };
  private sticksOn = false;
  private readonly keys = new Set<string>();
  private tiltBase: number | null = null;
  private tiltOn = false;
  private lastEventMs = 0;
  readonly events: InputEvent[] = [];
  private startedAt = performance.now();

  constructor(private readonly canvas: HTMLCanvasElement, private readonly view: SceneView, start: { x: number; y: number; z: number }) {
    this.cmd = { ...start, roll: 0, gripClosed: false, active: false };
    this.bindPointer();
    window.addEventListener("keydown", (e) => {
      const key = e.key.toLowerCase();
      if (CONTROL_KEYS.has(key) && !(e.target instanceof HTMLInputElement)) this.keys.add(key);
    });
    window.addEventListener("keyup", (e) => {
      this.keys.delete(e.key.toLowerCase());
      if (e.key === " ") this.set({ gripClosed: false });
    });
  }

  /** Reset for a new attempt, keeping the same listeners. */
  restart(start: { x: number; y: number; z: number }): void {
    this.cmd = { ...start, roll: 0, gripClosed: false, active: false };
    this.events.length = 0;
    this.startedAt = performance.now();
    this.tiltBase = null;
  }

  /** Joystick mode: one finger on the main view orbits the camera instead of steering the gripper. */
  useSticks(on: boolean): void {
    this.sticksOn = on;
  }

  /** Stick input as x right, y up, each -1..1. The move stick is camera relative. */
  setStick(name: StickName, x: number, y: number): void {
    this.sticks = { ...this.sticks, [name]: { x, y } };
    if (x !== 0 || y !== 0) this.set({ active: true });
  }

  /** Apply the held sticks for one control step of `dt` seconds. */
  advance(dt: number): void {
    const { move, lift } = this.sticks;
    if (move.x === 0 && move.y === 0 && lift.x === 0 && lift.y === 0) return;
    const { forward, right } = this.view.groundAxes();
    const planar = PLANAR_SPEED * dt;
    const x = this.cmd.x + (forward.x * move.y + right.x * move.x) * planar;
    const y = this.cmd.y + (forward.y * move.y + right.y * move.x) * planar;
    const target = clampWorkspace(x, y, this.cmd.z + lift.y * VERTICAL_SPEED * dt);
    const roll = clamp(this.cmd.roll + lift.x * ROLL_SPEED * dt, -ROLL_LIMIT, ROLL_LIMIT);
    this.set({ ...target, roll, active: true });
    this.log("joy", target.x, target.y, target.z);
  }

  snapshot(): Command {
    this.applyKeys();
    return { ...this.cmd };
  }

  setHeight(z: number): void {
    this.set({ z: clamp(z, HEIGHT_MIN, HEIGHT_MAX), active: true });
    this.log("height", undefined, undefined, z);
  }

  setGrip(closed: boolean): void {
    this.set({ gripClosed: closed, active: true });
    this.log("grip", undefined, undefined, closed ? 1 : 0);
  }

  /** iOS requires a user gesture and permission before tilt events arrive. */
  async enableTilt(): Promise<boolean> {
    const Orientation = DeviceOrientationEvent as unknown as { requestPermission?: () => Promise<string> };
    if (typeof Orientation.requestPermission === "function") {
      if ((await Orientation.requestPermission()) !== "granted") return false;
    }
    if (!this.tiltOn) {
      window.addEventListener("deviceorientation", (e) => this.onTilt(e));
      this.tiltOn = true;
    }
    return true;
  }

  set(patch: Partial<Command>): void {
    this.cmd = { ...this.cmd, ...patch };
  }

  private bindPointer(): void {
    let dragView: ViewName | null = null;
    const move = (e: PointerEvent) => {
      if (dragView === null) return;
      const hit = this.view.targetFrom(dragView, e.clientX, e.clientY, this.cmd);
      if (!hit) return;
      const target = clampWorkspace(hit.x, hit.y, hit.z);
      this.set({ ...target, active: true });
      this.log("ptr", target.x, target.y);
    };
    this.canvas.addEventListener("pointerdown", (e) => {
      // Left button moves the gripper; right and middle belong to the camera.
      if (e.button !== 0 || !e.isPrimary) return;
      dragView = this.view.viewAt(e.clientX, e.clientY);
      if (this.sticksOn && e.pointerType === "touch" && dragView === "main") {
        dragView = null; // the camera takes this touch
        return;
      }
      this.canvas.setPointerCapture(e.pointerId);
      move(e);
    });
    this.canvas.addEventListener("pointermove", (e) => {
      if (e.isPrimary) move(e);
    });
    for (const type of ["pointerup", "pointercancel"]) this.canvas.addEventListener(type, () => (dragView = null));
  }

  private applyKeys(): void {
    if (this.keys.size === 0) return;
    let { x, y, z, roll } = this.cmd;
    if (this.keys.has("w")) x += KEY_STEP;
    if (this.keys.has("s")) x -= KEY_STEP;
    if (this.keys.has("a")) y += KEY_STEP;
    if (this.keys.has("d")) y -= KEY_STEP;
    if (this.keys.has("e")) z += KEY_STEP;
    if (this.keys.has("q")) z -= KEY_STEP;
    if (this.keys.has("arrowleft")) roll -= 0.03;
    if (this.keys.has("arrowright")) roll += 0.03;
    const radius = Math.hypot(x, y);
    const scale = radius > 0 ? clamp(radius, REACH_MIN, REACH_MAX) / radius : 1;
    const closed = this.cmd.gripClosed || this.keys.has(" ");
    this.set({
      x: x * scale,
      y: y * scale,
      z: clamp(z, HEIGHT_MIN, HEIGHT_MAX),
      roll: clamp(roll, -ROLL_LIMIT, ROLL_LIMIT),
      gripClosed: closed,
      active: true,
    });
    this.log("key", x, y);
  }

  private onTilt(e: DeviceOrientationEvent): void {
    if (e.gamma === null) return;
    if (this.tiltBase === null) this.tiltBase = e.gamma;
    const roll = clamp((e.gamma - this.tiltBase) * TILT_GAIN, -ROLL_LIMIT, ROLL_LIMIT);
    this.set({ roll, active: this.cmd.active });
    this.log("tilt", undefined, undefined, e.gamma);
  }

  private log(kind: string, x?: number, y?: number, v?: number): void {
    const now = performance.now();
    if (now - this.lastEventMs < EVENT_INTERVAL_MS || this.events.length >= MAX_EVENTS) return;
    this.lastEventMs = now;
    this.events.push({ t: Math.round(now - this.startedAt), kind, x, y, v });
  }
}

import { TABLE_Z } from "./constants";
import type { InputEvent } from "./types";
import type { SceneView } from "./view";

export interface Command {
  x: number;
  y: number;
  z: number;
  roll: number;
  gripClosed: boolean;
  /** True once the player has touched any control. */
  active: boolean;
}

const REACH_MIN = 0.1;
const REACH_MAX = 0.3;
const HEIGHT_MIN = 0.012;
const HEIGHT_MAX = 0.16;
const KEY_STEP = 0.0035;
const ROLL_LIMIT = 2.6;
const TILT_GAIN = 0.035; // rad of wrist roll per degree of phone tilt
const EVENT_INTERVAL_MS = 33;
const MAX_EVENTS = 20_000;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export class Controls {
  private cmd: Command;
  private readonly keys = new Set<string>();
  private tiltBase: number | null = null;
  private tiltOn = false;
  private lastEventMs = 0;
  readonly events: InputEvent[] = [];
  private startedAt = performance.now();

  constructor(private readonly canvas: HTMLCanvasElement, private readonly view: SceneView, start: { x: number; y: number; z: number }) {
    this.cmd = { ...start, roll: 0, gripClosed: false, active: false };
    this.bindPointer();
    window.addEventListener("keydown", (e) => this.keys.add(e.key.toLowerCase()));
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
    const move = (e: PointerEvent) => {
      const hit = this.view.pointOnPlane(e.clientX, e.clientY, this.cmd.z + TABLE_Z);
      if (!hit) return;
      const radius = Math.hypot(hit.x, hit.y);
      const scale = radius > 0 ? clamp(radius, REACH_MIN, REACH_MAX) / radius : 1;
      this.set({ x: hit.x * scale, y: hit.y * scale, active: true });
      this.log("ptr", hit.x, hit.y);
    };
    this.canvas.addEventListener("pointerdown", (e) => {
      this.canvas.setPointerCapture(e.pointerId);
      move(e);
    });
    this.canvas.addEventListener("pointermove", (e) => {
      if (e.buttons !== 0 || e.pointerType === "touch") move(e);
    });
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

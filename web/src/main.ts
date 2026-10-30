import { fetchLeaderboard, fetchTicket, submitBundle, waitForVerdict } from "./api";
import { EXPLORER_URL, POOL_URL, POOL_URLS } from "./config";
import { HEIGHT_MAX, HEIGHT_MIN } from "./constants";
import { Controls } from "./controls";
import { IkSolver } from "./ik";
import { Session } from "./session";
import { getMujoco, Sim } from "./sim";
import type { LeaderboardEntry, Verdict } from "./types";
import { SceneView } from "./view";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const canvas = $<HTMLCanvasElement>("stage");
const view = new SceneView(canvas, { top: $("inset-top"), side: $("inset-side") });

let sim: Sim | null = null;
let ik: IkSolver | null = null;
let controls: Controls | null = null;
let session: Session | null = null;
let contributor = "anonymous";
let submitting = false;
let lastFrame = performance.now();

function show(id: string, visible: boolean): void {
  $(id).hidden = !visible;
}

function setStatus(text: string, ok = false): void {
  const chip = $("status");
  chip.textContent = text;
  chip.classList.toggle("ok", ok);
}

function cleanup(): void {
  ik?.dispose();
  sim?.dispose();
  ik = sim = session = null;
}

async function beginRound(): Promise<void> {
  cleanup();
  const [mujoco, ticket] = await Promise.all([getMujoco(), fetchTicket(POOL_URL, "put_cube_in_bowl")]);
  sim = new Sim(mujoco, ticket.scene_xml);
  view.build(sim);
  ik = new IkSolver(sim);
  const tip = sim.tip();
  const start = { x: tip[0], y: tip[1], z: tip[2] };
  if (controls) controls.restart(start);
  else controls = new Controls(canvas, view, start);
  session = new Session(sim, controls, ik, ticket);
  $("instruction").textContent = ticket.instruction;
  $<HTMLInputElement>("height").value = String(Math.min(HEIGHT_MAX, Math.max(HEIGHT_MIN, tip[2])));
  setStatus("Touch the scene to begin");
  $<HTMLButtonElement>("submit").disabled = true;
  show("intro", false);
  show("result", false);
  show("hud", true);
  show("dock", true);
  show("insets", true);
  submitting = false;
}

function replayAttempt(): void {
  if (!sim || !session || !controls || !ik) return;
  sim.reset();
  const tip = sim.tip();
  controls.restart({ x: tip[0], y: tip[1], z: tip[2] });
  session = new Session(sim, controls, ik, session.ticket);
  setStatus("Touch the scene to begin");
  $<HTMLButtonElement>("submit").disabled = true;
}

function frame(now: number): void {
  const dt = (now - lastFrame) / 1000;
  lastFrame = now;
  if (sim && session && !submitting) {
    session.tick(dt);
    const [tx, ty, tz] = session.currentTarget();
    view.setMarker(tx, ty, tz);
    $("timer").textContent = `${(session.steps * 0.02).toFixed(1)} s`;
    if (session.phase === "full") setStatus("Time limit reached, submit or reset");
    else if (session.readyToSubmit) setStatus("Cube is in the bowl. Submit when ready.", true);
    else if (session.phase === "recording") setStatus("Recording");
    $<HTMLButtonElement>("submit").disabled = !session.canSubmit;
    syncHeightSlider();
  }
  if (sim) view.update(sim);
  view.render();
  requestAnimationFrame(frame);
}

function syncHeightSlider(): void {
  // Dragging in the side view changes the height, so keep the slider showing it.
  const slider = $<HTMLInputElement>("height");
  if (controls && document.activeElement !== slider) slider.value = String(controls.snapshot().z);
}

function metric(label: string, value: string): string {
  return `<dt>${label}</dt><dd>${value}</dd>`;
}

function renderVerdict(verdict: Verdict): void {
  const title = $("verdict-title");
  title.textContent = verdict.accepted ? "Verified" : "Not accepted";
  title.className = verdict.accepted ? "good" : "bad";
  $("verdict-detail").textContent = verdict.accepted
    ? "Validators replayed your run and it checks out."
    : `Reason: ${verdict.reason}`;
  $("metrics").innerHTML = verdict.accepted
    ? metric("Replay", "matches") +
      metric("Task", verdict.success ? "completed" : "failed") +
      metric("Quality", verdict.quality.toFixed(2)) +
      metric("Novelty", verdict.novelty.toFixed(2)) +
      metric("Score", verdict.score.toFixed(2))
    : metric("Task", verdict.success ? "completed" : "not completed");
}

function renderLeaderboards(boards: LeaderboardEntry[][]): void {
  const list = $("leaderboard");
  const merged = boards[0] ?? [];
  list.innerHTML = merged
    .slice(0, 8)
    .map((e) => `<li><strong>${escapeHtml(e.contributor)}</strong>: ${e.value.toFixed(2)} (${e.accepted}/${e.submitted} accepted)</li>`)
    .join("") || "<li>No scores yet</li>";
  const totals = boards.map((b) => b.reduce((sum, e) => sum + e.value, 0));
  $("pools").textContent =
    boards.length > 1 ? totals.map((t, i) => `Pool ${i + 1}: ${t.toFixed(2)}`).join("   ") : "";
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);
}

async function submit(): Promise<void> {
  if (!session || submitting) return;
  submitting = true;
  show("dock", false);
  show("insets", false);
  show("result", true);
  $("verdict-title").textContent = "Sending your run...";
  $("verdict-title").className = "";
  $("verdict-detail").textContent = "A validator will replay it in the same physics engine.";
  $("metrics").innerHTML = "";
  $("leaderboard").innerHTML = "";
  $("pools").textContent = "";
  try {
    const { bundle_id } = await submitBundle(POOL_URL, session.bundle(contributor));
    $("verdict-title").textContent = "Waiting for validators...";
    const verdict = await waitForVerdict(POOL_URL, bundle_id);
    renderVerdict(verdict);
    const boards = await Promise.all(POOL_URLS.map((url) => fetchLeaderboard(url).catch(() => [])));
    renderLeaderboards(boards);
    const link = $<HTMLAnchorElement>("explorer");
    link.hidden = !EXPLORER_URL;
    if (EXPLORER_URL) link.href = EXPLORER_URL;
  } catch (error) {
    $("verdict-title").textContent = "Something went wrong";
    $("verdict-title").className = "bad";
    $("verdict-detail").textContent = error instanceof Error ? error.message : String(error);
  }
}

function bindUi(): void {
  const start = $<HTMLButtonElement>("start");
  start.addEventListener("click", async () => {
    const nickname = $<HTMLInputElement>("nickname").value.trim() || `player-${Math.floor(Math.random() * 9000 + 1000)}`;
    const wallet = $<HTMLInputElement>("wallet").value.trim();
    contributor = wallet ? `${nickname} (${wallet})` : nickname;
    start.disabled = true;
    try {
      await beginRound();
    } catch (error) {
      $("intro-error").textContent = `Could not start: ${error instanceof Error ? error.message : String(error)}`;
      start.disabled = false;
    }
  });
  $("again").addEventListener("click", () => void beginRound().catch((e) => ($("verdict-detail").textContent = String(e))));
  $("reset").addEventListener("click", replayAttempt);
  $("submit").addEventListener("click", () => void submit());
  $<HTMLInputElement>("height").addEventListener("input", (e) => controls?.setHeight(Number((e.target as HTMLInputElement).value)));
  const grip = $("grip");
  const press = (closed: boolean) => {
    grip.classList.toggle("on", closed);
    controls?.setGrip(closed);
  };
  grip.addEventListener("pointerdown", (e) => {
    grip.setPointerCapture(e.pointerId);
    press(true);
  });
  for (const type of ["pointerup", "pointercancel"]) grip.addEventListener(type, () => press(false));
  const tilt = $<HTMLButtonElement>("tilt");
  if ("DeviceOrientationEvent" in window && navigator.maxTouchPoints > 0) tilt.hidden = false;
  tilt.addEventListener("click", async () => {
    const granted = await controls?.enableTilt();
    tilt.textContent = granted ? "Tilt on" : "Tilt blocked";
    tilt.disabled = !!granted;
  });
  canvas.addEventListener("dblclick", () => view.resetCamera());
  window.addEventListener("resize", () => view.resize());
}

bindUi();
requestAnimationFrame(frame);
if (new URLSearchParams(window.location.search).has("debug")) {
  // Test hook for automated browser runs: lets a script read the live session and view.
  Object.assign(window, { teach: { session: () => session, view, controls: () => controls } });
}
getMujoco()
  .then(() => {
    const start = $<HTMLButtonElement>("start");
    start.disabled = false;
    start.textContent = "Start";
  })
  .catch((error) => {
    $("intro-error").textContent = `Simulator failed to load: ${error instanceof Error ? error.message : String(error)}`;
  });

import { fetchLeaderboard, fetchTasks, fetchTicket, submitBundle, waitForVerdict } from "./api";
import { EXPLORER_URL, POOL_URL, POOL_URLS } from "./config";
import { CONTROL_DT, HEIGHT_MAX, HEIGHT_MIN } from "./constants";
import { Controls } from "./controls";
import { canFullscreen, enterFullscreen, exitFullscreen, haptic, isCoarsePointer, keepAwake, toggleFullscreen } from "./device";
import { IkSolver } from "./ik";
import { buildSlotLabels } from "./labels";
import { Joystick } from "./joystick";
import { Session } from "./session";
import { getMujoco, Sim } from "./sim";
import { TASKS, taskInfo, type TaskInfo } from "./tasks";
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
let sticksOn = false;
let task: TaskInfo = TASKS[0];
let lastFrame = performance.now();
let frameAverage = 1 / 60;
let slowSeconds = 0;

const SLOW_FRAME_S = 0.035; // drop shadows when frames stay slower than ~28 fps
const SLOW_LIMIT_S = 2;

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
  const [mujoco, ticket] = await Promise.all([getMujoco(), fetchTicket(POOL_URL, task.id)]);
  sim = new Sim(mujoco, ticket.scene_xml);
  view.build(sim);
  view.setDecor(buildSlotLabels(sim, ticket.scene_spec));
  ik = new IkSolver(sim);
  const tip = sim.tip();
  const start = { x: tip[0], y: tip[1], z: tip[2] };
  if (controls) controls.restart(start);
  else controls = new Controls(canvas, view, start);
  controls.useSticks(sticksOn);
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
  keepAwake(true);
}

function renderTasks(offered: readonly TaskInfo[]): void {
  const list = $("tasks");
  list.replaceChildren();
  const cards = offered.map((info) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "task";
    card.setAttribute("role", "radio");
    for (const [tag, text] of [["em", info.industry], ["strong", info.title], ["span", info.blurb]] as const) {
      const part = document.createElement(tag);
      part.textContent = text;
      card.append(part);
    }
    card.addEventListener("click", () => {
      task = info;
      for (const other of cards) other.setAttribute("aria-checked", String(other === card));
    });
    return card;
  });
  const first = offered.find((info) => info.id === task.id) ?? offered[0];
  task = first;
  cards.forEach((card, i) => card.setAttribute("aria-checked", String(offered[i] === first)));
  list.append(...cards);
}

/** Offer the tasks the pool serves, in its order; fall back to the full catalog if it cannot say. */
async function loadTasks(): Promise<void> {
  try {
    const served = await fetchTasks(POOL_URL);
    const offered = served.map(taskInfo).filter((info, i) => info.id === served[i]);
    renderTasks(offered.length > 0 ? offered : TASKS);
  } catch (error) {
    console.debug("pool did not list tasks", error);
    renderTasks(TASKS);
  }
}

function backToIntro(): void {
  cleanup();
  keepAwake(false);
  void exitFullscreen();
  closeHudMenu();
  for (const id of ["result", "hud", "dock", "insets"]) show(id, false);
  show("intro", true);
  $<HTMLButtonElement>("start").disabled = false;
}

function closeHudMenu(): void {
  if (!isCoarsePointer()) return;
  const panel = $("hud-menu-panel");
  const toggle = $<HTMLButtonElement>("hud-menu");
  panel.hidden = true;
  toggle.setAttribute("aria-expanded", "false");
}

function toggleHudMenu(): void {
  const panel = $("hud-menu-panel");
  const toggle = $<HTMLButtonElement>("hud-menu");
  const open = panel.hidden;
  panel.hidden = !open;
  toggle.setAttribute("aria-expanded", String(open));
}

function syncHudMenu(): void {
  const menu = $<HTMLButtonElement>("hud-menu");
  const exit = $<HTMLButtonElement>("hud-exit");
  const panel = $("hud-menu-panel");
  const coarse = isCoarsePointer();
  menu.hidden = !coarse;
  exit.hidden = !coarse;
  panel.hidden = coarse;
}

function setSticks(on: boolean): void {
  sticksOn = on;
  document.body.classList.toggle("touch", on);
  $("sticks-toggle").setAttribute("aria-pressed", String(on));
  controls?.useSticks(on);
  view.setTouchOrbit(on);
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
  frameAverage += (Math.min(dt, 0.25) - frameAverage) * 0.05;
  slowSeconds = frameAverage > SLOW_FRAME_S ? slowSeconds + dt : 0;
  if (slowSeconds > SLOW_LIMIT_S) view.setShadows(false);
  if (sim && session && !submitting) {
    session.tick(dt);
    const [tx, ty, tz] = session.currentTarget();
    view.setMarker(tx, ty, tz);
    $("timer").textContent = `${(session.steps * CONTROL_DT).toFixed(1)} s`;
    if (session.phase === "full") setStatus("Time limit reached, submit or reset");
    else if (session.readyToSubmit) setStatus(task.done, true);
    else if (session.phase === "recording") setStatus("Recording");
    $<HTMLButtonElement>("submit").disabled = !session.canSubmit;
    const menuSubmit = document.querySelector<HTMLButtonElement>('[data-for="submit"]');
    if (menuSubmit) menuSubmit.disabled = !session.canSubmit;
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
  keepAwake(false);
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
    if (isCoarsePointer()) void enterFullscreen();
    start.disabled = true;
    try {
      await beginRound();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const tunnelHint =
        message === "Failed to fetch" &&
        (POOL_URL.startsWith("http://127.0.0.1") || POOL_URL.endsWith("/pool"))
          ? " Make sure practice.py (or the miner) is running on port 8091. For two tunnels, use the URL from scripts/demo/tunnels.sh."
          : "";
      $("intro-error").textContent = `Could not start: ${message}${tunnelHint}`;
      start.disabled = false;
    }
  });
  $("switch").addEventListener("click", backToIntro);
  $("again").addEventListener("click", () => {
    if (isCoarsePointer()) void enterFullscreen();
    void beginRound().catch((e) => ($("verdict-detail").textContent = String(e)));
  });
  $("reset").addEventListener("click", replayAttempt);
  $("submit").addEventListener("click", () => void submit());
  $<HTMLInputElement>("height").addEventListener("input", (e) => controls?.setHeight(Number((e.target as HTMLInputElement).value)));
  const grip = $("grip");
  let gripClosed = false;
  const press = (closed: boolean) => {
    gripClosed = closed;
    grip.classList.toggle("on", closed);
    grip.textContent = sticksOn ? (closed ? "Release" : "Grip") : "Hold to grip";
    controls?.setGrip(closed);
  };
  grip.addEventListener("pointerdown", (e) => {
    grip.setPointerCapture(e.pointerId);
    // Thumbs are busy on the sticks, so touch toggles the grip; a mouse holds it.
    if (sticksOn && e.pointerType === "touch") {
      haptic();
      press(!gripClosed);
    } else press(true);
  });
  for (const type of ["pointerup", "pointercancel"]) {
    grip.addEventListener(type, (e) => {
      if (!(sticksOn && (e as PointerEvent).pointerType === "touch")) press(false);
    });
  }
  new Joystick($("stick-move"), (x, y) => controls?.setStick("move", x, y));
  new Joystick($("stick-lift"), (x, y) => controls?.setStick("lift", x, y));
  $("sticks-toggle").addEventListener("click", () => {
    setSticks(!sticksOn);
    press(false);
  });
  $("camera").addEventListener("click", () => ($("camera").textContent = `Cam: ${view.cyclePreset()}`));
  $("views").addEventListener("click", () => {
    const collapsed = $("insets").classList.toggle("collapsed");
    $("views").setAttribute("aria-pressed", String(!collapsed));
  });
  const fullscreen = $("fullscreen");
  fullscreen.hidden = !canFullscreen();
  fullscreen.addEventListener("click", () => void toggleFullscreen());
  $<HTMLButtonElement>("hud-exit").addEventListener("click", () => void exitFullscreen());
  $<HTMLButtonElement>("hud-menu").addEventListener("click", (event) => {
    event.stopPropagation();
    toggleHudMenu();
  });
  for (const proxy of document.querySelectorAll<HTMLButtonElement>("[data-for]")) {
    proxy.addEventListener("click", () => {
      $(proxy.dataset.for!).click();
      closeHudMenu();
    });
  }
  document.addEventListener("click", (event) => {
    if ($("hud-menu-panel").hidden) return;
    const target = event.target as Node;
    if ($("hud-menu-panel").contains(target) || $("hud-menu").contains(target) || $("hud-exit").contains(target)) return;
    closeHudMenu();
  });
  setSticks(isCoarsePointer());
  syncHudMenu();
  window.matchMedia("(pointer: coarse)").addEventListener("change", () => syncHudMenu());
  press(false);
  const tilt = $<HTMLButtonElement>("tilt");
  if ("DeviceOrientationEvent" in window && navigator.maxTouchPoints > 0) tilt.hidden = false;
  tilt.addEventListener("click", async () => {
    const granted = await controls?.enableTilt();
    tilt.textContent = granted ? "Tilt on" : "Tilt blocked";
    tilt.disabled = !!granted;
  });
  canvas.addEventListener("dblclick", () => {
    view.resetCamera();
    $("camera").textContent = "Cam: Front";
  });
  window.addEventListener("resize", () => view.resize());
}

bindUi();
void loadTasks();
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

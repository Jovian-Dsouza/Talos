import { fetchLeaderboard, fetchMe, fetchProgress, fetchTasks, fetchTicket, submitBundle, waitForVerdict } from "./api";
import { authAvailable, initAuth, onAuthChange, playerName, signIn, signOut } from "./auth";
import { EXPLORER_URL, POOL_URL } from "./config";
import { CONTROL_DT, HEIGHT_MAX, HEIGHT_MIN } from "./constants";
import { Controls } from "./controls";
import { canFullscreen, enterFullscreen, exitFullscreen, haptic, isCoarsePointer, keepAwake, toggleFullscreen } from "./device";
import { escapeHtml } from "./format";
import { link } from "./header";
import { IkSolver } from "./ik";
import { buildSlotLabels } from "./labels";
import { Joystick } from "./joystick";
import { loadStanding, refreshLiveStrip, renderBests, renderPlayer } from "./play/lobby";
import { setJourney, showReward } from "./play/result";
import { Session } from "./session";
import { getMujoco, Sim } from "./sim";
import { TASKS, taskInfo, type TaskInfo } from "./tasks";
import type { LeaderboardEntry, Me, Progress, Verdict } from "./types";
import { points, reasonLabel, seconds } from "./words";
import { SceneView } from "./view";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const canvas = $<HTMLCanvasElement>("stage");
const view = new SceneView(canvas, { top: $("inset-top"), side: $("inset-side") });

let sim: Sim | null = null;
let ik: IkSolver | null = null;
let controls: Controls | null = null;
let session: Session | null = null;
let me: Me | null = null;
let progress: Progress | null = null;
let simReady = false;
let submitting = false;
let sticksOn = false;
let task: TaskInfo = TASKS[0];
let lastFrame = performance.now();
let frameAverage = 1 / 60;
let slowSeconds = 0;

const SLOW_FRAME_S = 0.035; // drop shadows when frames stay slower than ~28 fps
const SLOW_LIMIT_S = 2;
const ME_POLL_MS = 4000;
const LOBBY_POLL_MS = 15_000;

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
  const [mujoco, ticket] = await Promise.all([getMujoco(), fetchTicket(task.id)]);
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
    card.dataset.task = info.id;
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
  renderBests(progress);
}

/** Offer the tasks the pool serves, in its order; fall back to the full catalog if it cannot say. */
async function loadTasks(): Promise<void> {
  try {
    const served = await fetchTasks();
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
  updateStartButton();
  void refreshLobby();
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
    ? "A validator replayed your run step by step and it checks out. It is now part of the dataset."
    : `${reasonLabel(verdict.reason)}. Rejected runs earn nothing, so try another run.`;
  $("metrics").innerHTML = verdict.accepted
    ? metric("Replay", "matches") +
      metric("Time", `${seconds(verdict.duration_s)} (${points(verdict.time_score)} of 100)`) +
      metric("Smoothness", `${points(verdict.smooth_score)} of 100`) +
      metric("Score", `${points(verdict.score)} of 100`)
    : metric("Task", verdict.success ? "completed" : "not completed");
}

function renderLeaderboard(entries: LeaderboardEntry[]): void {
  const list = $("leaderboard");
  list.innerHTML =
    entries
      .slice(0, 8)
      .map((e) => {
        const rank = e.uid === undefined ? "" : ` <small>UID ${e.uid}</small>`;
        return `<li><strong>${escapeHtml(e.contributor)}</strong>${rank}: ${points(e.value)} points (${e.accepted} of ${e.submitted} verified)</li>`;
      })
      .join("") || "<li>No scores yet</li>";
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
  const before = progress;
  setJourney("sending");
  showReward(null, null, false);
  try {
    const { bundle_id, registration } = await submitBundle(session.bundle(playerName() ?? ""));
    setJourney("waiting");
    $("verdict-title").textContent = "Waiting for a validator...";
    if (registration !== "registered") {
      $("verdict-detail").textContent = "Your miner is still being registered on the subnet. Validators score this run as soon as it is.";
    }
    const verdict = await waitForVerdict(bundle_id);
    setJourney(verdict.accepted ? "accepted" : "rejected");
    renderVerdict(verdict);
    const after = await fetchProgress().catch(() => null);
    showReward(before, after, verdict.accepted);
    progress = after ?? progress;
    renderLeaderboard(await fetchLeaderboard().catch(() => []));
    const link = $<HTMLAnchorElement>("explorer");
    link.hidden = !EXPLORER_URL;
    if (EXPLORER_URL) link.href = EXPLORER_URL;
  } catch (error) {
    setJourney("failed");
    $("verdict-title").textContent = "Something went wrong";
    $("verdict-title").className = "bad";
    $("verdict-detail").textContent = error instanceof Error ? error.message : String(error);
  }
}

function updateStartButton(): void {
  const start = $<HTMLButtonElement>("start");
  if (!simReady) {
    start.disabled = true;
    start.textContent = "Loading simulator...";
    return;
  }
  const signedIn = playerName() !== null;
  start.disabled = !signedIn;
  start.textContent = signedIn ? "Start" : "Sign in to start";
}

function minerLine(name: string): string {
  if (!me) return `Signed in as ${name}.`;
  if (me.registration === "registered") return `${name}: miner UID ${me.uid} on subnet ${me.netuid}`;
  if (me.registration === "failed") return `${name}: miner registration failed. ${me.registration_note}`;
  return `${name}: registering your miner on the subnet...`;
}

function renderAccount(): void {
  const name = playerName();
  $("sign-in").hidden = name !== null || !authAvailable;
  $("sign-out").hidden = name === null;
  $("account-line").textContent = !authAvailable
    ? "Sign-in is not configured on this build."
    : name === null
      ? ""
      : minerLine(name);
  $("tasks").hidden = name === null;
  updateStartButton();
}

async function refreshMe(): Promise<void> {
  if (playerName() === null) me = null;
  else me = await fetchMe().catch(() => me);
  renderAccount();
}

/** Level, XP, goal and earnings for the signed-in player, plus bests on the task cards. */
async function refreshLobby(): Promise<void> {
  const name = playerName();
  const standing = name === null ? { progress: null, wallet: null } : await loadStanding();
  progress = standing.progress ?? (name === null ? null : progress);
  renderPlayer(name, { ...standing, progress });
  renderBests(progress);
}

function bindUi(): void {
  $("sign-in").addEventListener("click", signIn);
  $("sign-out").addEventListener("click", () => void signOut().then(() => refreshMe()));
  const start = $<HTMLButtonElement>("start");
  start.addEventListener("click", async () => {
    if (isCoarsePointer()) void enterFullscreen();
    start.disabled = true;
    try {
      await beginRound();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const tunnelHint =
        message === "Failed to fetch" &&
        (POOL_URL.startsWith("http://127.0.0.1") || POOL_URL.endsWith("/pool"))
          ? " Make sure the backend is running and reachable."
          : "";
      $("intro-error").textContent = `Could not start: ${message}${tunnelHint}`;
      updateStartButton();
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
void refreshLiveStrip();
for (const anchor of document.querySelectorAll<HTMLAnchorElement>("a[data-link]")) {
  anchor.href = link(anchor.getAttribute("href") ?? "/");
}
requestAnimationFrame(frame);
if (new URLSearchParams(window.location.search).has("debug")) {
  // Test hook for automated browser runs: lets a script read the live session and view.
  Object.assign(window, { teach: { session: () => session, view, controls: () => controls } });
}
initAuth()
  .then(() => {
    onAuthChange(() => {
      void refreshMe();
      void refreshLobby();
    });
    void refreshMe();
    void refreshLobby();
    window.setInterval(() => {
      if (!$("intro").hidden) void refreshMe();
    }, ME_POLL_MS);
    window.setInterval(() => {
      if (!$("intro").hidden) {
        void refreshLobby();
        void refreshLiveStrip();
      }
    }, LOBBY_POLL_MS);
  })
  .catch((error) => {
    $("intro-error").textContent = `Sign-in failed to load: ${error instanceof Error ? error.message : String(error)}`;
  });
getMujoco()
  .then(() => {
    simReady = true;
    updateStartButton();
  })
  .catch((error) => {
    $("intro-error").textContent = `Simulator failed to load: ${error instanceof Error ? error.message : String(error)}`;
  });

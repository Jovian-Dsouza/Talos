// Recorded RoboJev attempts: a video, the scores it was given every 0.5 s, and the frames behind each score.
type AttemptName = "success" | "failure";
interface ScorePoint { t: number; p: number; frames: number[]; }
interface Attempt { video: string; duration: number; points: ScorePoint[]; }
interface Traces { fps: number; attempts: Record<AttemptName, Attempt>; }

const TRACES_URL = "/media/robojev/traces.json";
const FRAME_DIR = "/media/robojev/frames";
const PLOT = { left: 8, width: 284, bottom: 72, height: 64 };
const LIKELY = 0.5;
const COMPLETE = 0.8;
const UNCERTAIN = 0.2;

/** Index of the latest score at or before `time`, or -1 before the first one. */
function sampleAt(points: readonly ScorePoint[], time: number): number {
  let low = 0;
  let high = points.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (points[middle].t <= time + 1e-6) low = middle + 1;
    else high = middle;
  }
  return low - 1;
}

function stepPath(points: readonly ScorePoint[], index: number, time: number, duration: number): string {
  if (index < 0) return "";
  const x = (t: number): string => (PLOT.left + (PLOT.width * t) / duration).toFixed(2);
  const y = (p: number): string => (PLOT.bottom - PLOT.height * p).toFixed(2);
  let path = `M${x(points[0].t)},${y(points[0].p)}`;
  for (let i = 1; i <= index; i++) path += `H${x(points[i].t)}V${y(points[i].p)}`;
  return `${path}H${x(Math.max(points[index].t, Math.min(time, duration)))}`;
}

const verdictFor = (p: number): string => (p >= COMPLETE ? "Likely complete" : p >= UNCERTAIN ? "Uncertain" : "Not yet");

export async function mountRoboJev(): Promise<void> {
  const root = document.getElementById("robojev");
  if (!root) return;
  const $ = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;
  const video = $<HTMLVideoElement>("rj-video");
  const play = $<HTMLButtonElement>("rj-play");
  const seek = $<HTMLInputElement>("rj-seek");
  const path = document.getElementById("rj-trace-path")!;
  const dot = document.getElementById("rj-trace-dot")!;
  const thumbnails = [...document.querySelectorAll<HTMLImageElement>("#rj-frames img")];
  const buttons = [...root.querySelectorAll<HTMLButtonElement>(".rj-tabs [data-attempt]")];
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");

  let traces: Traces;
  try {
    const response = await fetch(TRACES_URL);
    if (!response.ok) throw new Error(`Trace request failed: ${response.status}`);
    traces = (await response.json()) as Traces;
  } catch (error) {
    console.error("RoboJev trace unavailable", error);
    $("rj-verdict").textContent = "Replay unavailable";
    $("rj-frame-note").textContent = "The recorded scores could not be loaded. The video still plays.";
    return;
  }

  let name: AttemptName = "success";
  let index = -2;
  let dragging = false;
  video.controls = false;
  $("rj-playback").hidden = false;

  const render = (): void => {
    const attempt = traces.attempts[name];
    const time = Math.max(0, Math.min(video.currentTime || 0, attempt.duration));
    const current = sampleAt(attempt.points, time);
    const point = current >= 0 ? attempt.points[current] : undefined;
    if (!dragging) seek.value = String(time);
    $("rj-time").textContent = `${time.toFixed(1)} / ${attempt.duration.toFixed(1)} s`;
    seek.setAttribute("aria-valuetext", `${time.toFixed(1)} of ${attempt.duration.toFixed(1)} seconds`);
    play.textContent = video.paused ? "Play" : "Pause";
    play.setAttribute("aria-label", video.paused ? "Play the recorded attempt" : "Pause the recorded attempt");
    path.setAttribute("d", stepPath(attempt.points, current, time, attempt.duration));
    root.dataset.likely = String(!!point && point.p >= LIKELY);
    dot.style.display = point ? "" : "none";
    if (point) {
      dot.setAttribute("cx", (PLOT.left + (PLOT.width * time) / attempt.duration).toFixed(2));
      dot.setAttribute("cy", (PLOT.bottom - PLOT.height * point.p).toFixed(2));
    }
    if (index === current) return;
    index = current;
    $("rj-probability").textContent = point ? point.p.toFixed(2) : "—";
    $("rj-verdict").textContent = point ? verdictFor(point.p) : "Waiting for frames";
    $("rj-sample-time").textContent = point ? `Scored at ${point.t.toFixed(1)} s` : "First score at 0.5 s";
    $("rj-frame-note").textContent = point ? "RoboJev used these ten front-camera frames for this score." : "Play the attempt to see the frames RoboJev uses.";
    thumbnails.forEach((image, i) => {
      image.src = `${FRAME_DIR}/${name}-${point ? point.frames[i] : 0}.webp`;
      image.alt = point ? `Input ${i + 1} of 10, at ${(point.frames[i] / traces.fps).toFixed(2)} seconds` : "First frame of the attempt";
    });
  };

  const select = (next: AttemptName): void => {
    name = next;
    index = -2;
    root.dataset.attempt = name;
    video.src = traces.attempts[name].video;
    video.poster = `/media/robojev/${name}-poster.webp`;
    video.setAttribute("aria-label", `Recorded ${name === "success" ? "successful" : "failed"} ring-on-peg attempt with measured scores over time`);
    seek.max = String(traces.attempts[name].duration);
    for (const button of buttons) button.setAttribute("aria-pressed", String(button.dataset.attempt === name));
    render();
    if (!reduced.matches) void video.play().catch(render);
  };

  for (const button of buttons) button.addEventListener("click", () => select(button.dataset.attempt as AttemptName));
  play.addEventListener("click", () => { if (video.paused) void video.play().catch(render); else video.pause(); });
  seek.addEventListener("input", () => { dragging = true; video.currentTime = Number(seek.value); render(); });
  seek.addEventListener("change", () => { dragging = false; render(); });
  for (const event of ["timeupdate", "seeked", "play", "pause", "loadedmetadata", "ended"]) video.addEventListener(event, render);
  reduced.addEventListener("change", (event) => { if (event.matches) video.pause(); });
  if (reduced.matches) video.pause();
  select("success");
  if ("requestVideoFrameCallback" in video) {
    const frame = (): void => { render(); video.requestVideoFrameCallback(frame); };
    video.requestVideoFrameCallback(frame);
  }
}

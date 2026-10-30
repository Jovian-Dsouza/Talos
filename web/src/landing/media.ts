import type { RobotDemo } from "./robot-demo";
import type { JointName, JointState } from "./joints";

/** The arm loads automatically while the film plays behind its transparent viewport. */
export function mountHeroMedia(): void {
  const video = document.getElementById("robot-film") as HTMLVideoElement;
  const toggle = document.getElementById("film-toggle") as HTMLButtonElement;
  const demoPanel = document.getElementById("demo-panel")!;
  const controls = document.getElementById("demo-controls")!;
  const status = document.getElementById("demo-status")!;
  const retry = document.getElementById("demo-retry") as HTMLButtonElement;
  const canvas = document.getElementById("robot-demo") as HTMLCanvasElement;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  let manuallyPaused = false;
  let manuallyPlaying = false;
  let inView = false;
  let loading = false;
  let demo: RobotDemo | undefined;

  video.muted = true;
  video.defaultMuted = true;
  video.autoplay = !reduced.matches;
  const syncPlayback = (): void => {
    const playing = !document.hidden && inView && !manuallyPaused && (!reduced.matches || manuallyPlaying);
    if (playing) void video.play().catch(() => { updateVideoButton(); });
    else video.pause();
    demo?.setActive(inView && !document.hidden);
  };
  const updateVideoButton = (): void => {
    const label = video.paused ? "Play background video" : "Pause background video";
    toggle.textContent = video.paused ? "▷" : "Ⅱ";
    toggle.setAttribute("aria-label", label);
    toggle.title = label;
  };
  video.addEventListener("play", updateVideoButton);
  video.addEventListener("pause", updateVideoButton);
  video.addEventListener("error", () => { toggle.hidden = true; });
  toggle.addEventListener("click", () => {
    manuallyPaused = !video.paused;
    manuallyPlaying = video.paused;
    if (video.paused) void video.play().catch(() => { toggle.title = "Background video unavailable"; });
    else video.pause();
  });
  reduced.addEventListener("change", () => { manuallyPlaying = false; syncPlayback(); updateVideoButton(); });
  document.addEventListener("visibilitychange", syncPlayback);
  const observer = new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; syncPlayback(); });
  observer.observe(demoPanel);

  const syncSliders = (pose: JointState): void => {
    for (const input of controls.querySelectorAll<HTMLInputElement>("[data-joint]")) {
      input.value = String(pose[input.dataset.joint as JointName]);
      document.getElementById(`${input.id}-value`)!.textContent = `${Math.round(Number(input.value))}°`;
    }
  };
  const loadDemo = async (): Promise<void> => {
    if (demo || loading) return;
    loading = true;
    retry.hidden = true;
    status.hidden = false;
    status.textContent = "Loading the robot arm…";
    demoPanel.setAttribute("aria-busy", "true");
    try {
      const { RobotDemo } = await import("./robot-demo");
      demo = new RobotDemo(canvas);
      await demo.load();
      status.hidden = true;
      controls.hidden = false;
      syncPlayback();
    } catch {
      demo?.dispose();
      demo = undefined;
      status.textContent = "The 3D model could not be opened. Try again, or explore a task on the Play page.";
      retry.hidden = false;
    } finally {
      loading = false;
      demoPanel.removeAttribute("aria-busy");
    }
  };
  retry.addEventListener("click", () => void loadDemo());
  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    demo?.dispose();
    demo = undefined;
    controls.hidden = true;
    status.hidden = false;
    status.textContent = "The 3D view was interrupted. Retry to reopen the model.";
    retry.hidden = false;
  });
  for (const button of controls.querySelectorAll<HTMLButtonElement>("[data-pose]")) button.addEventListener("click", () => {
    if (!demo) return;
    syncSliders(demo.setPose(button.dataset.pose!));
    controls.querySelectorAll("[data-pose]").forEach((other) => other.setAttribute("aria-pressed", String(other === button)));
  });
  for (const input of controls.querySelectorAll<HTMLInputElement>("[data-joint]")) input.addEventListener("input", () => {
    demo?.setJoint(input.dataset.joint as JointName, Number(input.value));
    document.getElementById(`${input.id}-value`)!.textContent = `${input.value}°`;
    controls.querySelectorAll("[data-pose]").forEach((button) => button.setAttribute("aria-pressed", "false"));
  });
  document.getElementById("demo-reset")!.addEventListener("click", () => demo?.resetView());
  for (const button of controls.querySelectorAll<HTMLButtonElement>("[data-view]")) button.addEventListener("click", () => demo?.changeView(button.dataset.view!));
  window.addEventListener("pagehide", (event) => {
    if (event.persisted) return;
    observer.disconnect();
    demo?.dispose();
  });
  window.addEventListener("pageshow", syncPlayback);
  syncPlayback();
  updateVideoButton();
  void loadDemo();
}

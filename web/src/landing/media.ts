import type { RobotDemo } from "./robot-demo";
import type { JointName, JointState } from "./joints";

/** Video and demo share one viewport; neither runs when its panel is hidden. */
export function mountHeroMedia(): void {
  const video = document.getElementById("robot-film") as HTMLVideoElement;
  const toggle = document.getElementById("film-toggle") as HTMLButtonElement;
  const filmTab = document.getElementById("film-tab") as HTMLButtonElement;
  const demoTab = document.getElementById("demo-tab") as HTMLButtonElement;
  const filmPanel = document.getElementById("film-panel")!;
  const demoPanel = document.getElementById("demo-panel")!;
  const controls = document.getElementById("demo-controls")!;
  const status = document.getElementById("demo-status")!;
  const retry = document.getElementById("demo-retry") as HTMLButtonElement;
  const canvas = document.getElementById("robot-demo") as HTMLCanvasElement;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  let manuallyPaused = false;
  let manuallyPlaying = false;
  let demoSelected = false;
  let inView = true;
  let loading = false;
  let demo: RobotDemo | undefined;

  video.muted = true;
  video.defaultMuted = true;
  video.autoplay = !reduced.matches;
  const syncPlayback = (): void => {
    const playing = !demoSelected && !document.hidden && inView && !manuallyPaused && (!reduced.matches || manuallyPlaying);
    if (playing) void video.play().catch(() => { toggle.textContent = "Play video"; });
    else video.pause();
    demo?.setActive(demoSelected && inView && !document.hidden);
  };
  const updateVideoButton = () => { toggle.textContent = video.paused ? "Play video" : "Pause video"; };
  video.addEventListener("play", updateVideoButton);
  video.addEventListener("pause", updateVideoButton);
  video.addEventListener("error", () => { toggle.hidden = true; });
  toggle.addEventListener("click", () => {
    manuallyPaused = !video.paused;
    manuallyPlaying = video.paused;
    if (video.paused) void video.play().catch(() => { toggle.textContent = "Video unavailable"; });
    else video.pause();
  });
  reduced.addEventListener("change", () => { manuallyPlaying = false; syncPlayback(); updateVideoButton(); });
  document.addEventListener("visibilitychange", syncPlayback);
  const observer = new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; syncPlayback(); });
  observer.observe(filmPanel.closest("figure")!);

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
    status.textContent = "Loading the robot model…";
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
  const select = (showDemo: boolean): void => {
    demoSelected = showDemo;
    filmPanel.hidden = showDemo;
    demoPanel.hidden = !showDemo;
    filmTab.setAttribute("aria-selected", String(!showDemo));
    demoTab.setAttribute("aria-selected", String(showDemo));
    filmTab.tabIndex = showDemo ? -1 : 0;
    demoTab.tabIndex = showDemo ? 0 : -1;
    document.getElementById("media-description")!.textContent = showDemo ? "Interactive model preview / no sign-in needed" : "Teleoperation reference footage";
    syncPlayback();
    if (showDemo) void loadDemo();
  };
  filmTab.addEventListener("click", () => select(false));
  demoTab.addEventListener("click", () => select(true));
  for (const tab of [filmTab, demoTab]) tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const nextDemo = event.key === "Home" ? false : event.key === "End" ? true : !demoSelected;
    select(nextDemo);
    (nextDemo ? demoTab : filmTab).focus();
  });
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
}

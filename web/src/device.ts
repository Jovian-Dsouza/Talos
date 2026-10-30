// Phone features that may be missing or refused. Each helper is best effort: a failure is logged at
// debug level and the app carries on without the feature.

export function haptic(ms = 15): void {
  navigator.vibrate?.(ms);
}

export const canFullscreen = (): boolean => document.fullscreenEnabled === true;

type LockableOrientation = ScreenOrientation & { lock?: (orientation: string) => Promise<void> };

export async function toggleFullscreen(): Promise<void> {
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }
    await document.documentElement.requestFullscreen();
    await (screen.orientation as LockableOrientation).lock?.("landscape");
  } catch (error) {
    console.debug("fullscreen or orientation lock not available", error);
  }
}

let sentinel: WakeLockSentinel | null = null;
let wanted = false;

async function acquire(): Promise<void> {
  if (!wanted || sentinel || !navigator.wakeLock) return;
  try {
    sentinel = await navigator.wakeLock.request("screen");
    sentinel.addEventListener("release", () => (sentinel = null));
  } catch (error) {
    console.debug("screen wake lock refused", error);
  }
}

/** Keep the screen on while a run is being recorded; the lock is dropped when the tab is hidden. */
export function keepAwake(on: boolean): void {
  wanted = on;
  if (on) void acquire();
  else {
    void sentinel?.release();
    sentinel = null;
  }
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") void acquire();
});

// Result card: the run's journey through the network (uploaded, replayed, verified, in the dataset)
// and what it earned in the game (XP, level ups, new badges, rank).
import { escapeHtml } from "../format";
import { nextLevelText, rankText } from "../progress-view";
import type { Progress } from "../types";

export type Journey = "sending" | "waiting" | "accepted" | "rejected" | "failed";

const COUNT_UP_MS = 700;

type Step = [label: string, classes: string];

function steps(journey: Journey): Step[] {
  switch (journey) {
    case "sending": return [["Uploading", "now"], ["Replay", ""], ["Verdict", ""], ["Dataset", ""]];
    case "waiting": return [["Uploaded", "done"], ["Replaying", "now"], ["Verdict", ""], ["Dataset", ""]];
    case "accepted": return [["Uploaded", "done"], ["Replayed", "done"], ["Verified", "done ok"], ["In the dataset", "done ok"]];
    case "rejected": return [["Uploaded", "done"], ["Replayed", "done"], ["Rejected", "fail"], ["Not added", ""]];
    case "failed": return [["Not sent", "fail"], ["Replay", ""], ["Verdict", ""], ["Dataset", ""]];
  }
}

export function setJourney(journey: Journey): void {
  const list = document.getElementById("journey") as HTMLElement;
  list.innerHTML = steps(journey).map(([label, classes]) => `<li class="${classes}">${label}</li>`).join("");
}

function countUp(el: HTMLElement, target: number): void {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    el.textContent = `+${target} XP`;
    return;
  }
  const started = performance.now();
  const tick = (now: number) => {
    const share = Math.min(1, (now - started) / COUNT_UP_MS);
    el.textContent = `+${Math.round(target * (1 - (1 - share) ** 3))} XP`;
    if (share < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

/** Show what a verified run earned, comparing progress from before the run with after it. */
export function showReward(before: Progress | null, after: Progress | null, accepted: boolean): void {
  const box = document.getElementById("reward") as HTMLElement;
  const gained = after?.history.at(-1)?.xp ?? 0;
  if (!after || !accepted || gained === 0) {
    box.hidden = true;
    return;
  }
  const levelUp = before !== null && after.level > before.level
    ? `<span class="level-up">Level up: you are now level ${after.level}, ${escapeHtml(after.title)}.</span> ` : "";
  const fresh = after.badges.filter((b) => b.earned && !before?.badges.some((old) => old.id === b.id && old.earned));
  box.innerHTML = `<div class="gain">+0 XP</div>
    <p>${levelUp}${nextLevelText(after)}. Rank ${rankText(after)}.</p>
    ${fresh.length ? `<ul aria-label="New badges">${fresh.map((b) => `<li>${escapeHtml(b.title)}</li>`).join("")}</ul>` : ""}`;
  box.hidden = false;
  countUp(box.querySelector(".gain") as HTMLElement, gained);
}

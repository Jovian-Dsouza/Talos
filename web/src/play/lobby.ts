// Play lobby: the signed-in player's strip (level, XP, daily goal, streak, earnings), personal
// bests on the task cards, and one line about what the network is doing right now.
import { fetchActivity, fetchProgress, fetchWallet } from "../api";
import { escapeHtml } from "../format";
import { link } from "../header";
import { levelShare, rankText } from "../progress-view";
import type { Progress, Wallet } from "../types";
import { amount, pluralize, points } from "../words";

const RING_RADIUS = 18;
const RING = 2 * Math.PI * RING_RADIUS;

export interface Standing {
  progress: Progress | null;
  wallet: Wallet | null;
}

export async function loadStanding(): Promise<Standing> {
  const [progress, wallet] = await Promise.all([fetchProgress().catch(() => null), fetchWallet().catch(() => null)]);
  return { progress, wallet };
}

function goalRing(done: number, goal: number): string {
  const share = Math.min(1, done / goal) * RING;
  return `<div class="goal" title="Today's goal: ${goal} verified runs">
    <svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true">
      <circle cx="22" cy="22" r="${RING_RADIUS}" fill="none" stroke="var(--line)" stroke-width="5" />
      <circle cx="22" cy="22" r="${RING_RADIUS}" fill="none" stroke="var(--hazard)" stroke-width="5" stroke-linecap="round"
        stroke-dasharray="${share} ${RING - share}" /></svg>
    <b>${Math.min(done, goal)}/${goal}</b><span class="sr">verified runs today</span></div>`;
}

export function renderPlayer(name: string | null, standing: Standing): void {
  const el = document.getElementById("player") as HTMLElement;
  const p = standing.progress;
  if (name === null || p === null) {
    el.hidden = true;
    return;
  }
  const streak = p.streak_days ? `${pluralize(p.streak_days, "day")} streak` : "No streak yet";
  const earned = standing.wallet
    ? `<a class="chip-earned" href="${link("/wallet")}" title="Your wallet"><span class="mark" aria-hidden="true">τ</span>${amount(standing.wallet.earned_tao)}<span class="sr"> TAO earned</span></a>`
    : "";
  el.innerHTML = `<span class="avatar" aria-hidden="true">${escapeHtml(name.slice(0, 1).toUpperCase())}</span>
    <div class="who"><strong>${escapeHtml(name)}</strong><span>Level ${p.level}, ${escapeHtml(p.title)}</span>
      <div class="xp-mini" title="${p.xp} XP"><span style="width:${Math.round(levelShare(p) * 100)}%"></span></div></div>
    ${goalRing(p.daily.done, p.daily.goal)}
    <div class="player-facts"><span>${streak}, rank ${rankText(p)}</span>${earned}</div>`;
  el.hidden = false;
}

/** Tag each task card with the player's best score on it. */
export function renderBests(progress: Progress | null): void {
  for (const card of document.querySelectorAll<HTMLElement>(".task[data-task]")) {
    const best = progress?.bests.find((b) => b.task_id === card.dataset.task);
    let tag = card.querySelector<HTMLElement>("small.best");
    if (!best) {
      tag?.remove();
      continue;
    }
    if (!tag) {
      tag = document.createElement("small");
      tag.className = "best";
      card.prepend(tag);
    }
    tag.textContent = `Best ${points(best.score)}`;
  }
}

export async function refreshLiveStrip(): Promise<void> {
  const el = document.getElementById("live-strip") as HTMLElement;
  try {
    const { summary } = await fetchActivity();
    el.textContent = `${summary.playing_now} playing now, ${pluralize(summary.validating_now, "validator")} replaying runs, ${pluralize(summary.episodes, "episode")} in the datasets`;
    el.hidden = false;
  } catch {
    el.hidden = true;
  }
}

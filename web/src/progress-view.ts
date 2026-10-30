// The player's game progress (level, XP, streak, badges), shared by the wallet page and the play lobby.
import { escapeHtml } from "./format";
import type { Progress } from "./types";
import { count } from "./words";

/** Share of the way from this level to the next, 0..1 (1 at the top level). */
export function levelShare(p: Progress): number {
  if (p.next_xp === null) return 1;
  return Math.min(1, (p.xp - p.level_xp) / (p.next_xp - p.level_xp));
}

export function nextLevelText(p: Progress): string {
  return p.next_xp === null
    ? `${count(p.xp)} XP, the top level`
    : `${count(p.xp)} XP, ${count(p.next_xp - p.xp)} more to level ${p.level + 1}`;
}

export function xpBar(p: Progress): string {
  const share = Math.round(levelShare(p) * 100);
  return `<div class="xp" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${share}"
    aria-label="Progress to the next level"><span style="width:${share}%"></span></div>`;
}

export function rankText(p: Progress): string {
  return p.rank === null ? "Unranked" : `#${p.rank} of ${count(p.players)}`;
}

export function badgeList(p: Progress): string {
  return `<ul class="badges">${p.badges.map((b) =>
    `<li class="badge${b.earned ? " earned" : ""}"><strong>${escapeHtml(b.title)}</strong><span>${escapeHtml(b.detail)}</span></li>`).join("")}</ul>`;
}

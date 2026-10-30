// Wallet page: what the player's miner has earned, their addresses, progress, badges and runs.
import { fetchProgress, fetchWallet } from "./api";
import { authAvailable, playerName, signIn } from "./auth";
import { columns, type Series } from "./charts/bars";
import { sparkline } from "./charts/spark";
import { escapeHtml } from "./format";
import { mountHeader } from "./header";
import { badgeList, nextLevelText, rankText, xpBar } from "./progress-view";
import type { Progress, Wallet } from "./types";
import { amount, count, points, reasonLabel, taskTitle } from "./words";

const POLL_MS = 15_000;
const REJECTED_STUB = 4; // a rejected run has no score; draw a short stub so it still shows up
const RUN_SERIES: Series[] = [
  { key: "accepted", label: "Verified run score", color: "var(--nitrile)" },
  { key: "rejected", label: "Rejected (no score)", color: "var(--rejected)" },
];
const REGISTRATION: Record<Wallet["registration"], string> = {
  pending: "Queued for registration",
  funding: "Funding your miner",
  registering: "Registering on the subnet",
  registered: "Registered",
  failed: "Registration failed",
};
const $ = (id: string) => document.getElementById(id) as HTMLElement;

function earningsText(w: Wallet): string {
  if (w.registration !== "registered") {
    return "Your miner is being registered on the subnet. Earnings start after your first verified runs.";
  }
  if (w.staked_alpha === 0) {
    return "Earnings start after your first verified runs: validators weigh miners each tempo and the subnet pays out in alpha.";
  }
  const rate = w.tao_per_day ? ` At the current rate that is about ${amount(w.tao_per_day)} TAO a day.` : "";
  return `Your miner holds ${amount(w.staked_alpha)} alpha on ${escapeHtml(w.subnet_name ?? "the subnet")}, worth ${amount(w.alpha_price)} TAO each today.${rate}`;
}

function keyRow(label: string, value: string, copyable = true): string {
  const copy = copyable ? `<button type="button" class="copy" data-copy="${escapeHtml(value)}">Copy</button>` : "";
  return `<div><dt>${label}</dt><dd><span class="${copyable ? "mono" : ""}" title="${escapeHtml(value)}">${escapeHtml(value)}</span>${copy}</dd></div>`;
}

function renderWallet(w: Wallet): void {
  $("wallet-meta").textContent = `${w.subnet_name ?? "Subnet"} on netuid ${w.netuid}`;
  $("earned").innerHTML = `${amount(w.earned_tao)}<small>TAO earned</small>`;
  $("earned-detail").innerHTML = earningsText(w);
  $("earned-chart").innerHTML = sparkline(w.history.map((s) => s.tao), "Earned TAO over time");
  $("keys").innerHTML =
    keyRow("Wallet address (coldkey)", w.coldkey) +
    keyRow("Miner key (hotkey)", w.hotkey) +
    keyRow("Miner", w.uid === null ? REGISTRATION[w.registration] : `UID ${w.uid}, ${REGISTRATION[w.registration].toLowerCase()}`, false) +
    keyRow("Free balance", `${amount(w.free_tao)} TAO`, false);
}

function renderProgress(p: Progress): void {
  $("progress").innerHTML = `<div class="level"><strong>Level ${p.level}</strong><span>${escapeHtml(p.title)}</span></div>
    ${xpBar(p)}<p class="muted small" style="margin:0">${nextLevelText(p)}</p>
    <dl class="facts">
      <div><dt>Streak</dt><dd>${count(p.streak_days)} ${p.streak_days === 1 ? "day" : "days"}</dd></div>
      <div><dt>Today</dt><dd>${p.daily.done >= p.daily.goal ? `${count(p.daily.done)}, goal met` : `${count(p.daily.done)} of ${count(p.daily.goal)}`}</dd></div>
      <div><dt>Rank</dt><dd>${rankText(p)}</dd></div>
    </dl>`;
  $("badges").innerHTML = badgeList(p);
  $("runs").innerHTML = p.history.length
    ? columns(p.history.map((run, i) => ({
        label: i === 0 ? "oldest" : i === p.history.length - 1 ? "latest" : null,
        title: `${taskTitle(run.task_id)}: ${run.accepted ? `score ${points(run.score)}, +${run.xp} XP` : reasonLabel(run.reason)}`,
        values: run.accepted ? { accepted: Math.round(run.score * 100), rejected: 0 } : { accepted: 0, rejected: REJECTED_STUB },
      })), RUN_SERIES, "Score of each of your recent runs")
    : `<p class="empty">No runs yet. Finish a task on the Play page and it shows up here.</p>`;
}

async function refresh(): Promise<void> {
  try {
    const [wallet, progress] = await Promise.all([fetchWallet(), fetchProgress()]);
    renderWallet(wallet);
    renderProgress(progress);
    $("wallet").hidden = false;
    $("wallet-error").textContent = "";
  } catch (error) {
    $("wallet-error").textContent = `Your wallet could not be loaded: ${error instanceof Error ? error.message : String(error)}. Retrying.`;
  }
}

document.addEventListener("click", (event) => {
  const button = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-copy]");
  if (!button) return;
  navigator.clipboard.writeText(button.dataset.copy ?? "").then(
    () => (button.textContent = "Copied"),
    () => (button.textContent = "Select and copy"),
  );
});

async function start(): Promise<void> {
  await mountHeader("wallet");
  if (playerName() === null) {
    $("gate").hidden = false;
    const button = $("gate-sign-in") as HTMLButtonElement;
    button.hidden = !authAvailable;
    button.addEventListener("click", signIn);
    return;
  }
  await refresh();
  window.setInterval(() => void refresh(), POLL_MS);
}

void start();

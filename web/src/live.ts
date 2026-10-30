// Live page: the conveyor, totals, outcome and time charts, rejection reasons, the run feed,
// and the miner and validator tables.
import { fetchActivity, fetchNetwork } from "./api";
import { columns, rows, type Column, type Series } from "./charts/bars";
import { Conveyor } from "./charts/conveyor";
import { donut } from "./charts/donut";
import { EXPLORER_URL } from "./config";
import { jobItem } from "./feed";
import { escapeHtml, shorten } from "./format";
import { mountHeader } from "./header";
import type { Activity, Network } from "./types";
import { count, pluralize, points, reasonLabel, seconds, taskTitle } from "./words";

const ACTIVITY_POLL_MS = 3000;
const NETWORK_POLL_MS = 10_000;
const OUTCOMES: Series[] = [
  { key: "accepted", label: "Verified", color: "var(--verified)" },
  { key: "rejected", label: "Rejected", color: "var(--rejected)" },
  { key: "queued", label: "Waiting", color: "var(--waiting)" },
];
const FEED_ITEMS = 12;
const REJECTED: Series[] = [{ key: "count", label: "Rejected runs", color: "var(--rejected)" }];

const $ = (id: string) => document.getElementById(id) as HTMLElement;
const conveyor = new Conveyor($("conveyor"));
let windowName: Activity["window"] = "1h";

function cell(label: string, value: string, note: string): string {
  return `<div><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`;
}

function renderReadout(a: Activity): void {
  const s = a.summary;
  $("readout").innerHTML =
    cell("Miners", count(s.miners_registered), `${count(s.miners_active)} active today`) +
    cell("Validators", count(s.validators_on_chain), `${count(s.validating_now)} validating now`) +
    cell("Runs submitted", count(s.runs), pluralize(a.pipeline.queued, "waiting", "waiting")) +
    cell("Motion collected", seconds(s.demo_seconds), pluralize(s.episodes, "verified episode")) +
    cell("Chain block", count(a.block), `subnet ${a.netuid}`);
}

function timeLabel(epoch: number, withMinutes: boolean): string {
  const date = new Date(epoch * 1000);
  return date.toLocaleTimeString([], withMinutes ? { hour: "2-digit", minute: "2-digit" } : { hour: "2-digit" });
}

function renderTimeline(a: Activity): void {
  const { buckets, bucket_seconds: size } = a.timeline;
  const every = Math.ceil(buckets.length / 4);
  const data: Column[] = buckets.map((b, i) => ({
    label: i % every === 0 ? timeLabel(b.start, size < 3600) : null,
    title: `${timeLabel(b.start, true)} to ${timeLabel(b.start + size, true)}`,
    values: { accepted: b.accepted, rejected: b.rejected, queued: b.queued },
  }));
  $("timeline").innerHTML = columns(data, OUTCOMES, `Runs submitted per ${size / 60} minutes, by outcome`);
}

function renderCharts(a: Activity): void {
  const p = a.pipeline;
  const judged = p.accepted + p.rejected;
  $("outcomes").innerHTML = donut(
    OUTCOMES.map((s) => ({ label: s.label, value: p[s.key as keyof typeof p], color: s.color })),
    judged ? `${Math.round((p.accepted / judged) * 100)}%` : "-",
    "of judged runs verified",
  );
  renderTimeline(a);
  $("reasons").innerHTML = a.reasons.length
    ? rows(a.reasons.map((r) => ({ label: reasonLabel(r.reason), values: { count: r.count } })), REJECTED, "Rejected runs by reason")
    : `<p class="empty">No rejected runs. Every run so far replayed cleanly.</p>`;
  $("tasks").innerHTML = a.tasks.length
    ? rows(a.tasks.map((t) => ({ label: taskTitle(t.task_id), values: { accepted: t.accepted, rejected: t.rejected, queued: t.queued } })), OUTCOMES, "Runs by task and outcome")
    : `<p class="empty">No runs yet. Pick a task on the Play page to start one.</p>`;
}

function renderActivity(a: Activity): void {
  $("meta").textContent = `${a.subnet_name ?? "Subnet"} on netuid ${a.netuid}, block ${count(a.block)}`;
  conveyor.update(a);
  renderReadout(a);
  renderCharts(a);
  $("feed").innerHTML = a.jobs.slice(0, FEED_ITEMS).map(jobItem).join("") || `<li class="empty">No runs yet. The first one shows up here within seconds.</li>`;
}

function hotkeyCell(hotkey: string): string {
  return EXPLORER_URL
    ? `<a class="mono" href="${EXPLORER_URL}/${hotkey}" target="_blank" rel="noreferrer">${shorten(hotkey)}</a>`
    : `<span class="mono">${shorten(hotkey)}</span>`;
}

function renderNetwork(net: Network): void {
  $("miners").innerHTML = net.miners.map((m) => `<tr><td>${m.uid}</td><td>${escapeHtml(m.contributor)}</td>
      <td class="num">${m.accepted} of ${m.submitted}</td><td class="num">${points(m.value)}</td>
      <td class="num">${(m.incentive * 100).toFixed(1)}%</td></tr>`).join("")
    || `<tr><td colspan="5" class="muted">No miners yet. Sign in on the Play page to become the first.</td></tr>`;
  $("validators").innerHTML = net.validators.map((v) => {
    const root = v.root
      ? `<span class="mono">${v.root.root.slice(0, 16)}...</span> <span class="muted">epoch ${v.root.epoch}</span>`
      : `<span class="muted">none yet</span>`;
    return `<tr><td>${v.uid}</td><td>${hotkeyCell(v.hotkey)}</td><td>${root}</td></tr>`;
  }).join("") || `<tr><td colspan="3" class="muted">No validator online.</td></tr>`;
}

async function pollActivity(): Promise<void> {
  try {
    renderActivity(await fetchActivity(windowName));
  } catch (error) {
    $("meta").textContent = `Cannot reach the subnet right now (${error instanceof Error ? error.message : String(error)}). Retrying.`;
  }
}

async function pollNetwork(): Promise<void> {
  try {
    renderNetwork(await fetchNetwork());
  } catch (error) {
    console.warn("network tables unavailable", error);
  }
}

for (const button of document.querySelectorAll<HTMLButtonElement>("[data-window]")) {
  button.addEventListener("click", () => {
    windowName = button.dataset.window as Activity["window"];
    for (const other of document.querySelectorAll("[data-window]")) other.setAttribute("aria-pressed", String(other === button));
    void pollActivity();
  });
}

void mountHeader("live");
void pollActivity();
void pollNetwork();
window.setInterval(() => void pollActivity(), ACTIVITY_POLL_MS);
window.setInterval(() => void pollNetwork(), NETWORK_POLL_MS);

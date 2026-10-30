// Datasets page: one card per task dataset with a 96-well plate of its latest runs, and an
// episode browser filtered by task.
import { fetchDatasets, fetchEpisodes } from "./api";
import { miniBars } from "./charts/spark";
import { ago, escapeHtml } from "./format";
import { mountHeader } from "./header";
import { taskInfo, TASKS } from "./tasks";
import type { Dataset, Datasets, Job } from "./types";
import { count, points, seconds, STAGE_LABEL, taskTitle } from "./words";

const WELLS = 96;
const POLL_MS = 15_000;
const $ = (id: string) => document.getElementById(id) as HTMLElement;
let filter: string | null = null;
let next: number | null = null;

function well(job: Job | undefined): string {
  if (!job) return `<span class="well"></span>`;
  const title = escapeHtml(`${job.contributor}, ${STAGE_LABEL[job.stage].toLowerCase()}${job.stage === "accepted" ? `, score ${points(job.score)}` : ""}`);
  if (job.stage === "accepted") {
    return `<span class="well filled" style="--fill:${Math.round(30 + job.score * 70)}%" title="${title}"></span>`;
  }
  return `<span class="well" title="${title}">${job.stage === "rejected" ? "✕" : ""}</span>`;
}

function card(d: Dataset, recent: Job[]): string {
  const known = TASKS.some((t) => t.id === d.task_id);
  const days = d.per_day.map((day) => ({
    value: day.episodes,
    title: `${new Date(day.day * 1000).toLocaleDateString([], { month: "short", day: "numeric" })}: ${day.episodes}`,
  }));
  const link = d.link
    ? `<a href="${escapeHtml(d.link)}" target="_blank" rel="noreferrer">Open on Hugging Face</a>`
    : `<span class="muted">Not published to Hugging Face yet</span>`;
  return `<article class="panel dataset">
    <header><p>${known ? escapeHtml(taskInfo(d.task_id).industry) : "Task"}</p><h2>${escapeHtml(taskTitle(d.task_id))}</h2></header>
    <dl>
      <div><dt>Episodes</dt><dd>${count(d.episodes)}</dd></div>
      <div><dt>Motion</dt><dd>${seconds(d.seconds)}</dd></div>
      <div><dt>Contributors</dt><dd>${count(d.contributors)}</dd></div>
    </dl>
    <div class="plate" role="img" aria-label="${escapeHtml(`Last ${recent.length} runs: ${recent.filter((j) => j.stage === "accepted").length} verified`)}">
      ${Array.from({ length: WELLS }, (_, i) => well(recent[i])).join("")}</div>
    <p class="plate-note">One well per run, newest first. Filled wells were verified, darker means a higher score, and ✕ marks a rejected run.</p>
    <div><p class="muted small" style="margin:0 0 6px">Verified episodes per day, last two weeks</p>${miniBars(days, "Verified episodes per day")}</div>
    <footer><span>Average score ${points(d.average_score)}, best ${points(d.best_score)}${d.updated_at ? `, last added ${ago(d.updated_at)}` : ""}</span>${link}</footer>
  </article>`;
}

async function renderDatasets(): Promise<Datasets> {
  const data = await fetchDatasets();
  const recent = await Promise.all(data.datasets.map((d) => fetchEpisodes(d.task_id, null, WELLS).catch(() => ({ episodes: [], next: null }))));
  $("format").textContent = `Every verified run is added to the dataset for its task. Exports are ${data.format} files for the ${data.robot} arm at ${data.fps} fps, with ${data.cameras.join(" and ")} camera video.`;
  $("datasets").innerHTML = data.datasets.map((d, i) => card(d, recent[i].episodes)).join("")
    || `<p class="empty">No datasets yet. They fill up as players finish tasks.</p>`;
  return data;
}

function episodeRow(job: Job): string {
  const tag = job.stage === "accepted" ? "ok" : job.stage === "rejected" ? "no" : "";
  const scored = job.stage === "accepted";
  return `<tr><td>${ago(job.received_at)}</td><td>${escapeHtml(job.contributor)}</td><td>${escapeHtml(taskTitle(job.task_id))}</td>
    <td><span class="tag ${tag}">${STAGE_LABEL[job.stage]}</span></td>
    <td class="num">${scored ? seconds(job.duration_s) : "-"}</td><td class="num">${scored ? points(job.smooth_score) : "-"}</td>
    <td class="num">${scored ? points(job.score) : "-"}</td></tr>`;
}

async function loadEpisodes(reset: boolean): Promise<void> {
  const body = $("episodes");
  try {
    const page = await fetchEpisodes(filter, reset ? null : next);
    next = page.next;
    const rowsHtml = page.episodes.map(episodeRow).join("");
    body.innerHTML = reset ? rowsHtml || `<tr><td colspan="7" class="muted">No episodes for this task yet.</td></tr>` : body.innerHTML + rowsHtml;
    $("more").hidden = next === null;
  } catch (error) {
    body.innerHTML = `<tr><td colspan="7" class="muted">Episodes are unavailable right now (${escapeHtml(String(error))}).</td></tr>`;
  }
}

function renderFilter(data: Datasets): void {
  const options: [string | null, string][] = [[null, "All tasks"], ...data.datasets.map((d): [string, string] => [d.task_id, taskTitle(d.task_id)])];
  const group = $("filter");
  group.innerHTML = options.map(([id, label]) =>
    `<button type="button" data-task="${id ?? ""}" aria-pressed="${id === filter}">${escapeHtml(label)}</button>`).join("");
  for (const button of group.querySelectorAll<HTMLButtonElement>("button")) {
    button.addEventListener("click", () => {
      filter = button.dataset.task || null;
      for (const other of group.querySelectorAll("button")) other.setAttribute("aria-pressed", String(other === button));
      void loadEpisodes(true);
    });
  }
}

async function start(): Promise<void> {
  try {
    renderFilter(await renderDatasets());
  } catch (error) {
    $("datasets").innerHTML = `<p class="empty">Datasets are unavailable right now (${escapeHtml(String(error))}). Retrying.</p>`;
  }
  await loadEpisodes(true);
  window.setInterval(() => void renderDatasets().catch(() => undefined), POLL_MS);
}

$("more").addEventListener("click", () => void loadEpisodes(false));
void mountHeader("datasets");
void start();

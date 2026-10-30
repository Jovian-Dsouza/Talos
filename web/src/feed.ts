// A run told as a sentence, with the stages it has passed. Used by the live feed.
import { ago, escapeHtml } from "./format";
import type { Job } from "./types";
import { points, reasonLabel, seconds, taskTitle } from "./words";

function sentence(job: Job): string {
  const who = `<b>${escapeHtml(job.contributor)}</b>`;
  const task = `<em>${escapeHtml(taskTitle(job.task_id))}</em>`;
  if (job.stage === "accepted") {
    return `${who} finished ${task} in ${seconds(job.duration_s)}. Verified with a score of ${points(job.score)}
      <span class="muted">(time ${points(job.time_score)}, smoothness ${points(job.smooth_score)})</span>.`;
  }
  if (job.stage === "rejected") return `${who} tried ${task}. Rejected: ${escapeHtml(reasonLabel(job.reason))}.`;
  return `${who} submitted ${task}. Waiting for a validator to replay it.`;
}

function steps(job: Job): string {
  const verdict = job.stage === "rejected" ? `<li class="done no">Rejected</li>` : `<li class="${job.stage === "accepted" ? "done ok" : ""}">Verified</li>`;
  const shelved = job.stage === "rejected" ? "" : `<li class="${job.stage === "accepted" ? "done ok" : ""}">In dataset</li>`;
  return `<ol class="mini-steps"><li class="done">Submitted</li><li class="${job.judged_at ? "done" : "now"}">Replayed</li>${verdict}${shelved}</ol>`;
}

const MARK: Record<Job["stage"], string> = { accepted: "✓", rejected: "✕", queued: "…" };

export function jobItem(job: Job): string {
  return `<li class="job job-${job.stage}">
    <span class="job-mark" aria-hidden="true">${MARK[job.stage]}</span>
    <div><p>${sentence(job)}</p>${steps(job)}</div>
    <time datetime="${new Date(job.received_at * 1000).toISOString()}">${ago(job.received_at)}</time>
  </li>`;
}

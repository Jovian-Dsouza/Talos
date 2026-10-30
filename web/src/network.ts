import { fetchNetwork } from "./api";
import { EXPLORER_URL } from "./config";
import { ago, escapeHtml, shorten } from "./format";
import type { Network } from "./types";

const $ = (id: string) => document.getElementById(id) as HTMLElement;
const DATASET_URL: string = import.meta.env.VITE_DATASET_URL ?? "";

function render(net: Network): void {
  $("meta").textContent = `Subnet ${net.netuid} at block ${net.block.toLocaleString()}`;
  $("miners").innerHTML =
    net.miners
      .map(
        (m) => `<tr><td>${m.uid}</td><td>${escapeHtml(m.contributor)}</td>
          <td class="num">${m.accepted}/${m.submitted}</td><td class="num">${m.value.toFixed(2)}</td>
          <td class="num">${(m.incentive * 100).toFixed(1)}%</td></tr>`,
      )
      .join("") || `<tr><td colspan="5" class="muted">No miners yet. Be the first to play.</td></tr>`;
  $("validators").innerHTML =
    net.validators
      .map((v) => {
        const root = v.root
          ? `<span class="mono">${v.root.root.slice(0, 24)}...</span> <span class="muted">epoch ${v.root.epoch}, block ${v.root.block}</span>`
          : `<span class="muted">none yet</span>`;
        const key = EXPLORER_URL
          ? `<a class="mono" href="${EXPLORER_URL}/${v.hotkey}" target="_blank" rel="noreferrer">${shorten(v.hotkey)}</a>`
          : `<span class="mono">${shorten(v.hotkey)}</span>`;
        return `<tr><td>${v.uid}</td><td>${key}</td><td>${root}</td></tr>`;
      })
      .join("") || `<tr><td colspan="3" class="muted">No validator online.</td></tr>`;
  $("feed").innerHTML =
    net.feed
      .map((item) => {
        const v = item.verdict;
        const tag = v.accepted ? `<span class="tag">accepted ${v.score.toFixed(2)}</span>` : `<span class="tag no">rejected</span>`;
        const detail = v.accepted ? `${v.duration_s.toFixed(1)} s, smoothness ${v.smooth_score.toFixed(2)}` : escapeHtml(v.reason);
        return `<li>${tag}<span><strong>${escapeHtml(item.contributor)}</strong> <span class="muted">${detail} &middot; ${ago(item.at)}</span></span></li>`;
      })
      .join("") || `<li class="muted">No runs scored yet.</li>`;
  const dataset = $("dataset");
  dataset.hidden = !DATASET_URL;
  if (DATASET_URL) dataset.innerHTML = `Verified data: <a href="${DATASET_URL}" target="_blank" rel="noreferrer">LeRobot dataset on Hugging Face</a>`;
}

async function refresh(): Promise<void> {
  try {
    render(await fetchNetwork());
  } catch (error) {
    $("meta").textContent = `Network unavailable: ${error instanceof Error ? error.message : String(error)}`;
  }
}

void refresh();
window.setInterval(() => void refresh(), 10000);

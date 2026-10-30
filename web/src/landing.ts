// Landing page: the live conveyor under the hero, plus the shared header.
import { fetchActivity } from "./api";
import { Conveyor } from "./charts/conveyor";
import { link, mountHeader } from "./header";
import { count, pluralize } from "./words";

const POLL_MS = 5000;
const conveyor = new Conveyor(document.getElementById("conveyor") as HTMLElement);
const meta = document.getElementById("live-meta") as HTMLElement;

async function refresh(): Promise<void> {
  try {
    const activity = await fetchActivity();
    conveyor.update(activity);
    meta.textContent = `${pluralize(activity.summary.miners_registered, "miner")}, ${pluralize(activity.summary.validators_on_chain, "validator")}, block ${count(activity.block)}`;
  } catch {
    meta.textContent = "Live numbers are unavailable right now.";
  }
}

for (const anchor of document.querySelectorAll<HTMLAnchorElement>("a[data-link]")) {
  anchor.href = link(anchor.getAttribute("href") ?? "/");
}
void mountHeader("home");
void refresh();
window.setInterval(() => void refresh(), POLL_MS);

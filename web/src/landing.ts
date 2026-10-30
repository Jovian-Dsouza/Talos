// Landing page: the live conveyor under the hero, plus the shared header.
import { fetchActivity } from "./api";
import { Conveyor } from "./charts/conveyor";
import { link, mountHeader } from "./header";
import { count, pluralize } from "./words";
import { mountHeroMedia } from "./landing/media";

const POLL_MS = 5000;
const conveyor = new Conveyor(document.getElementById("conveyor") as HTMLElement);
const meta = document.getElementById("live-meta") as HTMLElement;
const pipeline = document.getElementById("conveyor") as HTMLElement;
let loaded = false;

async function refresh(): Promise<void> {
  try {
    const activity = await fetchActivity();
    conveyor.update(activity);
    loaded = true;
    meta.textContent = `${pluralize(activity.summary.miners_registered, "miner")}, ${pluralize(activity.summary.validators_on_chain, "validator")}, block ${count(activity.block)}`;
  } catch {
    meta.textContent = loaded ? "Connection interrupted. Showing the last update; reconnecting…" : "Live numbers are unavailable right now. Reconnecting…";
    if (!loaded && !document.getElementById("retry-activity")) {
      pipeline.innerHTML = `<li class="empty">The network could not be reached. This view will update when it reconnects. <button type="button" class="btn small retry" id="retry-activity">Try again</button></li>`;
      document.getElementById("retry-activity")?.addEventListener("click", () => void refresh());
    }
  }
}

for (const anchor of document.querySelectorAll<HTMLAnchorElement>("a[data-link]")) {
  anchor.href = link(anchor.getAttribute("href") ?? "/");
}
void mountHeader("home");
mountHeroMedia();
void refresh();
window.setInterval(() => void refresh(), POLL_MS);

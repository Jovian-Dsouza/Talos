// The chain of custody every run goes through, drawn as stations on a belt. When a station's
// counter rises between two polls, a sample travels along the belt into it, so a new run, a
// verdict or a new dataset episode is visible the moment it happens.
import type { Activity } from "../types";
import { count, pluralize, seconds } from "../words";

interface Station {
  key: string;
  label: string;
  value: string;
  caption: string; // HTML built from numbers and fixed words only
}

function stations(a: Activity): Station[] {
  const { pipeline: p, summary: s } = a;
  const judged = p.accepted + p.rejected;
  const rate = judged ? `${Math.round((p.accepted / judged) * 100)}%` : "-";
  return [
    { key: "playing", label: "Playing now", value: count(s.playing_now), caption: "people driving the arm" },
    { key: "waiting", label: "Waiting", value: count(p.queued), caption: "runs in line for a validator" },
    { key: "replay", label: "Replaying", value: count(s.validating_now),
      caption: `${s.validating_now === 1 ? "validator re-runs" : "validators re-run"} the physics` },
    { key: "verdict", label: "Verified", value: rate,
      caption: `<b class="ok">${count(p.accepted)} verified</b> <b class="no">${count(p.rejected)} rejected</b>` },
    { key: "dataset", label: "In the dataset", value: count(s.episodes),
      caption: `${pluralize(s.episodes, "episode")}, ${seconds(s.demo_seconds)} of motion` },
  ];
}

/** What moved since the last poll, per station. */
function counters(a: Activity): Record<string, number> {
  const judged = a.pipeline.accepted + a.pipeline.rejected;
  return { playing: a.summary.playing_now, waiting: a.summary.runs, replay: judged, verdict: judged, dataset: a.summary.episodes };
}

export class Conveyor {
  private readonly items = new Map<string, HTMLLIElement>();
  private previous: Record<string, number> | null = null;

  constructor(private readonly root: HTMLElement) {}

  update(activity: Activity): void {
    const list = stations(activity);
    if (this.items.size === 0) this.build(list);
    for (const station of list) {
      const item = this.items.get(station.key)!;
      item.querySelector(".station-value")!.textContent = station.value;
      item.querySelector(".station-caption")!.innerHTML = station.caption;
    }
    const now = counters(activity);
    if (this.previous) {
      for (const [key, value] of Object.entries(now)) if (value > (this.previous[key] ?? 0)) this.arrive(key);
    }
    this.previous = now;
  }

  private build(list: Station[]): void {
    this.root.replaceChildren(...list.map((station) => {
      const item = document.createElement("li");
      item.className = `station station-${station.key}`;
      item.innerHTML = `<span class="belt" aria-hidden="true"></span>
        <div class="station-body"><span class="station-label">${station.label}</span>
        <strong class="station-value"></strong><span class="station-caption"></span></div>`;
      this.items.set(station.key, item);
      return item;
    }));
  }

  private arrive(key: string): void {
    const item = this.items.get(key);
    if (!item) return;
    const sample = document.createElement("i");
    sample.className = "sample";
    sample.addEventListener("animationend", () => sample.remove());
    item.querySelector(".belt")?.append(sample);
    item.classList.remove("arrived");
    void item.offsetWidth; // restart the arrival highlight
    item.classList.add("arrived");
  }
}

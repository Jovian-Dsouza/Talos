// Small trend marks without axes: a line for a running total, bars for counts per day.
// They sit beside the number they describe, which carries the exact value.
import { escapeHtml } from "../format";

export function sparkline(values: number[], label: string): string {
  if (values.length < 2) return `<div class="spark empty">Not enough history yet</div>`;
  const min = Math.min(...values);
  const span = Math.max(...values) - min || 1;
  const points = values.map((v, i) => `${(i / (values.length - 1)) * 100},${28 - ((v - min) / span) * 26}`);
  return `<svg class="spark" viewBox="0 0 100 30" preserveAspectRatio="none" role="img" aria-label="${escapeHtml(label)}">
    <polygon points="0,30 ${points.join(" ")} 100,30" fill="var(--nitrile-soft)" />
    <polyline points="${points.join(" ")}" fill="none" stroke="var(--nitrile)" stroke-width="2"
      vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round" /></svg>`;
}

export function miniBars(values: { value: number; title: string }[], label: string): string {
  const max = Math.max(1, ...values.map((v) => v.value));
  const bars = values.map((v) =>
    `<span style="height:${Math.max(v.value ? 8 : 2, (v.value / max) * 100)}%" title="${escapeHtml(v.title)}"
      class="${v.value ? "" : "zero"}"></span>`).join("");
  return `<div class="minibars" role="img" aria-label="${escapeHtml(label)}">${bars}</div>`;
}

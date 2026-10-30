// Bar charts drawn with HTML so labels stay readable at phone width. One y scale per chart,
// a 2px surface gap between stacked segments, values in ink and identity in the legend.
import { escapeHtml } from "../format";
import { count } from "../words";

export interface Series {
  key: string;
  label: string;
  color: string;
}

export interface Column {
  label: string | null; // x-axis label, or null to leave this tick blank
  title: string; // hover text naming the bucket
  values: Record<string, number>;
}

/** Round up to 1, 2 or 5 times a power of ten so gridlines land on readable numbers. */
export function niceMax(value: number): number {
  if (value <= 0) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  return ([1, 2, 5, 10].find((step) => step * power >= value) ?? 10) * power;
}

export function legend(series: Series[]): string {
  return `<ul class="legend inline">${series.map((s) =>
    `<li><i style="background:${s.color}"></i><span>${escapeHtml(s.label)}</span></li>`).join("")}</ul>`;
}

/** Stacked columns over time. */
export function columns(data: Column[], series: Series[], ariaLabel: string): string {
  const totals = data.map((col) => series.reduce((sum, s) => sum + (col.values[s.key] ?? 0), 0));
  const max = niceMax(Math.max(0, ...totals));
  const cols = data.map((col, i) => {
    const parts = series.filter((s) => (col.values[s.key] ?? 0) > 0).map((s) =>
      `<span style="height:${((col.values[s.key] ?? 0) / max) * 100}%;background:${s.color}"></span>`).join("");
    const detail = series.map((s) => `${s.label} ${col.values[s.key] ?? 0}`).join(", ");
    return `<div class="col" title="${escapeHtml(`${col.title}: ${totals[i]} runs (${detail})`)}">${parts}</div>`;
  }).join("");
  const axis = data.map((col) => `<span>${col.label === null ? "" : escapeHtml(col.label)}</span>`).join("");
  return `<div class="columns" role="img" aria-label="${escapeHtml(ariaLabel)}">
    <div class="columns-plot">
      <div class="gridlines"><span data-v="${count(max)}"></span><span data-v="${count(max / 2)}"></span><span data-v="0"></span></div>
      <div class="cols" style="--n:${data.length}">${cols}</div>
    </div>
    <div class="columns-axis" style="--n:${data.length}">${axis}</div>
  </div>${legend(series)}`;
}

export interface Row {
  label: string;
  values: Record<string, number>;
}

/** Horizontal bars, optionally stacked, each row labelled with its total. */
export function rows(data: Row[], series: Series[], unit: string): string {
  const totals = data.map((row) => series.reduce((sum, s) => sum + (row.values[s.key] ?? 0), 0));
  const max = Math.max(1, ...totals);
  const body = data.map((row, i) => {
    const parts = series.filter((s) => (row.values[s.key] ?? 0) > 0).map((s) =>
      `<span style="width:${((row.values[s.key] ?? 0) / max) * 100}%;background:${s.color}"
        title="${escapeHtml(`${s.label}: ${row.values[s.key]}`)}"></span>`).join("");
    return `<li><span class="row-label">${escapeHtml(row.label)}</span>
      <span class="row-bar">${parts}</span><strong>${count(totals[i])}</strong></li>`;
  }).join("");
  return `<ul class="rows" aria-label="${escapeHtml(unit)}">${body}</ul>${series.length > 1 ? legend(series) : ""}`;
}

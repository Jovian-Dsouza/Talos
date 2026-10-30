// Donut for parts of a whole (three or more slices; two slices read better as a meter).
// Identity never rests on colour alone: the legend repeats every label, value and share.
import { escapeHtml } from "../format";
import { count } from "../words";

export interface Slice {
  label: string;
  value: number;
  color: string; // a CSS colour, normally a token such as var(--verified)
}

const RADIUS = 52;
const STROKE = 14;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const GAP = 2; // surface gap between slices, in the same units as the circumference

export function donut(slices: Slice[], centerValue: string, centerLabel: string): string {
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  const shown = slices.filter((s) => s.value > 0);
  let offset = 0;
  const arcs = shown.map((s) => {
    const length = (s.value / total) * CIRCUMFERENCE;
    const visible = shown.length > 1 ? Math.max(0, length - GAP) : length;
    const arc = `<circle r="${RADIUS}" cx="60" cy="60" fill="none" stroke="${s.color}" stroke-width="${STROKE}"
      stroke-dasharray="${visible} ${CIRCUMFERENCE - visible}" stroke-dashoffset="${-offset}">
      <title>${escapeHtml(s.label)}: ${count(s.value)}</title></circle>`;
    offset += length;
    return arc;
  });
  const ring = total === 0
    ? `<circle r="${RADIUS}" cx="60" cy="60" fill="none" stroke="var(--line)" stroke-width="${STROKE}" />`
    : arcs.join("");
  const legend = slices.map((s) => {
    const share = total ? Math.round((s.value / total) * 100) : 0;
    return `<li><i style="background:${s.color}"></i><span>${escapeHtml(s.label)}</span>
      <strong>${count(s.value)}</strong><small>${share}%</small></li>`;
  }).join("");
  return `<div class="donut">
    <div class="donut-ring"><svg viewBox="0 0 120 120" role="img" aria-label="${escapeHtml(centerLabel)}">
      <g transform="rotate(-90 60 60)">${ring}</g></svg>
      <div class="donut-center"><strong>${escapeHtml(centerValue)}</strong><span>${escapeHtml(centerLabel)}</span></div>
    </div>
    <ul class="legend">${legend}</ul>
  </div>`;
}

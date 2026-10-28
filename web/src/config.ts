// Pool URLs come from the page query (?pool=URL&pool2=URL) or build-time env vars.
const params = new URLSearchParams(window.location.search);

export const POOL_URL: string =
  params.get("pool") ?? import.meta.env.VITE_POOL_URL ?? "http://127.0.0.1:8091";
export const POOL_URLS: string[] = [
  POOL_URL,
  ...[params.get("pool2") ?? import.meta.env.VITE_POOL2_URL].filter((u): u is string => !!u),
];
export const EXPLORER_URL: string = import.meta.env.VITE_EXPLORER_URL ?? "";
export const STATUS_POLL_MS = 1000;
export const STATUS_POLL_LIMIT_MS = 120_000;

// Pool URLs come from the page query (?pool=URL&pool2=URL), build-time env vars, or a dev proxy.
const params = new URLSearchParams(window.location.search);

function defaultPoolUrl(): string {
  const env = import.meta.env.VITE_POOL_URL;
  if (env) return env;
  const { protocol, hostname, origin } = window.location;
  // Desktop dev on localhost keeps a direct HTTP pool; HTTPS (tunnels, preview) uses same-origin /pool.
  if (protocol === "https:" || (hostname !== "localhost" && hostname !== "127.0.0.1")) {
    return `${origin}/pool`;
  }
  return "http://127.0.0.1:8091";
}

export const POOL_URL: string = params.get("pool") ?? defaultPoolUrl();
export const POOL_URLS: string[] = [
  POOL_URL,
  ...[params.get("pool2") ?? import.meta.env.VITE_POOL2_URL].filter((u): u is string => !!u),
];
export const EXPLORER_URL: string = import.meta.env.VITE_EXPLORER_URL ?? "";
export const STATUS_POLL_MS = 1000;
export const STATUS_POLL_LIMIT_MS = 120_000;

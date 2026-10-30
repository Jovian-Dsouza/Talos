// Backend URL comes from the page query (?pool=URL), a build-time env var, or a same-origin /pool proxy.
const params = new URLSearchParams(window.location.search);

function defaultPoolUrl(): string {
  const env = import.meta.env.VITE_POOL_URL;
  if (env) return env;
  const { protocol, hostname, origin } = window.location;
  // Desktop dev on localhost keeps a direct HTTP backend; HTTPS (tunnels, Vercel) uses same-origin /pool.
  if (protocol === "https:" || (hostname !== "localhost" && hostname !== "127.0.0.1")) {
    return `${origin}/pool`;
  }
  return "http://127.0.0.1:8091";
}

export const POOL_URL: string = params.get("pool") ?? defaultPoolUrl();
export const CLERK_KEY: string = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ?? "";
// Local testing only: ?dev=NAME signs in as a dev player when the backend runs with AUTH_DEV_LOGIN=1.
export const DEV_LOGIN: boolean = import.meta.env.VITE_ALLOW_DEV_LOGIN === "1";
export const EXPLORER_URL: string = import.meta.env.VITE_EXPLORER_URL ?? "";
export const STATUS_POLL_MS = 1000;
export const STATUS_POLL_LIMIT_MS = 120_000;

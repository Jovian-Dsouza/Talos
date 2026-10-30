import { authHeaders } from "./auth";
import { POOL_URL, STATUS_POLL_LIMIT_MS, STATUS_POLL_MS } from "./config";
import type { LeaderboardEntry, Me, Network, Status, Ticket, Verdict } from "./types";

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      // body was not JSON; keep the status text
    }
    throw new Error(`${response.status} ${detail}`);
  }
  return (await response.json()) as T;
}

async function call<T>(path: string, init: RequestInit = {}, signedIn = false): Promise<T> {
  const headers = { ...(init.headers as Record<string, string>), ...(signedIn ? await authHeaders() : {}) };
  return json<T>(await fetch(`${POOL_URL}${path}`, { ...init, headers }));
}

export const fetchTicket = (task: string) =>
  call<Ticket>(`/ticket?task=${encodeURIComponent(task)}`, {}, true);

export const submitBundle = (bundle: unknown) =>
  call<{ bundle_id: string; registration: string }>(
    "/submit",
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(bundle) },
    true,
  );

export const fetchMe = () => call<Me>("/me", {}, true);
export const fetchNetwork = () => call<Network>("/network");
export const fetchTasks = async () => (await call<{ tasks: string[] }>("/tasks")).tasks;
export const fetchLeaderboard = async () => (await call<{ contributors: LeaderboardEntry[] }>("/leaderboard")).contributors;

export async function waitForVerdict(bundleId: string, onWaiting?: () => void): Promise<Verdict> {
  const started = performance.now();
  while (performance.now() - started < STATUS_POLL_LIMIT_MS) {
    const status = await call<Status>(`/status/${bundleId}`);
    const verdicts = Object.values(status.verdicts);
    if (verdicts.length > 0) return verdicts[0];
    onWaiting?.();
    await new Promise((resolve) => setTimeout(resolve, STATUS_POLL_MS));
  }
  throw new Error("The validators have not answered yet. Check back in a moment.");
}

import { STATUS_POLL_LIMIT_MS, STATUS_POLL_MS } from "./config";
import type { LeaderboardEntry, Status, Ticket, Verdict } from "./types";

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

export async function fetchTicket(pool: string, task: string): Promise<Ticket> {
  return json<Ticket>(await fetch(`${pool}/ticket?task=${encodeURIComponent(task)}`));
}

export async function submitBundle(pool: string, bundle: unknown): Promise<{ bundle_id: string }> {
  const response = await fetch(`${pool}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bundle),
  });
  return json(response);
}

export async function waitForVerdict(pool: string, bundleId: string): Promise<Verdict> {
  const started = performance.now();
  while (performance.now() - started < STATUS_POLL_LIMIT_MS) {
    const status = await json<Status>(await fetch(`${pool}/status/${bundleId}`));
    const verdicts = Object.values(status.verdicts);
    if (verdicts.length > 0) return verdicts[0];
    await new Promise((resolve) => setTimeout(resolve, STATUS_POLL_MS));
  }
  throw new Error("The validators have not answered yet. Check back in a moment.");
}

export async function fetchLeaderboard(pool: string): Promise<LeaderboardEntry[]> {
  const body = await json<{ contributors: LeaderboardEntry[] }>(await fetch(`${pool}/leaderboard`));
  return body.contributors;
}

export async function fetchTasks(pool: string): Promise<string[]> {
  return (await json<{ tasks: string[] }>(await fetch(`${pool}/tasks`))).tasks;
}

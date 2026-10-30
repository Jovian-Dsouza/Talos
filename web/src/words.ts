// Plain-language names for what the network does, shared by every page so a stage or a reason
// reads the same everywhere.
import { taskInfo, TASKS } from "./tasks";
import type { Stage } from "./types";

const REASONS: Record<string, string> = {
  "replay does not match the recording": "Replay did not match the recording",
  "task not completed on replay": "Task was not finished on replay",
  "near duplicate of an accepted episode": "Copy of an earlier run",
  "block hash does not match the chain": "Ticket was not found on chain",
  "ticket already used": "Ticket was used twice",
  "ticket expired": "Ticket expired before upload",
  "run not signed by the miner hotkey": "Not signed by the player's miner",
  "MuJoCo version differs from the validator": "Different physics engine version",
  "model hash mismatch": "Scene was altered",
  "malformed upload": "Upload was damaged",
};

export const STAGE_LABEL: Record<Stage, string> = {
  queued: "Waiting for a validator",
  accepted: "Verified",
  rejected: "Rejected",
};

export function reasonLabel(reason: string): string {
  const key = reason.split(":")[0].trim();
  return REASONS[key] ?? (key ? key[0].toUpperCase() + key.slice(1) : "Unknown reason");
}

/** Task title, or the raw id for a task this build does not know. */
export function taskTitle(id: string): string {
  return TASKS.some((task) => task.id === id) ? taskInfo(id).title : id;
}

export function points(score: number): string {
  return String(Math.round(score * 100));
}

export function seconds(value: number): string {
  if (value < 90) return `${value.toFixed(1)} s`;
  if (value < 5400) return `${Math.round(value / 60)} min`;
  return `${(value / 3600).toFixed(1)} h`;
}

export function count(value: number): string {
  return value.toLocaleString("en-US");
}

/** TAO and alpha amounts: enough digits to see small localnet and testnet earnings move. */
export function amount(value: number): string {
  if (value === 0) return "0";
  if (Math.abs(value) < 0.001) return value.toExponential(1);
  return value.toLocaleString("en-US", { maximumFractionDigits: value < 10 ? 4 : 2 });
}

export function pluralize(n: number, one: string, many = `${one}s`): string {
  return `${count(n)} ${n === 1 ? one : many}`;
}

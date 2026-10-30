export interface SceneObject {
  id: string;
  kind: "cube" | "bowl" | "vial" | "rack";
  color: string;
  x: number;
  y: number;
  yaw: number;
}

export interface SceneSpec {
  task_id: string;
  instruction: string;
  pick: string;
  place: { x: number; y: number; z: number };
  target_slot?: string;
  objects: SceneObject[];
}

export interface Ticket {
  block: number;
  block_hash: string;
  hotkey: string;
  task_id: string;
  counter: number;
  // 64-bit seed as a decimal string; JavaScript numbers cannot hold it.
  seed: string;
  scene_spec: SceneSpec;
  scene_xml: string;
  instruction: string;
  expires_block: number;
  // Echoed back in the upload; the validator recomputes and compares it.
  model_hash?: string;
}

export interface Verdict {
  accepted: boolean;
  reason: string;
  replay_drift: number;
  success: boolean;
  time_score: number;
  smooth_score: number;
  duration_s: number;
  score: number;
}

export interface Status {
  bundle_id: string;
  contributor: string;
  verdicts: Record<string, Verdict>;
}

export interface LeaderboardEntry {
  contributor: string;
  uid?: number;
  submitted: number;
  accepted: number;
  value: number;
}

export interface InputEvent {
  t: number;
  kind: string;
  x?: number;
  y?: number;
  v?: number;
}

export interface Me {
  name: string;
  coldkey: string;
  hotkey: string;
  uid: number | null;
  registration: "pending" | "funding" | "registering" | "registered" | "failed";
  registration_note: string;
  submitted: number;
  accepted: number;
  score: number;
  incentive: number;
  emission: number;
  netuid: number;
}

export interface NetworkMiner {
  uid: number;
  hotkey: string;
  contributor: string;
  submitted: number;
  accepted: number;
  value: number;
  incentive: number;
  emission: number;
}

export interface Network {
  netuid: number;
  block: number;
  miners: NetworkMiner[];
  validators: { uid: number; hotkey: string; stake: number; root: { epoch: number; root: string; block: number } | null }[];
  feed: { hotkey: string; contributor: string; verdict: Verdict; at: number }[];
}

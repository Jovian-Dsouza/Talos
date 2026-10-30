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
  subnet_name: string | null;
  chain: string;
  block: number;
  miners: NetworkMiner[];
  validators: { uid: number; hotkey: string; stake: number; root: { epoch: number; root: string; block: number } | null }[];
  feed: { hotkey: string; contributor: string; verdict: Verdict; at: number }[];
}

export type Stage = "queued" | "accepted" | "rejected";

/** One submitted run with its first validator verdict (mirrors miner/activity.py job_view). */
export interface Job {
  id: number;
  bundle_id: string;
  hotkey: string;
  contributor: string;
  task_id: string;
  stage: Stage;
  received_at: number;
  judged_at: number | null;
  validator: string | null;
  reason: string;
  score: number;
  time_score: number;
  smooth_score: number;
  duration_s: number;
}

export interface TimelineBucket {
  start: number;
  accepted: number;
  rejected: number;
  queued: number;
}

export interface Activity {
  netuid: number;
  subnet_name: string | null;
  block: number;
  window: "1h" | "24h";
  summary: {
    miners_registered: number;
    miners_active: number;
    playing_now: number;
    validators_on_chain: number;
    validating_now: number;
    runs: number;
    episodes: number;
    demo_seconds: number;
  };
  pipeline: { playing: number; queued: number; accepted: number; rejected: number };
  reasons: { reason: string; count: number }[];
  tasks: { task_id: string; accepted: number; rejected: number; queued: number }[];
  timeline: { bucket_seconds: number; buckets: TimelineBucket[] };
  jobs: Job[];
  at: number;
}

export interface Dataset {
  task_id: string;
  episodes: number;
  rejected: number;
  queued: number;
  seconds: number;
  contributors: number;
  average_score: number;
  best_score: number;
  updated_at: number | null;
  per_day: { day: number; episodes: number }[];
  link: string;
}

export interface Datasets {
  format: string;
  robot: string;
  fps: number;
  cameras: string[];
  datasets: Dataset[];
}

export interface EpisodePage {
  episodes: Job[];
  next: number | null;
}

export interface Badge {
  id: string;
  title: string;
  detail: string;
  earned: boolean;
}

export interface Progress {
  xp: number;
  level: number;
  title: string;
  level_xp: number;
  next_xp: number | null;
  streak_days: number;
  longest_streak: number;
  daily: { done: number; goal: number };
  runs: number;
  verified: number;
  rejected: number;
  rank: number | null;
  players: number;
  bests: { task_id: string; score: number; duration_s: number }[];
  badges: Badge[];
  history: { at: number; task_id: string; accepted: boolean; score: number; time_score: number; smooth_score: number; reason: string; xp: number }[];
}

export interface Wallet {
  coldkey: string;
  hotkey: string;
  uid: number | null;
  registration: Me["registration"];
  netuid: number;
  subnet_name: string | null;
  free_tao: number;
  staked_alpha: number;
  alpha_price: number;
  earned_tao: number;
  emission_alpha_per_tempo: number;
  alpha_per_day: number | null;
  tao_per_day: number | null;
  history: { block: number; alpha: number; at: number; tao: number }[];
}

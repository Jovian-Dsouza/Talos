export interface SceneObject {
  id: string;
  kind: "cube" | "bowl";
  color: string;
  x: number;
  y: number;
  yaw: number;
}

export interface Ticket {
  block: number;
  block_hash: string;
  hotkey: string;
  task_id: string;
  counter: number;
  // 64-bit seed as a decimal string; JavaScript numbers cannot hold it.
  seed: string;
  scene_spec: { task_id: string; instruction: string; objects: SceneObject[] };
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
  quality: number;
  novelty: number;
  score: number;
}

export interface Status {
  bundle_id: string;
  contributor: string;
  verdicts: Record<string, Verdict>;
}

export interface LeaderboardEntry {
  contributor: string;
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

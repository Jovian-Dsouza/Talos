// Mirrors common/schema.py. Keep the two in sync: the validator replays with these values.
export const HOME_POSE = [0.0, -1.2, 1.2, 0.8, 0.0, 0.5] as const;
export const NUM_JOINTS = 6;
export const SUBSTEPS = 10;
export const CONTROL_DT = 0.02;
export const CHECKPOINT_EVERY = 25;
export const MAX_STEPS = 3000;
export const MIN_STEPS = 10;

export const GRIPPER_OPEN = 1.3;
export const GRIPPER_CLOSED = 0.05;
// Reachable workspace for the tip with the tool kept roughly pointing down (metres).
export const REACH_MIN = 0.14;
export const REACH_MAX = 0.29;
export const HEIGHT_MIN = 0.012;
export const HEIGHT_MAX = 0.11;

// Rack layout for rack_vial. Mirrors common/scene.py (RACK_ROWS, RACK_COLS).
export const RACK_ROWS = "AB";
export const RACK_COLS = 4;

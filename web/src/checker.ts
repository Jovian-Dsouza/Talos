import type { Sim } from "./sim";
import type { SceneSpec } from "./types";

// Same rules as common/tasks/*.json. Only the validator's copy decides success; this one gives
// instant feedback.
const CONTAINER_RULE = { xyRadius: 0.03, zMin: 0.008, zMax: 0.03, maxSpeed: 0.05, maxArmSpeed: 0.2 };
const SLOT_RULE = { xyRadius: 0.011, zMin: 0.032, zMax: 0.041, minUpright: 0.94, maxSpeed: 0.05, maxArmSpeed: 0.2 };

export interface Progress {
  success: boolean;
  distance: number;
}

function speedOf(sim: Sim, first: number): number {
  let sum = 0;
  for (let i = 0; i < 6; i++) sum += sim.data.qvel[first + i] ** 2;
  return Math.sqrt(sum);
}

export function checkProgress(sim: Sim, spec: SceneSpec): Progress {
  const object = sim.bodyPos(spec.pick);
  const objectSpeed = speedOf(sim, sim.model.body_dofadr[sim.model.body(spec.pick).id]);
  const armSpeed = speedOf(sim, 0);
  if (spec.target_slot !== undefined) {
    const slot = sim.sitePos(`slot_${spec.target_slot}`);
    const distance = Math.hypot(object[0] - slot[0], object[1] - slot[1]);
    const rule = SLOT_RULE;
    const success =
      distance <= rule.xyRadius &&
      object[2] >= rule.zMin &&
      object[2] <= rule.zMax &&
      sim.bodyUpright(spec.pick) >= rule.minUpright &&
      objectSpeed <= rule.maxSpeed &&
      armSpeed <= rule.maxArmSpeed;
    return { success, distance };
  }
  const distance = Math.hypot(object[0] - spec.place.x, object[1] - spec.place.y);
  const rule = CONTAINER_RULE;
  const success =
    distance <= rule.xyRadius &&
    object[2] >= rule.zMin &&
    object[2] <= rule.zMax &&
    objectSpeed <= rule.maxSpeed &&
    armSpeed <= rule.maxArmSpeed;
  return { success, distance };
}

import type { Sim } from "./sim";

// Same rules as common/tasks/put_cube_in_bowl.json. Only the validator's copy decides success;
// this one gives instant feedback.
const RULE = { xyRadius: 0.03, zMin: 0.008, zMax: 0.03, maxSpeed: 0.05, maxArmSpeed: 0.2 };

export interface Progress {
  success: boolean;
  distance: number;
}

export function checkProgress(sim: Sim): Progress {
  const cube = sim.bodyPos("cube_target");
  const bowl = sim.bodyPos("bowl_target");
  const distance = Math.hypot(cube[0] - bowl[0], cube[1] - bowl[1]);
  const first: number = sim.model.body_dofadr[sim.model.body("cube_target").id];
  let objectSpeed = 0;
  for (let i = 0; i < 6; i++) objectSpeed += sim.data.qvel[first + i] ** 2;
  let armSpeed = 0;
  for (let i = 0; i < 6; i++) armSpeed += sim.data.qvel[i] ** 2;
  const success =
    distance <= RULE.xyRadius &&
    cube[2] >= RULE.zMin &&
    cube[2] <= RULE.zMax &&
    Math.sqrt(objectSpeed) <= RULE.maxSpeed &&
    Math.sqrt(armSpeed) <= RULE.maxArmSpeed;
  return { success, distance };
}

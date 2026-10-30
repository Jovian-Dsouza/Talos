export interface TaskInfo {
  id: string;
  title: string;
  industry: string;
  blurb: string;
  done: string;
}

// Mirrors the task ids in common/scene.py. The pool decides which of these it serves.
export const TASKS: readonly TaskInfo[] = [
  {
    id: "rack_vial",
    title: "Vial racking",
    industry: "Lab automation",
    blurb: "Seat the named sample vial in its slot of the rack.",
    done: "Vial is seated. Submit when ready.",
  },
  {
    id: "put_cube_in_bowl",
    title: "Parts to tote",
    industry: "Logistics",
    blurb: "Move the named part into the matching tote.",
    done: "Part is in the tote. Submit when ready.",
  },
];

export function taskInfo(id: string): TaskInfo {
  return TASKS.find((task) => task.id === id) ?? TASKS[0];
}

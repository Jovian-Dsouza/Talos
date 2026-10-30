import type { PracticeScene } from "../types";

let scenes: Promise<PracticeScene[]> | null = null;
let previous = -1;

/** Static assets only. Practice never requests a ticket or sends a recording. */
export async function practiceScene(): Promise<PracticeScene> {
  scenes ??= fetch(`${import.meta.env.BASE_URL}assets/practice/scenes.json`)
    .then(async (response) => {
      if (!response.ok) throw new Error("Practice scenes could not be loaded. Please try again.");
      const data = await response.json() as PracticeScene[];
      if (!data.length) throw new Error("Practice scenes are unavailable.");
      return data;
    }).catch((error) => { scenes = null; throw error; });
  const choices = await scenes;
  const random = new Uint32Array(1);
  crypto.getRandomValues(random);
  const index = choices.length > 1 ? (previous + 1 + random[0] % (choices.length - 1)) % choices.length : 0;
  previous = index;
  return choices[index];
}

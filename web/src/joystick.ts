export type StickHandler = (x: number, y: number) => void;

const DEAD_ZONE = 0.12;
const TRAVEL = 0.6; // knob travel as a fraction of the base radius

/**
 * Round on-screen thumbstick. Reports x to the right and y upward, each in -1..1. Output is zero
 * inside a small dead zone and eases in quadratically, so small thumb movements give fine control.
 * Each stick owns one pointer, so two sticks work at once with two thumbs.
 */
export class Joystick {
  private pointer: number | null = null;
  private readonly knob: HTMLElement;

  constructor(private readonly base: HTMLElement, private readonly onChange: StickHandler) {
    const knob = base.querySelector<HTMLElement>(".knob");
    if (!knob) throw new Error("joystick base needs a .knob child");
    this.knob = knob;
    base.addEventListener("pointerdown", (e) => {
      if (this.pointer !== null) return;
      this.pointer = e.pointerId;
      base.setPointerCapture(e.pointerId);
      this.drag(e);
    });
    base.addEventListener("pointermove", (e) => {
      if (e.pointerId === this.pointer) this.drag(e);
    });
    for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) {
      base.addEventListener(type, (e) => {
        if ((e as PointerEvent).pointerId === this.pointer) this.release();
      });
    }
    base.addEventListener("contextmenu", (e) => e.preventDefault());
  }

  private drag(e: PointerEvent): void {
    const rect = this.base.getBoundingClientRect();
    const travel = (rect.width / 2) * TRAVEL;
    let dx = (e.clientX - (rect.left + rect.width / 2)) / travel;
    let dy = (e.clientY - (rect.top + rect.height / 2)) / travel;
    const length = Math.hypot(dx, dy);
    if (length > 1) {
      dx /= length;
      dy /= length;
    }
    this.knob.style.transform = `translate(${dx * travel}px, ${dy * travel}px)`;
    const magnitude = Math.min(length, 1);
    if (magnitude < DEAD_ZONE) {
      this.onChange(0, 0);
      return;
    }
    const eased = ((magnitude - DEAD_ZONE) / (1 - DEAD_ZONE)) ** 2;
    this.onChange((dx / magnitude) * eased, (-dy / magnitude) * eased);
  }

  private release(): void {
    this.pointer = null;
    this.knob.style.transform = "";
    this.onChange(0, 0);
  }
}

import * as THREE from "three";

/** Layer for scenery. Only the main camera renders it, so the top and side insets stay clean. */
export const ENV_LAYER = 1;
export const BENCH_WIDTH = 1.4; // metres along x
export const BENCH_DEPTH = 1.0; // metres along y
export const ROOM_COLOR = 0xcfd6db;

const FLOOR_Z = -0.72;
const DOT_PITCH = 0.025; // mounting plate hole spacing, so distances read at a glance
export const SLAB_TOP = -0.0205; // just under the thin slab that gives the side inset its ground line

interface BoxSpec {
  size: [number, number, number];
  at: [number, number, number];
  color: number;
  metal?: number;
  rough?: number;
}

function box({ size, at, color, metal = 0.05, rough = 0.7 }: BoxSpec): THREE.Mesh {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(...size),
    new THREE.MeshStandardMaterial({ color, metalness: metal, roughness: rough }),
  );
  mesh.position.set(...at);
  return mesh;
}

/** Perforated aluminium mounting plate: a fine dot grid on anodised grey. */
export function benchMaterial(): THREE.Material {
  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "#b9c2ca";
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = "#7e8a94";
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, 6, 0, Math.PI * 2);
    ctx.fill();
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(BENCH_WIDTH / DOT_PITCH, BENCH_DEPTH / DOT_PITCH);
  texture.anisotropy = 8;
  texture.colorSpace = THREE.SRGBColorSpace;
  return new THREE.MeshStandardMaterial({ map: texture, roughness: 0.55, metalness: 0.35 });
}

function signTexture(): THREE.Texture {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "#14324d";
    ctx.fillRect(0, 0, 1024, 256);
    ctx.fillStyle = "#f2c200";
    for (let x = -256; x < 1024; x += 64) {
      ctx.beginPath();
      ctx.moveTo(x, 256);
      ctx.lineTo(x + 32, 256);
      ctx.lineTo(x + 32 + 40, 216);
      ctx.lineTo(x + 40, 216);
      ctx.fill();
    }
    ctx.fillStyle = "#ffffff";
    ctx.font = "700 92px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("ROBOT WORK CELL 03", 512, 110);
    ctx.fillStyle = "#9fc4e0";
    ctx.font = "500 44px system-ui, sans-serif";
    ctx.fillText("Authorised operators only", 512, 176);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return texture;
}

function room(): THREE.Object3D[] {
  const wall = (size: [number, number, number], at: [number, number, number]) =>
    box({ size, at, color: 0xe3e8eb, rough: 0.9 });
  const height = 2.6;
  const mid = FLOOR_Z + height / 2;
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(8, 8),
    new THREE.MeshStandardMaterial({ color: 0x4a5159, roughness: 0.85 }),
  );
  floor.position.z = FLOOR_Z;
  return [
    floor,
    wall([8, 0.05, height], [0, 1.6, mid]),
    wall([8, 0.05, height], [0, -2.4, mid]),
    wall([0.05, 8, height], [2.4, 0, mid]),
    wall([0.05, 8, height], [-2.4, 0, mid]),
  ];
}

function bench(): THREE.Object3D[] {
  const thickness = 0.05;
  const parts: THREE.Object3D[] = [
    box({ size: [BENCH_WIDTH, BENCH_DEPTH, thickness], at: [0, 0, SLAB_TOP - thickness / 2], color: 0x6f7b85, metal: 0.5, rough: 0.45 }),
    box({ size: [BENCH_WIDTH - 0.1, 0.02, 0.4], at: [0, -BENCH_DEPTH / 2 + 0.06, SLAB_TOP - thickness - 0.2], color: 0x56616b }),
  ];
  const legHeight = SLAB_TOP - thickness - FLOOR_Z;
  for (const sx of [-1, 1]) {
    for (const sy of [-1, 1]) {
      parts.push(
        box({
          size: [0.05, 0.05, legHeight],
          at: [sx * (BENCH_WIDTH / 2 - 0.05), sy * (BENCH_DEPTH / 2 - 0.05), FLOOR_Z + legHeight / 2],
          color: 0x59646e,
          metal: 0.6,
        }),
      );
    }
  }
  // Yellow safety tape on the floor around the bench.
  const tape = (size: [number, number, number], at: [number, number, number]) => box({ size, at: [at[0], at[1], FLOOR_Z + 0.002], color: 0xf2c200 });
  const gap = 0.35;
  parts.push(
    tape([BENCH_WIDTH + 2 * gap, 0.05, 0.002], [0, -BENCH_DEPTH / 2 - gap, 0]),
    tape([BENCH_WIDTH + 2 * gap, 0.05, 0.002], [0, BENCH_DEPTH / 2 + gap, 0]),
    tape([0.05, BENCH_DEPTH + 2 * gap, 0.002], [-BENCH_WIDTH / 2 - gap, 0, 0]),
    tape([0.05, BENCH_DEPTH + 2 * gap, 0.002], [BENCH_WIDTH / 2 + gap, 0, 0]),
  );
  return parts;
}

/** Hazard arc on the bench, just outside the arm's reach. */
function reachMarking(): THREE.Object3D {
  const arc = new THREE.Mesh(
    new THREE.RingGeometry(0.325, 0.34, 96, 1, -Math.PI * 0.62, Math.PI * 1.24),
    new THREE.MeshBasicMaterial({ color: 0xf2c200, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }),
  );
  arc.position.z = 0.0004;
  return arc;
}

/** Controller cabinet and a signal tower on the bench, outside the arm's reach. */
function equipment(): THREE.Object3D[] {
  const lamp = (z: number, color: number, lit: boolean) => {
    const mesh = new THREE.Mesh(
      new THREE.CylinderGeometry(0.018, 0.018, 0.03, 20).rotateX(Math.PI / 2),
      new THREE.MeshStandardMaterial({ color, emissive: lit ? color : 0x000000, emissiveIntensity: lit ? 0.9 : 0, roughness: 0.4 }),
    );
    mesh.position.set(-0.22, 0.34, z);
    return mesh;
  };
  const strip = new THREE.Mesh(new THREE.PlaneGeometry(0.1, 0.012), new THREE.MeshBasicMaterial({ color: 0x38e08a }));
  strip.position.set(-0.22 + 0.0001, -0.3 - 0.07, 0.1);
  strip.rotation.x = Math.PI / 2;
  return [
    box({ size: [0.14, 0.13, 0.14], at: [-0.22, -0.3, 0.07], color: 0x3c454d, metal: 0.4, rough: 0.5 }),
    strip,
    box({ size: [0.012, 0.012, 0.06], at: [-0.22, 0.34, 0.03], color: 0x2b3238, metal: 0.6 }),
    lamp(0.075, 0xe03c3c, false),
    lamp(0.105, 0xf2a900, false),
    lamp(0.135, 0x38e08a, true),
  ];
}

function shelving(): THREE.Object3D[] {
  const parts: THREE.Object3D[] = [];
  const y = 1.42;
  let seed = 7;
  const random = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const glass = [0x8a4b12, 0x9b5a1a, 0xcfe3ec, 0x2f6fa8];
  for (const z of [-0.15, 0.2, 0.55]) {
    parts.push(box({ size: [1.6, 0.3, 0.02], at: [0.1, y, z], color: 0x8e99a3, metal: 0.5 }));
    for (let x = -0.68; x < 0.9; x += 0.09 + random() * 0.04) {
      const height = 0.08 + random() * 0.1;
      const radius = 0.025 + random() * 0.015;
      const color = glass[Math.floor(random() * glass.length)];
      const bottle = new THREE.Mesh(
        new THREE.CylinderGeometry(radius, radius, height, 16).rotateX(Math.PI / 2),
        new THREE.MeshStandardMaterial({ color, roughness: 0.25, metalness: 0.1 }),
      );
      bottle.position.set(0.1 + x, y + (random() - 0.5) * 0.1, z + 0.01 + height / 2);
      parts.push(bottle);
    }
  }
  for (const x of [-0.7, 0.9]) parts.push(box({ size: [0.03, 0.3, 0.9], at: [x, y, 0.2], color: 0x59646e, metal: 0.6 }));
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.25), new THREE.MeshBasicMaterial({ map: signTexture() }));
  sign.position.set(0.1, 1.57, 1.0);
  sign.rotation.x = Math.PI / 2;
  parts.push(sign);
  return parts;
}

export function buildEnvironment(): THREE.Group {
  const group = new THREE.Group();
  group.add(...room(), ...bench(), reachMarking(), ...equipment(), ...shelving());
  group.traverse((object) => object.layers.set(ENV_LAYER));
  return group;
}

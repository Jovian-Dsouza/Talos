import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { Sim } from "./sim";

const GEOM = { plane: 0, sphere: 2, capsule: 3, cylinder: 5, box: 6, mesh: 7 } as const;
const MAX_VISIBLE_GROUP = 2; // groups 3 and 4 hold collision geometry
const SKY = 0xdfe3e7;
const TILE = 0.05; // metres per checker square
const FLOOR_SIZE = 6;

export type ViewName = "main" | "top" | "side";

const PRESETS = [
  { name: "Front", position: [-0.2, -0.42, 0.42] },
  { name: "Overhead", position: [0.12, -0.05, 0.62] },
  { name: "Side", position: [0.17, -0.6, 0.1] },
] as const;
export interface Point3 {
  x: number;
  y: number;
  z: number;
}

/** Main perspective view plus two orthographic inset views drawn into one canvas. */
export class SceneView {
  readonly renderer: THREE.WebGLRenderer;
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(48, 1, 0.02, 8);
  private readonly top = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 5);
  private readonly side = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 5);
  private readonly orbit: OrbitControls;
  private readonly meshes: { object: THREE.Object3D; geom: number }[] = [];
  private readonly marker = new THREE.Group();
  private readonly ray = new THREE.Raycaster();
  private readonly insets: Record<"top" | "side", HTMLElement>;
  private preset = 0;

  constructor(private readonly canvas: HTMLCanvasElement, insets: Record<"top" | "side", HTMLElement>) {
    this.insets = insets;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.scene.background = new THREE.Color(SKY);
    this.scene.fog = new THREE.Fog(SKY, 1.4, 3.6);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(0.4, -0.3, 1.0);
    this.scene.add(sun);

    // A thin slab under the floor shows the ground as a line in the edge-on side view.
    const slab = new THREE.Mesh(new THREE.BoxGeometry(FLOOR_SIZE, FLOOR_SIZE, 0.02), new THREE.MeshBasicMaterial({ color: 0x6b7683 }));
    slab.position.z = -0.0105;
    this.scene.add(slab);

    this.camera.up.set(0, 0, 1);
    this.camera.position.set(-0.2, -0.42, 0.42);
    this.orbit = this.createOrbit();
    this.configureInsetCameras();
    this.createMarker();
    this.resize();
  }

  private createOrbit(): OrbitControls {
    const orbit = new OrbitControls(this.camera, this.canvas);
    orbit.target.set(0.17, 0.02, 0.0);
    orbit.enableDamping = true;
    orbit.dampingFactor = 0.12;
    orbit.minDistance = 0.2;
    orbit.maxDistance = 1.6;
    orbit.maxPolarAngle = Math.PI / 2 - 0.04; // stay above the floor
    // Left button is reserved for moving the gripper. Right drag orbits, shift or middle drag pans.
    orbit.mouseButtons = { LEFT: null, MIDDLE: THREE.MOUSE.PAN, RIGHT: THREE.MOUSE.ROTATE } as typeof orbit.mouseButtons;
    orbit.touches = { ONE: null, TWO: THREE.TOUCH.DOLLY_PAN } as typeof orbit.touches;
    orbit.update();
    orbit.saveState();
    // Capture phase runs before OrbitControls sees the event: orbit only from the main view.
    this.canvas.addEventListener(
      "pointerdown",
      (e) => {
        orbit.enabled = this.viewAt(e.clientX, e.clientY) === "main";
      },
      true,
    );
    return orbit;
  }

  private configureInsetCameras(): void {
    // Top view: robot at the bottom, forward (+x) up the screen, so screen right is -y.
    this.top.up.set(1, 0, 0);
    this.top.position.set(0.17, 0, 2);
    this.top.lookAt(0.17, 0, 0);
    // Side view from the robot's right: base on the left, reach (+x) to the right.
    this.side.up.set(0, 0, 1);
    this.side.position.set(0.17, -2, 0.1);
    this.side.lookAt(0.17, 0, 0.1);
  }

  private createMarker(): void {
    const material = new THREE.MeshBasicMaterial({ color: 0x1971c2, side: THREE.DoubleSide, depthTest: false });
    this.marker.add(new THREE.Mesh(new THREE.RingGeometry(0.012, 0.018, 32), material));
    this.marker.add(new THREE.Mesh(new THREE.SphereGeometry(0.006, 12, 8), material));
    this.marker.renderOrder = 10;
    this.marker.children.forEach((child) => (child.renderOrder = 10));
    this.scene.add(this.marker);
  }

  build(sim: Sim): void {
    for (const { object } of this.meshes) this.scene.remove(object);
    this.meshes.length = 0;
    const { model } = sim;
    for (let g = 0; g < model.ngeom; g++) {
      if (model.geom_group[g] > MAX_VISIBLE_GROUP) continue;
      const geometry = this.geometryFor(sim, g);
      if (!geometry) continue;
      const object = new THREE.Mesh(geometry, this.materialFor(sim, g));
      object.matrixAutoUpdate = false;
      this.scene.add(object);
      this.meshes.push({ object, geom: g });
    }
    this.update(sim);
  }

  private materialFor(sim: Sim, g: number): THREE.Material {
    const { model } = sim;
    if (model.geom_type[g] === GEOM.plane) return floorMaterial();
    const matId = model.geom_matid[g];
    const rgba = matId >= 0 ? model.mat_rgba.slice(4 * matId, 4 * matId + 4) : model.geom_rgba.slice(4 * g, 4 * g + 4);
    return new THREE.MeshStandardMaterial({
      color: new THREE.Color(rgba[0], rgba[1], rgba[2]),
      side: THREE.DoubleSide,
      roughness: 0.65,
      metalness: 0.05,
      transparent: rgba[3] < 1,
      opacity: rgba[3],
    });
  }

  private geometryFor(sim: Sim, g: number): THREE.BufferGeometry | null {
    const { model } = sim;
    const size = [model.geom_size[3 * g], model.geom_size[3 * g + 1], model.geom_size[3 * g + 2]];
    switch (model.geom_type[g]) {
      case GEOM.plane:
        return new THREE.PlaneGeometry(FLOOR_SIZE, FLOOR_SIZE);
      case GEOM.sphere:
        return new THREE.SphereGeometry(size[0], 16, 12);
      case GEOM.capsule:
        return new THREE.CapsuleGeometry(size[0], 2 * size[1], 4, 12).rotateX(Math.PI / 2);
      case GEOM.cylinder:
        return new THREE.CylinderGeometry(size[0], size[0], 2 * size[1], 20).rotateX(Math.PI / 2);
      case GEOM.box:
        return new THREE.BoxGeometry(2 * size[0], 2 * size[1], 2 * size[2]);
      case GEOM.mesh:
        return this.meshGeometry(sim, model.geom_dataid[g]);
      default:
        return null;
    }
  }

  private meshGeometry(sim: Sim, id: number): THREE.BufferGeometry {
    const { model } = sim;
    const vertStart = model.mesh_vertadr[id];
    const vertCount = model.mesh_vertnum[id];
    const faceStart = model.mesh_faceadr[id];
    const faceCount = model.mesh_facenum[id];
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.BufferAttribute(model.mesh_vert.slice(3 * vertStart, 3 * (vertStart + vertCount)), 3),
    );
    const faces = Uint32Array.from(model.mesh_face.slice(3 * faceStart, 3 * (faceStart + faceCount)));
    geometry.setIndex(new THREE.BufferAttribute(faces, 1));
    geometry.computeVertexNormals();
    return geometry;
  }

  /** Copy MuJoCo geom poses into the three.js objects. */
  update(sim: Sim): void {
    const { geom_xpos: p, geom_xmat: m } = sim.data;
    const matrix = new THREE.Matrix4();
    for (const { object, geom } of this.meshes) {
      const r = 9 * geom;
      const t = 3 * geom;
      matrix.set(m[r], m[r + 1], m[r + 2], p[t], m[r + 3], m[r + 4], m[r + 5], p[t + 1], m[r + 6], m[r + 7], m[r + 8], p[t + 2], 0, 0, 0, 1);
      object.matrix.copy(matrix);
      object.matrixWorldNeedsUpdate = true;
    }
  }

  setMarker(x: number, y: number, z: number): void {
    this.marker.position.set(x, y, z);
  }

  /** Which view is under the pointer: an inset if it is over one, otherwise the main view. */
  viewAt(clientX: number, clientY: number): ViewName {
    for (const name of ["top", "side"] as const) {
      const rect = this.insets[name].getBoundingClientRect();
      const inside = rect.width > 0 && clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom;
      if (inside) return name;
    }
    return "main";
  }

  /**
   * Gripper target implied by a pointer position in the given view. The main and top views set
   * x and y at the current height, the side view sets x and height at the current y.
   */
  targetFrom(view: ViewName, clientX: number, clientY: number, current: Point3): Point3 | null {
    const element = view === "main" ? this.canvas : this.insets[view];
    const rect = element.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return null;
    const ndc = new THREE.Vector2(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
    const camera = view === "main" ? this.camera : view === "top" ? this.top : this.side;
    this.ray.setFromCamera(ndc, camera);
    const hit = new THREE.Vector3();
    if (view === "side") {
      const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -current.y);
      return this.ray.ray.intersectPlane(plane, hit) ? { x: hit.x, y: current.y, z: hit.z } : null;
    }
    const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), -current.z);
    return this.ray.ray.intersectPlane(plane, hit) ? { x: hit.x, y: hit.y, z: current.z } : null;
  }

  resize(): void {
    const { clientWidth: w, clientHeight: h } = this.canvas;
    if (w === 0 || h === 0) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    // Keep the whole workspace in view on tall phone screens.
    this.camera.fov = w / h < 0.8 ? 62 : 48;
    this.camera.updateProjectionMatrix();
  }

  resetCamera(): void {
    this.orbit.reset();
    this.preset = 0;
  }

  /** Jump to the next camera preset and return its name. */
  cyclePreset(): string {
    this.preset = (this.preset + 1) % PRESETS.length;
    const { name, position } = PRESETS[this.preset];
    this.camera.position.set(position[0], position[1], position[2]);
    this.orbit.update();
    return name;
  }

  /** With joysticks on, a one finger touch on the main view orbits the camera. */
  setTouchOrbit(on: boolean): void {
    this.orbit.touches = { ONE: on ? THREE.TOUCH.ROTATE : null, TWO: THREE.TOUCH.DOLLY_PAN } as typeof this.orbit.touches;
  }

  /** Ground directions of "away from the camera" and "to the right of the screen", unit length. */
  groundAxes(): { forward: { x: number; y: number }; right: { x: number; y: number } } {
    // For a camera pitched down by p, look + screen-up is (cos p + sin p) times the horizontal
    // heading, so it stays well defined from level to straight down.
    const look = this.camera.getWorldDirection(new THREE.Vector3());
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(this.camera.quaternion);
    const fx = look.x + up.x;
    const fy = look.y + up.y;
    const length = Math.hypot(fx, fy) || 1;
    const forward = { x: fx / length, y: fy / length };
    return { forward, right: { x: forward.y, y: -forward.x } };
  }

  render(): void {
    this.orbit.update();
    const canvasRect = this.canvas.getBoundingClientRect();
    const { clientWidth: w, clientHeight: h } = this.canvas;
    this.renderer.setScissorTest(true);
    this.renderer.setViewport(0, 0, w, h);
    this.renderer.setScissor(0, 0, w, h);
    this.renderer.render(this.scene, this.camera);
    this.drawInset("top", this.top, 0.23, canvasRect, h);
    this.drawInset("side", this.side, 0.17, canvasRect, h);
    this.renderer.setScissorTest(false);
  }

  private drawInset(name: "top" | "side", camera: THREE.OrthographicCamera, halfHeight: number, canvasRect: DOMRect, canvasHeight: number): void {
    const rect = this.insets[name].getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;
    const aspect = rect.width / rect.height;
    camera.left = -halfHeight * aspect;
    camera.right = halfHeight * aspect;
    camera.top = halfHeight;
    camera.bottom = -halfHeight;
    camera.updateProjectionMatrix();
    const x = rect.left - canvasRect.left;
    const y = canvasHeight - (rect.top - canvasRect.top) - rect.height;
    this.renderer.setViewport(x, y, rect.width, rect.height);
    this.renderer.setScissor(x, y, rect.width, rect.height);
    this.renderer.render(this.scene, camera);
  }
}

let floorMaterialCache: THREE.MeshStandardMaterial | null = null;

/** Checkerboard floor, one square per 5 cm, so distances read at a glance in every view. */
function floorMaterial(): THREE.Material {
  if (floorMaterialCache) return floorMaterialCache;
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "#c5ccd4";
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = "#aeb7c1";
    ctx.fillRect(0, 0, size / 2, size / 2);
    ctx.fillRect(size / 2, size / 2, size / 2, size / 2);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(FLOOR_SIZE / (2 * TILE), FLOOR_SIZE / (2 * TILE));
  texture.anisotropy = 8;
  texture.colorSpace = THREE.SRGBColorSpace;
  floorMaterialCache = new THREE.MeshStandardMaterial({ map: texture, roughness: 0.95, metalness: 0 });
  return floorMaterialCache;
}

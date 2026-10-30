import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import arm from "./arm-model.json";
import { JOINTS, POSES, type JointName, type JointState } from "./joints";
import { ARM_MOUNT, WHEELS, chassisParts, makeGeometry, piParts, wheelParts, type Part } from "./robot-model";

const CAMERA = new THREE.Vector3(0.68, 0.46, 0.65);
const TARGET = new THREE.Vector3(0.03, 0.18, 0);

/** A visual robot explorer, independent of the authenticated physics simulator. */
export class RobotDemo {
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(36, 1, 0.01, 20);
  private readonly renderer: THREE.WebGLRenderer;
  private readonly orbit: OrbitControls;
  private readonly resizeObserver: ResizeObserver;
  private readonly joints = new Map<string, THREE.Group>();
  private readonly axes = new Map<string, THREE.Vector3>();
  private readonly meshGeometry = new Map<string, THREE.BufferGeometry>();
  private readonly rover = new THREE.Group();
  private values: JointState = { ...POSES.Ready };
  private active = true;
  private disposed = false;
  private frame = 0;

  constructor(private readonly canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    this.renderer.setClearColor(0xb6bec2);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.35;
    this.orbit = new OrbitControls(this.camera, canvas);
    this.orbit.enableDamping = false;
    this.orbit.enablePan = false;
    this.orbit.enableZoom = false; // Page scrolling stays available; the zoom keys control the view.
    this.orbit.minDistance = 0.45;
    this.orbit.maxDistance = 1.8;
    this.orbit.maxPolarAngle = Math.PI / 2.05;
    this.orbit.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_ROTATE };
    this.orbit.addEventListener("change", this.draw);
    this.resizeObserver = new ResizeObserver(this.draw);
    this.resizeObserver.observe(canvas);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x66737b, 2.4));
    const key = new THREE.DirectionalLight(0xffffff, 3.8);
    key.position.set(-1.5, 2.8, 2);
    const fill = new THREE.DirectionalLight(0xd8e2e8, 1.3);
    fill.position.set(2, 0.8, -1);
    this.scene.add(key, fill);
    this.rover.rotation.x = -Math.PI / 2;
    this.scene.add(this.rover);
    const floor = new THREE.Mesh(new THREE.CircleGeometry(0.48, 80), new THREE.MeshStandardMaterial({ color: 0xcbd0d2, roughness: 0.9, metalness: 0.05 }));
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.001;
    this.scene.add(floor);
    const grid = new THREE.GridHelper(1.4, 28, 0x96a2aa, 0xa7b1b6);
    grid.position.y = -0.003;
    this.scene.add(grid);
    this.resetView();
  }

  async load(): Promise<void> {
    const loader = new STLLoader();
    const names = [...new Set(arm.links.flatMap((link) => link.visuals.map((visual) => visual.mesh)))];
    const results = await Promise.allSettled(names.map(async (name) => {
      const geometry = await loader.loadAsync(`/assets/so101/assets/${name}`);
      geometry.computeVertexNormals();
      this.meshGeometry.set(name, geometry);
    }));
    if (results.some((result) => result.status === "rejected")) {
      this.dispose();
      throw new Error("Robot meshes could not be loaded.");
    }
    if (this.disposed) {
      this.meshGeometry.forEach((geometry) => geometry.dispose());
      this.meshGeometry.clear();
      return;
    }
    for (const part of [...chassisParts(), ...piParts()]) this.rover.add(this.partMesh(part));
    for (const wheel of WHEELS) {
      const group = new THREE.Group();
      group.position.fromArray(wheel.position);
      for (const part of wheelParts(wheel.handed)) group.add(this.partMesh(part));
      this.rover.add(group);
    }
    const links = new Map<string, THREE.Group>();
    const printed = new THREE.MeshStandardMaterial({ color: 0x353c41, roughness: 0.64, metalness: 0.12 });
    const motor = new THREE.MeshStandardMaterial({ color: 0x181e22, roughness: 0.48, metalness: 0.2 });
    for (const link of arm.links) {
      const group = new THREE.Group();
      group.name = link.name;
      for (const visual of link.visuals) {
        const mesh = new THREE.Mesh(this.meshGeometry.get(visual.mesh), visual.motor ? motor : printed);
        mesh.position.fromArray(visual.position);
        mesh.rotation.set(visual.rotation[0], visual.rotation[1], visual.rotation[2], "ZYX");
        group.add(mesh);
      }
      links.set(link.name, group);
    }
    for (const joint of arm.joints) {
      const origin = new THREE.Group();
      origin.position.fromArray(joint.position);
      origin.rotation.set(joint.rotation[0], joint.rotation[1], joint.rotation[2], "ZYX");
      const motion = new THREE.Group();
      origin.add(motion);
      motion.add(links.get(joint.child)!);
      links.get(joint.parent)!.add(origin);
      this.joints.set(joint.name, motion);
      this.axes.set(joint.name, new THREE.Vector3().fromArray(joint.axis));
    }
    const base = links.get("base_link")!;
    base.position.fromArray(ARM_MOUNT);
    this.rover.add(base);
    this.setPose("Ready");
    this.draw();
  }

  private partMesh(part: Part): THREE.Mesh {
    const dark = part.name.includes("roller") || part.name.includes("battery") || part.name.includes("pcb") || part.name.includes("gpio");
    const mesh = new THREE.Mesh(makeGeometry(part), new THREE.MeshStandardMaterial({
      color: dark ? 0x30383d : 0x9ca8af,
      roughness: 0.58,
      metalness: dark ? 0.05 : 0.35,
    }));
    mesh.position.fromArray(part.position);
    mesh.quaternion.fromArray(part.quaternion);
    return mesh;
  }

  setJoint(name: JointName, degrees: number): void {
    const spec = JOINTS.find((joint) => joint.name === name)!;
    this.values[name] = THREE.MathUtils.clamp(degrees, spec.min, spec.max);
    this.joints.get(name)?.quaternion.setFromAxisAngle(this.axes.get(name)!, THREE.MathUtils.degToRad(this.values[name]));
    this.draw();
  }

  setPose(name: string): JointState {
    const pose = POSES[name] ?? POSES.Ready;
    for (const joint of JOINTS) this.setJoint(joint.name, pose[joint.name]);
    return { ...this.values };
  }

  resetView(): void {
    this.camera.position.copy(CAMERA);
    this.orbit.target.copy(TARGET);
    this.orbit.update();
    this.draw();
  }

  changeView(action: string): void {
    const offset = this.camera.position.clone().sub(this.orbit.target);
    if (action === "left" || action === "right") offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), action === "left" ? -Math.PI / 8 : Math.PI / 8);
    else {
      const length = THREE.MathUtils.clamp(offset.length() * (action === "in" ? 0.85 : 1.18), 0.45, 1.8);
      offset.setLength(length);
    }
    this.camera.position.copy(this.orbit.target).add(offset);
    this.orbit.update();
    this.draw();
  }

  setActive(active: boolean): void {
    this.active = active;
    this.orbit.enabled = active;
    if (active) this.draw();
  }

  private draw = (): void => {
    if (this.frame || this.disposed || !this.active || document.hidden) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      const { clientWidth: width, clientHeight: height } = this.canvas;
      if (!width || !height || this.disposed || !this.active) return;
      this.renderer.setSize(width, height, false);
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      this.renderer.render(this.scene, this.camera);
    });
  };

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    cancelAnimationFrame(this.frame);
    this.resizeObserver.disconnect();
    this.orbit.removeEventListener("change", this.draw);
    this.orbit.dispose();
    const geometries = new Set<THREE.BufferGeometry>(this.meshGeometry.values());
    const materials = new Set<THREE.Material>();
    this.scene.traverse((object) => {
      const mesh = object as THREE.Mesh;
      if (mesh.geometry) geometries.add(mesh.geometry);
      if (mesh.material) for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) materials.add(material);
    });
    geometries.forEach((geometry) => geometry.dispose());
    materials.forEach((material) => material.dispose());
    this.meshGeometry.clear();
    this.renderer.dispose();
  }
}

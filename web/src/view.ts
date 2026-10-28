import * as THREE from "three";
import type { Sim } from "./sim";

const GEOM = { plane: 0, sphere: 2, capsule: 3, cylinder: 5, box: 6, mesh: 7 } as const;
const MAX_VISIBLE_GROUP = 2; // groups 3 and 4 hold collision geometry

export class SceneView {
  readonly renderer: THREE.WebGLRenderer;
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(48, 1, 0.02, 8);
  private readonly meshes: { object: THREE.Object3D; geom: number }[] = [];
  private readonly marker: THREE.Mesh;
  private readonly ray = new THREE.Raycaster();

  constructor(private readonly canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.scene.background = new THREE.Color(0xdfe3e7);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(0.4, -0.3, 1.0);
    this.scene.add(sun);
    this.camera.up.set(0, 0, 1);
    this.camera.position.set(-0.2, -0.42, 0.42);
    this.camera.lookAt(0.17, 0.02, 0.0);
    this.marker = new THREE.Mesh(
      new THREE.RingGeometry(0.012, 0.018, 32),
      new THREE.MeshBasicMaterial({ color: 0x1971c2, side: THREE.DoubleSide, transparent: true, opacity: 0.85 }),
    );
    this.scene.add(this.marker);
    this.resize();
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
        return new THREE.PlaneGeometry(6, 6);
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
    geometry.setIndex(new THREE.BufferAttribute(Uint32Array.from(model.mesh_face.slice(3 * faceStart, 3 * (faceStart + faceCount))), 1));
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

  /** Where the pointer's ray meets the horizontal plane at height z, or null. */
  pointOnPlane(clientX: number, clientY: number, z: number): THREE.Vector3 | null {
    const rect = this.canvas.getBoundingClientRect();
    const ndc = new THREE.Vector2(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
    this.ray.setFromCamera(ndc, this.camera);
    const hit = new THREE.Vector3();
    return this.ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 0, 1), -z), hit);
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

  render(): void {
    this.renderer.render(this.scene, this.camera);
  }
}

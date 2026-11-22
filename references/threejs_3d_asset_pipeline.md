# Three.js 3D Asset Pipeline, Shading & Render Budgets

A 3D scene is the highest-leverage visual surface in a product — and the easiest place to
burn a frame budget without noticing. This reference gives an agent everything it needs to
**create 3D assets to their full potential** and then **verify** that the result stays inside
the Plastic Surgery performance contract: zero functional regression, zero dropped frames,
zero silent asset-budget overruns.

It assumes `three` r160+ (WebGL 2), `three/addons/*` for loaders/post-processing, and a
glTF 2.0 asset pipeline. API names are read from the installed package where they could drift
(`WebGLRenderer.outputColorSpace`, `PMREMGenerator`, `BatchedMesh`, `GLTFLoader`).

> [!IMPORTANT]
> **Check the installed version before copying an API.** three.js moves fast and renames
> things. Every version claim in this document was verified against the upstream source
> tags (see §14), but the *installed* package is always the authority. If a snippet here
> throws or warns, run `node -e "import('three').then(t => console.log(t.REVISION))"` and
> diff against §14 before assuming the snippet is wrong.

---

## 1. Two Distinct 3D Modes — Decide Before Writing Code

| Mode | Trigger | Goal | Primary artefacts |
| :--- | :--- | :--- | :--- |
| **3D Asset Creation** | "Make this 3D asset", "build a model", "procedural prop", "export an asset" | Produce a *correct, reusable, budgeted* asset: geometry, UVs, PBR texture set, LODs, packed `.glb` | Source geometry + texture set + `.glb` + manifest entry |
| **3D Scene Polish** | "The scene looks flat / cheap / dark", "make this dashboard 3D" | Elevate an existing scene's lighting, materials, camera and post-processing *without* touching scene graph logic | Material/lighting/post/camera changes only |

**Zero-regression rule for 3D polish:** the scene graph, object names, `userData`, animation
clips, event payloads and asset URLs are **immutable**. Only materials, lights, tone mapping,
post-processing chain, camera parameters and renderer settings may change.

---

## 2. The End-to-End Asset Pipeline

Each stage has an explicit gate. Do not advance with a failing gate.

```text
[1 Concept & Budget]  -> [2 Blockout] -> [3 Detail & Topology] -> [4 UV & Texel Density]
        -> [5 Texture Authoring & Bake] -> [6 LOD & Rig] -> [7 Export glTF 2.0]
        -> [8 Compress & Pack] -> [9 Runtime Load & Validate] -> [10 Frame-Budget Audit]
```

### Stage 1 — Concept & Budget (before any polygon exists)

Write the budget *first*; it is a contract, not an aspiration.

| Tier | Target device | Visible triangles | Draw calls | Texture VRAM | Max texture size | Shadow maps |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Low** | Mid-range mobile / WebGL fallback | `<= 60 k` | `<= 80` | `<= 64 MB` | `1024` | `1 x 1024` |
| **Medium** | Modern mobile / integrated desktop GPU | `<= 300 k` | `<= 250` | `<= 256 MB` | `2048` | `1-2 x 2048` |
| **High** | Discrete desktop GPU | `<= 1.5 M` | `<= 1000` | `<= 512 MB` | `4096` | `2 x 2048` |

Pick the tier from the **Alignment Gate** (Phase 0): *Mobile/Desktop* decides the triangle and
texture ceilings, *Private/Commercial* decides how much hand-authoring time is justified,
*Adult/All audiences* decides stylisation vs. realism.

### Stage 2-3 — Blockout, Detail & Topology

- **Silhouette first.** Read the asset as a solid black shape on white. If the silhouette is
  not identifiable, no amount of texture will save it.
- **Chamfer every hard edge.** A `2-3%` bevel on 90° edges is the single highest-value
  realism multiplier on hard-surface assets — it creates the specular highlight that makes
  edges read as metal/plastic instead of as flat polygons.
- **Density follows screen size, not artistic intent.** Hero assets get the triangles;
  background props get almost none.
- **Triangle budget per object** (Medium tier): hero prop `8 k - 25 k`, mid prop `1 k - 5 k`,
  background prop `<= 500`, vegetation/scatter `<= 60` per instance.
- **Triangulate on export**, not before — keep quads in the source for clean topology.

### Stage 4 — UV & Texel Density

- **Texel density** = pixels per world unit. Keep it *consistent within an asset* and
  *consistent across an asset set*. Common targets: `1024 px/m` for props/characters,
  `2048 px/m` for hero pieces, `512 px/m` for environment kits.
- Use a **single UV island per material slot** where possible; seams destroy mip coherence.
- **Padding**: `4-8 px` gutter on 1024² maps; without it, mip level 3-4 bleeds across islands
  and the asset looks like it has dirt rings.
- Reserve **UV0** for the PBR set and **UV1** for lightmaps if baking GI.

### Stage 5 — Texture Authoring & Bake

The glTF 2.0 metallic-roughness PBR set:

| Map | Channel layout | Color space | Notes |
| :--- | :--- | :--- | :--- |
| **Base colour** | RGB | **sRGB** | Bake AO into it only if you also author an AO map |
| **Normal** | RGB (OpenGL, +Y up) | **Linear** | Tangent-space; glTF expects OpenGL convention |
| **ORM** | R = Occlusion, G = Roughness, B = Metallic | **Linear** | One texture, three channels — halves the map count |
| **Emissive** | RGB | **sRGB** | Only if the asset emits |

- **Never bake lighting into albedo.** Bake ambient occlusion, not directional light. Direct
  light belongs to the runtime scene, not the asset.
- **Roughness is the realism dial.** Polished metal `0.15-0.25`, painted plastic `0.35-0.5`,
  rubber `0.8-0.95`. Uniform roughness reads as plastic; subtle roughness variation reads as
  material.
- **Normal map convention:** glTF/OpenGL is **+Y up (green)**. Blender exports OpenGL by
  default; DirectX-style (+Y down) normal maps must be flipped in green channel.

### Stage 6 — LOD & Rig

| LOD | Triangle share of LOD0 | Switch distance (Medium tier) | Textures |
| :--- | :--- | :--- | :--- |
| LOD0 | 100 % | `0` | Full set |
| LOD1 | ~40 % | `~8 m` | Half-res (`1024`) set |
| LOD2 | ~15 % | `~20 m` | Quarter-res (`512`) set, or unlit baked |

- LODs must keep the **same material slots** so they can share a material instance and batch.
- Skinned assets: cap bones (`<= 60` for props, `<= 100` for characters) and never skin more
  than ~4 influences per vertex.

### Stage 7-8 — Export, Compress & Pack

Export as **glTF 2.0 binary (`.glb`)**. Always:

1. `+Y up`, **meters**, **-Z forward** glTF convention (three.js is Y-up too — no axis fix needed).
2. **Apply transforms** before export (no leftover scale/rotation on nodes) — negative scale
   flips normals and tangents.
3. Triangulate; keep normals and tangents consistent.
4. Compress geometry (**Draco** or **meshopt**) and textures (**KTX2 / UASTC or ETC1S**).

```bash
# Validate then optimise (gltf-transform is the reference CLI)
npx @gltf-transform/cli validate model.glb
npx @gltf-transform/cli inspect model.glb

# Geometry compression: --compress draco | meshopt
# Texture compression:  --texture-compress webp | avif | ktx2  (+ --texture-size)
# KTX2 encoding shells out to KTX-Software (`toktx`) — install it before using it.
npx @gltf-transform/cli optimize in.glb out.glb \
  --compress meshopt --texture-compress ktx2 --texture-size 2048
```

**Compression trade-offs:**

| Codec | Geometry gain | Cost | Use when |
| :--- | :--- | :--- | :--- |
| Uncompressed | — | Baseline | Dev iteration only |
| **Draco** | `~50-70 %` | Decode hitch on first load, `~30 ms/MB` | Static meshes, load-once scenes |
| **meshopt** (`EXT_meshopt_compression`) | `~40-60 %` | GPU-friendly, faster decode | Mobile / streamed scenes (preferred) |

Texture codec choice per platform: **KTX2 + UASTC** (high quality, universal), **ETC1S**
(smallest, slight quality loss), **BC7/ASTC** (desktop/Apple GPUs, large but fast).

---

## 3. glTF 2.0 Runtime Contract in Three.js

```ts
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

/**
 * One loader for the whole app: Draco + meshopt + KTX2 wired in.
 * A loader without a decoder silently inflates payload by 3-10x.
 */
export function createAssetLoader(renderer: THREE.WebGLRenderer) {
  const draco = new DRACOLoader().setDecoderPath('/draco/');
  const ktx2 = new KTX2Loader().setTranscoderPath('/basis/').detectSupport(renderer);
  const loader = new GLTFLoader()
    .setDRACOLoader(draco)
    .setKTX2Loader(ktx2)
    .setMeshoptDecoder(MeshoptDecoder);
  return { loader, dispose: () => { draco.dispose(); ktx2.dispose(); } };
}
```

**Runtime rules after load:**

```ts
const gltf = await loader.loadAsync('/assets/hero.glb');
const root = gltf.scene;

// 1. Texture colour space is the #1 asset bug. glTF loader already sets
//    sRGB on base colour/emissive and Linear on normal/ORM — never override it.
root.traverse((obj) => {
  const mesh = obj as THREE.Mesh;
  if (!mesh.isMesh) return;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.frustumCulled = true;
  // 2. Recompute bounds after any runtime geometry edit, or the object
  //    culls incorrectly and pops in/out at screen edges.
  mesh.geometry.computeBoundingSphere();
  // 3. Static objects: stop recomputing matrices every frame.
  mesh.updateMatrix();
  mesh.matrixAutoUpdate = false;
});
```

**glTF extensions worth knowing** (and their three.js support):
`KHR_texture_transform` (UV tiling), `KHR_materials_emissive_strength` (HDR emissives),
`KHR_materials_clearcoat` / `sheen` / `transmission` / `iridescence` / `ior` / `volume`,
`KHR_materials_unlit`, `KHR_lights_punctual`, `KHR_draco_mesh_compression`,
`KHR_texture_basisu`, `EXT_meshopt_compression`, `EXT_texture_webp`, `MSFT_lod`.

---

## 4. Procedural Asset Creation in Three.js

Procedural assets are *first-class* assets here: they are code, so they are reviewable,
diffable, and can be parameterised by quality tier.

### 4.1 Lathe / Extrude / Shape — parametric hard-surface props

```ts
/** A vase/bottle profile authored as Vector2 points, revolved into a solid. */
export function latheProfile(points: Array<[number, number]>, segments = 64): THREE.BufferGeometry {
  const profile = points.map(([x, y]) => new THREE.Vector2(x, y));
  const geo = new THREE.LatheGeometry(profile, segments);
  geo.computeVertexNormals();
  geo.computeBoundingSphere();
  return geo;
}

/** Extrude a 2D profile with a bevel — the bevel is what sells the edge highlight. */
export function beveledExtrude(shape: THREE.Shape, depth = 0.2, bevel = 0.01): THREE.BufferGeometry {
  const geo = new THREE.ExtrudeGeometry(shape, {
    depth,
    bevelEnabled: bevel > 0,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 3,
    curveSegments: 24,
  });
  geo.center();
  geo.computeVertexNormals();
  geo.computeBoundingSphere();
  return geo;
}
```

### 4.2 Merge & batch — draw-call reduction

```ts
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

/** Merge static geometries that share a material. Merge BEFORE adding to the scene. */
export function mergeStatic(geos: THREE.BufferGeometry[]): THREE.BufferGeometry {
  const merged = mergeGeometries(geos, false);
  geos.forEach((g) => g.dispose());
  merged.computeBoundingSphere();
  return merged;
}

/** Many different geometries, one material, one draw call (three r159+).
 *  NOTE: the first constructor argument was renamed across versions —
 *  r159-r165 take `maxGeometryCount`, r166+ take `maxInstanceCount`.
 *  Check the signature in the installed package before copying. */
export function batchedMesh(
  geometries: THREE.BufferGeometry[],
  material: THREE.Material,
  maxInstances: number
): THREE.BatchedMesh {
  // The vertex/index budget must cover ALL geometries combined.
  const maxVertexCount = geometries.reduce((n, g) => n + g.attributes.position.count, 0);
  const maxIndexCount = geometries.reduce(
    (n, g) => n + (g.index ? g.index.count : g.attributes.position.count),
    0
  );

  const batched = new THREE.BatchedMesh(
    maxInstances,      // r166+ (r159-r165: maxGeometryCount)
    maxVertexCount,
    maxIndexCount,
    material           // the material is a constructor argument, not setMaterialAt()
  );

  geometries.forEach((geo) => {
    const geometryId = batched.addGeometry(geo);
    const instanceId = batched.addInstance(geometryId);
    batched.setMatrixAt(instanceId, new THREE.Matrix4());
  });

  return batched;
}
```

> **Merge rule:** merge only geometries that share a **material instance** and are **static**.
> Merging skinned or animated geometry breaks the skeleton.

### 4.3 Instancing — repeated assets (foliage, rocks, rivets, crowds)

```ts
export function scatterInstances(
  geometry: THREE.BufferGeometry,
  material: THREE.Material,
  transforms: Array<{ position: THREE.Vector3; rotation: THREE.Euler; scale: THREE.Vector3 }>
): THREE.InstancedMesh {
  const mesh = new THREE.InstancedMesh(geometry, material, transforms.length);
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const s = new THREE.Vector3();
  const p = new THREE.Vector3();

  transforms.forEach((t, i) => {
    p.copy(t.position);
    q.setFromEuler(t.rotation);
    s.copy(t.scale);
    m.compose(p, q, s);
    mesh.setMatrixAt(i, m);
  });

  mesh.instanceMatrix.needsUpdate = true;
  // CRITICAL: InstancedMesh frustum-culls against the base geometry's bounds.
  // If instances are scattered far from the origin, recompute or disable culling.
  mesh.computeBoundingSphere();
  return mesh;
}
```

### 4.4 LOD — distance-based detail swap

```ts
export function buildLOD(lod0: THREE.Object3D, lod1: THREE.Object3D, lod2: THREE.Object3D): THREE.LOD {
  const lod = new THREE.LOD();
  lod.addLevel(lod0, 0);
  lod.addLevel(lod1, 8);
  lod.addLevel(lod2, 20);
  lod.autoUpdate = true; // per-frame distance check; cheap
  return lod;
}
```

- The third `addLevel()` argument is **hysteresis** (a distance band that prevents
  LOD thrash when the camera sits exactly on a switch distance).
- Chamfered geometry has a first-class addon: `RoundedBoxGeometry` from
  `three/addons/geometries/RoundedBoxGeometry.js` — use it instead of a raw `BoxGeometry`
  when the asset needs the edge highlight that makes PBR read as real.

### 4.5 Morph targets, skinning, curves

- **Morph targets** (glTF `mesh.primitives[].targets`) drive facial blendshapes and
  procedural deformation. Keep the count low (`<= 8` for props, `<= 52` for ARKit blendshapes)
  and remember every morph target multiplies vertex-shader cost.
- **Skinning** (`Skeleton`, `SkinnedMesh`) — bind pose must be the rest pose. Animate via
  `AnimationMixer`; never mutate `bone.position` per frame alongside a mixer, or the two fight.
- **Curves** (`CatmullRomCurve3`, `TubeGeometry`) — `tubeSegments` should be
  `~8 x` the number of control points, `radialSegments >= 8`, else the tube shows facets.

### 4.6 Terrain & procedural geometry

**Terrain is a displaced plane, not an isosurface.** Marching cubes generates an *isosurface*
of a scalar field — it is the right tool for blobs and organic volumes, and the wrong tool
for a heightmap.

```ts
import { ImprovedNoise } from 'three/addons/math/ImprovedNoise.js';

/** A heightmap-displaced terrain mesh. 1 unit = 1 metre. */
export function buildTerrain(
  size = 200,
  segments = 128,
  material: THREE.Material
): THREE.Mesh {
  const geo = new THREE.PlaneGeometry(size, size, segments, segments);
  geo.rotateX(-Math.PI / 2); // lie flat; the plane starts in XY

  const noise = new ImprovedNoise();
  const pos = geo.attributes.position as THREE.BufferAttribute;
  const v = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    const h =
      noise.noise(v.x * 0.01, 0, v.z * 0.01) * 8 +
      noise.noise(v.x * 0.04, 0, v.z * 0.04) * 2;
    pos.setY(i, h);
  }
  pos.needsUpdate = true;
  geo.computeVertexNormals();
  geo.computeBoundingSphere();
  return new THREE.Mesh(geo, material);
}
```

> **Budget note:** `segments = 128` means `128 x 128 x 2 = 32 768` triangles — fine for one
> terrain tile, fatal for ten. Keep the *total* scene under the tier's triangle budget
> (see §2) and use an instanced or LOD'd tile system rather than one giant mesh.

**Marching cubes** (`MarchingCubes` from `three/addons/objects/MarchingCubes.js`) is for
isosurfaces — metaballs, blobs, dissolved shapes:

```ts
import { MarchingCubes } from 'three/addons/objects/MarchingCubes.js';

export function buildBlobs(material: THREE.Material): MarchingCubes {
  const field = new MarchingCubes(32, material, false, false, 100_000);
  field.isolation = 80;

  field.reset();
  field.addBall(0.5, 0.5, 0.5, 0.6, 12);   // x, y, z, strength, subtract
  field.addBall(0.62, 0.5, 0.5, 0.4, 12);
  field.update();
  return field;
}
```

> **Budget note:** marching cubes allocates the **whole grid up front**, and the vertex
> buffer is sized by `maxPolyCount` — not by how much geometry you actually generate.
> Measured on three r187: two metaballs produced **1 128 polygons** but the buffer was
> allocated for **100 000 triangles** (because `maxPolyCount: 100_000`). The grid itself
> scales as `resolution^3`: `32` → `32 768` cells, `64` → `262 144`, `128` → `2.1 M` and
> VRAM death. The upstream comment says "32 is pushing it in Javascript".
> Always re-check `renderer.info.render.triangles` after generating, and size
> `maxPolyCount` to the output you actually expect.

### 4.7 3D text & labels

```ts
import { FontLoader } from 'three/addons/loaders/FontLoader.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';

const font = await new FontLoader().loadAsync('/fonts/inter.typeface.json');
const label = new THREE.Mesh(
  new TextGeometry('NODE 07', { font, size: 0.4, depth: 0.08, curveSegments: 8 }),
  new THREE.MeshStandardMaterial({ color: 0xdfe6f0, roughness: 0.45, metalness: 0.1 })
);
label.geometry.computeBoundingSphere();
```

- `depth: 0` gives a flat extrusion (one quad per glyph outline) — cheap but the side
  walls disappear at grazing angles. `depth >= 0.05` gives readable side walls.
- Text geometry is a **static** mesh: it never needs to be re-tessellated. Do not rebuild
  it per frame; swap the geometry only when the string changes.
- For UI-style labels in 3D, prefer `CSS2DRenderer` / `CSS3DRenderer` — the DOM gives you
  crisp text, real accessibility, and zero triangle cost.

### 4.8 glTF material variants (product configurators)

`KHR_materials_variants` lets one asset ship multiple material sets (colourways, materials)
without duplicating geometry — the single highest-value extension for a configurator.

> [!IMPORTANT]
> **three's core `GLTFLoader` does NOT implement `KHR_materials_variants`.** It is one of
> the extensions that are *"supported by separately registered plugins"*. Without the
> plugin the loader silently ignores the extension and every variant renders as the
> default material — no error, no warning.

```ts
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
// Optional plugin (not part of three core):
// import { GLTFMeshStandardMaterialVariants } from 'three-gltf-extensions';

const loader = new GLTFLoader();
// loader.register((parser) => new GLTFMeshStandardMaterialVariants(parser));

const gltf = await loader.loadAsync('/assets/product.glb');
const root = gltf.scene;

// After the plugin is registered, variants are exposed per mesh:
type VariantSet = { variants: Array<{ materials: number[] }> };

root.traverse((obj) => {
  const mesh = obj as THREE.Mesh;
  const variants = mesh.userData.gltfExtensions?.KHR_materials_variants as VariantSet | undefined;
  if (!variants) return;
  const variant = variants.variants[0];          // first colourway
  const materials = mesh.material as THREE.Material[];
  variant.materials.forEach((materialIndex: number, primitiveIndex: number) => {
    materials[primitiveIndex] = root.userData.materials[materialIndex];
  });
});
```

> Always verify the extension actually applied: if `userData.gltfExtensions` is absent, the
> plugin is not registered. **Check it, do not assume it.**

---

## 5. Materials, Colour Management & Environment Lighting

### 5.1 Material selection

| Material | Cost | Use for |
| :--- | :--- | :--- |
| `MeshBasicMaterial` | Cheapest | Unlit/baked assets, HUD-like billboards |
| `MeshLambertMaterial` | Cheap | Non-PBR fallback for low tier |
| `MeshStandardMaterial` | **Default** | 95 % of surfaces — full metal/rough PBR |
| `MeshPhysicalMaterial` | +shader cost | Clearcoat, transmission, sheen, iridescence, anisotropy |
| `MeshToonMaterial` / `MeshMatcapMaterial` | Cheap | Stylised; matcap = zero lights, zero env |

**Rule:** reach for `MeshPhysicalMaterial` only when the effect is visible in the shot.
Transmission in particular is *not* free — it re-renders the scene into a transmission render
target every frame. Mitigate it with `renderer.transmissionResolutionScale = 0.5` (r175+),
or drop transmission for a simple alpha-blended material on the Low tier.

### 5.2 Colour management (the most common 3D "why is it washed out" bug)

```ts
renderer.outputColorSpace = THREE.SRGBColorSpace;  // display-referred output (default in r152+)
renderer.toneMapping = THREE.ACESFilmicToneMapping; // or AgX / Neutral
renderer.toneMappingExposure = 1.0;

// Texture colour spaces — the loader does this for you; only do it manually for
// textures you create in code:
const albedo = new THREE.TextureLoader().load('/albedo.png');
albedo.colorSpace = THREE.SRGBColorSpace;    // colour data
const orm = new THREE.TextureLoader().load('/orm.png');
orm.colorSpace = THREE.NoColorSpace;         // data (roughness/metallic/AO/normal)
```

**The rules that matter:**

1. **sRGB for colour, Linear for data.** Albedo, emissive and specular-tint textures are sRGB.
   Normal, roughness, metallic, AO, ORM are linear (a.k.a. `NoColorSpace`).
2. **Double conversion is the classic bug**: marking an sRGB PNG as linear makes it look
   washed out; loading it twice-converted makes it look crushed. Symptom: the asset looks
   *lighter and lower-contrast* than in Blender.
3. **Tone mapping happens once.** If you use `EffectComposer`, end the chain with `OutputPass`
   — it applies tone mapping *and* the sRGB conversion. Adding a manual `LinearToSRGB` pass
   on top of `OutputPass` double-converts.
4. **Colours set in code are sRGB by default** (`new THREE.Color('#ff8800')` is converted for
   you). Do not pre-convert hex values yourself.

### 5.3 Environment lighting (Ibl) — the cheapest realism upgrade

```ts
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const pmrem = new THREE.PMREMGenerator(renderer);
pmrem.compileEquirectangularShader();

// Option A — studio HDRI (a .hdr/.exr equirectangular):
const hdr = pmrem.fromEquirectangular(hdrTexture).texture;

// Option B — zero-asset studio rig (procedural room, shipped with three):
const room = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

scene.environment = room;             // lights PBR surfaces
scene.environmentIntensity = 1.0;      // r163+
scene.background = room;               // optional
scene.backgroundBlurriness = 0.6;      // r158+ — blurred backdrop, no visible seams
scene.backgroundIntensity = 0.4;       // keep the backdrop subordinate to the subject
```

> **Always dispose the PMREM generator** (`pmrem.dispose()`) after generating environments,
> and dispose the source HDR texture. PMREM render targets are GPU memory.

---

## 6. Lighting & Shadows

Three.js has used **physically-correct lighting by default since r155** (`useLegacyLights`
removed in r165). Intensities are no longer arbitrary "look" numbers.

| Light | Unit | Typical intensity | Notes |
| :--- | :--- | :--- | :--- |
| `AmbientLight` | Radiance-ish | `0.2 - 1.0` | Flat filler; use sparingly, kills form |
| `HemisphereLight` | — | `0.5 - 2.0` | Cheap sky/ground tint, good for outdoor |
| `DirectionalLight` | Irradiance | `1.0 - 3.0` (sun) | The workhorse; **shadows** are its job |
| `PointLight` | Candela | `10 - 500` | Physical falloff, `decay = 2` |
| `SpotLight` | Candela | `50 - 2000` | Needs `angle`, `penumbra`, `decay = 2` |
| `RectAreaLight` | — | `1 - 10` | Needs `RectAreaLightUniformsLib.init()`; **no shadows** |

**Shadow discipline** (shadows are the #1 cost in a 3D scene):

> [!WARNING]
> **`THREE.PCFSoftShadowMap` was removed in r186.** Setting it now logs
> `WebGLShadowMap: PCFSoftShadowMap has been removed. Using PCFShadowMap instead.`
> and silently falls back. Use `THREE.PCFShadowMap` and control softness with
> `shadow.radius` (the PCF sampling spread). `THREE.VSMShadowMap` still exists
> but bleeds and is slower.

```ts
const sun = new THREE.DirectionalLight(0xffffff, 2.5);
sun.position.set(6, 10, 4);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);       // 1024 on Low tier
sun.shadow.camera.near = 0.5;
sun.shadow.camera.far = 60;
sun.shadow.camera.left = -20;              // TIGHT frustum — a loose frustum wastes resolution
sun.shadow.camera.right = 20;
sun.shadow.camera.top = 20;
sun.shadow.camera.bottom = -20;
sun.shadow.bias = -0.0004;                 // detaches shadow acne
sun.shadow.normalBias = 0.02;             // detaches peter-panning (scale with unit size!)
sun.shadow.radius = 2;                    // PCF spread — this is the "softness" control now
scene.add(sun);
```

- **One shadow-casting light** is usually enough. A second caster doubles the shadow render
  passes (each shadow map is a full scene re-render).
- **Static scenes: stop re-rendering shadow maps.** Set `renderer.shadowMap.autoUpdate = false`
  and flip `renderer.shadowMap.needsUpdate = true` only when the light or geometry changes.
  This alone can halve the frame time of a static scene.
- **Baked GI for static environments**: bake lightmaps in the source tool and ship them as
  `emissive` + `lightMap` (`uv1` in glTF). At runtime use a `LightProbeGenerator` for
  dynamic probes.
- **`normalBias` must scale with your world scale.** If the scene is authored at `0.01`
  scale (glTF centimetres), `normalBias = 0.02` is larger than the object.

---

## 6.5 Shader Customisation — Stylising Without Breaking PBR

`MeshStandardMaterial` covers most work, but stylisation needs shader control. There are
three levels of intervention; use the least invasive one that works.

### Level 1 — `onBeforeCompile` (patch the existing PBR shader)

Keeps all of three.js's lighting, shadows, fog and tone mapping. Use this for
stylised ramp lighting, outlines, or a custom dissolve.

```ts
import * as THREE from 'three';

export function applyRampLighting(material: THREE.MeshStandardMaterial, steps = 4): void {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uSteps = { value: steps };
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>
         uniform float uSteps;`
      )
      .replace(
        '#include <dithering_fragment>',
        `#include <dithering_fragment>
         // Quantise the outgoing light into bands for a stylised look.
         gl_FragColor.rgb = floor(gl_FragColor.rgb * uSteps + 0.5) / uSteps;`
      );
  };
  // Force a shader recompile so onBeforeCompile takes effect.
  material.needsUpdate = true;
}
```

> **The `needsUpdate = true` trap:** assigning `onBeforeCompile` after the material has
> already been compiled has no effect until the shader is rebuilt. Always set
> `material.needsUpdate = true` afterwards, and remember this costs one extra shader
> compile (a visible hitch on first frame).

### Level 2 — `ShaderMaterial` / `RawShaderMaterial` (full control, full cost)

You own lighting entirely: no automatic shadows, fog, or tone mapping. Use for
non-photorealistic effects (energy fields, holographic shaders, stylised water).

```ts
const material = new THREE.ShaderMaterial({
  uniforms: {
    uTime: { value: 0 },
    uColor: { value: new THREE.Color(0x44aaff) },
  },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: /* glsl */`
    uniform float uTime;
    uniform vec3 uColor;
    varying vec2 vUv;
    void main() {
      float wave = sin(vUv.y * 12.0 - uTime * 2.0) * 0.5 + 0.5;
      gl_FragColor = vec4(uColor * wave, 1.0);
    }
  `,
});
```

- **Do not forget `#include <tonemapping_fragment>` and `#include <colorspace_fragment>`**
  if the material should participate in the scene's tone mapping and colour pipeline.
  Without them the material will look "not quite right" against PBR neighbours.
- Set `material.toneMapped = true` (the default) so the renderer applies its tone mapping.

### Level 3 — Node materials / TSL (three's forward-looking path)

three.js now ships **TSL (Three Shading Language)** and node materials used by the
`WebGPURenderer` path. The same scene graph, materials and lights, but the material graph
is built in JS instead of GLSL.

```ts
import { WebGPURenderer } from 'three/webgpu';
import { MeshStandardNodeMaterial } from 'three/webgpu';
import { uv, fract, mix, vec3 } from 'three/tsl';

const renderer = new WebGPURenderer({ antialias: true });
await renderer.init();

const material = new MeshStandardNodeMaterial();
// Stripe the surface: fract() of a tiled UV, mixed between two colours.
material.colorNode = mix(vec3(0.1, 0.2, 0.4), vec3(0.9, 0.95, 1.0), fract(uv().x.mul(12)));
```

**The TSL API is small and specific:** node maths is exposed as *functions*
(`fract`, `mod`, `mix`, `float`, `vec3`, …) imported from `three/tsl`, plus chainable
methods on the resulting nodes (`.mul()`, `.add()`, `.oneMinus()`). There is **no
`.remainder()`** — the modulo operation is `mod(a, b)` or the `.mod(b)` method.

**Practical guidance:**

| | WebGL (`WebGLRenderer`) | WebGPU (`WebGPURenderer`) |
| :--- | :--- | :--- |
| Browser support | Universal | Chrome/Edge stable; Safari and Firefox still catching up |
| Fallback | — | `WebGPURenderer` has a WebGL2 fallback backend |
| Node materials / TSL | Limited | Full |
| Best for | Maximum compatibility, mobile | Compute-heavy effects, new features |

> **Do not adopt WebGPU/TSL on a compatibility-constrained project** without an explicit
> product decision. Keep the scene graph and assets portable; treat the renderer choice as
> a runtime decision, not an architecture decision.

---

## 7. Post-Processing Chain (correct order or wrong colours)

```ts
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { SSAOPass } from 'three/addons/postprocessing/SSAOPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const target = new THREE.WebGLRenderTarget(w, h, {
  type: THREE.HalfFloatType, // HDR pipeline — required for correct bloom
  samples: 4,                // WebGL2 MSAA (antialias:true does NOT apply to RTs)
});

const composer = new EffectComposer(renderer, target);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(ssaoPass);            // contact darkening — do this BEFORE bloom
composer.addPass(bloomPass);           // UnrealBloomPass: threshold 0.85+, strength 0.3-0.8
composer.addPass(new SMAAPass());       // anti-alias AFTER post (no ctor args; sized via setSize)
composer.addPass(new OutputPass());    // tone mapping + sRGB — ALWAYS LAST
```

**Post-processing rules:**

| Rule | Why |
| :--- | :--- |
| `OutputPass` last, exactly once | Tone mapping + colour space happen there |
| HalfFloat render target | 8-bit targets clip HDR highlights and bloom fails |
| MSAA via `samples` on the target | `antialias: true` only affects the default framebuffer |
| Bloom threshold `>= 0.8` | Low thresholds smear the whole frame into a haze |
| SSAO/GTAO before bloom | AO darkening must not be bloomed |
| Cap post at 3 passes | Each pass is a full-screen blit; mobile dies at 4+ |
| Skip post entirely on Low tier | Post is the first thing to cut, not geometry |

---

## 8. Runtime Performance Discipline

### 8.1 The renderer contract

```ts
export function createRenderer(container: HTMLElement): THREE.WebGLRenderer {
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    powerPreference: 'high-performance',
    stencil: false,          // not needed unless you do stencil tricks
    alpha: false,            // opaque canvas is cheaper
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)); // clamp [1, 2]
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap; // PCFSoftShadowMap was REMOVED in r186
  container.appendChild(renderer.domElement);
  return renderer;
}
```

### 8.2 Resize, visibility, and on-demand rendering

```ts
const onResize = () => {
  const w = container.clientWidth;
  const h = container.clientHeight;
  camera.aspect = w / Math.max(h, 1);
  camera.updateProjectionMatrix();
  renderer.setSize(w, h, false);   // false = do not touch the CSS size of the canvas
};
window.addEventListener('resize', onResize);

// Pause when the tab or the container is not visible.
const io = new IntersectionObserver(([entry]) => {
  running = entry.isIntersecting && !document.hidden;
}, { threshold: 0 });
io.observe(container);
```

- **On-demand rendering** — for a scene that only changes on interaction, render on demand:

```ts
let dirty = true;
export const invalidate = () => { dirty = true; };
renderer.setAnimationLoop(() => {
  if (!dirty) return;   // skip the whole frame
  dirty = false;
  renderer.render(scene, camera);
});
```

### 8.3 Disposal (memory leaks are invisible until the tab is resized 50 times)

```ts
export function disposeObject(root: THREE.Object3D): void {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  const textures = new Set<THREE.Texture>();

  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (mesh.geometry) geometries.add(mesh.geometry);
    const mat = mesh.material as THREE.Material | THREE.Material[] | undefined;
    if (Array.isArray(mat)) mat.forEach((m) => materials.add(m));
    else if (mat) materials.add(mat);
  });

  materials.forEach((m) => {
    // material.dispose() does NOT dispose its textures
    for (const key of Object.keys(m)) {
      const value = (m as unknown as Record<string, unknown>)[key];
      if (value instanceof THREE.Texture) textures.add(value);
    }
    m.dispose();
  });
  textures.forEach((t) => t.dispose());
  geometries.forEach((g) => g.dispose());
  root.parent?.remove(root);
}
```

**Every** `scene.remove(obj)` in a SPA must be paired with `disposeObject(obj)`; every
`new THREE.TextureLoader().load(...)` must be paired with `texture.dispose()`.

### 8.4 The budget harness (the 3D equivalent of the preflight linter)

```ts
export interface RenderBudget {
  maxDrawCalls: number;
  maxTriangles: number;
  maxFrameMs: number;
  maxTextureMB: number;
}

/** Call every N frames in dev; assert in CI against a headless render. */
export function auditRender(
  renderer: THREE.WebGLRenderer,
  budget: RenderBudget
): string[] {
  const violations: string[] = [];
  const { calls, triangles } = renderer.info.render;
  const { geometries, textures } = renderer.info.memory;

  if (calls > budget.maxDrawCalls) {
    violations.push(`draw calls ${calls} > ${budget.maxDrawCalls}`);
  }
  if (triangles > budget.maxTriangles) {
    violations.push(`triangles ${triangles} > ${budget.maxTriangles}`);
  }
  if (geometries > 512) violations.push(`geometry count ${geometries} > 512 (leak?)`);
  if (textures > 128) violations.push(`texture count ${textures} > 128 (leak?)`);
  return violations;
}
```

`renderer.info.render.calls` and `.triangles` are **per-frame** counters reset on each
`render()`; `renderer.info.memory.geometries` / `.textures` are **cumulative** and are the
leak detectors.

---

## 9. Motion, Cameras & Reduced Motion in 3D

- **Frame-rate independence applies to 3D too.** Use `delta = clock.getDelta()` and the
  `expDecay()` / sub-stepped spring helpers from `kinetic_physics_and_springs.md` for
  camera damping and object interpolation. A fixed `lerp(a, b, 0.1)` per frame rotates the
  camera twice as fast on a 120 Hz display.
- **Clamp the delta**: `const dt = Math.min(clock.getDelta(), 0.1)` — a backgrounded tab
  returns a multi-second delta that teleports the camera.
- **Prefer `AnimationMixer`** with `THREE.AnimationUtils.makeClipAdditive()` for layering
  (e.g. base locomotion + additive look-at).
- **Reduced motion is a hard requirement**, not a nice-to-have:

```ts
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const applyMotionPreference = () => {
  const reduced = reduceMotion.matches;
  autoRotate.enabled = !reduced;        // kill orbit drift
  cameraDamping.enabled = !reduced;     // kill idle drift
  // keep essential state changes legible, but instantaneous
};
reduceMotion.addEventListener('change', applyMotionPreference);
applyMotionPreference();
```

- **Camera discipline:** `camera.near` should be as large as safely possible (e.g. `0.1` not
  `0.001`) — the depth buffer precision is a function of the near/far ratio. Keep
  `far / near` under `~10^4` for a 24-bit depth buffer.

---

## 10. Verification Harness (how an agent proves the 3D work is good)

| Gate | Method | Pass criterion |
| :--- | :--- | :--- |
| **Asset validity** | `gltf-transform validate` | No errors; warnings reviewed |
| **Triangle / draw-call budget** | `renderer.info` after a representative frame | Within tier table (§2, Stage 1) |
| **Texture memory** | `renderer.info.memory.textures` + asset manifest | `<= tier VRAM ceiling` |
| **Frame time** | `performance.now()` around `render()` over 120 frames | p95 `<= 16.67 ms` @ 60 Hz |
| **Colour correctness** | Render a known swatch scene; compare to reference | No washed-out/crushed output |
| **Shadow acne** | Screenshot at grazing light angles | No banding/moiré on curved surfaces |
| **Camera framing** | Screenshot at 3 aspect ratios (`16:9`, `4:3`, `9:16`) | Subject framed, no clipping |
| **Leak check** | Toggle the scene 20x; watch `renderer.info.memory` | Geometry/texture counts stable |
| **Reduced motion** | Emulate `prefers-reduced-motion: reduce` | No auto-rotation / idle drift |
| **Static lint** | `python3 scripts/preflight_visual_lint.py .` | Zero HIGH findings (incl. `THREE_*` rules) |

**Headless screenshot recipe** (used for CI and for the agent's own eyes):

```ts
renderer.render(scene, camera);
const url = renderer.domElement.toDataURL('image/png'); // call immediately after render,
// or construct the renderer with preserveDrawingBuffer: true
```

---

## 11. Pitfalls (ranked by how often they actually bite)

1. **sRGB / linear confusion.** Marking an sRGB albedo as linear (or vice-versa) is the
   single most common "the render looks wrong" cause. Symptom: washed out, low contrast.
2. **Tone mapping applied twice.** With `EffectComposer`, `OutputPass` must be last and
   `renderer.toneMapping` must not be double-applied by another pass.
3. **Unclamped `devicePixelRatio`.** `setPixelRatio(window.devicePixelRatio)` on a 3x phone
   multiplies fill-rate by 9. Clamp to `[1, 2]`.
4. **`InstancedMesh` culled incorrectly.** Scattered instances outside the base geometry's
   bounding sphere disappear. Call `computeBoundingSphere()` or `frustumCulled = false`.
5. **Geometry bounds stale after edits.** Modify positions → `computeBoundingSphere()` and
   `computeBoundingBox()`, or the mesh pops at screen edges.
6. **`material.dispose()` does not free textures.** Textures are separate GPU resources;
   dispose them explicitly or VRAM grows every scene change.
7. **Draco/meshopt decoder not wired.** A `GLTFLoader` without a decoder loads raw geometry —
   3-10x the payload — and the page looks fine offline but stalls in production.
8. **`KTX2Loader.detectSupport(renderer)` omitted.** Transcoding never completes, textures
   stay blank.
9. **Shadow frustum too large.** A 1000-unit shadow camera with a 2048 map gives ~0.5 units
   per texel: mushy shadows and acne.
10. **`normalBias` not scaled to world units.** Too large → light leaks; too small → acne.
11. **Negative scale on a node.** Flips normals/tangents; the asset renders inside-out.
12. **Baking lighting into albedo.** The asset looks correct only under the author's light.
13. **8-bit render targets for HDR pipelines.** Highlights clip; bloom produces flat white.
14. **Post-processing on Low tier.** Full-screen passes are cheaper to drop than geometry.
15. **Merging skinned geometry.** Breaks the skeleton; the mesh renders in T-pose.
16. **Unbounded `clock.getDelta()`.** A tab resume returns a multi-second delta and the camera
    teleports through walls.
17. **Every frame allocates `new THREE.Vector3()`.** GC pressure shows up as periodic stutter.
    Reuse scratch vectors at module scope.
18. **Shadow maps re-rendered every frame for a static scene.** Set
    `renderer.shadowMap.autoUpdate = false` and flag `needsUpdate` on change.

---

## 12. Quick Reference

### 12.1 Decision tables — "I need to …"

| Goal | Do this | Reference |
| :--- | :--- | :--- |
| Make a flat asset look real | `PMREMGenerator` + `RoomEnvironment` as `scene.environment` | §5.3 |
| Add edge definition | Chamfer the geometry (or `RoundedBoxGeometry`), not a texture | §2, §4.4 |
| Get a believable highlight | One shadow-casting key light with tuned `bias`/`normalBias` | §6 |
| Control object count | `InstancedMesh` for repeats, `mergeGeometries` for statics, `BatchedMesh` for mixed | §4.2, §4.3 |
| Cut far-field cost | `THREE.LOD` levels + `hysteresis` | §4.4 |
| Make terrain | Displace a `PlaneGeometry` with `ImprovedNoise` — **not** marching cubes | §4.6 |
| Make organic blobs | `MarchingCubes.addBall()` (and size `maxPolyCount` to the output) | §4.6 |
| Ship a smaller asset | Draco (static) or meshopt (mobile) + KTX2 textures | §2 Stage 8 |
| Prove the asset fits | `scripts/preflight_gltf_budget.py --tier <tier>` | §15 |
| Prove the scene fits | `renderer.info.render` / `renderer.info.memory` assertions | §8.4 |
| Fix washed-out colours | sRGB for colour maps, Linear for data maps | §5.2 |
| Fix black/over-bright output | One `OutputPass` last; tone mapping exactly once | §7 |
| Fix shadow acne | `shadow.bias` + `shadow.normalBias`, scaled to world units | §6 |
| Stop a VRAM leak | Dispose geometries, materials **and** textures | §8.3 |
| Style a material | `onBeforeCompile` (keeps PBR) before `ShaderMaterial` | §6.5 |
| Ship colourways | `KHR_materials_variants` **via a plugin** — three's core loader ignores it | §4.8 |
| Honour reduced motion | `matchMedia('(prefers-reduced-motion: reduce)')` → disable idle motion | §9 |

### 12.2 Copy-paste starter templates

| Need | Where to look |
| :--- | :--- |
| Renderer + scene + camera bootstrap | §5.2, §8.1 |
| Studio environment without an HDRI | §5.3 (`RoomEnvironment` + PMREM) |
| glTF loading with Draco / meshopt / KTX2 | §3 |
| Procedural prop geometry | §4.1 |
| Draw-call reduction (merge / batch / instance) | §4.2, §4.3 |
| LOD setup | §4.4 |
| Runtime terrain / SDF mesh | §4.6 |
| 3D text and labels | §4.7 |
| glTF material variants | §4.8 |
| Shadow configuration | §6 |
| Shader customisation (3 levels) | §6.5 |
| Post-processing chain | §7 |
| Resize / visibility / on-demand loop | §8.2 |
| Full teardown without leaks | §8.3 |
| Budget assertions | §8.4 |
| Reduced-motion handling | §9 |
| Asset budget gate | §15 (`scripts/preflight_gltf_budget.py`) |

---

## 13. Static Analysis Notes (preflight linter `THREE_*` codes)

The preflight visual linter scans JS/TS for three.js-specific hazards. These are **triage
signals, not verdicts** — see `preflight_scanner_notes.md` for the full triage workflow.

The rules were calibrated against the **503 real source files** of `three/examples/jsm`
(the upstream addon library). A rule that cannot separate a real defect from idiomatic
three.js code is noise, and noise gets ignored — so the rules use a scope-aware analyser
rather than a flat regex.

| Code | Severity | Signal (after calibration) | Triage |
| :--- | :--- | :--- | :--- |
| `THREE_UNCLAMPED_PIXEL_RATIO` | HIGH | `setPixelRatio(devicePixelRatio)` with no clamp | Real unless a wrapper clamps upstream |
| `THREE_PER_FRAME_ALLOCATION` | MEDIUM | Zero-arg `new THREE.Vector3()` **inside a function body** (module scope and constructors are excluded) in a file with a render loop | Real if that function runs per frame; ignore one-shot helpers |
| `THREE_MISSING_DISPOSE` | MEDIUM | A `WebGLRenderer` is created in this file and no `.dispose()` is ever called | Real — the renderer owns a WebGL context |
| `THREE_MISSING_SHADOW_BIAS` | MEDIUM | This file **creates a light** and sets `castShadow` but no `shadow.bias` / `normalBias` | Real unless bias is set by a central light factory |
| `THREE_UNSET_OUTPUT_COLOR_SPACE` | LOW | Renderer created without `outputColorSpace` | Fine on r152+ (sRGB is the default) — pin it anyway |
| `THREE_UNCOMPRESSED_GLTF` | LOW | A `GLTFLoader` is **instantiated** with no Draco/meshopt/KTX2 decoder | Real for shipped payloads; ignore exporters |
| `THREE_MISSING_RESIZE_HANDLER` | LOW | Renderer created, no `resize` / `ResizeObserver` / `setSize` | Real if the canvas is not fixed-size |
| `THREE_DEPRECATED_API` | MEDIUM | Uses `PCFSoftShadowMap` (removed r186), `useLegacyLights` (r165), or `CubeUVReflectionMapping` (r187) | Upgrade to `PCFShadowMap` + `shadow.radius`, physical lights, or `PMREMGenerator` |
| `THREE_MISSING_OUTPUT_PASS` | MEDIUM | `EffectComposer` configured without `OutputPass` | Append `OutputPass` as the final pass |
| `THREE_COMPOSER_8BIT_TARGET` | LOW | `UnrealBloomPass` with single-arg `EffectComposer(renderer)` | Pass `WebGLRenderTarget` with `THREE.HalfFloatType` |

Note: `.mjs`, `.cjs`, and inline `<script>` blocks in `.html`/`.vue`/`.svelte` are scanned automatically.

---

## 14. Version Compatibility (verified against upstream source tags)

Every row was checked against the three.js source at the stated tag. Use it to decide
whether a snippet in this document applies to the installed version.

| API / behaviour | Available from | Notes |
| :--- | :--- | :--- |
| `renderer.outputColorSpace = SRGBColorSpace` | r152 | sRGB is the **default** from r152 — set it explicitly anyway |
| `THREE.ColorManagement.enabled` | r152 | Enabled by default; `NoColorSpace` is the correct tag for data maps |
| `scene.backgroundBlurriness` | r158 | Blurred environment backdrop |
| `THREE.AgXToneMapping` | r160 | Filmic highlight rolloff; gentler than ACES |
| `THREE.NeutralToneMapping` | r162 | Khronos PBR Neutral — best for product/configurator colour fidelity |
| `scene.environmentIntensity` | r163 | Global IBL intensity multiplier |
| `THREE.MeshPhysicalMaterial.anisotropy` | r155 | Anisotropic specular (brushed metal) |
| Physically-correct lighting by default | r155 | `useLegacyLights` flag **removed in r165** |
| `renderer.transmissionResolutionScale` | r175 | Halves the cost of `transmission` materials |
| `BatchedMesh(maxInstanceCount, …)` | r166 | r159–r165 used `maxGeometryCount` as the first argument |
| `RenderPipeline` (WebGPU) | r183+ | Replaces `PostProcessing` on `WebGPURenderer`; `EffectComposer` is WebGL-only |
| `THREE.PCFSoftShadowMap` | **removed in r186** | Use `THREE.PCFShadowMap`; `shadow.radius` is the softness control |
| `outputBufferType` / `screenSize` | r186 | Replaced `colorBufferType` and TSL `viewportResolution` |
| `CubeUVReflectionMapping` | **removed in r187** | `PMREMGenerator` uses native cube RTs; `MeshPhysicalMaterial` adds EON rough diffuse BRDF; `WebGPURenderer.dispose()` is async |

**How to re-verify in 30 seconds:**

```bash
grep -n "export const PCFSoftShadowMap" node_modules/three/src/constants.js
node -e "import('three').then(t => console.log('REVISION', t.REVISION))"
```

> [!NOTE]
> `THREE.PCFSoftShadowMap` still *exists* as an exported constant after r186 (marked
> `@deprecated`), so `import` succeeds and the mistake is silent apart from a console
> warning. Console warnings during scene setup are defects — read them.

---

## 15. The Asset Budget Auditor (gate the pipeline, do not just describe it)

`scripts/preflight_gltf_budget.py` turns §2 into an executable gate. It parses a `.glb`
or `.gltf` and reports what the asset will cost at runtime — no Blender, no browser,
stdlib only:

```bash
python3 scripts/preflight_gltf_budget.py asset.glb --tier medium --fail-on high
```

| Code | Severity | Signal |
| :--- | :--- | :--- |
| `GLTF_TRIANGLE_BUDGET_EXCEEDED` | HIGH | Triangle count above the tier ceiling |
| `GLTF_DRAW_CALL_BUDGET_EXCEEDED` | HIGH | Primitive count (≈ draw calls) above the tier ceiling |
| `GLTF_TEXTURE_VRAM_EXCEEDED` | HIGH | Estimated GPU texture footprint above the tier ceiling |
| `GLTF_NEGATIVE_SCALE_NODE` | HIGH | A node with negative scale — normals and tangents flip, the asset renders inside-out |
| `GLTF_TEXTURE_TOO_LARGE` | MEDIUM | A texture larger than the tier's max dimension |
| `GLTF_MATERIAL_SLOT_EXPLOSION` | MEDIUM | More material slots than the tier allows (each is a draw call + shader variant) |
| `GLTF_UNCOMPRESSED_GEOMETRY` | MEDIUM | No Draco/meshopt compression |
| `GLTF_UNCOMPRESSED_TEXTURES` | MEDIUM | Textures ship as PNG/JPEG instead of KTX2/WebP |
| `GLTF_MISSING_LOD` | MEDIUM | A heavy asset with no LOD structure |
| `GLTF_SCALE_SUSPICIOUS` | MEDIUM | Geometry extent is not in metres (glTF is defined in metres) |
| `GLTF_NON_UNIFORM_SCALE_NODE` | LOW | Non-uniform node scale distorts normal mapping |
| `GLTF_NORMAL_MAP_WITHOUT_TANGENTS` | LOW | Normal map present but no `TANGENT` attribute |
| `GLTF_PRIMITIVE_WITHOUT_MATERIAL` | LOW | A primitive with no material renders with the default material |
| `GLTF_MESH_WITHOUT_MATERIAL` | LOW | A mesh with no material assigned |

---

## 16. Headless 3D Video Baking (`surgical-media` `threejs_bridge`)

When polishing `surgical-media` `threejs_hybrid` / `threejs_3d` scenes:
- **Virtual-clock stepping**: `runner.mjs` steps `tNorm` deterministically; never use `requestAnimationFrame` wall-clock deltas inside `params.threejs_script`.
- **Shadow & HDR contracts**: Use `THREE.PCFShadowMap` + `shadow.bias` / `shadow.normalBias`, `HalfFloatType` `WebGLRenderTarget` when `UnrealBloomPass` is active, and `roomEnv.dispose()` + `pmrem.dispose()` after IBL baking.
- **Asset tier**: Target `--tier medium` in `preflight_gltf_budget.py` for headless Chromium/SwiftShader bakes (`--tier high` for GPU/Blender).

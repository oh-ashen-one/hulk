# Third-party code and assets

## Foundation: Spiderbench, by Shikhar (xikhar)
- Source: https://github.com/xikhar/spiderbench (via the oh-ashen-one/spider-man-2 fork). Source-Available, View-Only License: see [LICENSE](LICENSE).
- Everything under `src/`, `public/` and `index.html`, and the city that the Unreal builders export, derives from it.

## Rampage (Elemental skin), by Epic Games — Fab Standard License
- Source: Fab listing "Paragon: Rampage" (0807cf74-08fd-4a33-8c8d-f33c9439fb1f), free. Unreal Engine use only; the Paragon name is not used in titles or ads.
- **Not in this repository.** Users add it to `Content/ParagonRampage` themselves. Our clips are retargeted onto it by `tools/brute/retarget_paragon.py`. Ledger: [docs/brute/ASSETS.md](docs/brute/ASSETS.md).

## Brute mesh and animation sources
- Mesh: generated with Customuse, then rigged, skinned and corrected by `tools/brute/`. Motions: Cartwheel text-to-motion (through Customuse), Meshy text-to-motion, MiniMax H3 (fal.ai) and ByteDance Seedance reference videos, fitted with video2rig (https://github.com/canitcode/video2rig, AGPL-3.0; our fork oh-ashen-one/video2rig). The tool's licence does not cover its outputs. Ledger: [docs/brute/video2rig/LEDGER.md](docs/brute/video2rig/LEDGER.md).
- The generated GLB/FBX files are not in this repository.


## three-pinata — MIT, © Daniel Greenheck
- Source: https://github.com/dgreenheck/three-pinata — npm `@dgreenheck/three-pinata@2.0.1` (dependency, not vendored).
- Used for: Voronoi fracture (3D and 2.5D) of breakable props, glass panes, crates and bins
  (`src/game/destruction/fracture.worker.js`, run in a Web Worker).

## ez-tree — MIT, © Daniel Greenheck
- Source: https://github.com/dgreenheck/ez-tree @ v2.0.0 (`dcf309b`, 2026-07-16).
- Vendored: `src/lib/*` -> `src/world/eztree/` (tree generator, options, presets as JS modules, trellis). Local
  changes are marked `(pat)` and listed in the header of `src/world/eztree/tree.js` (instanced wind fix, per-instance
  wind phase, wind in the shadow pass, bark sway, metric bark UVs, Uint32 indices). License: `src/world/eztree/LICENSE`.
- Ported: the instanced wind grass of the demo app (`src/app/grass.js`) -> `src/world/grass.js` (rewritten for
  camera-anchored GPU instancing; its simplex wind code kept).
- Assets: leaf-spray textures of the demo app (`src/app/public/textures/leaves/{ash,oak,pine,aspen}.png`, project
  license, MIT) -> `public/assets/eztree/leaves/`. The ambientCG bark textures of the demo are **not** used (the city's
  own bark array is).

## dgreenheck/tidewater — MIT License, © 2026 DRG Software Solutions LLC
https://github.com/dgreenheck/tidewater — techniques and shader math ported from WGSL (raw WebGPU) to GLSL / three.js r186 WebGL2
on the `water-effects` branch:

| Our file | Adapted from |
|---|---|
| `src/world/cdlod.js` | `src/core/CDLOD.js` (CDLOD quadtree selection + world-space geomorph) |
| `src/world/water.js` (shading, sea detail) | `src/ocean/WaterMaterial.js` (Fresnel, GGX glint, Cox-Munk roughness, turbid-medium body, underside), `src/ocean/SeaDetail.js` |
| `src/render/underwater.js` | `src/post/Underwater.js` (lens medium, in-scattering, shafts, meniscus), `src/ocean/Caustics.js` (photon-splat caustics) |
| `src/render/pipeline.js` (lens droplets in the final pass) | `src/post/LensDroplets.js` |
| `src/world/waterfx/spray.js` (sprite shading) | `src/fx/Spray.js` |
| `src/world/waterfx/gulls.js` | `src/world/Gulls.js` |

MIT License text: https://github.com/dgreenheck/tidewater/blob/main/LICENSE — "Permission is hereby granted, free of charge, to any person
obtaining a copy of this software ... The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software."

## Evan Wallace — "WebGL Water" (MIT)
The ripple heightfield (`src/world/waterfx/ripples.js`) and the caustic splatting idea follow https://madebyevan.com/webgl-water/.

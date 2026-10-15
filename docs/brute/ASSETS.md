# Brute assets — provenance

Owner instruction (2026-10-15): asset creation goes through the **Customuse** connector (Codex Apps connector `customuse`,
driven non-interactively with `codex exec`). No ripped assets, logos, likenesses, music or audio from the 2005 game.

## The Brute body

| Field | Value |
|---|---|
| Customuse profile | the connected owner profile (balance before: 4,386 credits) |
| Preview set (free) | setId `4241eb26-f468-405b-bdbf-c518610970c8`, sessionId `ba5b5c9f-8506-4bb4-9d49-b763ca669394` |
| Category / tier | `game-dev` / `characters`, quality tier `super` (Tripo P1), PBR on, 20,000 polys, private |
| Prompt | "Original giant green-skinned brute, a huge muscular hulking brawler about 2.5 m tall, massive shoulders, enormous fists and forearms, small head, heavy brow, messy dark hair, torn ragged purple shorts, barefoot, no logo, no shirt. Strict T-pose ... Full body, front facing, stylized chunky game character." |
| Chosen preview | `7c3ed898-d265-4229-b18f-339f05fa25af` (arms clear of the torso -> clean rigid cuts); still in `evidence/customuse_preview_selected.png` |
| Paid model | taskId `2f1f1d60-bf4d-44e5-924f-5c6f52dd9ae0`, status completed, **100 credits** charged (exactly one paid generation) |
| Output | one textured GLB (27,927 verts, 4K BaseColor / NormalGL / ORM), local copy `~/hulk-scratch/customuse/brute.glb` (not committed: generated binary; re-download from the task) |

Pipeline (all reproducible, no binaries in git):

1. `tools/brute/rig_brute.py` (Blender 5.2, headless) scales the GLB to 2.6 m, welds the UV-seam-split vertices (27,927 -> 9,646) so
   the surface is one piece, builds an 11-bone armature at the measured joints and skins the WHOLE mesh with smooth inverse-distance
   weights (region prior + neighbour bones + weight smoothing). It self-tests a bent pose (`MAX_EDGE_STRETCH`, optional renders with
   `BRUTE_RENDER=1`) and writes `brute_skel.fbx`, the three PNG maps and `unreal/WebHomage/Config/BruteRig.json` (bone heads in UE cm,
   rest arm abduction 27 deg).
2. `tools/brute/make_fx_meshes.py` (Blender) builds the impact-effect meshes procedurally: shock ring / arc bands, dust puff, rock,
   crater bowl.
3. `python3 unreal/WebHomage/Scripts/build_brute.py` (one headless commandlet through the shared GPU slot) imports the skeletal mesh
   `/Game/Brute/Skel/SK_Brute` + `M_Brute` (PBR, skeletal-mesh usage, never-stream textures) and the fx into `/Game/Brute/Fx`.
4. In game, `ABruteCharacter` animates invisible joint components procedurally and copies them onto the bones of a
   `UPoseableMeshComponent` every frame (bone = rest bone x rest joint^-1 x joint now).

History: loop 1 first cut the model into 11 rigid pieces (removed `segment_brute.py`); that tore at every joint and the owner rejected
it on first sight (2026-10-15). The skinned body replaced it the same day.

The pawn falls back to a placeholder brick body (engine cubes) if `/Game/Brute/Skel` is missing (`-WHBruteBricks` forces it).

## Re-generating

`codex exec` with the customuse tools: `customuse_create_3d_preview_set` (free) -> pick a preview -> `customuse_start_3d_generation`
(paid, never retry automatically) -> poll `customuse_get_3d_generation_task` for `modelUrl`. Then steps 1-3 above. If the new model's
proportions differ, re-measure the landmarks at the top of `segment_brute.py` (the slice profile printout is the reference).

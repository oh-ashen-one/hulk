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

## Brute v2 (2026-10-15, owner: "do the entire thing again on Customuse")

| Step | Value |
|---|---|
| Previews (free) | setId `5c497309-2a0f-4e26-9a12-51cee0b6b81c`, realistic-anatomy A-pose prompt; chosen preview `50cd6afd-54b6-49bd-8f4a-3f27661c2498` |
| Model (paid) | task `cbdd9877-6c27-4a3f-ad89-9522ece557f2`, Customuse CR 2.1 requested, 100 credits; Customuse names it "Emerald Behemoth" (https://customuse.com/d/cbdd9877-6c27-4a3f-ad89-9522ece557f2) |
| Rig | Customuse website, Nodes editor -> Humanoid **Auto Rig** node (Cartwheel), 8 credits, driven through Codex Computer Use on the owner's Chrome; export `Emerald_Behemoth_Rigged_fbx.zip` (`SM_Character_Brute.fbx`, 52-bone SMPL-style skeleton incl. fingers, PBR PNGs) |
| Animation | `tools/brute/animate_brute.py` (Blender): re-aims limb bones, leg IK + flat-foot copy-rotation baked to FK; Idle, Walk, Run, Stop, WallClimb, JumpCharge, JumpAir, Land -> `brute.glb` / `brute_anim.fbx` + `clips.json` |
| Review | `tools/brute/viewer/serve.sh` -> http://127.0.0.1:8765 (three.js) |
| Final clips (owner-approved in the viewer) | Cartwheel text-to-motion via the Customuse Humanoid Animation node: Idle, Walk (2nd gen), Run, StopLunge (trimmed at the coil), Jump (charge crouch -> launch), WallAttach (fists into the wall); **WallClimb reuses WallAttach** (owner's call after the Cartwheel and Meshy climbs were rejected). Hand-made Blender clips were rejected and are not used. `tools/brute/assemble_motion.py` cleans and merges them into `brute_anim.fbx` |
| In game (2026-10-16) | `build_brute.py` imports `brute_anim.fbx` as `/Game/Brute/Body/SK_Brute` (+ `SK_Brute_Skeleton`, `M_Brute` from the export's D / N / ORM maps) and `A_Brute_<Clip>` AnimSequences. `ABruteCharacter::AnimateClips` samples them on the game thread into the poseable mesh: state -> clip segment, crossfades, root travel removed, feet put back on the street; combat moves aim the arms along the procedural joints as an overlay. Segment markers come from the bone curves (`tools/brute/analyze_clips.py`). `-WHBruteV1` falls back to the v1 path |

## Re-generating

`codex exec` with the customuse tools: `customuse_create_3d_preview_set` (free) -> pick a preview -> `customuse_start_3d_generation`
(paid, never retry automatically) -> poll `customuse_get_3d_generation_task` for `modelUrl`. Then steps 1-3 above. If the new model's
proportions differ, re-measure the landmarks at the top of `segment_brute.py` (the slice profile printout is the reference).

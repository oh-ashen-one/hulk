# Build your own game on this repo

A recipe for people and their coding agents. It takes you from a clean clone to your own character smashing through this Manhattan. Read [`../AGENTS.md`](../AGENTS.md) first for the rules and the repo map.

> **Licence check (do this first).** The city and browser foundation are Shikhar's [Spiderbench](https://github.com/xikhar/spiderbench) under a view-only [licence](../LICENSE). Studying, prototyping and running it locally are allowed. Shipping, selling or redistributing a game built on it is **not** allowed without Shikhar's written permission. Third-party packs (Fab/Paragon, fonts, npm modules) keep their own licences. Hulk belongs to Marvel/Disney, so don't use the name, logo or likeness in anything you release.

## 0. What you get

- **A whole procedural Manhattan island in UE 5.8**, with streets, buildings, foliage, water, traffic, pedestrian crowds, day and night lighting, and a Times Square plaza.
- **A heavyweight third-person character controller in C++** (`ABruteCharacter`), with:
  - sprinting that knocks cars aside;
  - a charged super jump with crater landings and leap chains;
  - wall run, hang, climb and kick-off;
  - an air dash;
  - a punch/slap combo, a launcher uppercut, a thunderclap and a ground smash/grand slam;
  - car grab, carry and throw.
- **A 17-clip animation contract**, so any character with the right clips drops in (section 3).
- **Data-driven tuning**: hit frames, act windows and speeds in `unreal/WebHomage/Config/Brute*.json`.
- **An offscreen capture harness** with scripted input and telemetry. Agents can test gameplay without anyone touching the keyboard (section 5).

## 1. Prerequisites

| Need | Notes |
|---|---|
| Mac with Apple silicon | Built and tested on a Mac Studio M3 Ultra (macOS). Windows/Linux would need the shell scripts ported, and was never tested. |
| Unreal Engine 5.8 | From the Epic Games Launcher, at `/Users/Shared/Epic Games/UE_5.8`. Scripts hard-code that path; change the `UE=` lines if yours differs. |
| Xcode + command-line tools | Needed for the C++ module. |
| Python 3, Node.js 20.19+ / 22.12+ | Python for builders, Node for the browser city export (`npm ci`). |
| Blender 4.x | Only for the character tools in `tools/brute/`. |
| About 60 GB free disk | The generated content plus one Paragon pack (Rampage is 3.2 GB). |

## 2. Build order

Run each step from the repo root. Each Unreal step is a headless commandlet launched through the GPU slot, one at a time.

```bash
npm ci
unreal/WebHomage/Scripts/build_editor.sh                 # 1. C++ module
python3 unreal/WebHomage/Scripts/build_manhattan.py      # 2. city: export -> import -> materials -> maps (long; --steps a,b to resume)
python3 unreal/WebHomage/Scripts/build_brute.py --fbx <your_character.fbx>   # 3. player body and clips (section 3)
```

**Known rough edge:** a few steps of `build_manhattan.py` (`characters`, `terrain`) still point at the original author's scratch folders. When a step fails on a missing path, read that step's docstring and point it at your own inputs. Each builder prints `SM2_BUILD_OK: <script>` when it succeeds and `SM2_BUILD_FAILED` when it fails. More notes: [UNREAL_PLAYTEST.md](UNREAL_PLAYTEST.md).

Then play:

```bash
./Play-Brute.command                         # windowed 1920x1080, 60 fps cap, Times Square start
./Play-Brute.command -WHBruteSkin=Brute      # force the build_brute.py body
```

## 3. Bring your own character

The game loads one skeletal mesh and **17 AnimSequences named `A_Brute_<Clip>`**:

```
Idle Walk Run StopLunge Jump WallAttach WallClimb PunchL PunchR Slap Clap Smash Lift Throw Uppercut Fall Land
```

All 17 must exist, or the rig falls back. Each clip's role and timing (hit frame, release frame, loop length, speed) lives in `unreal/WebHomage/Config/BruteClipTiming.json`. Re-measure it when you swap clips.

### Route A: a Fab / Epic character on the UE4 mannequin skeleton (easiest)

Most free Paragon heroes on Fab (Rampage, Crunch, Grux, Sevarog…) use UE4 mannequin bone names (`pelvis, spine_02, spine_03, neck_01, head, upperarm_l, lowerarm_l, hand_l, thigh_l, foot_l, ball_l`, plus the right side). Our clips retarget onto them automatically:

1. Add the pack to the project: in the UE 5.8 editor, open **Window → Fab**, then **Add to Project**. On a Mac, the launcher hides Windows-only packs, so the editor panel is the only way. The pack lands in `Content/Paragon<Hero>/`.
2. Add the mesh path to `SKINS` in [`tools/brute/retarget_paragon.py`](../tools/brute/retarget_paragon.py) and to `SkinMeshes` in `BuildClipRig` (`Source/WebHomage/Brute/BruteCharacter.cpp`). Rebuild C++.
3. Retarget: `BRUTE_SKIN=<Hero> UnrealEditor-Cmd WebHomage.uproject -run=pythonscript -script=tools/brute/retarget_paragon.py -unattended -nullrhi`. This writes `/Game/Brute/<Hero>/A_Brute_*` and never touches the originals.
4. Play with `-WHBruteSkin=<Hero>`. If the character runs slightly off-axis, trim it with `-WHBruteYawTrim=<deg>`.
5. Record the pack in `docs/brute/ASSETS.md`. Never commit it.

Route A needs the source clips in `/Game/Brute/Body` (step 3 of the build), because they're what gets retargeted.

### Route B: a Mixamo-rigged character (your own model or a Mixamo one)

`build_brute.py` imports one FBX containing the mesh and 17 takes named by clip on a **Mixamo-named skeleton** (`Hips, Spine1, Spine2, Neck, Head, LeftArm, LeftForeArm, LeftHand, LeftUpLeg, LeftFoot, LeftToeBase`, plus the right side). It renames the takes to `A_Brute_<Clip>` under `/Game/Brute/Body`. To build that FBX:

- Get motions from Mixamo or Fab first, or from any licensed source. Pick the nearest base for each clip and fix it up (grip, contact, transitions) rather than animating from scratch.
- Assemble them with Blender: `tools/brute/assemble_motion.py <rigged_mesh.glb> <motion_dir> <out_dir>`. It writes `brute_anim.fbx`, `clips.json` and `clips_meta.json`.
- For motions nobody sells, generate a reference video and fit it with [video2rig](https://github.com/oh-ashen-one/video2rig). Our full process, costs and blind A/B verdicts are in [`docs/brute/video2rig/`](brute/video2rig/).

### Route C: different gameplay entirely

`ABruteCharacter` is one large class. To make a different hero, a common approach is to copy it, keep the clip loader and capture hooks, and replace the move set. The game mode picks the pawn (`AWebTravGameMode`, declared in `Source/WebHomage/Traversal/WebTravCharacter.h`). The old Spider-Man hero is still there behind `-WHSpidey` as a second example.

## 4. Tuning without C++

| File | What it controls |
|---|---|
| `Config/BruteClipTiming.json` | Per-move timing: which clip, act and hit frames, release, carry windows, and the hit table (what each attack does to cars). |
| `Config/BruteAnim.json` | Blend times, play rates and locomotion thresholds. |
| `Config/BruteRig.json` | Rig and bone data for the original body. |
| `-WHBruteTune=Gravity=…,SprintSpeed=…,RunSpeed=…,SuperJumpHeight=…,SuperJumpRange=…,ThrowSpeed=…` | Override core movement numbers at launch, without rebuilding. |

## 5. Test like an agent: offscreen captures

```bash
CAPTURE_GATES_ONLY=1 tools/brute/capture.sh none                                   # GPU gates open?
tools/brute/capture.sh m7_combat_cars -shots 1.2,4.4,7.9 -quit 11 -res 1920x1080  # stills
tools/brute/capture.sh v3_combat -movie                                            # every frame + mp4
```

- A **case** (`tools/brute/cases/<name>.json`) is a spawn point plus timed inputs (`move`, `look`, `sprint`, `jump`, `attack`, `heavy`, `grab`, `clap`…). Copy one to script a new test.
- Output goes to `~/hulk-scratch/cap/<case>/`: PNG stills or an mp4, a telemetry CSV (position, velocity, state per frame) and `WH_BRUTE t=…` event lines (`punch_hit cars=1`, `ground_grand_slam`…). These are good for asserting behaviour.
- The run is offscreen with a fixed timestep (`-benchmark -fps=30`), so script time equals shot time. It is not proof of frame rate.
- A run that never reaches frame 1 within 120 s is stopped (exit 5). Don't relaunch blindly. Read the log.
- Always look at the frames. Telemetry has said "fine" while the character was visibly running sideways.

## 6. GPU safety (shared machines)

`tools/gpu/gpu_gates.py` refuses a launch in four cases: the GPU is busy (90 % or more on three readings), another engine is stuck exiting, too many GPU clients are running (cap 3, or 2 when no GPU watchdog is installed), or the previous launch was less than 20 s ago. `tools/gpu/gpu_slot.sh` then queues the launch for a slot. On your own machine, these gates mostly stop two agents from launching engines at once, which can hang macOS's window server. Keep them. Details: [tools/gpu/README.md](../tools/gpu/README.md).

## 7. Problems we already solved

| Symptom | Cause | Fix |
|---|---|---|
| Fab pack shows "No compatible user projects" on a Mac | The pack is listed Windows-only | Editor **Window → Fab → Add to Project** |
| Retargeted character placed 80 m away | Full-body IK op plus 110×-scaled source bones | Disable the IK op (FK only); remove Root Motion |
| New body runs sideways / leans | 80° hip turn in the clips plus a rest-facing mismatch (10° vs 90°) | New editable retarget pose: turn the source Hips to the target's rest facing, then `auto_align_all_bones` |
| Edits to the retarget pose do nothing | The built-in Default Pose ignores edits | `create_retarget_pose("…")` and edit that |
| `create_asset` returns None on re-run | Asset already exists and is referenced | Reuse the existing asset; `remove_all_ops()` before `add_default_ops()` |
| Commandlet exits 1 | Old GameFeatureData error | Harmless; check the script's own log |
| Gates count phantom Unity editors | iOS Simulator wallpaper process | Fixed in `gpu_gates.py` (Simulator processes ignored) |

## 8. Hand-off etiquette

When an agent stops, it writes what it changed, what it verified (with capture paths) and what's still open at the top of `HANDOFF.md`, then pushes its branch. The next agent starts there.

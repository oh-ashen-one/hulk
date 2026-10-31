# AGENTS.md: Hulk in Manhattan (`oh-ashen-one/hulk`)

You are an AI coding agent working in this repo. Read this file first, then [`docs/BUILD_ON_THIS.md`](docs/BUILD_ON_THIS.md) for step-by-step recipes and [`HANDOFF.md`](HANDOFF.md) for the latest state. (Updated 2026-10-31.)

## What this is

An unofficial, non-commercial fan homage to *The Incredible Hulk: Ultimate Destruction*, built in **Unreal Engine 5.8 (C++)** on a procedural Manhattan. The player is a 2.6 m brute (default body: Epic's free Rampage rock skin) with 17 animation clips. He can sprint, super jump, run up walls, punch, slap, thunderclap, grand slam, and grab and throw cars. The city, traffic and crowds come from the Spider-Man 2 port of Shikhar's Spiderbench.

`main` is the single canonical branch. For your own work, use a branch and open a pull request.

## Rules that are not optional

1. **Licence.** The upstream code and assets are under Shikhar's view-only [LICENSE](LICENSE). Before helping anyone ship, sell or redistribute a game built on this repo, tell them it needs Shikhar's written permission. Learning, prototyping and local play are fine.
2. **Homage disclaimer.** Keep "homage game, not an official Marvel game" in the README, DISCLAIMER.md and the header of any new script. Don't add Marvel logos, ripped game assets, music or audio from the original game, or an actor's likeness.
3. **Licensed packs never go in Git.** `Content/` is git-ignored. Fab/Paragon packs are Unreal-only under the Fab Standard License: never commit them, and never use the PARAGON name in a title or ad. Record every third-party asset (source, licence, what was changed) in [`docs/brute/ASSETS.md`](docs/brute/ASSETS.md).
4. **Never commit secrets.** Provider API keys (fal.ai, Customuse, BytePlus and others) are read from the user's own files at run time. Never print, log or commit them.
5. **One renderer at a time, offscreen.** Launch every Unreal process through the GPU gates and slot (`tools/gpu/`). Never open a fullscreen window. Stop only processes you started: SIGTERM, wait up to 60 s, and SIGKILL only as a last resort. Never auto-relaunch after two crashes.
6. **Evidence, not claims.** "It compiled" is not "it works". Prove a gameplay change with an offscreen capture (`tools/brute/capture.sh`), then look at the frames yourself. Fixed-timestep captures are not frame-rate evidence.

## Repo map

| Path | What it is |
|---|---|
| `unreal/WebHomage/WebHomage.uproject` | The UE 5.8 project. `Source/WebHomage/` is the C++ module. |
| `Source/WebHomage/Brute/BruteCharacter.cpp` | The player: movement, super jump, wall run, combat, grab/throw, clip state machine, and skin selection (`BuildClipRig`). |
| `Source/WebHomage/Brute/BruteFx.cpp`, `BruteHUD.cpp` | Impact effects (craters, debris, shockwaves) and the HUD (damage counter, controls card, jump charge meter). |
| `Source/WebHomage/{Traversal,Combat,Characters,Life,Look,Core}` | Inherited Spider-Man systems: traversal/camera, crowds and traffic ("Life"), lighting ("Look"), game mode and settings. |
| `unreal/WebHomage/Config/BruteClipTiming.json`, `BruteAnim.json`, `BruteRig.json` | Data-driven clip timing (hit frames, act windows), animation tuning and rig data. Edit these before touching C++. |
| `unreal/WebHomage/Scripts/` | Headless content builders: `build_editor.sh` (C++), `build_manhattan.py` (city), `build_brute.py` (green body and clips), `run_game.sh` (offscreen game runner). |
| `tools/brute/` | Character pipeline: Blender rig/skin/texture tools, `assemble_motion.py`, `retarget_paragon.py` (clips onto a Fab character), `capture.sh` and `cases/*.json` (scripted gameplay captures), `v2r/` (video2rig glue). |
| `tools/gpu/` | GPU gates and slot (`gpu_gates.py`, `gpu_slot.sh`) used by every launcher. |
| `Play-Brute.command` | The windowed player launcher for humans (1920×1080, 60 fps cap). |
| `src/`, `public/`, `index.html` | Spiderbench's original browser game (Three.js) plus the city exporter's source. `npm run dev`. |
| `docs/brute/` | Brief, results, moveset, asset ledger, evidence images, animation ledger. |
| `docs/history/` | Archived agent rules and the spider-man-2 history. For context only; don't follow them. |

## Common commands

```bash
unreal/WebHomage/Scripts/build_editor.sh                      # C++ (refuses while this project's engine is running)
python3 unreal/WebHomage/Scripts/build_manhattan.py           # city content, staged; see docs/UNREAL_PLAYTEST.md
python3 unreal/WebHomage/Scripts/build_brute.py --fbx X.fbx   # green body and 17 A_Brute_* clips -> /Game/Brute/Body
CAPTURE_GATES_ONLY=1 tools/brute/capture.sh none              # are the GPU gates open?
tools/brute/capture.sh m12_look -shots 1.5,3.7,6.5 -quit 10 -res 1920x1080   # offscreen capture -> ~/hulk-scratch/cap/m12_look/
```

Headless Unreal Python (e.g. a retarget):

```bash
"/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor-Cmd" \
  unreal/WebHomage/WebHomage.uproject -run=pythonscript -script=tools/brute/retarget_paragon.py \
  -unattended -nosplash -nullrhi -NoSound
```

It exits with code 1 because of an old GameFeatureData error, which is harmless. Judge success by the script's own log lines.

## Launch flags (game)

`-WHBruteSkin=Rampage|Crunch|Brute` (default Rampage, which falls back to Brute if the pack is missing) · `-WHBruteYawTrim=<deg>` · `-WHSpawnTimesSquare` · `-WHSpidey` (old hero) · `-WHBruteScript=<case.json>` (scripted input, used by captures) · `-WHBruteCsv=<path>` (telemetry) · `-WHBruteTune=SprintSpeed=…,SuperJumpHeight=…` (movement overrides) · `-WHBruteNoClipTiming`.

## Gotchas we already paid for

- **Fab on a Mac:** the launcher says "No compatible user projects" for Windows-only packs such as Rampage. Use the UE 5.8 editor's Window → Fab → Add to Project.
- **Retarget pitfalls:** SK_Brute bones carry about 110× scale, so a full-body IK op chases goals 80 m away. Use FK only and remove the Root Motion op. Edits to the built-in Default Pose are ignored, so create a new retarget pose. Turn the *source* Hips to the target's rest facing, then auto-align. See `tools/brute/retarget_paragon.py`.
- **Quaternions in UE Python:** there is no `Quat.inverse`. Use `unreal.MathLibrary.quat_inversed` and `multiply_quat_quat`.
- **Facing:** Paragon skins face by torso (hips plus shoulders), not toes.
- **A bigger animation is not better:** only ship a clip when a blind A/B shows a *clear* visual win. "Slightly better" has looked the same to players every time.

## When you finish

Update `HANDOFF.md` with what you changed and verified, what's still open, and your branch name. Push your branch.

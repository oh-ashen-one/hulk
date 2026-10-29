## video2rig animation upgrade — in progress (Claude Fable 5.1 overnight run, 2026-10-29)

> **2026-10-29 19:30 — CANDIDATE r2 BUILT, FULL NEW CAPTURE SET RUNNING.** r2 = 14 v2r (StopLunge included; Lift/Uppercut/WallClimb Sonnet refits; Throw burst refit) + Jump, WallAttach, Smash old, `~/hulk-scratch/brute_v2r_candidate/out/` (r1 in `out-r1/`), imported with build_brute.py (17 A_Brute_*). Timing rule: today's game-time windows kept, rate capped 1.6 (Throw 1.155), JSON committed. Captures: `ab_ingame.py run --label new --ignore-window --redo`, log `~/hulk-scratch/ab-ingame/new-r2.log` (~2.2 h with the 10/h budget); then `check --label new`, `pack`. The 19:05 note below is superseded on the clip list and timing rule.
> **2026-10-29 19:05 — PHASE 5 CANDIDATE BUILD DONE, NEW CAPTURES RUNNING (Opus 5.5 high).** Candidate set = 13 v2r clips + 4 old (StopLunge, Jump, WallAttach, Smash), assembled in `~/hulk-scratch/brute_v2r_candidate/out/` (shipped `~/hulk-scratch/brute_v5` untouched) and imported with `build_brute.py --fbx ~/hulk-scratch/brute_v2r_candidate/out/brute_anim.fbx`: **/Game/Brute/Body now holds the CANDIDATE clips** (all 17 A_Brute_*). To go back: `python3 unreal/WebHomage/Scripts/build_brute.py` (default = brute_v5). `Config/BruteClipTiming.json` now carries the v2r timings (contact game-time = today's for every act); with the old assets, run with `-WHBruteNoClipTiming`. New: refine burst pass (Throw frame-27 arm jump fixed), assemble TRIM skip for v2r, measure_timing contact-time/Throw/climb-cycle fixes, BruteCharacter per-clip wall times (editor rebuilt). New captures: `ab_ingame.py run --label new --ignore-window`, log `~/hulk-scratch/ab-ingame/new-full.log`; then `check --label new` and `pack`. Open findings for the critic in LEDGER "Phase 5 candidate set": Throw armpit creases 25 -> 162/frame, Idle-derived body yaw 10.7 deg off, combat playback 2.5-4.5x, Slap/Uppercut/Throw act length shorter.

> **2026-10-29 — GROUND READER DONE.** `GATE reader-ground PASS median_px front 2.41 side 2.83 (bar <4)`. Brute-aligned `reader/reader.pt` saved (9000 steps; held-out medians front 2.41 px, side 2.83 px). Details in LEDGER "Ground reader (brute-aligned): DONE".
> **2026-10-29 — AIR READER DONE.** `GATE reader-air PASS median_px front 2.85 side 3.30 (bar <4)`. Brute-air `reader/reader.pt` saved (9000 steps; final loss 2.38). Details in LEDGER "Air reader (brute-air): DONE".
> **In progress:** air reader training: done. Fall (airborne) being fitted via `tools/brute/v2r/run_clip.sh` (project `brute-air`, fork `/Users/midir/video2rig-brute-air`). Ground-clip fits (Phase 2/3) running via `tools/brute/v2r/run_clip.sh`, one clip at a time, Sonnet worker.

**Machine rules (2026-10-29, after the 7-hour GPU wedge; details `tools/brute/v2r/ab_ingame.md` "GPU gates")**

- Every engine capture goes through `tools/brute/capture.sh`, which runs the machine-wide gates first (`tools/gpu/gpu_gates.py`):
  an `UnrealEditor` in state E/Z = machine-wide pause, notify the owner; 2+ GPU clients of any kind (engines, Blender, torch /
  `reader.train` / video2rig python) = refuse; GPU util < 90 % on three readings 5 s apart (waits up to 10 min); 20 s since the
  last launch anywhere (`~/.cache/gpu-slot/last_launch`). STREAMING flag and the 11-13 ET window as before.
- Frame-1 watchdog: a Brute run with no `WH_BRUTE tick1` line within 120 s is SIGTERMed (60 s, SIGKILL last), exit 5, not retried.
- `ab_ingame.py run` launch budget: at most 6 cold launches per rolling hour, 30 s cool-down between cases, printed as it goes.
- Offline check of all of it: `tools/brute/v2r/test_ab_ingame_gates.sh` (never launches anything).


**Goal:** re-animate and enhance every existing Brute clip through the video2rig route (first-frame MiniMax H3 video at 768P via fal.ai, joint reader, per-frame fit, Blender Action), as set out in the plan. [1]

- Plan `docs/brute/video2rig/PLAN.md` · ledger `docs/brute/video2rig/LEDGER.md` · gates `docs/brute/video2rig/GATES-phase0-1.md` · prompts `docs/brute/video2rig/prompts/` (one `.txt` per clip plus `INDEX.md`). [2]

**Branch and state**

- Branch `chinese-animation-upgrades`, HEAD `2a53715` (`tools/brute/v2r/run_clip.sh: per-clip pipeline ...`). [3]
- Remote: `## chinese-animation-upgrades...origin/chinese-animation-upgrades` with no ahead/behind marker, so it matches the remote-tracking ref as last fetched. No fetch was run for this entry. [4]
- Uncommitted: 24 untracked `tools/brute/cases/ab_*.json` (the A/B cases) and untracked `tools/brute/v2r/ab_ingame.py`. Nothing else is modified. [5]
- Commits since `8be8157` (Handoff: camera/music fix built), 14 total, newest first: [6]
  - `2a53715` run_clip.sh per-clip pipeline (size gate, check, run, review, import, refine, export, sheet) with tests
  - `b716689` Fall clip from the air start picture; all 17 clips generated, 6.96 USD total
  - `57c411c` Phase 3 generation batch (13 ground + 2 wall clips, 20 takes, 6.18 USD)
  - `e34846e` GATES-phase0-1 (tool gates, rig/start facts, reader timings, pilot billing, air project)
  - `a295dca` blind A/B harness (3 fixed cameras, seeded labels, KEY hidden from the critic)
  - `a76c1cb` Brute optional `Config/BruteClipTiming.json` overrides; `measure_timing.py` proposes them
  - `c518614` Fall prompt rewritten for the air start picture
  - `ba6abde` v2r_rig, export_clip (EXPORT_GATE), refine_brute (REFINE_GATE), offline round-trip tests
  - `3c15fe8` fal MiniMax H3 generator (queue API, resume, balance/price) and silhouette size gate
  - `a8aa8e5` prompts for all 17 Brute clips + INDEX
  - `5c894a2` ledger clip rows, spend table, Phase 0 gate lines
  - `5a415aa` Plan: spend rule (fal balance first, then Higgsfield; no per-clip stop)
  - `61db2e6` Plan: fal H3 endpoint verified, Higgsfield fallback
  - `7220c6b` Brute video2rig + MiniMax (fal) animation upgrade: plan only

**Projects** (`/Users/midir/hulk/Local/video2rig/`, all gitignored) [7]

- `brute-aligned`: ground project. `align.py`, `clips/`, `creature.json`, `model.blend`, `reader/`, `rig/`, `start/`, `work/`, `limbs.txt`, `twins.txt`, `export_rig.log`. Reader training in progress; no `reader.pt` yet.
- `brute-air`: airborne project. `build_info.json`, `clips/`, `creature.json`, `model.blend`, `reader/`, `rig/`, `scripts/`, `start/`, `work/`, `REPORT-air.md`, `limbs.txt`, `twins.txt`, `start_render.log`, `export_rig.log`. Poses and renders done (`reader/poses.npz`, `reader/renders/`); no `reader.pt` yet.
- `brute`: original, superseded. `REPORT-phase0.md`, `hinges.txt`, `model.blend1`, `creature.json`, `rig/`, `scripts/`, `start/`.
- `motion-v2r`: does not exist yet. It is the export target; `run_clip.sh` defaults `--motion-dir` to it. [8]
- `work-tools`: scratch (`assemble_motion_dir`, `assemble_out`, `fake_fit`, `logs/`, `motion_*`, `proj_size`, `proj_size_air`, `proj_test`, `sheet/`, `stubfork/`, `synthetic_fit_idle.npz`).
- `ab`: contains `test-idle` only.

**Clips generated** [9]

- `brute-aligned/clips/` (21 mp4, bytes): clap_v1 829187; idle_v1 977897; jump_v1 910088; jump_v2 747310; land_v1 992474; lift_v1 981409; punchl_v1 792863; punchr_v1 894412; punchr_v2 822585; run_v1 1643157; slap_v1 842289; smash_v1 794209; stoplunge_v1 853226; stoplunge_v2 965959; throw_v1 971707; uppercut_v1 874522; walk_v1 1266005; wallattach_v1 964393; wallattach_v2 879433; wallclimb_v1 1073050; wallclimb_v2 1105175.
- `brute-air/clips/` (1 mp4): fall_v1 802085.
- Per-clip verdicts (check, size gate, A/B) are in the LEDGER.md Clip ledger table. Not retyped here. The ledger records two failed takes for StopLunge and Jump, each with the old clip kept.
- Gap: the LEDGER row for Idle v1 is all dashes, although `idle_v1.mp4` exists and the Spend table lists an Idle pilot at 0.48 USD.

**Reader state** [10]

- `brute-aligned` training: PID `94848` (`reader.train ... --minutes 8.0 --steps 9000 --out reader/reader.pt`), parent PID `91354` (`reader.prepare ... --steps 9000 --blender ...`). Last line of `reader/train.log` at check time (02:39): `[4832.6s] step 2200 loss 5.5183 (2.185 s per step, 24% of the time)`. Target is 9000 steps.
- `reader/prepare-9000.log` is only 62 bytes (`VISIBLE 3000 poses in 27.0 s`); the live progress is in `reader/train.log`.
- Other sessions' reader processes, not ours, do not touch: PIDs `27311`/`27313` (mayor_mine, under `~/Markhor-Meadow-M3-2026-10-10`) and PIDs `77726`/`77731` (mayor_chop, same root). All four list cwd `~/video2rig`.
- `brute-air`: no reader yet. Its `reader/` holds `poses.npz`, `visible.npz`, `renders/`, `prepare-skiptrain.log`, `prepare-skiptrain-air.log`. Worktree `/Users/midir/video2rig-brute-air` exists at `1c720d4` (`reader.poses: opt-in air config ...`).

**Next steps (from the director's brief, in order)**

1. Ground clips, one at a time: `tools/brute/v2r/run_clip.sh /Users/midir/hulk/Local/video2rig/brute-aligned <clipname> <Clip> --loop` or `--return-to-stance`. Loops: idle_v1 Idle, walk_v1 Walk, run_v1 Run, wallclimb_v2 WallClimb. Return-to-stance: all others.
2. Fall: `fall_v1 Fall --loop --fork-dir /Users/midir/video2rig-brute-air`, once the air reader exists.
3. Assemble (`tools/brute/assemble_motion.py`) into the motion-v2r files, then `python3 unreal/WebHomage/Scripts/build_brute.py` (headless commandlet through gpu_slot; imports brute_anim.fbx), capture cases `tools/brute/cases/ab_*.json`, blind A/B by an Opus critic, timing JSON via `tools/brute/v2r/measure_timing.py`, then the HANDOFF gate lines (none written yet).

**Gaps to resolve before step 1**

- `run_clip.sh` line 17 lists loop modes as "Idle Walk Run Fall". WallClimb is not in that list, but `docs/brute/video2rig/prompts/INDEX.md:20` marks WallClimb as a loop "yes (segment)". Resolve before running `wallclimb_v2` with `--loop`.
- Brute content import = `unreal/WebHomage/Scripts/build_brute.py` (the Unreal import; `tools/ue_char/brute/build_brute.sh` is an older wrapper). [11]

**Rules in force**

- One paid clip at a time. Never fit a clip that fails the check. Two failures keep the old clip. Never commit to `main`.
- fal key at `~/.config/fal/secrets.env`, read in-process, never printed. Its presence was confirmed with `test -f` only.
- Blender headless only. Cap of 2 renderers when Unreal is involved, otherwise 4 Blender processes.
- No captures while `~/.cache/gpu-slot/STREAMING` exists. At check time it was absent.
- Never touch other sessions' reader trainings (PIDs listed above).

**Spend** [12]

- fal (from the LEDGER Spend table): 6.96 USD total (Idle 0.48 + batch 6.48). Balance before 23.65 USD; after about 16.69 USD (derived, per the table).
- Higgsfield: unknown (`?` in the table).
- Per-clip prices in the ledger: 0.30 USD for a 5 s take, 0.36 USD for a 6 s take.

**Footnotes: commands used to verify this entry**

1. `sed -n 1,12p ~/hulk/docs/brute/video2rig/PLAN.md` (goal quoted from the owner instruction paragraph)
2. `ls -la ~/hulk/docs/brute/video2rig/ ~/hulk/docs/brute/video2rig/prompts/`
3. `git -C ~/hulk log -1 --oneline`
4. `git -C ~/hulk status -sb | head -1`
5. `git -C ~/hulk status --short`
6. `git -C ~/hulk log --oneline 8be8157..HEAD`
7. `ls /Users/midir/hulk/Local/video2rig/{brute-aligned,brute-air,brute,motion-v2r,work-tools,ab}`
8. `ls /Users/midir/hulk/Local/video2rig/motion-v2r` (no such directory)
9. `ls -la /Users/midir/hulk/Local/video2rig/brute-aligned/clips/*.mp4 /Users/midir/hulk/Local/video2rig/brute-air/clips/*.mp4`
10. `tail -n 1 /Users/midir/hulk/Local/video2rig/brute-aligned/reader/train.log`; `ps -axo pid,etime,command | grep "reader.train /Users/midir/hulk" | grep -v grep | cut -c1-100`; `ps -o pid,ppid,etime,command -p 91354,94848`; `ps -o args= -p <pid>` for PIDs 27311, 27313, 77726, 77731; `lsof -a -p <pid> -d cwd -Fn`; `ls .../reader/reader.pt` (no such file, both projects)
11. `find ~/hulk/tools ~/hulk/Local/video2rig -name 'build_brute*'`
12. `grep -n -A 25 -i spend ~/hulk/docs/brute/video2rig/LEDGER.md`
- Also: `git -C /Users/midir/video2rig-brute-air log -1 --oneline`; `cat ~/.cache/gpu-slot/STREAMING` (No such file); `ls ~/hulk/tools/brute/cases/ab_*.json | wc -l` (24); `grep -c '| fal |' ~/hulk/docs/brute/video2rig/LEDGER.md` (22); `sed -n 9,30p ~/hulk/tools/brute/v2r/run_clip.sh`; `grep -n -i wallclimb ~/hulk/docs/brute/video2rig/prompts/INDEX.md`

## Owner play session 2026-10-24 (live)

- Owner played live via `Play-Brute.command`; requested: remove the background music, fix the rooftop camera lock.
- `c1e19c2`: `UWHMusicSubsystem::EnsureStarted` now requires `-WHMusic` (silent by default; `SW_CuriousGroove` is the only audio asset in the project, there is no ambient-sound system to restore).
- `c1e19c2`: `UpdateCamera` boxed-in lift no longer fires when the arm is crushed by an up-facing floor/roof slab (normal Z > 0.5); on roofs the pitch stays free, the boom just shortens. Occlusion check ignores a held car.
- BUILT: `libUnrealEditor-WebHomage.dylib` relinked while the session ran (manifest already pointed at the unsuffixed dylib). Owner playtest of the fix pending -- the running window keeps the OLD code until relaunch.

# Brute — rolling handoff (updated 2026-10-16, v2 body + clips integrated in Unreal)

Owner direction 2026-10-15: replace all of Spider-Man with a big green Hulk-like character; no swinging — he stomps, jumps and
leaps. Owner "go" (full permissions, "don't interrupt other sessions", "use the Customuse API/MCP for assets"):
**jumping, launching, hitting, slapping, thunderclap, picking cars up to throw them, HUGE jumps and grand slam.**

Read `docs/brute/BRIEF.md` (design), `docs/brute/RESULTS.md` (loop-1 gameplay evidence), `docs/brute/MOVESET.md`
(controls + numbers), `docs/brute/ASSETS.md` (asset provenance + pipeline).

## Where we are

**v1 gameplay is live in-game on `brute`** (all pushed): Brute is the default pawn (`-WHSpidey` restores Spider-Man),
walk/run/sprint, charged super jump (~40 m/100 m; running 46 m/115 m), leap chain, air dash x2, wall run/top-out/kick,
crater landings, grand slam (air dive + ground), punch-punch-slap, sprint launcher uppercut, thunderclap, grab/throw cars,
crowd panic, HUD (collateral + charge meter), camera polish. Everything in RESULTS.md was verified by scripted offscreen
captures; the owner has played it live once.

**v2 asset (body + animation) is the current work thread.** The owner rejected two earlier bodies ("super fucking ugly",
"still looks horrible") and several animation passes. The current set below is the one the owner reviewed in the localhost
viewer and approved clip-by-clip. **Integrated into Unreal 2026-10-16** (see "In-game v2" below); the owner has not played it yet.

## Approved v2 asset set (owner-reviewed 2026-10-15)

Model: **"Emerald Behemoth"**, Customuse CR 2.1 (NOT Tripo), task `cbdd9877-6c27-4a3f-ad89-9522ece557f2`, 100 credits.
Rigged via Customuse website Humanoid Auto Rig node (Cartwheel), 8 credits → 52-bone humanoid skeleton incl. fingers,
PBR textures. Rigged FBX: `~/hulk-scratch/brute_v2/` (exported from Downloads as `Emerald_Behemoth_Rigged_fbx.zip`).

Approved clips (assembled into `~/hulk-scratch/brute_v4/brute.glb` + `brute_anim.fbx`, viewer copies in
`tools/brute/viewer/`):

| Clip | Source | Notes |
|---|---|---|
| Idle | Cartwheel T2M via Customuse | approved |
| Walk | Cartwheel | approved (2nd gen; 1st was "zombie" — prompt asked "slow heavy", got shuffle). Upright lumbering, ~0.6 m/s |
| Run | Cartwheel | approved, ~2.1 m/s |
| StopLunge | Cartwheel | approved after trim: sprint → slam → coil, cut at coil (full clip's stand-up blew out the traps) |
| Jump | Cartwheel regen | approved: ~2 s charge crouch (knees bent, looking up), then explosive launch |
| WallAttach | Cartwheel regen | approved: leap at wall, both fists punch in overhead, hangs |
| WallClimb | **reuses WallAttach clip** | owner call: separate climb attempts all rejected; game replays the attach slam per step |

Rejected motion attempts (do NOT resurrect): Blender hand-authored clips ("looks like shit"), Cartwheel climb v1/v2
(ladder-like, hands too close, elbows in), Meshy T2M climb (`~/hulk-scratch/meshy/climbA/B_rt.glb`, still "completely
fucked up"). WallClimb = WallAttach was the owner's suggested fix.

## Pipeline (all scripts in `tools/brute/`)

- `assemble_motion.py` — Blender script: imports rigged FBX + per-clip GLBs from `~/hulk-scratch/brute_v2/motion/`,
  cleans (root-drift removal, seamless loops, 2.6 m height, feet on ground), writes `brute.glb`, `brute_anim.fbx`,
  `clips.json`. Blender 5: actions need `assign()` slot handling — already coded.
- `viewer/` — Three.js viewer (`index.html`, `serve.sh` → http://127.0.0.1:8765). Camera follows hips; wall clips show
  translucent wall (`wallZ` in clips.json). Owner refreshes with Cmd+Shift+R.
- `retarget_motion.py` — maps Meshy 24-bone rig → Behemoth 52-bone skeleton; env `BRUTE_FIST`/`BRUTE_FIST_AXIS` add fist
  curl (Meshy has no fingers).
- `meshy_motion.py` — Meshy API helper (rig, text-to-motion prime 10 cr, apply 3 cr).
- `animate_brute.py`, `rig_brute.py`, `segment_brute.py` — v1 pipeline, kept for reference.
- `capture.sh`, `cases/` — scripted in-game captures.

## In-game v2 (2026-10-16, pushed)

- `python3 unreal/WebHomage/Scripts/build_brute.py` imports `~/hulk-scratch/brute_v4/brute_anim.fbx` + the Customuse maps into
  `/Game/Brute/Body` (`SK_Brute`, `A_Brute_<Clip>` x7, `M_Brute`); old `/Game/Brute/Skel` + `Parts` are deleted. A fresh folder
  is required: re-importing over the v1 `SK_Brute` fails with "cannot merge bone tree with the existing skeleton".
- `ABruteCharacter::BuildClipRig` / `AnimateClips` (BruteCharacter.cpp, end of file): clips sampled on the game thread into the
  poseable mesh. Ground: Idle / Walk / Run by speed (rates clamped, feet slide at sprint speed by design), charge = Jump clip's
  crouch scrubbed by the charge (from a run: StopLunge coil), air = Jump launch -> apex hold, hard landing = StopLunge coil,
  wall = WallAttach slam then the slam segment looped as the climb. Root travel removed, lowest foot pinned to the street, forward
  measured from a sampled idle frame (the bind pose is turned 77 deg vs the clips). Combat moves (punch/slap/clap/smash/grab/
  carry/throw/uppercut/slam dive/dash) still come from the procedural joints, applied as a spine + arm-aim overlay.
- FX the owner asked for: full charge cracks the street (`charge_floor_crack`), a strong take-off leaves a crater; every climb
  fist leaves a wall crater with cracks, rubble and dust (`ABruteShockwave::InitWall`, events `wall_punch L/R`).
- Verified offscreen (movie frames inspected): `tools/brute/capture.sh v2_loco -movie` and `m3_wallrun -movie`; strips in
  `docs/brute/evidence/v2_ingame_*.jpg`. Not verified: owner live play, Manhattan_Island, fps.
- `-WHBruteV1` falls back to the old procedural path (needs the old Skel content, which the build now deletes -> bricks).

## Owner fix list 2026-10-16 (status)

1. DONE `ef67045` stuck inside buildings: speed-scaled substeps (<= 0.3 m per substep), indoor watchdog `IsIndoors` (real geometry:
   roof above -- also traced down from above, roofs are one-sided -- and walls within 15 m on 7/8 sides; the box index misses some
   buildings and overhangs sidewalks, so it is NOT used), rescue to the last verified-outdoor spot else onto the roof, hold R / d-pad
   down 1 s = manual respawn. Cases `fix1_inside` (spawned inside -> on the roof in 1 s), `fix1_stuck_repro`; no false rescues in
   v2_loco / m3 / m11 / m5 / m6.
2. DONE `7c41923` latch from a jump: air contact with a tall face = 0.45 s wall-slide window, ATTACK (buffered 0.3 s, also a 1.6 m
   probe ahead / sideways when gliding past) = `wall_latch`; latched he hangs, W / Shift climbs (Shift x1.3), S drops, Space kicks.
   Case `fix2_latch`.
3. DONE `e4f1f67` attacks wreck everything: `BruteWorld::BreakProps` (called from every Blast) hides small street-level instances
   of the city HISMs (lamps, sign poles, hydrants, trash, newsboxes, parked ISM cars, trees = bark + its leaves as one falling tree)
   and spawns `ABruteDebris` physics copies (cap 40 per blast / 180 alive); every walker in the blast radius is flung (cap 30 per
   blast, ~60 alive); cars x1.3 speed / x1.35 up / more spin. `-WHBruteDebugBreak` logs candidates.
4/5. DONE (owner "go ahead", 2026-10-16) combat + air clips in game: `build_brute.py` imports `~/hulk-scratch/brute_v5/brute_anim.fbx`
   (17 clips; two commandlets: clean, then import; if Interchange drops the takes it re-imports them explicitly as animations onto
   the skeleton). `ABruteCharacter::ActClip` maps each act to its clip segment (from / to / rate) and the act's hit time + duration
   now come from the clip's contact time (clips.json `hit`): punches alternate PunchR / PunchL, Slap, Clap, Smash, Uppercut, Grab =
   Lift, Carry = Lift hold, Throw. Falling = Fall loop, hard landing = Land (superhero landing, then he rises). Procedural arm overlay
   only for slam dive + air dash now. Case `v3_combat`. Clap + Throw redone 2026-10-16 (Meshy takes corrected in Blender:
   `tools/brute/clap_fix.py`, `throw_splice.py`; palms meet at the chest, Throw = hard overhead hurl). Still weak: Slap (spins, back to
   camera). Meshy balance 1,064.


## Look + animation quality pass (2026-10-16/17, owner: "focus heavily on the animations and the visual look ... highest quality")

- Anim worker (`tools/brute/anim_*.py`): forward Slap (twist limited, arm arc in front), mirrored Clap (rig is 6 cm asymmetric),
  heavy Throw recovery, frame 0-1 bind-pose pops removed on all Cartwheel clips + loop seams 0 deg, foot locking with leg IK on
  combat clips, Uppercut crouch lifted. 30 Meshy credits (balance 1,034).
- Mesh worker (`tools/brute/mesh_*.py`, report `~/hulk-scratch/brute_mesh/REPORT.md`): bone-heat re-weight of arms / shoulders /
  chest / upper back, hair locked to the head, elbow smoothing (shoulder peak stretch 10.8x -> 5.6x, folded tris/frame 91 -> 70).
  Then `mesh_subdiv.py`: 1 level Catmull-Clark applied under the skin (9.5k -> 55k verts) = `~/hulk-scratch/brute_mesh/brute_rigged_subd.glb`,
  which is now the FIRST ARGUMENT of assemble_motion.py (`brute_v5` rebuilt from it).
- Material (`build_brute.py`, `--material-only` for look-dev): baked AO (`tools/brute/bake_ao.py` on the subd mesh ->
  `~/hulk-scratch/brute_look/T_Brute_AO.png`) as occlusion + cavity, normal x1.4, skin-masked emerald deepening. MSM_SUBSURFACE
  was tried and rejected (washed the form out to flat lime).
- Vision critic (subagent_general; subagent_explore cannot view images) scored LOOK 5 / ANIM 4 before the fixes; fixed after it:
  ground-level dust, no beige arc tubes on cones, flat wall cracks + flat impact disc, Fall pose right after launch, sprint lean,
  closer combat camera, deeper skin. Round 2 (owner "fix rest"): menace posture layer on Idle / Walk in game (chest hunched, head
  forward, arms flared, elbows bent; `MenaceW` in AnimateClips), skin roughness noise + matte cloth on the shorts (material), wall
  impacts = fist-sized charcoal dents + hairline cracks + glass shards + rubble, camera rises when a car / truck (traffic has no
  collision: `AWHLifeTraffic::SegmentHitsCar`) or physics body blocks the view. Round 3: veins + shorts folds baked into the
  normal map (`tools/brute/tex_bake.py` -> `~/hulk-scratch/brute_tex/`, vein tint mask; normals now imported green-flipped =
  OpenGL->UE), projected crack decals for wall punches + ground craters (`tools/brute/make_crack_decal.py`, `M_BruteCrackDecal`;
  the body ignores decals), armpit corrective morphs CorrArmUp/CorrArmSide _L/_R (`tools/brute/mesh_corrective*.py`, mesh =
  `~/hulk-scratch/brute_corr/brute_rigged_corr.glb` is now assemble_motion's first arg; driven in `ApplyCorrectives` by the
  upper-arm angle to the Neck->Spine1 axis: Up = smoothstep(100,150), Side = smoothstep(50,85) x (1 - Up)). Correctives help Lift /
  Smash / Throw / WallAttach / Clap. Round 4 ("fix leftovers"): correctives v2 = 18 morphs (CorrArm{Up,UpFwd,UpSide,Fwd,Side,
  MidFwd,LowFwd,MidSide,LowSide}_L/_R) over elevation x azimuth, Gaussian kernels + NULL centre, gate smoothstep(50,85)
  (`ApplyCorrectives` = port of `mesh_corrective_lib.py weights()`); every clip now has fewer armpit creases than no correctives
  (Smash -42 %, Slap -33 %, WallAttach -32 %, Throw -30 %, ..., Idle unchanged). Veins re-baked smooth at 4x, seam-consistent
  across UV islands (`tex_seams.py`), calmer upper arms, frayed torn hem. Camera backs up +7 m when carrying a bus / truck.

## Next steps (after the list)

- Independent critic pass, desktop fps measurement.
- Wall run face test now probes at 3 heights (`14c091e`); at m11's (224,-8) he now pops onto a ~4 m storefront ledge, then re-catches.
- Camera: real-geometry sweep + boxed-in view (rises over walls / drops under awnings + tree crowns), `-WHBruteDebugCam` logs it.

## Gotchas (learned the hard way)

- Customuse tab: owner designated ONE Chrome tab (id was 911546424, window with 3 other tabs). Drive it via AppleScript
  JavaScript by tab ID — no mouse/focus, works while owner uses the Mac. **Do not open new Customuse tabs/windows.**
  ALWAYS verify the prompt field actually contains the new text before pressing Run (readonly-unlock races cost one
  wasted 33-credit run already). Codex Computer Use was tried and abandoned — collides with owner input.
- Credits: Customuse ≈2,876 left (Simple T2M ~33/run but billing was uneven — one run took 67/150; verify before/after).
  Meshy ≈1,314 left (`~/.agents-md/.secrets/meshy.env`, `MESHY_API_KEY` — never print/commit). Tripo secrets at
  `~/.agents-md/.secrets/tripo.env` (unused so far).
- Customuse Simple mode T2M is weak for nonstandard motion (climb failed repeatedly); Detailed ~98 cr. Meshy prime is
  cheap and fast (~15 s) but also failed this climb. For future hard motions: prefer retargeting Meshy/preset clips and
  correcting in Blender over endless Cartwheel rerolls.
- Viewer lies to watch for: hips-follow camera (fixed), leftover Cartwheel "Icosphere" (removed), one-shots must not
  ping-pong, check actual playback not just stills before telling owner it's good.
- GPU: shared `~/.cache/gpu-slot`, cap 2 renderer engines; captures need `-benchmark -fps=N`; `capture.sh` handles it.
  Don't kill other sessions' engines.
- Scratch: `~/hulk-scratch/` (disposable): `brute_v2/` rigged FBX + motion GLBs, `brute_v4/` assembled output, `meshy/`.
  Logs `~/hulk-logs/`.
- `Content/` is git-ignored; imported assets regenerate via `build_brute.py`.
- Owner tone: blunt, curses, hates being shown unviewed output. Watch actual playback before claiming quality.
  Show, don't promise.

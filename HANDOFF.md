## FINAL SET (2026-10-31): Seedance Smash + Seedance Lift ship; everything else as shipped

Branch `chinese-animation-upgrades` (never `main`; the owner merges). Decision by the director from the blind in-game close-up A/B (`cuold` vs
`cusd`, one Opus critic, decoded): **Smash = Seedance, Lift = Seedance**; PunchR stays old, Clap stays the shipped hold-compressed clip (tie), PunchL /
Slap / Throw unchanged. Details and verdict wording: `docs/brute/video2rig/SEEDANCE.md` ("17-clip status").

```
FINAL Smash   SEEDANCE (Brute_smash-v2r.glb, motion-sd)      blind close-up A/B: Seedance wins (double-fist raise, head back; old twisted/side-on)
FINAL Lift    SEEDANCE (Brute_liftthrow-v2r.glb, motion-sd)  blind close-up A/B: Seedance wins (palms on the car; old floats it ~35 px for ~2 s)
FINAL PunchR  OLD (Brute_punchr.glb)                          Seedance lost (forearm swipe, head down, no fist at contact)
FINAL Clap    video2rig MiniMax, hold-compressed (shipped)    Seedance tie -> old kept ("visibly better" rule)
FINAL Idle Walk Run Slap Fall   video2rig MiniMax (shipped)
FINAL StopLunge Land            video2rig MiniMax hold-compressed (shipped)
FINAL PunchL Throw Uppercut Jump WallAttach WallClimb   OLD (shipped)
TOTAL 2 Seedance + 5 MiniMax + 3 MiniMax-hc + 7 old = 17; clips_meta differs from brute_v5 in exactly Smash and Lift
```

- Final set dir: `~/hulk-scratch/brute_final_sd/` (`motion/` = copy of the shipped `~/hulk-scratch/brute_v2/motion/` + only `Brute_smash-v2r.glb` and
  `Brute_liftthrow-v2r.glb` from `Local/video2rig/motion-sd/`; outputs `brute.glb`, `brute_anim.fbx`, `clips_meta.json`, `clips.json`, `logs/`). Local only (GLB/FBX are
  not committed).
- Rebuild (Blender one at a time, `taskpolicy -b`, then one headless commandlet through gpu_slot):
  ```
  cd ~/hulk; F=~/hulk-scratch/brute_final_sd
  taskpolicy -b /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P tools/brute/assemble_motion.py -- ~/hulk-scratch/brute_corr/brute_rigged_corr.glb $F/motion $F
  taskpolicy -b /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P tools/brute/v2r/measure_timing.py -- $F/brute.glb --all --out $F/logs/timing_all_raw.json --dump $F/logs/telemetry.json
  python3 unreal/WebHomage/Scripts/build_brute.py --fbx $F/brute_anim.fbx      # expect 17 A_Brute_* lines
  ```
- `unreal/WebHomage/Config/BruteClipTiming.json` is now the COMMITTED FINAL STATE (shipped file + Smash, Grab, Carry acts, hit_table Smash, measured Smash/Lift, clip
  list Smash/Lift; Carry.to = 2.7 by hand; Clap and PunchR rows = shipped). `~/hulk-scratch/brute_sd/BruteClipTiming.shipped.json` is the pre-Seedance backup. Fresh
  measurement on the final set matched the Seedance A/B timing exactly for Smash, Grab and the telemetry; the only difference is the deliberate Carry.to (3.533 -> 2.700).
- The Seedance A/B set `~/hulk-scratch/brute_sd/` (4 Seedance clips) is superseded; do not rebuild from it.
- Capture gaps the critic found (OPEN, not fixed): no angle shows the feet, so foot contact is unproven; the car blocks the lens during the grab and the throw
  release; the smash contact falls below the frame. A reshoot needs the camera pulled back and lowered (`--cam-dist` larger, lower camera height).
- Confirmation capture `cufinal` (2026-10-31 02:24-02:36, `--cam-dist 4.0 --hide-help`, combat_tq + grab_tq): `ab_ingame.py check --label cufinal` ok for both. Unreal import printed 17 A_Brute_* lines; the 7 BruteFx "Error opening file" linker warnings were already in the 10-30 build log (not new). Frames in `/private/tmp/claude-501/cufinal-frames/`: Lift carry at 2.5 s has the hands on the car; the Smash window from 5.675 s matches the judged `cusd` capture frame for frame (the first frames differ because the move before Smash is now the old Clap).
- Still pending (owner): the feel playtest of the final set, the merge decision for this branch and the fork branches.

## video2rig animation upgrade — Phase 6 handoff: FINAL SET after round 4 (2026-10-30 04:45 EDT, Opus 5.5 high)

> Superseded for Smash and Lift by the "FINAL SET (2026-10-31)" section above (both now Seedance; the rows below still describe the pre-Seedance shipped set, `brute_v5`).

Branch `chinese-animation-upgrades` (never `main`; the owner merges). Plan `docs/brute/video2rig/PLAN.md`, ledger
`docs/brute/video2rig/LEDGER.md` (every take, check, fit, refine, verdict, dollar), blind verdicts `AB-ingame-critique.md` (r2),
`AB-ingame-r3-critique.md` (r3) and the round-4 rows in LEDGER, hold compression `HOLD-COMPRESSION.md`.

**Verified state (commands run for this entry)**

- `/Game/Brute/Body` holds the FINAL set: `python3 unreal/WebHomage/Scripts/build_brute.py` (default input = the shipped
  `~/hulk-scratch/brute_v5/brute_anim.fbx`), exit 0 at 04:38:55 EDT, 17 A_Brute_* (log `~/hulk-scratch/brute_v2r_r4/build_brute-final.log`).
  Content/ is gitignored; the build is reproducible from the inputs below.
- Shipped motion dir `~/hulk-scratch/brute_v2/motion/`: the 8 winning GLBs (+ export JSONs) beside all 16 old files (nothing removed;
  the `-v2r` / `Brute_v2r_` names sort first, so a new file wins only where one exists). Run = run_v2 and Fall = the round-4 refit
  (both sha-equal to `Local/video2rig/motion-v2r-r4/`), Land = hold-compressed v1 (sha-equal to `motion-v2r-hc/`).
- `assemble_motion.py` re-run into `~/hulk-scratch/brute_v5/` (log `~/hulk-scratch/brute_v2r_r4/assemble-final.log`): clips_meta 8 new/hc
  + 9 old, every clip equal to the r4 build's meta (Run 3.767 s, 3.80 m/s); Land and Fall durations as r3. md5 brute.glb 22961571...,
  brute_anim.fbx 89c7bce9.... Pre-v2r outputs kept in `brute_v5/pre-v2r-20261018/`.
- `unreal/WebHomage/Config/BruteClipTiming.json` (8b1cbdc, measured on brute_v5): Slap 1.527 / 3.020 / 1.6 / hit 2.167, Clap 0.195 /
  1.672 / 1.6 / hit 0.933 (game-time deltas 0.000), LandStart 0.000, LungeStart 0.533 = the r3 values. Run is NOT speed-matched from the
  clip: BruteCharacter.cpp plays it at clamp(ground speed / 11, 0.9, 1.9), so Run v2 (3.80 m/s in place) vs v1 (4.23) may change
  foot slide slightly; watch it in the playtest. The 9 old clips use the C++ constants. GLBs, blends and captures are local only.

**Final set**

| clip | source | file (in `~/hulk-scratch/brute_v2/motion/`) | why |
| --- | --- | --- | --- |
| Idle | new (v2r) | Brute_v2r_idle.glb | in-game NEW (low-med) |
| Walk | new (v2r) | Brute_v2r_walk.glb | in-game NEW (low-med) |
| Run | new (v2r, run_v2) | Brute_v2r_run.glb (from motion-v2r-r4) | r2 v1 tie vs old; r4 v2 vs v1 tie on screen, v2 ships on numbers (fit 4.35 vs 4.65 px, seam 0.46 vs 0.67) |
| StopLunge | new-hc | Brute_v2r_stoplunge.glb | r2 NEW (med); r3 hc vs r2 tie, hc kept (already built, 2.23 s) |
| Slap | new (v2r) | Brute_slap-v2r.glb | NEW in r2 (med) and again in r3 (med) |
| Clap | new-hc | Brute_clap-v2r.glb | r2 OLD (low-med); r3 hc beats old (med) |
| Fall | new (v2r, round-4 refit) | Brute_fall-v2r.glb (from motion-v2r-r4) | r2 tie vs old (med-high); r4 refit pixel-identical to r3 Fall, adopted (LeftFoot range warning cleared) |
| Land | new-hc (v1) | Brute_land-v2r.glb (from motion-v2r-hc) | r2 NEW (med); r3 hc beats r2 Land (high); r4 Land v3 LOST to it (high) |
| PunchL | old | Brute_punchl.glb | OLD (low); neither take lands a clean straight punch |
| PunchR | old | Brute_punchr.glb | OLD (med); same note |
| Uppercut | old | Brute_uppercut.glb | OLD (low-med); new is a mild overhead reach |
| Lift | old | Brute_liftthrow.glb | OLD (high); new take drops the car |
| Throw | old | Brute_throw.glb | OLD (high); new take drops the car |
| WallClimb | old | Emerald_Behemoth_attach_30fps.glb (reuses WallAttach) | OLD (low-med); new flails both hands off the wall |
| Jump | old | Emerald_Behemoth_jump_30fps.glb | two generation failures, never fitted |
| Smash | old | Brute_smash.glb | two check failures (1.65, 1.53 %), never fitted |
| WallAttach | old | Emerald_Behemoth_attach_30fps.glb | two failures (visual, 2.16 % check), never fitted |

**Gate lines** (check = video check %, fit = median keypoint px, seam = loop/one-shot seam ratio, drift / toe = refine foot drift / toe
minimum; numbers from LEDGER rows and `Local/video2rig/hc-refined/*_hc.json`; for old clips they describe the rejected new take)

```
GATE reader-ground PASS 2.41/2.83 px
GATE reader-air PASS 2.85/3.30 px
GATE reader-dense PASS 1.65/1.85 px (not adopted: refits with it were not better)
GATE Idle check 0.54 fit 1.81 seam 0.30 drift 1.6 toe 0.0 ab NEW
GATE Walk check 0.28 fit 2.51 seam 0.76 drift 9.5 toe 0.0 ab NEW
GATE Run check 1.08 fit 4.35 seam 0.46 drift 2.4 toe 0.0 ab tie->new (v2 by numbers)
GATE StopLunge check 1.24 fit 4.60 seam 0.00 drift 4.0 toe 0.0 ab NEW (hc = r2 tie)
GATE Slap check 0.46 fit 3.09 seam 0.00 drift 3.9 toe 0.6 ab NEW
GATE Clap check 0.26 fit 2.59 seam 0.00 drift 2.7 toe 0.0 ab NEW (hc)
GATE Fall check 0.24 fit 1.56 seam 0.37 drift n/a toe n/a ab tie->new
GATE Land check 1.01 fit 5.52 seam 0.00 drift 5.5 toe 0.0 ab NEW (hc)
GATE PunchL check 0.31 fit 3.08 seam 0.02 drift 3.3 toe 0.0 ab OLD
GATE PunchR check 0.51 fit 3.41 seam 0.01 drift 2.8 toe 0.0 ab OLD
GATE Uppercut check 0.53 fit 3.60 seam 0.01 drift 10.6 toe 0.0 ab OLD
GATE Lift check 0.58 fit 3.75 seam 0.00 drift 3.5 toe 0.0 ab OLD
GATE Throw check 0.69 fit 3.98 seam 0.01 drift 36.2 toe 0.0 ab OLD
GATE WallClimb check 0.65 fit 3.42 seam 0.54 drift 1.2 toe 445.2 ab OLD
GATE Jump check FAIL(visual x2) fit - seam - drift - toe - ab old (no new take)
GATE Smash check 1.53 FAIL fit - seam - drift - toe - ab old (no new take)
GATE WallAttach check 2.16 FAIL fit - seam - drift - toe - ab old (no new take)
GATE spend fal 8.22 USD (15.43 left; round 4 added run_v2 0.36, land_v2 0.30, land_v3 0.30)
GATE build final brute_v5 fbx-md5 89c7bce9 glb-md5 22961571 timing 8b1cbdc (build_brute exit 0, 17 assets, 2026-10-30 04:38)
```

Bar misses (4 px), recorded honestly: Run 4.35, StopLunge 4.60, Land 5.52 px. The dense reader (1.65/1.85 px gate) did not lower
them (Run 4.92, StopLunge 4.97, Land v1 5.73, Land v3 4.80): the takes themselves limit the fit, not the reader.
Fall has planting off (airborne); WallClimb's toe 445 mm is the hang (feet off the floor all window).

**Round 4 outcome** (blind pack `~/hulk-scratch/ab-ingame/blind-r4`): Land v3 lost to hc Land v1 in all three angles (high); Run v2
vs v1 tie on screen (same cycle, bob, swing), v2 ships on its numbers; Fall refit vs r3 Fall pixel-identical, refit adopted.

**Which captures prove the final content** (`~/hulk-scratch/ab-ingame/`; final `check`: old 24/24, new 24/24, r3 9/9, r4 6/6 ok)

- `idle_*` (Idle): set `new` (r2).
- `loco_*` (Walk, Run v2): set `r4` (Walk same file as r2).
- `lunge_*`, `combat_*` (StopLunge, Jump, PunchR/L, Slap, Clap, Smash): set `r3`.
- `jump_*` (Jump, Fall, Land hc v1): set `r3` (Land hc v1; the r4 Fall refit rendered pixel-identical to r3's Fall in `r4` jump_*).
- `uppercut_*`, `grab_*`, `wall_*` (Uppercut, Lift, Throw, WallAttach, WallClimb): set `old` (the C++ per-clip wall keys added
  today default to the old constants).
- Blind packs with keys in `_director/KEY.json`: `blind/` (r2 vs old, 24), `blind-r3/` (9), `blind-r4/` (6).
- Engine launches tonight (gpu_slot `runs.jsonl`, label `hulk-*`, since 2026-10-29 18:00): 56 = 46 captures + 10 build commandlets
  (5 builds x 2, -nullrhi), every one outcome `ran`; the first 6 (grab/wall 18:36-18:46) may be another hulk session's.

**Critics' open notes (not fixed)**

- The HUD control-help box covers the feet in the front and tq angles; foot sliding is unjudgeable there. Next capture revision: hide
  help (H), add a 3 s Idle hold after landing and after each loco speed.
- Landing crouch timing: the takes stand upright ~0.55 s after the crater before the crouch; it should start at touchdown.
- Punches: neither take has a closed-fist straight punch (old kept, still weak).
- Lift / Throw: the new takes drop the car (old kept).
- Uppercut: old wins; the new take is a mild overhead reach.
- Front/tq cameras are tight and chest-high; low combat poses drop out of frame.

**Fork branches** (`oh-ashen-one/video2rig`, all pushed; the owner merges, nothing merged by agents)

- `brute-lockfeet-floor` = c60a645 (lock_feet keeps the floor in the pinned foot's target height) + ede6cce (road.run `--set KEY=VALUE`
  reaches the reader fit); worktree `~/video2rig-lockfix`. Every ground fit after the fix used it.
- `brute-air-reader` = 1c720d4 (opt-in air poses) + cherry-picks 664409d / f8ba690 of the two commits above; worktree
  `~/video2rig-brute-air`.
- `mac-mps` unchanged at ec99e23.

**How to rebuild the shipped set**

1. `cd ~/hulk && /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P tools/brute/assemble_motion.py -- ~/hulk-scratch/brute_corr/brute_rigged_corr.glb ~/hulk-scratch/brute_v2/motion ~/hulk-scratch/brute_v5`
2. Timing: `Blender -b --factory-startup -P tools/brute/v2r/measure_timing.py -- ~/hulk-scratch/brute_v5/brute.glb --check-today 0.15`
   (writes `Config/BruteClipTiming.json` for the v2r clips only; exit 3 on absolute deltas is expected; the game-time table must
   print 0.00 for every written act).
3. `python3 unreal/WebHomage/Scripts/build_brute.py` (default input `~/hulk-scratch/brute_v5/brute_anim.fbx`; one headless commandlet
   through gpu_slot) and confirm 17 `[brute] anim /Game/Brute/Body/A_Brute_*` lines.
- Back to the pre-v2r clips: `build_brute.py --fbx ~/hulk-scratch/brute_v5/pre-v2r-20261018/brute_anim.fbx` and run the game with
  `-WHBruteNoClipTiming`.
- A new take wins only through its A/B: put its GLB in the motion dir (name from `export_clip.py` NAMES) only after it wins.

**How to A/B again**

- `python3 tools/brute/v2r/ab_ingame.py run --label <set> --ignore-window [--cases a,b]` (any `[a-z0-9_-]` label; budget-paced),
  then `check --label <set>`, then `pack --a <set> --b <other> --cases ... --out <dir>` (labels or dirs; a second `pack` into the same
  `--out` adds pairs). Give the critic only `<dir>/critic`; decode with `<dir>/_director/KEY.json` afterwards.

**Rule fixes made today**

- Timing rate rule (`measure_timing.py game_window`, `--selftest-rule` PASS): a length-scaled clip keeps today's game-time windows
  exactly; Rate = min(today's x length ratio, 1.6), lowered to fit the clip, never below 1.0. Loops and Land keep speed-matching.
- `ab_ingame.py check`: `wall_release` is forbidden only before the script's own release time (7d2d4e9).
- Hold compression (`refine_brute.py --compress-holds` with `--hold-frac/--hold-min-dps/--hold-max-dps/--hold-min-s/--contact-s/
  --hold-keep/--hold-keep-up/--max-seconds/--max-speedup`, plus `--stance-snap N`; 1709ce1; `HOLD-COMPRESSION.md`).
- Also: refine burst pass (`--burst-*`, Throw frame-27 arm jump), assemble skips TRIM for v2r files, per-clip wall times in
  BruteCharacter (WAttachImpact2 / WAttachEnd / WClimbImpact1), `ab_ingame.py run --label` any label and `pack --a/--b/--cases`.

**Machine rules (2026-10-29, after the 7-hour GPU wedge; details `tools/brute/v2r/ab_ingame.md` "GPU gates")**

- Every engine capture goes through `tools/brute/capture.sh`, which runs the machine-wide gates first (`tools/gpu/gpu_gates.py`):
  an `UnrealEditor` in state E/Z = machine-wide pause, notify the owner; 2+ GPU clients of any kind (engines, Blender, torch /
  `reader.train` / video2rig python) = refuse; GPU util < 90 % on three readings 5 s apart (waits up to 10 min); 20 s since the
  last launch anywhere (`~/.cache/gpu-slot/last_launch`). STREAMING flag and the 11-13 ET window as before.
- Frame-1 watchdog: a Brute run with no `WH_BRUTE tick1` line within 120 s is SIGTERMed (60 s, SIGKILL last), exit 5, not retried.
- `ab_ingame.py run` launch budget: at most 10 cold launches per rolling hour (`LAUNCHES_PER_HOUR`, owner clarification, 2c9c693;
  was 6), 30 s cool-down between cases, printed as it goes.
- Offline check of all of it: `tools/brute/v2r/test_ab_ingame_gates.sh` (never launches anything; 31/31 PASS today).

**Pending (owner)**: the feel playtest of the final set (not done yet); merge decision for this branch and the fork branches;
optional re-film with the HUD hidden. No further GPU work by this run. Disk is at 100 % (18 GB free): scratch sets
`~/hulk-scratch/ab-ingame` (~0.7 GB), `brute_v2r_candidate`, `brute_v2r_r3`, `brute_v2r_r4` can go after the merge.


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

## Seedance round (2026-10-30, owner brief 11:45 EDT; CLOSED 2026-10-31, final set above)

Owner rejected the MiniMax result ("80 % the same") and re-briefed: Seedance takes that look much better, then the pipeline, ship only what is
visibly better. Rules, ledger and findings: `docs/brute/video2rig/SEEDANCE.md`; error log that led here: operating-rules "Fidelity gates are not
quality gates" (agents-md PR #36). Progress page: http://127.0.0.1:8777/progress.html (visual; `status_loop.py` + `progress.html` in the session
scratch `before-after/` dir, server `python3 -m http.server 8777`).

- Provider: Seedance 2.5 on Higgsfield (720p, 16:9, 5 s, audio ON, literal prompt, preset declined, 35 cr); fal `bytedance/seedance-2.0/image-to-video`
  via `generate_fal.py --provider seedance2` (~0.77 USD) as a second lane. Higgsfield credits are ONE pool shared with the Invincible session
  (midir-d3): 442.64 -> 127.64 (Hulk 6 charged takes = 210, Invincible 3 = 105); Hulk stopped spending there at 127.64 by agreement.
- KEY FINDING: ~60 % of outputs are refused AFTER rendering by ByteDance's copyright classifier (fal: "Potential copyright violation"; Higgsfield
  shows "nsfw"); the figure's shape trips it, a desaturated start picture does not help on fal (the Invincible session reports black-and-white
  start pictures DO pass on Higgsfield, 2 of 2). Refusals were never charged for start-only requests (Invincible saw a charged refusal with end_image).
- Fitted + exported to `Local/video2rig/motion-sd/` (CPU, `V2R_DEVICE=cpu`, lockfix fork): Smash (check 0.69, fit 4.65 px with per-clip joint ranges
  `clips.smash_sd_v1.joints` in creature.json), PunchR (0.47, 2.26 px, refine `--lock-yaw` removed an 84 deg body turn), Clap (0.72, 2.47 px),
  Lift (fitting now). Two strikes, old clip stays: Jump, Uppercut, Slap, StopLunge (one check FAIL 3.97 % + one refusal), Land.
- Director close-ups (CPU Cycles, `~/hulk-scratch/sd-compare/<clip>/`): Smash clearly better than old; PunchR and Clap marginal; the in-game blind
  A/B decides.
- Ready for the GPU: `~/hulk-scratch/brute_sd/` (brute_anim.fbx with the Seedance Smash/PunchR/Clap, BruteClipTiming.json re-measured, README.md
  with the exact build + capture commands; add Lift once exported). Harness: `ab_ingame.py --cam-dist 4.0 --hide-help` (new; the old baseline must
  be recaptured at the same settings; pack refuses mixed settings). GPU order: Markhor readers -> Dragon reader -> Hulk captures / Invincible reader.
- New tools: refine_brute.py `--lock-yaw`; generate_fal.py `--provider seedance2` (+ selftest_fal.py); ab_ingame.py `--cam-dist`, `--hide-help`.
- fal lane closed (14:55): bytedance/seedance-2.0 refused 8 of 8 outputs on this figure (copyright), 0 USD charged, fal balance still 15.43.
  Remaining moves without a Seedance take (PunchL, Throw, Run, Walk, Idle, Fall, Jump, Uppercut, Slap, StopLunge, Land, WallAttach, WallClimb)
  keep today's clips unless the owner adds Higgsfield credits (the ~35 % pass lane) or changes the figure's silhouette (hair/shorts), which is a
  model change and the owner's call. Prompts for all of them are written under docs/brute/video2rig/prompts/seedance/.
- 16:39: OLD baseline recaptured at the close-up settings (`cuold`: combat + grab, 3 angles, `--cam-dist 4.0 --hide-help`, 6 gated launches, check 6/6 ok, `~/hulk-scratch/ab-ingame/cuold/`). Remaining GPU steps (timing swap -> `build_brute.py --fbx brute_sd/brute_anim.fbx` -> `cusd` captures -> pack -> Opus blind critique -> restore/ship) run after Dragon's reader (~20:00) and Invincible's training; exact commands in `~/hulk-scratch/brute_sd/README.md`.

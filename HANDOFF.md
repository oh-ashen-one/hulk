## video2rig animation upgrade — Phase 6 handoff: FINAL SET = r3 (2026-10-29 22:45 EDT, Opus 5.5 high)

Branch `chinese-animation-upgrades` (never `main`; the owner merges). Plan `docs/brute/video2rig/PLAN.md`, ledger
`docs/brute/video2rig/LEDGER.md` (every take, check, fit, refine, verdict, dollar), blind verdicts `AB-ingame-critique.md` (r2) and
`AB-ingame-r3-critique.md` (r3), hold compression `HOLD-COMPRESSION.md`.

**Verified state (commands run for this entry)**

- `/Game/Brute/Body` holds the final set: `build_brute.py --fbx ~/hulk-scratch/brute_v2r_r3/out/brute_anim.fbx`, exit 0, 17 A_Brute_*
  (log `~/hulk-scratch/brute_v2r_r3/build_brute-r3.log`; branch at `96ccd64`, timing JSON from `5fcac67`). Content/ is gitignored.
- Reproducible from the documented shipped inputs: the 8 winning GLBs are copied into `~/hulk-scratch/brute_v2/motion/` (beside all
  16 old files, nothing removed; the `-v2r` / `Brute_v2r_` names sort first, so a v2r file wins only where one exists), and
  `assemble_motion.py` re-run into `~/hulk-scratch/brute_v5/` (pre-v2r copy of its 4 outputs in `brute_v5/pre-v2r-20261018/`).
  Its `clips_meta.json` and `clips.json` equal the r3 build's exactly; `brute.glb` is byte-identical (md5 008429d7...); `brute_anim.fbx`
  differs only in the FBX creation timestamp, the embedded texture path (out dir name) and Blender's per-export object ids: a node-tree
  compare with those ignored finds 0 differences, so Unreal was NOT rebuilt. Log `~/hulk-scratch/brute_v2r_r3/assemble-shipped.log`.
- `unreal/WebHomage/Config/BruteClipTiming.json` carries only the new clips (Slap, Clap acts; LandStart, LungeStart); the 9 old clips
  use the C++ constants. GLBs, blends and captures are local only (`Local/` and `~/hulk-scratch/` are not in git).

**Final set**

| clip | source | file (in `~/hulk-scratch/brute_v2/motion/`) | why |
| --- | --- | --- | --- |
| Idle | new (v2r) | Brute_v2r_idle.glb | in-game NEW (low-med) |
| Walk | new (v2r) | Brute_v2r_walk.glb | in-game NEW (low-med) |
| Run | new (v2r) | Brute_v2r_run.glb | in-game tie (sprint hidden by cars), tie rule ships new |
| StopLunge | new-hc | Brute_v2r_stoplunge.glb | r2 NEW (med); r3 hc vs r2 tie, hc kept (already built, 2.23 s) |
| Slap | new (v2r) | Brute_slap-v2r.glb | NEW in r2 (med) and again in r3 (med) |
| Clap | new-hc | Brute_clap-v2r.glb | r2 OLD (low-med); r3 hc beats old (med) |
| Fall | new (v2r) | Brute_fall-v2r.glb | in-game tie (med-high), tie rule ships new |
| Land | new-hc | Brute_land-v2r.glb | r2 NEW (med); r3 hc beats r2 Land (high) |
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
GATE Idle check 0.54 fit 1.81 seam 0.30 drift 1.6 toe 0.0 ab NEW
GATE Walk check 0.28 fit 2.51 seam 0.76 drift 9.5 toe 0.0 ab NEW
GATE Run check 1.02 fit 4.65 seam 0.67 drift 0.0 toe 0.0 ab tie->new
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
GATE spend fal 7.26 USD (16.69 left)
GATE build r3 96ccd64 timing 5fcac67 fbx-md5 a5408935 (r3 out) / 51c7d4dc (brute_v5, same content) glb-md5 008429d7
```

Fit over the 4 px bar on Run 4.65, StopLunge 4.60, Land 5.52 (the reading itself; a better reader or clip is the only lever).
Fall has planting off (airborne); WallClimb's toe 445 mm is the hang (feet off the floor all window).

**Which captures prove the final content** (`~/hulk-scratch/ab-ingame/`, all gate-checked ok)

- `idle_*`, `loco_*` (Idle, Walk, Run): set `new` (r2; same files as final). Fall also appears in r2 `jump_*`.
- `lunge_*`, `jump_*`, `combat_*` (StopLunge, Jump, Fall, Land, PunchR/L, Slap, Clap, Smash): set `r3` (the final build exactly).
- `uppercut_*`, `grab_*`, `wall_*` (Uppercut, Lift, Throw, WallAttach, WallClimb): set `old` (same old clips; the C++ per-clip wall
  keys added today default to the old constants).
- Blind packs: `blind/` (r2 vs old, 24 pairs), `blind-r3/` (9 pairs); keys in their `_director/KEY.json`.

**Critics' open notes (not fixed)**

- The HUD control-help box covers the feet in the front and tq angles; foot sliding is unjudgeable there. Next capture revision: hide
  help (H), add a 3 s Idle hold after landing and after each loco speed.
- Landing: both takes stand upright ~0.55 s after the crater before the crouch; the crouch should start at touchdown.
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

**Next (owner)**: feel playtest of the final set; merge decision for this branch and the fork branches; optional re-film with the HUD
hidden. Disk is at 100 % (13 GB free): scratch sets `~/hulk-scratch/ab-ingame` (~0.6 GB), `brute_v2r_candidate` can go after merge.

**Round 4 (queued behind Dragon-boss and Markhor on the GPU)** (written 2026-10-29 23:00 EDT, Opus 5.5 high)

Rule: **nothing launches (no `video2rig check`, fit, reader training, Blender batch, build or capture) until Markhor reports done**;
the GPU belongs to the Dragon-boss and Markhor sessions until then, and every launch still goes through the GPU gates above.

- Goals: fit median < 4 px and no fit warnings on Run, StopLunge, Land and Fall.
- Done already (GPU-free): two new takes, size gate + contact sheet only (LEDGER rows `run_v2`, `land_v2`; spend +0.66 USD, fal
  balance 15.73): `Local/video2rig/brute-aligned/clips/run_v2.mp4` (size PASS 1.26, sharp full-speed run in place, wide arms,
  snaps to stance only in the last 2 frames, so cut a treadmill window as for v1) and `land_v2.mp4` (size PASS 1.09, two-foot
  fist+palm contact, no hop, no raised arm, but impact at ~0.67 s and a ~1.3 s still crouch: needs `--compress-holds`).
- Done since (GPU-free): land_v2 failed `check` (1.96 %), so one more Land take, `land_v3.mp4` (LEDGER row `Land v3 (round 4)`,
  +0.30 USD, live fal balance 15.73 -> 15.43): prompt fix for panel agreement (slow legible crouch, exact same timing in both panels);
  size PASS 1.04, panels crouch and rise on the same frames, no hop/raised arm/twist, ends exactly on the stance; only the left fist
  reaches the floor, ~1.3 s still crouch (`--compress-holds`), stance ~4.3 s. **check/fit pending GPU.** Land's second regeneration
  after a failure: if v3 fails check, keep the hold-compressed v1; no fourth take.
- Steps:
  1. `check` + fit `run_v2` and `land_v2` with the lockfix fork: `run_clip.sh <P> run_v2 Run --loop --fork-dir ~/video2rig-lockfix
     --run-args "--set steps=false" --refine-args "--treadmill --window <a> <b> --loop-win 0.5 --trim 0"` (as Run v1) and
     `run_clip.sh <P> land_v2 Land --return-to-stance --fork-dir ~/video2rig-lockfix --refine-args "--max-lift 0.06
     --compress-holds"`. land_v2 failed check; same for land_v3: `run_clip.sh <P> land_v3 Land --return-to-stance --fork-dir
     ~/video2rig-lockfix --refine-args "--compress-holds --return-frames 18 --stance-snap 8 --max-seconds 3.0 --max-lift 0.06"`. A take that does not beat v1's fit (Run 4.65, Land 5.52 px) is not used.
  2. Joints tuning (`creature.json clips.<clip>.joints`, as Lift/Uppercut exp B): Fall's LeftFoot; Land/Run range warnings
     (Land v1: RightFoot, RightShoulder, Spine1, Head). StopLunge v2 stays unadopted unless a new take rises (it never does).
  3. If still > 4 px: train the dense reader warm-started from reader.pt and refit run_v2, land_v3 (after check), stoplunge_v2 and
     land_v1 with it: see the **Round 4 dense reader** block below (also in `docs/brute/video2rig/ROUND4.md`).
  4. In-game blind A/B round 4 (`ab_ingame.py run/check/pack`) for every clip that changed; a clip ships only if it wins or ties.
  5. Final build (`assemble_motion.py` -> `measure_timing.py` -> `build_brute.py`), HANDOFF + LEDGER gate lines.

**Round 4 dense reader** (plan only, nothing run; written 2026-10-29 by Opus 5.5 high; every flag dry-parsed with each module's own
argparse on the exact argv, `render_poses.py` parsed with bpy stubbed; check: `tools/brute/v2r/dryparse_dense.py`, 17/17 parse, CPU only, writes nothing)

- What it is: `python -m video2rig.reader.dense` (TUTORIAL.md "Advanced: the dense reader"). It reads a square window round the body
  (~1.8x larger in its input than a whole panel) and adds per-pixel bone labels + depth; the author measured ~1.5x more exact joints,
  "experimental, used on one creature". It is NOT `reader.prepare --init` (that retrains the standard whole-panel reader); `prepare`
  stays unused here.
- Warm start from the standard reader WORKS: `dense train --init reader/reader.pt` loads 262 of 298 tensors (backbone + keypoint heads;
  reader.pt has the same 41 keypoints; only the depth and dense heads start fresh). Checked on the CPU, nothing trained.
- Nothing overwrites `reader/reader.pt`: renders, poses and labels go to `reader/renders-dense/`, the weights to `reader/reader-dense.pt`
  (`--out`, default is that same file), readings to `work/<clip>/dense/`, fits to `work/<clip>/fit-dense.npz` + `out/<clip>-dense.npz`.
  No copy/swap of `reader/` is needed. The standard `reader/renders/` is not touched either (the dense set is its own folder).
- GPU: the Blender render, `dense train` and every `dense read` are GPU clients. Each waits for `python3 tools/gpu/gpu_gates.py check`
  (clients under the cap, util < 90 %, 20 s since the last launch, no STREAMING) and runs headless under `taskpolicy -b`. Only after the
  Dragon-boss / Markhor GPU work reports done. Disk: 14 GB free now; the dense set is ~0.5-1 GB.

Train (cwd `/Users/midir/video2rig-lockfix`, `PY=/Users/midir/video2rig/.venv/bin/python`, `P=/Users/midir/hulk/Local/video2rig/brute-aligned`,
`R=$P/reader/renders-dense`, `B=/Applications/Blender.app/Contents/MacOS/Blender`):

```
$PY -m video2rig.reader.poses $P --n 6000 --seed 1 --out $R/poses.npz                                 # CPU, ~6 min
$B $P/model.blend --background --factory-startup --python /Users/midir/video2rig-lockfix/blender/render_poses.py -- \
   --poses $R/poses.npz --cameras $P/start/cameras.json --out $R --copies 12 --samples 8 --fit 896 --height 720 --project $P
                                                                                                       # Blender (GPU), ~20-35 min
$PY -m video2rig.reader.visible $P --poses $R/poses.npz --out $R/visible.npz                          # CPU, ~5-15 min
$PY -m video2rig.reader.dense labels $P --renders reader/renders-dense                                 # CPU, ~10-30 min; check dense_labels_check.jpg
$PY -m video2rig.reader.dense train $P --renders reader/renders-dense --init $P/reader/reader.pt \
   --steps 8000 --out reader/reader-dense.pt                                                           # MPS, the long part
```

Expected: 8000 steps (author default, batch 24). The standard reader ran 0.89 s/step alone and 2.03 s/step beside two other trainers
(9000 steps = 5.1 h); the dense net is the same 448 px ViT plus two heads, so about 1.0-1.2 s/step alone = **2.2-2.7 h**, up to ~5 h
if another trainer shares the GPU. With poses, render, visible and labels: **~3-3.5 h wall alone, ~6 h contended.** RAM ~8 GB for the
12000 windows. Never judge it before the last step (the dragon read 13 px at 300 steps, 4 px at 9000).

Refit (per clip; joints and other `clips.<clip>` settings in creature.json still apply through `clip_cfg`):

```
$PY -m video2rig.reader.dense read $P <clip> --reader $P/reader/reader-dense.pt --locator masks        # GPU, ~1-3 min -> work/<clip>/dense/reading.npz
$PY -m video2rig.reader.fit $P <clip> --reading $P/work/<clip>/dense/reading.npz --tag=-dense [--set steps=false]
                                                                                                       # CPU ~2-3 min -> out/<clip>-dense.npz, work/<clip>/fit-dense.npz,
                                                                                                       #   fit-dense-report.json; "median keypoint miss" in its output
$PY -m video2rig review $P <clip> --tag=-dense                                                        # work/<clip>/review-dense.mp4
```

| clip | fit extras | install + refine (after the dense fit beats the standard one) |
| --- | --- | --- |
| run_v2 | `--set steps=false` | `run_clip.sh $P run_v2 Run --loop --refine-args "--treadmill --window 33 124 --loop-win 0.7 --trim 0"` (bar: 4.35 px) |
| land_v3 | none; only once `check` has passed (else skip it) | `run_clip.sh $P land_v3 Land --return-to-stance --refine-args "--compress-holds --return-frames 18 --stance-snap 8 --max-seconds 3.0 --max-lift 0.06"` |
| stoplunge_v2 | none | `run_clip.sh $P stoplunge_v2 StopLunge --return-to-stance --refine-args "--compress-holds --return-frames 18 --stance-snap 8 --max-seconds 3.0 --max-lift 0.07"` (bar 4.58 px; still not adoptable unless the take rises, which the fit cannot add) |
| land_v1 | none | `run_clip.sh $P land_v1 Land --return-to-stance --refine-args "--compress-holds --return-frames 18 --stance-snap 8 --max-seconds 3.0 --max-lift 0.06"` (bar 5.52 px; the shipped hold-compressed Land) |

Every `run_clip.sh` line also takes `--fork-dir /Users/midir/video2rig-lockfix --motion-dir /Users/midir/hulk/Local/video2rig/motion-v2r-dense
--from import` (a separate GLB folder: motion-v2r and motion-v2r-r4 stay untouched). Install step before it, as for Lift's `-jt` fit:
`mkdir -p $P/work/<clip>/attempt-pre-dense && cp $P/out/<clip>.npz $P/work/<clip>/{fit.npz,report.json} $P/work/<clip>/attempt-pre-dense/ (the files that exist)
&& cp $P/out/<clip>-dense.npz $P/out/<clip>.npz` (restore = copy back). run_clip's CLIP line then still prints the standard fit px from
pipeline.state: record the dense px from the `reader.fit` output instead. The dense miss is measured against the dense reading itself,
so judge by the review film and the in-game A/B, not by px alone.


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

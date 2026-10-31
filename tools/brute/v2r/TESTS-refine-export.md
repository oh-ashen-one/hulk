# refine_brute.py + export_clip.py: offline tests (2026-10-29)

Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

No video, no spend, no reader, no engine. There is no real video2rig fit yet, so the tests use synthetic fits built
from the shipped clips. Machine: Mac Studio M3 Ultra, Blender 5.2.0 LTS, every run `-b --factory-startup`, one Blender
at a time (other sessions had 0-2 Blender processes running; no UnrealEditor). The aligned project
`~/hulk/Local/video2rig/brute-aligned/` was only read: `model.blend` was copied (its mtime stayed 01:09) and nothing
was written to `reader/`.

Reproduce everything with `tools/brute/v2r/test_refine_export.sh` (work dir `~/hulk/Local/video2rig/work-tools/`,
gitignored; logs in `work-tools/logs/`, full transcript `work-tools/test_run.txt`). The numbers below come from the
final run.

## Files

| File | Role |
| --- | --- |
| `v2r_rig.py` | shared transform, both directions: `P_dst = P_src @ R_src^-1 @ R_dst` (armature space), then a parent-aware pose basis; rig check (names, parents, heads within 1e-4); bulk key writer |
| `export_clip.py` | aligned-rig Action -> `<motion_dir>/<name>.glb` on the shipped rig, resampled to 30 fps, `EXPORT_GATE` |
| `refine_brute.py` | trim, spikes, loop close or return to stance, foot plant, toe clamp, JSON report, `REFINE_GATE` |
| `make_test_fit.py` | test helper: shipped clip -> aligned rig, keyed the way `import_motion.py` keys a fit; can inject spikes and a still tail |
| `roundtrip_check.py` | test helper: two motion files on the shipped rig, the way assemble_motion sees them |
| `test_refine_export.sh` | runs the whole chain below |

## 0. File names vs assemble_motion's CLIPS

```
Blender -b --factory-startup -P tools/brute/v2r/export_clip.py -- --self-test
```
`EXPORT_SELFTEST PASS (17 clips from assemble_motion CLIPS)`. CLIPS is read from `assemble_motion.py` with `ast`
(nothing imported). Each name is checked with assemble's own lookup: first the pattern's first alternative, then the
whole pattern, first match in sorted order. Each name is tested alone and with all 17 v2r names in one directory.
Names: `Brute_v2r_{idle,walk,run,stoplunge,jump,wallattach,wallclimb}.glb` and
`Brute_{punchl,punchr,slap,clap,smash,liftthrow,throw,uppercut,fall,land}-v2r.glb`. The optional `--tag v1`
appends `_v1`; that variant also passes.

Precedence: if a v2r file and the old file for the same clip are both in one motion dir, the v2r file wins for
**all 17** clips (checked against the file names in `~/hulk-scratch/brute_v2/motion`). The combat names use `-`
because it sorts before `.`. Without it, `Brute_punchl.glb` would beat `Brute_punchl_v2r.glb`, while the locomotion
v2r names already beat the `Emerald_Behemoth_*` names. That would be inconsistent. So a v2r file goes into a motion
dir only once it has won its A/B.

## 1. Synthetic Idle fit

```
Blender -b --factory-startup -P tools/brute/v2r/make_test_fit.py -- work-tools/model_aligned_copy.blend ~/hulk-scratch/brute_v5/brute.glb Idle work-tools/fake_fit/Idle_fit.blend
```
`TESTFIT rig check True ['bones 52, max head delta 0']`. The test fit has 156 frames of the shipped Idle (5.167 s
at 30 fps), retargeted shipped -> aligned. Its keys are at 1.00..125.00 in the 24 fps fit scene. The 30 fps sample
times land on fractional frames `1 + k*0.8`, as `import_motion.py` would place a 30 fps video fit. All 52 bones are
keyed; a real fit keys only the fitted bones, and export_clip samples the full evaluated pose either way. Location
keys: Hips.

## 2. Exact round trip (unrefined fit)

```
Blender -b --factory-startup -P tools/brute/v2r/export_clip.py -- work-tools/fake_fit/Idle_fit.blend Idle work-tools/motion_raw
Blender -b --factory-startup -P tools/brute/v2r/roundtrip_check.py -- ~/hulk-scratch/brute_v5/brute.glb Idle work-tools/motion_raw/Brute_v2r_idle.glb
```
- `EXPORT Idle output: 156 frames (0..155) at 30 fps = 5.167 s; resampled 24 -> 30 fps: output frame k samples the source Action at frame 1.000 + k*0.8000 (same time, linear)`
- rig check: `bones 52, max head delta 7.26e-07`
- retarget only (in memory): 0.0011 mm; max |pose scale - 1| 8.2e-06
- **`EXPORT_GATE Idle max_vertex_delta_mm 0.0026 frames 5 PASS`**. This compares the glb re-imported the way
  assemble does against the aligned rig, on the aligned mesh (83129 verts). Re-imported frames 0..155; assemble
  location scale 1.0000.
- **Round trip vs the original shipped Idle: `ROUNDTRIP_GATE max_vertex_delta_mm 0.0021 frames 12 lengths 156/156 PASS`.**
  Bone heads max 0.0020 mm over every frame; shipped mesh, 83085 verts.

## 3. Refine (--loop), export, compare

```
Blender -b --factory-startup -P tools/brute/v2r/refine_brute.py -- work-tools/fake_fit/Idle_fit.blend --loop --clip Idle
Blender -b --factory-startup -P tools/brute/v2r/export_clip.py -- work-tools/fake_fit/Idle_fit_refined.blend Idle work-tools/motion_refined
```
- **`REFINE_GATE Idle seam 1.18 foot_drift_mm 3.6 toe_min_mm 0.0 peakhand_L 21 peakhand_R 153`**
- Frame 0 vs the start-picture stance (`brute-aligned/rig/rig.json` start_pose): 0.001 mm before. After refinement:
  mean 0.36, p95 3.2, max 6.4 mm, caused by the toe clamp's smoothing.
- Trim: nothing trimmed (still tail start 155 = the last sample). Spikes: none found.
- Loop: best end = the last sample (the shipped Idle is already closed); cost 0; xfade 12; seam before 0.00 (last
  frame -> frame 0). After, seam 1.18 = step from the last distinct frame to frame 0 / median step. The end frame
  equals frame 0, the convention assemble_motion uses. Leg end residual 0.0 deg.
- Feet (both feet planted for the whole clip): drift before L ankle 36.0 / toe 46.8 mm, R 29.5 / 27.6 mm. The
  shipped Idle's feet slide. After: L 3.6 / 0.007 mm, R 0.5 / 0.006 mm. IK reach: no pin missed.
- Toe clamp: lowest toe -10.1 mm before (the left toe sinks into the floor mid-clip), 0.002 mm after. Left foot
  lifted by at most 5.5 mm over 121 samples.
- Arms: rotation change from the plant 0.000 deg; change outside spike frames and the blend window 0.000 deg. Peak
  hand speed is at the same sample before and after (L 21 = 0.70 s, R 153 = 5.10 s). Neck/Head range vs frame 0:
  3.0 / 6.4 deg.
- `EXPORT_GATE Idle max_vertex_delta_mm 0.0029 frames 5 PASS`
- Refined vs the original Idle (for information, not a gate: the plant moves the feet on purpose): max 70.4 mm
  mid-clip, 5.8 mm at frames 0/155. That is the original foot slide being removed.

## 4. assemble_motion ingests the export

```
work-tools/assemble_motion_dir = symlinks to every ~/hulk-scratch/brute_v2/motion/*.glb (read-only) + motion_refined/Brute_v2r_idle.glb
Blender -b --factory-startup -P tools/brute/assemble_motion.py -- ~/hulk-scratch/brute_corr/brute_rigged_corr.glb work-tools/assemble_motion_dir work-tools/assemble_out
Blender -b --factory-startup -P tools/brute/v2r/roundtrip_check.py -- work-tools/assemble_out/brute.glb Idle work-tools/motion_refined/Brute_v2r_idle.glb
```
- `CLIP Idle 5.17 s speed 0.00 m/s in-place False loop True from Brute_v2r_idle.glb`. The v2r file won over
  `Emerald_Behemoth_idle_30fps.glb`, which was in the same dir. `LOOP Idle end frame 155 of 155 mismatch 0.0001`:
  assemble kept our loop end. All 17 clips were written: brute.glb, brute_anim.fbx, clips.json, clips_meta.json.
- The assembled Idle vs our export: `ROUNDTRIP_GATE max_vertex_delta_mm 0.0012 frames 12 lengths 156/156 PASS`.

## 5. One-shot path (PunchL, --return-to-stance), extra

```
Blender ... make_test_fit.py -- ... PunchL work-tools/fake_fit/PunchL_fit.blend --spike LeftForeArm:20:25 --spike Spine1:30:-15 --hold 1.0
Blender ... refine_brute.py -- work-tools/fake_fit/PunchL_fit.blend --return-to-stance --clip PunchL --floor=-0.435
Blender ... export_clip.py -- work-tools/fake_fit/PunchL_fit_refined.blend PunchL work-tools/motion_punchl
```
- **`REFINE_GATE PunchL seam 0.16 foot_drift_mm 2.2 toe_min_mm -5.5 peakhand_L 31 peakhand_R 29`**
- **`EXPORT_GATE PunchL max_vertex_delta_mm 0.0063 frames 5 PASS`**. 49 frames at 30 fps = 1.6 s; file
  `Brute_punchl-v2r.glb`.
- Trim: the 1 s still tail was found (still tail start 48) and 28 samples were cut.
- Spikes: the injected LeftForeArm spike was removed (samples 19-21). The injected 15 deg Spine1 spike at sample 30
  was **not** removed: the spine turns fast there, so the default isolation test (`--spike-iso 3`) does not see it
  as isolated. `--spike-iso 2` catches it. An earlier version without the isolation test also smoothed the punch's
  own elbow snap and moved the left hand's peak from sample 31 to 29; the isolation test exists to prevent that.
- Return to stance: limited to 12 samples so the blend starts 0.2 s after the later hand peak (sample 31). End vs
  start: 13.4 rad summed before, 0.0 after.
- Feet: toe drift 173 / 116 mm before, under 0.01 mm after. Ankle drift (heel down) 12.2 / 20.3 mm before,
  2.2 / 1.3 mm after.
- Peak hand speed is unchanged: L sample 31 (1.033 s), R 29 (0.967 s). The HIT table has PunchL at 1.0 s.
- `--floor=-0.435` is needed because the old Meshy PunchL stands about 0.43 m lower in armature space than the Idle
  stance, and its frame 0 is not the stance: mesh delta mean 795 mm, Hips 644 mm. That is a property of the old
  clip, not of the tool. Real fits start at the stance on z = 0. With the default floor, the toe clamp hit its
  `--max-lift` cap (50 mm) and reported `floor_mismatch` instead of folding the legs. Even with the floor set, one
  sample stays 55 mm deep (`toe_min -5.5` after the cap).
- Visual check (Workbench renders, raw over refined, scratch): `work-tools/sheet/punch_side_cmp.jpg` and
  `work-tools/sheet/idle_front_cmp.jpg`. No knee flips or broken legs.

## 6. Open loop (--loop with a real seam), extra

```
Blender ... make_test_fit.py -- ... Idle work-tools/fake_fit/IdleOpen_fit.blend --cut 40     (the shipped Idle minus its last 40 samples)
Blender ... refine_brute.py -- work-tools/fake_fit/IdleOpen_fit.blend --loop --clip IdleOpen
Blender ... export_clip.py -- work-tools/fake_fit/IdleOpen_fit_refined.blend Idle work-tools/motion_idleopen
```
- Seam before: 11.24 x the median step (last frame -> frame 0). The best end in the last 2 s was the last sample
  (cost 0.073). Offset 1.13 rad summed; xfade 24 (auto rule capped at 24: keeping the added step under half a
  median step would need about 36).
- **`REFINE_GATE IdleOpen seam 1.34 foot_drift_mm 3.2 toe_min_mm 0.0 peakhand_L 21 peakhand_R 9`**. Frame 0 vs
  the stance: max 0.8 mm.
- **`EXPORT_GATE Idle max_vertex_delta_mm 0.0028 frames 5 PASS`** (116 frames, 3.833 s at 30 fps).

## Not verified

- No real video2rig fit exists. Real-fit specifics are untested: keys only on the fitted bones, 24 or 25 fps video
  times, props, actual foot jitter. The code handles fractional key grids and unkeyed bones by construction, and the
  test fit exercises the fractional grid.
- Not imported into Unreal (`build_brute.py`); no engine was run.
- Observation: in the start-picture stance the right foot hovers 33.5 mm above the floor (the lowest right-foot
  vertex at frame 0). Plants work relative to each foot's own lowest point, so this is not a problem for the tool.

## 7. Burst pass (2026-10-29, after the Throw fit)

The Throw refit's LeftArm turned 67 / 100 / 68 deg over frames 26-28 between 3 deg steps; RightArm did the same (71 / 106 / 71).
Swing/twist decomposition: the upper arm's direction moved ~20 deg while its twist changed ~125 deg (path 235 deg, net 126 deg),
at a frame where the fitter re-initialised (`fit-report` frame 27 `start: reset`). The single-frame spike test cannot catch it
(the bone never comes back). `refine_brute.py` now finds runs of 1-4 big steps (> 8 x median and > 30 deg, smallest > 3 x the
2 steps either side) whose bone direction moves <= 45 deg, removes the jump and re-adds its net change as a smoothstep offset
over a window (peak <= 12 deg/step, at most 0.5 s). Throw's hurl (frames 98-101: arms overhead -> forward, 72 / 85 deg swing)
passes the step tests but is real motion; the swing limit leaves it alone (`bursts.skipped_as_swing`). Without the swing
limit the hurl was flattened and the right-hand peak moved from sample 98 to 56, which is why the limit exists.

```
Blender ... make_test_fit.py -- ... PunchL work-tools/fake_fit/PunchLBurst_fit.blend --twist LeftArm:8:120:2
Blender ... refine_brute.py -- work-tools/fake_fit/PunchLBurst_fit.blend --return-to-stance --clip PunchLBurst --floor=-0.435
Blender ... refine_brute.py -- (same) --no-burst --out work-tools/fake_fit/PunchLBurst_fit_noburst.blend
```
- `BURST_TEST bones ['LeftArm'] ... swing 5.2, steps 58.5/57.5, net 116.0, window [0, 15], peak_step_after 13.7 ... peakhand_L 30 (same fit, --no-burst: 30) PASS`
- Only LeftArm is touched; the punch's own elbow snap and the injected LeftForeArm/Spine1 spikes of step 5 are unaffected
  (step 5 still `REFINE spikes {"LeftForeArm": 3}`, `bursts {}`). Steps 0-6 reproduce the numbers above exactly.
- The injection is 60 deg/step because this synthetic PunchL's LeftArm median step is 6.9 deg (8 x = 55); a 40 deg/step
  injection is (correctly) below threshold there. Real fits are calmer (Throw LeftArm median 1.45 deg).
- Tried and reverted: dropping plant edge samples the IK cannot reach (Throw left foot 52-56). The raw foot is still 0.9 m
  back at sample 53, so the trimmed foot skated 0.9 m along the floor in 4 samples; the pinned version (36 mm toe settle
  while the heel lands, leg at full reach) is better and stays.

## 8. Hold compression + stance snap (2026-10-29)

```
Blender ... make_test_fit.py -- ... PunchL work-tools/fake_fit/PunchLHold_fit.blend --hold 1.0
Blender ... refine_brute.py -- work-tools/fake_fit/PunchLHold_fit.blend --return-to-stance --clip PunchLHold --floor=-0.435 --trim 0 --compress-holds --stance-snap 6
Blender ... refine_brute.py -- (same, without the two flags) --out work-tools/fake_fit/PunchLHold_fit_off.blend
```
- `REFINE_HOLDS PunchLHold spans 1 compressed 1 speedup 1.00 seconds 2.533 -> 1.800 hitL 0.967 -> 0.967 s hitR 1.000 -> 1.000 s`
- `HOLD_TEST spans [[48, 76]] compressed [[48, 76]] samples 77 -> 55 hit L/R 29/30 (no flag: 29/30) end_vs_frame0_mm 35.000 (no flag: 37.843) toe 0.0 drift 2.2 (no flag: toe -0.0 drift 4.4) PASS`
- The kept 1 s still tail is found as one hold and re-timed to 6 samples. The hit samples are unchanged, and the toes and drift are no worse.
- The 35 mm end gap is a property of this synthetic fit. Its left foot is inside a plant blend at frame 0 (the plant starts at sample 2) but swings at the end. The lift match cannot change that, and the run without the flags is 37.8 mm.
- On the real fits, the last frame equals frame 0 to 0.0 mm; see `docs/brute/video2rig/HOLD-COMPRESSION.md`.
- Step 5 was re-run after the change. Its numbers are identical.

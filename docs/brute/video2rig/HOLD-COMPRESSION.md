# refine_brute.py: hold compression + stance return (2026-10-29)

Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

Variants only. They are in `Local/video2rig/motion-v2r-hc/` (same file names as `motion-v2r/`). Nothing is shipped, and `motion-v2r/` and the candidate `*_refined.blend` files were not touched. The variant blends are `Local/video2rig/hc-refined/<fit>_hc.blend`, with `.json` reports and refine/export logs.

## Why

The blind Blender critique (`~/hulk-scratch/ab-blender/CRITIQUE-blender.md`) flagged the v2r one-shots for 0.7-2 s frozen holds, because the prompts asked for "held ~2 s".

Three complaints quoted in the brief belong to the OLD takes according to the keys: the Slap 3.4x end gap (Slap B), the Land arm-up flex (Land B) and the Throw 3-frame release (Throw B). The NEW one-shots already ended at frame 0, with ab_measure end gaps of 0.002-0.48.

## Flags (all off by default)

Existing runs, and the numbers in TESTS-refine-export.md steps 0-7, are unchanged. Step 5 was re-run and gave seam 0.16, drift 2.2, toe -5.5, peaks 31/29, identical to before.

- `--compress-holds` (needs `--return-to-stance`). It runs after spikes/bursts and before the return blend.
  - **Hold detection.** A hold is a span where the 5-sample mean bone angular speed stays under clamp(`--hold-frac` 0.3 x the clip's p95, `--hold-min-dps` 4, `--hold-max-dps` 8) deg/s for at least `--hold-min-s` 0.25 s.
  - **Contact windows.** Each hand's raw speed peak +- `--contact-s` 0.1 s is never part of a hold. These windows play at real speed, eased in over 3 samples, so a strike keeps its own weight.
  - **Re-timing.** Each hold is re-timed to `--hold-keep` 6 samples with a cosine-eased rate: the rate is unchanged at the hold's edges and fastest mid-hold. A hold with both hands above the Head keeps `--hold-keep-up` samples instead.
  - **Length cap.** If the clip is still longer than `--max-seconds`, the remaining time is sped up uniformly by the smallest factor that meets the cap, up to `--max-speedup` 1.6.
  - **Hit times.** These move. They are re-measured after the run and also mapped from the raw peak (`retime.hit_mapped`).
- `--stance-snap N`: the toe clamp's smoothed lift could differ between the first and last frames (the Land candidate had a 4.5 mm gap). This flag blends the last N samples' lift onto frame 0's lift, never below what the toes need. Result: last frame = frame 0, 0.0 mm on every variant.
  - Tried first and dropped: blending the leg rotations after the clamp (PunchL: drift 1 -> 8 mm, toe -1.3 mm).
- New report fields: `retime`, `last_frame_vs_frame0`, `last_frame_vs_start_stance`, `feet.stance_snap`, and a `REFINE_HOLDS` line.

Variant runs used `--return-to-stance --compress-holds --return-frames 18 --stance-snap 8` plus these per-clip options:

| Clips | Options |
| --- | --- |
| PunchL, PunchR, Slap, Clap | `--max-seconds 2.5` |
| Uppercut, Throw, Land | `--max-seconds 3.0` |
| Lift | `--max-seconds 3.5 --hold-keep-up 12` |
| Land | also `--max-lift 0.06`, as in its candidate |
| StopLunge | `--max-seconds 3.0 --max-lift 0.07` (with 0.05 its left foot capped at 60 mm deep, toe -12.2 mm) |

Sources were the candidate fits (`brute-aligned/<Clip>_v2r_vN.blend`, the same N as in `motion-v2r/*.export.json`). Every `EXPORT_GATE` passed (0.0027-0.0045 mm).

## Per clip (candidate -> variant)

- **Holds** are listed as fit samples at 24 fps.
- **End gap** is ab_measure `seam.mesh_ratio` (last->first mesh step / median step), with the gap in mm in brackets. It is measured in game root mode on the 30 fps export.
- **Drift / toe** are refine's planted-foot drift and lowest toe vertex.
- **ab drift** is ab_measure `drift_cm` with the Hips XY pinned, as the game does.

| Clip | holds found (s) | compressed (samples -> kept) | speed-up | length s | hit L s | hit R s | end gap | still tail (frames) | drift mm / toe mm | ab drift cm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PunchL | 0-0.25, 1.79-3.38, 3.54-5.08 | 43-81->6, 85-122->6 | 1.00 | 5.08 -> 2.46 | 1.375 -> 1.375 | 1.375 -> 1.375 | 0.090 (0.6) -> 0.075 (1.4) | 2 -> 2 | 3.3 / 0.0 -> 5.0 / 0.0 | 19.9 -> 20.0 |
| PunchR | 0-0.38, 2.00-3.08, 4.33-5.08 | 48-74->6, 104-122->6 | 1.60 | 5.08 -> 2.62 | 1.542 -> 1.042 | 1.542 -> 1.042 | 0.022 (0.2) -> 0.005 (0.1) | 12 -> 6 | 2.8 / 0.0 -> 2.2 / 0.0 | 14.4 -> 12.8 |
| Slap | 0.04-0.25 | none | 1.60 | 5.12 -> 3.33 | 2.167 -> 1.667 | 2.250 -> 2.750 | 0.002 (0.0) -> 0.011 (0.2) | 9 -> 4 | 3.9 / 0.6 -> 1.9 / 0.8 | 14.3 -> 14.3 |
| Clap | 1.25-2.33, 3.54-4.67 | 30-56->6, 85-112->6 | 1.25 | 4.67 -> 2.50 | 0.875 -> 0.708 | 0.875 -> 0.708 | 0.015 (0.2) -> 0.000 (0.0) | 13 -> 5 | 1.9 / 0.0 -> 2.7 / 0.0 | 7.5 -> 7.5 |
| Uppercut | 0-0.42, 2.04-3.92 | 0-10->6, 49-94->6 | 1.13 | 5.08 -> 3.00 | 1.708 -> 1.417 | 1.542 -> 1.250 | 0.014 (0.2) -> 0.000 (0.0) | 4 -> 4 | 10.6 / 0.0 -> 3.4 / 0.0 | 17.5 -> 17.3 |
| Lift | 0-0.25, 1.08-1.46, 2.17-2.67, 3.54-4.63 (hands up) | 52-64->6, 85-111->12 | 1.60 | 6.42 -> 4.00 | 3.042 -> 1.750 | 5.208 -> 3.042 | 0.003 (0.0) -> 0.000 (0.0) | 8 -> 5 | 3.5 / 0.0 -> 3.2 / 0.0 | 15.8 -> 15.7 |
| Throw | 2.71-3.25, 4.63-5.08 | 65-78->6, 111-122->6 | 1.60 | 5.08 -> 3.25 | 2.208 -> 2.667 | 4.083 -> 2.667 | 0.010 (0.2) -> 0.005 (0.2) | 10 -> 6 | 36.2 / 0.0 -> 33.1 / 0.0 | 57.2 -> 57.3 |
| Land | 1.46-3.08 | 35-74->6 | 1.29 | 5.12 -> 3.00 | 1.083 -> 0.833 | 1.083 -> 0.833 | 0.208 (4.5) -> 0.000 (0.0) | 6 -> 6 | 3.7 / 0.0 -> 5.5 / 0.0 | 38.2 -> 15.8 |
| StopLunge | 2.13-3.58, 4.08-5.13 | 51-86->6, 98-123->6 | 1.05 | 5.12 -> 3.00 | 0.375 -> 0.333 | 0.875 -> 0.875 | 0.479 (9.8) -> 0.000 (0.0) | 4 -> 8 | 2.4 / -5.0 -> 4.0 / 0.0 | 67.5 -> 52.7 |

### Hit times

The hit columns give the re-measured peak hand speed. These cases need a note:

- **Slap R** moved to a later swing at 2.75 s. The raw contact peak maps to 1.49 s and plays at real speed, so the 1.6x faster follow-through now out-speeds it.
- **Throw.** Both hands peak at the hurl (2.667 s), at 14.0 m/s, compared with 13.8 m/s raw. The left raw peak was the lift, mapped to 1.43 s.
- **Lift.** Its "hits" are the heave (1.75 s) and the return motion (3.04 s).
- **PunchL** kept 1.375 s, because it was under the cap without any speed-up. The critic's 0.30-0.50 s contact target is not met by re-timing.

### Not met or not addressed

- **Length caps.**
  - Slap is 3.33 s against 2.5. It has almost no holds; it is uniformly slow.
  - Lift is 4.00 s against 3.5, and Throw is 3.25 s against 3.0. Both hit the 1.6x speed-up limit.
- **Foot drift.** Throw's 33 mm drift is inherited: three left-foot samples miss the IK reach, as in the candidate. ab drift with the Hips pinned (Throw 57 cm, StopLunge 53 cm) comes from hip travel and is not changed by this pass.
- **Problems re-timing cannot fix:**
  - PunchR's open claw hand.
  - PunchL's open-hand reach.
  - Lift's squat / stand / raise structure. The stand pause is now 6 samples, but the beats remain.
  - The Lift -> Throw hand-off: the new Lift returns to idle and the new Throw starts from idle.
- **Stance rig.** The last frame equals frame 0 (0.0 mm). Frame 0 sits 8-13 mm (mean mesh) from the rig.json start pose, as before.

## Blind pairs

The pairs are OLD = `~/hulk-scratch/brute_v5/brute.glb:<Clip>` against the variant. They were made with `ab_pair.py` at `--root game`, with 3 cameras and labels from a fresh random seed per clip.

- Pairs: `~/hulk-scratch/ab-blender-hc/<Clip>/`
- Keys and `_director/` logs: `~/hulk-scratch/ab-blender-hc-keys/<Clip>/`
- Clips: PunchL, PunchR, Slap, Clap, Uppercut, Lift, Throw, Land, StopLunge

Each Blender run (refine, export, render, measure) was started only when `tools/gpu/gpu_gates.py` listed no UnrealEditor client, util was under 40 % and no other Blender was running. All runs were headless, one at a time.

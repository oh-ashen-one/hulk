# Blender blind A/B: OLD (shipped brute_v5) vs NEW (v2r) for 14 clips

Director's file. It names the true source per row; the critic never sees it. The critic's material is the pair folders only (A_/B_ mp4s, `measure.json` keyed by label, `critic_brief.md`), where nothing names the source.

- Date: 2026-10-29. Tools: `tools/brute/v2r/ab_pair.py` (renders + `ab_measure.py`, `--root game`, 854x480 Eevee, 10 samples, 3 fixed cameras, clay), driven one Blender at a time, each render started only when `tools/gpu/gpu_gates.py` listed no UnrealEditor client and util < 40 % (ab_ingame captures kept running in the gaps).
- OLD = Action `<Clip>` in `~/hulk-scratch/brute_v5/brute.glb`. NEW = `Local/video2rig/motion-v2r/Brute_*v2r*.glb` (Lift = `Brute_liftthrow-v2r.glb`). Both on the brute_v5 mesh.
- Label mapping is random per clip (seed = crc32 of the clip name); the last column gives it.
- Locations (outside the repo): pairs `~/hulk-scratch/ab-blender/<Clip>/`; keys `~/hulk-scratch/ab-blender-keys/<Clip>/KEY.json` (+ `_director/` render/measure logs and timings).

## ab_measure, OLD / NEW (game root mode)

| Clip | Kind | seam ratio | foot_drift_px | secondary | frames | label map |
| --- | --- | --- | --- | --- | --- | --- |
| Idle | loop | 0.00 / 0.20 | 11.2 / 12.5 | 0.45 / 0.31 | 125 / 149 | A=old B=new |
| Walk | loop | 0.00 / 0.75 | 48.3 / 102.4 | 0.28 / 0.14 | 145 / 75 | A=old B=new |
| Run | loop | 0.00 / 0.85 | 21.0 / 0.0 | 0.23 / 0.14 | 145 / 89 | A=old B=new |
| StopLunge | one-shot | n/a / n/a | 0.0 / 70.5 | 0.85 / 0.33 | 69 / 124 | A=new B=old |
| PunchL | one-shot | n/a / n/a | 24.4 / 22.3 | 0.28 / 0.16 | 38 / 123 | A=new B=old |
| PunchR | one-shot | n/a / n/a | 19.4 / 14.3 | 0.28 / 0.46 | 38 / 123 | A=old B=new |
| Slap | one-shot | n/a / n/a | 37.0 / 14.9 | 0.44 / 0.32 | 60 / 124 | A=new B=old |
| Clap | one-shot | n/a / n/a | 0.0 / 7.5 | 0.75 / 0.45 | 39 / 113 | A=old B=new |
| Uppercut | one-shot | n/a / n/a | 40.2 / 19.6 | 0.17 / 0.18 | 60 / 123 | A=old B=new |
| Lift | one-shot | n/a / n/a | 12.0 / 17.7 | 0.28 / 0.23 | 73 / 155 | A=new B=old |
| Throw | one-shot | n/a / n/a | 13.4 / 63.9 | 0.82 / 0.23 | 36 / 123 | A=new B=old |
| Land | one-shot | n/a / n/a | 18.7 / 38.4 | 0.17 / 0.22 | 72 / 124 | A=new B=old |
| WallClimb | loop | 14.16 / 1.79 | 12.4 / 1.8 | 0.10 / 0.10 | 121 / 30 | A=new B=old |
| Fall | loop | 0.24 / 0.00 | 7.6 / 32.6 | 1.14 / 0.28 | 48 / 113 | A=new B=old |

Columns are OLD / NEW. seam = last->first mesh jump over median step (~1 clean, 0 = last frame equals first i.e. a one-frame hold, >2 pop); foot_drift_px = worst planted-foot contact patch movement in film pixels; secondary = head+finger articulation relative to pelvis; frames at 24 fps.

Reading notes (numbers only, no verdicts):
- Seam 0.00 means the last frame duplicates the first (a one-frame hold at the wrap): OLD Idle, Walk, Run and NEW Fall. OLD Fall is 0.24; NEW loops are 0.20 (Idle), 0.75 (Walk), 0.85 (Run). The only seam above 2 is OLD WallClimb at 14.16 against NEW 1.79.
- Walk / Run / StopLunge foot drift is the gait sliding backwards under a pinned root (by design); compare `planted_speed_m_s` in measure.json (Walk: OLD 1.357, NEW 1.280 m/s against clips_meta speed 0.609; Run and StopLunge report none). NEW Run and OLD StopLunge read 0.0 px because ab_measure found no grounded run of >= 3 samples (feet grounded only 7-9 % of frames), not because the feet are clean. Fall NEW is measured with first-frame grounding only (air clip), as designed.
- Clip lengths differ a lot (NEW Walk 75 vs OLD 145 frames; NEW WallClimb 30 vs 121; NEW Fall 113 vs 48; NEW one-shots ~113-155 frames vs OLD 36-73), so the film durations differ between A and B in most pairs.
- Largest foot drift: Walk NEW 102.4, StopLunge NEW 70.5, Throw OLD 63.9, Walk OLD 48.3.
- ab_measure also writes a seam value for one-shots in measure.json (e.g. OLD StopLunge 10.2, OLD Clap 6.5); the table shows n/a because it is only meaningful for loops.

## Pair folders (`~/hulk-scratch/ab-blender/`)

- `Idle/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `Walk/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `Run/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `StopLunge/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `PunchL/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `PunchR/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `Slap/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `Clap/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `Uppercut/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `Lift/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `Throw/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `Land/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `WallClimb/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)
- `Fall/` (A_/B_ front, left, threequarter mp4, measure.json, critic_brief.md)

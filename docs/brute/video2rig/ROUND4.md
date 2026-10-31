# Brute video2rig round 4

Hulk-in-Manhattan fan homage; not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
Companion to [PLAN.md](PLAN.md), [LEDGER.md](LEDGER.md) and the "Round 4" section of `HANDOFF.md`. Branch `chinese-animation-upgrades`.
Goal: fit median < 4 px and no fit warnings on Run, StopLunge, Land and Fall. Every GPU step goes through the machine-wide gates and
waits until the Dragon-boss and Markhor sessions report done.

## Takes (GPU-free part: generation, size gate, contact sheet)

| take | size gate | visual | check / fit |
| --- | --- | --- | --- |
| run_v2 | PASS 1.26 | PASS (sharp run in place, wide arms) | check 1.08 PASS, fit 4.65 -> 4.35 px (candidate, motion-v2r-r4) |
| land_v2 | PASS 1.09 | PARTIAL (1.3 s still crouch) | **check FAIL 1.96 %**, never fitted |
| land_v3 | PASS 1.04 | PARTIAL: panels crouch and rise on the same frames, no hop, no raised arm, no twist, ends exactly on the stance; only the left fist touches the floor, contact ~1.0-1.2 s, ~1.3 s still crouch (needs `--compress-holds`), stance ~4.3 s | **pending GPU** |

Land v3 is Land's second regeneration after a failure: if it fails `check` too, keep the hold-compressed v1 (the A/B winner) and stop
(no fourth take). Spend: fal +0.30 USD for land_v3, live balance 15.73 -> 15.43 USD (fal total 8.22 USD).

Next GPU steps for land_v3, once the gates allow: `run_clip.sh $P land_v3 Land --return-to-stance --fork-dir ~/video2rig-lockfix
--refine-args "--compress-holds --return-frames 18 --stance-snap 8 --max-seconds 3.0 --max-lift 0.06"` (size gate, check, fit, refine);
it is used only if check passes and the fit beats Land v1 (5.52 px) and then wins the in-game A/B.

## Dense reader

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

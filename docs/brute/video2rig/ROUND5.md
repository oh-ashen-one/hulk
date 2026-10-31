# Brute video2rig round 5: why Run, StopLunge and Land miss 4 px, and the routes under it

Hulk-in-Manhattan fan homage; not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
Analysis only (Opus 5.5 high, 2026-10-30). CPU only: no spend, no GPU process, no Blender, nothing in the project or the fork was
written (checked with `find -newer`). Companion to [ROUND4.md](ROUND4.md) and [LEDGER.md](LEDGER.md). Branch `chinese-animation-upgrades`.

## Method

- **What the px number is.** `fit.py` computes the "median keypoint miss" in the frame-by-frame solve, before `clean_motion`. Per frame,
  it takes the median pixel distance between each reprojected keypoint and its reading, over points with conf > 0.3, both panels
  pooled. The clip number is the median of those per-frame values.
  - So `lock_feet`, `steps`, despike, low-pass, springs and `keep_out` cannot move it. That is why the ROUND4 fit-pass and twin_link
    rows did not change.
  - What does move it: anything in the per-frame solve (`w_smooth`, `w_prior`, `cauchy_px`, joint `range`/`prior` in creature.json),
    and anything that changes the readings or their weights before the solve (`panel_drift`, `panel_pick`, `hidden_refit`, twins).
- **The probe.** I re-ran `road.fit_reading` in memory with a wrapper that captures the raw per-frame params (`/private/tmp/claude-501/-Users-midir/dc49ac78-9559-4631-aa7f-c07d9639c787/scratchpad/r5-analysis/tools/r5probe.py`
  and `r5probe_rep.py`, which also runs `video2rig.report`), then broke the miss down per keypoint, panel and frame.
  - Baselines reproduce the ledger: Run 4.35, StopLunge 4.60, Land v1 5.52, Land v3 4.86, Idle 1.81, Walk 2.51, Slap 3.09, Clap 2.59,
    PunchL 3.08. The fit is single-threaded and deterministic, so every number below is what `video2rig run --set ...` will print.
  - The probe ran under the Homebrew python3.12 with a scratch script path, so no `video2rig`/`torch` word was on the command line
    (the gpu_slot false-positive rule).
- **Panel geometry.** Front and side are orthographic, so both see the up axis. I measured, per frame, how far the two panels put the
  same keypoint apart along it:
  - the trunk shift (median over hips/spine/neck/head);
  - the per-point residual after that shift;
  - the scale difference;
  - foot / hip / head heights per panel;
  - a fractional time-lag search (`offsplit.py`, `feet.py`, `lag.py` in the same folder).
  - Results: `.../r5-analysis/out/*.json`.

## 1. Where each miss comes from

| | Run v2 (4.35) | StopLunge v2 (4.60) | Land v1 (5.52, shipped hc) | Land v3 (4.86, lost A/B) |
| --- | --- | --- | --- | --- |
| front / side panel median px | 3.63 / **5.39** | 4.63 / 4.93 | 4.95 / 5.09 | 2.48 / 4.14 |
| frames over 4 px | 107/158, spread over every stride (4.87 in them, 3.78 outside) | 113/124: run-in 5-33 and the whole braced hold 36-114 | 84/124: crouch 22-99 = 63 % of the clip, **7.94** px inside, 2.92 outside | 64/124: crouch 13-76, **6.43** inside, 1.27 outside |
| worst keypoints (front, side px) | RightArm (7, **20**), RightForeArm (7, 16), RightToeBase.side (2, 13), RightLeg (7, 10) | RightArm (9, **41**), RightForeArm (5, 20), RightLeg (14, 15), RightToeBase.side (19, 11) | RightHand points (6, **24**), RightForeArm (6, 22), LeftToeBase.side (19, 10), Spine2 (7, 12) | RightHand points (1, **29**), RightArm (3, 20), Spine2 (5, 15) |
| trunk shift between panels, median / p90 / range over the clip | 6.2 / 10.5 / 14.5 px | 7.1 / 11.4 / **43.6** px | 5.0 / 6.9 / 16.9 px | 6.2 / 15.8 / 20.6 px |
| head height, front minus side (feet agree within ~2 px) | -5 to -7 px in every eighth | -6 to -10 in the hold | -8 in the crouch | **-15 to -17** in the crouch |
| scale difference between panels, median / p90 | 1.8 / 5.7 % | 0.3 / 6.3 % | 2.3 / 4.3 % | 1.6 / 5.0 % |
| body height in the reading (px, median / min) | 335 / 309 | 338 / 314 | 281 / **203** | 320 / 227 |
| corr(per-frame miss, panel disagreement) | 0.88 | 0.93 | 0.93 | 0.89 |
| corr(per-frame miss, reading speed) | 0.14 (fastest clip: 9 px/frame median) | 0.53 | -0.25 | 0.13 |
| bend axes at their limit (raw solve frames) | Left/RightShoulder twist 29 / 24 | RightHand 22, Spine 11 | RightFoot 65, RightShoulder 59, Spine1 49, Head 34 | Spine 57, Spine1 55, Spine2 50, Head 50, RightFoot 36 |
| best time lag between panels | +0.75 frame (7.44 -> 6.66 px) | +2 frames (7.19 -> 7.04) | 0 | 0 |

### What causes it

- **Main cause: the take (all three).** Whenever the torso pitches forward toward the front camera (Run's lean, StopLunge's lunge and
  hold, Land's fold over the thighs), MiniMax draws the head and hips 5-17 px lower in the front panel than in the side panel, while
  the feet agree.
  - That is a perspective-style foreshortening in a picture that should be orthographic. No rig pose satisfies both panels, so the
    fit splits the difference.
  - The per-frame miss tracks this disagreement (r = 0.88-0.93 in every clip, and 0.79-0.87 in the clean ones too).
  - It is not a time desync. The best lag gains at most 0.8 px.
  - It is not the reader. It is a consistent shift of the whole trunk in one panel, not scattered per-joint error. The dense reader
    (1.65/1.85 px held-out) left it in place (4.4-5.7 px).
- **Land, second cause: fit range.** The deep fold drives the spine and head bend axes to their ±35° anatomy limit in the crouch
  frames (Land v3: 50-57 of 124 frames).
  - Wider joint ranges recover 0.5 px on Land v3 (4.86 -> 4.33).
  - The rest is the panel disagreement (crouch window still 5.3 px after the fix).
  - Land v1 also spends 63 % of its frames in the crouch (the long hold), so the frame median sits inside the bad window.
- **Things that are not the cause, or are minor:**
  - **Far arm.** The side panel's guessed far (right) arm is the worst point in every clip, the clean ones included (Clap 19 px, Walk
    17 px). It is an outlier the Cauchy loss already discounts; it lifts the median slightly but does not explain 4 vs 2.5 px.
  - **Motion blur and speed.** They are not the driver: miss vs reading speed is r = 0.14 on Run, the only fast clip, and negative on
    Land v1.
  - **Out of frame, cropped feet, camera drift.** None of these. Body height stays stable in standing frames, and no keypoint leaves
    the panel.
  - **Hold frames.** Bad only through the frame count: Land v1's crouch hold puts more than half of the frames into the bad window.
    Hold compression in refine does not touch the fit number.

## 2. What the sub-4 px takes have in common

| take (px) | body height px median / min | trunk shift median / range | head front-side | scale diff median / p90 | reading speed px/frame |
| --- | --- | --- | --- | --- | --- |
| Idle (1.81) | 397 / 392 | 3.1 / 3.0 | ~0 | 0.3 / 0.4 % | 0.3 |
| Walk (2.51) | 385 / 369 | 1.4 / 9.3 | -1.6 to +0.9 | 0.6 / 1.3 % | 2.8 |
| Clap (2.59) | 400 / 391 | 0.9 / 6.5 | n/m | 1.2 / 1.7 % | 0.6 |
| PunchL (3.08) | 388 / 375 | 1.3 / 5.2 | n/m | 1.4 / 1.8 % | 0.5 |
| Slap (3.09) | 386 / 381 | 2.5 / 5.6 | -0.7 to -6.2 | 1.0 / 1.7 % | 0.9 |
| **Run v2 (4.35)** | 335 / 309 | 6.2 / 14.5 | -5 to -7 | 1.8 / 5.7 % | **9.0** |
| **StopLunge v2 (4.60)** | 338 / 314 | 7.1 / 43.6 | -6 to -10 | 0.3 / 6.3 % | 0.9 |
| **Land v1 (5.52)** | 281 / 203 | 5.0 / 16.9 | -8 | 2.3 / 4.3 % | 1.9 |
| **Land v3 (4.86)** | 320 / 227 | 6.2 / 20.6 | -15 to -17 | 1.6 / 5.0 % | 0.4 |

- The sub-4 takes keep the back upright the whole clip: body height never drops below ~370 px.
- The two panels agree on the body's height within ~1-3 px. Their shift range stays under 10 px and their scale differs by under 2 %.
- The clips near the bar show the same effect in their bending phase:
  - Throw 3.98: head -14 / -11 px during the hurl lean.
  - Lift 4.23: head -8 px in the squat.
  - Uppercut 3.81 stays upright: head within ±3 px.
- Prompt wording is not what separates the two groups. The sub-4 prompts still carry "slow heavy acceleration" and "no motion blur",
  but so did StopLunge v2 and Land v1. The move does: torso pitch and crouch depth.

## 3. Routes per clip (measured, not estimated, unless marked)

Fit-knob sweep, `report` px (same code path as `video2rig run`). `D` = `--set panel_drift=true --set drift_min=0`. Joint sets are
`clips.<clip>.joints` in creature.json.

| settings | Run v2 | StopLunge v2 | Land v1 | Land v3 |
| --- | --- | --- | --- | --- |
| baseline | 4.35 | 4.60 | 5.52 | 4.86 |
| `D` | 3.74 | 4.08 | 5.31 | 3.69 |
| `w_smooth=10` | 4.12 | 4.53 | 5.57 | 4.25 |
| `w_prior=0.5` | 4.28 | - | - | - |
| `cauchy_px=10` | 4.91 (worse) | - | - | - |
| `hidden_refit=true` | 4.13 * | 4.13 * | 5.06 * | 4.23 * |
| joints only | 4.33 | 4.58 | 5.50 | 4.33 |
| `D` + `w_smooth=10` | 3.49 | 3.80 | - | 3.74 |
| `D` + `w_smooth=15` | **3.52** | 4.00 | - | - |
| `D` + joints | 3.73 | 4.04 | 5.17 | **3.71** (joints L3) |
| `D` + `w_smooth=15` + joints | - | **3.89** (joints S2) | **4.65** (joints L1b) | - |

\* `hidden_refit` lowers the printed number by down-weighting points out of the "seen" set. On the same points it is 4.31 / 4.59 /
5.32 / 4.56, so it is metric shrinkage; not recommended.

- **`panel_drift`.** It moves each panel's readings half the trunk shift along the shared up axis, per frame (5-frame median). That
  removes exactly the contradiction diagnosed above. It has been off upstream since 2026-10-19 because it threw a troll's arms off on
  combo01, so judge the review film and the in-game A/B, not px alone.
- **Joint sets used** (ranges in rad from the start pose, as in the ROUND4 `jt` rows):
  - L3 = `{"Spine":{"range":1.0},"Spine1":{"range":1.0},"Spine2":{"range":1.0},"Head":{"range":1.5},"RightFoot":{"range":1.5}}`
  - S2 = `{"RightHand":{"range":1.5},"RightFoot":{"range":1.5},"LeftFoot":{"range":1.5},"LeftToeBase":{"range":1.5},"RightArm":{"range":2.0},"LeftArm":{"range":2.0}}`
  - L1b = L3 plus `"LeftFoot":{"range":1.5},"RightShoulder":{"range":1.0},"RightArm":{"range":2.0}`

Report warnings on the finalists (bar = median < 4 px and no warnings):

| candidate | px | report warnings | outline F / S |
| --- | --- | --- | --- |
| Run v2 `D` + `w_smooth=15` | **3.52** | **none** | 0.847 / 0.820 (shipped 0.840 / 0.816) |
| Run v2 `D` | 3.74 | none | 0.841 / 0.815 |
| Run v2 `D` + `w_smooth=10` | 3.49 | LeftArm turns 53° at frame 154 | 0.845 / 0.820 |
| Run v2 `D` + `w_smooth=20` | 3.61 | none | 0.847 / 0.819 |
| Land v3 `D` + joints L3 | **3.71** | **none** | 0.914 / 0.872 (shipped v3 0.915 / 0.864) |
| Land v1 `D` + `w_smooth=15` + L1b | 4.65 | Spine at range in 60 frames | 0.893 / 0.845 |
| StopLunge v2 `D` + `w_smooth=15` + S2 | 3.89 | LeftArm turns 62° at frame 29; body under the floor in 4 frames | 0.837 / 0.804 |
| StopLunge v2, 5 other variants | 3.71-3.96 | always 2-4 warnings: a 47-112° one-frame arm or leg turn at frames 20-34 (the run-in-to-plant), the body under the floor in 3-8 frames | ~0.84 / 0.80 |

Caveats:

- **Land v3 crouch.** Land v3 passes on the frame median because 65 of 124 frames are standing (about 1 px). Its crouch window still
  misses 5.3 px. Land v1's best fit route stays over the bar (4.65).
- **StopLunge warnings.** No StopLunge fit clears its warnings: the plant transition and the floor dip are in the take. The take also
  never rises (ROUND4), which no fit can add.

### Ranked routes

| clip | rank | route | expected | confidence |
| --- | --- | --- | --- | --- |
| **Run** | 1 | **(a) fit-only:** run_v2, `D` + `w_smooth=15` | 3.52 px, no warnings (measured) | high on the number; medium that it looks as good (watch the arms in review-r5.mp4) |
| | 2 | (c) new take run_v3 with the prompt edit below, plus the same fit | 3.0-3.5 px (estimate) | low-medium. It would be the third Run take; only if (a) loses the A/B |
| **Land** | 1 | **(a) fit-only on land_v3:** `D` + joints L3, then fix v3's in-game timing | 3.71 px, no warnings (measured) | high on the number; medium on the A/B. See the note below the table |
| | 2 | (c) new take land_v4 (back upright, short hold) plus `D` + L3 | 2.5-3.5 px (estimate: the crouch window should fall from 5.3-6.4 toward the ~3 px of upright clips) | medium-low. It is the fourth Land take: needs a director override of "no fourth take" and 0.30 USD |
| | 3 | (a) fit-only on shipped land_v1 | 4.65 px, 1 warning (measured) | does not reach the bar |
| **StopLunge** | 1 | **(c) new take stoplunge_v3** (upright brace, short hold, real rise) plus `D` + `w_smooth=15` | 3.0-3.5 px (estimate). Needed anyway for the rise | medium-low. Third take: needs a director override of "no third take" and about 0.25-0.30 USD |
| | 2 | (a) fit-only fallback on stoplunge_v2: `D` + `w_smooth=15` + S2 | 3.89 px, 2 warnings (measured; baseline 4.60 with 3 warnings) | high on the number; it cannot meet the no-warnings bar |

Note on the Land fit route:

- Land v3 lost r4 because it "stays upright for 0.1-0.25 s after the crater, folds 0.4 s late" (AB-ingame-r4-critique). That is a
  timing problem, not a pose problem.
- v3's contact is around 1.0-1.2 s, against 0.833 s for hc Land v1. Re-measure its crouch onset (`measure_timing.py`, Land
  `hit_by='ground'`) so the game's Land segment starts on the onset, then rematch it in-game against hc Land v1.
- If v3 loses again, hc Land v1 stays and Land stays a recorded bar miss unless route 2 is approved.

### Prompt edits (template Brute wording kept; never "slowly" or "held ~2 s")

**StopLunge v3** (edit of the current `prompts/StopLunge.txt`; send with `--end`, 5 s). These edits apply Land v3's sync wording and
an upright back:

- Changed: "both show the same moment;" -> "both show the same moment in exact sync, with exactly the same timing;"
- Changed: "no camera shake, no slow motion, no motion blur;" -> "no slow motion;" (the appended template carries the fast-shutter
  sentence, as Run v2 / Land v3)
- Changed: "He weighs a ton: slow heavy acceleration, nothing floats." -> "He weighs a ton, nothing floats."
- Changed: "a sprint stopping dead, ON THE SPOT, the floor does not move:" -> "a sprint stopping dead, ON THE SPOT, facing the front
  camera throughout, the floor does not move:"
- Removed: "1) 0-1.4 s he runs in place leaning forward with slow heavy strides, fists sharp, no smear;"
  Added: "1) 0-1.4 s he runs in place with heavy strides, torso nearly upright with only a slight forward tilt, fists sharp;"
- Removed: "2) 1.4-2.2 s both feet plant hard, his torso lunges forward over his front knee and his arms swing wide for balance;
  3) 2.2-3.2 s he holds the low braced lunge, breathing hard; 4) 3.2-5 s he slowly straightens and stands in the starting stance."
  Added: "2) 1.4-2.0 s both feet plant hard, wide apart, and he drops into a low braced stance, knees deeply bent, back nearly
  upright, chest to the front camera, arms swinging wide for balance, no arm above the shoulders; 3) 2.0-2.3 s he holds the braced
  stance for at most 0.3 s; 4) 2.3-3.6 s he pushes up and rises heavily, back in the starting stance by 3.6 s; 5) 3.6-5 s he stands
  still in the starting stance, chest heaving."
- Kept unchanged: the creature sentence, the panels sentence, "Both views end back in the first-frame stance, feet where they
  started.", "The whole body stays inside the frame the whole time." and "Fists and feet stay sharp and on the floor."
- The full text is about 1240 chars, plus the appended template.

**Land v4** (edit of the current `prompts/Land.txt` = v3 text; `--end`, 5 s; only with the override):

- Removed: "torso folding straight forward with no twist," Added: "back staying nearly upright with no twist, head always above his
  knees,"
- Removed: "4) he holds the crouch for at most 0.3 s;" Added: "4) he holds the crouch for at most 0.3 s, then rises at once;"
- Everything else is kept, including the exact-sync sentence that passed `check` (1.08 %).

**Run v3** (only if fit route (a) loses its A/B):

- Removed: "torso leaning forward," Added: "torso nearly upright with only a slight forward tilt, head level,"
- "both show the same moment in exact sync;" -> "both show the same moment in exact sync, with exactly the same timing;"
- Risk: the critics liked the lumbering lean; the upright run may read lighter.

## 4. Recommendation: order and exact commands

Order:

1. **Run (a).** Free and CPU; meets the bar on numbers.
2. **Land (a) on v3.** Free and CPU: fit, then timing, then in-game rematch.
3. **StopLunge (a) fallback** (free; better than shipped, 3.89 vs 4.60 px).
4. **Ask the director** about the StopLunge v3 take, the only route to a rise and no warnings. Land v4 only if v3 loses its rematch.

One paid clip at a time, fal first (balance 15.43 USD).

Concurrency: another session wrote `brute-aligned/clips/smash_sd_v1.prompt.txt` during this analysis, and `docs/brute/video2rig/SEEDANCE.md`
is untracked. Check before editing `creature.json` (back it up as `creature.json.pre-r5`) and never touch its other clip entries.

Common setup:

```
P=/Users/midir/hulk/Local/video2rig/brute-aligned; PY=/Users/midir/video2rig/.venv/bin/python; cd /Users/midir/video2rig-lockfix
```

Notes on these commands:

- `video2rig run --tag=-r5` reads `work/<clip>/reader-r5.npz`. Without the copy below it would read the clip again with the reader on
  the GPU.
- With the copy, the reader's fingerprint, the clip, the TTA and the crops all match, so it is a CPU fit (about 2-3.5 min). It writes
  only the `-r5` files: `fit-r5.npz`, `fit-r5-report.json`, `report-r5.json`, `clock-r5.json` and `out/<clip>-r5.npz`.
- These command lines contain `video2rig`, so gpu_slot will count them as an ML client. Run them when no capture is waiting.

**Run (a)**, CPU evaluation:

```
cp $P/work/run_v2/reader.npz $P/work/run_v2/reader-r5.npz
$PY -m video2rig run $P run_v2 --tag=-r5 --set panel_drift=true --set drift_min=0 --set w_smooth=15   # expect "median keypoint miss 3.52 px", report warnings none
$PY -m video2rig review $P run_v2 --tag=-r5                                                          # work/run_v2/review-r5.mp4: check arms/panels by eye
```

Adoption: the Blender steps are GPU clients, so they wait for `python3 tools/gpu/gpu_gates.py check`. `--from run` re-fits untagged and
overwrites fit.npz, report.json and out/run_v2.npz, so back up first:

```
mkdir -p $P/work/run_v2/attempt-pre-r5 && cp $P/out/run_v2.npz $P/work/run_v2/{fit.npz,fit-report.json,report.json,pipeline.state} $P/work/run_v2/attempt-pre-r5/
cd /Users/midir/hulk && tools/brute/v2r/run_clip.sh $P run_v2 Run --loop --fork-dir /Users/midir/video2rig-lockfix \
  --motion-dir /Users/midir/hulk/Local/video2rig/motion-v2r-r5 --from run \
  --run-args "--set panel_drift=true --set drift_min=0 --set w_smooth=15" \
  --refine-args "--treadmill --window 33 124 --loop-win 0.7 --trim 0"
```

Then run the in-game blind A/B: Run r5 against shipped Run v2.

**Land (a) on v3.** Add `"land_v3": {"joints": <L3 above>}` under `clips` in `$P/creature.json`, then:

```
cp $P/work/land_v3/reader.npz $P/work/land_v3/reader-r5.npz
$PY -m video2rig run $P land_v3 --tag=-r5 --set panel_drift=true --set drift_min=0      # expect 3.71 px, report warnings none
$PY -m video2rig review $P land_v3 --tag=-r5
mkdir -p $P/work/land_v3/attempt-pre-r5 && cp $P/out/land_v3.npz $P/work/land_v3/{fit.npz,fit-report.json,report.json,pipeline.state} $P/work/land_v3/attempt-pre-r5/
cd /Users/midir/hulk && tools/brute/v2r/run_clip.sh $P land_v3 Land --return-to-stance --fork-dir /Users/midir/video2rig-lockfix \
  --motion-dir /Users/midir/hulk/Local/video2rig/motion-v2r-r5 --from run --run-args "--set panel_drift=true --set drift_min=0" \
  --refine-args "--compress-holds --return-frames 18 --stance-snap 8 --max-seconds 3.0 --max-lift 0.06"
```

Then re-measure the crouch onset (Land `hit_by='ground'` in `tools/brute/v2r/measure_timing.py`) so the game segment starts on it, and
rematch in-game against hc Land v1.

**StopLunge (a) fallback.** Add `"stoplunge_v2": {"joints": <S2 above>}`, then:

```
cp $P/work/stoplunge_v2/reader.npz $P/work/stoplunge_v2/reader-r5.npz
$PY -m video2rig run $P stoplunge_v2 --tag=-r5 --set panel_drift=true --set drift_min=0 --set w_smooth=15   # expect 3.89 px, 2 warnings
```

Adopt only if it wins the A/B against shipped hc v2. Use the same `run_clip.sh ... --from run` pattern with
`--refine-args "--compress-holds --return-frames 18 --stance-snap 8 --max-seconds 3.0 --max-lift 0.07"`.

**StopLunge (c)**, only after the director approves a third take:

1. Save the v3 text above as `prompts/StopLunge.txt` (v2 as sent is in `clips/stoplunge_v2.prompt.txt`).
2. Generate:
   ```
   cd /Users/midir/hulk && python3 tools/brute/v2r/generate_fal.py $P stoplunge_v3 --prompt docs/brute/video2rig/prompts/StopLunge.txt --duration 5 --end --dry-run   # then without --dry-run
   ```
3. Run the size gate, then `check` (the GPU read; gated), then
   `run --set panel_drift=true --set drift_min=0 --set w_smooth=15`.
4. Accept only if: check < 1.5 %, it rises to the stance, fit < 4 px, report warnings none.

**Dry-parse** (CPU, nothing executed; `/private/tmp/claude-501/-Users-midir/dc49ac78-9559-4631-aa7f-c07d9639c787/scratchpad/r5-analysis/tools/dryparse_r5.py`, `dp_fal.py`, `rc_opts.sh`). All parsed:

- **`python -m video2rig` argparse.** Parsed `run <P> {run_v2,stoplunge_v2,land_v3} --tag=-r5 --set ...`, `review <P> {run_v2,stoplunge_v2} --tag=-r5`
  and the untagged `run` that `--run-args` produces. Each `--set` value converts as `__main__.py` does: `panel_drift` -> True (bool),
  `drift_min` -> 0 (int), `w_smooth` -> 10/15 (int). All three are reader-fit SETTINGS keys, so `road.run` forwards them (commit
  `ede6cce`).
- **`video2rig.reader.fit`.** `<P> run_v2 --tag=-r5 --set ...` parsed with the same values.
- **`run_clip.sh` option loop** (lines 217-239 run on the exact argv). Run: MODE `--loop`, FROM `run`, MOTION_DIR `motion-v2r-r5`,
  RUN_ARGS splits into 6 words (`--set panel_drift=true --set drift_min=0 --set w_smooth=15|10`), REFINE_ARGS as ROUND4. StopLunge:
  MODE `--return-to-stance`, same.
- **`generate_fal.py`.** `<P> stoplunge_v3 --prompt .../StopLunge.txt --duration 5 --end [--dry-run]` gives duration 5, end True,
  768P, endpoint `minimax/h3/image-to-video`, expansion disabled.
- **The joint sets** go into creature.json, not onto the command line. The probe passed them as `clips.<clip>.joints` (the same
  `clip_cfg` path `Creature.bounds` reads).

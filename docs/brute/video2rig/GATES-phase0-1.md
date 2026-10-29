Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

# GATES phase 0-1: verified gate lines (collected 2026-10-29)

Bookkeeping for the director to merge into `LEDGER.md` later. This file is not merged into the ledger (another agent is appending to it). Every number below is quoted from the named source file; nothing is re-measured or interpreted. Dates are 2026-10-29 unless shown. Branch `chinese-animation-upgrades`.

## Phase 0 tools (`tools/brute/v2r`, no spend, nothing submitted to fal)

Sources: `tools/brute/v2r/TESTS.md`, `TESTS-refine-export.md`, `TESTS-ab.md`, `TESTS-timing.md`.

- 2026-10-29 fal price (`GET /v1/models/pricing`, read-only): `unit_price 0.05`, unit seconds, USD. 5 s clip = 0.25 USD. Per-clip cap default 2.00 USD; override env `V2R_FAL_MAX_USD`. (TESTS.md section 1-3)
- 2026-10-29 fal balance (`GET /v1/account/billing`, read-only): `current_balance 23.65 USD`. (TESTS.md section 3)
- 2026-10-29 fal endpoint schema: duration int 5..15; resolution enum 480P/768P/2K/4K, schema default 2K, we send 768P; prompt_expansion_mode default balanced, we send disabled. No price field in the OpenAPI spec. (TESTS.md section 3)
- 2026-10-29 generate_fal.py exit codes: 0 done, 2 other, 3 balance, 4 auth, 5 USD cap, 6 stopped while waiting (resume with `--resume`, no new charge). Mock selftest: all scenarios exit as listed. (TESTS.md section 2)
- 2026-10-29 size gate on the dragon project clips (`size_gate.py`, limit 1.30, area metric default; dragon clips only, not Brute). Default metric, scale: PASS idle 1.05, idle_look 1.00, bite 1.12, claw_swipe 1.18, stagger 1.07, rise 1.18, land2 1.19, collapse 1.06, death 1.01, roar_sd2 1.17. FAIL roar 1.55, roar2 1.56, roar_sd 1.24 (wings off both front edges 60+ frames), land 1.26 (edges 14-16 frames), takeoff 1.39, takeoff2 1.31. Box metric also FAILs rise (height 1.38, pose) and land2 (height 1.57, hop pitches body up). (TESTS.md section 4)
- 2026-10-29 EXPORT_SELFTEST PASS (17 clips from assemble_motion CLIPS; v2r names win over old names in one dir). (TESTS-refine-export.md section 0)
- 2026-10-29 ROUNDTRIP_GATE Idle max_vertex_delta_mm 0.0021 frames 12 lengths 156/156 PASS (export vs shipped Idle). (TESTS-refine-export.md section 2)
- 2026-10-29 EXPORT_GATE Idle max_vertex_delta_mm 0.0026 frames 5 PASS (unrefined fit). (TESTS-refine-export.md section 2)
- 2026-10-29 ROUNDTRIP_GATE Idle max_vertex_delta_mm 0.0012 frames 12 lengths 156/156 PASS (assemble_motion output vs export). (TESTS-refine-export.md section 4)
- 2026-10-29 REFINE_GATE Idle seam 1.18 foot_drift_mm 3.6 toe_min_mm 0.0 peakhand_L 21 peakhand_R 153 (refined test fit; seam 1.18 = step last frame to frame 0 over median step). (TESTS-refine-export.md section 3)
- 2026-10-29 EXPORT_GATE Idle max_vertex_delta_mm 0.0029 frames 5 PASS (refined). (TESTS-refine-export.md section 3)
- 2026-10-29 REFINE_GATE PunchL seam 0.16 foot_drift_mm 2.2 toe_min_mm -5.5 peakhand_L 31 peakhand_R 29 (one-shot path, `--return-to-stance`, `--floor=-0.435`). (TESTS-refine-export.md section 5)
- 2026-10-29 EXPORT_GATE PunchL max_vertex_delta_mm 0.0063 frames 5 PASS (49 frames, 1.6 s). (TESTS-refine-export.md section 5)
- 2026-10-29 REFINE_GATE IdleOpen seam 1.34 foot_drift_mm 3.2 toe_min_mm 0.0 peakhand_L 21 peakhand_R 9 (open-loop test, seam before 11.24 x median). (TESTS-refine-export.md section 6)
- 2026-10-29 EXPORT_GATE Idle max_vertex_delta_mm 0.0028 frames 5 PASS (IdleOpen, 116 frames). (TESTS-refine-export.md section 6)
- 2026-10-29 AB_MEASURE Idle A seam 0.00 foot_drift_px 11.2 secondary 0.45 (A = brute_v5 Idle, old). (TESTS-ab.md)
- 2026-10-29 AB_MEASURE Idle B seam 0.00 foot_drift_px 3.7 secondary 0.49 (B = refined v2r test Idle). (TESTS-ab.md)
- 2026-10-29 AB test pair KEY (test only, the source marks it "may be shown"; it is a harness check, not a quality verdict): seed 2081823275 (crc32 of "Idle"), A = old, B = new. Do not give this file to a blind critic. (TESTS-ab.md)
- 2026-10-29 AB render time: render A 217 s, render B 208 s (250 frames x 3 cameras, 0.28 s per frame); measure 4.5 s; about 7 min per pair. (TESTS-ab.md)
- 2026-10-29 timing check (`measure_timing.py`, brute_v5 vs today's constants, tolerance 0.15 s): worst difference 0.100 s (Uppercut To: today 1.40, measured 1.300, clamped by a second generated swing). Proposed HIT: PunchL/R 0.967, Slap 0.933, Clap 0.700, Smash 1.167, Uppercut 0.600, Throw 0.467, Land 0.467 (today 1.0 / 0.9 / 0.7 / 1.17 / 0.6 / 0.45 / 0.5). (TESTS-timing.md)
- 2026-10-29 timing build: `unreal/WebHomage/Scripts/build_editor.sh` Succeeded (BruteCharacter.cpp, no warnings). Not run in game; no engine launched. FBX cross-check not done. (TESTS-timing.md, C++ side)
- 2026-10-29 timing data: v5 writes nothing (`NOTHING TO WRITE`, no v2r clips), so the game keeps today's constants; no `BruteClipTiming.json` in the repo. (TESTS-timing.md, Selection)

## Phase 0 rig and start picture (`Local/video2rig/brute/`, `brute-aligned/`)

Sources: `Local/video2rig/brute/REPORT-phase0.md` (paths relative to `/Users/midir/hulk/`).

- 2026-10-29 EXPORT_RIG: 52 bones, 83129 vertices, 108756 triangles, 0 props, 1 material. (REPORT-phase0.md item 4)
- 2026-10-29 shape keys: 18 corrective (+ Basis = 19 key blocks), all values 0, no drivers, no key animation; 17 Actions incl. Idle (0-124, 24 fps). (REPORT-phase0.md item 1)
- 2026-10-29 floor: armature object lowered by 0.4567 (z 1.1267 -> 0.67); final bounds z 0.000..2.575 (height 2.575 m). (REPORT-phase0.md item 1)
- 2026-10-29 facing -Y: hips L-R axis -93 deg, ankle->toe -91.5 deg (`creature.json "facing": "-Y"`). (REPORT-phase0.md item 2)
- 2026-10-29 twins (auto): 23 pairs, all Left*/Right*. Limbs (auto): 5 chains; 8 standing-leg bones; locked feet LeftToeBase, RightToeBase. Hinges (auto): LeftLeg, RightLeg, LeftForeArm, RightForeArm found; fitted bones 69 channels. (REPORT-phase0.md item 5)
- 2026-10-29 bone-tail finding (on `brute/`, glTF import): tails perpendicular to the limb (cos about 0.00). Hinge auto-detect marks LeftLeg REVERSED from a 116 deg left-knee tail angle (right knee 7.6 deg). (REPORT-phase0.md, Finding)
- 2026-10-29 aligned project decision: `brute-aligned/` = same mesh and stance, bones re-tailed to child heads, pose recomputed; max vertex delta 5e-7; 23 twins and same limbs; no reversed knee; flat-foot term present. Cost: per-bone basis conversion back to shipped frames before assemble_motion (`v2r_rig.py` + `export_clip.py` implement the aligned<->shipped retarget per TESTS-refine-export.md). The Phase 0 report recommended this; the reader is training on `brute-aligned/` (see Phase 1), but no decision note was found in the files read. (REPORT-phase0.md, Finding and Files)
- 2026-10-29 start picture (`brute/start/start.png`, copied to `brute-aligned/start/`): 1920x1080, two orthographic 960x1080 panels (front | side); flags `--facing=-Y --margin 1.9 --lead 0.15` (the `=` is required); 4 s, Cycles CPU 64 samples. Ortho height 4.89 m per panel; floor line 12 % above bottom edge; 4.30 m above floor; Brute about 568 px tall; front half-width 2.17 m (Idle width 1.48 m). (REPORT-phase0.md item 6)
- 2026-10-29 start note: Cycles output is not bit-reproducible; never re-render one start without copying it to the other. (REPORT-phase0.md, Files)

## Phase 1 reader (in progress, `brute-aligned/reader/`)

Sources: `Local/video2rig/brute-aligned/reader/poses.log`, `reader/renders/render.log`, `reader/train.log`.

- 2026-10-29 POSES 3000 -> `reader/poses.npz` in 174.8 s. (poses.log)
- 2026-10-29 RENDER_POSES done: 3000 poses in 245.9 s (setup 0.1 s), 0.082 s per pose; last frames 0187 saved for v2r_front and v2r_side. (render.log)
- 2026-10-29 train (ground project), last line seen at 02:04 EDT: `[2606.9s] step 1200 loss 5.7106  (2.152 s per step, 13% of the time)`. Previous: step 1000 at 2137.9 s, 2.113 s/step, loss 7.1831. Log last written 02:02:07 EDT. Setup: device mps, bf16; 6000 pictures (5700 to learn, 300 held out), 41 keypoints, seen 0.82 of the keypoints; reader 22.4 M parameters. (train.log)
- 2026-10-29 status: training still running at the time of reading (ps: `video2rig.reader.train ... brute-aligned --minutes 8.0 --steps 9000 --out reader/reader.pt`, 45:56 elapsed; prepare 52:59 elapsed). Target 9000 steps; at 2.15 s/step that is about 5.4 h. Whether `--minutes 8.0` stops it early is not verified. No `reader.pt` yet. (train.log, ps)

## Pilot clip (`brute-aligned/clips/idle_v1`)

Sources: `Local/video2rig/brute-aligned/clips/idle_v1.json`, `work/idle_v1/`.

- 2026-10-29 provenance: provider fal, endpoint `minimax/h3/image-to-video`, request_id `01a18627-e6a7-7a10-9818-53b8a462c39c`. Start `brute-aligned/start/start.png`, sha256 `ac8793971a4ed5e7153a667ea04a111c307be930561e1e4f75d2e32dd04b64ad`, image_source data_uri, end_frame true. (idle_v1.json)
- 2026-10-29 settings: 768P, duration 8 s, seed 1917715662 (random), prompt 1347 chars, prompt_expansion_mode disabled. Submitted 2026-10-29T05:35:24Z, completed 05:37:39Z, seconds_to_ready 113, metrics.inference_time 110.99 s. Output 977897 bytes (video/mp4). (idle_v1.json)
- 2026-10-29 cost: unit 0.05 USD/s; estimate 0.40 USD; billing_event quantity 9.6 s, cost_total 0.48 USD (`cost_total_usd 0.48`). CONTRADICTION: the same file records balance_before 23.65, balance_after 23.65, balance_delta_usd 0.0. The billing event is the charge figure; the balance delta was read before the feed caught up (not verified).
- 2026-10-29 size gate: NOT FOUND. `work/idle_v1/` holds only `sheet.jpg` (92644 bytes, 01:37). The other clip dirs (punchr_v1, punchr_v2, punchl_v1, slap_v1, clap_v1, smash_v1, uppercut_v1, walk_v1, run_v1, stoplunge_v1, stoplunge_v2) each have `size_gate.txt`. Idle_v1 has no gate result on record.

## Air project (`Local/video2rig/brute-air/`)

Sources: `Local/video2rig/brute-air/REPORT-air.md`. The `## UPDATE` section at the end is the current state; the body above it describes the earlier stock-checkout run and is superseded.

- 2026-10-29 Fall frame: action Fall, key 0.8 used (first key = loop start; range 0.8..48.0 at 24 fps). Commit c518614 (prompts/Fall.txt + INDEX.md) pushed to origin. (REPORT-air.md)
- 2026-10-29 hover: armature z 1.7254; lowest vertex 0.9000 m; top 3.4447 m; body height 2.5447 m; `--hover 0.3536713813895498`; creature.json `"floor": -1.570372`. Cameras same flags as ground project (ortho 4.835 m vs 4.892 m). Floor not visible in the start picture (cameras horizontal). (REPORT-air.md)
- 2026-10-29 air key (UPDATE, current): `"air": {"alt_rig": "/Users/midir/hulk/Local/video2rig/brute-aligned/rig", "alt_share": 0.3, "jump_share": 0.8, "jump_max": 0.5}`; checkout worktree `/Users/midir/video2rig-brute-air` (branch brute-air-reader, 1c720d4; diff vs mac-mps = video2rig/reader/poses.py +27/-4). Values are untested suggestions. (REPORT-air.md UPDATE)
- 2026-10-29 height distribution, 300 random poses, lowest vertex above floor in body heights. Stock checkout (superseded): on floor 69 %, 0.02-0.3 31 %, >0.3 0 %, max 0.29. With air key (current): on floor (<0.02) 22 %, 0.02-0.2 31 %, 0.2-0.5 47 %, >0.5 0 %, max 0.50, median 0.18. Start pose hovers at 0.35. (REPORT-air.md)
- 2026-10-29 prepare timings (air, `--skip-train`): poses_s 177.2, visible_s 27.3, render_s 230.9. Earlier stock run: 170.9 / 26.8 / 225.6. (REPORT-air.md UPDATE)
- 2026-10-29 air poses state: `reader/poses.npz` 3000 poses (7.8 MB), `visible.npz` seen in panels [0.90, 0.79], renders v2r_front and v2r_side 188 sheets each; no `reader.pt`, no training. (REPORT-air.md UPDATE)

## Commits on `chinese-animation-upgrades` since 8be8157 (10)

`git -C ~/hulk log --oneline 8be8157..HEAD`. HEAD = origin/chinese-animation-upgrades = a295dca (0 commits ahead of origin at 02:04 EDT).

- a295dca tools/brute/v2r: blind A/B harness (3 fixed cameras, seeded labels, KEY hidden from the critic, AB_MEASURE seam/foot drift/secondary)
- a76c1cb Brute: optional Config/BruteClipTiming.json overrides act/segment clip times (constants unchanged without it; -WHBruteNoClipTiming); measure_timing.py proposes them from the clips (old clips within 0.10 s)
- c518614 brute prompts: Fall rewritten for the air start picture (hovering braced pose, falling in place); INDEX row updated
- ba6abde tools/brute/v2r: v2r_rig (aligned<->shipped retarget), export_clip (EXPORT_GATE), refine_brute (REFINE_GATE), offline round-trip tests
- 3c15fe8 tools/brute/v2r: fal MiniMax H3 generator (queue API, resume, balance/price, exit codes) + silhouette size gate; offline tests
- a8aa8e5 video2rig prompts for all 17 Brute clips + INDEX (durations, loop, end pose, risks)
- 5c894a2 video2rig ledger: clip rows, spend table, Phase 0 environment gate lines, timing data to re-measure
- 5a415aa Plan: spend rule = use fal balance fully, then Higgsfield; no per-clip stop
- 61db2e6 Plan: fal H3 endpoint verified, Higgsfield fallback, run in ~/hulk, disk/GPU notes
- 7220c6b Brute video2rig + MiniMax (fal) animation upgrade: plan only, no work started

## Observed, not ours (no action taken)

- Working tree at 02:04 EDT has 4 modified tracked files not from this task: `docs/brute/video2rig/LEDGER.md` (being appended by another agent), `prompts/INDEX.md`, `prompts/PunchR.txt`, `prompts/StopLunge.txt`. Left untouched.
- A separate paid fal job is running in `brute-aligned` (`generate_fal.py ... lift_v1 --duration 6 --resolution 768P`, task file `clips/lift_v1.task.json`), started about 01:11 before 02:04. Not ours; not stopped. Its cost is not in this file.
- Other sessions' Markhor Meadow (`mayor_mine`, `mayor_chop`) reader prepare/train processes are also running.

## Director decisions (Fable 5.1, 2026-10-29)

- 01:05 Rig: use the ALIGNED project (bone tails re-pointed at children, mesh deformation identical to 5e-7 m) for reader and fits; export_clip.py retargets back to the shipped bone frames with an EXPORT_GATE under 1.0 mm.
- 01:45 Clips are generated ahead of the reader (they depend only on the start picture); check/fit run once the reader lands.
- 02:00 Air project uses the `air` key from the fork branch brute-air-reader in our own worktree ~/video2rig-brute-air; training starts after the ground reader finishes (shared GPU).
- fal billing: the 8 s pilot was billed as 9.6 s = 0.48 USD (fal rounds up); budget per 5 s clip assume 0.30 USD.

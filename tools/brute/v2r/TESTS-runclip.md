# run_clip.sh: usage and offline tests (2026-10-29)

Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

No video, no spend, no reader training. Nothing was written to `~/hulk/Local/video2rig/brute-aligned/` or its `reader/`: the tests
use a copy of `model.blend` (made earlier by `test_refine_export.sh`) and symlinks to the shipped clips, `start/`, `rig/` and
`creature.json` for the size gate. Machine: Mac Studio M3 Ultra, Blender 5.2.0 LTS, one Blender of ours at a time (1 other
Blender, no UnrealEditor, while testing).

## Usage

```
tools/brute/v2r/run_clip.sh <project_dir> <clipname> <Clip> [--loop | --return-to-stance]
     [--fork-dir <video2rig checkout>] [--motion-dir <dir>] [--from <step>] [--to <step>] [--python <python>]
     [--no-size-gate] [--run-args "..."] [--refine-args "..."] [--export-args "..."]
tools/brute/v2r/run_clip.sh --selftest
```

Examples (once the reader exists):

```
tools/brute/v2r/run_clip.sh ~/hulk/Local/video2rig/brute-aligned idle_v1 Idle --loop
tools/brute/v2r/run_clip.sh ~/hulk/Local/video2rig/brute-aligned punchl_v1 PunchL --return-to-stance
tools/brute/v2r/run_clip.sh ~/hulk/Local/video2rig/brute-air fall_v1 Fall --loop --fork-dir ~/video2rig-brute-air
tools/brute/v2r/run_clip.sh ~/hulk/Local/video2rig/brute-aligned idle_v1 Idle --loop --from refine   # restart
```

Steps, in order (`--from` / `--to` take these names). Each step's full output is `<project>/work/<clipname>/<step>.log`.

| step | what | gate / parsed |
| --- | --- | --- |
| `size` | `size_gate.py <project> <clipname> --max 1.3` (extra to the brief: PLAN says a clip failing it is never fitted; `--no-size-gate` skips it) | `SIZE_GATE FAIL` stops (exit 3), with the first FAIL reason |
| `check` | `video2rig check` | result line `OK\|WARN\|FAIL <clip>: body 0.0107, limbs ...`; percent = body x 100; FAIL if the tool says FAIL, exits 1, or the percent is over 1.5; WARN continues and prints the WARN lines; no readable result, or `body None` (not two panels), stops |
| `run` | `video2rig run` (needs `<project>/reader/reader.pt`, else it stops: without it `run` would silently take the slow `--old` road) | `fit <clip>: ...; median keypoint miss 1.37 px` (fit px); `report {json}`: `len(warnings)` and the `outline_match` values joined by `/`; needs `out/<clipname>.npz`. Fit over 4 px: WARN, continues. Any warning, or outline under 0.9: printed, continues |
| `review` | `video2rig review` | `work/<clipname>/review.mp4` must exist |
| `import` | `blender model.blend -b --factory-startup --python <fork>/blender/import_motion.py -- --motion out/<clipname>.npz --action <clipname> --save <project>/<Clip>_v2r_v<N>.blend`; N = first free number | `IMPORT_MOTION saved` |
| `refine` | `refine_brute.py -- <blend> [--loop\|--return-to-stance] --clip <Clip> --stance-rig <project>/rig/rig.json` | `REFINE_GATE` line (seam, foot drift mm, toe min mm, peak hands) and `<blend>_refined.blend`; WARN only for loop seam over 2, toe under -10 mm, drift over 10 mm |
| `export` | `export_clip.py -- <refined.blend> <Clip> <motion_dir>` (default `/Users/midir/hulk/Local/video2rig/motion-v2r/`, created by this step only) | `EXPORT_GATE ... PASS` and `EXPORT ... wrote <glb>`; FAIL stops (exit 3) |
| `sheet` | `ffmpeg ... select=not(mod(n,N)),scale=480:-2,tile=4x4` -> `work/<clipname>/review_sheet.jpg` (N = frames / 16 from ffprobe) | file exists |
| `log` | append and print the line below | |

```
CLIP <Clip> <clipname> check <pct> <PASS|FAIL> fit <px> warn <n> outline <a>/<b> refine <seam> <drift_mm> <toe_mm> export <mm> <PASS|FAIL> blend <refined.blend> glb <glb>
```

Fields map to LEDGER.md columns: check % (body only; the limbs share is in `check.log`), fit median px, fit warnings, refine
(seam x, foot drift; the log's drift is in mm, as `REFINE_GATE` prints it). Outline is per view in the order of the report's
`outline_match` (the project's view names; front then side for the Brute).

Other behaviour:
- Exit codes: 0 done, 2 usage, 3 a gate failed (one `GATE FAIL <step>: <reason> (log: ...)` line), 4 a tool crashed or a gate line /
  output file is missing (`ERROR <step>: ...`). Both stops also append `STOP <Clip> <clipname> step <step> <reason>` to
  `<project>/PIPELINE.log`, so the ledger keeper sees failed attempts. Only a clean run appends the `CLIP` line.
- `--from <step>` restarts; earlier results come from `work/<clipname>/pipeline.state` (written after each step), else from
  `check.json` / `report.json` (video2rig's own files), else the fields show `n/a`. After `import` the newest
  `<Clip>_v2r_v<N>.blend` is used; `import` itself always writes the next number (never overwrites).
- Blender: `ps -axo comm=` counts real Blender processes (not the reader's python, whose arguments mention Blender); waits while
  4 run (2 when an UnrealEditor runs), up to 2 h, then errors out. Always `--background --factory-startup`.
- `--fork-dir` is the cwd of `python -m video2rig`; python defaults to `<fork-dir>/.venv/bin/python`, else
  `~/video2rig/.venv/bin/python` (the brute-air checkout has no `.venv`). Pass-through args: `--run-args`, `--refine-args`
  (for example `--floor=-0.43` for an old clip), `--export-args`.

## What was proven, and how

Reproduce everything: `tools/brute/v2r/test_run_clip.sh` (needs `work-tools/fake_fit/Idle_fit.blend` and
`model_aligned_copy.blend` from `test_refine_export.sh`; work dir `~/hulk/Local/video2rig/work-tools/`, gitignored; transcript
of the last run `work-tools/test_run_clip.out`). `make_test_npz.py` turns the synthetic Idle fit into a motion `.npz` in video2rig's
`out/<clip>.npz` format, so `import_motion.py` really runs. Steps 1-3 run against a stub of `python -m video2rig` that prints
the formats copied from the source; everything else is the real tools.

| Step | Status | Evidence |
| --- | --- | --- |
| parsers (check, run, refine, export, size) | **parser-only, on sample strings** (`run_clip.sh --selftest`, 22 assertions) | formats copied from `__main__.py`, `check.py`, `reader/fit.py`, `report.py`, `refine_brute.py`, `export_clip.py`, `size_gate.py`. Cases: OK, WARN, FAIL 1.82, tool says OK but 1.55 (FAIL), exactly 1.50 (PASS), `body None`, `5e-05`, unreadable clip, report with 0 / 2 warnings, one-view `report.json`, older-road log (n/a), `foot_drift_mm n/a`, negative toe, `EXPORT_GATE nan ... FAIL (rig mismatch)`, size PASS/FAIL. A deliberately wrong expectation made the selftest fail, so the asserts bite. |
| 0 size | **live** on real clips | `idle_v1` PASS scale 1.04; `jump_v2` FAIL (top edge, scale 1.13) stops with exit 3 and the reason; air project `fall_v1` with `--fork-dir ~/video2rig-brute-air` PASS 1.05 |
| 1 check | **chaining against the stub; the real tool only for its error path** | stub prints check.py's exact line format. FAIL 1.82 % stops (exit 3), unreadable result stops (exit 4), WARN continues. The real `video2rig check` was run on a symlinked project with no reader: its message (`no reader for ...: run python -m video2rig.reader.prepare first`) is reported as `ERROR check` (exit 4). Real result line untested until the reader exists. |
| 2 run | **stub + parser** | stub prints fit.py's `median keypoint miss` line and `__main__.py`'s `[ 39.0s] report {..}` line with report.py's keys; fit 5.20 px over 4 gave the WARN and the run continued, 2 warnings printed, outline `0.953/0.947`. The `reader.pt` preflight is proven (stops, exit 4). The real `run` was never executed. |
| 3 review | **stub** | stub writes `work/<clip>/review.mp4` (a shipped clip stands in for the film); the existence check is proven. Real `review` untested. |
| 4 import | **live** | real `import_motion.py` on a copy of the aligned `model.blend` with the synthetic npz: `IMPORT_MOTION idle_test: 156 keys, 124.0 frames at 24 fps`, `Idle_v2r_v1.blend`; a second import wrote `_v2.blend` |
| 5 refine | **live** | `REFINE_GATE Idle seam 1.18 foot_drift_mm 3.6 toe_min_mm 0.0 peakhand_L 21 peakhand_R 153`, identical to TESTS-refine-export.md section 3 (here the fit goes npz -> import_motion -> refine, not the direct synthetic .blend) |
| 6 export | **live** | `EXPORT_GATE Idle max_vertex_delta_mm 0.0029 frames 5 PASS`, glb `Brute_v2r_idle.glb`; `--export-args "--gate-mm 0.0001"` gave `GATE FAIL export` (exit 3) and a STOP line |
| 7 sheet | **live** | ffmpeg 4x4 sheet of the stand-in film (192 frames, every 12th, 1920 px wide; viewed: 16 tiles of a 5-panel film). A real review film goes through the same filter. |
| 8 log | **live** | line below; `--from log` re-prints it from `pipeline.state`; with the state file removed the video2rig fields show `n/a` instead of failing |
| restarts | **live** | `--from refine`, `--from log`, `--from import --to import`, `--from refine --to refine` (takes the newest number) |

PIPELINE.log line of the test (check, fit, warn and outline come from the stub; refine and export are real):

```
CLIP Idle idle_test check 1.21 PASS fit 5.20 warn 2 outline 0.953/0.947 refine 1.18 3.6 0.0 export 0.0029 PASS blend /Users/midir/hulk/Local/video2rig/work-tools/proj_test/Idle_v2r_v1_refined.blend glb /Users/midir/hulk/Local/video2rig/work-tools/proj_test/motion-out/Brute_v2r_idle.glb
```

The whole chain with the stub takes about 12 s.

## Not verified (needs the reader)

- Real `video2rig check` / `run` / `review` output on a Brute clip: the parsers match the formats printed in the source, but no
  real reader-road run exists yet. On the first real clip, look at: that the `report` line is printed (it is, in the reader branch
  of `__main__.py`) and that `outline_match` has the two view names; that `check` prints only one `OK|WARN|FAIL <clip>: body` line
  (the parser takes the last).
- A real fit keys only the fitted bones, at 24/25 fps video times; `refine_brute.py` and `export_clip.py` were written for that
  (TESTS-refine-export.md, "Not verified").
- `size` runs under `<fork-dir>/.venv/bin/python` with `V2R_HOME=<fork-dir>`; proven with `~/video2rig` and with `~/video2rig-brute-air`
  (with the `~/video2rig` python).
- `--run-args --old` (older road) is not supported by design: the run step stops at the missing fit-px line.

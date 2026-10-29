Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

# Brute video2rig upgrade: clip LEDGER

Companion to [PLAN.md](PLAN.md). Every reader, clip, check, fit, refine, A/B verdict and dollar goes in here. Branch `chinese-animation-upgrades`, checkout `~/hulk`. Created 2026-10-29 (Phase 0 bookkeeping). Spend rule (owner, 2026-10-29): fal balance first, then Higgsfield MiniMax H3 Max; one paid clip at a time.

## Clip ledger

| clip | take | date | provider | model | res | seconds | cost | check % (body/limbs) | size gate | fit median px | fit warnings | refine (seam x, foot drift px) | A/B verdict | shipped? | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Idle | v1 | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| Walk | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 6 | 0.36 | - | PASS 1.23 | - | - | - | - | - | In place, six steps, panels in phase, returns to stance, nothing drawn. |
| Run | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 6 | 0.36 | - | PASS 1.25 | - | - | - | - | - | Runs in place, strides read, panels in phase, ends in stance, nothing drawn. |
| StopLunge | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.25 | - | - | - | - | - | FAIL visual: motion blur on fists in run-in, feet off floor mid-stride. |
| StopLunge | v2 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.26 | - | - | - | - | - | FAIL visual: sharp now, but never rises; ends in deep crouch. Two failures, old clip kept. |
| PunchL | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.25 | - | - | - | - | - | Left fist, correct hand; slow jab held ~2 s; returns to stance; clean. |
| PunchR | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.24 | - | - | - | - | - | FAIL visual: body twists ~120 deg, panels disagree, arm across face, fist smeared. |
| PunchR | v2 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.22 | - | - | - | - | - | PASS visual: right straight, sharp fist, big torso twist, returns to stance. |
| Slap | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.19 | - | - | - | - | - | Left open palm sweeps wide and across chest, returns to stance; clean. |
| Clap | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.10 | - | - | - | - | - | Arms spread, palms meet at chest, parts, returns to stance; clean, in frame. |
| Smash | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.09 | - | - | - | - | - | Fists overhead, slam to floor, crouch, rise, stance; clean floor, slight slam smear. |
| Uppercut | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.19 | - | - | - | - | - | Right fist rises overhead, held ~2 s, no real hop; returns to stance; clean. |
| Lift | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 6 | 0.36 | - | PASS 1.07 | - | - | - | - | - | Squat, empty-air overhead hold, lowers to stance; no car or object drawn. |
| Throw | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.21 | - | - | - | - | - | Overhead hold, arch, step and hurl, follow-through, stance; no object drawn. |
| Jump | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.15 (top-edge WARN) | - | - | - | - | - | FAIL visual: rises ~1.5 m, long hang, hand leaves top of frame. |
| Jump | v2 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | FAIL (hand leaves top edge, 30 frames) | - | - | - | - | - | FAIL: hands cut off at top, ~1.5 s hang. Two failures, old clip kept. |
| Land | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.12 | - | - | - | - | - | Small hop, heavy one-knee crouch, hold, rises to stance; clean. |
| Fall | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.05 | - | - | - | - | - | PASS visual (brute-air): constant height, no floor, subtle limb drift, loops to first frame. |
| WallAttach | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.23 | - | - | - | - | - | FAIL visual: drifts sideways ~2 body widths to panel edges, feet shuffle; no wall drawn. |
| WallAttach | v2 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.15 | - | - | - | - | - | PASS visual: stays put, panels agree, both fists push forward, no wall drawn. |
| WallClimb | v1 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.16 (top-edge WARN) | - | - | - | - | - | FAIL visual: reaching hand fingers cut by top of frame; no wall drawn. |
| WallClimb | v2 | 2026-10-29 | fal | minimax/h3/image-to-video | 768P | 5 | 0.30 | - | PASS 1.12 | - | - | - | - | - | PASS visual: hands inside frame, hangs off floor, weak hand-over-hand, no wall drawn. |

## Spend

| provider | balance before | balance after | total |
| --- | --- | --- | --- |
| fal | 23.65 (before Idle pilot) | about 16.69 (derived: 23.17 before walk_v1 minus 6.48 for the batch incl. Fall; the clips json balance_after field lags a clip) | 6.96 USD (Idle 0.48 + batch 6.48) |
| Higgsfield | ? | ? | ? |

## Gate lines

### Phase 0 environment (2026-10-29)

Checked by Haiku 5.5 (high) with the commands shown. No spend, no renderer launched, `~/.config/fal/secrets.env` not read.

- **Host and CPU**: `hostname; sysctl -n machdep.cpu.brand_string` gives `Mac` and `Apple M3 Ultra`.
- **Blender**: `/Applications/Blender.app/Contents/MacOS/Blender --version | head -1` gives `Blender 5.2.0 LTS`.
- **video2rig fork**: `git -C ~/video2rig log -1 --oneline` gives `ec99e23 creature.json limbs: explicit leg chains and feet for rigs that branch at the ends`; `git -C ~/video2rig branch --show-current` gives `mac-mps`.
- **torch and MPS**: `~/video2rig/.venv/bin/python -c "import torch;print(torch.__version__, torch.backends.mps.is_available())"` gives `2.14.1 True`.
- **ffmpeg**: `/opt/homebrew/bin/ffmpeg` (`ffmpeg version 8.1.2`).
- **Unreal path**: `ls "/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"` lists the binary (exists).
- **APFS free**: `diskutil info /System/Volumes/Data | grep "Container Free"` gives `78.6 GB (78590189568 Bytes)`. PLAN.md's Machine row says 17.5 GB; the live value is newer and higher, so the PLAN figure is stale.
- **STREAMING flag**: `ls ~/.cache/gpu-slot/STREAMING` reports no such file (absent).
- **Engine processes**: 0 Blender or UnrealEditor renderer processes. A grep for `MacOS/Blender|UnrealEditor` matches one line (pid 64538), only because that reader's argument names the Blender path.
- **video2rig reader processes** (none are ours; we have not started a reader). Command `ps -axo pid,etime,command | grep -E "MacOS/Blender|UnrealEditor|video2rig.reader" | grep -v grep`, each line cut to 120 characters:

```
27311    01:12:50 /opt/homebrew/Cellar/python@3.12/3.12.13/Frameworks/Python.framework/Versions/3.12/Resources/Python.ap
27313    01:12:50 /opt/homebrew/Cellar/python@3.12/3.12.13/Frameworks/Python.framework/Versions/3.12/Resources/Python.ap
64538    02:42:49 /opt/homebrew/Cellar/python@3.12/3.12.13/Frameworks/Python.framework/Versions/3.12/Resources/Python.ap
66705    02:40:36 /opt/homebrew/Cellar/python@3.12/3.12.13/Frameworks/Python.framework/Versions/3.12/Resources/Python.ap
77726       15:02 /opt/homebrew/Cellar/python@3.12/3.12.13/Frameworks/Python.framework/Versions/3.12/Resources/Python.ap
77731       15:01 /opt/homebrew/Cellar/python@3.12/3.12.13/Frameworks/Python.framework/Versions/3.12/Resources/Python.ap
```

  Identified from full argument lines and `lsof` working directories:
  - pids 27311 and 27313: `video2rig.reader.prepare --blend .../Markhor-Meadow-M3-2026-10-10/.../mayor/v2r/mayor_mine` and its `train`; cwd `~/video2rig`.
  - pids 77726 and 77731: the same pipeline on `.../mayor/v2r/mayor_chop`; cwd `~/video2rig`.
  - pids 64538 and 66705: `video2rig.reader.prepare video2rig/dragon-air` and its `train`; cwd `~/video2rig-air`.
  - Three reader pipelines (six processes). PLAN.md says two other readers; the live count is three. Owners not verified. Do not touch.
- **hulk checkout**: `git -C ~/hulk log -1 --oneline` gives `5a415aa Plan: spend rule = use fal balance fully, then Higgsfield; no per-clip stop`; `git -C ~/hulk branch --show-current` gives `chinese-animation-upgrades`.
- **Clip inventory** from `~/hulk-scratch/brute_v5/clips_meta.json` (17 clips, mtime 2026-10-18 19:03). `wall_fwd` is 0.779 on both WallAttach and WallClimb.

| clip | loop | dur (s) | speed | src |
| --- | --- | --- | --- | --- |
| Idle | yes | 5.167 | 0.001 | Emerald_Behemoth_idle_30fps.glb |
| Walk | yes | 6.0 | 0.609 | Emerald_Behemoth_walk2_30fps.glb |
| Run | yes | 6.0 | 2.15 | Emerald_Behemoth_run_30fps.glb |
| StopLunge | no | 2.833 | 1.043 | Emerald_Behemoth_stoplunge_30fps.glb |
| Jump | no | 5.0 | 0.016 | Emerald_Behemoth_jump_30fps.glb |
| WallAttach | no | 5.0 | 0.058 | Emerald_Behemoth_attach_30fps.glb |
| WallClimb | yes | 5.0 | 0.058 | Emerald_Behemoth_attach_30fps.glb |
| PunchL | no | 1.533 | 0.029 | Brute_punchl.glb |
| PunchR | no | 1.533 | 0.029 | Brute_punchr.glb |
| Slap | no | 2.467 | 0.012 | Brute_slap.glb |
| Clap | no | 1.567 | 0.0 | Brute_clap.glb |
| Smash | no | 2.967 | 0.003 | Brute_smash.glb |
| Lift | no | 3.0 | 0.004 | Brute_liftthrow.glb |
| Throw | no | 1.467 | 0.107 | Brute_throw.glb |
| Uppercut | no | 2.467 | 0.014 | Brute_uppercut.glb |
| Fall | yes | 1.967 | 0.005 | Brute_fall.glb |
| Land | no | 2.967 | 0.011 | Brute_land.glb |

### In-game A/B: OLD baseline capture set (2026-10-29 03:45 EDT)

- `ab_ingame.py run --label old --extra=-WHBruteNoClipTiming` (one capture at a time via gpu_slot, no STREAMING flag seen).
- `check --label old`: ok 14/24 — idle front/left/tq, loco front/left/tq, lunge front/left/tq, jump front/left/tq, combat front/left.
- MISSING 10/24: combat_tq (engine hung at start: ensure `OriginX <= OriginMax` in the distance-field scene update, rc=124,
  no WH_BRUTE lines; the UnrealEditor stayed in macOS state `?E` for 25+ min after SIGTERM) plus uppercut x3, grab x3, wall x3
  (not launched: never launch while an engine is stuck exiting).
- ~2.5 min per capture with the GPU at 100 % from other sessions' work (64 min wall for 15 launches incl. the hang).
- Captures: ~/hulk-scratch/ab-ingame/old/<case>/ (104 MB). Contact sheets angles_idle.png, angles_combat.png: three angles
  differ, camYawOff active. Caveat for the critic: combat_front has him partly cut off at the bottom edge by a car and the
  low camera; HUD help text and the damage counter are burned into every capture (same for old and new, so blind-fair).
- 03:15-03:17 the whole GPU wedged (three MPS readers blocked in waitUntilCompleted, a fresh MPS matmul hung, ioreg 100 %
  util / recoveryCount 0, WindowServer + loginwindow reset 03:28:37). Last launches before it: this task's capture engine +
  a second engine (singapore source-world-r3, 03:14) + three MPS trainers. Owner pinged; Studio rebooted 10:16 EDT.
- Ground reader lost its run (no checkpoints before the end): relaunched 10:37 with --keep, 9000 steps from 0.
- Remaining 10 OLD cases rerun after the reboot; a second combat_tq hang = that case is dropped from both sets.

### Timing data to re-measure (before values, 2026-10-29)

Integration phase (PLAN Phase 5) replaces these with values measured from the new clips. Copied verbatim with line numbers.

`unreal/WebHomage/Source/WebHomage/Brute/BruteCharacter.cpp`, per-act `C.From / C.To / C.Rate / C.Hit` (`ABruteCharacter::ActClip`, starting at the `case EBruteAct::` near line 1627):

```
1627: 	case EBruteAct::Punch: C.Clip = (Combo % 2 == 0) ? CPunchR : CPunchL; C.From = 0.45f; C.To = 1.40f; C.Rate = 1.6f; C.Hit = 1.0f; break;
1628: 	case EBruteAct::Slap: C.Clip = CSlap; C.From = 0.30f; C.To = 1.70f; C.Rate = 1.5f; C.Hit = 0.90f; break;
1629: 	case EBruteAct::Clap: C.Clip = CClap; C.From = 0.10f; C.To = 1.30f; C.Rate = 1.3f; C.Hit = 0.70f; break;
1630: 	case EBruteAct::Smash: C.Clip = CSmash; C.From = 0.40f; C.To = 2.00f; C.Rate = 1.4f; C.Hit = 1.17f; break;
1631: 	case EBruteAct::Uppercut: C.Clip = CUppercut; C.From = 0.15f; C.To = 1.40f; C.Rate = 1.4f; C.Hit = 0.60f; break;
1632: 	case EBruteAct::Grab: C.Clip = CLift; C.From = 0.60f; C.To = 2.40f; C.Rate = 2.0f; C.Hit = 2.40f; break;
1633: 	case EBruteAct::Carry: C.Clip = CLift; C.From = 2.40f; C.To = 2.95f; C.Rate = 0.f; break;
1634: 	case EBruteAct::Throw: C.Clip = CThrow; C.From = 0.00f; C.To = 1.46f; C.Rate = 1.25f; C.Hit = 0.45f; break;   // incl. the heavy recovery
```

Also used: line 666 (`ActHitAt` and `ActDur` derive from `C.Hit`, `C.From`, `C.To`, `C.Rate`) and line 1637 (`C.To` clamps to the clip's `GetPlayLength()`).

`tools/brute/assemble_motion.py`, `HIT` / `TRIM` / `LOOP_WIN` (and the empty `FOOTLOCK` table):

```
29: TRIM = {'PunchL': (0, 46), 'PunchR': (0, 46), 'Lift': (19, 109)}
30: # contact moment (seconds from the clip start, after TRIM): fist / palm / ground contact, measured from hand telemetry
31: HIT = {'PunchL': 1.0, 'PunchR': 1.0, 'Slap': 0.9, 'Clap': 0.7, 'Smash': 1.17, 'Uppercut': 0.6, 'Throw': 0.45, 'Land': 0.5}
32: # 2026-10-17 foot lock (anim_lib.plant_targets kwargs) for the generated one-shots; locomotion / air / wall clips are left alone
33: FOOTLOCK = {n: {} for n in ('PunchL', 'PunchR', 'Slap', 'Clap', 'Smash', 'Lift', 'Throw', 'Uppercut', 'Land')}
34: # loops re-cut at the best-matching end frame within the last N frames (WallClimb keeps its old blend: the game loops a segment)
35: LOOP_WIN = {'Idle': 60, 'Walk': 40, 'Run': 40, 'Fall': 20}
```

- 2026-10-29 Phase 3 generation batch (reader still training; director decision 01:45: clips are independent of the reader, generated ahead to compress the night). Sonnet 5.5 high, one clip at a time, each reviewed on its sheet before the next. 20 takes, 6.18 USD. Size gate PASS on all but Jump v2 (top edge). Visual failures the gate missed: StopLunge v1 (motion blur), PunchR v1 (twist, arm across face), WallAttach v1 (drift). Two failures, old clip kept: StopLunge, Jump. Sheets in `Local/video2rig/brute-aligned/work/<clip>/sheet.jpg`, gate output beside them.

# Brute — rolling handoff (updated 2026-10-15 ~02:05 local, overnight loop 1)

Owner direction 2026-10-15: replace all of Spider-Man with a big green Hulk-like character; no swinging — he stomps, jumps and
leaps. Owner "go" (then asleep, full permissions, "don't interrupt other sessions", "use the Customuse API/MCP for assets"):
**jumping, launching, hitting, slapping, thunderclap, picking cars up to throw them, HUGE jumps and grand slam.**

Read `docs/brute/BRIEF.md` (design), `docs/brute/RESULTS.md` (what loop 1 delivered, with stills), `docs/brute/MOVESET.md`
(controls + numbers), `docs/brute/ASSETS.md` (Customuse provenance + asset pipeline).

## State (verified on the Studio, checkout `/Users/midir/hulk`, branch `brute`, pushed)

- Brute is the default pawn on every map using `AWebTravGameMode` (Manhattan, Manhattan_Island showcase, ...). `-WHSpidey` restores
  the web-swinger (code untouched otherwise).
- Moves working in the real game (telemetry + stills in RESULTS.md): walk/run/sprint (knocks cars), hop, charged super jump
  (40 m / 100 m; running 46 m / 115 m), leap chain (to 52 m / 128 m), air dash x2, wall run + top-out + wall kick, crater landings,
  grand slam dive, punch-punch-slap, launcher uppercut (sprint + attack), ground grand slam, thunderclap, grab car overhead + throw. Impacts throw traffic cars as physics
  props, knock pedestrians over and make the crowd flee; traffic bounces off a standing Brute; HUD collateral counter + charge meter
  + controls card. Camera: speed FOV, trauma shake, air tilt toward the landing, keeps out of facades and tree crowns.
- Body: Customuse model (one paid generation, 100 credits) cut into 11 rigid parts on a procedural rig.
- Verified on Manhattan (midtown), Manhattan_Island day + night (owner map, Times Square start, playable profile); a 44 s stress
  case chaining every move ran without errors (`tools/brute/cases/m11_stress.json`). The one `precision loss` ensure in the log
  is pre-existing (also in the Spider-Man baseline smoke run).
- Owner launcher: `./Play-Brute.command` (guarded launcher, Manhattan_Island, Times Square start, 1080p window, 60 fps cap).
  **Not launched by this session** (owner launches it).

## Content on this machine (git-ignored)

- `unreal/WebHomage/Content/` = read-only rsync copy of `/Users/midir/spider-man-2/unreal/WebHomage/Content` (same source commit
  `0ca553f`, 2.9 GB) instead of the multi-hour rebuild. The full rebuild (`build_manhattan.py`) was started first and stopped at
  `city_prep/gen_shaders` on missing donor inputs; fixed so far: `~/spiderbench` cloned at the pinned `64d957f` (+ npm install),
  night lights exported to `~/hulk-scratch/night/export/night_lights.json` (pass `SM2_NIGHT_JSON` when rebuilding). Still missing
  for a from-scratch rebuild: P2 character `ueimport` inputs, terrain export, night ref shots (all historically under
  `~/sm2-n1/_scratch`, which no longer has them). Not needed while the copied Content is used.
- `Content/Brute/{Parts,Fx}` from `python3 unreal/WebHomage/Scripts/build_brute.py` (inputs in `~/hulk-scratch/brute_parts`,
  `~/hulk-scratch/brute_fx`; regenerate with `tools/brute/segment_brute.py` / `make_fx_meshes.py` from the Customuse GLB).

## Next steps (loop 2), in order

1. **Independent critic pass** on the loop-1 captures (`~/hulk-scratch/cap/*`, regenerate with `tools/brute/capture.sh <case>`):
   not done — this session ran without subagents. Builder self-review is in RESULTS.md.
2. Owner playtest via `Play-Brute.command`; turn feedback into stories.
3. Milestone 3: destructible facade proxies on one district, collateral counter already wired (`BruteWorld::Collateral()`).
4. Milestone 4: cops / SWAT enemies for the melee kit (hits currently affect cars / props / pedestrians only).
5. Polish: occlusion fade for trees/awnings, stronger thunderclap read, skinned body (rigid seams), diagonal wall runs.
6. Perf: desktop-session launch (`open -n -W -a`) under the exclusive perf lock; not measured yet.

## House rules that bit before (do not relearn)

- Shared GPU coordinator `~/.cache/gpu-slot`, hard cap 2 engines; every launch via `tools/gpu/gpu_slot.sh` (capture.sh does it).
  Kill ONLY exact PIDs this task started. Another session (Invincible / Hollow Current) runs engines in parallel — leave them be.
- Captures need `-benchmark -fps=N` (capture.sh adds it): without it the game clock and the script clock drift apart.
- Commandlets exit 1 on the engine's own error summary (GameFeatureData warning): judge by the `SM2_BUILD_OK` sentinel.
- Perf numbers only from a desktop-session launch, never SSH/offscreen.
- Logs `~/hulk-logs/`, scratch `~/hulk-scratch/` (disposable). Customuse via `codex exec` (Codex Apps connector `customuse`).

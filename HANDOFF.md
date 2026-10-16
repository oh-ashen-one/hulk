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

## Next steps

1. Owner playtest via `./Play-Brute.command`; turn feedback into fixes.
   - **BUG (owner 2026-10-16, backlog): got stuck inside a building** after landing on / hitting a roof. Log copy
     `~/hulk-logs/play-brute-stuck-20261016.log`: last events `super_jump` at (-310.8 -115.6 0.2) then `air_wall_smash` at
     (-304.8 -115.6 9.1) moving +X at 26 m/s, then nothing — he ended up inside the facade. Likely causes: `StepAir` push-out
     only bounces the velocity (no depenetration check after the 120 Hz substep at 26-60 m/s), and `PushOutCapsule` can resolve to
     the inside of a box. Fix: after every air/ground step, if the capsule centre is inside a building box, push to the nearest
     face (or the roof top); plus an "unstuck" watchdog (no progress for 1.5 s while inside geometry -> teleport to `LastSafe` or the
     roof) and a manual key (e.g. hold R 1 s = respawn at last safe street spot). Reproduce with a scripted case from that spawn.
2. Combat clips: punches/clap/smash/grab/throw are still procedural arm overlays on the new body — generate real clips (Meshy
   preset library has punches) if the owner wants them.
3. No falling/landing clip: air uses the jump's arms-up hold. Generate JumpAir/Land if needed.
4. Independent critic pass, Manhattan_Island check, desktop fps measurement.

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

# Brute animation upgrade via video2rig + MiniMax (fal.ai) — PLAN (not started)

Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

Written 2026-10-29 by Claude Fable 5.1 (director). Branch `chinese-animation-upgrades`, checkout `~/hulk` (released to this task by the owner 2026-10-29; the earlier
worktree was removed). Status: **ready; owner go pending (via a /goal the owner will have me write).**

## Owner instruction (2026-10-29)

Re-animate and enhance **all** existing Brute clips with the shared brain's `boss-fight-blueprint` creature route
(video2rig: first-frame AI video of our own rig, joint reader, per-frame fit, Blender Action). Video provider:
**MiniMax H3 at 768p through the fal.ai API** (key at `~/.config/fal/secrets.env`, `FAL_KEY`; never printed, never
committed). Use subagents: Opus 5.5, Sonnet 5.5 and Haiku 5.5 as needed.

Rule reconciliation, recorded so nobody re-litigates it:
- `animation-sourcing` keeps humanoids source-first; the owner's instruction above is the explicit per-task exception
  for the Brute (same creature exception the dragon got on 2026-10-28).
- `operating-rules` forbids MiniMax for animation "unless the user explicitly overrides": overridden here, explicitly.
- Paid generation stays **one clip at a time, reviewed before the next** (owner rule; also the blueprint's rule).
  Subagents never fan out paid generations.

## What exists today (measured, not assumed)

| Item | Fact |
| --- | --- |
| Clips in game (17) | Idle, Walk, Run, StopLunge, Jump, WallAttach, WallClimb (= WallAttach segment looped), PunchL, PunchR, Slap, Clap, Smash, Lift, Throw, Uppercut, Fall, Land |
| Sources | 6 Cartwheel text-to-motion (Customuse), 10 Meshy text-to-motion retargeted, hand splices (Clap, Throw) |
| Rig | 52 bones, Mixamo names (`Hips, LeftUpLeg, LeftLeg, LeftFoot, LeftToeBase, Spine..Spine2, LeftShoulder, LeftArm, LeftForeArm, LeftHand` + 15 finger bones per hand, `Neck, Head`), 18 corrective morphs; mesh `~/hulk-scratch/brute_corr/brute_rigged_corr.glb` (first arg of assemble_motion) |
| Into the game | per-clip motion files -> `tools/brute/assemble_motion.py` (matches files by keyword) -> `brute_anim.fbx` -> `unreal/WebHomage/Scripts/build_brute.py` (headless commandlet through `gpu_slot`) -> `A_Brute_<Clip>` -> `ABruteCharacter::AnimateClips` |
| Timing data that must move with the clips | `HIT` / `TRIM` / `LOOP_WIN` / `FOOTLOCK` tables in assemble_motion.py; `C.From / C.To / C.Rate / C.Hit` per act in `BruteCharacter.cpp` ~1627-1634; speed matching from `clips_meta.json`; segment markers from `tools/brute/analyze_clips.py` |
| video2rig | fork `~/video2rig` branch `mac-mps`, own `.venv`; `generate.py` is BytePlus/Seedance only (no fal provider yet); Mixamo hinge names are auto-detected, so `creature.json` is near-empty |
| Dragon precedent | reader 9000 steps = ~3 h on MPS; clip -> Action ~4 min; good fit = median miss 2-4 px, two-view check < 1.5 %; MiniMax oversized a winged creature (size gate needed); airborne moves need their own start picture + reader; a raw fit is a base, never a deliverable (refine script closes loops, plants feet) |
| Machine | Mac Studio M3 Ultra. Two other video2rig readers are training on the GPU tonight (Markhor mayor, dragon air): our reader runs 2-3x slower alongside them (owner accepted). Blender cap 4 minus others' instances, 2 total when an Unreal commandlet runs. APFS container free 17.5 GB (Finder shows more because of purgeable space): owner accepted the risk; keep `work/` renders trimmed, delete capture movies after measuring. `STREAMING` flag absent now; owner streams 11:00-13:00 ET (no captures then) |

## Unverified items that gate step 0

1. **fal.ai model id: VERIFIED 2026-10-29** with the key (read-only catalog query): `minimax/h3/image-to-video`
   (no `fal-ai/` prefix), inputs `prompt`, `image_url` (first frame), `resolution` enum 480P/768P/2K/4K (use 768P),
   `duration` (int seconds, default 5), `prompt_expansion_mode` (set `disabled`: we want the literal prompt), `seed`.
2. **Price per second on fal** is not in the OpenAPI spec: read the real charge after the pilot clip and write it into
   the ledger. Owner 2026-10-29: no per-clip stop; the fal balance (about $20) is to be used in full, then switch to
   Higgsfield MiniMax H3 Max and keep going.
3. **`fal_client` is not installed** anywhere. Plan: plain `urllib` against `https://queue.fal.run/<model>` (submit,
   poll, fetch) so the fork gains no dependency; the start frame is sent as a base64 data URI.

## Architecture of the work

```
~/hulk/Local/video2rig/brute/          (gitignored; Local/ added to .gitignore on this branch)
  creature.json   rig/   start/ (ground)   start-air/   start-wall/   reader/   reader-air/   clips/   work/   out/
  refine/         (Brute refine scripts; ported from the dragon's refine/lib_anim.py, committed copy in tools/brute/v2r/)
docs/brute/video2rig/   PLAN.md (this)  LEDGER.md (every clip: provider, model, res, seconds, USD, check %, fit px, verdict)
                        prompts/<clip>.txt (committed; text only)
tools/brute/v2r/        generate_fal.py  size_gate.py  refine_brute.py  export_clip.py  ab_render.py  (committed)
```

Clip naming: `<Clip>_v2r_v1`, regenerations bump the suffix. Old clips are never deleted: assemble_motion keeps
matching the old file unless the new one wins its A/B, so the game can ship a mix (keep-the-best per clip).

## Phases

### Phase 0 — Gates and setup (no spend, ~1 h wall)
- [Haiku 5.5 high] Verify fal model id + price (read-only API call), fal account balance if exposed, `ffmpeg`, fork
  `.venv` health, disk free, GPU slot + Blender count, STREAMING flag. Write `LEDGER.md` header with the price.
- [Sonnet 5.5 high] Build the project: `creature.json` (`root_bone: Hips`, `facing` measured from the mesh, not
  assumed: the bind pose is turned 77 deg vs the clips; `fit_bones: auto` so weightless finger stubs drop out),
  `export_rig.py`, `render_start.py` from the **idle stance** (Idle frame 0 posed onto the rig, so every clip starts
  and returns to the shipped stance; front | side; margins wide enough for Smash/Clap arm reach and the Jump crouch).
  Dry-run `twins` and `limbs` and paste both outputs into the ledger.
- [Opus 5.5 high] `generate_fal.py`: queue submit / poll / resume with the task id saved the moment fal accepts it
  (same contract as the fork's `generate.py`), prompt file + the mandatory no-effects sentence appended, 768p,
  duration flag, cost estimate printed and refused over a per-run USD cap read from an env var (default 2.00 per clip).
  Also `size_gate.py` (silhouette width + reach at the peak frame vs the start picture; reject over 1.3x) because
  `check` only measures panel agreement. Unit-test both against the dragon's existing clips (free).
- Owner go/no-go on the exact model + price before Phase 1.

### Phase 1 — Ground reader (~3 h MPS, unattended, no spend)
- [Sonnet 5.5 high] `python -m video2rig.reader.prepare brute --blend model.blend --steps 9000`. Never judge it before
  9000 steps (dragon: 300 steps read 13 px, 9000 read 4 px). Record held-out px front/side. Target < 4 px.
- Runs headless under `taskpolicy -b`; one Blender for the pose renders; counts against the Blender cap.
- While it trains: [Sonnet] write all 17 prompts (`docs/brute/video2rig/prompts/`), each: the brute as the picture
  shows him, both panels one moment, static cameras, the move in numbered beats, how each view ENDS (back in the
  stance for one-shots; same pose as frame 0 for loops), whole body in frame, the no-effects sentence. Fable reviews
  every prompt before it is spent.

### Phase 2 — Pilot clip (first spend, one clip)
- Idle first (loop; cheapest to judge; matches the dragon's first clip). Generate 1 clip, `check` (< 1.5 %),
  `size_gate` (< 1.3x), `run` (median miss < 4 px, no warnings), `review` film, `import_motion.py` -> Action.
- [Opus 5.5 high] `refine_brute.py` v1 on this clip: trim still tail, close the loop (crossfade 12-24 f), IK-plant
  feet while grounded, smooth flicks, re-apply the in-game `MenaceW` posture layer expectation (keep the head neutral
  enough for the game's overlay). Budget 10 min of script per move, never hand keys.
- `export_clip.py` writes the Action to the file name assemble_motion expects, `assemble_motion.py` builds a test
  `brute_v6` with only Idle swapped, `build_brute.py` imports, `tools/brute/capture.sh` films front/side/three-quarter.
- [Opus 5.5 high, opus-critic] Blind A/B: old Idle vs new Idle, identical renders, random labels, numbers first
  (seam ratio, foot drift px, secondary-motion ratio), score second. **Owner looks at the pilot before any batch.**

### Phase 3 — Ground move set (13 clips, one at a time)
Order by value and risk: Walk, Run (loops with stride: measure `speed` for clips_meta, feet slide at sprint by design),
StopLunge, PunchL, PunchR, Slap, Clap, Smash, Uppercut, Lift, Throw, Jump (charge crouch + launch only; the apex hold
stays scrubbed by the game), Land (ground start is fine: it ends in the stance and the game plays from 0.35 s).
Per clip, the same loop as Phase 2. A clip failing `check`/size gate is regenerated with a prompt fix, never fitted;
two failures on one move = keep the old clip, log it, move on (never a third blind retry).
Parallelism: generation serial (owner rule); fit/refine/render of clip N runs while clip N+1 generates (Sonnet
workers, Blender cap respected); Haiku keeps the ledger and extracts every gate line.
Props: Lift/Throw need a car. Prompt rule from VIDEO.md: one rigid object, lies still until lifted; or generate the
lift with an invisible load and keep the existing hand-splice for the car. Decide at prompt review.

### Phase 4 — Airborne and wall clips (own start pictures)
- Fall and Jump-air: hover start picture (`start-air/`), **second reader (~3 h)**; dragon finding: a ground reader
  assumes feet on a floor and airborne clips failed the check until a flying start picture existed.
- WallAttach / WallClimb: wall start picture with a plain slab in frame; riskiest, done last; if two generations fail
  the check, the existing Cartwheel attach clip stays and the gap is reported.
- Each still goes through check, size gate, fit, refine, A/B.

### Provider fallback (owner, 2026-10-29)
If MiniMax on fal runs out (credits exhausted, sustained API failure, or H3 withdrawn), fall back to **MiniMax H3 Max
on Higgsfield** (the Higgs MCP, `start_image` role, 768p, 16:9, 5 s) exactly as the dragon did; record the switch and
its credits in the ledger. A per-move quality failure is NOT a provider switch: two failed generations keep the old clip.

### Phase 5 — Integration and gates
- [Opus 5.5 high] C++ pass: re-measure every `C.From / C.To / C.Hit` and the `HIT` table from the NEW clips with
  `analyze_clips.py` (contact = hand speed peak, not the old numbers), loop windows, clips_meta speeds, corrective
  morph behaviour on the new arm arcs (`mesh_corrective_check.py`), `-WHBruteV2Old` style flag to switch the whole
  old set back for A/B in the real game.
- Captures via `capture.sh` for v2_loco, combat cases, m3_wallrun (-movie), outside the stream window.
- [opus-critic] Final blind A/B of the full set in-game, old vs new, per clip; a clip ships only if it wins or ties.
- Gate lines in HANDOFF: reader px, per-clip check %, fit px, seam, foot drift, A/B score, USD.

### Phase 6 — Handoff, brain, cleanup
- `HANDOFF.md` rolling update; `LEDGER.md` complete; push the branch; owner merges (never us).
- Lessons (humanoid-specific) proposed to `boss-fight-blueprint/references/` on an `agents-md` task branch.
- `wiki-suggest` the durable facts. Remove `work/` renders; keep clips, Actions, ledger.

## Budget and time (estimates, to be replaced by ledger numbers)

| Item | Estimate |
| --- | --- |
| Clips | 17 first takes + ~40 % regenerations = ~24 clips x 5-6 s |
| Spend | fal balance (~$20) used in full, then Higgsfield credits; no per-clip stop; every clip in the ledger |
| Reader training | ground ~3 h + air ~3 h MPS, unattended |
| Wall-clock | Phase 0-2 one session (~6 h incl. reader); Phases 3-4 ~2 sessions; Phase 5 ~1 session |

## Subagent roster (label every spawn `[Model effort]`)

| Role | Model | Work |
| --- | --- | --- |
| Director | Fable 5.1 (this session) | plan, prompt review, go/no-go per clip, reconcile critics; never builds |
| opus-builder | Opus 5.5 high | generate_fal.py + size gate, refine_brute.py, C++ timing/integration pass |
| opus-critic | Opus 5.5 high | every blind A/B, final in-game verdict; never skipped |
| sonnet-builder | Sonnet 5.5 high | rig mapping, start pictures, reader runs, prompts, check/fit/review/export per clip, assemble/build/capture runs, review page |
| haiku-scout | Haiku 5.5 high | ledger, log triage, gate-line extraction, disk/GPU/stream checks, model-id lookup |

## Hard rules carried into execution

- One paid clip at a time; review before the next; every clip's cost, model, resolution and verdict in the ledger.
- fal first until its balance is exhausted or the API fails, then Higgsfield MiniMax H3 Max; never stop for money.
- Blender headless `--background --factory-startup`; engine builds only through `gpu_slot`; cap 2 with Unreal, 4 Blender
  otherwise; never touch the other session's Blender or `~/hulk`; no windows; no captures while `STREAMING` exists.
- Never rename rig bones (Unreal skeleton + reader are keyed to them). Never vendor video2rig into this repo.
- Old clips stay; keep-the-best per clip. No merge to `main` without the owner.
- Secrets: `FAL_KEY` is read from `~/.config/fal/secrets.env` in-process; never on a command line, log or commit.

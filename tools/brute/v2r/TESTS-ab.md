# Blind A/B harness: test on Idle (2026-10-29)

Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

No video generation, no spend, no engine, no reader. Mac Studio M3 Ultra, Blender 5.2.0 LTS, every run
`--background --factory-startup`, one Blender of ours at a time (other sessions ran 1-2). Scratch (gitignored):
`~/hulk/Local/video2rig/ab/test-idle/`.

## Files

| File | Role |
| --- | --- |
| `ab_common.py` | the one camera table (front 0 deg, left side 90 deg, three-quarter 45 deg from his facing; 50 mm, 10.8 m away, 3.4 m high, aimed at z 1.75; frame covers z -0.55 to 3.9 m at his distance), subject loading, 24 fps sampling, the game's root treatment |
| `ab_render.py` | Blender script: one subject, three cameras, `<out>/<label>_{front,left,threequarter}.mp4`, loops played twice |
| `ab_measure.py` | Blender script: seam, foot drift (cm and px), secondary ratio, straight from the Actions; `measure.json` + one `AB_MEASURE` line per subject |
| `ab_pair.py` | system python: random A/B (seeded), renders both, measures both, writes `KEY.json`, `critic_brief.md`, `measure.json` |

A subject is `<file.glb>[:<Action>]` on the shipped rig: the brute_v5 glb (Action = clip name), an `export_clip.py` motion glb
(one Action), or an assembled glb. **Every subject is rendered on the same character (the brute_v5 mesh, corrective shape keys
as exported, same bind)**; a motion glb's location keys are rescaled by its armature scale ratio exactly as `assemble_motion.py`
does (here 0.910). So the pair differs only in the Action.

Design decisions worth knowing
- **Root treatment = the game's** (`BruteCharacter.cpp` ~l.1442): Hips XY pinned to the rest pose, and for ground clips the lowest
  foot bone put back on its rest height every frame (Jump / Fall / WallAttach / WallClimb: first-frame correction only).
  `--root raw` shows the Action as exported. The shipped Idle hovers 0.46 m above the floor as exported; the game never shows that.
- Look: Eevee, 10 samples, 854 x 480, flat grey clay character, light floor with a soft sun shadow (this is how foot contact
  reads), camera-relative fill, no text, no metadata in the mp4. Workbench was tried and dropped: its shadow darkens a whole floor.
  `--material texture` keeps the exported material.
- Loops play start..end twice, the last key included, so a last frame equal to the first shows as a one-frame hold; the seam
  number says so (`seam 0.00`, `duplicate_end_frame` in the json).
- Foot drift: the contact patch of each planted foot (vertices within 1 cm of the lowest at the middle of the planted run) is
  followed rigidly, so heel/toe roll does not count; the worst horizontal extent over both feet and the three fixed cameras is
  `foot_drift_px`. A foot's planted level is its own 5th-percentile height (reported as `planted_level_cm` against the floor).
- Secondary: head (in the Spine2 frame) + fingers (in their Hand frame) mean speed / Hips world speed of the Action as exported.
  The rig has no hair or shorts bones. Definitions are in the `ab_measure.py` header.

## Command and result

```
python3 tools/brute/v2r/ab_pair.py --clip Idle \
  --old ~/hulk-scratch/brute_v5/brute.glb:Idle \
  --new Local/video2rig/work-tools/motion_refined/Brute_v2r_idle.glb \
  --out Local/video2rig/ab/test-idle
```
The new take is the refined v2r test Idle from `TESTS-refine-export.md` (a synthetic fit made FROM the shipped Idle, then
refined and exported), so the two motions are nearly the same by construction; the test proves the harness, not a quality verdict.

Timings (one Blender each): render A 217 s, render B 208 s (250 frames x 3 cameras, 0.28 s per frame), measure both 4.5 s;
total about 7 min per pair.

```
AB_MEASURE Idle A seam 0.00 foot_drift_px 11.2 secondary 0.45
AB_MEASURE Idle B seam 0.00 foot_drift_px 3.7 secondary 0.49
```
Details (`measure.json`): foot drift A 10.2 / 7.6 cm (left / right foot), B 3.3 / 2.8 cm; planted level A -4.6 / -1.2 cm,
B -4.5 / -1.4 cm (soles sit below the street in both: the mesh sole is lower than the foot bones the game grounds);
median step 1.92 mm (A) and 1.67 mm (B), biggest step 5.3x / 5.6x the median.

**KEY (test only, may be shown):** seed 2081823275 (crc32 of "Idle"), **A = old (brute_v5 Idle), B = new (refined v2r Idle)**.

Observation: both takes have last frame equal to the first (seam 0.00 = a duplicated end frame, a one-frame hold when a loop
plays inclusive of its last key). The refined clip inherits it from the shipped Idle the test fit was made from (cause in
`refine_brute.py` not checked); the real Phase 2 numbers will say whether the engine sees it (assemble_motion kept the loop end,
`LOOP Idle end frame 155 of 155 mismatch 0.0001`).

Output checks: one frame of each camera was extracted and viewed (whole body in frame, floor and shadow visible, hands
overhead would still fit: 0.4 m of headroom above a 3.5 m reach). Frame PNGs were deleted after encoding; the frames viewed are
`Local/video2rig/ab/test-idle/frame_{A,B}_{front,left,threequarter}.png` and `contact.png` (A top row, B bottom row).
`critic_brief.md` names only A/B, lists the six questions and the numbers' definitions, and quotes MOVESET.md rows where the
clip has one (Idle has none; a neutral line stands in).

## Not verified / limits
- Only Idle was run; Walk / Run / one-shots were run through `ab_measure.py` alone against brute_v5 (sanity: PunchL forced to
  loop gives seam 8.8, Walk planted-foot speed ~1.3 m/s, which differs from the `clips_meta.json` speed 0.609 and is worth a
  look in Phase 3). `ab_render.py` with a travelling or airborne clip has not been looked at.
- Corrective shape keys are rendered at the values stored in the glb (no pose drivers); the game drives them from the arm
  pose in C++, so correctives are not part of what the critic sees. `mesh_corrective_check.py` stays the Phase 5 check.
- `--material texture` was not rendered.

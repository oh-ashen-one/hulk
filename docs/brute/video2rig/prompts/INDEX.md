# Brute video prompts (17 clips)

Written 2026-10-29 by Claude Sonnet 5.5 (prompt pass, no generation, no spend). Hulk-in-Manhattan fan homage; prompts never name a character.
Start picture: `Local/video2rig/brute-aligned/start/start.png` (front | side, idle stance, he faces -Y; the side panel shows his LEFT flank, he faces
image-left there; his left hand is on the image-right of the front panel). Every file is the prompt only: the generator appends the mandatory
no-effects sentence (~330 chars), so file length (<= 1100 chars) + 330 stays under 1450. Fable reviews each prompt before it is spent.

Structure of every file: (1) the brute as the picture shows him, (2) both-panels/static-camera/studio sentence, (3) weight sentence,
(4) move in numbered beats with seconds, (5) how both views END, (6) whole body stays inside the frame. Timing is a request, not a guarantee:
MiniMax drifts, so Phase 5 re-measures every `HIT` / `C.Hit` from the new clip (`analyze_clips.py`).

| clip | duration s | loop? | ends in | notes / risks |
| --- | --- | --- | --- | --- |
| Idle | 8 | yes | first-frame stance | 8 s = two breaths (5 s gives one cycle only). Feet planted; weight shift + slow head turn so no part keeps >85% of its motion in one cycle. Closing the seam is still done in refine. Pilot clip. |
| Walk | 6 | yes | first-frame stance | On the spot, treadmill-style, six steps. Starts and ends in stance, so the loopable stride is the middle (cut in refine; `LOOP_WIN` 40). Speed 0.609 m/s stays from clips_meta. Risk: generator travels forward despite "in place". |
| Run | 6 | yes | first-frame stance | On the spot, ~2 strides/s, ramp-up 1.2 s and ramp-down 1.2 s around a steady middle (the loop). Speed 2.15 stays from clips_meta. Risks: float (heavy sprint hangs), motion blur on fast legs. |
| StopLunge | 5 | no | first-frame stance | Run-in-place into a planted-foot braced lunge, then rise. Game segment = the stop and lunge (1.4-3.2 s requested). Risk: it slides or travels instead of planting; check foot drift. |
| Jump | 5 | no | first-frame stance | Crouch charge 0-0.85 s, explosive launch, one metre of rise, heavy drop, landing crouch, rise. Game uses only the crouch + launch segment. Risks: floats at the top, rises far above one metre and leaves the frame (headroom is 4.3 m over the floor). Airborne apex would need Phase 4. |
| WallAttach | 5 | no | first-frame stance | RISKY: no wall in the picture; "invisible wall" may draw a wall or crack (size gate + effects check). Forward is toward the front camera, so the front panel foreshortens the slam. Phase 4 may render a wall start picture; two failures keep the Cartwheel clip. |
| WallClimb | 5 | yes (segment) | first-frame stance | RISKY: same as WallAttach; climbing in place from a ground stance means feet leave the floor with no wall to show it. Game loops a mid segment (as today, WallClimb = WallAttach segment). Likely wants the wall start picture. |
| PunchL | 5 | no | first-frame stance | Left fist, contact requested at 1.0 s (current `HIT` 1.0; re-measure). No target, no shockwave. Risk: fast swing blurs, or the right fist comes along. |
| PunchR | 5 | no | first-frame stance | Mirror of PunchL, right fist, contact 1.0 s. In the side panel the right arm is on the far side, hidden by the body; the front panel carries it. Risk: the side view loses the hand. |
| Slap | 5 | no | first-frame stance | Left open-hand wide horizontal sweep, contact 0.9 s (current `HIT` 0.9, game plays 0.30-1.70 s at 1.5x). Hand choice (left, after punch L, punch R) is an assumption: the game does not say which hand. Risk: draws a fist instead of a palm. |
| Clap | 5 | no | first-frame stance | Both palms meet in front of the chest at 0.7 s (`HIT` 0.7). Risk: palms meet away from the chest; arms stay in the frame (front panel half-width 2.17 m). |
| Smash | 5 | no | first-frame stance | Double fists overhead then down to the floor in front, contact 1.17 s (`HIT` 1.17), deep crouch. Risk: a crater, dust or debris drawn despite the no-effects sentence; fists overhead near the top margin (hands ~3.3-3.5 m, headroom ok). |
| Lift | 6 | no | first-frame stance | Squat, grip invisible car-sized load at knee height, heave overhead, hold 1 s (3.6-4.6 s), lower. Game uses the lift-and-hold half and splices the throw. Risks: a car or box appears (prompt says none; if it does, keep the old clip and the car prop); arms drift off the overhead hold. |
| Throw | 5 | no | first-frame stance | The start picture is the stance, not the overhead hold, so the prompt raises the load in 0.8 s, holds, then hurls with a left step; release requested at 1.5 s. The old `HIT` 0.45 s is measured from the spliced hold, so Phase 3 must trim the new clip to start at the hold and re-measure. Risk: invisible load drawn; he steps out of frame (heavy step forward, keep small). |
| Uppercut | 5 | no | first-frame stance | Sprint-start lean, right fist hip to above head, small hop, contact 0.6 s (`HIT` 0.6). Right hand is on the left of the front panel. Risks: hop floats; the fist rises above the frame top (hands ~3.5 m up, margin exists). |
| Fall | 5 | yes | first-frame stance | RISKY: a ground start cannot show a fall; asks for a small hop into a braced air pose, held as long as possible, then a heavy landing. Likely floats (that is the wanted hold) and the landing is generator-timed. Phase 4 may redo it from an air start picture and a second reader. Game loops the braced hold. |
| Land | 5 | no | first-frame stance | Small hop (0.4-0.9 s), heavy crouched impact at 0.9 s, hold, rise. Game plays from 0.35 s with `HIT` 0.5 s in the old clip, so the impact time moves by ~0.4 s: re-measure `HIT` and `C.From` in Phase 5. Risk: hop too high and floaty; no crater or dust. |

## Cross-clip risks (for the director's review)

- Left/right: the prompts name the hand and give its panel position (front panel mirrors the creature; his left hand is image-right). MiniMax may still mirror one punch; check the first frame to contact against the prompt before using the clip.
- Size drift: MiniMax enlarged a winged dragon ~2x. A brute with fists overhead (Smash, Lift, Throw, Uppercut) is the analogue; run `size_gate.py` (< 1.3x) before fitting.
- Heavy creatures float: jump, hop and landing beats say "nothing floats" and "heavy"; hang time is also fixed in the Action (retime), not by regenerating.
- Invisible objects (Lift, Throw, WallAttach, WallClimb): a drawn car or wall is a reject, not a fit.
- Durations differ from the old clips (clips_meta: Idle 5.2, Walk/Run 6.0, StopLunge 2.8, punches 1.5, Slap 2.5, Clap 1.6, Smash 3.0, Lift 3.0, Throw 1.5, Uppercut 2.5, Fall 2.0, Land 3.0 s). Generated clips are 5-8 s with a still tail; refine trims to the move, then `TRIM` / `HIT` / `LOOP_WIN` / `FOOTLOCK` and C.From/To/Rate/Hit are re-set per clip.

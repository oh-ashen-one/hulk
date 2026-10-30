# Blind A/B critique: Brute one-shots (Blender renders, ab-blender-hc)

Critic: Opus 5.5 high, blind. Sources were only `ab-blender-hc/<Clip>/` (six mp4s, `measure.json`, `critic_brief.md`). Method: ffmpeg CPU extraction, a cropped 16-frame contact sheet per camera per take, per-frame strips around each strike and at the last frame, a per-frame pixel-change motion profile across all three cameras (to find holds, snaps and pops), plus the measure.json foot, seam and secondary numbers. Scores run 1-10. R = readability of the move, W = weight/timing, F = foot contact, E = end/return to stance, P = pose quality, S = secondary.

## Verdict table

| Clip | A (R/W/F/E/P/S = sum) | B (R/W/F/E/P/S = sum) | Verdict | Confidence | Both unacceptable? |
| --- | --- | --- | --- | --- | --- |
| PunchL | 4/6/3/2/5/5 = 25 | 3/3/6/9/3/3 = 27 | **A wins** (move readability overrides) | low | **YES** |
| PunchR | 4/6/3/2/5/5 = 25 | 3/3/6/9/3/3 = 27 | **A wins** (move readability overrides) | low | **YES** |
| Slap | 8/7/3/6/7/6 = 37 | 4/3/6/9/5/4 = 31 | **A wins** | medium-high | no (A has a foot-slide fix) |
| Clap | 6/6/7/9/5/4 = 37 | 7/3/5/6/6/5 = 32 | **A wins** | low | no |
| Uppercut | 8/5/3/3/6/4 = 29 | 4/4/6/9/4/4 = 31 | **A wins** (move readability overrides) | medium | borderline (A needs end and feet fixed) |
| Lift | 3/3/6/8/4/3 = 27 | 7/5/5/3/6/4 = 30 | **B wins** | medium | no |
| Throw | 6/5/2/5/2/4 = 24 | 7/5/5/3/6/5 = 31 | **B wins** | medium | no |
| Land | 7/7/5/9/6/4 = 38 | 4/4/4/2/2/3 = 19 | **A wins** | high | no |
| StopLunge | 5/6/2/9/6/5 = 33 | 3/4/4/1/3/3 = 18 | **A wins** | low | **YES** |

Tally: A wins 7, B wins 2, no ties. On PunchL, PunchR and Uppercut, B has the higher sum because it scores well on returning to stance and foot contact. B loses all three because it does not perform the named move: the first criterion is readability of the move, and a clean return does not save a clip that never shows it.

Biggest gap (testable): **neither take ships a straight punch.** A's PunchL and PunchR are one flailing multi-beat animation, mirrored (identical `hips_mm_per_sample` 15.247 and secondary 0.285 / 0.284). It ends turned roughly 90-180 degrees away, 449 to 455 mm from its start pose. B's punches are slow forward reaches with an open, splayed hand. To pass: one lead-hand extension that reaches full arm length in 3 to 5 frames with a closed fist, at most one strike beat, the pelvis turning less than 30 degrees, and an end pose within 50 mm of frame 0 (`last_first_gap_mm` < 50).

Recurring issues, by take:
- **A:** planted feet slide 17 to 64 px (Slap 37, Uppercut 40, StopLunge 55, Throw 64). The weighted foot goes up on its toe (PunchL f28-33, left camera), and the lowest foot vertex sits about 13 cm under the floor on six clips. A never moves its fingers (`fingers_in_hand_mm_per_sample` = 0 everywhere except Slap).
- **B:** open claw hands on strikes, long dead holds (Lift 1.4 s squat, Land 1.4 s twisted crouch, StopLunge 0.9 s frozen end), and five of the nine clips end 0.5 to 0.95 m away from the start pose.

---

## Per-clip detail

### PunchL: A wins (low). Both unacceptable.
- measure.json: A ends 449 mm from its start pose, planted-foot drift 24.4 px, lowest foot vertex -13.7 cm. B ends 1.4 mm from its start pose, drift 22.4 px, lowest vertex -5.5 cm, secondary ratio 0.14 (the lowest of all takes).
- A defects:
  - A closed-fist forward extension at 0.42-0.71 s (left camera, f10-17) is followed by a second arm swinging overhead at 0.83-0.92 s (f20-22) and a torso spin, so the clip ends with his back to the left camera at 1.54 s.
  - Foot slide of 24 px over f26-35; the weighted foot is on its toe at f28-33.
- B defects:
  - About 1.3 s of near-idle wind-up (f0-31), then the left arm reaches forward and downward with a splayed open hand (front camera, f35-47, 1.46-1.96 s).
  - The arm stays extended for about 8 frames.
  - It reads as a grab or shove, not a straight punch.
- Why: A at least shows a fisted forward strike in its first 0.7 s, while B never forms a fist or a straight line. A's spin-away ending and sliding feet still make it unshippable as combo hit 1.

### PunchR: A wins (low). Both unacceptable.
- measure.json: A is the PunchL flail mirrored (ends 455 mm from its start pose, drift 19.4 px, identical hip and secondary numbers). B ends 0.1 mm from its start pose, drift 12.8 px.
- A defects: the same four-beat flail. The overhead swing is at 0.83-0.92 s and he ends in a deep lunge turned away (front camera, f30-37).
- B defects:
  - Both arms open wide with splayed hands at 0.54-0.88 s.
  - The right arm rises over the face at 1.04 s and then extends forward at shoulder height with an open claw hand (left camera, f29-42, 1.21-1.75 s). That is a zombie-reach silhouette held for about 13 frames.
- Why: B's straight-arm forward extension is closer in line than A's flail, but an open hand held still for half a second is not a punch. A's closed-fist extension (0.42-0.71 s) is the only strike content on screen.

### Slap: A wins (medium-high).
- measure.json: A ends 139 mm from its start pose, drift 37.0 px (left foot f27-59), finger motion 0.705. B ends 0.16 mm from its start pose, drift 14.9 px.
- A defects:
  - The left foot skates 37 px during recovery (three-quarter camera, f27-59). This is the main fix needed.
  - The end pose is close to the start stance but not exact.
- A strengths: a big open-palm wind-up over the head at 0.50-0.83 s (front camera) and a full-body swing with the hips leading at 1.00-1.29 s. The follow-through crosses the body at 1.46 s.
- B defects: the arm drifts out sideways at shoulder height (front camera, f21-37) and sweeps across the chest at 1.75-2.42 s. Its peak pixel motion is 7,062, half of A's 14,235. It reads as a slow swat with no weight shift.
- Why: A is unmistakably a heavy open-hand slap with anticipation, contact and recovery. B is a slow arm sweep that would read as a gesture, not a finisher.

### Clap: A wins (low).
- measure.json: A ends exactly on its start pose (0 mm), drift 7.5 px. B ends 91 mm from its start pose, drift 0.0 px (legs never move), lowest vertex -10.9 cm, secondary 0.753.
- A defects:
  - The arms spread into a stiff, almost straight T at 0.50-0.67 s (front camera) with an upright torso.
  - The palms meet in front of the chest at 0.83 s and stay nearly static until about 1.33 s (motion profile is flat over f23-32).
  - Modest menace.
- B defects:
  - The arms go from hanging to a full T in 3 frames (front camera, f0-3, 0-0.12 s), an impossible snap for this mass.
  - About a 10-frame hold with the arms raised (f5-15) and about a 12-frame hold with the palms together (f18-30).
  - The legs stay locked in one wide stance for the whole clip, with no hip or knee weight shift.
  - The arms drop back in 6 frames.
- B strength: the left camera shows the best key pose in either take, an overhead wind-up at 0.21-0.54 s whipping into both arms fully forward at 0.75 s.
- Why: B has the stronger thunderclap silhouette, but the 0.12 s opening snap, two dead holds and frozen legs fail weight and timing outright. A is weaker but clean, weighted and returns to stance exactly.

### Uppercut: A wins (medium). A is borderline unacceptable.
- measure.json: A ends 344 mm from its start pose, maximum frame step 15.15 times the median, drift 40.2 px. B ends exactly on its start pose (0 mm), drift 19.3 px.
- A defects:
  - Crouch to full vertical extension in 2 frames (left camera, f13-15, 0.54-0.62 s). This is the single largest frame step in the set.
  - The arm then stays raised for about 1 s with very little motion (f17-35).
  - Left foot slides 40 px over f7-59.
  - Ends off stance.
- A strengths: a real launcher read. A folded crouch at 0.17-0.50 s explodes into a rising closed fist straight overhead, on one leg.
- B defects:
  - The body turns away at 0.79-1.00 s (left camera, back visible), then the arm sweeps up into an open-hand overhead reach (three-quarter camera, f32-40, 1.33-1.67 s).
  - No crouch and no upward drive. It reads as reaching for a shelf.
- Why: A shows the anticipation-explosion-launch the move needs, with a closed fist. B is clean on feet and return but has no uppercut in it.

### Lift: B wins (medium).
- measure.json: A ends exactly on its start pose (0 mm), 16 still frame-steps, drift 17.6 px. B ends 615 mm from its start pose (holding overhead), 2 still steps, drift 12.0 px.
- A defects:
  - He squats (0.54-0.79 s), then stands fully upright with empty hands hanging at his sides (front camera, f32-38, 1.33-1.58 s) before raising his arms. There is no continuous grip; the car would be dropped.
  - The overhead hold is upright with splayed "cheering" fingers and no strain (f51-70, 2.12-2.92 s, flat motion profile).
- B defects:
  - The squat with the hands gripping at the floor is held nearly still for about 1.4 s (f14-48), a dead hold.
  - The hands pass the hips at f53 before going overhead (a brief grip break).
- B strengths: the heave to overhead and the lean-back hold read as bearing a load (left camera, f58-72), and the hands stay curled as if holding something. The end pose suits a handoff to Throw.
- Why: B reads as picking up something heavy and getting it overhead, which is the clip's job. A breaks the grab midway and holds a weightless overhead pose.

### Throw: B wins (medium).
- measure.json: A ends 0.17 mm from its start pose, drift 63.9 px (left foot f35-78), travel 0.525 m. B ends 616 mm from its start pose, maximum step 9.94 times the median, drift 13.4 px.
- A defects:
  - **Arm-flick glitch.** The arms go from forward-low to straight overhead and back to hanging within f62-64 (2.58-2.67 s, left and front cameras). This is the motion-profile spike at f63.
  - The planted foot skates 64 px, the worst in the set.
  - It starts from an empty idle stance, so the arms must re-raise an imaginary car.
- B defects:
  - Recovery from doubled over to upright takes only 6 frames (front camera, f14-20, 0.58-0.83 s).
  - Ends in a scissor stance with the trailing foot on its toe (f21-35), not the idle stance.
- B strengths: it starts with the arms overhead (it continues from a lift), and the hurl happens in 3 frames (f9-12) with a deep follow-through and a counterbalancing back leg at 0.58-0.67 s.
- Why: B is a readable overhead hurl with a believable follow-through. A has a visible glitch flick and the worst foot skating, which outweigh its slower, weightier step.

### Land: A wins (high).
- measure.json: A ends exactly on its start pose (0 mm), drift 16.7 px, lowest vertex -14.0 cm. B ends 497 mm from its start pose, maximum step 17.2 times the median, drift 18.7 px.
- A defects:
  - The "airborne" tiptoe pose at 0.58-0.79 s (front camera) is pinned to the floor by the grounding, so it reads as a bounce rather than a fall.
  - Toes about 14 cm under the floor by measurement.
- A strengths: a three-point impact crouch with one hand down at 1.00-1.58 s, a weighted rise and an exact stance by 3.0 s.
- B defects:
  - The airborne hammer pose at f0-5 is mostly skipped, since the game starts the clip at 0.35 s.
  - After impact the spine is twisted, the head is buried at pelvis height and one arm points straight up (front camera, f14-47, 0.58-1.96 s). That contorted pose is held nearly frozen for about 1.4 s.
  - Ends in a rotated flex pose (2.58-2.96 s).
- Why: A reads cleanly as a heavy superhero landing and recovers to stance. B's post-impact pose looks broken and dead, and it ends off stance.

### StopLunge: A wins (low). Both unacceptable.
- measure.json: A ends exactly on its start pose (0 mm), planted-foot drift 54.8 px (right foot f20-22), feet grounded only 8-15 % of frames. B ends 949 mm from its start pose with 21 still tail samples (about 0.9 s frozen).
- A defects:
  - It starts from idle stance, not a run (front camera, f0), so it will pop when it follows the run cycle.
  - 55 px foot skate at f20-22.
- A strengths: two reaching lunge strides (left camera, f14 and f29) and a wide menacing plant at 1.58-2.21 s.
- B defects:
  - About 1.5 s more of running (f0-36) after the run is released.
  - Then it tucks into a ball, head buried below the shoulders and hands on the floor (front camera, f45-68), frozen for about 0.9 s.
  - No lunge, and it never returns to stance.
- Why: A at least contains a plant-and-lunge and settles into a hunched, threatening stance. B is a run that collapses into a frozen crouch. Neither enters from a run and brakes immediately, which is what the clip is for.

## Decoded (director)

The critic judged blind. The key decodes the labels. "new-hc" is the hold-compressed variant from `Local/video2rig/motion-v2r-hc/` (see [HOLD-COMPRESSION.md](HOLD-COMPRESSION.md)).

| clip | A | B | winner | decoded | confidence |
| --- | --- | --- | --- | --- | --- |
| PunchL | old | new-hc | A | OLD wins (both unacceptable) | low |
| PunchR | old | new-hc | A | OLD wins (both unacceptable) | low |
| Slap | old | new-hc | A | OLD wins | med-high |
| Clap | new-hc | old | A | NEW-hc wins | low |
| Uppercut | old | new-hc | A | OLD wins | med |
| Lift | new-hc | old | B | OLD wins | med |
| Throw | new-hc | old | B | OLD wins | med |
| Land | new-hc | old | A | NEW-hc wins | high |
| StopLunge | new-hc | old | A | NEW-hc wins (both unacceptable) | low |

Round-1 Blender verdicts (AB-blender-critique.md) compared the un-compressed candidates; hold compression turned Land from a loss into a high-confidence win and left the rest as before. In-game blind A/B decides shipping.

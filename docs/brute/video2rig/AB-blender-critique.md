# Blind A/B critique: Brute (Hulk) clips, Blender pair set

Critic: Opus 5.5 high, blind. Evidence came only from the pair folders: 6 mp4s, `measure.json` and `critic_brief.md` per clip. I did not open key files, `_director/`, ledgers, git, mtimes or sizes.
Method: I extracted every frame per camera with ffmpeg (CPU), cropped it to the character and built 12-frame contact sheets per camera and subject. I added dense sheets (every 2-3 frames) around strikes, contacts and wraps, plus full-resolution stills at contact frames. I also measured a per-frame motion-energy trace (changed-pixel permil, left camera) to find holds, pops and snaps, and tracked the silhouette top y. Times are clip seconds (frame/24).

## Verdicts

| Clip | Winner | Confidence | One-line reason |
| --- | --- | --- | --- |
| Idle | B | med | A is almost a statue: the head moves 4 px in 5 s, then snaps at 5.00-5.13 s (step 5.3x median) into a duplicate-frame hold. B breathes and shifts weight. |
| Walk | B | high | A stops walking at 5.1-5.8 s for a hand-to-forehead gesture (front cam), inside the loop. B is a steady wide-armed stomp with a clean wrap (seam 0.75). |
| Run | B | high | A is a stand, run, stand one-shot: upright at 0.0 s and 6.0 s, with big lateral lurches. B is a continuous heavy stride (seam 0.85). |
| StopLunge | A | med | A brakes into a wide gorilla brace at 1.9 s and returns to stance. B hops upright at 1.5 s, then folds into a head-buried ball and never returns (seam 10.2). |
| PunchL | A | low | A is one left strike that returns to stance, but it is a limp open-hand reach held for 2 s. B is a jab plus a right haymaker that ends mid-lunge. **Neither take is shippable.** |
| PunchR | B | low | A is a mirror of PunchL-B: right jab, then the big hit comes from the left hand. B is one right strike that returns to stance, but with an open claw hand and about 0.7 s frozen. **Neither take is shippable.** |
| Slap | B | low | B is a committed open-palm swing led by the hips and shoulders. A is a slow, upright arm sweep. B pays for it with a 32.6 cm skate during recovery and a 3.4x end gap. |
| Clap | B | high | B rises up to 17 px, slams into a crouch at the 1.29 s clap and returns to idle. A snaps its arms to a T in 3 frames with locked legs (foot height min = max) and does not return (seam 6.5). |
| Uppercut | A | high | A gathers in a near-all-fours crouch (0.21 s) and explodes to full vertical extension in 3 frames: a true launcher. B is a mild wind-up, then an arm held overhead for about 1.9 s. |
| Lift | B | high | B grabs at floor level (0.54-1.92 s) and heaves overhead, ending in the hold the throw needs. A squats empty-handed, stands up, then raises its arms as a separate beat. |
| Throw | B | low | B starts from the overhead hold and whips through. A repeats a whole lift inside itself, skates 57 cm and flicks its arms up again at 4.0-4.1 s. B's 3-frame release and 0.3 s recovery read light. |
| Land | B | med | The game starts A at 0.35 s, but A then crouches and hops (airborne at 0.92 s) before it lands. B impacts at 0.33-0.38 s and compresses hard, but holds one arm straight up for 1.3 s. **Neither take is shippable.** |
| WallClimb | A | high | A is a clean 1.2 s hand-over-hand climb (seam 1.8). B is a jump-up-and-fall one-shot that leaves the top of the frame from 1.4 s to 4.1 s (seam 14.2). |
| Fall | B | low | Both are the same arms-wide braced hold. A pedals its legs, has a duplicate end frame and three dead stalls per loop. B is a steadier, quieter hold (seam 0.24). |

Tally: B wins 10, A wins 4, no ties. Clips where both takes are unacceptable for shipping: **PunchL, PunchR, Land**. Marginal winners that still need work: StopLunge-A (2.5 s crouch hold, starts from idle rather than from a run) and WallClimb-A (a light ladder climb, not an 18 m/s wall run).

**Single biggest gap (testable):** the combo punches. Neither take delivers one closed-fist straight with weight transfer that starts and ends in the shared combat stance. PunchL and PunchR should each pass all of these checks:
- exactly one strike in the clip
- fist visibly closed at the contact frame
- contact at 0.30-0.50 s
- pelvis and shoulder rotation of at least 30 degrees into the hit
- no hold longer than 6 frames
- total length of 1.2 s or less
- end pose back in the start stance (seam ratio under 2)

**Secondary issues:**
- **The winners mix two stance families.** One family starts and ends in idle and runs about 5 s with long frozen holds (PunchL-A, PunchR-B, StopLunge-A, Uppercut-B, Lift-A, Throw-A, Clap-B, Slap-A). The other runs 1.5-3 s from a wide fighting stance and does not return (PunchL-B, PunchR-A, Slap-B, Uppercut-A, Lift-B, Throw-B, Land-B). The combo chain (PunchL A, PunchR B, Slap B) therefore needs stance blends.
- **Long frozen holds** (energy 0-2 for 0.7-2 s) recur across the idle-return family. They read as dead pauses, not weight.
- **Idle foot drift.** Both Idle takes drift 7-12 cm on fully planted feet.
- **Walk contacts.** Walk-A registers a planted foot on only 17-21 % of frames per foot.

---

## Per-clip detail

Scores run from 1 to 10. R = readability, W = weight and timing, F = foot contact, S = loop seam or return to stance, P = pose quality, 2nd = secondary motion, O = overall (weighted: W and P highest).

### Idle (loop): B wins, med
`measure.json`: A has 125 frames, a duplicate end frame (seam 0.00), max step 5.27x median, drift 11.2 px, secondary 0.45. B has 149 frames, seam 0.20 with 2 still-tail frames, max step 2.8x, drift 12.5 px, secondary 0.31.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 5 | 4 | 5 | 4 | 7 | 3 | 4.5 |
| B | 7 | 6 | 5 | 6 | 7 | 5 | 6 |

- **A:** The silhouette top moves only 115-119 px over 5.2 s and motion energy sits at 0-1 for most of the loop, so it reads as a held pose rather than a patient brute. Energy jumps to 3-5 at f120-123 (5.00-5.13 s), then the duplicate end frame holds: a visible catch-up and freeze at every wrap.
- **B:** A slow breath and weight shift is visible: the head dips about 10 px, and in the front cam the arms flare at 1.1-2.3 s. The wrap is a soft near-hold (ratio 0.2, 2 still frames). Both takes skate their planted feet by 7-12 cm.

### Walk (loop): B wins, high
`measure.json`: A has 145 frames, a duplicate end frame, max step 2.74x, grounded 17 % (left) and 21 % (right), drift 48 px. B has 75 frames, seam 0.75 (bone 1.02), max step 1.57x, grounded 53 % and 47 %, drift 102 px (planted speed 1.28 m/s by design).

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 2 | 5 | 4 | 5 | 5 | 4 | 3 |
| B | 8 | 7 | 6 | 8 | 7 | 5 | 7 |

- **A:** The front cam at 5.08-5.75 s shows the gait stop: the right hand goes up to the forehead and the left hand flares out. The energy spikes (56, 49) and the silhouette rises 15 px. That is a non-locomotion beat baked into the loop, and it would replay every 6 s.
- **B:** A consistent hunched stomp with arms held wide. Clear alternating stance phases. The cleanest seam of any loop.

### Run (loop): B wins, high
`measure.json`: A has 145 frames, a duplicate end frame, energy near 10 for the first 20 frames and 20 or less for the last 25. B has 89 frames, seam 0.85, energy steady at 30-77.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 4 | 6 | 4 | 3 | 6 | 5 | 3.5 |
| B | 8 | 7 | 6 | 8 | 7 | 5 | 7 |

- **A:** In the left cam he stands upright at 0.00 s and again at 6.00 s, so the loop is a start-run-stop one-shot. In the front cam the body weaves heavily from side to side (2.2-4.4 s), and the silhouette top bounces about 60 px. The gallop in the middle is menacing but cannot be looped.
- **B:** Continuous pumping strides with a forward lean, a steady silhouette (160-177 px) and a seamless wrap.

### StopLunge (one-shot): A wins, med
`measure.json`: A is 5.1 s, end gap 0.48, max step 5.98x, drift 70.5 px (during the run section). B is 2.9 s, end gap 10.2 (949 mm), 21 still-tail frames.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 6 | 7 | 5 | 8 | 7 | 5 | 6.5 |
| B | 4 | 6 | 5 | 2 | 4 | 6 | 4 |

- **A:** Burst forward at 0.46-1.42 s, then plants into a wide arms-out brace (threequarter cam, 1.75-2.17 s) and rises to idle. Faults: the 2.5 s crouch hold is too long, and the clip starts from idle rather than from a run.
- **B:** Enters mid-run, which suits the purpose. But at 1.50-1.67 s it pops upright onto its toes, then collapses into a folded ball with the head buried between the knees (2.0-2.83 s), and it holds there without returning to stance.

### PunchL (one-shot): A wins, low. Both unacceptable
`measure.json`: A is 5.1 s, seam 0.09, drift 22.3 px, lowest foot vertex -5.5 cm. B is 1.5 s, end gap 8.0 (449 mm), drift 24.4 px, lowest foot vertex -13.7 cm.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 6 | 4 | 6 | 8 | 4 | 3 | 5 |
| B | 4 | 7 | 4 | 2 | 7 | 5 | 4.5 |

- **A:** The left arm cocks high and wide (0.83-1.33 s), then strikes at 1.33-1.50 s. At contact (full-res frame 45) the hand is open and the arm hangs low and forward, with almost no hip drive. It reads as a reach or shove. The extension is then held for about 2 s (energy 0-9).
- **B:** Starts in a fighting stance with closed fists. A left jab lands at 0.54 s, a right overhead haymaker follows with a big lunge (1.0-1.54 s), and the clip ends mid-lunge. That is two hits, and the climax uses the wrong hand. The weight transfer is strong, but the clip cannot stand alone as hit 1.

### PunchR (one-shot): B wins, low. Both unacceptable
`measure.json`: A is 1.5 s, end gap 7.9, secondary 0.284, hips 15.247. These match PunchL-B almost exactly, so it looks like the same motion mirrored. B is 5.1 s, seam 0.02, 12 still-tail frames, drift 14.3 px.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 4 | 7 | 5 | 2 | 7 | 5 | 4.5 |
| B | 6 | 5 | 6 | 8 | 5 | 3 | 5.5 |

- **A:** In the front cam a right jab lands at 0.54 s, then the left hand winds up overhead at 0.83 s and lands the big lunge at 1.0-1.54 s. The main hit is the left hand, the wrong hand for this clip, and the clip ends mid-lunge.
- **B:** From idle, a right strike at 1.83 s. The full-res contact frame shows an open, splayed claw rather than a fist, and the torso is turned about 90 degrees side-on. Energy is 0-2 for about 0.7 s after contact, then a slow return to idle. It reads as one right-hand blow, but not as a punch.

### Slap (one-shot): B wins, low
`measure.json`: A is 5.1 s, seam 0.00, drift 14.9 px. B is 2.5 s, end gap 3.4 (139 mm), drift 37.0 px (left foot skates 32.6 cm over f27-59), finger motion 0.705 (A: 0).

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 5 | 4 | 7 | 8 | 6 | 4 | 5 |
| B | 7 | 7 | 3 | 4 | 6 | 6 | 5.5 |

- **A:** The arm hangs cocked out to the side for about 0.6 s (1.58-2.08 s), then sweeps across at 2.2-2.5 s with an upright, uncommitted torso. Peak energy 35. A long, slow recovery follows.
- **B:** A forehand-to-backhand swing with a full torso twist and an open palm (threequarter cam, 0.42-1.33 s). Peak energy 50. Faults: the hand stays raised behind the head until about 1.33 s, the recovery skates, and the end pose misses the start pose.

### Clap (one-shot): B wins, high
`measure.json`: A is 1.6 s, end gap 6.5, foot drift 0.0 with foot min height = max height (legs locked solid). B is 4.7 s, seam 0.02, drift 7.5 px.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 6 | 3 | 6 | 3 | 5 | 5 | 4 |
| B | 8 | 7 | 7 | 8 | 7 | 4 | 7 |

- **A:** The arms snap from hanging to a T-pose in 3 frames (0.00-0.12 s, energy 54-59), hold, clap at 0.71 s, hold again, then drop. The lower body never moves, so the clap has no mass behind it, and the clip does not return to stance.
- **B:** The wind-up rises onto the toes (silhouette 121 to 104), the arms open to a T at 0.83 s, then the body drops into a crouch as the palms meet at 1.29 s. The front-cam silhouette reads clearly. Fault: a dead freeze at the clap (energy 0 for f29-55, about 1.1 s) before a slow return to idle.

### Uppercut (one-shot): A wins, high
`measure.json`: A is 2.5 s, end gap 9.7, drift 40.2 px (left foot 36.8 cm over a planted run). B is 5.1 s, seam 0.01, 4 still-tail frames, drift 19.6 px.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 8 | 8 | 4 | 3 | 7 | 5 | 7 |
| B | 5 | 4 | 6 | 8 | 6 | 3 | 5 |

- **A:** The full-res threequarter shows a near-all-fours gather at 0.21 s, a rise at 0.46 s, a whip at f14 (energy 137-141) and full vertical extension with a lifted knee from 0.67 to 1.33 s. It then drops into a wide stance. It reads instantly as a launcher. Faults: foot skate, and the end pose differs from the start pose.
- **B:** A small dip and arm spread at 0.9-1.4 s, then the right arm goes overhead at 1.83 s and holds there for about 1.9 s (energy 0 over roughly f55-76). It reads as raising a fist, not as a launcher.

### Lift (one-shot): B wins, high
`measure.json`: A is 6.4 s, seam 0.00, about 1.2 s frozen overhead. B is 3.0 s, end gap 20.1. Ending in the overhead hold is correct for a grab-and-hold.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 3 | 3 | 7 | 8 | 6 | 3 | 3.5 |
| B | 9 | 8 | 6 | 7 | 7 | 5 | 8 |

- **A:** Front cam: squats at 1.17 s with the hands at knee height, gripping nothing. Stands at 2.33 s. Then lifts straight arms overhead with open hands and straight legs (3.5-4.67 s), and returns to idle. It reads as squat, stand, stretch, with no load in it.
- **B:** A deep squat with the hands at floor level, set for about 1.4 s (0.54-1.92 s). An explosive heave at 2.17-2.46 s ends with bent elbows overhead and the torso leaning back under the load (left cam, 2.71 s). Clear weight, and it hands off to the throw.

### Throw (one-shot): B wins, low
`measure.json`: A is 5.1 s, seam 0.01, drift 63.9 px (left foot skates 57.2 cm over f54-122). B is 1.5 s, end gap 13.1, drift 13.4 px, finger motion 0.91.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 7 | 6 | 3 | 8 | 6 | 5 | 5.5 |
| B | 7 | 6 | 6 | 3 | 6 | 6 | 6 |

- **A:** From idle the arms go overhead (0.92 s), load behind the head (1.4-1.8 s), lean back (2.08-2.33 s) and hurl into a bent follow-through (2.58-3.33 s, held). The arc is good, but the clip repeats a whole lift, skates during the follow-through, and flicks the arms back overhead at 4.0-4.1 s (energy 57-73).
- **B:** Starts from the overhead hold, extends and leans back (0.12-0.42 s), then whips down to horizontal in 3 frames (f10-13, energy 115-125). Back upright by 0.79 s, which is light for the mass. The rear foot rests on its toe tip from 0.88 to 1.46 s.

### Land (one-shot, played from 0.35 s): B wins, med. Both unacceptable
`measure.json`: A is 5.1 s, seam 0.21, drift 38.4 px. B is 3.0 s, end gap 17.1, max step 17.2x at impact.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 2 | 6 | 4 | 8 | 6 | 4 | 3 |
| B | 7 | 8 | 5 | 3 | 4 | 4 | 6 |

- **A:** From 0.35 s the player would see a crouch and then a hop: airborne with tucked legs at 0.92 s, impact around 1.0-1.08 s. That is an extra jump after the real landing. A three-point crouch follows and is held for about 2 s (energy 0-2).
- **B:** Falling pose with arms up, then impact right at about 0.35 s. The silhouette compresses 31 to 150 px within 2 frames and rebounds slightly. Then a fist-down superhero crouch and a rise into a flexing stance. Faults: the right arm stays locked straight up for the whole 0.54-1.88 s crouch, and the clip ends in a wide flex rather than the stance.

### WallClimb (loop): A wins, high. B unacceptable
`measure.json`: A has 30 frames, seam 1.80, drift 1.8 px. B has 121 frames, seam 14.2 (639 mm), foot height up to 254 cm.

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 6 | 4 | 6 | 7 | 6 | 3 | 5.5 |
| B | 2 | 4 | 3 | 1 | 4 | 3 | 2 |

- **A:** Alternating overhead reaches with matching knee lifts (all cameras), loop cycle 1.21 s, slight wrap bump. Weakness: open hands patting upward with no body heave. It reads as a ladder climb, not an 18 m/s run up a facade.
- **B:** A crouch jump at 0-0.46 s, then the body leaves the top of the 854x480 frame from about 1.4 s to 4.1 s (silhouette top y = 0), then it falls back to the floor at 5.0 s. It is not a loop. Most of the clip cannot be judged, and the wrap is a 14x pop.

### Fall (loop): B wins, low
`measure.json`: A has 113 frames, a duplicate end frame, drift 32.6 px (the leg scissor reads as drift), secondary 0.28. B has 48 frames, seam 0.24, drift 7.6 px, secondary 1.14 (high only because the pelvis is nearly still, 0.32 mm/sample).

| | R | W | F | S | P | 2nd | O |
|---|---|---|---|---|---|---|---|
| A | 6 | 5 | 5 | 4 | 7 | 5 | 5.5 |
| B | 7 | 5 | 6 | 6 | 7 | 4 | 6 |

- **A:** An arms-wide brace with a slow leg scissor (front cam, 0.83/1.29 s versus 3.38/3.83 s), so he appears to walk in the air. Energy drops to 0-1 at f24-30, f54-60 and f83-87: three eased stalls per loop, plus the duplicate-frame hold at the wrap.
- **B:** The same brace with a fixed bent-knee leg and low-amplitude continuous motion. It reads as more braced, with one small hold at the wrap. Close to static, but not frozen.

## Decoded (director)

The critic judged blind; the key decodes labels.

| clip | A | B | winner | decoded | confidence |
| --- | --- | --- | --- | --- | --- |
| Idle | old | new | B | NEW wins | med |
| Walk | old | new | B | NEW wins | high |
| Run | old | new | B | NEW wins | high |
| StopLunge | new | old | A | NEW wins | med |
| PunchL | new | old | A | NEW wins (neither shippable per critic) | low |
| PunchR | old | new | B | NEW wins (neither shippable per critic) | low |
| Slap | new | old | B | OLD wins | low |
| Clap | old | new | B | NEW wins | high |
| Uppercut | old | new | A | OLD wins | high |
| Lift | new | old | B | OLD wins | high |
| Throw | new | old | B | OLD wins | low |
| Land | new | old | B | OLD wins (neither shippable per critic) | med |
| WallClimb | new | old | A | NEW wins | high |
| Fall | new | old | B | OLD wins | low |

Blender-side A/B is advisory; the in-game blind A/B (ab_ingame) decides shipping.

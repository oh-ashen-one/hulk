# In-game blind A/B critique, round 4 (final): Brute

Critic: Opus 5.5 (high), independent. The only inputs were `blind-r4/critic/` (brief.md plus six case folders). Method: CPU ffmpeg contact sheets and frame-accurate crops (`select=n`), per-frame A/B PSNR/MSE (full frame and character region), green-silhouette tracking with OpenCV (head-top y, extent, autocorrelation for cycle period, frame-to-frame IoU to catch pops). Frame numbers are at 60 fps, so frame 318 = 5.30 s.

## Cross-angle take matching (labels are shuffled per folder)

- **Land:** two takes, matched by pose at identical frames in all three angles.
  - **Take Y** = `jump_front` **B**, `jump_left` **A**, `jump_tq` **A**. It drops into a forward crouch on the touchdown frames (321-324), then one arm reaches down and braces toward the ground (tq A 338-343, left A 338-343; seen from the front as both arms hanging low and wide, front B 336-345).
  - **Take X** = `jump_front` **A**, `jump_left` **B**, `jump_tq` **B**. It stays upright with a vertical back and arms hanging for about 15 frames after the crater fires (front A 321-327, tq B 323-333, left B 328), and only folds into its crouch at about 342-348.
  - Silhouette head-top y gives the same pairing on its own in every angle: X is high early, then drops and rises late; Y is low early and rises earlier.
- **Fall:** the takes cannot be told apart, so they cannot be matched (see below).
- **Run:** the two takes have the same cadence and nearly the same poses. No feature reliably tells them apart, so cross-angle matching is not possible.

## Verdict table

| Clip | Preferred label per folder | Confidence | Evidence (frame / time) |
|---|---|---|---|
| **Land** | **front B / left A / tq A** (take Y) | High (0.8) | The crater and dust ring fire at about frame 318 (5.30 s). **Y** is in a forward crouch by 321-324 (front B 324: hunched, arms wide) and braces one hand toward the ground at 336-345 (tq A 342, left A 338-343). Impact absorption starts on contact. It rises gradually from about 384 to 414 (front B head-top y 362, 348, 334, 320, 312, 302 at frames 384-414) and is in Idle by about 414-420, roughly 1.6 s after touchdown. No pop at the Idle blend (front 414-438 is steady). **X** stays stiff and upright for 0.1-0.25 s after the crater (front A 321-327 standing tall, arms at its sides; tq B 323-333; left B 328 back vertical). That reads as weightless: the ground explodes and the body does not react. It then folds late (about 342-348, 0.4 s after contact), holds an asymmetric, lopsided crouch under the dust, and pops up over about 12 frames (front A 402 to 414: head-top y 332 to 301) into the same Idle at about 414. In both takes the dust cloud hides the body at 348-380, and the help box hides the feet in front and tq for the whole landing. |
| **Fall** | **tie** (front -, left -, tq -) | High that they are identical | A and B match pixel for pixel during the whole Fall (about 3.1-5.25 s). Full-frame MSE in jump_left is 3-4 for 2.0-4.5 s, below the 7 of the identical opening walk-in (compression noise). In front and tq it is 9-14 against an 8 baseline, and character-region MSE is 11-22 with frame-identical poses at 120-208 (front sheet). Only the Land window differs (MSE 290-830 from 5.0 s on). **The Fall difference did not render in either take.** Either both builds played the same Fall asset, or the Fall loop is overridden or not entered. Fall cannot be judged as an A/B question, and the director should check the build. |
| **Run** | **tie** (front tie / left tie / tq tie) | Medium (0.6) | Same cadence in both: a 37-frame (0.62 s) cycle by silhouette-extent autocorrelation in loco_left, frames 300-500 (A ac 0.48, B ac 0.71). Same vertical bob: head-top detrended std A 8.3 px vs B 7.8 px. Same arm-swing amplitude: extent std A 34 vs B 36 px. Frame-to-frame silhouette change shows no pop in either; the maximum outliers are the shared occlusions at frame 400 (traffic barrel) and 493 (truck). Walk to Run at about 4.7 s (frame 282) blends cleanly in both (tq 264-315). By eye, A pitches the torso slightly more and reaches the near fist further forward and down (left 440-450), while B carries the elbows a little wider in front (front 452-470). That is not enough to prefer either. **Foot contact is unproven for both.** The help box covers the feet in front and tq, and in left too at this camera height: the planted foot sits behind the box text at y > 430 (left 440-477, contrast-boosted). The higher autocorrelation of B's extent (0.71 vs 0.48) hints at a slightly more regular loop. That is weak evidence, not a win. |

## Notes

- **Sprint (8.5-11.5 s) is only partly judgeable this round.** It is visible about 8.9-9.6 s and 10.1-11.5 s in left and tq. The tumbling truck and cars hide the Brute at about 9.6-10.0 s (left frames 574-600, front 9.7 s, tq 9.7-10.2 s). Where visible, A and B show the same low, leaning sprint (left 534-566 and 606-694), with no difference that would change the Run verdict.
- **Run segment timing:** the run plays from about frame 282 (4.7 s) to 510 (8.5 s). Traffic physics differs between takes from the very first frame (full-frame MSE 500-1500 at 0-2.5 s in loco_*). The differences are background noise, not animation.
- **The brief's beat table is off for the jump:** touchdown and crater are at about 5.28-5.30 s (frame 317-318), not "~6.6 s". The Fall is about 3.1-5.25 s.
- **Landing is the only clip with a real difference.** Y is the correct impact grammar: compress on contact, brace, settle, rise. X has the inverted timing (stand, then crouch) and a late, fast rise. Neither is shippable yet: the rise in both is mostly hidden by dust, and the feet cannot be checked under the help box.
- **Biggest gap (testable):** in take Y, the crouch should start no later than 2 frames after the crater frame, and the rise should finish into Idle within 1.0-1.2 s of touchdown, not 1.6 s. Verify with a capture with the help box hidden (H) and the dust VFX disabled, from the side camera.

## Per-clip reply blocks (brief format)

```
CLIP      Land   (take Y = front B, left A, tq A; take X = front A, left B, tq B)
SCORES    Y: weight 3  readability 3  contact 3  foot ?(hidden)  arm 3  transitions 3  menace 3 | X: weight 2  readability 2  contact 2  foot ?(hidden)  arm 3  transitions 2  menace 2
DEFECTS   Y: rise to Idle ~1.6 s, mostly under dust (348-380); feet hidden by help box.  X: upright/stiff 321-333 after crater at 318 (front A, tq B, left B); late fold ~342-348; lopsided hold; ~12-frame pop-up 402-414 (front A).
WINNER    Y  -> front B / left A / tq A
WHY       Y compresses into a braced crouch on the contact frame, so the crater reads as caused by the Brute's mass; X stands tall through the explosion and crouches 0.4 s late. Both settle into Idle without a pop, but X's late quick rise adds a hitch Y does not have.

CLIP      Fall
SCORES    A = B (identical pixels)
DEFECTS   Difference not rendered in either take (MSE at compression-noise level 3.1-5.25 s, all angles).
WINNER    tie (unjudgeable as A/B)
WHY       The two takes are frame-identical through the whole air time. Whatever Fall clip was meant to differ is not what played.

CLIP      Run
SCORES    A: weight 3  readability 3  contact n/a  foot ?(hidden)  arm 3  transitions 3  menace 3 | B: same
DEFECTS   A/B: feet behind help box in all three angles; sprint occluded 9.6-10.0 s by tumbling vehicles.
WINNER    tie (front tie / left tie / tq tie)
WHY       Same 0.62 s cycle, same bob and arm-swing amplitude, clean Walk-to-Run blend in both, no measurable pop. The pose differences (A slightly more pitched, B elbows slightly wider) are real but too small to call.
```

## Decoded (director)

Key decodes the per-folder labels:

- **Land:** preferred take = r3 (hold-compressed Land v1) in all three angles, beats Land v3 (r4), high.
- **Run:** tie between Run v2 (r4) and Run v1 (r2/r3).
- **Fall:** r4 refit vs r3 rendered pixel-identical (tie).

Director decisions:

- Land v3 rejected; hold-compressed v1 stays.
- Run v2 ships on its better numbers (fit 4.35 vs 4.65 px, seam 0.46 vs 0.67), since the screen tie leaves it to the numbers.
- Fall r4 refit adopted (no warnings, identical on screen).
- Dense reader (1.65/1.85 px held-out) did not lower any fit. The AI takes limit the fit at 4.35-5.5 px for Run, StopLunge, Land; recorded as bar misses.

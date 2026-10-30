# In-game blind A/B critique, round 3 (Brute, UE 5.8 homage)

Critic: Opus 5.5 high, independent. Evidence was taken only from `blind-r3/critic/` (brief.md plus 9 case folders). Method: ffmpeg on CPU. I measured the per-frame A-B difference over the whole frame and over a crop around the subject, to find where the takes diverge. Then I built side-by-side contact sheets (4-60 fps, full frame and tight crops), measured frame-to-frame motion energy in crops around the subject, and measured the luminance onset of the dust effect. Takes were matched across angles by their pose at the same timestamps. All extracted frames have been deleted.

## Take matching across angles (labels are shuffled per folder)

| Clip | Take | front | left | tq |
| --- | --- | --- | --- | --- |
| Land | X: rises to idle | B | A | B |
| Land | Y: stays in a frozen crouch | A | B | A |
| Slap | Q: arm cocked back, strike lands on the effect | A | B | B |
| Slap | P: early sweep, then a hand-up flick | B | A | A |
| Clap | S: continuous wide windup | A | B | B |
| Clap | R: snaps overhead, frozen hold | B | A | A |
| StopLunge | not separable (see below) | - | - | - |

## Verdict table

| Clip | Preferred label per folder | Confidence | Evidence (seconds from film start) |
| --- | --- | --- | --- |
| Land (jump_*) | front **B** / left **A** / tq **B** (take X) | High | Both takes are byte-for-byte the same up to the crater (whole-frame diff about 2 until 5.15 s, then they diverge at 5.2 s). X drops into the crouch at 5.77-5.80 s. From 6.3 s it rises steadily, upright by 6.9 s and settled in idle by 7.0 s. Rise motion energy is 1.6-2.6 per frame with no spike, so there is no pop into idle. Y drops at 5.90-5.97 s and then holds the crouch: motion energy 0.6-0.9 from 6.0 to 7.3 s, which is the noise floor. That is a frozen hold of about 1.3 s. Y only starts to rise at about 7.35 s and is still crouched when the film ends at 7.5 s, 2.3 s after touchdown. Y also stays half-hidden behind the HUD box in the front and tq views; X comes up into clear view. |
| StopLunge (lunge_*) | front **tie** / left **tie** / tq **tie** | High (that they are equivalent) | In the subject crop the A-B diff stays at 2.4-4.7 from 1.5 to 2.62 s, the same as the noise floor before the move. Strips at 15/30/60 fps show the same plant/coil silhouettes frame for frame (front 2.16-2.43 s, left 2.58-2.86 s). From 2.65 s the divergence is environmental: the traffic barrel, truck and debris settle differently, for example the barrel is already flipped in one take at 2.696 s (left). The release and launch heights match at 2.816 s and 2.849 s in all angles. There is no visible pose difference to prefer. |
| Slap (combat_*) | front **A** / left **B** / tq **B** (take Q) | Medium | The dust effect starts at 2.417 s in both takes (measured luminance step from 80 to 83, then rising), so the hit time is fixed by the game. **Q** cocks the arm back from 2.10 to 2.38 s, then the palm sweeps through 2.42-2.48 s, onto the dust as it erupts (left). It ends arms-wide and settles by 2.80 s (motion energy 1.2-1.7). **P** sweeps across at 2.08-2.20 s, about 0.25 s before the effect. When the dust appears at 2.42 s, P's arm is already lifting away into a raised-hand flick (2.45-2.70 s, held about 0.2 s; looks like a wave). P also dips into the bottom-left corner behind the HUD from 2.05 to 2.45 s in tq and front, so the strike cannot be read from 2 of 3 cameras. P has the better body twist and weight (left 2.08-2.38 s), but it fails contact and readability. |
| Clap (combat_*) | front **A** / left **B** / tq **B** (take S) | Medium | The palms meet at about 4.15-4.17 s in both takes. The effect and camera shake hit at 4.20 s in both (motion energy jumps to 17-18 in every angle), so contact is equal. **R** throws the arms overhead in about 4 frames (front motion energy 7.1 then 9.8 at 3.73-3.77 s). It then holds that pose frozen from 3.83 to 4.03 s: energy 0.78-1.16, which is the idle floor (front about 0.85). The frozen hold shows in all three angles (left 0.76-0.98, tq 0.82-1.4; tq frames 3.80-4.00 s look identical). **S** keeps the windup moving through 3.73-3.97 s (front 2.4-4.7, tq 2.0-2.7) with no snap and no hold. R's overhead pose is the stronger thunderclap silhouette, but the snap plus 0.2 s freeze breaks the "no frozen holds / no pops" bar. Recovery after the clap (hands held together 4.2-4.45 s) is equivalent. |
| PunchR, PunchL, Smash | identical | High | Tight left-view strips at 0.45-1.55 s and 5.45-6.55 s show the same poses frame for frame. The only differences are vehicle and debris physics (1.2-1.5 s, from 6.1 s) and a slight idle-phase offset at the start of the film. |

## Notes and shared defects (present in both takes, not decided by the A/B)

- **Land:** both takes stand upright with arms spread for about 0.55 s after the crater (5.2-5.75 s), then drop into the crouch in about 4 frames. The impact is absorbed late and the drop is too fast for a multi-ton body. The crouch should start on the touchdown frame.
- **Framing:** the front and tq cameras keep the Brute at the bottom edge, under the HUD help box (jump landing, lunge coil, slap). That hurts readability in every take. Fix the camera or hide the HUD for these captures before the next round, or readability stays unprovable.
- **Land:** the dithered occlusion fade turns the Brute translucent in the dust from 5.8 to 6.3 s in both takes. Both takes have it.
- **StopLunge:** the "plant and coil" reads as a hunched run, not a plant. The root keeps travelling 1.8-2.78 s in both takes. If the two StopLunge candidates really differ, the difference is not reaching the screen; check the blend weight or the slot.
- **Slap Q:** the cocked arm is nearly static for 2.12-2.38 s. That is acceptable anticipation, but if the next iteration shortens it the strike will start before the effect time, and the take loses the sync it won on.

## Single biggest gap (testable)

Land take Y must start rising by 6.3 s (no more than 0.5 s after the crouch bottoms out). Its motion energy in the subject crop must stay above 1.5 between 6.0 and 6.9 s, and it must be fully upright in idle by 7.0 s. Take X already meets this, so the next round should keep X and fix the shared late absorption: the crouch must start on the touchdown frame (5.2 s), not 0.55 s after it.

## Decoded (director)

Labels per folder were decoded with `blind-r3/_director/KEY.json` (critic never saw it). Preferred take per clip:

- Land (jump_*): preferred = r3 (hold-compressed) in all 3 angles, beats r2 Land, high.
- Slap (combat_*): preferred = r3 (the v2r Slap, same file as r2), beats old, med.
- Clap (combat_*): preferred = r3 (hold-compressed), beats old, med.
- StopLunge (lunge_*): tie between hold-compressed and r2, high.
- PunchR / PunchL / Smash: identical (old in both).

Final shipping set = the r3 build: v2r Idle, Walk, Run, Slap, Fall; hold-compressed Land, Clap, StopLunge; old PunchL, PunchR, Uppercut, Lift, Throw, WallClimb, Jump, Smash, WallAttach.

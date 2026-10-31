# In-game blind A/B critique: Brute re-animation

Critic: Opus 5.5 (high), independent, deciding vote. Inputs read: only `blind/critic/brief.md` and the 24 `<group>_<angle>/A.mp4` / `B.mp4` pairs. All 48 files: 960x540, 60 fps, and the A and B in each pair have the same length.

## READ THIS FIRST: labels are not consistent across angles

Labels were randomized **per case folder**, so the same subject is sometimes `A` in one angle and `B` in another. I matched subjects across angles using pose content: distinctive poses at the same timestamp, plus how the A-minus-B silhouette signals correlate between angles (jump: front vs left r = -0.89, front vs tq r = -0.93, so jump_front is flipped). For wall, the end-of-run collateral-damage HUD agrees exactly: $50,791 = back B = backleft A = left A. **The winner column therefore names the winning subject per angle folder.** Always read the winner with its angle.

## Method

- Ran per-frame PSNR between A and B for every case, on the full frame and on a crop around the character. No pair is bit-identical: idle background PSNR is 39-45 dB, character crop 23-28 dB.
- Masked the green silhouette in OpenCV and traced its area, head top, width and centroid. Used these for idle breathing amplitude, walk width and bob phase, and combat crouch depth.
- Built dense contact sheets (6-30 fps crops) and three-angle sheets at matched timestamps for every move. Read every move from all three angles.
- Ground truth for "same clip": a stretch where the character crop is visually identical and PSNR is high. Examples: jump_left 1.8-4.0 s at 35-43 dB, smash wind-up 5.55-6.0 s.

## 1. Verdict table (one row per clip)

| Clip | Winner (per folder) | Confidence | Evidence (case, angle, seconds) |
|---|---|---|---|
| Idle | **B** in idle_front, idle_tq, idle_left | low-med | B: hunched forward, weight in front, head top travels 115-122 px (left/tq, 4.1-5.0 s), so it reads as breathing. A: upright and flared, head top moves only 115-117 px, nearly frozen. A shows mass width better, but reads static. |
| Walk | **front A / tq B / left A** (wide, ape-arm walk) | low-med | front A 2.5-3.2: arms swing wide of the lats, silhouette 191 px wide vs 117 for the other subject; tq B 2.5-2.9: hunched with arms hanging low. The other subject walks upright and compact, close to a human stride, with less menace. Feet are under the HUD help box in front/tq, so foot sliding is **unproven** for both. |
| Run | tie | low | loco tq/left 6.0-6.53: both are deep forward-lean charges with matching stride rate. front A has wider arms, B keeps its head lower. No pop at the walk-to-run (4.5 s) or run-to-sprint (8.5 s) blend in either. The sprint (9.6-10.2) is **unjudgeable**: tumbling cars hide the character in all angles. |
| StopLunge | **front B / tq A / left B** (wide plant) | med | lunge 2.05-2.65: this subject plants a wide split stance with arms out and a hand near the ground (left B 2.2-2.5, front B 2.05-2.5), which reads as braking and coiling. The other subject (front A, tq B, left A) folds into a featureless ball with its head tucked and the silhouette lost. |
| Jump (charge crouch + air) | tie (very likely the same clip) | med-high | jump_* 0.6-1.2: character crop 30-36 dB, poses identical. Air segment jump_left 1.8-3.0: 35-43 dB. lunge_front 2.9-4.3: air poses (arms overhead) match frame for frame. |
| Fall | tie (very likely the same clip) | med-high | jump_left 3.1-5.0: 35-42 dB, visually identical loop. |
| Land | **front A / tq B / left B** (3-point crater landing) | med | jump front 5.33-5.73: crouch, arms spread, hands down at the crater; tq B 5.33-5.73: fist planted on the ground. The other subject (front B, tq A, left A) has one arm thrust **straight up** at touchdown (front B 5.4-5.73), so the jump pose leaks into the impact and no hand or fist meets the crater. Winner caveat: it is still crouched at 7.25-7.5, more than 2 s after touchdown, so the rise to idle is never seen (see section 3). |
| PunchR | **front B / tq B / left A** (deep-commit version) | med | combat_left 0.58-0.72: full horizontal hook, arm extended across the body, torso twisted, hips leading. The other subject (left B) only swings the arm low by its side over 0.58-0.85, which reads weakly. |
| PunchL | **front B / tq B / left A** | low | combat_left 1.33: left arm extended about 0.13 s after input. The other subject's extension arrives at 1.67, about 0.47 s late. But the winner then folds over the car (left 0.95-1.2), and in front/tq its body sits in the bottom 25% of frame (head top y = 400-420 of 540, front 0.9-1.9). |
| Slap | **front A / tq A / left B** (upright version) | med | combat_left 2.40-2.55: arm sweeps into the dust ring, so it is at the contact spot when the effect fires. front A 2.1-2.4 and tq A 2.1-2.4: wide sweep fully in frame. The deep version is cut off by the bottom of frame in front/tq (front B 1.95-3.0 shows only a fist and shoulder), and in left A 2.55 its arm is already behind the body when the dust fires. |
| Clap | **front B / tq B / left A** (deep version) | low-med | combat front 3.85-4.05: arms raised in a high V above the head for the anticipation (left A 3.85-4.05: arm straight overhead). The other subject only spreads its arms to shoulder height. Both bring the palms together at about 4.2 when the effect fires. A bigger wind-up gives clearer anticipation and more menace. |
| Smash | tie (likely the same clip) | med | combat_* 5.55-6.0: wind-up and slam poses are visually identical in all three angles (front/left character crop 26-33 dB, the highest in the clip). Differences after 6.1 come from debris and the recovery blend, not from a different smash. |
| Uppercut | **front A / tq B / left B** (vertical launcher) | low-med | uppercut_left 2.17-2.33 and uppercut_tq 2.03-2.2: fist driven straight up overhead, so it reads as a launcher. The other subject (left A 2.17-2.5) goes near-horizontal with the arm forward-up, reading as a flying punch rather than an uppercut. In front B, a car and dust hide the character for 1.93-2.27, so that angle is unproven. |
| Lift (grab + carry) | **front A / tq A / left B** (arms-up hold) | **high** | grab_front 1.4-3.2: both arms locked overhead, holding the car. The other subject (front B, tq B, left A) stands with **arms hanging at its sides while the car floats above its head** (front B 1.4-3.2, tq B 1.7-2.9, left A 1.4-2.9). This is a hard contact defect and a veto. |
| Throw | **front A / tq A / left B** (overhead throw) | high | grab_left 3.2-3.67: car released from overhead with the arm at full extension, then a deep forward follow-through (3.8-3.93). The other subject swings sidearm at hip height (front B 3.4-3.6, left A 3.47) while the car starts above its head, so hand and car disagree. |
| WallAttach | tie (likely the same clip) | med | wall_back 1.3-2.47: attach slam and first grip match frame for frame. |
| WallClimb | **back A / left B / backleft B** (hand-over-hand, body on the wall) | low-med | The other subject (back B, left A, backleft A) raises **both** hands off the wall at once with fingers splayed, in a surrender/flail pose: back B 2.65-2.8 and 4.17-5.33, left A 4.33-5.33 with the torso pushed off the wall. The winner keeps one hand on the wall and alternates. It is compact, so its silhouette is weaker from the back. Top-out at 6.0-6.95 is identical in both. |

## 2. Per-group notes

- **idle**: Both loops are planted, with no foot drift visible at 0.5-5.5 s. Neither is clearly shippable. A is close to a held pose. B's breathing is more alive, but its arms hang in front of the thighs and hide some width. No loop seam visible in either over 6 s.
- **loco**: Walk is the only clear difference. The flared walk reads as a 2.6 m brute. The compact walk reads as a big man. Run: no meaningful difference. Sprint and stop: all angles are dominated by car physics and camera chaos. The settle into idle at 11.9-12.8 looks equally clean in both (loco_front/tq).
- **lunge**: The plant pose decides it. The ball crouch hides the head and arms completely in left/tq. The jump release at 2.8 and the air segment are identical.
- **jump**: Charge, air and fall are the same in both. Only Land differs. The winning landing has the right contact pose but holds the crouch too long. The losing landing's raised arm at impact is a contact error.
- **combat**: The two subjects are consistent styles. One "deep-commit" set bends far forward into the targets; the other "upright" set stays tall. The deep set wins PunchR, PunchL and Clap on strike readability and wind-up. The upright set wins Slap on contact and framing. **The deep set leaves the gameplay camera's sweet spot in front/tq for about 1 s (0.9-1.9 s) and again during the slap (1.95-3.0).** If the camera cannot follow, that alone may cancel its wins.
- **uppercut**: The vertical launcher is correct. The front camera is blocked by a thrown car in one subject, which is a camera/physics issue, not the clip.
- **grab**: Decisive. The arms-up subject is the only acceptable Lift and Throw.
- **wall**: Attach and top-out are the same. Climb differs in hand contact, and the flail version fails contact.

## 3. Clips where BOTH subjects are unacceptable or unproven

- **Sprint (Run clip at 27 m/s, loco 8.5-11.5 s)**: unjudgeable in both subjects and all angles. The character is hidden behind tumbling cars and motion blur (loco_* 9.6-10.2). Unproven means it fails.
- **Land**: the winner never rises before the film ends (still crouched at 7.5, more than 2 s after touchdown), so its transition to idle is unproven and may read as tired. The loser fails contact.
- **PunchR / PunchL / Slap framing**: one subject has weak strikes, the other drops below the gameplay camera's frame. Neither is a clean AAA read in all three angles.
- **Foot contact in general**: the semi-transparent control-help HUD box covers the feet in the front and tq angles of loco, combat and idle. Foot sliding and skating are **unproven** for every ground clip.

## 4. Global observations

- **Labels are randomized per angle folder**, not per group (confirmed in jump, wall, grab, combat, lunge). Any downstream tally that assumes "A" means the same subject across a group will be wrong. Use the per-folder winners above.
- **Camera**: the front/tq cameras are tight and chest-high. Any clip that bends low (the deep combat set) drops out of the bottom of frame. The sprint and uppercut shots are swamped by physics debris. The help-text HUD in the lower-left covers the legs. Re-capture with the HUD hidden ("H hide/show") before the next blind round.
- **Determinism**: traffic and debris diverge between takes (background PSNR 39-45 dB in idle, 13-20 dB after impacts), so not every pixel difference is animation. All verdicts above rest on character pose at matched timestamps.
- **Unchanged clips**: Jump (charge + air), Fall, Smash, WallAttach, and the wall top-out are visually identical in both subjects. No pair is byte-identical; the residual differences are traffic and debris.
- **Rate and blends**: no speed absurdities seen. No visible pops at the walk/run/sprint blends or at the stop-to-idle settle (loco 11.9-12.8). The worst blend is Land-to-idle, which never happens on screen in the winning subject.

## Biggest gap (testable instruction)

Re-film with the HUD hidden and add a stop-and-hold beat (3 s of Idle after the Land and after each loco speed). Then verify with a foot-pixel trace that planted feet move by no more than 2 px between contact frames. Do the same check on the Land crouch: it must rise to Idle within 1.2 s of touchdown.

## Decoded (director)

The critic judged blind with labels shuffled per case folder. The key (`_director/KEY.json`, not given to the critic) decodes every per-folder winner.

| clip | decoded winner | confidence | ships |
| --- | --- | --- | --- |
| Idle | NEW (all 3 angles) | low-med | new |
| Walk | NEW (all 3) | low-med | new |
| Run | tie (sprint hidden by cars in every angle) | low | new (tie rule) |
| StopLunge | NEW (all 3) | med | new |
| Jump | tie, same old clip in both | med-high | old (no new take) |
| Fall | tie (indistinguishable at capture distance) | med-high | new (tie rule) |
| Land | NEW (all 3) | med | new |
| PunchR | OLD (all 3) | med | old |
| PunchL | OLD (all 3) | low | old |
| Slap | NEW (all 3) | med | new |
| Clap | OLD (all 3) | low-med | old |
| Smash | tie, same old clip in both | med | old (no new take) |
| Uppercut | OLD (2 of 3 angles; the critic's front-angle match was inconsistent with the key) | low-med | old |
| Lift | OLD (all 3) | high | old |
| Throw | OLD (all 3) | high | old |
| WallAttach | tie, same old clip in both | med | old (no new take) |
| WallClimb | OLD (all 3) | low-med | old |

Rule: a new clip ships only if it wins or ties the in-game blind A/B. Round 3 (hold-compressed Land, Clap, StopLunge variants) is being captured and judged before the final build.

Critic's case-design notes (hide the help text with H, add a 3 s idle hold after landing/locomotion) are recorded for the next capture-set revision; the cases were kept identical for old and new in this run.

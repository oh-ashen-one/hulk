# Brute Seedance round (owner brief 2026-10-30 11:45 EDT)

Hulk-in-Manhattan fan homage; not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

Owner's words: whenever we use video2rig we are trying to increase the quality of the animations, the 3D and the fluidity; the current
clips look blocky and glitchy. Generate Seedance takes that look much better, then run the pipeline. This replaces the MiniMax/fal brief
of `PLAN.md` for every clip from here on. Error log that led here: `HANDOFF.md` "Fidelity gates are not quality gates" and the
operating-rules section of the same name (agents-md PR #36).

## Rules for this round

- Provider: Seedance 2.5 on Higgsfield (`generate_video`, model `seedance_2_5`, mode `omni_reference`, `start_image` = our start
  picture, 720p, 16:9, 5 s, audio off, literal prompt with the preset recommendation declined). 35 credits per 5 s take; balance at start
  442.64. 1080p costs 80 and is not used (the reader reads 720-high panels).
- One take at a time. The take is judged on its own look FIRST (frames beside the old clip's strip): weight, anticipation, follow-through,
  fluidity, no stiffness. A take that is not visibly better than the old clip is not fitted, whatever `check` says.
- Then the pipeline as before (size gate, check, fit, refine, export, build) with close-up captures, and a blind A/B whose ship rule is
  "visibly better", never "tie". Timing data moves with the take (`measure_timing.py`, rate cap 1.6).
- The mesh itself is out of scope for video2rig (it moves bones only); the model is the Customuse "Emerald Behemoth" (`docs/brute/ASSETS.md`).
  A mesh upgrade is a separate job for the owner to call.
- GPU: fits, Blender and captures go through the gates (cap 3, util < 90, no capture while the STREAMING flag is `manual`); Markhor's
  and Dragon's readers run today, so GPU steps queue behind them. Generation and the first-look judgement need no GPU.

## Order (most visible upgrade first, budget ~12 takes)

Smash (pilot), PunchR, PunchL, Uppercut, Jump, Land, Lift, Throw, Clap, Slap, StopLunge, Run. Idle, Walk, Fall, WallAttach, WallClimb
only if credits remain (WallAttach/WallClimb need a wall in the picture; see `prompts/INDEX.md` risks).

## Ledger

| take | job | credits | first look (director) | check | fit | A/B | ship |
| --- | --- | --- | --- | --- | --- | --- | --- |
| smash_sd_v0 | 2e1a88e5 | 0 (refused, status nsfw, not charged) | prompt had "violent", "slams", "snarl", "glare": moderation refusal | | | | no |
| smash_sd_v1 | a7c145a4 | 35 | size gate PASS 1.08; sharp, model intact; wind-up 0.5-0.9 s, FROZEN 1.0-1.6 s at the top, slam 1.6-1.9 s (fast, deep fold), FROZEN 2.2-3.8 s in the crouch, rise 3.8-4.8 s. Slam beats the old clip; the two freezes are a prompt problem (next prompts: "never pauses or freezes"). Fitted with --compress-holds. | PASS 0.69 % | standard 4.88 px / 2 warn; joint ranges widened per clip (creature.json clips.smash_sd_v1.joints: shoulders 60 deg, spine 52, right foot 46) -> 4.65 px / 1 warn, the 54 deg arm jump gone; frame 42 fists still a head low (fit limit, not range). SHIPPED fit = -wide, refine seam 0.00 drift 6.9 mm toe 0.0, GLB motion-sd/Brute_smash-v2r.glb (Smash_v2r_v2_refined.blend) | pending close-up A/B | |
| punchr_sd_v1 | 941e6204 | 35 | size gate 1.25 (near the limit); REJECTED at first look: he turns 90 deg to throw the punch (front camera sees his profile at 1.4-2.6 s), freezes at full extension 1.8-2.6 s, then turns back. Not fitted. | | | | no |
| punchr_sd_v2 | 090730e9 | 0 (refused, nsfw, "straight right punch ... knuckles toward the camera") | not generated | | | | no |
| punchr_sd_v3 | 54133316 | 0 (refused, nsfw: "toward the front camera" phrasing) | not generated; "shadow boxing" wording + facing pinned ("never turns, never pivots, never steps"), fist to the hip, "arm snaps straight back without stopping" | | | | |
| punchr_sd_v4 | e0590850 | 35 | v1 wording that passed ("at the empty air in front of him") + neutral orientation sentence ("same orientation as the first frame ... no turning, no pivoting, no stepping"), fist to the hip, snaps back without stopping | | | | |
| (punchr_sd_v4 first look) | | | size gate 1.20; sharp, model intact, good load-up and a fast strike at 1.5-1.7 s, BUT he again turns ~90 deg to deliver it (front panel sees his profile at 1.8-2.5 s) and freezes 1.9-2.3 s. Seedance frames a straight punch by rotating the body (2 of 2 real takes). Decision: fit it anyway and lock the root yaw in refine (the limb motion is good); if that fails, PunchR keeps the old clip. | | | | |
| jump_sd_v1 | 87802bfa | 0 (refused after rendering, status nsfw, not charged) | not generated | | | | no |
| jump_sd_v2 | 3945c169 | 0 (refused after rendering, nsfw, not charged) | not generated; Jump = two refusals, keeps the old clip for now (output classifier, not the prompt) | | | | no |
| clap_sd_v1 | 6f8a8e1e | 35 | arms wide, one fast clap at 0.9 s, bounce apart, settle | | | | |
| (punchr_sd_v4 fit) | | | | PASS 0.47 % | 2.26 px, 1 warning, outline 0.896/0.908 (the body turn is consistent in both panels, so the fit is the best of the run). Refine with --lock-yaw (new flag, being added) to keep the game facing. | | |
| (punchr_sd_v4 refine) | | | | | refine --lock-yaw (new flag, tools/brute/v2r/refine_brute.py: Hips world yaw and travel turned back to frame 0's facing, 83.8 deg removed, limb motion kept: hand moves 1.15 units forward at the strike either way), seam 0.00, drift 6.7 mm, toe 0.0; exported motion-sd/Brute_punchr-v2r.glb (PunchR_v2r_v3_refined.blend). Risk for the critic: the hips lunge ~0.6 units forward-left and return inside the 18-frame blend. | pending close-up A/B | |

# measure_timing.py tests (2026-10-29)

Homage fan game: not an official Marvel game, no affiliation.

## What was run

```
Blender -b --factory-startup -P tools/brute/v2r/measure_timing.py -- ~/hulk-scratch/brute_v5/brute.glb \
    --all --out <scratch>/v5_glb_timing.json --dump <scratch>/v5_glb_tel.json --check-today 0.15      # exit 0, CHECK OK
python3 tools/brute/v2r/measure_timing.py --telemetry <scratch>/v5_glb_tel.json ...                     # same numbers, no Blender
```

Blender 5.2.0, one instance of mine (one other session's Blender was running). The v5 output went to scratch, not to
`unreal/WebHomage/Config/BruteClipTiming.json`: the repo has no timing file, so the game keeps today's constants.

## Old clips (brute_v5) vs today's constants

Tolerance 0.15 s. Worst difference is 0.100 s (Uppercut To). Rates are unchanged because every clip is the same length as
today's (the 20 % rule does not apply).

| act / segment | field | today | measured | diff | note |
| --- | --- | --- | --- | --- | --- |
| PunchR | from / to / hit | 0.45 / 1.40 / 1.00 | 0.417 / 1.367 / 0.967 | -0.033 | peak right-hand speed 15.9 m/s at frame 29 |
| PunchL | from / to / hit | 0.45 / 1.40 / 1.00 | 0.417 / 1.367 / 0.967 | -0.033 | peak left-hand speed at frame 29 |
| Slap | from / to / hit | 0.30 / 1.70 / 0.90 | 0.333 / 1.733 / 0.933 | +0.033 | right hand; next bout (left-hand tail) at 1.767 |
| Clap | from / to / hit | 0.10 / 1.30 / 0.70 | 0.100 / 1.300 / 0.700 | 0 | palms meet at frame 21 (gap 0.16 m) |
| Smash | from / to / hit | 0.40 / 2.00 / 1.17 | 0.397 / 1.997 / 1.167 | -0.003 | left fist reaches the street at frame 35 |
| Uppercut | from / hit | 0.15 / 0.60 | 0.150 / 0.600 | 0 | peak 29.5 m/s at frame 18 |
| Uppercut | to | 1.40 | **1.300** | **-0.100** | clamped: the generated tail starts a second swing at 1.30 (right hand 0.7 to 16.8 m/s by 1.53) |
| Grab | from / to / hit | 0.60 / 2.40 / 2.40 | 0.600 / 2.400 / 2.400 | 0 | arms overhead (85 % of max) at frame 72 |
| Carry | from / to | 2.40 / 2.95 | 2.400 / 2.967 | +0.017 | to = last frame before the end |
| Throw | from / to / hit | 0.00 / 1.46 / 0.45 | 0.000 / 1.467 / 0.467 | +0.017 | to clamped at the clip end |
| JChargeLo | seg | 0.17 | 0.167 | -0.003 | hips' high point before the crouch |
| JChargeHi | seg | 2.45 | 2.500 | +0.050 | deepest crouch (hips over the lowest foot 0.488 m) |
| JLaunch | seg | 2.55 | 2.533 | -0.017 | first frame with hips rising above 0.5 m/s |
| JApex | seg | 3.17 | 3.167 | -0.003 | hips highest |
| AttachStart | seg | 0.20 | 0.200 | 0 | impact - 0.5 s (analyze_clips 'reach') |
| WAttachImpact | seg | 0.70 | 0.700 | 0 | both fists within 8 cm of their highest point |
| WClimbImpact2 | seg | 1.50 | 1.467 | -0.033 | second fist-height peak (left hand 0.43 m over the head) |
| WClimbLo | seg | 0.55 | 0.550 | 0 | impact - 0.15 (today's offset) |
| WClimbHi | seg | 1.85 | 1.817 | -0.033 | impact2 + 0.35 (today's offset) |
| LandStart | seg | 0.35 | 0.400 | +0.050 | lowest foot back on the floor (within 3 cm of settled) |
| LungeStart | seg | 1.00 | 1.000 | 0 | **cal**: coil 1.567 - 0.567. Exact by construction, so this is not a validation |

HIT table proposal (assemble_motion `HIT`): PunchL/R 0.967, Slap 0.933, Clap 0.700, Smash 1.167, Uppercut 0.600,
Throw 0.467, Land 0.467. Today's values are 1.0 / 0.9 / 0.7 / 1.17 / 0.6 / 0.45 / 0.5.

## Where a pure animation event and today's constant disagree

- **To is not a settle event.** If To meant "striking hand under 10 % of its peak" (the suggested semantic), the values
  would be: Slap 1.10 (today 1.70), Clap 0.73 (1.30), Smash 1.20 (2.00), Uppercut 0.70 (1.40), Throw 0.93 (1.46). PunchR
  never drops under 10 %: its minimum after the hit is 1.59 m/s against a 1.585 m/s threshold. Each of today's To values
  includes a hold the game chose to show: the slap arm coming down, the smash fists held in the street, the clap arms
  opening, the uppercut held overhead, the throw's heavy recovery. So To = hit + today's recovery span. That keeps
  ActDur, the act lockout and therefore gameplay, the same. It is then clamped by measured events: the clip end, the next
  motion bout, and never before the follow-through ends.
- **From** is today's wind-up lead (Hit - From) placed before the measured hit. That keeps ActHitAt, the time from
  button press to connect, exactly as it plays today. Throw is the exception: it always starts at 0, because the take
  is cross-faded from the carry pose.
- **Uppercut To (-0.10)**: today's 1.40 plays 0.1 s into a second swing that the generator added. The measured value
  stops before that swing starts.
- **StopLunge** has no event at today's 1.0 s (it is mid-stride, between foot contacts at 1.03 and 1.27). So the start
  is tied to the coil (the start of the biggest hips descent) with an offset calibrated on v5.
- **LandStart +0.05**: today's 0.35 is 0.05 s before the feet touch down (0.40) and 0.08 s before the hips' lowest
  point (0.43).
- The generic `feet_off` / `feet_on` diagnostics under `measured` are unreliable on clips with vertical root drift
  (Jump, Wall: the Cartwheel takes move the armature up) and on stance shuffles. No written value uses them.

## Rate rule check (synthetic)

These clips were resampled from the v5 telemetry to test the rule. They are not real clips.

| clip | stretch | rate | from / hit / to | hit game-time (today) | act game-time (today) |
| --- | --- | --- | --- | --- | --- |
| PunchR | x1.5 (> 20 %) | 2.401 | 0.608 / 1.433 / 2.033 | 0.3436 (0.3438) | 0.5935 (0.5937) |
| Smash | x1.1 (< 20 %) | 1.4 (kept) | 0.530 / 1.300 / 2.130 | 0.5500 (0.5500) | 1.1429 (1.1429) |

## Selection

- Default with `clips_meta.json` beside the glb: only clips whose `src` contains `v2r` are written. On v5 there are
  none, so it prints `NOTHING TO WRITE` and writes no file.
- `--clips Slap,Jump` writes acts `[Slap]` and segments `[JApex JChargeHi JChargeLo JLaunch]`.

## C++ side

- `unreal/WebHomage/Scripts/build_editor.sh` result: **Succeeded**. BruteCharacter.cpp compiled with no warnings. Log:
  `<scratch>/build_editor2.log`.
- The first attempt failed. UE 5.8 JSON object keys are `TSharedString`, so the keys are now converted with `FString(KV.Key)`.
- Every act and segment key the tool writes is accepted by `LoadClipTiming`. This was checked by parsing the .cpp.
- Not run in game. No engine or editor was launched.
- Not done: an FBX cross-check (`brute_anim.fbx`, the file UE imports). The machine was already at the renderer cap:
  another session's Unreal capture plus another session's Blender.

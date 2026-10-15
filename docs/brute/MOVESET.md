# Brute moveset (as built, 2026-10-15)

Source: `unreal/WebHomage/Source/WebHomage/Brute/BruteCharacter.cpp` (tuning UPROPERTYs at the top of the header; a few can be
overridden with `-WHBruteTune=Name=V,...`). Units: metres, seconds. Gravity 22 m/s^2 (reads heavy).

## Controls

| Action | Keyboard / mouse | Pad |
|---|---|---|
| Move / look | WASD / mouse | left / right stick |
| Sprint (knocks cars aside, crowd scatters) | Shift | R2 or L3 |
| Hop | tap Space | A |
| **Super jump** | hold Space (charge 0.85 s, crouch + meter), release | hold A |
| **Leap chain** | after a super jump, press and keep holding Space through the landing | hold A |
| Air dash (x2 per jump) | Shift in the air | R2 in the air |
| **Grand slam dive** | RMB / C / Ctrl in the air (>= 2.5 m up) | Y in the air |
| Wall run | sprint into a facade (> 3.5 m tall) | R2 + stick |
| Wall kick | Space on the wall | A |
| **Punch, punch, SLAP** combo | LMB (x3) | X |
| **Ground grand slam** (overhead double-fist smash) | RMB / C on the ground | Y |
| **Thunderclap** (forward cone, 32 m) | F | R1 |
| **Grab a car** / throw it where the camera looks | E (then E or LMB) | B |
| Hide the controls card | H | |

## Numbers

| Move | Value |
|---|---|
| Walk / run / sprint | 7 / 13 / 27 m/s (traffic drives 9-16 m/s) |
| Super jump, full charge | 40 m apex, 100 m range on the flat (vz 42, vh 26) |
| Running super jump (sprint into the charge) | x1.15: 46 m / 115 m |
| Leap chain | +10 % per link (max +30 %), each link re-launches at 80 % charge: measured 40 -> 44 -> 48 -> 52 m apex, 100 -> 128 m range, 440 m covered in 4 links |
| Air dash | 24 m/s along the stick / camera, 0.3 s low gravity |
| Wall run | 18 m/s straight up; pops over the roof edge (8 m/s in, 11 m/s up); measured 24 m setback -> caught the next face -> 73 m roof |
| Crater landing | landing faster than 17 m/s: crater r = clamp(0.5 x vz, 7, 22) m, cars thrown 24 m/s + 16 up |
| Grand slam dive | 60 m/s down; crater r = 14 + 0.35 x drop (16-30 m), cars 34 m/s + 24 up |
| Punch / slap | 3.6 m / 5 m reach cone, cars 30 / 34 m/s |
| Ground grand slam | crater r 13 m in front |
| Thunderclap | 32 m forward cone (cos 0.62), cars 42 m/s + 11 up |
| Throw | 58 m/s along the camera (+6 deg), spinning; thrown cars blast on impact > 14 m/s |

Every impact also: knocks nearby pedestrians over (tumble, lie, gone) and makes walkers within 2.5 x radius + 15 m turn and run;
adds to the collateral counter; camera trauma shake + FOV punch.

## Known gaps (next loop)

- No melee enemies yet (milestone 4: cops / SWAT); hits only affect cars, props and pedestrians.
- Buildings do not break (milestone 3: destructible proxies).
- Rigid-part body: elbows / knees show small seams on big bends; no facial animation.
- Wall run only goes straight up (no diagonal / sideways runs); no ledge hang.
- The camera can sit inside tree canopies (trees have no collision).
- Thrown cars use simple box physics.

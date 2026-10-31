# Brute licensed-asset ledger

Hulk-in-Manhattan fan homage. Third-party assets used by the Brute, with source, licence and where they live (raw packs never go in this public repo).

## 2026-10-31 — Paragon: Rampage (rock "Elemental" skin), branch character-enhancement

- Source: Fab listing 0807cf74-08fd-4a33-8c8d-f33c9439fb1f, "Paragon: Rampage" by Epic Games, free, Standard License (Unreal Engine use only; the PARAGON name may not be used in titles or ads). Fab lists it Windows-only, so the Mac launcher hides every project; added through the UE 5.8 editor's Fab panel into an empty project, then copied to `Content/ParagonRampage` (3.2 GB).
- Not in git: `Content/` is ignored in this public repo; binary snapshots belong in the private `webhomage-unreal-content` repo.
- Used: `Skins/Tier2/Elemental/Meshes/Rampage_Elemental` + its own materials. Our 17 clips retargeted (auto IK Rig + IK Retargeter, `tools/brute/retarget_rampage.py`) into `/Game/Brute/Rampage`. Originals untouched. In game behind `-WHBruteRampage` / `Play-Rampage.command`.
- Not yet verified in a capture (GPU gate full at the time); hand-contact moves (Clap, Lift, Smash) may need retarget fixes.

# Brute licensed-asset ledger

Hulk-in-Manhattan fan homage. Third-party assets used by the Brute, with source, licence and where they live (raw packs never go in this public repo).

## 2026-10-31 — Paragon: Rampage (rock "Elemental" skin), branch character-enhancement

- Source: Fab listing 0807cf74-08fd-4a33-8c8d-f33c9439fb1f, "Paragon: Rampage" by Epic Games, free, Standard License (Unreal Engine use only; the PARAGON name may not be used in titles or ads). Fab lists it Windows-only, so the Mac launcher hides every project; added through the UE 5.8 editor's Fab panel into an empty project, then copied to `Content/ParagonRampage` (3.2 GB).
- Not in git: `Content/` is ignored in this public repo; binary snapshots belong in the private `webhomage-unreal-content` repo.
- Used: `Skins/Tier2/Elemental/Meshes/Rampage_Elemental` + its own materials. Our 17 clips retargeted (auto IK Rig + IK Retargeter, `tools/brute/retarget_rampage.py`) into `/Game/Brute/Rampage`. Originals untouched. In game as the default skin (`-WHBruteSkin=Rampage`).
- **Default Brute body since 2026-10-31** (owner): Play-Brute.command uses it; `-WHBruteSkin=Brute` restores the original. Without the pack the game falls back to SK_Brute. Verified in captures and owner play (crooked-run fix: retarget aligns rest-pose facing, see tools/brute/retarget_paragon.py).

## 2026-10-31 — Paragon: Crunch (base mesh), branch character-enhancement

- Source: Fab listing c23ee3a7-4a73-4a83-9061-30b682d269f8, "Paragon: Crunch" by Epic Games, free, Standard License (Unreal Engine only; no PARAGON name in titles/ads). Added by the owner through the UE 5.8 editor's Fab panel (empty RampageDrop project), copied to `Content/ParagonCrunch` (2.0 GB). Not in git.
- Used: `Characters/Heroes/Crunch/Meshes/Crunch` + own materials; 17 clips retargeted FK-only by `tools/brute/retarget_paragon.py` (`BRUTE_SKIN=Crunch`) into `/Game/Brute/Crunch`. Was in game behind `-WHBruteSkin=Crunch`. Verified in a capture: 2.61 m, upright, idle and run.
- Removed locally 2026-10-31 (owner kept Rampage); re-add via Fab + `BRUTE_SKIN=Crunch` retarget if wanted. `-WHBruteSkin=Crunch` still works then.
- Other skins in the pack: Titanium, Military, GoldenGloves, Valentine (Tier 1); Black Site, Crash Site (Tier 3).

# Brute — rolling handoff (started 2026-10-15)

Owner direction 2026-10-15 (verbatim intent): replace all of Spider-Man with a big
green Hulk character. No swinging — he stomps, jumps and leaps around as his mode
of transportation. That is the scope of the FIRST overnight loop: complete removal
of Spider-Man and swinging, replaced by a big brick Hulk jumping and running around.
**The owner said: do not start yet.** Prep only until an explicit go.

Read `docs/brute/BRIEF.md` first (design, milestones, AI roles, house rules).
This loop = brief milestones 1+2 (Brute walks, Brute moves), plus removing the
Spider-Man hero and web-swinging as the default.

## Repo facts
- `oh-ashen-one/hulk` is a standalone repo: main = single-commit 1.4 GB snapshot of
  spider-man-2 main `0ca553f` (the finished Unreal 5.8 port) without `docs/night1`.
  Full history stays in spider-man-2. No dependency on the Invincible project —
  do not read or touch `/Users/midir/spider-man-2-invincible` or that repo.
- `Content/` is git-ignored everywhere; `unreal/WebHomage/Scripts/build_manhattan.py`
  regenerates every asset (see `unreal/WebHomage/CONTENT.md`).
- Work branch: `brute`. Merging to `main` needs explicit owner permission.

## Verified state (Studio, M3 Ultra, checkout `/Users/midir/hulk`)
- Editor C++ compiled OK 2026-10-15: `unreal/WebHomage/Scripts/build_editor.sh`
  printed `OK: UnrealEditor.modules -> libUnrealEditor-WebHomage.dylib`
  (log: `~/hulk-logs/compile.log`).
- Unreal Content: NOT built yet. Nothing launched, captured or played.

## Next steps, in order (after the owner says go)
1. Content rebuild (hours; headless; one Unreal at a time via the shared GPU slot):

   ```bash
   cd ~/hulk && SM2_MANHATTAN_SCR=~/hulk-scratch/manhattan \
     SM2_WATER_SCR=~/hulk-scratch/water SM2_LIFE_SCR=~/hulk-scratch/life \
     nohup caffeinate -s python3 unreal/WebHomage/Scripts/build_manhattan.py \
     > ~/hulk-logs/content.log 2>&1 &
   ```

   Hulk-owned scratch dirs on purpose: never share `~/sm2-n1/_scratch/manhattan`
   state with other sessions. The characters step reads P2 staged inputs read-only.
2. Smoke: guarded `-game` launch of the built Manhattan, screenshot, confirm the
   existing Spider-Man hero still works before changing anything.
3. The loop itself, small verified stories, one commit each, on `brute`:
   - Remove the web-swing hero as the default (flag-off first, delete later).
   - Placeholder Brute: ~2.5 m green blocky brawler through the existing character
     pipeline (`Scripts/build_characters.py` path), existing chase camera.
   - Traversal: sprint (knocks cars aside), charged super jump (~40 m vert /
     100 m horiz), leap chains, air dash, landing shockwave/crater, wall run later.
   - Capture suite per move + an independent critic pass, per the brief's
     milestone rules.
4. Push after every session; update this file in the same commit.

## House rules that bit before (do not relearn)
- Shared GPU coordinator `~/.cache/gpu-slot`, hard cap 2 engines, SIGTERM then
  wait 60 s. Kill ONLY by exact PID of processes this task started — a pkill
  pattern once hit another session's push.
- Perf numbers only from a desktop-session launch (`open -n -W -a`), never SSH exec.
- The Studio's /bin/bash is 3.2 (no mapfile); its zsh login shell breaks `grep -q`
  exit codes over ssh — wrap remote checks in `bash -c`, and prefer scp'ing files
  over heredocs through ssh (quoting mangles them).
- GitHub refuses single pushes > 2 GB; the LFS budget is exhausted. Scripts stay
  the only source of truth for content.
- Logs live in `~/hulk-logs/`; scratch in `~/hulk-scratch/` (disposable).

# GPU launch rules (tools/gpu)

Hulk-in-Manhattan fan homage tooling. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

State as of 2026-10-29 23:20 ET. This page records the owner's decision and the rule set the code in this folder enforces.

## Owner decision, 2026-10-29 23:20

The owner set this for an overnight unattended run across three Claude Code sessions: "do the maximum amount that is safe at the same time."

The evidence behind it:

- After the 10:17 reboot there were 98 gated launches and 2841 GPU-watchdog samples, with zero warnings and zero trips.
- From 10-02 to 10-28 the regime was cap 4 with a tripwire.
- The 10-29 wedge (03:23 to 10:17, with a power-button reset) had three causes:
  - 5 or more GPU clients were running, including Metal/MPS trainers that nobody counted.
  - There were 15 cold `-game` launches back to back, about 34 GB each, with zero gaps at 100 % util.
  - The display was asleep.

The decision: a machine-wide cap of **three** renderer-bearing GPU clients, with a tripwire on the GPU watchdog. The tripwire demotes the cap to 2 on any watchdog warning and refuses all launches on a trip. MPS trainers stay serialized with engine launches through the existing util gate. The 20 s gaps, the per-session 10/h budgets and the frame-1 watchdog are unchanged.

## Rule text (other sessions should mirror this verbatim)

```
GPU launch rules (owner 2026-10-29 23:20, supersedes "hard cap 2"):
1. Cap: at most THREE renderer-bearing GPU clients machine-wide. Count every Unreal editor/-game, Godot, Unity editor/player,
   *-Shipping / packaged game, Blender, owner game .exe (CrossOver/Wine), and every MPS/Metal/torch trainer (video2rig,
   reader.train, torch). A child of a counted client folds into its parent. Before a launch: clients >= cap -> do not launch.
2. Tripwire: read ~/.cache/gpu-slot/gpu_watchdog.json at every launch decision.
   trip set (or tripped true)                        -> refuse EVERY launch until the owner clears it (even if the file is stale).
   warn non-null, hang_strikes > 0, any stuck_since  -> cap 2, print why.
   file missing, unreadable, or updated > 120 s ago  -> cap 2 ("watchdog stale").
3. Util gate: GPU "Device Utilization %" < 90 on three readings 5 s apart, else wait (up to 10 min) or refuse. This keeps
   MPS trainers serialized with engine launches: never launch into a GPU at >= 90 %.
4. Gap: >= 20 s since the last engine launch anywhere (~/.cache/gpu-slot/last_launch; stamp it at every launch).
5. Budget: at most 10 engine launches per session per rolling hour; 30 s cool-down after each capture.
6. Frame-1 watchdog: no first-frame log line within 120 s -> SIGTERM, wait 60 s, SIGKILL only if still alive; never retry.
   A launch that never reaches frame 1 stops all launches machine-wide.
7. Unchanged: an engine stuck exiting (ps E/Z) refuses every launch (pause, notify the owner); PAUSED is never cleared by an
   agent; STREAMING flag / 11-13 ET window frame caps; never auto-relaunch after two crashes; no OS dialogs; headless/offscreen
   only; kill only PIDs you started (SIGTERM first).
```

## What enforces it here

| Rule | Where | How |
| --- | --- | --- |
| Cap 3, client counting | `gpu_gates.py` (`MAX_CLIENTS`, `client_kind`, `gpu_clients`) | `check` refuses (exit 3) when clients >= effective cap and prints them |
| Watchdog tripwire | `gpu_gates.py` `effective_cap()` | returns `(cap, reasons)`: 3; 2 when demoted; 0 on a trip. Read before the process gates and again after the util wait |
| Capture slots | `gpu_slot.py` `effective_slots()` | `GPU_SLOT_CAPTURE_SLOTS` (default 3) is clamped to `effective_cap()` at every acquire attempt. It counts every held slot, so a demotion while three run lets no new capture in until fewer than two are held. On a trip nothing acquires: it waits, then exits 75 (`wait-timeout`, logged with `cap=0` and the reason). If `gpu_gates` cannot be imported, the clamp is 2 |
| Util < 90 x3 | `gpu_gates.py` `util_gate()` | polls every 15 s, for up to 10 min |
| 20 s gap | `gpu_gates.py` `wait_gap()` / `stamp` | `run_game.sh` waits out the gap and stamps `last_launch` |
| 10/h budget, 30 s cool-down | `tools/brute/v2r/ab_ingame.py` `Budget` | per `run` |
| Frame-1 watchdog | `unreal/WebHomage/Scripts/run_game.sh -firstline` | `capture.sh` passes it for every Brute script run |
| Stuck engine | `gpu_gates.py` `stuck_engines()` | refuses |

`tools/brute/capture.sh` runs `gpu_gates.py check` before it asks `gpu_slot.sh capture` for a slot. `ab_ingame.py run` runs the same gates in `preflight` before every case.

Commands:

```
python3 tools/gpu/gpu_gates.py cap       # "cap N" and the reasons; exit 3 on a trip
python3 tools/gpu/gpu_gates.py status    # effective cap, clients, util, last launch
python3 tools/gpu/gpu_gates.py check     # exit 0 go / 3 refused
GPU_SLOT_DIR=~/.cache/gpu-slot python3 tools/gpu/gpu_slot.py status   # slots in use / effective / configured + clamp reason
```

Environment: `GPU_GATES_MAX_CLIENTS` (default 3) still overrides the cap, but a demotion still caps it at 2. The other settings are `GPU_GATES_WATCHDOG_JSON` (default `~/.cache/gpu-slot/gpu_watchdog.json`) and `GPU_GATES_WATCHDOG_STALE_S` (default 120). `GPU_SLOT_CAPTURE_SLOTS` defaults to 3.

## Tests (offline; nothing is launched)

- `tools/brute/v2r/test_ab_ingame_gates.sh` has 55 checks. It uses fake ps, ioreg and watchdog JSON. It covers:
  - cap 3, with a refusal at 3 clients;
  - demotion to 2 on warn, hang strike, stuck_since, a stale or missing or unreadable file, and an env override;
  - refusal on a trip, including a stale file that says trip and a trip that appears during the util wait;
  - the `cap` subcommand;
  - `capture.sh` and `ab_ingame.py run` refusing on a trip.

  The legacy cap-2 cases are pinned with `GPU_GATES_MAX_CLIENTS=2`.
- `tools/gpu/test_gpu_slot.sh` has 47 checks. Sections (a) to (c) are the lock mechanics with two slots. Section (d) covers:
  - 3 concurrent captures by default;
  - the clamp to 2 on warn, strike, stuck, old or missing;
  - a demotion while three run;
  - a trip, which exits 75 without running the command.

## The machine-wide wrapper

Other sessions call `~/.cache/gpu-slot/bin/gpu_slot.py`. It is a different, newer tool, deployed by `tools/gpu/install.sh` from `oh-ashen-one/claude-code-game-builder`. Commit `a017f67` on branch `opus/gpu-cap3-tripwire` gives it the same semantics, and that commit was deployed on 2026-10-29 at 23:49 ET. The details:

- 3 slots by default, also used as the foreign-client cap.
- `watchdog_cap()` re-reads the watchdog JSON at every acquire and every gate poll.
- A new `gpu_slot.sh cap` subcommand.

The previous file is kept as `~/.cache/gpu-slot/bin/gpu_slot.py.bak-20261029-cap2`. The rule text is also in `~/.cache/gpu-slot/RULES-2026-10-29.md`.

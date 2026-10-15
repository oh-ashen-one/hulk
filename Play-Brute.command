#!/bin/bash
# Hulk-in-Manhattan fan homage (unofficial, non-commercial; see docs/brute/BRIEF.md and DISCLAIMER.md).
# Owner playtest: the Brute in the whole Manhattan island, starting in the Times Square plaza. 1920x1080 windowed, 60 fps cap.
# Runs through the guarded launcher (shared GPU coordinator ~/.cache/gpu-slot): it refuses to start while another engine or GPU
# holder is running, and stops the game gracefully if the shared GPU is PAUSED. Esc opens the settings menu / releases the mouse.
# Options: append  -WHSpidey  to play the old web-swinging hero instead;  /Game/Showcase/Maps/Manhattan_Island_Night  for night.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
UE="/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
if [ ! -x "$UE" ]; then echo "Unreal Engine 5.8 is missing: $UE" >&2; exit 1; fi
if [ ! -d "$HERE/unreal/WebHomage/Content/Brute/Parts" ]; then
  echo "Brute content missing: run python3 unreal/WebHomage/Scripts/build_brute.py (and the Manhattan content build) first" >&2; exit 1
fi
MAP="${BRUTE_MAP:-/Game/Showcase/Maps/Manhattan_Island}"
mkdir -p "$HOME/hulk-logs"
export GPU_SLOT_DIR="$HOME/.cache/gpu-slot"
unset SM2_COEXIST_HOLDER
exec /usr/bin/env python3 "$HERE/tools/m5/guarded_preview.py" -- "$UE" "$HERE/unreal/WebHomage/WebHomage.uproject" "$MAP" \
  -WHSpawnTimesSquare -game -windowed -ResX=1920 -ResY=1080 -ForceRes -NoVSync \
  -WHProfile=playable -WHResScale=100 "-WHPerfPreset=$HERE/unreal/WebHomage/Config/PerfPlayableFast.cvars" \
  -NoCrashReports -notraceserver "-ExecCmds=t.MaxFPS 60,r.ScreenPercentage 100,r.AntiAliasingMethod 4" \
  "-abslog=$HOME/hulk-logs/play-brute.log" "$@"

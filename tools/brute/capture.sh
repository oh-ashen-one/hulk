#!/bin/bash
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# One Brute capture of the REAL game: offscreen -game through the shared GPU slot (~/.cache/gpu-slot, capture class), fixed timestep
# (-benchmark -fps=N) so script time == shot time, telemetry CSV + stills (or every frame + mp4 with -movie).
#   tools/brute/capture.sh <case> [-map /Game/Maps/Manhattan] [-shots 2,4] [-quit 10] [-res 1280x720] [-movie] [-- extra UE args]
# case = tools/brute/cases/<case>.json (or "none"); output ~/hulk-scratch/cap/<case>/
set -uo pipefail
CASE="$1"; shift
MAP=/Game/Maps/Manhattan; SHOTS=""; QUIT=12; RES=1280x720; MOVIE=0; EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    -map) MAP="$2"; shift 2;; -shots) SHOTS="$2"; shift 2;; -quit) QUIT="$2"; shift 2;; -res) RES="$2"; shift 2;;
    -movie) MOVIE=1; shift;; --) shift; EXTRA=("$@"); break;; *) echo "unknown $1"; exit 1;;
  esac
done
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$HOME/hulk-scratch/cap/$CASE"; rm -rf "$OUT"; mkdir -p "$OUT"
ARGS=("$OUT" -map "$MAP" -res "$RES" -quit "$QUIT" -name "$CASE" -timeout 900)
[ -n "$SHOTS" ] && ARGS+=(-shots "$SHOTS")
if [ "$MOVIE" = 1 ]; then ARGS+=(-movie); FPSARGS=(); else FPSARGS=(-benchmark -fps=30); fi
SCRIPTARG=(); [ "$CASE" != none ] && [ -f "$ROOT/tools/brute/cases/$CASE.json" ] && SCRIPTARG=("-WHBruteScript=$ROOT/tools/brute/cases/$CASE.json")
export GPU_SLOT_DIR="$HOME/.cache/gpu-slot" GPU_SLOT_CAPTURE_MAX_HOLD=1200
"$ROOT/tools/gpu/gpu_slot.sh" capture --label "hulk-$CASE" --timeout 3600 -- "$ROOT/unreal/WebHomage/Scripts/run_game.sh" "${ARGS[@]}" -- \
  "${FPSARGS[@]+"${FPSARGS[@]}"}" "${SCRIPTARG[@]+"${SCRIPTARG[@]}"}" "${EXTRA[@]+"${EXTRA[@]}"}" > "$OUT/capture.txt" 2>&1
RC=$?
tail -4 "$OUT/capture.txt"
grep -E "WH_BRUTE t=" "$OUT/$CASE.log" 2>/dev/null | sed 's/.*WH_BRUTE /  /'
grep -E "Fatal|Assertion failed|Unhandled Exception" "$OUT/$CASE.log" 2>/dev/null | head -5
exit $RC

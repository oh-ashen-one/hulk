#!/bin/bash
# Homage fan game. Not an official Marvel, Sony or Insomniac game; no affiliation.
# Unattended run of the REAL game (standalone -game, offscreen by default) with screenshots,
# frame-time stats and an auto-quit. Never opens a window, never touches the mouse.
#
# usage: Scripts/run_game.sh <out_dir> [options] [-- extra UE args]
#   -map /Game/Maps/Foundation_Test   map to open
#   -res 3840x2160                    output (back-buffer) size
#   -shots 20,30,40                   screenshot times (game seconds)
#   -perf 20:40                       frame-time window (writes <name>_perf.json)
#   -quit 41                          exit time (default: perf end + 1, or last shot + 2)
#   -name f4k                         file prefix
#   -exec "r.ScreenPercentage 100,stat unit"   console commands at start (comma separated)
#   -window                           windowed on the secondary 1080x1920 display instead of offscreen
#   -movie                            dump EVERY frame (-dumpmovie) with fixed 60 fps timestep
#   -timeout 300                      hard kill after N wall seconds
#   -firstline 'WH_BRUTE (tick1|t=)'  frame-1 watchdog (ERE on the log): no match within -firstline_s (default 120) wall seconds of
#                                     launch -> SIGTERM, wait 60 s, SIGKILL last, exit 5 "NO FIRST FRAME" (2026-10-29 GPU wedge)
# Every launch waits for the machine-wide 20 s launch gap and stamps ~/.cache/gpu-slot/last_launch (tools/gpu/gpu_gates.py).
set -uo pipefail
OUT="$1"; shift
MAP=/Game/Maps/Foundation_Test; RES=3840x2160; SHOTS=""; PERF=""; QUIT=""; NAME=shot; EXEC=""; WINDOW=0; MOVIE=0; TIMEOUT=300; FIRSTLINE=""; FIRSTLINE_S=120; EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    -map) MAP="$2"; shift 2;; -res) RES="$2"; shift 2;; -shots) SHOTS="$2"; shift 2;;
    -perf) PERF="$2"; shift 2;; -quit) QUIT="$2"; shift 2;; -name) NAME="$2"; shift 2;;
    -exec) EXEC="$2"; shift 2;; -window) WINDOW=1; shift;; -movie) MOVIE=1; shift;;
    -timeout) TIMEOUT="$2"; shift 2;; -firstline) FIRSTLINE="$2"; shift 2;; -firstline_s) FIRSTLINE_S="$2"; shift 2;;
    --) shift; EXTRA=("$@"); break;;
    *) echo "unknown option $1"; exit 1;;
  esac
done
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UPROJECT="$PROJ_DIR/WebHomage.uproject"
UE="${WH_UE_BIN:-/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor}"   # WH_UE_BIN: test stub only
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
W="${RES%x*}"; H="${RES#*x}"
ARGS=("$UPROJECT" "$MAP" -game -ResX="$W" -ResY="$H" -ForceRes -NoCrashReports -NoSound -NoVSync
      -WHNoMouseCapture -WHShotDir="$OUT" -WHShotName="$NAME" -abslog="$OUT/$NAME.log")
if [ "$WINDOW" = 1 ]; then ARGS+=(-windowed -WinX=-1080 -WinY=40); else ARGS+=(-RenderOffScreen); fi
[ -n "$SHOTS" ] && ARGS+=(-WHShotAt="$SHOTS")
if [ -n "$PERF" ]; then ARGS+=(-WHPerfFrom="${PERF%:*}" -WHPerfTo="${PERF#*:}" -WHCsv); fi
if [ -z "$QUIT" ]; then
  if [ -n "$PERF" ]; then QUIT=$(python3 -c "print(float('${PERF#*:}')+1)");
  elif [ -n "$SHOTS" ]; then QUIT=$(python3 -c "print(max(map(float,'$SHOTS'.split(',')))+2)"); else QUIT=20; fi
fi
ARGS+=(-WHQuitAt="$QUIT")
# 2026-10-01 18:12 (WindowServer starvation probe failing with one 1080p capture at GPU 100 %): non-perf captures are frame-capped so the
# GPU idles between frames and WindowServer gets its slice. Movie captures use a fixed 1/60 s step, so their frames are unchanged.
# Perf runs stay uncapped. Override with WH_CAPTURE_MAXFPS.
# 20:43: a native-4K still capture pinned the GPU (a 4K frame takes > 22 ms, so a 45 fps cap never engages): stills and any capture
# >= 2560 px wide run at <= 20 fps (fixed-step captures produce the same frames, just slower).
RESW=${RES%%x*}
if [ -n "$PERF" ] && [ "${GPU_SLOT_HELD:-}" = "perf" ]; then EXECS="t.MaxFPS 0"   # only real perf runs (exclusive perf lock) are uncapped
elif [ "$MOVIE" = 1 ] && [ "${RESW:-0}" -lt 2560 ]; then EXECS="t.MaxFPS ${WH_CAPTURE_MAXFPS:-30}"
elif [ "${RESW:-0}" -ge 2560 ]; then EXECS="t.MaxFPS ${WH_CAPTURE_MAXFPS:-8}"   # 03:45: a 4K frame takes > 50 ms, so 20 fps still pinned the GPU
else EXECS="t.MaxFPS ${WH_CAPTURE_MAXFPS:-20}"; fi
[ -n "$EXEC" ] && EXECS="$EXECS,$EXEC"
ARGS+=(-ExecCmds="$EXECS")
if [ "$MOVIE" = 1 ]; then rm -f "$PROJ_DIR"/Saved/Screenshots/MacEditor/MovieFrame*.png; ARGS+=(-benchmark -fps=60 -dumpmovie); fi
ARGS+=("${EXTRA[@]+"${EXTRA[@]}"}")
echo "run_game: out=$OUT res=$RES quit=$QUIT window=$WINDOW movie=$MOVIE timeout=$TIMEOUT firstline=${FIRSTLINE:-off}"
GATES="$PROJ_DIR/../../tools/gpu/gpu_gates.py"
if [ -f "$GATES" ]; then python3 "$GATES" gap; python3 "$GATES" stamp --label "run_game:$NAME"; fi   # machine-wide 20 s launch gap
"$UE" "${ARGS[@]}" > "$OUT/$NAME.stdout.txt" 2>&1 &
PID=$!
START=$(date +%s)
# stop OUR engine only: SIGTERM, wait up to 60 s, SIGKILL only if it is still alive (RULES.md 2026-09-29 panic)
stop_engine() { kill -TERM $PID 2>/dev/null; for _ in $(seq 1 60); do kill -0 $PID 2>/dev/null || return 0; sleep 1; done; kill -0 $PID 2>/dev/null && kill -9 $PID; }
NOFIRST=0; SEEN=0
while kill -0 $PID 2>/dev/null; do
  EL=$(( $(date +%s) - START ))
  if [ -n "$FIRSTLINE" ] && [ "$SEEN" = 0 ]; then
    if grep -qE "$FIRSTLINE" "$OUT/$NAME.log" 2>/dev/null; then SEEN=1; echo "run_game: first frame after ${EL} s"
    elif [ "$EL" -gt "$FIRSTLINE_S" ]; then
      echo "NO FIRST FRAME: no line matching '$FIRSTLINE' in $OUT/$NAME.log within ${FIRSTLINE_S} s of launch; stopping $PID (SIGTERM, wait 60 s, SIGKILL last)"
      NOFIRST=1; stop_engine; break
    fi
  fi
  if [ "$EL" -gt "$TIMEOUT" ]; then echo "timeout: stopping $PID (SIGTERM, wait 60 s, SIGKILL last; RULES.md 2026-09-29 panic)"; stop_engine; break; fi
  sleep 2
done
wait $PID 2>/dev/null; RC=$?
if [ "$NOFIRST" = 1 ]; then
  echo "NO FIRST FRAME: engine stopped (rc $RC); not retried. Read $OUT/$NAME.log (the 'OriginX <= OriginMax' ensure is benign)."
  [ "$MOVIE" = 1 ] && rm -f "$PROJ_DIR"/Saved/Screenshots/MacEditor/MovieFrame*.png
  exit 5
fi
grep -E "WH_(PERF|SHOT|QUIT)" "$OUT/$NAME.log" | sed 's/^.*LogWebHomage: Display: //'
if [ "$MOVIE" = 1 ]; then
  # -dumpmovie writes Saved/Screenshots/MacEditor/MovieFrameNNNNN.png (one per rendered frame, game time fixed at 1/60 s)
  mkdir -p "$OUT/${NAME}_frames"
  mv "$PROJ_DIR"/Saved/Screenshots/MacEditor/MovieFrame*.png "$OUT/${NAME}_frames/" 2>/dev/null
  N=$(ls "$OUT/${NAME}_frames" | wc -l | tr -d ' ')
  echo "movie frames: $N -> $OUT/${NAME}_frames"
  if [ "$N" -gt 0 ] && command -v ffmpeg >/dev/null; then
    ffmpeg -loglevel error -y -framerate 60 -i "$OUT/${NAME}_frames/MovieFrame%05d.png" \
      -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart "$OUT/${NAME}.mp4" && echo "movie: $OUT/${NAME}.mp4"
  fi
fi
exit $RC

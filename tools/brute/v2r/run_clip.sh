#!/bin/bash
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
#
# Per-clip pipeline runner for the Brute video2rig upgrade (docs/brute/video2rig/PLAN.md, Phases 2-4), one clip at a time:
#   size gate -> video2rig check -> run -> review -> import_motion -> refine_brute -> export_clip -> contact sheet -> PIPELINE.log
#
#   tools/brute/v2r/run_clip.sh <project_dir> <clipname> <Clip> [--loop | --return-to-stance]
#        [--fork-dir <video2rig checkout>] [--motion-dir <dir>] [--from <step>] [--to <step>]
#        [--python <python>] [--no-size-gate] [--run-args "..."] [--refine-args "..."] [--export-args "..."]
#   tools/brute/v2r/run_clip.sh --selftest        (parsers only, on sample strings; no project, no Blender)
#
#   <project_dir>  the video2rig project (creature.json, model.blend, clips/, work/, out/), e.g. ~/hulk/Local/video2rig/brute-aligned
#                  (the airborne project: ~/hulk/Local/video2rig/brute-air; its fork checkout is ~/video2rig-brute-air)
#   <clipname>     the clip's name for video2rig: clips/<clipname>.mp4, work/<clipname>/, out/<clipname>.npz (idle_v1, punchr_v2, ...)
#   <Clip>         assemble_motion's CLIPS name: Idle Walk Run StopLunge Jump WallAttach WallClimb PunchL PunchR Slap Clap Smash
#                  Lift Throw Uppercut Fall Land
#   --loop / --return-to-stance   refine_brute.py mode (loops: Idle Walk Run Fall; one-shots: the moves). Neither = no loop/return pass.
#   --fork-dir     the video2rig checkout (cwd of `python -m video2rig`, source of blender/import_motion.py); default ~/video2rig
#   --python       interpreter for video2rig and size_gate.py; default <fork-dir>/.venv/bin/python, else ~/video2rig/.venv/bin/python
#   --motion-dir   where Brute_<key>-v2r.glb goes; default /Users/midir/hulk/Local/video2rig/motion-v2r/ (a v2r file only goes into the
#                  game's motion dir once it has won its A/B; see export_clip.py)
#   --from <step>  restart at a step; steps: size check run review import refine export sheet log. Earlier results (check %, fit px,
#                  warnings, outline) come from work/<clipname>/pipeline.state, else from check.json / report.json.
#                  --from refine / export / sheet / log reuse the newest <Clip>_v2r_v<N>.blend; `import` always writes the next number.
#   --to <step>    stop after a step (testing)
#   --no-size-gate skip step 0 (tools/brute/v2r/size_gate.py, limit 1.3x; PLAN: a clip failing it is regenerated, never fitted)
#   --*-args "..." extra arguments passed through to `video2rig run`, refine_brute.py or export_clip.py (e.g. --refine-args "--floor=-0.43")
#
# Gates (stop at the first failure with one `GATE FAIL ...` line, exit 3; the line `STOP ...` is appended to <project>/PIPELINE.log):
#   size    SIZE_GATE FAIL                         (scale over 1.3)
#   check   FAIL line of `video2rig check` (body disagreement over 1.5 % of the height), or no readable result; never fit a failed clip
#   export  EXPORT_GATE FAIL
# Warnings only (printed, the run continues, the director decides): check WARN, fit median miss over 4 px, any report warning,
# outline match under 0.9, refine toe/seam oddities. A crashed tool, a missing gate line or a missing output file stops with exit 4.
# Preflight for step `run`: <project>/reader/reader.pt must exist (else `run` would silently take the slow, inaccurate --old road).
#
# Every step's full output: <project>/work/<clipname>/<step>.log. Final line, also appended to <project>/PIPELINE.log and printed:
#   CLIP <Clip> <clipname> check <pct> <PASS|FAIL> fit <px> warn <n> outline <a>/<b> refine <seam> <drift> <toe> export <mm> <PASS|FAIL> blend <refined.blend> glb <glb>
# Blender: one process of ours, headless (-b --factory-startup); waits while 4 Blender processes run (2 if an UnrealEditor runs).
# Exit codes: 0 done, 2 usage, 3 gate failed, 4 tool/IO error. bash 3.2 compatible (macOS).

set -u -o pipefail

B=${V2R_BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
HERE=$(cd "$(dirname "$0")" && pwd)
STEPS="size check run review import refine export sheet log"
BODY_FAIL_PCT=1.5      # video2rig check.py BODY_FAIL = 0.015 of the creature's height
FIT_WARN_PX=4
SIZE_MAX=1.3

# ------------------------------------------------------------------ parsers (selftest below runs them on sample strings)
# `video2rig check`:  "<OK|WARN|FAIL> <clip>: body 0.0123, limbs 0.015 (share of the height, median), frame 0 [..]" (+ "  WARN: ..." lines)
parse_check() {    # file -> CHK_VERDICT CHK_BODY CHK_LIMBS CHK_PCT; returns 1 when there is no result line
  local line
  CHK_VERDICT=''; CHK_BODY=''; CHK_LIMBS=''; CHK_PCT=''
  line=$(grep -E '^(OK|WARN|FAIL) [^ ]+: body ' "$1" | tail -1)
  [ -n "$line" ] || return 1
  CHK_VERDICT=${line%% *}
  CHK_BODY=$(printf '%s\n' "$line" | sed -E 's/^.*: body ([^,]+),.*$/\1/')
  CHK_LIMBS=$(printf '%s\n' "$line" | sed -E 's/^.*, limbs ([^ ]+) .*$/\1/')
  case $CHK_BODY in None|'') CHK_PCT='n/a' ;; *) CHK_PCT=$(awk -v b="$CHK_BODY" 'BEGIN { printf "%.2f", b * 100 }') ;; esac
  return 0
}

# PASS/FAIL/UNCHECKED from parsed check values + the tool's exit code ($1); FAIL when the tool says FAIL, exits 1, or the body is over 1.5 %
check_verdict() {
  if [ -z "$CHK_VERDICT" ]; then echo UNCHECKED; return; fi
  if [ "$CHK_VERDICT" = FAIL ] || [ "$1" = 1 ]; then echo FAIL; return; fi
  if [ "$CHK_PCT" = 'n/a' ]; then echo UNCHECKED; return; fi
  awk -v p="$CHK_PCT" -v t="$BODY_FAIL_PCT" 'BEGIN { print (p + 0 > t + 0) ? "FAIL" : "PASS" }'
}

# `video2rig run` (reader road) logs "[ 12.3s] fit <clip>: <T> frames; median keypoint miss 1.23 px; ..." and "[ 41.0s] report {json}"
# (report.py: outline_match per view, warnings list). Also accepts work/<clip>/report.json itself (a one-line JSON object).
parse_run() {      # file -> RUN_FIT RUN_WARN RUN_OUTLINE RUN_WARN_TEXT (n/a when absent)
  local out
  RUN_FIT=$(grep -E 'median keypoint miss [0-9.]+ px' "$1" | tail -1 | sed -E 's/^.*median keypoint miss ([0-9.]+) px.*$/\1/')
  case $RUN_FIT in *[!0-9.]*|'') RUN_FIT='n/a' ;; esac
  out=$(python3 - "$1" <<'PY'
import json, re, sys
path = sys.argv[1]
d = None
txt = open(path, errors='replace').read()
for l in txt.splitlines():
    m = re.match(r'^(?:\[\s*[0-9.]+s\]\s*)?report (\{.*\})\s*$', l)
    if m:
        try:
            d = json.loads(m.group(1))
        except ValueError:
            pass
if d is None:
    try:
        d = json.loads(txt)
    except ValueError:
        d = None
if not isinstance(d, dict) or 'outline_match' not in d:
    print('n/a'); print('n/a')
else:
    w = d.get('warnings') or []
    print(len(w)); print('/'.join(str(v) for v in d['outline_match'].values()) or 'n/a')
    for s in w:
        print(s)
PY
  ) || out=$'n/a\nn/a'
  RUN_WARN=$(printf '%s\n' "$out" | sed -n 1p)
  RUN_OUTLINE=$(printf '%s\n' "$out" | sed -n 2p)
  RUN_WARN_TEXT=$(printf '%s\n' "$out" | sed -n '3,$p')
  return 0
}

# refine_brute.py: "REFINE_GATE <clip> seam 1.18 foot_drift_mm 3.6 toe_min_mm 0.0 peakhand_L 21 peakhand_R 153" (foot_drift_mm may be n/a)
# with --lock-yaw the line ends in " yaw_locked 84.2" (deg span of the removed root yaw) -> REF_YAW (empty without it)
parse_refine() {   # file -> REF_SEAM REF_DRIFT REF_TOE REF_PL REF_PR REF_YAW; returns 1 when there is no gate line
  local line
  REF_SEAM=''; REF_DRIFT=''; REF_TOE=''; REF_PL=''; REF_PR=''; REF_YAW=''
  line=$(grep -E '^REFINE_GATE [^ ]+ seam [^ ]+ foot_drift_mm [^ ]+ toe_min_mm [^ ]+ peakhand_L [0-9]+ peakhand_R [0-9]+' "$1" | tail -1)
  [ -n "$line" ] || return 1
  set -- $line
  REF_SEAM=$4; REF_DRIFT=$6; REF_TOE=$8; REF_PL=${10}; REF_PR=${12}
  [ "${13-}" = yaw_locked ] && REF_YAW=${14-}
  return 0
}

# export_clip.py: "EXPORT_GATE <Clip> max_vertex_delta_mm 0.0029 frames 5 PASS" (FAIL variants: "... nan frames 0 FAIL (rig mismatch)")
# and "EXPORT <clip> wrote <path.glb> (x MB); location keys on ..."
parse_export() {   # file -> EXP_MM EXP_RESULT EXP_GLB; returns 1 when there is no gate line
  local line
  EXP_MM=''; EXP_RESULT=''; EXP_GLB=''
  line=$(grep -E '^EXPORT_GATE [^ ]+ max_vertex_delta_mm [^ ]+ frames [0-9]+ (PASS|FAIL)' "$1" | tail -1)
  [ -n "$line" ] || return 1
  EXP_MM=$(printf '%s\n' "$line" | sed -E 's/^EXPORT_GATE [^ ]+ max_vertex_delta_mm ([^ ]+) frames.*$/\1/')
  EXP_RESULT=$(printf '%s\n' "$line" | sed -E 's/^.* frames [0-9]+ (PASS|FAIL).*$/\1/')
  EXP_GLB=$(grep -E '^EXPORT [^ ]+ wrote ' "$1" | tail -1 | sed -E 's/^EXPORT [^ ]+ wrote (.*\.glb) \(.*$/\1/')
  return 0
}

# size_gate.py: "SIZE_GATE <clip> PASS|FAIL width 1.89 height 1.00 peak_frame 40 scale 1.23 metric area"
parse_size() {     # file -> SIZE_RESULT SIZE_SCALE
  local line
  SIZE_RESULT=''; SIZE_SCALE=''
  line=$(grep -E '^SIZE_GATE [^ ]+ (PASS|FAIL) ' "$1" | tail -1)
  [ -n "$line" ] || return 1
  SIZE_RESULT=$(printf '%s\n' "$line" | sed -E 's/^SIZE_GATE [^ ]+ (PASS|FAIL) .*$/\1/')
  SIZE_SCALE=$(printf '%s\n' "$line" | sed -E 's/^.* scale ([0-9.]+) metric.*$/\1/')
  return 0
}

fnum_gt() { awk -v a="$1" -v b="$2" 'BEGIN { exit !(a + 0 > b + 0) }'; }
is_num() { case ${1:-} in ''|n/a|*[!0-9.eE+-]*) return 1 ;; *) return 0 ;; esac; }

# ------------------------------------------------------------------ selftest
selftest() {
  local d fails=0 t
  d=$(mktemp -d "${TMPDIR:-/tmp}/run_clip_selftest.XXXXXX") || exit 4
  eq() { if [ "$2" != "$3" ]; then echo "SELFTEST FAIL $1: got '$2' want '$3'"; fails=$((fails + 1)); fi; }
  # check: formats from video2rig/__main__.py + check.py (verdict, clip, body, limbs, frame 0 outline, messages)
  printf 'read: 158 frames x 2 panels\nOK idle_v1: body 0.0107, limbs 0.0153 (share of the height, median), frame 0 [0.93, 0.95]\n' > $d/c1
  parse_check $d/c1; eq check1 "$CHK_VERDICT $CHK_PCT $(check_verdict 0)" 'OK 1.07 PASS'
  printf 'WARN run_v1: body 0.0121, limbs 0.0262 (share of the height, median), frame 0 [0.93, 0.95]\n  WARN: the panels disagree on the limbs by 2.6%% of the height: fast legs\n' > $d/c2
  parse_check $d/c2; eq check2 "$CHK_VERDICT $CHK_PCT $(check_verdict 0)" 'WARN 1.21 PASS'
  printf 'FAIL punchr_v1: body 0.0182, limbs 0.021 (share of the height, median), frame 0 [0.93, 0.95]\n  FAIL: the panels disagree on the body by 1.8%% of its height\n' > $d/c3
  parse_check $d/c3; eq check3 "$CHK_VERDICT $CHK_PCT $(check_verdict 1)" 'FAIL 1.82 FAIL'
  printf 'OK x_v1: body 0.0155, limbs 0.01 (share of the height, median), frame 0 [0.9]\n' > $d/c4      # tool said OK, number says fail
  parse_check $d/c4; eq check4 "$CHK_VERDICT $CHK_PCT $(check_verdict 0)" 'OK 1.55 FAIL'
  printf 'OK x_v1: body 0.015, limbs 0.01 (share of the height, median), frame 0 [0.9]\n' > $d/c5       # exactly the line: not over
  parse_check $d/c5; eq check5 "$CHK_PCT $(check_verdict 0)" '1.50 PASS'
  printf 'WARN x_v1: body None, limbs None (share of the height, median), frame 0 [0.9]\n  WARN: not two orthographic panels: no panel check\n' > $d/c6
  parse_check $d/c6; eq check6 "$CHK_PCT $(check_verdict 0)" 'n/a UNCHECKED'
  printf 'OK x_v1: body 5e-05, limbs 0.01 (share of the height, median), frame 0 [0.9]\n' > $d/c7
  parse_check $d/c7; eq check7 "$CHK_PCT $(check_verdict 0)" '0.01 PASS'
  printf 'clip not found: /x/clips/y.mp4\n' > $d/c8
  parse_check $d/c8; eq check8 "rc=$? '$CHK_VERDICT' $(check_verdict 1)" "rc=1 '' UNCHECKED"
  # run: formats from reader/fit.py (fit line), __main__.py (log prefix, report line), report.py (keys, warnings)
  cat > $d/r1 <<'EOF'
[   0.9s] idle_v1: 158 frames, 2 view(s), timing 1.0, frame 0 outline match after alignment [0.93, 0.95]
[  12.0s] panels: the body along the axis both panels see is 0.8 px apart between them (median, 0.3% of the height): left as read
[  38.2s] fit idle_v1: 158 frames; median keypoint miss 1.37 px; 12 one-frame spikes smoothed; low-pass 6 Hz at 30 fps
[  39.0s] motion -> /p/out/idle_v1.npz
[  39.0s] report {"frames": 158, "outline_match": {"v2r_front": 0.953, "v2r_side": 0.947}, "worst_frames": {"v2r_front": [1, 2], "v2r_side": [3, 4]}, "max_twist_deg": {}, "biggest_jump_deg": {"deg": 9.1, "bone": "Spine", "frame": 40}, "frames_under_floor": 0, "frames_at_joint_limit": {}, "warnings": []}
[  39.0s] time {"total_s": 39.0}
EOF
  parse_run $d/r1; eq run1 "$RUN_FIT $RUN_WARN $RUN_OUTLINE" '1.37 0 0.953/0.947'
  cat > $d/r2 <<'EOF'
[  38.2s] fit run_v1: 150 frames; median keypoint miss 5.20 px; 3 one-frame spikes smoothed; low-pass 6 Hz at 30 fps
[  39.0s] report {"frames": 150, "outline_match": {"v2r_front": 0.88, "v2r_side": 0.91}, "warnings": ["v2r_front view: outline under 0.6 in frames 10-18", "joint at limit: LeftLeg"]}
EOF
  parse_run $d/r2; eq run2 "$RUN_FIT $RUN_WARN $RUN_OUTLINE $(printf '%s' "$RUN_WARN_TEXT" | wc -l | tr -d ' ')" '5.20 2 0.88/0.91 1'
  printf '[ 1s] the older road (point tracker + solve): no joint reader for this creature\n' > $d/r3
  parse_run $d/r3; eq run3 "$RUN_FIT $RUN_WARN $RUN_OUTLINE" 'n/a n/a n/a'
  printf '{"frames": 5, "outline_match": {"a": 0.9}, "warnings": []}\n' > $d/r4.json       # work/<clip>/report.json, one view
  parse_run $d/r4.json; eq run4 "$RUN_WARN $RUN_OUTLINE" '0 0.9'
  # refine / export / size: lines from TESTS-refine-export.md and size_gate.py
  printf 'REFINE saved a b\nREFINE_GATE Idle seam 1.18 foot_drift_mm 3.6 toe_min_mm 0.0 peakhand_L 21 peakhand_R 153\n' > $d/g1
  parse_refine $d/g1; eq refine1 "$REF_SEAM $REF_DRIFT $REF_TOE $REF_PL $REF_PR" '1.18 3.6 0.0 21 153'
  printf 'REFINE_GATE PunchL seam 0.16 foot_drift_mm n/a toe_min_mm -5.5 peakhand_L 31 peakhand_R 29\n' > $d/g2
  parse_refine $d/g2; eq refine2 "$REF_SEAM $REF_DRIFT $REF_TOE" '0.16 n/a -5.5'
  printf 'REFINE_GATE PunchR seam 0.20 foot_drift_mm 2.1 toe_min_mm 0.0 peakhand_L 40 peakhand_R 33 yaw_locked 84.2\n' > $d/g4
  parse_refine $d/g4; eq refine4 "$REF_PR $REF_YAW" '33 84.2'
  parse_refine $d/g1; eq refine5 "x$REF_YAW" 'x'
  printf 'Traceback\n' > $d/g3
  parse_refine $d/g3; eq refine3 "rc=$?" 'rc=1'
  printf 'EXPORT Idle wrote /m/Brute_v2r_idle.glb (4.2 MB); location keys on [Hips]\nEXPORT_GATE Idle max_vertex_delta_mm 0.0029 frames 5 PASS\n' > $d/e1
  parse_export $d/e1; eq export1 "$EXP_MM $EXP_RESULT $EXP_GLB" '0.0029 PASS /m/Brute_v2r_idle.glb'
  printf 'EXPORT_GATE Idle max_vertex_delta_mm nan frames 0 FAIL (rig mismatch)\n' > $d/e2
  parse_export $d/e2; eq export2 "$EXP_MM $EXP_RESULT" 'nan FAIL'
  printf 'EXPORT_GATE Idle max_vertex_delta_mm 1.5000 frames 5 FAIL\n' > $d/e3
  parse_export $d/e3; eq export3 "$EXP_MM $EXP_RESULT" '1.5000 FAIL'
  printf 'SIZE_GATE walk_v1 PASS width 1.89 height 1.00 peak_frame 40 scale 1.23 metric area\n' > $d/s1
  parse_size $d/s1; eq size1 "$SIZE_RESULT $SIZE_SCALE" 'PASS 1.23'
  printf 'SIZE_GATE jump_v2 FAIL width 2.10 height 1.40 peak_frame 40 scale 1.55 metric area\n' > $d/s2
  parse_size $d/s2; eq size2 "$SIZE_RESULT $SIZE_SCALE" 'FAIL 1.55'
  fnum_gt 4.2 4 || { echo 'SELFTEST FAIL fnum_gt 4.2>4'; fails=$((fails + 1)); }
  fnum_gt 4 4 && { echo 'SELFTEST FAIL fnum_gt 4>4'; fails=$((fails + 1)); }
  rm -rf "$d"
  if [ $fails -eq 0 ]; then echo 'RUN_CLIP_SELFTEST PASS (parsers: check, run, refine, export, size)'; exit 0; fi
  echo "RUN_CLIP_SELFTEST FAIL ($fails)"; exit 1
}

# ------------------------------------------------------------------ arguments
usage() { sed -n '3,30p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
[ "${1:-}" = --selftest ] && selftest
PROJ=''; CLIPNAME=''; CLIP=''; MODE=''; FORK=$HOME/video2rig; MOTION_DIR=/Users/midir/hulk/Local/video2rig/motion-v2r
FROM=''; TO=log; PY=''; SIZE_GATE=1; RUN_ARGS=''; REFINE_ARGS=''; EXPORT_ARGS=''
pos=0
while [ $# -gt 0 ]; do
  case $1 in
    --loop) MODE=--loop ;;
    --return-to-stance) MODE=--return-to-stance ;;
    --fork-dir) FORK=${2:?--fork-dir needs a directory}; shift ;;
    --motion-dir) MOTION_DIR=${2:?--motion-dir needs a directory}; shift ;;
    --from) FROM=${2:?--from needs a step}; shift ;;
    --to) TO=${2:?--to needs a step}; shift ;;
    --python) PY=${2:?--python needs a path}; shift ;;
    --no-size-gate) SIZE_GATE=0 ;;
    --run-args) RUN_ARGS=${2-}; shift ;;
    --refine-args) REFINE_ARGS=${2-}; shift ;;
    --export-args) EXPORT_ARGS=${2-}; shift ;;
    -h|--help) usage ;;
    --*) echo "run_clip: unknown option $1" >&2; exit 2 ;;
    *) pos=$((pos + 1))
       case $pos in 1) PROJ=$1 ;; 2) CLIPNAME=$1 ;; 3) CLIP=$1 ;; *) echo 'run_clip: too many arguments' >&2; exit 2 ;; esac ;;
  esac
  shift
done
[ $pos -eq 3 ] || usage
[ -d "$PROJ" ] || { echo "run_clip: project dir not found: $PROJ" >&2; exit 2; }
PROJ=$(cd "$PROJ" && pwd); FORK=$(cd "$FORK" 2>/dev/null && pwd) || { echo "run_clip: fork dir not found" >&2; exit 2; }
case $MOTION_DIR in /*) ;; *) MOTION_DIR=$PWD/$MOTION_DIR ;; esac     # created by the export step only
if [ -z "$PY" ]; then
  if [ -x "$FORK/.venv/bin/python" ]; then PY=$FORK/.venv/bin/python; else PY=$HOME/video2rig/.venv/bin/python; fi
fi
[ -x "$PY" ] || { echo "run_clip: python not found: $PY (--python)" >&2; exit 2; }
is_step() { case " $STEPS " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }
[ -n "$FROM" ] || { if [ $SIZE_GATE -eq 1 ]; then FROM=size; else FROM=check; fi; }
is_step "$FROM" || { echo "run_clip: --from must be one of: $STEPS" >&2; exit 2; }
is_step "$TO" || { echo "run_clip: --to must be one of: $STEPS" >&2; exit 2; }
WORK=$PROJ/work/$CLIPNAME
LOGF=$PROJ/PIPELINE.log
STATE=$WORK/pipeline.state
mkdir -p "$WORK"

# step gating: step_on <name> is true from --from through --to
idx() { local i=0 s; for s in $STEPS; do [ "$s" = "$1" ] && { echo $i; return; }; i=$((i + 1)); done; }
step_on() { [ "$(idx "$1")" -ge "$(idx "$FROM")" ] && [ "$(idx "$1")" -le "$(idx "$TO")" ]; }
[ "$(idx "$FROM")" -le "$(idx "$TO")" ] || { echo 'run_clip: --from is after --to' >&2; exit 2; }
[ "$FROM" = size ] && [ $SIZE_GATE -eq 0 ] && FROM=check

say() { echo "[run_clip $CLIP $CLIPNAME] $*"; }
stop_gate() {   # step reason logfile
  echo "GATE FAIL $1: $2 (log: ${3#$PWD/})"
  echo "STOP $CLIP $CLIPNAME step $1 $2" >> "$LOGF"
  exit 3
}
stop_err() {    # step reason logfile
  echo "ERROR $1: $2 (log: ${3#$PWD/})" >&2
  echo "STOP $CLIP $CLIPNAME step $1 error: $2" >> "$LOGF"
  exit 4
}
save_state() { local v; : > "$STATE"; for v in CHK_PCT CHK_RESULT RUN_FIT RUN_WARN RUN_OUTLINE REF_SEAM REF_DRIFT REF_TOE EXP_MM EXP_RESULT EXP_GLB FIT_BLEND REFINED_BLEND; do printf '%s=%q\n' $v "${!v:-}" >> "$STATE"; done; }
CHK_PCT=''; CHK_RESULT=''; RUN_FIT=''; RUN_WARN=''; RUN_OUTLINE=''; REF_SEAM=''; REF_DRIFT=''; REF_TOE=''
EXP_MM=''; EXP_RESULT=''; EXP_GLB=''; FIT_BLEND=''; REFINED_BLEND=''
latest_fit_blend() {   # newest <Clip>_v2r_v<N>.blend (not _refined)
  local best=0 n f
  for f in "$PROJ/${CLIP}_v2r_v"*.blend; do
    [ -f "$f" ] || continue
    case $f in *_refined.blend) continue ;; esac
    n=${f##*_v2r_v}; n=${n%.blend}
    case $n in ''|*[!0-9]*) continue ;; esac
    [ "$n" -gt "$best" ] && best=$n
  done
  [ "$best" -gt 0 ] && echo "$PROJ/${CLIP}_v2r_v$best.blend"
}

# earlier results when restarting: the state file, else the files video2rig itself wrote
if [ "$(idx "$FROM")" -gt "$(idx check)" ]; then
  # shellcheck disable=SC1090
  [ -f "$STATE" ] && . "$STATE"
  if [ -z "$CHK_PCT" ] && [ -f "$WORK/check.json" ]; then
    CHK_PCT=$(python3 -c 'import json,sys; b=json.load(open(sys.argv[1])).get("body"); print("n/a" if b is None else "%.2f" % (b*100))' "$WORK/check.json" 2>/dev/null || echo n/a)
    [ -z "$CHK_RESULT" ] && CHK_RESULT=$(python3 -c 'import json,sys; print("FAIL" if json.load(open(sys.argv[1])).get("verdict")=="FAIL" else "PASS")' "$WORK/check.json" 2>/dev/null || echo n/a)
  fi
  if [ -z "$RUN_WARN" ] && [ -f "$WORK/report.json" ]; then parse_run "$WORK/report.json"; fi
  [ -n "$CHK_PCT" ] || CHK_PCT='n/a'; [ -n "$CHK_RESULT" ] || CHK_RESULT='n/a'
  [ -n "$RUN_FIT" ] || RUN_FIT='n/a'; [ -n "$RUN_WARN" ] || RUN_WARN='n/a'; [ -n "$RUN_OUTLINE" ] || RUN_OUTLINE='n/a'
fi
# a restart after the import step works on the newest fit blend (import itself always writes the next number)
if [ "$(idx "$FROM")" -gt "$(idx import)" ]; then
  FIT_BLEND=$(latest_fit_blend); REFINED_BLEND=${FIT_BLEND%.blend}_refined.blend
fi


blender_slot() {   # wait until our one Blender fits under the machine cap (4; 2 when an UnrealEditor runs)
  local nb ue cap waited=0
  while true; do
    nb=$(ps -axo comm= | grep -c '/MacOS/Blender$')
    ue=$(ps -axo comm= | grep -c 'UnrealEditor')
    cap=4; [ "$ue" -gt 0 ] && cap=2
    [ "$nb" -lt "$cap" ] && return 0
    [ $waited -ge 7200 ] && return 1
    [ $((waited % 300)) -eq 0 ] && say "waiting for a Blender slot: $nb running, cap $cap"
    sleep 20; waited=$((waited + 20))
  done
}
run_blender() {    # <logfile> <blender args after --background --factory-startup...>; returns Blender's exit code
  local log=$1; shift
  blender_slot || return 99
  "$B" --background --factory-startup "$@" > "$log" 2>&1
}
v2r() {            # <logfile> <video2rig command and args...>; cwd = the fork checkout so `-m video2rig` is that checkout's code
  local log=$1; shift
  ( cd "$FORK" && "$PY" -m video2rig "$@" ) > "$log" 2>&1
}

N=0; TOTAL=8
hdr() { N=$((N + 1)); say "step $1: $2"; }

# ------------------------------------------------------------------ 0. size gate
if step_on size; then
  hdr size "size_gate.py (limit ${SIZE_MAX}x)"
  L=$WORK/size.log
  ( cd "$FORK" && V2R_HOME="$FORK" "$PY" "$HERE/size_gate.py" "$PROJ" "$CLIPNAME" --max "$SIZE_MAX" ) > "$L" 2>&1; rc=$?
  parse_size "$L" || stop_err size 'no SIZE_GATE line' "$L"
  if [ "$SIZE_RESULT" = FAIL ] || [ $rc -eq 1 ]; then
    why=$(grep -m1 -E '^  FAIL' "$L" | sed -E 's/^  FAIL: *//' | cut -c1-240)
    stop_gate size "SIZE_GATE FAIL (scale $SIZE_SCALE, limit $SIZE_MAX; ${why:-see log}): regenerate the clip, never fit it" "$L"
  fi
  [ $rc -eq 0 ] || stop_err size "size_gate exit $rc" "$L"
  say "size ok: scale $SIZE_SCALE"
fi

# ------------------------------------------------------------------ 1. check
if step_on check; then
  hdr check 'video2rig check (fail line 1.5 % of the height)'
  L=$WORK/check.log
  v2r "$L" check "$PROJ" "$CLIPNAME"; rc=$?
  parse_check "$L" || stop_err check "no result line (exit $rc): $(tail -1 "$L")" "$L"
  CHK_RESULT=$(check_verdict $rc)
  grep -E '^  (WARN|FAIL):' "$L" | sed 's/^/    /'
  [ "$CHK_RESULT" = FAIL ] && stop_gate check "check FAIL body $CHK_PCT % > $BODY_FAIL_PCT %: generate the clip again, never fit a failed clip" "$L"
  [ "$CHK_RESULT" = UNCHECKED ] && stop_gate check "no panel check possible (body $CHK_BODY): cannot clear the clip" "$L"
  [ "$CHK_VERDICT" = WARN ] && say "WARN check: look at the limbs in the review film"
  say "check $CHK_RESULT: body $CHK_PCT % (limbs $CHK_LIMBS), verdict $CHK_VERDICT"
  save_state
fi

# ------------------------------------------------------------------ 2. run
if step_on run; then
  hdr run 'video2rig run (reader road)'
  L=$WORK/run.log
  [ -f "$PROJ/reader/reader.pt" ] || stop_err run "no $PROJ/reader/reader.pt (reader not trained yet): run would take the slow --old road" "$L"
  # shellcheck disable=SC2086
  v2r "$L" run "$PROJ" "$CLIPNAME" $RUN_ARGS; rc=$?
  [ $rc -eq 0 ] || stop_err run "video2rig run exit $rc: $(tail -1 "$L")" "$L"
  parse_run "$L"
  [ -f "$PROJ/out/$CLIPNAME.npz" ] || stop_err run "out/$CLIPNAME.npz was not written" "$L"
  [ "$RUN_FIT" != 'n/a' ] || stop_err run 'no "median keypoint miss" line: not the reader road?' "$L"
  [ "$RUN_WARN" != 'n/a' ] || stop_err run 'no report line (outline / warnings)' "$L"
  if fnum_gt "$RUN_FIT" "$FIT_WARN_PX"; then say "WARN fit: median keypoint miss $RUN_FIT px is over $FIT_WARN_PX px; continuing, the director decides"; fi
  [ "$RUN_WARN" -gt 0 ] && { say "WARN fit: $RUN_WARN report warning(s):"; printf '%s\n' "$RUN_WARN_TEXT" | sed 's/^/    /'; }
  for o in $(echo "$RUN_OUTLINE" | tr '/' ' '); do is_num "$o" && ! fnum_gt "$o" 0.8999 && say "WARN fit: outline match $o under 0.9 in a view"; done
  say "run ok: fit median miss $RUN_FIT px, $RUN_WARN warning(s), outline $RUN_OUTLINE"
  save_state
fi

# ------------------------------------------------------------------ 3. review
if step_on review; then
  hdr review 'video2rig review'
  L=$WORK/review.log
  v2r "$L" review "$PROJ" "$CLIPNAME"; rc=$?
  [ $rc -eq 0 ] || stop_err review "video2rig review exit $rc: $(tail -1 "$L")" "$L"
  [ -s "$WORK/review.mp4" ] || stop_err review "work/$CLIPNAME/review.mp4 missing or empty" "$L"
  say "review ok: $WORK/review.mp4"
fi

# ------------------------------------------------------------------ 4. import_motion
if step_on import; then
  hdr import 'import_motion.py -> <Clip>_v2r_v<N>.blend'
  L=$WORK/import.log
  [ -f "$PROJ/model.blend" ] || stop_err import "no $PROJ/model.blend" "$L"
  [ -f "$PROJ/out/$CLIPNAME.npz" ] || stop_err import "no $PROJ/out/$CLIPNAME.npz (run the fit first)" "$L"
  [ -f "$FORK/blender/import_motion.py" ] || stop_err import "no $FORK/blender/import_motion.py" "$L"
  v=1; while [ -e "$PROJ/${CLIP}_v2r_v$v.blend" ]; do v=$((v + 1)); done
  FIT_BLEND=$PROJ/${CLIP}_v2r_v$v.blend
  run_blender "$L" "$PROJ/model.blend" --python "$FORK/blender/import_motion.py" -- --motion "$PROJ/out/$CLIPNAME.npz" --action "$CLIPNAME" --save "$FIT_BLEND"; rc=$?
  [ $rc -eq 0 ] && grep -q '^IMPORT_MOTION saved' "$L" && [ -s "$FIT_BLEND" ] || stop_err import "Blender exit $rc, no 'IMPORT_MOTION saved'" "$L"
  say "import ok: $(grep -E '^IMPORT_MOTION [^s]' "$L" | tail -1) -> $FIT_BLEND"
  save_state
fi

# ------------------------------------------------------------------ 5. refine
if step_on refine; then
  hdr refine "refine_brute.py ${MODE:-(no loop/return pass)}"
  L=$WORK/refine.log
  [ -n "$FIT_BLEND" ] && [ -f "$FIT_BLEND" ] || stop_err refine "no ${CLIP}_v2r_v<N>.blend in $PROJ (run the import step)" "$L"
  REFINED_BLEND=${FIT_BLEND%.blend}_refined.blend
  STANCE=(); [ -f "$PROJ/rig/rig.json" ] && STANCE=(--stance-rig "$PROJ/rig/rig.json")
  # shellcheck disable=SC2086
  run_blender "$L" -P "$HERE/refine_brute.py" -- "$FIT_BLEND" ${MODE:+$MODE} --clip "$CLIP" ${STANCE[@]+"${STANCE[@]}"} $REFINE_ARGS; rc=$?
  parse_refine "$L" || stop_err refine "Blender exit $rc, no REFINE_GATE line" "$L"
  [ $rc -eq 0 ] && [ -s "$REFINED_BLEND" ] || stop_err refine "Blender exit $rc, $REFINED_BLEND missing" "$L"
  if [ "$MODE" = --loop ] && fnum_gt "$REF_SEAM" 2; then say "WARN refine: loop seam $REF_SEAM x the median step (over 2)"; fi
  if is_num "$REF_TOE" && ! fnum_gt "$REF_TOE" -10.001; then say "WARN refine: toe_min $REF_TOE mm (feet through the floor)"; fi
  if is_num "$REF_DRIFT" && fnum_gt "$REF_DRIFT" 10; then say "WARN refine: foot drift $REF_DRIFT mm after the plant"; fi
  grep -E '^REFINE (trim|spikes|floor_mismatch)|floor_mismatch' "$L" | head -3 | sed 's/^/    /'
  say "refine ok: REFINE_GATE seam $REF_SEAM foot_drift_mm $REF_DRIFT toe_min_mm $REF_TOE peakhand_L $REF_PL peakhand_R $REF_PR${REF_YAW:+ yaw_locked $REF_YAW}"
  save_state
fi

# ------------------------------------------------------------------ 6. export
if step_on export; then
  hdr export "export_clip.py -> $MOTION_DIR"
  L=$WORK/export.log
  mkdir -p "$MOTION_DIR" || stop_err export "cannot create $MOTION_DIR" "$L"
  [ -n "$FIT_BLEND" ] && REFINED_BLEND=${FIT_BLEND%.blend}_refined.blend
  [ -n "$REFINED_BLEND" ] && [ -f "$REFINED_BLEND" ] || stop_err export "no refined blend $REFINED_BLEND (run the refine step)" "$L"
  # shellcheck disable=SC2086
  run_blender "$L" -P "$HERE/export_clip.py" -- "$REFINED_BLEND" "$CLIP" "$MOTION_DIR" $EXPORT_ARGS; rc=$?
  parse_export "$L" || stop_err export "Blender exit $rc, no EXPORT_GATE line" "$L"
  [ "$EXP_RESULT" = PASS ] || stop_gate export "EXPORT_GATE FAIL max_vertex_delta_mm $EXP_MM" "$L"
  [ $rc -eq 0 ] || stop_err export "Blender exit $rc after EXPORT_GATE PASS" "$L"
  [ -n "$EXP_GLB" ] && [ -s "$EXP_GLB" ] || stop_err export "no glb written ($EXP_GLB)" "$L"
  say "export ok: EXPORT_GATE max_vertex_delta_mm $EXP_MM $EXP_RESULT -> $EXP_GLB"
  save_state
fi

# ------------------------------------------------------------------ 7. contact sheet
if step_on sheet; then
  hdr sheet 'contact sheet of the review film (tile 4x4)'
  L=$WORK/sheet.log
  [ -s "$WORK/review.mp4" ] || stop_err sheet "no $WORK/review.mp4" "$L"
  nf=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$WORK/review.mp4" 2>>"$L" | head -1)
  case $nf in ''|*[!0-9]*) stop_err sheet "could not count the frames of review.mp4" "$L" ;; esac
  stepf=$((nf / 16)); [ $stepf -ge 1 ] || stepf=1
  ffmpeg -y -v error -i "$WORK/review.mp4" -vf "select='not(mod(n\\,$stepf))',scale=480:-2,tile=4x4" -frames:v 1 -fps_mode vfr -q:v 3 "$WORK/review_sheet.jpg" >> "$L" 2>&1; rc=$?
  [ $rc -eq 0 ] && [ -s "$WORK/review_sheet.jpg" ] || stop_err sheet "ffmpeg exit $rc" "$L"
  say "sheet ok: $WORK/review_sheet.jpg ($nf frames, every ${stepf}th)"
fi

# ------------------------------------------------------------------ 8. PIPELINE.log
if step_on log; then
  hdr log 'append to PIPELINE.log'
  [ -n "$FIT_BLEND" ] && REFINED_BLEND=${FIT_BLEND%.blend}_refined.blend
  # refine / export values when restarting at `log`: re-read the step logs
  if [ -z "$REF_SEAM" ] && [ -f "$WORK/refine.log" ]; then parse_refine "$WORK/refine.log"; fi
  if [ -z "$EXP_MM" ] && [ -f "$WORK/export.log" ]; then parse_export "$WORK/export.log"; fi
  [ -n "$EXP_MM" ] && [ -n "$REF_SEAM" ] || stop_err log 'no refine / export results to log' "$WORK/export.log"
  LINE="CLIP $CLIP $CLIPNAME check ${CHK_PCT:-n/a} ${CHK_RESULT:-n/a} fit ${RUN_FIT:-n/a} warn ${RUN_WARN:-n/a} outline ${RUN_OUTLINE:-n/a} refine $REF_SEAM $REF_DRIFT $REF_TOE export $EXP_MM $EXP_RESULT blend $REFINED_BLEND glb $EXP_GLB"
  echo "$LINE" >> "$LOGF"
  save_state
  echo "$LINE"
fi
exit 0

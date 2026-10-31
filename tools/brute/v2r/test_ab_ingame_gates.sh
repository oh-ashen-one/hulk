#!/bin/bash
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Offline test of the GPU launch gates (tools/gpu/gpu_gates.py: cap 3 + watchdog tripwire, owner 2026-10-29), their use in capture.sh / ab_ingame.py, the launch budget and the
# run_game.sh frame-1 watchdog, and ab_ingame.py pack --a/--b. Fake ps / ioreg via GPU_GATES_FAKE_*; a stub engine (WH_UE_BIN) and a stub capture.sh. NEVER starts an
# engine: capture.sh is only run with CAPTURE_GATES_ONLY=1, ab_ingame.py only with a stub AB_CAPTURE_SH.
#   tools/brute/v2r/test_ab_ingame_gates.sh        (exit 0 = all pass)
set -u
REPO=$(cd "$(dirname "$0")/../../.." && pwd)
G="$REPO/tools/gpu/gpu_gates.py"
W=$(mktemp -d "${TMPDIR:-/tmp}/abgates.XXXXXX")
export GPU_GATES_LAST_LAUNCH="$W/last_launch" GPU_GATES_SAMPLE_S=0 GPU_GATES_POLL_S=0.2 GPU_GATES_MAX_WAIT_S=1 GPU_GATES_MIN_GAP_S=0
PASS=0; FAIL=0
ok() { echo "PASS  $1"; PASS=$((PASS+1)); }
no() { echo "FAIL  $1"; FAIL=$((FAIL+1)); [ -n "${2:-}" ] && sed 's/^/      | /' "$2" | head -20; }
expect() {  # name want_rc want_regex cmd...
  local n="$1" rc="$2" re="$3"; shift 3
  "$@" > "$W/out" 2>&1; local got=$?
  if [ "$got" = "$rc" ] && grep -qE "$re" "$W/out"; then ok "$n"; else no "$n (rc $got, want $rc, /$re/)" "$W/out"; fi
}
ps_json() { python3 -c 'import json,sys; print(json.dumps([dict(zip(("pid","stat","comm","args"),r.split("|"))) for r in sys.argv[1:]]))' "$@" > "$W/ps.json"; }
UE='/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor'
export GPU_GATES_FAKE_PS="$W/ps.json" GPU_GATES_FAKE_UTIL=10
# the watchdog tripwire reads a private fake, never ~/.cache/gpu-slot/gpu_watchdog.json
export GPU_GATES_WATCHDOG_JSON="$W/wd.json" GPU_GATES_WATCHDOG_STALE_S=120
unset GPU_GATES_MAX_CLIENTS
wd() {  # wd healthy | warn | strike | stuck | trip | old | oldtrip   (updated = now, or 600 s ago for old*)
  python3 - "$GPU_GATES_WATCHDOG_JSON" "$1" <<'PY'
import datetime, json, sys
p, m = sys.argv[1], sys.argv[2]
now = datetime.datetime.now().astimezone()
d = {"schema": "gpu_watchdog/1", "hang_strikes": 0, "stuck_since": {}, "warn": None, "trip": None, "last_trip": None,
     "tripped": False, "updated": (now - datetime.timedelta(seconds=600 if m.startswith("old") else 0)).isoformat(timespec="milliseconds")}
if m == "warn": d["warn"] = {"why": "metal probe 900 ms"}
if m == "strike": d["hang_strikes"] = 1
if m == "stuck": d["stuck_since"] = {"4242": 1793300000}
if m in ("trip", "oldtrip"): d.update(trip={"why": "metal probe hung"}, tripped=True, last_trip="2026-10-29T03:28:00-04:00")
json.dump(d, open(p, "w"))
PY
}
wd healthy

echo "== a. stuck engine"
ps_json "101|S|/sbin/launchd|launchd" "202|SE|$UE|$UE x.uproject -game"
expect "UnrealEditor in state E refuses" 3 "engine stuck exiting: machine-wide pause, notify the owner" python3 "$G" check
ps_json "202|Z|$UE|$UE"
expect "UnrealEditor in state Z refuses" 3 "engine stuck exiting" python3 "$G" check

echo "== b. GPU client count (legacy cap-2 cases, pinned with GPU_GATES_MAX_CLIENTS=2: the env override still works)"
export GPU_GATES_MAX_CLIENTS=2
ps_json "1|S|/Applications/Blender.app/Contents/MacOS/blender-thumbnailer|thumb" "2|S|npm exec @coding-solo/godot-mcp|npm exec @coding-solo/godot-mcp" \
        "3|S|/usr/bin/python3|python3 -m http.server" "4|S|/Applications/Unity Hub.app/Contents/MacOS/Unity Hub|hub"
expect "thumbnailer, godot-mcp title, plain python, Unity Hub are not clients" 0 "gpu_gates: go" python3 "$G" check
ps_json "1|S|/Applications/Blender.app/Contents/MacOS/Blender|Blender -b x.blend" "2|S|/opt/homebrew/bin/python3.12|python -m reader.train --epochs 9"
expect "Blender + reader.train trainer = 2 clients refuses and lists them" 3 "2 GPU clients already running.*" python3 "$G" check
grep -q "reader.train" "$W/out" && grep -q "Blender -b" "$W/out" && ok "refusal lists both processes" || no "refusal lists both processes" "$W/out"
ps_json "1|S|/Users/x/.venv/bin/python|python train.py --device mps  # torch" "2|R|/opt/homebrew/bin/godot|godot --path game"
expect "torch python + Godot refuses" 3 "2 GPU clients" python3 "$G" check
ps_json "1|S|$UE|$UE a.uproject" "2|S|/x/Game-Mac-Shipping|Game-Mac-Shipping"
expect "UnrealEditor + *-Shipping refuses" 3 "2 GPU clients" python3 "$G" check
ps_json "1|S|/Library/Python/bin/python3|python3 -m video2rig fit proj clip"
expect "one client (video2rig) is allowed" 0 "1 other GPU client.*" python3 "$G" check
unset GPU_GATES_MAX_CLIENTS

echo "== b3. cap 3 (owner 2026-10-29 23:20) + watchdog tripwire (fake gpu_watchdog.json)"
TWO=("1|S|/Applications/Blender.app/Contents/MacOS/Blender|Blender -b x.blend" "2|S|/opt/homebrew/bin/python3.12|python -m reader.train --epochs 9")
wd healthy; ps_json "${TWO[@]}"
expect "healthy watchdog, 2 clients (Blender + MPS trainer): go, ours is #3" 0 "2 other GPU client\(s\), cap 3: ours would be #3" python3 "$G" check
ps_json "${TWO[@]}" "3|S|$UE|$UE a.uproject -game"
expect "healthy watchdog, 3 clients: refuses at cap 3" 3 "3 GPU clients already running \(cap 3, ours would be #4\)" python3 "$G" check
ps_json "${TWO[@]}" "3|S|/Users/x/Library/Application Support/CrossOver/Bottles/b/drive_c/Games/GTA5.exe|GTA5.exe"
expect "  ... an owner CrossOver game .exe counts as the third client" 3 "3 GPU clients already running \(cap 3.*" python3 "$G" check
ps_json "${TWO[@]}"
wd warn;   expect "watchdog warn: demoted to cap 2, 2 clients refuse" 3 "2 GPU clients already running \(cap 2 \(demoted: watchdog warn" python3 "$G" check
wd strike; expect "watchdog hang_strikes=1: demoted to cap 2, refuses" 3 "cap 2 \(demoted: watchdog hang_strikes=1" python3 "$G" check
wd stuck;  expect "watchdog stuck_since entry: demoted to cap 2, refuses" 3 "cap 2 \(demoted: watchdog stuck_since" python3 "$G" check
wd old;    expect "watchdog updated 600 s ago: stale -> cap 2, refuses" 3 "cap 2 \(demoted: watchdog stale: updated 600 s ago" python3 "$G" check
rm -f "$GPU_GATES_WATCHDOG_JSON"
expect "watchdog file missing: stale -> cap 2, refuses" 3 "watchdog stale: .*wd.json missing" python3 "$G" check
echo '{not json' > "$GPU_GATES_WATCHDOG_JSON"
expect "watchdog file unreadable: stale -> cap 2, refuses" 3 "watchdog stale: .*unreadable" python3 "$G" check
wd warn; ps_json "1|S|/opt/homebrew/bin/python3.12|python -m reader.train"
expect "watchdog warn, 1 client: go at cap 2, the demotion is printed" 0 "watchdog demotes the client cap to 2: watchdog warn" python3 "$G" check
wd warn; ps_json "${TWO[@]}"
GPU_GATES_MAX_CLIENTS=4 expect "a demotion also caps an env override (GPU_GATES_MAX_CLIENTS=4 + warn -> 2)" 3 "cap 2 \(demoted" python3 "$G" check
wd trip; ps_json "1|S|/sbin/launchd|launchd"
expect "watchdog trip: refuses every launch, even on an idle machine" 3 "watchdog TRIP .*every launch refused until the owner clears it" python3 "$G" check
wd oldtrip; expect "a stale file that says trip still refuses" 3 "watchdog TRIP" python3 "$G" check
wd healthy; expect "cap: healthy -> 'cap 3', exit 0" 0 "^cap 3$" python3 "$G" cap
wd strike;  expect "cap: strike -> 'cap 2' + reason, exit 0" 0 "hang_strikes=1 -> cap 2" python3 "$G" cap
wd trip;    expect "cap: trip -> 'cap 0', exit 3" 3 "^cap 0$" python3 "$G" cap
wd healthy; expect "status prints the effective cap" 0 "effective cap: 3 of 3" python3 "$G" status
python3 - "$REPO" "$GPU_GATES_WATCHDOG_JSON" <<'PYEOF' > "$W/out" 2>&1 && ok "a trip that appears during the util wait refuses (re-check after the wait)" || no "trip during util wait" "$W/out"
import json, sys
sys.path.insert(0, sys.argv[1] + '/tools/gpu'); import gpu_gates as G
calls = [0]
def util():
    calls[0] += 1
    if calls[0] == 2:   # mid-wait: the watchdog trips
        d = json.load(open(sys.argv[2])); d.update(trip={'why': 'hang'}, tripped=True); json.dump(d, open(sys.argv[2], 'w'))
    return 10.0
G.read_util = util
why = G.gates(wait=True, log=lambda m: None)
assert why and 'watchdog TRIP' in why[0] and 'during the util wait' in why[0], why
print('ok', why)
PYEOF
wd healthy

echo "== c. GPU utilization"
ps_json "1|S|/sbin/launchd|launchd"
GPU_GATES_FAKE_UTIL=95 expect "util 95 on every reading refuses after the wait" 3 "GPU util 95/95/95 % not < 90" python3 "$G" check
GPU_GATES_FAKE_UTIL=40,95,40,40,40,40 GPU_GATES_MAX_WAIT_S=5 expect "one high reading in three -> waits, then passes" 0 "waiting.*gpu_gates: util 40/40/40|util 40/40/40.*" python3 "$G" check
grep -q "waiting" "$W/out" && ok "the wait is printed" || no "the wait is printed" "$W/out"
GPU_GATES_FAKE_UTIL=89 expect "util 89 passes" 0 "util 89/89/89" python3 "$G" check
GPU_GATES_SAMPLE_S=0.3 GPU_GATES_FAKE_UTIL=10 bash -c "t0=\$(python3 -c 'import time;print(time.time())'); python3 '$G' check >/dev/null; python3 -c \"import time,sys; sys.exit(0 if time.time()-\$t0 >= 0.6 else 1)\"" \
  && ok "three readings are SAMPLE_S apart (2 gaps)" || no "three readings are SAMPLE_S apart"

echo "== d. 20 s launch gap"
python3 -c "import time; open('$W/last_launch','w').write('%.3f pid=1 label=other\n' % (time.time()-1))"
GPU_GATES_MIN_GAP_S=3 expect "--no-wait reports a recent launch" 3 "last engine launch only 1 s ago" python3 "$G" check --no-wait
t0=$(date +%s); GPU_GATES_MIN_GAP_S=3 python3 "$G" check > "$W/out" 2>&1; rc=$?; dt=$(( $(date +%s) - t0 ))
[ $rc = 0 ] && [ $dt -ge 1 ] && grep -q "waiting 2 s for the 3 s gap" "$W/out" && ok "check waits out the gap (${dt} s) then goes" || no "gap wait" "$W/out"
python3 "$G" stamp --label test && grep -q "label=test" "$W/last_launch" && ok "stamp writes epoch + label" || no "stamp"
rm -f "$W/last_launch"

echo "== capture.sh is gated too (CAPTURE_GATES_ONLY=1: never launches)"
ps_json "202|SE|$UE|$UE"
CAPTURE_GATES_ONLY=1 expect "capture.sh refuses on a stuck engine" 3 "REFUSED by the GPU gates" "$REPO/tools/brute/capture.sh" ab_idle_front -movie
ps_json "1|S|/Applications/Blender.app/Contents/MacOS/Blender|Blender" "2|S|$UE|$UE"
GPU_GATES_MAX_CLIENTS=2 CAPTURE_GATES_ONLY=1 expect "capture.sh refuses at 2 clients (cap pinned to 2)" 3 "REFUSED by the GPU gates" "$REPO/tools/brute/capture.sh" ab_idle_front -movie
CAPTURE_GATES_ONLY=1 expect "capture.sh at 2 clients, cap 3, healthy watchdog: gates pass, nothing launched" 0 "gates passed \(CAPTURE_GATES_ONLY=1" "$REPO/tools/brute/capture.sh" ab_idle_front -movie
ps_json "1|S|/Applications/Blender.app/Contents/MacOS/Blender|Blender" "2|S|$UE|$UE" "3|S|/x/Game-Mac-Shipping|Game-Mac-Shipping"
CAPTURE_GATES_ONLY=1 expect "capture.sh refuses at 3 clients (cap 3)" 3 "REFUSED by the GPU gates" "$REPO/tools/brute/capture.sh" ab_idle_front -movie
ps_json "1|S|/Applications/Blender.app/Contents/MacOS/Blender|Blender" "2|S|$UE|$UE"
wd warn; CAPTURE_GATES_ONLY=1 expect "capture.sh refuses at 2 clients when the watchdog warns (cap 2)" 3 "cap 2 \(demoted: watchdog warn" "$REPO/tools/brute/capture.sh" ab_idle_front -movie
wd trip; ps_json "1|S|/sbin/launchd|launchd"
CAPTURE_GATES_ONLY=1 expect "capture.sh refuses on a watchdog trip" 3 "watchdog TRIP" "$REPO/tools/brute/capture.sh" ab_idle_front -movie
wd healthy
ps_json "1|S|/sbin/launchd|launchd"
CAPTURE_GATES_ONLY=1 expect "capture.sh clean machine: gates pass, nothing launched" 0 "gates passed \(CAPTURE_GATES_ONLY=1" "$REPO/tools/brute/capture.sh" ab_idle_front -movie

echo "== ab_ingame.py run: preflight + budget (stub capture.sh)"
cat > "$W/capstub.sh" <<'EOF'
#!/bin/bash
echo "STUB capture $*" >> "$AB_STUB_LOG"; mkdir -p "$AB_CAP_ROOT/$1"; echo x > "$AB_CAP_ROOT/$1/$1.mp4"; exit 0
EOF
chmod +x "$W/capstub.sh"
export AB_CAPTURE_SH="$W/capstub.sh" AB_CAP_ROOT="$W/cap" AB_SET_ROOT="$W/set" AB_STREAM_FLAG="$W/STREAMING" AB_STUB_LOG="$W/stub.log"
ps_json "202|SE|$UE|$UE"
expect "run refuses on a stuck engine, stub never called" 3 "REFUSED:.*|engine stuck exiting" python3 "$REPO/tools/brute/v2r/ab_ingame.py" run --label new --cases idle_front --ignore-window
[ ! -f "$W/stub.log" ] && ok "no capture call after a refusal" || no "no capture call after a refusal" "$W/stub.log"
ps_json "1|S|/sbin/launchd|launchd"; wd trip
expect "run refuses on a watchdog trip" 3 "watchdog TRIP" python3 "$REPO/tools/brute/v2r/ab_ingame.py" run --label new --cases idle_front --ignore-window
[ ! -f "$W/stub.log" ] && ok "no capture call after a trip refusal" || no "no capture call after a trip refusal" "$W/stub.log"
wd healthy
ps_json "1|S|/sbin/launchd|launchd"
AB_COOLDOWN_S=2 expect "two cases: budget lines + cool-down printed" 0 "budget: cool-down 2 s before ab_idle_left" python3 "$REPO/tools/brute/v2r/ab_ingame.py" run --label new --cases idle_front,idle_left --ignore-window
grep -q "budget: launch 2/10 this hour" "$W/out" && ok "launch count printed" || no "launch count printed" "$W/out"
[ "$(wc -l < "$W/stub.log" | tr -d ' ')" = 2 ] && ok "stub called once per case" || no "stub called once per case" "$W/stub.log"
python3 - "$REPO" <<'EOF' > "$W/out" 2>&1 && ok "Budget: 6/h rolling window + cool-down (fake clock)" || no "Budget fake clock" "$W/out"
import sys; sys.path.insert(0, sys.argv[1] + '/tools/brute/v2r'); import ab_ingame as A
t = [0.0]; b = A.Budget(6, 30, clock=lambda: t[0], sleep=lambda s: t.__setitem__(0, t[0] + s)); starts = []
for i in range(8):
    b.wait_turn('c%d' % i); starts.append(t[0]); b.launched('c%d' % i); t[0] += 100; b.ended()
gaps = [starts[i+1] - starts[i] for i in range(7)]
assert all(g >= 130 for g in gaps), gaps                       # 100 s case + 30 s cool-down
assert starts[6] - starts[0] >= 3600, starts                   # the 7th launch waits for the first to age out of the hour
assert all(sum(1 for s in starts if s0 <= s < s0 + 3600) <= 6 for s0 in starts), starts
print('starts', [round(s) for s in starts])
EOF

echo "== ab_ingame.py run --cam-dist / --hide-help (stub capture.sh; case files rewritten, never the repo's)"
cat > "$W/capstub_cam.sh" <<'EOF'
#!/bin/bash
# records the args, BRUTE_CASES_DIR and the camDist of the case file the real capture.sh would hand the game
CF="${BRUTE_CASES_DIR:-$AB_REPO_CASES}/$1.json"
echo "STUB $* | BRUTE_CASES_DIR=${BRUTE_CASES_DIR:-unset} | camDist=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["spawn"]["camDist"])' "$CF")" >> "$AB_STUB_LOG"
mkdir -p "$AB_CAP_ROOT/$1"; echo x > "$AB_CAP_ROOT/$1/$1.mp4"; echo "movie frames: 9999" > "$AB_CAP_ROOT/$1/capture.txt"; exit 0
EOF
chmod +x "$W/capstub_cam.sh"
AB="$REPO/tools/brute/v2r/ab_ingame.py"
export AB_REPO_CASES="$REPO/tools/brute/cases"
CAMENV=(env AB_CAPTURE_SH="$W/capstub_cam.sh" AB_SET_ROOT="$W/camset" AB_STUB_LOG="$W/camstub.log" AB_COOLDOWN_S=0)
ps_json "1|S|/sbin/launchd|launchd"; wd healthy
for bad in abc 0 -1 nan inf 0.4 101; do
  expect "--cam-dist $bad is refused by the parser" 2 "must be a number of metres" "${CAMENV[@]}" python3 "$AB" run --label cam1 --cases idle_front --cam-dist=$bad --dry-run
done
expect "default dry run: camDist 7.5, help shown, no case rewrite, no -WHNoHud" 0 "camera: camDist 7.5, help box shown" "${CAMENV[@]}" python3 "$AB" run --label cam1 --cases idle_front --ignore-window --dry-run
grep -q "BRUTE_CASES_DIR" "$W/out" && no "default dry run must not set BRUTE_CASES_DIR" "$W/out" || ok "default dry run does not set BRUTE_CASES_DIR"
grep -q "WHNoHud" "$W/out" && no "default dry run must not add -WHNoHud" "$W/out" || ok "default dry run does not add -WHNoHud"
expect "--cam-dist 4.0 --hide-help dry run shows the rewrite, env and -WHNoHud" 0 "camera: camDist 4 \(case files rewritten.*help box hidden \(-WHNoHud\)" "${CAMENV[@]}" python3 "$AB" run --label cam1 --cases idle_front --ignore-window --dry-run --cam-dist 4.0 --hide-help
grep -qE "BRUTE_CASES_DIR=.*capstub_cam.sh ab_idle_front .* -- -WHNoHud" "$W/out" && ok "dry-run command carries BRUTE_CASES_DIR and the -WHNoHud extra" || no "dry-run command line" "$W/out"
expect "--hide-help does not duplicate an -WHNoHud already in --extra" 0 "help box hidden" "${CAMENV[@]}" python3 "$AB" run --label cam1 --cases idle_front --ignore-window --dry-run --hide-help --extra "-WHNoHud -WHBruteNoClipTiming"
[ "$(grep -o WHNoHud "$W/out" | wc -l | tr -d ' ')" = 2 ] && ok "-WHNoHud appears once in the command (+ once in the camera line)" || no "-WHNoHud duplicated" "$W/out"
[ ! -d "$W/camset/cam1/.cases" ] && ok "dry run wrote no case copies" || no "dry run wrote case copies"
rm -f "$W/camstub.log"
expect "real run (stub), default flags" 0 "DONE ab_idle_front" "${CAMENV[@]}" python3 "$AB" run --label camd --cases idle_front --ignore-window
grep -q "BRUTE_CASES_DIR=unset | camDist=7.5" "$W/camstub.log" && ok "default run: no BRUTE_CASES_DIR, repo case file (camDist 7.5)" || no "default run stub" "$W/camstub.log"
python3 - "$W/camset/camd/ab_idle_front" <<'PYEOF' > "$W/out" 2>&1 && ok "default run.json records cam_dist 7.5, hide_help false; capture.txt line" || no "default run.json" "$W/out"
import json, sys, os
d = sys.argv[1]; r = json.load(open(os.path.join(d, 'run.json')))
assert r['cam_dist'] == 7.5 and r['hide_help'] is False and r['extra'] == [], r
assert 'ab_ingame: cam_dist=7.5 hide_help=0' in open(os.path.join(d, 'capture.txt')).read()
assert not os.path.exists(os.path.join(d, 'case.json'))
PYEOF
rm -f "$W/camstub.log"
expect "real run (stub), --cam-dist 4.0 --hide-help, 2 cases" 0 "DONE ab_idle_left" "${CAMENV[@]}" python3 "$AB" run --label camc --cases idle_front,idle_left --ignore-window --cam-dist 4.0 --hide-help
[ "$(grep -c "BRUTE_CASES_DIR=$W/camset/camc/.cases | camDist=4.0" "$W/camstub.log")" = 2 ] && ok "close-up run: stub saw the rewritten case dir and camDist 4.0 for both cases" || no "close-up stub log" "$W/camstub.log"
grep -q -- "-- -WHNoHud | " "$W/camstub.log" && ok "close-up run passes -WHNoHud after --" || no "-WHNoHud arg" "$W/camstub.log"
python3 - "$W/camset/camc/ab_idle_left" "$REPO" <<'PYEOF' > "$W/out" 2>&1 && ok "close-up run.json/capture.txt/case.json record 4.0 + hidden help; rewritten case differs only in camDist" || no "close-up record" "$W/out"
import json, sys, os
d, repo = sys.argv[1], sys.argv[2]; r = json.load(open(os.path.join(d, 'run.json')))
assert r['cam_dist'] == 4.0 and r['hide_help'] is True and r['extra'] == ['-WHNoHud'], r
assert 'ab_ingame: cam_dist=4 hide_help=1' in open(os.path.join(d, 'capture.txt')).read()
new = json.load(open(os.path.join(d, 'case.json'))); old = json.load(open(os.path.join(repo, 'tools/brute/cases/ab_idle_left.json')))
assert new['spawn']['camDist'] == 4.0 and old['spawn']['camDist'] == 7.5
new['spawn']['camDist'] = 7.5; assert new == old
PYEOF
python3 "$AB" gen --check > "$W/out" 2>&1
grep -q DIFFERS "$W/out" && no "gen --check: a repo case file differs" "$W/out" || ok "the repo's generated case files are untouched (gen --check: no DIFFERS)"
grep -q 'BRUTE_CASES_DIR:-\$ROOT/tools/brute/cases' "$REPO/tools/brute/capture.sh" && grep -q '"-WHBruteScript=\$CASES/\$CASE.json"' "$REPO/tools/brute/capture.sh" && ok "capture.sh builds -WHBruteScript from BRUTE_CASES_DIR (default: repo cases)" || no "capture.sh BRUTE_CASES_DIR"

echo "== ab_ingame.py pack: same camera setup required (--allow-mixed-cam)"
AB_SET_ROOT="$W/packcam" python3 - "$REPO" "$W" <<'PYEOF' > "$W/out" 2>&1 && ok "pack refuses mixed camDist / help, --allow-mixed-cam packs with a NOTE, legacy sets count as 7.5 + help shown, capture.txt fallback" || no "pack camera gate" "$W/out"
import os, sys, json, shutil, io, contextlib
sys.path.insert(0, sys.argv[1] + '/tools/brute/v2r'); import ab_ingame as A
W = sys.argv[2]; R = os.path.join(W, 'packcam')
def mk(lab, cam=None, hide=False, how='run.json'):
    d = os.path.join(R, lab, 'ab_jump_front'); os.makedirs(d)
    open(os.path.join(d, 'ab_jump_front.mp4'), 'w').write(lab)
    if cam is not None and how == 'run.json': json.dump({'label': lab, 'cam_dist': cam, 'hide_help': hide}, open(os.path.join(d, 'run.json'), 'w'))
    if cam is not None and how == 'capture.txt': open(os.path.join(d, 'capture.txt'), 'w').write('x\nab_ingame: cam_dist=%g hide_help=%d\n' % (cam, hide))
mk('close_a', 4.0, True); mk('close_b', 4.0, True); mk('wide', 7.5, False); mk('legacy'); mk('close_nohide', 4.0, False); mk('close_txt', 4.0, True, 'capture.txt'); mk('d5', 5.0, True)
A.check_case = lambda d, n: []; A.events = lambda log: [(0.0, 'e1')]; A.trim = lambda src, dst, t0, t1: shutil.copy(src, dst)
n = [0]
def run(a, b, *more):
    n[0] += 1; sys.argv = ['ab_ingame.py', 'pack', '--a', a, '--b', b, '--cases', 'jump_front', '--out', os.path.join(W, 'pk%d' % n[0])] + list(more); buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf): A.main()
    except SystemExit as e:
        return (e.code if isinstance(e.code, int) else 1), buf.getvalue() + str(e.code)
    return 0, buf.getvalue()
assert A.cam_setup(os.path.join(R, 'legacy', 'ab_jump_front'))[:2] == (7.5, False)
assert A.cam_setup(os.path.join(R, 'close_txt', 'ab_jump_front'))[:3] == (4.0, True, 'capture.txt')
rc, o = run('close_a', 'close_b'); assert rc == 0 and 'NOT PACKED' not in o, o                       # same close-up setup: packs
rc, o = run('close_a', 'close_txt'); assert rc == 0, o                                               # run.json vs capture.txt record: same
rc, o = run('close_a', 'wide'); assert rc and 'not captured with the same camera setup' in o and 'camDist 4' in o and 'camDist 7.5' in o and '--allow-mixed-cam' in o, o
assert not os.path.exists(os.path.join(W, 'pk%d' % n[0], 'critic')), 'a refused pack wrote files'
rc, o = run('close_a', 'd5'); assert rc and 'camDist 4' in o and 'camDist 5' in o, o                  # 4.0 vs 5.0: any difference refused
rc, o = run('close_a', 'close_nohide'); assert rc and 'help hidden' in o and 'help shown' in o, o     # same distance, help differs: refused
rc, o = run('close_a', 'legacy'); assert rc and 'legacy (not recorded' in o, o                         # an unrecorded set is the wide setup
rc, o = run('wide', 'legacy'); assert rc == 0, o                                                     # unrecorded vs recorded wide: same
rc, o = run('close_a', 'wide', '--allow-mixed-cam')
assert rc == 0 and 'NOTE --allow-mixed-cam' in o and os.path.exists(os.path.join(W, 'pk%d' % n[0], 'critic', 'jump_front', 'A.mp4')), o
k = json.load(open(os.path.join(W, 'pk%d' % n[0], '_director', 'KEY.json'))); assert sorted(k['pairs']) == ['jump_front'], k
PYEOF

echo "== run_game.sh frame-1 watchdog (stub engine via WH_UE_BIN)"
cat > "$W/ue_silent.sh" <<'EOF'
#!/bin/bash
for a in "$@"; do case "$a" in -abslog=*) L="${a#-abslog=}";; esac; done
echo "LogInit: loading" > "$L"; trap 'echo "LogExit: SIGTERM" >> "$L"; exit 0' TERM; while :; do sleep 0.2; done
EOF
cat > "$W/ue_ticks.sh" <<'EOF'
#!/bin/bash
for a in "$@"; do case "$a" in -abslog=*) L="${a#-abslog=}";; esac; done
echo "LogOutputDevice: Error: Ensure condition failed: OriginX <= OriginMax" > "$L"; sleep 1
echo "LogWebHomage: Display: WH_BRUTE tick1 frame=1 t=0.017 script 1" >> "$L"; sleep 4; echo "WH_QUIT t=4.00" >> "$L"; exit 0
EOF
chmod +x "$W/ue_silent.sh" "$W/ue_ticks.sh"
WH_UE_BIN="$W/ue_silent.sh" expect "no tick line -> NO FIRST FRAME, SIGTERM, exit 5" 5 "NO FIRST FRAME: engine stopped" \
  "$REPO/unreal/WebHomage/Scripts/run_game.sh" "$W/rg1" -name t -quit 3 -timeout 30 -firstline 'WH_BRUTE (tick1|t=)' -firstline_s 3
grep -q "LogExit: SIGTERM" "$W/rg1/t.log" && ok "the stub got SIGTERM (not SIGKILL)" || no "SIGTERM first" "$W/rg1/t.log"
WH_UE_BIN="$W/ue_ticks.sh" expect "tick line in time (benign OriginX ensure ignored) -> normal exit" 0 "first frame after" \
  "$REPO/unreal/WebHomage/Scripts/run_game.sh" "$W/rg2" -name t -quit 3 -timeout 30 -firstline 'WH_BRUTE (tick1|t=)' -firstline_s 3
grep -q "label=run_game:t" "$W/last_launch" && ok "run_game stamped last_launch" || no "run_game stamp" "$W/last_launch"

echo "== ab_ingame.py check: wall_release allowed only at/after the script's own release"
python3 - "$REPO" "$W" <<'PYEOF' > "$W/out" 2>&1 && ok "wall_release before script release (t_rel-0.05) fails; at/after passes; rescue and wall_kick always fail" || no "wall_release before/after script release" "$W/out"
import os, sys
sys.path.insert(0, sys.argv[1] + '/tools/brute/v2r'); import ab_ingame as A
W = sys.argv[2]; name = 'ab_wall_back'
def case_dir(tag, rel_t, extra=()):
    d = os.path.join(W, 'chk_' + tag, name); os.makedirs(d, exist_ok=True)
    ev = ['WH_BRUTE t=3.03 wall_run_start', 'WH_BRUTE t=3.32 wall_punch L', 'WH_BRUTE t=4.33 wall_top_out', 'WH_BRUTE t=4.67 wall_catch',
          'WH_BRUTE t=4.95 wall_punch L', 'WH_BRUTE t=7.05 wall_top_out', 'WH_BRUTE t=7.38 wall_catch']
    if rel_t is not None: ev.append('WH_BRUTE t=%.2f wall_release pos (271.2 140.5 73.1) vel (-4.0 0.0 0.0)' % rel_t)
    ev += list(extra) + ['WH_QUIT t=8.60']
    open(os.path.join(d, name + '.log'), 'w').write('\n'.join(ev) + '\n')
    open(os.path.join(d, name + '_brute.csv'), 'w').write('frame,x,y,z\n0,249,140,0\n1,271,140,73\n')
    open(os.path.join(d, name + '.mp4'), 'w').write('x')
    return d
def problems(tag, rel_t, extra=()):
    return A.check_case(case_dir(tag, rel_t, extra), name)
rel = A.script_release_time(A.load_case(name)['keys'])
assert rel == 7.5, rel
assert not [p for p in problems('at', 7.50) if 'forbidden' in p], problems('at', 7.50)          # the script's own release
assert not [p for p in problems('edge', 7.45) if 'forbidden' in p], problems('edge', 7.45)      # t_rel - 0.05 is allowed
early = [p for p in problems('early', 7.44) if 'forbidden event wall_release' in p]               # just before it fails
assert early and 'before script release at 7.50' in early[0], problems('early', 7.44)
assert [p for p in problems('six', 6.00) if 'forbidden event wall_release' in p]                  # a release mid-climb fails
assert [p for p in problems('kick', 7.50, ['WH_BRUTE t=7.20 wall_kick pos (1 1 1) vel (0 0 0)']) if 'wall_kick' in p]
assert [p for p in problems('resc', 7.50, ['WH_BRUTE t=5.00 rescue']) if 'rescue' in p]
print('release 7.50 ok; 7.45 ok; 7.44 fails; 6.00 fails; wall_kick and rescue fail')
PYEOF

echo "== ab_ingame.py pack --a/--b (labels, --cases, extending an existing pack; trim / gates / events stubbed)"
AB_SET_ROOT="$W/sets" python3 - "$REPO" "$W" <<'PYEOF' > "$W/out" 2>&1 && ok "pack --a r3 --b new / --b old into one dir: labels in KEY, balanced A/B, brief lists all groups, duplicate refused" || no "pack --a/--b" "$W/out"
import os, sys, json, shutil, argparse, io, contextlib
sys.path.insert(0, sys.argv[1] + '/tools/brute/v2r'); import ab_ingame as A
W = sys.argv[2]; R = os.path.join(W, 'sets'); O = os.path.join(W, 'blind-r3')
assert A.SET_ROOT == R, A.SET_ROOT
for lab, cs in (('old', ['combat_front', 'combat_left']), ('new', ['jump_front', 'lunge_front']), ('r3', ['jump_front', 'lunge_front', 'combat_front'])):
    for c in cs:
        d = os.path.join(R, lab, 'ab_' + c); os.makedirs(d)
        open(os.path.join(d, 'ab_%s.mp4' % c), 'w').write(lab)          # content = set label, so the copies can be traced
A.check_case = lambda d, n: []
A.events = lambda log: [(0.0, 'e1')]
A.trim = lambda src, dst, t0, t1: shutil.copy(src, dst)
def run(*argv):
    sys.argv = ['ab_ingame.py', 'pack'] + list(argv); buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf): A.main()
    except SystemExit as e:
        return (e.code if isinstance(e.code, int) else 1), buf.getvalue() + str(e.code)
    return 0, buf.getvalue()
assert A.label_arg('r3') == 'r3'
for bad in ('R3', '../x', 'a b', ''):
    try: A.label_arg(bad); raise AssertionError('label accepted: %r' % bad)
    except argparse.ArgumentTypeError: pass
rc, o = run('--a', 'r3', '--out', O); assert rc and '--a and --b together' in o, o
rc, o = run('--a', 'r3', '--b', 'r3', '--out', O); assert rc and 'different labels' in o, o
rc, o = run('--a', 'r3', '--b', 'new', '--cases', 'jump_front,lunge_front,combat_front', '--out', O)
assert rc == 0 and 'NOT PACKED (missing in r3 or new): ab_combat_front' in o, o
k = json.load(open(os.path.join(O, '_director', 'KEY.json')))
assert sorted(k['pairs']) == ['jump_front', 'lunge_front'], k
assert sorted(r['A'] for r in k['pairs'].values()) == ['new', 'r3'], k        # balanced: one A from each set
for cid, r in k['pairs'].items():
    for ab in 'AB':
        assert open(os.path.join(O, 'critic', cid, ab + '.mp4')).read() == r[ab], (cid, ab, r)
rc, o = run('--a', 'r3', '--b', 'old', '--cases', 'combat_front', '--out', O)
assert rc == 0 and 'extending the pack' in o, o
k = json.load(open(os.path.join(O, '_director', 'KEY.json')))
assert sorted(k['pairs']) == ['combat_front', 'jump_front', 'lunge_front'] and set(k['pairs']['combat_front'].values()) == {'r3', 'old'}, k
assert set(k['sets']) == {'r3', 'new', 'old'} and [p['b'] for p in k['packs']] == ['new', 'old'], k
for cid, r in k['pairs'].items():
    for ab in 'AB':
        assert open(os.path.join(O, 'critic', cid, ab + '.mp4')).read() == r[ab], (cid, ab, r)
br = open(os.path.join(O, 'critic', 'brief.md')).read()
assert all('`%s_*`' % g in br for g in ('jump', 'lunge', 'combat')), br
assert not any(w in br for w in ('r3', 'old_dir', 'new_dir')), 'brief leaks a label'
rep = json.load(open(os.path.join(O, '_director', 'report.json')))['event_sequences']
assert rep['combat_front'] == {'same_event_sequence': True, 'r3_events': 1, 'old_events': 1}, rep
rc, o = run('--a', 'r3', '--b', 'old', '--cases', 'combat_front', '--out', O); assert rc and 'already holds combat_front' in o, o
rc, o = run('--a', os.path.join(R, 'r3'), '--b', os.path.join(R, 'old'), '--cases', 'combat_front', '--out', O, '--force', '--dry-run')
assert rc == 0 and 'combat_front: A=' in o, o                                   # dirs work as well as labels
print('labels, --cases, extend, duplicate refusal, dirs: ok')
PYEOF

echo; echo "gates test: $PASS passed, $FAIL failed  (work dir $W)"
[ $FAIL = 0 ] && rm -rf "$W"
exit $(( FAIL > 0 ))

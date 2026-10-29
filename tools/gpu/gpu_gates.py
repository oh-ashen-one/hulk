#!/usr/bin/env python3
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
"""Machine-wide GPU launch gates, checked right before any engine launch (tools/brute/capture.sh, ab_ingame.py run).

Why: 2026-10-29 the Studio wedged for 7 hours. 15 cold `-game` editor launches back to back (34 GB each, 0 s gaps, GPU at 100 % at every
launch) plus Metal/torch trainers that the slot tool does not count; the WindowServer watchdog killed the session at 03:28. gpu_slot.sh
counts its own holders only; these gates look at the whole machine.

  a. any UnrealEditor in ps state E (exiting) or Z (zombie)  -> refuse (machine-wide pause, notify the owner)
  b. GPU clients (UnrealEditor*, Godot*, Unity* editors, *-Shipping, Blender (not blender-thumbnailer), python whose command line
     contains reader.train / video2rig / torch) >= 2           -> refuse (ours would be the third); the list is printed
  c. "Device Utilization %" (ioreg IOAccelerator) < 90 on three readings 5 s apart; otherwise poll up to 10 min, then refuse
  d. >= 20 s since the last engine launch anywhere (~/.cache/gpu-slot/last_launch, written by `stamp` at every launch; anyone else
     may write it too): waits for the rest of the gap, never refuses
  (STREAMING flag and the 11-13 ET window stay where they were: gpu_slot.py and ab_ingame.preflight.)

  python3 tools/gpu/gpu_gates.py check [--no-wait]   exit 0 = go, 3 = refused (reasons on stdout)
  python3 tools/gpu/gpu_gates.py stamp [--label X]   record a launch now (run_game.sh does this right before starting the engine)
  python3 tools/gpu/gpu_gates.py gap                 wait until 20 s after the last launch (run_game.sh, inside the slot)
  python3 tools/gpu/gpu_gates.py status              print clients, util, last launch; never waits, always exit 0

Test hooks (env, tools/brute/v2r/test_ab_ingame_gates.sh): GPU_GATES_FAKE_PS=<json [{pid,stat,comm,args}]>,
GPU_GATES_FAKE_UTIL="95,95,40" (one value per reading, the last repeats), GPU_GATES_SAMPLE_S (5), GPU_GATES_POLL_S (15),
GPU_GATES_MAX_WAIT_S (600), GPU_GATES_MIN_GAP_S (20), GPU_GATES_LAST_LAUNCH (path), GPU_GATES_UTIL_MAX (90), GPU_GATES_MAX_CLIENTS (2).
"""
import json
import os
import re
import subprocess
import sys
import time


def _env(k, d):
    v = os.environ.get(k)
    return type(d)(v) if v not in (None, '') else d


SAMPLE_S = _env('GPU_GATES_SAMPLE_S', 5.0)
POLL_S = _env('GPU_GATES_POLL_S', 15.0)
MAX_WAIT_S = _env('GPU_GATES_MAX_WAIT_S', 600.0)
MIN_GAP_S = _env('GPU_GATES_MIN_GAP_S', 20.0)
UTIL_MAX = _env('GPU_GATES_UTIL_MAX', 90.0)
MAX_CLIENTS = _env('GPU_GATES_MAX_CLIENTS', 2)
LAST_LAUNCH = os.path.expanduser(os.environ.get('GPU_GATES_LAST_LAUNCH', '~/.cache/gpu-slot/last_launch'))
UNITY_HELPERS = ('unity hub', 'unityshadercompiler', 'unitypackagemanager', 'unitycrashhandler', 'unityhelper')
TRAIN_WORDS = ('reader.train', 'video2rig', 'torch')

_fake_util = None


def processes():
    """[{pid, stat, comm, args}] for every process (comm = executable path, may contain spaces)."""
    fake = os.environ.get('GPU_GATES_FAKE_PS')
    if fake:
        return json.load(open(fake))
    def ps(fmt):
        try:
            return subprocess.run(['ps', '-axo', fmt], capture_output=True, text=True, timeout=10).stdout.splitlines()
        except Exception:  # noqa: BLE001
            return []
    out = {}
    for ln in ps('pid=,ppid=,stat=,comm='):
        p = ln.strip().split(None, 3)
        if len(p) == 4 and p[0].isdigit():
            out[int(p[0])] = {'pid': int(p[0]), 'ppid': int(p[1]) if p[1].isdigit() else 0, 'stat': p[2], 'comm': p[3], 'args': ''}
    for ln in ps('pid=,args='):
        p = ln.strip().split(None, 1)
        if len(p) == 2 and p[0].isdigit() and int(p[0]) in out:
            out[int(p[0])]['args'] = p[1]
    return list(out.values())


def exe_name(comm):
    """Executable name: basename of a path; a process title that is not a path ("npm exec @x/godot-mcp") counts by its first word."""
    comm = comm.strip()
    return os.path.basename(comm.rstrip('/')) if comm.startswith('/') else (comm.split() or [''])[0]


WINE_SERVICES = ('wineserver', 'services.exe', 'explorer.exe', 'winedevice', 'plugplay', 'rpcss', 'svchost', 'conhost', 'steam',
                 'steamwebhelper', 'crossover', 'winemenubuilder', 'start.exe', 'tabtip', 'rundll32', 'launcher', 'epicgames',
                 'rockstar', 'socialclub', 'gameoverlay', 'cmd.exe', 'wine64-preloader', 'wine-preloader')


def client_kind(p):
    """Why this process counts as a GPU client, or None."""
    b = exe_name(p['comm']).lower()
    if b.startswith('unrealeditor'):
        return 'unreal'
    if b.startswith('godot'):
        return 'godot'
    if b.startswith('unity') and not b.startswith(UNITY_HELPERS):
        return 'unity'
    if b.endswith('-shipping'):
        return 'shipping'
    if b == 'blender':
        return 'blender'
    if b.startswith('python') and any(w in p.get('args', '') for w in TRAIN_WORDS):
        return 'python-gpu'
    # the owner's Windows games run through CrossOver/Wine (Bully, GTA V ...): a game .exe is a heavy renderer and is NEVER ours
    # to touch; launchers and wine services do not count
    if b.endswith('.exe') and not any(w in b for w in WINE_SERVICES):
        return 'owner-game'
    return None


def gpu_clients(procs=None):
    """One entry per GPU job: a client whose parent is itself a listed client (reader.prepare -> reader.train, an engine's
    helper) is folded into the parent, so one training job or one engine counts once."""
    me = {os.getpid(), os.getppid()}
    cl = [dict(p, kind=client_kind(p)) for p in (procs if procs is not None else processes()) if p['pid'] not in me and client_kind(p)]
    pids = {p['pid'] for p in cl}
    return [p for p in cl if p.get('ppid', 0) not in pids]


def stuck_engines(procs=None):
    return [p for p in (procs if procs is not None else processes())
            if exe_name(p['comm']).lower().startswith('unrealeditor') and re.search(r'[EZ]', p['stat'])]


def read_util():
    """Max "Device Utilization %" over accelerators, or None if unreadable."""
    global _fake_util
    fake = os.environ.get('GPU_GATES_FAKE_UTIL')
    if fake:
        if _fake_util is None:
            _fake_util = [float(x) for x in fake.split(',')]
        return _fake_util.pop(0) if len(_fake_util) > 1 else _fake_util[0]
    try:
        out = subprocess.run(['ioreg', '-r', '-d', '1', '-c', 'IOAccelerator'], capture_output=True, text=True, timeout=10).stdout
    except Exception:  # noqa: BLE001
        return None
    vals = [int(x) for x in re.findall(r'"Device Utilization %"\s*=\s*(\d+)', out)]
    return float(max(vals)) if vals else None


def util_gate(wait=True, log=print):
    """None if three readings SAMPLE_S apart are all < UTIL_MAX (polls up to MAX_WAIT_S when wait), else the refusal reason."""
    t0 = time.time()
    while True:
        r = []
        for i in range(3):
            if i:
                time.sleep(SAMPLE_S)
            r.append(read_util())
        if all(u is not None and u < UTIL_MAX for u in r):
            log('gpu_gates: util %s %% (< %.0f on 3 readings %.0f s apart) ok' % ('/'.join('%.0f' % u for u in r), UTIL_MAX, SAMPLE_S))
            return None
        shown = '/'.join('?' if u is None else '%.0f' % u for u in r)
        waited = time.time() - t0
        if not wait or waited + POLL_S > MAX_WAIT_S:
            return 'GPU util %s %% not < %.0f on three readings (waited %.0f s of %.0f)' % (shown, UTIL_MAX, waited, MAX_WAIT_S)
        log('gpu_gates: util %s %% (need < %.0f on 3 readings), waiting %.0f s (%.0f of %.0f s)' % (shown, UTIL_MAX, POLL_S, waited, MAX_WAIT_S))
        time.sleep(POLL_S)


def last_launch():
    """(epoch, text) of the last recorded launch, or (None, '')."""
    try:
        txt = open(LAST_LAUNCH).read().strip()
        return float(txt.split()[0]), txt
    except Exception:  # noqa: BLE001
        try:
            return os.path.getmtime(LAST_LAUNCH), ''
        except OSError:
            return None, ''


def wait_gap(log=print):
    """Sleep until MIN_GAP_S after the last launch anywhere; returns the seconds waited."""
    t, txt = last_launch()
    if t is None:
        return 0.0
    rest = MIN_GAP_S - (time.time() - t)
    if rest <= 0:
        return 0.0
    log('gpu_gates: last engine launch %.0f s ago (%s), waiting %.0f s for the %.0f s gap' % (time.time() - t, txt or LAST_LAUNCH, rest, MIN_GAP_S))
    time.sleep(rest)
    return rest


def stamp(label=''):
    os.makedirs(os.path.dirname(LAST_LAUNCH), exist_ok=True)
    tmp = LAST_LAUNCH + '.%d' % os.getpid()
    with open(tmp, 'w') as fh:
        fh.write('%.3f pid=%d label=%s %s\n' % (time.time(), os.getppid(), label or '-', time.strftime('%Y-%m-%dT%H:%M:%S')))
    os.replace(tmp, LAST_LAUNCH)


def fmt_proc(p):
    return '  pid %-6s %-5s %-10s %s' % (p['pid'], p['stat'], p.get('kind', ''), (p.get('args') or p['comm'])[:150])


def gates(wait=True, log=print):
    """Reasons not to launch (empty = go). Order: stuck engine, client count, gap (waits), util (waits up to MAX_WAIT_S)."""
    procs = processes()
    stuck = stuck_engines(procs)
    if stuck:
        return ['engine stuck exiting: machine-wide pause, notify the owner\n' + '\n'.join(fmt_proc(p) for p in stuck)]
    cl = gpu_clients(procs)
    if len(cl) >= MAX_CLIENTS:
        return ['%d GPU clients already running (cap %d, ours would be #%d):\n%s' % (len(cl), MAX_CLIENTS, len(cl) + 1, '\n'.join(fmt_proc(p) for p in cl))]
    if cl:
        log('gpu_gates: %d other GPU client(s):\n%s' % (len(cl), '\n'.join(fmt_proc(p) for p in cl)))
    if wait:
        wait_gap(log)
    else:
        t, _ = last_launch()
        if t is not None and time.time() - t < MIN_GAP_S:
            return ['last engine launch only %.0f s ago (< %.0f s)' % (time.time() - t, MIN_GAP_S)]
    u = util_gate(wait, log)
    if u:
        return [u]
    # the util wait can take minutes: re-check the process gates before saying go
    procs = processes()
    if stuck_engines(procs):
        return ['engine stuck exiting (appeared during the util wait): machine-wide pause, notify the owner']
    cl = gpu_clients(procs)
    if len(cl) >= MAX_CLIENTS:
        return ['%d GPU clients running after the util wait (cap %d):\n%s' % (len(cl), MAX_CLIENTS, '\n'.join(fmt_proc(p) for p in cl))]
    if wait:
        wait_gap(log)
    return []


def main(argv):
    cmd = argv[1] if len(argv) > 1 else 'status'
    if cmd == 'check':
        why = gates(wait='--no-wait' not in argv, log=lambda s: print(s, flush=True))
        if why:
            print('GPU GATES REFUSED:\n' + '\n'.join('  ' + w for w in why), flush=True)
            return 3
        print('gpu_gates: go', flush=True)
        return 0
    if cmd == 'stamp':
        stamp(argv[argv.index('--label') + 1] if '--label' in argv else '')
        return 0
    if cmd == 'gap':
        wait_gap(lambda s: print(s, flush=True))
        return 0
    if cmd == 'status':
        procs = processes()
        cl = gpu_clients(procs)
        print('GPU clients (%d):%s' % (len(cl), ''.join('\n' + fmt_proc(p) for p in cl)))
        print('stuck engines: %d' % len(stuck_engines(procs)))
        print('util now: %s %%' % read_util())
        t, txt = last_launch()
        print('last launch: %s' % ('none recorded' if t is None else '%.0f s ago (%s)' % (time.time() - t, txt)))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))

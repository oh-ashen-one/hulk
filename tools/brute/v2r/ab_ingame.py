#!/usr/bin/env python3
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
"""In-game blind A/B of the 17 Brute clips (PLAN.md Phase 5): case generator, set runner, gate checker, blind packer.

  python3 tools/brute/v2r/ab_ingame.py list                      cases, clips covered, GPU time estimate
  python3 tools/brute/v2r/ab_ingame.py gen [--check]             (re)write tools/brute/cases/ab_<group>_<angle>.json
  python3 tools/brute/v2r/ab_ingame.py run --label old|new [--cases a,b] [--extra "-WHBruteNoClipTiming"] [--dry-run]
  python3 tools/brute/v2r/ab_ingame.py check <set_dir>           telemetry gates for every case of one set
  python3 tools/brute/v2r/ab_ingame.py pack --old DIR --new DIR --out DIR [--seed N] [--dry-run]

Read tools/brute/v2r/ab_ingame.md first. `run` calls tools/brute/capture.sh (GPU slot, capture class) one case at a time and never
in parallel; it refuses while ~/.cache/gpu-slot/STREAMING exists. `gen`, `list`, `check` and `pack --dry-run` never start an engine.
Cases are generated, not hand-edited: the camera-angle trigonometry lives here (see CAMERA below).
"""
import argparse
import datetime
import json
import math
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CASES_DIR = os.path.join(REPO, 'tools', 'brute', 'cases')
CAPTURE_SH = os.environ.get('AB_CAPTURE_SH', os.path.join(REPO, 'tools', 'brute', 'capture.sh'))
CAP_ROOT = os.path.expanduser(os.environ.get('AB_CAP_ROOT', '~/hulk-scratch/cap'))     # capture.sh writes <CAP_ROOT>/<case>/
SET_ROOT = os.path.expanduser(os.environ.get('AB_SET_ROOT', '~/hulk-scratch/ab-ingame'))
STREAM_FLAG = os.path.expanduser(os.environ.get('AB_STREAM_FLAG', '~/.cache/gpu-slot/STREAMING'))
CPP = os.path.join(REPO, 'unreal', 'WebHomage', 'Source', 'WebHomage', 'Brute', 'BruteCharacter.cpp')
RES = '960x540'               # the size the earlier -movie evidence (v2_loco, v3_combat, m3_wallrun) used
MAP = '/Game/Maps/Manhattan'  # every spawn below is a Manhattan coordinate taken from an existing case
MIN_FREE_GB = 8.0             # one movie capture writes ~0.5-1 GB of PNG frames before they are encoded and deleted

# ---------------------------------------------------------------------------------------------------------------- CAMERA
# Offsets are the camera's VIEW yaw relative to the character's heading, degrees clockwise seen from above (Unreal yaw: +X -> +Y).
# The camera sits behind its own view direction, so offset 0 = behind him (the game default), 180 = in FRONT of him, 90 = on his LEFT,
# 135 = front-left three-quarter. These are the same three viewpoints as the Blender harness (ab_common.CAMERAS: front, left,
# threequarter = 45 deg off front towards his left).
ANG3 = {'front': 180.0, 'left': 90.0, 'tq': 135.0}
# A wall climb faces the facade, so a camera in front of him would be inside the building: back / left / back-left instead.
ANGW = {'back': 0.0, 'left': 90.0, 'backleft': 45.0}
SPIN_S = 1.0   # the camera orbits to its offset during the first second with the game's own `look` rate key (deg/s, integrates exactly)


def spin(off):
    """Emulated camera yaw (works with today's schema): `look` rate for SPIN_S seconds while he stands still. The stop key sits 1 ms
    before the boundary so the 30 fps and the 60 fps step both integrate exactly off degrees (frame n samples the script at n*dt)."""
    ks = [{'t': 0.0, 'move': [0, 0]}]
    if off:
        ks[0]['look'] = [off / SPIN_S, 0]
        ks.append({'t': round(SPIN_S - 0.001, 3), 'look': [0, 0]})
    return ks


def mv(off, m):
    """Stick vector that walks him along his ORIGINAL heading D while the camera looks along D+off: WishDir = F*y + R*x with
    F = dir(V), R = (-sin V, cos V); dir(D) = F cos(D-V) + R sin(D-V), so (x, y) = m * (sin d, cos d) with d = D-V = -off."""
    d = math.radians(-off)
    return [round(m * math.sin(d), 6) + 0.0, round(m * math.cos(d), 6) + 0.0]


# ------------------------------------------------------------------------------------------------------------------ GROUPS
# kind 'emu'   : camera angle emulated with look + stick compensation; runs on today's build (a heading-following move, or no move).
# kind 'patch' : needs the proposed `spawn.camYawOff` (ab_ingame.md, Gaps): standing acts and carries turn him to the camera yaw,
#                so no look-rate trick can put the camera anywhere but behind him.
# Spawns are copied from existing cases: idle (249,150) yaw 180 = m12_look / look_close; loco + lunge (249,178) yaw -90 = v2_loco /
# m4_running_jump_slam; jump (249,150) down the same lane (landing zone y ~50 = m4's impact); combat (255.6,190.2) yaw 0 = v3_combat;
# uppercut (259,170) yaw 90 = m10_launcher; grab (244.6,183.2) yaw 180 = m2_grab_throw; wall (249,140) yaw 0 = m3_wallrun.
# Input timings keep the earlier cases' RELATIVE timings (run-up, hold lengths); press spacings are widened where a new clip could
# move a hit time (combo presses 0.75 s apart sit inside every Hit..End+0.45 s window).
G = [
    dict(id='idle', kind='emu', angles=ANG3, spawn=((249.0, 150.0, 0.0), 180, -4), quit=8.2, film=(2.0, 8.0), clips=['Idle'],
         beats=[(2.0, 'stands (Idle loop, game layers the menace posture on top)')],
         purpose='Stand 6 s.',
         expect=[], forbid=['act_', 'rescue', 'super_jump', 'hop', 'wall_'], travel=None, zmax=None,
         keys=lambda o: spin(o) + [{'t': 8.0, 'move': [0, 0]}]),
    dict(id='loco', kind='emu', angles=ANG3, spawn=((249.0, 178.0, 0.0), -90, -8), quit=14.6, film=(1.5, 14.5), clips=['Walk', 'Run'],
         beats=[(2.0, 'walk 4 s (7 m/s)'), (6.0, 'run 4 s (13 m/s)'), (10.0, 'sprint 3 s (27 m/s, Run clip faster, upper body leans in)'),
                (13.0, 'stop, settles back to Idle')],
         purpose='Walk 4 s, run 4 s, sprint 3 s, stop. (There is no separate sprint clip and no stop clip: StopLunge is the jump-charge plant, see lunge.)',
         expect=[], forbid=['act_', 'rescue', 'super_jump', 'hop', 'wall_'], travel=120.0, zmax=None,
         keys=lambda o: spin(o) + [{'t': 2.0, 'move': mv(o, 0.45)}, {'t': 6.0, 'move': mv(o, 1.0)},
                                   {'t': 10.0, 'sprint': 1, 'move': mv(o, 1.0)}, {'t': 13.0, 'sprint': 0, 'move': [0, 0]}]),
    dict(id='lunge', kind='emu', angles=ANG3, spawn=((249.0, 178.0, 0.0), -90, -10), quit=6.0, film=(1.5, 5.9), clips=['StopLunge', 'Jump'],
         beats=[(1.5, 'sprint'), (3.3, 'jump held while sprinting: plant and coil (StopLunge)'), (4.25, 'release: running super jump, Jump air segment')],
         purpose='Running super jump: sprint, then hold jump at full speed (the only way the game plays StopLunge), release, first second of flight.',
         expect=['charge_floor_crack', 'super_jump'], forbid=['act_', 'rescue', 'wall_'], travel=60.0, zmax=None,
         keys=lambda o: spin(o) + [{'t': 1.5, 'sprint': 1, 'move': mv(o, 1.0)}, {'t': 3.3, 'jump': 1}, {'t': 4.25, 'jump': 0},
                                   {'t': 4.3, 'sprint': 0}, {'t': 5.5, 'move': [0, 0]}]),
    dict(id='jump', kind='emu', angles=ANG3, spawn=((249.0, 150.0, 0.0), -90, -10), quit=9.1, film=(1.5, 9.0), clips=['Jump', 'Fall', 'Land'],
         beats=[(2.0, 'hold jump: charge crouch (Jump clip scrubbed by the charge)'), (3.0, 'release: full super jump (Jump air segment while rising)'),
                (4.6, 'past the apex: Fall loop (until touchdown ~6.6 s)'), (6.6, 'hard landing, crater (Land clip)')],
         purpose='Charge to full, super jump (40 m apex, 100 m range), Fall loop in the air, hard crater landing.',
         expect=['charge_floor_crack', 'super_jump', 'crater_landing'], forbid=['act_', 'rescue', 'wall_', 'grand_slam', 'air_dash'],
         travel=60.0, zmax=None,
         keys=lambda o: spin(o) + [{'t': 2.0, 'jump': 1}, {'t': 3.0, 'jump': 0}, {'t': 9.0, 'move': [0, 0]}]),
    dict(id='combat', kind='patch', angles=ANG3, spawn=((255.6, 190.2, 0.0), 0, -8), quit=9.1, film=(1.5, 9.0),
         clips=['PunchR', 'PunchL', 'Slap', 'Clap', 'Smash'],
         beats=[(2.0, 'punch (right fist)'), (2.75, 'punch (left fist)'), (3.5, 'slap'), (5.2, 'thunderclap'), (7.0, 'ground smash')],
         purpose='Punch, punch, slap; thunderclap; ground smash (standing, fighting stance).',
         expect=['act_punch', 'act_punch', 'act_slap', 'act_thunderclap', 'act_ground_smash'], forbid=['rescue', 'grab_nothing'],
         travel=None, zmax=None,
         keys=lambda o: [{'t': 0.0, 'move': [0, 0]},
                         {'t': 2.0, 'attack': 1}, {'t': 2.08, 'attack': 0}, {'t': 2.75, 'attack': 1}, {'t': 2.83, 'attack': 0},
                         {'t': 3.5, 'attack': 1}, {'t': 3.58, 'attack': 0}, {'t': 5.2, 'clap': 1}, {'t': 5.3, 'clap': 0},
                         {'t': 7.0, 'heavy': 1}, {'t': 7.15, 'heavy': 0}, {'t': 8.9, 'move': [0, 0]}]),
    dict(id='uppercut', kind='emu', angles=ANG3, spawn=((259.0, 170.0, 0.0), 90, -6), quit=6.5, film=(1.5, 6.4), clips=['Uppercut'],
         beats=[(2.0, 'sprint'), (3.05, 'attack while sprinting: launcher uppercut, he pops up with it'), (3.7, 'sprint released, lands')],
         purpose='Sprint uppercut (launcher). Kept out of the standing combat case: it needs a 1 s run-up and the combat spot has no lane.',
         expect=['act_launcher_uppercut', 'launcher_hit'], forbid=['rescue'], travel=20.0, zmax=None,
         keys=lambda o: spin(o) + [{'t': 2.0, 'sprint': 1, 'move': mv(o, 1.0)}, {'t': 3.05, 'attack': 1}, {'t': 3.15, 'attack': 0},
                                   {'t': 3.7, 'sprint': 0, 'move': [0, 0]}]),
    dict(id='grab', kind='patch', angles=ANG3, spawn=((244.6, 183.2, 0.0), 180, -10), quit=5.2, film=(0.8, 5.0), clips=['Lift', 'Throw'],
         beats=[(1.0, 'grab: lift the car overhead (Lift, Grab segment)'), (2.0, 'carry ~2 s (Lift held pose)'), (4.2, 'throw (Throw clip); film ends 0.4 s after release')],
         purpose='Grab the parked car, carry it overhead about 2 s, throw it.',
         expect=['act_grab', 'act_throw', 'throw'], forbid=['grab_nothing', 'rescue'], travel=None, zmax=None,
         keys=lambda o: [{'t': 0.0, 'move': [0, 0]}, {'t': 1.0, 'grab': 1}, {'t': 1.15, 'grab': 0}, {'t': 4.2, 'grab': 1}, {'t': 4.35, 'grab': 0},
                         {'t': 5.1, 'move': [0, 0]}]),
    dict(id='wall', kind='emu', angles=ANGW, spawn=((249.0, 140.0, 0.0), 0, -8), quit=8.6, film=(1.5, 8.5), clips=['WallAttach', 'WallClimb'],
         beats=[(2.0, 'sprint into the facade'), (3.0, 'attach slam, climb (23.8 m face)'), (4.3, 'top out, catch the next face'),
                (4.7, 'climb to the roof (73 m), top out ~7.0 s')],
         purpose='Sprint into a facade, wall attach and climb (about 3.7 s attached in total: 1.3 s on the first face, 2.4 s on the second).',
         expect=['wall_run_start', 'wall_punch', 'wall_top_out', 'wall_catch', 'wall_punch', 'wall_top_out'], forbid=['rescue', 'wall_release', 'wall_kick'],
         travel=None, zmax=60.0,
         keys=lambda o: spin(o) + [{'t': 2.0, 'sprint': 1, 'move': mv(o, 1.0)}, {'t': 7.5, 'sprint': 0, 'move': [0, 0]}]),
]
SEC_PER_CASE = 30.0     # engine start + map load + shutdown (hold_s of the earlier movie captures: 56 s at 6 s of game time ... 107 s at 11 s)
SEC_PER_GAME_S = 6.5    # wall seconds per game second at 960x540 -movie (fit of those captures)


def js(o):
    return json.dumps(o)


def cases():
    out = []
    for g in G:
        for an, off in g['angles'].items():
            out.append((g, an, off))
    return out


def case_name(g, an):
    return 'ab_%s_%s' % (g['id'], an)


def build(g, an, off):
    """(file text, parsed dict) of one case."""
    sp = {'pos': list(g['spawn'][0]), 'yaw': g['spawn'][1], 'camPitch': g['spawn'][2], 'camDist': 7.5}
    if g['kind'] == 'patch':
        sp['camYawOff'] = off
    ab = {'group': g['id'], 'angle': an, 'cam_offset_deg': off,
          'mode': 'needs spawn.camYawOff (C++ patch, ab_ingame.md Gaps)' if g['kind'] == 'patch' else 'emulated: look-rate orbit + stick compensation, no C++ change',
          'clips': g['clips'], 'purpose': g['purpose'], 'beats_s': [[t, s] for t, s in g['beats']],
          'film_s': list(g['film']), 'quit_s': g['quit'], 'expect_events': g['expect'], 'forbid_events': g['forbid'],
          'expect_travel_min_m': g['travel'], 'expect_zmax_min_m': g['zmax']}
    keys = g['keys'](off)
    name = case_name(g, an)
    L = ['{', ' "name": %s,' % js(name), ' "ab": %s,' % json.dumps(ab, indent=1).replace('\n', '\n '), ' "spawn": %s,' % js(sp), ' "keys": [']
    L += ['  %s%s' % (js(k), ',' if i < len(keys) - 1 else '') for i, k in enumerate(keys)]
    L += [' ]', '}']
    text = '\n'.join(L) + '\n'
    return text, json.loads(text)


def est_seconds(quit_s):
    return SEC_PER_CASE + SEC_PER_GAME_S * quit_s


# ------------------------------------------------------------------------------------------------------------------ list/gen
def cmd_list(a):
    tot_sim = tot_wall = 0.0
    print('%-18s %-6s %-8s %6s %6s  %s' % ('case', 'kind', 'cam_off', 'sim_s', 'est_s', 'clips'))
    for g, an, off in cases():
        w = est_seconds(g['quit'])
        tot_sim += g['quit']
        tot_wall += w
        print('%-18s %-6s %8.0f %6.1f %6.0f  %s' % (case_name(g, an), g['kind'], off, g['quit'], w, ', '.join(g['clips'])))
    n = len(cases())
    allclips = sorted({c for g in G for c in g['clips']})
    print('\n%d cases per set, %.0f game seconds, estimated GPU wall time per set %.0f min (both sets %.0f min)' % (n, tot_sim, tot_wall / 60, 2 * tot_wall / 60))
    print('clips covered (%d): %s' % (len(allclips), ', '.join(allclips)))


def cmd_gen(a):
    bad = 0
    for g, an, off in cases():
        text, _ = build(g, an, off)
        path = os.path.join(CASES_DIR, case_name(g, an) + '.json')
        if a.check:
            ok = os.path.exists(path) and open(path).read() == text
            bad += 0 if ok else 1
            print('%s %s' % ('same   ' if ok else 'DIFFERS', path))
        else:
            open(path, 'w').write(text)
            print('wrote', path)
    return 1 if bad else 0


# ----------------------------------------------------------------------------------------------------------------- run
def now_et():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo('America/New_York'))
    except Exception:  # noqa: BLE001
        return datetime.datetime.now()


def unreal_count():
    out = subprocess.run(['ps', '-axo', 'command'], capture_output=True, text=True).stdout.splitlines()
    return sum(1 for ln in out if ln.split() and 'UnrealEditor' in os.path.basename(ln.split()[0]))


def preflight(a):
    """Reasons not to launch a capture right now (empty list = go). The STREAMING flag is absolute; the 11:00-13:00 ET window can be overridden."""
    why = []
    if os.path.exists(STREAM_FLAG):
        why.append('%s exists (owner is streaming, mode in the file): no captures' % STREAM_FLAG)
    t = now_et()
    if 11 <= t.hour < 13 and not getattr(a, 'ignore_window', False):
        why.append('now %s is inside the owner stream window 11:00-13:00 ET (override only with --ignore-window if the owner said so)' % t.strftime('%H:%M %Z'))
    n = unreal_count()
    if n >= 2:
        why.append('%d UnrealEditor processes already running (global cap two; ours would be the third)' % n)
    free = shutil.disk_usage(os.path.expanduser('~')).free / 1e9
    if free < MIN_FREE_GB:
        why.append('only %.1f GB free (< %.0f GB for one movie capture)' % (free, MIN_FREE_GB))
    return why


def select(names):
    allc = {case_name(g, an): (g, an, off) for g, an, off in cases()}
    if not names:
        return list(allc.items())
    out = []
    for n in names.split(','):
        n = n.strip()
        n = n if n.startswith('ab_') else 'ab_' + n
        if n not in allc:
            sys.exit('unknown case %s (try: list)' % n)
        out.append((n, allc[n]))
    return out


def cmd_run(a):
    sel = select(a.cases)
    patched = 'camYawOff' in open(CPP).read()
    extra = shlex.split(a.extra) if a.extra else []
    root = os.path.join(SET_ROOT, a.label)
    why = preflight(a)
    if why and not a.dry_run:
        print('REFUSED:\n  ' + '\n  '.join(why))
        return 3
    if why:
        print('(dry run, these would refuse a real run)\n  ' + '\n  '.join(why))
    skipped = []
    os.makedirs(root, exist_ok=True) if not a.dry_run else None
    for name, (g, an, off) in sel:
        if g['kind'] == 'patch' and not patched and not a.force_unpatched:
            skipped.append(name)
            continue
        dst = os.path.join(root, name)
        if os.path.exists(dst) and not a.redo:
            print('SKIP %s: %s exists (--redo to capture again)' % (name, dst))
            continue
        cmd = [CAPTURE_SH, name, '-map', MAP, '-movie', '-res', RES, '-quit', str(g['quit'])] + (['--'] + extra if extra else [])
        print('RUN %s  (est %.0f s)\n    %s' % (name, est_seconds(g['quit']), ' '.join(shlex.quote(c) for c in cmd)))
        if a.dry_run:
            continue
        again = preflight(a)
        if again:
            print('STOP before %s:\n  %s\n  resume later with --cases (finished cases are skipped)' % (name, '\n  '.join(again)))
            return 3
        t0 = datetime.datetime.now()
        rc = subprocess.run(cmd).returncode
        src = os.path.join(CAP_ROOT, name)
        mp4 = os.path.join(src, name + '.mp4')
        if not os.path.exists(mp4):
            print('FAIL %s: rc=%d and no %s (frames kept in %s)' % (name, rc, mp4, src))
            return 4
        shutil.rmtree(os.path.join(src, name + '_frames'), ignore_errors=True)   # the mp4 holds them; the PNGs are ~0.5-1 GB
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.move(src, dst)
        json.dump({'label': a.label, 'extra': extra, 'rc': rc, 'started': t0.isoformat(timespec='seconds'),
                   'wall_s': round((datetime.datetime.now() - t0).total_seconds(), 1)}, open(os.path.join(dst, 'run.json'), 'w'))
        print('DONE %s rc=%d -> %s' % (name, rc, dst))
    if skipped:
        print('\nSKIPPED (need the camYawOff patch, not in %s): %s' % (os.path.relpath(CPP, REPO), ', '.join(skipped)))
        return 2
    return 0


# --------------------------------------------------------------------------------------------------------------- check
EV = re.compile(r'WH_BRUTE t=([0-9.]+) (\S+)')


def events(log):
    out = []
    if os.path.exists(log):
        for ln in open(log, errors='replace'):
            m = EV.search(ln)
            if m:
                out.append((float(m.group(1)), m.group(2)))
    return out


def csv_stats(path):
    if not os.path.exists(path):
        return None
    pts = []
    for r in open(path).read().strip().split('\n')[1:]:
        c = r.split(',')
        if len(c) > 3:
            pts.append((float(c[1]), float(c[2]), float(c[3])))
    if not pts:
        return None
    return {'travel': math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]), 'zmax': max(p[2] for p in pts), 'rows': len(pts)}


def subseq(seq, want):
    it = iter(seq)
    return all(any(w == s for s in it) for w in want)


def load_case(name):
    return json.load(open(os.path.join(CASES_DIR, name + '.json')))


def check_case(d, name):
    """Problems for one captured case directory (empty = pass)."""
    ab = load_case(name)['ab']
    bad = []
    log = os.path.join(d, name + '.log')
    if not os.path.exists(log):
        return ['no %s.log' % name]
    text = open(log, errors='replace').read()
    if 'WH_QUIT' not in text:
        bad.append('run did not reach WH_QUIT')
    if re.search(r'Fatal error|Assertion failed|Unhandled Exception', text):
        bad.append('crash / assertion in the log')
    toks = [t for _, t in events(log)]
    if not subseq(toks, ab['expect_events']):
        bad.append('events %s not found in order (got %s)' % (ab['expect_events'], [t for t in toks if not t.startswith(('car_bounced', 'sprint_knock', 'blast_cars'))][:24]))
    for f in ab['forbid_events']:
        hit = [t for t in toks if t.startswith(f)]
        if hit:
            bad.append('forbidden event %s (%s x%d)' % (f, hit[0], len(hit)))
    st = csv_stats(os.path.join(d, name + '_brute.csv'))
    if st is None:
        bad.append('no telemetry csv')
    else:
        if ab['expect_travel_min_m'] and st['travel'] < ab['expect_travel_min_m']:
            bad.append('travelled %.0f m < %.0f m (stuck / pinned?)' % (st['travel'], ab['expect_travel_min_m']))
        if ab['expect_zmax_min_m'] and st['zmax'] < ab['expect_zmax_min_m']:
            bad.append('max z %.0f m < %.0f m' % (st['zmax'], ab['expect_zmax_min_m']))
    if 'camYawOff' in ab['mode']:
        m = re.search(r'camYawOff\s+(-?[0-9.]+)', text)
        if not m:
            bad.append('log has no "camYawOff <deg>" (build without the patch: all three angles would be the rear view)')
        elif abs(float(m.group(1)) - ab['cam_offset_deg']) > 0.5:
            bad.append('camYawOff in the log is %s, case says %s' % (m.group(1), ab['cam_offset_deg']))
    cap = os.path.join(d, 'capture.txt')
    if os.path.exists(cap):
        m = re.search(r'movie frames: (\d+)', open(cap, errors='replace').read())
        if m and int(m.group(1)) < int(ab['quit_s'] * 60) - 3:
            bad.append('only %s movie frames for quit %.1f s' % (m.group(1), ab['quit_s']))
    if not os.path.exists(os.path.join(d, name + '.mp4')):
        bad.append('no mp4')
    return bad


def cmd_check(a):
    rc = 0
    for g, an, off in cases():
        name = case_name(g, an)
        d = os.path.join(a.set_dir, name)
        if not os.path.isdir(d):
            print('MISSING %s' % name)
            rc = 1
            continue
        bad = check_case(d, name)
        print('%s %s%s' % ('FAIL   ' if bad else 'ok     ', name, ''.join('\n          - ' + b for b in bad)))
        rc = rc or (1 if bad else 0)
    return rc


# ---------------------------------------------------------------------------------------------------------------- pack
def trim(src, dst, t0, t1):
    cmd = ['ffmpeg', '-loglevel', 'error', '-y', '-ss', '%.3f' % t0, '-to', '%.3f' % t1, '-i', src, '-an', '-map_metadata', '-1',
           '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-flags:v', '+bitexact', '-fflags', '+bitexact', '-movflags', '+faststart', dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit('ffmpeg failed for %s: %s' % (src, r.stderr.strip()))


QUESTIONS = [
    ('Weight', 'Does he read as a 2.6 m, multi-ton brute? Mass settles after each beat, no floating, no twitching, hips and shoulders lead.'),
    ('Readability', 'Can you tell the anticipation, the contact and the recovery? Is the key pose clear in silhouette from the side camera?'),
    ('Contact', 'When the hit, clap, smash, landing or throw effect fires (dust ring, crater, car leaving), is the fist, palm, foot or hand actually there?'),
    ('Foot contact', 'Planted feet stay put (no skating, swimming, sinking, hovering); stepping feet lift, travel and plant believably.'),
    ('Arm arc and mesh', 'Smooth weighty arcs with lead-lag, no wobble, stall or flick; no pinched elbows or shoulders, no stretched mesh.'),
    ('Transitions', 'Entering and leaving the move (from idle, run, air): any pop, snap or foot jump at the blend?'),
    ('Menace', 'Threatening and in character, or passive, tired, nervous, cartoony?'),
]


def brief(pairs, t_of):
    L = ['# Blind A/B: the Brute in the real game\n',
         'Every folder holds two takes of the same scripted run, A and B. You are not told which is which, what produced either, or how. Judge only what you see. '
         'Do not look for logs, build names or anything outside this folder.\n',
         'Same map, same start, same scripted inputs, same lighting and traffic, same camera rig (960 x 540, 60 fps, fixed time step). '
         'The takes differ only in the Brute\'s animation clips (and therefore possibly in when a contact frame lands, by a few frames).\n',
         'Each move is filmed from three fixed camera angles (folders `<group>_front`, `_left`, `_tq` = front-left three-quarter; the wall climb uses `_back`, `_left`, `_backleft` because the front of a wall climb is inside the building). '
         'Watch all three angles before you score a move. A move is judged as a whole: one verdict per clip, not per angle.\n',
         '## Moves\n', '| folder group | clips to judge | what happens (seconds from the start of each film) |', '| --- | --- | --- |']
    for gid, rows in pairs.items():
        g = next(x for x in G if x['id'] == gid)
        beats = '; '.join('%.1f s %s' % (t - g['film'][0], s) for t, s in g['beats'])
        L.append('| `%s_*` | %s | %s |' % (gid, ', '.join(g['clips']), beats))
    L += ['\n(Beat times are the moments the script presses the input; the animation follows within a fraction of a second.)\n', '## Questions (answer for A and B, 1 = broken, 5 = shippable in a AAA brawler)\n']
    L += ['%d. **%s.** %s' % (i, t, q) for i, (t, q) in enumerate(QUESTIONS, 1)]
    L += ['\n## Reply format (one block per clip)\n',
          '```\nCLIP      <name>\nSCORES    A: weight n  readability n  contact n  foot n  arm n  transitions n  menace n | B: ...\nDEFECTS   A: ...  B: ...   (second and camera angle)\nWINNER    A | B | tie    (not clearly better = tie)\nWHY       two sentences\n```\n']
    return '\n'.join(L)


def cmd_pack(a):
    old, new, out = [os.path.abspath(os.path.expanduser(p)) for p in (a.old, a.new, a.out)]
    names = [case_name(g, an) for g, an, off in cases() if os.path.isdir(os.path.join(old, case_name(g, an))) and os.path.isdir(os.path.join(new, case_name(g, an)))]
    only_one = [case_name(g, an) for g, an, off in cases() if case_name(g, an) not in names]
    if only_one:
        print('NOT PACKED (missing in old or new): %s' % ', '.join(only_one))
    if not names:
        sys.exit('no case exists in both sets')
    problems = {}
    for lab, d in (('old', old), ('new', new)):
        for n in names:
            b = check_case(os.path.join(d, n), n)
            if b:
                problems.setdefault(n, {})[lab] = b
    if problems and not a.force:
        for n, v in problems.items():
            print('GATE FAIL %s: %s' % (n, json.dumps(v)))
        sys.exit('refusing to pack failed cases (fix and re-capture, or --force)')
    seed = a.seed if a.seed is not None else zlib.crc32(b'ab_ingame')
    rng = random.Random(seed)
    first = ['old'] * (len(names) // 2) + ['new'] * (len(names) - len(names) // 2)   # balanced: half the A takes are old
    rng.shuffle(first)
    crit, direc = os.path.join(out, 'critic'), os.path.join(out, '_director')
    key = {'seed': seed, 'note': 'the critic is NOT given this file or this folder', 'old_dir': old, 'new_dir': new, 'pairs': {}}
    pairs = {}
    for n, f in zip(names, first):
        g = next(x for x in G if case_name(x, n.split('_', 2)[2]) == n)
        cid = n[3:]
        roles = {'A': f, 'B': 'new' if f == 'old' else 'old'}
        key['pairs'][cid] = roles
        pairs.setdefault(g['id'], []).append(cid)
        t0, t1 = g['film']
        print('%s: A=%s B=%s  trim %.1f-%.1f s' % (cid, roles['A'], roles['B'], t0, t1))
        if not a.dry_run:
            os.makedirs(os.path.join(crit, cid), exist_ok=True)
            for lab in ('A', 'B'):
                src = os.path.join(old if roles[lab] == 'old' else new, n, n + '.mp4')
                trim(src, os.path.join(crit, cid, lab + '.mp4'), t0, t1)
    # director-only: did both builds run the same script? (event name sequences; times legitimately differ with clip timing)
    rep = {}
    for n in names:
        so = [t for _, t in events(os.path.join(old, n, n + '.log')) if not t.startswith(('car_bounced', 'sprint_knock', 'blast_cars'))]
        sn = [t for _, t in events(os.path.join(new, n, n + '.log')) if not t.startswith(('car_bounced', 'sprint_knock', 'blast_cars'))]
        rep[n[3:]] = {'same_event_sequence': so == sn, 'old_events': len(so), 'new_events': len(sn)}
    if not a.dry_run:
        os.makedirs(direc, exist_ok=True)
        json.dump(key, open(os.path.join(direc, 'KEY.json'), 'w'), indent=1)
        json.dump({'gate_problems_forced': problems, 'event_sequences': rep}, open(os.path.join(direc, 'report.json'), 'w'), indent=1)
        open(os.path.join(crit, 'brief.md'), 'w').write(brief(pairs, None))
        print('packed -> %s  (give the critic ONLY %s)' % (out, crit))
    diff = [k for k, v in rep.items() if not v['same_event_sequence']]
    if diff:
        print('NOTE event sequence differs between old and new for: %s (see _director/report.json; usually a hit that missed a car)' % ', '.join(diff))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list').set_defaults(f=cmd_list)
    p = sub.add_parser('gen')
    p.add_argument('--check', action='store_true', help='compare the files on disk with the generator, write nothing')
    p.set_defaults(f=cmd_gen)
    p = sub.add_parser('run')
    p.add_argument('--label', required=True, choices=['old', 'new'])
    p.add_argument('--cases', default='', help='comma list (ab_ prefix optional); default all')
    p.add_argument('--extra', default='', help='extra UE args passed after -- to capture.sh, e.g. "-WHBruteNoClipTiming"')
    p.add_argument('--redo', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--ignore-window', action='store_true')
    p.add_argument('--force-unpatched', action='store_true', help='run the camYawOff cases anyway (all three angles = rear view)')
    p.set_defaults(f=cmd_run)
    p = sub.add_parser('check')
    p.add_argument('set_dir')
    p.set_defaults(f=cmd_check)
    p = sub.add_parser('pack')
    p.add_argument('--old', required=True)
    p.add_argument('--new', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--seed', type=int, default=None)
    p.add_argument('--force', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.set_defaults(f=cmd_pack)
    a = ap.parse_args()
    sys.exit(a.f(a) or 0)


if __name__ == '__main__':
    main()

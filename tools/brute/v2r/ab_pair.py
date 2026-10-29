#!/usr/bin/env python3
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
"""Blind A/B pair for one Brute clip: old vs new, random labels, identical renders, numbers, a critic brief that names no source.

  python3 tools/brute/v2r/ab_pair.py --clip Idle \\
      --old ~/hulk-scratch/brute_v5/brute.glb:Idle --new Local/video2rig/work-tools/motion_refined/Brute_v2r_idle.glb \\
      --out Local/video2rig/ab/test-idle

Subjects are '<file.glb>[:<Action>]' on the shipped Brute rig (see ab_common.py). Everything the critic may see sits in
<out>/<clip>/ : A_*.mp4, B_*.mp4 (front, left, threequarter), measure.json (labels only), critic_brief.md.
Everything only the director may see sits in <out>/<clip>/KEY.json and <out>/<clip>/_director/ (logs, timings, which label is old).
Labels come from random.Random(seed) (default seed = crc32 of the clip name, so a re-run keeps the mapping); --seed N overrides.
Runs ONE Blender process at a time (render A, render B, measure both) and waits while the machine is at its Blender cap
(4, or 2 when an UnrealEditor runs). Needs system python 3 and the Blender app; no network, no GPU slot beyond Blender itself.
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
MOVESET = os.path.join(REPO, 'docs', 'brute', 'MOVESET.md')
CAMS = ['front', 'left', 'threequarter']

# clip -> (regexes over MOVESET.md lines to quote verbatim, neutral fallback text when MOVESET has no row for it)
PURPOSE = {
    'Idle': ([], 'The standing loop he returns to between everything; the game layers a hunched, chest-forward posture on top. He must look huge, heavy and patient, never tired or passive.'),
    'Walk': ([r'Walk / run / sprint'], 'The 7 m/s walk loop.'),
    'Run': ([r'Walk / run / sprint'], 'The 13 m/s run loop (sprint is 27 m/s).'),
    'StopLunge': ([r'Walk / run / sprint'], 'The braking plant-and-lunge when a run is released.'),
    'Jump': ([r'Super jump', r'Hop'], 'The charge crouch and launch of the hop / super jump (the airborne apex is held by the game).'),
    'Land': ([r'Crater landing'], 'The heavy landing: the game plays it from 0.35 s.'),
    'Fall': ([r'Grand slam dive', r'Air dash'], 'The braced airborne hold.'),
    'WallAttach': ([r'Wall run', r'Wall kick'], 'Slamming onto a facade before the wall run.'),
    'WallClimb': ([r'Wall run'], 'The wall-run loop up a facade at 18 m/s.'),
    'PunchL': ([r'Punch, punch, SLAP', r'Punch / slap'], 'First hit of the punch, punch, slap combo (left fist).'),
    'PunchR': ([r'Punch, punch, SLAP', r'Punch / slap'], 'Second hit of the punch, punch, slap combo (right fist).'),
    'Slap': ([r'Punch, punch, SLAP', r'Punch / slap'], 'The finishing slap of the combo.'),
    'Clap': ([r'Thunderclap'], 'The thunderclap: both palms meet, a 32 m forward cone leaves.'),
    'Smash': ([r'Ground grand slam'], 'The overhead double-fist ground smash (crater r 13 m in front).'),
    'Uppercut': ([r'Launcher uppercut'], 'The launcher: cars go straight up, he pops up with them.'),
    'Lift': ([r'Grab a car'], 'Grabbing a car and heaving it overhead.'),
    'Throw': ([r'Grab a car', r'^\| Throw'], 'Hurling the car where the camera looks.'),
}


def procs():
    out = subprocess.run(['ps', '-axo', 'command'], capture_output=True, text=True).stdout.splitlines()
    first = [ln.split()[0] for ln in out if ln.split()]
    return (sum(1 for t in first if t.endswith('/MacOS/Blender')), sum(1 for t in first if 'UnrealEditor' in os.path.basename(t)))


def wait_for_slot(max_wait):
    t0 = time.time()
    while True:
        nb, nu = procs()
        cap = 2 if nu else 4
        if nb + 1 <= cap:
            return nb, nu, cap
        if time.time() - t0 > max_wait:
            sys.exit('ab_pair: %d Blender and %d UnrealEditor processes running (cap %d); waited %d s, not launching' % (nb, nu, cap, max_wait))
        time.sleep(15)


def blender(script, args, log, wait):
    nb, nu, cap = wait_for_slot(wait)
    cmd = [BLENDER, '--background', '--factory-startup', '-P', os.path.join(HERE, script), '--'] + args
    t0 = time.time()
    with open(log, 'w') as f:
        rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
    return rc, time.time() - t0


def norm_spec(sp):
    path, sep, act = sp.partition('.glb:')
    return os.path.abspath(os.path.expanduser(path + '.glb')) + ':' + act if sep else os.path.abspath(os.path.expanduser(sp))


def purpose(clip):
    pats, fb = PURPOSE.get(clip, ([], 'No purpose line recorded for this clip.'))
    rows = []
    if os.path.exists(MOVESET):
        lines = open(MOVESET).read().splitlines()
        for p in pats:
            for ln in lines:
                if re.search(p, ln) and ln not in rows:
                    rows.append(ln)
    return fb, rows


QUESTIONS = [
    ('Weight', 'Does he read as a 2.6 m, multi-ton brute? Look at how the mass settles after each beat: a heavy body leads with the hips and shoulders, takes weight slowly onto a foot, and has no floating or twitching.'),
    ('Readability of the move', 'Watch one camera with the sound of the purpose line in mind: can you tell what he is doing, and which parts are the anticipation, the main action and the recovery? Is the key pose clear in silhouette from the side camera?'),
    ('Loop seam', 'Loops only (the film plays the clip twice, the seam is at the midpoint). Is there a pop, a hold, a jump of the head, hand or hips, or a change of rhythm where it wraps? For one-shots: does it start and end in the stance without a snap?'),
    ('Foot contact', 'Look at the shadow under each foot in the front and left cameras. Do planted feet stay put (no skating, no swimming, no sinking into the floor, no hovering)? Does a stepping foot lift, travel and plant believably?'),
    ('Arm arc', 'Follow each hand. Is its path a smooth, weighty arc with natural lead-lag from shoulder to elbow to wrist and fingers, or does it wobble, stall, flick or pass through the body? Check the elbows and the shoulder bulge for mesh pinching.'),
    ('Menace', 'Does the clip read as threatening and in character (hunched, patient, dangerous), or passive, tired, nervous or cartoony?'),
]


def brief(clip, loop, labels, files, out_dir):
    fb, rows = purpose(clip)
    L = []
    L.append('# Blind A/B: %s\n' % clip)
    L.append('Two takes of the same Brute move, labelled A and B. You are not told which is which, which tool made either, or how they were made; judge only what you see and measure. Do not open `KEY.json` or the `_director/` folder.\n')
    L.append('## Files\n')
    L.append('| take | front | left side | three-quarter |\n| --- | --- | --- | --- |')
    for lab in labels:
        L.append('| %s | %s | %s | %s |' % (lab, *files[lab]))
    L.append('\n`measure.json`: numbers for both takes, keyed by label (definitions below). Read it first, then watch, then score.\n')
    L.append('Every film: same character, same mesh and rig, same three fixed cameras, same lights, 24 fps, 854 x 480; the takes differ only in the animation. %s Root motion is dropped and the lowest foot is put back on the floor every frame, exactly as the game does for ground clips, so the feet you see are the feet the player would see.\n' % (
        'This is a loop, so each film plays the clip twice end to end (the wrap is at the midpoint).' if loop else 'This is a one-shot, so each film plays it once.'))
    L.append('## What the clip is for\n')
    L.append(fb + '\n')
    for ln in rows:
        L.append('> ' + ln)
    if rows:
        L.append('\n(rows quoted from `docs/brute/MOVESET.md`)\n')
    L.append('## Numbers (`measure.json`)\n')
    L.append('- `seam` (loops): how far the mesh jumps from the last frame to the first, as a multiple of a normal frame step. About 1 is a clean wrap; 0 means the last frame equals the first (a one-frame hold); above 2 is a visible pop. `n/a` for one-shots.')
    L.append('- `foot_drift_px`: the largest horizontal movement, in pixels of the film, of a planted foot\'s contact patch while it is on the floor (worst of both feet and the three cameras). Planted feet should read near 0; a gait slides backwards by design (the json has `planted_speed_m_s`).')
    L.append('- `secondary`: head and finger articulation (in their parent frames) relative to pelvis motion. Compare A with B: near 0 means a frozen head and hands, much higher than the other take means flicking.')
    L.append('- The json also has the per-run foot numbers, the worst bones at the seam, and how deep or high each foot sits against the floor.\n')
    L.append('## Questions (answer for A and B, score 1 = broken to 5 = shippable in a AAA brawler)\n')
    for i, (t, q) in enumerate(QUESTIONS, 1):
        L.append('%d. **%s.** %s' % (i, t, q))
    L.append('\n## Reply format\n')
    L.append('```\nNUMBERS   one line on what measure.json says for A and B\nSCORES    A: weight n  readability n  seam n  foot n  arm n  menace n   | B: weight n  readability n  seam n  foot n  arm n  menace n\nDEFECTS   A: ...   B: ...   (time in seconds and camera for each)\nWINNER    A | B | tie     (a take that is not clearly better is a tie)\nWHY       two sentences\n```\n')
    open(os.path.join(out_dir, 'critic_brief.md'), 'w').write('\n'.join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--clip', required=True)
    ap.add_argument('--old', required=True, help='<file.glb>[:<Action>] of the shipped / old take')
    ap.add_argument('--new', required=True, help='<file.glb>[:<Action>] of the new take')
    ap.add_argument('--out', required=True)
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--loop', dest='loop', action='store_true', default=None)
    ap.add_argument('--no-loop', dest='loop', action='store_false')
    ap.add_argument('--root', choices=['game', 'raw'], default='game')
    ap.add_argument('--samples', type=int, default=10)
    ap.add_argument('--cams', default=','.join(CAMS))
    ap.add_argument('--max-wait', type=int, default=900, help='seconds to wait for a free Blender slot')
    ap.add_argument('--max-frames', type=int, default=0, help='debug: stop each film after N frames')
    ap.add_argument('--skip-render', action='store_true', help='re-measure and rewrite the brief only')
    a = ap.parse_args()

    seed = a.seed if a.seed is not None else zlib.crc32(a.clip.encode())
    rng = random.Random(seed)
    roles = ['old', 'new']
    rng.shuffle(roles)
    labels = ['A', 'B']
    mapping = dict(zip(labels, roles))
    spec = {'old': norm_spec(a.old), 'new': norm_spec(a.new)}
    clip_dir = os.path.join(os.path.abspath(a.out), a.clip)
    dd = os.path.join(clip_dir, '_director')
    os.makedirs(dd, exist_ok=True)
    key = dict(clip=a.clip, seed=seed, A=dict(role=mapping['A'], source=spec[mapping['A']]), B=dict(role=mapping['B'], source=spec[mapping['B']]),
               note='the critic is NOT given this file')
    json.dump(key, open(os.path.join(clip_dir, 'KEY.json'), 'w'), indent=1)

    flags = (['--loop'] if a.loop is True else ['--no-loop'] if a.loop is False else [])
    timings = {}
    if not a.skip_render:
        for lab in labels:
            args = ['--subject', spec[mapping[lab]], '--label', lab, '--out', clip_dir, '--clip', a.clip, '--root', a.root,
                    '--samples', str(a.samples), '--cams', a.cams] + flags + (['--max-frames', str(a.max_frames)] if a.max_frames else [])
            rc, dt = blender('ab_render.py', args, os.path.join(dd, 'render_%s.log' % lab), a.max_wait)
            timings['render_' + lab] = round(dt, 1)
            print('AB_PAIR render %s %.1f s (rc %d)' % (lab, dt, rc), flush=True)
            if rc != 0:
                sys.exit('ab_pair: render %s failed, see %s' % (lab, os.path.join(dd, 'render_%s.log' % lab)))
    args = ['--clip', a.clip, '--out', clip_dir, '--root', a.root] + flags
    for lab in labels:
        args += ['--subject', '%s=%s' % (lab, spec[mapping[lab]])]
    mlog = os.path.join(dd, 'measure.log')
    rc, dt = blender('ab_measure.py', args, mlog, a.max_wait)
    timings['measure_both'] = round(dt, 1)
    print('AB_PAIR measure %.1f s (rc %d)' % (dt, rc), flush=True)
    if rc != 0:
        sys.exit('ab_pair: measure failed, see ' + mlog)
    for ln in open(mlog):
        if ln.startswith('AB_MEASURE'):
            print(ln.rstrip())
    m = json.load(open(os.path.join(clip_dir, 'measure.json')))
    files = {lab: ['`%s_%s.mp4`' % (lab, c) for c in CAMS] for lab in labels}
    brief(a.clip, bool(m['loop']), labels, files, clip_dir)
    json.dump(dict(timings_s=timings, seed=seed), open(os.path.join(dd, 'timings.json'), 'w'), indent=1)
    print('AB_PAIR done %s -> %s ; KEY %s' % (a.clip, clip_dir, json.dumps({k: key[k]['role'] for k in labels})))


if __name__ == '__main__':
    main()

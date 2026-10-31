#!/usr/bin/env python3
"""Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.

Round 4 dense refit helper: `reader.fit --tag=-dense` writes fit-dense.npz but not the outline/warning report that `video2rig run`
writes next to a standard fit. This builds it the same way (video2rig.report.report on the fit's creature), CPU only.

    <fork>/.venv/bin/python tools/brute/v2r/dense_report.py <project> <clip> [--tag=-dense] [--fork-dir ~/video2rig-lockfix]
-> <project>/work/<clip>/report<tag>.json ; prints one line: OUTLINE <front>/<side> WARN <n> and each warning.
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('clip')
    ap.add_argument('--tag', default='-dense')
    ap.add_argument('--fork-dir', default=str(Path.home() / 'video2rig-lockfix'))
    a = ap.parse_args()
    sys.path.insert(0, a.fork_dir)
    from video2rig.common import Project
    from video2rig.creature import Creature
    from video2rig.__main__ import review_creature
    from video2rig.report import report
    project = Project(a.project)
    cfg = project.clip_cfg(a.clip)
    cfg.setdefault('solve', {})
    work = project.work(a.clip)
    fit = work / f'fit{a.tag}.npz'
    log = lambda s: print(s, flush=True)
    creature = review_creature(project, cfg, fit, work, a.tag, log)
    P = creature.load_params(fit)
    rep = report(creature, a.clip, P, work / f'report{a.tag}.json')
    o = rep['outline_match']
    names = list(o)
    print('OUTLINE ' + '/'.join(str(o[n]) for n in names), 'WARN', len(rep['warnings']))
    for w in rep['warnings']:
        print('  WARN:', w)
    print('LIMIT', json.dumps(rep['frames_at_joint_limit']))
    print('JUMP', json.dumps(rep['biggest_jump_deg']), 'under_floor', rep['frames_under_floor'])


if __name__ == '__main__':
    main()

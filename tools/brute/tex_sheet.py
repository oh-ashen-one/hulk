"""Side-by-side comparison sheets from tex_render outputs (system python3 + PIL).
  python3 tools/brute/tex_sheet.py [--tags before,after] [view ...]
Default tags: before,after -> renders/cmp_<view>.jpg ; other tag sets -> cmp_<tags>_<view>.jpg
If a 'uvj_<view>.png' (UV-border overlay render) exists and --uv is given it is appended.
"""
import sys, os, glob
from PIL import Image, ImageDraw
D = os.path.expanduser('~/hulk-scratch/brute_tex/renders/')
args = sys.argv[1:]
tags = ['before', 'after']
uv = False
if '--tags' in args:
    i = args.index('--tags'); tags = args[i + 1].split(','); del args[i:i + 2]
if '--uv' in args:
    uv = True; args.remove('--uv')
views = args or sorted({os.path.basename(p)[len(tags[-1]) + 1:-4] for p in glob.glob(D + tags[-1] + '_*.png')})
for v in views:
    paths = [D + f'{t}_{v}.png' for t in tags]
    labels = [t.upper() for t in tags]
    if uv and os.path.exists(D + f'uvj_{v}.png'):
        paths.append(D + f'uvj_{v}.png'); labels.append('UV BORDERS (red)')
    if not all(os.path.exists(p) for p in paths):
        continue
    ims = [Image.open(p).convert('RGB') for p in paths]
    w, h = ims[0].size
    S = Image.new('RGB', (len(ims) * (w + 8) - 8, h), (255, 255, 255))
    dr = ImageDraw.Draw(S)
    for k, (im, lab) in enumerate(zip(ims, labels)):
        S.paste(im, (k * (w + 8), 0))
        dr.text((k * (w + 8) + 8, 8), lab + ('  ' + v if k == 0 else ''), fill=(255, 255, 0))
    name = f'cmp_{v}.jpg' if tags == ['before', 'after'] and not uv else f'cmp_{"_".join(tags)}{"_uv" if uv else ""}_{v}.jpg'
    S.save(D + name, quality=90)
    print(D + name)

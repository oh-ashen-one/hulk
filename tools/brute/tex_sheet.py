"""Side-by-side before|after sheets from tex_render outputs (system python3 + PIL).
  python3 tools/brute/tex_sheet.py [view ...]
"""
import sys, os, glob
from PIL import Image, ImageDraw
D = os.path.expanduser('~/hulk-scratch/brute_tex/renders/')
views = sys.argv[1:] or sorted({os.path.basename(p)[6:-4] for p in glob.glob(D + 'after_*.png')})
for v in views:
    a, b = D + f'before_{v}.png', D + f'after_{v}.png'
    if not (os.path.exists(a) and os.path.exists(b)):
        continue
    A, B = Image.open(a).convert('RGB'), Image.open(b).convert('RGB')
    S = Image.new('RGB', (A.width + B.width + 8, A.height), (255, 255, 255))
    S.paste(A, (0, 0)); S.paste(B, (A.width + 8, 0))
    dr = ImageDraw.Draw(S); dr.text((8, 8), 'BEFORE ' + v, fill=(255, 255, 0)); dr.text((A.width + 16, 8), 'AFTER', fill=(255, 255, 0))
    S.save(D + f'cmp_{v}.jpg', quality=90)
    print(D + f'cmp_{v}.jpg')

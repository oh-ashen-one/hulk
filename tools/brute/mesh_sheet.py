# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Contact sheets for the Brute mesh track (system python3 + PIL, not Blender).
#   python3 tools/brute/mesh_sheet.py single <dir> <out.jpg> <pose1,pose2,...> [views=q34,bq34]
#   python3 tools/brute/mesh_sheet.py ba <before_dir> <after_dir> <out.jpg> <pose1,...> [views]   (before | after per view)
import sys, os
from PIL import Image, ImageDraw
mode = sys.argv[1]
TW = 360
def tile(path, label):
    im = Image.open(path).convert('RGB'); im = im.resize((TW, int(TW * im.height / im.width)))
    dr = ImageDraw.Draw(im); dr.rectangle((0, 0, TW, 18), fill=(0, 0, 0)); dr.text((4, 3), label, fill=(255, 255, 0)); return im
if mode == 'grid':
    # python3 mesh_sheet.py grid <out.jpg> <cols> <tile_px> files...
    out, cols, tp, fs = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5:]
    TW = tp; ims = [tile(f, os.path.basename(f)[:-4]) for f in fs]; th = max(i.height for i in ims)
    rows_n = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (TW * cols, th * rows_n), (20, 20, 20))
    for i, im in enumerate(ims): sheet.paste(im, ((i % cols) * TW, (i // cols) * th))
    sheet.save(out, quality=88); print(out, sheet.size); sys.exit(0)
if mode == 'single':
    d, out, poses = sys.argv[2], sys.argv[3], sys.argv[4].split(',')
    views = (sys.argv[5] if len(sys.argv) > 5 else 'q34,bq34').split(',')
    rows = [[tile(os.path.join(d, '%s_%s.png' % (p, v)), '%s %s' % (p, v)) for v in views] for p in poses]
else:
    b, a, out, poses = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5].split(',')
    views = (sys.argv[6] if len(sys.argv) > 6 else 'q34,bq34').split(',')
    rows = [[tile(os.path.join(dd, '%s_%s.png' % (p, v)), '%s %s %s' % (tag, p, v)) for v in views for dd, tag in ((b, 'BEFORE'), (a, 'AFTER'))] for p in poses]
cols = max(len(r) for r in rows); th = rows[0][0].height
# lay out: if many rows, wrap into 2 column groups
groups = 2 if len(rows) > 4 and cols <= 2 else 1
per = (len(rows) + groups - 1) // groups
sheet = Image.new('RGB', (TW * cols * groups, th * per), (20, 20, 20))
for i, r in enumerate(rows):
    gx, gy = i // per, i % per
    for j, im in enumerate(r): sheet.paste(im, ((gx * cols + j) * TW, gy * th))
sheet.save(out, quality=85); print(out, sheet.size)

# contact sheet of a capture folder's stills: python3 tools/brute/sheet.py <dir> [cols]
import sys, glob, os
from PIL import Image, ImageDraw
d = sys.argv[1]; cols = int(sys.argv[2]) if len(sys.argv) > 2 else 3
fs = sorted(f for f in glob.glob(os.path.join(d, '*_t*.png')))
W, H = 640, 360; rows = (len(fs) + cols - 1) // cols
sheet = Image.new('RGB', (W * cols, H * rows))
for i, f in enumerate(fs):
    im = Image.open(f).convert('RGB').resize((W, H))
    ImageDraw.Draw(im).text((8, 6), os.path.basename(f).split('_t')[-1][:-4], fill=(255, 255, 0))
    sheet.paste(im, ((i % cols) * W, (i // cols) * H))
out = os.path.join(d, 'sheet.jpg'); sheet.save(out, quality=82); print(out)

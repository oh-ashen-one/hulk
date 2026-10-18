#!/usr/bin/env python3
# Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
# Procedural impact-crack decal for the Brute's punches / landings (critic 2026-10-17: the geometry dents read as round blobs with
# spikes): a crushed centre (dented, chipped, darkest), jagged branching radial cracks that thin out and fork, a few concentric
# fractures, chipped spall flakes. Writes RGBA colour (alpha = coverage) + a tangent normal map derived from the crack height.
# usage: python3 tools/brute/make_crack_decal.py <out_dir> [seed]
import sys, os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1]; SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 7
os.makedirs(OUT, exist_ok=True)
S = 1024; C = S / 2
rng = random.Random(SEED)
depth = Image.new('L', (S, S), 0)      # 255 = deepest
d = ImageDraw.Draw(depth)

def crack(x, y, ang, length, width, gen):
    """jagged crack: short segments with random heading drift, forks while it thins"""
    steps = int(length / 9)
    for i in range(steps):
        ang += rng.uniform(-0.38, 0.38)
        seg = rng.uniform(6, 13)
        nx, ny = x + math.cos(ang) * seg, y + math.sin(ang) * seg
        w = max(1, int(width * (1 - i / steps) + 0.5))
        d.line([(x, y), (nx, ny)], fill=int(170 + 80 * (1 - i / steps)), width=w)
        x, y = nx, ny
        if gen < 3 and rng.random() < 0.07 + 0.03 * gen:
            crack(x, y, ang + rng.choice((-1, 1)) * rng.uniform(0.35, 0.9), length * rng.uniform(0.3, 0.55) * (1 - i / steps), width * 0.6, gen + 1)

# crushed centre: irregular blob, chipped edge, filled with pits (no concentric rings: they read as a target)
core_r = S * 0.13
pts = []
jit = [rng.uniform(0.82, 1.12) for _ in range(12)]
for k in range(96):   # smooth wobbly outline (interpolated jitter: no star points)
    a = k / 96 * 2 * math.pi; u = k / 96 * 12; i0 = int(u) % 12; f = u - int(u)
    r = core_r * (jit[i0] * (1 - f) + jit[(i0 + 1) % 12] * f) * rng.uniform(0.97, 1.03)
    pts.append((C + math.cos(a) * r, C + math.sin(a) * r))
d.polygon(pts, fill=140)
for k in range(260):  # crushed, chipped concrete: overlapping irregular pits, deeper and denser towards the middle
    rr = core_r * math.sqrt(rng.random()) * 0.95; a = rng.uniform(0, 2 * math.pi)
    x, y = C + math.cos(a) * rr, C + math.sin(a) * rr; s_ = rng.uniform(4, 18) * (1.2 - rr / core_r)
    d.polygon([(x + rng.uniform(-s_, s_), y + rng.uniform(-s_, s_)) for _ in range(6)], fill=int(165 + 80 * (1 - rr / core_r) * rng.uniform(0.6, 1.0)))
# radial cracks
n = rng.randint(9, 13)
for k in range(n):
    a = k / n * 2 * math.pi + rng.uniform(-0.2, 0.2)
    r0 = core_r * rng.uniform(0.7, 1.0)
    crack(C + math.cos(a) * r0, C + math.sin(a) * r0, a, S * rng.uniform(0.22, 0.38), rng.uniform(5, 9), 0)
# spall flakes around the core
for k in range(26):
    a = rng.uniform(0, 2 * math.pi); r = core_r * rng.uniform(1.15, 1.9); s = rng.uniform(3, 8)
    x, y = C + math.cos(a) * r, C + math.sin(a) * r
    d.polygon([(x + rng.uniform(-s, s), y + rng.uniform(-s, s)) for _ in range(5)], fill=rng.randint(70, 120))

dep = np.asarray(depth.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.0
# radial fade so the decal edge never shows
yy, xx = np.mgrid[0:S, 0:S]; rad = np.sqrt((xx - C) ** 2 + (yy - C) ** 2) / (S / 2)
fade = np.clip((1.0 - rad) / 0.25, 0, 1)
alpha = np.clip(dep * 1.6, 0, 1) * fade
# colour: concrete dust grey-brown in the crush, near-black inside the cracks
grey = np.array([0.30, 0.28, 0.26]); black = np.array([0.04, 0.035, 0.03])
k = np.clip((dep - 0.55) / 0.45, 0, 1)[..., None]
col = grey * (1 - k) + black * k
rgba = np.dstack([col, alpha[..., None]])
Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'T_BruteCrack_D.png'))
# normal from height (height = -depth), OpenGL convention
h = -dep * 6.0
gx = np.zeros_like(h); gy = np.zeros_like(h)
gx[:, 1:-1] = (h[:, 2:] - h[:, :-2]) * 0.5; gy[1:-1, :] = (h[2:, :] - h[:-2, :]) * 0.5
nz = np.ones_like(h); nrm = np.dstack([-gx, gy, nz]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8), 'RGB').save(os.path.join(OUT, 'T_BruteCrack_N.png'))
print('WROTE', OUT)

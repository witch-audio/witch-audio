import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1280, 640
OUT = Path('/Users/witchaudio/Developer/github-personal/witch-audio/witch_audio_profile_art.png')
FONT_PATH = '/System/Library/Fonts/SFNSMono.ttf'
TITLE_FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
CHARS = ' .,:;irsXA253hMHGS#9B&@'
random.seed(7)
np.random.seed(7)

img = Image.new('RGB', (W, H), (3, 6, 10))
arr = np.zeros((H, W, 3), dtype=np.float32)

y = np.linspace(0, 1, H)[:, None]
x = np.linspace(0, 1, W)[None, :]
arr[..., 0] = 4 + 9 * (1 - y)
arr[..., 1] = 8 + 18 * (1 - y)
arr[..., 2] = 14 + 28 * (1 - y)

# deep glows
for cx, cy, rx, ry, col, a in [
    (0.18, 0.30, 0.18, 0.25, np.array([60, 255, 180]), 0.18),
    (0.82, 0.30, 0.20, 0.25, np.array([90, 220, 255]), 0.18),
    (0.50, 0.55, 0.30, 0.18, np.array([180, 80, 255]), 0.10),
]:
    blob = np.exp(-(((x - cx) ** 2) / rx**2 + ((y - cy) ** 2) / ry**2))
    arr += blob[..., None] * col * a

# stars / dust
for _ in range(1400):
    px = random.randint(0, W - 1)
    py = random.randint(0, H - 1)
    v = random.randint(30, 120)
    arr[max(0, py-1):min(H, py+2), max(0, px-1):min(W, px+2), :] += np.array([v * 0.2, v * 0.5, v * 0.8])

base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
draw = ImageDraw.Draw(base)

mono = ImageFont.truetype(FONT_PATH, 13)
small = ImageFont.truetype(FONT_PATH, 16)
cell_w = 8
cell_h = 13
cols = W // cell_w
rows = H // cell_h

# intensity field for layered art
field = np.zeros((rows, cols), dtype=np.float32)
color_mix = np.zeros((rows, cols, 3), dtype=np.float32)
xx = np.linspace(0, 1, cols)[None, :]
yy = np.linspace(0, 1, rows)[:, None]

# left/right phantom clusters with depth
for cx, cy, sx, sy, amp, tint in [
    (0.22, 0.48, 0.10, 0.22, 1.2, np.array([70, 255, 180])),
    (0.78, 0.48, 0.10, 0.22, 1.15, np.array([90, 220, 255])),
    (0.18, 0.45, 0.16, 0.28, 0.55, np.array([150, 80, 255])),
    (0.82, 0.45, 0.16, 0.28, 0.55, np.array([150, 80, 255])),
]:
    blob = np.exp(-(((xx - cx) ** 2) / sx**2 + ((yy - cy) ** 2) / sy**2)) * amp
    ripple = 0.72 + 0.28 * np.sin((xx * 26 + yy * 17) * math.pi)
    shaped = blob * ripple
    field += shaped
    color_mix += shaped[..., None] * tint

# center void and atmosphere
void = np.exp(-(((xx - 0.50) ** 2) / 0.11**2 + ((yy - 0.48) ** 2) / 0.22**2))
field *= (1 - void * 0.92)

# subtle waveform arc across center
arc = np.exp(-((yy - (0.62 + 0.07 * np.sin(xx * math.pi * 3.0))) ** 2) / 0.003)
field += arc * 0.22
color_mix += arc[..., None] * np.array([255, 120, 255])

# digital rain / vertical streaks
for c in range(0, cols, 2):
    strength = 0.10 + 0.18 * (math.sin(c * 0.22) * 0.5 + 0.5)
    column = np.linspace(0.2, 1.0, rows)[:, None].flatten()
    streak = np.zeros(rows, dtype=np.float32)
    start = random.randint(0, rows - 1)
    length = random.randint(rows // 5, rows // 2)
    for r in range(length):
        streak[(start + r) % rows] += strength * (r / max(1, length))
    field[:, c] += streak * 0.45
    color_mix[:, c, :] += streak[:, None] * np.array([70, 220, 255])

# noise field
noise = np.random.rand(rows, cols) * 0.18
field += noise

# render ascii layers
for gy in range(rows):
    for gx in range(cols):
        val = field[gy, gx]
        if val < 0.08:
            if random.random() < 0.022:
                ch = random.choice('.,:')
                draw.text((gx * cell_w, gy * cell_h), ch, font=mono, fill=(40, 90, 110))
            continue
        idx = min(len(CHARS) - 1, int(val / 1.6 * (len(CHARS) - 1)))
        ch = CHARS[idx]
        tint = color_mix[gy, gx]
        if tint.sum() == 0:
            tint = np.array([120, 220, 255], dtype=np.float32)
        tint = tint / max(1.0, tint.max())
        lum = min(1.0, 0.25 + val * 0.8)
        col = (tint * 200 * lum + np.array([40, 60, 90])).clip(0, 255)
        draw.text((gx * cell_w, gy * cell_h), ch, font=mono, fill=tuple(int(c) for c in col))

# soft scanlines and glow panels
arr = np.asarray(base, dtype=np.float32)
arr[::2, :, :] *= 0.975
for y0 in [84, 530]:
    arr[y0:y0+1, 54:W-54, :] += np.array([30, 80, 110])

base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')

overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
od = ImageDraw.Draw(overlay)

# title and metadata, subtle and art-directed
try:
    title_font = ImageFont.truetype(TITLE_FONT, 56)
except:
    title_font = ImageFont.truetype(FONT_PATH, 44)
meta_font = ImageFont.truetype(FONT_PATH, 17)
small_meta = ImageFont.truetype(FONT_PATH, 14)

od.text((52, 52), '/* witch.audio :: making AI do the weird audio stuff i always wanted */', font=meta_font, fill=(160, 235, 255, 220))
od.text((52, 78), '[ livestream mode: ON ]', font=meta_font, fill=(210, 150, 255, 220))
od.text((W-52, 52), 'goal: 10,000 apps', font=meta_font, fill=(230, 245, 255, 220), anchor='ra')
od.text((W-52, 78), 'status: signal found', font=meta_font, fill=(255, 150, 235, 220), anchor='ra')

# central title glow
for dx, dy, fill in [(-2,0,(70,220,255,90)), (2,0,(160,100,255,90)), (0,0,(240,250,255,235))]:
    od.text((W//2 + dx, H//2 - 36 + dy), 'witch.audio', font=title_font, fill=fill, anchor='ma')
od.text((W//2, H//2 + 26), 'weird audio apps  //  agent-made plugins  //  vibe marketing tools', font=meta_font, fill=(190, 230, 255, 210), anchor='ma')

# side notes
for i, line in enumerate([
    '>> build weird audio tools live',
    '>> turn fear into signal',
    '>> ship beautiful cursed software',
]):
    od.text((80, 430 + i * 26), line, font=meta_font, fill=(220, 245, 255, 210))

for i, line in enumerate([
    'now building',
    'weird audio apps',
    'AI plugin experiments',
    'livestream chaos',
]):
    fill = (235, 245, 255, 225) if i == 0 else (190, 230, 255, 210)
    od.text((930, 420 + i * 26), line, font=meta_font, fill=fill)

od.text((52, H-30), 'github.com/witch-audio', font=small_meta, fill=(120, 170, 200, 220))
od.text((W//2, H-30), 'make it strange // make it sing', font=small_meta, fill=(120, 170, 200, 220), anchor='ma')
od.text((W-52, H-30), 'witch.audio', font=small_meta, fill=(120, 170, 200, 220), anchor='ra')

# vignette
final = Image.alpha_composite(base, overlay).convert('RGB')
arr = np.asarray(final, dtype=np.float32)
xx2 = np.linspace(-1, 1, W)[None, :]
yy2 = np.linspace(-1, 1, H)[:, None]
v = np.clip(1.10 - 0.32 * np.sqrt(xx2**2 + yy2**2), 0.70, 1.05)
arr *= v[:, :, None]
Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(OUT)
print(OUT)

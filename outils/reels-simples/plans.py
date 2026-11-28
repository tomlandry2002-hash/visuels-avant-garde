#!/usr/bin/env python3
"""Découpe un extrait en plans et repère les visages : python3 plans.py extrait.mp4 sortie.jpg
Affiche pour chaque plan : début, fin, visages (cx, cy, taille) ; produit une planche annotée."""
import cv2, sys, subprocess, re
from PIL import Image, ImageDraw, ImageFont
src, out = sys.argv[1], sys.argv[2]
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout)
r = subprocess.run(['ffmpeg', '-v', 'info', '-i', src, '-vf', "scale=160:90,select='gt(scene,0.1)',showinfo", '-f', 'null', '-'], capture_output=True, text=True).stderr
cuts = [float(x) for x in re.findall(r'pts_time:([0-9.]+)', r)]
bornes = [0.0] + cuts + [dur]
casc = cv2.CascadeClassifier(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'haar.xml'))
cap = cv2.VideoCapture(src)
tiles = []
import os
try:
    font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'polices', 'Outfit-Bold.ttf'), 26)
except OSError:
    font = ImageFont.load_default()
for i in range(len(bornes) - 1):
    a, b = bornes[i], bornes[i + 1]
    if b - a < 0.2: continue
    t = (a + b) / 2
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, fr = cap.read()
    if not ok: continue
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    fs = casc.detectMultiScale(g, 1.1, 6, minSize=(90, 90))
    fs = sorted(fs, key=lambda f: -f[2])[:3]
    desc = ' '.join(f'({x + w // 2},{y + h // 2},{w})' for x, y, w, h in fs)
    print(f'plan {i}: {a:6.2f} -> {b:6.2f}  visages {desc}')
    im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)).resize((480, 270))
    d = ImageDraw.Draw(im)
    for x in range(0, 480, 48): d.line([(x, 0), (x, 270)], fill=(255, 255, 0), width=1)
    for y in range(0, 270, 27): d.line([(0, y), (480, y)], fill=(255, 255, 0), width=1)
    for x, y, w, h in fs: d.rectangle([x / 4, y / 4, (x + w) / 4, (y + h) / 4], outline=(255, 0, 0), width=3)
    d.rectangle([0, 0, 260, 32], fill=(0, 0, 0)); d.text((4, 2), f'{i}: {a:.1f}-{b:.1f}', fill=(255, 255, 255), font=font)
    tiles.append(im)
cols = 4; rows = (len(tiles) + cols - 1) // cols
sheet = Image.new('RGB', (480 * cols, 270 * rows))
for k, im in enumerate(tiles): sheet.paste(im, ((k % cols) * 480, (k // cols) * 270))
sheet.save(out, quality=80)

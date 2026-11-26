#!/usr/bin/env python3
"""Recentre chaque morceau d'un plan.json sur le visage le plus proche du cx prévu.
python3 ajuster.py plan.json   (réécrit le fichier ; affiche les changements)"""
import cv2, json, sys, statistics
p = sys.argv[1]; c = json.load(open(p))
casc = cv2.CascadeClassifier(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'haar.xml'))
cap = cv2.VideoCapture(c['source'])
LOGO_X, LOGO_Y, BAS = 1560, 135, 775
for m in c['morceaux']:
    t0, t1, cx, cy, h = m[:5]
    xs, ys = [], []
    for f in (0.2, 0.5, 0.8):
        cap.set(cv2.CAP_PROP_POS_MSEC, (t0 + (t1 - t0) * f) * 1000)
        ok, fr = cap.read()
        if not ok: continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        fs = [f_ for f_ in casc.detectMultiScale(g, 1.1, 6, minSize=(110, 110)) if f_[1] + f_[3] / 2 < 700]
        if not fs: continue
        x, y, w, hh = min(fs, key=lambda f_: abs(f_[0] + f_[2] / 2 - cx))
        if abs(x + w / 2 - cx) > 420: continue
        xs.append(x + w / 2); ys.append(y + hh / 2)
    if xs:
        ncx = statistics.median(xs); fy = statistics.median(ys)
        ncy = fy + 0.12 * h                       # visage un peu au-dessus du centre
        w = h * 0.8
        ncy = max(h / 2, min(BAS - h / 2, ncy))
        if ncx + w / 2 > LOGO_X and ncy - h / 2 < LOGO_Y:   # éviter le logo en haut à droite
            ncy = LOGO_Y + h / 2
            if ncy + h / 2 > BAS: h = BAS - LOGO_Y; ncy = LOGO_Y + h / 2; m[4] = int(h)
        print(f'{t0:6.2f}-{t1:6.2f}: cx {cx}->{ncx:.0f}  cy {cy}->{ncy:.0f}  h {m[4]}')
        m[2], m[3] = int(ncx), int(ncy)
    else:
        print(f'{t0:6.2f}-{t1:6.2f}: pas de visage, inchangé')
json.dump(c, open(p, 'w'), ensure_ascii=False, indent=1)

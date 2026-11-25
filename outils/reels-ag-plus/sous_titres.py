#!/usr/bin/env python3
"""Brouillon de sous-titres à partir de la transcription (transcrire.py).

  python3 sous_titres.py transcription.jsonl DEBUT FIN [--decalage D] [--max 28]

DEBUT et FIN en secondes dans la vidéo complète ; --decalage = seconde de la vidéo complète
qui correspond au début du montage. Affiche des blocs [t0, t1, "texte"] relatifs au montage,
coupés à la ponctuation ou vers --max signes : à reprendre à la main (deux lignes au plus,
28 signes par ligne environ, typographie française, **mot** pour surligner).
"""
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument('jsonl'); ap.add_argument('debut', type=float); ap.add_argument('fin', type=float)
ap.add_argument('--decalage', type=float); ap.add_argument('--max', type=int, default=28)
a = ap.parse_args()
o = a.debut if a.decalage is None else a.decalage
mots = []
for l in open(a.jsonl):
    mots += json.loads(l)['w']
mots = [m for m in mots if a.debut <= m[0] <= a.fin]
bloc = []
for m in mots:
    bloc.append(m)
    t = ''.join(x[2] for x in bloc).strip()
    if (m[2].strip()[-1:] in '.,?!' and len(t) > 12) or len(t) > a.max * 2 - 6:
        print(f'[{bloc[0][0] - o:.2f}, {bloc[-1][1] - o:.2f}, {t!r}],'); bloc = []
if bloc:
    print(f'[{bloc[0][0] - o:.2f}, {bloc[-1][1] - o:.2f}, {"".join(x[2] for x in bloc).strip()!r}],')

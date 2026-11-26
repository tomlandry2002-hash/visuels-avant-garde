#!/usr/bin/env python3
"""Reel d'extrait (compte Roussel, espace Publer C) : carte d'accroche blanche en haut, panneau 4:5 sur fond flouté,
zooms par phrase, sous-titres mot à mot en Barlow Condensed Black (majuscules, mot prononcé en jaune), musique discrète.

  python3 monter.py plan.json

plan.json :
  source        extrait 1920x1080 (recoupé avec marge), temps en secondes dans ce fichier
  transcription jsonl (transcrire.py), decalage = seconde de l'émission qui correspond au t=0 de source
  morceaux      [[t0, t1, cx, cy, h, z0, z1], ...]  boîte 4:5 centrée (cx, cy) de hauteur h dans la source,
                zoom de z0 à z1 au fil du morceau (1 = boîte telle quelle)
  accroche      ["LIGNE 1", "LIGNE 2"] en majuscules, carte blanche fixe ; *mot* = rouge (2 lignes, ~32 signes max)
  corrections   [[temps absolu approx., "mot transcrit", "mot juste"], ...] (ponctuation comprise dans le mot juste)
  musique       réglages de ../reels/musique.py + "volume" (dB, défaut -21)
  sortie        dossier
"""
import json, os, re, subprocess, sys
cfg = json.load(open(sys.argv[1]))
OUT = cfg['sortie']; os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
PW, PH, PY = 1080, 1350, 360          # panneau vidéo
ACC = cfg.get('accent', '&H0000D4FF&')  # jaune (BGR)
ICI = os.path.dirname(os.path.abspath(__file__))
FONTDIR = os.path.join(ICI, 'polices')
src = cfg['source']; dec = cfg['decalage']
morceaux = cfg['morceaux']

# ---------- sous-titres mot à mot (ASS) ----------
mots = []
for l in open(cfg['transcription']):
    for w in json.loads(l)['w']:
        mots.append([w[0] - dec, w[1] - dec, w[2].strip()])
# fusion des morceaux de mots (c + 'est, peut + -être)
m2 = []
for a, b, w in mots:
    if m2 and w[:1] in "'-" and a - m2[-1][1] < 0.3:
        m2[-1][1] = b; m2[-1][2] += w
    else:
        m2.append([a, b, w])
mots = m2
for t, old, neu in cfg.get('corrections', []):   # [temps absolu approx., mot transcrit, mot juste]
    c = [m for m in mots if m[2].lower().strip('.,') == old.lower().strip('.,') and abs(m[0] + dec - t) < 0.6]
    if not c: print('correction introuvable', t, old)
    else: min(c, key=lambda m: abs(m[0] + dec - t))[2] = neu
seg = []; tpos = 0.0
for (t0, t1, *_r) in morceaux:
    for a, b, w in mots:
        if t0 - 0.05 <= a < t1 - 0.05 and w:
            seg.append([a - t0 + tpos, min(b, t1) - t0 + tpos, w])
    tpos += t1 - t0
D = tpos

def fr(t):  # typographie : espace fine insécable avant ? ! ; :
    t = t.replace("'", "’")
    return re.sub(r'\s*([?!;:])', ' \\1', t)

# découpe en groupes de 1 à 3 mots, coupure après ponctuation ou pause
groupes = []; g = []
for i, m in enumerate(seg):
    g.append(m)
    pause = i + 1 < len(seg) and seg[i + 1][0] - m[1] > 0.35
    long_ = sum(len(x[2]) + 1 for x in g) > 18
    PETITS = {'le', 'la', 'les', 'de', 'des', 'du', 'un', 'une', 'à', 'et', 'au', 'aux', 'pour', 'par', 'dans', 'leur', 'leurs'}
    if m[2][-1:] in '.,?!;:…' or pause or i == len(seg) - 1:
        groupes.append(g); g = []
    elif len(g) >= 3 or long_:
        if len(g) > 1 and g[-1][2].lower() in PETITS:
            groupes.append(g[:-1]); g = [g[-1]]
        else:
            groupes.append(g); g = []
for k, g in enumerate(groupes):  # chaque groupe reste jusqu'au suivant (max +0,4 s)
    fin = g[-1][1] + 0.4
    if k + 1 < len(groupes): fin = min(fin, groupes[k + 1][0][0])
    g.append(fin)

def ts(t):
    t = max(t, 0); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

ass = [
    '[Script Info]', 'ScriptType: v4.00+', f'PlayResX: {W}', f'PlayResY: {H}', 'WrapStyle: 0', '',
    '[V4+ Styles]',
    'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
    'Style: ST,Barlow Condensed Black,118,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,5,3,2,60,60,560,1',
    'Style: HK,Barlow Condensed Black,88,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,80,80,134,1',
    '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
for g in groupes:
    fin = g[-1]; ws = g[:-1]
    for j, (a, b, w) in enumerate(ws):
        e = ws[j + 1][0] if j + 1 < len(ws) else fin
        parts = []
        for jj, (_, _, ww) in enumerate(ws):
            txt = fr(ww).upper()
            parts.append('{\\c' + ACC + '}' + txt + '{\\c&HFFFFFF&}' if jj == j else txt)
        pop = '{\\fscx110\\fscy110\\t(0,90,\\fscx100\\fscy100)}' if j == 0 else ''
        ass.append(f'Dialogue: 0,{ts(a)},{ts(e)},ST,,0,0,0,,{pop}' + ' '.join(parts))
# accroche fixe en haut, encadré blanc
hk = []
for l in cfg.get('accroche', []):
    hk.append(re.sub(r'\*(.+?)\*', lambda m: '{\\c&H1A1AD6&}' + m.group(1) + '{\\c&H111111&}', fr(l)))
if hk:
    txt = '\\N'.join(hk)
    ass.append(f'Dialogue: 1,{ts(0)},{ts(D)},HK,,0,0,0,,{{\\c&H111111&\\3c&HFFFFFF&\\bord0\\fad(150,0)}}{txt}')
open(os.path.join(OUT, 'st.ass'), 'w').write('\n'.join(ass) + '\n')

# ---------- musique ----------
mus = cfg.get('musique')
if mus is not None:
    sections = []; t = 0; plan = 4 * 60 / mus.get('bpm', 112) * 2
    ener = ['intro', 'groove', 'plein', 'groove', 'creux', 'plein']
    k = 0
    while t < D:
        sections.append({'debut': t, 'duree': min(plan, D - t + 0.01), 'energie': ener[min(k, len(ener) - 1)] if k < 2 else ener[2 + (k % 4)], 'impact': False})
        t += plan; k += 1
    sections[-1]['energie'] = 'fin'
    subprocess.run(['python3', os.path.join(ICI, '..', 'reels', 'musique.py'), '--sortie', os.path.join(OUT, 'musique.wav'),
                    '--reglages', json.dumps(mus), '--sections', json.dumps(sections)], check=True)

# ---------- vidéo ----------
fc = []; n = len(morceaux)
fc.append(f'[0:v]split={n}' + ''.join(f'[v{k}]' for k in range(n)))
fc.append(f'[0:a]asplit={n}' + ''.join(f'[a{k}]' for k in range(n)))
for k, (t0, t1, cx, cy, h, z0, z1) in enumerate(morceaux):
    w = h * 4 / 5; d = t1 - t0
    x = max(0, min(1920 - w, cx - w / 2)); y = max(0, min(1080 - h, cy - h / 2))
    z = f'({z0}+({z1}-{z0})*min(t/{d:.3f},1))'
    fc.append(f'[v{k}]trim={t0}:{t1},setpts=PTS-STARTPTS,fps={FPS},crop={int(w)}:{int(h)}:{int(x)}:{int(y)},split[p{k}][b{k}]')
    fc.append(f"[p{k}]scale=w='trunc({PW}*{z}/2)*2':h='trunc({PH}*{z}/2)*2':eval=frame:flags=bicubic,crop={PW}:{PH},"
              f"eq=contrast=1.06:saturation=1.08,setsar=1[q{k}]")
    fc.append(f'[b{k}]scale=-2:{H},crop={W}:{H},boxblur=30:3,eq=brightness=-0.22:saturation=1.2,setsar=1[g{k}]')
    fc.append(f'[g{k}][q{k}]overlay=0:{PY}:shortest=1,format=yuv420p[c{k}]')
    fc.append(f'[a{k}]atrim={t0}:{t1},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={d - 0.05:.3f}:d=0.05[s{k}]')
fc.append(''.join(f'[c{k}]' for k in range(n)) + f'concat=n={n}:v=1:a=0[fond]')
fc.append(''.join(f'[s{k}]' for k in range(n)) + f'concat=n={n}:v=0:a=1[voix0]')
# bandeau blanc derrière l'accroche
lignes = len(cfg.get('accroche', []))
if lignes:
    bh = 46 + 88 * lignes
    fc.append(f'[fond]drawbox=x=60:y=110:w={W - 120}:h={bh}:color=white@1:t=fill[fond2]')
else:
    fc.append('[fond]null[fond2]')
fc.append(f"[fond2]subtitles={os.path.join(OUT, 'st.ass')}:fontsdir={FONTDIR}[v]")
fc.append('[voix0]aformat=channel_layouts=stereo,highpass=f=70,loudnorm=I=-15:TP=-1.5:LRA=9,aresample=48000,asplit[voix][sc]')
inputs = ['-i', src]
if mus is not None:
    vol = mus.get('volume', -21)
    inputs += ['-i', os.path.join(OUT, 'musique.wav')]
    fc.append(f'[1:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol}dB,afade=t=out:st={D - 1.2:.2f}:d=1.2[m0]')
    fc.append('[m0][sc]sidechaincompress=threshold=0.05:ratio=6:attack=15:release=350[m1]')
    fc.append('[voix][m1]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[a]')
else:
    fc.append('[voix]anull[a]')
sortie = os.path.join(OUT, 'reel.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', str(FPS),
                '-c:a', 'aac', '-b:a', '192k', '-t', f'{D:.3f}', '-movflags', '+faststart', sortie], check=True)
# planche de contrôle
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', sortie, '-vf', f'fps={12 / D:.4f},scale=270:480,tile=6x2', '-frames:v', '1',
                os.path.join(OUT, 'planche.jpg')], check=True)
print('OK', sortie, f'{D:.1f} s')

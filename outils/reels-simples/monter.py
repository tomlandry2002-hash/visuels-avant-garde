#!/usr/bin/env python3
"""Reel SIMPLE (style sobre « Attal », validé par Tom le 28/11/2026) : vidéo plein cadre 9:16, étalonnage doux, grain léger,
sous-titres blancs Outfit ExtraBold (minuscules, 2 ou 3 mots, ombre noire floutée), sans titre,
bandeau nom (cartouche blanc) + fonction (cartouche noir translucide) qui se déroulent les 4 premières secondes.
Coupes : mêmes règles que reels-roussel/monter.py (jamais un mot coupé, allongement auto aux jonctions).

  python3 monter.py plan.json

plan.json :
  source          extrait 1920x1080 (recoupé avec 1,5 s de marge), temps en secondes dans ce fichier
  transcription   jsonl de transcrire.py ; decalage = seconde de l'émission qui correspond au t=0 de source
  morceaux        [[t0, t1, cx, cy, h, z0, z1], ...] : boîte 9:16 (largeur = h × 9/16) centrée (cx, cy), hauteur h
                  (1080 = pleine hauteur, conseillé : l'image est déjà agrandie 1,78 fois), zoom z0 → z1 (max 1,2)
  nom             ["Prénom Nom", "Fonction"] : bandeau (facultatif)
  corrections     [[temps absolu, "mot transcrit", "mot juste"], ...]
  musique_fichier WAV de composer.py (facultatif) ; musique_volume en dB (défaut -12, test à -6), baisse sous la voix
  accroche        facultatif, déconseillé (Tom le trouve inutile) : lignes courtes en haut à gauche
  police          facultatif (défaut "Outfit ExtraBold") ; police2 (défaut "Outfit Bold")
  sortie          dossier (reel.mp4 + planche.jpg)
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
DEBORD = cfg.get('debord', False)

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
# coupes sûres : ne jamais couper un mot (demande de Tom, 26/11/2026).
# Aux jonctions avec saut (et en fin de reel), on prolonge jusqu'à la fin réelle du dernier mot
# + 0,35 s (Whisper note souvent la fin trop tôt), sans mordre sur le mot suivant ; au début d'un
# morceau après un saut, on recule jusqu'à 0,12 s avant le premier mot.
def _src_dur():
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src],
                       capture_output=True, text=True).stdout.strip()
    return float(r) if r else 1e9
DUR = _src_dur()
for i, m in enumerate(morceaux):
    t0, t1 = m[0], m[1]
    saut_apres = i == len(morceaux) - 1 or morceaux[i + 1][0] > t1 + 0.05
    saut_avant = i == 0 or morceaux[i - 1][1] < t0 - 0.05
    if saut_apres:
        dedans = [w for w in mots if w[0] < t1 - 0.02 and w[1] > t0]
        apres = [w[0] for w in mots if w[0] >= t1 - 0.02]
        if dedans:
            fin = max(w[1] for w in dedans) + 0.35
            if apres: fin = min(fin, min(apres) - 0.04)
            if i + 1 < len(morceaux): fin = min(fin, morceaux[i + 1][0] if morceaux[i + 1][0] > t0 else fin)
            m[1] = round(min(max(t1, fin), DUR - 0.05), 3)
    if saut_avant:
        premiers = [w for w in mots if w[0] >= t0 - 0.05 and w[0] < m[1]]
        avant = [w[1] for w in mots if w[1] <= t0 + 0.02 and w[0] < t0]
        if premiers:
            deb = min(w[0] for w in premiers) - 0.12
            if avant: deb = max(deb, max(avant) + 0.03)
            m[0] = round(max(0.0, min(t0, deb)), 3)
    if (m[0], m[1]) != (t0, t1):
        print(f'coupe ajustée : {t0:.2f}-{t1:.2f} -> {m[0]:.2f}-{m[1]:.2f}')
seg = []; tpos = 0.0
for (t0, t1, *_r) in morceaux:
    for a, b, w in mots:
        if t0 - 0.05 <= a < t1 - 0.05 and w:
            seg.append([a - t0 + tpos, min(b, t1) - t0 + tpos, w])
    tpos += t1 - t0
D = tpos

def fr(t):  # typographie : apostrophe courbe, espace avant ? ! ; :
    t = t.replace("'", "’")
    return re.sub(r'\s*([?!;:])', ' \\1', t)

# groupes de 2 à 5 mots (≤ 24 signes), coupure après ponctuation ou pause
PETITS = {'le', 'la', 'les', 'de', 'des', 'du', 'un', 'une', 'à', 'et', 'au', 'aux', 'pour', 'par', 'dans', 'leur', 'leurs',
          'en', 'ce', 'ces', 'son', 'sa', 'ses', 'qui', 'que', 'on', 'nous', 'ne', 'pas', 'plus', "qu'", 'sur', 'avec'}
groupes = []; g = []
for i, m in enumerate(seg):
    g.append(m)
    pause = i + 1 < len(seg) and seg[i + 1][0] - m[1] > 0.4
    long_ = sum(len(x[2]) + 1 for x in g) > 13 or len(g) >= 3
    if m[2][-1:] in '.?!;:…' or pause or i == len(seg) - 1:
        groupes.append(g); g = []
    elif long_ or (m[2][-1:] == ',' and len(g) >= 2):
        if long_ and len(g) > 1 and g[-1][2].lower() in PETITS:
            groupes.append(g[:-1]); g = [g[-1]]
        else:
            groupes.append(g); g = []
for k, g in enumerate(groupes):
    fin = g[-1][1] + 0.5
    if k + 1 < len(groupes): fin = min(fin, groupes[k + 1][0][0])
    g.append(fin)

def ts(t):
    t = max(t, 0); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

def propre(w):  # minuscules naturelles, ponctuation de fin retirée (sauf ? et !)
    w = fr(w)
    return re.sub(r'[.,;:…]+$', '', w)

F = cfg.get('police', 'Outfit ExtraBold'); FQ = cfg.get('police2', 'Outfit Bold')
STY = 'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding'
ass = ['[Script Info]', 'ScriptType: v4.00+', f'PlayResX: {W}', f'PlayResY: {H}', 'WrapStyle: 0', 'ScaledBorderAndShadow: yes', '',
       '[V4+ Styles]', STY,
       f'Style: ST,{F},112,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,2,90,90,560,1',
       f'Style: HK,{F},64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,70,70,170,1',
       f'Style: NM,{F},54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,1,90,90,330,1',
       f'Style: NQ,{FQ},42,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,1,90,90,285,1',
       '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']

def pose(style, x, y, an):  # positions explicites pour décaler l'ombre de 3 px
    return (f'\\an{an}\\pos({x + 2},{y + 4})', f'\\an{an}\\pos({x},{y})')

# sous-titres : un groupe à la fois, petit fondu (sobre)
for g in groupes:
    fin = g[-1]; ws = g[:-1]
    txt = ' '.join(propre(w) for _, _, w in ws)
    sh, tx = pose('ST', W // 2, H - 560, 2)
    ass.append(f'Dialogue: 0,{ts(ws[0][0])},{ts(fin)},ST,,0,0,0,,{{{sh}\\c&H000000&\\alpha&H60&\\blur10\\fad(70,0)}}{txt}')
    ass.append(f'Dialogue: 1,{ts(ws[0][0])},{ts(fin)},ST,,0,0,0,,{{{tx}\\fad(70,0)}}{txt}')
# titre discret en haut (phrase en minuscules, *mot* = semi-gras plus lumineux… on garde blanc uni)
hk = [re.sub(r'\*(.+?)\*', r'\1', fr(l)) for l in cfg.get('accroche', [])]
if hk:
    txt = '\\N'.join(hk)
    sh, tx = pose('HK', 70, 170, 7)
    ass.append(f'Dialogue: 2,{ts(0)},{ts(D)},HK,,0,0,0,,{{{sh}\\c&H000000&\\alpha&H58&\\blur12\\q2\\fad(250,0)}}{txt}')
    ass.append(f'Dialogue: 3,{ts(0)},{ts(D)},HK,,0,0,0,,{{{tx}\\q2\\fad(250,0)}}{txt}')
# nom en bas-tiers, 4 s au début, avec un filet
nom = cfg.get('nom')
if nom:
    # bandeau : nom en sombre dans un cartouche blanc qui se déroule de gauche à droite, fonction juste dessous
    from PIL import ImageFont
    def largeur(txt, fichier, taille):
        f = ImageFont.truetype(os.path.join(FONTDIR, fichier), taille)
        asc, desc = f.getmetrics()   # libass ramène la taille à la hauteur de ligne
        return f.getlength(txt) * taille / (asc + desc)
    a, b = 0.4, min(4.8, D)
    X0, Y0, HB, PAD, TN = 70, 1500, 86, 28, 54
    wb = int(largeur(fr(nom[0]), cfg.get('police_fichier', 'Outfit-ExtraBold.ttf'), TN) + 2 * PAD)
    ouvre = f'\\clip({X0},0,{X0},{H})\\t(0,320,0.6,\\clip({X0},0,{X0 + wb + 4},{H}))'
    boite = f'm 0 0 l {wb} 0 l {wb} {HB} l 0 {HB}'
    ass.append(f'Dialogue: 4,{ts(a)},{ts(b)},NM,,0,0,0,,{{\\an7\\pos({X0 + 3},{Y0 + 6})\\p1\\c&H000000&\\alpha&H80&\\blur12\\bord0\\shad0{ouvre}\\fad(0,250)}}{boite}{{\\p0}}')
    ass.append(f'Dialogue: 5,{ts(a)},{ts(b)},NM,,0,0,0,,{{\\an7\\pos({X0},{Y0})\\p1\\c&HFFFFFF&\\bord0\\shad0{ouvre}\\fad(0,250)}}{boite}{{\\p0}}')
    ass.append(f'Dialogue: 6,{ts(a + 0.12)},{ts(b)},NM,,0,0,0,,{{\\an4\\pos({X0 + PAD},{Y0 + HB // 2 + 2})\\c&H141414&\\fs{TN}\\clip({X0},0,{X0},{H})\\t(0,320,0.6,\\clip({X0},0,{X0 + wb},{H}))\\fad(0,250)}}{fr(nom[0])}')
    if len(nom) > 1:
        # fonction : cartouche noir translucide collé sous le blanc, qui se déroule juste après
        TQ, HQ, PQ = 40, 62, 22
        wq = int(largeur(fr(nom[1]), cfg.get('police2_fichier', 'Outfit-Bold.ttf'), TQ) + 2 * PQ)
        yq = Y0 + HB
        ouvre2 = f'\\clip({X0},0,{X0},{H})\\t(0,320,0.6,\\clip({X0},0,{X0 + wq + 4},{H}))'
        ass.append(f'Dialogue: 4,{ts(a + 0.25)},{ts(b)},NQ,,0,0,0,,{{\\an7\\pos({X0},{yq})\\p1\\c&H101010&\\alpha&H38&\\bord0\\shad0{ouvre2}\\fad(0,250)}}m 0 0 l {wq} 0 l {wq} {HQ} l 0 {HQ}{{\\p0}}')
        ass.append(f'Dialogue: 6,{ts(a + 0.35)},{ts(b)},NQ,,0,0,0,,{{\\an4\\pos({X0 + PQ},{yq + HQ // 2 + 1})\\fs{TQ}\\clip({X0},0,{X0},{H})\\t(0,320,0.6,\\clip({X0},0,{X0 + wq},{H}))\\fad(0,250)}}{fr(nom[1])}')
open(os.path.join(OUT, 'st.ass'), 'w').write('\n'.join(ass) + '\n')

# ---------- vidéo ----------
# étalonnage doux : hautes lumières retenues, contraste léger, couleurs un peu adoucies
LOOK = "curves=all='0/0.02 0.5/0.47 0.85/0.78 1/0.9',eq=contrast=1.05:saturation=0.92"
fc = []; n = len(morceaux)
fc.append(f'[0:v]split={n}' + ''.join(f'[v{k}]' for k in range(n)))
fc.append(f'[0:a]asplit={n}' + ''.join(f'[a{k}]' for k in range(n)))
for k, (t0, t1, cx, cy, h, z0, z1) in enumerate(morceaux):
    w = round(h * 9 / 16); d = t1 - t0
    x = max(0, min(1920 - w, cx - w / 2)); y = max(0, min(1080 - h, cy - h / 2))
    z = f'({z0}+({z1}-{z0})*min(t/{d:.3f},1))'
    fc.append(f'[v{k}]trim={t0}:{t1},setpts=PTS-STARTPTS,fps={FPS},crop={int(w)}:{int(h)}:{int(x)}:{int(y)},'
              f"scale=w='trunc({W}*{z}/2)*2':h='trunc({H}*{z}/2)*2':eval=frame:flags=lanczos,crop={W}:{H},"
              f'{LOOK},unsharp=5:5:0.85:5:5:0,noise=c0s=5:c0f=t,setsar=1,format=yuv420p[c{k}]')
    fc.append(f'[a{k}]atrim={t0}:{t1},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={d - 0.05:.3f}:d=0.05[s{k}]')
fc.append(''.join(f'[c{k}]' for k in range(n)) + f'concat=n={n}:v=1:a=0[fond]')
fc.append(''.join(f'[s{k}]' for k in range(n)) + f'concat=n={n}:v=0:a=1[voix0]')
# dégradés sombres discrets en haut et en bas (lisibilité du blanc), + fondu d'entrée/sortie
fc.append(f"color=black:s={W}x{H}:d={D:.3f}:r={FPS},format=rgba,"
          f"geq=r=0:g=0:b=0:a='255*(0.55*pow(max(0,1-Y/620),1.6)+0.5*pow(max(0,(Y-{H - 900})/900),1.8))'[grad]")
fc.append(f'[fond][grad]overlay=0:0:shortest=1,fade=t=in:d=0.25,fade=t=out:st={D - 0.3:.3f}:d=0.3,format=yuv420p[fond2]')
fc.append(f"[fond2]subtitles={os.path.join(OUT, 'st.ass')}:fontsdir={FONTDIR}[v]")
fc.append(f'[voix0]aformat=channel_layouts=stereo,highpass=f=70,loudnorm=I=-15:TP=-1.5:LRA=9,aresample=48000,afade=t=out:st={D - 0.3:.3f}:d=0.3,asplit[voix][sc]')
MUS = cfg.get('musique_fichier')   # WAV de composer.py ; volume en dB sous la voix (défaut -12), baisse quand elle parle
entrees = ['-i', src]
if MUS:
    entrees += ['-i', MUS]
    fc.append(f"[1:a]aresample=48000,aformat=channel_layouts=stereo,volume={cfg.get('musique_volume', -12)}dB,apad,atrim=0:{D:.3f},afade=t=out:st={D - 1.2:.3f}:d=1.2[m0]")
    fc.append('[m0][sc]sidechaincompress=threshold=0.04:ratio=4:attack=30:release=600[m1]')
    fc.append('[voix][m1]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[a]')
else:
    fc.append('[voix]anull[a]'); fc.append('[sc]anullsink')
sortie = os.path.join(OUT, 'reel.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y'] + entrees + ['-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', str(FPS),
                '-c:a', 'aac', '-b:a', '192k', '-t', f'{D:.3f}', '-movflags', '+faststart', sortie], check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', sortie, '-vf', f'fps={12 / D:.4f},scale=270:480,tile=6x2', '-frames:v', '1',
                os.path.join(OUT, 'planche.jpg')], check=True)
if os.path.getsize(sortie) > 19.5e6:
    tmp = sortie + '.tmp.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', sortie, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24',
                    '-c:a', 'copy', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, sortie)
print('OK', sortie, f'{D:.1f} s', f'{os.path.getsize(sortie) / 1e6:.1f} Mo')

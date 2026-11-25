#!/usr/bin/env python3
"""Reel d'extrait d'entretien AG+ : vidéo en couleurs naturelles, voix d'origine, sous-titres.

  python3 entretien.py plan.json [--miniature]

plan.json (voir exemple-claire-quidet.json) :
  sortie, source (extrait 1920x1080 recoupé avec marge),
  morceaux : [[t0, t1, x], ...]  secondes dans la source ; x = bord gauche du recadrage 9:16 (largeur 607)
  contexte : texte fixe à côté du logo AG+ (titre de l'émission)
  nom, qualite, t_nom : bandeau nom (gras) + qualité, qui apparaît puis disparaît
  sous_titres : [[t0, t1, ["ligne", "ligne"]], ...] relatifs au montage, **mot** surligné
  fin_texte, fin_titre, duree_fin : carte de fin rouge (logo L'Avant-Garde+ blanc)
  miniature : comme reel.py (placée sur les 2 premières images, couverture par défaut)
  titre (facultatif, déconseillé) : accroche en haut qui apparaît puis disparaît (t_ctx)
Sorties : reel.mp4, planche.jpg (une image par sous-titre), miniature.jpg, miniature-grille.jpg.
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image
ICI_AGP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI_AGP, '..', 'reels'))
import reel
from reel import W, H, FPS, css, balise, table, miniature

def rendu(pages, dossier):
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--allow-file-access-from-files'])
        pg = b.new_page(viewport={'width': W, 'height': H})
        for nom, corps in pages.items():
            f = os.path.join(dossier, 'calques', nom + '.html')
            open(f, 'w').write(f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css()}{EXTRA}</style></head><body>{corps}</body></html>')
            pg.goto('file://' + f); pg.wait_for_timeout(200)
            pg.screenshot(path=f[:-5] + '.png', omit_background=True)
            out[nom] = f[:-5] + '.png'
        b.close()
    return out

LOGOS = os.path.join(ICI_AGP, "logos") + "/"
EXTRA = """
.tete{position:absolute;left:72px;right:72px;top:150px;height:70px;display:flex;align-items:center;gap:26px}.agp{height:62px}
.ctx{font-style:italic;font-size:30px;line-height:1.25;text-shadow:0 0 20px rgba(0,0,0,.6)}.ctx b{font-weight:700}
.haut3{position:absolute;left:72px;right:72px;top:262px}
.fintitre{display:inline-block;margin-top:44px;background:#fff;color:#c41d22;font-weight:800;font-style:italic;font-size:36px;line-height:58px;padding:0 30px;text-transform:uppercase}
.haut2{position:absolute;left:190px;right:80px;top:150px;min-height:84px;display:flex;align-items:center}
.nom{position:absolute;left:0;right:0;bottom:640px;text-align:center}.lt{display:inline-block;background:#fff;color:#c41d22;font-size:36px;line-height:62px;padding:0 30px;font-weight:400}.lt b{font-weight:800;font-style:italic;margin-right:10px}.nom .bandeau{margin:0;font-size:32px;height:52px;line-height:52px;padding:0 30px}
.titre{font-weight:800;font-style:italic;font-size:64px;line-height:1.08;letter-spacing:-.03em;text-shadow:0 0 36px rgba(0,0,0,.6)}
.ombreh{position:absolute;left:0;top:0;width:1080px;height:560px;background:linear-gradient(0deg,rgba(11,11,12,0) 0,rgba(11,11,12,.35) 60%,rgba(11,11,12,.5) 100%)}
.ombre{top:1100px;height:820px;background:linear-gradient(180deg,rgba(11,11,12,0) 0,rgba(11,11,12,.45) 55%,rgba(11,11,12,.6) 100%)}
.titre{font-size:58px}
.st{position:absolute;left:90px;right:90px;bottom:430px;text-align:center}
.st .phrase{font-size:58px;line-height:1.24;text-shadow:0 0 30px rgba(0,0,0,.6),0 2px 10px rgba(0,0,0,.5)}
"""

def lut_expr(lo, hi, m=0.55):
    """Expression lutrgb : niveau auto (lo, hi) puis rampe ombre -> rouge -> lumière (comme reel.table)."""
    O, R, L = reel.OMBRE, reel.ROUGE, reel.LUM
    t = f'clip((val-{lo:.1f})/{max(hi - lo, 1):.1f},0,1)'
    ex = []
    for c in range(3):
        ex.append(f"if(lte({t},{m}),{O[c]}+({R[c]}-{O[c]})*{t}/{m},{R[c]}+({L[c]}-{R[c]})*({t}-{m})/{1 - m})")
    return ex

def niveaux(src, debut, d):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(debut + d / 2), '-i', src, '-frames:v', '1', '-vf', 'scale=480:-1,format=gray',
                          '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    g = np.frombuffer(raw, np.uint8).astype(np.float32)
    return np.percentile(g, 1), np.percentile(g, 99)

def main():
    cfg = json.load(open(sys.argv[1]))
    dossier = cfg['sortie']; os.makedirs(os.path.join(dossier, 'calques'), exist_ok=True)
    if '--miniature' in sys.argv:
        print(miniature(cfg['miniature'], dossier)); return
    src, debut, fin = cfg['source'], cfg.get('debut', 0), cfg.get('fin', 0)
    d = fin - debut
    dfin = cfg.get('duree_fin', 2.5)
    logo = open(os.path.join(reel.ICI, 'logo-ag.svg')).read()
    band = f'<div class="bandeau">{cfg["bandeau"]}</div>' if cfg.get('bandeau') else ''
    titre = '<br>'.join(balise(l) for l in cfg.get('titre', []))
    ctx = cfg.get('contexte', '')
    pages = {'haut': f'<div class="ombreh"></div><div class="ombre"></div><div class="tete"><img class="agp" src="file://{LOGOS}agplus-blanc.png"><div class="ctx">{ctx}</div></div>',
             'ctx': f'<div class="haut3"><div class="titre">{titre}</div></div>',
             'nom': f'<div class="nom"><div class="lt"><b>{cfg.get("nom", "")}</b> {cfg.get("qualite", "")}</div></div>'}
    for i, (a, b_, lignes) in enumerate(cfg['sous_titres']):
        pages[f'st{i}'] = '<div class="st"><div class="phrase">' + '<br>'.join(balise(l) for l in lignes) + '</div></div>'
    gros = logo.replace('<svg ', '<svg width="240" height="240" ', 1)
    pages['fin'] = (f'<div class="rouge"></div><div style="position:absolute;left:0;right:0;top:560px;text-align:center">'
                    f'<img src="file://{LOGOS}avantgardeplus-blanc.png" style="width:560px;margin:0 auto 80px;display:block">'
                    f'<div class="phrase" style="font-size:58px;text-shadow:none">{cfg.get("fin_texte", "")}</div>'
                    f'<div class="fintitre">{cfg.get("fin_titre", "")}</div></div>')
    png = rendu(pages, dossier)

    lh = 1080; cw = int(lh * 9 / 16)
    morceaux = cfg.get('morceaux') or [[debut, fin, cfg['x']]]
    d = sum(m[1] - m[0] for m in morceaux)
    entrees = ['-i', src]
    fc = []; n = len(morceaux)
    fc.append(f'[0:v]split={n}' + ''.join(f'[v{k}]' for k in range(n)))
    fc.append(f'[0:a]asplit={n}' + ''.join(f'[sa{k}]' for k in range(n)))
    for k, (t0, t1, x) in enumerate(morceaux):
        fc.append(f'[v{k}]trim={t0}:{t1},setpts=PTS-STARTPTS,crop={cw}:{lh}:{x}:0,scale={W}:{H}:flags=lanczos,fps={FPS},'
                  f"scale=w='{W}*if(lt(n,6),1.04-0.0066*n,1)':h='{H}*if(lt(n,6),1.04-0.0066*n,1)':eval=frame,crop={W}:{H},"
                  f"eq=contrast=1.05:saturation=0.95,setsar=1,format=rgb24[c{k}]")
        fc.append(f'[sa{k}]atrim={t0}:{t1},asetpts=PTS-STARTPTS,afade=t=in:d=0.05,afade=t=out:st={t1 - t0 - 0.08}:d=0.08[s{k}]')
    fc.append(''.join(f'[c{k}]' for k in range(n)) + f'concat=n={n}:v=1:a=0[fond]')
    fc.append(''.join(f'[s{k}]' for k in range(n)) + f'concat=n={n}:v=0:a=1[voix]')
    idx = 1
    entrees += ['-loop', '1', '-i', png['haut']]
    fc.append(f'[fond][{idx}:v]overlay=0:0:shortest=1[o{idx}]'); prev = f'o{idx}'; idx += 1
    for cle in (('ctx', 'nom') if cfg.get('titre') else ('nom',)):
        a, b_ = cfg.get('t_' + cle, [0.3, 4.5])
        entrees += ['-loop', '1', '-framerate', str(FPS), '-t', str(d), '-i', png[cle]]
        fc.append(f'[{idx}:v]format=rgba,fade=t=in:st={a}:d=0.3:alpha=1,fade=t=out:st={b_ - 0.3}:d=0.3:alpha=1[l{idx}]')
        fc.append(f"[{prev}][l{idx}]overlay=0:0:eof_action=pass:enable='between(t,{a},{b_})'[o{idx}]"); prev = f'o{idx}'; idx += 1
    for i, (a, b_, _) in enumerate(cfg['sous_titres']):
        entrees += ['-i', png[f'st{i}']]
        fc.append(f"[{prev}][{idx}:v]overlay=0:0:enable='between(t,{a},{b_})'[o{idx}]"); prev = f'o{idx}'; idx += 1
    # carte de fin
    entrees += ['-loop', '1', '-t', str(dfin), '-framerate', str(FPS), '-i', png['fin']]
    fc.append(f'[{idx}:v]format=rgb24,fps={FPS},setsar=1[fin]')
    fc.append(f'[{prev}]format=rgb24,setsar=1[corps];[corps][fin]concat=n=2:v=1:a=0,format=yuv420p[v]')
    # son : voix d'origine normalisée, fondu de sortie, silence sur la carte de fin
    fc.append(f'[voix]aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={d - 0.3}:d=0.3,apad=pad_dur={dfin}[a]')
    sortie = os.path.join(dossier, 'reel.mp4')
    cmd = ['ffmpeg', '-v', 'error', '-y'] + entrees + ['-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-r', str(FPS), '-c:a', 'aac', '-b:a', '192k',
           '-t', str(d + dfin), '-movflags', '+faststart', sortie]
    subprocess.run(cmd, check=True)
    # planche de contrôle : une image par sous-titre
    vign = []
    for a, b_, _ in cfg['sous_titres']:
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str((a + b_) / 2), '-i', sortie, '-frames:v', '1', '-vf', 'scale=270:480',
                              '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
        vign.append(Image.frombytes('RGB', (270, 480), raw))
    cols = min(len(vign), 8); rows = (len(vign) + cols - 1) // cols
    pl = Image.new('RGB', (270 * cols, 480 * rows))
    for i, v in enumerate(vign):
        pl.paste(v, ((i % cols) * 270, (i // cols) * 480))
    pl.save(os.path.join(dossier, 'planche.jpg'), quality=80)
    if cfg.get('miniature'):
        mini = miniature(cfg['miniature'], dossier)
        # miniature en tête (2 images) pour qu'elle serve de couverture par défaut
        tmp = os.path.join(dossier, 'reel-tmp.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', str(FPS), '-t', str(2 / FPS), '-i', mini,
                        '-f', 'lavfi', '-t', str(2 / FPS), '-i', 'anullsrc=r=48000:cl=stereo', '-i', sortie,
                        '-filter_complex', f'[0:v]scale={W}:{H},format=yuv420p,setsar=1[m];[2:v]setsar=1[r];[2:a]aresample=48000[ra];[m][1:a][r][ra]concat=n=2:v=1:a=1[v][a]',
                        '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-c:a', 'aac', '-b:a', '192k',
                        '-movflags', '+faststart', tmp], check=True)
        os.replace(tmp, sortie)
    print('OK', sortie, f'{d + dfin:.1f} s')

if __name__ == '__main__':
    main()

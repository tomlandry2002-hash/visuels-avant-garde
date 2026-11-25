#!/usr/bin/env python3
"""Reel vertical de L'Avant-Garde à partir d'un fichier de réglages JSON.

  python3 reel.py plan.json

Produit, dans le dossier de sortie du JSON : reel-muet.mp4, musique.wav, reel.mp4 (avec musique)
et planche.jpg (une image par plan, pour le contrôle). Voir exemple-nvidia.json.

Style : bichromie rouge et noir, bandeaux blancs à texte rouge, mots surlignés (**mot**),
lignes qui apparaissent sur les temps, coupes calées sur les mesures de la musique.
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
POLICES = '/usr/share/fonts/truetype/google-fonts/'
CACHE = os.path.expanduser('~/.cache/poppins/')

# ---------------------------------------------------------------- bichromie
OMBRE, ROUGE, LUM = np.array((11, 11, 12)), np.array((196, 29, 34)), np.array((255, 217, 214))

def table(m=0.55):
    t = np.arange(256) / 255
    return np.where(t[:, None] <= m, OMBRE + (ROUGE - OMBRE) * (t[:, None] / m),
                    ROUGE + (LUM - ROUGE) * ((t[:, None] - m) / (1 - m))).round().astype(np.uint8)

def bichro(gris, lut, lo=None, hi=None):
    g = gris.astype(np.float32)
    if lo is None:
        lo, hi = np.percentile(g, 1), np.percentile(g, 99)
    return lut[np.clip((g - lo) * 255 / max(hi - lo, 1), 0, 255).astype(np.uint8)], lo, hi

# ---------------------------------------------------------------- calques de texte
def police_extra():
    f = CACHE + 'Poppins-ExtraBoldItalic.ttf'
    if not os.path.exists(f):
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(['curl', '-sSLo', f, 'https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-ExtraBoldItalic.ttf'], check=True)
    return f

def css():
    return f"""
@font-face{{font-family:P;src:url(file://{POLICES}Poppins-Regular.ttf);font-weight:400}}
@font-face{{font-family:P;src:url(file://{POLICES}Poppins-Bold.ttf);font-weight:700}}
@font-face{{font-family:P;src:url(file://{police_extra()});font-weight:800;font-style:italic}}
@font-face{{font-family:P;src:url(file://{POLICES}Poppins-Italic.ttf);font-weight:400;font-style:italic}}
*{{margin:0;padding:0}}html,body{{background:transparent}}
body{{width:1080px;height:1920px;position:relative;overflow:hidden;font-family:P;color:#fff}}
.ombre{{position:absolute;left:0;top:820px;width:1080px;height:1100px;background:linear-gradient(180deg,rgba(11,11,12,0) 0,rgba(11,11,12,.5) 40%,rgba(11,11,12,.85) 100%)}}
.rouge{{position:absolute;inset:0;background:linear-gradient(160deg,#c41d22,#dc2a2a)}}
.logo{{position:absolute;left:72px;top:150px;width:84px;height:84px}}.logo svg{{width:84px;height:84px}}
.bloc{{position:absolute;left:100px;right:90px;bottom:430px}}.bloc.haut{{bottom:auto;top:620px}}
.bandeau{{display:inline-block;height:58px;padding:0 40px;margin-bottom:30px;background:#fff;color:#c41d22;font-weight:800;font-style:italic;font-size:38px;line-height:58px;text-transform:uppercase}}
.l{{display:block}}.cache{{visibility:hidden}}
.phrase{{font-size:72px;line-height:1.24;letter-spacing:-.02em;text-shadow:0 0 40px rgba(0,0,0,.55),0 2px 12px rgba(0,0,0,.4)}}
.formule{{font-weight:800;font-style:italic;letter-spacing:-.03em;line-height:1.04;text-shadow:0 0 40px rgba(0,0,0,.5)}}
.h{{background:#fff;color:#c41d22;font-weight:700;padding:0 14px;text-shadow:none}}
.formule .h{{font-weight:800}}
.sous{{font-style:italic;font-size:38px;line-height:1.3;margin-top:28px}}
"""

def balise(s):
    """**mot** devient un surlignage blanc à texte rouge."""
    out, ouvert = '', False
    for i, morceau in enumerate(s.split('**')):
        out += morceau if i == 0 else (('</span>' if ouvert else '<span class="h">') + morceau)
        if i: ouvert = not ouvert
    return out

def calques(plans, dossier):
    from playwright.sync_api import sync_playwright
    logo = open(os.path.join(ICI, 'logo-ag.svg')).read()
    style = css()
    pages = {}
    for k, p in enumerate(plans):
        fond = '<div class="rouge"></div>' if p['type'] in ('aplat', 'fin') else '<div class="ombre"></div>'
        if p['type'] == 'fin':
            gros = logo.replace('<svg ', '<svg width="240" height="240" ', 1)
            texte = p.get('texte', 'Lire l’article sur<br><b>lavantgarde.fr</b>')
            pages[k] = [f'{fond}<div style="position:absolute;left:0;right:0;top:600px;text-align:center"><div style="width:240px;height:240px;margin:0 auto 70px">{gros}</div><div class="phrase" style="font-size:66px;text-shadow:none">{texte}</div></div>']
            continue
        lignes = [balise(l) for l in p['lignes']]
        classe = 'formule' if p.get('style') == 'formule' else 'phrase'
        taille = f'style="font-size:{p["taille"]}px"' if p.get('taille') else ''
        band = f'<div class="bandeau">{p["bandeau"]}</div>' if p.get('bandeau') else ''
        sous = p.get('sous', '')
        etats = []
        n = len(lignes) + (1 if sous else 0)
        for v in range(1, n + 1):
            corps = ''.join(f'<span class="l{"" if i < v else " cache"}">{l}</span>' for i, l in enumerate(lignes))
            s = f'<div class="sous{"" if v > len(lignes) else " cache"}">{sous}</div>' if sous else ''
            pos = ' haut' if p.get('position') == 'haut' or p['type'] == 'aplat' else ''
            etats.append(f'{fond}<div class="logo">{logo}</div><div class="bloc{pos}">{band}<div class="{classe}" {taille}>{corps}</div>{s}</div>')
        pages[k] = etats
    os.makedirs(os.path.join(dossier, 'calques'), exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--allow-file-access-from-files'])
        pg = b.new_page(viewport={'width': W, 'height': H})
        for k, etats in pages.items():
            for i, corps in enumerate(etats):
                f = os.path.join(dossier, 'calques', f'{k}-{i}.html')
                open(f, 'w').write(f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{style}</style></head><body>{corps}</body></html>')
                pg.goto('file://' + f); pg.wait_for_timeout(250)
                pg.screenshot(path=f[:-5] + '.png', omit_background=True)
        b.close()
    return {k: len(v) for k, v in pages.items()}

# ---------------------------------------------------------------- images de fond
def punch(img, i, n=7, z=1.07):
    if i >= n: return img
    s = z - (z - 1) * (i / n)
    w, h = int(W / s), int(H / s); x, y = (W - w) // 2, (H - h) // 2
    return np.asarray(Image.fromarray(img).crop((x, y, x + w, y + h)).resize((W, H), Image.BILINEAR))

def fond_video(p, d, lut):
    src = p['source']
    lh = int(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                             '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.split(',')[1])
    cw = int(lh * 9 / 16)
    x = p.get('x', None)
    crop = f'crop={cw}:{lh}:{x}:0' if x is not None else f'crop={cw}:{lh}'
    cmd = ['ffmpeg', '-v', 'error', '-ss', str(p.get('debut', 0)), '-t', str(d), '-i', src, '-vf',
           f'{crop},scale={W}:{H}:flags=lanczos,fps={FPS},format=gray', '-f', 'rawvideo', '-']
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (W * H)
    fr = np.frombuffer(raw, np.uint8)[:n * W * H].reshape(n, H, W)
    lo = hi = None
    for i in range(int(round(d * FPS))):
        rgb, lo, hi = bichro(fr[min(i, n - 1)], lut, lo, hi)
        yield punch(rgb, i)

def fond_photo(p, d, lut, zfin=1.06):
    im = Image.open(p['source']).convert('L')
    if p.get('boite'):
        im = im.crop(tuple(p['boite']))
    else:  # recadrage 9:16 centré (ou centré sur p['centre_x'])
        cw = int(im.height * 9 / 16)
        if cw <= im.width:
            cx = p.get('centre_x', im.width // 2)
            x0 = min(max(cx - cw // 2, 0), im.width - cw); im = im.crop((x0, 0, x0 + cw, im.height))
        else:
            ch = int(im.width * 16 / 9); im = im.crop((0, 0, im.width, min(ch, im.height)))
    big = Image.fromarray(bichro(np.asarray(im.resize((int(W * zfin) + 2, int(H * zfin) + 2), Image.LANCZOS)), lut)[0])
    N = int(round(d * FPS))
    for i in range(N):
        s = 1 + (zfin - 1) * i / N
        sm = big.resize((int(big.width / zfin * s), int(big.height / zfin * s)), Image.BILINEAR)
        x, y = (sm.width - W) // 2, (sm.height - H) // 2
        yield punch(np.asarray(sm.crop((x, y, x + W, y + H))), i)

def fond_uni(d):
    for _ in range(int(round(d * FPS))):
        yield np.zeros((H, W, 3), np.uint8)

# ---------------------------------------------------------------- principal
def main():
    cfg = json.load(open(sys.argv[1]))
    dossier = cfg.get('sortie', os.path.dirname(os.path.abspath(sys.argv[1])))
    os.makedirs(dossier, exist_ok=True)
    mus = cfg.get('musique', {})
    temps = 60 / mus.get('bpm', 120)
    plans = cfg['plans']
    durees = [p.get('mesures', 2 if p['type'] != 'fin' else 1.5) * 4 * temps for p in plans]
    nb = calques(plans, dossier)
    lut = table(cfg.get('milieu', 0.55))
    sortie = os.path.join(dossier, 'reel-muet.mp4')
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', sortie], stdin=subprocess.PIPE)
    vignettes = []
    for k, (p, d) in enumerate(zip(plans, durees)):
        n_etats = nb[k]
        pas = p.get('rythme', 2 * temps / 2)  # une ligne par temps par défaut
        tops = p.get('apparitions') or [i * pas for i in range(n_etats)]
        cal = []
        for i in range(n_etats):
            a = np.asarray(Image.open(os.path.join(dossier, 'calques', f'{k}-{i}.png')).convert('RGBA')).astype(np.float32)
            cal.append((a[..., :3], a[..., 3:] / 255))
        gen = fond_video(p, d, lut) if p['type'] == 'video' else fond_photo(p, d, lut) if p['type'] == 'photo' else fond_uni(d)
        total = int(round(d * FPS))
        for i, fr in enumerate(gen):
            e = max(j for j, s in enumerate(tops) if i / FPS >= s)
            c, al = cal[e]
            out = (fr.astype(np.float32) * (1 - al) + c * al).astype(np.uint8)
            if i == total - 1:
                vignettes.append(Image.fromarray(out).resize((270, 480)))
            enc.stdin.write(out.tobytes())
    enc.stdin.close(); enc.wait()
    planche = Image.new('RGB', (270 * len(vignettes), 480))
    for i, v in enumerate(vignettes):
        planche.paste(v, (i * 270, 0))
    planche.save(os.path.join(dossier, 'planche.jpg'), quality=80)
    # musique
    sections = [{'debut': sum(durees[:k]), 'duree': d, 'energie': p.get('energie', 'groove'), 'impact': p.get('impact', False),
                 'apparitions': [sum(durees[:k]) + t for t in (p.get('apparitions') or [])]} for k, (p, d) in enumerate(zip(plans, durees))]
    wav = os.path.join(dossier, 'musique.wav')
    subprocess.run([sys.executable, os.path.join(ICI, 'musique.py'), '--sortie', wav, '--reglages', json.dumps(mus),
                    '--sections', json.dumps(sections)], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', sortie, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac',
                    '-b:a', '192k', '-shortest', '-movflags', '+faststart', os.path.join(dossier, 'reel.mp4')], check=True)
    print(f'OK : {os.path.join(dossier, "reel.mp4")} ({sum(durees):.1f} s), planche.jpg à regarder')

if __name__ == '__main__':
    main()

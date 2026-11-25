#!/usr/bin/env python3
"""Musique originale des reels de L'Avant-Garde, calée sur les plans du montage.

Appelée par reel.py. Réglages (clé "musique" du JSON du reel), tous facultatifs :
  bpm        tempo (120)
  accords    liste d'accords en notes MIDI, un par mesure, en boucle ([[57,60,64],[53,57,60],[48,52,55],[55,59,62]] : la m, fa, do, sol)
  basse      fondamentales MIDI de la basse, une par mesure ([33,29,36,31])
  graine     variation aléatoire des sons (3)
  gains      {"drums":1,"bass":1,"pad":1,"arp":1,"fx":1} pour doser chaque piste
Les sections (énergie de chaque plan : intro, groove, plein, creux, fin ; impact oui/non) viennent du montage.
La patte musicale validée par Tom est décrite dans references/patte-musicale.md de la skill reels-avant-garde.
"""
import argparse, json, wave
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

a = argparse.ArgumentParser()
a.add_argument('--sortie', required=True)
a.add_argument('--reglages', default='{}')
a.add_argument('--sections', required=True)
a = a.parse_args()
R = json.loads(a.reglages); SECT = json.loads(a.sections)

SR = 48000
BPM = R.get('bpm', 120); BEAT = 60 / BPM; BAR = 4 * BEAT
ACC = R.get('accords', [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]])
BASSE = R.get('basse', [33, 29, 36, 31])
G = {'drums': 1, 'bass': 1, 'pad': 1, 'arp': 1, 'fx': 1, **R.get('gains', {})}
DUR = SECT[-1]['debut'] + SECT[-1]['duree']
N = int(SR * DUR)
rng = np.random.default_rng(R.get('graine', 3))
pistes = {k: np.zeros((N, 2)) for k in G}

def section(t):
    for s in SECT:
        if s['debut'] <= t < s['debut'] + s['duree']:
            return s['energie']
    return 'fin'

def place(piste, sig, t, g=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= N or i < 0: return
    if sig.ndim == 1:
        sig = np.stack([sig * (1 - max(pan, 0)), sig * (1 + min(pan, 0))], 1)
    s = sig[:N - i] * g
    pistes[piste][i:i + len(s)] += s

def env(n, att, dec, sus=0.0, rel=None):
    t = np.arange(n) / SR
    e = np.minimum(t / max(att, 1e-4), 1) * (sus + (1 - sus) * np.exp(-t / dec))
    if rel:
        k = min(int(rel * SR), n); e[-k:] *= np.linspace(1, 0, k)
    return e

def lp(x, f, o=2): return sosfilt(butter(o, min(f, SR / 2 - 100), 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)

def saw(f, n, det=(0,)):
    t = np.arange(n) / SR; out = np.zeros(n)
    for d in det:
        ff = f * 2 ** (d / 1200); ph = rng.random() * 2 * np.pi
        for k in range(1, int(9000 / ff) + 1):
            out += np.sin(2 * np.pi * k * ff * t + k * ph) / k
    return out / len(det) * 0.6

def hz(m): return 440 * 2 ** ((m - 69) / 12)

# ---------- batterie
def kick():
    n = int(0.5 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.035)
    k = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.22)
    return np.tanh((k + hp(rng.standard_normal(n), 3000) * env(n, 0.0005, 0.004) * 0.3) * 1.6)

def clap():
    n = int(0.45 * SR)
    x = sosfilt(butter(2, [900, 4500], 'band', fs=SR, output='sos'), rng.standard_normal(n))
    e = np.zeros(n)
    for d in (0, 0.011, 0.022):
        i = int(d * SR); e[i:] += env(n - i, 0.0005, 0.012 if d < .02 else 0.16)
    return x * e * 0.9 + np.sin(2 * np.pi * 190 * np.arange(n) / SR) * env(n, 0.001, 0.05) * 0.4

def hat(ouvert=False):
    n = int((0.35 if ouvert else 0.08) * SR)
    return hp(rng.standard_normal(n), 7000, 4) * env(n, 0.0005, 0.12 if ouvert else 0.018)

K, C, Hh, O = kick(), clap(), hat(), hat(True)
nb = int(DUR / BEAT) + 1
for b in range(nb * 2):
    t = b * BEAT / 2; sec = section(t); pos = b % 8
    swing = 0.018 if b % 2 else 0
    if sec == 'fin' and pos != 0: continue
    if sec == 'intro':
        if pos == 0 and (t % (2 * BAR)) >= BAR: place('drums', K, t, 0.7)  # kick seul à la 2e mesure de l'intro
        continue
    if pos in (0, 4) or (sec == 'plein' and pos == 3) or (sec == 'groove' and pos == 3 and (b // 8) % 2):
        place('drums', K, t, 0.7)
    if pos in (2, 6) and sec in ('groove', 'plein'):
        place('drums', C, t, 0.5)
    if sec in ('groove', 'plein'):
        place('drums', Hh, t + swing, 0.32 if pos % 2 == 0 else 0.2, pan=0.3)
        if pos == 7 and (b // 8) % 2: place('drums', O, t + swing, 0.16, pan=0.3)
    if sec == 'creux' and pos % 2 == 1:
        place('drums', Hh, t + swing, 0.12, pan=0.3)
# roulement de clap la demi-mesure avant chaque passage en « plein »
for s0, s1 in zip(SECT, SECT[1:]):
    if s1['energie'] == 'plein' and s0['energie'] != 'plein':
        for i in range(8):
            place('drums', C, s1['debut'] - BAR / 2 + i * BEAT / 4, 0.15 + 0.05 * i)

# ---------- basse filtrée
for b in range(nb * 2):
    t = b * BEAT / 2; sec = section(t)
    if sec in ('intro', 'fin'): continue
    bar = int(t // BAR) % len(BASSE)
    note = BASSE[bar] + (12 if b % 4 == 3 else 0)
    n = int(BEAT / 2 * SR * 0.92)
    s = saw(hz(note), n, (-6, 6)); tt = np.arange(n) / SR
    cut = 180 + (900 if sec == 'plein' else 500) * np.exp(-tt / 0.06)
    out = np.zeros(n)
    for sl in np.array_split(np.arange(n), 6):
        out[sl] = lp(s, cut[sl[0]], 2)[sl]
    place('bass', out * env(n, 0.003, 0.25, 0.6, 0.01), t, 0.85 if sec != 'creux' else 0.45)

# ---------- nappe
for m in range(int(np.ceil(DUR / BAR))):
    t = m * BAR; sec = section(t)
    n = min(int(BAR * SR * (1.6 if sec == 'fin' else 1.02)), N - int(t * SR))
    if n <= 0: break
    ch = sum(saw(hz(x), n, (-9, 0, 9)) for x in ACC[m % len(ACC)])
    ch = lp(ch, {'intro': 900, 'plein': 2400}.get(sec, 1600), 2) * env(n, 0.25, 9, 1, 0.3)
    place('pad', np.stack([lp(ch, 1500) * 0.98, ch], 1), t, 0.36)

# ---------- arpège pincé
motif = [0, 1, 2, 1, 2, 0, 1, 2]
for b in range(nb * 4):
    t = b * BEAT / 4; sec = section(t)
    if sec not in ('intro', 'plein', 'creux'): continue
    if sec == 'creux' and b % 2: continue
    note = ACC[int(t // BAR) % len(ACC)][motif[b % 8]] + 12
    n = int(0.22 * SR)
    s = lp(saw(hz(note), n, (-4, 4)), 2600 if sec == 'plein' else 1500) * env(n, 0.002, 0.07)
    place('arp', s, t, 1.0 if sec != 'creux' else 0.7, pan=(-0.35 if b % 2 else 0.35))

# ---------- effets
def montee(d):
    n = int(d * SR); t = np.arange(n) / SR; x = rng.standard_normal(n + 2000); out = np.zeros(n)
    for sl in np.array_split(np.arange(n), 40):
        out[sl] = lp(x[sl[0]:sl[-1] + 2000], 400 + 9000 * (sl[0] / n) ** 2)[:len(sl)]
    return out * (t / d) ** 2

def impact():
    n = int(2.5 * SR); t = np.arange(n) / SR
    f = 36 + 70 * np.exp(-t / 0.1)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.7) + lp(rng.standard_normal(n), 2500) * env(n, 0.001, 0.25) * 0.4

if SECT[0]['energie'] == 'intro' and len(SECT) > 1:
    place('fx', montee(min(2.0, SECT[0]['duree'] / 2)), SECT[1]['debut'] - min(2.0, SECT[0]['duree'] / 2), 0.25)
for s in SECT[1:]:
    if s['impact'] or s['energie'] == 'fin':
        place('fx', impact(), s['debut'], 0.75)
        if s['energie'] == 'plein':
            place('fx', montee(1.0), s['debut'] - 1.0, 0.2)
    elif s['energie'] != 'intro':
        place('fx', impact(), s['debut'], 0.35)

# ---------- mixage : pompe, réverbération, saturation douce
t = np.arange(N) / SR
pompe = np.ones(N)
for b in range(nb):
    tb = b * BEAT
    if section(tb) in ('groove', 'plein', 'creux'):
        i = int(tb * SR); k = min(int(0.3 * SR), N - i)
        if k > 0:
            pompe[i:i + k] = np.minimum(pompe[i:i + k], 1 - 0.55 * np.exp(-np.arange(k) / SR / 0.09))
pistes['pad'] *= pompe[:, None]; pistes['arp'] *= pompe[:, None]; pistes['bass'] *= (0.5 + 0.5 * pompe)[:, None]
for k in pistes: pistes[k] *= G[k]

def reverb(x, d=2.2):
    n = int(d * SR); tt = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-tt / (d / 6.9))[:, None]
    ir = np.stack([lp(ir[:, 0], 6000), lp(ir[:, 1], 6000)], 1); ir /= np.sqrt((ir ** 2).sum(0))
    return np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1)

envoi = pistes['pad'] + pistes['arp'] + pistes['drums'] * 0.25
mix = pistes['drums'] + pistes['bass'] + pistes['fx'] * 0.8 + pistes['pad'] + pistes['arp'] + reverb(envoi) * 0.35
mix = np.stack([hp(mix[:, 0], 30), hp(mix[:, 1], 30)], 1)
mix *= (np.clip((DUR - t) / 1.5, 0, 1) * np.minimum(t / 0.05, 1))[:, None]
mix = np.tanh(mix / np.abs(mix).max() * 1.25) / np.tanh(1.25) * 0.93
with wave.open(a.sortie, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print('Musique :', a.sortie)

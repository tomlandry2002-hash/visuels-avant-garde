#!/usr/bin/env python3
"""Musique de fond jouée par de vrais instruments échantillonnés (soundfont GeneralUser GS, FluidSynth).
Écrit une partition MIDI selon une ambiance, puis la rend en WAV 48 kHz.

  python3 composer.py AMBIANCE DUREE sortie.wav [--graine N]

Ambiances :
  grave     piano feutré et cordes tenues, ré mineur, 68 bpm (sujets lourds : jeunesse sacrifiée, inégalités)
  tendu     ostinato de cordes, pulsation sourde, piano en octaves, la mineur, 96 bpm (prix, profits, RN)
  elan      piano en arpèges, cordes qui montent, batterie légère, do majeur, 104 bpm (mobilisation, espoir)
La forme évolue sur la durée (entrée, développement, sommet, retombée) pour éviter l'effet boucle.
Soundfont : variable SOUNDFONT ou /home/claude/sf/gugs/GeneralUser-GS.sf2 (licence libre)
(dépôt https://github.com/mrbumpy409/GeneralUser-GS, git clone --depth 1). Paquets : mido, fluidsynth (apt).
"""
import argparse, os, random, subprocess, tempfile
import mido

ap = argparse.ArgumentParser()
ap.add_argument('ambiance'); ap.add_argument('duree', type=float); ap.add_argument('sortie')
ap.add_argument('--graine', type=int, default=7)
a = ap.parse_args()
random.seed(a.graine)
SF = os.environ.get('SOUNDFONT', '/home/claude/sf/gugs/GeneralUser-GS.sf2')
TPB = 480

NOTES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
def n(nom, octave):  # 'Bb', 3 -> numéro MIDI
    v = NOTES[nom[0]] + (1 if '#' in nom else 0) - (1 if 'b' in nom[1:] else 0)
    return 12 * (octave + 1) + v
def accord(fond, qualite, octave):
    r = n(fond, octave)
    return [r, r + (3 if qualite == 'm' else 4), r + 7]

AMB = {
    'grave': dict(bpm=68, prog=[('D', 'm'), ('Bb', ''), ('F', ''), ('C', ''), ('D', 'm'), ('G', 'm'), ('Bb', ''), ('A', '')]),
    'tendu': dict(bpm=96, prog=[('A', 'm'), ('A', 'm'), ('F', ''), ('F', ''), ('C', ''), ('C', ''), ('G', ''), ('E', '')]),
    'elan':  dict(bpm=104, prog=[('C', ''), ('G', ''), ('A', 'm'), ('F', ''), ('C', ''), ('G', ''), ('F', ''), ('G', '')]),
}[a.ambiance]
bpm = AMB['bpm']; spb = 60 / bpm
mesure = 4 * spb
nb = int(a.duree / mesure) + 2          # nombre de mesures (une par accord)
total_ticks = nb * 4 * TPB

ev = {}  # canal -> liste (tick, type, note, vel)
def note(ch, t_beats, dur_beats, p, vel):
    j = random.uniform(-0.02, 0.02) if ch != 9 else random.uniform(-0.01, 0.01)
    t0 = max(0, int((t_beats + j) * TPB)); t1 = max(t0 + 10, int((t_beats + dur_beats) * TPB))
    vel = max(1, min(127, int(vel + random.uniform(-7, 7))))
    ev.setdefault(ch, []).append((t0, 'note_on', p, vel)); ev[ch].append((t1, 'note_off', p, 0))
def cc(ch, t_beats, num, val):
    ev.setdefault(ch, []).append((int(t_beats * TPB), 'cc', num, int(val)))

def phase(m):  # intensité 0..1 selon la forme : entrée, développement, sommet, retombée
    x = m / max(1, nb - 1)
    return 0.35 + 0.65 * min(1, x / 0.6) if x < 0.85 else 1 - (x - 0.85) * 3

instruments = {}
if a.ambiance == 'grave':
    instruments = {0: 0, 1: 49, 2: 42}           # piano, cordes lentes, violoncelle
    for m in range(nb):
        f, q = AMB['prog'][m % len(AMB['prog'])]; I = phase(m); b0 = m * 4
        ac = accord(f, q, 3)
        # piano : accord brisé lent + note aiguë qui chante une mesure sur deux
        for k, p in enumerate([ac[0] - 12, ac[1], ac[2], ac[0] + 12]):
            note(0, b0 + k * 0.75, 3.2 - k * 0.6, p, 48 + 18 * I)
        if m % 2 == 1 or I > 0.7:
            mel = random.choice([ac[1] + 12, ac[2] + 12, ac[0] + 24])
            note(0, b0 + 2.5, 1.5, mel, 52 + 16 * I)
        # cordes : accord tenu, crescendo par mesure
        for p in ac: note(1, b0, 4, p, 60)
        cc(1, b0, 11, 40 + 70 * I); cc(1, b0 + 2, 11, 50 + 75 * I)
        if m >= 1: note(2, b0, 4, ac[0] - 12, 55 + 20 * I)
    cc(1, 0, 7, 92); cc(2, 0, 7, 80); cc(0, 0, 7, 100)
elif a.ambiance == 'tendu':
    instruments = {0: 0, 1: 48, 2: 44, 3: 33}    # piano, cordes, cordes trémolo, basse
    for m in range(nb):
        f, q = AMB['prog'][m % len(AMB['prog'])]; I = phase(m); b0 = m * 4
        ac = accord(f, q, 3)
        # ostinato de croches piquées (cordes)
        motif = [ac[0], ac[0] + 12, ac[1] + 12, ac[0] + 12, ac[2], ac[0] + 12, ac[1] + 12, ac[2] + 12]
        for k, p in enumerate(motif):
            note(1, b0 + k * 0.5, 0.22, p, (58 if k % 2 == 0 else 46) + 22 * I)
        # basse : noires sourdes
        for k in range(4): note(3, b0 + k, 0.8, ac[0] - 24, 70 + 20 * I)
        # piano en octaves, sur le premier temps une mesure sur deux
        if m % 2 == 0: note(0, b0, 3.5, ac[0], 64 + 16 * I); note(0, b0, 3.5, ac[0] + 12, 60 + 16 * I)
        if I > 0.75:   # sommet : trémolo aigu
            for p in ac: note(2, b0, 4, p + 12, 50 + 20 * I)
        # pulsation : grosse caisse feutrée et toms graves
        if m >= 1:
            for k in range(4): note(9, b0 + k, 0.2, 36, 58 + 22 * I)
            if I > 0.6: note(9, b0 + 3.5, 0.2, 41, 56)
    cc(1, 0, 7, 96); cc(3, 0, 7, 92); cc(0, 0, 7, 92); cc(2, 0, 7, 70); cc(9, 0, 7, 82)
else:  # elan
    instruments = {0: 0, 1: 48, 3: 33}
    for m in range(nb):
        f, q = AMB['prog'][m % len(AMB['prog'])]; I = phase(m); b0 = m * 4
        ac = accord(f, q, 4)
        arp = [ac[0], ac[1], ac[2], ac[1] + 12, ac[2], ac[1], ac[0] + 12, ac[2]]
        for k, p in enumerate(arp): note(0, b0 + k * 0.5, 0.6, p, 54 + 18 * I)
        for p in accord(f, q, 3): note(1, b0, 4, p, 50 + 30 * I)
        note(3, b0, 1.5, ac[0] - 24, 72); note(3, b0 + 2, 1.5, ac[0] - 24, 66); note(3, b0 + 3.5, 0.5, ac[2] - 24, 62)
        if m >= 2:
            for k in range(4): note(9, b0 + k, 0.2, 36 if k % 2 == 0 else 38, (60 if k % 2 == 0 else 46) + 20 * I)
            for k in range(8): note(9, b0 + k * 0.5, 0.1, 42, 34 + 14 * I)
    cc(1, 0, 7, 84); cc(3, 0, 7, 90); cc(0, 0, 7, 100); cc(9, 0, 7, 72)

mid = mido.MidiFile(ticks_per_beat=TPB)
tr0 = mido.MidiTrack(); mid.tracks.append(tr0)
tr0.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))
for ch, liste in ev.items():
    tr = mido.MidiTrack(); mid.tracks.append(tr)
    if ch != 9: tr.append(mido.Message('program_change', channel=ch, program=instruments.get(ch, 0), time=0))
    tr.append(mido.Message('control_change', channel=ch, control=91, value=70, time=0))  # réverbération
    liste.sort(key=lambda e: (e[0], e[1] == 'note_on'))
    t = 0
    for tick, typ, x, y in liste:
        if tick > total_ticks: continue
        d = tick - t; t = tick
        if typ == 'cc': tr.append(mido.Message('control_change', channel=ch, control=x, value=max(0, min(127, y)), time=d))
        else: tr.append(mido.Message(typ, channel=ch, note=x, velocity=y, time=d))
tmp = tempfile.mkdtemp()
mf = os.path.join(tmp, 'm.mid'); mid.save(mf)
brut = os.path.join(tmp, 'brut.wav')
subprocess.run(['fluidsynth', '-ni', '-q', '-g', '0.7', '-r', '48000', '-R', '1', '-C', '1',
                '-o', 'synth.reverb.room-size=0.75', '-o', 'synth.reverb.level=0.6', '-F', brut, SF, mf],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
# mise en forme : fondu d'entrée, coupe à la durée avec fondu de sortie, égalisation douce, normalisation
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', brut, '-af',
                f'atrim=0:{a.duree:.3f},afade=t=in:d=0.6,afade=t=out:st={a.duree - 1.5:.3f}:d=1.5,'
                'highpass=f=40,equalizer=f=2500:t=q:w=1:g=-3,loudnorm=I=-18:TP=-2,aresample=48000', a.sortie], check=True)
print('OK', a.sortie)

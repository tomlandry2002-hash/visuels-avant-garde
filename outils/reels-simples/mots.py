#!/usr/bin/env python3
"""Affiche les mots horodatés d'une transcription entre deux instants (secondes de l'émission).
python3 mots.py transcription.jsonl 536 602"""
import json, sys
f, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
ws = [w for l in open(f) for w in json.loads(l)['w'] if a <= w[0] <= b]
print(' '.join(f"{w[2].strip()}|{w[0]:.2f}" for w in ws))

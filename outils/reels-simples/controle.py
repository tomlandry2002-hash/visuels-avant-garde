#!/usr/bin/env python3
"""Assemble les planche.jpg de plusieurs reels en images de contrôle (5 reels par image).
python3 controle.py sortie_prefixe dossier_reel1 dossier_reel2 ..."""
import sys
from PIL import Image
pre, ds = sys.argv[1], sys.argv[2:]
ims = [Image.open(f'{d}/planche.jpg').resize((810, 480)) for d in ds]
for k in range(0, len(ims), 5):
    sel = ims[k:k + 5]; c = Image.new('RGB', (1620, 480 * 3))
    for i, im in enumerate(sel): c.paste(im, ((i % 2) * 810, (i // 2) * 480))
    c.save(f'{pre}{k // 5}.jpg', quality=80); print(f'{pre}{k // 5}.jpg')

# Outils des reels de L'Avant-Garde

- `reel.py plan.json` : monte le reel (bichromie rouge et noir, bandeaux, surlignages, apparitions sur les temps) et y pose la musique. Sorties : `reel.mp4`, `reel-muet.mp4`, `musique.wav`, `planche.jpg`.
- `reel.py plan.json --miniature` : refait seulement la miniature (`miniature.jpg` 1080 × 1920, et `miniature-grille.jpg`, son recadrage 4:5 tel que la grille du profil le montre). Avec une clé `miniature` dans le JSON, le montage complet la fabrique aussi et la place sur les deux premières images de la vidéo, pour qu'elle serve de couverture.
- `musique.py` : la musique originale, appelée par `reel.py`, réglages dans la clé `musique` du JSON.
- `exemple-nvidia.json` : le reel du 25 novembre 2026, modèle de fichier de réglages.
- `patte-musicale.md` : le carnet de la patte musicale, à mettre à jour à chaque retour de Tom.
- `logo-ag.svg` : le logo AG.

Dépendances : Python 3 avec numpy, scipy, Pillow, Playwright ; Chrome (/usr/bin/google-chrome) ; ffmpeg. Police Poppins (ExtraBold Italic téléchargée au besoin).

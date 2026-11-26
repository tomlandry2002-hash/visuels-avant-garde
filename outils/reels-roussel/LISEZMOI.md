# Reels Roussel

Chaîne de montage des reels tirés des émissions de Fabien Roussel (compte Instagram de l'espace Publer C).

- `plans.py extrait.mp4 planche.jpg` : découpe l'extrait en plans (seuil de scène 0,1) et repère les visages ; planche annotée.
- `mots.py transcription.jsonl début fin` : mots horodatés d'un passage, pour placer les coupes et les corrections.
- `ajuster.py plan.json` : recentre chaque morceau sur le visage le plus proche du cx prévu, au-dessus des bandeaux et hors du logo.
- `monter.py plan.json` : monte le reel (charte validée le 26 novembre 2026). Il allonge seul les coupes pour ne jamais couper un mot, et réencode sous 20 Mo (limite jsDelivr).
- `controle.py prefixe dossier1 dossier2 …` : assemble les planches de contrôle, 5 reels par image.
- `journal-horaires.md` : une ligne par reel programmé, et les analyses d'horaires.

Modèle de plan : `exemple-sans-papiers.json`. Dépendances : ffmpeg, Pillow, opencv-python-headless (`haar.xml` fourni).

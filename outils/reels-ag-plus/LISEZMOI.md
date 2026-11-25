# Outils des reels AG+ (extraits d'entretiens de L'Avant-Garde Plus)

- `transcrire.py audio.mp3 transcription.jsonl` : transcription horodatée au mot (faster-whisper `small`, français). Environ 11 minutes pour une heure d'émission sur 2 cœurs. Dépendance : `pip install faster-whisper` (le décodage passe par ffmpeg, pas par PyAV).
- `sous_titres.py transcription.jsonl DEBUT FIN --decalage D` : brouillon de sous-titres d'un passage, à reprendre à la main.
- `entretien.py plan.json` : monte le reel (couleurs naturelles, voix d'origine normalisée, logo AG+ et titre de l'émission fixes en haut, bandeau nom et qualité qui apparaît puis disparaît, sous-titres surlignés, carte de fin rouge L'Avant-Garde+, miniature en tête). Réutilise `../reels/reel.py` (polices, surlignage, miniature) sans le modifier.
- `exemple-claire-quidet.json` : le premier reel AG+ (25 novembre 2026), modèle de fichier de réglages.
- `logos/` : AG+ blanc, L'Avant-Garde+ blanc, L'Avant-Garde+ blanc et rouge.

Dépendances : celles de `../reels/` (Python 3, numpy, Pillow, Playwright, Chrome, ffmpeg, Poppins) et faster-whisper.

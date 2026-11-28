#!/bin/bash
# Installe la boîte à outils « reels simples » dans le conteneur, sans compte GitHub (dépôt public).
#   bash installer.sh [dossier]   (défaut /home/claude/reels-simples)
set -e
D=${1:-/home/claude/reels-simples}; B=https://raw.githubusercontent.com/tomlandry2002-hash/visuels-avant-garde/main/outils/reels-simples
mkdir -p "$D/polices"
for f in monter.py composer.py transcrire.py mots.py plans.py controle.py haar.xml exemple-raud-jeunesse.json; do curl -sfL -o "$D/$f" "$B/$f"; done
for f in Outfit-Bold.ttf Outfit-ExtraBold.ttf; do curl -sfL -o "$D/polices/$f" "$B/polices/$f"; done
pip install -q --break-system-packages faster-whisper opencv-python-headless mido pillow 2>&1 | grep -v -i warn || true
echo "OK : outils dans $D"

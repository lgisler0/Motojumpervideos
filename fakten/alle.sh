#!/bin/bash
# rendert alle fehlenden Vorlagen-Videos, zwei gleichzeitig
cd /home/claude/fakten
python3 -c "
import fakten_daten as d, os
print('\n'.join(e[0] for e in d.DATEN if not os.path.exists(f'videos/fakten_{e[0]}.mp4')))" > /tmp/offen.txt
xargs -a /tmp/offen.txt -P 2 -n 1 sh -c 'python3 fakten_studio.py "$0" >> /tmp/render.log 2>&1 || echo "FEHLER $0" >> /tmp/render.log'
echo "ENDE $(ls videos/*.mp4 | wc -l) Videos"

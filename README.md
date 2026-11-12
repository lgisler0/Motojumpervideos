# Motojumper Videos

Fertige Folgen des YouTube-Kanals **Motojumper** (Lern-Geschichten fuer Kinder) und das Studio, das sie erzeugt.

- `videos/` – fertige Folgen (`.mp4`) mit Titel, Beschreibung und Drehbuch (`.txt`)
- `studio/` – der Code: `motojumper_studio.py` (Drehbuecher + Regie) und `kids_worker.py` (Zeichnen, Stimme, Musik)
- `setup.sh` – installiert alles Noetige

Neue Folge rendern: `./setup.sh && cd studio && python3 motojumper_studio.py <name> --ordner ../videos`

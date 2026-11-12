# Motojumper – Arbeitsanleitung

Dieses Repository gehoert zum YouTube-Kanal **Motojumper** von Loris: kurze Lern-Geschichten (Shorts, 1080x1920,
Englisch) fuer Kleinkinder und Vorschulkinder. Ziel: Kanal aufbauen und spaeter monetarisieren. Deshalb gilt:
**Qualitaet und Abwechslung vor Menge.** Keine Vorlagen-Massenware.

## Feste Regeln

- Jede Folge hat ein **eigenes, neu geschriebenes Drehbuch**: kleine Geschichte (Anfang, Mitte, Schluss) + ein klares
  Lernziel, das ein Kind nach dem Video wirklich kann. Nie eine bestehende Folge nur mit anderen Tieren/Zahlen kopieren.
- Nur die eigenen Figuren: Sunny (Sonne, Erzaehlerin), Momo (Baer), Juju (Hase), Freddy (Frosch), Pip (Kueken),
  Kiki (Katze), Dodo (Hund). Keine geschuetzten Figuren, Marken oder Musik von anderen.
- Inhalte sind fuer kleine Kinder: freundlich, gewaltfrei, nichts Gruseliges, keine Werbung.
- Titel und Beschreibung versprechen nur, was das Video zeigt. Keine Stichwort-Listen.
- **2 Videos pro Tag** (17:00 und 21:00), nie mehr als 3. Kanalname bleibt "Motojumper".
- Mehr Folgen heisst nicht weniger Sorgfalt: lieber eine Folge weniger als eine, die einer alten zu aehnlich ist.
- Vor dem Lesen von `EPISODES.md` kein neues Thema waehlen: dort stehen alle bisherigen Folgen. Themen nicht wiederholen.

## Neue Folgen erstellen

1. `./setup.sh` ausfuehren (installiert Pakete, Schrift, Stimm-Modell).
2. In `studio/motojumper_studio.py` pro Folge einen neuen Eintrag in `EPISODEN` schreiben (Aufbau wie die bestehenden:
   `titel`, `lernziel`, `yt_titel`, `yt_text`, `tags`, `buehne`, `zeilen`). Neue Requisiten als `p_<name>`-Funktion
   ergaenzen und in `PROPS` eintragen. Laenge: 20-35 Sekunden.
3. Rendern: `cd studio && python3 motojumper_studio.py <key> --ordner ../videos`
4. **Pruefen, bevor etwas hochgeht:** aus jeder Folge 2-3 Standbilder ziehen (`ffmpeg -ss <t> -i <mp4> -frames:v 1`)
   und ansehen: Figuren ueberlappen nicht, Text ist lesbar und nicht abgeschnitten, nichts ragt aus dem Bild.
   Bei einzelnen Buchstaben/Lauten die Aussprache mit `kw._K.tokenizer.phonemize(text, "en-us")` kontrollieren.
5. Folge in `EPISODES.md` eintragen.
6. Qualitaet: immer 1080x1920, 60 Bilder/s, `-preset slow -crf 15`, Ton 256k (so ist das Studio eingestellt, nicht senken).
7. Committen und pushen (Branch `main`, **ein Video pro Push**, damit der Push klein bleibt).

## Einplanen (Metricool)

- Brand/blogId: `8045262`, Zeitzone `Europe/Zurich`, zwei Sendeplaetze pro Tag: **17:00** und **21:00**.
- Zuerst `getScheduledPosts` aufrufen: Sendeplaetze, die schon belegt sind, auslassen. Neue Folgen fruehestens
  **2 Tage im Voraus** einplanen, damit Loris sie vorher ansehen und stoppen kann.
- Video-Link mit Commit-Hash (nicht `main`, wegen Zwischenspeicher):
  `https://raw.githubusercontent.com/lgisler0/Motojumpervideos/<commit>/videos/motojumper_<key>.mp4`
- `createScheduledPost` mit: `providers: [{"network":"youtube"}]` und
  `youtubeData: {title, type: "short", privacy: "public", tags, category: "EDUCATION", madeForKids: true, isAiGeneratedContent: false}`.
  `madeForKids` muss immer `true` sein.
- **Titel:** kurz und natuerlich, hoechstens 60 Zeichen, Aufbau `<Was passiert>! <1 Emoji> <Lernthema> #shorts`,
  z. B. `Kiki Builds a House! 🏠 Learn Shapes #shorts`. Keine Stichwort-Ketten, kein "| Story for Kids".
- **Beschreibung (`text`):** lebhaft und mit Emojis, nicht monoton. Aufbau:
  1. passendes Emoji + 2-3 kurze Saetze, die die Geschichte anreissen und neugierig machen (1-2 weitere Emojis im Text);
  2. Leerzeile, dann `✨ What you learn: ...`;
  3. Leerzeile, dann `🌈 New learning stories every day on Motojumper, with Momo, Juju and friends! 💛`;
  4. Leerzeile, dann genau 8 Hashtags: `#shorts`, drei zum Thema der Folge (z. B. `#learnshapes #shapesforkids #shapes`),
     dann immer `#kidslearning #preschool #toddlerlearning #educationalvideos`.
  Nur Hashtags, die zum Video passen. Nie mehr als 10 (zu viele wirken wie Spam).
- **Tags:** 6-8 Suchbegriffe zum Thema, dazu immer `preschool learning`, `toddler learning`, `Momo and Juju`, `Motojumper`.
- Meldet Metricool ein Limit oder einen Fehler: nicht umgehen, sondern aufhoeren und Loris berichten.

## Abschluss

Loris kurz auf Deutsch berichten: welche Folgen (Titel, Lernziel, Datum) eingeplant sind, was nicht geklappt hat,
und dass er sie im Ordner `videos/` ansehen kann. Keine erfundenen Zahlen oder Erfolgsversprechen.

# STAND – Basis für neue Chats (18.11.2026, 23:00)

Diese Datei ist der aktuelle Stand. Ein neuer Chat liest zuerst diese Datei (und CLAUDE.md, rekorde/WEITERMACHEN.md ist veraltet) und arbeitet danach weiter.
Sprache mit Loris: **Deutsch (Schweiz, «ss» statt «ß»), einfach und kurz**. Er schreibt oft per Sprache mit Tippfehlern.

## 1. Kanäle und Ziel
Ziel: beide Kanäle wachsen lassen, Play Button holen, monetarisieren.

| Kanal | Inhalt | Metricool blogId | Regeln |
|---|---|---|---|
| **Motojumper** | Lern-Geschichten für Kleinkinder | `8045262` | siehe `CLAUDE.md` (2 Videos/Tag 17:00 + 21:00, madeForKids **true**, Figuren Sunny/Momo/Juju/…) |
| **Wissenskanal** (englisch, YouTube UC7joBao8qrnJtz93Bwe1lKg) | Wissens-Shorts, **ab Dezember Weltrekorde** | `8066320` | madeForKids false, category SCIENCE_TECHNOLOGY, isAiGeneratedContent false (animiert) |

Zeitzone `Europe/Zurich`. Name, Beschreibung und Banner vom Wissenskanal hat Loris selbst angepasst – dort nichts ändern.

## 2. Was gerade eingeplant ist (Wissenskanal)
- 6 Videos pro Tag (12, 14, 16, 18, 20, 22 Uhr) bis **30.11.**, alle mit neuem Einstieg (Repo `fakten/v2/`).
- Zusätzlich am 18.11. um 19:00 das 3D-Tiefsee-Video (`fakten/3d/fakten_tiefsee3d.mp4`).
- **Ab 1.12.: nur noch Weltrekorde.** Erinnerung am 27.11. 10:00 (geplante Aufgabe), den Plan Loris vorzulegen – vorher nichts posten und keine Credits ausgeben.

## 3. Weltrekorde ab 1.12. (2 pro Tag: 12:00 und 19:00)
Eingeplant (Metricool 8066320):
Auf Wunsch von Loris (19.11.) vorgezogen, jeweils 19:00 zusätzlich zum bisherigen Plan:
- 19.11. 19:00 ThrustSSC (`rekorde/3d/rekord_thrust_3d.mp4`)
- 20.11. 19:00 Airbus A380 (`rekorde/3d/rekord_a380_3d.mp4`)
- 21.11. 19:00 Burj Khalifa (`rekorde/3d/rekord_burj_3d.mp4`)
- 22.11. 19:00 BelAZ 75710 (`rekorde/3d/rekord_belaz_3d.mp4`, Quellen `rekorde/belaz3d.py`, `belaz_schnitt.py`)
- 23.11. 19:00 Fahrer-Geschichte «How Do You Stop an 800-Tonne Truck?» (`rekorde/3d/rekord_fahrer_3d.mp4`, neuer Stil mit Person + Aufgabe)
- 22.11.: Loris: «nur noch so» (3D, eine Person, ein Job) und **nur 2 Posts pro Tag** (13:00 + 19:00). Alle 46 alten 2D-Fakten-Posts (22.–30.11.) auf Entwurf gesetzt (nicht geloescht).
- Eingeplant: 22.11. 19:00 BelAZ, 23.11. 13:00 Fensterputzer (c26a91e), 23.11. 19:00 BelAZ-Fahrer, 24.11. 13:00 Tankwart (15865d2), 24.11. 19:00 Stratosphaeren-Sprung (fa591f7). Ab 25.11. leer -> neue 3D-Videos noetig (Render ca. 5-6 h pro Video).
- Naechste Ideen: Atem anhalten (Vitomir Maričić 29:03), Kami Rita Sherpa (Everest 32x).
Neue 3D-Rekord-Videos (ca. 2–3 h pro Video) immer zuerst Loris zeigen.
Die 2D-Weltrekord-Videos werden **nicht** mehr verwendet (Loris will nur noch 3D).

## 4. Feste Wünsche von Loris (immer einhalten)
- **Stimme: ab jetzt immer Frauenstimme «Hope – upbeat and clear»** (ElevenLabs voice_id `tnSpp4vdxKPjI9w0GnoV`, Modell `eleven_v4`). Alte Männerstimme «Ethan» (`uB5dGadiIOtRLnqbQl9M`) nicht mehr verwenden.
- **Format Weltrekorde: nur noch 3D (Blender) wie ThrustSSC/A380/Burj**, Zahlenkarte oben, Untertitel (aktives Wort gelb).
- **Daten aus Guinness World Records** (guinnessworldrecords.com) nehmen.
- **Musik: spannend aber leise** (`ton_spannung` in `rk_basis.py`: Bass-Puls, Ticken, Spannungsbogen vor Schnitten, Ducking unter der Stimme).
- Logos/Markennamen nicht nachbauen (Markenrecht), sonst Form/Farben/Bemalung 1:1.
- **Loop:** letzter Satz führt in den ersten (z. B. «…still measures» → «Almost eighty meters.»), letztes Bild = erstes Bild.
- **Objekte 1:1 erkennbar:** Was im Text vorkommt (Eiffelturm, G-Klasse, Dinosaurier …), muss im Bild sofort erkennbar und massstabsgetreu sein – auch wenn es länger dauert. Vor dem Rendern Standbilder prüfen.
- Nichts darf nach KI-Massenware aussehen. Spannend: immer Bewegung, Kamerafahrten.
- Alle Zahlen vorher im Internet prüfen.
- Vor dem Posten Loris das Video zeigen, ausser er sagt ausdrücklich «poste».
- Nichts löschen ohne Rückfrage, keine Käufe ohne Zustimmung, Passwörter gibt nur Loris ein.

## 5. Beschreibung / Titel (Recherche 18.11.)
- Titel kurz und sauber, max. ~60 Zeichen, ein Emoji.
- 3–5 Hashtags **in die Beschreibung** (die ersten 3 erscheinen über dem Titel).
- Beschreibung: 1. Satz mit Stichwort + Neugier, dann Frage an Zuschauer, dann Hashtags.
- Erster Kommentar mit Frage (Metricool `firstCommentText`).
- «Ähnliches Video»-Link geht nur in YouTube Studio am PC (nicht per Metricool) → Loris setzt ihn selbst, z. B. Burj ↔ Tiefsee.

## 6. Technik
- Repo `lgisler0/Motojumpervideos`, Branch `main`, ein Video pro Commit, Dateien < 100 MB.
- Metricool-Video-Link mit Commit-Hash: `https://raw.githubusercontent.com/lgisler0/Motojumpervideos/<commit>/<pfad>`.
- `updateScheduledPost` braucht id + uuid + vollen Inhalt (id ändert sich danach). `getScheduledPosts` nur in 2–3-Tages-Stücken abfragen.
- 3D: `rekorde/burj3d_v2.py`, `rekorde/a380_3d.py` (Blender als Python-Modul `bpy`, Cycles CPU, halbe Grösse, 15 fps) → Schnitt `burj3d_schnitt.py` / `a380_schnitt.py` (minterpolate auf 60 fps, Overlays aus `rk_basis.py`). Rendern dauert ca. 1–2 h pro Video.
- 2D-Engine: `rekorde/rk_basis.py`, `rk_szenen.py`, `rk_szenen2.py`. Stimmen + Wortzeiten: `rekorde/stimme/` (`worte.json`, mit faster-whisper `base.en`).
- 3D-Grundvideos ohne Ton/Schrift zum Neuvertonen: `rekorde/3d/burj3d_basis.mp4`, `rekorde/3d/a380_basis.mp4`.
- Wissens-Vorlagen (alt): `fakten/fakten_studio.py`, `fakten_daten.py`, `plan.json`.
- ElevenLabs-Abo «Creator» (131'000 Credits/Monat). Higgsfield: nur lesen per Connector, Erzeugen nur per Browser; Plus-Abo 1'200 Credits/Monat.
- Geplante Aufgaben: wöchentlich Kinderkanal (Do), Erinnerung 27.11. 10:00 Weltrekord-Plan.

## 7. Analyse-Stand (17./18.11.)
- Shorts bekommen ca. 200–1'000 Aufrufe; 60–66 % wischen weg, Wiedergabe Ø 0:17 → der Einstieg war das Problem → neuer Einstieg ab 17.11.
- Kinderkanal stagniert (12 Abonnenten). Frage an Loris, ob neue Kinder-Folgen pausieren sollen, ist noch offen.


## Kinderkanal Motojumper: PAUSIERT (19.11., Wunsch Loris)
- Alle 29 geplanten Folgen (20.11.–19.12.) in Metricool auf Entwurf gesetzt (nichts gelöscht, kann wieder aktiviert werden).
- Geplante Aufgaben «Motojumper Wochenfolgen» und «Motojumper: Auswertung nach 10 Videos» ausgeschaltet.
- Fokus nur noch auf Wissenskanal / 3D-Weltrekorde. Tiefsee-3D: 52,5 % bis zum Ende angesehen (älter 2D: ~35–40 %).


## Realistische Menschen (ab 20.11.)
- Modul `rekorde/mensch_mh.py` (Klasse `Arbeiter`): MakeHuman/MPFB2-Basismensch (CC0) mit Skelett, Augen, Haut; Kleidung als Hüllen mit Alpha-Masken (Hemd mit Warnweste, Hose, Handschuhe), Stiefel, Helm, Augenbrauen, Bartschatten.
- Vorher einrichten: `git clone --depth 1 https://github.com/makehumancommunity/mpfb2.git /tmp/mpfb2_test` und
  `git clone --depth 1 --filter=blob:none --sparse https://github.com/makehumancommunity/makehuman.git /tmp/mh && cd /tmp/mh && git sparse-checkout set makehuman/data`.
- Posen über Knochen (`dreh(bone, x,y,z)`), z. B. Arme runter: `upperarm01.L` z=-0.72, `upperarm01.R` z=+0.72.
- Regel von Loris: Figuren und Details in jedem neuen Clip so detailliert wie möglich.

## Neue Richtung (21.11., Loris): spannende Rekorde, die MENSCHEN geschafft haben
- Format bleibt: Person mit Aufgabe (Zack-D-Stil), realistische MPFB-Figur, Hope-Stimme, Loop, Zahlen geprüft (GWR zuerst).
- Echte Rekordhalter werden mit Namen genannt, aber als allgemeine Figur gezeigt (kein Nachbau ihres Gesichts).
- Themen-Ideen (geprüft 21.11.): höchster Fallschirm-Freifall Alan Eustace 41'422 m (2014); längstes Luftanhalten Vitomir Maričić 29:03 (2025, mit Sauerstoff-Vorbereitung); meiste Everest-Besteigungen Kami Rita Sherpa (32., Mai 2026).

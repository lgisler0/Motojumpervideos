# Weltrekord-Videos – Stand 18.11.2026

- 10 Weltrekord-Videos (2D, Loop) gemacht mit `rk_szenen.py <key>` (Stimme: ElevenLabs "Ethan", voice_id uB5dGadiIOtRLnqbQl9M).
- 3D-Test Burj Khalifa: Blender-Bilder in `3d/burj3d_basis.mp4` (1080x1920, 60 fps, OHNE Overlays/Ton).
- Offen: Loris will ab jetzt immer eine **Frauenstimme** (ElevenLabs). Burj-3D neu vertonen:
  1. ElevenLabs-Stimme (Frau) mit Text `texte.json["burj"]` erzeugen -> `stimme/burj.mp3` ersetzen, Wortzeiten mit faster-whisper neu in `stimme/worte.json`.
  2. Stimme auf die Videolaenge (23.21 s) bringen (ffmpeg atempo), dann `burj3d_schnitt.py` mit `_b3basis.mp4` = `3d/burj3d_basis.mp4`.
  3. Loris das Video zeigen, dann in Metricool (Brand 8066320, Wissenskanal) einplanen.
- Titel: "The Tallest Building on Earth 🏙️ Burj Khalifa in 3D"
- Beschreibung: "828 meters tall 🏙️ The Burj Khalifa has been the tallest building on Earth since 2010, more than twice as tall as the Eiffel Tower. But in Saudi Arabia, something bigger is rising… 👀\n\nWhich world record should we show next? Tell us in the comments 👇\n\n#burjkhalifa #worldrecord #shorts"
- Erster Kommentar: "Would you ride all the way to the top? 🛗"
- "Related video"-Link nur in YouTube Studio (Desktop) moeglich -> Loris: auf das Tiefsee-3D-Short verlinken.
